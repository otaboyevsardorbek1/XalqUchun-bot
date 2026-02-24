# bot/data.py
import os
import json
import logging
from dotenv import load_dotenv
from typing import List, Dict

# Fly.io muhitini aniqlash
IS_FLY_IO = os.getenv('FLY_APP_NAME') is not None

# .env faylini yuklash
load_dotenv()

# Logger sozlash
logger = logging.getLogger(__name__)

# ---------------------- BOT TOKEN ----------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    if IS_FLY_IO:
        error_msg = "❌ BOT_TOKEN topilmadi! Fly.io da 'fly secrets set BOT_TOKEN=...' qiling"
        logger.error(error_msg)
        raise ValueError(error_msg)
    else:
        logger.warning("⚠️ Mahalliy muhitda BOT_TOKEN topilmadi!")
        BOT_TOKEN = input("Bot tokenni kiriting: ").strip()

# ---------------------- OWNER ID ----------------------
def parse_id(value: str, default: int) -> int:
    """ID ni parse qilish"""
    try:
        if '#' in value:
            value = value.split('#')[0].strip()
        if ',' in value:
            value = value.split(',')[0].strip()
        return int(value)
    except (ValueError, TypeError):
        return default

OWNER_ID = parse_id(os.getenv("OWNER_ID", "6646928202"), 6646928202)

# ---------------------- ADMIN IDS ----------------------
def parse_admin_ids(value: str, default: List[int]) -> List[int]:
    """Admin ID larni parse qilish"""
    if not value:
        return default
    
    try:
        if '#' in value:
            value = value.split('#')[0].strip()
        
        if value.startswith('['):
            return json.loads(value)
        else:
            return [int(x.strip()) for x in value.split(',') if x.strip()]
    except Exception as e:
        logger.error(f"ADMIN_IDS parse qilishda xato: {e}")
        return default

ADMIN_IDS = parse_admin_ids(os.getenv("ADMIN_IDS", "6684122507"), [6684122507])

# ---------------------- ALL OWNER IDS ----------------------
ALL_OWNER_IDS = list(set([OWNER_ID] + ADMIN_IDS))
if 0 in ALL_OWNER_IDS:
    ALL_OWNER_IDS.remove(0)

# ---------------------- LOG FILE ----------------------
LOG_FILE = None if IS_FLY_IO else "bot.log"
MAX_LOG_SIZE_MB = int(os.getenv("MAX_LOG_SIZE_MB", "20"))

# ---------------------- WEBHOOK ----------------------
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else None

if IS_FLY_IO:
    WEBHOOK_URL = None

# ---------------------- REFERRAL REWARDS ----------------------
LEVEL_REWARDS: Dict[int, float] = {
    1: 100.0, 2: 50.0, 3: 25.0, 4: 10.0, 5: 5.0
}
MAX_REWARD_LEVEL = max(LEVEL_REWARDS.keys())
MAX_TREE_DEPTH = int(os.getenv("MAX_TREE_DEPTH", "15"))

# ---------------------- DATABASE URL ----------------------
if IS_FLY_IO:
    DATA_DIR = '/data'
    os.makedirs(DATA_DIR, exist_ok=True)
    DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR}/database.sqlite3"
else:
    DATABASE_URL = "sqlite+aiosqlite:///./database.sqlite3"

# ---------------------- KONFIGURATSIYANI CHIQARISH ----------------------
logger.info("=" * 60)
logger.info("🤖 BOT KONFIGURATSIYASI")
logger.info("=" * 60)
logger.info(f"  • Fly.io: {IS_FLY_IO}")
logger.info(f"  • BOT_TOKEN: {'✅' if BOT_TOKEN else '❌'}")
logger.info(f"  • OWNER_ID: {OWNER_ID}")
logger.info(f"  • ADMIN_IDS: {ADMIN_IDS}")
logger.info(f"  • ALL_OWNER_IDS: {ALL_OWNER_IDS}")
logger.info(f"  • DATABASE_URL: {DATABASE_URL}")
logger.info("=" * 60)