import random
import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from databricks_client import query_serving_endpoint

router = APIRouter(prefix="/api/scoring", tags=["scoring"])
logger = logging.getLogger("boxscore.scoring")

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


def _build_demand_features(req: DemandRequest) -> dict:
    """Build feature vector matching the demand_forecast model's training schema."""
    base = SECTION_BASE_PRICES.get(req.section_id, 60)
    rival = RIVAL_MULTIPLIER.get(req.opponent, 1.0)
    return {
        "base_price": float(base),
        "days_to_event": req.days_to_event,
        "is_weekend": 1.0 if req.is_weekend else 0.0,
        "has_promotion": 1.0 if req.has_promotion else 0.0,
        "opponent_factor": rival,
        "section_capacity": 3500.0,
        "historical_demand_avg": 2625.0,
        "page_view_index": round(random.uniform(0.6, 1.4), 3),
        "sales_velocity_7d": round(random.uniform(80, 200), 1),
        "season_win_pct": 0.52,
    }


def _build_pricing_features(req: PricingRequest) -> dict:
    """Build feature vector matching the price_sensitivity model's training schema."""
    base = SECTION_BASE_PRICES.get(req.section_id, 60)
    return {
        "current_price": req.current_price,
        "base_price": float(base),
        "demand_forecast": float(req.demand_forecast),
        "inventory_level": req.inventory_level,
        "demand_ratio": req.demand_forecast / 41200.0,
        "price_vs_base_ratio": req.current_price / max(base, 1),
        "secondary_market_premium": round(random.uniform(1.05, 1.45), 3),
        "days_to_event": 14.0,
        "section_capacity": 3500.0,
        "competitor_price_index": round(random.uniform(0.9, 1.3), 3),
    }


def _mock_demand(req: DemandRequest) -> dict:
    """Fallback mock scoring when serving endpoint is unavailable."""
    base = SECTION_BASE_PRICES.get(req.section_id, 60)
    capacity = 3500
    rival = RIVAL_MULTIPLIER.get(req.opponent, 1.0)
    weekend = 1.12 if req.is_weekend else 1.0
    promo = 1.10 if req.has_promotion else 1.0
    decay = max(0.6, 1.0 - 0.008 * max(0, 60 - req.days_to_event))
    predicted = min(int(capacity * 0.75 * rival * weekend * promo * decay), capacity)
    noise = int(predicted * 0.06)
    std_dev = int(predicted * 0.08)

    return {
        "predicted_demand": predicted,
        "std_dev": std_dev,
        "confidence_lower": predicted - noise * 2,
        "confidence_upper": min(predicted + noise * 2, capacity),
    }


def _mock_pricing(req: PricingRequest) -> dict:
    """Fallback mock scoring when serving endpoint is unavailable."""
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

    recommended = round(max(req.current_price + price_adj, base * 0.5), 2)
    std_dev = round(recommended * random.uniform(0.05, 0.10), 2)

    return {
        "recommended_price": recommended,
        "elasticity": elasticity,
        "std_dev": std_dev,
    }


@router.post("/demand")
async def score_demand(req: DemandRequest):
    capacity = 3500
    source = "model-serving"

    features = _build_demand_features(req)
    payload = {"dataframe_records": [features]}

    resp = query_serving_endpoint("boxscore-demand-forecast", payload)

    if resp and "predictions" in resp:
        pred_raw = resp["predictions"]
        predicted = int(pred_raw[0]) if isinstance(pred_raw, list) else int(pred_raw)
        predicted = max(0, min(predicted, capacity))
        std_dev = int(predicted * 0.08)
        noise = int(predicted * 0.06)
        logger.info(f"Demand scored via serving endpoint: {predicted}")
    else:
        source = "mock-fallback"
        mock = _mock_demand(req)
        predicted = mock["predicted_demand"]
        std_dev = mock["std_dev"]
        noise = int(predicted * 0.06)
        logger.info("Demand scored via mock fallback")

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
        "model_version": 1,
        "serving_source": source,
        "factors": {
            "opponent_effect": round(RIVAL_MULTIPLIER.get(req.opponent, 1.0) - 1.0, 3),
            "weekend_effect": round((1.12 if req.is_weekend else 1.0) - 1.0, 3),
            "promotion_effect": round((1.10 if req.has_promotion else 1.0) - 1.0, 3),
            "time_decay_effect": round(max(0.6, 1.0 - 0.008 * max(0, 60 - req.days_to_event)) - 1.0, 3),
        },
    }


@router.post("/pricing")
async def score_pricing(req: PricingRequest):
    source = "model-serving"

    features = _build_pricing_features(req)
    payload = {"dataframe_records": [features]}

    resp = query_serving_endpoint("boxscore-price-sensitivity", payload)

    if resp and "predictions" in resp:
        pred_raw = resp["predictions"]
        recommended = round(float(pred_raw[0]) if isinstance(pred_raw, list) else float(pred_raw), 2)
        base = SECTION_BASE_PRICES.get(req.section_id, 60)
        recommended = max(recommended, base * 0.5)
        elasticity = round(random.uniform(-1.6, -0.4), 2)
        std_dev = round(recommended * random.uniform(0.05, 0.10), 2)
        logger.info(f"Pricing scored via serving endpoint: ${recommended}")
    else:
        source = "mock-fallback"
        mock = _mock_pricing(req)
        recommended = mock["recommended_price"]
        elasticity = mock["elasticity"]
        std_dev = mock["std_dev"]
        logger.info("Pricing scored via mock fallback")

    ml_confidence_score = round(random.uniform(0.70, 0.95), 2)
    delta_pct = (recommended - req.current_price) / max(req.current_price, 0.01)
    volume_change = elasticity * delta_pct
    new_volume = req.demand_forecast * (1 + volume_change)
    revenue_current = req.current_price * req.demand_forecast
    revenue_recommended = recommended * new_volume
    revenue_change = revenue_recommended - revenue_current

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
        "model_version": 1,
        "serving_source": source,
    }


@router.post("/what-if")
async def what_if(req: WhatIfRequest):
    base_capacity = 3500
    rival = RIVAL_MULTIPLIER.get(req.opponent, 1.0)
    base_demand = int(base_capacity * 0.72 * rival)

    elasticity = -1.1
    price_ratio = (req.proposed_price - req.current_price) / max(req.current_price, 0.01)
    demand_change = elasticity * price_ratio
    scenario_demand = max(0, min(int(base_demand * (1 + demand_change)), base_capacity))

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
