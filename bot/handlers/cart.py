# bot/handlers/cart.py
from aiogram import Router, types, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
import re
from bot.keyboards.main import get_main_menu, get_back_button
from typing import Union
from aiogram.types import Message, CallbackQuery
from bot.keyboards.cart import cart_kb, edit_custom_item_kb
from bot.db.database import AsyncSessionLocal
from bot.db.models import Product
from bot.states.checkout import EditCustomItem
from bot.utils.cart import get_cart_manager, get_cart, remove_from_cart, update_cart_item_qty
from bot.utils.helpers import format_price, parse_product_line, normalize_unit
from bot.utils.chat_action import with_typing_action, send_typing_action
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "🛒 Savat")
@router.callback_query(F.data == "view_cart")
@with_typing_action
async def show_cart(event: Union[Message, CallbackQuery], state: FSMContext = None):
    """Savatni ko'rsatish"""
    try:
        user_id = event.from_user.id
        cart_manager = get_cart_manager()
        cart_data = cart_manager.get_cart(user_id)
        
        if not cart_data:
            text = "🛒 *Savatingiz bo'sh* 🛒\n\nMahsulot qo'shish uchun 🛍 Katalog bo'limiga o'ting."
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛍 Katalog", callback_data="show_catalog")],
                [InlineKeyboardButton(text="📝 Maxsus buyurtma", callback_data="custom_order")],
                [InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="back_to_main")]
            ])
            
            if isinstance(event, types.Message):
                await event.answer(text, parse_mode="Markdown", reply_markup=kb)
            else:
                await event.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
                await event.answer()
            return
        
        # Mahsulot nomlarini olish (oddiy mahsulotlar uchun)
        product_ids = [pid for pid in cart_data.keys() if pid > 0]
        products = {}
        if product_ids:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Product).where(Product.id.in_(product_ids))
                )
                products = {p.id: p.name for p in result.scalars().all()}
        
        # Savat tarkibini tayyorlash
        lines = []
        total = 0
        items_list = []
        
        for item_id, item in cart_data.items():
            if item_id > 0:  # oddiy mahsulot
                name = products.get(item_id, item.get('name', 'Noma\'lum'))
                subtotal = item['qty'] * item['price']
                total += subtotal
                price_str = format_price(subtotal)
                lines.append(f"• *{name}*: {item['qty']} dona × {format_price(item['price'])} = {price_str} so'm")
                items_list.append({
                    'id': item_id,
                    'name': name,
                    'qty': item['qty'],
                    'price': item['price'],
                    'type': 'regular'
                })
            else:  # maxsus mahsulot
                name = item['name']
                lines.append(f"• 📦 *{name}*: {item['qty']} {item['unit']} (maxsus)")
                items_list.append({
                    'id': item_id,
                    'name': name,
                    'qty': item['qty'],
                    'unit': item['unit'],
                    'type': 'custom'
                })
        
        total_str = format_price(total)
        text = f"🛒 *SAVATINGIZ* 🛒\n\n" + "\n".join(lines) + f"\n\n💰 *Jami: {total_str} so'm*"
        
        # Savat tugmalarini yaratish
        builder = InlineKeyboardBuilder()
        
        for item in items_list:
            if item['type'] == 'regular':
                btn_text = f"❌ {item['name']} ({item['qty']} dona)"
            else:
                btn_text = f"❌ {item['name']} ({item['qty']} {item['unit']})"
            
            builder.button(text=btn_text, callback_data=f"remove_{item['id']}")
        
        builder.button(text="✅ Buyurtma berish", callback_data="checkout")
        builder.button(text="🔄 Savatni tozalash", callback_data="clear_cart")
        builder.button(text="🛍 Katalog", callback_data="show_catalog")
        builder.button(text="🏠 Asosiy menyu", callback_data="back_to_main")
        builder.adjust(1)
        
        kb = builder.as_markup()
        
        if isinstance(event, types.Message):
            await event.answer(text, parse_mode="Markdown", reply_markup=kb)
        else:
            await event.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
            await event.answer()
            
    except Exception as e:
        logger.error(f"Savatni ko'rsatishda xato: {e}")
        error_msg = "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
        if isinstance(event, types.Message):
            await event.answer(error_msg)
        else:
            await event.message.answer(error_msg)
            await event.answer()

@router.callback_query(F.data.startswith("remove_"))
async def remove_item(callback: CallbackQuery):
    """Mahsulotni savatdan olib tashlash"""
    try:
        item_id = int(callback.data.split("_")[1])
        success = remove_from_cart(callback.from_user.id, item_id)
        
        if success:
            await callback.answer("✅ Mahsulot olib tashlandi")
            
            # Savatni qayta ko'rsatish
            await show_cart(callback.message, None)
        else:
            await callback.answer("❌ Mahsulot topilmadi", show_alert=True)
            
    except Exception as e:
        logger.error(f"Mahsulotni olib tashlashda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data == "clear_cart")
async def clear_cart_handler(callback: CallbackQuery):
    """Savatni tozalash"""
    try:
        cart_manager = get_cart_manager()
        success = cart_manager.clear_cart(callback.from_user.id)
        
        if success:
            await callback.answer("✅ Savat tozalandi")
            await show_cart(callback.message, None)
        else:
            await callback.answer("❌ Savat allaqachon bo'sh", show_alert=True)
            
    except Exception as e:
        logger.error(f"Savatni tozalashda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data.startswith("edit_custom_"))
async def edit_custom_item(callback: CallbackQuery, state: FSMContext):
    """Maxsus mahsulotni tahrirlash"""
    try:
        custom_id = int(callback.data.split("_")[2])
        cart = get_cart(callback.from_user.id)
        item = cart.get(custom_id)
        
        if not item:
            await callback.answer("❌ Mahsulot topilmadi", show_alert=True)
            return
        
        await state.update_data(
            edit_item_id=custom_id,
            edit_item_name=item['name'],
            edit_item_unit=item['unit'],
            edit_item_qty=item['qty']
        )
        
        text = (
            f"✏️ *MAHSULOTNI TAHRIRLASH*\n\n"
            f"📦 *Mahsulot:* {item['name']}\n"
            f"📊 *Hozirgi miqdor:* {item['qty']} {item['unit']}\n\n"
            "Nima qilmoqchisiz?)"
            )
        
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=edit_custom_item_kb(custom_id)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Maxsus mahsulotni tahrirlashda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data.startswith("edit_delete_"))
async def edit_delete_item(callback: CallbackQuery):
    """Maxsus mahsulotni o'chirish"""
    try:
        custom_id = int(callback.data.split("_")[2])
        success = remove_from_cart(callback.from_user.id, custom_id)
        
        if success:
            await callback.answer("✅ Mahsulot o'chirildi")
            await show_cart(callback.message, None)
        else:
            await callback.answer("❌ Mahsulot topilmadi", show_alert=True)
            
    except Exception as e:
        logger.error(f"Maxsus mahsulotni o'chirishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data.startswith("edit_qty_"))
async def edit_qty_start(callback: CallbackQuery, state: FSMContext):
    """Miqdorni o'zgartirishni boshlash"""
    try:
        custom_id = int(callback.data.split("_")[2])
        await state.update_data(edit_item_id=custom_id)
        
        await callback.message.edit_text(
            "✏️ *Yangi miqdorni kiriting*\n\n"
            "Format: `son birlik`\n"
            "Masalan: `2.5 kg` yoki `3 dona`\n\n"
            "ℹ️ Agar birlikni o'zgartirmoqchi bo'lsangiz, yangi birlik bilan yozing.",
            parse_mode="Markdown"
        )
        await state.set_state(EditCustomItem.waiting_for_new_quantity)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Miqdorni o'zgartirishni boshlashda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.message(EditCustomItem.waiting_for_new_quantity)
async def edit_qty_received(message: types.Message, state: FSMContext):
    """Yangi miqdorni qabul qilish"""
    try:
        await send_typing_action(message.bot, message.chat.id)
        
        text = message.text.strip()
        product = parse_product_line(f"Mahsulot - {text}")
        
        if not product:
            await message.answer(
                "❌ *Noto'g'ri format.*\n\n"
                "Iltimos, quyidagi formatda kiriting:\n"
                "`son birlik`\n\n"
                "Masalan: `2.5 kg` yoki `3 dona`",
                parse_mode="Markdown"
            )
            return
        
        data = await state.get_data()
        item_id = data['edit_item_id']
        new_qty = product['quantity']
        new_unit = normalize_unit(product['unit'])
        
        # Yangilash
        success = update_cart_item_qty(message.from_user.id, item_id, new_qty)
        
        if success:
            # Agar birlik o'zgargan bo'lsa, uni ham yangilash kerak
            # (bu uchun maxsus funksiya kerak)
            await message.answer(
                f"✅ *Miqdor yangilandi!*\n\nYangi miqdor: {new_qty} {new_unit}",
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ Mahsulot topilmadi")
        
        await state.clear()
        
        # Savatni ko'rsatish
        await show_cart(message, state=None)
        
    except Exception as e:
        logger.error(f"Yangi miqdorni qabul qilishda xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        await state.clear()

@router.callback_query(F.data == "back_to_cart")
async def back_to_cart(callback: CallbackQuery, state: FSMContext):
    """Savatga qaytish"""
    await state.clear()
    await show_cart(callback.message, None)
    await callback.answer()