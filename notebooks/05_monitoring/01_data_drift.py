# Databricks notebook source
# MAGIC %md
# MAGIC # Data Drift Monitoring
# MAGIC Compares current feature distributions to the training baseline.
# MAGIC Uses KS-test and PSI (Population Stability Index) per feature.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, FloatType, TimestampType
import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime
import matplotlib.pyplot as plt

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

CATALOG = "boxscore"
QUALITY_LOG = f"{CATALOG}.monitoring.data_quality_log"

PSI_WARNING = 0.1
PSI_CRITICAL = 0.2

FEATURE_TABLES = {
    "demand": f"{CATALOG}.features.demand_features",
    "pricing": f"{CATALOG}.features.pricing_features",
    "inventory": f"{CATALOG}.features.inventory_features",
}

MONITOR_FEATURES = {
    "demand": [
        "rolling_7d_page_views", "rolling_14d_page_views", "rolling_30d_page_views",
        "sales_velocity_24h", "sales_velocity_48h", "sales_velocity_72h",
        "days_to_event", "opponent_draw_index", "win_pct",
    ],
    "pricing": [
        "current_price", "price_vs_median", "secondary_market_premium",
        "price_changes_7d", "competitor_pricing_index",
    ],
    "inventory": [
        "sell_through_rate", "remaining_inventory_pct",
        "days_of_inventory_remaining", "masked_seat_ratio",
    ],
}

dbutils.widgets.text("baseline_start", "2025-04-01", "Baseline Start")
dbutils.widgets.text("baseline_end", "2025-09-30", "Baseline End")
dbutils.widgets.text("current_start", "2026-04-01", "Current Start")
dbutils.widgets.text("current_end", "2026-09-30", "Current End")

baseline_start = dbutils.widgets.get("baseline_start")
baseline_end = dbutils.widgets.get("baseline_end")
current_start = dbutils.widgets.get("current_start")
current_end = dbutils.widgets.get("current_end")

# COMMAND ----------

# MAGIC %md
# MAGIC ## PSI Calculation

# COMMAND ----------

def calculate_psi(expected, actual, n_bins=10):
    """Population Stability Index between two distributions."""
    breakpoints = np.linspace(
        min(np.min(expected), np.min(actual)),
        max(np.max(expected), np.max(actual)),
        n_bins + 1,
    )
    expected_counts = np.histogram(expected, breakpoints)[0] + 1
    actual_counts = np.histogram(actual, breakpoints)[0] + 1

    expected_pct = expected_counts / expected_counts.sum()
    actual_pct = actual_counts / actual_counts.sum()

    psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
    return float(psi)


def classify_drift(psi_value):
    if psi_value >= PSI_CRITICAL:
        return "CRITICAL"
    elif psi_value >= PSI_WARNING:
        return "WARNING"
    return "OK"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run Drift Analysis

# COMMAND ----------

all_results = []

for domain, table_name in FEATURE_TABLES.items():
    features_to_check = MONITOR_FEATURES.get(domain, [])
    if not features_to_check:
        continue

    try:
        df = spark.table(table_name)
    except Exception as e:
        print(f"Skipping {domain}: {e}")
        continue

    available_cols = set(df.columns)
    features_to_check = [f for f in features_to_check if f in available_cols]
    if not features_to_check:
        print(f"No monitored features found in {domain}")
        continue

    baseline_df = df.filter(F.col("game_date").between(baseline_start, baseline_end))
    current_df = df.filter(F.col("game_date").between(current_start, current_end))

    baseline_pdf = baseline_df.select(*features_to_check).toPandas()
    current_pdf = current_df.select(*features_to_check).toPandas()

    print(f"\n{'=' * 60}")
    print(f"  Domain: {domain.upper()} — {len(baseline_pdf):,} baseline / {len(current_pdf):,} current rows")
    print(f"{'=' * 60}")

    for feature in features_to_check:
        baseline_vals = baseline_pdf[feature].dropna().values.astype(float)
        current_vals = current_pdf[feature].dropna().values.astype(float)

        if len(baseline_vals) < 20 or len(current_vals) < 20:
            continue

        psi = calculate_psi(baseline_vals, current_vals)
        ks_stat, ks_pvalue = stats.ks_2samp(baseline_vals, current_vals)
        drift_level = classify_drift(psi)

        indicator = {"OK": "  ", "WARNING": "⚠️", "CRITICAL": "🔴"}[drift_level]
        print(f"  {indicator} {feature:<35} PSI={psi:.4f}  KS={ks_stat:.4f}  p={ks_pvalue:.4f}  [{drift_level}]")

        all_results.append({
            "domain": domain,
            "feature": feature,
            "psi": float(psi),
            "ks_statistic": float(ks_stat),
            "ks_pvalue": float(ks_pvalue),
            "drift_level": drift_level,
            "baseline_mean": float(np.mean(baseline_vals)),
            "baseline_std": float(np.std(baseline_vals)),
            "current_mean": float(np.mean(current_vals)),
            "current_std": float(np.std(current_vals)),
            "baseline_count": int(len(baseline_vals)),
            "current_count": int(len(current_vals)),
            "monitored_at": datetime.utcnow(),
        })

# COMMAND ----------

# MAGIC %md
# MAGIC ## Visualize Drift

# COMMAND ----------

critical_features = [r for r in all_results if r["drift_level"] in ("WARNING", "CRITICAL")]

if critical_features:
    n_plots = min(len(critical_features), 6)
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()

    for idx, result in enumerate(critical_features[:n_plots]):
        domain = result["domain"]
        feature = result["feature"]
        table = FEATURE_TABLES[domain]
        df = spark.table(table)

        baseline_vals = df.filter(F.col("game_date").between(baseline_start, baseline_end)).select(feature).toPandas()[feature].dropna().values.astype(float)
        current_vals = df.filter(F.col("game_date").between(current_start, current_end)).select(feature).toPandas()[feature].dropna().values.astype(float)

        ax = axes[idx]
        ax.hist(baseline_vals, bins=30, alpha=0.5, label="Baseline", color="#27251F", density=True)
        ax.hist(current_vals, bins=30, alpha=0.5, label="Current", color="#FD5A1E", density=True)
        ax.set_title(f"{feature}\nPSI={result['psi']:.4f} [{result['drift_level']}]", fontsize=10)
        ax.legend(fontsize=8)

    for idx in range(n_plots, 6):
        axes[idx].set_visible(False)

    plt.suptitle("Feature Distribution Drift — Baseline vs Current", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig("/tmp/data_drift.png", dpi=150, bbox_inches="tight")
    plt.show()
else:
    print("No features with WARNING or CRITICAL drift detected.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Log Results

# COMMAND ----------

if all_results:
    schema = StructType([
        StructField("domain", StringType()),
        StructField("feature", StringType()),
        StructField("psi", FloatType()),
        StructField("ks_statistic", FloatType()),
        StructField("ks_pvalue", FloatType()),
        StructField("drift_level", StringType()),
        StructField("baseline_mean", FloatType()),
        StructField("baseline_std", FloatType()),
        StructField("current_mean", FloatType()),
        StructField("current_std", FloatType()),
        StructField("baseline_count", FloatType()),
        StructField("current_count", FloatType()),
        StructField("monitored_at", TimestampType()),
    ])

    results_df = spark.createDataFrame(pd.DataFrame(all_results))
    results_df.write.mode("append").saveAsTable(QUALITY_LOG)
    print(f"\nDrift results logged to {QUALITY_LOG}: {len(all_results)} features")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

n_ok = sum(1 for r in all_results if r["drift_level"] == "OK")
n_warn = sum(1 for r in all_results if r["drift_level"] == "WARNING")
n_crit = sum(1 for r in all_results if r["drift_level"] == "CRITICAL")

print("=" * 60)
print("  Data Drift Summary")
print("=" * 60)
print(f"  Features monitored: {len(all_results)}")
print(f"  OK      : {n_ok}")
print(f"  WARNING : {n_warn}")
print(f"  CRITICAL: {n_crit}")
if n_crit > 0:
    print("\n  ACTION REQUIRED: Features with critical drift may require model retraining.")
    for r in all_results:
        if r["drift_level"] == "CRITICAL":
            print(f"    - {r['domain']}.{r['feature']}  PSI={r['psi']:.4f}")
print("=" * 60)
