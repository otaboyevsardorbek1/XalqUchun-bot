# bot/handlers/start.py
from aiogram import Router, types, F
from typing import Union
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.keyboards.main import get_main_menu, get_admin_menu
from bot.utils.referral import add_user
from bot.data import ADMIN_IDS, ALL_OWNER_IDS, BOT_TOKEN
from bot.utils.helpers import format_phone_for_display
import logging

router = Router()
logger = logging.getLogger(__name__)

WELCOME_MESSAGE = """
🌟 *XUSH KELIBSIZ!* 🌟

Assalomu alaykum, {name}!

Bizning do'konimizda eng sifatli mahsulotlarni xarid qilishingiz mumkin.

📌 *Qanday buyurtma berish mumkin:*
1️⃣ 🛍 *Katalog* - kerakli mahsulotni tanlang
2️⃣ 🔢 *Miqdorni* belgilang
3️⃣ 🛒 *Savatga* qo'shing
4️⃣ ✅ *Buyurtma berish* tugmasini bosing
5️⃣ 📞 Telefon raqamingizni yuboring
6️⃣ 📍 Joylashuvingizni yuboring

🎁 *Har bir buyurtma uchun bonuslar!*

Qanday yordam kerak? /help
"""

ADMIN_WELCOME = """
👑 *ADMIN PANELIGA XUSH KELIBSIZ!* 👑

Sizda quyidagi imkoniyatlar mavjud:

📊 *Buyurtmalarni boshqarish*
👥 *Foydalanuvchilarni boshqarish*
💰 *To'lovlarni boshqarish*
📢 *Ommaviy xabarlar*
📈 *Statistika*

Asosiy buyruqlar:
• /orders - Yangi buyurtmalar
• /users - Foydalanuvchilar
• /ads - Xabar yuborish
• /help - To'liq yordam
"""

async def bot_token_id() -> int:
    """Bot ID sini olish"""
    try:
        return int(BOT_TOKEN.split(':')[0])
    except Exception as e:
        logger.error(f"Bot token ID olishda xato: {e}")
        return 0

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Start komandasi"""
    try:
        args = message.text.split()
        referrer_id = None
        
        # Referral ID ni tekshirish
        if len(args) > 1 and args[1].isdigit():
            referrer_id = int(args[1])
        
        # Foydalanuvchini ro'yxatdan o'tkazish
        await add_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name,
            referrer_id
        )
        
        # Foydalanuvchi adminmi?
        is_admin = message.from_user.id in ADMIN_IDS or message.from_user.id in ALL_OWNER_IDS
        
        # Chiroyli start xabari
        welcome_text = ADMIN_WELCOME if is_admin else WELCOME_MESSAGE
        welcome_text = welcome_text.format(name=message.from_user.full_name)
        
        # Chiroyli inline tugmalar
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Katalog", callback_data="show_catalog")],
            [InlineKeyboardButton(text="📝 Maxsus buyurtma", callback_data="custom_order")],
            [InlineKeyboardButton(text="📞 Bog'lanish", callback_data="contact_info")],
            [InlineKeyboardButton(text="❓ Yordam", callback_data="help")]
        ])
        
        await message.answer(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=kb
        )
        
        logger.info(f"Foydalanuvchi start: {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Start komandasida xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

@router.message(F.text == "📞 Bog'lanish")
@router.message(Command("info"))
@router.callback_query(F.data == "contact_info")
async def contact_info(event:types.CallbackQuery):
    """Bog'lanish ma'lumotlari"""
    text = """
📞 *BIZ BILAN BOG'LANISH*

┌─────────────────────
│ 👤 *Admin:* @bbm1311
│ 📱 *Telefon:* +998 95 818 27 28
├─────────────────────
│ 👨‍💻 *Dasturchi:* @prodevuzoff
│ 📱 *Telefon:* +998 91 861 04 70
├─────────────────────
│ ⏰ *Ish vaqti:* 09:00 - 22:00
│ 📍 *Manzil:* Namangan viloyati 
└─────────────────────

🌐 *Website:* https://sost.uz/

Savollar bo'lsa, bemalol murojaat qiling!
    """
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_to_main")]
    ])
    
    if isinstance(event, types.Message):
        await event.answer(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await event.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        await event.answer()

@router.message(Command("help"))
@router.callback_query(F.data == "help")
async def cmd_help(event: Union[Message, CallbackQuery]):
    """Yordam komandasi"""
    is_admin = False
    user_id = event.from_user.id if isinstance(event, types.Message) else event.from_user.id
    
    if isinstance(event, types.CallbackQuery):
        user_id = event.from_user.id
    
    is_admin = user_id in ADMIN_IDS or user_id in ALL_OWNER_IDS
    
    help_text = """
🆘 *YORDAM BO'LIMI* 🆘

📌 *ASOSIY BUYRUQLAR:*
• /start - Botni ishga tushirish
• /help - Yordam oynasi
• /profile - Profil ma'lumotlari
• /info - Bog'lanish ma'lumotlari

👥 *REFERAL TIZIM:*
• /tree - Referal daraxti (matn)
• /treeimg - Referal daraxti (rasm)
• /downline - Avlodlar soni
• /me - To'liq profil
• /balance - Balansni ko'rish
• /withdraw [summa] - Pul yechish
• /transactions - Tranzaksiyalar

🛒 *BUYURTMA TIZIMI:*
1. Katalog → Mahsulot tanlash
2. Miqdorni belgilash
3. Savatga qo'shish
4. Buyurtma berish

📝 *Maxsus buyurtma formati:*
`Mahsulot - miqdor birlik`
Misol: `Olma - 2 kg`

✅ *Telefon raqam* bir marta so'raladi
📍 *Lokatsiya* har bir buyurtmada so'raladi
    """
    
    if is_admin:
        help_text += """
        
👑 *ADMIN BUYRUGLARI:*
• /orders - Buyurtmalarni boshqarish
• /setrole [id] [rol] - Rol o'zgartirish
• /users - Foydalanuvchilar ro'yxati
• /withdraw_requests - Pul so'rovlari
• /confirm_withdraw [id] - Tasdiqlash
• /decline_withdraw [id] - Rad etish
• /export_withdraws - CSV eksport
• /maintenance_on - Texnik rejim
• /maintenance_off - Texnik rejim o'chirish
• /log - Log faylini olish
        """
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_to_main")]
    ])
    
    if isinstance(event, types.Message):
        await event.answer(help_text, parse_mode="Markdown", reply_markup=kb)
    else:
        await event.message.edit_text(help_text, parse_mode="Markdown", reply_markup=kb)
        await event.answer()

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    """Asosiy menyuga qaytish"""
    is_admin = callback.from_user.id in ADMIN_IDS or callback.from_user.id in ALL_OWNER_IDS
    
    text = "🌟 *Asosiy menyu* 🌟\n\nKerakli bo'limni tanlang:"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Katalog", callback_data="show_catalog")],
        [InlineKeyboardButton(text="📝 Maxsus buyurtma", callback_data="custom_order")],
        [InlineKeyboardButton(text="🛒 Savat", callback_data="view_cart")],
        [InlineKeyboardButton(text="👤 Profil", callback_data="view_profile")],
        [InlineKeyboardButton(text="📞 Bog'lanish", callback_data="contact_info")],
        [InlineKeyboardButton(text="❓ Yordam", callback_data="help")]
    ])
    
    try:
        await callback.message.delete()
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=kb)
    except:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    
    await callback.answer()

@router.callback_query(F.data == "show_catalog")
async def show_catalog_callback(callback: types.CallbackQuery):
    """Katalogga o'tish"""
    from bot.handlers.catalog import show_categories
    await show_categories(callback.message)
    await callback.answer()