from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime

class CameraBase(BaseModel):
    camera_code: str = Field(..., example="CAM-01")
    name: str = Field(..., example="North Gate Junction")
    location_name: str = Field(..., example="Outer Ring Road, Sector 4")
    latitude: float = Field(..., example=28.6139)
    longitude: float = Field(..., example=77.2090)
    ip_stream_url: Optional[str] = None
    status: Optional[str] = "ACTIVE"
    is_demo: Optional[bool] = False
    connected_cameras: Optional[List[str]] = []
    transit_rules: Optional[Dict[str, Any]] = {}

class CameraCreate(CameraBase):
    pass

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    ip_stream_url: Optional[str] = None
    status: Optional[str] = None
    connected_cameras: Optional[List[str]] = None
    transit_rules: Optional[Dict[str, Any]] = None

class CameraResponse(CameraBase):
    id: int
    created_at: datetime
    updated_at: datetime
    active_jobs_count: Optional[int] = 0
    total_detections_count: Optional[int] = 0

    class Config:
        from_attributes = True
