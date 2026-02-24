from aiogram import Router, types, F
from aiogram.filters import Command
from bot.keyboards.main import main_menu, admin_menu
from bot.utils.referral import add_user
from bot.data import ADMIN_IDS, ALL_OWNER_IDS
from bot.data import BOT_TOKEN
import logging

router = Router()
logger = logging.getLogger(__name__)

async def bot_token_id():
    """Bot tokenidan bot ID sini olish"""
    try:
        bot_id_parse = BOT_TOKEN.split(':')[0]
        return int(bot_id_parse)
    except Exception as e:
        logger.error(f"Bot token ID olishda xato: {e}")
        return None

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Start komandasi - botni ishga tushirish va foydalanuvchini ro'yxatdan o'tkazish"""
    try:
        args = message.text.split()
        ref = None
        
        # Referral ID ni tekshirish
        if len(args) > 1 and args[1].isdigit():
            ref = int(args[1])
            await add_user(
                message.from_user.id,
                message.from_user.username,
                message.from_user.full_name, 
                ref)
            logger.info(f"Yangi foydalanuvchi referal orqali qo'shildi: {message.from_user.id} (referrer: {ref})")
        else:
            ref = await bot_token_id()
            await add_user(
                message.from_user.id,
                message.from_user.username,
                message.from_user.full_name, 
                ref)
            logger.info(f"Yangi foydalanuvchi qo'shildi: {message.from_user.id}")
        
        # Foydalanuvchi admin yoki oddiy foydalanuvchi ekanligini tekshirish
        if message.from_user.id in ADMIN_IDS or message.from_user.id in ALL_OWNER_IDS:
            await message.answer(
                "👋 *Assalomu alaykum, admin! Xush kelibsiz.*\n\n"
                "📊 *Admin paneliga xush kelibsiz*\n\n"
                "🔹 Yangi buyurtmalarni ko'rish uchun /orders\n"
                "🔹 Foydalanuvchilarni boshqarish uchun /users\n"
                "🔹 To'liq yordam uchun /help",
                parse_mode="Markdown",
                reply_markup=admin_menu
            )
        else:
            await message.answer(
                "👋 *Assalomu alaykum! Xush kelibsiz.*\n\n"
                "🛍 *Do'konimizga xush kelibsiz!*\n\n"
                "✅ *Buyurtma berish uchun:*\n"
                "1. 🛍 Katalog - mahsulotlarni tanlang\n"
                "2. 🛒 Savat - tanlangan mahsulotlarni ko'ring\n"
                "3. ✅ Buyurtma berish - buyurtmani yakunlang\n\n"
                "📝 *Maxsus buyurtma* - o'zingiz xohlagan mahsulotni buyurtma qiling\n\n"
                "❓ Yordam uchun /help",
                parse_mode="Markdown",
                reply_markup=main_menu
            )
    except Exception as e:
        logger.error(f"Start komandasida xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

@router.message(F.text == "📞 Biz bilan bogʻlanish")
@router.message(Command("info"))
async def contact_us(message: types.Message):
    """Bog'lanish ma'lumotlari"""
    await message.answer(
        "📞 *BIZ BILAN BOG'LANISH*\n\n"
        "┌─────────────────────\n"
        "│ 👤 *Admin:* @bbm1311\n"
        "│ 📱 *Telefon:* +998 95 818 27 28\n"
        "├─────────────────────\n"
        "│ 👨‍💻 *Dasturchi:* @prodevuzoff\n"
        "│ 📱 *Telefon:* +998 91 861 04 70\n"
        "├─────────────────────\n"
        "│ ⏰ *Ish vaqti:* 09:00 - 22:00\n"
        "│ 📍 *Manzil:* Toshkent shahri\n"
        "└─────────────────────\n\n"
        "📧 *Email:* support@example.com\n"
        "🌐 *Website:* www.example.com",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

# ==================== MUKAMMAL HELP KOMMANDASI ====================
@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Foydalanuvchi va adminlar uchun to'liq yordam xabari"""
    try:
        # Foydalanuvchi admin yoki owner ekanligini tekshirish
        is_admin = message.from_user.id in ADMIN_IDS or message.from_user.id in ALL_OWNER_IDS
        
        # Asosiy yordam matni
        help_text = "🆘 *YORDAM BO'LIMI* 🆘\n\n"
        
        # ========== ASOSIY BUYRUQLAR ==========
        help_text += "📌 *ASOSIY BUYRUQLAR:*\n"
        help_text += "┌─────────────────────────────────\n"
        help_text += "│ 🔹 `/start` - Botni ishga tushirish\n"
        help_text += "│ 🔹 `/help` - Yordam oynasi\n"
        help_text += "│ 🔹 `/profile` - Profil ma'lumotlari\n"
        help_text += "│ 🔹 `/info` - Bog'lanish ma'lumotlari\n"
        help_text += "└─────────────────────────────────\n\n"
        
        # ========== REFERAL TIZIM ==========
        help_text += "👥 *REFERAL TIZIM:*\n"
        help_text += "┌─────────────────────────────────\n"
        help_text += "│ 🌳 `/tree` - Referal daraxti (matn)\n"
        help_text += "│ 🖼 `/treeimg` - Referal daraxti (rasm)\n"
        help_text += "│ 📊 `/downline` - Avlodlar soni\n"
        help_text += "│ 👤 `/me` - To'liq profil\n"
        help_text += "│ 💰 `/balance` - Balansni ko'rish\n"
        help_text += "│ 💸 `/withdraw [summa]` - Pul yechish\n"
        help_text += "│ 📜 `/transactions` - Tranzaksiyalar\n"
        help_text += "└─────────────────────────────────\n\n"
        
        # ========== BUYURTMA TIZIMI ==========
        help_text += "🛒 *BUYURTMA TIZIMI:*\n"
        help_text += "┌─────────────────────────────────\n"
        help_text += "│ 📦 *Oddiy buyurtma:*\n"
        help_text += "│   1. Katalog → Mahsulot tanlash\n"
        help_text += "│   2. Miqdorni belgilash\n"
        help_text += "│   3. Savatga qo'shish\n"
        help_text += "│   4. Savat → Buyurtma berish\n"
        help_text += "│\n"
        help_text += "│ 📝 *Maxsus buyurtma:*\n"
        help_text += "│   Format: `Mahsulot - miqdor birlik`\n"
        help_text += "│   Masalan: `Olma - 2 kg`\n"
        help_text += "│   \n"
        help_text += "│   *Qabul qilinadigan birliklar:*\n"
        help_text += "│   • kg, gramm, tonna\n"
        help_text += "│   • litr, ml\n"
        help_text += "│   • metr, sm\n"
        help_text += "│   • dona, juft, quti\n"
        help_text += "└─────────────────────────────────\n\n"
        
        # ========== FAQAT ADMINLAR UCHUN ==========
        if is_admin:
            help_text += "👑 *ADMIN BUYRUGLARI:*\n"
            help_text += "┌─────────────────────────────────\n"
            help_text += "│ 📋 `/orders` - Buyurtmalarni boshqarish\n"
            help_text += "│ 🔐 `/setrole [id] [rol]` - Rol o'zgartirish\n"
            help_text += "│ 👥 `/users` - Foydalanuvchilar ro'yxati\n"
            help_text += "│\n"
            help_text += "│ 💰 *Pul yechish so'rovlari:*\n"
            help_text += "│   🔹 `/withdraw_requests` - So'rovlar\n"
            help_text += "│   🔹 `/confirm_withdraw [id]` - Tasdiqlash\n"
            help_text += "│   🔹 `/decline_withdraw [id]` - Rad etish\n"
            help_text += "│   🔹 `/export_withdraws` - Eksport CSV\n"
            help_text += "│   🔹 `/manual_payout [id] [summa]` - To'lov\n"
            help_text += "│\n"
            help_text += "│ 🛠 *Texnik buyruqlar:*\n"
            help_text += "│   🔹 `/maintenance_on` - Texnik rejim yoqish\n"
            help_text += "│   🔹 `/maintenance_off` - Texnik rejim o'chirish\n"
            help_text += "│   🔹 `/set_webhook` - Webhook o'rnatish\n"
            help_text += "│   🔹 `/delete_webhook` - Webhook o'chirish\n"
            help_text += "│   🔹 `/webhook_info` - Webhook ma'lumoti\n"
            help_text += "│   🔹 `/log` - Log faylini olish\n"
            help_text += "└─────────────────────────────────\n\n"
        
        # ========== QO'SHIMCHA MA'LUMOTLAR ==========
        help_text += "ℹ️ *QO'SHIMCHA MA'LUMOT:*\n"
        help_text += "┌─────────────────────────────────\n"
        help_text += "│ ✅ Telefon raqam bir marta so'raladi\n"
        help_text += "│ 📍 Lokatsiya har bir buyurtmada so'raladi\n"
        help_text += "│ 💾 Barcha ma'lumotlar xavfsiz saqlanadi\n"
        help_text += "│ 📞 Muammo bo'lsa /info orqali bog'lan\n"
        help_text += "└─────────────────────────────────\n\n"
        
        # ========== BOT VERSIYASI ==========
        help_text += "┌─────────────────────────────────\n"
        help_text += "│ 🤖 *Bot versiyasi:* 2.0.0\n"
        help_text += "│ 📅 *Yangilangan:* 2026-02-24\n"
        help_text += "│ 👨‍💻 *Dasturchi:* @prodevuzoff\n"
        help_text += "└─────────────────────────────────\n"
        
        # Adminlar uchun qisqa eslatma
        if is_admin:
            help_text += "\n📢 *Admin eslatmasi:* Barcha admin buyruqlari faqat adminlar uchun!"
        
        await message.answer(help_text, parse_mode="Markdown")
        logger.info(f"Foydalanuvchi {message.from_user.id} help buyrug'ini ishlatdi")
        
    except Exception as e:
        logger.error(f"Help komandasida xato: {e}")
        await message.answer("❌ Yordam oynasini yuklashda xatolik yuz berdi.")