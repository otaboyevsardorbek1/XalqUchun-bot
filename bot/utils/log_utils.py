import os
import asyncio
from datetime import datetime
from aiogram import Bot
from aiogram.types import FSInputFile
import logging
from bot.data import LOG_FILE, MAX_LOG_SIZE_MB
from aiogram.types import User


logger = logging.getLogger(__name__)

async def check_log_file(bot: Bot, owner_id: int):
    while True:
        await asyncio.sleep(3600)  # check every hour
        if os.path.exists(LOG_FILE):
            size_mb = os.path.getsize(LOG_FILE) / (1024 * 1024)
            if size_mb >= MAX_LOG_SIZE_MB:
                try:
                    bot_info: User = await bot.get_me()
                    bot_username = bot_info.username
                    lode_file_time=datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    await bot.send_document(
                        owner_id,
                        FSInputFile(LOG_FILE),
                        caption=f"📂 Log fayl hajmi: {size_mb:.2f} MB\n🕒 Vaqt: {lode_file_time}\nBot foydalanuvchi nomi: @{bot_username}"
                    )
                    with open(LOG_FILE, "w", encoding="utf-8") as f:
                        f.write("")  # clear log
                except Exception as e:
                    logger.error(f"Failed to send log: {e}")