# Databricks notebook source
# MAGIC %md
# MAGIC # A/B Test Evaluation Framework
# MAGIC Evaluates pricing decisions: model-recommended price vs baseline.
# MAGIC Measures revenue lift, sell-through, and statistical significance.

# COMMAND ----------

import mlflow
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, FloatType, TimestampType
import numpy as np
import pandas as pd
from scipy import stats
from datetime import datetime

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

CATALOG = "boxscore"
RESULTS_TABLE = f"{CATALOG}.monitoring.ab_test_results"

dbutils.widgets.text("start_date", "2026-04-01", "Test Start Date")
dbutils.widgets.text("end_date", "2026-06-30", "Test End Date")
dbutils.widgets.text("experiment_name", "pricing_v2_vs_baseline", "Experiment Name")

start_date = dbutils.widgets.get("start_date")
end_date = dbutils.widgets.get("end_date")
experiment_name = dbutils.widgets.get("experiment_name")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Experiment Data

# COMMAND ----------

recommendations_df = spark.table(f"{CATALOG}.models.price_recommendations").filter(
    F.col("score_date").between(start_date, end_date)
)

sales_df = spark.table(f"{CATALOG}.raw.sales").filter(
    F.col("transaction_date").between(start_date, end_date)
)

events_df = spark.table(f"{CATALOG}.raw.event_details")

experiment_df = recommendations_df.alias("r").join(
    sales_df.alias("s"),
    (F.col("r.game_id") == F.col("s.game_id")) & (F.col("r.section_id") == F.col("s.section_id")),
    "left"
).join(
    events_df.alias("e"),
    F.col("r.game_id") == F.col("e.game_id"),
    "left"
).select(
    F.col("r.game_id"),
    F.col("r.section_id"),
    F.col("r.recommended_price"),
    F.col("r.baseline_price"),
    F.col("r.model_version"),
    F.col("s.revenue").alias("actual_revenue"),
    F.col("s.tickets_sold").alias("actual_tickets_sold"),
    F.col("s.total_inventory").alias("total_inventory"),
    F.col("e.game_type"),
    F.col("e.day_of_week"),
)

exp_pdf = experiment_df.toPandas()
print(f"Experiment data: {len(exp_pdf):,} rows across {exp_pdf['game_id'].nunique()} games")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Revenue Lift Calculation

# COMMAND ----------

exp_pdf["used_model_price"] = exp_pdf["recommended_price"].notna()

model_group = exp_pdf[exp_pdf["used_model_price"]]
baseline_group = exp_pdf[~exp_pdf["used_model_price"]]

if len(model_group) == 0 or len(baseline_group) == 0:
    model_rev_per_seat = exp_pdf.loc[exp_pdf["used_model_price"], "actual_revenue"].sum() / max(exp_pdf.loc[exp_pdf["used_model_price"], "actual_tickets_sold"].sum(), 1)
    baseline_rev_per_seat = exp_pdf.loc[~exp_pdf["used_model_price"], "actual_revenue"].sum() / max(exp_pdf.loc[~exp_pdf["used_model_price"], "actual_tickets_sold"].sum(), 1)
else:
    model_rev_per_seat = model_group["actual_revenue"].sum() / max(model_group["actual_tickets_sold"].sum(), 1)
    baseline_rev_per_seat = baseline_group["actual_revenue"].sum() / max(baseline_group["actual_tickets_sold"].sum(), 1)

revenue_lift = (model_rev_per_seat - baseline_rev_per_seat) / baseline_rev_per_seat if baseline_rev_per_seat > 0 else 0

print(f"Model revenue/seat   : ${model_rev_per_seat:.2f}")
print(f"Baseline revenue/seat: ${baseline_rev_per_seat:.2f}")
print(f"Revenue lift         : {revenue_lift:.2%}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Statistical Significance — t-test

# COMMAND ----------

model_revenues = model_group.groupby("game_id")["actual_revenue"].sum().values if len(model_group) > 0 else np.array([0])
baseline_revenues = baseline_group.groupby("game_id")["actual_revenue"].sum().values if len(baseline_group) > 0 else np.array([0])

t_stat, p_value = stats.ttest_ind(model_revenues, baseline_revenues, equal_var=False)

print(f"t-statistic: {t_stat:.4f}")
print(f"p-value    : {p_value:.6f}")
print(f"Significant: {'YES' if p_value < 0.05 else 'NO'} (alpha=0.05)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bootstrap Confidence Interval (95%)

# COMMAND ----------

def bootstrap_ci(data_a, data_b, n_bootstrap=10000, ci=0.95):
    diffs = []
    for _ in range(n_bootstrap):
        sample_a = np.random.choice(data_a, size=len(data_a), replace=True)
        sample_b = np.random.choice(data_b, size=len(data_b), replace=True)
        diffs.append(np.mean(sample_a) - np.mean(sample_b))
    lower = np.percentile(diffs, (1 - ci) / 2 * 100)
    upper = np.percentile(diffs, (1 + ci) / 2 * 100)
    return lower, upper, np.array(diffs)

ci_lower, ci_upper, boot_diffs = bootstrap_ci(model_revenues, baseline_revenues)
print(f"95% CI for revenue difference: [${ci_lower:,.2f}, ${ci_upper:,.2f}]")
print(f"CI excludes zero: {'YES' if ci_lower > 0 or ci_upper < 0 else 'NO'}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sell-Through Rate Comparison

# COMMAND ----------

model_sellthrough = model_group["actual_tickets_sold"].sum() / max(model_group["total_inventory"].sum(), 1) if len(model_group) > 0 else 0
baseline_sellthrough = baseline_group["actual_tickets_sold"].sum() / max(baseline_group["total_inventory"].sum(), 1) if len(baseline_group) > 0 else 0

print(f"Model sell-through   : {model_sellthrough:.2%}")
print(f"Baseline sell-through: {baseline_sellthrough:.2%}")
print(f"Difference           : {(model_sellthrough - baseline_sellthrough):.2%}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Segment Analysis

# COMMAND ----------

def segment_lift(df, segment_col):
    results = []
    for seg, grp in df.groupby(segment_col):
        model_seg = grp[grp["used_model_price"]]
        base_seg = grp[~grp["used_model_price"]]
        if len(model_seg) < 5 or len(base_seg) < 5:
            continue
        m_rev = model_seg["actual_revenue"].sum() / max(model_seg["actual_tickets_sold"].sum(), 1)
        b_rev = base_seg["actual_revenue"].sum() / max(base_seg["actual_tickets_sold"].sum(), 1)
        lift = (m_rev - b_rev) / b_rev if b_rev > 0 else 0
        _, p = stats.ttest_ind(
            model_seg.groupby("game_id")["actual_revenue"].sum().values,
            base_seg.groupby("game_id")["actual_revenue"].sum().values,
            equal_var=False,
        )
        results.append({"segment": str(seg), "model_rev_per_seat": m_rev, "baseline_rev_per_seat": b_rev, "lift": lift, "p_value": p, "n_model": len(model_seg), "n_baseline": len(base_seg)})
    return pd.DataFrame(results)

section_results = segment_lift(exp_pdf, "section_id")
if len(section_results) > 0:
    print("=== Lift by Section ===")
    display(spark.createDataFrame(section_results.sort_values("lift", ascending=False)))

game_type_results = segment_lift(exp_pdf, "game_type")
if len(game_type_results) > 0:
    print("\n=== Lift by Game Type ===")
    display(spark.createDataFrame(game_type_results.sort_values("lift", ascending=False)))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Visualizations

# COMMAND ----------

import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 3, figsize=(18, 5))

axes[0].hist(boot_diffs, bins=50, color="#FD5A1E", edgecolor="white", alpha=0.8)
axes[0].axvline(0, color="black", linestyle="--", linewidth=1.5)
axes[0].axvline(ci_lower, color="#27251F", linestyle="--", linewidth=1)
axes[0].axvline(ci_upper, color="#27251F", linestyle="--", linewidth=1)
axes[0].set_title("Bootstrap Revenue Difference Distribution")
axes[0].set_xlabel("Revenue Difference ($)")

if len(section_results) > 0:
    top_sections = section_results.nlargest(10, "lift")
    axes[1].barh(top_sections["segment"].astype(str), top_sections["lift"] * 100, color="#FD5A1E")
    axes[1].set_xlabel("Revenue Lift (%)")
    axes[1].set_title("Top 10 Sections by Lift")

if len(section_results) > 0:
    axes[2].scatter(section_results["lift"] * 100, -np.log10(section_results["p_value"].clip(1e-20)), color="#FD5A1E", s=60, alpha=0.7)
    axes[2].axhline(-np.log10(0.05), color="red", linestyle="--", label="p=0.05")
    axes[2].set_xlabel("Lift (%)")
    axes[2].set_ylabel("-log10(p-value)")
    axes[2].set_title("Volcano Plot: Lift vs Significance")
    axes[2].legend()

plt.tight_layout()
plt.savefig("/tmp/ab_test_results.png", dpi=150, bbox_inches="tight")
plt.show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Persist Results

# COMMAND ----------

summary_schema = StructType([
    StructField("experiment_name", StringType()),
    StructField("start_date", StringType()),
    StructField("end_date", StringType()),
    StructField("model_rev_per_seat", FloatType()),
    StructField("baseline_rev_per_seat", FloatType()),
    StructField("revenue_lift_pct", FloatType()),
    StructField("t_statistic", FloatType()),
    StructField("p_value", FloatType()),
    StructField("ci_lower", FloatType()),
    StructField("ci_upper", FloatType()),
    StructField("model_sellthrough", FloatType()),
    StructField("baseline_sellthrough", FloatType()),
    StructField("is_significant", StringType()),
    StructField("evaluated_at", TimestampType()),
])

summary_row = [(
    experiment_name, start_date, end_date,
    float(model_rev_per_seat), float(baseline_rev_per_seat),
    float(revenue_lift * 100), float(t_stat), float(p_value),
    float(ci_lower), float(ci_upper),
    float(model_sellthrough), float(baseline_sellthrough),
    str(p_value < 0.05), datetime.utcnow(),
)]

spark.createDataFrame(summary_row, summary_schema).write.mode("append").saveAsTable(RESULTS_TABLE)
print(f"Results saved to {RESULTS_TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 60)
print(f"  A/B Test Results — {experiment_name}")
print("=" * 60)
print(f"  Revenue lift : {revenue_lift:+.2%}")
print(f"  p-value      : {p_value:.6f} ({'Significant' if p_value < 0.05 else 'Not significant'})")
print(f"  95% CI       : [${ci_lower:,.2f}, ${ci_upper:,.2f}]")
print(f"  Sell-through : Model {model_sellthrough:.1%} vs Baseline {baseline_sellthrough:.1%}")
print("=" * 60)
