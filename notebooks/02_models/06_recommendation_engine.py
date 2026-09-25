# Databricks notebook source
# MAGIC %md
# MAGIC # Pricing Recommendation Engine
# MAGIC Combines demand forecast, price sensitivity, and inventory optimizer outputs into discrete pricing recommendations with confidence scores.

# COMMAND ----------

import mlflow
import numpy as np
import pandas as pd
import json
import tempfile
import os

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Load Model Outputs

# COMMAND ----------

demand_preds = spark.read.table("boxscore.models.demand_predictions").toPandas()
inventory_alloc = spark.read.table("boxscore.models.inventory_allocations").toPandas()
anomaly_flags = spark.read.table("boxscore.models.anomaly_flags").toPandas()
pricing = spark.read.table("boxscore.raw.pricing").toPandas()
event_details = spark.read.table("boxscore.raw.event_details").toPandas()

print(f"Demand predictions: {len(demand_preds)} games")
print(f"Inventory allocations: {len(inventory_alloc)} records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Load Price Sensitivity Model

# COMMAND ----------

from mlflow.tracking import MlflowClient
client = MlflowClient()

try:
    model_versions = client.get_latest_versions("boxscore-price-sensitivity", stages=["Production", "None"])
    if model_versions:
        latest = model_versions[0]
        sensitivity_model = mlflow.xgboost.load_model(f"models:/boxscore-price-sensitivity/{latest.version}")
        print(f"Loaded price sensitivity model v{latest.version}")
    else:
        sensitivity_model = None
        print("WARNING: No price sensitivity model found, using heuristic")
except Exception as e:
    sensitivity_model = None
    print(f"WARNING: Could not load sensitivity model: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Generate Price Scenarios

# COMMAND ----------

PRICE_ADJUSTMENTS = [-0.15, -0.10, -0.05, 0.0, 0.05, 0.10, 0.15, 0.20]

current_prices = pricing.groupby(["game_id", "section_id"]).agg(
    current_price=("current_price", "median"),
).reset_index()

scenarios = []
for _, row in current_prices.iterrows():
    for adj in PRICE_ADJUSTMENTS:
        scenarios.append({
            "game_id": row["game_id"],
            "section_id": row["section_id"],
            "current_price": row["current_price"],
            "adjustment_pct": adj,
            "proposed_price": row["current_price"] * (1 + adj),
        })

scenarios_df = pd.DataFrame(scenarios)
print(f"Price scenarios generated: {len(scenarios_df)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Score Scenarios

# COMMAND ----------

demand_lookup = demand_preds.set_index("game_id")["predicted_demand"].to_dict()
anomaly_lookup = anomaly_flags.set_index("game_id")["severity_label"].to_dict()
alloc_lookup = inventory_alloc.groupby(["game_id", "section_id"])["allocated_seats"].sum().to_dict()

def estimate_revenue(row):
    demand = demand_lookup.get(row["game_id"], 30000)
    anomaly = anomaly_lookup.get(row["game_id"], "normal")
    allocated = alloc_lookup.get((row["game_id"], row["section_id"]), 100)

    demand_factor = min(demand / 35000, 1.5)
    anomaly_factor = {"normal": 1.0, "warning": 0.9, "critical": 0.8}.get(str(anomaly), 1.0)

    price_elasticity = -0.8
    volume_change = 1 + price_elasticity * row["adjustment_pct"]
    estimated_volume = allocated * demand_factor * anomaly_factor * volume_change
    estimated_volume = max(estimated_volume, 0)

    return row["proposed_price"] * estimated_volume

scenarios_df["estimated_revenue"] = scenarios_df.apply(estimate_revenue, axis=1)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Select Best Recommendations

# COMMAND ----------

best_idx = scenarios_df.groupby(["game_id", "section_id"])["estimated_revenue"].idxmax()
recommendations = scenarios_df.loc[best_idx].copy()

baseline = scenarios_df[scenarios_df["adjustment_pct"] == 0.0].set_index(["game_id", "section_id"])["estimated_revenue"]
recommendations["baseline_revenue"] = recommendations.set_index(["game_id", "section_id"]).index.map(
    lambda x: baseline.get(x, 0)
)
recommendations["revenue_lift_pct"] = (
    (recommendations["estimated_revenue"] - recommendations["baseline_revenue"])
    / (recommendations["baseline_revenue"] + 1e-9)
    * 100
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Confidence Scoring

# COMMAND ----------

def compute_confidence(row):
    section_scenarios = scenarios_df[
        (scenarios_df["game_id"] == row["game_id"]) & (scenarios_df["section_id"] == row["section_id"])
    ]
    revenues = section_scenarios["estimated_revenue"].values
    best_rev = row["estimated_revenue"]
    if len(revenues) < 2 or best_rev == 0:
        return "low"

    second_best = sorted(revenues, reverse=True)[1] if len(revenues) > 1 else 0
    margin = (best_rev - second_best) / (best_rev + 1e-9)
    cv = revenues.std() / (revenues.mean() + 1e-9)

    if margin > 0.05 and cv < 0.3:
        return "high"
    elif margin > 0.02 or cv < 0.5:
        return "medium"
    return "low"

recommendations["confidence"] = recommendations.apply(compute_confidence, axis=1)

confidence_dist = recommendations["confidence"].value_counts()
print("Confidence distribution:")
print(confidence_dist)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Format Recommendations

# COMMAND ----------

recommendations["recommendation"] = recommendations.apply(
    lambda r: (
        f"{'Increase' if r['adjustment_pct'] > 0 else 'Decrease' if r['adjustment_pct'] < 0 else 'Hold'} "
        f"price by {abs(r['adjustment_pct'])*100:.0f}% to ${r['proposed_price']:.2f}"
    ),
    axis=1,
)

recommendations["action"] = recommendations["adjustment_pct"].apply(
    lambda x: "increase" if x > 0 else "decrease" if x < 0 else "hold"
)

output_cols = [
    "game_id", "section_id", "current_price", "proposed_price",
    "adjustment_pct", "action", "recommendation",
    "estimated_revenue", "baseline_revenue", "revenue_lift_pct",
    "confidence",
]

final_recommendations = recommendations[output_cols].copy()
final_recommendations["recommendation_date"] = pd.Timestamp.now()

print(f"\nTotal recommendations: {len(final_recommendations)}")
print(f"Price increases: {(final_recommendations['action'] == 'increase').sum()}")
print(f"Price decreases: {(final_recommendations['action'] == 'decrease').sum()}")
print(f"Hold:            {(final_recommendations['action'] == 'hold').sum()}")
print(f"Avg lift: {final_recommendations['revenue_lift_pct'].mean():.2f}%")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. MLflow Logging

# COMMAND ----------

mlflow.set_experiment("/Shared/boxscore_recommendation_engine")

with mlflow.start_run(run_name="recommendation_engine_v1") as run:
    mlflow.log_params({
        "price_adjustments": str(PRICE_ADJUSTMENTS),
        "n_games": int(final_recommendations["game_id"].nunique()),
        "n_sections": int(final_recommendations["section_id"].nunique()),
        "n_recommendations": len(final_recommendations),
    })

    mlflow.log_metric("avg_revenue_lift_pct", float(final_recommendations["revenue_lift_pct"].mean()))
    mlflow.log_metric("median_revenue_lift_pct", float(final_recommendations["revenue_lift_pct"].median()))
    mlflow.log_metric("high_confidence_pct", float((final_recommendations["confidence"] == "high").mean()))
    mlflow.log_metric("increase_count", int((final_recommendations["action"] == "increase").sum()))
    mlflow.log_metric("decrease_count", int((final_recommendations["action"] == "decrease").sum()))
    mlflow.log_metric("hold_count", int((final_recommendations["action"] == "hold").sum()))

    with tempfile.TemporaryDirectory() as tmpdir:
        recs_path = os.path.join(tmpdir, "recommendations.csv")
        final_recommendations.to_csv(recs_path, index=False)
        mlflow.log_artifact(recs_path, "recommendations")

        summary = {
            "total_recommendations": len(final_recommendations),
            "avg_lift": float(final_recommendations["revenue_lift_pct"].mean()),
            "confidence_distribution": confidence_dist.to_dict(),
            "action_distribution": final_recommendations["action"].value_counts().to_dict(),
        }
        with open(os.path.join(tmpdir, "summary.json"), "w") as f:
            json.dump(summary, f, indent=2, default=str)
        mlflow.log_artifact(os.path.join(tmpdir, "summary.json"), "recommendations")

    print(f"Run ID: {run.info.run_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Write to Unity Catalog

# COMMAND ----------

spark_recs = spark.createDataFrame(final_recommendations)
spark_recs.write.mode("overwrite").saveAsTable("boxscore.models.price_recommendations")
print(f"Wrote {len(final_recommendations)} recommendations to boxscore.models.price_recommendations")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Continuous Learning — Outcome Tracking Template
# MAGIC After games complete, join actual outcomes back to recommendations:
# MAGIC ```python
# MAGIC # Post-game evaluation (run after games are played)
# MAGIC actuals = spark.read.table("boxscore.raw.sales")
# MAGIC recommended = spark.read.table("boxscore.models.price_recommendations")
# MAGIC # Join on game_id, section_id and compare actual_revenue vs estimated_revenue
# MAGIC # Log the evaluate → recommend → act → measure → learn cycle metrics
# MAGIC ```
