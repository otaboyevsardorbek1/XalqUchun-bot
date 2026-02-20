# import asyncio
# import logging
# from aiogram import Bot, Dispatcher
# from aiogram.client.default import DefaultBotProperties
# from aiogram.enums import ParseMode
# from aiogram.fsm.storage.memory import MemoryStorage
# from aiogram.types import BotCommand

# from bot.data import BOT_TOKEN, ADMIN_IDS, OWNER_ID, WEBHOOK_URL
# from bot.db.database import engine
# from bot.db.base import Base
# from bot.handlers import (
#     start, catalog, cart, checkout, admin, profile,
#     referral, role_management, webhook_management, maintenance, log_handlers
# )
# from bot.keyboards.main import main_menu
# from bot.middlewares.error_reporter import ErrorReporterMiddleware
# from bot.middlewares.maintenance import MaintenanceMiddleware
# from bot.middlewares.role_access import RoleAccessMiddleware
# from bot.utils.start_stop import notify_admins_startup, notify_admins_shutdown
# from bot.utils.log_utils import check_log_file

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Bot setup
# bot = Bot(
#     token=BOT_TOKEN,
#     default=DefaultBotProperties(parse_mode=ParseMode.HTML)
# )
# storage = MemoryStorage()
# dp = Dispatcher(storage=storage)

# # Register middlewares
# dp.message.middleware(ErrorReporterMiddleware(bot, ADMIN_IDS + [OWNER_ID]))
# dp.message.middleware(MaintenanceMiddleware())
# dp.message.middleware(RoleAccessMiddleware())
# dp.callback_query.middleware(ErrorReporterMiddleware(bot, ADMIN_IDS + [OWNER_ID]))
# dp.callback_query.middleware(MaintenanceMiddleware())
# dp.callback_query.middleware(RoleAccessMiddleware())

# # Include routers
# dp.include_router(start.router)
# dp.include_router(catalog.router)
# dp.include_router(cart.router)
# dp.include_router(checkout.router)
# dp.include_router(admin.router)
# dp.include_router(profile.router)
# dp.include_router(referral.router)
# dp.include_router(role_management.router)
# dp.include_router(webhook_management.router)
# dp.include_router(maintenance.router)
# dp.include_router(log_handlers.router)

# async def on_startup():
#     # Create DB tables
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#     # Set bot commands (global and per-role will be set dynamically)
#     await bot.set_my_commands([
#         BotCommand(command="start", description="Botni ishga tushirish"),
#         BotCommand(command="help", description="Yordam"),
#         BotCommand(command="profile", description="Profil"),
#     ])
#     await notify_admins_startup(bot, ADMIN_IDS + [OWNER_ID])
#     # Check log file size
#     asyncio.create_task(check_log_file(bot, OWNER_ID))
#     # Set webhook if configured
#     if WEBHOOK_URL:
#         await bot.set_webhook(WEBHOOK_URL)
#         logger.info(f"Webhook set to {WEBHOOK_URL}")

# async def on_shutdown():
#     await notify_admins_shutdown(bot, ADMIN_IDS + [OWNER_ID])
#     if WEBHOOK_URL:
#         await bot.delete_webhook()
#     await bot.session.close()
#     await engine.dispose()

# async def main():
#     dp.startup.register(on_startup)
#     dp.shutdown.register(on_shutdown)

#     if WEBHOOK_URL:
#         # Start webhook mode (requires FastAPI or similar, omitted for brevity)
#         # For simplicity, we use polling. If you need webhook, implement FastAPI app.
#         logger.warning("Webhook configured but using polling. To use webhook, run via FastAPI.")
#         await dp.start_polling(bot)
#     else:
#         await dp.start_polling(bot)

# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except (KeyboardInterrupt, SystemExit):
#         logger.info("Bot stopped.")
#====================================================================================================================================================

# main.py eng yuqori qismiga qo'shing
import sys
import os

# Keyin boshqa importlar...
import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

from bot.data import BOT_TOKEN, ADMIN_IDS, OWNER_ID
from bot.db.base import Base
from bot.handlers import (
    start, catalog, cart, checkout, admin, profile,
    referral, role_management, webhook_management, maintenance, log_handlers
)
from bot.middlewares.error_reporter import ErrorReporterMiddleware
from bot.middlewares.maintenance import MaintenanceMiddleware
from bot.middlewares.role_access import RoleAccessMiddleware
from bot.utils.start_stop import notify_admins_startup, notify_admins_shutdown
from bot.utils.log_utils import check_log_file

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MUHIM: Fly.io muhitini aniqlash
IS_FLY_IO = os.getenv('FLY_APP_NAME') is not None
logger.info(f"Fly.io muhiti: {IS_FLY_IO}")

# MUHIM: Database URL ni to'g'ri sozlash
if IS_FLY_IO:
    # Fly.io da volume'dan foydalanish
    DATA_DIR = '/data'
    # Papkani yaratish (agar mavjud bo'lmasa)
    os.makedirs(DATA_DIR, exist_ok=True)
    logger.info(f"Data papkasi: {DATA_DIR} - mavjudmi: {os.path.exists(DATA_DIR)}")
    
    # DATABASE_URL ni secretdan olish
    DATABASE_URL = os.getenv('DATABASE_URL', f"sqlite+aiosqlite:///{DATA_DIR}/database.sqlite3")
    
    # Agar DATABASE_URL sqlite:// bilan boshlansa, uni to'g'rilash
    if DATABASE_URL.startswith('sqlite://'):
        DATABASE_URL = DATABASE_URL.replace('sqlite://', 'sqlite+aiosqlite://', 1)
        logger.info("DATABASE_URL sqlite:// dan sqlite+aiosqlite:// ga o'zgartirildi")
else:
    # Mahalliy muhit
    DATABASE_URL = "sqlite+aiosqlite:///./database.sqlite3"

logger.info(f"Database URL: {DATABASE_URL}")

# Database engine yaratish
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # SQL loglarini ko'rish uchun
    future=True,
    pool_pre_ping=True,  # Ulanishni tekshirish
    connect_args={"check_same_thread": False} if 'sqlite' in DATABASE_URL else {}
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    # class_=AsyncSessionLocal
)

# Bot setup
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Register routers
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

# Register middlewares
dp.message.middleware(ErrorReporterMiddleware(bot, ADMIN_IDS + [OWNER_ID]))
dp.message.middleware(MaintenanceMiddleware())
dp.message.middleware(RoleAccessMiddleware())
dp.callback_query.middleware(ErrorReporterMiddleware(bot, ADMIN_IDS + [OWNER_ID]))
dp.callback_query.middleware(MaintenanceMiddleware())
dp.callback_query.middleware(RoleAccessMiddleware())

async def on_startup():
    """Bot ishga tushganda bajariladigan funksiyalar"""
    logger.info("=" * 50)
    logger.info("BOT ISHGA TUSHMQODA...")
    logger.info("=" * 50)
    
    try:
        # 1. Database jadvallarini yaratish
        logger.info("1. Database jadvallari yaratilmoqda...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            # Database mavjudligini tekshirish
            result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = result.fetchall()
            logger.info(f"   Jadvallar: {[t[0] for t in tables]}")
        logger.info("✅ Database jadvallari muvaffaqiyatli yaratildi")
        
        # 2. Bot komandalarini o'rnatish
        logger.info("2. Bot komandalari o'rnatilmoqda...")
        commands = [
            BotCommand(command="start", description="Botni ishga tushirish"),
            BotCommand(command="help", description="Yordam"),
            BotCommand(command="profile", description="Profil"),
        ]
        await bot.set_my_commands(commands)
        logger.info("✅ Bot komandalari muvaffaqiyatli o'rnatildi")
        
        # 3. Adminlarni xabardor qilish
        logger.info("3. Adminlar xabardor qilinmoqda...")
        await notify_admins_startup(bot, ADMIN_IDS + [OWNER_ID])
        logger.info("✅ Adminlar xabardor qilindi")
        
        # 4. Log faylini tekshirish
        logger.info("4. Log fayli tekshirilmoqda...")
        asyncio.create_task(check_log_file(bot, OWNER_ID))
        logger.info("✅ Log fayli tekshirildi")
        
        # 5. Bot haqida ma'lumot
        bot_info = await bot.get_me()
        logger.info(f"🤖 Bot: @{bot_info.username} (ID: {bot_info.id})")
        logger.info(f"👥 Adminlar: {ADMIN_IDS}")
        logger.info(f"👑 Owner: {OWNER_ID}")
        
        logger.info("=" * 50)
        logger.info("✅ BOT MUVAFFAQIYATLI ISHGA TUSHDI!")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"❌ Startup xatosi: {e}", exc_info=True)
        logger.error("=" * 50)
        logger.error("BOT ISHGA TUSHA OLMADI!")
        logger.error("=" * 50)
        raise

async def on_shutdown():
    """Bot to'xtaganda bajariladigan funksiyalar"""
    logger.info("=" * 50)
    logger.info("BOT TO'XTATILMOQDA...")
    logger.info("=" * 50)
    
    try:
        # 1. Adminlarni xabardor qilish
        logger.info("1. Adminlar xabardor qilinmoqda...")
        await notify_admins_shutdown(bot, ADMIN_IDS + [OWNER_ID])
        logger.info("✅ Adminlar xabardor qilindi")
        
        # 2. Bot sessionni yopish
        logger.info("2. Bot session yopilmoqda...")
        await bot.session.close()
        logger.info("✅ Bot session yopildi")
        
        # 3. Databse engine ni yopish
        logger.info("3. Database engine yopilmoqda...")
        await engine.dispose()
        logger.info("✅ Database engine yopildi")
        
        logger.info("=" * 50)
        logger.info("✅ BOT MUVAFFAQIYATLI TO'XTATILDI!")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"❌ Shutdown xatosi: {e}", exc_info=True)

async def main():
    """Asosiy funksiya"""
    try:
        # Startup va shutdown funksiyalarini ro'yxatdan o'tkazish
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        
        # Botni ishga tushirish
        logger.info("🔄 Bot polling boshlanmoqda...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Polling xatosi: {e}", exc_info=True)
        raise
    finally:
        # Har holda bot sessionni yopish
        await bot.session.close()
        await engine.dispose()

def check_environment():
    """Muhit o'zgaruvchilarini tekshirish"""
    logger.info("🌍 MUHIT O'ZGARUVCHILARI TEKSHIRILMOQDA...")
    
    required_vars = ['BOT_TOKEN']
    optional_vars = ['ADMIN_IDS', 'OWNER_ID', 'DATABASE_URL']
    
    for var in required_vars:
        if not os.getenv(var):
            logger.error(f"❌ {var} muhit o'zgaruvchisi topilmadi!")
            return False
        else:
            logger.info(f"✅ {var} mavjud")
    
    for var in optional_vars:
        if os.getenv(var):
            logger.info(f"✅ {var} mavjud")
        else:
            logger.info(f"ℹ️ {var} mavjud emas (default ishlatiladi)")
    
    # Fly.io maxsus tekshiruv
    if IS_FLY_IO:
        # Volume mavjudligini tekshirish
        data_dir = '/data'
        if os.path.exists(data_dir):
            logger.info(f"✅ Volume {data_dir} mavjud")
            # Yozish huquqini tekshirish
            test_file = f"{data_dir}/test_write_{os.getpid()}.txt"
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                logger.info(f"✅ Volume {data_dir} ga yozish mumkin")
            except Exception as e:
                logger.error(f"❌ Volume {data_dir} ga yozish mumkin emas: {e}")
                return False
        else:
            logger.error(f"❌ Volume {data_dir} mavjud emas!")
            return False
    
    logger.info("✅ MUHIT TEKSHIRUVI MUVAFFAQIYATLI")
    return True

if __name__ == "__main__":
    try:
        # Muhitni tekshirish
        if not check_environment():
            logger.error("❌ Muhit tekshiruvi muvaffaqiyatsiz!")
            sys.exit(1)
        
        # Asosiy funksiyani ishga tushirish
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("👋 Bot foydalanuvchi tomonidan to'xtatildi")
    except SystemExit:
        logger.info("👋 Bot tizim tomonidan to'xtatildi")
    except Exception as e:
        logger.error(f"💥 Kritik xato: {e}", exc_info=True)
        sys.exit(1)