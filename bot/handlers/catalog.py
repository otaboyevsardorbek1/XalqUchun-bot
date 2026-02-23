from aiogram import Router, types, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update
import re
import asyncio
from bot.keyboards.main import main_menu
from bot.db.database import AsyncSessionLocal
from bot.db.models import Category, Product, CustomOrder, User
from bot.keyboards.catalog import categories_kb, products_kb
from bot.states.checkout import AddToCart, CustomOrder as CustomOrderState
from bot.utils.cart import add_to_cart, get_next_custom_id
from bot.utils.chat_action import with_typing_action, Actions
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
            username=username,
            role="guest"
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info(f"Yangi foydalanuvchi yaratildi: {telegram_id}")
    
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
        logger.info(f"Foydalanuvchi telefon raqami yangilandi: {telegram_id} -> {phone_number}")
        return True
    except Exception as e:
        logger.error(f"Telefon raqam yangilashda xato: {e}")
        return False

async def get_user_phone(session, telegram_id: int):
    """Foydalanuvchi telefon raqamini olish"""
    try:
        result = await session.execute(
            select(User.phone_number).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Telefon raqam olishda xato: {e}")
        return None

# Kategoriyalarni ko'rsatish
@router.message(F.text == "🛍 Katalog")
@with_typing_action
async def show_categories(message: types.Message):
    try:
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
                    "📭 *Hozircha kategoriyalar mavjud emas.*\n\n"
                    "Agar o'zingiz istagan mahsulotni buyurtma qilmoqchi bo'lsangiz, "
                    "quyidagi tugmani bosing.",
                    parse_mode="Markdown",
                    reply_markup=kb
                )
                return
        
        await message.answer(
            "📋 *Kategoriyani tanlang:*",
            parse_mode="Markdown",
            reply_markup=categories_kb(cats)
        )
    except Exception as e:
        logger.error(f"Kategoriyalarni ko'rsatishda xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

@router.callback_query(F.data.startswith("cat_"))
@with_typing_action
async def show_products(callback: CallbackQuery):
    try:
        cat_id = int(callback.data.split("_")[1])
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Product).where(Product.category_id == cat_id)
            )
            prods = result.scalars().all()
        
        if not prods:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Maxsus buyurtma", callback_data="custom_order")],
                [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_categories")]
            ])
            await callback.message.edit_text(
                "📭 *Bu kategoriyada hozircha mahsulot yo'q.*\n\n"
                "Agar o'zingiz istagan mahsulotni buyurtma qilmoqchi bo'lsangiz, "
                "quyidagi tugmani bosing.",
                parse_mode="Markdown",
                reply_markup=kb
            )
        else:
            await callback.message.edit_text(
                "📦 *Mahsulotni tanlang:*",
                parse_mode="Markdown",
                reply_markup=products_kb(prods, cat_id)
            )
        await callback.answer()
    except Exception as e:
        logger.error(f"Mahsulotlarni ko'rsatishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data == "back_to_categories")
@with_typing_action
async def back_to_categories(callback: CallbackQuery):
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Category))
            cats = result.scalars().all()
        
        await callback.message.edit_text(
            "📋 *Kategoriyani tanlang:*",
            parse_mode="Markdown",
            reply_markup=categories_kb(cats)
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Orqaga qaytishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data.startswith("prod_"))
@with_typing_action
async def product_detail(callback: CallbackQuery, state: FSMContext):
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
                category_id=product.category_id
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
            f"💰 *Narxi:* {product.price} so'm\n"
            f"📝 *Ta'rif:* {product.description or 'Tarif mavjud emas'}\n\n"
            "🔢 *Miqdorni tanlang:*",
            parse_mode="Markdown",
            reply_markup=kb
        )
        await state.set_state(AddToCart.waiting_for_quantity)
        await callback.answer()
    except Exception as e:
        logger.error(f"Mahsulot detallarini ko'rsatishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

# Miqdorni oshirish/kamaytirish uchun handlerlar
@router.callback_query(F.data.startswith("qty_inc_"))
async def increase_quantity(callback: CallbackQuery, state: FSMContext):
    try:
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
    except Exception as e:
        logger.error(f"Miqdorni oshirishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data.startswith("qty_dec_"))
async def decrease_quantity(callback: CallbackQuery, state: FSMContext):
    try:
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
    except Exception as e:
        logger.error(f"Miqdorni kamaytirishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

# Savatga qo'shish
@router.callback_query(F.data.startswith("add_to_cart_final_"))
async def add_to_cart_final(callback: CallbackQuery, state: FSMContext):
    try:
        # Upload photo action yuborish
        await callback.bot.send_chat_action(
            chat_id=callback.from_user.id, 
            action=Actions.UPLOAD_PHOTO
        )
        await asyncio.sleep(1)
        
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
            f"✅ *{name}* savatga qo'shildi!\n\n"
            f"📦 Miqdor: {quantity} dona\n"
            f"💰 Summa: {price * quantity:,} so'm",
            parse_mode="Markdown",
            reply_markup=kb
        )
        await state.clear()
        await callback.answer()
    except Exception as e:
        logger.error(f"Savatga qo'shishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data.startswith("back_to_cat_"))
@with_typing_action
async def back_to_category(callback: CallbackQuery):
    try:
        cat_id = int(callback.data.split("_")[3])
        await show_products(callback)
    except Exception as e:
        logger.error(f"Kategoriyaga qaytishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

# ========== MAXSUS BUYURTMA ==========

@router.callback_query(F.data == "custom_order")
@with_typing_action
async def custom_order_start(callback: CallbackQuery, state: FSMContext):
    try:
        # Avval foydalanuvchining telefon raqami borligini tekshirish
        async with AsyncSessionLocal() as session:
            phone = await get_user_phone(session, callback.from_user.id)
        
        if phone:
            # Telefon raqam bor, to'g'ridan-to'g'ri mahsulotlarni so'rash
            await state.update_data(user_phone=phone)
            await state.set_state(CustomOrderState.waiting_for_products)
            await callback.message.edit_text(
                "📝 *Maxsus buyurtma*\n\n"
                "Iltimos, buyurtmangizni quyidagi formatda yozing:\n\n"
                "`Mahsulot nomi - miqdor birlik`\n\n"
                "*Masalan:*\n"
                "• Olma - 2 kg\n"
                "• Non - 1 dona\n"
                "• Kartoshka - 5 kg\n"
                "• Sut - 2 litr\n\n"
                "⚠️ Eslatma: Mahsulot nomi va miqdor orasida tire (`-`) bo'lishi shart.",
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
                "📞 *Maxsus buyurtma berish uchun telefon raqamingiz kerak.*\n\n"
                "Telefon raqamingizni qanday yuborasiz?",
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
    try:
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await callback.message.delete()
        await callback.message.answer(
            "📱 *Telefon raqamingizni yuborish tugmasini bosing:*",
            parse_mode="Markdown",
            reply_markup=kb
        )
        await state.set_state(CustomOrderState.waiting_for_contact)
        await callback.answer()
    except Exception as e:
        logger.error(f"Telefon raqam tanlashda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data == "custom_phone_manual")
@with_typing_action
async def custom_phone_manual(callback: CallbackQuery, state: FSMContext):
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
        logger.error(f"Qo'lda telefon raqam kiritishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.message(CustomOrderState.waiting_for_contact, F.contact)
async def custom_contact_received(message: types.Message, state: FSMContext):
    try:
        phone = message.contact.phone_number
        
        # Telefon raqamni bazaga saqlash
        async with AsyncSessionLocal() as session:
            success = await update_user_phone(session, message.from_user.id, phone)
            
            if not success:
                await message.answer("❌ Telefon raqam saqlashda xatolik yuz berdi.")
                return
        
        await state.update_data(user_phone=phone)
        
        # Endi mahsulotlarni so'rash
        await state.set_state(CustomOrderState.waiting_for_products)
        await message.answer(
            "📝 *Maxsus buyurtma*\n\n"
            "Iltimos, buyurtmangizni quyidagi formatda yozing:\n\n"
            "`Mahsulot nomi - miqdor birlik`\n\n"
            "*Masalan:*\n"
            "• Olma - 2 kg\n"
            "• Non - 1 dona\n"
            "• Kartoshka - 5 kg\n"
            "• Sut - 2 litr",
            parse_mode="Markdown",
            reply_markup=types.ReplyKeyboardRemove()
        )
    except Exception as e:
        logger.error(f"Kontakt qabul qilishda xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

@router.message(CustomOrderState.waiting_for_custom_phone)
async def custom_phone_received(message: types.Message, state: FSMContext):
    try:
        phone = message.text.strip()
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Telefon raqam formatini tekshirish
        if not re.match(r'^\+998\d{9}$', cleaned):
            await message.answer(
                "❌ *Noto'g'ri format.*\n\n"
                "Iltimos, telefon raqamingizni quyidagi formatda kiriting:\n"
                "`+998 XX XXX XX XX`\n\n"
                "Masalan: `+998 90 123 45 67`",
                parse_mode="Markdown"
            )
            return
        
        # Telefon raqamni bazaga saqlash
        async with AsyncSessionLocal() as session:
            success = await update_user_phone(session, message.from_user.id, cleaned)
            
            if not success:
                await message.answer("❌ Telefon raqam saqlashda xatolik yuz berdi.")
                return
        
        await state.update_data(user_phone=cleaned)
        
        # Endi mahsulotlarni so'rash
        await state.set_state(CustomOrderState.waiting_for_products)
        await message.answer(
            "📝 *Maxsus buyurtma*\n\n"
            "Iltimos, buyurtmangizni quyidagi formatda yozing:\n\n"
            "`Mahsulot nomi - miqdor birlik`\n\n"
            "*Masalan:*\n"
            "• Olma - 2 kg\n"
            "• Non - 1 dona\n"
            "• Kartoshka - 5 kg\n"
            "• Sut - 2 litr",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Telefon raqam qabul qilishda xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
@router.message(CustomOrderState.waiting_for_products)
async def process_custom_products(message: types.Message, state: FSMContext):
    try:
        text = message.text.strip()
        
        # Avval butun matnni qatorlarga ajratamiz
        lines = text.split('\n')
        
        # Barcha qatorlarni yig'ish
        all_products = []
        all_errors = []
        
        # Har bir qatorni alohida qayta ishlaymiz
        for line_idx, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # Agar qator uzun bo'lsa, uni bir nechta mahsulotlarga ajratish mumkin
            # Masalan: "olma - 2 kg anor - 3 kg" ni ajratish
            # Buning uchun murakkabroq pattern ishlatamiz
            
            # Bir qatorda bir nechta "nomi - miqdor birlik" bo'lishi mumkin
            # Pattern: ([\w\s\-]+?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*([a-z]+)
            product_pattern = r'([A-Za-zА-Яа-я\s\-]+?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*([a-z]+)'
            
            # Qatordagi barcha mosliklarni topish
            matches = re.findall(product_pattern, line, re.IGNORECASE)
            
            if matches:
                # Agar mosliklar topilsa, har birini mahsulot sifatida qo'shamiz
                for match in matches:
                    product_name = match[0].strip()
                    quantity_str = match[1].replace(',', '.')
                    unit = match[2].lower()
                    
                    try:
                        quantity = float(quantity_str)
                        if quantity.is_integer():
                            quantity = int(quantity)
                        
                        # Birliklarni normallashtirish
                        unit_map = {
                            # Og'irlik birliklari
                            'kg': 'kg', 'kilogram': 'kg', 'kilogramm': 'kg', 'kilo': 'kg',
                            'gramm': 'gr', 'gram': 'gr', 'gr': 'gr', 'g': 'gr',
                            'tonna': 'tonna', 'ton': 'tonna', 't': 'tonna', 'т': 'tonna',
                            'sentyabr': 'kg', 'sentner': 'kg', 'ts': 'kg',
                            
                            # Hajm birliklari
                            'l': 'litr', 'litr': 'litr', 'liter': 'litr', 'л': 'litr',
                            'ml': 'ml', 'millilitr': 'ml', 'milliliter': 'ml',
                            
                            # Uzunlik birliklari
                            'metr': 'metr', 'meter': 'metr', 'm': 'metr', 'м': 'metr',
                            'sm': 'sm', 'santimetr': 'sm', 'centimeter': 'sm',
                            
                            # Soniya birliklari
                            'dona': 'dona', 'dono': 'dona', 'та': 'dona', 'шт': 'dona', 
                            'штук': 'dona', 'piece': 'dona', 'pcs': 'dona',
                            
                            # O'ram birliklari
                            'quti': 'quti', 'box': 'quti', 'korobka': 'quti',
                            'paket': 'paket', 'pack': 'paket', 'пaket': 'paket',
                            
                            # Suyuqlik birliklari
                            'butilka': 'butilka', 'bottle': 'butilka', 'şişe': 'butilka',
                            'bank': 'bank', 'jar': 'bank', 'банка': 'bank',
                            
                            # Boshqa birliklar
                            'juft': 'juft', 'pair': 'juft',
                            'komplekt': 'komplekt', 'set': 'komplekt',
                            'list': 'list', 'sheet': 'list',
                            'rulon': 'rulon', 'roll': 'rulon'
                        }
                        
                        unit = unit_map.get(unit, unit)
                        
                        all_products.append({
                            'name': product_name,
                            'quantity': quantity,
                            'unit': unit
                        })
                        
                    except ValueError:
                        all_errors.append(f"Qator {line_idx}: {product_name} - miqdor noto'g'ri")
            
            else:
                # Agar moslik topilmasa, eski pattern bilan tekshirish
                old_pattern = r'^([A-Za-zА-Яа-я\s\-]{2,})\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*(.+)$'
                match = re.match(old_pattern, line, re.IGNORECASE)
                
                if match:
                    product_name = match.group(1).strip()
                    quantity_str = match.group(2).replace(',', '.')
                    unit = match.group(3).strip().lower()
                    
                    try:
                        quantity = float(quantity_str)
                        if quantity.is_integer():
                            quantity = int(quantity)
                        
                        all_products.append({
                            'name': product_name,
                            'quantity': quantity,
                            'unit': unit
                        })
                    except ValueError:
                        all_errors.append(f"Qator {line_idx}: {line}")
                else:
                    all_errors.append(f"Qator {line_idx}: {line}")
        
        # Xatoliklarni tekshirish
        if all_errors:
            error_text = "❌ *Quyidagi qatorlarda xato bor:*\n\n"
            for error in all_errors[:10]:  # Eng ko'pi bilan 10 ta xatoni ko'rsatish
                error_text += f"• {error}\n"
            
            if len(all_errors) > 10:
                error_text += f"\n... va yana {len(all_errors) - 10} ta xato"
            
            error_text += "\n\n📝 Iltimos, to'g'ri formatda qayta yozing.\n\n"
            error_text += "Format: `Mahsulot nomi - miqdor birlik`\n"
            error_text += "Masalan: `Olma - 2 kg` yoki `Olma - 2 kg, Anor - 3 kg`"
            
            await message.answer(error_text, parse_mode="Markdown")
            return
        
        if not all_products:
            await message.answer(
                "❌ *Hech qanday mahsulot kiritilmadi.*\n\n"
                "Iltimos, quyidagi formatda mahsulotlarni kiriting:\n"
                "`Mahsulot nomi - miqdor birlik`\n\n"
                "Masalan:\n"
                "• Olma - 2 kg\n"
                "• Non - 1 dona\n"
                "• Sut - 2 litr",
                parse_mode="Markdown"
            )
            return
        
        # Mahsulotlarni state ga saqlash
        await state.update_data(custom_products=all_products)
        
        # Mahsulotlar ro'yxatini ko'rsatish
        products_text = ""
        for i, p in enumerate(all_products, 1):
            products_text += f"{i}. *{p['name']}*: {p['quantity']} {p['unit']}\n"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Davom etish", callback_data="custom_continue_to_location")],
            [InlineKeyboardButton(text="🔄 Qayta yozish", callback_data="custom_retry_products")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="custom_cancel")]
        ])
        
        await message.answer(
            f"📝 *Kiritilgan mahsulotlar ({len(all_products)} ta):*\n\n{products_text}\n\n"
            "✅ Mahsulotlar to'g'ri kiritilgan bo'lsa, davom eting.",
            parse_mode="Markdown",
            reply_markup=kb
        )
        await state.set_state(CustomOrderState.waiting_for_confirm_products)
        
    except Exception as e:
        logger.error(f"Mahsulotlarni qayta ishlashda xato: {e}")
        await message.answer(
            "❌ *Xatolik yuz berdi.*\n\n"
            "Iltimos, quyidagi formatda qayta urinib ko'ring:\n"
            "`Mahsulot nomi - miqdor birlik`\n\n"
            "Masalan:\n"
            "• Olma - 2 kg\n"
            "• Non - 1 dona\n"
            "• Sut - 2 litr",
            parse_mode="Markdown"
        )
@router.callback_query(F.data == "custom_continue_to_location")
@with_typing_action
async def custom_continue_to_location(callback: CallbackQuery, state: FSMContext):
    try:
        # Lokatsiya so'rash
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True)]],
            resize_keyboard=True, one_time_keyboard=True
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
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data == "custom_cancel")
async def custom_cancel(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await callback.message.edit_text("❌ Buyurtma bekor qilindi.")
        await callback.message.answer(
            "🏠 *Asosiy menyu:*",
            parse_mode="Markdown",
            reply_markup=main_menu
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Bekor qilishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.message(CustomOrderState.waiting_for_location, F.location)
async def custom_location_received(message: types.Message, state: FSMContext):
    try:
        # Find location action yuborish
        await message.bot.send_chat_action(
            chat_id=message.chat.id, 
            action=Actions.FIND_LOCATION
        )
        await asyncio.sleep(1)
        
        lat = message.location.latitude
        lon = message.location.longitude
        location_link = f"https://www.google.com/maps?q={lat},{lon}"
        
        await state.update_data(location=location_link, location_coords=f"{lat},{lon}")
        
        data = await state.get_data()
        products = data['custom_products']
        phone = data['user_phone']
        
        products_text = ""
        for p in products:
            products_text += f"• *{p['name']}*: {p['quantity']} {p['unit']}\n"
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="custom_confirm_yes")],
            [InlineKeyboardButton(text="🔄 Qayta boshlash", callback_data="custom_retry_all")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="custom_cancel")]
        ])
        
        await message.answer(
            f"📦 *Buyurtma ma'lumotlari:*\n\n"
            f"{products_text}\n"
            f"📞 *Telefon:* {phone}\n"
            f"📍 *Lokatsiya:* [Xaritada ko'rish]({location_link})\n\n"
            "✅ Buyurtmani tasdiqlaysizmi?",
            parse_mode="Markdown",
            reply_markup=kb,
            disable_web_page_preview=True
        )
        
        # Reply keyboardni olib tashlash
        await message.answer(
            "⏳...",
            reply_markup=types.ReplyKeyboardRemove()
        )
        
        await state.set_state(CustomOrderState.confirming_order)
    except Exception as e:
        logger.error(f"Lokatsiya qabul qilishda xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

@router.message(CustomOrderState.waiting_for_location)
async def custom_location_invalid(message: types.Message):
    await message.answer(
        "❌ *Iltimos, joylashuvni yuborish tugmasidan foydalaning.*\n\n"
        "📍 Joylashuvni yuborish uchun pastdagi tugmani bosing.",
        parse_mode="Markdown"
    )

@router.callback_query(CustomOrderState.confirming_order, F.data == "custom_confirm_yes")
async def custom_confirm_yes(callback: CallbackQuery, state: FSMContext):
    try:
        # Upload document action yuborish
        await callback.bot.send_chat_action(
            chat_id=callback.from_user.id, 
            action=Actions.UPLOAD_DOCUMENT
        )
        await asyncio.sleep(1)
        
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
                logger.info(f"Maxsus buyurtma saqlandi: {user_id}")
            
            await callback.message.edit_text(
                "✅ *Buyurtmangiz qabul qilindi va savatga qo'shildi!*\n\n"
                "🛒 *Savatni ko'rish* va buyurtmani yakunlash uchun quyidagi tugmani bosing.\n\n"
                "Yangi buyurtma berishda davom etishingiz mumkin."
            )
            
        except Exception as e:
            logger.error(f"Maxsus buyurtmani bazaga saqlashda xato: {e}")
            await callback.message.edit_text(
                "✅ *Buyurtmangiz savatga qo'shildi!*\n\n"
                "🛒 Savatni ko'rish uchun quyidagi tugmani bosing."
            )
        
        # Savatni ko'rish tugmasi
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Savatni ko'rish", callback_data="view_cart")],
            [InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="back_to_main")]
        ])
        
        await callback.message.answer(
            "🏠 *Asosiy menyu:*",
            parse_mode="Markdown",
            reply_markup=kb
        )
        
        await state.clear()
        await callback.answer()
    except Exception as e:
        logger.error(f"Buyurtmani tasdiqlashda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(CustomOrderState.confirming_order, F.data == "custom_retry_all")
@with_typing_action
async def custom_retry_all(callback: CallbackQuery, state: FSMContext):
    try:
        # Boshidan boshlash
        await state.set_state(CustomOrderState.waiting_for_products)
        await callback.message.edit_text(
            "📝 *Iltimos, buyurtmangizni qayta kiriting:*\n\n"
            "Format: `Mahsulot nomi - miqdor birlik`\n\n"
            "*Masalan:*\n"
            "Olma - 2 kg",
            parse_mode="Markdown"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Qayta boshlashda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data == "view_cart")
async def view_cart_handler(callback: CallbackQuery):
    try:
        from bot.handlers.cart import show_cart
        await show_cart(callback.message, callback.from_user.id)
        await callback.answer()
    except Exception as e:
        logger.error(f"Savatni ko'rishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery):
    try:
        await callback.message.delete()
        await callback.message.answer(
            "🏠 *Asosiy menyu:*",
            parse_mode="Markdown",
            reply_markup=main_menu
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Asosiy menyuga qaytishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)