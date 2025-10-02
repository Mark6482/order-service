from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from decimal import Decimal

from app.database import get_db, engine, Base
from app.schemas import (
    OrderCreate, OrderResponse, OrderStatusUpdate, OrderWithEvents,
    CancelOrderRequest, CancelOrderResponse, TestDataResponse,
    OrderStatus, OrderItem
)
from app.crud import (
    get_order, create_order, update_order_status, cancel_order,
    get_orders_by_user, 
    get_all_orders
)
from app.kafka.producer import event_producer  # Добавлен импорт

app = FastAPI(title="Order Service", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await event_producer.start()  # Запускаем Kafka producer

@app.on_event("shutdown")
async def shutdown_event():
    await event_producer.stop()

# Основные эндпоинты
@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_new_order(
    order: OrderCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создать новый заказ"""
    db_order = await create_order(db, order)
    
    # Отправляем событие в Kafka
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

@app.put("/orders/{order_id}/status", response_model=OrderResponse)
async def update_order_status_endpoint(
    order_id: int,
    status_update: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновить статус заказа"""
    db_order = await update_order_status(db, order_id, status_update)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Отправляем событие обновления статуса
    status_data = {
        "order_id": order_id,
        "user_id": db_order.user_id,
        "status": status_update.status,
        "description": status_update.description or f"Order status updated to {status_update.status}"
    }
    await event_producer.send_order_status_updated(status_data)
    
    return db_order

@app.post("/orders/{order_id}/cancel", response_model=CancelOrderResponse)
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
    return CancelOrderResponse(
        message="Order cancelled successfully",
        order_id=order_id,
        status=OrderStatus.CANCELLED
    )

@app.get("/users/{user_id}/orders", response_model=List[OrderWithEvents])
async def get_user_orders(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Получить заказы пользователя"""
    return await get_orders_by_user(db, user_id, skip, limit)

# ТЕСТОВЫЕ ЭНДПОИНТЫ - только для разработки
@app.get("/test/orders", response_model=List[OrderWithEvents])
async def list_test_orders(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Список всех заказов (для тестирования)"""
    return await get_all_orders(db, skip, limit)

@app.post("/test/seed", response_model=TestDataResponse)
async def seed_test_data(db: AsyncSession = Depends(get_db)):
    """Создание тестовых данных"""
    # Создаем тестовые заказы
    order1 = await create_order(db, OrderCreate(
        user_id=1,
        restaurant_id=1,
        items=[
            OrderItem(
                dish_id=1,
                dish_name="Пицца Маргарита",
                quantity=1,
                price=Decimal('12.50'),
                special_instructions="Без лука"
            ),
            OrderItem(
                dish_id=2,
                dish_name="Паста Карбонара", 
                quantity=1,
                price=Decimal('10.75')
            )
        ],
        delivery_address={
            "address": "ул. Тестовая, 123",
            "lat": 55.7558,
            "lng": 37.6173
        },
        special_instructions="Позвонить за 15 минут"
    ))

    order2 = await create_order(db, OrderCreate(
        user_id=2,
        restaurant_id=2,
        items=[
            OrderItem(
                dish_id=3,
                dish_name="Бургер",
                quantity=2,
                price=Decimal('8.50')
            )
        ],
        delivery_address={
            "address": "ул. Примерная, 45",
            "lat": 55.7604,
            "lng": 37.6252
        }
    ))

    # Обновляем статусы для тестирования
    await update_order_status(db, order1.id, OrderStatusUpdate(
        status=OrderStatus.CONFIRMED,
        description="Order confirmed by restaurant"
    ))

    await update_order_status(db, order2.id, OrderStatusUpdate(
        status=OrderStatus.COOKING,
        description="Order is being prepared"
    ))

    # Назначаем доставку для одного заказа
    await assign_delivery_to_order(db, order1.id, 101)

    return TestDataResponse(
        message="Test data seeded successfully",
        created_ids={
            "orders": [order1.id, order2.id]
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)