from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class OrderEventResponse(BaseModel):
    id: int
    order_id: int
    status: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class OrderWithEvents(BaseModel):
    id: int
    user_id: int
    restaurant_id: int
    delivery_id: Optional[int]
    status: str
    total_amount: float
    discount_amount: float
    final_amount: float
    payment_status: str
    items: list
    delivery_address: dict
    special_instructions: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    order_events: List[OrderEventResponse] = []

    class Config:
        from_attributes = True