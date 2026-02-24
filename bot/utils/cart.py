# bot/utils/cart.py
from typing import Dict, Any, List, Optional
import json
import os
import logging
import uuid

logger = logging.getLogger(__name__)

CART_FILE = 'user_carts.json'

class CartManager:
    """Savat boshqaruvchisi"""
    
    def __init__(self):
        self.carts = self.load_carts()
    
    def load_carts(self) -> Dict[str, Any]:
        """Savat ma'lumotlarini yuklash"""
        try:
            if os.path.exists(CART_FILE):
                with open(CART_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading carts: {e}")
            return {}
    
    def save_carts(self) -> None:
        """Savat ma'lumotlarini saqlash"""
        try:
            with open(CART_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.carts, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving carts: {e}")
    
    def get_cart(self, user_id: int) -> Dict[int, Any]:
        """Foydalanuvchi savatini olish"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.carts:
            return {}
        
        cart = {}
        for key, value in self.carts[user_id_str].items():
            try:
                cart[int(key)] = value
            except ValueError:
                cart[key] = value
        return cart
    
    def add_to_cart(self, user_id: int, item_id: int, qty: float, price: float, 
                    name: str = None, unit: str = 'dona', item_type: str = "regular") -> bool:
        """Savatga mahsulot qo'shish"""
        try:
            user_id_str = str(user_id)
            
            if user_id_str not in self.carts:
                self.carts[user_id_str] = {}
            
            item_id_str = str(item_id)
            
            if item_id_str in self.carts[user_id_str]:
                self.carts[user_id_str][item_id_str]['qty'] += qty
            else:
                self.carts[user_id_str][item_id_str] = {
                    'qty': qty,
                    'price': price,
                    'name': name or f"Mahsulot {item_id}",
                    'unit': unit,
                    'item_type': item_type
                }
            
            self.save_carts()
            return True
        except Exception as e:
            logger.error(f"Error adding to cart: {e}")
            return False
    
    def remove_from_cart(self, user_id: int, item_id: int) -> bool:
        """Mahsulotni savatdan olib tashlash"""
        try:
            user_id_str = str(user_id)
            item_id_str = str(item_id)
            
            if user_id_str in self.carts and item_id_str in self.carts[user_id_str]:
                del self.carts[user_id_str][item_id_str]
                self.save_carts()
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing from cart: {e}")
            return False
    
    def update_cart_item_qty(self, user_id: int, item_id: int, new_qty: float) -> bool:
        """Savatdagi mahsulot miqdorini yangilash"""
        try:
            user_id_str = str(user_id)
            item_id_str = str(item_id)
            
            if user_id_str in self.carts and item_id_str in self.carts[user_id_str]:
                if new_qty <= 0:
                    return self.remove_from_cart(user_id, item_id)
                
                self.carts[user_id_str][item_id_str]['qty'] = new_qty
                self.save_carts()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating cart item: {e}")
            return False
    
    def clear_cart(self, user_id: int) -> bool:
        """Foydalanuvchi savatini tozalash"""
        try:
            user_id_str = str(user_id)
            
            if user_id_str in self.carts:
                self.carts[user_id_str] = {}
                self.save_carts()
                return True
            return False
        except Exception as e:
            logger.error(f"Error clearing cart: {e}")
            return False
    
    def get_cart_total(self, user_id: int) -> float:
        """Savatdagi mahsulotlarning umumiy narxini hisoblash"""
        cart = self.get_cart(user_id)
        total = 0.0
        
        for item_id, item in cart.items():
            if isinstance(item_id, int) and item_id > 0:
                total += item['qty'] * item['price']
        
        return total
    
    def get_cart_items_count(self, user_id: int) -> int:
        """Savatdagi mahsulotlar sonini qaytarish"""
        cart = self.get_cart(user_id)
        return len(cart)
    
    def get_next_custom_id(self) -> int:
        """Maxsus buyurtma uchun keyingi ID ni olish (manfiy)"""
        min_id = 0
        
        for user_items in self.carts.values():
            for item_id_str in user_items.keys():
                try:
                    item_id = int(item_id_str)
                    if item_id < 0 and item_id < min_id:
                        min_id = item_id
                except ValueError:
                    continue
        
        if min_id >= 0:
            return -1
        return min_id - 1
    
    def get_cart_items(self, user_id: int) -> List[Dict[str, Any]]:
        """Savatdagi barcha mahsulotlarni ro'yxat qilib qaytarish"""
        cart = self.get_cart(user_id)
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

# Global cart manager instance
_cart_manager = None

def get_cart_manager() -> CartManager:
    """CartManager instansini olish"""
    global _cart_manager
    if _cart_manager is None:
        _cart_manager = CartManager()
    return _cart_manager

# Eski funksiyalar bilan moslik uchun
def get_cart(user_id: int) -> Dict[int, Any]:
    return get_cart_manager().get_cart(user_id)

def add_to_cart(user_id: int, item_id: int, qty: float, price: float, 
                name: str = None, unit: str = 'dona', item_type: str = "regular") -> bool:
    return get_cart_manager().add_to_cart(user_id, item_id, qty, price, name, unit, item_type)

def remove_from_cart(user_id: int, item_id: int) -> bool:
    return get_cart_manager().remove_from_cart(user_id, item_id)

def update_cart_item_qty(user_id: int, item_id: int, new_qty: float) -> bool:
    return get_cart_manager().update_cart_item_qty(user_id, item_id, new_qty)

def clear_cart(user_id: int) -> bool:
    return get_cart_manager().clear_cart(user_id)

def get_next_custom_id() -> int:
    return get_cart_manager().get_next_custom_id()