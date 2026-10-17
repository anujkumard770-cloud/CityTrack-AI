import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from app.database.session import Base

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    camera_code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    location_name = Column(String(200), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    ip_stream_url = Column(String(255), nullable=True)
    status = Column(String(20), default="ACTIVE")  # ACTIVE, INACTIVE, MAINTENANCE
    is_demo = Column(Boolean, default=False)
    
    # Stored as JSON string list: e.g. ["CAM-02", "CAM-03"]
    connected_cameras_json = Column(Text, default="[]")
    # Stored as JSON string dict: e.g. {"CAM-02": {"min_seconds": 30, "max_seconds": 600, "distance_km": 1.2}}
    transit_rules_json = Column(Text, default="{}")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    jobs = relationship("VideoJob", back_populates="camera", cascade="all, delete-orphan")
    detections = relationship("VehicleDetection", back_populates="camera", cascade="all, delete-orphan")
    plate_observations = relationship("PlateObservation", back_populates="camera", cascade="all, delete-orphan")

    @property
    def connected_cameras(self):
        try:
            return json.loads(self.connected_cameras_json or "[]")
        except Exception:
            return []

    @connected_cameras.setter
    def connected_cameras(self, val):
        self.connected_cameras_json = json.dumps(val)

    @property
    def transit_rules(self):
        try:
            return json.loads(self.transit_rules_json or "{}")
        except Exception:
            return {}

    @transit_rules.setter
    def transit_rules(self, val):
        self.transit_rules_json = json.dumps(val)
