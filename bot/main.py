import asyncio
import logging
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import BOT_TOKEN, ADMIN_IDS, OWNER_ID, WEBHOOK_URL
from db.database import engine
from db.base import Base
from handlers import (
    start, catalog, cart, checkout, admin, profile,
    referral, role_management, webhook_management, maintenance, log_handlers
)
from keyboards.main import main_menu
from middlewares.error_reporter import ErrorReporterMiddleware
from middlewares.maintenance import MaintenanceMiddleware
from middlewares.role_access import RoleAccessMiddleware
from utils.start_stop import notify_admins_startup, notify_admins_shutdown
from utils.log_utils import check_log_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot setup
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Register middlewares
dp.message.middleware(ErrorReporterMiddleware(bot, ADMIN_IDS + [OWNER_ID]))
dp.message.middleware(MaintenanceMiddleware())
dp.message.middleware(RoleAccessMiddleware())
dp.callback_query.middleware(ErrorReporterMiddleware(bot, ADMIN_IDS + [OWNER_ID]))
dp.callback_query.middleware(MaintenanceMiddleware())
dp.callback_query.middleware(RoleAccessMiddleware())

# Include routers
dp.include_router(start.router)
dp.include_router(catalog.router)
dp.include_router(cart.router)
dp.include_router(checkout.router)
dp.include_router(admin.router)
dp.include_router(profile.router)
dp.include_router(referral.router)
dp.include_router(role_management.router)
dp.include_router(webhook_management.router)
dp.include_router(maintenance.router)
dp.include_router(log_handlers.router)

async def on_startup():
    # Create DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Set bot commands (global and per-role will be set dynamically)
    await bot.set_my_commands([
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="help", description="Yordam"),
        BotCommand(command="profile", description="Profil"),
    ])
    await notify_admins_startup(bot, ADMIN_IDS + [OWNER_ID])
    # Check log file size
    asyncio.create_task(check_log_file(bot, OWNER_ID))
    # Set webhook if configured
    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL)
        logger.info(f"Webhook set to {WEBHOOK_URL}")

async def on_shutdown():
    await notify_admins_shutdown(bot, ADMIN_IDS + [OWNER_ID])
    if WEBHOOK_URL:
        await bot.delete_webhook()
    await bot.session.close()
    await engine.dispose()

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    if WEBHOOK_URL:
        # Start webhook mode (requires FastAPI or similar, omitted for brevity)
        # For simplicity, we use polling. If you need webhook, implement FastAPI app.
        logger.warning("Webhook configured but using polling. To use webhook, run via FastAPI.")
        await dp.start_polling(bot)
    else:
        await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")