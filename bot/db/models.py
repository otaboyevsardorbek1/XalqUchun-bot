from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    full_name = Column(String(255))
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="user")

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
    location_link = Column(Text)  # yoki latitude/longitude alohida
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="new")  # new, processed, cancelled

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)  # nullable bo'lishi kerak
    quantity = Column(Float, nullable=False)  # Float bo'lishi kerak (2.5 kg)
    price = Column(Float, nullable=False)
    custom_name = Column(String(200), nullable=True)   # maxsus mahsulot nomi
    custom_unit = Column(String(20), nullable=True)    # maxsus birlik

    order = relationship("Order", back_populates="items")
    product = relationship("Product")

class CustomOrder(Base):
    __tablename__ = "custom_orders"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"),nullable=False)
    product_name = Column(String(200), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)