from fastapi import APIRouter

from src.api.v1.endpoints import orders, health

api_router = APIRouter()

api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(health.router, prefix="/health", tags=["health"])