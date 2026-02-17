# Foydalanuvchi savati: {user_id: {product_name: {"qty": qty, "price": price}}}
cart_data = {}

# Mahsulotni savatga qo‘shish
def add_to_cart(user_id, product, price=0, qty=1):
    if user_id not in cart_data:
        cart_data[user_id] = {}
    if product in cart_data[user_id]:
        cart_data[user_id][product]["qty"] += qty
    else:
        cart_data[user_id][product] = {"qty": qty, "price": price}

# Mahsulotni savatdan olib tashlash
def remove_from_cart(user_id, product):
    if user_id in cart_data and product in cart_data[user_id]:
        del cart_data[user_id][product]

# Foydalanuvchi savatini olish
def get_cart(user_id):
    return cart_data.get(user_id, {})

# Foydalanuvchi savatini tozalash
def clear_cart(user_id):
    if user_id in cart_data:
        cart_data[user_id] = {}
