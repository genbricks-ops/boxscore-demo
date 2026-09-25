# Databricks notebook source
# MAGIC %md
# MAGIC # Boxscore — Inventory Feature Engineering
# MAGIC Builds inventory signals: sell-through rate, remaining inventory by tier, days of inventory, masked ratio, velocity trend.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

spark.sql("USE CATALOG boxscore")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Source Tables

# COMMAND ----------

df_inv = spark.table("raw.available_inventory")
df_sales = spark.table("raw.sales")
df_events = spark.table("raw.event_details")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Sell-Through Rate

# COMMAND ----------

df_sellthrough = (
    df_inv
    .withColumn("sell_through_rate",
        F.round(F.col("sold_seats") / F.col("total_seats"), 4)
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Remaining Inventory by Price Tier (JSON string)

# COMMAND ----------

df_remaining_by_tier = (
    df_inv
    .groupBy("game_id", "section_id", "inventory_date")
    .agg(
        F.sum("available_seats").alias("remaining_inventory"),
        F.to_json(
            F.map_from_entries(
                F.collect_list(
                    F.struct(F.col("price_tier"), F.col("available_seats"))
                )
            )
        ).alias("remaining_by_tier")
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Days of Inventory Remaining

# COMMAND ----------

df_daily_sales = (
    df_sales
    .groupBy("game_id", "section_id", "sale_date")
    .agg(F.count("transaction_id").alias("daily_sold"))
)

w_vel = Window.partitionBy("game_id", "section_id").orderBy("sale_date").rowsBetween(-6, 0)

df_sales_vel = (
    df_daily_sales
    .withColumn("avg_daily_velocity", F.avg("daily_sold").over(w_vel))
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Velocity Trend (7d slope proxy)

# COMMAND ----------

w_trend = Window.partitionBy("game_id", "section_id").orderBy("sale_date").rowsBetween(-6, 0)

df_trend = (
    df_daily_sales
    .withColumn("vel_start", F.first("daily_sold").over(w_trend))
    .withColumn("vel_end", F.last("daily_sold").over(w_trend))
    .withColumn("velocity_trend",
        F.round((F.col("vel_end") - F.col("vel_start")) / F.greatest(F.col("vel_start"), F.lit(1)), 3)
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Assemble Inventory Features

# COMMAND ----------

df_inv_features = (
    df_sellthrough
    .join(
        df_remaining_by_tier,
        on=["game_id", "section_id", "inventory_date"],
        how="left"
    )
    .join(
        df_sales_vel.select("game_id", "section_id", "sale_date", "avg_daily_velocity"),
        on=[
            df_sellthrough.game_id == df_sales_vel.game_id,
            df_sellthrough.section_id == df_sales_vel.section_id,
            df_sellthrough.inventory_date == df_sales_vel.sale_date,
        ],
        how="left"
    )
    .join(
        df_trend.select("game_id", "section_id", "sale_date", "velocity_trend"),
        on=[
            df_sellthrough.game_id == df_trend.game_id,
            df_sellthrough.section_id == df_trend.section_id,
            df_sellthrough.inventory_date == df_trend.sale_date,
        ],
        how="left"
    )
    .withColumn("masked_ratio",
        F.round(F.col("masked_seats") / F.greatest(F.col("total_seats"), F.lit(1)), 4)
    )
    .withColumn("days_of_inventory",
        F.round(
            F.col("available_seats") / F.greatest(F.coalesce(df_sales_vel.avg_daily_velocity, F.lit(1)), F.lit(1)),
            1
        )
    )
    .withColumn("inventory_risk_score",
        F.round(
            F.when(F.col("sell_through_rate") < 0.3, 0.8)
             .when(F.col("sell_through_rate") < 0.5, 0.5)
             .when(F.col("sell_through_rate") < 0.7, 0.3)
             .otherwise(0.1)
            + F.when(F.col("days_of_inventory") > 30, 0.2).otherwise(0.0),
            2
        )
    )
    .select(
        df_sellthrough.game_id,
        df_sellthrough.section_id,
        F.col("inventory_date").alias("as_of_date"),
        "sell_through_rate",
        "remaining_inventory",
        "remaining_by_tier",
        "days_of_inventory",
        "masked_ratio",
        F.col("held_seats").alias("hold_back_count"),
        "velocity_trend",
        "inventory_risk_score"
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write to Feature Table

# COMMAND ----------

df_inv_features.write.mode("overwrite").saveAsTable("boxscore.features.inventory_features")
count = spark.table("boxscore.features.inventory_features").count()
print(f"✅ inventory_features: {count:,} rows written")
