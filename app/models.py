from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey, Text, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    restaurant_id = Column(Integer, index=True)
    delivery_id = Column(Integer, nullable=True)  # ID из delivery-service
    status = Column(String, default="created")  # created, confirmed, cooking, ready, in_delivery, delivered, cancelled
    total_amount = Column(Numeric(10, 2))
    discount_amount = Column(Numeric(10, 2), default=0)
    final_amount = Column(Numeric(10, 2))
    items = Column(JSON)  # Список блюд с ценами и количеством
    delivery_address = Column(JSON)
    special_instructions = Column(Text, nullable=True)
    payment_status = Column(String, default="pending")  # pending, paid, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    order_events = relationship("OrderEvent", back_populates="order")

class OrderEvent(Base):
    __tablename__ = "order_events"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    status = Column(String)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order", back_populates="order_events")