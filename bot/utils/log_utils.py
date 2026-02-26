import os
import asyncio
from datetime import datetime
from aiogram import Bot
from aiogram.types import FSInputFile
import logging
from bot.data import LOG_FILE, MAX_LOG_SIZE_MB
from aiogram.types import User
logger = logging.getLogger(__name__)
import logging
import sys
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime

class CustomLogger:
    def __init__(self, name='bot', log_file='bot.log', log_level=logging.DEBUG):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        
        # Eski handlerlarni tozalash (agar mavjud bo'lsa)
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Log formatini yaratish
        log_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Fayl handler (aylanuvchi fayl - maksimal 5MB, 3 backup)
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(log_format)
        
        # Konsol handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(log_format)
        
        # Handlerlarni qo'shish
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def get_logger(self):
        return self.logger

# Global logger obyektini yaratish
def setup_logger(name='bot', log_file='bot.log'):
    """Logger sozlamalarini o'rnatish"""
    custom_logger = CustomLogger(name, log_file)
    return custom_logger.get_logger()

# Logger instansiyasini yaratish
logger = setup_logger()

# Loglarni faylga yozish uchun yordamchi funksiyalar
def log_info(message):
    logger.info(message)

def log_error(message):
    logger.error(message)

def log_warning(message):
    logger.warning(message)

def log_debug(message):
    logger.debug(message)

def log_critical(message):
    logger.critical(message)

# Terminal outputni faylga yozish uchun klass
class TerminalLogger:
    def __init__(self, log_file='bot.log'):
        self.log_file = log_file
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
    def write(self, message):
        """Terminal outputni faylga ham yozish"""
        if message.strip():  # Bo'sh qatorlarni tashlab ketmaslik
            with open(self.log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{timestamp} - TERMINAL: {message}")
        self.original_stdout.write(message)
    
    def flush(self):
        self.original_stdout.flush()

def enable_terminal_logging(log_file='bot.log'):
    """Terminal outputni log fayliga yozishni yoqish"""
    sys.stdout = TerminalLogger(log_file)
    sys.stderr = TerminalLogger(log_file)


async def check_log_file(bot: Bot, owner_id: int):
    while True:
        await asyncio.sleep(3600)  # check every hour
        if os.path.exists(LOG_FILE):
            size_mb = os.path.getsize(LOG_FILE) / (1024 * 1024)
            if size_mb >= MAX_LOG_SIZE_MB:
                try:
                    bot_info: User = await bot.get_me()
                    bot_username = bot_info.username
                    lode_file_time=datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    await bot.send_document(
                        owner_id,
                        FSInputFile(LOG_FILE),
                        caption=f"📂 Log fayl hajmi: {size_mb:.2f} MB\n🕒 Vaqt: {lode_file_time}\nBot foydalanuvchi nomi: @{bot_username}"
                    )
                    with open(LOG_FILE, "w", encoding="utf-8") as f:
                        f.write("")  # clear log
                except Exception as e:
                    logger.error(f"Failed to send log: {e}")