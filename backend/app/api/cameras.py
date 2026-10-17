from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database.session import get_db
from app.models import Camera, VehicleDetection
from app.schemas.camera import CameraCreate, CameraUpdate, CameraResponse
from app.models import VideoJob

router = APIRouter(prefix="/cameras", tags=["Cameras"])


def _to_response(cam: Camera, active_jobs: int = 0, total_det: int = 0) -> dict:
    return {
        "id": cam.id,
        "camera_code": cam.camera_code,
        "name": cam.name,
        "location_name": cam.location_name,
        "latitude": cam.latitude,
        "longitude": cam.longitude,
        "ip_stream_url": cam.ip_stream_url,
        "status": cam.status,
        "is_demo": cam.is_demo,
        "connected_cameras": cam.connected_cameras,
        "transit_rules": cam.transit_rules,
        "created_at": cam.created_at.isoformat(),
        "updated_at": cam.updated_at.isoformat(),
        "active_jobs_count": active_jobs,
        "total_detections_count": total_det,
    }


@router.get("", response_model=list)
async def list_cameras(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camera).order_by(Camera.created_at.desc()))
    cameras = result.scalars().all()
    out = []
    for cam in cameras:
        active_j = (await db.execute(
            select(func.count()).select_from(VideoJob)
            .where(VideoJob.camera_id == cam.id, VideoJob.status == "PROCESSING")
        )).scalar() or 0
        det_count = (await db.execute(
            select(func.count()).select_from(VehicleDetection)
            .where(VehicleDetection.camera_id == cam.id)
        )).scalar() or 0
        out.append(_to_response(cam, active_j, det_count))
    return out


@router.post("", status_code=201)
async def create_camera(payload: CameraCreate, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(
        select(Camera).where(Camera.camera_code == payload.camera_code)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Camera code '{payload.camera_code}' already exists.")

    cam = Camera(
        camera_code=payload.camera_code,
        name=payload.name,
        location_name=payload.location_name,
        latitude=payload.latitude,
        longitude=payload.longitude,
        ip_stream_url=payload.ip_stream_url,
        status=payload.status or "ACTIVE",
        is_demo=payload.is_demo or False,
    )
    cam.connected_cameras = payload.connected_cameras or []
    cam.transit_rules = payload.transit_rules or {}
    db.add(cam)
    await db.commit()
    await db.refresh(cam)
    return _to_response(cam)


@router.get("/{camera_id}")
async def get_camera(camera_id: int, db: AsyncSession = Depends(get_db)):
    cam = (await db.execute(select(Camera).where(Camera.id == camera_id))).scalar_one_or_none()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")
    det_count = (await db.execute(
        select(func.count()).select_from(VehicleDetection).where(VehicleDetection.camera_id == cam.id)
    )).scalar() or 0
    return _to_response(cam, total_det=det_count)


@router.patch("/{camera_id}")
async def update_camera(camera_id: int, payload: CameraUpdate, db: AsyncSession = Depends(get_db)):
    cam = (await db.execute(select(Camera).where(Camera.id == camera_id))).scalar_one_or_none()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")
    for field, value in payload.model_dump(exclude_none=True).items():
        if field == "connected_cameras":
            cam.connected_cameras = value
        elif field == "transit_rules":
            cam.transit_rules = value
        else:
            setattr(cam, field, value)
    from datetime import datetime
    cam.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(cam)
    return _to_response(cam)


@router.delete("/{camera_id}", status_code=204)
async def delete_camera(camera_id: int, db: AsyncSession = Depends(get_db)):
    cam = (await db.execute(select(Camera).where(Camera.id == camera_id))).scalar_one_or_none()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")
    await db.delete(cam)
    await db.commit()
