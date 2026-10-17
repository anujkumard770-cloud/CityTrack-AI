from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.services import analytics_service as svc

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(get_db)):
    return await svc.get_summary(db)


@router.get("/traffic")
async def get_traffic(hours: int = 24, db: AsyncSession = Depends(get_db)):
    return await svc.get_traffic_over_time(db, hours=hours)


@router.get("/classes")
async def get_class_distribution(db: AsyncSession = Depends(get_db)):
    return await svc.get_vehicle_class_distribution(db)


@router.get("/cameras")
async def get_camera_metrics(db: AsyncSession = Depends(get_db)):
    return await svc.get_camera_metrics(db)


@router.get("/heatmap")
async def get_heatmap(db: AsyncSession = Depends(get_db)):
    return await svc.get_congestion_heatmap(db)


@router.get("/transitions")
async def get_transitions(db: AsyncSession = Depends(get_db)):
    return await svc.get_transition_matrix(db)
