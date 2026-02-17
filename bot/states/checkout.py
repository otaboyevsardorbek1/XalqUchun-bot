from aiogram.fsm.state import State, StatesGroup

class AddToCart(StatesGroup):
    waiting_for_quantity = State()

class Checkout(StatesGroup):
    waiting_for_phone = State()
    waiting_for_location = State()
    confirming = State()

class CustomOrder(StatesGroup):
    waiting_for_products = State()           # birinchi
    waiting_for_phone_choice = State()
    waiting_for_contact = State()
    waiting_for_custom_phone = State()
    waiting_for_location = State()
    confirming_order = State()                # tasdiqlash bosqichi

class EditCustomItem(StatesGroup):
    waiting_for_new_quantity = State()  # maxsus mahsulot miqdorini o'zgartirish