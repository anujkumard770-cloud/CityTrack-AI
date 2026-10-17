from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database.session import Base

class CrossCameraMatch(Base):
    __tablename__ = "cross_camera_matches"

    id = Column(Integer, primary_key=True, index=True)
    trajectory_id = Column(Integer, ForeignKey("vehicle_trajectories.id", ondelete="CASCADE"), nullable=False)
    
    from_camera_id = Column(Integer, nullable=False)
    from_camera_code = Column(String(50), nullable=True)
    to_camera_id = Column(Integer, nullable=False)
    to_camera_code = Column(String(50), nullable=True)
    
    from_time = Column(DateTime, nullable=False)
    to_time = Column(DateTime, nullable=False)
    transit_duration_seconds = Column(Float, nullable=False)
    
    # Method: PLATE_MATCH, REID_VISUAL_SPATIOTEMPORAL, TENTATIVE
    match_method = Column(String(50), nullable=False)
    match_confidence = Column(Float, nullable=False)
    
    # Whether the transit time matches configured plausible camera network rules
    is_spatially_plausible = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    trajectory = relationship("VehicleTrajectory", back_populates="matches")
