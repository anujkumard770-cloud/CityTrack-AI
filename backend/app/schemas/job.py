from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class VideoJobBase(BaseModel):
    camera_id: int
    filename: str

class VideoJobCreate(BaseModel):
    camera_id: int

class VideoJobResponse(BaseModel):
    id: int
    camera_id: int
    filename: str
    status: str
    progress: float
    total_frames: int
    processed_frames: int
    fps: float
    duration_seconds: float
    total_vehicles_detected: int
    total_plates_recognized: int
    processed_video_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
