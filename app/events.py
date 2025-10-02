from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

class EventType(str, Enum):
    USER_CREATED = "user.created"
    ORDER_CREATED = "order.created"
    ORDER_STATUS_UPDATED = "order.status.updated"

class BaseEvent(BaseModel):
    event_id: str
    event_type: EventType
    timestamp: datetime
    source_service: str
    data: Dict[str, Any]

# Order Events
class OrderItemData(BaseModel):
    dish_id: int
    dish_name: str
    quantity: int
    price: float
    special_instructions: Optional[str] = None

class OrderCreatedData(BaseModel):
    order_id: int
    user_id: int
    restaurant_id: int
    items: List[OrderItemData]
    total_amount: float
    final_amount: float
    delivery_address: Dict[str, Any]
    status: str

class OrderCreatedEvent(BaseEvent):
    event_type: EventType = EventType.ORDER_CREATED
    data: OrderCreatedData

class OrderStatusUpdatedData(BaseModel):
    order_id: int
    user_id: int
    status: str
    description: str

class OrderStatusUpdatedEvent(BaseEvent):
    event_type: EventType = EventType.ORDER_STATUS_UPDATED
    data: OrderStatusUpdatedData