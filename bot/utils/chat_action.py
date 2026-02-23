# bot/utils/chat_actions.py
from aiogram import Bot
from aiogram.types import ChatActions
import asyncio
import logging

logger = logging.getLogger(__name__)

class ChatActionSender:
    """Chat action yuborish uchun context manager"""
    
    def __init__(self, bot: Bot, chat_id: int, action: str, interval: float = 4.5):
        self.bot = bot
        self.chat_id = chat_id
        self.action = action
        self.interval = interval
        self._task = None
        self._running = False
    
    async def __aenter__(self):
        self._running = True
        self._task = asyncio.create_task(self._send_action_loop())
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._running = False
        if self._task:
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

# Action turlari
class Actions:
    TYPING = "typing"  # Yozmoqda
    UPLOAD_PHOTO = "upload_photo"  # Rasm yuklamoqda
    UPLOAD_VIDEO = "upload_video"  # Video yuklamoqda
    UPLOAD_DOCUMENT = "upload_document"  # Hujjat yuklamoqda
    FIND_LOCATION = "find_location"  # Lokatsiya izlamoqda
    RECORD_VIDEO = "record_video"  # Video yozmoqda
    RECORD_VOICE = "record_voice"  # Ovoz yozmoqda
    CHOOSE_STICKER = "choose_sticker"  # Sticker tanlamoqda

# Yordamchi funksiyalar
async def send_typing_action(bot: Bot, chat_id: int, duration: float = 2.0):
    """Bir marta typing action yuborish"""
    try:
        await bot.send_chat_action(chat_id=chat_id, action=Actions.TYPING)
        await asyncio.sleep(duration)
    except Exception as e:
        logger.error(f"Typing action yuborishda xato: {e}")

async def send_upload_photo_action(bot: Bot, chat_id: int, duration: float = 2.0):
    """Bir marta upload photo action yuborish"""
    try:
        await bot.send_chat_action(chat_id=chat_id, action=Actions.UPLOAD_PHOTO)
        await asyncio.sleep(duration)
    except Exception as e:
        logger.error(f"Upload photo action yuborishda xato: {e}")

async def send_find_location_action(bot: Bot, chat_id: int, duration: float = 2.0):
    """Bir marta find location action yuborish"""
    try:
        await bot.send_chat_action(chat_id=chat_id, action=Actions.FIND_LOCATION)
        await asyncio.sleep(duration)
    except Exception as e:
        logger.error(f"Find location action yuborishda xato: {e}")

# Decorator yordamida action qo'shish
def with_typing_action(func):
    """Handlerlarni typing action bilan o'rash uchun decorator"""
    async def wrapper(*args, **kwargs):
        # Message yoki CallbackQuery dan chat_id ni olish
        event = args[0]
        if hasattr(event, 'message'):
            chat_id = event.message.chat.id
            bot = event.bot if hasattr(event, 'bot') else kwargs.get('bot')
        else:
            chat_id = event.chat.id
            bot = event.bot if hasattr(event, 'bot') else kwargs.get('bot')
        
        if bot and chat_id:
            async with ChatActionSender(bot, chat_id, Actions.TYPING):
                return await func(*args, **kwargs)
        else:
            return await func(*args, **kwargs)
    return wrapper