# Databricks notebook source
# MAGIC %md
# MAGIC # Batch Scoring Pipeline
# MAGIC Daily job: score all upcoming games (next 60 days) with production models.
# MAGIC Designed to run as a Databricks Workflow scheduled at 6 AM PT.

# COMMAND ----------

import mlflow
from mlflow.tracking import MlflowClient
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, FloatType, TimestampType, IntegerType, DoubleType
from databricks.feature_engineering import FeatureEngineeringClient
from datetime import datetime, timedelta
import numpy as np

client = MlflowClient()
fe_client = FeatureEngineeringClient()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

CATALOG = "boxscore"
SCORING_DATE = datetime.utcnow().strftime("%Y-%m-%d")
HORIZON_DAYS = 60
CUTOFF_DATE = (datetime.utcnow() + timedelta(days=HORIZON_DAYS)).strftime("%Y-%m-%d")

MODELS = {
    "demand": {
        "registered_name": "boxscore-demand-forecast",
        "output_table": f"{CATALOG}.models.demand_predictions",
        "feature_table": f"{CATALOG}.features.demand_features",
    },
    "pricing": {
        "registered_name": "boxscore-price-sensitivity",
        "output_table": f"{CATALOG}.models.price_recommendations",
        "feature_table": f"{CATALOG}.features.pricing_features",
    },
    "revenue": {
        "registered_name": "boxscore-revenue-predictor",
        "output_table": f"{CATALOG}.models.revenue_predictions",
        "feature_table": f"{CATALOG}.features.demand_features",
    },
}

print(f"Scoring date : {SCORING_DATE}")
print(f"Horizon      : {HORIZON_DAYS} days (through {CUTOFF_DATE})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Upcoming Games

# COMMAND ----------

events_df = spark.table(f"{CATALOG}.raw.event_details").filter(
    (F.col("game_date") >= SCORING_DATE) & (F.col("game_date") <= CUTOFF_DATE)
)

sections_df = spark.table(f"{CATALOG}.raw.seat_facts").select("section_id").distinct()

scoring_keys = events_df.crossJoin(sections_df).select(
    "game_id", "section_id", F.lit(SCORING_DATE).cast("date").alias("as_of_date")
)

n_games = events_df.count()
n_keys = scoring_keys.count()
print(f"Upcoming games: {n_games}")
print(f"Scoring keys  : {n_keys:,} (game x section)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Helper: Load Production Model

# COMMAND ----------

def load_production_model(registered_name):
    versions = client.get_latest_versions(registered_name, stages=["Production"])
    if not versions:
        print(f"WARNING: No production model for {registered_name}, trying latest version")
        all_versions = client.search_model_versions(f"name='{registered_name}'")
        if not all_versions:
            raise ValueError(f"No model versions found for {registered_name}")
        versions = [sorted(all_versions, key=lambda v: int(v.version), reverse=True)[0]]

    mv = versions[0]
    model_uri = f"models:/{registered_name}/{mv.version}"
    model = mlflow.pyfunc.load_model(model_uri)
    print(f"Loaded {registered_name} v{mv.version} (stage: {mv.current_stage})")
    return model, mv

# COMMAND ----------

# MAGIC %md
# MAGIC ## Score: Demand Forecast

# COMMAND ----------

demand_config = MODELS["demand"]
demand_features = spark.table(demand_config["feature_table"]).filter(
    F.col("game_date") >= SCORING_DATE
)

feature_cols = [c for c in demand_features.columns if c not in [
    "game_id", "section_id", "seat_id", "game_date", "as_of_date",
    "actual_demand", "actual_revenue", "actual_conversion_rate"
]]

demand_pdf = demand_features.toPandas()

try:
    demand_model, demand_mv = load_production_model(demand_config["registered_name"])
    demand_pdf["predicted_demand"] = demand_model.predict(demand_pdf[feature_cols].fillna(0))
except Exception as e:
    print(f"Demand model not available ({e}), using baseline estimates")
    demand_pdf["predicted_demand"] = demand_pdf.get("avg_historical_demand", 0)
    demand_mv = type("obj", (object,), {"version": "0"})()

demand_pdf["model_version"] = str(demand_mv.version)
demand_pdf["score_timestamp"] = datetime.utcnow()
demand_pdf["score_date"] = SCORING_DATE
demand_pdf["confidence"] = np.clip(1.0 - demand_pdf.get("days_to_event", 30).values / 60.0, 0.3, 0.95)

output_cols = ["game_id", "section_id", "game_date", "predicted_demand", "model_version", "score_timestamp", "score_date", "confidence"]
existing_cols = [c for c in output_cols if c in demand_pdf.columns]
demand_out = spark.createDataFrame(demand_pdf[existing_cols])
demand_out.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(demand_config["output_table"])
print(f"Demand predictions written: {demand_out.count():,} rows -> {demand_config['output_table']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Score: Price Sensitivity & Recommendations

# COMMAND ----------

pricing_config = MODELS["pricing"]
pricing_features = spark.table(pricing_config["feature_table"]).filter(
    F.col("game_date") >= SCORING_DATE
)

price_cols = [c for c in pricing_features.columns if c not in [
    "game_id", "section_id", "seat_id", "game_date", "as_of_date",
    "actual_demand", "actual_revenue", "actual_conversion_rate"
]]

pricing_pdf = pricing_features.toPandas()

try:
    pricing_model, pricing_mv = load_production_model(pricing_config["registered_name"])
    pricing_pdf["predicted_conversion_rate"] = pricing_model.predict(pricing_pdf[price_cols].fillna(0))
except Exception as e:
    print(f"Pricing model not available ({e}), using baseline")
    pricing_pdf["predicted_conversion_rate"] = 0.5
    pricing_mv = type("obj", (object,), {"version": "0"})()

pricing_pdf["recommended_price"] = pricing_pdf.get("current_price", 50) * (1 + (pricing_pdf["predicted_conversion_rate"] - 0.5) * 0.1)
pricing_pdf["baseline_price"] = pricing_pdf.get("current_price", 50)
pricing_pdf["model_version"] = str(pricing_mv.version)
pricing_pdf["score_timestamp"] = datetime.utcnow()
pricing_pdf["score_date"] = SCORING_DATE
pricing_pdf["confidence"] = np.clip(pricing_pdf["predicted_conversion_rate"], 0.1, 0.95)

price_out_cols = ["game_id", "section_id", "game_date", "recommended_price", "baseline_price", "predicted_conversion_rate", "model_version", "score_timestamp", "score_date", "confidence"]
existing_price_cols = [c for c in price_out_cols if c in pricing_pdf.columns]
pricing_out = spark.createDataFrame(pricing_pdf[existing_price_cols])
pricing_out.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(pricing_config["output_table"])
print(f"Price recommendations written: {pricing_out.count():,} rows -> {pricing_config['output_table']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Score: Revenue Predictions

# COMMAND ----------

revenue_config = MODELS["revenue"]

try:
    revenue_model, revenue_mv = load_production_model(revenue_config["registered_name"])
    demand_pdf["predicted_revenue"] = revenue_model.predict(demand_pdf[feature_cols].fillna(0))
except Exception as e:
    print(f"Revenue model not available ({e}), estimating from demand * price")
    demand_pdf["predicted_revenue"] = demand_pdf["predicted_demand"] * pricing_pdf.get("recommended_price", 50).values[:len(demand_pdf)]
    revenue_mv = type("obj", (object,), {"version": "0"})()

demand_pdf["revenue_model_version"] = str(revenue_mv.version)

rev_out_cols = ["game_id", "section_id", "game_date", "predicted_revenue", "revenue_model_version", "score_timestamp", "score_date"]
existing_rev_cols = [c for c in rev_out_cols if c in demand_pdf.columns]
revenue_out = spark.createDataFrame(demand_pdf[existing_rev_cols])
revenue_out.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{CATALOG}.models.revenue_predictions")
print(f"Revenue predictions written: {revenue_out.count():,} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Inventory Allocation (derived from demand + pricing)

# COMMAND ----------

inventory_df = spark.table(f"{CATALOG}.raw.available_inventory").filter(
    F.col("game_date") >= SCORING_DATE
)

demand_spark = spark.createDataFrame(demand_pdf[["game_id", "section_id", "predicted_demand", "score_date"]].head(50000))

allocation_df = inventory_df.alias("i").join(
    demand_spark.alias("d"),
    (F.col("i.game_id") == F.col("d.game_id")) & (F.col("i.section_id") == F.col("d.section_id")),
    "left"
).select(
    F.col("i.game_id"),
    F.col("i.section_id"),
    F.col("i.game_date"),
    F.col("i.total_seats"),
    F.col("i.available_seats"),
    F.coalesce(F.col("d.predicted_demand"), F.lit(0)).alias("predicted_demand"),
    F.col("d.score_date"),
).withColumn(
    "recommended_release_pct",
    F.when(F.col("predicted_demand") > F.col("available_seats") * 0.8, 1.0)
     .when(F.col("predicted_demand") > F.col("available_seats") * 0.5, 0.75)
     .otherwise(0.5)
).withColumn(
    "recommended_available", (F.col("total_seats") * F.col("recommended_release_pct")).cast("int")
).withColumn("score_timestamp", F.current_timestamp())

allocation_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{CATALOG}.models.inventory_allocations")
print(f"Inventory allocations written: {allocation_df.count():,} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 60)
print(f"  Batch Scoring Complete — {SCORING_DATE}")
print("=" * 60)
print(f"  Games scored   : {n_games}")
print(f"  Demand rows    : {demand_out.count():,}")
print(f"  Pricing rows   : {pricing_out.count():,}")
print(f"  Revenue rows   : {revenue_out.count():,}")
print(f"  Allocation rows: {allocation_df.count():,}")
print("=" * 60)
