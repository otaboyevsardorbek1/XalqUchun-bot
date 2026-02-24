# bot/db/models.py
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    username = Column(String(100), nullable=True)
    phone_number = Column(String(20), nullable=True)
    is_phone_verified = Column(Boolean, default=False)
    role = Column(String(50), default="guest")  # owner, admin, manager, worker, diller, dastafka, guest
    balance = Column(Float, default=0.0)
    referrals_count = Column(Integer, default=0)
    referrer_telegram_id = Column(BigInteger, nullable=True, index=True)
    blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    orders = relationship("Order", back_populates="user", foreign_keys="Order.user_id")
    custom_orders = relationship("CustomOrder", back_populates="user", foreign_keys="CustomOrder.user_id")
    sent_messages = relationship("Message", foreign_keys="Message.sender_telegram_id", back_populates="sender")
    received_messages = relationship("Message", foreign_keys="Message.receiver_telegram_id", back_populates="receiver")
    transactions = relationship("Transaction", back_populates="user", foreign_keys="Transaction.user_telegram_id")

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    products = relationship("Product", back_populates="category", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    image_url = Column(String(500), nullable=True)
    is_available = Column(Boolean, default=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    order_number = Column(String(50), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    phone = Column(String(20), nullable=False)
    location_link = Column(Text, nullable=False)
    location_coords = Column(String(100), nullable=True)
    total_amount = Column(Float, default=0.0)
    status = Column(String(50), default="new")  # new, processing, ready, delivered, cancelled
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_name = Column(String(200), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    unit = Column(String(20), default="dona")
    is_custom = Column(Boolean, default=False)
    
    order = relationship("Order", back_populates="items")
    product = relationship("Product")

class CustomOrder(Base):
    __tablename__ = 'custom_orders'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    phone_number = Column(String(20), nullable=False)
    location = Column(String(500), nullable=False)
    location_coords = Column(String(100), nullable=True)
    status = Column(String(50), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="custom_orders")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    sender_telegram_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    receiver_telegram_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    sender = relationship("User", foreign_keys=[sender_telegram_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_telegram_id], back_populates="received_messages")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True)
    transaction_number = Column(String(50), unique=True, nullable=False)
    user_telegram_id = Column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String(50), default="withdraw")  # withdraw, bonus, manual, payment
    method = Column(String(50), default="manual")  # payme, click, bank, cash, system
    status = Column(String(50), default="pending")  # pending, approved, declined
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    admin_telegram_id = Column(BigInteger, nullable=True)
    
    user = relationship("User", back_populates="transactions")