# bot/utils/cart.py
from typing import Dict, Any, List, Optional
import json
import os
import logging

logger = logging.getLogger(__name__)

CART_FILE = 'user_carts.json'

def load_carts() -> Dict[str, Any]:
    """Savat ma'lumotlarini yuklash"""
    try:
        if os.path.exists(CART_FILE):
            with open(CART_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading carts: {e}")
        return {}

def save_carts(carts: Dict[str, Any]) -> None:
    """Savat ma'lumotlarini saqlash"""
    try:
        with open(CART_FILE, 'w', encoding='utf-8') as f:
            json.dump(carts, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving carts: {e}")

def get_cart(user_id: int) -> Dict[int, Any]:
    """Foydalanuvchi savatini olish"""
    carts = load_carts()
    user_id_str = str(user_id)
    
    if user_id_str not in carts:
        return {}
    
    # JSON da kalitlar string, lekin biz int kerak
    cart = {}
    for key, value in carts[user_id_str].items():
        try:
            cart[int(key)] = value
        except ValueError:
            cart[key] = value  # Agar int ga o'tmasa, string qoldiramiz
    
    return cart

def add_to_cart(user_id: int, item_id: int, qty: int, price: float, 
                name: str = None, unit: str = 'dona', item_type: str = "regular") -> None:
    """Savatga mahsulot qo'shish"""
    carts = load_carts()
    user_id_str = str(user_id)
    
    if user_id_str not in carts:
        carts[user_id_str] = {}
    
    item_id_str = str(item_id)
    
    # Mavjudligini tekshirish
    if item_id_str in carts[user_id_str]:
        carts[user_id_str][item_id_str]['qty'] += qty
    else:
        # Yangi item qo'shish
        carts[user_id_str][item_id_str] = {
            'qty': qty,
            'price': price,
            'name': name or f"Mahsulot {item_id}",
            'unit': unit,
            'item_type': item_type
        }
    
    save_carts(carts)

def remove_from_cart(user_id: int, item_id: int) -> None:
    """Mahsulotni savatdan olib tashlash"""
    carts = load_carts()
    user_id_str = str(user_id)
    item_id_str = str(item_id)
    
    if user_id_str in carts and item_id_str in carts[user_id_str]:
        del carts[user_id_str][item_id_str]
        save_carts(carts)

def update_cart_item_qty(user_id: int, item_id: int, new_qty: float) -> None:
    """Savatdagi mahsulot miqdorini yangilash"""
    carts = load_carts()
    user_id_str = str(user_id)
    item_id_str = str(item_id)
    
    if user_id_str in carts and item_id_str in carts[user_id_str]:
        carts[user_id_str][item_id_str]['qty'] = new_qty
        save_carts(carts)

def clear_cart(user_id: int) -> None:
    """Foydalanuvchi savatini tozalash"""
    carts = load_carts()
    user_id_str = str(user_id)
    
    if user_id_str in carts:
        carts[user_id_str] = {}
        save_carts(carts)

def get_cart_total(user_id: int) -> float:
    """Savatdagi mahsulotlarning umumiy narxini hisoblash"""
    cart = get_cart(user_id)
    total = 0.0
    
    for item_id, item in cart.items():
        if isinstance(item_id, int) and item_id > 0:  # Oddiy mahsulot
            total += item['qty'] * item['price']
    
    return total

def get_cart_items_count(user_id: int) -> int:
    """Savatdagi mahsulotlar sonini qaytarish"""
    cart = get_cart(user_id)
    return len(cart)

def get_next_custom_id() -> int:
    """Maxsus buyurtma uchun keyingi ID ni olish (manfiy)"""
    carts = load_carts()
    min_id = 0
    
    for user_items in carts.values():
        for item_id_str in user_items.keys():
            try:
                item_id = int(item_id_str)
                if item_id < 0 and item_id < min_id:
                    min_id = item_id
            except ValueError:
                continue
    
    # Agar hech qanday maxsus ID bo'lmasa, -1 dan boshlaymiz
    if min_id >= 0:
        return -1
    
    return min_id - 1

def get_cart_items(user_id: int) -> List[Dict[str, Any]]:
    """Savatdagi barcha mahsulotlarni ro'yxat qilib qaytarish"""
    cart = get_cart(user_id)
    items = []
    
    for item_id, item in cart.items():
        items.append({
            'id': item_id,
            'name': item.get('name', 'Noma\'lum'),
            'qty': item.get('qty', 1),
            'price': item.get('price', 0),
            'unit': item.get('unit', 'dona'),
            'type': item.get('item_type', 'regular')
        })
    
    return items

def format_cart_text(user_id: int) -> str:
    """Savat matnini formatlash"""
    items = get_cart_items(user_id)
    
    if not items:
        return "🛒 Savatingiz bo'sh"
    
    lines = ["🛒 *Savatdagi mahsulotlar:*\n"]
    total = 0
    
    for item in items:
        if item['type'] == 'regular':
            subtotal = item['qty'] * item['price']
            total += subtotal
            lines.append(f"• {item['name']} - {item['qty']} dona x {item['price']} = {subtotal} so'm")
        else:
            lines.append(f"• 📦 {item['name']} - {item['qty']} {item['unit']} (maxsus)")
    
    if total > 0:
        lines.append(f"\n💰 *Jami: {total} so'm*")
    
    return "\n".join(lines)

# Eski funksiyalar bilan moslik uchun
def get_cart_dict(user_id: int) -> Dict[int, Any]:
    """Eski kodlar bilan moslik uchun"""
    return get_cart(user_id)