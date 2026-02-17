from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛍 Katalog")],
        [KeyboardButton(text="🛒 Savat"), KeyboardButton(text="📞 Biz bilan bogʻlanish")]
    ],
    resize_keyboard=True
)