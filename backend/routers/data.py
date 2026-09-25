import random
from datetime import date, timedelta

from fastapi import APIRouter

router = APIRouter(prefix="/api/data", tags=["data"])

OPPONENTS = [
    "Los Angeles Dodgers", "San Diego Padres", "Arizona Diamondbacks",
    "Colorado Rockies", "Atlanta Braves", "New York Mets",
    "Philadelphia Phillies", "Chicago Cubs", "St. Louis Cardinals",
    "Milwaukee Brewers", "Cincinnati Reds", "Pittsburgh Pirates",
    "Houston Astros", "Oakland Athletics", "Seattle Mariners",
    "Texas Rangers",
]

SECTIONS = [
    {"name": "Field Club", "capacity": 2800, "base_price": 350},
    {"name": "Club Level Infield", "capacity": 3200, "base_price": 180},
    {"name": "Club Level Outfield", "capacity": 2400, "base_price": 120},
    {"name": "Lower Box Infield", "capacity": 4100, "base_price": 95},
    {"name": "Lower Box Outfield", "capacity": 3600, "base_price": 65},
    {"name": "View Reserve Infield", "capacity": 4800, "base_price": 55},
    {"name": "View Reserve Outfield", "capacity": 4200, "base_price": 40},
    {"name": "Bleachers", "capacity": 5400, "base_price": 30},
    {"name": "Arcade", "capacity": 3200, "base_price": 28},
    {"name": "Gallery", "capacity": 2600, "base_price": 25},
    {"name": "Suite Level", "capacity": 1800, "base_price": 450},
    {"name": "Gotham Club", "capacity": 600, "base_price": 420},
]

PROMOTIONS = [
    "Bobblehead Night", "Fireworks Friday", "Orange Friday",
    "Cap Giveaway", "Jersey Day", "Family Sunday",
    "Fan Appreciation", "Heritage Night", "Military Appreciation",
    None, None, None, None, None,
]

random.seed(42)


def _build_games(count: int = 30):
    games = []
    start = date(2026, 4, 3)
    for i in range(count):
        gd = start + timedelta(days=i * 2 + random.randint(0, 1))
        opp = OPPONENTS[i % len(OPPONENTS)]
        promo = random.choice(PROMOTIONS)
        is_weekend = gd.weekday() >= 4
        is_night = random.random() > 0.3
        rival_boost = 1.3 if "Dodgers" in opp else 1.15 if "Padres" in opp else 1.0
        base_demand = int(32000 * rival_boost * (1.1 if is_weekend else 1.0) * (1.15 if promo else 1.0))
        noise = random.randint(-2000, 2000)
        demand = max(20000, min(41200, base_demand + noise))
        games.append({
            "game_id": f"SF2026-{i+1:03d}",
            "game_date": gd.isoformat(),
            "opponent": opp,
            "day_of_week": gd.strftime("%A"),
            "time": "19:15" if is_night else "13:05",
            "promotion": promo,
            "is_weekend": is_weekend,
            "forecast_demand": demand,
            "actual_demand": demand + random.randint(-1500, 1500) if i < 20 else None,
            "confidence_lower": demand - 2500,
            "confidence_upper": demand + 2500,
        })
    return games


GAMES = _build_games(30)


@router.get("/dashboard")
async def dashboard():
    completed = [g for g in GAMES if g["actual_demand"] is not None]
    total_revenue = sum(
        int(g["actual_demand"] * random.uniform(55, 85)) for g in completed
    )
    total_sold = sum(g["actual_demand"] for g in completed)
    return {
        "total_revenue": total_revenue,
        "total_revenue_formatted": f"${total_revenue:,.0f}",
        "total_tickets_sold": total_sold,
        "avg_ticket_price": round(total_revenue / max(total_sold, 1), 2),
        "sell_through_rate": round(random.uniform(0.78, 0.92), 3),
        "games_completed": len(completed),
        "games_remaining": len(GAMES) - len(completed),
        "season_forecast_revenue": int(total_revenue * (81 / max(len(completed), 1))),
        "upcoming_games": [
            {
                "game_id": g["game_id"],
                "date": g["game_date"],
                "opponent": g["opponent"],
                "forecast_demand": g["forecast_demand"],
                "promotion": g["promotion"],
            }
            for g in GAMES if g["actual_demand"] is None
        ][:5],
        "model_health": {
            "demand_forecast": {"status": "healthy", "mape": 8.2},
            "price_sensitivity": {"status": "healthy", "mape": 6.1},
            "revenue_predictor": {"status": "warning", "mape": 12.4},
        },
    }


@router.get("/demand")
async def demand():
    return {"games": GAMES}


@router.get("/pricing")
async def pricing():
    rows = []
    confidence_tiers = {
        "Field Club": 0.94, "Club Level Infield": 0.91, "Club Level Outfield": 0.89,
        "Lower Box Infield": 0.86, "Lower Box Outfield": 0.84, "View Reserve Infield": 0.82,
        "View Reserve Outfield": 0.78, "Bleachers": 0.72, "Arcade": 0.75,
        "Gallery": 0.65, "Suite Level": 0.92, "Gotham Club": 0.90,
    }
    for sec in SECTIONS:
        elasticity = round(random.uniform(-1.8, -0.3), 2)
        rec_change = round(sec["base_price"] * random.uniform(-0.08, 0.15), 2)
        recommended_mean = round(sec["base_price"] + rec_change, 2)
        std_dev = round(sec["base_price"] * random.uniform(0.05, 0.12), 2)
        ml_score = confidence_tiers.get(sec["name"], 0.70)
        rows.append({
            "section": sec["name"],
            "current_price": sec["base_price"],
            "recommended_price": recommended_mean,
            "recommended_price_mean": recommended_mean,
            "recommended_price_min": round(recommended_mean - std_dev * 1.96, 2),
            "recommended_price_max": round(recommended_mean + std_dev * 1.96, 2),
            "std_dev": std_dev,
            "ml_confidence_score": ml_score,
            "confidence_interval": "95%",
            "price_change": round(rec_change, 2),
            "elasticity": elasticity,
            "confidence": "high" if ml_score >= 0.85 else "medium" if ml_score >= 0.70 else "low",
            "revenue_impact": round(rec_change * sec["capacity"] * random.uniform(0.6, 0.9), 0),
            "sell_through_at_current": round(random.uniform(0.65, 0.95), 3),
            "sell_through_at_recommended": round(random.uniform(0.75, 0.98), 3),
        })
    return {"sections": rows}


@router.get("/inventory")
async def inventory():
    rows = []
    for sec in SECTIONS:
        sell_pct = round(random.uniform(0.55, 0.95), 3)
        sold = int(sec["capacity"] * sell_pct)
        masked = int((sec["capacity"] - sold) * random.uniform(0.1, 0.4))
        rows.append({
            "section": sec["name"],
            "capacity": sec["capacity"],
            "sold": sold,
            "available": sec["capacity"] - sold - masked,
            "masked": masked,
            "sell_through_pct": sell_pct,
            "price_tier": "premium" if sec["base_price"] > 150 else "standard" if sec["base_price"] > 50 else "value",
            "avg_price": round(sec["base_price"] * random.uniform(0.9, 1.2), 2),
            "days_of_inventory": round(random.uniform(2, 30), 1),
        })
    return {"sections": rows, "total_capacity": 41200}


@router.get("/events")
async def events():
    return {"events": GAMES}


@router.get("/monitoring")
async def monitoring():
    models_data = [
        {
            "model_name": "boxscore-demand-forecast",
            "mape": round(random.uniform(6, 12), 1),
            "rmse": round(random.uniform(1200, 2800), 0),
            "r2": round(random.uniform(0.82, 0.94), 3),
            "drift_score": round(random.uniform(0.02, 0.18), 3),
            "last_trained": "2026-09-20",
            "status": "healthy",
            "predictions_today": 324,
        },
        {
            "model_name": "boxscore-price-sensitivity",
            "mape": round(random.uniform(4, 9), 1),
            "rmse": round(random.uniform(0.02, 0.08), 4),
            "r2": round(random.uniform(0.85, 0.95), 3),
            "drift_score": round(random.uniform(0.01, 0.12), 3),
            "last_trained": "2026-09-18",
            "status": "healthy",
            "predictions_today": 1890,
        },
        {
            "model_name": "boxscore-revenue-predictor",
            "mape": round(random.uniform(8, 16), 1),
            "rmse": round(random.uniform(45000, 120000), 0),
            "r2": round(random.uniform(0.72, 0.88), 3),
            "drift_score": round(random.uniform(0.08, 0.25), 3),
            "last_trained": "2026-09-15",
            "status": "warning",
            "predictions_today": 81,
        },
        {
            "model_name": "boxscore-anomaly-detector",
            "mape": None,
            "rmse": None,
            "r2": None,
            "drift_score": round(random.uniform(0.01, 0.08), 3),
            "last_trained": "2026-09-22",
            "status": "healthy",
            "predictions_today": 162,
            "anomalies_flagged": 3,
        },
        {
            "model_name": "boxscore-recommendation-engine",
            "mape": round(random.uniform(5, 10), 1),
            "rmse": round(random.uniform(3, 12), 1),
            "r2": round(random.uniform(0.80, 0.92), 3),
            "drift_score": round(random.uniform(0.03, 0.15), 3),
            "last_trained": "2026-09-21",
            "status": "healthy",
            "predictions_today": 972,
        },
    ]
    return {
        "models": models_data,
        "drift_history": [
            {"date": (date(2026, 9, 1) + timedelta(days=i)).isoformat(),
             "demand_psi": round(random.uniform(0.01, 0.15), 3),
             "pricing_psi": round(random.uniform(0.01, 0.10), 3),
             "inventory_psi": round(random.uniform(0.02, 0.20), 3)}
            for i in range(24)
        ],
    }
