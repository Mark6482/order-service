from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.api.deps import get_db
from src.schemas.order import (
OrderCreate, OrderResponse, OrderStatusUpdate,
CancelOrderRequest, CancelOrderResponse
)
from src.schemas.order_event import OrderWithEvents
from src.services.order import (
    get_order_by_id, create_order, update_order_status, cancel_order,
    get_orders_by_user
)
from src.utils.kafka.producer import event_producer

router = APIRouter()

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_new_order(
    order: OrderCreate,
    x_user_id: int | None = Header(None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db)
):
    """Создать новый заказ"""
    if x_user_id is not None and order.user_id != x_user_id:
        order = OrderCreate(
            user_id=x_user_id,
            restaurant_id=order.restaurant_id,
            items=order.items,
            delivery_address=order.delivery_address,
            special_instructions=order.special_instructions,
        )

    db_order = await create_order(db, order)
    
    order_data = {
        "order_id": db_order.id,
        "user_id": db_order.user_id,
        "restaurant_id": db_order.restaurant_id,
        "items": [
            {
                "dish_id": item["dish_id"],
                "dish_name": item["dish_name"],
                "quantity": item["quantity"],
                "price": float(item["price"]),
                "special_instructions": item.get("special_instructions")
            }
            for item in db_order.items
        ],
        "total_amount": float(db_order.total_amount),
        "final_amount": float(db_order.final_amount),
        "delivery_address": db_order.delivery_address,
        "status": db_order.status
    }
    await event_producer.send_order_created(order_data)
    
    return db_order

@router.get("/{order_id}", response_model=OrderWithEvents)
async def get_order_by_id_endpoint(
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить заказ по ID"""
    db_order = await get_order_by_id(db, order_id)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order

@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status_endpoint(
    order_id: int,
    status_update: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновить статус заказа"""
    db_order = await update_order_status(db, order_id, status_update)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    
    status_data = {
        "order_id": order_id,
        "user_id": db_order.user_id,
        "status": status_update.status,
        "description": status_update.description or f"Order status updated to {status_update.status}"
    }
    await event_producer.send_order_status_updated(status_data)
    
    return db_order

@router.post("/{order_id}/cancel", response_model=CancelOrderResponse)
async def cancel_order_endpoint(
    order_id: int,
    cancel_request: CancelOrderRequest,
    db: AsyncSession = Depends(get_db)
):
    """Отменить заказ"""
    db_order = await cancel_order(db, order_id, cancel_request)
    if db_order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found or cannot be cancelled in current status"
        )
    
    status_data = {
        "order_id": order_id,
        "user_id": db_order.user_id,
        "status": "cancelled",
        "description": cancel_request.reason or "Order cancelled by user"
    }
    await event_producer.send_order_status_updated(status_data)
    
    return CancelOrderResponse(
        message="Order cancelled successfully",
        order_id=order_id,
        status="cancelled"
    )

@router.get("/users/{user_id}/orders", response_model=List[OrderWithEvents])
async def get_user_orders(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Получить заказы пользователя"""
    return await get_orders_by_user(db, user_id, skip, limit)