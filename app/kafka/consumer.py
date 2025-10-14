import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer
from app.event_handlers import (
    handle_delivery_assigned,
    handle_delivery_status_updated,
    handle_cart_checked_out,
)

logger = logging.getLogger(__name__)

class KafkaEventConsumer:
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None

    async def start(self):
        self.consumer = AIOKafkaConsumer(
            'delivery.assigned',
            'delivery.status.updated',
            'cart.checked_out',
            bootstrap_servers=self.bootstrap_servers,
            group_id="order-service",
            enable_auto_commit=False,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')) if v else None
        )
        await self.consumer.start()
        await self.consume_events()

    async def stop(self):
        if self.consumer:
            await self.consumer.stop()

    async def consume_events(self):
        try:
            async for msg in self.consumer:
                try:
                    if not msg.value:
                        continue
                        
                    event_data = msg.value
                    event_type = event_data.get('event_type')
                    
                    logger.info(f"Received event: {event_type}")
                    
                    if event_type == 'delivery.assigned':
                        await handle_delivery_assigned(event_data)
                    elif event_type == 'delivery.status.updated':
                        await handle_delivery_status_updated(event_data)
                    elif event_type == 'cart.checked_out':
                        await handle_cart_checked_out(event_data)
                    else:
                        logger.warning(f"Unknown event type: {event_type}")
                    
                    await self.consumer.commit()
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        except Exception as e:
            logger.error(f"Consumer error: {e}")

event_consumer = KafkaEventConsumer()