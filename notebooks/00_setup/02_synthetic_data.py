# Databricks notebook source
# MAGIC %md
# MAGIC # Boxscore — Synthetic Data Generation
# MAGIC Generates realistic ticket data for the SF Giants 2024–2026 seasons across all 8 raw tables.

# COMMAND ----------

import uuid
from datetime import date, datetime, timedelta
from pyspark.sql import functions as F
from pyspark.sql.types import *

spark.sql("USE CATALOG boxscore")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

SEASONS = [2024, 2025, 2026]
GAMES_PER_SEASON = 81
ORACLE_PARK_CAPACITY = 41_265

SECTIONS = [
    ("SEC_FC1", "Field Club 1",        120, "premium",  15.0),
    ("SEC_FC2", "Field Club 2",        120, "premium",  20.0),
    ("SEC_CL1", "Club Level 201",      250, "club",     45.0),
    ("SEC_CL2", "Club Level 202",      250, "club",     50.0),
    ("SEC_CL3", "Club Level 203",      250, "club",     55.0),
    ("SEC_CL4", "Club Level 204",      220, "club",     60.0),
    ("SEC_LB1", "Lower Box 101",       400, "lower",    90.0),
    ("SEC_LB2", "Lower Box 102",       400, "lower",    95.0),
    ("SEC_LB3", "Lower Box 103",       380, "lower",   100.0),
    ("SEC_LB4", "Lower Box 104",       380, "lower",   105.0),
    ("SEC_UB1", "Upper Box 301",       500, "upper",   150.0),
    ("SEC_UB2", "Upper Box 302",       500, "upper",   155.0),
    ("SEC_UB3", "Upper Box 303",       480, "upper",   160.0),
    ("SEC_VR1", "View Reserve 311",    600, "view",    200.0),
    ("SEC_VR2", "View Reserve 312",    600, "view",    210.0),
    ("SEC_VR3", "View Reserve 313",    550, "view",    220.0),
    ("SEC_BL1", "Bleachers 135",       800, "bleacher", 280.0),
    ("SEC_BL2", "Bleachers 136",       800, "bleacher", 290.0),
    ("SEC_AR1", "Arcade 147",          350, "arcade",  130.0),
    ("SEC_AR2", "Arcade 148",          350, "arcade",  140.0),
]

OPPONENTS = [
    ("LAD", "Los Angeles Dodgers",    1.35),
    ("SDP", "San Diego Padres",       1.10),
    ("ARI", "Arizona Diamondbacks",   0.95),
    ("COL", "Colorado Rockies",       0.85),
    ("NYY", "New York Yankees",       1.40),
    ("BOS", "Boston Red Sox",         1.25),
    ("CHC", "Chicago Cubs",           1.15),
    ("STL", "St. Louis Cardinals",    1.05),
    ("ATL", "Atlanta Braves",         1.10),
    ("PHI", "Philadelphia Phillies",  1.10),
    ("NYM", "New York Mets",          1.05),
    ("HOU", "Houston Astros",         1.20),
    ("SEA", "Seattle Mariners",       0.95),
    ("OAK", "Oakland Athletics",      0.90),
    ("TEX", "Texas Rangers",          1.00),
    ("MIA", "Miami Marlins",          0.80),
    ("PIT", "Pittsburgh Pirates",     0.80),
    ("CIN", "Cincinnati Reds",        0.90),
    ("MIL", "Milwaukee Brewers",      0.95),
    ("WSH", "Washington Nationals",   0.85),
]

PROMOTIONS = [
    (None,            None,                    0.00),
    ("bobblehead",    "Player Bobblehead",     0.15),
    ("fireworks",     "Friday Night Fireworks", 0.12),
    ("hat_day",       "Giants Hat Day",         0.10),
    ("jersey_day",    "Jersey Giveaway",        0.12),
    ("family",        "Family Sunday",          0.08),
    ("heritage",      "Heritage Night",         0.06),
    ("bark_park",     "Dog Day at the Park",    0.05),
    ("college_night", "College Night",          0.04),
]

BASE_PRICES = {
    "premium":  (250.0, 600.0),
    "club":     (120.0, 350.0),
    "lower":    (70.0,  200.0),
    "upper":    (40.0,  120.0),
    "view":     (25.0,  80.0),
    "bleacher": (15.0,  50.0),
    "arcade":   (55.0,  160.0),
}

CHANNELS = ["online", "box_office", "mobile_app", "phone", "group_sales", "season_ticket"]
SEGMENTS = ["individual", "season_ticket_holder", "group", "corporate", "student", "military"]

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Generate Event Details

# COMMAND ----------

import random
random.seed(42)

event_rows = []
game_counter = 0

for season in SEASONS:
    season_start = date(season, 3, 28)
    season_end = date(season, 9, 29)
    delta_days = (season_end - season_start).days

    game_dates = sorted(random.sample(
        [season_start + timedelta(days=d) for d in range(delta_days)],
        min(GAMES_PER_SEASON, delta_days)
    ))

    win_count = 0
    for g_idx, gd in enumerate(game_dates):
        game_counter += 1
        game_id = f"G{season}_{g_idx+1:03d}"
        opp_code, opp_name, opp_strength = random.choice(OPPONENTS)
        promo_type, promo_desc, promo_boost = random.choice(PROMOTIONS)

        day_name = gd.strftime("%A")
        is_weekend = day_name in ("Saturday", "Sunday", "Friday")
        game_time = "19:15" if gd.weekday() < 5 else random.choice(["13:05", "16:05", "18:05"])
        dn = "night" if int(game_time.split(":")[0]) >= 17 else "day"

        base_att = int(ORACLE_PARK_CAPACITY * 0.70)
        att_adj = int(base_att * opp_strength)
        att_adj = int(att_adj * (1 + promo_boost))
        if is_weekend:
            att_adj = int(att_adj * 1.08)
        att_adj += random.randint(-2000, 2000)
        attendance = max(20000, min(ORACLE_PARK_CAPACITY, att_adj))

        win_count += 1 if random.random() < 0.52 else 0
        win_pct = round(win_count / (g_idx + 1), 3)

        weather_temp = round(random.gauss(62, 8), 1)
        weather_cond = random.choice(["clear", "partly_cloudy", "foggy", "overcast", "windy"])

        event_rows.append((
            game_id, season, gd, game_time, dn, day_name,
            opp_name, opp_strength, True, promo_type, promo_desc,
            is_weekend, gd.month, attendance, ORACLE_PARK_CAPACITY,
            weather_temp, weather_cond
        ))

event_schema = StructType([
    StructField("game_id", StringType()), StructField("season", IntegerType()),
    StructField("game_date", DateType()), StructField("game_time", StringType()),
    StructField("day_night", StringType()), StructField("day_of_week", StringType()),
    StructField("opponent", StringType()), StructField("opponent_strength", DoubleType()),
    StructField("is_home", BooleanType()), StructField("promotion_type", StringType()),
    StructField("promotion_desc", StringType()), StructField("is_weekend", BooleanType()),
    StructField("month", IntegerType()), StructField("attendance", IntegerType()),
    StructField("capacity", IntegerType()), StructField("weather_temp_f", DoubleType()),
    StructField("weather_condition", StringType()),
])

df_events = spark.createDataFrame(event_rows, schema=event_schema)
df_events.write.mode("overwrite").saveAsTable("boxscore.raw.event_details")
print(f"✅ event_details: {df_events.count()} games")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Generate Seat Facts

# COMMAND ----------

seat_rows = []
for sec_id, sec_name, capacity, tier, dist in SECTIONS:
    for s in range(1, capacity + 1):
        row_num = (s - 1) // 20 + 1
        seat_num = (s - 1) % 20 + 1
        row_name = chr(64 + min(row_num, 26))

        quality = round(max(0.1, min(1.0, 1.0 - (dist / 350.0) + random.gauss(0, 0.05))), 3)
        view_rat = round(max(1.0, min(5.0, quality * 5)), 1)
        is_aisle = seat_num in (1, 20)
        is_front = row_num == 1

        seat_id = f"{sec_id}_R{row_name}_{seat_num:02d}"
        seat_rows.append((
            seat_id, sec_id, sec_name, row_name, seat_num,
            quality, dist, is_aisle, is_front,
            random.random() < 0.4, view_rat, tier, capacity
        ))

seat_schema = StructType([
    StructField("seat_id", StringType()), StructField("section_id", StringType()),
    StructField("section_name", StringType()), StructField("row_name", StringType()),
    StructField("seat_number", IntegerType()), StructField("seat_quality_score", DoubleType()),
    StructField("distance_to_home_ft", DoubleType()), StructField("is_aisle", BooleanType()),
    StructField("is_front_row", BooleanType()), StructField("has_shade", BooleanType()),
    StructField("view_rating", DoubleType()), StructField("price_tier", StringType()),
    StructField("section_capacity", IntegerType()),
])

df_seats = spark.createDataFrame(seat_rows, schema=seat_schema)
df_seats.write.mode("overwrite").saveAsTable("boxscore.raw.seat_facts")
print(f"✅ seat_facts: {df_seats.count()} seats")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Generate Pricing Data
# MAGIC Daily pricing per game/section, with dynamic adjustments based on demand signals.

# COMMAND ----------

events_list = df_events.select("game_id", "game_date", "opponent_strength", "promotion_type", "is_weekend").collect()

pricing_rows = []
for ev in events_list:
    gd = ev.game_date
    for sec_id, sec_name, capacity, tier, dist in SECTIONS:
        lo, hi = BASE_PRICES[tier]
        base = round(random.uniform(lo, hi), 2)

        for days_out in range(60, -1, -1):
            price_date = gd - timedelta(days=days_out)
            if price_date < date(2024, 1, 1):
                continue

            decay = 1.0 + 0.3 * (1 - days_out / 60.0)
            opp_mult = ev.opponent_strength
            promo_mult = 1.08 if ev.promotion_type else 1.0
            wknd_mult = 1.05 if ev.is_weekend else 1.0
            noise = random.gauss(1.0, 0.02)

            current = round(base * decay * opp_mult * promo_mult * wknd_mult * noise, 2)
            current = max(lo * 0.8, min(hi * 1.5, current))

            change_dir = "up" if current > base else ("down" if current < base else "none")

            pricing_rows.append((
                ev.game_id, sec_id, price_date, base, current,
                round(lo * 0.8, 2), round(hi * 1.5, 2), tier,
                random.randint(1, 8), None, change_dir,
                round(current - base, 2)
            ))

pricing_schema = StructType([
    StructField("game_id", StringType()), StructField("section_id", StringType()),
    StructField("price_date", DateType()), StructField("base_price", DoubleType()),
    StructField("current_price", DoubleType()), StructField("min_price", DoubleType()),
    StructField("max_price", DoubleType()), StructField("price_tier", StringType()),
    StructField("price_scale", IntegerType()), StructField("last_price_change", TimestampType()),
    StructField("change_direction", StringType()), StructField("change_amount", DoubleType()),
])

df_pricing = spark.createDataFrame(pricing_rows, schema=pricing_schema)
df_pricing.write.mode("overwrite").saveAsTable("boxscore.raw.pricing")
print(f"✅ pricing: {df_pricing.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Generate Page Views

# COMMAND ----------

pv_rows = []
for ev in events_list:
    gd = ev.game_date
    for days_out in range(90, -1, -1):
        vd = gd - timedelta(days=days_out)
        if vd < date(2024, 1, 1):
            continue

        base_pv = 500
        time_mult = 1.0 + 3.0 * max(0, 1 - days_out / 30.0)
        opp_mult = ev.opponent_strength
        promo_mult = 1.2 if ev.promotion_type else 1.0
        wknd_mult = 1.3 if vd.weekday() >= 4 else 1.0

        total_pv = int(base_pv * time_mult * opp_mult * promo_mult * wknd_mult * random.gauss(1, 0.15))
        total_pv = max(50, total_pv)
        unique = int(total_pv * random.uniform(0.55, 0.80))

        pv_rows.append((
            ev.game_id, vd, total_pv, unique,
            round(random.uniform(30, 180), 1),
            round(random.uniform(0.25, 0.65), 3),
            round(random.uniform(0.45, 0.75), 3),
            random.choice(["organic", "email", "social", "paid", "direct"])
        ))

pv_schema = StructType([
    StructField("game_id", StringType()), StructField("view_date", DateType()),
    StructField("total_page_views", IntegerType()), StructField("unique_visitors", IntegerType()),
    StructField("avg_time_on_page_s", DoubleType()), StructField("bounce_rate", DoubleType()),
    StructField("mobile_pct", DoubleType()), StructField("referral_source", StringType()),
])

df_pv = spark.createDataFrame(pv_rows, schema=pv_schema)
df_pv.write.mode("overwrite").saveAsTable("boxscore.raw.page_views")
print(f"✅ page_views: {df_pv.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Generate Sales Data
# MAGIC Transaction-level ticket sales — generated with Spark for volume.

# COMMAND ----------

events_broadcast = spark.sparkContext.broadcast(
    [(ev.game_id, ev.game_date, ev.opponent_strength, ev.promotion_type, ev.is_weekend) for ev in events_list]
)
sections_broadcast = spark.sparkContext.broadcast(
    [(s[0], s[1], s[2], s[3]) for s in SECTIONS]
)

sales_rows = []
for ev_tuple in events_broadcast.value:
    game_id, gd, opp_str, promo, is_wknd = ev_tuple
    for sec_id, sec_name, capacity, tier in sections_broadcast.value:
        sell_rate = min(0.95, 0.55 * opp_str * (1.1 if promo else 1.0) * (1.05 if is_wknd else 1.0))
        total_sold = int(capacity * sell_rate)

        lo, hi = BASE_PRICES.get(tier, (30, 100))
        for i in range(total_sold):
            days_before = max(0, int(random.expovariate(0.03)))
            days_before = min(days_before, 120)
            sale_dt = gd - timedelta(days=days_before)
            hour = random.choice([9,10,11,12,13,14,15,16,17,18,19,20])
            minute = random.randint(0, 59)
            sale_ts = datetime.combine(sale_dt, datetime.min.time()).replace(hour=hour, minute=minute)

            price = round(random.uniform(lo, hi) * opp_str, 2)
            channel = random.choice(CHANNELS)
            segment = random.choice(SEGMENTS)

            seat_idx = random.randint(1, capacity)
            row_letter = chr(64 + min((seat_idx - 1) // 20 + 1, 26))
            seat_num = (seat_idx - 1) % 20 + 1
            seat_id = f"{sec_id}_R{row_letter}_{seat_num:02d}"

            sales_rows.append((
                str(uuid.uuid4())[:12], game_id, sec_id, seat_id,
                sale_ts, sale_dt, 1, price, price,
                channel, segment,
                segment == "season_ticket_holder",
                segment == "group",
                days_before
            ))

sales_schema = StructType([
    StructField("transaction_id", StringType()), StructField("game_id", StringType()),
    StructField("section_id", StringType()), StructField("seat_id", StringType()),
    StructField("sale_timestamp", TimestampType()), StructField("sale_date", DateType()),
    StructField("quantity", IntegerType()), StructField("unit_price", DoubleType()),
    StructField("total_amount", DoubleType()), StructField("channel", StringType()),
    StructField("customer_segment", StringType()), StructField("is_season_ticket", BooleanType()),
    StructField("is_group_sale", BooleanType()), StructField("days_before_game", IntegerType()),
])

df_sales = spark.createDataFrame(sales_rows, schema=sales_schema)
df_sales.write.mode("overwrite").saveAsTable("boxscore.raw.sales")
print(f"✅ sales: {df_sales.count()} transactions")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Generate Available Inventory

# COMMAND ----------

inv_rows = []
for ev in events_list:
    gd = ev.game_date
    for sec_id, sec_name, capacity, tier, dist in SECTIONS:
        sell_rate = min(0.95, 0.55 * ev.opponent_strength * (1.1 if ev.promotion_type else 1.0))

        for days_out in [60, 45, 30, 21, 14, 7, 3, 1, 0]:
            inv_date = gd - timedelta(days=days_out)
            if inv_date < date(2024, 1, 1):
                continue

            progress = 1 - (days_out / 60.0)
            sold = int(capacity * sell_rate * progress * random.uniform(0.85, 1.15))
            sold = max(0, min(capacity, sold))
            held = int(capacity * random.uniform(0.02, 0.08))
            masked = int(capacity * random.uniform(0, 0.05))
            available = max(0, capacity - sold - held - masked)

            inv_rows.append((
                ev.game_id, sec_id, inv_date, capacity, available,
                sold, held, masked,
                round(sold / capacity, 4) if capacity > 0 else 0, tier
            ))

inv_schema = StructType([
    StructField("game_id", StringType()), StructField("section_id", StringType()),
    StructField("inventory_date", DateType()), StructField("total_seats", IntegerType()),
    StructField("available_seats", IntegerType()), StructField("sold_seats", IntegerType()),
    StructField("held_seats", IntegerType()), StructField("masked_seats", IntegerType()),
    StructField("sell_through_pct", DoubleType()), StructField("price_tier", StringType()),
])

df_inv = spark.createDataFrame(inv_rows, schema=inv_schema)
df_inv.write.mode("overwrite").saveAsTable("boxscore.raw.available_inventory")
print(f"✅ available_inventory: {df_inv.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Generate Secondary Market Listings

# COMMAND ----------

listing_rows = []
for ev in events_list:
    gd = ev.game_date
    for sec_id, sec_name, capacity, tier, dist in SECTIONS:
        lo, hi = BASE_PRICES[tier]
        num_listings = int(capacity * random.uniform(0.05, 0.20))

        for _ in range(num_listings):
            days_before = random.randint(0, 45)
            listing_date = gd - timedelta(days=days_before)
            if listing_date < date(2024, 1, 1):
                continue

            face_val = round(random.uniform(lo, hi), 2)
            markup = 1.0 + random.uniform(-0.1, 0.8) * ev.opponent_strength
            listing_price = round(face_val * markup, 2)
            qty = random.choice([1, 1, 1, 2, 2, 4])
            source = random.choice(["stubhub", "seatgeek", "vivid_seats", "ticketmaster_resale"])
            seller = random.choice(["broker", "stm", "individual"])

            listing_rows.append((
                str(uuid.uuid4())[:12], ev.game_id, sec_id, listing_date,
                listing_price, qty, source, seller,
                seller == "stm", days_before,
                round((listing_price - face_val) / face_val, 4) if face_val > 0 else 0
            ))

listing_schema = StructType([
    StructField("listing_id", StringType()), StructField("game_id", StringType()),
    StructField("section_id", StringType()), StructField("listing_date", DateType()),
    StructField("listing_price", DoubleType()), StructField("quantity", IntegerType()),
    StructField("source", StringType()), StructField("seller_type", StringType()),
    StructField("is_giants_stm", BooleanType()), StructField("days_before_game", IntegerType()),
    StructField("price_vs_face", DoubleType()),
])

df_listings = spark.createDataFrame(listing_rows, schema=listing_schema)
df_listings.write.mode("overwrite").saveAsTable("boxscore.raw.secondary_listings")
print(f"✅ secondary_listings: {df_listings.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Generate Secondary Market Sales

# COMMAND ----------

sec_sale_rows = []
for ev in events_list:
    gd = ev.game_date
    for sec_id, sec_name, capacity, tier, dist in SECTIONS:
        lo, hi = BASE_PRICES[tier]
        num_sales = int(capacity * random.uniform(0.02, 0.10))

        for _ in range(num_sales):
            days_before = random.randint(0, 30)
            sale_date = gd - timedelta(days=days_before)
            if sale_date < date(2024, 1, 1):
                continue

            face_val = round(random.uniform(lo, hi), 2)
            markup = 1.0 + random.uniform(-0.15, 0.6) * ev.opponent_strength
            sale_price = round(face_val * markup, 2)
            qty = random.choice([1, 1, 2, 2])
            source = random.choice(["stubhub", "seatgeek", "vivid_seats"])
            seller = random.choice(["broker", "stm", "individual"])

            sec_sale_rows.append((
                str(uuid.uuid4())[:12], ev.game_id, sec_id, sale_date,
                sale_price, face_val, qty, source, seller,
                seller == "stm",
                round((sale_price - face_val) / face_val * 100, 2) if face_val > 0 else 0,
                days_before
            ))

sec_sale_schema = StructType([
    StructField("sale_id", StringType()), StructField("game_id", StringType()),
    StructField("section_id", StringType()), StructField("sale_date", DateType()),
    StructField("sale_price", DoubleType()), StructField("face_value", DoubleType()),
    StructField("quantity", IntegerType()), StructField("source", StringType()),
    StructField("seller_type", StringType()), StructField("is_giants_stm", BooleanType()),
    StructField("markup_pct", DoubleType()), StructField("days_before_game", IntegerType()),
])

df_sec_sales = spark.createDataFrame(sec_sale_rows, schema=sec_sale_schema)
df_sec_sales.write.mode("overwrite").saveAsTable("boxscore.raw.secondary_sales")
print(f"✅ secondary_sales: {df_sec_sales.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 60)
print("  Boxscore Synthetic Data Generation — Complete")
print("=" * 60)
for tbl in ["event_details", "seat_facts", "pricing", "available_inventory",
            "page_views", "sales", "secondary_listings", "secondary_sales"]:
    count = spark.table(f"boxscore.raw.{tbl}").count()
    print(f"  boxscore.raw.{tbl:25s} → {count:>10,} rows")
print("=" * 60)
