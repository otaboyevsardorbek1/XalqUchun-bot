# bot/keyboards/catalog.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.db.models import Category, Product
from typing import List
from bot.utils.helpers import format_price

def categories_kb(categories: List[Category]) -> InlineKeyboardMarkup:
    """Kategoriyalar ro'yxati"""
    builder = InlineKeyboardBuilder()
    
    for cat in categories:
        builder.button(
            text=f"📁 {cat.name}",
            callback_data=f"cat_{cat.id}"
        )
    
    builder.button(text="📝 Maxsus buyurtma", callback_data="custom_order")
    builder.button(text="🔙 Asosiy menyu", callback_data="back_to_main")
    builder.adjust(1)
    
    return builder.as_markup()

def products_kb(products: List[Product], category_id: int) -> InlineKeyboardMarkup:
    """Kategoriyadagi mahsulotlar"""
    builder = InlineKeyboardBuilder()
    
    for prod in products:
        price_str = format_price(prod.price)
        builder.button(
            text=f"{prod.name} - {price_str} so'm",
            callback_data=f"prod_{prod.id}"
        )
    
    builder.button(text="📝 Maxsus buyurtma", callback_data="custom_order")
    builder.button(text="🔙 Orqaga", callback_data=f"back_to_cat_{category_id}")
    builder.adjust(1)
    
    return builder.as_markup()

def product_detail_kb(
    product_id: int,
    category_id: int,
    current_qty: int = 1
) -> InlineKeyboardMarkup:
    """Mahsulot detallari uchun tugmalar"""
    builder = InlineKeyboardBuilder()
    
    # Miqdor tanlash tugmalari
    builder.row(
        InlineKeyboardButton(text="➖", callback_data=f"qty_dec_{product_id}"),
        InlineKeyboardButton(text=f"{current_qty}", callback_data="noop"),
        InlineKeyboardButton(text="➕", callback_data=f"qty_inc_{product_id}"),
        width=3
    )
    
    # Savatga qo'shish
    builder.row(
        InlineKeyboardButton(
            text="🛒 Savatga qo'shish", 
            callback_data=f"add_to_cart_{product_id}"
        )
    )
    
    # Orqaga
    builder.row(
        InlineKeyboardButton(
            text="🔙 Orqaga", 
            callback_data=f"back_to_cat_{category_id}"
        )
    )
    
    return builder.as_markup()