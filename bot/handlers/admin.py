from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
import re
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from states.admin import BroadcastState
from aiogram.exceptions import TelegramBadRequest
import asyncio

from bot.data import ADMIN_IDS
from bot.db.database import AsyncSessionLocal
from bot.db.models import Order, OrderItem,  User
from bot.states.admin import CourierState
import logging

router = Router()
logger = logging.getLogger(__name__)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(Command("orders"))
async def list_orders(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("Siz admin emassiz!")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Order).where(Order.status == "new").options(selectinload(Order.items).selectinload(OrderItem.product))
        )
        orders = result.scalars().all()
        if not orders:
            await message.answer("Yangi buyurtmalar yoʻq.")
            return

        for order in orders:
            text = f"Buyurtma #{order.id}\n"
            text += f"Telefon: {order.phone}\n"
            text += f"Lokatsiya: {order.location_link}\n"
            text += "Mahsulotlar:\n"
            total = 0
            for item in order.items:
                if item.product_id:
                    name = item.product.name
                    subtotal = item.quantity * item.price
                else:
                    name = item.custom_name or "Maxsus"
                    subtotal = 0  # maxsus mahsulot narxi 0
                text += f"  {name} x{item.quantity} = {subtotal} so'm\n"
                total += subtotal
            text += f"Jami: {total} so'm\n"
            text += f"Vaqt: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Tayyor", callback_data=f"admin_ready_{order.id}"),
                 InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"admin_cancel_{order.id}")]
            ])
            await message.answer(text, reply_markup=kb)

@router.callback_query(F.data.startswith("admin_ready_"))
async def admin_ready(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[2])
    await state.update_data(order_id=order_id)
    await callback.message.edit_text(
        "Kuryer telefon raqamini kiriting (+998 XX XXX XX XX):"
    )
    await state.set_state(CourierState.waiting_for_courier_phone)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_cancel_"))
async def admin_cancel(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[2])
    await state.update_data(order_id=order_id)
    await callback.message.edit_text(
        "Bekor qilish sababini kiriting:"
    )
    await state.set_state(CourierState.waiting_for_cancel_reason)
    await callback.answer()

@router.message(CourierState.waiting_for_courier_phone)
async def courier_phone_received(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    cleaned = re.sub(r'[^\d+]', '', phone)
    if not re.match(r'^\+998\d{9}$', cleaned):
        await message.answer("❌ Noto'g'ri format. Iltimos, +998 XX XXX XX XX formatida kiriting.")
        return
    data = await state.get_data()
    order_id = data['order_id']
    # Tasdiqlash tugmasi
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm_courier_{order_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_cancel_action")]
    ])
    await message.answer(
        f"Kuryer raqami: {cleaned}\nTasdiqlaysizmi?",
        reply_markup=kb
    )
    await state.update_data(courier_phone=cleaned)

@router.callback_query(F.data.startswith("confirm_courier_"))
async def confirm_courier(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    courier_phone = data['courier_phone']
    async with AsyncSessionLocal() as session:
        order = await session.get(Order, order_id)
        if order:
            order.status = "ready"
            await session.commit()
            user_id = order.user_id
            user = await session.get(User, user_id)
            if user:
                try:
                    await callback.bot.send_message(
                        user.telegram_id,
                        f"✅ Sizning buyurtmangiz tayyor!\n"
                        f"Kuryer telefon raqami: {courier_phone}\n"
                        f"U bilan bog'lanib, yetib kelgan vaqtni bilib olishingiz mumkin."
                    )
                except Exception as e:
                    logger.error(f"Foydalanuvchiga xabar yuborilmadi: {e}")
    await callback.message.edit_text("✅ Buyurtma tayyor deb belgilandi va foydalanuvchiga xabar yuborildi.")
    await state.clear()
    await callback.answer()

@router.message(CourierState.waiting_for_cancel_reason)
async def cancel_reason_received(message: types.Message, state: FSMContext):
    reason = message.text.strip()
    data = await state.get_data()
    order_id = data['order_id']
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm_cancel_{order_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_cancel_action")]
    ])
    await message.answer(
        f"Sabab: {reason}\nTasdiqlaysizmi?",
        reply_markup=kb
    )
    await state.update_data(cancel_reason=reason)

@router.callback_query(F.data.startswith("confirm_cancel_"))
async def confirm_cancel(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    reason = data['cancel_reason']
    async with AsyncSessionLocal() as session:
        order = await session.get(Order, order_id)
        if order:
            order.status = "cancelled"
            await session.commit()
            user_id = order.user_id
            user = await session.get(User, user_id)
            if user:
                try:
                    await callback.bot.send_message(
                        user.telegram_id,
                        f"❌ Sizning buyurtmangiz bekor qilindi.\nSabab: {reason}"
                    )
                except Exception as e:
                    logger.error(f"Foydalanuvchiga xabar yuborilmadi: {e}")
    await callback.message.edit_text("✅ Buyurtma bekor qilindi va foydalanuvchiga xabar yuborildi.")
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "admin_cancel_action")
async def admin_cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Amal bekor qilindi.")
    await callback.answer()

# ------------------- Broadcast (ommaviy xabar) -------------------

def get_broadcast_type_keyboard():
    """Broadcast turini tanlash uchun inline klaviatura"""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Faqat matn", callback_data="broadcast_type_text")],
        [InlineKeyboardButton(text="🖼 Rasm", callback_data="broadcast_type_photo")],
        [InlineKeyboardButton(text="🎥 Video", callback_data="broadcast_type_video")],
        [InlineKeyboardButton(text="📄 Hujjat", callback_data="broadcast_type_document")],
        [InlineKeyboardButton(text="📝+🖼 Matn va rasm", callback_data="broadcast_type_text_photo")],
        [InlineKeyboardButton(text="📝+🎥 Matn va video", callback_data="broadcast_type_text_video")],
        [InlineKeyboardButton(text="📝+📄 Matn va hujjat", callback_data="broadcast_type_text_document")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel")]
    ])
    return kb

@router.message(Command("ads"))
async def admin_broadcast_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Siz admin emassiz!")
        return
    await state.clear()
    await message.answer(
        "📢 **Ommaviy xabar yuborish**\n\n"
        "Qanday turdagi xabar yubormoqchisiz?",
        reply_markup=get_broadcast_type_keyboard(),
        parse_mode="Markdown"
    )
# /ads
@router.callback_query(F.data.startswith("broadcast_type_"))
async def broadcast_type_selected(callback: CallbackQuery, state: FSMContext):
    cb_type = callback.data.replace("broadcast_type_", "")
    
    if cb_type == "cancel":
        await state.clear()
        await callback.message.edit_text("❌ Broadcast bekor qilindi.")
        await callback.answer()
        return

    # Tanlangan turni saqlaymiz
    await state.update_data(broadcast_type=cb_type)

    # State ni mos keladigan holatga o'tkazamiz va kerakli so'rovni yuboramiz
    if cb_type == "text":
        await state.set_state(BroadcastState.waiting_for_broadcast_text)
        await callback.message.edit_text(
            "✍️ Yubormoqchi bo'lgan matningizni kiriting:"
        )

    elif cb_type == "photo":
        await state.set_state(BroadcastState.waiting_for_broadcast_photo)
        await callback.message.edit_text(
            "🖼 Rasmni yuboring (agar sarlavha qo'shmoqchi bo'lsangiz, rasm bilan birga yozishingiz mumkin):"
        )

    elif cb_type == "video":
        await state.set_state(BroadcastState.waiting_for_broadcast_video)
        await callback.message.edit_text(
            "🎥 Videoni yuboring (sarlavha bilan birga bo'lishi mumkin):"
        )

    elif cb_type == "document":
        await state.set_state(BroadcastState.waiting_for_broadcast_document)
        await callback.message.edit_text(
            "📄 Hujjatni yuboring (sarlavha bilan birga bo'lishi mumkin):"
        )

    elif cb_type == "text_photo":
        await state.set_state(BroadcastState.waiting_for_broadcast_text_and_photo)
        await callback.message.edit_text(
            "✍️ Avval matnni kiriting:"
        )

    elif cb_type == "text_video":
        await state.set_state(BroadcastState.waiting_for_broadcast_text_and_video)
        await callback.message.edit_text(
            "✍️ Avval matnni kiriting:"
        )

    elif cb_type == "text_document":
        await state.set_state(BroadcastState.waiting_for_broadcast_text_and_document)
        await callback.message.edit_text(
            "✍️ Avval matnni kiriting:"
        )

    await callback.answer()

# ------------------- Matn qabul qilish -------------------
@router.message(BroadcastState.waiting_for_broadcast_text)
async def broadcast_text_received(message: types.Message, state: FSMContext):
    text = message.text
    await state.update_data(broadcast_text=text)
    # Tasdiqlash
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="broadcast_confirm")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel")]
    ])
    await message.answer(
        f"📝 **Matn**:\n\n{text}\n\nUshbu xabarni barcha foydalanuvchilarga yuborishni tasdiqlaysizmi?",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await state.set_state(BroadcastState.waiting_for_broadcast_text_and_media_type)  # faqat tasdiqlash uchun

# ------------------- Rasm qabul qilish -------------------
@router.message(BroadcastState.waiting_for_broadcast_photo, F.photo)
async def broadcast_photo_received(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    caption = message.caption or ""
    await state.update_data(broadcast_photo=photo_id, broadcast_caption=caption)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="broadcast_confirm")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel")]
    ])
    await message.answer_photo(
        photo=photo_id,
        caption=f"🖼 **Rasm**\n\n{caption}\n\nUshbu xabarni yuborishni tasdiqlaysizmi?",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await state.set_state(BroadcastState.waiting_for_broadcast_text_and_media_type)

# ------------------- Video qabul qilish -------------------
@router.message(BroadcastState.waiting_for_broadcast_video, F.video)
async def broadcast_video_received(message: types.Message, state: FSMContext):
    video_id = message.video.file_id
    caption = message.caption or ""
    await state.update_data(broadcast_video=video_id, broadcast_caption=caption)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="broadcast_confirm")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel")]
    ])
    await message.answer_video(
        video=video_id,
        caption=f"🎥 **Video**\n\n{caption}\n\nUshbu xabarni yuborishni tasdiqlaysizmi?",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await state.set_state(BroadcastState.waiting_for_broadcast_text_and_media_type)

# ------------------- Hujjat qabul qilish -------------------
@router.message(BroadcastState.waiting_for_broadcast_document, F.document)
async def broadcast_document_received(message: types.Message, state: FSMContext):
    doc_id = message.document.file_id
    caption = message.caption or ""
    await state.update_data(broadcast_document=doc_id, broadcast_caption=caption)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="broadcast_confirm")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel")]
    ])
    await message.answer_document(
        document=doc_id,
        caption=f"📄 **Hujjat**\n\n{caption}\n\nUshbu xabarni yuborishni tasdiqlaysizmi?",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await state.set_state(BroadcastState.waiting_for_broadcast_text_and_media_type)

# ------------------- Matn+rasm: birinchi qadam (matn) -------------------
@router.message(BroadcastState.waiting_for_broadcast_text_and_photo)
async def broadcast_text_and_photo_step1(message: types.Message, state: FSMContext):
    await state.update_data(broadcast_text=message.text)
    await state.set_state(BroadcastState.waiting_for_broadcast_text_and_photo_step2)
    await message.answer("🖼 Endi rasmni yuboring:")

# Matn+rasm: ikkinchi qadam (rasm)
@router.message(BroadcastState.waiting_for_broadcast_text_and_photo_step2, F.photo)
async def broadcast_text_and_photo_step2(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = data.get('broadcast_text', '')
    photo_id = message.photo[-1].file_id
    await state.update_data(broadcast_photo=photo_id, broadcast_caption=text)  # text caption sifatida
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="broadcast_confirm")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel")]
    ])
    await message.answer_photo(
        photo=photo_id,
        caption=text,
        reply_markup=kb
    )
    await state.set_state(BroadcastState.waiting_for_broadcast_text_and_media_type)

# ------------------- Matn+video: birinchi qadam (matn) -------------------
@router.message(BroadcastState.waiting_for_broadcast_text_and_video)
async def broadcast_text_and_video_step1(message: types.Message, state: FSMContext):
    await state.update_data(broadcast_text=message.text)
    await state.set_state(BroadcastState.waiting_for_broadcast_text_and_video_step2)
    await message.answer("🎥 Endi videoni yuboring:")

@router.message(BroadcastState.waiting_for_broadcast_text_and_video_step2, F.video)
async def broadcast_text_and_video_step2(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = data.get('broadcast_text', '')
    video_id = message.video.file_id
    await state.update_data(broadcast_video=video_id, broadcast_caption=text)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="broadcast_confirm")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel")]
    ])
    await message.answer_video(
        video=video_id,
        caption=text,
        reply_markup=kb
    )
    await state.set_state(BroadcastState.waiting_for_broadcast_text_and_media_type)

# ------------------- Matn+hujjat: birinchi qadam (matn) -------------------
@router.message(BroadcastState.waiting_for_broadcast_text_and_document)
async def broadcast_text_and_document_step1(message: types.Message, state: FSMContext):
    await state.update_data(broadcast_text=message.text)
    await state.set_state(BroadcastState.waiting_for_broadcast_text_and_document_step2)
    await message.answer("📄 Endi hujjatni yuboring:")

@router.message(BroadcastState.waiting_for_broadcast_text_and_document_step2, F.document)
async def broadcast_text_and_document_step2(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = data.get('broadcast_text', '')
    doc_id = message.document.file_id
    await state.update_data(broadcast_document=doc_id, broadcast_caption=text)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="broadcast_confirm")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast_cancel")]
    ])
    await message.answer_document(
        document=doc_id,
        caption=text,
        reply_markup=kb
    )
    await state.set_state(BroadcastState.waiting_for_broadcast_text_and_media_type)

# ------------------- Tasdiqlash va yuborish -------------------
async def get_all_users():
    """Barcha foydalanuvchilarning telegram_id larini qaytaradi"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User.telegram_id))
        return [row[0] for row in result.all()]

@router.callback_query(F.data == "broadcast_confirm")
async def broadcast_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    broadcast_type = data.get('broadcast_type')
    
    # Xabar turiga qarab, mavjud xabarni o'chirib, yangi "yuborilmoqda" xabarini yuborish
    await callback.message.delete()
    status_msg = await callback.message.answer("⏳ Xabarlar yuborilmoqda. Bu biroz vaqt olishi mumkin...")
    await callback.answer()

    users = await get_all_users()
    if not users:
        await status_msg.edit_text("❌ Hech qanday foydalanuvchi topilmadi.")
        await state.clear()
        return

    success = 0
    failed = 0

    for uid in users:
        try:
            if broadcast_type == "text":
                await callback.bot.send_message(uid, data['broadcast_text'])
            elif broadcast_type == "photo":
                await callback.bot.send_photo(uid, data['broadcast_photo'], caption=data.get('broadcast_caption', ''))
            elif broadcast_type == "video":
                await callback.bot.send_video(uid, data['broadcast_video'], caption=data.get('broadcast_caption', ''))
            elif broadcast_type == "document":
                await callback.bot.send_document(uid, data['broadcast_document'], caption=data.get('broadcast_caption', ''))
            elif broadcast_type in ("text_photo", "text_video", "text_document"):
                if broadcast_type == "text_photo":
                    await callback.bot.send_photo(uid, data['broadcast_photo'], caption=data.get('broadcast_caption', ''))
                elif broadcast_type == "text_video":
                    await callback.bot.send_video(uid, data['broadcast_video'], caption=data.get('broadcast_caption', ''))
                elif broadcast_type == "text_document":
                    await callback.bot.send_document(uid, data['broadcast_document'], caption=data.get('broadcast_caption', ''))
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Xatolik user {uid}: {e}")
            failed += 1

    await status_msg.edit_text(
        f"✅ **Broadcast yakunlandi**\n\n"
        f"👥 Jami foydalanuvchilar: {len(users)}\n"
        f"✅ Yuborildi: {success}\n"
        f"❌ Xatolik: {failed}"
    )
    await state.clear()
    
@router.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Broadcast bekor qilindi.")
    await callback.answer()
