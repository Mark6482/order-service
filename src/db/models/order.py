from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.db.session import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    restaurant_id = Column(Integer, index=True)
    delivery_id = Column(Integer, nullable=True)
    status = Column(String, default="created")
    total_amount = Column(Numeric(10, 2))
    discount_amount = Column(Numeric(10, 2), default=0)
    final_amount = Column(Numeric(10, 2))
    items = Column(JSON)
    delivery_address = Column(JSON)
    special_instructions = Column(Text, nullable=True)
    payment_status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    order_events = relationship("OrderEvent", back_populates="order")