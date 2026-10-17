from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from app.database.session import Base

class CongestionRecord(Base):
    __tablename__ = "congestion_records"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    vehicle_count = Column(Integer, default=0)
    flow_rate_per_min = Column(Float, default=0.0)
    
    # LOW, MODERATE, HIGH, SEVERE
    congestion_level = Column(String(20), default="LOW")
    congestion_index = Column(Float, default=0.0)  # 0.0 - 100.0 score
    
    created_at = Column(DateTime, default=datetime.utcnow)
