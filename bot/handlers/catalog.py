from aiogram import Router, types, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update
import re
from bot.keyboards.main import main_menu
from bot.db.database import AsyncSessionLocal
from bot.db.models import Category, Product, CustomOrder, User  # User modelini qo'shish
from bot.keyboards.catalog import categories_kb, products_kb
from bot.states.checkout import AddToCart, CustomOrder as CustomOrderState
from bot.utils.cart import add_to_cart, get_next_custom_id
import logging

router = Router()
logger = logging.getLogger(__name__)

# Foydalanuvchini bazaga qo'shish yoki yangilash uchun yordamchi funksiya
async def get_or_create_user(session, telegram_id: int, full_name: str = None, username: str = None):
    """Foydalanuvchini olish yoki yaratish"""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    return user

# Foydalanuvchi telefon raqamini yangilash
async def update_user_phone(session, telegram_id: int, phone_number: str):
    """Foydalanuvchi telefon raqamini yangilash"""
    await session.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(phone_number=phone_number, is_phone_verified=True)
    )
    await session.commit()

# Foydalanuvchi telefon raqamini olish
async def get_user_phone(session, telegram_id: int):
    """Foydalanuvchi telefon raqamini olish"""
    result = await session.execute(
        select(User.phone_number).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()

# Kategoriyalarni ko'rsatish
@router.message(F.text == "🛍 Katalog")
async def show_categories(message: types.Message):
    async with AsyncSessionLocal() as session:
        # Foydalanuvchini bazaga qo'shish
        await get_or_create_user(
            session, 
            message.from_user.id,
            message.from_user.full_name,
            message.from_user.username
        )
        
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
        await state.update_data(
            selected_product_id=prod_id, 
            product_price=product.price,
            product_name=product.name
        )
    
    # Miqdorni so'rash uchun inline tugmalar
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➖", callback_data=f"qty_dec_{prod_id}"),
            InlineKeyboardButton(text="1", callback_data="qty_show"),
            InlineKeyboardButton(text="➕", callback_data=f"qty_inc_{prod_id}")
        ],
        [InlineKeyboardButton(text="✅ Savatga qo'shish", callback_data=f"add_to_cart_final_{prod_id}")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"back_to_cat_{product.category_id}")]
    ])
    
    await callback.message.edit_text(
        f"📦 *{product.name}*\n\n"
        f"💰 Narxi: {product.price} so'm\n"
        f"📝 {product.description or 'Tarif mavjud emas'}\n\n"
        "Miqdorni tanlang:",
        parse_mode="Markdown",
        reply_markup=kb
    )
    await state.set_state(AddToCart.waiting_for_quantity)
    await callback.answer()

# Miqdorni oshirish/kamaytirish uchun handlerlar
@router.callback_query(F.data.startswith("qty_inc_"))
async def increase_quantity(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    current_qty = data.get('quantity', 1)
    new_qty = current_qty + 1
    
    await state.update_data(quantity=new_qty)
    
    # Tugmalarni yangilash
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➖", callback_data=f"qty_dec_{prod_id}"),
            InlineKeyboardButton(text=str(new_qty), callback_data="qty_show"),
            InlineKeyboardButton(text="➕", callback_data=f"qty_inc_{prod_id}")
        ],
        [InlineKeyboardButton(text="✅ Savatga qo'shish", callback_data=f"add_to_cart_final_{prod_id}")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"back_to_cat_{data.get('category_id', 0)}")]
    ])
    
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("qty_dec_"))
async def decrease_quantity(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    current_qty = data.get('quantity', 1)
    
    if current_qty > 1:
        new_qty = current_qty - 1
        await state.update_data(quantity=new_qty)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="➖", callback_data=f"qty_dec_{prod_id}"),
                InlineKeyboardButton(text=str(new_qty), callback_data="qty_show"),
                InlineKeyboardButton(text="➕", callback_data=f"qty_inc_{prod_id}")
            ],
            [InlineKeyboardButton(text="✅ Savatga qo'shish", callback_data=f"add_to_cart_final_{prod_id}")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"back_to_cat_{data.get('category_id', 0)}")]
        ])
        
        await callback.message.edit_reply_markup(reply_markup=kb)
    
    await callback.answer()

@router.callback_query(F.data.startswith("add_to_cart_final_"))
async def add_to_cart_final(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split("_")[3])
    data = await state.get_data()
    quantity = data.get('quantity', 1)
    price = data.get('product_price')
    name = data.get('product_name')
    
    # Savatga qo'shish
    add_to_cart(
        callback.from_user.id, 
        prod_id, 
        quantity, 
        price, 
        name=name, 
        item_type="regular"
    )
    
    # Muvaffaqiyatli qo'shilgani haqida xabar
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Savatni ko'rish", callback_data="view_cart")],
        [InlineKeyboardButton(text="⬅️ Katalogga qaytish", callback_data="back_to_categories")]
    ])
    
    await callback.message.edit_text(
        f"✅ *{name}* savatga qo'shildi!\n"
        f"Miqdor: {quantity} dona\n"
        f"Summa: {price * quantity} so'm",
        parse_mode="Markdown",
        reply_markup=kb
    )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("back_to_cat_"))
async def back_to_category(callback: CallbackQuery):
    cat_id = int(callback.data.split("_")[3])
    await show_products(callback)

# ========== MAXSUS BUYURTMA ==========

@router.callback_query(F.data == "custom_order")
async def custom_order_start(callback: CallbackQuery, state: FSMContext):
    # Avval foydalanuvchining telefon raqami borligini tekshirish
    async with AsyncSessionLocal() as session:
        phone = await get_user_phone(session, callback.from_user.id)
    
    if phone:
        # Telefon raqam bor, to'g'ridan-to'g'ri mahsulotlarni so'rash
        await state.update_data(user_phone=phone)
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
    else:
        # Telefon raqam yo'q, so'rash
        await state.set_state(CustomOrderState.waiting_for_phone_choice)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Telegram raqam", callback_data="custom_phone_telegram")],
            [InlineKeyboardButton(text="📞 Maxsus raqam", callback_data="custom_phone_manual")]
        ])
        
        await callback.message.edit_text(
            "Maxsus buyurtma berish uchun telefon raqamingiz kerak.\n"
            "Telefon raqamingizni tanlang:",
            reply_markup=kb
        )
    
    await callback.answer()

@router.callback_query(F.data == "custom_phone_telegram")
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

@router.callback_query(F.data == "custom_phone_manual")
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
    
    # Telefon raqamni bazaga saqlash
    async with AsyncSessionLocal() as session:
        await update_user_phone(session, message.from_user.id, phone)
    
    await state.update_data(user_phone=phone)
    
    # Endi mahsulotlarni so'rash
    await state.set_state(CustomOrderState.waiting_for_products)
    await message.answer(
        "📝 **Maxsus buyurtma**\n\n"
        "Iltimos, buyurtmangizni quyidagi formatda yozing.\n"
        "Har bir mahsulotni yangi qatorga yozing:\n"
        "`Mahsulot nomi - miqdor birlik`\n\n"
        "**Masalan:**\n"
        "Olma - 2 kg\n"
        "Non - 1 dona\n"
        "Kartoshka - 5 kg\n"
        "Sut - 2 litr",
        parse_mode="Markdown"
    )

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
    
    # Telefon raqamni bazaga saqlash
    async with AsyncSessionLocal() as session:
        await update_user_phone(session, message.from_user.id, cleaned)
    
    await state.update_data(user_phone=cleaned)
    
    # Endi mahsulotlarni so'rash
    await state.set_state(CustomOrderState.waiting_for_products)
    await message.answer(
        "📝 **Maxsus buyurtma**\n\n"
        "Iltimos, buyurtmangizni quyidagi formatda yozing.\n"
        "Har bir mahsulotni yangi qatorga yozing:\n"
        "`Mahsulot nomi - miqdor birlik`\n\n"
        "**Masalan:**\n"
        "Olma - 2 kg\n"
        "Non - 1 dona\n"
        "Kartoshka - 5 kg\n"
        "Sut - 2 litr",
        parse_mode="Markdown"
    )

@router.message(CustomOrderState.waiting_for_products)
async def process_custom_products(message: types.Message, state: FSMContext):
    text = message.text.strip()
    lines = text.split('\n')
    
    # Kengaytirilgan pattern (o'zbek va rus tillari uchun)
    pattern = r'^([A-Za-zА-Яа-я\s\-]{2,})\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*(kg|dona|litr|gr|gramm|kilogram|gram|l|метr|метр|metr|m|та|доно|dono|шт|штук|soat|dona|kg|л|l|м)$'
    
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
                # Agar butun son bo'lsa, integerga o'tkazish
                if quantity.is_integer():
                    quantity = int(quantity)
            except ValueError:
                errors.append(f"Qator {idx}: miqdor noto'g'ri - {line}")
                continue
            
            unit = match.group(3).lower()
            
            # Birliklarni normallashtirish
            unit_map = {
                'kg': 'kg', 'kilogram': 'kg', 'gramm': 'gr', 'gram': 'gr', 'gr': 'gr',
                'l': 'litr', 'litr': 'litr', 'л': 'litr',
                'dona': 'dona', 'доно': 'dona', 'dono': 'dona', 'та': 'dona', 'шт': 'dona', 'штук': 'dona',
                'metr': 'metr', 'метр': 'metr', 'm': 'metr', 'м': 'metr'
            }
            
            unit = unit_map.get(unit, unit)
            
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
    
    # Mahsulotlar ro'yxatini ko'rsatish va tasdiqlash
    products_text = ""
    for p in products:
        products_text += f"• {p['name']}: {p['quantity']} {p['unit']}\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Davom etish", callback_data="custom_continue_to_location")],
        [InlineKeyboardButton(text="🔄 Qayta yozish", callback_data="custom_retry_products")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="custom_cancel")]
    ])
    
    await message.answer(
        f"📝 **Kiritilgan mahsulotlar:**\n\n{products_text}\n\n"
        "Mahsulotlar to'g'ri kiritilgan bo'lsa, davom eting.",
        parse_mode="Markdown",
        reply_markup=kb
    )
    await state.set_state(CustomOrderState.waiting_for_confirm_products)

@router.callback_query(F.data == "custom_continue_to_location")
async def custom_continue_to_location(callback: CallbackQuery, state: FSMContext):
    # Lokatsiya so'rash
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    
    await callback.message.delete()
    await callback.message.answer(
        "📍 Iltimos, joylashuvingizni yuboring:",
        reply_markup=kb
    )
    await state.set_state(CustomOrderState.waiting_for_location)
    await callback.answer()

@router.callback_query(F.data == "custom_retry_products")
async def custom_retry_products(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CustomOrderState.waiting_for_products)
    await callback.message.edit_text(
        "📝 Iltimos, mahsulotlarni qayta kiriting:",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "custom_cancel")
async def custom_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Buyurtma bekor qilindi.")
    await callback.message.answer("Asosiy menyu:", reply_markup=main_menu)
    await callback.answer()

@router.message(CustomOrderState.waiting_for_location, F.location)
async def custom_location_received(message: types.Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude
    location_link = f"https://www.google.com/maps?q={lat},{lon}"
    
    await state.update_data(location=location_link, location_coords=f"{lat},{lon}")
    
    data = await state.get_data()
    products = data['custom_products']
    phone = data['user_phone']
    
    products_text = ""
    for p in products:
        products_text += f"• {p['name']}: {p['quantity']} {p['unit']}\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="custom_confirm_yes")],
        [InlineKeyboardButton(text="🔄 Qayta yozish", callback_data="custom_retry_all")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="custom_cancel")]
    ])
    
    await message.answer(
        f"**Buyurtma ma'lumotlari:**\n\n"
        f"📦 Mahsulotlar:\n{products_text}\n"
        f"📞 Telefon: {phone}\n"
        f"📍 [Xarita]({location_link})\n\n"
        "Tasdiqlaysizmi?",
        parse_mode="Markdown",
        reply_markup=kb
    )
    await state.set_state(CustomOrderState.confirming_order)

@router.message(CustomOrderState.waiting_for_location)
async def custom_location_invalid(message: types.Message):
    await message.answer(
        "❌ Iltimos, joylashuvni yuborish tugmasidan foydalaning.\n"
        "📍 Joylashuvni yuborish uchun pastdagi tugmani bosing."
    )

@router.callback_query(CustomOrderState.confirming_order, F.data == "custom_confirm_yes")
async def custom_confirm_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    products = data['custom_products']
    phone = data['user_phone']
    location = data['location']
    location_coords = data.get('location_coords', '')
    user_id = callback.from_user.id
    
    # Maxsus mahsulotlarni savatga qo'shish
    for p in products:
        custom_id = get_next_custom_id()
        add_to_cart(
            user_id=user_id,
            item_id=custom_id,
            qty=p['quantity'],
            price=0,  # Maxsus buyurtma narxi keyin belgilanadi
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
        
        await callback.message.edit_text(
            "✅ Buyurtmangiz qabul qilindi va savatga qo'shildi!\n\n"
            "🛒 Savatni ko'rish va buyurtmani yakunlash uchun '🛒 Savat' tugmasini bosing.\n\n"
            "Yoki yangi buyurtma berishda davom etishingiz mumkin."
        )
        
        # Asosiy menyuni ko'rsatish
        await callback.message.answer(
            "Asosiy menyu:",
            reply_markup=main_menu
        )
        
    except Exception as e:
        logger.error(f"Maxsus buyurtmani bazaga saqlashda xato: {e}")
        await callback.message.edit_text(
            "✅ Buyurtmangiz savatga qo'shildi!\n\n"
            "🛒 Savatni ko'rish uchun '🛒 Savat' tugmasini bosing."
        )
        await callback.message.answer("Asosiy menyu:", reply_markup=main_menu)
    
    await state.clear()
    await callback.answer()

@router.callback_query(CustomOrderState.confirming_order, F.data == "custom_retry_all")
async def custom_retry_all(callback: CallbackQuery, state: FSMContext):
    # Boshidan boshlash
    await state.set_state(CustomOrderState.waiting_for_products)
    await callback.message.edit_text(
        "📝 Iltimos, buyurtmangizni qayta kiriting:",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "view_cart")
async def view_cart_handler(callback: CallbackQuery):
    """Savatni ko'rish uchun handler"""
    from bot.handlers.cart import show_cart  # Import qilish
    await show_cart(callback.message, callback.from_user.id)
    await callback.answer()