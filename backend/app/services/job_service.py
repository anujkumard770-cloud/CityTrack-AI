"""
Background job service — runs video processing in a thread pool,
writes results to the database incrementally, then triggers trajectory matching.
"""
import asyncio
import logging
import json
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.models import (
    Camera, VideoJob, VehicleDetection, PlateObservation,
    VehicleTrajectory, CrossCameraMatch, CongestionRecord,
)
from app.vision.processor import VideoProcessor, ModelManager
from app.vision.matcher import build_trajectories
from app.core.config import settings

logger = logging.getLogger("citytrack.job_service")

_executor = ThreadPoolExecutor(max_workers=2)
_active_jobs: Dict[int, bool] = {}  # job_id -> is_running


def _congestion_level(index: float) -> str:
    if index < 25:
        return "LOW"
    elif index < 50:
        return "MODERATE"
    elif index < 75:
        return "HIGH"
    return "SEVERE"


async def _init_models() -> ModelManager:
    """Load models once (singleton pattern)."""
    mgr = ModelManager.get()
    if not mgr._vehicle_model_ok:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, mgr.load_vehicle_model, settings.VEHICLE_MODEL_PATH
        )
    if not mgr._plate_model_ok:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, mgr.load_plate_model, settings.PLATE_MODEL_PATH
        )
    if not mgr._ocr_ok:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, mgr.load_ocr)
    return mgr


async def _save_frame_results(frame_results: list, db: AsyncSession):
    """Bulk-insert a batch of frame detection + plate results."""
    for fr in frame_results:
        det = VehicleDetection(
            job_id=fr["job_id"],
            camera_id=fr["camera_id"],
            tracking_id=fr["tracking_id"],
            frame_number=fr["frame_number"],
            timestamp=fr["timestamp"],
            vehicle_class=fr["vehicle_class"],
            confidence=fr["confidence"],
            bbox_x1=fr["bbox_x1"],
            bbox_y1=fr["bbox_y1"],
            bbox_x2=fr["bbox_x2"],
            bbox_y2=fr["bbox_y2"],
            dominant_color=fr.get("dominant_color"),
        )
        db.add(det)
        await db.flush()

        plate = fr.get("plate")
        if plate and plate.get("normalized_plate"):
            po = PlateObservation(
                detection_id=det.id,
                job_id=fr["job_id"],
                camera_id=fr["camera_id"],
                tracking_id=fr["tracking_id"],
                raw_plate_text=plate.get("raw_plate_text"),
                normalized_plate=plate.get("normalized_plate"),
                is_valid_format=plate.get("is_valid_format", False),
                is_readable=plate.get("is_readable", True),
                state_code=plate.get("state_code"),
                plate_confidence=plate.get("plate_confidence", 0.0),
                ocr_confidence=plate.get("ocr_confidence", 0.0),
                crop_path=plate.get("crop_path"),
                timestamp=fr["timestamp"],
            )
            db.add(po)

    await db.commit()


async def _rebuild_trajectories(job: VideoJob, camera: Camera, db: AsyncSession):
    """
    After processing, build per-tracking-ID observation summaries
    and run the cross-camera matcher for this camera's results,
    then insert/update trajectory records.
    """
    # Aggregate best plate per tracking_id in this job
    from sqlalchemy import func
    result = await db.execute(
        select(
            VehicleDetection.tracking_id,
            VehicleDetection.vehicle_class,
            VehicleDetection.dominant_color,
            func.min(VehicleDetection.timestamp).label("first_seen"),
            func.max(VehicleDetection.timestamp).label("last_seen"),
        )
        .where(VehicleDetection.job_id == job.id)
        .group_by(
            VehicleDetection.tracking_id,
            VehicleDetection.vehicle_class,
            VehicleDetection.dominant_color,
        )
    )
    tracking_rows = result.all()

    # Best plate per tracking_id
    plate_result = await db.execute(
        select(PlateObservation)
        .where(PlateObservation.job_id == job.id)
        .order_by(PlateObservation.ocr_confidence.desc())
    )
    all_plates = plate_result.scalars().all()
    best_plates: Dict[int, PlateObservation] = {}
    for po in all_plates:
        if po.tracking_id not in best_plates:
            best_plates[po.tracking_id] = po

    observations = []
    for row in tracking_rows:
        plate_obs = best_plates.get(row.tracking_id)
        observations.append({
            "camera_id": camera.id,
            "camera_code": camera.camera_code,
            "camera_name": camera.name,
            "latitude": camera.latitude,
            "longitude": camera.longitude,
            "tracking_id": row.tracking_id,
            "vehicle_class": row.vehicle_class,
            "dominant_color": row.dominant_color,
            "normalized_plate": plate_obs.normalized_plate if plate_obs else None,
            "ocr_confidence": plate_obs.ocr_confidence if plate_obs else 0.0,
            "first_seen_time": row.first_seen,
            "last_seen_time": row.last_seen,
            "crop_path": plate_obs.crop_path if plate_obs else None,
        })

    # Build trajectories for this camera's observations only
    # (cross-camera matching can be triggered separately)
    transit_rules = {camera.camera_code: camera.transit_rules}
    trajectories = build_trajectories(observations, transit_rules)

    for traj in trajectories:
        t = VehicleTrajectory(
            global_vehicle_id=traj["global_vehicle_id"],
            primary_plate=traj.get("primary_plate"),
            vehicle_class=traj["vehicle_class"],
            dominant_color=traj.get("dominant_color"),
            first_seen_camera_id=traj["first_seen_camera_id"],
            first_seen_camera_code=traj.get("first_seen_camera_code"),
            first_seen_time=traj["first_seen_time"],
            last_seen_camera_id=traj["last_seen_camera_id"],
            last_seen_camera_code=traj.get("last_seen_camera_code"),
            last_seen_time=traj["last_seen_time"],
            total_cameras_count=traj["total_cameras_count"],
            total_detections_count=traj["total_detections_count"],
            match_method=traj["match_method"],
            overall_match_confidence=traj["overall_match_confidence"],
            is_cross_camera=traj["is_cross_camera"],
            is_trajectory_complete=traj["is_trajectory_complete"],
        )
        t.checkpoints = traj["checkpoints"]
        db.add(t)
        await db.flush()

        for m in traj.get("matches", []):
            match = CrossCameraMatch(
                trajectory_id=t.id,
                from_camera_id=m["from_camera_id"],
                from_camera_code=m.get("from_camera_code"),
                to_camera_id=m["to_camera_id"],
                to_camera_code=m.get("to_camera_code"),
                from_time=datetime.fromisoformat(m["from_time"]) if isinstance(m["from_time"], str) else m["from_time"],
                to_time=datetime.fromisoformat(m["to_time"]) if isinstance(m["to_time"], str) else m["to_time"],
                transit_duration_seconds=m["transit_duration_seconds"],
                match_method=m["match_method"],
                match_confidence=m["match_confidence"],
                is_spatially_plausible=m["is_spatially_plausible"],
            )
            db.add(match)

    await db.commit()

    # Congestion record
    total_unique = len(tracking_rows)
    job_dur = job.duration_seconds or 1.0
    flow_rate = (total_unique / job_dur) * 60.0  # vehicles per minute
    cong_index = min(100.0, (flow_rate / 30.0) * 100.0)  # 30 vpm = max
    cong = CongestionRecord(
        camera_id=camera.id,
        timestamp=datetime.utcnow(),
        vehicle_count=total_unique,
        flow_rate_per_min=flow_rate,
        congestion_level=_congestion_level(cong_index),
        congestion_index=cong_index,
    )
    db.add(cong)
    await db.commit()


async def start_processing_job(job_id: int):
    """
    Entry point called by the API. Runs the full pipeline for a job
    in the background, updating status in the database.
    """
    if _active_jobs.get(job_id):
        logger.warning("Job %d is already running", job_id)
        return

    _active_jobs[job_id] = True
    logger.info("Starting processing job %d", job_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            logger.error("Job %d not found", job_id)
            _active_jobs.pop(job_id, None)
            return

        camera_result = await db.execute(select(Camera).where(Camera.id == job.camera_id))
        camera = camera_result.scalar_one_or_none()
        if not camera:
            logger.error("Camera for job %d not found", job_id)
            _active_jobs.pop(job_id, None)
            return

        # Mark PROCESSING
        job.status = "PROCESSING"
        job.progress = 0.0
        await db.commit()

    try:
        models = await _init_models()

        # Collect all frame results in memory (batched to avoid huge lists)
        batch: list = []
        BATCH_SIZE = 200

        async def flush_batch(batch_data: list):
            async with AsyncSessionLocal() as db:
                await _save_frame_results(batch_data, db)

        def on_frame_results(frame_results: list):
            batch.extend(frame_results)

        async def on_progress(pct: float):
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(VideoJob)
                    .where(VideoJob.id == job_id)
                    .values(progress=pct)
                )
                await db.commit()

            if len(batch) >= BATCH_SIZE:
                data = batch.copy()
                batch.clear()
                await flush_batch(data)

        loop = asyncio.get_event_loop()

        # Run blocking processor in thread
        def run_processor():
            nonlocal batch
            proc = VideoProcessor(
                video_path=job.file_path,
                camera_code=camera.camera_code,
                job_id=job.id,
                camera_id=camera.id,
                plate_crops_dir=settings.PLATE_CROPS_DIR,
                models=models,
                confidence_threshold=settings.CONFIDENCE_THRESHOLD,
                plate_confidence_threshold=settings.PLATE_CONFIDENCE_THRESHOLD,
                frame_callback=lambda fr: batch.extend(fr),
                progress_callback=None,  # handled after thread
            )
            return proc.process()

        summary = await loop.run_in_executor(_executor, run_processor)

        # Flush remaining batch
        if batch:
            await flush_batch(batch)
            batch.clear()

        # Update job with summary
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one()
            job.status = "COMPLETED"
            job.progress = 100.0
            job.total_frames = summary["total_frames"]
            job.processed_frames = summary["processed_frames"]
            job.fps = summary["fps"]
            job.duration_seconds = summary["duration_seconds"]
            job.total_vehicles_detected = summary["total_vehicles_detected"]
            job.total_plates_recognized = summary["total_plates_recognized"]
            job.completed_at = datetime.utcnow()
            await db.commit()

            camera_result = await db.execute(select(Camera).where(Camera.id == job.camera_id))
            camera = camera_result.scalar_one()
            await _rebuild_trajectories(job, camera, db)

        logger.info("Job %d completed successfully", job_id)

    except Exception as exc:
        logger.error("Job %d failed: %s\n%s", job_id, exc, traceback.format_exc())
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(VideoJob)
                .where(VideoJob.id == job_id)
                .values(status="FAILED", error_message=str(exc)[:500])
            )
            await db.commit()
    finally:
        _active_jobs.pop(job_id, None)
