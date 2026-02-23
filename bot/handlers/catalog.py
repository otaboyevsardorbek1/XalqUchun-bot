from aiogram import Router, types, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
import re
from bot.keyboards.main import main_menu
from bot.db.database import AsyncSessionLocal
from bot.db.models import Category, Product, CustomOrder
from bot.keyboards.catalog import categories_kb, products_kb
from bot.states.checkout import AddToCart, CustomOrder as CustomOrderState
from bot.utils.cart import add_to_cart, get_next_custom_id
import logging

router = Router()
logger = logging.getLogger(__name__)

# Kategoriyalarni ko'rsatish
@router.message(F.text == "🛍 Katalog")
async def show_categories(message: types.Message):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Category))
        cats = result.scalars().all()
        if not cats:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Maxsus buyurtma", callback_data="custom_order")]
            ])
            await message.answer(
                "Hozircha kategoriyalar mavjud emas.\n"
                "Agar o'zingiz istagan mahsulotni buyurtma qilmoqchi bo'lsangiz, quyidagi tugmani bosing.",
                reply_markup=kb
            )
            return
    await message.answer("Kategoriyani tanlang:", reply_markup=categories_kb(cats))

@router.callback_query(F.data.startswith("cat_"))
async def show_products(callback: CallbackQuery):
    cat_id = int(callback.data.split("_")[1])
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Product).where(Product.category_id == cat_id))
        prods = result.scalars().all()
    if not prods:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Maxsus buyurtma", callback_data="custom_order")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_categories")]
        ])
        await callback.message.edit_text(
            "Bu kategoriyada hozircha mahsulot yo'q.\n"
            "Agar o'zingiz istagan mahsulotni buyurtma qilmoqchi bo'lsangiz, quyidagi tugmani bosing.",
            reply_markup=kb
        )
    else:
        await callback.message.edit_text(
            "Mahsulotni tanlang:",
            reply_markup=products_kb(prods, cat_id)
        )
    await callback.answer()

@router.callback_query(F.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Category))
        cats = result.scalars().all()
    await callback.message.edit_text(
        "Kategoriyani tanlang:",
        reply_markup=categories_kb(cats)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("prod_"))
async def product_detail(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split("_")[1])
    async with AsyncSessionLocal() as session:
        product = await session.get(Product, prod_id)
        await state.update_data(selected_product_id=prod_id, product_price=product.price)
    await callback.message.edit_text(
        f"{product.name}\nNarxi: {product.price} so'm\n\n"
        "Qancha miqdorda xohlaysiz? (raqam yozing)",
        reply_markup=None
    )
    await state.set_state(AddToCart.waiting_for_quantity)
    await callback.answer()

@router.message(AddToCart.waiting_for_quantity)
async def add_quantity(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat son kiriting.")
        return
    qty = int(message.text)
    data = await state.get_data()
    prod_id = data.get("selected_product_id")
    price = data.get("product_price")
    # Mahsulot nomini olish uchun bazaga murojaat
    async with AsyncSessionLocal() as session:
        product = await session.get(Product, prod_id)
        name = product.name
    add_to_cart(message.from_user.id, prod_id, qty, price, name=name, item_type="regular")
    await message.answer(f"✅ Mahsulot savatga qoʻshildi.")
    await state.clear()

@router.callback_query(F.data.startswith("back_to_cat_"))
async def back_to_category(callback: CallbackQuery):
    cat_id = int(callback.data.split("_")[3])
    await show_products(callback)

# ========== MAXSUS BUYURTMA ==========

@router.callback_query(F.data == "custom_order")
async def custom_order_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CustomOrderState.waiting_for_products)
    await callback.message.edit_text(
        "📝 **Maxsus buyurtma**\n\n"
        "Iltimos, buyurtmangizni quyidagi formatda yozing.\n"
        "Har bir mahsulotni yangi qatorga yozing:\n"
        "`Mahsulot nomi - miqdor birlik`\n\n"
        "**Masalan:**\n"
        "Olma - 2 kg\n"
        "Non - 1 dona\n"
        "Kartoshka - 5 kg\n"
        "Sut - 2 litr\n\n"
        "Eslatma: Mahsulot nomi va miqdor orasida tire (`-`) bo'lishi shart.",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(CustomOrderState.waiting_for_products)
async def process_custom_products(message: types.Message, state: FSMContext):
    text = message.text.strip()
    lines = text.split('\n')
    pattern = r'^([A-Za-zА-Яа-я\s\-]{2,})\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*(kg|dona|litr|gr|gramm|kilogram|gram|l)$'
    products = []
    errors = []
    for idx, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        match = re.match(pattern, line, re.IGNORECASE)
        if not match:
            errors.append(f"Qator {idx}: {line}")
        else:
            product_name = match.group(1).strip()
            quantity_str = match.group(2).replace(',', '.')
            try:
                quantity = float(quantity_str)
            except ValueError:
                errors.append(f"Qator {idx}: miqdor noto'g'ri - {line}")
                continue
            unit = match.group(3).lower()
            products.append({
                'name': product_name,
                'quantity': quantity,
                'unit': unit
            })
    if errors:
        error_text = "❌ Quyidagi qatorlarda xato bor:\n" + "\n".join(errors) + \
                     "\n\nIltimos, to'g'ri formatda qayta yozing."
        await message.answer(error_text)
        return
    if not products:
        await message.answer("Hech qanday mahsulot kiritilmadi. Qayta urinib ko'ring.")
        return
    await state.update_data(custom_products=products)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Telegram raqam", callback_data="custom_phone_telegram")],
        [InlineKeyboardButton(text="📞 Maxsus raqam", callback_data="custom_phone_manual")]
    ])
    await message.answer(
        "Buyurtmangiz qabul qilindi. Endi telefon raqamingizni tanlang:",
        reply_markup=kb
    )
    await state.set_state(CustomOrderState.waiting_for_phone_choice)

@router.callback_query(CustomOrderState.waiting_for_phone_choice, F.data == "custom_phone_telegram")
async def custom_phone_telegram(callback: CallbackQuery, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await callback.message.delete()
    await callback.message.answer(
        "Iltimos, telefon raqamingizni yuborish tugmasini bosing:",
        reply_markup=kb
    )
    await state.set_state(CustomOrderState.waiting_for_contact)
    await callback.answer()

@router.callback_query(CustomOrderState.waiting_for_phone_choice, F.data == "custom_phone_manual")
async def custom_phone_manual(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(
        "Iltimos, telefon raqamingizni +998 XX XXX XX XX formatida kiriting:"
    )
    await state.set_state(CustomOrderState.waiting_for_custom_phone)
    await callback.answer()

@router.message(CustomOrderState.waiting_for_contact, F.contact)
async def custom_contact_received(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer(
        "Telefon raqam qabul qilindi. Endi joylashuvingizni yuboring:",
        reply_markup=kb
    )
    await state.set_state(CustomOrderState.waiting_for_location)

@router.message(CustomOrderState.waiting_for_custom_phone)
async def custom_phone_received(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    cleaned = re.sub(r'[^\d+]', '', phone)
    if not re.match(r'^\+998\d{9}$', cleaned):
        await message.answer(
            "❌ Noto'g'ri format. Iltimos, +998 XX XXX XX XX formatida kiriting.\n"
            "Masalan: +998 90 123 45 67"
        )
        return
    await state.update_data(phone=cleaned)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await message.answer(
        "Telefon raqam qabul qilindi. Endi joylashuvingizni yuboring:",
        reply_markup=kb
    )
    await state.set_state(CustomOrderState.waiting_for_location)

@router.message(CustomOrderState.waiting_for_location, F.location)
async def custom_location_received(message: types.Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude
    location_link = f"https://www.google.com/maps?q={lat},{lon}"
    await state.update_data(location=location_link)
    data = await state.get_data()
    products = data['custom_products']
    phone = data['phone']
    location = data['location']
    products_text = ""
    for p in products:
        products_text += f"• {p['name']}: {p['quantity']} {p['unit']}\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="custom_confirm_yes")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="custom_confirm_no")]
    ])
    await message.answer(
        f"**Buyurtma ma'lumotlari:**\n\n"
        f"{products_text}\n"
        f"📞 +{phone}\n"
        f"📍 [Xarita]({location})\n\n"
        "Tasdiqlaysizmi?",
        parse_mode="Markdown",
        reply_markup=kb
    )
    await state.set_state(CustomOrderState.confirming_order)

@router.callback_query(CustomOrderState.confirming_order, F.data == "custom_confirm_yes")
async def custom_confirm_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    products = data['custom_products']
    phone = data['phone']
    location = data['location']
    user_id = callback.from_user.id
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
    products_text = ""
    for p in products:
        products_text += f"• {p['name']}: {p['quantity']} {p['unit']}\n"
    # admin_text = (
    #     f"📝 **Maxsus buyurtma**\n\n"
    #     f"👤 Foydalanuvchi: {callback.from_user.full_name} (ID: {user_id})\n"
    #     f"📞 {phone}\n"
    #     f"📍 [Xarita]({location})\n"
    #     f"Buyurtma tarkibi:\n{products_text}"
    # )
    # for admin_id in ADMIN_IDS:
    #     try:
    #         await callback.bot.send_message(admin_id, admin_text, parse_mode="Markdown")
    #     except Exception as e:
    #         logger.error(f"Admin {admin_id} ga xabar yuborilmadi: {e}")
    try:
        async with AsyncSessionLocal() as session:
            for p in products:
                custom_order = CustomOrder(
                    user_id=user_id,
                    product_name=p['name'],
                    quantity=p['quantity'],
                    unit=p['unit']
                )
                session.add(custom_order)
            await session.commit()
        await callback.message.edit_text(
        "✅ Buyurtmangiz  savatga qo'shildi!\n"
        "Savatni ko'rish uchun 🛒 Savat tugmasini bosing.")
        await callback.message.answer("Asosiy menyu:", reply_markup=main_menu)
    except Exception as e:
        logger.error(f"Maxsus buyurtmani bazaga saqlashda xato: {e}")
        await callback.message.edit_text(
        "✅ Buyurtmangiz  savatga qo'shildi!\n"
        "Savatni ko'rish uchun 🛒 Savat tugmasini bosing.")
        await callback.message.answer("Asosiy menyu:", reply_markup=main_menu)

    await state.clear()
    await callback.answer()

@router.callback_query(CustomOrderState.confirming_order, F.data == "custom_confirm_no")
async def custom_confirm_no(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Buyurtma bekor qilindi.")
    await state.clear()
    await callback.answer()

@router.message(CustomOrderState.waiting_for_location)
async def custom_location_invalid(message: types.Message):
    await message.answer("Iltimos, joylashuvni yuborish tugmasidan foydalaning.")