# # bot/middlewares/chat_action.py
# from aiogram import BaseMiddleware, types
# from aiogram.types import Message, CallbackQuery
# from aiogram.enums import ChatAction  # ChatAction ni import qilish
# from bot.utils.chat_action import ChatActionSender  # Fayl nomi chat_action (sizda chat_action.py)
# import logging

# logger = logging.getLogger(__name__)

# class ChatActionMiddleware(BaseMiddleware):
#     async def __call__(self, handler, event, data):
#         if isinstance(event, Message):
#             # Message handlerlar uchun typing action
#             async with ChatActionSender(data['bot'], event.chat.id, ChatAction.TYPING, interval=3.0):
#                 return await handler(event, data)
#         elif isinstance(event, CallbackQuery):
#             # Callback query handlerlar uchun typing action
#             async with ChatActionSender(data['bot'], event.message.chat.id, ChatAction.TYPING, interval=3.0):
#                 return await handler(event, data)
#         else:
#             return await handler(event, data)