"""
Analytics service — queries the database for traffic summaries,
charts, camera metrics, and congestion data.
Returns plain dicts that the API serialises.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    VehicleDetection, PlateObservation,
    VehicleTrajectory, CongestionRecord, Camera, VideoJob,
)


async def get_summary(db: AsyncSession) -> Dict[str, Any]:
    total_det = (await db.execute(select(func.count()).select_from(VehicleDetection))).scalar() or 0
    total_traj = (await db.execute(select(func.count()).select_from(VehicleTrajectory))).scalar() or 0
    cross_cam = (await db.execute(
        select(func.count()).select_from(VehicleTrajectory)
        .where(VehicleTrajectory.is_cross_camera == True)
    )).scalar() or 0
    total_plates = (await db.execute(
        select(func.count()).select_from(PlateObservation)
        .where(PlateObservation.normalized_plate != None)
    )).scalar() or 0
    active_cameras = (await db.execute(
        select(func.count()).select_from(Camera).where(Camera.status == "ACTIVE")
    )).scalar() or 0

    # Average congestion from latest record per camera
    cong_result = await db.execute(
        select(func.avg(CongestionRecord.congestion_index))
    )
    avg_cong = float(cong_result.scalar() or 0.0)

    return {
        "total_detections": total_det,
        "unique_tracked_vehicles": total_traj,
        "cross_camera_journeys": cross_cam,
        "active_cameras_count": active_cameras,
        "average_congestion_index": round(avg_cong, 1),
        "total_plates_recognized": total_plates,
        "is_demo_data": False,
    }


async def get_traffic_over_time(
    db: AsyncSession,
    hours: int = 24,
) -> List[Dict[str, Any]]:
    since = datetime.utcnow() - timedelta(hours=hours)

    # Group detections by hour using SQLite strftime
    result = await db.execute(
        text("""
        SELECT
            strftime('%Y-%m-%dT%H:00:00', timestamp) AS hour,
            COUNT(*) AS total,
            SUM(CASE WHEN vehicle_class='car' THEN 1 ELSE 0 END) AS cars,
            SUM(CASE WHEN vehicle_class='motorcycle' THEN 1 ELSE 0 END) AS motorcycles,
            SUM(CASE WHEN vehicle_class='bus' THEN 1 ELSE 0 END) AS buses,
            SUM(CASE WHEN vehicle_class='truck' THEN 1 ELSE 0 END) AS trucks
        FROM vehicle_detections
        WHERE timestamp >= :since
        GROUP BY hour
        ORDER BY hour ASC
        """),
        {"since": since.isoformat()},
    )
    rows = result.fetchall()
    return [
        {
            "hour": r[0],
            "volume": r[1],
            "cars": r[2],
            "motorcycles": r[3],
            "buses": r[4],
            "trucks": r[5],
        }
        for r in rows
    ]


async def get_vehicle_class_distribution(db: AsyncSession) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(VehicleDetection.vehicle_class, func.count().label("cnt"))
        .group_by(VehicleDetection.vehicle_class)
        .order_by(func.count().desc())
    )
    rows = result.all()
    total = sum(r[1] for r in rows) or 1
    return [
        {
            "vehicle_class": r[0],
            "count": r[1],
            "percentage": round(r[1] / total * 100, 1),
        }
        for r in rows
    ]


async def get_camera_metrics(db: AsyncSession) -> List[Dict[str, Any]]:
    cameras_res = await db.execute(select(Camera))
    cameras = cameras_res.scalars().all()
    out = []
    for cam in cameras:
        total_v = (await db.execute(
            select(func.count()).select_from(VehicleDetection)
            .where(VehicleDetection.camera_id == cam.id)
        )).scalar() or 0
        unique_v = (await db.execute(
            select(func.count(VehicleDetection.tracking_id.distinct()))
            .where(VehicleDetection.camera_id == cam.id)
        )).scalar() or 0
        avg_conf = (await db.execute(
            select(func.avg(VehicleDetection.confidence))
            .where(VehicleDetection.camera_id == cam.id)
        )).scalar() or 0.0

        # Latest congestion record
        cong_res = await db.execute(
            select(CongestionRecord)
            .where(CongestionRecord.camera_id == cam.id)
            .order_by(CongestionRecord.timestamp.desc())
            .limit(1)
        )
        cong = cong_res.scalar_one_or_none()
        out.append({
            "camera_id": cam.id,
            "camera_code": cam.camera_code,
            "camera_name": cam.name,
            "latitude": cam.latitude,
            "longitude": cam.longitude,
            "total_vehicles": total_v,
            "unique_vehicles": unique_v,
            "congestion_level": cong.congestion_level if cong else "LOW",
            "congestion_index": round(cong.congestion_index if cong else 0.0, 1),
            "avg_confidence": round(float(avg_conf), 3),
        })
    return out


async def get_congestion_heatmap(db: AsyncSession) -> List[Dict[str, Any]]:
    cameras_res = await db.execute(select(Camera))
    cameras = cameras_res.scalars().all()
    out = []
    for cam in cameras:
        cong_res = await db.execute(
            select(CongestionRecord)
            .where(CongestionRecord.camera_id == cam.id)
            .order_by(CongestionRecord.timestamp.desc())
            .limit(1)
        )
        cong = cong_res.scalar_one_or_none()
        vol = (await db.execute(
            select(func.count()).select_from(VehicleDetection)
            .where(VehicleDetection.camera_id == cam.id)
        )).scalar() or 0
        out.append({
            "camera_id": cam.id,
            "camera_code": cam.camera_code,
            "camera_name": cam.name,
            "latitude": cam.latitude,
            "longitude": cam.longitude,
            "congestion_index": round(cong.congestion_index if cong else 0.0, 1),
            "congestion_level": cong.congestion_level if cong else "LOW",
            "current_volume": vol,
        })
    return out


async def get_transition_matrix(db: AsyncSession) -> List[Dict[str, Any]]:
    from app.models import CrossCameraMatch
    result = await db.execute(
        select(
            CrossCameraMatch.from_camera_code,
            CrossCameraMatch.to_camera_code,
            func.count().label("vehicle_count"),
            func.avg(CrossCameraMatch.transit_duration_seconds).label("avg_transit"),
        )
        .group_by(CrossCameraMatch.from_camera_code, CrossCameraMatch.to_camera_code)
    )
    rows = result.all()
    return [
        {
            "from_camera_code": r[0],
            "to_camera_code": r[1],
            "vehicle_count": r[2],
            "avg_transit_minutes": round((r[3] or 0) / 60, 1),
        }
        for r in rows
    ]
