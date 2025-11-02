from fastapi import APIRouter
from src.schemas.health import HealthResponse

router = APIRouter()

@router.get("", response_model=HealthResponse)
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy", "service": "order-service"}