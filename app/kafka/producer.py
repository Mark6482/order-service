import json
import uuid
from datetime import datetime
from aiokafka import AIOKafkaProducer
import logging
from app.events import OrderCreatedEvent, OrderStatusUpdatedEvent

logger = logging.getLogger(__name__)

class KafkaEventProducer:
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None

    async def start(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers
        )
        await self.producer.start()

    async def stop(self):
        if self.producer:
            await self.producer.stop()

    async def send_order_created(self, order_data: dict):
        """Отправка события создания заказа"""
        event = OrderCreatedEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            source_service="order-service",
            data=order_data
        )
        
        try:
            await self.producer.send_and_wait(
                "order.created",
                event.json().encode('utf-8')
            )
            logger.info(f"Order created event sent: {order_data['order_id']}")
        except Exception as e:
            logger.error(f"Failed to send order created event: {e}")

    async def send_order_status_updated(self, status_data: dict):
        """Отправка события обновления статуса заказа"""
        event = OrderStatusUpdatedEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            source_service="order-service",
            data=status_data
        )
        
        try:
            await self.producer.send_and_wait(
                "order.status.updated",
                event.json().encode('utf-8')
            )
            logger.info(f"Order status updated event sent: {status_data['order_id']}")
        except Exception as e:
            logger.error(f"Failed to send order status updated event: {e}")

# Глобальный экземпляр продюсера
event_producer = KafkaEventProducer()