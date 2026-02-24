# bot/handlers/checkout.py
from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from typing import Union
import asyncio
from bot.keyboards.main import get_main_menu, get_confirmation_keyboard, get_back_button
from bot.db.database import AsyncSessionLocal
from bot.db.models import User, Order, OrderItem, Product
from bot.states.checkout import Checkout
from bot.utils.cart import get_cart_manager, clear_cart
from bot.utils.chat_action import with_typing_action, send_find_location_action, send_typing_action
from bot.utils.helpers import format_price, format_phone_for_display, generate_order_number
from bot.data import ADMIN_IDS
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "checkout")
@router.message(F.text == "✅ Buyurtma berish")
@with_typing_action
async def start_checkout(event: Union[types.Message, CallbackQuery], state: FSMContext):
    """Buyurtma berishni boshlash"""
    try:
        user_id = event.from_user.id
        cart_manager = get_cart_manager()
        cart = cart_manager.get_cart(user_id)
        
        if not cart:
            text = "🛒 *Savatingiz bo'sh* 🛒\n\nAvval mahsulot qo'shing."
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛍 Katalog", callback_data="show_catalog")],
                [InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="back_to_main")]
            ])
            
            if isinstance(event, CallbackQuery):
                await event.message.answer(text, parse_mode="Markdown", reply_markup=kb)
                await event.answer()
            else:
                await event.answer(text, parse_mode="Markdown", reply_markup=kb)
            return
        
        # Avval foydalanuvchi telefon raqamini tekshirish
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user and user.phone_number:
                # Telefon raqam bor, to'g'ridan-to'g'ri lokatsiya so'rash
                await state.update_data(
                    cart=cart,
                    phone=user.phone_number
                )
                await state.set_state(Checkout.waiting_for_location)
                
                kb = ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True)]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
                
                text = f"""
📞 *Telefon raqamingiz:* {format_phone_for_display(user.phone_number)}

📍 Endi joylashuvingizni yuboring:
                """
                
                if isinstance(event, CallbackQuery):
                    await event.message.answer(text, parse_mode="Markdown", reply_markup=kb)
                    await event.answer()
                else:
                    await event.answer(text, parse_mode="Markdown", reply_markup=kb)
                return
        
        # Telefon raqam yo'q, so'rash
        await state.update_data(cart=cart)
        await state.set_state(Checkout.waiting_for_phone)
        
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        text = """
📞 *Iltimos, telefon raqamingizni yuboring:*

Telefon raqamingizni yuborish tugmasini bosing yoki qo'lda kiriting:
Format: `+998 XX XXX XX XX`
        """
        
        if isinstance(event, CallbackQuery):
            await event.message.answer(text, parse_mode="Markdown", reply_markup=kb)
            await event.answer()
        else:
            await event.answer(text, parse_mode="Markdown", reply_markup=kb)
            
    except Exception as e:
        logger.error(f"Buyurtma boshlashda xato: {e}")
        error_msg = "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
        if isinstance(event, CallbackQuery):
            await event.message.answer(error_msg)
            await event.answer()
        else:
            await event.answer(error_msg)

@router.message(Checkout.waiting_for_phone, F.contact)
@with_typing_action
async def get_phone_contact(message: types.Message, state: FSMContext):
    """Telefon raqamni kontakt orqali olish"""
    try:
        phone = message.contact.phone_number
        
        # Telefon raqamni saqlash
        async with AsyncSessionLocal() as session:
            user = await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
            user = user.scalar_one_or_none()
            
            if user:
                user.phone_number = phone
                user.is_phone_verified = True
                await session.commit()
        
        await state.update_data(phone=phone)
        await state.set_state(Checkout.waiting_for_location)
        
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await message.answer(
            f"✅ Telefon raqam saqlandi: {format_phone_for_display(phone)}\n\n📍 Endi joylashuvingizni yuboring:",
            parse_mode="Markdown",
            reply_markup=kb
        )
        
    except Exception as e:
        logger.error(f"Telefon raqam olishda xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

@router.message(Checkout.waiting_for_phone)
@with_typing_action
async def get_phone_text(message: types.Message, state: FSMContext):
    """Telefon raqamni matn orqali olish"""
    try:
        from bot.utils.helpers import validate_uz_phone
        
        phone = message.text.strip()
        is_valid, cleaned_phone = validate_uz_phone(phone)
        
        if not is_valid:
            await message.answer(
                "❌ *Noto'g'ri format.*\n\n"
                "Iltimos, telefon raqamingizni quyidagi formatda kiriting:\n"
                "`+998 XX XXX XX XX`\n\n"
                "Masalan: `+998 90 123 45 67`",
                parse_mode="Markdown"
            )
            return
        
        # Telefon raqamni saqlash
        async with AsyncSessionLocal() as session:
            user = await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
            user = user.scalar_one_or_none()
            
            if user:
                user.phone_number = cleaned_phone
                user.is_phone_verified = True
                await session.commit()
        
        await state.update_data(phone=cleaned_phone)
        await state.set_state(Checkout.waiting_for_location)
        
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await message.answer(
            f"✅ Telefon raqam saqlandi: {format_phone_for_display(cleaned_phone)}\n\n📍 Endi joylashuvingizni yuboring:",
            parse_mode="Markdown",
            reply_markup=kb
        )
        
    except Exception as e:
        logger.error(f"Telefon raqam olishda xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

@router.message(Checkout.waiting_for_location, F.location)
async def get_location(message: types.Message, state: FSMContext):
    """Lokatsiyani olish"""
    try:
        await send_find_location_action(message.bot, message.chat.id)
        
        lat = message.location.latitude
        lon = message.location.longitude
        location_link = f"https://www.google.com/maps?q={lat},{lon}"
        
        await state.update_data(
            location=location_link,
            location_coords=f"{lat},{lon}"
        )
        
        data = await state.get_data()
        cart = data['cart']
        phone = data['phone']
        
        # Mahsulot nomlarini olish
        product_ids = [pid for pid in cart.keys() if pid > 0]
        products = {}
        if product_ids:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Product).where(Product.id.in_(product_ids))
                )
                products = {p.id: p.name for p in result.scalars().all()}
        
        # Buyurtma tarkibini tayyorlash
        lines = []
        total = 0
        
        for pid, item in cart.items():
            if pid > 0:
                name = products.get(pid, item.get('name', 'Noma\'lum'))
                subtotal = item['qty'] * item['price']
                total += subtotal
                lines.append(f"• *{name}*: {item['qty']} dona × {format_price(item['price'])} = {format_price(subtotal)} so'm")
            else:
                name = item['name']
                lines.append(f"• 📦 *{name}*: {item['qty']} {item['unit']} (maxsus)")
        
        total_str = format_price(total) if total > 0 else "0 so'm"
        
        order_text = f"""
📦 *BUYURTMA TARKIBI*
{'-' * 30}
{chr(10).join(lines)}
{'-' * 30}
💰 *Jami: {total_str}*

📞 *Telefon:* {format_phone_for_display(phone)}
📍 *Lokatsiya:* [Xaritada ko'rish]({location_link})

Buyurtmani tasdiqlaysizmi?
        """
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_order")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_order")]
        ])
        
        await message.answer(
            order_text,
            parse_mode="Markdown",
            reply_markup=kb,
            disable_web_page_preview=True
        )
        
        # Reply keyboardni olib tashlash
        await message.answer("⏳...", reply_markup=types.ReplyKeyboardRemove())
        
        await state.set_state(Checkout.confirming)
        
    except Exception as e:
        logger.error(f"Lokatsiya olishda xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

@router.message(Checkout.waiting_for_location)
async def location_invalid(message: types.Message):
    """Noto'g'ri lokatsiya"""
    await message.answer(
        "❌ *Iltimos, joylashuvni yuborish tugmasidan foydalaning.*\n\n"
        "📍 Joylashuvni yuborish uchun pastdagi tugmani bosing.",
        parse_mode="Markdown"
    )

@router.callback_query(StateFilter(Checkout.confirming), F.data == "confirm_order")
@with_typing_action
async def confirm_order(callback: CallbackQuery, state: FSMContext):
    """Buyurtmani tasdiqlash"""
    try:
        data = await state.get_data()
        cart = data['cart']
        phone = data['phone']
        location = data['location']
        location_coords = data.get('location_coords', '')
        user_id = callback.from_user.id
        
        # Buyurtma raqamini yaratish
        order_number = generate_order_number()
        
        async with AsyncSessionLocal() as session:
            # Foydalanuvchini topish yoki yaratish
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                user = User(
                    telegram_id=user_id,
                    full_name=callback.from_user.full_name,
                    phone_number=phone,
                    is_phone_verified=True
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            else:
                user.phone_number = phone
                user.is_phone_verified = True
                await session.commit()
            
            # Buyurtma yaratish
            total_amount = 0
            for pid, item in cart.items():
                if pid > 0:
                    total_amount += item['qty'] * item['price']
            
            order = Order(
                order_number=order_number,
                user_id=user.id,
                phone=phone,
                location_link=location,
                location_coords=location_coords,
                total_amount=total_amount,
                status='new'
            )
            session.add(order)
            await session.flush()  # order.id olish uchun
            
            # Mahsulotlarni qo'shish
            for pid, item in cart.items():
                if pid > 0:
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=pid,
                        product_name=item['name'],
                        quantity=item['qty'],
                        price=item['price'],
                        unit='dona',
                        is_custom=False
                    )
                else:
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=None,
                        product_name=item['name'],
                        quantity=item['qty'],
                        price=0,
                        unit=item['unit'],
                        is_custom=True
                    )
                session.add(order_item)
            
            await session.commit()
        
        # Savatni tozalash
        cart_manager = get_cart_manager()
        cart_manager.clear_cart(user_id)
        
        # Foydalanuvchiga xabar
        text = f"""
✅ *BUYURTMANGIZ QABUL QILINDI!*

📋 *Buyurtma raqami:* `{order_number}`
💰 *Umumiy summa:* {format_price(total_amount)} so'm
📞 *Telefon:* {format_phone_for_display(phone)}

⏳ Tez orada operatorlarimiz siz bilan bog'lanadi.

Buyurtma holatini kuzatish uchun admin bilan bog'lanishingiz mumkin.
        """
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Yangi buyurtma", callback_data="show_catalog")],
            [InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="back_to_main")]
        ])
        
        await callback.message.edit_text(text, parse_mode="Markdown")
        await callback.message.answer("👇", reply_markup=kb)
        
        # Adminlarga xabar yuborish
        await notify_admins(callback.bot, order, cart, user_id, callback.from_user.full_name)
        
        await state.clear()
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Buyurtmani tasdiqlashda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(StateFilter(Checkout.confirming), F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    """Buyurtmani bekor qilish"""
    try:
        await state.clear()
        await callback.message.edit_text("❌ Buyurtma bekor qilindi.")
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Katalog", callback_data="show_catalog")],
            [InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="back_to_main")]
        ])
        
        await callback.message.answer("👇", reply_markup=kb)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Buyurtmani bekor qilishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

async def notify_admins(bot, order, cart, user_id, user_name):
    """Adminlarga xabar yuborish"""
    try:
        # Mahsulot nomlarini olish
        product_ids = [pid for pid in cart.keys() if pid > 0]
        products = {}
        if product_ids:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Product).where(Product.id.in_(product_ids))
                )
                products = {p.id: p.name for p in result.scalars().all()}
        
        # Buyurtma tarkibi
        items_text = ""
        total = 0
        for pid, item in cart.items():
            if pid > 0:
                name = products.get(pid, item.get('name', 'Noma\'lum'))
                subtotal = item['qty'] * item['price']
                total += subtotal
                items_text += f"• {name} x{item['qty']} = {format_price(subtotal)} so'm\n"
            else:
                items_text += f"• 📦 {item['name']} x{item['qty']} {item['unit']}\n"
        
        admin_text = f"""
🆕 *YANGI BUYURTMA!*
{'-' * 30}

👤 *Mijoz:* {user_name}
🆔 *ID:* {user_id}
📞 *Telefon:* {order.phone}
📍 *Lokatsiya:* [Xarita]({order.location_link})

📦 *Buyurtma tarkibi:*
{items_text}
{'-' * 30}
💰 *Jami:* {format_price(order.total_amount)} so'm
📋 *Buyurtma raqami:* `{order.order_number}`
🕐 *Vaqt:* {order.created_at.strftime('%d.%m.%Y %H:%M')}
        """
        
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    admin_text,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"Admin {admin_id} ga xabar yuborilmadi: {e}")
                
    except Exception as e:
        logger.error(f"Adminlarga xabar yuborishda xato: {e}")