# bot/keyboards/main.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Optional

def get_main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Asosiy menyu"""
    keyboard = [
        [KeyboardButton(text="🛍 Katalog")],
        [KeyboardButton(text="🛒 Savat"), KeyboardButton(text="📞 Bog'lanish")],
        [KeyboardButton(text="👤 Profil"), KeyboardButton(text="❓ Yordam")]
    ]
    
    if is_admin:
        keyboard.append([KeyboardButton(text="👑 Admin panel")])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Menyudan tanlang..."
    )

def get_admin_menu() -> ReplyKeyboardMarkup:
    """Admin menyusi"""
    keyboard = [
        [KeyboardButton(text="📦 Buyurtmalar"), KeyboardButton(text="👥 Foydalanuvchilar")],
        [KeyboardButton(text="💰 Pul so'rovlari"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="📢 Xabar yuborish"), KeyboardButton(text="⚙️ Sozlamalar")],
        [KeyboardButton(text="🔙 Asosiy menyu")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Admin panel..."
    )

def get_back_button(callback_data: str = "back_to_main") -> InlineKeyboardMarkup:
    """Orqaga tugmasi"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Orqaga", callback_data=callback_data)
    return builder.as_markup()

def get_confirmation_keyboard(
    confirm_callback: str = "confirm",
    cancel_callback: str = "cancel"
) -> InlineKeyboardMarkup:
    """Tasdiqlash tugmalari"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Ha", callback_data=confirm_callback)
    builder.button(text="❌ Yo'q", callback_data=cancel_callback)
    builder.adjust(2)
    return builder.as_markup()

def get_pagination_keyboard(
    current_page: int,
    total_pages: int,
    prefix: str,
    back_callback: Optional[str] = None
) -> InlineKeyboardMarkup:
    """Paginatsiya tugmalari"""
    builder = InlineKeyboardBuilder()
    
    if current_page > 1:
        builder.button(text="⬅️", callback_data=f"{prefix}_page_{current_page-1}")
    
    builder.button(text=f"{current_page}/{total_pages}", callback_data="noop")
    
    if current_page < total_pages:
        builder.button(text="➡️", callback_data=f"{prefix}_page_{current_page+1}")
    
    builder.adjust(3)
    
    if back_callback:
        builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=back_callback))
    
    return builder.as_markup()