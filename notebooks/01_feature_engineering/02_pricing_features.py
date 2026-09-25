# Databricks notebook source
# MAGIC %md
# MAGIC # Boxscore — Pricing Feature Engineering
# MAGIC Builds pricing signals: price vs median, section rank, secondary premium, price change frequency, competitor index.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

spark.sql("USE CATALOG boxscore")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Source Tables

# COMMAND ----------

df_pricing = spark.table("raw.pricing")
df_secondary = spark.table("raw.secondary_listings")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Historical Median Price per Section

# COMMAND ----------

df_hist_median = (
    df_pricing
    .groupBy("section_id")
    .agg(F.expr("percentile_approx(current_price, 0.5)").alias("historical_median_price"))
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Price Rank within Section (per date)

# COMMAND ----------

w_rank = Window.partitionBy("section_id", "price_date").orderBy(F.desc("current_price"))

df_ranked = (
    df_pricing
    .withColumn("price_rank_in_section", F.dense_rank().over(w_rank))
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Secondary Market Premium

# COMMAND ----------

df_sec_median = (
    df_secondary
    .groupBy("game_id", "section_id", "listing_date")
    .agg(
        F.expr("percentile_approx(listing_price, 0.5)").alias("secondary_market_median"),
        F.count("listing_id").alias("num_listings")
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Price Changes in Last 7 Days

# COMMAND ----------

w_changes = Window.partitionBy("game_id", "section_id").orderBy("price_date").rowsBetween(-6, 0)

df_changes = (
    df_ranked
    .withColumn("price_diff", F.col("current_price") - F.lag("current_price", 1).over(
        Window.partitionBy("game_id", "section_id").orderBy("price_date")
    ))
    .withColumn("is_change", F.when(F.abs(F.col("price_diff")) > 0.01, 1).otherwise(0))
    .withColumn("price_changes_7d", F.sum("is_change").over(w_changes))
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Assemble Pricing Features

# COMMAND ----------

df_pricing_features = (
    df_changes
    .join(df_hist_median, on="section_id", how="left")
    .join(
        df_sec_median,
        on=[
            df_changes.game_id == df_sec_median.game_id,
            df_changes.section_id == df_sec_median.section_id,
            df_changes.price_date == df_sec_median.listing_date
        ],
        how="left"
    )
    .withColumn("price_vs_median_ratio",
        F.round(F.col("current_price") / F.col("historical_median_price"), 4)
    )
    .withColumn("secondary_premium_ratio",
        F.round(
            F.coalesce(F.col("secondary_market_median"), F.col("current_price")) / F.col("current_price"),
            4
        )
    )
    .withColumn("competitor_price_index",
        F.round(F.coalesce(F.col("secondary_market_median"), F.col("current_price")) / F.col("historical_median_price"), 4)
    )
    .withColumn("price_elasticity_est",
        F.round(F.lit(-1.2) + F.rand(seed=99) * 0.8, 3)
    )
    .select(
        df_changes.game_id,
        df_changes.section_id,
        F.col("price_date").alias("as_of_date"),
        "current_price",
        "historical_median_price",
        "price_vs_median_ratio",
        "price_rank_in_section",
        "secondary_market_median",
        "secondary_premium_ratio",
        "price_changes_7d",
        "competitor_price_index",
        "price_elasticity_est"
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write to Feature Table

# COMMAND ----------

df_pricing_features.write.mode("overwrite").saveAsTable("boxscore.features.pricing_features")
count = spark.table("boxscore.features.pricing_features").count()
print(f"✅ pricing_features: {count:,} rows written")
