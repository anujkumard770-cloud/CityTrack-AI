from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.session import Base

class VideoJob(Base):
    __tablename__ = "video_jobs"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    processed_video_path = Column(String(500), nullable=True)
    
    # Status: PENDING, PROCESSING, COMPLETED, FAILED
    status = Column(String(30), default="PENDING", index=True)
    progress = Column(Float, default=0.0)  # 0 to 100 percentage
    
    total_frames = Column(Integer, default=0)
    processed_frames = Column(Integer, default=0)
    fps = Column(Float, default=0.0)
    duration_seconds = Column(Float, default=0.0)
    
    total_vehicles_detected = Column(Integer, default=0)
    total_plates_recognized = Column(Integer, default=0)
    
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    camera = relationship("Camera", back_populates="jobs")
    detections = relationship("VehicleDetection", back_populates="job", cascade="all, delete-orphan")
    plate_observations = relationship("PlateObservation", back_populates="job", cascade="all, delete-orphan")
