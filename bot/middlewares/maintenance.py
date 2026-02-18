from aiogram import BaseMiddleware, types
from aiogram.types import Message
import logging

logger = logging.getLogger(__name__)

MAINTENANCE_MODE = False  # Global flag

class MaintenanceMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if not MAINTENANCE_MODE:
            return await handler(event, data)

        if isinstance(event, Message):
            user_id = event.from_user.id
            # Allow admins and owner to bypass
            from config import ADMIN_IDS, OWNER_ID
            if user_id in ADMIN_IDS or user_id == OWNER_ID:
                return await handler(event, data)
            await event.answer("🛠 Texnik ishlar olib borilmoqda. Keyinroq urinib ko'ring.")
            return None
        return None  # Block all other events during maintenance