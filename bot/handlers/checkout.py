from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from sqlalchemy import select
from typing import Union

from db.database import AsyncSessionLocal
from db.models import User, Order, OrderItem, Product
from states.checkout import Checkout
from utils.cart import get_cart, clear_cart
from config import ADMIN_IDS

router = Router()

@router.callback_query(F.data == "checkout")
@router.message(F.text == "✅ Buyurtma berish")
async def start_checkout(event: Union[types.Message, CallbackQuery], state: FSMContext):
    user_id = event.from_user.id
    cart = get_cart(user_id)
    if not cart:
        text = "Savat boʻsh. Avval mahsulot qoʻshing."
        if isinstance(event, CallbackQuery):
            await event.message.answer(text)
            await event.answer()
        else:
            await event.answer(text)
        return

    await state.update_data(cart=cart)
    await state.set_state(Checkout.waiting_for_phone)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    if isinstance(event, CallbackQuery):
        await event.message.answer("Iltimos, telefon raqamingizni yuboring:", reply_markup=kb)
        await event.answer()
    else:
        await event.answer("Iltimos, telefon raqamingizni yuboring:", reply_markup=kb)

@router.message(Checkout.waiting_for_phone, F.contact)
async def get_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone=phone)

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer("Endi joylashuvingizni yuboring:", reply_markup=kb)
    await state.set_state(Checkout.waiting_for_location)

@router.message(Checkout.waiting_for_location, F.location)
async def get_location(message: types.Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude
    location_link = f"https://www.google.com/maps?q={lat},{lon}"
    await state.update_data(location=location_link)

    data = await state.get_data()
    cart = data['cart']
    phone = data['phone']
    loc = data['location']

    async with AsyncSessionLocal() as session:
        product_ids = list(cart.keys())
        result = await session.execute(select(Product).where(Product.id.in_(product_ids)))
        products = {p.id: p.name for p in result.scalars().all()}

    lines = []
    total = 0
    for pid, item in cart.items():
        name = products.get(pid, "Noma'lum")
        subtotal = item['qty'] * item['price']
        lines.append(f"{name} x{item['qty']} = {subtotal} so'm")
        total += subtotal
    order_text = "Buyurtma:\n" + "\n".join(lines) + f"\nJami: {total} so'm"
    order_text += f"\n📞 {phone}\n📍 [Xarita]({loc})"

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_order")],
            [types.InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_order")]
        ]
    )
    await message.answer(order_text, reply_markup=kb, parse_mode="Markdown")
    await state.set_state(Checkout.confirming)

@router.callback_query(StateFilter(Checkout.confirming), F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data['cart']
    phone = data['phone']
    location = data['location']
    user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        # Foydalanuvchini bazaga qo'shish yoki yangilash
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(telegram_id=user_id, full_name=callback.from_user.full_name, phone=phone)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        else:
            user.phone = phone
            await session.commit()

        # Buyurtma yaratish
        order = Order(user_id=user.id, phone=phone, location_link=location)
        session.add(order)
        await session.flush()

        # Buyurtma mahsulotlarini qo'shish
        for pid, item in cart.items():
            order_item = OrderItem(
                order_id=order.id,
                product_id=pid,
                quantity=item['qty'],
                price=item['price']
            )
            session.add(order_item)

        await session.commit()

        # Mahsulot nomlarini olish
        product_ids = list(cart.keys())
        result = await session.execute(select(Product).where(Product.id.in_(product_ids)))
        products = {p.id: p.name for p in result.scalars().all()}

    # Savatni tozalash
    clear_cart(user_id)

    await callback.message.edit_text("✅ Buyurtmangiz qabul qilindi! Tez orada siz bilan bogʻlanamiz.")
    await callback.answer()

    # Adminlarga xabar yuborish
    admin_text = (
        f"🆕 Yangi buyurtma!\n"
        f"👤 {callback.from_user.full_name} (ID: {user_id})\n"
        f"📞 {phone}\n"
        f"📍 [Xarita]({location})\n"
        f"Buyurtma tarkibi:\n"
    )
    total = 0
    for pid, item in cart.items():
        name = products.get(pid, "Noma'lum")
        subtotal = item['qty'] * item['price']
        admin_text += f"{name} x{item['qty']} = {subtotal} so'm\n"
        total += subtotal
    admin_text += f"Jami: {total} so'm"

    for admin_id in ADMIN_IDS:
        try:
            await callback.bot.send_message(admin_id, admin_text, parse_mode="Markdown")
        except Exception as e:
            print(f"Admin {admin_id} ga xabar yuborilmadi: {e}")

    await state.clear()

@router.callback_query(StateFilter(Checkout.confirming), F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Buyurtma bekor qilindi.")
    await callback.answer()
    await state.clear()