import logging
from src.db.session import AsyncSessionLocal
from src.services.order import update_order_status, create_order, cancel_orders_by_user_id
from src.schemas.order import OrderStatusUpdate, OrderCreate, OrderItem
from src.utils.kafka.producer import event_producer

logger = logging.getLogger(__name__)

async def handle_delivery_assigned(event_data: dict):
    logger.info(f"Handling delivery_assigned event: {event_data}")
    
    try:
        data = event_data['data']
        order_id = data['order_id']
        
        async with AsyncSessionLocal() as db:
            status_update = OrderStatusUpdate(
                status="in_delivery",
                description=f"Delivery assigned to courier #{data['courier_id']}"
            )
            
            await update_order_status(db, order_id, status_update)
            logger.info(f"Updated order {order_id} status to 'in_delivery'")
            
    except Exception as e:
        logger.error(f"Error handling delivery_assigned event: {e}", exc_info=True)

async def handle_delivery_status_updated(event_data: dict):
    logger.info(f"Handling delivery_status_updated event: {event_data}")
    
    try:
        data = event_data['data']
        order_id = data['order_id']
        delivery_status = data['status']
        
        async with AsyncSessionLocal() as db:
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

async def handle_cart_checked_out(event_data: dict):
    logger.info(f"Handling cart_checked_out event: {event_data}")
    try:
        data = event_data.get("data") or {}
        payment = data.get("payment") or {}
        if payment.get("status") != "paid":
            logger.warning("Skipping order creation because payment is not paid")
            return
        user_id = data.get("user_id")
        restaurant_id = data.get("restaurant_id")
        items = data.get("items") or []
        delivery_address = data.get("delivery_address") or {}
        special_instructions = data.get("special_instructions")

        if user_id is None or restaurant_id is None:
            logger.warning("cart_checked_out missing user_id or restaurant_id; skipping order creation")
            return

        order_items: list[OrderItem] = []
        for it in items:
            try:
                order_items.append(
                    OrderItem(
                        dish_id=it["dish_id"],
                        dish_name=it["dish_name"],
                        quantity=it["quantity"],
                        price=it["price"],
                        special_instructions=it.get("special_instructions")
                    )
                )
            except Exception as e:
                logger.error(f"Invalid cart item payload {it}: {e}")

        if not order_items:
            logger.warning("cart_checked_out has no valid items; skipping order creation")
            return

        order_create = OrderCreate(
            user_id=user_id,
            restaurant_id=restaurant_id,
            items=order_items,
            delivery_address=delivery_address,
            special_instructions=special_instructions
        )

        async with AsyncSessionLocal() as db:
            created = await create_order(db, order_create)
            try:
                created.payment_status = "paid"
                await db.commit()
                await db.refresh(created)
            except Exception as e:
                logger.error(f"Failed to set payment_status=paid for order {created.id}: {e}")
            logger.info(f"Created order {created.id} from cart {data.get('cart_id')}")

            try:
                order_data = {
                    "order_id": created.id,
                    "user_id": created.user_id,
                    "restaurant_id": created.restaurant_id,
                    "items": [
                        {
                            "dish_id": it.dish_id,
                            "dish_name": it.dish_name,
                            "quantity": it.quantity,
                            "price": float(it.price),
                            "special_instructions": it.special_instructions,
                        }
                        for it in order_items
                    ],
                    "total_amount": float(created.total_amount),
                    "final_amount": float(created.final_amount),
                    "delivery_address": delivery_address,
                    "status": created.status,
                }
                await event_producer.send_order_created(order_data)
            except Exception as e:
                logger.error(f"Failed to emit order.created for order {created.id}: {e}")
    except Exception as e:
        logger.error(f"Error handling cart_checked_out event: {e}", exc_info=True)

async def handle_user_deleted(event_data: dict):
    """Обрабатывает событие удаления пользователя"""
    logger.info(f"Handling user_deleted event: {event_data}")
    
    try:
        data = event_data['data']
        user_id = data['id']
        
        async with AsyncSessionLocal() as db:
            cancelled_count = await cancel_orders_by_user_id(db, user_id)
            logger.info(f"Successfully cancelled {cancelled_count} orders for deleted user {user_id}")
            
    except Exception as e:
        logger.error(f"Error handling user_deleted event: {e}", exc_info=True)