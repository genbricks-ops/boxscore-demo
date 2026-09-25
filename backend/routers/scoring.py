import random
import math
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/scoring", tags=["scoring"])

SECTION_BASE_PRICES = {
    "Field Club": 350, "Club Level Infield": 180, "Club Level Outfield": 120,
    "Lower Box Infield": 95, "Lower Box Outfield": 65, "View Reserve Infield": 55,
    "View Reserve Outfield": 40, "Bleachers": 30, "Arcade": 28, "Gallery": 25,
    "Suite Level": 450, "Gotham Club": 420,
}

RIVAL_MULTIPLIER = {
    "Los Angeles Dodgers": 1.35, "San Diego Padres": 1.15,
    "Atlanta Braves": 1.10, "New York Mets": 1.08,
}


class DemandRequest(BaseModel):
    game_id: str
    section_id: str = "Lower Box Infield"
    days_to_event: int = 14
    opponent: str = "Los Angeles Dodgers"
    is_weekend: bool = False
    has_promotion: bool = False


class PricingRequest(BaseModel):
    game_id: str
    section_id: str = "Lower Box Infield"
    current_price: float = 95.0
    demand_forecast: int = 35000
    inventory_level: float = 0.4


class WhatIfRequest(BaseModel):
    game_id: str
    section_id: str = "Lower Box Infield"
    proposed_price: float
    current_price: float
    days_to_event: int = 14
    opponent: Optional[str] = "Colorado Rockies"


@router.post("/demand")
async def score_demand(req: DemandRequest):
    base = SECTION_BASE_PRICES.get(req.section_id, 60)
    capacity = 3500

    rival = RIVAL_MULTIPLIER.get(req.opponent, 1.0)
    weekend = 1.12 if req.is_weekend else 1.0
    promo = 1.10 if req.has_promotion else 1.0
    decay = max(0.6, 1.0 - 0.008 * max(0, 60 - req.days_to_event))

    predicted = int(capacity * 0.75 * rival * weekend * promo * decay)
    predicted = min(predicted, capacity)
    noise = int(predicted * 0.06)

    std_dev = int(predicted * 0.08)

    return {
        "game_id": req.game_id,
        "section_id": req.section_id,
        "predicted_demand": predicted,
        "std_dev": std_dev,
        "confidence_lower": predicted - noise * 2,
        "confidence_upper": min(predicted + noise * 2, capacity),
        "confidence_level": 0.95,
        "prediction_interval": "95%",
        "sell_through_probability": round(min(predicted / capacity, 0.99), 3),
        "model": "boxscore-demand-forecast",
        "model_version": 4,
        "factors": {
            "opponent_effect": round(rival - 1.0, 3),
            "weekend_effect": round(weekend - 1.0, 3),
            "promotion_effect": round(promo - 1.0, 3),
            "time_decay_effect": round(decay - 1.0, 3),
        },
    }


@router.post("/pricing")
async def score_pricing(req: PricingRequest):
    base = SECTION_BASE_PRICES.get(req.section_id, 60)
    elasticity = round(random.uniform(-1.6, -0.4), 2)
    demand_ratio = req.demand_forecast / 41200

    if demand_ratio > 0.85:
        price_adj = base * random.uniform(0.05, 0.18)
    elif demand_ratio > 0.70:
        price_adj = base * random.uniform(-0.02, 0.08)
    else:
        price_adj = base * random.uniform(-0.12, -0.02)

    if req.inventory_level < 0.2:
        price_adj += base * 0.10
    elif req.inventory_level > 0.6:
        price_adj -= base * 0.05

    recommended = round(req.current_price + price_adj, 2)
    recommended = max(recommended, base * 0.5)

    delta_pct = (recommended - req.current_price) / req.current_price
    volume_change = elasticity * delta_pct
    new_volume = req.demand_forecast * (1 + volume_change)
    revenue_current = req.current_price * req.demand_forecast
    revenue_recommended = recommended * new_volume
    revenue_change = revenue_recommended - revenue_current

    std_dev = round(recommended * random.uniform(0.05, 0.10), 2)
    ml_confidence_score = round(random.uniform(0.70, 0.95), 2)

    return {
        "game_id": req.game_id,
        "section_id": req.section_id,
        "current_price": req.current_price,
        "recommended_price": recommended,
        "recommended_price_range": {
            "min": round(recommended - std_dev * 1.96, 2),
            "max": round(recommended + std_dev * 1.96, 2),
            "mean": recommended,
            "std_dev": std_dev,
        },
        "ml_confidence_score": ml_confidence_score,
        "prediction_interval": "95%",
        "price_change": round(recommended - req.current_price, 2),
        "price_change_pct": round(delta_pct * 100, 1),
        "elasticity": elasticity,
        "expected_volume_change_pct": round(volume_change * 100, 1),
        "expected_revenue_change": round(revenue_change, 0),
        "expected_revenue_change_pct": round(revenue_change / max(revenue_current, 1) * 100, 1),
        "confidence": "high" if ml_confidence_score >= 0.85 else "medium" if ml_confidence_score >= 0.70 else "low",
        "model": "boxscore-price-sensitivity",
        "model_version": 3,
    }


@router.post("/what-if")
async def what_if(req: WhatIfRequest):
    base_capacity = 3500
    rival = RIVAL_MULTIPLIER.get(req.opponent, 1.0)
    base_demand = int(base_capacity * 0.72 * rival)

    elasticity = -1.1
    price_ratio = (req.proposed_price - req.current_price) / req.current_price
    demand_change = elasticity * price_ratio
    scenario_demand = int(base_demand * (1 + demand_change))
    scenario_demand = max(0, min(scenario_demand, base_capacity))

    revenue_current = req.current_price * base_demand
    revenue_proposed = req.proposed_price * scenario_demand

    return {
        "game_id": req.game_id,
        "section_id": req.section_id,
        "scenario": {
            "current": {
                "price": req.current_price,
                "estimated_demand": base_demand,
                "estimated_revenue": round(revenue_current, 0),
                "sell_through": round(base_demand / base_capacity, 3),
            },
            "proposed": {
                "price": req.proposed_price,
                "estimated_demand": scenario_demand,
                "estimated_revenue": round(revenue_proposed, 0),
                "sell_through": round(scenario_demand / base_capacity, 3),
            },
        },
        "revenue_delta": round(revenue_proposed - revenue_current, 0),
        "revenue_delta_pct": round((revenue_proposed - revenue_current) / max(revenue_current, 1) * 100, 1),
        "demand_delta": scenario_demand - base_demand,
        "recommendation": "increase" if revenue_proposed > revenue_current else "hold",
        "confidence": "medium",
    }
