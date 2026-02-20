from aiogram import Router, types, F
from aiogram.filters import Command
from bot.data import OWNER_ID, ADMIN_IDS
from bot.middlewares.maintenance import MAINTENANCE_MODE
from bot.utils.auth import is_admin, is_owner
router = Router()
 

@router.message(Command("maintenance_on"))
async def maintenance_on(message: types.Message):
    if is_admin(message.from_user.id) or is_owner(message.from_user.id):
        global MAINTENANCE_MODE
        MAINTENANCE_MODE = True
        await message.reply("🛠 Texnik rejim YOQILDI.")
        return
    return

@router.message(Command("maintenance_off"))
async def maintenance_off(message: types.Message):
    if is_admin(message.from_user.id) or is_owner(message.from_user.id):
        global MAINTENANCE_MODE
        MAINTENANCE_MODE = False
        await message.reply("✅ Texnik rejim OʻCHIRILDI.")
        return
    return