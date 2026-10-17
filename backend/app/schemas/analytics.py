from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class TrafficSummaryMetrics(BaseModel):
    total_detections: int
    unique_tracked_vehicles: int
    cross_camera_journeys: int
    active_cameras_count: int
    average_congestion_index: float
    total_plates_recognized: int
    is_demo_data: bool

class VehicleClassDistribution(BaseModel):
    vehicle_class: str
    count: int
    percentage: float

class HourlyTrafficPoint(BaseModel):
    hour: str
    volume: int
    cars: int
    motorcycles: int
    buses: int
    trucks: int

class CameraTrafficMetric(BaseModel):
    camera_id: int
    camera_code: str
    camera_name: str
    latitude: float
    longitude: float
    total_vehicles: int
    unique_vehicles: int
    congestion_level: str
    congestion_index: float
    avg_confidence: float

class CongestionHeatmapPoint(BaseModel):
    camera_id: int
    camera_code: str
    camera_name: str
    latitude: float
    longitude: float
    congestion_index: float
    congestion_level: str
    current_volume: int

class TransitionMatrixItem(BaseModel):
    from_camera_code: str
    to_camera_code: str
    vehicle_count: int
    avg_transit_minutes: float
