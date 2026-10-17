import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "CityTrack AI"
    APP_ENV: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # SQLite async database
    DATABASE_URL: str = "sqlite+aiosqlite:///./citytrack.db"
    
    # Storage paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "uploads")
    PROCESSED_DIR: str = os.path.join(BASE_DIR, "processed")
    MODELS_DIR: str = os.path.join(BASE_DIR, "models_weights")
    PLATE_CROPS_DIR: str = os.path.join(BASE_DIR, "uploads", "plate_crops")
    
    # AI Models
    VEHICLE_MODEL_PATH: str = "yolov8n.pt"
    PLATE_MODEL_PATH: str = os.path.join(MODELS_DIR, "license_plate_detector.pt")
    
    # Detection & ANPR
    CONFIDENCE_THRESHOLD: float = 0.35
    PLATE_CONFIDENCE_THRESHOLD: float = 0.30
    TRACKER_TYPE: str = "bytetrack.yaml"
    
    # Privacy & Retention
    ENABLE_DEMO_DATA: bool = True
    MASK_PLATES_ON_DISPLAY: bool = False
    DATA_RETENTION_DAYS: int = 30

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

# Ensure vital directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.PROCESSED_DIR, exist_ok=True)
os.makedirs(settings.MODELS_DIR, exist_ok=True)
os.makedirs(settings.PLATE_CROPS_DIR, exist_ok=True)
