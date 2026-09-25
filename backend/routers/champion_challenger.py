"""Champion/Challenger feedback loop — compare models, accept/reject, swap serving."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

import databricks_client as dbc

router = APIRouter(prefix="/api/champion-challenger", tags=["champion-challenger"])
logger = logging.getLogger("boxscore.champion_challenger")

# In-memory evaluation store (production: use Delta table)
_evaluations: dict = {}
_promotion_history: list = []

MODEL_CONFIGS = {
    "demand_forecast": {
        "uc_name": "workspace.boxscore_models.demand_forecast",
        "endpoint": "boxscore-demand-forecast",
        "primary_metric": "mape",
        "lower_is_better": True,
        "threshold": 15.0,
    },
    "price_sensitivity": {
        "uc_name": "workspace.boxscore_models.price_sensitivity",
        "endpoint": "boxscore-price-sensitivity",
        "primary_metric": "mape",
        "lower_is_better": True,
        "threshold": 12.0,
    },
    "revenue_predictor": {
        "uc_name": "workspace.boxscore_models.revenue_predictor",
        "endpoint": "boxscore-revenue-predictor",
        "primary_metric": "mape",
        "lower_is_better": True,
        "threshold": 18.0,
    },
    "anomaly_detector": {
        "uc_name": "workspace.boxscore_models.anomaly_detector",
        "endpoint": "boxscore-anomaly-detector",
        "primary_metric": "f1",
        "lower_is_better": False,
        "threshold": 0.70,
    },
    "recommendation_engine": {
        "uc_name": "workspace.boxscore_models.recommendation_engine",
        "endpoint": "boxscore-recommendation-engine",
        "primary_metric": "revenue_lift_pct",
        "lower_is_better": False,
        "threshold": 2.0,
    },
}

CHAMPION_METRICS = {
    "demand_forecast": {
        "mape": 8.2, "rmse": 1850, "r2": 0.91, "mae": 1420,
        "confidence_score": 0.88, "version": 1,
    },
    "price_sensitivity": {
        "mape": 6.1, "rmse": 0.045, "r2": 0.93, "mae": 0.031,
        "confidence_score": 0.91, "version": 1,
    },
    "revenue_predictor": {
        "mape": 12.4, "rmse": 85000, "r2": 0.84, "mae": 62000,
        "confidence_score": 0.82, "version": 1,
    },
    "anomaly_detector": {
        "precision": 0.89, "recall": 0.82, "f1": 0.85,
        "confidence_score": 0.86, "version": 1,
    },
    "recommendation_engine": {
        "revenue_lift_pct": 4.7, "acceptance_rate": 0.72, "avg_confidence": 0.81,
        "confidence_score": 0.84, "version": 1,
    },
}

CHALLENGER_METRICS = {
    "demand_forecast": {
        "mape": 7.5, "rmse": 1680, "r2": 0.93, "mae": 1280,
        "confidence_score": 0.91, "version": 2,
        "features_added": ["rolling_30d_page_views", "weather_index", "promo_engagement_score"],
        "features_removed": [],
    },
    "price_sensitivity": {
        "mape": 5.4, "rmse": 0.038, "r2": 0.95, "mae": 0.026,
        "confidence_score": 0.93, "version": 2,
        "features_added": ["competitor_resale_premium", "loyalty_tier_factor"],
        "features_removed": ["legacy_price_bucket"],
    },
    "revenue_predictor": {
        "mape": 10.8, "rmse": 72000, "r2": 0.87, "mae": 54000,
        "confidence_score": 0.85, "version": 2,
        "features_added": ["concessions_forecast", "parking_revenue_proxy"],
        "features_removed": [],
    },
    "anomaly_detector": {
        "precision": 0.92, "recall": 0.85, "f1": 0.88,
        "confidence_score": 0.89, "version": 2,
        "features_added": ["social_sentiment_spike"],
        "features_removed": ["manual_flag_count"],
    },
    "recommendation_engine": {
        "revenue_lift_pct": 5.3, "acceptance_rate": 0.78, "avg_confidence": 0.85,
        "confidence_score": 0.87, "version": 2,
        "features_added": ["demand_ensemble_v2_output", "inventory_urgency_score"],
        "features_removed": [],
    },
}


class PromotionRequest(BaseModel):
    model_name: str
    action: str  # "accept" or "reject"
    reason: Optional[str] = None


def _compute_comparison(model_name: str) -> dict:
    config = MODEL_CONFIGS[model_name]
    champion = CHAMPION_METRICS[model_name]
    challenger = CHALLENGER_METRICS[model_name]

    primary = config["primary_metric"]
    lower = config["lower_is_better"]
    champ_val = champion.get(primary, 0)
    chall_val = challenger.get(primary, 0)

    if lower:
        improvement = round((champ_val - chall_val) / max(champ_val, 0.001) * 100, 1)
        challenger_wins = chall_val < champ_val
    else:
        improvement = round((chall_val - champ_val) / max(champ_val, 0.001) * 100, 1)
        challenger_wins = chall_val > champ_val

    shared_metrics = set(champion.keys()) & set(challenger.keys()) - {"version", "confidence_score", "features_added", "features_removed"}
    metric_diffs = {}
    for metric in sorted(shared_metrics):
        c_val = champion[metric]
        ch_val = challenger[metric]
        if isinstance(c_val, (int, float)) and isinstance(ch_val, (int, float)):
            diff = ch_val - c_val
            pct = round(diff / max(abs(c_val), 0.001) * 100, 1) if c_val != 0 else 0
            metric_diffs[metric] = {
                "champion": c_val,
                "challenger": ch_val,
                "diff": round(diff, 4),
                "diff_pct": pct,
            }

    return {
        "model_name": model_name,
        "uc_name": config["uc_name"],
        "endpoint": config["endpoint"],
        "primary_metric": primary,
        "improvement_pct": improvement,
        "challenger_wins": challenger_wins,
        "champion": {
            "version": champion["version"],
            "confidence_score": champion.get("confidence_score", 0),
            "metrics": {k: v for k, v in champion.items() if k not in ("version", "confidence_score")},
        },
        "challenger": {
            "version": challenger["version"],
            "confidence_score": challenger.get("confidence_score", 0),
            "metrics": {k: v for k, v in challenger.items() if k not in ("version", "confidence_score", "features_added", "features_removed")},
            "features_added": challenger.get("features_added", []),
            "features_removed": challenger.get("features_removed", []),
        },
        "metric_diffs": metric_diffs,
        "threshold": config["threshold"],
        "meets_threshold": (chall_val < config["threshold"]) if lower else (chall_val > config["threshold"]),
    }


@router.get("/compare")
async def compare_all():
    """Get champion vs challenger comparison for all models."""
    comparisons = []
    for model_name in MODEL_CONFIGS:
        comp = _compute_comparison(model_name)
        prev = _evaluations.get(model_name)
        comp["evaluation_status"] = prev["action"] if prev else "pending"
        comparisons.append(comp)

    return {
        "comparisons": comparisons,
        "summary": {
            "total_models": len(comparisons),
            "challengers_winning": sum(1 for c in comparisons if c["challenger_wins"]),
            "promoted": sum(1 for c in comparisons if c["evaluation_status"] == "accept"),
            "rejected": sum(1 for c in comparisons if c["evaluation_status"] == "reject"),
            "pending": sum(1 for c in comparisons if c["evaluation_status"] == "pending"),
        },
        "auth_mode": dbc.get_auth_mode(),
    }


@router.get("/compare/{model_name}")
async def compare_one(model_name: str):
    """Get detailed champion vs challenger for one model."""
    if model_name not in MODEL_CONFIGS:
        return {"error": f"Model '{model_name}' not found"}

    comp = _compute_comparison(model_name)
    prev = _evaluations.get(model_name)
    comp["evaluation_status"] = prev["action"] if prev else "pending"
    comp["evaluation_history"] = prev
    return comp


@router.post("/promote")
async def promote_model(req: PromotionRequest):
    """Accept or reject a challenger model. Accept triggers alias swap + endpoint update."""
    if req.model_name not in MODEL_CONFIGS:
        return {"error": f"Model '{req.model_name}' not found"}
    if req.action not in ("accept", "reject"):
        return {"error": "Action must be 'accept' or 'reject'"}

    config = MODEL_CONFIGS[req.model_name]
    challenger = CHALLENGER_METRICS[req.model_name]
    champion = CHAMPION_METRICS[req.model_name]
    timestamp = datetime.utcnow().isoformat() + "Z"

    evaluation = {
        "model_name": req.model_name,
        "action": req.action,
        "reason": req.reason,
        "timestamp": timestamp,
        "champion_version": champion["version"],
        "challenger_version": challenger["version"],
    }

    if req.action == "accept":
        alias_swapped = False
        endpoint_updated = False

        alias_swapped = dbc.set_model_alias(
            config["uc_name"], "champion", challenger["version"]
        )
        if alias_swapped:
            logger.info(f"Swapped champion alias to v{challenger['version']} for {config['uc_name']}")

        endpoint_updated = dbc.update_serving_endpoint(
            config["endpoint"], config["uc_name"], str(challenger["version"])
        )
        if endpoint_updated:
            logger.info(f"Updated serving endpoint {config['endpoint']} to v{challenger['version']}")

        CHAMPION_METRICS[req.model_name] = dict(challenger)
        CHAMPION_METRICS[req.model_name]["version"] = challenger["version"]

        new_challenger_version = challenger["version"] + 1
        CHALLENGER_METRICS[req.model_name]["version"] = new_challenger_version

        evaluation["alias_swapped"] = alias_swapped
        evaluation["endpoint_updated"] = endpoint_updated
        evaluation["new_champion_version"] = challenger["version"]

        _promotion_history.append(evaluation)
        _evaluations[req.model_name] = evaluation

        return {
            "status": "promoted",
            "model_name": req.model_name,
            "new_champion_version": challenger["version"],
            "alias_swapped": alias_swapped,
            "endpoint_updated": endpoint_updated,
            "message": f"Challenger v{challenger['version']} promoted to champion for {req.model_name}",
            "timestamp": timestamp,
        }

    else:
        evaluation["alias_swapped"] = False
        evaluation["endpoint_updated"] = False
        _evaluations[req.model_name] = evaluation
        _promotion_history.append(evaluation)

        return {
            "status": "rejected",
            "model_name": req.model_name,
            "message": f"Challenger rejected for {req.model_name} — champion v{champion['version']} retained",
            "reason": req.reason,
            "timestamp": timestamp,
        }


@router.get("/history")
async def promotion_history():
    """Get the full promotion history."""
    return {
        "history": list(reversed(_promotion_history)),
        "total_promotions": sum(1 for h in _promotion_history if h["action"] == "accept"),
        "total_rejections": sum(1 for h in _promotion_history if h["action"] == "reject"),
    }
