import os
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from datetime import datetime
from bot.data import LOG_FILE, OWNER_ID

router = Router()

@router.message(Command("log"))
async def send_log(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    if not os.path.exists(LOG_FILE):
        await message.reply("❌ Log fayli topilmadi.")
        return
    file_size_mb = os.path.getsize(LOG_FILE) / (1024 * 1024)
    await message.reply_document(
        FSInputFile(LOG_FILE),
        caption=f"📂 Log fayl\nHajmi: {file_size_mb:.2f} MB\nOxirgi yangilanish: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )