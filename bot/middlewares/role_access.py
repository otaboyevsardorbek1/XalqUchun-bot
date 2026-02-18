from aiogram import BaseMiddleware, types
import logging

logger = logging.getLogger(__name__)

class RoleAccessMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        # This middleware can check if user has role to execute a command
        # For now, we pass through; actual checks are in handlers.
        return await handler(event, data)