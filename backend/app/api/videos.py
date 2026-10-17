import os
import uuid
import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models import Camera, VideoJob
from app.core.config import settings
from app.services.job_service import start_processing_job

logger = logging.getLogger("citytrack.api.videos")

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
MAX_FILE_SIZE_MB = 2048  # 2 GB

router = APIRouter(tags=["Videos & Jobs"])


@router.post("/videos/upload")
async def upload_video(
    camera_id: int = Form(...),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    # Validate camera exists
    cam = (await db.execute(select(Camera).where(Camera.id == camera_id))).scalar_one_or_none()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")

    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Safe filename — no path traversal
    safe_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(settings.UPLOAD_DIR, safe_name)

    # Stream to disk with size check
    total_bytes = 0
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    try:
        with open(dest_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1 MB chunks
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    os.remove(dest_path)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds {MAX_FILE_SIZE_MB} MB limit.",
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    # Create job record
    job = VideoJob(
        camera_id=camera_id,
        filename=file.filename or safe_name,
        file_path=dest_path,
        status="PENDING",
        progress=0.0,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    logger.info("Video uploaded for camera %d, job_id=%d, path=%s", camera_id, job.id, dest_path)
    return {
        "job_id": job.id,
        "camera_id": camera_id,
        "filename": job.filename,
        "status": job.status,
        "message": "Upload successful. Start processing via POST /api/process.",
    }


@router.post("/process")
async def start_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    job = (await db.execute(select(VideoJob).where(VideoJob.id == job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status in ("PROCESSING", "COMPLETED"):
        raise HTTPException(
            status_code=409,
            detail=f"Job is already in status '{job.status}'.",
        )
    background_tasks.add_task(start_processing_job, job_id)
    return {"job_id": job_id, "status": "PROCESSING", "message": "Processing started in background."}


@router.get("/jobs/{job_id}")
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job = (await db.execute(select(VideoJob).where(VideoJob.id == job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    processed_video_url = None
    if job.processed_video_path and os.path.isfile(job.processed_video_path):
        processed_video_url = f"/api/files/processed/{os.path.basename(job.processed_video_path)}"
    return {
        "id": job.id,
        "camera_id": job.camera_id,
        "filename": job.filename,
        "status": job.status,
        "progress": job.progress,
        "total_frames": job.total_frames,
        "processed_frames": job.processed_frames,
        "fps": job.fps,
        "duration_seconds": job.duration_seconds,
        "total_vehicles_detected": job.total_vehicles_detected,
        "total_plates_recognized": job.total_plates_recognized,
        "processed_video_url": processed_video_url,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.get("/jobs")
async def list_jobs(
    camera_id: int | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    q = select(VideoJob).order_by(VideoJob.created_at.desc()).limit(limit)
    if camera_id:
        q = q.where(VideoJob.camera_id == camera_id)
    jobs = (await db.execute(q)).scalars().all()
    return [
        {
            "id": j.id,
            "camera_id": j.camera_id,
            "filename": j.filename,
            "status": j.status,
            "progress": j.progress,
            "total_vehicles_detected": j.total_vehicles_detected,
            "total_plates_recognized": j.total_plates_recognized,
            "created_at": j.created_at.isoformat(),
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        }
        for j in jobs
    ]
