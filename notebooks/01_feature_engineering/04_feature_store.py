# Databricks notebook source
# MAGIC %md
# MAGIC # Boxscore — Feature Store Registration
# MAGIC Registers demand, pricing, and inventory feature tables in the Databricks Feature Store with point-in-time lookup keys.

# COMMAND ----------

from databricks.feature_engineering import FeatureEngineeringClient, FeatureFunction, FeatureLookup
from pyspark.sql import functions as F

spark.sql("USE CATALOG boxscore")
fe = FeatureEngineeringClient()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Register Demand Features

# COMMAND ----------

demand_df = spark.table("boxscore.features.demand_features")

fe.create_table(
    name="boxscore.features.demand_features",
    primary_keys=["game_id", "section_id", "as_of_date"],
    timestamp_keys=["as_of_date"],
    df=demand_df,
    description="Demand signals: rolling page views, sales velocity, days-to-event, opponent draw, promotions, season win %",
    tags={"domain": "demand", "team": "boxscore", "refresh": "daily"},
)
print("✅ Registered boxscore.features.demand_features")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Register Pricing Features

# COMMAND ----------

pricing_df = spark.table("boxscore.features.pricing_features")

fe.create_table(
    name="boxscore.features.pricing_features",
    primary_keys=["game_id", "section_id", "as_of_date"],
    timestamp_keys=["as_of_date"],
    df=pricing_df,
    description="Pricing signals: price vs median, section rank, secondary premium, price changes, elasticity estimate",
    tags={"domain": "pricing", "team": "boxscore", "refresh": "daily"},
)
print("✅ Registered boxscore.features.pricing_features")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Register Inventory Features

# COMMAND ----------

inventory_df = spark.table("boxscore.features.inventory_features")

fe.create_table(
    name="boxscore.features.inventory_features",
    primary_keys=["game_id", "section_id", "as_of_date"],
    timestamp_keys=["as_of_date"],
    df=inventory_df,
    description="Inventory signals: sell-through rate, remaining inventory, days of stock, masked ratio, velocity trend",
    tags={"domain": "inventory", "team": "boxscore", "refresh": "daily"},
)
print("✅ Registered boxscore.features.inventory_features")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Define Feature Lookups for Training
# MAGIC Example of how downstream model notebooks will pull features with point-in-time correctness.

# COMMAND ----------

feature_lookups = [
    FeatureLookup(
        table_name="boxscore.features.demand_features",
        lookup_key=["game_id", "section_id"],
        timestamp_lookup_key="as_of_date",
        feature_names=[
            "page_views_7d_avg", "sales_velocity_24h",
            "days_to_event", "opponent_hist_draw",
            "has_promotion", "season_win_pct", "demand_index"
        ],
    ),
    FeatureLookup(
        table_name="boxscore.features.pricing_features",
        lookup_key=["game_id", "section_id"],
        timestamp_lookup_key="as_of_date",
        feature_names=[
            "current_price", "price_vs_median_ratio",
            "secondary_premium_ratio", "price_changes_7d",
            "price_elasticity_est"
        ],
    ),
    FeatureLookup(
        table_name="boxscore.features.inventory_features",
        lookup_key=["game_id", "section_id"],
        timestamp_lookup_key="as_of_date",
        feature_names=[
            "sell_through_rate", "remaining_inventory",
            "days_of_inventory", "inventory_risk_score"
        ],
    ),
]

print("✅ Feature lookups defined — ready for model training notebooks")
print(f"   {len(feature_lookups)} lookup groups covering {sum(len(fl.feature_names) for fl in feature_lookups)} features")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verification

# COMMAND ----------

for table_name in [
    "boxscore.features.demand_features",
    "boxscore.features.pricing_features",
    "boxscore.features.inventory_features",
]:
    info = fe.get_table(name=table_name)
    print(f"\n{table_name}")
    print(f"  Primary keys: {info.primary_keys}")
    print(f"  Timestamp keys: {info.timestamp_keys}")
    print(f"  Description: {info.description}")

print("\n✅ Feature Store registration complete!")
