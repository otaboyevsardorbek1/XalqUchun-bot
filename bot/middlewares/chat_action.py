# bot/middlewares/chat_action.py
from aiogram import BaseMiddleware, types
from aiogram.types import Message, CallbackQuery
from bot.utils.chat_action import ChatActionSender, Actions
import logging

logger = logging.getLogger(__name__)

class ChatActionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            # Message handlerlar uchun typing action
            async with ChatActionSender(data['bot'], event.chat.id, Actions.TYPING, interval=3.0):
                return await handler(event, data)
        elif isinstance(event, CallbackQuery):
            # Callback query handlerlar uchun typing action
            async with ChatActionSender(data['bot'], event.message.chat.id, Actions.TYPING, interval=3.0):
                return await handler(event, data)
        else:
            return await handler(event, data)