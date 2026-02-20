import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN") or "8211159471:AAE9JILqkqkwdTtWuFgV-F6uJAcJNwfHlf8"
OWNER_ID = int(os.getenv("OWNER_ID", "6684122507,6646928202"))
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else [6684122507, 6646928202]
# 0 ni chiqarib tashlash
ALL_OWNER_IDS = [OWNER_ID] + ADMIN_IDS
if 0 in ALL_OWNER_IDS:
    ALL_OWNER_IDS.remove(0)

LOG_FILE = "bot.log"
MAX_LOG_SIZE_MB = int(os.getenv("MAX_LOG_SIZE_MB", "20")) 
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "")  # e.g. https://example.com
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else None

# Referral rewards config
LEVEL_REWARDS = {1: 100.0, 
                 2: 50.0,
                 3: 25.0, 
                 4: 10.0, 
                 5: 5.0}
MAX_REWARD_LEVEL = max(LEVEL_REWARDS.keys())
MAX_TREE_DEPTH = int(os.getenv("MAX_TREE_DEPTH", "15"))