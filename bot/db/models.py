from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    full_name = Column(String(255))
    username = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    role = Column(String(50), default="guest")  # owner, admin, manager, worker, diller, dastafka, guest
    balance = Column(Float, default=0.0)
    referrals_count = Column(Integer, default=0)
    referrer_telegram_id = Column(BigInteger, nullable=True)
    blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="user")
    custom_orders = relationship("CustomOrder", back_populates="user")
    sent_messages = relationship("Message", foreign_keys="Message.sender_telegram_id")
    received_messages = relationship("Message", foreign_keys="Message.receiver_telegram_id")
    transactions = relationship("Transaction", back_populates="user")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    price = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    phone = Column(String(20))
    location_link = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="new")
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    custom_name = Column(String(200), nullable=True)
    custom_unit = Column(String(20), nullable=True)
    order = relationship("Order", back_populates="items")
    product = relationship("Product")

class CustomOrder(Base):
    __tablename__ = "custom_orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    product_name = Column(String(200), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="custom_orders")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    sender_telegram_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    receiver_telegram_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    text = Column(Text, nullable=False)
    message_type = Column(String(50), default="text")
    created_at = Column(DateTime, default=datetime.utcnow)

    sender = relationship("User", foreign_keys=[sender_telegram_id], overlaps="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_telegram_id], overlaps="received_messages")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    user_telegram_id = Column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String(50), default="withdraw")  # withdraw, bonus, manual
    method = Column(String(50), default="manual")  # payme/qiwi/bank/manual/system
    status = Column(String(50), default="pending")  # pending/approved/declined
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    admin_telegram_id = Column(BigInteger, nullable=True)
    note = Column(Text, nullable=True)
    user = relationship("User", back_populates="transactions")