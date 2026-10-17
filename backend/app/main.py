"""
FastAPI main application entry point for CityTrack AI.
"""
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.database.session import engine, Base
from app.models import (  # noqa: F401 — import all models so Base knows them
    Camera, VideoJob, VehicleDetection, PlateObservation,
    VehicleTrajectory, CrossCameraMatch, CongestionRecord, AuditLog,
)
from app.api import health, cameras, videos, vehicles, analytics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("citytrack.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────
    logger.info("CityTrack AI starting up…")

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified.")

    # Seed demo data if enabled
    if settings.ENABLE_DEMO_DATA:
        from app.database.session import AsyncSessionLocal
        from app.services.demo_seeder import seed_demo_data
        async with AsyncSessionLocal() as db:
            await seed_demo_data(db)

    # Pre-load vehicle model (plate model and OCR load lazily on first job)
    from app.vision.processor import ModelManager
    mgr = ModelManager.get()
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, mgr.load_vehicle_model, settings.VEHICLE_MODEL_PATH)
    await loop.run_in_executor(None, mgr.load_plate_model, settings.PLATE_MODEL_PATH)
    await loop.run_in_executor(None, mgr.load_ocr)

    logger.info("Model status: %s", mgr.status)
    yield

    # ── Shutdown ─────────────────────────────────────────────────────
    await engine.dispose()
    logger.info("CityTrack AI shut down.")


app = FastAPI(
    title="CityTrack AI",
    description=(
        "City-Wide AI Engine for Multi-Camera ANPR, "
        "Trajectory Tracking and Urban Traffic Analytics — SIH26127"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ───────────────────────────────────────────────────────
PREFIX = "/api"
app.include_router(health.router, prefix=PREFIX)
app.include_router(cameras.router, prefix=PREFIX)
app.include_router(videos.router, prefix=PREFIX)
app.include_router(vehicles.router, prefix=PREFIX)
app.include_router(analytics.router, prefix=PREFIX)

# ── Static file serving (plate crops, processed videos) ──────────────
os.makedirs(settings.PLATE_CROPS_DIR, exist_ok=True)
os.makedirs(settings.PROCESSED_DIR, exist_ok=True)

app.mount(
    "/api/files/crops",
    StaticFiles(directory=settings.PLATE_CROPS_DIR),
    name="plate_crops",
)
app.mount(
    "/api/files/processed",
    StaticFiles(directory=settings.PROCESSED_DIR),
    name="processed_videos",
)


@app.get("/")
async def root():
    return {
        "service": "CityTrack AI Backend",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }
