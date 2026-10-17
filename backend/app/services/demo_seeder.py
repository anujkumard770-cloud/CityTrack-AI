"""
Demo data seeder — inserts sample cameras, detections, plates, trajectories,
and congestion records that are clearly flagged as synthetic/demo data.
Safe to run multiple times (idempotent via camera_code check).
"""
import uuid
import random
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Camera, VideoJob, VehicleDetection, PlateObservation,
    VehicleTrajectory, CrossCameraMatch, CongestionRecord,
)

logger = logging.getLogger("citytrack.demo")

DEMO_CAMERAS = [
    {
        "camera_code": "DEMO-CAM-01",
        "name": "Connaught Place Junction",
        "location_name": "Connaught Place, New Delhi",
        "latitude": 28.6315,
        "longitude": 77.2167,
        "status": "ACTIVE",
        "is_demo": True,
        "connected_cameras": ["DEMO-CAM-02", "DEMO-CAM-03"],
        "transit_rules": {
            "DEMO-CAM-02": {"min_seconds": 60, "max_seconds": 600, "distance_km": 2.1},
            "DEMO-CAM-03": {"min_seconds": 120, "max_seconds": 900, "distance_km": 3.5},
        },
    },
    {
        "camera_code": "DEMO-CAM-02",
        "name": "India Gate Circle",
        "location_name": "Rajpath, New Delhi",
        "latitude": 28.6129,
        "longitude": 77.2295,
        "status": "ACTIVE",
        "is_demo": True,
        "connected_cameras": ["DEMO-CAM-01", "DEMO-CAM-03"],
        "transit_rules": {
            "DEMO-CAM-01": {"min_seconds": 60, "max_seconds": 600, "distance_km": 2.1},
            "DEMO-CAM-03": {"min_seconds": 90, "max_seconds": 720, "distance_km": 2.8},
        },
    },
    {
        "camera_code": "DEMO-CAM-03",
        "name": "Lodi Road Flyover",
        "location_name": "Lodi Road, New Delhi",
        "latitude": 28.5932,
        "longitude": 77.2248,
        "status": "ACTIVE",
        "is_demo": True,
        "connected_cameras": ["DEMO-CAM-01", "DEMO-CAM-02"],
        "transit_rules": {
            "DEMO-CAM-01": {"min_seconds": 120, "max_seconds": 900, "distance_km": 3.5},
            "DEMO-CAM-02": {"min_seconds": 90, "max_seconds": 720, "distance_km": 2.8},
        },
    },
    {
        "camera_code": "DEMO-CAM-04",
        "name": "Nehru Place Intersection",
        "location_name": "Nehru Place, New Delhi",
        "latitude": 28.5491,
        "longitude": 77.2521,
        "status": "MAINTENANCE",
        "is_demo": True,
        "connected_cameras": [],
        "transit_rules": {},
    },
]

VEHICLE_CLASSES = ["car", "motorcycle", "bus", "truck"]
COLORS = ["white", "black", "grey", "blue", "red", "silver", "yellow"]
STATE_CODES = ["DL", "MH", "HR", "UP", "KA", "RJ", "GJ"]

SAMPLE_PLATES = [
    "DL01AB1234", "DL02CD5678", "MH12XY9010",
    "HR26EF3456", "UP32GH7890", "KA05IJ2345",
    "RJ14KL6789", "DL03MN0123", "MH43OP4567",
    "HR55QR8901",
]


def _rnd_plate():
    sc = random.choice(STATE_CODES)
    d = random.randint(1, 99)
    letters = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=2))
    num = random.randint(1000, 9999)
    return f"{sc}{d:02d}{letters}{num}"


async def seed_demo_data(db: AsyncSession):
    """Insert demo cameras, jobs, detections, plates, trajectories, congestion."""
    # ── Cameras ──────────────────────────────────────────────────────
    existing = (await db.execute(
        select(Camera).where(Camera.is_demo == True)
    )).scalars().all()
    if existing:
        logger.info("Demo data already seeded — skipping.")
        return

    cam_objects = []
    for cd in DEMO_CAMERAS:
        c = Camera(
            camera_code=cd["camera_code"],
            name=cd["name"],
            location_name=cd["location_name"],
            latitude=cd["latitude"],
            longitude=cd["longitude"],
            status=cd["status"],
            is_demo=True,
        )
        c.connected_cameras = cd["connected_cameras"]
        c.transit_rules = cd["transit_rules"]
        db.add(c)
        cam_objects.append(c)
    await db.flush()

    # Use only ACTIVE demo cameras for fake detections
    active_cams = [c for c in cam_objects if c.status == "ACTIVE"]

    # ── Fake VideoJob per camera ─────────────────────────────────────
    now = datetime.utcnow()
    jobs = []
    for cam in active_cams:
        j = VideoJob(
            camera_id=cam.id,
            filename="[DEMO] sample_traffic.mp4",
            file_path="/demo/sample_traffic.mp4",
            status="COMPLETED",
            progress=100.0,
            total_frames=3600,
            processed_frames=1200,
            fps=25.0,
            duration_seconds=144.0,
            total_vehicles_detected=random.randint(60, 150),
            total_plates_recognized=random.randint(20, 60),
            completed_at=now - timedelta(minutes=random.randint(5, 60)),
        )
        db.add(j)
        jobs.append((cam, j))
    await db.flush()

    # ── Detections + Plates ──────────────────────────────────────────
    track_counter = 1
    cam_track_plates = {}  # (cam_id, track_id) -> plate_str

    for cam, job in jobs:
        base_time = now - timedelta(hours=2)
        n_tracks = random.randint(20, 50)
        for _ in range(n_tracks):
            t_id = track_counter
            track_counter += 1
            v_class = random.choice(VEHICLE_CLASSES)
            color = random.choice(COLORS)
            n_frames = random.randint(3, 15)
            plate_str = random.choice(SAMPLE_PLATES + [_rnd_plate(), None, None])

            for fi in range(n_frames):
                ts = base_time + timedelta(seconds=random.randint(0, 7200))
                det = VehicleDetection(
                    job_id=job.id,
                    camera_id=cam.id,
                    tracking_id=t_id,
                    frame_number=fi * 3,
                    timestamp=ts,
                    vehicle_class=v_class,
                    confidence=round(random.uniform(0.55, 0.97), 3),
                    bbox_x1=random.uniform(50, 400),
                    bbox_y1=random.uniform(50, 300),
                    bbox_x2=random.uniform(450, 800),
                    bbox_y2=random.uniform(350, 600),
                    dominant_color=color,
                )
                db.add(det)
                await db.flush()

                # Add plate on first frame only
                if fi == 0 and plate_str:
                    cam_track_plates[(cam.id, t_id)] = plate_str
                    po = PlateObservation(
                        detection_id=det.id,
                        job_id=job.id,
                        camera_id=cam.id,
                        tracking_id=t_id,
                        raw_plate_text=plate_str.replace("", " "),
                        normalized_plate=plate_str,
                        is_valid_format=True,
                        is_readable=True,
                        state_code=plate_str[:2],
                        plate_confidence=round(random.uniform(0.6, 0.95), 3),
                        ocr_confidence=round(random.uniform(0.65, 0.92), 3),
                        timestamp=ts,
                    )
                    db.add(po)

    await db.flush()

    # ── Trajectories (cross-camera for shared plates) ────────────────
    # Find plates appearing on >1 camera
    plate_to_cams = {}
    for (cam_id, t_id), plate in cam_track_plates.items():
        plate_to_cams.setdefault(plate, []).append((cam_id, t_id))

    cam_map = {c.id: c for c in cam_objects}

    for plate, entries in plate_to_cams.items():
        if len(entries) < 2:
            # Single-camera trajectory
            cam_id, t_id = entries[0]
            cam = cam_map.get(cam_id)
            if not cam:
                continue
            ts = now - timedelta(minutes=random.randint(10, 120))
            t = VehicleTrajectory(
                global_vehicle_id=f"TRAJ-{uuid.uuid4().hex[:12].upper()}",
                primary_plate=plate,
                vehicle_class=random.choice(VEHICLE_CLASSES),
                dominant_color=random.choice(COLORS),
                first_seen_camera_id=cam_id,
                first_seen_camera_code=cam.camera_code,
                first_seen_time=ts,
                last_seen_camera_id=cam_id,
                last_seen_camera_code=cam.camera_code,
                last_seen_time=ts + timedelta(seconds=random.randint(10, 120)),
                total_cameras_count=1,
                total_detections_count=random.randint(3, 12),
                match_method="SINGLE_CAMERA",
                overall_match_confidence=1.0,
                is_cross_camera=False,
                is_trajectory_complete=True,
            )
            t.checkpoints = [{
                "camera_id": cam_id,
                "camera_code": cam.camera_code,
                "camera_name": cam.name,
                "latitude": cam.latitude,
                "longitude": cam.longitude,
                "timestamp": ts.isoformat(),
                "plate": plate,
                "confidence": 0.85,
            }]
            db.add(t)
        else:
            # Multi-camera trajectory
            entries_sorted = entries[:3]  # max 3 cameras for demo
            cam_id_0, _ = entries_sorted[0]
            cam_id_last, _ = entries_sorted[-1]
            cam_0 = cam_map.get(cam_id_0)
            cam_last = cam_map.get(cam_id_last)
            if not cam_0 or not cam_last:
                continue

            first_ts = now - timedelta(minutes=random.randint(30, 120))
            checkpoints = []
            for idx, (cid, tid) in enumerate(entries_sorted):
                c = cam_map.get(cid)
                if not c:
                    continue
                cp_ts = first_ts + timedelta(minutes=idx * random.randint(5, 15))
                checkpoints.append({
                    "camera_id": cid,
                    "camera_code": c.camera_code,
                    "camera_name": c.name,
                    "latitude": c.latitude,
                    "longitude": c.longitude,
                    "timestamp": cp_ts.isoformat(),
                    "plate": plate,
                    "confidence": round(random.uniform(0.7, 0.95), 2),
                })

            v_class = random.choice(VEHICLE_CLASSES)
            traj = VehicleTrajectory(
                global_vehicle_id=f"TRAJ-{uuid.uuid4().hex[:12].upper()}",
                primary_plate=plate,
                vehicle_class=v_class,
                dominant_color=random.choice(COLORS),
                first_seen_camera_id=cam_id_0,
                first_seen_camera_code=cam_0.camera_code,
                first_seen_time=datetime.fromisoformat(checkpoints[0]["timestamp"]),
                last_seen_camera_id=cam_id_last,
                last_seen_camera_code=cam_last.camera_code,
                last_seen_time=datetime.fromisoformat(checkpoints[-1]["timestamp"]),
                total_cameras_count=len(checkpoints),
                total_detections_count=random.randint(5, 20),
                match_method="PLATE_MATCH",
                overall_match_confidence=round(random.uniform(0.82, 0.98), 2),
                is_cross_camera=True,
                is_trajectory_complete=True,
            )
            traj.checkpoints = checkpoints
            db.add(traj)
            await db.flush()

            # Cross-camera match links
            for i in range(len(checkpoints) - 1):
                a = checkpoints[i]
                b = checkpoints[i + 1]
                ta = datetime.fromisoformat(a["timestamp"])
                tb = datetime.fromisoformat(b["timestamp"])
                delta = (tb - ta).total_seconds()
                db.add(CrossCameraMatch(
                    trajectory_id=traj.id,
                    from_camera_id=a["camera_id"],
                    from_camera_code=a["camera_code"],
                    to_camera_id=b["camera_id"],
                    to_camera_code=b["camera_code"],
                    from_time=ta,
                    to_time=tb,
                    transit_duration_seconds=delta,
                    match_method="PLATE_MATCH",
                    match_confidence=round(random.uniform(0.82, 0.98), 2),
                    is_spatially_plausible=True,
                ))

    await db.flush()

    # ── Congestion records ────────────────────────────────────────────
    cong_levels = ["LOW", "LOW", "MODERATE", "MODERATE", "HIGH", "SEVERE"]
    for cam in active_cams:
        idx = round(random.uniform(5, 85), 1)
        lvl = "LOW" if idx < 25 else ("MODERATE" if idx < 50 else ("HIGH" if idx < 75 else "SEVERE"))
        db.add(CongestionRecord(
            camera_id=cam.id,
            timestamp=now,
            vehicle_count=random.randint(20, 200),
            flow_rate_per_min=round(random.uniform(2, 30), 1),
            congestion_level=lvl,
            congestion_index=idx,
        ))

    await db.commit()
    logger.info("Demo data seeded successfully.")
