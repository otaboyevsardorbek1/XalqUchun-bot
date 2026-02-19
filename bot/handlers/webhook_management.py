from aiogram import Router, types, F
from aiogram.filters import Command
from bot.data import WEBHOOK_URL, OWNER_ID, ADMIN_IDS

router = Router()

@router.message(Command("set_webhook"))
async def set_webhook(message: types.Message):
    if message.from_user.id not in ADMIN_IDS and message.from_user.id != OWNER_ID:
        return
    if not WEBHOOK_URL:
        await message.reply("WEBHOOK_HOST sozlanmagan. .env faylida koʻrsating.")
        return
    await message.bot.set_webhook(WEBHOOK_URL)
    await message.reply(f"✅ Webhook oʻrnatildi: {WEBHOOK_URL}")

@router.message(Command("delete_webhook"))
async def delete_webhook(message: types.Message):
    if message.from_user.id not in ADMIN_IDS and message.from_user.id != OWNER_ID:
        return
    await message.bot.delete_webhook()
    await message.reply("✅ Webhook oʻchirildi.")

@router.message(Command("webhook_info"))
async def webhook_info(message: types.Message):
    if message.from_user.id not in ADMIN_IDS and message.from_user.id != OWNER_ID:
        return
    info = await message.bot.get_webhook_info()
    text = (
        f"🌐 Webhook URL: {info.url or '❌'}\n"
        f"⏳ Kutilayotgan yangilanishlar: {info.pending_update_count}\n"
        f"📡 IP: {info.ip_address or '❌'}\n"
        f"🔒 Maxsus sertifikat: {info.has_custom_certificate}\n"
        f"⚡ Maksimal ulanishlar: {info.max_connections or 'default'}\n"
        f"📂 Ruxsat etilgan yangilanishlar: {info.allowed_updates or 'default'}"
    )
    await message.reply(text)