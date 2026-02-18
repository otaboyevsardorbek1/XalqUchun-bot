from aiogram import Router, types, F
from aiogram.filters import Command
from config import OWNER_ID, ADMIN_IDS
from middlewares.maintenance import MAINTENANCE_MODE

router = Router()

@router.message(Command("maintenance_on"))
async def maintenance_on(message: types.Message):
    if message.from_user.id not in ADMIN_IDS and message.from_user.id != OWNER_ID:
        return
    global MAINTENANCE_MODE
    MAINTENANCE_MODE = True
    await message.reply("🛠 Texnik rejim YOQILDI.")

@router.message(Command("maintenance_off"))
async def maintenance_off(message: types.Message):
    if message.from_user.id not in ADMIN_IDS and message.from_user.id != OWNER_ID:
        return
    global MAINTENANCE_MODE
    MAINTENANCE_MODE = False
    await message.reply("✅ Texnik rejim OʻCHIRILDI.")