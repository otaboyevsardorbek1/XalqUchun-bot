from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def categories_kb(categories):
    """Kategoriyalar ro'yxati uchun inline klaviatura"""
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat.name, callback_data=f"cat_{cat.id}")
    builder.adjust(1)
    return builder.as_markup()

def products_kb(products, category_id):
    builder = InlineKeyboardBuilder()
    for prod in products:
        builder.button(text=f"{prod.name}", callback_data=f"prod_{prod.id}")
    # Maxsus buyurtma tugmasi
    builder.button(text="📝 Maxsus buyurtma", callback_data="custom_order")
    builder.button(text="⬅️ Orqaga", callback_data=f"back_to_cat_{category_id}")
    builder.adjust(1)
    return builder.as_markup()

# def products_kb(products, category_id):
#     builder = InlineKeyboardBuilder()
#     for prod in products:
#         builder.button(text=f"{prod.name} - {prod.price} so'm", callback_data=f"prod_{prod.id}")
#     # Maxsus buyurtma tugmasi
#     builder.button(text="📝 Maxsus buyurtma", callback_data="custom_order")
#     builder.button(text="⬅️ Orqaga", callback_data=f"back_to_cat_{category_id}")
#     builder.adjust(1)
#     return builder.as_markup()