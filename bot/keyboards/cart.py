from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def cart_kb(cart_data: dict):
    builder = InlineKeyboardBuilder()
    for item_id, item in cart_data.items():
        if item['type'] == 'regular':
            # regular mahsulotlar uchun mahsulot nomini olish kerak, lekin bu yerda faqat item_id bor.
            # Buning uchun qo'shimcha ma'lumot kerak. Eng yaxshisi, cart_data da name saqlash.
            # Keling, regular mahsulotlar uchun ham name ni qo'shamiz.
            # utils/cart.py da add_to_cart ga name parametrini qo'shamiz.
            text = f"{item['name']} x{item['qty']} - {item['qty']*item['price']} so'm"
        else:
            text = f"{item['name']} x{item['qty']} {item['unit']} (maxsus)"
        builder.button(
            text=f"❌ {text}",
            callback_data=f"edit_{item_id}"
        )
    builder.button(text="✅ Buyurtma berish", callback_data="checkout")
    builder.button(text="⬅️ Orqaga", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()