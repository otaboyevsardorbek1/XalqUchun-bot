import time
import logging
from aiogram import Bot
from typing import List  # add import

logger = logging.getLogger(__name__)
from bot.data import ALL_OWNER_IDS  # add import
async def notify_admins_startup(bot: Bot):  # changed
    date_now = time.strftime("%Y-%m-%d")
    time_now = time.strftime("%H:%M:%S")
    for admin in ALL_OWNER_IDS:
        try:
            await bot.send_message(
                admin,
                f"✅ *Bot ishga tushdi!*\n📅 {date_now}\n⏰ {time_now}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin}: {e}")

async def notify_admins_shutdown(bot: Bot):  # changed
    date_now = time.strftime("%Y-%m-%d")
    time_now = time.strftime("%H:%M:%S")
    for admin in ALL_OWNER_IDS:
        try:
            await bot.send_message(
                admin,
                f"❌ *Bot to'xtadi!*\n📅 {date_now}\n⏰ {time_now}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin}: {e}")