from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models import Order, OrderEvent
from app.schemas import OrderCreate, OrderStatusUpdate, CancelOrderRequest
from decimal import Decimal
from datetime import datetime

# Order CRUD
async def get_order(db: AsyncSession, order_id: int):
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.order_events))
        .filter(Order.id == order_id)
    )
    return result.scalar_one_or_none()

async def get_order_by_id(db: AsyncSession, order_id: int):
    """Получить заказ по ID"""
    return await get_order(db, order_id)

async def get_orders_by_user(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.order_events))
        .filter(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def create_order(db: AsyncSession, order: OrderCreate):
    # Рассчитываем стоимость заказа
    total_amount = Decimal('0')
    for item in order.items:
        total_amount += item.price * item.quantity
    
    # Применяем скидки
    discount_amount = Decimal('0')
    if total_amount > Decimal('1000'):
        discount_amount = total_amount * Decimal('0.1')
    
    final_amount = total_amount - discount_amount
    
    # Преобразуем Decimal в float для JSON сериализации
    items_for_json = []
    for item in order.items:
        item_dict = item.dict()
        item_dict['price'] = float(item_dict['price'])
        items_for_json.append(item_dict)
    
    db_order = Order(
        user_id=order.user_id,
        restaurant_id=order.restaurant_id,
        items=items_for_json,
        delivery_address=order.delivery_address,
        special_instructions=order.special_instructions,
        total_amount=total_amount,
        discount_amount=discount_amount,
        final_amount=final_amount,
        status="created"
    )
    
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)
    
    # Создаем начальное событие заказа
    order_event = OrderEvent(
        order_id=db_order.id,
        status="created",
        description="Order created successfully"
    )
    db.add(order_event)
    await db.commit()
    
    return db_order

async def update_order_status(db: AsyncSession, order_id: int, status_update: OrderStatusUpdate):
    db_order = await get_order(db, order_id)
    if not db_order:
        return None
    
    db_order.status = status_update.status
    
    # Создаем событие изменения статуса
    order_event = OrderEvent(
        order_id=order_id,
        status=status_update.status,
        description=status_update.description or f"Order status updated to {status_update.status}"
    )
    db.add(order_event)
    
    await db.commit()
    await db.refresh(db_order)
    return db_order

async def cancel_order(db: AsyncSession, order_id: int, cancel_request: CancelOrderRequest):
    db_order = await get_order(db, order_id)
    if not db_order:
        return None
    
    # Проверяем, можно ли отменить заказ (не все статусы можно отменить)
    cancellable_statuses = ["created", "confirmed", "cooking"]
    if db_order.status not in cancellable_statuses:
        return None
    
    db_order.status = "cancelled"
    
    # Создаем событие отмены
    order_event = OrderEvent(
        order_id=order_id,
        status="cancelled",
        description=cancel_request.reason or "Order cancelled by user"
    )
    db.add(order_event)
    
    await db.commit()
    await db.refresh(db_order)
    return db_order

