# Databricks notebook source
# MAGIC %md
# MAGIC # Model Validation — Champion/Challenger Framework
# MAGIC Compares a new challenger model against the current production champion on a holdout test set.
# MAGIC Supports demand, pricing, and revenue model types.

# COMMAND ----------

import mlflow
from mlflow.tracking import MlflowClient
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, FloatType, TimestampType, IntegerType
import numpy as np
from datetime import datetime

client = MlflowClient()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

CATALOG = "boxscore"
MONITORING_SCHEMA = "monitoring"
METRICS_TABLE = f"{CATALOG}.{MONITORING_SCHEMA}.model_metrics_log"

MODEL_CONFIGS = {
    "demand": {
        "registered_name": "boxscore-demand-forecast",
        "target_col": "actual_demand",
        "prediction_col": "predicted_demand",
        "test_table": f"{CATALOG}.features.demand_features",
        "mape_threshold": 0.15,
        "r2_threshold": 0.70,
        "max_bias_pct": 0.05,
    },
    "pricing": {
        "registered_name": "boxscore-price-sensitivity",
        "target_col": "actual_conversion_rate",
        "prediction_col": "predicted_conversion_rate",
        "test_table": f"{CATALOG}.features.pricing_features",
        "mape_threshold": 0.15,
        "r2_threshold": 0.70,
        "max_bias_pct": 0.05,
    },
    "revenue": {
        "registered_name": "boxscore-revenue-predictor",
        "target_col": "actual_revenue",
        "prediction_col": "predicted_revenue",
        "test_table": f"{CATALOG}.features.demand_features",
        "mape_threshold": 0.15,
        "r2_threshold": 0.70,
        "max_bias_pct": 0.05,
    },
}

dbutils.widgets.dropdown("model_type", "demand", list(MODEL_CONFIGS.keys()), "Model Type")
model_type = dbutils.widgets.get("model_type")
config = MODEL_CONFIGS[model_type]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Champion and Challenger Models

# COMMAND ----------

def get_model_versions(registered_name):
    """Return the current Production (champion) and latest Staging (challenger) versions."""
    champion_versions = client.get_latest_versions(registered_name, stages=["Production"])
    challenger_versions = client.get_latest_versions(registered_name, stages=["Staging"])

    champion = champion_versions[0] if champion_versions else None
    challenger = challenger_versions[0] if challenger_versions else None
    return champion, challenger

champion_mv, challenger_mv = get_model_versions(config["registered_name"])

if challenger_mv is None:
    dbutils.notebook.exit("No challenger model in Staging. Nothing to validate.")

print(f"Champion : v{champion_mv.version if champion_mv else 'NONE'}")
print(f"Challenger: v{challenger_mv.version}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Prepare Holdout Test Set (2026 Season)

# COMMAND ----------

test_df = spark.table(config["test_table"]).filter(
    F.col("game_date").between("2026-04-01", "2026-09-30")
)

feature_cols = [c for c in test_df.columns if c not in [
    "game_id", "section_id", "seat_id", "game_date",
    config["target_col"], "as_of_date"
]]

test_pdf = test_df.toPandas()
X_test = test_pdf[feature_cols].fillna(0)
y_test = test_pdf[config["target_col"]].values

print(f"Holdout set: {len(test_pdf):,} rows, {len(feature_cols)} features")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Score with Both Models

# COMMAND ----------

def score_model(model_version, X):
    model_uri = f"models:/{config['registered_name']}/{model_version.version}"
    model = mlflow.pyfunc.load_model(model_uri)
    return model.predict(X)

challenger_preds = score_model(challenger_mv, X_test)

if champion_mv:
    champion_preds = score_model(champion_mv, X_test)
else:
    champion_preds = np.full_like(y_test, y_test.mean())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Compute Validation Metrics

# COMMAND ----------

def compute_metrics(y_true, y_pred, label):
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)

    mask = y_true != 0
    ape = np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])
    mape = float(np.mean(ape))

    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    bias = float(np.mean(y_pred - y_true))

    print(f"[{label}]  MAPE={mape:.4f}  R²={r2:.4f}  RMSE={rmse:.2f}  Bias={bias:.2f}")
    return {"mape": mape, "r2": r2, "rmse": rmse, "bias": bias}

champion_metrics = compute_metrics(y_test, champion_preds, "Champion")
challenger_metrics = compute_metrics(y_test, challenger_preds, "Challenger")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation Checks

# COMMAND ----------

def check_performance(metrics, thresholds):
    return metrics["mape"] <= thresholds["mape_threshold"] and metrics["r2"] >= thresholds["r2_threshold"]

def check_stability(y_pred, y_true):
    hist_std = np.std(y_true)
    pred_range = np.max(y_pred) - np.min(y_pred)
    expected_range = 4 * hist_std  # within 2 std on each side
    return pred_range <= expected_range

def check_fairness(test_pdf, y_pred, y_true, segment_col="section_id"):
    if segment_col not in test_pdf.columns:
        return True, {}
    import pandas as pd
    df = pd.DataFrame({"actual": y_true, "predicted": y_pred, "segment": test_pdf[segment_col].values})
    segment_bias = {}
    for seg, grp in df.groupby("segment"):
        if len(grp) < 10:
            continue
        mean_actual = grp["actual"].mean()
        if mean_actual == 0:
            continue
        bias_pct = abs((grp["predicted"].mean() - mean_actual) / mean_actual)
        segment_bias[seg] = bias_pct
    max_bias = max(segment_bias.values()) if segment_bias else 0
    return max_bias <= config["max_bias_pct"], segment_bias

perf_pass = check_performance(challenger_metrics, config)
stability_pass = check_stability(challenger_preds, y_test)
fairness_pass, segment_biases = check_fairness(test_pdf, challenger_preds, y_test)

beats_champion = challenger_metrics["mape"] < champion_metrics["mape"]

print(f"\nPerformance check : {'PASS' if perf_pass else 'FAIL'}")
print(f"Stability check   : {'PASS' if stability_pass else 'FAIL'}")
print(f"Fairness check    : {'PASS' if fairness_pass else 'FAIL'}")
print(f"Beats champion    : {'YES' if beats_champion else 'NO'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Auto-Promote or Reject

# COMMAND ----------

all_pass = perf_pass and stability_pass and fairness_pass and beats_champion
decision = "PROMOTED" if all_pass else "REJECTED"

if all_pass:
    client.transition_model_version_stage(
        name=config["registered_name"],
        version=challenger_mv.version,
        stage="Production",
        archive_existing_versions=True,
    )
    print(f"Challenger v{challenger_mv.version} PROMOTED to Production")
else:
    client.transition_model_version_stage(
        name=config["registered_name"],
        version=challenger_mv.version,
        stage="Archived",
    )
    print(f"Challenger v{challenger_mv.version} REJECTED and archived")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Log Validation Results

# COMMAND ----------

validation_rows = [
    (
        model_type,
        config["registered_name"],
        int(champion_mv.version) if champion_mv else 0,
        int(challenger_mv.version),
        decision,
        float(champion_metrics["mape"]),
        float(challenger_metrics["mape"]),
        float(champion_metrics["r2"]),
        float(challenger_metrics["r2"]),
        float(challenger_metrics["rmse"]),
        perf_pass,
        stability_pass,
        fairness_pass,
        beats_champion,
        datetime.utcnow(),
    )
]

schema = StructType([
    StructField("model_type", StringType()),
    StructField("registered_name", StringType()),
    StructField("champion_version", IntegerType()),
    StructField("challenger_version", IntegerType()),
    StructField("decision", StringType()),
    StructField("champion_mape", FloatType()),
    StructField("challenger_mape", FloatType()),
    StructField("champion_r2", FloatType()),
    StructField("challenger_r2", FloatType()),
    StructField("challenger_rmse", FloatType()),
    StructField("perf_pass", StringType()),
    StructField("stability_pass", StringType()),
    StructField("fairness_pass", StringType()),
    StructField("beats_champion", StringType()),
    StructField("validated_at", TimestampType()),
])

result_df = spark.createDataFrame(
    [(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9],
      str(r[10]), str(r[11]), str(r[12]), str(r[13]), r[14]) for r in validation_rows],
    schema,
)

result_df.write.mode("append").saveAsTable(METRICS_TABLE)
print(f"Validation results logged to {METRICS_TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 60)
print(f"  Model Validation Summary — {model_type.upper()}")
print("=" * 60)
print(f"  Champion  v{champion_mv.version if champion_mv else 'NONE'}  MAPE={champion_metrics['mape']:.4f}  R²={champion_metrics['r2']:.4f}")
print(f"  Challenger v{challenger_mv.version}  MAPE={challenger_metrics['mape']:.4f}  R²={challenger_metrics['r2']:.4f}")
print(f"  Decision: {decision}")
print("=" * 60)
