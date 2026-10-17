from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from app.database.session import Base

class PlateObservation(Base):
    __tablename__ = "plate_observations"

    id = Column(Integer, primary_key=True, index=True)
    detection_id = Column(Integer, ForeignKey("vehicle_detections.id", ondelete="CASCADE"), nullable=True)
    job_id = Column(Integer, ForeignKey("video_jobs.id", ondelete="CASCADE"), nullable=False)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    
    tracking_id = Column(Integer, nullable=False, index=True)
    
    raw_plate_text = Column(String(50), nullable=True)
    normalized_plate = Column(String(50), nullable=True, index=True)
    is_valid_format = Column(Boolean, default=False)
    is_readable = Column(Boolean, default=True)
    
    # State code (e.g., DL, MH, KA, HR, UP, etc.)
    state_code = Column(String(10), nullable=True, index=True)
    
    plate_confidence = Column(Float, default=0.0)
    ocr_confidence = Column(Float, default=0.0)
    
    crop_path = Column(String(500), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("VideoJob", back_populates="plate_observations")
    camera = relationship("Camera", back_populates="plate_observations")
    detection = relationship("VehicleDetection", back_populates="plate_observation")

    __table_args__ = (
        Index("idx_normalized_plate_time", "normalized_plate", "timestamp"),
    )
