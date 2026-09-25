# Databricks notebook source
# MAGIC %md
# MAGIC # Model Performance Monitoring
# MAGIC Tracks predictions vs actuals as games complete.
# MAGIC Monitors MAPE, RMSE, and bias over rolling windows.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, FloatType, TimestampType, IntegerType
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

CATALOG = "boxscore"
METRICS_LOG = f"{CATALOG}.monitoring.model_metrics_log"
RETRAINING_MAPE_THRESHOLD = 0.15

MODEL_TARGETS = {
    "demand": {
        "predictions_table": f"{CATALOG}.models.demand_predictions",
        "actuals_table": f"{CATALOG}.raw.sales",
        "pred_col": "predicted_demand",
        "actual_col": "actual_demand",
        "join_keys": ["game_id", "section_id"],
        "date_col": "game_date",
    },
    "pricing": {
        "predictions_table": f"{CATALOG}.models.price_recommendations",
        "actuals_table": f"{CATALOG}.raw.sales",
        "pred_col": "predicted_conversion_rate",
        "actual_col": "actual_conversion_rate",
        "join_keys": ["game_id", "section_id"],
        "date_col": "game_date",
    },
    "revenue": {
        "predictions_table": f"{CATALOG}.models.revenue_predictions",
        "actuals_table": f"{CATALOG}.raw.sales",
        "pred_col": "predicted_revenue",
        "actual_col": "actual_revenue",
        "join_keys": ["game_id", "section_id"],
        "date_col": "game_date",
    },
}

ROLLING_WINDOWS = [7, 14, 30]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Compute Metrics per Model

# COMMAND ----------

def compute_rolling_metrics(pred_df, actual_df, config, windows):
    """Join predictions to actuals and compute rolling performance metrics."""
    join_keys = config["join_keys"]
    pred_col = config["pred_col"]
    actual_col = config["actual_col"]
    date_col = config["date_col"]

    joined = pred_df.alias("p").join(
        actual_df.alias("a"),
        [F.col(f"p.{k}") == F.col(f"a.{k}") for k in join_keys],
        "inner",
    ).select(
        *[F.col(f"p.{k}") for k in join_keys],
        F.col(f"p.{date_col}").alias("game_date"),
        F.col(f"p.{pred_col}").cast("double").alias("predicted"),
        F.col(f"a.{actual_col}").cast("double").alias("actual"),
        F.col("p.model_version"),
    ).filter(
        F.col("actual").isNotNull() & F.col("predicted").isNotNull() & (F.col("actual") > 0)
    )

    joined = joined.withColumn("abs_pct_error", F.abs((F.col("predicted") - F.col("actual")) / F.col("actual")))
    joined = joined.withColumn("squared_error", F.pow(F.col("predicted") - F.col("actual"), 2))
    joined = joined.withColumn("error", F.col("predicted") - F.col("actual"))

    pdf = joined.toPandas()
    if len(pdf) == 0:
        return pd.DataFrame()

    pdf["game_date"] = pd.to_datetime(pdf["game_date"])
    pdf = pdf.sort_values("game_date")

    metrics_rows = []
    for window in windows:
        for i in range(len(pdf)):
            end_date = pdf.iloc[i]["game_date"]
            start_date = end_date - timedelta(days=window)
            window_data = pdf[(pdf["game_date"] > start_date) & (pdf["game_date"] <= end_date)]

            if len(window_data) < 3:
                continue

            mape = window_data["abs_pct_error"].mean()
            rmse = np.sqrt(window_data["squared_error"].mean())
            bias = window_data["error"].mean()
            n_samples = len(window_data)

            metrics_rows.append({
                "game_date": end_date,
                "window_days": window,
                "mape": float(mape),
                "rmse": float(rmse),
                "bias": float(bias),
                "n_samples": int(n_samples),
            })

    return pd.DataFrame(metrics_rows).drop_duplicates(subset=["game_date", "window_days"])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run Performance Tracking

# COMMAND ----------

all_metrics = []
alerts = []

for model_name, config in MODEL_TARGETS.items():
    print(f"\n{'=' * 60}")
    print(f"  {model_name.upper()} Model Performance")
    print(f"{'=' * 60}")

    try:
        pred_df = spark.table(config["predictions_table"])
        actual_df = spark.table(config["actuals_table"])
    except Exception as e:
        print(f"  Skipping {model_name}: {e}")
        continue

    metrics_pdf = compute_rolling_metrics(pred_df, actual_df, config, ROLLING_WINDOWS)

    if len(metrics_pdf) == 0:
        print(f"  No completed games with actuals yet for {model_name}")
        continue

    metrics_pdf["model_name"] = model_name
    metrics_pdf["monitored_at"] = datetime.utcnow()

    for window in ROLLING_WINDOWS:
        window_data = metrics_pdf[metrics_pdf["window_days"] == window]
        if len(window_data) == 0:
            continue
        latest = window_data.iloc[-1]
        status = "ALERT" if latest["mape"] > RETRAINING_MAPE_THRESHOLD else "OK"
        print(f"  {window:>2}d window: MAPE={latest['mape']:.4f}  RMSE={latest['rmse']:.2f}  Bias={latest['bias']:.2f}  [{status}]")

        if status == "ALERT":
            alerts.append({
                "model": model_name,
                "window": window,
                "mape": latest["mape"],
                "threshold": RETRAINING_MAPE_THRESHOLD,
            })

    all_metrics.append(metrics_pdf)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Visualize Performance Trends

# COMMAND ----------

if all_metrics:
    combined = pd.concat(all_metrics, ignore_index=True)
    model_names = combined["model_name"].unique()

    fig, axes = plt.subplots(len(model_names), 3, figsize=(18, 5 * len(model_names)))
    if len(model_names) == 1:
        axes = axes.reshape(1, -1)

    for row, model_name in enumerate(model_names):
        model_data = combined[combined["model_name"] == model_name]

        for col, window in enumerate(ROLLING_WINDOWS):
            window_data = model_data[model_data["window_days"] == window].sort_values("game_date")
            if len(window_data) == 0:
                continue

            ax = axes[row, col]

            ax.plot(window_data["game_date"], window_data["mape"], color="#FD5A1E", linewidth=2, label="MAPE")
            ax.axhline(RETRAINING_MAPE_THRESHOLD, color="red", linestyle="--", alpha=0.7, label=f"Threshold ({RETRAINING_MAPE_THRESHOLD:.0%})")
            ax.fill_between(
                window_data["game_date"],
                window_data["mape"],
                RETRAINING_MAPE_THRESHOLD,
                where=window_data["mape"] > RETRAINING_MAPE_THRESHOLD,
                color="red", alpha=0.15,
            )

            ax.set_title(f"{model_name.upper()} — {window}d Rolling MAPE")
            ax.set_ylabel("MAPE")
            ax.legend(fontsize=8)
            ax.tick_params(axis="x", rotation=45)

    plt.suptitle("Model Performance Trends", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig("/tmp/model_performance.png", dpi=150, bbox_inches="tight")
    plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bias Analysis by Section

# COMMAND ----------

for model_name, config in MODEL_TARGETS.items():
    try:
        pred_df = spark.table(config["predictions_table"])
        actual_df = spark.table(config["actuals_table"])
    except Exception:
        continue

    joined = pred_df.alias("p").join(
        actual_df.alias("a"),
        [F.col(f"p.{k}") == F.col(f"a.{k}") for k in config["join_keys"]],
        "inner",
    ).select(
        F.col("p.section_id"),
        (F.col(f"p.{config['pred_col']}") - F.col(f"a.{config['actual_col']}")).alias("error"),
    ).filter(F.col(f"a.{config['actual_col']}").isNotNull())

    bias_by_section = joined.groupBy("section_id").agg(
        F.mean("error").alias("mean_bias"),
        F.stddev("error").alias("std_error"),
        F.count("*").alias("n"),
    ).orderBy(F.abs(F.col("mean_bias")).desc())

    print(f"\n{model_name.upper()} — Bias by Section (top 10):")
    display(bias_by_section.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Log Metrics

# COMMAND ----------

if all_metrics:
    combined = pd.concat(all_metrics, ignore_index=True)

    schema = StructType([
        StructField("model_name", StringType()),
        StructField("game_date", StringType()),
        StructField("window_days", IntegerType()),
        StructField("mape", FloatType()),
        StructField("rmse", FloatType()),
        StructField("bias", FloatType()),
        StructField("n_samples", IntegerType()),
        StructField("monitored_at", TimestampType()),
    ])

    combined["game_date"] = combined["game_date"].astype(str)
    metrics_spark = spark.createDataFrame(combined[["model_name", "game_date", "window_days", "mape", "rmse", "bias", "n_samples", "monitored_at"]])
    metrics_spark.write.mode("append").saveAsTable(METRICS_LOG)
    print(f"\nMetrics logged to {METRICS_LOG}: {len(combined)} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Retraining Alerts

# COMMAND ----------

print("=" * 60)
print("  Model Performance Summary")
print("=" * 60)

if alerts:
    print(f"\n  ⚠️  {len(alerts)} RETRAINING ALERT(S):")
    for alert in alerts:
        print(f"    - {alert['model']} ({alert['window']}d window): MAPE={alert['mape']:.4f} > threshold {alert['threshold']:.2f}")
    print("\n  ACTION: Consider retraining the flagged models with recent data.")
else:
    print("\n  All models within acceptable performance thresholds.")

print("=" * 60)
