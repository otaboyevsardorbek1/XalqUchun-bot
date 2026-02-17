from aiogram import Router, types, F
from aiogram.filters import Command
from keyboards.main import main_menu
from db.database import AsyncSessionLocal
from db.models import User
from sqlalchemy import select
from config import ADMIN_IDS

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name

    # Foydalanuvchini bazaga qo'shish (agar mavjud bo'lmasa)
    async with AsyncSessionLocal() as session:
        if user_id in ADMIN_IDS:
            await message.answer("Admin sifatida tizimga kirdingiz!")
            return
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            new_user = User(telegram_id=user_id, full_name=full_name)
            session.add(new_user)
            await session.commit()

    await message.answer(
        "Assalomu alaykum! Xush kelibsiz.\n"
        "Buyurtma berish uchun quyidagi tugmalardan foydalaning."
        "bu bot xozirda test rejimida ishlamoqda\nbuyurtmalarni qabul qilinadi ammo bekor qilib bo`lmaydi\nBatafsil ma`lumot uchun /info ni bosing",
        reply_markup=main_menu
    )

@router.message(F.text == "📞 Biz bilan bogʻlanish")
@router.message(Command("info"))
async def contact_us(message: types.Message):
    await message.answer(
        "Biz bilan bogʻlanish uchun:\n"
        "Admin: @bbm1311\n"
        "Admin telefon: +998958182728\n"
        "Dasturchi: @prodevuzoff\n"
        "Dasturchi telefon:+998918610470\n"
        "Sizning fikr-mulohazalaringiz biz uchun muhim!"
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🆘 **Yordam**\n\n"
        "Quyidagi buyruqlar mavjud:\n"
        "/start - Botni ishga tushirish\n"
        "/help - Yordam oynasi\n"
        "/profile - Profil ma'lumotlari\n"
        "/orders - (faqat adminlar uchun) Yangi buyurtmalarni ko'rish\n\n"
        "Botdan foydalanish:\n"
        "• Katalogdan mahsulot tanlang\n"
        "• Maxsus buyurtma berishingiz mumkin\n"
        "• Savatni ko'rib, tahrirlang\n"
        "• Buyurtmani tasdiqlang"
    )