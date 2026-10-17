"""
Health check and AI model status routes.
"""
from fastapi import APIRouter
from app.vision.processor import ModelManager
from app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "CityTrack AI Backend"}


@router.get("/models/status")
async def model_status():
    mgr = ModelManager.get()
    status = mgr.status
    all_ok = (
        status["vehicle_model"]["loaded"]
        and status["ocr_engine"]["loaded"]
    )
    plate_ok = status["plate_model"]["loaded"]
    return {
        "all_models_ready": all_ok and plate_ok,
        "vehicle_detection": status["vehicle_model"],
        "plate_detection": {
            **status["plate_model"],
            "setup_instructions": (
                None if plate_ok else
                "Download a YOLO-based license plate detection model (e.g., from "
                "https://github.com/nicehash/license_plate_detector or Roboflow universe) "
                "and place the .pt file at: " + settings.PLATE_MODEL_PATH
            ),
        },
        "ocr_engine": status["ocr_engine"],
        "settings": {
            "vehicle_model_path": settings.VEHICLE_MODEL_PATH,
            "plate_model_path": settings.PLATE_MODEL_PATH,
            "confidence_threshold": settings.CONFIDENCE_THRESHOLD,
            "plate_confidence_threshold": settings.PLATE_CONFIDENCE_THRESHOLD,
            "demo_mode_enabled": settings.ENABLE_DEMO_DATA,
            "mask_plates": settings.MASK_PLATES_ON_DISPLAY,
            "data_retention_days": settings.DATA_RETENTION_DAYS,
        },
    }
