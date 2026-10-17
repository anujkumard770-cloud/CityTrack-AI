from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class CrossCameraMatchResponse(BaseModel):
    id: int
    from_camera_id: int
    from_camera_code: Optional[str] = None
    to_camera_id: int
    to_camera_code: Optional[str] = None
    from_time: datetime
    to_time: datetime
    transit_duration_seconds: float
    match_method: str
    match_confidence: float
    is_spatially_plausible: bool

    class Config:
        from_attributes = True

class TrajectoryCheckpoint(BaseModel):
    camera_id: int
    camera_code: str
    camera_name: str
    latitude: float
    longitude: float
    timestamp: datetime
    plate: Optional[str] = None
    confidence: float
    crop_url: Optional[str] = None
    dominant_color: Optional[str] = None
    vehicle_class: Optional[str] = None

class VehicleTrajectoryResponse(BaseModel):
    id: int
    global_vehicle_id: str
    primary_plate: Optional[str] = None
    vehicle_class: str
    dominant_color: Optional[str] = None
    first_seen_camera_id: int
    first_seen_camera_code: Optional[str] = None
    first_seen_time: datetime
    last_seen_camera_id: int
    last_seen_camera_code: Optional[str] = None
    last_seen_time: datetime
    total_cameras_count: int
    total_detections_count: int
    match_method: str
    overall_match_confidence: float
    is_cross_camera: bool
    is_trajectory_complete: bool
    checkpoints: List[Dict[str, Any]]
    matches: List[CrossCameraMatchResponse] = []

    class Config:
        from_attributes = True
