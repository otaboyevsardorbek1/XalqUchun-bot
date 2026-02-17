from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def products_keyboard(category, products_list):
    kb = InlineKeyboardMarkup(row_width=1)
    for p in products_list:
        # Har bir mahsulot tugmasi: nomi + narxi
        kb.add(
            InlineKeyboardButton(
                text=f"{p['name']} - {p['price']} so'm",
                callback_data=f"prod_{p['id']}"
            )
        )
    # Orqaga tugma
    kb.add(InlineKeyboardButton("⬅️ Orqaga", callback_data="show_categories"))
    return kb
