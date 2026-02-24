# bot/handlers/catalog.py
from aiogram import Router, types, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update
import asyncio
from typing import Union
from aiogram.types import Message, CallbackQuery
from bot.keyboards.main import get_main_menu, get_back_button
from bot.keyboards.catalog import categories_kb, products_kb, product_detail_kb
from bot.db.database import AsyncSessionLocal
from bot.db.models import Category, Product, CustomOrder, User
from bot.states.checkout import AddToCart, CustomOrder as CustomOrderState
from bot.utils.cart import add_to_cart, get_next_custom_id, get_cart_manager
from bot.utils.chat_action import with_typing_action, Actions, send_upload_photo_action
from bot.utils.helpers import format_price, parse_multiple_products, normalize_unit
from bot.data import ADMIN_IDS, ALL_OWNER_IDS
import logging
import re

router = Router()
logger = logging.getLogger(__name__)

# Foydalanuvchini bazaga qo'shish yoki yangilash
async def get_or_create_user(session, telegram_id: int, full_name: str = None, username: str = None):
    """Foydalanuvchini olish yoki yaratish"""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
            role="guest"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info(f"✅ Yangi foydalanuvchi: {telegram_id}")
    
    return user

async def update_user_phone(session, telegram_id: int, phone_number: str):
    """Foydalanuvchi telefon raqamini yangilash"""
    try:
        await session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(phone_number=phone_number, is_phone_verified=True)
        )
        await session.commit()
        logger.info(f"📞 Telefon yangilandi: {telegram_id}")
        return True
    except Exception as e:
        logger.error(f"Telefon yangilashda xato: {e}")
        return False

async def get_user_phone(session, telegram_id: int):
    """Foydalanuvchi telefon raqamini olish"""
    try:
        result = await session.execute(
            select(User.phone_number).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Telefon olishda xato: {e}")
        return None

@router.message(F.text == "🛍 Katalog")
@router.callback_query(F.data == "show_catalog")
@with_typing_action
async def show_categories(event: Union[Message, CallbackQuery]):
    """Kategoriyalarni ko'rsatish"""
    try:
        async with AsyncSessionLocal() as session:
            # Foydalanuvchini bazaga qo'shish
            user_id = event.from_user.id
            if isinstance(event, types.Message):
                await get_or_create_user(
                    session, user_id,
                    event.from_user.full_name,
                    event.from_user.username
                )
            
            result = await session.execute(select(Category))
            cats = result.scalars().all()
        
        text = "📋 *Kategoriyalar* 📋\n\nKerakli kategoriyani tanlang:"
        
        if not cats:
            text = "📭 *Hozircha kategoriyalar mavjud emas.*\n\nAgar o'zingiz istagan mahsulotni buyurtma qilmoqchi bo'lsangiz, quyidagi tugmani bosing:"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Maxsus buyurtma", callback_data="custom_order")],
                [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_to_main")]
            ])
        else:
            kb = categories_kb(cats)
        
        if isinstance(event, types.Message):
            await event.answer(text, parse_mode="Markdown", reply_markup=kb)
        else:
            await event.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
            await event.answer()
            
    except Exception as e:
        logger.error(f"Kategoriyalarni ko'rsatishda xato: {e}")
        error_msg = "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
        if isinstance(event, types.Message):
            await event.answer(error_msg)
        else:
            await event.message.answer(error_msg)
            await event.answer()

@router.callback_query(F.data.startswith("cat_"))
@with_typing_action
async def show_products(callback: CallbackQuery):
    """Kategoriyadagi mahsulotlarni ko'rsatish"""
    try:
        cat_id = int(callback.data.split("_")[1])
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Product).where(Product.category_id == cat_id)
            )
            prods = result.scalars().all()
            
            # Kategoriya nomini olish
            category = await session.get(Category, cat_id)
            cat_name = category.name if category else "Kategoriya"
        
        if not prods:
            text = f"📭 *{cat_name}* kategoriyasida hozircha mahsulot yo'q.\n\nAgar o'zingiz istagan mahsulotni buyurtma qilmoqchi bo'lsangiz, quyidagi tugmani bosing:"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Maxsus buyurtma", callback_data="custom_order")],
                [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_categories")]
            ])
        else:
            text = f"📦 *{cat_name}* kategoriyasidagi mahsulotlar:\n\nKerakli mahsulotni tanlang:"
            kb = products_kb(prods, cat_id)
        
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Mahsulotlarni ko'rsatishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data == "back_to_categories")
@with_typing_action
async def back_to_categories(callback: CallbackQuery):
    """Kategoriyalarga qaytish"""
    await show_categories(callback)

@router.callback_query(F.data.startswith("prod_"))
@with_typing_action
async def product_detail(callback: CallbackQuery, state: FSMContext):
    """Mahsulot detallarini ko'rsatish"""
    try:
        prod_id = int(callback.data.split("_")[1])
        async with AsyncSessionLocal() as session:
            product = await session.get(Product, prod_id)
            if not product:
                await callback.answer("❌ Mahsulot topilmadi", show_alert=True)
                return
            
            await state.update_data(
                selected_product_id=prod_id,
                product_price=product.price,
                product_name=product.name,
                category_id=product.category_id,
                quantity=1
            )
        
        price_str = format_price(product.price)
        text = (
            f"📦 *{product.name}*\n\n"
            f"💰 *Narxi:* {price_str} so'm\n"
            f"📝 *Ta'rif:* {product.description or 'Tarif mavjud emas'}\n\n"
            f"🔢 *Miqdorni tanlang:*"
        )
        
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=product_detail_kb(prod_id, product.category_id, 1)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Mahsulot detallarida xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data.startswith("qty_inc_"))
async def increase_quantity(callback: CallbackQuery, state: FSMContext):
    """Miqdorni oshirish"""
    try:
        prod_id = int(callback.data.split("_")[2])
        data = await state.get_data()
        current_qty = data.get('quantity', 1)
        new_qty = current_qty + 1
        max_qty = 99  # Maksimal miqdor
        
        if new_qty <= max_qty:
            await state.update_data(quantity=new_qty)
            await callback.message.edit_reply_markup(
                reply_markup=product_detail_kb(
                    prod_id,
                    data.get('category_id', 0),
                    new_qty
                )
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Miqdorni oshirishda xato: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)

@router.callback_query(F.data.startswith("qty_dec_"))
async def decrease_quantity(callback: CallbackQuery, state: FSMContext):
    """Miqdorni kamaytirish"""
    try:
        prod_id = int(callback.data.split("_")[2])
        data = await state.get_data()
        current_qty = data.get('quantity', 1)
        
        if current_qty > 1:
            new_qty = current_qty - 1
            await state.update_data(quantity=new_qty)
            await callback.message.edit_reply_markup(
                reply_markup=product_detail_kb(
                    prod_id,
                    data.get('category_id', 0),
                    new_qty
                )
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Miqdorni kamaytirishda xato: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)

@router.callback_query(F.data.startswith("add_to_cart_"))
async def add_to_cart_handler(callback: CallbackQuery, state: FSMContext):
    """Savatga qo'shish"""
    try:
        # Upload photo action
        await send_upload_photo_action(callback.bot, callback.from_user.id)
        
        data = await state.get_data()
        quantity = data.get('quantity', 1)
        name = data.get('product_name')
        price = data.get('product_price')
        prod_id = data.get('selected_product_id')
        
        # Savatga qo'shish
        success = add_to_cart(
            callback.from_user.id,
            prod_id,
            quantity,
            price,
            name=name,
            item_type="regular"
        )
        
        if success:
            cart_manager = get_cart_manager()
            cart_total = cart_manager.get_cart_total(callback.from_user.id)
            total_items = cart_manager.get_cart_items_count(callback.from_user.id)
            price_str = format_price(price * quantity)
            
            text = f"""
✅ *{name}* savatga qo'shildi!

📦 *Miqdor:* {quantity} dona
💰 *Summa:* {price_str} so'm

🛒 *Savatda:* {total_items} ta mahsulot
💰 *Jami:* {format_price(cart_total)} so'm
            """
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Savatni ko'rish", callback_data="view_cart")],
                [InlineKeyboardButton(text="⬅️ Katalogga qaytish", callback_data="back_to_categories")],
                [InlineKeyboardButton(text="✅ Buyurtma berish", callback_data="checkout")]
            ])
            
            await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        else:
            await callback.message.answer("❌ Savatga qo'shishda xatolik yuz berdi.")
        
        await state.clear()
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Savatga qo'shishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data.startswith("back_to_cat_"))
@with_typing_action
async def back_to_category(callback: CallbackQuery):
    """Kategoriyaga qaytish"""
    try:
        cat_id = int(callback.data.split("_")[3])
        # Kategoriyadagi mahsulotlarni ko'rsatish
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Product).where(Product.category_id == cat_id)
            )
            prods = result.scalars().all()
            
            category = await session.get(Category, cat_id)
            cat_name = category.name if category else "Kategoriya"
        
        text = f"📦 *{cat_name}* kategoriyasidagi mahsulotlar:\n\nKerakli mahsulotni tanlang:"
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=products_kb(prods, cat_id)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Kategoriyaga qaytishda xato: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)

# ========== MAXSUS BUYURTMA ==========

@router.callback_query(F.data == "custom_order")
@with_typing_action
async def custom_order_start(callback: CallbackQuery, state: FSMContext):
    """Maxsus buyurtma boshlash"""
    try:
        async with AsyncSessionLocal() as session:
            phone = await get_user_phone(session, callback.from_user.id)
        
        if phone:
            await state.update_data(user_phone=phone)
            await state.set_state(CustomOrderState.waiting_for_products)
            text = """
📝 *MAXSUS BUYURTMA*

Iltimos, buyurtmangizni quyidagi formatda yozing:

`Mahsulot nomi - miqdor birlik`

*Masalan:*
• Olma - 2 kg
• Non - 1 dona
• Sut - 2 litr

✅ *Bir nechta mahsulotni* yangi qatordan yoki vergul bilan yozishingiz mumkin:
`Olma - 2 kg, Non - 1 dona, Sut - 2 litr`

⚠️ Mahsulot nomi va miqdor orasida tire (-) bo'lishi shart.
            """
            await callback.message.edit_text(text, parse_mode="Markdown")
        else:
            await state.set_state(CustomOrderState.waiting_for_phone_choice)
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📱 Telegram raqam", callback_data="custom_phone_telegram")],
                [InlineKeyboardButton(text="📞 Maxsus raqam", callback_data="custom_phone_manual")],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")]
            ])
            
            await callback.message.edit_text(
                "📞 *Maxsus buyurtma berish uchun telefon raqamingiz kerak.*\n\nTelefon raqamingizni qanday yuborasiz?",
                parse_mode="Markdown",
                reply_markup=kb
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Maxsus buyurtma boshlashda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data == "custom_phone_telegram")
@with_typing_action
async def custom_phone_telegram(callback: CallbackQuery, state: FSMContext):
    """Telegram orqali telefon raqam yuborish"""
    try:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await callback.message.delete()
        await callback.message.answer(
            "📱 *Telefon raqamingizni yuborish tugmasini bosing*",
            parse_mode="Markdown",
            reply_markup=kb
        )
        await state.set_state(CustomOrderState.waiting_for_contact)
        await callback.answer()
    except Exception as e:
        logger.error(f"Telefon tanlashda xato: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)

@router.callback_query(F.data == "custom_phone_manual")
@with_typing_action
async def custom_phone_manual(callback: CallbackQuery, state: FSMContext):
    """Qo'lda telefon raqam kiritish"""
    try:
        await callback.message.delete()
        await callback.message.answer(
            "📞 *Telefon raqamingizni kiriting:*\n\n"
            "Format: `+998 XX XXX XX XX`\n"
            "Masalan: `+998 90 123 45 67`",
            parse_mode="Markdown"
        )
        await state.set_state(CustomOrderState.waiting_for_custom_phone)
        await callback.answer()
    except Exception as e:
        logger.error(f"Qo'lda telefon kiritishda xato: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)

@router.message(CustomOrderState.waiting_for_contact, F.contact)
async def custom_contact_received(message: types.Message, state: FSMContext):
    """Telegram kontakt qabul qilish"""
    try:
        phone = message.contact.phone_number
        
        async with AsyncSessionLocal() as session:
            success = await update_user_phone(session, message.from_user.id, phone)
            
            if not success:
                await message.answer("❌ Telefon raqam saqlashda xatolik yuz berdi.")
                return
        
        await state.update_data(user_phone=phone)
        await state.set_state(CustomOrderState.waiting_for_products)
        
        text = """
📝 *MAXSUS BUYURTMA*

✅ Telefon raqam saqlandi!

Endi buyurtmangizni quyidagi formatda yozing:

`Mahsulot nomi - miqdor birlik`

*Masalan:*
• Olma - 2 kg
• Non - 1 dona
• Sut - 2 litr

✅ *Bir nechta mahsulotni* yangi qatordan yoki vergul bilan yozishingiz mumkin.
        """
        
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=types.ReplyKeyboardRemove()
        )
        
    except Exception as e:
        logger.error(f"Kontakt qabul qilishda xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

@router.message(CustomOrderState.waiting_for_custom_phone)
async def custom_phone_received(message: types.Message, state: FSMContext):
    """Qo'lda kiritilgan telefon raqamni qabul qilish"""
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
        
        async with AsyncSessionLocal() as session:
            success = await update_user_phone(session, message.from_user.id, cleaned_phone)
            
            if not success:
                await message.answer("❌ Telefon raqam saqlashda xatolik yuz berdi.")
                return
        
        await state.update_data(user_phone=cleaned_phone)
        await state.set_state(CustomOrderState.waiting_for_products)
        
        text = """
📝 *MAXSUS BUYURTMA*

✅ Telefon raqam saqlandi!

Endi buyurtmangizni quyidagi formatda yozing:

`Mahsulot nomi - miqdor birlik`

*Masalan:*
• Olma - 2 kg
• Non - 1 dona
• Sut - 2 litr
        """
        
        await message.answer(text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Telefon raqam qabul qilishda xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

@router.message(CustomOrderState.waiting_for_products)
async def process_custom_products(message: types.Message, state: FSMContext):
    """Maxsus buyurtma mahsulotlarini qayta ishlash"""
    try:
        from bot.utils.helpers import parse_multiple_products, normalize_unit
        
        text = message.text.strip()
        products, errors = parse_multiple_products(text)
        
        # Birliklarni normallashtirish
        for product in products:
            product['unit'] = normalize_unit(product['unit'])
        
        if errors:
            error_text = "❌ *Quyidagi qatorlarda xato bor:*\n\n"
            for error in errors[:5]:
                error_text += f"• {error}\n"
            
            if len(errors) > 5:
                error_text += f"\n... va yana {len(errors) - 5} ta xato"
            
            error_text += "\n\n📝 Iltimos, to'g'ri formatda qayta yozing."
            
            await message.answer(error_text, parse_mode="Markdown")
            return
        
        if not products:
            await message.answer(
                "❌ *Hech qanday mahsulot kiritilmadi.*\n\n"
                "Iltimos, quyidagi formatda mahsulotlarni kiriting:\n"
                "`Mahsulot nomi - miqdor birlik`\n\n"
                "Masalan: `Olma - 2 kg`",
                parse_mode="Markdown"
            )
            return
        
        # Mahsulotlarni state ga saqlash
        await state.update_data(custom_products=products)
        
        # Mahsulotlar ro'yxatini ko'rsatish
        products_text = ""
        for i, p in enumerate(products, 1):
            products_text += f"{i}. *{p['name']}*: {p['quantity']} {p['unit']}\n"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Davom etish", callback_data="custom_continue_to_location")],
            [InlineKeyboardButton(text="🔄 Qayta yozish", callback_data="custom_retry_products")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="custom_cancel")]
        ])
        
        await message.answer(
            f"📝 *Kiritilgan mahsulotlar ({len(products)} ta):*\n\n{products_text}\n\n"
            "✅ Mahsulotlar to'g'ri kiritilgan bo'lsa, davom eting.",
            parse_mode="Markdown",
            reply_markup=kb
        )
        await state.set_state(CustomOrderState.waiting_for_confirm_products)
        
    except Exception as e:
        logger.error(f"Mahsulotlarni qayta ishlashda xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

@router.callback_query(F.data == "custom_continue_to_location")
@with_typing_action
async def custom_continue_to_location(callback: CallbackQuery, state: FSMContext):
    """Lokatsiya so'rash"""
    try:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await callback.message.delete()
        await callback.message.answer(
            "📍 *Iltimos, joylashuvingizni yuboring:*\n\n"
            "Joylashuvni yuborish uchun pastdagi tugmani bosing.",
            parse_mode="Markdown",
            reply_markup=kb
        )
        await state.set_state(CustomOrderState.waiting_for_location)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Lokatsiya so'rashda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data == "custom_retry_products")
@with_typing_action
async def custom_retry_products(callback: CallbackQuery, state: FSMContext):
    """Mahsulotlarni qayta yozish"""
    try:
        await state.set_state(CustomOrderState.waiting_for_products)
        await callback.message.edit_text(
            "📝 *Mahsulotlarni qayta kiriting:*\n\n"
            "Format: `Mahsulot nomi - miqdor birlik`",
            parse_mode="Markdown"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Qayta yozishda xato: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)

@router.callback_query(F.data == "custom_cancel")
async def custom_cancel(callback: CallbackQuery, state: FSMContext):
    """Buyurtmani bekor qilish"""
    try:
        await state.clear()
        await callback.message.edit_text("❌ Buyurtma bekor qilindi.")
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="back_to_main")]
        ])
        
        await callback.message.answer(
            "🏠 *Asosiy menyu:*",
            parse_mode="Markdown",
            reply_markup=kb
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Bekor qilishda xato: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)

@router.message(CustomOrderState.waiting_for_location, F.location)
async def custom_location_received(message: types.Message, state: FSMContext):
    """Lokatsiya qabul qilish"""
    try:
        from bot.utils.chat_action import send_find_location_action
        
        await send_find_location_action(message.bot, message.chat.id)
        
        lat = message.location.latitude
        lon = message.location.longitude
        location_link = f"https://www.google.com/maps?q={lat},{lon}"
        
        await state.update_data(location=location_link, location_coords=f"{lat},{lon}")
        
        data = await state.get_data()
        products = data['custom_products']
        phone = data['user_phone']
        
        from bot.utils.helpers import format_phone_for_display
        phone_display = format_phone_for_display(phone)
        
        products_text = ""
        for p in products:
            products_text += f"• *{p['name']}*: {p['quantity']} {p['unit']}\n"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="custom_confirm_yes")],
            [InlineKeyboardButton(text="🔄 Qayta boshlash", callback_data="custom_retry_all")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="custom_cancel")]
        ])
        
        await message.answer(
            f"📦 *BUYURTMA MA'LUMOTLARI*\n\n"
            f"{products_text}\n"
            f"📞 *Telefon:* {phone_display}\n"
            f"📍 *Lokatsiya:* [Xaritada ko'rish]({location_link})\n\n"
            "✅ Buyurtmani tasdiqlaysizmi?",
            parse_mode="Markdown",
            reply_markup=kb,
            disable_web_page_preview=True
        )
        
        await message.answer("⏳...", reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(CustomOrderState.confirming_order)
        
    except Exception as e:
        logger.error(f"Lokatsiya qabul qilishda xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

@router.message(CustomOrderState.waiting_for_location)
async def custom_location_invalid(message: types.Message):
    """Noto'g'ri lokatsiya"""
    await message.answer(
        "❌ *Iltimos, joylashuvni yuborish tugmasidan foydalaning.*\n\n"
        "📍 Joylashuvni yuborish uchun pastdagi tugmani bosing.",
        parse_mode="Markdown"
    )

@router.callback_query(CustomOrderState.confirming_order, F.data == "custom_confirm_yes")
async def custom_confirm_yes(callback: CallbackQuery, state: FSMContext):
    """Buyurtmani tasdiqlash"""
    try:
        from bot.utils.chat_action import send_action, Actions
        
        await send_action(callback.bot, callback.from_user.id, Actions.UPLOAD_DOCUMENT, 1)
        
        data = await state.get_data()
        products = data['custom_products']
        phone = data['user_phone']
        location = data['location']
        location_coords = data.get('location_coords', '')
        user_id = callback.from_user.id
        
        # Maxsus ID lar yaratish
        from bot.utils.helpers import generate_order_number
        
        # Maxsus mahsulotlarni savatga qo'shish
        for p in products:
            custom_id = get_next_custom_id()
            add_to_cart(
                user_id=user_id,
                item_id=custom_id,
                qty=p['quantity'],
                price=0,
                name=p['name'],
                unit=p['unit'],
                item_type="custom"
            )
        
        # Maxsus buyurtmani bazaga saqlash
        try:
            async with AsyncSessionLocal() as session:
                for p in products:
                    custom_order = CustomOrder(
                        user_id=user_id,
                        product_name=p['name'],
                        quantity=p['quantity'],
                        unit=p['unit'],
                        phone_number=phone,
                        location=location,
                        location_coords=location_coords,
                        status='pending'
                    )
                    session.add(custom_order)
                await session.commit()
                logger.info(f"✅ Maxsus buyurtma saqlandi: {user_id}")
            
            text = """
✅ *BUYURTMANGIZ QABUL QILINDI!*

📦 Mahsulotlaringiz savatga qo'shildi.

Endi quyidagi amallarni bajaring:
1️⃣ 🛒 *Savatni ko'rish* tugmasini bosing
2️⃣ ✅ *Buyurtma berish* ni tanlang
3️⃣ Buyurtmani yakunlang

🎁 *Eslatma:* Maxsus buyurtmalar admin tomonidan tekshiriladi.
            """
            
        except Exception as e:
            logger.error(f"Maxsus buyurtmani saqlashda xato: {e}")
            text = """
✅ *BUYURTMANGIZ SAVATGA QO'SHILDI!*

📦 Mahsulotlaringiz savatga qo'shildi.

🛒 Savatni ko'rish va buyurtmani yakunlash uchun quyidagi tugmani bosing.
            """
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Savatni ko'rish", callback_data="view_cart")],
            [InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="back_to_main")]
        ])
        
        await callback.message.edit_text(text, parse_mode="Markdown")
        await callback.message.answer("👇", reply_markup=kb)
        
        await state.clear()
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Buyurtmani tasdiqlashda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(CustomOrderState.confirming_order, F.data == "custom_retry_all")
@with_typing_action
async def custom_retry_all(callback: CallbackQuery, state: FSMContext):
    """Boshidan boshlash"""
    try:
        await state.set_state(CustomOrderState.waiting_for_products)
        await callback.message.edit_text(
            "📝 *Iltimos, buyurtmangizni qayta kiriting:*\n\n"
            "Format: `Mahsulot nomi - miqdor birlik`",
            parse_mode="Markdown"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Qayta boshlashda xato: {e}")
        await callback.answer("❌ Xatolik", show_alert=True)

#================================================================================
# add new funqtions for cart keyboard here

# bot/keyboards/cart.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Dict, Any, List

def cart_kb(cart_items: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Savat tugmalari"""
    builder = InlineKeyboardBuilder()
    
    for item in cart_items:
        if item['type'] == 'regular':
            text = f"❌ {item['name']} ({item['qty']} dona)"
        else:
            text = f"❌ {item['name']} ({item['qty']} {item['unit']})"
        
        builder.button(text=text, callback_data=f"remove_{item['id']}")
    
    builder.button(text="✅ Buyurtma berish", callback_data="checkout")
    builder.button(text="🔄 Savatni tozalash", callback_data="clear_cart")
    builder.button(text="🔙 Orqaga", callback_data="back_to_main")
    
    builder.adjust(1)
    return builder.as_markup()

def edit_custom_item_kb(custom_id: int) -> InlineKeyboardMarkup:
    """Maxsus mahsulotni tahrirlash tugmalari"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"edit_delete_{custom_id}"),
        InlineKeyboardButton(text="✏️ Miqdorni o'zgartirish", callback_data=f"edit_qty_{custom_id}")
    )
    
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_cart"))
    
    return builder.as_markup()