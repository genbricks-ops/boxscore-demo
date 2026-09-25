from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health_check():
    return {
        "status": "healthy",
        "service": "boxscore-demo",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
async def readiness():
    databricks_ok = True
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        w.current_user.me()
    except Exception:
        databricks_ok = False

    return {
        "status": "ready" if databricks_ok else "degraded",
        "checks": {
            "databricks": "connected" if databricks_ok else "unavailable",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
