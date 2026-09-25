# Databricks notebook source
# MAGIC %md
# MAGIC # Inventory Optimization — Linear Programming
# MAGIC Allocates seats across price tiers per section to maximize total revenue, using demand forecasts as inputs.

# COMMAND ----------

import mlflow
import numpy as np
import pandas as pd
from scipy.optimize import linprog
import json
import tempfile
import os

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Load Data

# COMMAND ----------

demand_predictions = spark.read.table("boxscore.models.demand_predictions").toPandas()
seat_facts = spark.read.table("boxscore.raw.seat_facts").toPandas()
pricing = spark.read.table("boxscore.raw.pricing").toPandas()
inventory = spark.read.table("boxscore.raw.available_inventory").toPandas()

demand_predictions["game_date"] = pd.to_datetime(demand_predictions["game_date"])
print(f"Games to optimize: {demand_predictions['game_id'].nunique()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Define Sections and Price Tiers

# COMMAND ----------

SECTIONS = seat_facts["section_id"].unique()

section_capacity = seat_facts.groupby("section_id")["seat_id"].count().to_dict()

price_tiers = pricing.groupby(["section_id", "price_tier"]).agg(
    tier_price=("current_price", "median"),
    tier_count=("seat_id", "count"),
).reset_index()

section_tiers = {}
for section_id in SECTIONS:
    tiers = price_tiers[price_tiers["section_id"] == section_id].sort_values("tier_price")
    if len(tiers) == 0:
        continue
    section_tiers[section_id] = tiers[["price_tier", "tier_price", "tier_count"]].to_dict("records")

print(f"Sections with tiers: {len(section_tiers)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Optimization Model

# COMMAND ----------

MIN_AVAILABILITY_PCT = 0.10
MAX_PRICE_CHANGES_PER_DAY = 2

def optimize_game(game_id, predicted_demand, section_tiers, section_capacity):
    """Optimize seat allocation for one game. Returns allocation plan and objective value."""
    decision_vars = []
    for section_id, tiers in section_tiers.items():
        for tier in tiers:
            decision_vars.append({
                "section_id": section_id,
                "price_tier": tier["price_tier"],
                "tier_price": tier["tier_price"],
                "max_seats": tier["tier_count"],
            })

    n_vars = len(decision_vars)
    if n_vars == 0:
        return [], 0.0

    c = np.array([-d["tier_price"] for d in decision_vars])

    A_ub = []
    b_ub = []

    for section_id in section_tiers:
        cap = section_capacity.get(section_id, 0)
        indices = [i for i, d in enumerate(decision_vars) if d["section_id"] == section_id]
        if not indices:
            continue

        row = np.zeros(n_vars)
        for idx in indices:
            row[idx] = 1.0
        A_ub.append(row)
        b_ub.append(cap * (1.0 - MIN_AVAILABILITY_PCT))

    for i, d in enumerate(decision_vars):
        row = np.zeros(n_vars)
        row[i] = 1.0
        A_ub.append(row)
        b_ub.append(d["max_seats"])

    bounds = [(0, d["max_seats"]) for d in decision_vars]

    if not A_ub:
        return [], 0.0

    A_ub = np.array(A_ub)
    b_ub = np.array(b_ub)

    result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")

    if not result.success:
        print(f"  WARNING: Optimization failed for game {game_id}: {result.message}")
        return [], 0.0

    allocation = []
    for i, d in enumerate(decision_vars):
        allocated = int(round(result.x[i]))
        if allocated > 0:
            allocation.append({
                "game_id": game_id,
                "section_id": d["section_id"],
                "price_tier": d["price_tier"],
                "tier_price": d["tier_price"],
                "allocated_seats": allocated,
                "expected_revenue": allocated * d["tier_price"],
            })

    total_revenue = -result.fun
    return allocation, total_revenue

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Run Optimization Across Games

# COMMAND ----------

all_allocations = []
game_results = []

for _, row in demand_predictions.iterrows():
    game_id = row["game_id"]
    predicted_demand = row["predicted_demand"]

    allocation, total_revenue = optimize_game(game_id, predicted_demand, section_tiers, section_capacity)
    all_allocations.extend(allocation)

    total_allocated = sum(a["allocated_seats"] for a in allocation if a["game_id"] == game_id)
    game_results.append({
        "game_id": game_id,
        "predicted_demand": predicted_demand,
        "total_allocated": total_allocated,
        "expected_revenue": total_revenue,
    })

results_df = pd.DataFrame(game_results)
allocations_df = pd.DataFrame(all_allocations)

print(f"Optimized {len(results_df)} games")
print(f"Total expected revenue: ${results_df['expected_revenue'].sum():,.0f}")
print(f"Total allocation records: {len(allocations_df)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. MLflow Logging

# COMMAND ----------

mlflow.set_experiment("/Shared/boxscore_inventory_optimizer")

with mlflow.start_run(run_name="linprog_optimizer_v1") as run:
    mlflow.log_params({
        "min_availability_pct": MIN_AVAILABILITY_PCT,
        "max_price_changes_per_day": MAX_PRICE_CHANGES_PER_DAY,
        "n_sections": len(section_tiers),
        "n_games_optimized": len(results_df),
        "solver": "scipy.optimize.linprog (highs)",
    })

    mlflow.log_metric("total_expected_revenue", float(results_df["expected_revenue"].sum()))
    mlflow.log_metric("avg_revenue_per_game", float(results_df["expected_revenue"].mean()))
    mlflow.log_metric("avg_seats_allocated", float(results_df["total_allocated"].mean()))

    with tempfile.TemporaryDirectory() as tmpdir:
        results_path = os.path.join(tmpdir, "game_optimization_results.csv")
        results_df.to_csv(results_path, index=False)
        mlflow.log_artifact(results_path, "results")

        alloc_path = os.path.join(tmpdir, "allocation_plan.csv")
        allocations_df.to_csv(alloc_path, index=False)
        mlflow.log_artifact(alloc_path, "results")

        summary = {
            "total_games": len(results_df),
            "total_revenue": float(results_df["expected_revenue"].sum()),
            "avg_revenue": float(results_df["expected_revenue"].mean()),
            "total_seats_allocated": int(results_df["total_allocated"].sum()),
        }
        summary_path = os.path.join(tmpdir, "optimization_summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        mlflow.log_artifact(summary_path, "results")

    print(f"Run ID: {run.info.run_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Write Allocation Plan to Unity Catalog

# COMMAND ----------

if len(allocations_df) > 0:
    allocations_df["optimization_date"] = pd.Timestamp.now()
    spark_alloc = spark.createDataFrame(allocations_df)
    spark_alloc.write.mode("overwrite").saveAsTable("boxscore.models.inventory_allocations")
    print(f"Wrote {len(allocations_df)} allocation records")
