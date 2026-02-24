# bot/middlewares/maintenance.py
from aiogram import BaseMiddleware, types
from aiogram.types import Message
import logging
from bot.data import ADMIN_IDS, OWNER_ID

logger = logging.getLogger(__name__)

# Global flag - bu o'zgaruvchi admin_settings orqali o'zgartiriladi
MAINTENANCE_MODE = False

class MaintenanceMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if not MAINTENANCE_MODE:
            return await handler(event, data)

        if isinstance(event, Message):
            user_id = event.from_user.id
            # Admin va ownerga ruxsat
            if user_id in ADMIN_IDS or user_id == OWNER_ID:
                return await handler(event, data)
            
            await event.answer(
                "🛠 *Texnik ishlar olib borilmoqda*\n\n"
                "Bot vaqtincha ishlamaydi. Keyinroq urinib ko'ring.\n\n"
                "⏳ Taxminiy vaqt: 10-15 daqiqa",
                parse_mode="Markdown"
            )
            return None
        
        elif isinstance(event, types.CallbackQuery):
            user_id = event.from_user.id
            if user_id in ADMIN_IDS or user_id == OWNER_ID:
                return await handler(event, data)
            
            await event.answer(
                "🛠 Texnik ishlar olib borilmoqda",
                show_alert=True
            )
            return None
        
        return None