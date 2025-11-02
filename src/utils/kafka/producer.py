import json
import uuid
from datetime import datetime
from aiokafka import AIOKafkaProducer
import logging

from src.core.config import settings

logger = logging.getLogger(__name__)

class KafkaEventProducer:
    def __init__(self, bootstrap_servers: str = settings.KAFKA_BOOTSTRAP_SERVERS):
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
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "order.created",
            "timestamp": datetime.utcnow().isoformat(),
            "source_service": "order-service",
            "data": order_data
        }
        
        try:
            await self.producer.send_and_wait(
                "order.created",
                json.dumps(event).encode('utf-8')
            )
            logger.info(f"Order created event sent: {order_data['order_id']}")
        except Exception as e:
            logger.error(f"Failed to send order created event: {e}")

    async def send_order_status_updated(self, status_data: dict):
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "order.status.updated",
            "timestamp": datetime.utcnow().isoformat(),
            "source_service": "order-service",
            "data": status_data
        }
        
        try:
            await self.producer.send_and_wait(
                "order.status.updated",
                json.dumps(event).encode('utf-8')
            )
            logger.info(f"Order status updated event sent: {status_data['order_id']}")
        except Exception as e:
            logger.error(f"Failed to send order status updated event: {e}")

event_producer = KafkaEventProducer()