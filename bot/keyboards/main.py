from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛍 Katalog")],
        [KeyboardButton(text="🛒 Savat")],
        [KeyboardButton(text="📞 Biz bilan bogʻlanish")]
    ],
    resize_keyboard=True
)

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛍 Katalog")],
        [KeyboardButton(text="🛒 Savat")],
        [KeyboardButton(text="📞 Biz bilan bogʻlanish")],
        [KeyboardButton(text="Admin panel")]
    ],
    resize_keyboard=True
)
