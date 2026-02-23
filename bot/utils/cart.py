# bot/utils/cart.py
from typing import Dict, Any
import json
import os

CART_FILE = 'user_carts.json'

def load_carts():
    """Savat ma'lumotlarini yuklash"""
    if os.path.exists(CART_FILE):
        with open(CART_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_carts(carts):
    """Savat ma'lumotlarini saqlash"""
    with open(CART_FILE, 'w') as f:
        json.dump(carts, f, indent=2)

def add_to_cart(user_id: int, item_id: int, qty: int, price: float, 
                name: str = None, unit: str = 'dona', item_type: str = "regular"):
    """Savatga mahsulot qo'shish"""
    carts = load_carts()
    user_id_str = str(user_id)
    
    if user_id_str not in carts:
        carts[user_id_str] = []
    
    # Mavjudligini tekshirish
    for item in carts[user_id_str]:
        if item['item_id'] == item_id and item['item_type'] == item_type:
            item['quantity'] += qty
            save_carts(carts)
            return
    
    # Yangi item qo'shish
    carts[user_id_str].append({
        'item_id': item_id,
        'name': name or f"Mahsulot {item_id}",
        'quantity': qty,
        'price': price,
        'unit': unit,
        'item_type': item_type
    })
    
    save_carts(carts)

def get_next_custom_id():
    """Maxsus buyurtma uchun keyingi ID ni olish"""
    carts = load_carts()
    max_id = 0
    for user_items in carts.values():
        for item in user_items:
            if item['item_type'] == 'custom' and item['item_id'] > max_id:
                max_id = item['item_id']
    return max_id + 1