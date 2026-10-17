from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from app.database.session import Base
import json

class VehicleTrajectory(Base):
    __tablename__ = "vehicle_trajectories"

    id = Column(Integer, primary_key=True, index=True)
    global_vehicle_id = Column(String(100), unique=True, index=True, nullable=False)
    
    primary_plate = Column(String(50), nullable=True, index=True)
    vehicle_class = Column(String(50), nullable=False)
    dominant_color = Column(String(30), nullable=True)
    
    first_seen_camera_id = Column(Integer, nullable=False)
    first_seen_camera_code = Column(String(50), nullable=True)
    first_seen_time = Column(DateTime, nullable=False, index=True)
    
    last_seen_camera_id = Column(Integer, nullable=False)
    last_seen_camera_code = Column(String(50), nullable=True)
    last_seen_time = Column(DateTime, nullable=False, index=True)
    
    total_cameras_count = Column(Integer, default=1)
    total_detections_count = Column(Integer, default=1)
    
    # Matching details: PLATE_EXACT, REID_SPATIOTEMPORAL, TENTATIVE, SINGLE_CAMERA
    match_method = Column(String(50), default="SINGLE_CAMERA")
    overall_match_confidence = Column(Float, default=1.0)
    
    is_cross_camera = Column(Boolean, default=False, index=True)
    is_trajectory_complete = Column(Boolean, default=True)
    
    # JSON list of checkpoints:
    # [{"camera_id": 1, "camera_code": "CAM-01", "name": "Main Gate", "lat": 28.61, "lng": 77.20, "timestamp": "...", "plate": "...", "confidence": 0.95, "crop_path": "..."}]
    checkpoints_json = Column(Text, default="[]")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    matches = relationship("CrossCameraMatch", back_populates="trajectory", cascade="all, delete-orphan")

    @property
    def checkpoints(self):
        try:
            return json.loads(self.checkpoints_json or "[]")
        except Exception:
            return []

    @checkpoints.setter
    def checkpoints(self, val):
        self.checkpoints_json = json.dumps(val)
