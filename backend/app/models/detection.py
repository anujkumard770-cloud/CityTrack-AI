from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.session import Base

class VehicleDetection(Base):
    __tablename__ = "vehicle_detections"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("video_jobs.id", ondelete="CASCADE"), nullable=False)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    
    tracking_id = Column(Integer, nullable=False, index=True)
    frame_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Classes: car, motorcycle, bus, truck, auto_rickshaw
    vehicle_class = Column(String(50), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    
    # Bounding box normalized or pixels [x1, y1, x2, y2]
    bbox_x1 = Column(Float, nullable=False)
    bbox_y1 = Column(Float, nullable=False)
    bbox_x2 = Column(Float, nullable=False)
    bbox_y2 = Column(Float, nullable=False)
    
    # Extracted dominant color
    dominant_color = Column(String(30), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("VideoJob", back_populates="detections")
    camera = relationship("Camera", back_populates="detections")
    plate_observation = relationship("PlateObservation", back_populates="detection", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_cam_track_time", "camera_id", "tracking_id", "timestamp"),
    )
