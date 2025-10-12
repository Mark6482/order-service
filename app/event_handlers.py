import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.crud import update_order_status, get_order
from app.schemas import OrderStatusUpdate

logger = logging.getLogger(__name__)

async def handle_delivery_assigned(event_data: dict):
    """Обработка события назначения курьера - обновляем статус заказа"""
    logger.info(f"Handling delivery_assigned event: {event_data}")
    
    try:
        data = event_data['data']
        order_id = data['order_id']
        
        async with AsyncSessionLocal() as db:
            # Обновляем статус заказа на "in_delivery"
            status_update = OrderStatusUpdate(
                status="in_delivery",
                description=f"Delivery assigned to courier #{data['courier_id']}"
            )
            
            await update_order_status(db, order_id, status_update)
            logger.info(f"Updated order {order_id} status to 'in_delivery'")
            
    except Exception as e:
        logger.error(f"Error handling delivery_assigned event: {e}", exc_info=True)

async def handle_delivery_status_updated(event_data: dict):
    """Обработка события обновления статуса доставки"""
    logger.info(f"Handling delivery_status_updated event: {event_data}")
    
    try:
        data = event_data['data']
        order_id = data['order_id']
        delivery_status = data['status']
        
        async with AsyncSessionLocal() as db:
            # Синхронизируем статус заказа со статусом доставки
            order_status_map = {
                "picked_up": "in_delivery",
                "delivered": "delivered",
                "cancelled": "cancelled"
            }
            
            if delivery_status in order_status_map:
                status_update = OrderStatusUpdate(
                    status=order_status_map[delivery_status],
                    description=data.get('description', f"Delivery status: {delivery_status}")
                )
                
                await update_order_status(db, order_id, status_update)
                logger.info(f"Updated order {order_id} status to '{order_status_map[delivery_status]}'")
            
    except Exception as e:
        logger.error(f"Error handling delivery_status_updated event: {e}", exc_info=True)