import re
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from bot.data import ADMIN_IDS
from bot.db.database import AsyncSessionLocal
from bot.db.models import User
from bot.keyboards.main import main_menu
from bot.utils.referral import get_user_by_tid

router = Router()

class ProfileState(StatesGroup):
    waiting_for_new_phone = State()

def validate_uz_phone(phone: str) -> bool:
    cleaned = re.sub(r'[^\d+]', '', phone)
    if cleaned.startswith('+998') and len(cleaned) == 13:
        return True
    if cleaned.startswith('998') and len(cleaned) == 12:
        return True
    if len(cleaned) == 9 and cleaned.isdigit():
        return True
    return False

def normalize_uz_phone(phone: str) -> str:
    cleaned = re.sub(r'[^\d+]', '', phone)
    if cleaned.startswith('998') and len(cleaned) == 12:
        return '+' + cleaned
    if len(cleaned) == 9:
        return '+998' + cleaned
    return cleaned

@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:
        await message.answer(f"Admin profilingiz:\nID: {user_id}\nIsm: {message.from_user.full_name}")
        return
    async with AsyncSessionLocal() as session:
        user = await get_user_by_tid(session, user_id)
        if not user:
            await message.answer("Siz roʻyxatdan oʻtmagan. /start ni bosing.")
            return
        text = (
            f"👤 Profilingiz\n"
            f"ID: {user.telegram_id}\n"
            f"Ism: {user.full_name}\n"
            f"Telefon: {user.phone or '❌'}\n"
            f"Rol: {user.role}\n"
            f"Balans: {user.balance:.2f} soʻm\n"
            f"Takliflar: {user.referrals_count}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📞 Telefonni yangilash", callback_data="update_phone")]
        ])
        await message.answer(text, reply_markup=kb)

@router.callback_query(F.data == "update_phone")
async def update_phone_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await callback.message.answer(
        "Yangi telefon raqamingizni yuboring (+998 XX XXX XX XX):",
        reply_markup=kb
    )
    await state.set_state(ProfileState.waiting_for_new_phone)
    await callback.answer()

@router.message(ProfileState.waiting_for_new_phone, F.contact)
async def update_phone_contact(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    if not validate_uz_phone(phone):
        await message.answer("❌ Notoʻgʻri Oʻzbekiston raqami. Iltimos, qayta urinib koʻring.")
        return
    phone = normalize_uz_phone(phone)
    await update_user_phone(message.from_user.id, phone)
    await message.answer("✅ Telefon raqam yangilandi!", reply_markup=main_menu)
    await state.clear()

@router.message(ProfileState.waiting_for_new_phone)
async def update_phone_text(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if not validate_uz_phone(phone):
        await message.answer("❌ Notoʻgʻri format. Iltimos, +998 XX XXX XX XX formatida kiriting.")
        return
    phone = normalize_uz_phone(phone)
    await update_user_phone(message.from_user.id, phone)
    await message.answer("✅ Telefon raqam yangilandi!", reply_markup=main_menu)
    await state.clear()

async def update_user_phone(telegram_id: int, phone: str):
    async with AsyncSessionLocal() as session:
        user = await get_user_by_tid(session, telegram_id)
        if user:
            user.phone = phone
            await session.commit()