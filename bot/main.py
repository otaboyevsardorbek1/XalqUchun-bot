import asyncio
from datetime import datetime, timedelta
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from utils.cart import clear_cart, get_cart
from config import BOT_TOKEN
from db.database import engine
from db.base import Base
from handlers import start, catalog, cart, checkout, admin,profile
from config import ADMIN_IDS
from keyboards.main import main_menu
# from aiogram.types import Update
# from aiogram.types import ErrorEvent
from aiogram.types import BotCommand
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot yaratish (to'g'rilangan qism)
bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
dp = Dispatcher(storage=MemoryStorage())

async def Admin_info_message(text: str):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text,reply_markup=main_menu)
        except Exception as e:
            logger.error(f"Admin {admin_id} ga xabar yuborishda xato: {e}")

async def monitor_carts():
    while True:
        await asyncio.sleep(60)  # har 60 sekund
        from utils.cart import carts, get_cart_creation_time
        for user_id, cart in list(carts.items()):
            created_time = cart.get('_created_time')
            if created_time and now - created_time > timedelta(minutes=10):
                # adminga yuborish
                text = f"⏰ {user_id} foydalanuvchining savati 10 daqiqadan oshdi. Tarkibi:\n"
                for item_id, item in cart.items():
                    if item_id == '_created_time':
                        continue
                    if item['type'] == 'regular':
                        text += f"• {item['name']} x{item['qty']} - {item['qty']*item['price']} so'm\n"
                    else:
                        text += f"• {item['name']} x{item['qty']} {item['unit']} (maxsus)\n"
                for admin_id in ADMIN_IDS:
                    try:
                        await bot.send_message(admin_id, text)
                    except:
                        pass
                # savatni tozalaymiz
                clear_cart(user_id)
                
async def on_startup():
    # Ma'lumotlar bazasini yaratish
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Default komandalarni o'rnatish
    commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="help", description="Yordam"),
        BotCommand(command="profile", description="Profil ma'lumotlari"),
        BotCommand(command="orders", description="Buyurtmalar (admin)"),
    ]
    await bot.set_my_commands(commands)
    await Admin_info_message(f"✅ Bot ishga tushdi:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Bot ishga tushdi...")

async def stop_bot():
    print("Bot to'xtadi...")
    await Admin_info_message(f"✅ Bot to'xtadi:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    await bot.session.close()
    await engine.dispose()
    await dp.storage.close()
        

async def main():
    # Routerlarni ulash
    dp.include_router(start.router)
    dp.include_router(catalog.router)
    dp.include_router(cart.router)
    dp.include_router(checkout.router)
    dp.include_router(admin.router)
    dp.include_router(profile.router)

    # Bot ishga tushganda bazani yaratish
    dp.startup.register(on_startup)
    dp.shutdown.register(stop_bot)

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot to'xtatildi...")
    finally:
        asyncio.run(stop_bot())