from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from decimal import Decimal
import logging

from src.db.models.order import Order
from src.db.models.order_event import OrderEvent
from src.schemas.order import OrderCreate, OrderStatusUpdate, CancelOrderRequest

logger = logging.getLogger(__name__)

async def get_order(db: AsyncSession, order_id: int):
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.order_events))
        .filter(Order.id == order_id)
    )
    return result.scalar_one_or_none()

async def get_order_by_id(db: AsyncSession, order_id: int):
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
    total_amount = Decimal('0')
    for item in order.items:
        total_amount += item.price * item.quantity
    
    discount_amount = Decimal('0')
    if total_amount > Decimal('1000'):
        discount_amount = total_amount * Decimal('0.1')
    
    final_amount = total_amount - discount_amount
    
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
    
    cancellable_statuses = ["created", "confirmed", "cooking"]
    if db_order.status not in cancellable_statuses:
        return None
    
    db_order.status = "cancelled"
    
    order_event = OrderEvent(
        order_id=order_id,
        status="cancelled",
        description=cancel_request.reason or "Order cancelled by user"
    )
    db.add(order_event)
    
    await db.commit()
    await db.refresh(db_order)
    return db_order

async def cancel_orders_by_user_id(db: AsyncSession, user_id: int):
    active_statuses = ["created", "confirmed", "cooking", "ready", "in_delivery"]
    
    result = await db.execute(
        select(Order)
        .filter(Order.user_id == user_id, Order.status.in_(active_statuses))
    )
    orders = result.scalars().all()
    
    cancelled_count = 0
    for order in orders:
        order.status = "cancelled"
        
        order_event = OrderEvent(
            order_id=order.id,
            status="cancelled",
            description=f"Order cancelled due to user deletion (user_id: {user_id})"
        )
        db.add(order_event)
        cancelled_count += 1
    
    if cancelled_count > 0:
        await db.commit()
        logger.info(f"Cancelled {cancelled_count} orders for user {user_id}")
    
    return cancelled_count