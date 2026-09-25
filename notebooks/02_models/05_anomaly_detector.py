# Databricks notebook source
# MAGIC %md
# MAGIC # Anomaly Detection — Isolation Forest + Statistical Thresholds
# MAGIC Flags games with unusual demand spikes/drops, price outliers, or inventory anomalies for human review.

# COMMAND ----------

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import tempfile
import os

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Load Data

# COMMAND ----------

demand_features = spark.read.table("boxscore.features.demand_features").toPandas()
pricing_features = spark.read.table("boxscore.features.pricing_features").toPandas()
inventory_features = spark.read.table("boxscore.features.inventory_features").toPandas()

game_demand = demand_features.groupby("game_id").agg({
    "page_view_avg_7d": "mean",
    "sales_velocity_24h": "mean",
    "sales_velocity_48h": "mean",
}).reset_index()

game_pricing = pricing_features.groupby("game_id").agg({
    "current_price": "mean",
    "price_vs_median": "mean",
    "secondary_market_premium": "mean",
    "price_change_count_7d": "sum",
}).reset_index()

game_inventory = inventory_features.groupby("game_id").agg({
    "sell_through_rate": "mean",
    "remaining_inventory_pct": "mean",
}).reset_index()

df = game_demand.merge(game_pricing, on="game_id", how="outer")
df = df.merge(game_inventory, on="game_id", how="outer")
df = df.fillna(0)

print(f"Games to analyze: {len(df)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Statistical Baselines (IQR & Z-Score)

# COMMAND ----------

anomaly_cols = [
    "page_view_avg_7d", "sales_velocity_24h",
    "current_price", "secondary_market_premium",
    "sell_through_rate", "remaining_inventory_pct",
]

available_cols = [c for c in anomaly_cols if c in df.columns]
stat_flags = pd.DataFrame(index=df.index)

for col in available_cols:
    values = df[col]
    q1 = values.quantile(0.25)
    q3 = values.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    stat_flags[f"{col}_iqr_anomaly"] = ((values < lower) | (values > upper)).astype(int)

    mean = values.mean()
    std = values.std()
    z_scores = (values - mean) / (std + 1e-9)
    stat_flags[f"{col}_zscore"] = z_scores.abs()
    stat_flags[f"{col}_zscore_anomaly"] = (z_scores.abs() > 2.5).astype(int)

df["stat_anomaly_count"] = stat_flags[[c for c in stat_flags.columns if c.endswith("_iqr_anomaly")]].sum(axis=1)
print(f"Games with >= 1 statistical anomaly: {(df['stat_anomaly_count'] > 0).sum()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Isolation Forest

# COMMAND ----------

X = df[available_cols].fillna(0)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

iso_params = {
    "n_estimators": 200,
    "contamination": 0.05,
    "max_samples": "auto",
    "max_features": 1.0,
    "random_state": 42,
}

iso_model = IsolationForest(**iso_params)
iso_model.fit(X_scaled)

df["iso_score"] = iso_model.decision_function(X_scaled)
df["iso_anomaly"] = iso_model.predict(X_scaled)
df["iso_anomaly_flag"] = (df["iso_anomaly"] == -1).astype(int)

print(f"Isolation Forest anomalies: {df['iso_anomaly_flag'].sum()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Combined Severity Score

# COMMAND ----------

df["severity_score"] = (
    df["stat_anomaly_count"] * 0.3
    + df["iso_anomaly_flag"] * 0.5
    + (1 - (df["iso_score"] - df["iso_score"].min()) / (df["iso_score"].max() - df["iso_score"].min() + 1e-9)) * 0.2
)

df["severity_label"] = pd.cut(
    df["severity_score"],
    bins=[-0.01, 0.2, 0.5, 1.0],
    labels=["normal", "warning", "critical"],
)

flagged = df[df["severity_label"].isin(["warning", "critical"])].copy()
print(f"Flagged games: {len(flagged)} ({len(flagged[flagged['severity_label'] == 'critical'])} critical)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Visualization

# COMMAND ----------

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

if "page_view_avg_7d" in df.columns and "sales_velocity_24h" in df.columns:
    ax = axes[0, 0]
    colors = df["iso_anomaly_flag"].map({0: "steelblue", 1: "red"})
    ax.scatter(df["page_view_avg_7d"], df["sales_velocity_24h"], c=colors, alpha=0.6, edgecolors="k", linewidths=0.3)
    ax.set_xlabel("Page View Avg (7d)")
    ax.set_ylabel("Sales Velocity (24h)")
    ax.set_title("Demand Anomalies")

ax = axes[0, 1]
ax.hist(df["iso_score"], bins=40, edgecolor="black", alpha=0.7)
ax.axvline(x=0, color="red", linestyle="--", label="Threshold")
ax.set_xlabel("Isolation Score")
ax.set_title("Anomaly Score Distribution")
ax.legend()

ax = axes[1, 0]
severity_counts = df["severity_label"].value_counts()
severity_counts.plot(kind="bar", ax=ax, color=["green", "orange", "red"])
ax.set_title("Severity Distribution")
ax.set_ylabel("Count")

ax = axes[1, 1]
ax.hist(df["severity_score"], bins=30, edgecolor="black", alpha=0.7, color="coral")
ax.set_xlabel("Severity Score")
ax.set_title("Combined Severity Scores")

plt.tight_layout()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. MLflow Logging

# COMMAND ----------

mlflow.set_experiment("/Shared/boxscore_anomaly_detector")

with mlflow.start_run(run_name="isolation_forest_v1") as run:
    mlflow.log_params(iso_params)
    mlflow.log_param("n_features", len(available_cols))
    mlflow.log_param("n_games", len(df))

    mlflow.log_metric("total_anomalies", int(df["iso_anomaly_flag"].sum()))
    mlflow.log_metric("anomaly_rate", float(df["iso_anomaly_flag"].mean()))
    mlflow.log_metric("critical_count", int((df["severity_label"] == "critical").sum()))
    mlflow.log_metric("warning_count", int((df["severity_label"] == "warning").sum()))

    mlflow.sklearn.log_model(iso_model, artifact_path="iso_model")

    with tempfile.TemporaryDirectory() as tmpdir:
        fig.savefig(os.path.join(tmpdir, "anomaly_plots.png"), dpi=150, bbox_inches="tight")
        mlflow.log_artifact(os.path.join(tmpdir, "anomaly_plots.png"), "plots")

        flagged_path = os.path.join(tmpdir, "flagged_games.csv")
        flagged.to_csv(flagged_path, index=False)
        mlflow.log_artifact(flagged_path, "results")

    print(f"Run ID: {run.info.run_id}")

plt.close("all")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Write Anomaly Flags to Unity Catalog

# COMMAND ----------

output = df[["game_id", "iso_score", "iso_anomaly_flag", "stat_anomaly_count", "severity_score", "severity_label"]].copy()
output["detection_date"] = pd.Timestamp.now()

spark_output = spark.createDataFrame(output)
spark_output.write.mode("overwrite").saveAsTable("boxscore.models.anomaly_flags")
print(f"Wrote {len(output)} anomaly flag records")
