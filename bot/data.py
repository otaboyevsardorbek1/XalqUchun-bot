import os
import json
import logging
from dotenv import load_dotenv

# Fly.io muhitini aniqlash
IS_FLY_IO = os.getenv('FLY_APP_NAME') is not None

# Fly.io da .env fayli bo'lmasligi mumkin, lekin baribir yuklaymiz (mahalliy uchun)
load_dotenv()

# Logger sozlash
logger = logging.getLogger(__name__)

# ---------------------- BOT TOKEN ----------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    # Fly.io da bu secret orqali keladi
    if IS_FLY_IO:
        error_msg = "BOT_TOKEN topilmadi! Fly.io da 'fly secrets set BOT_TOKEN=...' qiling"
        logger.error(error_msg)
        raise ValueError(error_msg)
    else:
        # Mahalliy muhitda default token (faqat test uchun!)
        BOT_TOKEN = "8211159471:AAE9JILqkqkwdTtWuFgV-F6uJAcJNwfHlf8"
        logger.warning("⚠️ Mahalliy muhitda default BOT_TOKEN ishlatilmoqda!")

# ---------------------- OWNER ID ----------------------
try:
    # OWNER_ID ni int qilib olish
    owner_id_str = os.getenv("OWNER_ID", "6684122507")
    # Agar vergul bo'lsa, birinchi qiymatni olish
    if ',' in owner_id_str:
        owner_id_str = owner_id_str.split(',')[0].strip()
    OWNER_ID = int(owner_id_str)
except (ValueError, TypeError) as e:
    logger.error(f"OWNER_ID xato: {e}")
    OWNER_ID = 6684122507  # Default

# ---------------------- ADMIN IDS ----------------------
ADMIN_IDS = []
admin_ids_str = os.getenv("ADMIN_IDS", "")

if admin_ids_str:
    # JSON formatida bo'lishi mumkin: "[123,456]" yoki "123,456"
    try:
        if admin_ids_str.startswith('['):
            # JSON format
            ADMIN_IDS = json.loads(admin_ids_str)
        else:
            # Vergul bilan ajratilgan format
            ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]
    except Exception as e:
        logger.error(f"ADMIN_IDS parse qilishda xato: {e}")
        ADMIN_IDS = [6684122507, 6646928202]  # Default
else:
    # Default adminlar
    ADMIN_IDS = [6684122507, 6646928202]

# ---------------------- ALL OWNER IDS ----------------------
ALL_OWNER_IDS = list(set([OWNER_ID] + ADMIN_IDS))  # set() takrorlanuvchilarni olib tashlaydi

# 0 ni olib tashlash (agar mavjud bo'lsa)
if 0 in ALL_OWNER_IDS:
    ALL_OWNER_IDS.remove(0)
    logger.warning("⚠️ 0 OWNER_IDS dan olib tashlandi")

logger.info(f"OWNER_ID: {OWNER_ID}")
logger.info(f"ADMIN_IDS: {ADMIN_IDS}")
logger.info(f"ALL_OWNER_IDS: {ALL_OWNER_IDS}")

# ---------------------- LOG FILE ----------------------
LOG_FILE = "bot.log"
if IS_FLY_IO:
    # Fly.io da loglarni stdout ga yozish yaxshiroq
    LOG_FILE = None  # None bo'lsa, logging std out ga yoziladi
    logger.info("Fly.io: Loglar stdout ga yoziladi")
else:
    LOG_FILE = "bot.log"
    
MAX_LOG_SIZE_MB = int(os.getenv("MAX_LOG_SIZE_MB", "20"))

# ---------------------- WEBHOOK ----------------------
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else None

# Fly.io da webhook ishlatilmaydi (polling ishlatamiz)
if IS_FLY_IO:
    WEBHOOK_URL = None
    logger.info("Fly.io: Webhook o'chirildi, polling ishlatiladi")

# ---------------------- REFERRAL REWARDS ----------------------
LEVEL_REWARDS = {
    1: 100.0, 
    2: 50.0,
    3: 25.0, 
    4: 10.0, 
    5: 5.0
}
MAX_REWARD_LEVEL = max(LEVEL_REWARDS.keys())
MAX_TREE_DEPTH = int(os.getenv("MAX_TREE_DEPTH", "15"))

# ---------------------- DATABASE URL (MUHIM!) ----------------------
if IS_FLY_IO:
    # Fly.io da volume ga yozish
    DATA_DIR = '/data'
    DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR}/database.sqlite3"
    logger.info(f"Fly.io: Database {DATA_DIR}/database.sqlite3 da")
else:
    # Mahalliy muhit
    DATABASE_URL = "sqlite+aiosqlite:///./database.sqlite3"
    logger.info(f"Mahalliy: Database ./database.sqlite3 da")

# ---------------------- MA'LUMOTLARNI CHIQARISH ----------------------
logger.info("=" * 50)
logger.info("BOT KONFIGURATSIYASI:")
logger.info(f"  • Fly.io: {IS_FLY_IO}")
logger.info(f"  • BOT_TOKEN mavjud: {bool(BOT_TOKEN)}")
logger.info(f"  • OWNER_ID: {OWNER_ID}")
logger.info(f"  • ADMIN_IDS: {ADMIN_IDS}")
logger.info(f"  • ALL_OWNER_IDS: {ALL_OWNER_IDS}")
logger.info(f"  • MAX_TREE_DEPTH: {MAX_TREE_DEPTH}")
logger.info(f"  • DATABASE_URL: {DATABASE_URL}")
logger.info(f"  • WEBHOOK_URL: {WEBHOOK_URL}")
logger.info("=" * 50)