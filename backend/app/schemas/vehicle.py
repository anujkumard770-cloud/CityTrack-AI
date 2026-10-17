from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class PlateObservationResponse(BaseModel):
    id: int
    camera_id: int
    camera_code: Optional[str] = None
    tracking_id: int
    raw_plate_text: Optional[str] = None
    normalized_plate: Optional[str] = None
    is_valid_format: bool
    is_readable: bool
    state_code: Optional[str] = None
    plate_confidence: float
    ocr_confidence: float
    crop_url: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class VehicleDetectionResponse(BaseModel):
    id: int
    camera_id: int
    camera_code: Optional[str] = None
    tracking_id: int
    frame_number: int
    timestamp: datetime
    vehicle_class: str
    confidence: float
    bbox: List[float]
    dominant_color: Optional[str] = None
    plate: Optional[PlateObservationResponse] = None

    class Config:
        from_attributes = True

class VehicleSearchFilter(BaseModel):
    plate_query: Optional[str] = None
    vehicle_class: Optional[str] = None
    camera_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    min_confidence: Optional[float] = 0.0
    limit: Optional[int] = 50
    offset: Optional[int] = 0
