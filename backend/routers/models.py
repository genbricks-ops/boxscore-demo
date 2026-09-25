import random
from fastapi import APIRouter

router = APIRouter(prefix="/api/models", tags=["models"])

REGISTERED_MODELS = {
    "boxscore-demand-forecast": {
        "model_name": "boxscore-demand-forecast",
        "description": "Prophet + LightGBM ensemble for ticket demand forecasting",
        "latest_version": 5,
        "production_version": 4,
        "stage": "Production",
        "metrics": {"mape": 8.2, "rmse": 1850, "mae": 1420, "r2": 0.91},
        "last_updated": "2026-09-20T14:30:00Z",
        "framework": "lightgbm",
        "features_used": 24,
        "training_rows": 486000,
        "versions": [
            {"version": 5, "stage": "Staging", "mape": 7.8, "rmse": 1720, "created": "2026-09-20"},
            {"version": 4, "stage": "Production", "mape": 8.2, "rmse": 1850, "created": "2026-09-12"},
            {"version": 3, "stage": "Archived", "mape": 9.1, "rmse": 2100, "created": "2026-08-28"},
            {"version": 2, "stage": "Archived", "mape": 10.5, "rmse": 2450, "created": "2026-08-10"},
            {"version": 1, "stage": "Archived", "mape": 14.2, "rmse": 3200, "created": "2026-07-15"},
        ],
    },
    "boxscore-price-sensitivity": {
        "model_name": "boxscore-price-sensitivity",
        "description": "XGBoost regression for price elasticity and willingness-to-pay",
        "latest_version": 3,
        "production_version": 3,
        "stage": "Production",
        "metrics": {"mape": 6.1, "rmse": 0.045, "mae": 0.031, "r2": 0.93},
        "last_updated": "2026-09-18T09:15:00Z",
        "framework": "xgboost",
        "features_used": 18,
        "training_rows": 1240000,
        "versions": [
            {"version": 3, "stage": "Production", "mape": 6.1, "rmse": 0.045, "created": "2026-09-18"},
            {"version": 2, "stage": "Archived", "mape": 7.4, "rmse": 0.058, "created": "2026-08-20"},
            {"version": 1, "stage": "Archived", "mape": 9.8, "rmse": 0.072, "created": "2026-07-22"},
        ],
    },
    "boxscore-revenue-predictor": {
        "model_name": "boxscore-revenue-predictor",
        "description": "LightGBM for total game revenue prediction",
        "latest_version": 4,
        "production_version": 3,
        "stage": "Production",
        "metrics": {"mape": 12.4, "rmse": 85000, "mae": 62000, "r2": 0.84},
        "last_updated": "2026-09-15T11:45:00Z",
        "framework": "lightgbm",
        "features_used": 31,
        "training_rows": 243000,
        "versions": [
            {"version": 4, "stage": "Staging", "mape": 11.1, "rmse": 78000, "created": "2026-09-22"},
            {"version": 3, "stage": "Production", "mape": 12.4, "rmse": 85000, "created": "2026-09-15"},
            {"version": 2, "stage": "Archived", "mape": 15.0, "rmse": 102000, "created": "2026-08-25"},
            {"version": 1, "stage": "Archived", "mape": 18.3, "rmse": 128000, "created": "2026-07-30"},
        ],
    },
    "boxscore-anomaly-detector": {
        "model_name": "boxscore-anomaly-detector",
        "description": "Isolation Forest for demand/price/inventory anomaly detection",
        "latest_version": 2,
        "production_version": 2,
        "stage": "Production",
        "metrics": {"precision": 0.89, "recall": 0.82, "f1": 0.85, "contamination": 0.05},
        "last_updated": "2026-09-22T08:00:00Z",
        "framework": "sklearn",
        "features_used": 15,
        "training_rows": 972000,
        "versions": [
            {"version": 2, "stage": "Production", "precision": 0.89, "recall": 0.82, "created": "2026-09-22"},
            {"version": 1, "stage": "Archived", "precision": 0.78, "recall": 0.75, "created": "2026-08-05"},
        ],
    },
    "boxscore-recommendation-engine": {
        "model_name": "boxscore-recommendation-engine",
        "description": "Ensemble pricing recommendation engine combining demand, elasticity, and inventory signals",
        "latest_version": 3,
        "production_version": 3,
        "stage": "Production",
        "metrics": {"revenue_lift_pct": 4.7, "acceptance_rate": 0.72, "avg_confidence": 0.81},
        "last_updated": "2026-09-21T16:20:00Z",
        "framework": "custom",
        "features_used": 42,
        "training_rows": 648000,
        "versions": [
            {"version": 3, "stage": "Production", "revenue_lift_pct": 4.7, "created": "2026-09-21"},
            {"version": 2, "stage": "Archived", "revenue_lift_pct": 3.2, "created": "2026-08-30"},
            {"version": 1, "stage": "Archived", "revenue_lift_pct": 1.8, "created": "2026-08-01"},
        ],
    },
}


@router.get("")
async def list_models():
    summary = []
    for m in REGISTERED_MODELS.values():
        summary.append({
            "model_name": m["model_name"],
            "description": m["description"],
            "latest_version": m["latest_version"],
            "production_version": m["production_version"],
            "stage": m["stage"],
            "metrics": m["metrics"],
            "framework": m["framework"],
            "last_updated": m["last_updated"],
        })
    return {"models": summary, "count": len(summary)}


@router.get("/{model_name}")
async def get_model(model_name: str):
    model = REGISTERED_MODELS.get(model_name)
    if not model:
        return {"error": f"Model '{model_name}' not found"}
    return {"model": model}


@router.get("/{model_name}/validation")
async def get_validation(model_name: str):
    model = REGISTERED_MODELS.get(model_name)
    if not model:
        return {"error": f"Model '{model_name}' not found"}

    versions = model["versions"]
    champion = next((v for v in versions if v["stage"] == "Production"), versions[0])
    challenger = next((v for v in versions if v["stage"] == "Staging"), None)

    result = {
        "model_name": model_name,
        "champion": {
            "version": champion["version"],
            "stage": champion["stage"],
            "metrics": {k: v for k, v in champion.items() if k not in ("version", "stage", "created")},
            "created": champion["created"],
        },
        "validation_checks": {
            "performance_threshold": {"passed": True, "detail": "MAPE within acceptable range"},
            "stability": {"passed": True, "detail": "Predictions within 2 std of historical range"},
            "fairness": {"passed": True, "detail": "No systematic bias across sections (max bias 3.2%)"},
        },
    }

    if challenger:
        result["challenger"] = {
            "version": challenger["version"],
            "stage": challenger["stage"],
            "metrics": {k: v for k, v in challenger.items() if k not in ("version", "stage", "created")},
            "created": challenger["created"],
        }
        result["comparison"] = "Challenger shows improved metrics — pending full validation"
    else:
        result["challenger"] = None
        result["comparison"] = "No challenger model in staging"

    return result
