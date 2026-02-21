from aiogram import Router, types, F
from aiogram.filters import Command
from bot.keyboards.main import main_menu,admin_menu
from bot.utils.referral import add_user
from bot.data import ADMIN_IDS, ALL_OWNER_IDS
from bot.data import BOT_TOKEN

router = Router()

async def bot_token_id():
    bot_id_parse=BOT_TOKEN.split(':')[0]
    return int(bot_id_parse)

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    args = message.text.split()
    ref = None
    if len(args) > 1 and args[1].isdigit():
        ref = int(args[1])
        await add_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name, 
            ref)
    else:
        ref= await bot_token_id()  # Bot tokenidan ID ni olish
        await add_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name, 
            ref)
    if message.from_user.id in ADMIN_IDS or message.from_user.id in ALL_OWNER_IDS  :  # Agar foydalanuvchi admin bo'lsa
        await message.answer(
            "Assalomu alaykum, admin! Xush kelibsiz.\n",
            reply_markup=admin_menu)
    else:
        await message.answer(
            "Assalomu alaykum! Xush kelibsiz.\n"
            "Buyurtma berish uchun quyidagi tugmalardan foydalaning.\n"
            "Batafsil maʼlumot uchun /info ni bosing.",
            reply_markup=main_menu)

@router.message(F.text == "📞 Biz bilan bogʻlanish")
@router.message(Command("info"))
async def contact_us(message: types.Message):
    await message.answer(
        "Biz bilan bogʻlanish uchun:\n"
        "Admin: @bbm1311\n"
        "Admin telefon: +998958182728\n"
        "Dasturchi: @prodevuzoff\n"
        "Dasturchi telefon:+998918610470"
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    if message.from_user.id in ALL_OWNER_IDS:  # Agar foydalanuvchi admin bo'lsa
        await message.answer(
        "🆘 **Yordam**\n\n"
        "Buyruqlar: /start, /help, /profile, /orders (admin)\n"
        "Referal tizim: /tree, /treeimg, /downline, /me, /balance, /withdraw, /transactions\n"
        "Adminlar uchun: /setrole, /users, /withdraw_requests, /export_withdraws, /manual_payout, /maintenance_on, /maintenance_off, /set_webhook, /delete_webhook, /webhook_info, /log")
    else:
        await message.answer(
            "🆘 **Yordam**\n\n"
            "Buyruqlar: /start, /help, /profile, /orders (admin)\n"
            "Referal tizim: /tree, /treeimg, /downline, /me, /balance, /withdraw, /transactions\n"
        )