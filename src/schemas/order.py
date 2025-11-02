from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal
from enum import Enum

class OrderStatus(str, Enum):
    CREATED = "created"
    CONFIRMED = "confirmed"
    COOKING = "cooking"
    READY = "ready"
    IN_DELIVERY = "in_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"

class OrderItem(BaseModel):
    dish_id: int
    dish_name: str
    quantity: int
    price: Decimal
    special_instructions: Optional[str] = None

    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    user_id: int
    restaurant_id: int
    items: List[OrderItem]
    delivery_address: Dict[str, Any]
    special_instructions: Optional[str] = None

class OrderCreate(OrderBase):
    pass

class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    description: Optional[str] = None

class OrderResponse(OrderBase):
    id: int
    delivery_id: Optional[int]
    status: OrderStatus
    total_amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    payment_status: PaymentStatus
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class CancelOrderRequest(BaseModel):
    reason: Optional[str] = "No reason provided"

class CancelOrderResponse(BaseModel):
    message: str
    order_id: int
    status: OrderStatus