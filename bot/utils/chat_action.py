# bot/utils/chat_action.py
from aiogram import Bot
from aiogram.enums import ChatAction
import asyncio
import logging
from functools import wraps
from typing import Union, Optional
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)

class ChatActionSender:
    """Chat action yuborish uchun context manager"""
    
    def __init__(self, bot: Bot, chat_id: int, action: str, interval: float = 4.5):
        self.bot = bot
        self.chat_id = chat_id
        self.action = action
        self.interval = interval
        self._task: Optional[asyncio.Task] = None
        self._running = False
    
    async def __aenter__(self):
        self._running = True
        self._task = asyncio.create_task(self._send_action_loop())
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _send_action_loop(self):
        """Action ni interval bilan yuborish"""
        while self._running:
            try:
                await self.bot.send_chat_action(chat_id=self.chat_id, action=self.action)
                await asyncio.sleep(self.interval)
            except Exception as e:
                logger.error(f"Chat action yuborishda xato: {e}")
                break

class Actions:
    """Chat action turlari"""
    TYPING = ChatAction.TYPING
    UPLOAD_PHOTO = ChatAction.UPLOAD_PHOTO
    UPLOAD_VIDEO = ChatAction.UPLOAD_VIDEO
    UPLOAD_DOCUMENT = ChatAction.UPLOAD_DOCUMENT
    FIND_LOCATION = ChatAction.FIND_LOCATION
    RECORD_VIDEO = ChatAction.RECORD_VIDEO
    RECORD_VOICE = ChatAction.RECORD_VOICE
    CHOOSE_STICKER = ChatAction.CHOOSE_STICKER

async def send_action(
    bot: Bot, 
    chat_id: int, 
    action: str, 
    duration: float = 2.0
) -> None:
    """Bir marta action yuborish"""
    try:
        await bot.send_chat_action(chat_id=chat_id, action=action)
        if duration > 0:
            await asyncio.sleep(duration)
    except Exception as e:
        logger.error(f"Action yuborishda xato: {e}")

async def send_typing_action(bot: Bot, chat_id: int, duration: float = 2.0):
    await send_action(bot, chat_id, ChatAction.TYPING, duration)

async def send_upload_photo_action(bot: Bot, chat_id: int, duration: float = 2.0):
    await send_action(bot, chat_id, ChatAction.UPLOAD_PHOTO, duration)

async def send_find_location_action(bot: Bot, chat_id: int, duration: float = 2.0):
    await send_action(bot, chat_id, ChatAction.FIND_LOCATION, duration)

def with_typing_action(func):
    """Handlerlarni typing action bilan o'rash uchun decorator"""
    @wraps(func)
    async def wrapper(event: Union[Message, CallbackQuery], *args, **kwargs):
        bot = None
        chat_id = None
        
        # Bot va chat_id ni olish
        if hasattr(event, 'bot'):
            bot = event.bot
        
        if isinstance(event, Message):
            chat_id = event.chat.id
        elif isinstance(event, CallbackQuery) and event.message:
            chat_id = event.message.chat.id
        
        # Typing action yuborish
        if bot and chat_id:
            try:
                await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            except Exception as e:
                logger.error(f"Typing action yuborishda xato: {e}")
        
        return await func(event, *args, **kwargs)
    
    return wrapper