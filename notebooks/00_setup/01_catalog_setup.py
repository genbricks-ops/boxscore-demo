# Databricks notebook source
# MAGIC %md
# MAGIC # Boxscore — Unity Catalog Setup
# MAGIC Creates the `boxscore` catalog with schemas and tables for the SF Giants commercial decision platform.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Create Catalog and Schemas

# COMMAND ----------

spark.sql("CREATE CATALOG IF NOT EXISTS boxscore")
spark.sql("USE CATALOG boxscore")

for schema in ["raw", "features", "models", "monitoring"]:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    print(f"✅ Schema boxscore.{schema} ready")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Raw Tables (mirrors Snowflake EDW)

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS boxscore.raw.event_details (
    game_id             STRING      NOT NULL,
    season              INT,
    game_date           DATE,
    game_time           STRING,
    day_night           STRING,
    day_of_week         STRING,
    opponent            STRING,
    opponent_strength   DOUBLE,
    is_home             BOOLEAN,
    promotion_type      STRING,
    promotion_desc      STRING,
    is_weekend          BOOLEAN,
    month               INT,
    attendance          INT,
    capacity            INT,
    weather_temp_f      DOUBLE,
    weather_condition   STRING
)
USING DELTA
COMMENT 'Static game attributes including promotions and special events'
""")
print("✅ boxscore.raw.event_details")

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS boxscore.raw.seat_facts (
    seat_id             STRING      NOT NULL,
    section_id          STRING      NOT NULL,
    section_name        STRING,
    row_name            STRING,
    seat_number         INT,
    seat_quality_score  DOUBLE,
    distance_to_home_ft DOUBLE,
    is_aisle            BOOLEAN,
    is_front_row        BOOLEAN,
    has_shade           BOOLEAN,
    view_rating         DOUBLE,
    price_tier          STRING,
    section_capacity    INT
)
USING DELTA
COMMENT 'Detailed seat characteristics including quality scores and rankings'
""")
print("✅ boxscore.raw.seat_facts")

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS boxscore.raw.pricing (
    game_id             STRING      NOT NULL,
    section_id          STRING      NOT NULL,
    price_date          DATE        NOT NULL,
    base_price          DOUBLE,
    current_price       DOUBLE,
    min_price           DOUBLE,
    max_price           DOUBLE,
    price_tier          STRING,
    price_scale         INT,
    last_price_change   TIMESTAMP,
    change_direction    STRING,
    change_amount       DOUBLE
)
USING DELTA
COMMENT 'Daily pricing data at game/section level'
PARTITIONED BY (price_date)
""")
print("✅ boxscore.raw.pricing")

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS boxscore.raw.available_inventory (
    game_id             STRING      NOT NULL,
    section_id          STRING      NOT NULL,
    inventory_date      DATE        NOT NULL,
    total_seats         INT,
    available_seats     INT,
    sold_seats          INT,
    held_seats          INT,
    masked_seats        INT,
    sell_through_pct    DOUBLE,
    price_tier          STRING
)
USING DELTA
COMMENT 'Daily available inventory at game/section level'
PARTITIONED BY (inventory_date)
""")
print("✅ boxscore.raw.available_inventory")

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS boxscore.raw.page_views (
    game_id             STRING      NOT NULL,
    view_date           DATE        NOT NULL,
    total_page_views    INT,
    unique_visitors     INT,
    avg_time_on_page_s  DOUBLE,
    bounce_rate         DOUBLE,
    mobile_pct          DOUBLE,
    referral_source     STRING
)
USING DELTA
COMMENT 'Daily page view metrics at game level'
PARTITIONED BY (view_date)
""")
print("✅ boxscore.raw.page_views")

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS boxscore.raw.sales (
    transaction_id      STRING      NOT NULL,
    game_id             STRING      NOT NULL,
    section_id          STRING      NOT NULL,
    seat_id             STRING,
    sale_timestamp      TIMESTAMP   NOT NULL,
    sale_date           DATE,
    quantity            INT,
    unit_price          DOUBLE,
    total_amount        DOUBLE,
    channel             STRING,
    customer_segment    STRING,
    is_season_ticket    BOOLEAN,
    is_group_sale       BOOLEAN,
    days_before_game    INT
)
USING DELTA
COMMENT 'Transaction-level ticket sales (every 15 min refresh)'
PARTITIONED BY (sale_date)
""")
print("✅ boxscore.raw.sales")

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS boxscore.raw.secondary_listings (
    listing_id          STRING      NOT NULL,
    game_id             STRING      NOT NULL,
    section_id          STRING      NOT NULL,
    listing_date        DATE        NOT NULL,
    listing_price       DOUBLE,
    quantity            INT,
    source              STRING,
    seller_type         STRING,
    is_giants_stm       BOOLEAN,
    days_before_game    INT,
    price_vs_face       DOUBLE
)
USING DELTA
COMMENT 'Daily secondary market listings (StubHub, brokers, STMs)'
PARTITIONED BY (listing_date)
""")
print("✅ boxscore.raw.secondary_listings")

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS boxscore.raw.secondary_sales (
    sale_id             STRING      NOT NULL,
    game_id             STRING      NOT NULL,
    section_id          STRING      NOT NULL,
    sale_date           DATE        NOT NULL,
    sale_price          DOUBLE,
    face_value          DOUBLE,
    quantity            INT,
    source              STRING,
    seller_type         STRING,
    is_giants_stm       BOOLEAN,
    markup_pct          DOUBLE,
    days_before_game    INT
)
USING DELTA
COMMENT 'Daily secondary market completed sales'
PARTITIONED BY (sale_date)
""")
print("✅ boxscore.raw.secondary_sales")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Feature Tables

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS boxscore.features.demand_features (
    game_id                 STRING      NOT NULL,
    section_id              STRING      NOT NULL,
    as_of_date              DATE        NOT NULL,
    page_views_7d_avg       DOUBLE,
    page_views_14d_avg      DOUBLE,
    page_views_30d_avg      DOUBLE,
    sales_velocity_24h      DOUBLE,
    sales_velocity_48h      DOUBLE,
    sales_velocity_72h      DOUBLE,
    days_to_event           INT,
    opponent_hist_draw      DOUBLE,
    day_of_week_enc         INT,
    month_enc               INT,
    is_weekend              BOOLEAN,
    has_promotion           BOOLEAN,
    promotion_type          STRING,
    season_win_pct          DOUBLE,
    demand_index            DOUBLE
)
USING DELTA
COMMENT 'Engineered demand features for ML models'
""")
print("✅ boxscore.features.demand_features")

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS boxscore.features.pricing_features (
    game_id                     STRING      NOT NULL,
    section_id                  STRING      NOT NULL,
    as_of_date                  DATE        NOT NULL,
    current_price               DOUBLE,
    historical_median_price     DOUBLE,
    price_vs_median_ratio       DOUBLE,
    price_rank_in_section       INT,
    secondary_market_median     DOUBLE,
    secondary_premium_ratio     DOUBLE,
    price_changes_7d            INT,
    competitor_price_index      DOUBLE,
    price_elasticity_est        DOUBLE
)
USING DELTA
COMMENT 'Engineered pricing features for ML models'
""")
print("✅ boxscore.features.pricing_features")

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS boxscore.features.inventory_features (
    game_id                     STRING      NOT NULL,
    section_id                  STRING      NOT NULL,
    as_of_date                  DATE        NOT NULL,
    sell_through_rate           DOUBLE,
    remaining_inventory         INT,
    remaining_by_tier           STRING,
    days_of_inventory           DOUBLE,
    masked_ratio                DOUBLE,
    hold_back_count             INT,
    velocity_trend              DOUBLE,
    inventory_risk_score        DOUBLE
)
USING DELTA
COMMENT 'Engineered inventory features for ML models'
""")
print("✅ boxscore.features.inventory_features")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Model Output Tables

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS boxscore.models.demand_predictions (
    game_id             STRING      NOT NULL,
    section_id          STRING,
    prediction_date     DATE        NOT NULL,
    forecast_horizon    INT,
    predicted_demand    DOUBLE,
    lower_bound         DOUBLE,
    upper_bound         DOUBLE,
    confidence          DOUBLE,
    model_version       STRING,
    model_name          STRING,
    run_id              STRING
)
USING DELTA
COMMENT 'Demand forecast predictions from ML models'
""")
print("✅ boxscore.models.demand_predictions")

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS boxscore.models.price_recommendations (
    game_id                 STRING      NOT NULL,
    section_id              STRING      NOT NULL,
    recommendation_date     DATE        NOT NULL,
    current_price           DOUBLE,
    recommended_price       DOUBLE,
    price_change            DOUBLE,
    expected_revenue_lift   DOUBLE,
    confidence_level        STRING,
    elasticity_at_price     DOUBLE,
    model_version           STRING,
    run_id                  STRING
)
USING DELTA
COMMENT 'Price change recommendations from optimization models'
""")
print("✅ boxscore.models.price_recommendations")

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS boxscore.models.inventory_allocations (
    game_id             STRING      NOT NULL,
    section_id          STRING      NOT NULL,
    allocation_date     DATE        NOT NULL,
    tier                STRING,
    allocated_seats     INT,
    mask_seats          INT,
    release_date        DATE,
    expected_revenue    DOUBLE,
    optimization_score  DOUBLE,
    model_version       STRING,
    run_id              STRING
)
USING DELTA
COMMENT 'Inventory allocation plans from optimization models'
""")
print("✅ boxscore.models.inventory_allocations")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Monitoring Tables

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS boxscore.monitoring.data_quality_log (
    check_id            STRING      NOT NULL,
    check_timestamp     TIMESTAMP   NOT NULL,
    table_name          STRING,
    feature_name        STRING,
    metric_type         STRING,
    metric_value        DOUBLE,
    threshold           DOUBLE,
    is_alert            BOOLEAN,
    details             STRING
)
USING DELTA
COMMENT 'Data quality and drift monitoring log'
""")
print("✅ boxscore.monitoring.data_quality_log")

# COMMAND ----------

spark.sql("""
CREATE TABLE IF NOT EXISTS boxscore.monitoring.model_metrics_log (
    log_id              STRING      NOT NULL,
    log_timestamp       TIMESTAMP   NOT NULL,
    model_name          STRING,
    model_version       STRING,
    metric_name         STRING,
    metric_value        DOUBLE,
    evaluation_set      STRING,
    window_start        DATE,
    window_end          DATE,
    is_degraded         BOOLEAN,
    details             STRING
)
USING DELTA
COMMENT 'Model performance tracking over time'
""")
print("✅ boxscore.monitoring.model_metrics_log")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verification

# COMMAND ----------

for schema in ["raw", "features", "models", "monitoring"]:
    tables = spark.sql(f"SHOW TABLES IN boxscore.{schema}").collect()
    print(f"\nboxscore.{schema}: {len(tables)} tables")
    for t in tables:
        print(f"  - {t.tableName}")

print("\n✅ Boxscore Unity Catalog setup complete!")
