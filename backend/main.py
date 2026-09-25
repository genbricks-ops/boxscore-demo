import os
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from routers import health, data, models, scoring, genie, async_ai

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("boxscore")

app = FastAPI(
    title="Boxscore Demo",
    description="Commercial Decision Platform — Ticket Pricing, Inventory & Demand Forecasting",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(data.router)
app.include_router(models.router)
app.include_router(scoring.router)
app.include_router(genie.router)
app.include_router(async_ai.router)

STATIC_DIR = Path(__file__).parent / "static"


@app.on_event("startup")
async def startup():
    env = os.getenv("ENV", "development")
    logger.info(f"Boxscore Demo starting — env={env}")
    if STATIC_DIR.exists():
        logger.info(f"Serving static files from {STATIC_DIR}")
    else:
        logger.warning("Static directory not found — run 'python build.py' first for production")


if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{full_path:path}")
async def serve_spa(request: Request, full_path: str):
    if full_path.startswith("api/"):
        return {"detail": "Not Found"}

    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "Boxscore Demo API — frontend not built yet. Run 'python build.py'."}
