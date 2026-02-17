from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
import re

from config import ADMIN_IDS
from db.database import AsyncSessionLocal
from db.models import User
from keyboards.main import main_menu

router = Router()

class ProfileState(StatesGroup):
    waiting_for_new_phone = State()

@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    user_id = message.from_user.id
    user_full_name = message.from_user.full_name
    if user_id in ADMIN_IDS:
        await message.answer("Admin profilingiz:\n\n" f"ID: {user_id}\nIsm familya: {user_full_name}\nSiz admin sifatida tizimga kirdingiz!")
        return
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("Siz hali ro'yxatdan o'tmagansiz. /start ni bosing.")
            return

        text = (
            f"👤 **Sizning profilingiz**\n\n"
            f"ID: {user.id}\n"
            f"Telegram ID: {user.telegram_id}\n"
            f"Ism familya: {user_full_name}\n"
            f"Telefon: +{user.phone or '❌ ko‘rsatilmagan'}\n"
            f"Ro'yxatdan o'tgan vaqt: {user.created_at.strftime('%Y-%m-%d %H:%M')}"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📞 Telefon raqamni yangilash", callback_data="update_phone")]
        ])
        await message.answer(text, parse_mode="Markdown", reply_markup=kb)

@router.callback_query(F.data == "update_phone")
async def update_phone_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await callback.message.answer(
        "Iltimos, yangi telefon raqamingizni yuborish tugmasini bosing yoki +998 XX XXX XX XX formatida kiriting:",
        reply_markup=kb
    )
    await state.set_state(ProfileState.waiting_for_new_phone)
    await callback.answer()

@router.message(ProfileState.waiting_for_new_phone, F.contact)
async def update_phone_contact(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    await update_user_phone(message.from_user.id, phone)
    await message.answer("✅ Telefon raqam yangilandi!", reply_markup=main_menu)
    await state.clear()

@router.message(ProfileState.waiting_for_new_phone)
async def update_phone_text(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    cleaned = re.sub(r'[^\d+]', '', phone)
    if not re.match(r'^\+998\d{9}$', cleaned):
        await message.answer("❌ Noto'g'ri format. Iltimos, +998 XX XXX XX XX formatida kiriting.")
        return
    await update_user_phone(message.from_user.id, cleaned)
    await message.answer("✅ Telefon raqam yangilandi!", reply_markup=main_menu)
    await state.clear()

async def update_user_phone(telegram_id: int, phone: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            user.phone = phone
            await session.commit()