import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

router = APIRouter(prefix="/api/ai", tags=["async-ai"])


class RequestType(str, Enum):
    PERFORMANCE_INSIGHT = "performance_insight"
    DEMAND_ANALYSIS = "demand_analysis"
    PRICING_RECOMMENDATION = "pricing_recommendation"


class RequestStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


_ai_requests: dict = {}


class AIRequest(BaseModel):
    request_type: RequestType
    payload: dict
    title: str


MOCK_INSIGHTS = {
    RequestType.PERFORMANCE_INSIGHT: (
        "## Performance Insight\n\n"
        "**Revenue is trending 4.7% above forecast** for the current homestand. "
        "Key drivers:\n\n"
        "- Dodgers series sold out 48 hours earlier than projected\n"
        "- Dynamic pricing captured an additional **$12.40 per ticket** in Field Club\n"
        "- Secondary market premium averaged **1.8x** face value for premium sections\n\n"
        "**Recommendation**: Consider releasing masked inventory in View Reserve "
        "for the upcoming Padres series — demand signals suggest 15% higher traffic."
    ),
    RequestType.DEMAND_ANALYSIS: (
        "## Demand Analysis\n\n"
        "The next 5 home games show a **mixed demand profile**:\n\n"
        "| Game | Opponent | Projected Fill | Risk |\n"
        "|------|----------|---------------|------|\n"
        "| Sep 26 | Dodgers | 99.5% | Low |\n"
        "| Sep 27 | Dodgers | 96.2% | Low |\n"
        "| Sep 28 | Dodgers | 94.8% | Low |\n"
        "| Sep 30 | Rockies | 71.3% | **High** |\n"
        "| Oct 1 | Rockies | 68.9% | **High** |\n\n"
        "**Action needed**: Rockies games are under-indexing. Consider activating "
        "promotional pricing for Bleachers and Gallery sections."
    ),
    RequestType.PRICING_RECOMMENDATION: (
        "## Pricing Recommendation\n\n"
        "Based on current demand signals and inventory position:\n\n"
        "**Increase** (high confidence):\n"
        "- Field Club: $350 → $385 (+10%) — demand exceeds supply by 2.3x\n"
        "- Club Level Infield: $180 → $195 (+8.3%) — sell-through at 92%\n\n"
        "**Hold** (medium confidence):\n"
        "- Lower Box sections: current pricing aligned with demand\n\n"
        "**Decrease** (medium confidence):\n"
        "- Gallery: $25 → $22 (-12%) — sell-through only 58%\n"
        "- Arcade: $28 → $24 (-14%) — inventory excess for midweek games\n\n"
        "**Estimated revenue impact**: +$47,200 per game if all recommendations adopted."
    ),
}


async def process_ai_request(request_id: str):
    if request_id not in _ai_requests:
        return

    data = _ai_requests[request_id]
    data["status"] = RequestStatus.PROCESSING

    await asyncio.sleep(2)

    try:
        result = MOCK_INSIGHTS.get(
            data["type"],
            "Analysis complete. No significant anomalies detected.",
        )
        data["status"] = RequestStatus.COMPLETED
        data["result"] = {
            "content": result,
            "model": "databricks-meta-llama-4-maverick",
            "fallback": False,
        }
        data["completed_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as e:
        data["status"] = RequestStatus.FAILED
        data["error"] = str(e)
        data["completed_at"] = datetime.now(timezone.utc).isoformat()


@router.post("/async/submit")
async def submit_request(request: AIRequest, background_tasks: BackgroundTasks):
    request_id = str(uuid.uuid4())[:8]

    _ai_requests[request_id] = {
        "id": request_id,
        "type": request.request_type,
        "title": request.title,
        "payload": request.payload,
        "status": RequestStatus.PENDING,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "result": None,
        "error": None,
        "seen": False,
    }

    background_tasks.add_task(process_ai_request, request_id)

    return {
        "status": "success",
        "data": {
            "request_id": request_id,
            "status": RequestStatus.PENDING,
            "title": request.title,
        },
    }


@router.get("/async/pending")
async def get_pending():
    pending = []
    ready = []

    for data in _ai_requests.values():
        entry = {
            "id": data["id"],
            "type": data["type"],
            "title": data["title"],
            "status": data["status"],
            "created_at": data["created_at"],
        }
        if data["status"] in (RequestStatus.PENDING, RequestStatus.PROCESSING):
            pending.append(entry)
        elif data["status"] == RequestStatus.COMPLETED and not data["seen"]:
            entry["completed_at"] = data["completed_at"]
            ready.append(entry)

    return {
        "status": "success",
        "data": {
            "pending_count": len(pending),
            "ready_count": len(ready),
            "pending": pending,
            "ready": ready,
            "total_unseen": len(pending) + len(ready),
        },
    }


@router.get("/async/result/{request_id}")
async def get_result(request_id: str):
    if request_id not in _ai_requests:
        return {"status": "error", "message": f"Request {request_id} not found"}

    data = _ai_requests[request_id]
    data["seen"] = True

    if data["status"] != RequestStatus.COMPLETED:
        return {"status": "pending", "data": {"status": data["status"]}}

    return {
        "status": "success",
        "data": {
            "id": data["id"],
            "result": data["result"],
            "completed_at": data["completed_at"],
        },
    }
