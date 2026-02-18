from typing import Dict, Any, Optional

# Unikal custom ID uchun counter (manfiy sonlar)
_custom_id_counter = 0

def get_next_custom_id() -> int:
    """Maxsus mahsulotlar uchun unikal manfiy ID qaytaradi"""
    global _custom_id_counter
    _custom_id_counter -= 1
    return _custom_id_counter

# {user_id: {item_id: {"type": "regular"/"custom", "name": str, "qty": float, "unit": str, "price": float}}}
carts: Dict[int, Dict[Any, Dict]] = {}
def add_to_cart(user_id: int, item_id: Any, qty: float, price: float = 0, name: str = "", unit: str = "dona", item_type: str = "regular"):
    if user_id not in carts:
        carts[user_id] = {}
    if item_id in carts[user_id]:
        carts[user_id][item_id]["qty"] += qty
    else:
        if item_type == "regular":
            carts[user_id][item_id] = {"type": "regular", "name": name, "qty": qty, "price": price, "unit": "dona"}
        else:
            carts[user_id][item_id] = {"type": "custom", "name": name, "qty": qty, "unit": unit, "price": 0}
def get_cart(user_id: int) -> Dict[Any, Dict]:
    return carts.get(user_id, {})

def remove_from_cart(user_id: int, item_id: Any):
    if user_id in carts and item_id in carts[user_id]:
        del carts[user_id][item_id]

def clear_cart(user_id: int):
    if user_id in carts:
        del carts[user_id]

def update_cart_item_qty(user_id: int, item_id: Any, new_qty: float):
    if user_id in carts and item_id in carts[user_id]:
        carts[user_id][item_id]["qty"] = new_qty