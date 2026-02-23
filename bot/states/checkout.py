from aiogram.fsm.state import State, StatesGroup

class AddToCart(StatesGroup):
    waiting_for_quantity = State()

class Checkout(StatesGroup):
    waiting_for_phone = State()
    waiting_for_location = State()
    confirming = State()

class CustomOrder(StatesGroup):
    waiting_for_products = State()           # Maxsus buyurtma mahsulotlarini kiritish
    waiting_for_phone_choice = State()        # Telefon raqam tanlash
    waiting_for_contact = State()             # Telegram kontakt kutish
    waiting_for_custom_phone = State()        # Qo'lda telefon raqam kiritish
    waiting_for_confirm_products = State()     # Mahsulotlarni tasdiqlash
    waiting_for_location = State()             # Lokatsiya kutish
    confirming_order = State()                  # Buyurtmani tasdiqlash

class EditCustomItem(StatesGroup):
    waiting_for_new_quantity = State()  # maxsus mahsulot miqdorini o'zgartirish