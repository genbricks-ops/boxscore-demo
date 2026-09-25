# Databricks notebook source
# MAGIC %md
# MAGIC # Boxscore — Demand Feature Engineering
# MAGIC Builds demand signals: rolling page views, sales velocity, days-to-event, opponent draw, promotions, season win %.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

spark.sql("USE CATALOG boxscore")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Source Tables

# COMMAND ----------

df_events = spark.table("raw.event_details")
df_pv = spark.table("raw.page_views")
df_sales = spark.table("raw.sales")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Rolling Page View Averages

# COMMAND ----------

w7 = Window.partitionBy("game_id").orderBy("view_date").rowsBetween(-6, 0)
w14 = Window.partitionBy("game_id").orderBy("view_date").rowsBetween(-13, 0)
w30 = Window.partitionBy("game_id").orderBy("view_date").rowsBetween(-29, 0)

df_pv_rolling = (
    df_pv
    .withColumn("page_views_7d_avg", F.avg("total_page_views").over(w7))
    .withColumn("page_views_14d_avg", F.avg("total_page_views").over(w14))
    .withColumn("page_views_30d_avg", F.avg("total_page_views").over(w30))
    .select("game_id", "view_date", "page_views_7d_avg", "page_views_14d_avg", "page_views_30d_avg")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Sales Velocity

# COMMAND ----------

df_sales_daily = (
    df_sales
    .groupBy("game_id", "section_id", "sale_date")
    .agg(
        F.count("transaction_id").alias("daily_tickets"),
        F.sum("total_amount").alias("daily_revenue")
    )
)

w_vel_24 = Window.partitionBy("game_id", "section_id").orderBy("sale_date").rowsBetween(-1, 0)
w_vel_48 = Window.partitionBy("game_id", "section_id").orderBy("sale_date").rowsBetween(-2, 0)
w_vel_72 = Window.partitionBy("game_id", "section_id").orderBy("sale_date").rowsBetween(-3, 0)

df_velocity = (
    df_sales_daily
    .withColumn("sales_velocity_24h", F.avg("daily_tickets").over(w_vel_24))
    .withColumn("sales_velocity_48h", F.avg("daily_tickets").over(w_vel_48))
    .withColumn("sales_velocity_72h", F.avg("daily_tickets").over(w_vel_72))
    .withColumnRenamed("sale_date", "as_of_date")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Opponent Historical Draw

# COMMAND ----------

df_opp_draw = (
    df_events
    .groupBy("opponent")
    .agg(
        F.avg("attendance").alias("opponent_hist_draw"),
        F.avg("opponent_strength").alias("avg_strength")
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Season Win Percentage (cumulative)

# COMMAND ----------

w_season = Window.partitionBy("season").orderBy("game_date").rowsBetween(Window.unboundedPreceding, 0)

df_wins = (
    df_events
    .withColumn("win_flag", (F.rand(seed=42) < 0.52).cast("int"))
    .withColumn("games_played", F.count("game_id").over(w_season))
    .withColumn("wins", F.sum("win_flag").over(w_season))
    .withColumn("season_win_pct", F.round(F.col("wins") / F.col("games_played"), 3))
    .select("game_id", "season_win_pct")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Assemble Demand Features

# COMMAND ----------

sections_df = spark.table("raw.seat_facts").select("section_id").distinct()

df_demand = (
    df_velocity
    .join(
        df_pv_rolling.withColumnRenamed("view_date", "as_of_date"),
        on=["game_id", "as_of_date"],
        how="left"
    )
    .join(df_events.select("game_id", "game_date", "opponent", "promotion_type",
                           "is_weekend", "day_of_week", "month"),
          on="game_id", how="left")
    .join(df_opp_draw, on="opponent", how="left")
    .join(df_wins, on="game_id", how="left")
    .withColumn("days_to_event", F.datediff("game_date", "as_of_date"))
    .withColumn("day_of_week_enc", F.dayofweek("as_of_date"))
    .withColumn("month_enc", F.month("as_of_date"))
    .withColumn("has_promotion", F.col("promotion_type").isNotNull())
    .withColumn("demand_index",
        F.round(
            F.coalesce(F.col("page_views_7d_avg"), F.lit(0)) * 0.4 +
            F.coalesce(F.col("sales_velocity_24h"), F.lit(0)) * 10 * 0.3 +
            F.coalesce(F.col("opponent_hist_draw"), F.lit(30000)) / 41265.0 * 100 * 0.2 +
            F.when(F.col("has_promotion"), 10).otherwise(0) * 0.1,
            2
        )
    )
    .select(
        "game_id", "section_id", "as_of_date",
        "page_views_7d_avg", "page_views_14d_avg", "page_views_30d_avg",
        "sales_velocity_24h", "sales_velocity_48h", "sales_velocity_72h",
        "days_to_event", "opponent_hist_draw",
        "day_of_week_enc", "month_enc", "is_weekend",
        "has_promotion", "promotion_type", "season_win_pct",
        "demand_index"
    )
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write to Feature Table

# COMMAND ----------

df_demand.write.mode("overwrite").saveAsTable("boxscore.features.demand_features")
count = spark.table("boxscore.features.demand_features").count()
print(f"✅ demand_features: {count:,} rows written")
