import os
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models import VehicleDetection, PlateObservation, Camera
from app.core.config import settings

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


def _plate_url(crop_path: Optional[str]) -> Optional[str]:
    if not crop_path or not os.path.isfile(crop_path):
        return None
    return f"/api/files/crops/{os.path.basename(crop_path)}"


@router.get("")
async def list_vehicles(
    camera_id: Optional[int] = None,
    vehicle_class: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(VehicleDetection)
        .order_by(VehicleDetection.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )
    if camera_id:
        q = q.where(VehicleDetection.camera_id == camera_id)
    if vehicle_class:
        q = q.where(VehicleDetection.vehicle_class == vehicle_class)

    dets = (await db.execute(q)).scalars().all()

    # Fetch cameras for code lookup
    cam_res = await db.execute(select(Camera))
    cam_map = {c.id: c for c in cam_res.scalars().all()}

    results = []
    for det in dets:
        cam = cam_map.get(det.camera_id)
        plate = det.plate_observation
        results.append({
            "id": det.id,
            "camera_id": det.camera_id,
            "camera_code": cam.camera_code if cam else None,
            "camera_name": cam.name if cam else None,
            "tracking_id": det.tracking_id,
            "frame_number": det.frame_number,
            "timestamp": det.timestamp.isoformat(),
            "vehicle_class": det.vehicle_class,
            "confidence": det.confidence,
            "bbox": [det.bbox_x1, det.bbox_y1, det.bbox_x2, det.bbox_y2],
            "dominant_color": det.dominant_color,
            "plate": {
                "normalized_plate": plate.normalized_plate,
                "is_valid_format": plate.is_valid_format,
                "ocr_confidence": plate.ocr_confidence,
                "state_code": plate.state_code,
                "crop_url": _plate_url(plate.crop_path),
            } if plate else None,
        })
    return results


@router.get("/search")
async def search_vehicles(
    plate_query: Optional[str] = None,
    vehicle_class: Optional[str] = None,
    camera_id: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if vehicle_class:
        filters.append(VehicleDetection.vehicle_class == vehicle_class)
    if camera_id:
        filters.append(VehicleDetection.camera_id == camera_id)
    if start_time:
        filters.append(VehicleDetection.timestamp >= start_time)
    if end_time:
        filters.append(VehicleDetection.timestamp <= end_time)

    if plate_query:
        normalized_q = plate_query.upper().replace(" ", "").replace("-", "")
        plate_ids_res = await db.execute(
            select(PlateObservation.detection_id)
            .where(PlateObservation.normalized_plate.contains(normalized_q))
        )
        matching_det_ids = [r[0] for r in plate_ids_res.all() if r[0]]
        if not matching_det_ids:
            return {"results": [], "total": 0}
        filters.append(VehicleDetection.id.in_(matching_det_ids))

    q = (
        select(VehicleDetection)
        .where(and_(*filters) if filters else True)
        .order_by(VehicleDetection.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )
    dets = (await db.execute(q)).scalars().all()
    total_q = select(func.count()).select_from(VehicleDetection).where(and_(*filters) if filters else True)
    total = (await db.execute(total_q)).scalar() or 0

    cam_res = await db.execute(select(Camera))
    cam_map = {c.id: c for c in cam_res.scalars().all()}

    results = []
    for det in dets:
        cam = cam_map.get(det.camera_id)
        plate = det.plate_observation
        results.append({
            "id": det.id,
            "camera_id": det.camera_id,
            "camera_code": cam.camera_code if cam else None,
            "camera_name": cam.name if cam else None,
            "tracking_id": det.tracking_id,
            "timestamp": det.timestamp.isoformat(),
            "vehicle_class": det.vehicle_class,
            "confidence": det.confidence,
            "dominant_color": det.dominant_color,
            "plate": {
                "normalized_plate": plate.normalized_plate if settings.MASK_PLATES_ON_DISPLAY else plate.normalized_plate,
                "is_valid_format": plate.is_valid_format,
                "ocr_confidence": plate.ocr_confidence,
                "state_code": plate.state_code,
                "crop_url": _plate_url(plate.crop_path),
            } if plate else None,
        })
    return {"results": results, "total": total, "limit": limit, "offset": offset}


@router.get("/{vehicle_id}/trajectory")
async def get_vehicle_trajectory(vehicle_id: int, db: AsyncSession = Depends(get_db)):
    from app.models import VehicleTrajectory, CrossCameraMatch
    traj = (await db.execute(
        select(VehicleTrajectory).where(VehicleTrajectory.id == vehicle_id)
    )).scalar_one_or_none()
    if not traj:
        raise HTTPException(status_code=404, detail="Trajectory not found.")

    matches_res = await db.execute(
        select(CrossCameraMatch).where(CrossCameraMatch.trajectory_id == traj.id)
        .order_by(CrossCameraMatch.from_time)
    )
    matches = matches_res.scalars().all()

    return {
        "id": traj.id,
        "global_vehicle_id": traj.global_vehicle_id,
        "primary_plate": traj.primary_plate,
        "vehicle_class": traj.vehicle_class,
        "dominant_color": traj.dominant_color,
        "first_seen_camera_id": traj.first_seen_camera_id,
        "first_seen_camera_code": traj.first_seen_camera_code,
        "first_seen_time": traj.first_seen_time.isoformat(),
        "last_seen_camera_id": traj.last_seen_camera_id,
        "last_seen_camera_code": traj.last_seen_camera_code,
        "last_seen_time": traj.last_seen_time.isoformat(),
        "total_cameras_count": traj.total_cameras_count,
        "total_detections_count": traj.total_detections_count,
        "match_method": traj.match_method,
        "overall_match_confidence": traj.overall_match_confidence,
        "is_cross_camera": traj.is_cross_camera,
        "is_trajectory_complete": traj.is_trajectory_complete,
        "checkpoints": traj.checkpoints,
        "matches": [
            {
                "id": m.id,
                "from_camera_id": m.from_camera_id,
                "from_camera_code": m.from_camera_code,
                "to_camera_id": m.to_camera_id,
                "to_camera_code": m.to_camera_code,
                "from_time": m.from_time.isoformat(),
                "to_time": m.to_time.isoformat(),
                "transit_duration_seconds": m.transit_duration_seconds,
                "match_method": m.match_method,
                "match_confidence": m.match_confidence,
                "is_spatially_plausible": m.is_spatially_plausible,
            }
            for m in matches
        ],
    }


@router.get("/trajectories")
async def list_trajectories(
    is_cross_camera: Optional[bool] = None,
    plate_query: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    from app.models import VehicleTrajectory
    filters = []
    if is_cross_camera is not None:
        filters.append(VehicleTrajectory.is_cross_camera == is_cross_camera)
    if plate_query:
        normalized_q = plate_query.upper().replace(" ", "").replace("-", "")
        filters.append(VehicleTrajectory.primary_plate.contains(normalized_q))

    q = (
        select(VehicleTrajectory)
        .where(and_(*filters) if filters else True)
        .order_by(VehicleTrajectory.first_seen_time.desc())
        .limit(limit)
        .offset(offset)
    )
    trajs = (await db.execute(q)).scalars().all()
    total = (await db.execute(
        select(func.count()).select_from(VehicleTrajectory)
        .where(and_(*filters) if filters else True)
    )).scalar() or 0

    return {
        "results": [
            {
                "id": t.id,
                "global_vehicle_id": t.global_vehicle_id,
                "primary_plate": t.primary_plate,
                "vehicle_class": t.vehicle_class,
                "dominant_color": t.dominant_color,
                "first_seen_camera_code": t.first_seen_camera_code,
                "first_seen_time": t.first_seen_time.isoformat(),
                "last_seen_camera_code": t.last_seen_camera_code,
                "last_seen_time": t.last_seen_time.isoformat(),
                "total_cameras_count": t.total_cameras_count,
                "match_method": t.match_method,
                "overall_match_confidence": t.overall_match_confidence,
                "is_cross_camera": t.is_cross_camera,
                "checkpoints": t.checkpoints,
            }
            for t in trajs
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
