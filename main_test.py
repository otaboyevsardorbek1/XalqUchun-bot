import asyncio
import random
import string
import hashlib
import csv
import io
import pyotp
import qrcode
import os
import logging
import json
import base64
import requests
import zipfile
import shutil
import matplotlib
import psutil
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    CallbackQuery, Message, FSInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import aiosqlite
from dateutil import parser

# ==================== KONFIGURATSIYA ====================

class Config:
    """Tizim konfiguratsiyasi"""
    BOT_TOKEN = "7165919586:AAEKmWvpt3VKYUFgNrI5S01zTSfguTDFl7s"
    ADMIN_IDS = [6646928202]
    OWNER_ID = 6646928202
    DB_FILE = "perfect_system.db"
    SESSION_TIMEOUT = 1800  # 30 daqiqa
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_TIME = 15  # daqiqa
    TOTP_INTERVAL = 30  # sekund
    BACKUP_CODES_COUNT = 8
    PASSWORD_MIN_STRENGTH = 2  # 0-3 oralig'ida
    
    # Yangi konfiguratsiyalar
    BACKUP_DIR = "backups"
    LOG_DIR = "logs"
    MAX_BACKUP_DAYS = 30
    API_RATE_LIMIT = 100  # Soatiga maksimal API so'rov
    WEBHOOK_URL = ""  # O'zgartirish kerak
    CHANNEL_ID = -1002120532575  # Kanal ID (o'zgartirish kerak)
    
    # To'lov tizimi sozlamalari
    CLICK_SERVICE_ID = "12345"
    CLICK_MERCHANT_ID = "12345"
    CLICK_SECRET_KEY = "your-click-secret-key"
    
    # Premium tariflar
    PREMIUM_PRICES = {
        'basic': 5.99,
        'pro': 14.99,
        'enterprise': 49.99
    }

# ==================== TILLAR ====================

class Languages:
    """Ko'p tillilik uchun lug'at"""
    
    UZ = {
        'welcome': 'Xush kelibsiz!',
        'login': 'Login',
        'password': 'Parol',
        'register': "Ro'yxatdan o'tish",
        'profile': 'Profil',
        'settings': 'Sozlamalar',
        'help': 'Yordam',
        'stats': 'Statistika',
        'charts': 'Grafiklar',
        'referral': 'Referral dasturi',
        'premium': 'Premium a\'zolik',
        'language': 'Til',
        'logout': 'Chiqish',
        'back': 'Orqaga',
        'confirm': 'Tasdiqlash',
        'cancel': 'Bekor qilish',
        'success': 'Muvaffaqiyatli',
        'error': 'Xatolik',
        'warning': 'Ogohlantirish',
        'info': 'Ma\'lumot',
        '2fa': 'Ikki bosqichli autentifikatsiya',
        'code': 'Kod',
        'invalid_code': 'Noto\'g\'ri kod',
        'expired_code': 'Muddati o\'tgan kod',
        'backup_code': 'Zaxira kod',
        'email': 'Email',
        'phone': 'Telefon',
        'account_name': 'Account nomi',
        'created_at': "Ro'yxatdan o'tgan",
        'last_login': 'Oxirgi kirish',
        'login_attempts': 'Urinishlar soni',
        'blocked_until': 'Bloklangan vaqt',
        'premium_tier': 'Premium daraja',
        'premium_until': 'Premium muddati',
        'referral_code': 'Referral kod',
        'referral_count': 'Taklif qilinganlar',
        'referral_bonus': 'Bonuslar',
        'total_logins': 'Jami kirishlar',
        'successful_logins': 'Muvaffaqiyatli',
        'failed_logins': 'Muvaffaqiyatsiz',
        'active_sessions': 'Faol sessiyalar',
        'system_stats': 'Tizim statistikasi',
    }
    
    EN = {
        'welcome': 'Welcome!',
        'login': 'Login',
        'password': 'Password',
        'register': 'Register',
        'profile': 'Profile',
        'settings': 'Settings',
        'help': 'Help',
        'stats': 'Statistics',
        'charts': 'Charts',
        'referral': 'Referral program',
        'premium': 'Premium membership',
        'language': 'Language',
        'logout': 'Logout',
        'back': 'Back',
        'confirm': 'Confirm',
        'cancel': 'Cancel',
        'success': 'Success',
        'error': 'Error',
        'warning': 'Warning',
        'info': 'Info',
        '2fa': 'Two-Factor Authentication',
        'code': 'Code',
        'invalid_code': 'Invalid code',
        'expired_code': 'Expired code',
        'backup_code': 'Backup code',
        'email': 'Email',
        'phone': 'Phone',
        'account_name': 'Account name',
        'created_at': 'Registered at',
        'last_login': 'Last login',
        'login_attempts': 'Login attempts',
        'blocked_until': 'Blocked until',
        'premium_tier': 'Premium tier',
        'premium_until': 'Premium until',
        'referral_code': 'Referral code',
        'referral_count': 'Referrals',
        'referral_bonus': 'Bonuses',
        'total_logins': 'Total logins',
        'successful_logins': 'Successful',
        'failed_logins': 'Failed',
        'active_sessions': 'Active sessions',
        'system_stats': 'System statistics',
    }
    
    RU = {
        'welcome': 'Добро пожаловать!',
        'login': 'Логин',
        'password': 'Пароль',
        'register': 'Регистрация',
        'profile': 'Профиль',
        'settings': 'Настройки',
        'help': 'Помощь',
        'stats': 'Статистика',
        'charts': 'Графики',
        'referral': 'Реферальная программа',
        'premium': 'Премиум подписка',
        'language': 'Язык',
        'logout': 'Выход',
        'back': 'Назад',
        'confirm': 'Подтвердить',
        'cancel': 'Отмена',
        'success': 'Успешно',
        'error': 'Ошибка',
        'warning': 'Предупреждение',
        'info': 'Информация',
        '2fa': 'Двухфакторная аутентификация',
        'code': 'Код',
        'invalid_code': 'Неверный код',
        'expired_code': 'Просроченный код',
        'backup_code': 'Резервный код',
        'email': 'Email',
        'phone': 'Телефон',
        'account_name': 'Имя аккаунта',
        'created_at': 'Зарегистрирован',
        'last_login': 'Последний вход',
        'login_attempts': 'Попыток входа',
        'blocked_until': 'Заблокирован до',
        'premium_tier': 'Премиум уровень',
        'premium_until': 'Премиум до',
        'referral_code': 'Реферальный код',
        'referral_count': 'Приглашенные',
        'referral_bonus': 'Бонусы',
        'total_logins': 'Всего входов',
        'successful_logins': 'Успешных',
        'failed_logins': 'Неудачных',
        'active_sessions': 'Активных сессий',
        'system_stats': 'Статистика системы',
    }

# ==================== MA'LUMOTLAR MODELLARI ====================

@dataclass
class Session:
    """Sessiya modeli"""
    user_id: int
    login: str
    login_time: datetime
    last_activity: datetime
    active: bool
    language: str
    session_id: str
    ip: Optional[str] = None
    premium_tier: str = 'free'

@dataclass
class User:
    """Foydalanuvchi modeli"""
    id: int
    login: str
    password_hash: str
    account_name: str
    email: Optional[str]
    phone: Optional[str]
    two_factor_enabled: bool
    two_factor_secret: Optional[str]
    language: str
    premium_tier: str
    premium_until: Optional[datetime]
    referral_code: Optional[str]
    referrer_id: Optional[int]
    created_at: datetime
    last_login: Optional[datetime]
    login_attempts: int
    locked_until: Optional[datetime]
    reset_code: Optional[str]
    reset_code_expires: Optional[datetime]

# ==================== PREMIUM DARAJALARI ====================

class PremiumTier(Enum):
    """Premium darajalari"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"

PREMIUM_FEATURES = {
    PremiumTier.FREE.value: {
        'max_accounts': 1,
        'backup_codes': 8,
        'session_timeout': 1800,
        'max_login_attempts': 5,
        'charts_enabled': False,
        'export_enabled': True,
        'api_access': False,
        'priority_support': False,
        'price': 0
    },
    PremiumTier.BASIC.value: {
        'max_accounts': 3,
        'backup_codes': 16,
        'session_timeout': 7200,
        'max_login_attempts': 10,
        'charts_enabled': True,
        'export_enabled': True,
        'api_access': False,
        'priority_support': False,
        'price': 5.99
    },
    PremiumTier.PRO.value: {
        'max_accounts': 10,
        'backup_codes': 32,
        'session_timeout': 86400,
        'max_login_attempts': 20,
        'charts_enabled': True,
        'export_enabled': True,
        'api_access': True,
        'priority_support': True,
        'price': 14.99
    },
    PremiumTier.ENTERPRISE.value: {
        'max_accounts': 100,
        'backup_codes': 128,
        'session_timeout': 259200,
        'max_login_attempts': 50,
        'charts_enabled': True,
        'export_enabled': True,
        'api_access': True,
        'priority_support': True,
        'price': 49.99
    }
}

# ==================== XAVFSIZLIK XIZMATLARI ====================

class SecurityService:
    """Xavfsizlik xizmati"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Parolni hash qilish"""
        salt = "perfect_system_v3_salt_2024"
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    @staticmethod
    def check_password_strength(password: str) -> Tuple[int, list]:
        """Parol kuchini tekshirish"""
        strength = 0
        messages = []
        
        if len(password) == 8:
            strength += 1
        else:
            messages.append("❌ 8 xonali bo'lishi kerak")
            return strength, messages
        
        if not password.isdigit():
            strength += 1
            messages.append("✅ Raqam va harf kombinatsiyasi")
        else:
            messages.append("⚠️ Faqat raqamlar - oddiy parol")
        
        if len(set(password)) >= 4:
            strength += 1
            messages.append("✅ Takrorlanmas raqamlar")
        else:
            messages.append("⚠️ Takrorlanuvchi raqamlar ko'p")
        
        dangerous = ['1234', '2345', '3456', '4567', '5678', '6789', 
                    '0123', '0000', '1111', '2222', '3333', '4444', 
                    '5555', '6666', '7777', '8888', '9999']
        
        for seq in dangerous:
            if seq in password:
                messages.append("⚠️ Xavfli kombinatsiya")
                strength = max(0, strength - 1)
                break
        
        return strength, messages
    
    @staticmethod
    def generate_api_key() -> str:
        """API kalit yaratish"""
        return base64.b64encode(os.urandom(32)).decode('utf-8')
    
    @staticmethod
    def encrypt_data(data: str) -> str:
        """Ma'lumotlarni shifrlash"""
        # Haqiqiy loyihada AES yoki boshqa shifrlash algoritmi ishlatiladi
        return base64.b64encode(data.encode()).decode()
    
    @staticmethod
    def decrypt_data(encrypted: str) -> str:
        """Ma'lumotlarni deshifrlash"""
        return base64.b64decode(encrypted).decode()

class TOTPManager:
    """TOTP (Time-based One-Time Password) menejeri"""
    
    def __init__(self):
        self.issuer_name = "PerfectSystem"
        self.interval = Config.TOTP_INTERVAL
    
    def generate_secret(self) -> str:
        """Yangi TOTP secret yaratish"""
        return pyotp.random_base32()
    
    def get_totp_uri(self, secret: str, account_name: str) -> str:
        """TOTP URI yaratish"""
        totp = pyotp.TOTP(secret, interval=self.interval)
        return totp.provisioning_uri(
            name=account_name,
            issuer_name=self.issuer_name
        )
    
    def generate_qr_code(self, secret: str, account_name: str) -> io.BytesIO:
        """QR kod yaratish"""
        uri = self.get_totp_uri(secret, account_name)
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        return bio
    
    def verify_code(self, secret: str, code: str) -> bool:
        """TOTP kodni tekshirish"""
        try:
            totp = pyotp.TOTP(secret, interval=self.interval)
            return totp.verify(code, valid_window=1)
        except Exception:
            return False
    
    def get_current_code(self, secret: str) -> str:
        """Joriy TOTP kodni olish"""
        totp = pyotp.TOTP(secret, interval=self.interval)
        return totp.now()
    
    def get_remaining_seconds(self, secret: str) -> int:
        """Joriy kodning amal qilish muddati"""
        return self.interval - (int(datetime.now().timestamp()) % self.interval)

class BackupCodeService:
    """Backup kodlar xizmati"""
    
    @staticmethod
    def generate_codes(count: int = Config.BACKUP_CODES_COUNT) -> list:
        """Backup kodlar yaratish"""
        codes = []
        for _ in range(count):
            letters = ''.join(random.choices(string.ascii_uppercase, k=4))
            digits = ''.join(random.choices(string.digits, k=4))
            code = f"{letters}{digits}"
            codes.append(code)
        return codes
    
    @staticmethod
    async def save_codes(db: aiosqlite.Connection, user_id: int, codes: list):
        """Backup kodlarni saqlash"""
        await db.execute("DELETE FROM backup_codes WHERE user_id = ?", (user_id,))
        
        for code in codes:
            await db.execute(
                "INSERT INTO backup_codes (user_id, code) VALUES (?, ?)",
                (user_id, code)
            )
        await db.commit()
    
    @staticmethod
    async def verify_code(db: aiosqlite.Connection, user_id: int, code: str) -> bool:
        """Backup kodni tekshirish"""
        cursor = await db.execute(
            "SELECT id FROM backup_codes WHERE user_id = ? AND code = ? AND used = 0",
            (user_id, code)
        )
        return await cursor.fetchone() is not None
    
    @staticmethod
    async def use_code(db: aiosqlite.Connection, user_id: int, code: str):
        """Backup kodni ishlatish"""
        await db.execute(
            "UPDATE backup_codes SET used = 1, used_at = CURRENT_TIMESTAMP WHERE user_id = ? AND code = ?",
            (user_id, code)
        )
        await db.commit()

# ==================== AUDIT XIZMATI ====================

class AuditService:
    """Audit log xizmati"""
    
    @staticmethod
    async def log(db: aiosqlite.Connection, user_id: int, action: str, 
                  details: str = "", ip: str = "Noma'lum"):
        """Audit log yozish"""
        await db.execute(
            "INSERT INTO audit_log (user_id, action, details, ip) VALUES (?, ?, ?, ?)",
            (user_id, action, details, ip)
        )
        await db.commit()

# ==================== REFERRAL TIZIMI ====================

class ReferralService:
    """Referral xizmati"""
    
    @staticmethod
    def generate_referral_code(user_id: int) -> str:
        """Referral kod yaratish"""
        import base64
        code_str = f"{user_id}-{random.randint(1000, 9999)}-{int(datetime.now().timestamp())}"
        code = base64.b64encode(code_str.encode()).decode()[:10]
        return code.upper()
    
    @staticmethod
    async def process_referral(db: aiosqlite.Connection, referrer_code: str, new_user_id: int):
        """Referralni qayta ishlash"""
        # Referrer ni topish
        cursor = await db.execute(
            "SELECT id FROM users WHERE referral_code = ?",
            (referrer_code,)
        )
        referrer = await cursor.fetchone()
        
        if referrer:
            referrer_id = referrer[0]
            
            # Referralni saqlash
            await db.execute(
                "INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)",
                (referrer_id, new_user_id)
            )
            await db.commit()
            
            return referrer_id
        return None
    
    @staticmethod
    async def get_referral_stats(db: aiosqlite.Connection, user_id: int) -> dict:
        """Referral statistikasini olish"""
        cursor = await db.execute(
            "SELECT COUNT(*) FROM referrals WHERE referrer_id = ?",
            (user_id,)
        )
        total = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            "SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND bonus_given = 1",
            (user_id,)
        )
        bonuses = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            "SELECT u.login, u.created_at FROM referrals r JOIN users u ON r.referred_id = u.id WHERE r.referrer_id = ? ORDER BY r.created_at DESC LIMIT 10",
            (user_id,)
        )
        recent = await cursor.fetchall()
        
        return {
            'total': total,
            'bonuses': bonuses,
            'recent': recent
        }

# ==================== TO'LOV TIZIMI ====================

class PaymentService:
    """To'lov xizmati"""
    
    def __init__(self):
        self.click_service_id = Config.CLICK_SERVICE_ID
        self.click_merchant_id = Config.CLICK_MERCHANT_ID
        self.click_secret_key = Config.CLICK_SECRET_KEY
    
    async def create_click_payment(self, user_id: int, amount: float, tier: str) -> str:
        """Click to'lov linki yaratish"""
        import hashlib
        
        transaction_id = f"{user_id}-{tier}-{int(datetime.now().timestamp())}"
        sign_string = f"{self.click_service_id}{transaction_id}{amount}{self.click_secret_key}"
        sign = hashlib.md5(sign_string.encode()).hexdigest()
        
        payment_url = (
            f"https://my.click.uz/services/pay"
            f"?service_id={self.click_service_id}"
            f"&merchant_id={self.click_merchant_id}"
            f"&amount={amount}"
            f"&transaction_id={transaction_id}"
            f"&sign={sign}"
        )
        
        return payment_url
    
    async def check_payment(self, transaction_id: str) -> bool:
        """To'lov holatini tekshirish"""
        # Click API orqali tekshirish
        # Bu yerda haqiqiy API chaqiruvi bo'lishi kerak
        return True

# ==================== MONITORING XIZMATI ====================

class MonitoringService:
    """Monitoring xizmati"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.webhook_url = Config.WEBHOOK_URL
        self.start_time = datetime.now()
        self.request_count = 0
        self.error_count = 0
    
    async def send_alert(self, message: str, level: str = "INFO"):
        """Alert yuborish"""
        try:
            payload = {
                'text': message,
                'level': level,
                'timestamp': datetime.now().isoformat(),
                'service': 'PerfectSecurityBot'
            }
            requests.post(self.webhook_url, json=payload, timeout=5)
        except Exception as e:
            print(f"Alert yuborishda xato: {e}")
    
    async def check_system_health(self):
        """Tizim sog'lig'ini tekshirish"""
        while True:
            await asyncio.sleep(3600)  # Har soatda
            
            checks = []
            
            # Ma'lumotlar bazasini tekshirish
            if not os.path.exists(Config.DB_FILE):
                checks.append("❌ Ma'lumotlar bazasi topilmadi!")
                await self.send_alert("Ma'lumotlar bazasi topilmadi!", "ERROR")
            else:
                size = os.path.getsize(Config.DB_FILE) / (1024 * 1024)
                if size > 100:
                    checks.append(f"⚠️ DB hajmi: {size:.2f} MB")
                    await self.send_alert(f"DB hajmi katta: {size:.2f} MB", "WARNING")
            
            # Disk hajmini tekshirish
            disk_usage = shutil.disk_usage('/')
            free_gb = disk_usage.free / (1024**3)
            if free_gb < 1:
                checks.append(f"⚠️ Diskda {free_gb:.2f} GB bo'sh joy")
                await self.send_alert(f"Diskda joy kam: {free_gb:.2f} GB", "WARNING")
            
            # Xotira tekshiruvi
            
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                checks.append(f"⚠️ Xotira: {memory.percent}% ishlatilgan")
                await self.send_alert(f"Xotira yuqori: {memory.percent}%", "WARNING")
            
            # Uptime
            uptime = datetime.now() - self.start_time
            checks.append(f"✅ Uptime: {uptime.days} kun {uptime.seconds//3600} soat")
            checks.append(f"📊 So'rovlar: {self.request_count}")
            checks.append(f"❌ Xatolar: {self.error_count}")
            
            # Log fayliga yozish
            log_file = f"{Config.LOG_DIR}/health_{datetime.now().strftime('%Y%m%d')}.log"
            os.makedirs(Config.LOG_DIR, exist_ok=True)
            with open(log_file, 'a') as f:
                f.write(f"{datetime.now().isoformat()}: {', '.join(checks)}\n")

# ==================== BACKUP XIZMATI ====================

class BackupService:
    """Backup xizmati"""
    
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.backup_dir = Config.BACKUP_DIR
        os.makedirs(self.backup_dir, exist_ok=True)
    
    async def create_backup(self) -> str:
        """Backup yaratish"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.backup_dir}/backup_{timestamp}.zip"
        
        with zipfile.ZipFile(backup_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Ma'lumotlar bazasini backup qilish
            zipf.write(self.db_file, "database.sqlite3")
            
            # Log fayllarini backup qilish
            if os.path.exists(Config.LOG_DIR):
                for log_file in Path(Config.LOG_DIR).glob("*.log"):
                    zipf.write(log_file, f"logs/{log_file.name}")
            
            # Konfiguratsiyani backup qilish
            config_data = {
                'timestamp': timestamp,
                'version': '3.0',
                'settings': {
                    'session_timeout': Config.SESSION_TIMEOUT,
                    'max_login_attempts': Config.MAX_LOGIN_ATTEMPTS,
                    'totp_interval': Config.TOTP_INTERVAL
                }
            }
            zipf.writestr("config.json", json.dumps(config_data, indent=2))
        
        # Eski backuplarni tozalash
        await self.cleanup_old_backups()
        
        return backup_name
    
    async def cleanup_old_backups(self, days: int = Config.MAX_BACKUP_DAYS):
        """Eski backuplarni tozalash"""
        now = datetime.now()
        for backup in Path(self.backup_dir).glob("*.zip"):
            created = datetime.fromtimestamp(backup.stat().st_ctime)
            if (now - created).days > days:
                backup.unlink()
                print(f"Eski backup o'chirildi: {backup.name}")
    
    async def restore_backup(self, backup_file: str) -> bool:
        """Backupdan tiklash"""
        try:
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                zipf.extractall(".")
            return True
        except Exception as e:
            print(f"Backup tiklashda xato: {e}")
            return False
    
    async def list_backups(self) -> list:
        """Backuplar ro'yxatini olish"""
        backups = []
        for backup in sorted(Path(self.backup_dir).glob("*.zip"), reverse=True):
            created = datetime.fromtimestamp(backup.stat().st_ctime)
            size = backup.stat().st_size / (1024 * 1024)  # MB
            backups.append({
                'name': backup.name,
                'created': created,
                'size': f"{size:.2f} MB"
            })
        return backups

# ==================== KANAL XIZMATI ====================

class ChannelService:
    """Telegram kanal xizmati"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.channel_id = Config.CHANNEL_ID
    
    async def post_new_user(self, user_id: int, username: str, referral: str = None):
        """Yangi foydalanuvchi haqida post"""
        text = (
            f"🆕 **Yangi foydalanuvchi!**\n\n"
            f"👤 ID: `{user_id}`\n"
            f"📝 Username: @{username}\n"
            f"🔄 Referral: {referral if referral else 'Yoq'}\n"
            f"⏰ Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        try:
            await self.bot.send_message(self.channel_id, text)
        except Exception as e:
            print(f"Kanalga yuborishda xato: {e}")
    
    async def post_login_alert(self, user_id: int, username: str, ip: str):
        """Login haqida alert"""
        text = (
            f"🔐 **Yangi login!**\n\n"
            f"👤 ID: `{user_id}`\n"
            f"📝 Username: @{username}\n"
            f"🌐 IP: `{ip}`\n"
            f"⏰ Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        try:
            await self.bot.send_message(self.channel_id, text)
        except Exception as e:
            print(f"Kanalga yuborishda xato: {e}")
    
    async def broadcast(self, text: str, buttons: list = None):
        """Barcha foydalanuvchilarga xabar yuborish"""
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute("SELECT id FROM users")
            users = await cursor.fetchall()
            
            success = 0
            failed = 0
            
            for user in users:
                try:
                    await self.bot.send_message(
                        user[0],
                        text,
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
                    )
                    success += 1
                    await asyncio.sleep(0.05)  # Rate limit
                except Exception as e:
                    failed += 1
                    print(f"Xabar yuborishda xato (user {user[0]}): {e}")
            
            # Natijani kanalga yuborish
            result_text = (
                f"📢 **Broadcast natijasi**\n\n"
                f"✅ Yuborildi: {success}\n"
                f"❌ Yuborilmadi: {failed}\n"
                f"📊 Jami: {len(users)}"
            )
            await self.bot.send_message(self.channel_id, result_text)

# ==================== RATE LIMITER ====================

class RateLimiter:
    """Rate limiting xizmati"""
    
    def __init__(self):
        self.attempts = {}
        self.api_calls = {}
    
    def check_limit(self, user_id: int, action: str, limit: int = 5, period: int = 3600) -> bool:
        """Limitni tekshirish"""
        key = f"{user_id}:{action}"
        now = datetime.now()
        
        if key not in self.attempts:
            self.attempts[key] = []
        
        # Eski urinishlarni tozalash
        self.attempts[key] = [t for t in self.attempts[key] if (now - t).seconds < period]
        
        if len(self.attempts[key]) >= limit:
            return False
        
        self.attempts[key].append(now)
        return True
    
    def check_api_limit(self, api_key: str) -> bool:
        """API limitini tekshirish"""
        now = datetime.now()
        
        if api_key not in self.api_calls:
            self.api_calls[api_key] = []
        
        self.api_calls[api_key] = [t for t in self.api_calls[api_key] if (now - t).seconds < 3600]
        
        if len(self.api_calls[api_key]) >= Config.API_RATE_LIMIT:
            return False
        
        self.api_calls[api_key].append(now)
        return True

# ==================== XAVFSIZLIK QO'SHIMCHALARI ====================

class SecurityEnhancements:
    """Qo'shimcha xavfsizlik"""
    
    @staticmethod
    def detect_suspicious_activity(login_attempts: list) -> bool:
        """Shubhali aktivlikni aniqlash"""
        ip_counts = {}
        for attempt in login_attempts:
            ip = attempt.get('ip', 'unknown')
            ip_counts[ip] = ip_counts.get(ip, 0) + 1
        
        for ip, count in ip_counts.items():
            if count > 10:
                return True
        
        return False
    
    @staticmethod
    def require_captcha():
        """Captcha talab qilish"""
        import random
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        result = num1 + num2
        
        return {
            'question': f"{num1} + {num2} = ?",
            'answer': str(result)
        }
    
    @staticmethod
    def validate_ip(ip: str) -> bool:
        """IP manzilni tekshirish"""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except:
            return False
    
    @staticmethod
    def get_client_ip(message: Message) -> str:
        """Client IP manzilini olish"""
        # Telegram client IP ni bermaydi, placeholder
        return "0.0.0.0"

# ==================== MA'LUMOTLAR VIZUALIZATSIYASI ====================

class DataVisualization:
    """Ma'lumotlarni vizual ko'rinishda ko'rsatish"""
    
    @staticmethod
    def create_activity_chart(dates: list, counts: list, title: str) -> io.BytesIO:
        """Aktivlik grafigini yaratish"""
        plt.figure(figsize=(10, 6))
        plt.plot(dates, counts, marker='o', linewidth=2, markersize=8, color='#3498DB')
        plt.fill_between(dates, counts, alpha=0.3, color='#3498DB')
        plt.title(title, fontsize=16, fontweight='bold')
        plt.xlabel('Sana', fontsize=12)
        plt.ylabel('Aktivlik', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        
        return buf
    
    @staticmethod
    def create_heatmap(login_times: list) -> io.BytesIO:
        """Heatmap yaratish"""
        hours = list(range(24))
        days = ['Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh', 'Ya']
        
        # 7x24 matritsa yaratish
        matrix = np.zeros((7, 24))
        
        for login_time in login_times:
            dt = datetime.fromisoformat(login_time)
            day = dt.weekday()
            hour = dt.hour
            matrix[day][hour] += 1
        
        plt.figure(figsize=(14, 6))
        sns.heatmap(matrix, annot=True, fmt='g', cmap='YlOrRd',
                   xticklabels=hours, yticklabels=days)
        plt.title('Haftalik aktivlik heatmap', fontsize=16, fontweight='bold')
        plt.xlabel('Soat', fontsize=12)
        plt.ylabel('Kun', fontsize=12)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        
        return buf
    
    @staticmethod
    def create_pie_chart(labels: list, values: list, title: str) -> io.BytesIO:
        """Doiraviy diagramma yaratish"""
        plt.figure(figsize=(8, 8))
        colors = ['#2ECC71', '#E74C3C', '#F39C12', '#3498DB']
        plt.pie(values, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
        plt.title(title, fontsize=16, fontweight='bold')
        plt.axis('equal')
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        
        return buf

# ==================== MA'LUMOTLAR BAZASI ====================

class Database:
    """Ma'lumotlar bazasi boshqaruvi"""
    
    def __init__(self, db_file: str):
        self.db_file = db_file
    
    async def init(self):
        """Jadvallarni yaratish"""
        async with aiosqlite.connect(self.db_file) as db:
            # Foydalanuvchilar jadvali (yangilangan)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    login TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    account_name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    two_factor_enabled BOOLEAN DEFAULT 0,
                    two_factor_secret TEXT,
                    language TEXT DEFAULT 'uz',
                    premium_tier TEXT DEFAULT 'free',
                    premium_until TIMESTAMP,
                    referral_code TEXT UNIQUE,
                    referrer_id INTEGER,
                    api_key TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    login_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP,
                    reset_code TEXT,
                    reset_code_expires TIMESTAMP,
                    settings TEXT DEFAULT '{}'
                )
            ''')
            
            # Backup kodlar jadvali
            await db.execute('''
                CREATE TABLE IF NOT EXISTS backup_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    code TEXT NOT NULL,
                    used BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    used_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Login tarixi jadvali
            await db.execute('''
                CREATE TABLE IF NOT EXISTS login_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip TEXT,
                    successful BOOLEAN,
                    method TEXT DEFAULT 'password',
                    user_agent TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Audit log jadvali
            await db.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    ip TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Referrals jadvali
            await db.execute('''
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bonus_given BOOLEAN DEFAULT 0,
                    FOREIGN KEY (referrer_id) REFERENCES users (id),
                    FOREIGN KEY (referred_id) REFERENCES users (id)
                )
            ''')
            
            # Payments jadvali
            await db.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    tier TEXT NOT NULL,
                    transaction_id TEXT UNIQUE,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Sessions jadvali
            await db.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip TEXT,
                    user_agent TEXT,
                    active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # API logs jadvali
            await db.execute('''
                CREATE TABLE IF NOT EXISTS api_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    api_key TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_time REAL,
                    status_code INTEGER
                )
            ''')
            
            await db.commit()
    
    async def check_lockout(self, login: str) -> Tuple[bool, Optional[int]]:
        """Bloklanganligini tekshirish"""
        async with aiosqlite.connect(self.db_file) as db:
            cursor = await db.execute(
                "SELECT locked_until FROM users WHERE login = ?",
                (login,)
            )
            result = await cursor.fetchone()
            
            if result and result[0]:
                locked_until = parser.parse(result[0])
                if datetime.now() < locked_until:
                    remaining = (locked_until - datetime.now()).seconds // 60
                    return True, remaining
            
            return False, None
    
    async def get_user_stats(self, user_id: int) -> dict:
        """Foydalanuvchi statistikasini olish"""
        async with aiosqlite.connect(self.db_file) as db:
            # Umumiy statistika
            cursor = await db.execute(
                "SELECT COUNT(*) FROM login_history WHERE user_id = ?",
                (user_id,)
            )
            total_logins = (await cursor.fetchone())[0]
            
            cursor = await db.execute(
                "SELECT COUNT(*) FROM login_history WHERE user_id = ? AND successful = 1",
                (user_id,)
            )
            successful = (await cursor.fetchone())[0]
            
            cursor = await db.execute(
                "SELECT COUNT(*) FROM login_history WHERE user_id = ? AND successful = 0",
                (user_id,)
            )
            failed = (await cursor.fetchone())[0]
            
            # Oxirgi 7 kunlik aktivlik
            cursor = await db.execute('''
                SELECT date(login_time), COUNT(*) 
                FROM login_history 
                WHERE user_id = ? AND login_time > datetime('now', '-7 days')
                GROUP BY date(login_time)
            ''', (user_id,))
            weekly = await cursor.fetchall()
            
            return {
                'total_logins': total_logins,
                'successful': successful,
                'failed': failed,
                'weekly': weekly
            }
    
    async def get_system_stats(self) -> dict:
        """Tizim statistikasini olish"""
        async with aiosqlite.connect(self.db_file) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            total_users = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE premium_tier != 'free'")
            premium_users = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE two_factor_enabled = 1")
            two_factor_users = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT COUNT(*) FROM login_history WHERE login_time > datetime('now', '-1 day')")
            today_logins = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE locked_until IS NOT NULL")
            blocked_users = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT COUNT(*) FROM payments WHERE status = 'completed'")
            total_payments = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT SUM(amount) FROM payments WHERE status = 'completed'")
            total_revenue = (await cursor.fetchone())[0] or 0
            
            return {
                'total_users': total_users,
                'premium_users': premium_users,
                'two_factor_users': two_factor_users,
                'today_logins': today_logins,
                'blocked_users': blocked_users,
                'total_payments': total_payments,
                'total_revenue': total_revenue
            }

# ==================== FSM HOLATLARI ====================

class RegisterState(StatesGroup):
    """Ro'yxatdan o'tish holatlari"""
    waiting_for_login = State()
    waiting_for_password = State()
    waiting_for_account_name = State()
    waiting_for_email = State()
    waiting_for_phone = State()
    waiting_for_2fa = State()
    waiting_for_referral = State()

class LoginState(StatesGroup):
    """Kirish holatlari"""
    waiting_for_login = State()
    waiting_for_password = State()
    waiting_for_2fa = State()
    waiting_for_backup = State()
    waiting_for_captcha = State()

class ProfileState(StatesGroup):
    """Profil holatlari"""
    waiting_for_new_account = State()
    waiting_for_old_password = State()
    waiting_for_new_password = State()
    waiting_for_new_email = State()
    waiting_for_new_phone = State()
    waiting_for_settings = State()

class ResetPasswordState(StatesGroup):
    """Parol tiklash holatlari"""
    waiting_for_login = State()
    waiting_for_code = State()
    waiting_for_new_password = State()

class TwoFactorState(StatesGroup):
    """2FA holatlari"""
    waiting_for_verification = State()
    waiting_for_backup = State()

class PremiumState(StatesGroup):
    """Premium holatlari"""
    waiting_for_payment = State()
    waiting_for_confirmation = State()

class AdminState(StatesGroup):
    """Admin holatlari"""
    waiting_for_user_id = State()
    waiting_for_broadcast = State()
    waiting_for_backup_restore = State()

# ==================== ASOSIY BOT KLASSI ====================

class PerfectSecurityBot:
    """Asosiy bot klassi"""
    
    def __init__(self, token: str):
        self.bot = Bot(token=token)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.db = Database(Config.DB_FILE)
        self.security = SecurityService()
        self.totp = TOTPManager()
        self.backup = BackupCodeService()
        self.audit = AuditService()
        self.referral = ReferralService()
        self.payment = PaymentService()
        self.monitoring = MonitoringService(token)
        self.backup_service = BackupService(Config.DB_FILE)
        self.channel = ChannelService(self.bot)
        self.rate_limiter = RateLimiter()
        self.visualization = DataVisualization()
        
        # Sessiyalar xotirasi
        self.sessions: Dict[int, Session] = {}
        
        # Handlerlarni ro'yxatdan o'tkazish
        self.register_handlers()
        
        # Papkalarni yaratish
        os.makedirs(Config.LOG_DIR, exist_ok=True)
        os.makedirs(Config.BACKUP_DIR, exist_ok=True)
    
    def register_handlers(self):
        """Barcha handlerlarni ro'yxatdan o'tkazish"""
        
        # ========== ASOSIY BUYRUQLAR ==========
        
        @self.dp.message(Command("start"))
        async def cmd_start(message: Message):
            await self.handle_start(message)
        
        @self.dp.message(Command("help"))
        async def cmd_help(message: Message):
            await self.handle_help(message)
        
        @self.dp.message(Command("language"))
        async def cmd_language(message: Message):
            await self.handle_language(message)
        
        @self.dp.message(Command("stats"))
        async def cmd_stats(message: Message):
            await self.handle_stats_command(message)
        
        # ========== MENYU CALLBACKLARI ==========
        
        @self.dp.callback_query(F.data == "menu_register")
        async def menu_register(callback: CallbackQuery, state: FSMContext):
            await self.register_start(callback, state)
        
        @self.dp.callback_query(F.data == "menu_login")
        async def menu_login(callback: CallbackQuery, state: FSMContext):
            await self.login_start(callback, state)
        
        @self.dp.callback_query(F.data == "menu_profile")
        async def menu_profile(callback: CallbackQuery):
            await self.profile_menu(callback)
        
        @self.dp.callback_query(F.data == "menu_stats")
        async def menu_stats(callback: CallbackQuery):
            await self.show_statistics(callback)
        
        @self.dp.callback_query(F.data == "menu_charts")
        async def menu_charts(callback: CallbackQuery):
            await self.show_charts_menu(callback)
        
        @self.dp.callback_query(F.data == "menu_referral")
        async def menu_referral(callback: CallbackQuery):
            await self.show_referral_stats(callback)
        
        @self.dp.callback_query(F.data == "menu_premium")
        async def menu_premium(callback: CallbackQuery):
            await self.premium_menu(callback)
        
        @self.dp.callback_query(F.data == "menu_language")
        async def menu_language(callback: CallbackQuery):
            await self.show_language_menu(callback)
        
        @self.dp.callback_query(F.data == "menu_settings")
        async def menu_settings(callback: CallbackQuery):
            await self.settings_menu(callback)
        
        @self.dp.callback_query(F.data == "menu_reset")
        async def menu_reset(callback: CallbackQuery, state: FSMContext):
            await self.reset_password_start(callback, state)
        
        @self.dp.callback_query(F.data == "menu_logout")
        async def menu_logout(callback: CallbackQuery):
            await self.logout(callback)
        
        @self.dp.callback_query(F.data == "menu_admin")
        async def menu_admin(callback: CallbackQuery):
            await self.admin_panel(callback)
        
        @self.dp.callback_query(F.data == "back_to_main")
        async def back_to_main(callback: CallbackQuery):
            await self.show_main_menu(callback)
        
        # ========== TIL HANDLERLARI ==========
        
        @self.dp.callback_query(F.data.startswith("lang_"))
        async def process_language(callback: CallbackQuery):
            await self.process_language(callback)
        
        # ========== REGISTER HANDLERLARI ==========
        
        @self.dp.callback_query(RegisterState.waiting_for_login, F.data.startswith("letter_"))
        async def register_process_login(callback: CallbackQuery, state: FSMContext):
            await self.register_process_login(callback, state)
        
        @self.dp.callback_query(RegisterState.waiting_for_login, F.data == "submit_login")
        async def register_login_submit(callback: CallbackQuery, state: FSMContext):
            await self.register_login_submit(callback, state)
        
        @self.dp.callback_query(RegisterState.waiting_for_password, F.data.startswith("digit_"))
        async def register_process_password(callback: CallbackQuery, state: FSMContext):
            await self.register_process_password(callback, state)
        
        @self.dp.callback_query(RegisterState.waiting_for_password, F.data == "submit")
        async def register_password_submit(callback: CallbackQuery, state: FSMContext):
            await self.register_password_submit(callback, state)
        
        @self.dp.callback_query(RegisterState.waiting_for_password, F.data == "clear_all")
        async def register_clear_password(callback: CallbackQuery, state: FSMContext):
            await self.register_clear_password(callback, state)
        
        @self.dp.callback_query(RegisterState.waiting_for_account_name, F.data.startswith("letter_"))
        async def register_process_account(callback: CallbackQuery, state: FSMContext):
            await self.register_process_account(callback, state)
        
        @self.dp.callback_query(RegisterState.waiting_for_account_name, F.data == "submit_login")
        async def register_account_submit(callback: CallbackQuery, state: FSMContext):
            await self.register_account_submit(callback, state)
        
        @self.dp.message(RegisterState.waiting_for_email)
        async def register_process_email(message: Message, state: FSMContext):
            await self.register_process_email(message, state)
        
        @self.dp.message(RegisterState.waiting_for_phone)
        async def register_process_phone(message: Message, state: FSMContext):
            await self.register_process_phone(message, state)
        
        @self.dp.message(RegisterState.waiting_for_2fa)
        async def register_process_2fa(message: Message, state: FSMContext):
            await self.register_process_2fa(message, state)
        
        # ========== LOGIN HANDLERLARI ==========
        
        @self.dp.callback_query(LoginState.waiting_for_login, F.data.startswith("letter_"))
        async def login_process_login(callback: CallbackQuery, state: FSMContext):
            await self.login_process_login(callback, state)
        
        @self.dp.callback_query(LoginState.waiting_for_login, F.data == "submit_login")
        async def login_login_submit(callback: CallbackQuery, state: FSMContext):
            await self.login_login_submit(callback, state)
        
        @self.dp.callback_query(LoginState.waiting_for_password, F.data.startswith("digit_"))
        async def login_process_password(callback: CallbackQuery, state: FSMContext):
            await self.login_process_password(callback, state)
        
        @self.dp.callback_query(LoginState.waiting_for_password, F.data == "submit")
        async def login_password_submit(callback: CallbackQuery, state: FSMContext):
            await self.login_password_submit(callback, state)
        
        @self.dp.callback_query(LoginState.waiting_for_2fa, F.data.startswith("2fa_digit_"))
        async def login_2fa_digit(callback: CallbackQuery, state: FSMContext):
            await self.login_2fa_digit(callback, state)
        
        @self.dp.callback_query(LoginState.waiting_for_2fa, F.data == "2fa_submit")
        async def login_2fa_submit(callback: CallbackQuery, state: FSMContext):
            await self.login_2fa_submit(callback, state)
        
        @self.dp.callback_query(LoginState.waiting_for_2fa, F.data == "2fa_backspace")
        async def login_2fa_backspace(callback: CallbackQuery, state: FSMContext):
            await self.login_2fa_backspace(callback, state)
        
        @self.dp.callback_query(LoginState.waiting_for_2fa, F.data == "2fa_refresh")
        async def login_2fa_refresh(callback: CallbackQuery, state: FSMContext):
            await self.login_2fa_refresh(callback, state)
        
        @self.dp.callback_query(LoginState.waiting_for_2fa, F.data == "2fa_use_backup")
        async def login_use_backup(callback: CallbackQuery, state: FSMContext):
            await self.login_use_backup(callback, state)
        
        # ========== PROFIL HANDLERLARI ==========
        
        @self.dp.callback_query(F.data == "profile_change_account")
        async def profile_change_account(callback: CallbackQuery, state: FSMContext):
            await self.profile_change_account_start(callback, state)
        
        @self.dp.callback_query(ProfileState.waiting_for_new_account, F.data.startswith("letter_"))
        async def profile_change_account_process(callback: CallbackQuery, state: FSMContext):
            await self.profile_change_account_process(callback, state)
        
        @self.dp.callback_query(ProfileState.waiting_for_new_account, F.data == "submit_login")
        async def profile_change_account_complete(callback: CallbackQuery, state: FSMContext):
            await self.profile_change_account_complete(callback, state)
        
        @self.dp.callback_query(F.data == "profile_change_password")
        async def profile_change_password(callback: CallbackQuery, state: FSMContext):
            await self.profile_change_password_start(callback, state)
        
        @self.dp.callback_query(ProfileState.waiting_for_old_password, F.data.startswith("digit_"))
        async def profile_change_password_old(callback: CallbackQuery, state: FSMContext):
            await self.profile_change_password_old(callback, state)
        
        @self.dp.callback_query(ProfileState.waiting_for_old_password, F.data == "submit")
        async def profile_change_password_old_submit(callback: CallbackQuery, state: FSMContext):
            await self.profile_change_password_old_submit(callback, state)
        
        @self.dp.callback_query(ProfileState.waiting_for_new_password, F.data.startswith("digit_"))
        async def profile_change_password_new(callback: CallbackQuery, state: FSMContext):
            await self.profile_change_password_new(callback, state)
        
        @self.dp.callback_query(ProfileState.waiting_for_new_password, F.data == "submit")
        async def profile_change_password_complete(callback: CallbackQuery, state: FSMContext):
            await self.profile_change_password_complete(callback, state)
        
        @self.dp.callback_query(F.data == "profile_2fa")
        async def profile_2fa_menu(callback: CallbackQuery):
            await self.profile_2fa_menu(callback)
        
        @self.dp.callback_query(F.data == "profile_stats")
        async def profile_stats(callback: CallbackQuery):
            await self.show_profile_stats(callback)
        
        @self.dp.callback_query(F.data == "export_data")
        async def export_data(callback: CallbackQuery):
            await self.export_user_data(callback)
        
        # ========== 2FA HANDLERLARI ==========
        
        @self.dp.callback_query(F.data == "2fa_enable")
        async def enable_2fa(callback: CallbackQuery, state: FSMContext):
            await self.enable_2fa_start(callback, state)
        
        @self.dp.callback_query(F.data == "2fa_disable")
        async def disable_2fa(callback: CallbackQuery):
            await self.disable_2fa(callback)
        
        @self.dp.callback_query(F.data == "2fa_show_qr")
        async def show_qr(callback: CallbackQuery):
            await self.show_2fa_qr(callback)
        
        @self.dp.callback_query(F.data == "2fa_regenerate_backup")
        async def regenerate_backup(callback: CallbackQuery):
            await self.regenerate_backup_codes(callback)
        
        # ========== PREMIUM HANDLERLARI ==========
        
        @self.dp.callback_query(F.data.startswith("buy_"))
        async def process_purchase(callback: CallbackQuery, state: FSMContext):
            await self.process_purchase(callback, state)
        
        @self.dp.callback_query(F.data.startswith("check_payment_"))
        async def check_payment(callback: CallbackQuery, state: FSMContext):
            await self.check_payment(callback, state)
        
        # ========== RESET PASSWORD HANDLERLARI ==========
        
        @self.dp.callback_query(ResetPasswordState.waiting_for_login, F.data.startswith("letter_"))
        async def reset_process_login(callback: CallbackQuery, state: FSMContext):
            await self.reset_process_login(callback, state)
        
        @self.dp.callback_query(ResetPasswordState.waiting_for_login, F.data == "submit_login")
        async def reset_login_submit(callback: CallbackQuery, state: FSMContext):
            await self.reset_login_submit(callback, state)
        
        @self.dp.message(ResetPasswordState.waiting_for_code)
        async def reset_process_code(message: Message, state: FSMContext):
            await self.reset_process_code(message, state)
        
        @self.dp.callback_query(ResetPasswordState.waiting_for_new_password, F.data.startswith("digit_"))
        async def reset_process_new_password(callback: CallbackQuery, state: FSMContext):
            await self.reset_process_new_password(callback, state)
        
        @self.dp.callback_query(ResetPasswordState.waiting_for_new_password, F.data == "submit")
        async def reset_complete(callback: CallbackQuery, state: FSMContext):
            await self.reset_complete(callback, state)
        
        # ========== ADMIN HANDLERLARI ==========
        
        @self.dp.callback_query(F.data == "admin_users")
        async def admin_users(callback: CallbackQuery):
            await self.admin_show_users(callback)
        
        @self.dp.callback_query(F.data == "admin_stats")
        async def admin_stats(callback: CallbackQuery):
            await self.admin_show_stats(callback)
        
        @self.dp.callback_query(F.data == "admin_blocked")
        async def admin_blocked(callback: CallbackQuery):
            await self.admin_show_blocked(callback)
        
        @self.dp.callback_query(F.data == "admin_logs")
        async def admin_logs(callback: CallbackQuery):
            await self.admin_show_logs(callback)
        
        @self.dp.callback_query(F.data == "admin_backup")
        async def admin_backup(callback: CallbackQuery):
            await self.admin_backup_menu(callback)
        
        @self.dp.callback_query(F.data == "admin_create_backup")
        async def admin_create_backup(callback: CallbackQuery):
            await self.admin_create_backup(callback)
        
        @self.dp.callback_query(F.data == "admin_list_backups")
        async def admin_list_backups(callback: CallbackQuery):
            await self.admin_list_backups(callback)
        
        @self.dp.callback_query(F.data == "admin_broadcast")
        async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
            await self.admin_broadcast_start(callback, state)
        
        @self.dp.message(AdminState.waiting_for_broadcast)
        async def admin_broadcast_process(message: Message, state: FSMContext):
            await self.admin_broadcast_process(message, state)
        
        # ========== GRAFIK HANDLERLARI ==========
        
        @self.dp.callback_query(F.data == "chart_weekly")
        async def chart_weekly(callback: CallbackQuery):
            await self.show_weekly_chart(callback)
        
        @self.dp.callback_query(F.data == "chart_heatmap")
        async def chart_heatmap(callback: CallbackQuery):
            await self.show_heatmap(callback)
        
        @self.dp.callback_query(F.data == "chart_pie")
        async def chart_pie(callback: CallbackQuery):
            await self.show_pie_chart(callback)
        
        # ========== UMUMIY HANDLERLAR ==========
        
        @self.dp.callback_query(F.data == "cancel")
        async def handle_cancel(callback: CallbackQuery, state: FSMContext):
            await self.cancel_operation(callback, state)
        
        @self.dp.callback_query(F.data == "backspace")
        async def handle_backspace(callback: CallbackQuery, state: FSMContext):
            await self.handle_backspace(callback, state)
    
    # ==================== TIL FUNKSIYALARI ====================
    
    def get_text(self, key: str, user_id: int = None) -> str:
        """Tilga mos matn olish"""
        lang = 'uz'
        if user_id and user_id in self.sessions:
            lang = self.sessions[user_id].language
        elif user_id:
            # Bazadan tilni olish kerak
            pass
        
        lang_dict = {
            'uz': Languages.UZ,
            'en': Languages.EN,
            'ru': Languages.RU
        }.get(lang, Languages.UZ)
        
        return lang_dict.get(key, key)
    
    # ==================== KLAVIATURALAR ====================
    
    def create_alphabet_keyboard(self) -> InlineKeyboardMarkup:
        """Ingliz alifbosi klaviaturasi"""
        buttons = []
        row = []
        
        for letter in string.ascii_uppercase:
            row.append(InlineKeyboardButton(text=letter, callback_data=f"letter_{letter}"))
            if len(row) == 5:
                buttons.append(row)
                row = []
        
        if row:
            buttons.append(row)
        
        buttons.append([
            InlineKeyboardButton(text="⌫", callback_data="backspace"),
            InlineKeyboardButton(text="✅", callback_data="submit_login"),
            InlineKeyboardButton(text="❌", callback_data="cancel")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def create_digit_keyboard(self) -> InlineKeyboardMarkup:
        """Raqamli klaviatura"""
        buttons = []
        row = []
        
        for i in range(1, 10):
            row.append(InlineKeyboardButton(text=str(i), callback_data=f"digit_{i}"))
            if len(row) == 3:
                buttons.append(row)
                row = []
        
        buttons.append([
            InlineKeyboardButton(text="0", callback_data="digit_0"),
            InlineKeyboardButton(text="⌫", callback_data="backspace_digit"),
            InlineKeyboardButton(text="✅", callback_data="submit")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def create_safe_keyboard(self, current_input: str = "") -> InlineKeyboardMarkup:
        """Raqamli seyf klaviaturasi"""
        buttons = []
        
        display = current_input if current_input else "⚫" * 8
        display_text = f"📱 {display}"
        buttons.append([InlineKeyboardButton(text=display_text, callback_data="noop")])
        
        row = []
        for i in range(1, 10):
            row.append(InlineKeyboardButton(text=str(i), callback_data=f"digit_{i}"))
            if len(row) == 3:
                buttons.append(row)
                row = []
        
        buttons.append([
            InlineKeyboardButton(text="0", callback_data="digit_0"),
            InlineKeyboardButton(text="⌫", callback_data="backspace_digit"),
            InlineKeyboardButton(text="🗑️", callback_data="clear_all"),
            InlineKeyboardButton(text="✅", callback_data="submit")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def create_2fa_keyboard(self) -> InlineKeyboardMarkup:
        """2FA kod kiritish klaviaturasi"""
        buttons = []
        
        row = []
        for i in range(1, 10):
            row.append(InlineKeyboardButton(text=str(i), callback_data=f"2fa_digit_{i}"))
            if len(row) == 3:
                buttons.append(row)
                row = []
        
        buttons.append([
            InlineKeyboardButton(text="0", callback_data="2fa_digit_0"),
            InlineKeyboardButton(text="⌫", callback_data="2fa_backspace"),
            InlineKeyboardButton(text="✅", callback_data="2fa_submit"),
            InlineKeyboardButton(text="🔄", callback_data="2fa_refresh")
        ])
        
        buttons.append([
            InlineKeyboardButton(text="🔑 Backup kod", callback_data="2fa_use_backup")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def create_main_menu(self, user_id: int = None) -> InlineKeyboardMarkup:
        """Asosiy menyu"""
        buttons = []
        
        if user_id and user_id in self.sessions:
            buttons = [
                [InlineKeyboardButton(text="👤 Profil", callback_data="menu_profile")],
                [InlineKeyboardButton(text="📊 Statistika", callback_data="menu_stats")],
                [InlineKeyboardButton(text="📈 Grafiklar", callback_data="menu_charts")],
                [InlineKeyboardButton(text="🤝 Referral", callback_data="menu_referral")],
                [InlineKeyboardButton(text="⭐ Premium", callback_data="menu_premium")],
                [InlineKeyboardButton(text="🌐 Til", callback_data="menu_language")],
                [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="menu_settings")],
                [InlineKeyboardButton(text="🚪 Chiqish", callback_data="menu_logout")]
            ]
        else:
            buttons = [
                [InlineKeyboardButton(text="📝 Ro'yxatdan o'tish", callback_data="menu_register")],
                [InlineKeyboardButton(text="🔑 Kirish", callback_data="menu_login")],
                [InlineKeyboardButton(text="🔄 Parolni tiklash", callback_data="menu_reset")],
                [InlineKeyboardButton(text="🌐 Til", callback_data="menu_language")]
            ]
        
        buttons.append([InlineKeyboardButton(text="📞 Yordam", callback_data="menu_help")])
        
        if user_id and user_id in Config.ADMIN_IDS:
            buttons.append([InlineKeyboardButton(text="👑 Admin panel", callback_data="menu_admin")])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def create_profile_menu(self) -> InlineKeyboardMarkup:
        """Profil menyusi"""
        buttons = [
            [InlineKeyboardButton(text="👤 Account nomini o'zgartirish", callback_data="profile_change_account")],
            [InlineKeyboardButton(text="🔐 Parolni o'zgartirish", callback_data="profile_change_password")],
            [InlineKeyboardButton(text="🔒 2FA sozlamalari", callback_data="profile_2fa")],
            [InlineKeyboardButton(text="📊 Shaxsiy statistika", callback_data="profile_stats")],
            [InlineKeyboardButton(text="📥 Ma'lumotlarni eksport", callback_data="export_data")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_main")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def create_charts_menu(self) -> InlineKeyboardMarkup:
        """Grafiklar menyusi"""
        buttons = [
            [InlineKeyboardButton(text="📊 Haftalik aktivlik", callback_data="chart_weekly")],
            [InlineKeyboardButton(text="🔥 Heatmap", callback_data="chart_heatmap")],
            [InlineKeyboardButton(text="🥧 Doiraviy diagramma", callback_data="chart_pie")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu_profile")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def create_language_menu(self) -> InlineKeyboardMarkup:
        """Til menyusi"""
        buttons = [
            [InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_uz")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_main")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # ==================== ASOSIY METODLAR ====================
    
    async def handle_start(self, message: Message):
        """Start komandasi"""
        user_id = message.from_user.id
        self.monitoring.request_count += 1
        
        # Referral kodni tekshirish
        args = message.text.split()
        referral_code = None
        if len(args) > 1 and args[1].startswith('ref_'):
            referral_code = args[1][4:]
        
        if user_id in self.sessions:
            await message.answer(
                f"👋 Xush kelibsiz, {self.sessions[user_id].login}!",
                reply_markup=self.create_main_menu(user_id)
            )
        else:
            welcome_text = (
                "🔐 **Perfect Security System v3.0**\n\n"
                "Xavfsiz va ishonchli autentifikatsiya tizimi.\n"
                "Microsoft Authenticator bilan to'liq integratsiya.\n\n"
                "**Imkoniyatlar:**\n"
                "✅ Ko'p tillilik (Uz/En/Ru)\n"
                "✅ 2FA (Microsoft Authenticator)\n"
                "✅ Referral dasturi\n"
                "✅ Premium a'zolik\n"
                "✅ Grafiklar va statistika\n"
                "✅ Ma'lumotlarni eksport\n"
                "✅ Avtomatik backup\n\n"
                "Tanlang:"
            )
            
            if referral_code:
                await message.answer(
                    f"{welcome_text}\n\n🔗 Referral kodingiz: `{referral_code}`",
                    reply_markup=self.create_main_menu()
                )
            else:
                await message.answer(
                    welcome_text,
                    reply_markup=self.create_main_menu()
                )
    
    async def handle_help(self, message: Message):
        """Yordam"""
        user_id = message.from_user.id
        
        help_text = (
            "📞 **Yordam**\n\n"
            "**Buyruqlar:**\n"
            "/start - Botni ishga tushirish\n"
            "/help - Yordam\n"
            "/language - Tilni o'zgartirish\n"
            "/stats - Statistika\n\n"
            "**Imkoniyatlar:**\n"
            "• 📝 Ro'yxatdan o'tish\n"
            "• 🔑 Tizimga kirish\n"
            "• 🔐 Microsoft Authenticator 2FA\n"
            "• 📊 Shaxsiy statistika\n"
            "• 📈 Grafiklar\n"
            "• 🤝 Referral dasturi\n"
            "• ⭐ Premium a'zolik\n"
            "• 📥 Ma'lumotlarni eksport\n\n"
            "**Xavfsizlik:**\n"
            "• 8 xonali parol\n"
            "• 5 urinishda bloklash (15 daqiqa)\n"
            "• 2FA har 30 sekundda kod\n"
            "• Backup kodlar (8 ta)\n"
            "• Avtomatik backup\n\n"
            "**Aloqa:** @admin"
        )
        
        await message.answer(
            help_text,
            reply_markup=self.create_main_menu(user_id if user_id in self.sessions else None)
        )
    
    async def handle_language(self, message: Message):
        """Tilni o'zgartirish"""
        await message.answer(
            "Tilni tanlang:",
            reply_markup=self.create_language_menu()
        )
    
    async def handle_stats_command(self, message: Message):
        """Statistika komandasi"""
        user_id = message.from_user.id
        
        if user_id not in self.sessions:
            await message.answer("Avval tizimga kiring!")
            return
        
        stats = await self.db.get_user_stats(user_id)
        
        text = (
            f"📊 **Sizning statistikangiz**\n\n"
            f"📈 Jami kirishlar: {stats['total_logins']}\n"
            f"✅ Muvaffaqiyatli: {stats['successful']}\n"
            f"❌ Muvaffaqiyatsiz: {stats['failed']}\n"
        )
        
        await message.answer(text, reply_markup=self.create_main_menu(user_id))
    
    async def show_main_menu(self, callback: CallbackQuery):
        """Asosiy menyuni ko'rsatish"""
        user_id = callback.from_user.id
        await callback.message.edit_text(
            "Asosiy menyu:",
            reply_markup=self.create_main_menu(user_id if user_id in self.sessions else None)
        )
    
    async def show_language_menu(self, callback: CallbackQuery):
        """Til menyusini ko'rsatish"""
        await callback.message.edit_text(
            "Tilni tanlang:",
            reply_markup=self.create_language_menu()
        )
    
    async def process_language(self, callback: CallbackQuery):
        """Tilni o'zgartirish"""
        lang = callback.data.split("_")[1]
        user_id = callback.from_user.id
        
        if user_id in self.sessions:
            self.sessions[user_id].language = lang
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            await db.execute(
                "UPDATE users SET language = ? WHERE id = ?",
                (lang, user_id)
            )
            await db.commit()
        
        await callback.message.edit_text(
            f"✅ Til o'zgartirildi!",
            reply_markup=self.create_main_menu(user_id if user_id in self.sessions else None)
        )
    
    # ==================== REGISTER METODLARI ====================
    
    async def register_start(self, callback: CallbackQuery, state: FSMContext):
        """Ro'yxatdan o'tishni boshlash"""
        if not self.rate_limiter.check_limit(callback.from_user.id, "register"):
            await callback.answer("❌ Ko'p urinish! Biroz kuting.", show_alert=True)
            return
        
        await callback.message.edit_text(
            "📝 **Ro'yxatdan o'tish**\n\n"
            "Login kiriting (ingliz alifbosi, 3-20 harf):",
            reply_markup=self.create_alphabet_keyboard()
        )
        await state.set_state(RegisterState.waiting_for_login)
    
    async def register_process_login(self, callback: CallbackQuery, state: FSMContext):
        """Login kiritish"""
        letter = callback.data.split("_")[1]
        data = await state.get_data()
        current_login = data.get("login", "") + letter
        
        if len(current_login) > 20:
            await callback.answer("Login juda uzun (maksimum 20)", show_alert=True)
            return
        
        await state.update_data(login=current_login)
        await callback.message.edit_text(
            f"📝 Login: {current_login}\n\n"
            "Kiritishni davom eting yoki ✅ bosing:",
            reply_markup=self.create_alphabet_keyboard()
        )
    
    async def register_login_submit(self, callback: CallbackQuery, state: FSMContext):
        """Loginni tasdiqlash"""
        data = await state.get_data()
        login = data.get("login", "")
        
        if len(login) < 3:
            await callback.answer("Login kamida 3 harf!", show_alert=True)
            return
        
        blocked = ['admin', 'root', 'system', 'support', 'moderator', 'administrator']
        if any(word in login.lower() for word in blocked):
            await callback.answer("Bu login taqiqlangan!", show_alert=True)
            return
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute("SELECT id FROM users WHERE login = ?", (login,))
            if await cursor.fetchone():
                await callback.answer("Bu login band!", show_alert=True)
                return
        
        await state.update_data(login=login)
        await callback.message.edit_text(
            "🔐 Endi 8 xonali parol kiriting:",
            reply_markup=self.create_safe_keyboard()
        )
        await state.set_state(RegisterState.waiting_for_password)
    
    async def register_process_password(self, callback: CallbackQuery, state: FSMContext):
        """Parol kiritish"""
        digit = callback.data.split("_")[1]
        data = await state.get_data()
        current_password = data.get("password", "") + digit
        
        if len(current_password) > 8:
            await callback.answer("Parol 8 xonali!", show_alert=True)
            return
        
        await state.update_data(password=current_password)
        
        strength, messages = self.security.check_password_strength(current_password)
        strength_emoji = ["🔴", "🟡", "🟢"][min(strength, 2)]
        
        messages_text = "\n".join(messages) if messages else ""
        
        await callback.message.edit_text(
            f"🔐 Parol: {'*' * len(current_password)}\n"
            f"Kuchlilik: {strength_emoji} {strength}/3\n"
            f"{messages_text}\n\n"
            "Raqamlarni kiriting yoki ✅ bosing:",
            reply_markup=self.create_safe_keyboard(current_password)
        )
    
    async def register_clear_password(self, callback: CallbackQuery, state: FSMContext):
        """Parolni tozalash"""
        await state.update_data(password="")
        await callback.message.edit_text(
            "🔐 Parolni qaytadan kiriting:",
            reply_markup=self.create_safe_keyboard()
        )
    
    async def register_password_submit(self, callback: CallbackQuery, state: FSMContext):
        """Parolni tasdiqlash"""
        data = await state.get_data()
        password = data.get("password", "")
        
        if len(password) != 8:
            await callback.answer("Parol 8 xonali!", show_alert=True)
            return
        
        strength, _ = self.security.check_password_strength(password)
        if strength < Config.PASSWORD_MIN_STRENGTH:
            await callback.answer("Parol yetarlicha kuchli emas!", show_alert=True)
            return
        
        await state.update_data(password_hash=self.security.hash_password(password))
        await callback.message.edit_text(
            "👤 Account nomini kiriting (2-30 harf):",
            reply_markup=self.create_alphabet_keyboard()
        )
        await state.set_state(RegisterState.waiting_for_account_name)
    
    async def register_process_account(self, callback: CallbackQuery, state: FSMContext):
        """Account nomi kiritish"""
        letter = callback.data.split("_")[1]
        data = await state.get_data()
        current_account = data.get("account", "") + letter
        
        if len(current_account) > 30:
            await callback.answer("Account nomi juda uzun", show_alert=True)
            return
        
        await state.update_data(account=current_account)
        
        await callback.message.edit_text(
            f"👤 Account: {current_account}\n\n"
            "Kiritishni davom eting yoki ✅ bosing:",
            reply_markup=self.create_alphabet_keyboard()
        )
    
    async def register_account_submit(self, callback: CallbackQuery, state: FSMContext):
        """Account nomini tasdiqlash"""
        data = await state.get_data()
        account = data.get("account", "")
        
        if len(account) < 2:
            await callback.answer("Account nomi kamida 2 harf!", show_alert=True)
            return
        
        # Referral kodni so'rash
        await callback.message.edit_text(
            "🔗 Referral kodingiz bormi? (bo'lmasa /skip)",
            reply_markup=None
        )
        await state.set_state(RegisterState.waiting_for_referral)
    
    @self.dp.message(RegisterState.waiting_for_referral)
    async def register_process_referral(self, message: Message, state: FSMContext):
        """Referral kodni qayta ishlash"""
        referral_code = message.text if message.text != "/skip" else None
        await state.update_data(referral_code=referral_code)
        
        await message.answer(
            "📧 Email (ixtiyoriy, o'tkazib yuborish uchun /skip):"
        )
        await state.set_state(RegisterState.waiting_for_email)
    
    async def register_process_email(self, message: Message, state: FSMContext):
        """Email kiritish"""
        email = message.text
        
        if email != "/skip":
            if "@" not in email or "." not in email:
                await message.answer("❌ Noto'g'ri email! Qaytadan yoki /skip:")
                return
        
        await state.update_data(email=email if email != "/skip" else None)
        await message.answer(
            "📱 Telefon (ixtiyoriy, o'tkazib yuborish uchun /skip):"
        )
        await state.set_state(RegisterState.waiting_for_phone)
    
    async def register_process_phone(self, message: Message, state: FSMContext):
        """Telefon kiritish"""
        phone = message.text
        
        if phone != "/skip":
            clean = phone.replace("+", "").replace("-", "").replace(" ", "")
            if not clean.isdigit() or len(clean) < 9:
                await message.answer("❌ Noto'g'ri telefon! Qaytadan yoki /skip:")
                return
        
        await state.update_data(phone=phone if phone != "/skip" else None)
        
        data = await state.get_data()
        secret = self.totp.generate_secret()
        qr_bio = self.totp.generate_qr_code(secret, data['account'])
        
        await state.update_data(two_factor_secret=secret)
        
        caption = (
            f"🔐 **Microsoft Authenticator sozlamalari**\n\n"
            f"1️⃣ Microsoft Authenticator'ni oching\n"
            f"2️⃣ ➕ → QR kodni skanerlash\n"
            f"3️⃣ Ushbu QR kodni skanerlang\n\n"
            f"📱 **Yoki kalitni qo'lda kiriting:**\n"
            f"`{secret}`\n\n"
            f"⏳ Kod har {Config.TOTP_INTERVAL} sekundda yangilanadi\n\n"
            f"✅ 6 xonali kodni kiriting (yoki /skip):"
        )
        
        await message.answer_photo(
            types.BufferedInputFile(qr_bio.getvalue(), filename="2fa.png"),
            caption=caption
        )
        await state.set_state(RegisterState.waiting_for_2fa)
    
    async def register_process_2fa(self, message: Message, state: FSMContext):
        """2FA kodni tekshirish"""
        code = message.text
        data = await state.get_data()
        
        two_factor_enabled = False
        
        if code != "/skip":
            if not self.totp.verify_code(data['two_factor_secret'], code):
                await message.answer("❌ Noto'g'ri kod! Qaytadan yoki /skip:")
                return
            two_factor_enabled = True
        
        # Referral kodni qayta ishlash
        referral_code = data.get('referral_code')
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            # Foydalanuvchini yaratish
            api_key = self.security.generate_api_key()
            referral_code_user = self.referral.generate_referral_code(0)  # Keyin yangilanadi
            
            cursor = await db.execute('''
                INSERT INTO users 
                (login, password_hash, account_name, email, phone, 
                 two_factor_enabled, two_factor_secret, api_key, referral_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['login'],
                data['password_hash'],
                data['account'],
                data.get('email'),
                data.get('phone'),
                two_factor_enabled,
                data['two_factor_secret'] if two_factor_enabled else None,
                api_key,
                referral_code_user
            ))
            await db.commit()
            user_id = cursor.lastrowid
            
            # Referral kodni yangilash
            new_referral_code = self.referral.generate_referral_code(user_id)
            await db.execute(
                "UPDATE users SET referral_code = ? WHERE id = ?",
                (new_referral_code, user_id)
            )
            
            # Referralni qayta ishlash
            if referral_code:
                referrer_id = await self.referral.process_referral(db, referral_code, user_id)
                if referrer_id:
                    await self.channel.post_new_user(user_id, data['login'], referral_code)
            
            # Backup kodlar
            if two_factor_enabled:
                backup_codes = self.backup.generate_codes()
                await self.backup.save_codes(db, user_id, backup_codes)
                
                codes_text = "\n".join([f"`{code}`" for code in backup_codes])
                await message.answer(
                    f"⚠️ **Backup kodlaringiz (xavfsiz joyda saqlang!)**\n\n"
                    f"{codes_text}\n\n"
                    f"Har bir kod faqat bir marta ishlatiladi!"
                )
            
            await self.audit.log(db, user_id, "REGISTER", "Muvaffaqiyatli ro'yxatdan o'tish")
        
        # Kanalga xabar yuborish
        await self.channel.post_new_user(user_id, data['login'], referral_code)
        
        result_text = (
            f"✅ **Ro'yxatdan o'tish muvaffaqiyatli!**\n\n"
            f"Login: {data['login']}\n"
            f"Account: {data['account']}\n"
            f"2FA: {'✅ Yoqilgan' if two_factor_enabled else '❌ Ochirilgan'}\n"
            f"🔑 API Kalit: `{api_key}`\n\n"
            f"Endi tizimga kirishingiz mumkin!"
        )
        
        await message.answer(
            result_text,
            reply_markup=self.create_main_menu()
        )
        await state.clear()
    
    # ==================== LOGIN METODLARI ====================
    
    async def login_start(self, callback: CallbackQuery, state: FSMContext):
        """Kirishni boshlash"""
        if not self.rate_limiter.check_limit(callback.from_user.id, "login"):
            await callback.answer("❌ Ko'p urinish! Biroz kuting.", show_alert=True)
            return
        
        await callback.message.edit_text(
            "🔑 Loginni kiriting:",
            reply_markup=self.create_alphabet_keyboard()
        )
        await state.set_state(LoginState.waiting_for_login)
    
    async def login_process_login(self, callback: CallbackQuery, state: FSMContext):
        """Login kiritish"""
        letter = callback.data.split("_")[1]
        data = await state.get_data()
        current_login = data.get("login", "") + letter
        
        await state.update_data(login=current_login)
        
        await callback.message.edit_text(
            f"🔑 Login: {current_login}\n\n"
            "Kiritishni davom eting yoki ✅ bosing:",
            reply_markup=self.create_alphabet_keyboard()
        )
    
    async def login_login_submit(self, callback: CallbackQuery, state: FSMContext):
        """Loginni tasdiqlash"""
        data = await state.get_data()
        login = data.get("login", "")
        
        locked, minutes = await self.db.check_lockout(login)
        
        if locked:
            await callback.answer(
                f"Hisob bloklangan! {minutes} daqiqadan so'ng urinib ko'ring.",
                show_alert=True
            )
            return
        
        async with aiosqlite.connect(Config.DB_FILE) as conn:
            cursor = await conn.execute(
                "SELECT id FROM users WHERE login = ?",
                (login,)
            )
            if not await cursor.fetchone():
                await callback.answer("Bunday login mavjud emas!", show_alert=True)
                return
        
        await callback.message.edit_text(
            "🔐 Parolni kiriting:",
            reply_markup=self.create_safe_keyboard()
        )
        await state.set_state(LoginState.waiting_for_password)
    
    async def login_process_password(self, callback: CallbackQuery, state: FSMContext):
        """Parol kiritish"""
        digit = callback.data.split("_")[1]
        data = await state.get_data()
        current_password = data.get("password", "") + digit
        
        if len(current_password) > 8:
            await callback.answer("Parol 8 xonali!", show_alert=True)
            return
        
        await state.update_data(password=current_password)
        
        await callback.message.edit_text(
            f"🔐 Parol: {'*' * len(current_password)}\n\n"
            "Raqamlarni kiriting yoki ✅ bosing:",
            reply_markup=self.create_safe_keyboard(current_password)
        )
    
    async def login_password_submit(self, callback: CallbackQuery, state: FSMContext):
        """Parolni tekshirish"""
        data = await state.get_data()
        login = data.get("login", "")
        password = data.get("password", "")
        
        if len(password) != 8:
            await callback.answer("Parol 8 xonali!", show_alert=True)
            return
        
        password_hash = self.security.hash_password(password)
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute('''
                SELECT id, account_name, two_factor_enabled, two_factor_secret, premium_tier 
                FROM users WHERE login = ? AND password_hash = ?
            ''', (login, password_hash))
            user = await cursor.fetchone()
            
            if not user:
                await db.execute(
                    "UPDATE users SET login_attempts = login_attempts + 1 WHERE login = ?",
                    (login,)
                )
                await db.commit()
                
                await callback.message.edit_text(
                    "❌ Noto'g'ri parol! Qaytadan urinib ko'ring:",
                    reply_markup=self.create_safe_keyboard()
                )
                await state.update_data(password="")
                return
            
            user_id, account_name, two_factor_enabled, two_factor_secret, premium_tier = user
            
            # Login urinishlarini reset qilish
            await db.execute(
                "UPDATE users SET login_attempts = 0 WHERE id = ?",
                (user_id,)
            )
            await db.commit()
            
            if two_factor_enabled:
                await state.update_data(
                    user_id=user_id,
                    account_name=account_name,
                    two_factor_secret=two_factor_secret,
                    login=login,
                    premium_tier=premium_tier
                )
                
                current_code = self.totp.get_current_code(two_factor_secret)
                remaining = self.totp.get_remaining_seconds(two_factor_secret)
                
                await callback.message.edit_text(
                    f"🔐 **Microsoft Authenticator kodi**\n\n"
                    f"📱 6 xonali kodni kiriting\n"
                    f"⏳ Yangilanadi: {remaining} sekund\n"
                    f"💡 Masalan: `{current_code}`",
                    reply_markup=self.create_2fa_keyboard()
                )
                await state.set_state(LoginState.waiting_for_2fa)
                return
            
            await self.complete_login(callback, user_id, account_name, login, premium_tier, db)
        
        await state.clear()
    
    async def login_2fa_digit(self, callback: CallbackQuery, state: FSMContext):
        """2FA kod kiritish"""
        digit = callback.data.split("_")[2]
        data = await state.get_data()
        current_code = data.get("two_fa_code", "") + digit
        
        if len(current_code) > 6:
            await callback.answer("Kod 6 xonali!", show_alert=True)
            return
        
        await state.update_data(two_fa_code=current_code)
        
        await callback.message.edit_text(
            f"🔐 Kod: {'*' * len(current_code)}\n"
            f"Kiritilgan: {current_code}\n\n"
            f"6 xonali kodni kiriting:",
            reply_markup=self.create_2fa_keyboard()
        )
    
    async def login_2fa_backspace(self, callback: CallbackQuery, state: FSMContext):
        """2FA kodni o'chirish"""
        data = await state.get_data()
        current_code = data.get("two_fa_code", "")
        
        if current_code:
            current_code = current_code[:-1]
            await state.update_data(two_fa_code=current_code)
            
            await callback.message.edit_text(
                f"🔐 Kod: {'*' * len(current_code)}\n"
                f"Kiritilgan: {current_code}\n\n"
                f"6 xonali kodni kiriting:",
                reply_markup=self.create_2fa_keyboard()
            )
    
    async def login_2fa_refresh(self, callback: CallbackQuery, state: FSMContext):
        """2FA kodni yangilash"""
        data = await state.get_data()
        
        current_code = self.totp.get_current_code(data['two_factor_secret'])
        remaining = self.totp.get_remaining_seconds(data['two_factor_secret'])
        
        await callback.message.edit_text(
            f"🔐 **Microsoft Authenticator kodi**\n\n"
            f"📱 Joriy kod: `{current_code}`\n"
            f"⏳ Yangilanadi: {remaining} sekund\n\n"
            f"6 xonali kodni kiriting:",
            reply_markup=self.create_2fa_keyboard()
        )
    
    async def login_2fa_submit(self, callback: CallbackQuery, state: FSMContext):
        """2FA kodni tekshirish"""
        data = await state.get_data()
        entered_code = data.get("two_fa_code", "")
        
        if len(entered_code) != 6:
            await callback.answer("6 xonali kod kiriting!", show_alert=True)
            return
        
        if self.totp.verify_code(data['two_factor_secret'], entered_code):
            async with aiosqlite.connect(Config.DB_FILE) as db:
                await self.complete_login(
                    callback, data['user_id'], data['account_name'], 
                    data['login'], data.get('premium_tier', 'free'), db
                )
            await state.clear()
            return
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            if await self.backup.verify_code(db, data['user_id'], entered_code):
                await self.backup.use_code(db, data['user_id'], entered_code)
                await self.complete_login(
                    callback, data['user_id'], data['account_name'], 
                    data['login'], data.get('premium_tier', 'free'), db
                )
                await state.clear()
                return
        
        await callback.answer("❌ Noto'g'ri kod!", show_alert=True)
        await state.update_data(two_fa_code="")
    
    async def login_use_backup(self, callback: CallbackQuery, state: FSMContext):
        """Backup kod ishlatish"""
        await callback.message.edit_text(
            "🔑 **Backup kodni kiriting**\n\n"
            "Ro'yxatdan o'tishda berilgan 8 xonali kodni yozing:",
            reply_markup=self.create_alphabet_keyboard()
        )
        await state.set_state(LoginState.waiting_for_backup)
    
    async def complete_login(self, callback: CallbackQuery, user_id: int, 
                            account_name: str, login: str, premium_tier: str, 
                            db: aiosqlite.Connection):
        """Login jarayonini yakunlash"""
        # Sessiya yaratish
        session_id = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        self.sessions[callback.from_user.id] = Session(
            user_id=user_id,
            login=login,
            login_time=datetime.now(),
            last_activity=datetime.now(),
            active=True,
            language='uz',
            session_id=session_id,
            premium_tier=premium_tier
        )
        
        # Sessiyani bazaga yozish
        await db.execute(
            "INSERT INTO sessions (session_id, user_id, ip) VALUES (?, ?, ?)",
            (session_id, user_id, "0.0.0.0")
        )
        
        # Login tarixiga yozish
        await db.execute(
            "INSERT INTO login_history (user_id, successful, method) VALUES (?, ?, ?)",
            (user_id, True, '2fa' if 'two_factor_secret' in await state.get_data() else 'password')
        )
        
        await db.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,)
        )
        await db.commit()
        
        await self.audit.log(db, user_id, "LOGIN_SUCCESS", "Muvaffaqiyatli kirish")
        
        # Premium xususiyatlar
        premium_features = PREMIUM_FEATURES.get(premium_tier, PREMIUM_FEATURES['free'])
        
        welcome_text = (
            f"✅ **Tizimga muvaffaqiyatli kirdingiz!**\n\n"
            f"👋 Xush kelibsiz, {account_name}!\n"
            f"⭐ Darajangiz: {premium_tier.upper()}\n\n"
            f"**Premium xususiyatlar:**\n"
            f"• Max accountlar: {premium_features['max_accounts']}\n"
            f"• Backup kodlar: {premium_features['backup_codes']}\n"
            f"• Sessiya muddati: {premium_features['session_timeout']//3600} soat\n"
            f"• Grafiklar: {'✅' if premium_features['charts_enabled'] else '❌'}\n"
            f"• API: {'✅' if premium_features['api_access'] else '❌'}"
        )
        
        await callback.message.edit_text(
            welcome_text,
            reply_markup=self.create_main_menu(callback.from_user.id)
        )
        
        # Kanalga xabar yuborish
        await self.channel.post_login_alert(user_id, login, "0.0.0.0")
    
    # ==================== PROFIL METODLARI ====================
    
    async def profile_menu(self, callback: CallbackQuery):
        """Profil menyusi"""
        if callback.from_user.id not in self.sessions:
            await callback.answer("Avval tizimga kiring!", show_alert=True)
            return
        
        self.sessions[callback.from_user.id].last_activity = datetime.now()
        
        await callback.message.edit_text(
            "👤 **Profil boshqaruvi**",
            reply_markup=self.create_profile_menu()
        )
    
    async def profile_change_account_start(self, callback: CallbackQuery, state: FSMContext):
        """Account nomini o'zgartirishni boshlash"""
        await callback.message.edit_text(
            "👤 Yangi account nomini kiriting:",
            reply_markup=self.create_alphabet_keyboard()
        )
        await state.set_state(ProfileState.waiting_for_new_account)
    
    async def profile_change_account_process(self, callback: CallbackQuery, state: FSMContext):
        """Yangi account nomi kiritish"""
        letter = callback.data.split("_")[1]
        data = await state.get_data()
        current_account = data.get("new_account", "") + letter
        
        if len(current_account) > 30:
            await callback.answer("Account nomi juda uzun", show_alert=True)
            return
        
        await state.update_data(new_account=current_account)
        
        await callback.message.edit_text(
            f"👤 Yangi account: {current_account}\n\n"
            "Kiritishni davom eting yoki ✅ bosing:",
            reply_markup=self.create_alphabet_keyboard()
        )
    
    async def profile_change_account_complete(self, callback: CallbackQuery, state: FSMContext):
        """Account nomini o'zgartirishni yakunlash"""
        data = await state.get_data()
        new_account = data.get("new_account", "")
        
        if len(new_account) < 2:
            await callback.answer("Account nomi kamida 2 harf!", show_alert=True)
            return
        
        user_id = callback.from_user.id
        login = self.sessions[user_id].login
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            await db.execute(
                "UPDATE users SET account_name = ? WHERE login = ?",
                (new_account, login)
            )
            await db.commit()
            
            cursor = await db.execute("SELECT id FROM users WHERE login = ?", (login,))
            user_id_db = (await cursor.fetchone())[0]
            await self.audit.log(db, user_id_db, "PROFILE_UPDATE", f"Account: {new_account}")
        
        await callback.message.edit_text(
            f"✅ Account nomi o'zgartirildi: {new_account}",
            reply_markup=self.create_main_menu(user_id)
        )
        await state.clear()
    
    async def profile_change_password_start(self, callback: CallbackQuery, state: FSMContext):
        """Parolni o'zgartirishni boshlash"""
        await callback.message.edit_text(
            "🔐 Eski parolni kiriting:",
            reply_markup=self.create_safe_keyboard()
        )
        await state.set_state(ProfileState.waiting_for_old_password)
    
    async def profile_change_password_old(self, callback: CallbackQuery, state: FSMContext):
        """Eski parol kiritish"""
        digit = callback.data.split("_")[1]
        data = await state.get_data()
        current_password = data.get("old_password", "") + digit
        
        if len(current_password) > 8:
            await callback.answer("Parol 8 xonali!", show_alert=True)
            return
        
        await state.update_data(old_password=current_password)
        
        await callback.message.edit_text(
            f"🔐 Eski parol: {'*' * len(current_password)}\n\n"
            "Raqamlarni kiriting yoki ✅ bosing:",
            reply_markup=self.create_safe_keyboard(current_password)
        )
    
    async def profile_change_password_old_submit(self, callback: CallbackQuery, state: FSMContext):
        """Eski parolni tekshirish"""
        data = await state.get_data()
        old_password = data.get("old_password", "")
        
        if len(old_password) != 8:
            await callback.answer("Parol 8 xonali!", show_alert=True)
            return
        
        user_id = callback.from_user.id
        login = self.sessions[user_id].login
        old_hash = self.security.hash_password(old_password)
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute(
                "SELECT id FROM users WHERE login = ? AND password_hash = ?",
                (login, old_hash)
            )
            user = await cursor.fetchone()
            
            if not user:
                await callback.answer("❌ Eski parol noto'g'ri!", show_alert=True)
                await state.update_data(old_password="")
                return
            
            await state.update_data(user_id_db=user[0])
        
        await callback.message.edit_text(
            "🔐 Yangi 8 xonali parolni kiriting:",
            reply_markup=self.create_safe_keyboard()
        )
        await state.set_state(ProfileState.waiting_for_new_password)
    
    async def profile_change_password_new(self, callback: CallbackQuery, state: FSMContext):
        """Yangi parol kiritish"""
        digit = callback.data.split("_")[1]
        data = await state.get_data()
        current_password = data.get("new_password", "") + digit
        
        if len(current_password) > 8:
            await callback.answer("Parol 8 xonali!", show_alert=True)
            return
        
        await state.update_data(new_password=current_password)
        
        strength, messages = self.security.check_password_strength(current_password)
        strength_emoji = ["🔴", "🟡", "🟢"][min(strength, 2)]
        
        messages_text = "\n".join(messages) if messages else ""
        
        await callback.message.edit_text(
            f"🔐 Yangi parol: {'*' * len(current_password)}\n"
            f"Kuchlilik: {strength_emoji} {strength}/3\n"
            f"{messages_text}\n\n"
            "Raqamlarni kiriting yoki ✅ bosing:",
            reply_markup=self.create_safe_keyboard(current_password)
        )
    
    async def profile_change_password_complete(self, callback: CallbackQuery, state: FSMContext):
        """Parolni o'zgartirishni yakunlash"""
        data = await state.get_data()
        new_password = data.get("new_password", "")
        
        if len(new_password) != 8:
            await callback.answer("Parol 8 xonali!", show_alert=True)
            return
        
        strength, _ = self.security.check_password_strength(new_password)
        if strength < Config.PASSWORD_MIN_STRENGTH:
            await callback.answer("Parol yetarlicha kuchli emas!", show_alert=True)
            return
        
        new_hash = self.security.hash_password(new_password)
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            await db.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_hash, data['user_id_db'])
            )
            await db.commit()
            await self.audit.log(db, data['user_id_db'], "PASSWORD_CHANGE", "Parol o'zgartirildi")
        
        await callback.message.edit_text(
            "✅ Parol muvaffaqiyatli o'zgartirildi!",
            reply_markup=self.create_main_menu(callback.from_user.id)
        )
        await state.clear()
    
    async def profile_2fa_menu(self, callback: CallbackQuery):
        """2FA menyusi"""
        user_id = callback.from_user.id
        
        if user_id not in self.sessions:
            await callback.answer("Avval tizimga kiring!", show_alert=True)
            return
        
        login = self.sessions[user_id].login
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute('''
                SELECT two_factor_enabled, two_factor_secret,
                       (SELECT COUNT(*) FROM backup_codes WHERE user_id = users.id AND used = 0)
                FROM users WHERE login = ?
            ''', (login,))
            result = await cursor.fetchone()
            
            if not result:
                await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
                return
            
            enabled, secret, backup_count = result
        
        if enabled:
            current_code = self.totp.get_current_code(secret) if secret else "Noma'lum"
            remaining = self.totp.get_remaining_seconds(secret) if secret else 0
            
            text = (
                f"📱 **Microsoft Authenticator 2FA**\n\n"
                f"🔐 **Holat:** ✅ Yoqilgan\n"
                f"⏳ **Joriy kod:** `{current_code}`\n"
                f"⚡ **Yangilanadi:** {remaining} sekund\n"
                f"📊 **Backup kodlar:** {backup_count} ta qoldi\n\n"
                f"**Xavfsizlik:**\n"
                f"• Kod har {Config.TOTP_INTERVAL} sekundda yangilanadi\n"
                f"• Backup kodlar 8 xonali\n"
                f"• Har bir backup kod faqat bir marta ishlatiladi"
            )
            
            buttons = [
                [InlineKeyboardButton(text="🔄 Yangi backup kodlar", callback_data="2fa_regenerate_backup")],
                [InlineKeyboardButton(text="📸 QR kodni ko'rsat", callback_data="2fa_show_qr")],
                [InlineKeyboardButton(text="🔓 2FA ni o'chirish", callback_data="2fa_disable")],
                [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu_profile")]
            ]
        else:
            text = (
                f"📱 **Microsoft Authenticator 2FA**\n\n"
                f"🔐 **Holat:** ❌ O'chirilgan\n\n"
                f"**2FA yoqish orqali:**\n"
                f"• Hisobingiz qo'shimcha himoyalanadi\n"
                f"• Har kirishda 6 xonali kod talab qilinadi\n"
                f"• Kod har {Config.TOTP_INTERVAL} sekundda yangilanadi"
            )
            
            buttons = [
                [InlineKeyboardButton(text="🔒 2FA ni yoqish", callback_data="2fa_enable")],
                [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu_profile")]
            ]
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    
    async def enable_2fa_start(self, callback: CallbackQuery, state: FSMContext):
        """2FA yoqishni boshlash"""
        user_id = callback.from_user.id
        
        if user_id not in self.sessions:
            await callback.answer("Avval tizimga kiring!", show_alert=True)
            return
        
        login = self.sessions[user_id].login
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute(
                "SELECT id, account_name FROM users WHERE login = ?",
                (login,)
            )
            user = await cursor.fetchone()
            
            if not user:
                await callback.answer("Foydalanuvchi topilmadi!", show_alert=True)
                return
            
            user_id_db, account_name = user
        
        secret = self.totp.generate_secret()
        qr_bio = self.totp.generate_qr_code(secret, account_name)
        
        await state.update_data(
            two_factor_secret=secret,
            user_id_db=user_id_db,
            account_name=account_name
        )
        
        caption = (
            f"🔐 **Microsoft Authenticator sozlamalari**\n\n"
            f"1️⃣ Microsoft Authenticator'ni oching\n"
            f"2️⃣ ➕ → QR kodni skanerlash\n"
            f"3️⃣ Ushbu QR kodni skanerlang\n\n"
            f"📱 **Yoki kalitni qo'lda kiriting:**\n"
            f"`{secret}`\n\n"
            f"✅ 6 xonali kodni kiriting:"
        )
        
        await callback.message.delete()
        await callback.message.answer_photo(
            types.BufferedInputFile(qr_bio.getvalue(), filename="2fa.png"),
            caption=caption
        )
        await state.set_state(TwoFactorState.waiting_for_verification)
    
    async def disable_2fa(self, callback: CallbackQuery):
        """2FA o'chirish"""
        user_id = callback.from_user.id
        login = self.sessions[user_id].login
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute("SELECT id FROM users WHERE login = ?", (login,))
            user_id_db = (await cursor.fetchone())[0]
            
            await db.execute(
                "UPDATE users SET two_factor_enabled = 0, two_factor_secret = NULL WHERE id = ?",
                (user_id_db,)
            )
            
            await db.execute("DELETE FROM backup_codes WHERE user_id = ?", (user_id_db,))
            await db.commit()
            
            await self.audit.log(db, user_id_db, "2FA_DISABLE", "2FA o'chirildi")
        
        await callback.message.edit_text(
            "❌ 2FA o'chirildi!",
            reply_markup=self.create_main_menu(user_id)
        )
    
    async def show_2fa_qr(self, callback: CallbackQuery):
        """2FA QR kodni ko'rsatish"""
        user_id = callback.from_user.id
        login = self.sessions[user_id].login
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute(
                "SELECT account_name, two_factor_secret FROM users WHERE login = ?",
                (login,)
            )
            user = await cursor.fetchone()
            
            if not user or not user[1]:
                await callback.answer("2FA sozlanmagan!", show_alert=True)
                return
            
            account_name, secret = user
        
        qr_bio = self.totp.generate_qr_code(secret, account_name)
        
        caption = (
            f"📱 **Microsoft Authenticator QR kodi**\n\n"
            f"Secret kalit: `{secret}`\n\n"
            f"Agar QR kodni skanerlay olmasangiz, kalitni qo'lda kiriting."
        )
        
        await callback.message.delete()
        await callback.message.answer_photo(
            types.BufferedInputFile(qr_bio.getvalue(), filename="2fa.png"),
            caption=caption,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="profile_2fa")]
            ])
        )
    
    async def regenerate_backup_codes(self, callback: CallbackQuery):
        """Yangi backup kodlar yaratish"""
        user_id = callback.from_user.id
        login = self.sessions[user_id].login
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute("SELECT id FROM users WHERE login = ?", (login,))
            user_id_db = (await cursor.fetchone())[0]
            
            new_codes = self.backup.generate_codes()
            await self.backup.save_codes(db, user_id_db, new_codes)
            
            await self.audit.log(db, user_id_db, "BACKUP_REGENERATE", "Yangi backup kodlar")
        
        codes_text = "\n".join([f"`{code}`" for code in new_codes])
        
        await callback.message.edit_text(
            f"✅ **Yangi backup kodlar yaratildi!**\n\n"
            f"{codes_text}\n\n"
            f"⚠️ Bu kodlarni xavfsiz joyda saqlang!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="profile_2fa")]
            ])
        )
    
    async def show_profile_stats(self, callback: CallbackQuery):
        """Shaxsiy statistika"""
        user_id = callback.from_user.id
        login = self.sessions[user_id].login
        
        stats = await self.db.get_user_stats(user_id)
        
        # Premium ma'lumotlarni olish
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute(
                "SELECT premium_tier, premium_until FROM users WHERE login = ?",
                (login,)
            )
            premium = await cursor.fetchone()
        
        tier = premium[0] if premium else 'free'
        until = premium[1] if premium and premium[1] else 'Muddati yo\'q'
        
        text = (
            f"📊 **Shaxsiy statistika**\n\n"
            f"⭐ **Daraja:** {tier.upper()}\n"
            f"⏳ **Premium muddati:** {until}\n\n"
            f"📈 **Umumiy:** {stats['total_logins']}\n"
            f"✅ **Muvaffaqiyatli:** {stats['successful']}\n"
            f"❌ **Muvaffaqiyatsiz:** {stats['failed']}\n"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=self.create_profile_menu()
        )
    
    # ==================== GRAFIK METODLARI ====================
    
    async def show_charts_menu(self, callback: CallbackQuery):
        """Grafiklar menyusini ko'rsatish"""
        user_id = callback.from_user.id
        
        if user_id not in self.sessions:
            await callback.answer("Avval tizimga kiring!", show_alert=True)
            return
        
        # Premium tekshirish
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute(
                "SELECT premium_tier FROM users WHERE id = ?",
                (self.sessions[user_id].user_id,)
            )
            tier = await cursor.fetchone()
            tier = tier[0] if tier else 'free'
        
        features = PREMIUM_FEATURES.get(tier, PREMIUM_FEATURES['free'])
        
        if not features['charts_enabled'] and tier == 'free':
            await callback.message.edit_text(
                "📈 **Grafiklar faqat premium a'zolar uchun!**\n\n"
                "Premium a'zo bo'lish orqali quyidagi imkoniyatlarga ega bo'ling:\n"
                "• Haftalik aktivlik grafigi\n"
                "• Heatmap\n"
                "• Doiraviy diagramma\n"
                "• Boshqa vizualizatsiyalar",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⭐ Premium olish", callback_data="menu_premium")],
                    [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu_profile")]
                ])
            )
            return
        
        await callback.message.edit_text(
            "📈 **Grafiklar**\n\n"
            "Quyidagi grafiklardan birini tanlang:",
            reply_markup=self.create_charts_menu()
        )
    
    async def show_weekly_chart(self, callback: CallbackQuery):
        """Haftalik grafikni ko'rsatish"""
        user_id = callback.from_user.id
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute('''
                SELECT date(login_time) as day, COUNT(*) 
                FROM login_history 
                WHERE user_id = ? AND login_time > datetime('now', '-7 days')
                GROUP BY date(login_time)
                ORDER BY day
            ''', (self.sessions[user_id].user_id,))
            data = await cursor.fetchall()
        
        if not data:
            await callback.answer("Ma'lumot yetarli emas!", show_alert=True)
            return
        
        days = [row[0][5:] for row in data]  # MM-DD format
        counts = [row[1] for row in data]
        
        chart = self.visualization.create_activity_chart(
            days, counts, "Oxirgi 7 kunlik aktivlik"
        )
        
        await callback.message.delete()
        await callback.message.answer_photo(
            types.BufferedInputFile(chart.getvalue(), filename="weekly.png"),
            caption="📊 **Oxirgi 7 kunlik aktivlik grafigi**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu_charts")]
            ])
        )
    
    async def show_heatmap(self, callback: CallbackQuery):
        """Heatmapni ko'rsatish"""
        user_id = callback.from_user.id
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute('''
                SELECT login_time FROM login_history 
                WHERE user_id = ? AND login_time > datetime('now', '-30 days')
            ''', (self.sessions[user_id].user_id,))
            data = await cursor.fetchall()
        
        if not data or len(data) < 5:
            await callback.answer("Heatmap uchun ma'lumot yetarli emas!", show_alert=True)
            return
        
        login_times = [row[0] for row in data]
        chart = self.visualization.create_heatmap(login_times)
        
        await callback.message.delete()
        await callback.message.answer_photo(
            types.BufferedInputFile(chart.getvalue(), filename="heatmap.png"),
            caption="🔥 **30 kunlik aktivlik heatmap**\n\n"
                    "Qizil rang - yuqori aktivlik\n"
                    "Sariq rang - o'rtacha aktivlik\n"
                    "To'q sariq - past aktivlik",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu_charts")]
            ])
        )
    
    async def show_pie_chart(self, callback: CallbackQuery):
        """Doiraviy diagrammani ko'rsatish"""
        user_id = callback.from_user.id
        
        stats = await self.db.get_user_stats(self.sessions[user_id].user_id)
        
        labels = ['Muvaffaqiyatli', 'Muvaffaqiyatsiz']
        values = [stats['successful'], stats['failed']]
        
        if sum(values) == 0:
            await callback.answer("Ma'lumot yetarli emas!", show_alert=True)
            return
        
        chart = self.visualization.create_pie_chart(
            labels, values, "Kirish statistikasi"
        )
        
        await callback.message.delete()
        await callback.message.answer_photo(
            types.BufferedInputFile(chart.getvalue(), filename="pie.png"),
            caption="🥧 **Kirish statistikasi**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu_charts")]
            ])
        )
    
    # ==================== REFERRAL METODLARI ====================
    
    async def show_referral_stats(self, callback: CallbackQuery):
        """Referral statistikasini ko'rsatish"""
        user_id = callback.from_user.id
        
        if user_id not in self.sessions:
            await callback.answer("Avval tizimga kiring!", show_alert=True)
            return
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute(
                "SELECT referral_code FROM users WHERE login = ?",
                (self.sessions[user_id].login,)
            )
            referral_code = await cursor.fetchone()
            
            stats = await self.referral.get_referral_stats(
                db, self.sessions[user_id].user_id
            )
        
        bot_info = await self.bot.get_me()
        referral_link = f"https://t.me/{bot_info.username}?start=ref_{referral_code[0]}"
        
        text = (
            f"🤝 **Referral dasturi**\n\n"
            f"📎 **Sizning referral kodingiz:**\n`{referral_code[0] if referral_code else 'Mavjud emas'}`\n\n"
            f"📊 **Statistika:**\n"
            f"• Jami taklif qilinganlar: {stats['total']}\n"
            f"• Bonus olganlar: {stats['bonuses']}\n\n"
            f"🔗 **Taklifnoma linki:**\n`{referral_link}`\n\n"
            f"**Oxirgi taklif qilinganlar:**\n"
        )
        
        for ref in stats['recent'][:5]:
            text += f"• {ref[0]} - {ref[1][:10]}\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Kodni nusxalash", callback_data=f"copy_{referral_code[0]}")],
                [InlineKeyboardButton(text="🔗 Linkni ulashish", url=f"https://t.me/share/url?url={referral_link}")],
                [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu_profile")]
            ])
        )
    
    # ==================== PREMIUM METODLARI ====================
    
    async def premium_menu(self, callback: CallbackQuery):
        """Premium menyu"""
        user_id = callback.from_user.id
        
        if user_id not in self.sessions:
            await callback.answer("Avval tizimga kiring!", show_alert=True)
            return
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute(
                "SELECT premium_tier, premium_until FROM users WHERE login = ?",
                (self.sessions[user_id].login,)
            )
            user = await cursor.fetchone()
        
        tier = user[0] if user else 'free'
        until = user[1] if user and user[1] else 'Aktiv emas'
        
        text = (
            f"⭐ **Premium a'zolik**\n\n"
            f"🔰 **Sizning darajangiz:** {tier.upper()}\n"
            f"⏳ **Amal qilish muddati:** {until}\n\n"
            f"**Tariflar:**\n"
            f"🆓 **FREE** - 0$\n"
            f"• 1 ta account\n"
            f"• 8 ta backup kod\n"
            f"• 30 daqiqa sessiya\n"
            f"• Grafiklar yo'q\n\n"
            f"⭐ **BASIC** - 5.99$/oy\n"
            f"• 3 ta account\n"
            f"• 16 ta backup kod\n"
            f"• 2 soat sessiya\n"
            f"• Grafiklar mavjud\n\n"
            f"💎 **PRO** - 14.99$/oy\n"
            f"• 10 ta account\n"
            f"• 32 ta backup kod\n"
            f"• 24 soat sessiya\n"
            f"• Grafiklar mavjud\n"
            f"• API access\n\n"
            f"🏢 **ENTERPRISE** - 49.99$/oy\n"
            f"• 100 ta account\n"
            f"• 128 ta backup kod\n"
            f"• 3 kun sessiya\n"
            f"• Grafiklar mavjud\n"
            f"• API access\n"
            f"• Priority support"
        )
        
        buttons = [
            [InlineKeyboardButton(text="⭐ BASIC (5.99$)", callback_data="buy_basic")],
            [InlineKeyboardButton(text="💎 PRO (14.99$)", callback_data="buy_pro")],
            [InlineKeyboardButton(text="🏢 ENTERPRISE (49.99$)", callback_data="buy_enterprise")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu_profile")]
        ]
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    
    async def process_purchase(self, callback: CallbackQuery, state: FSMContext):
        """Xarid qilish"""
        tier = callback.data.split("_")[1]
        amount = Config.PREMIUM_PRICES.get(tier, 0)
        
        if amount == 0:
            await callback.answer("Noto'g'ri tanlov!", show_alert=True)
            return
        
        payment_url = await self.payment.create_click_payment(
            callback.from_user.id, amount, tier
        )
        
        await state.update_data(
            tier=tier,
            amount=amount,
            transaction_id=f"{callback.from_user.id}-{tier}-{int(datetime.now().timestamp())}"
        )
        
        await callback.message.edit_text(
            f"💰 **To'lov**\n\n"
            f"Mahsulot: {tier.upper()}\n"
            f"Summa: {amount}$\n"
            f"To'lov turi: Click\n\n"
            f"To'lovni amalga oshirish uchun quyidagi linkni bosing:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Click orqali to'lash", url=payment_url)],
                [InlineKeyboardButton(text="✅ To'lovni tekshirish", callback_data=f"check_payment_{tier}")],
                [InlineKeyboardButton(text="⬅️ Bekor qilish", callback_data="menu_premium")]
            ])
        )
        
        await state.set_state(PremiumState.waiting_for_payment)
    
    async def check_payment(self, callback: CallbackQuery, state: FSMContext):
        """To'lovni tekshirish"""
        data = await state.get_data()
        
        # To'lovni tekshirish (simulyatsiya)
        payment_successful = await self.payment.check_payment(
            data.get('transaction_id', '')
        )
        
        if payment_successful:
            # Premiumni faollashtirish
            tier = data.get('tier', 'basic')
            user_id = callback.from_user.id
            
            async with aiosqlite.connect(Config.DB_FILE) as db:
                # Foydalanuvchi ID sini olish
                cursor = await db.execute(
                    "SELECT id FROM users WHERE login = ?",
                    (self.sessions[user_id].login,)
                )
                user_id_db = (await cursor.fetchone())[0]
                
                # Premium muddatini hisoblash
                premium_until = datetime.now() + timedelta(days=30)
                
                await db.execute(
                    "UPDATE users SET premium_tier = ?, premium_until = ? WHERE id = ?",
                    (tier, premium_until.isoformat(), user_id_db)
                )
                
                # To'lovni qayd etish
                await db.execute(
                    "INSERT INTO payments (user_id, amount, tier, transaction_id, status) VALUES (?, ?, ?, ?, ?)",
                    (user_id_db, data.get('amount', 0), tier, data.get('transaction_id', ''), 'completed')
                )
                await db.commit()
                
                await self.audit.log(db, user_id_db, "PREMIUM_PURCHASE", f"{tier} sotib olindi")
            
            # Sessiyani yangilash
            self.sessions[user_id].premium_tier = tier
            
            await callback.message.edit_text(
                f"✅ **To'lov muvaffaqiyatli!**\n\n"
                f"Tabriklaymiz! Siz {tier.upper()} paketini sotib oldingiz.\n"
                f"Endi barcha premium imkoniyatlardan foydalanishingiz mumkin!",
                reply_markup=self.create_main_menu(user_id)
            )
            await state.clear()
        else:
            await callback.answer(
                "❌ To'lov hali amalga oshirilmagan. Iltimos, to'lovni amalga oshiring va qayta tekshiring.",
                show_alert=True
            )
    
    # ==================== EXPORT METODLARI ====================
    
    async def export_user_data(self, callback: CallbackQuery):
        """Ma'lumotlarni eksport qilish"""
        user_id = callback.from_user.id
        login = self.sessions[user_id].login
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute('''
                SELECT id, login, account_name, email, phone, two_factor_enabled,
                       created_at, last_login, premium_tier, premium_until
                FROM users WHERE login = ?
            ''', (login,))
            user_data = await cursor.fetchone()
            
            if not user_data:
                await callback.answer("Ma'lumot topilmadi!", show_alert=True)
                return
            
            # Login tarixi
            cursor = await db.execute('''
                SELECT login_time, successful, method, ip
                FROM login_history 
                WHERE user_id = ? 
                ORDER BY login_time DESC LIMIT 50
            ''', (user_data[0],))
            history = await cursor.fetchall()
            
            # Backup kodlar
            cursor = await db.execute('''
                SELECT code, used, created_at, used_at
                FROM backup_codes 
                WHERE user_id = ?
            ''', (user_data[0],))
            backup_codes = await cursor.fetchall()
            
            # Audit log
            cursor = await db.execute('''
                SELECT action, details, timestamp
                FROM audit_log 
                WHERE user_id = ? 
                ORDER BY timestamp DESC LIMIT 20
            ''', (user_data[0],))
            audit = await cursor.fetchall()
            
            # CSV yaratish
            output = io.StringIO()
            writer = csv.writer(output)
            
            writer.writerow(['=== FOYDALANUVCHI MA\'LUMOTLARI ==='])
            writer.writerow(['Login:', user_data[1]])
            writer.writerow(['Account:', user_data[2]])
            writer.writerow(['Email:', user_data[3] or 'Mavjud emas'])
            writer.writerow(['Telefon:', user_data[4] or 'Mavjud emas'])
            writer.writerow(['2FA:', 'Yoqilgan' if user_data[5] else 'Ochirilgan'])
            writer.writerow(['Premium daraja:', user_data[8] or 'free'])
            writer.writerow(['Premium muddati:', user_data[9] or 'Mavjud emas'])
            writer.writerow(['Ro\'yxatdan o\'tgan:', user_data[6]])
            writer.writerow(['Oxirgi kirish:', user_data[7] or 'Hali kirilmagan'])
            writer.writerow([])
            
            writer.writerow(['=== KIRISH TARIXI (OXIRGI 50) ==='])
            writer.writerow(['Vaqt', 'Holat', 'Metod', 'IP'])
            for h in history:
                status = '✅' if h[1] else '❌'
                writer.writerow([h[0], status, h[2] or 'password', h[3] or 'Noma\'lum'])
            
            writer.writerow([])
            writer.writerow(['=== BACKUP KODLAR ==='])
            writer.writerow(['Kod', 'Holat', 'Yaratilgan', 'Ishlatilgan'])
            for bc in backup_codes:
                status = '✅ Ishlatilgan' if bc[1] else '⚡ Faol'
                writer.writerow([bc[0], status, bc[2] or 'Noma\'lum', bc[3] or 'Ishlatilmagan'])
            
            writer.writerow([])
            writer.writerow(['=== AUDIT LOG (OXIRGI 20) ==='])
            writer.writerow(['Harakat', 'Tafsilot', 'Vaqt'])
            for a in audit:
                writer.writerow([a[0], a[1] or '-', a[2]])
            
            await self.audit.log(db, user_data[0], "EXPORT_DATA", "Ma'lumotlar eksport qilindi")
            
            await callback.message.answer_document(
                types.BufferedInputFile(
                    output.getvalue().encode('utf-8-sig'),
                    filename=f"user_{login}_export_{datetime.now().strftime('%Y%m%d')}.csv"
                ),
                caption="✅ Ma'lumotlaringiz eksport qilindi!"
            )
        
        await callback.message.edit_text(
            "📥 Ma'lumotlar eksport qilindi!",
            reply_markup=self.create_main_menu(user_id)
        )
    
    # ==================== RESET PASSWORD METODLARI ====================
    
    async def reset_password_start(self, callback: CallbackQuery, state: FSMContext):
        """Parol tiklashni boshlash"""
        await callback.message.edit_text(
            "🔄 Parolni tiklash uchun loginingizni kiriting:",
            reply_markup=self.create_alphabet_keyboard()
        )
        await state.set_state(ResetPasswordState.waiting_for_login)
    
    async def reset_process_login(self, callback: CallbackQuery, state: FSMContext):
        """Login kiritish"""
        letter = callback.data.split("_")[1]
        data = await state.get_data()
        current_login = data.get("login", "") + letter
        
        await state.update_data(login=current_login)
        
        await callback.message.edit_text(
            f"🔄 Login: {current_login}\n\n"
            "Kiritishni davom eting yoki ✅ bosing:",
            reply_markup=self.create_alphabet_keyboard()
        )
    
    async def reset_login_submit(self, callback: CallbackQuery, state: FSMContext):
        """Loginni tasdiqlash"""
        data = await state.get_data()
        login = data.get("login", "")
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute(
                "SELECT id, email FROM users WHERE login = ?",
                (login,)
            )
            user = await cursor.fetchone()
            
            if not user:
                await callback.answer("Bunday login mavjud emas!", show_alert=True)
                return
            
            user_id, email = user
            
            if not email:
                await callback.answer(
                    "Email manzili yo'q! Admin bilan bog'lanishingiz kerak.",
                    show_alert=True
                )
                return
            
            reset_code = ''.join(random.choices(string.digits, k=6))
            expires = datetime.now() + timedelta(minutes=10)
            
            await db.execute(
                "UPDATE users SET reset_code = ?, reset_code_expires = ? WHERE id = ?",
                (reset_code, expires.isoformat(), user_id)
            )
            await db.commit()
            
            await callback.message.edit_text(
                f"📧 {email} manziliga 6 xonali kod yuborildi.\n"
                f"Kod: {reset_code}\n\n"
                f"Kodni kiriting:"
            )
        
        await state.set_state(ResetPasswordState.waiting_for_code)
    
    async def reset_process_code(self, message: Message, state: FSMContext):
        """Reset kodni tekshirish"""
        code = message.text
        data = await state.get_data()
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute('''
                SELECT id FROM users 
                WHERE login = ? AND reset_code = ? AND reset_code_expires > CURRENT_TIMESTAMP
            ''', (data['login'], code))
            
            user = await cursor.fetchone()
            
            if not user:
                await message.answer("❌ Noto'g'ri yoki muddati o'tgan kod. Qaytadan urinib ko'ring:")
                return
            
            await state.update_data(user_id=user[0])
        
        await message.answer(
            "🔐 Yangi 8 xonali parolni kiriting:",
            reply_markup=self.create_safe_keyboard()
        )
        await state.set_state(ResetPasswordState.waiting_for_new_password)
    
    async def reset_process_new_password(self, callback: CallbackQuery, state: FSMContext):
        """Yangi parol kiritish"""
        digit = callback.data.split("_")[1]
        data = await state.get_data()
        current_password = data.get("new_password", "") + digit
        
        if len(current_password) > 8:
            await callback.answer("Parol 8 xonali!", show_alert=True)
            return
        
        await state.update_data(new_password=current_password)
        
        strength, messages = self.security.check_password_strength(current_password)
        strength_emoji = ["🔴", "🟡", "🟢"][min(strength, 2)]
        
        messages_text = "\n".join(messages) if messages else ""
        
        await callback.message.edit_text(
            f"🔐 Yangi parol: {'*' * len(current_password)}\n"
            f"Kuchlilik: {strength_emoji} {strength}/3\n"
            f"{messages_text}\n\n"
            "Raqamlarni kiriting yoki ✅ bosing:",
            reply_markup=self.create_safe_keyboard(current_password)
        )
    
    async def reset_complete(self, callback: CallbackQuery, state: FSMContext):
        """Parol tiklashni yakunlash"""
        data = await state.get_data()
        new_password = data.get("new_password", "")
        
        if len(new_password) != 8:
            await callback.answer("Parol 8 xonali!", show_alert=True)
            return
        
        strength, _ = self.security.check_password_strength(new_password)
        if strength < Config.PASSWORD_MIN_STRENGTH:
            await callback.answer("Parol yetarlicha kuchli emas!", show_alert=True)
            return
        
        new_hash = self.security.hash_password(new_password)
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            await db.execute(
                "UPDATE users SET password_hash = ?, reset_code = NULL WHERE id = ?",
                (new_hash, data['user_id'])
            )
            await db.commit()
            await self.audit.log(db, data['user_id'], "PASSWORD_RESET", "Parol tiklandi")
        
        await callback.message.edit_text(
            "✅ Parol muvaffaqiyatli tiklandi! Endi tizimga kirishingiz mumkin.",
            reply_markup=self.create_main_menu()
        )
        await state.clear()
    
    # ==================== ADMIN METODLARI ====================
    
    async def admin_panel(self, callback: CallbackQuery):
        """Admin panel"""
        user_id = callback.from_user.id
        
        if user_id not in Config.ADMIN_IDS:
            await callback.answer("Ruxsat yo'q!", show_alert=True)
            return
        
        stats = await self.db.get_system_stats()
        
        text = (
            f"👑 **Admin panel**\n\n"
            f"📊 **Tizim statistikasi:**\n"
            f"👥 Jami foydalanuvchilar: {stats['total_users']}\n"
            f"⭐ Premium foydalanuvchilar: {stats['premium_users']}\n"
            f"🔒 2FA yoqilgan: {stats['two_factor_users']}\n"
            f"🚫 Bloklanganlar: {stats['blocked_users']}\n"
            f"📈 Bugungi kirishlar: {stats['today_logins']}\n"
            f"💰 Jami daromad: {stats['total_revenue']}$\n"
            f"💳 To'lovlar soni: {stats['total_payments']}"
        )
        
        buttons = [
            [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_users")],
            [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
            [InlineKeyboardButton(text="🔒 Bloklanganlar", callback_data="admin_blocked")],
            [InlineKeyboardButton(text="📝 Audit log", callback_data="admin_logs")],
            [InlineKeyboardButton(text="💾 Backup", callback_data="admin_backup")],
            [InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_main")]
        ]
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    
    async def admin_show_users(self, callback: CallbackQuery):
        """Foydalanuvchilar ro'yxati"""
        user_id = callback.from_user.id
        
        if user_id not in Config.ADMIN_IDS:
            return
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute('''
                SELECT login, account_name, email, two_factor_enabled, premium_tier,
                       created_at, last_login, login_attempts
                FROM users ORDER BY created_at DESC LIMIT 15
            ''')
            users = await cursor.fetchall()
            
            text = "👥 **Oxirgi 15 foydalanuvchi:**\n\n"
            
            for user in users:
                premium_icon = "⭐" if user[4] != 'free' else "🆓"
                text += f"{premium_icon} **{user[1]}** (@{user[0]})\n"
                text += f"   📧 {user[2] or 'Mavjud emas'}\n"
                text += f"   🔒 2FA: {'✅' if user[3] else '❌'}\n"
                text += f"   ⭐ Daraja: {user[4]}\n"
                text += f"   📅 {user[5][:10]}\n"
                text += f"   🔐 Urinishlar: {user[7]}\n\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu_admin")]
                ])
            )
    
    async def admin_show_stats(self, callback: CallbackQuery):
        """Admin statistika"""
        user_id = callback.from_user.id
        
        if user_id not in Config.ADMIN_IDS:
            return
        
        stats = await self.db.get_system_stats()
        
        # Qo'shimcha statistika
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM payments WHERE status = 'completed' AND created_at > datetime('now', '-30 days')")
            monthly_payments = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT SUM(amount) FROM payments WHERE status = 'completed' AND created_at > datetime('now', '-30 days')")
            monthly_revenue = (await cursor.fetchone())[0] or 0
            
            cursor = await db.execute("SELECT COUNT(*) FROM login_history WHERE login_time > datetime('now', '-7 days')")
            weekly_logins = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE created_at > datetime('now', '-7 days')")
            weekly_new_users = (await cursor.fetchone())[0]
        
        active_sessions = len(self.sessions)
        
        text = (
            f"📊 **Admin statistika**\n\n"
            f"👥 Jami foydalanuvchilar: {stats['total_users']}\n"
            f"🆕 Yangi (7 kun): {weekly_new_users}\n"
            f"⭐ Premium: {stats['premium_users']} ({stats['premium_users']/stats['total_users']*100:.1f}%)\n"
            f"🔒 2FA: {stats['two_factor_users']}\n"
            f"🟢 Hozir aktiv: {active_sessions}\n\n"
            f"**Login statistikasi:**\n"
            f"📈 Bugungi kirishlar: {stats['today_logins']}\n"
            f"📊 Haftalik kirishlar: {weekly_logins}\n\n"
            f"**Moliyaviy statistika:**\n"
            f"💰 Jami daromad: {stats['total_revenue']:.2f}$\n"
            f"📅 Oylik daromad: {monthly_revenue:.2f}$\n"
            f"💳 Jami to'lovlar: {stats['total_payments']}\n"
            f"📊 Oylik to'lovlar: {monthly_payments}\n\n"
            f"**Xavfsizlik:**\n"
            f"🚫 Bloklangan hisoblar: {stats['blocked_users']}"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📥 Eksport", callback_data="admin_export_stats")],
                [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu_admin")]
            ])
        )
    
    async def admin_show_blocked(self, callback: CallbackQuery):
        """Bloklangan foydalanuvchilar"""
        user_id = callback.from_user.id
        
        if user_id not in Config.ADMIN_IDS:
            return
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute('''
                SELECT login, account_name, login_attempts, locked_until
                FROM users WHERE locked_until IS NOT NULL
            ''')
            blocked = await cursor.fetchall()
            
            if not blocked:
                await callback.message.edit_text(
                    "✅ Bloklangan foydalanuvchilar yo'q",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu_admin")]
                    ])
                )
                return
            
            text = "🔒 **Bloklangan foydalanuvchilar:**\n\n"
            
            for user in blocked:
                locked_until = parser.parse(user[3])
                remaining = (locked_until - datetime.now()).seconds // 60
                text += f"🔹 {user[1]} (@{user[0]})\n"
                text += f"   Urinishlar: {user[2]}\n"
                text += f"   Bloklangan: {remaining} daqiqa qoldi\n\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔓 Blokni ochish", callback_data="admin_unlock_all")],
                    [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu_admin")]
                ])
            )
    
    async def admin_show_logs(self, callback: CallbackQuery):
        """Audit loglarni ko'rsatish"""
        user_id = callback.from_user.id
        
        if user_id not in Config.ADMIN_IDS:
            return
        
        async with aiosqlite.connect(Config.DB_FILE) as db:
            cursor = await db.execute('''
                SELECT user_id, action, details, timestamp, ip
                FROM audit_log ORDER BY timestamp DESC LIMIT 30
            ''')
            logs = await cursor.fetchall()
            
            text = "📝 **Oxirgi 30 log:**\n\n"
            
            for log in logs:
                text += f"[{log[3][:19]}] {log[1]}\n"
                if log[2]:
                    text += f"   📝 {log[2][:50]}\n"
                text += f"   👤 ID: {log[0]}\n"
                text += f"   🌐 IP: {log[4]}\n\n"
            
            # Pagination uchun
            if len(text) > 3500:
                text = text[:3500] + "...\n\n(Ko'proq ma'lumot uchun eksport qiling)"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📥 Eksport", callback_data="admin_export_logs")],
                    [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu_admin")]
                ])
            )
    
    async def admin_backup_menu(self, callback: CallbackQuery):
        """Backup menyusi"""
        user_id = callback.from_user.id
        
        if user_id not in Config.ADMIN_IDS:
            return
        
        backups = await self.backup_service.list_backups()
        
        text = "💾 **Backup boshqaruvi**\n\n"
        
        if backups:
            text += "**Mavjud backuplar:**\n"
            for i, backup in enumerate(backups[:5], 1):
                text += f"{i}. {backup['name']} - {backup['size']} ({backup['created'].strftime('%Y-%m-%d %H:%M')})\n"
        else:
            text += "Backuplar mavjud emas.\n"
        
        buttons = [
            [InlineKeyboardButton(text="🆕 Yangi backup yaratish", callback_data="admin_create_backup")],
            [InlineKeyboardButton(text="📋 Backuplar ro'yxati", callback_data="admin_list_backups")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu_admin")]
        ]
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    
    async def admin_create_backup(self, callback: CallbackQuery):
        """Yangi backup yaratish"""
        user_id = callback.from_user.id
        
        if user_id not in Config.ADMIN_IDS:
            return
        
        await callback.message.edit_text("🔄 Backup yaratilmoqda...")
        
        backup_file = await self.backup_service.create_backup()
        
        await callback.message.edit_text(
            f"✅ Backup muvaffaqiyatli yaratildi!\n\n"
            f"📁 Fayl: {backup_file}\n"
            f"📏 Hajmi: {os.path.getsize(backup_file) / (1024*1024):.2f} MB",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📥 Yuklab olish", callback_data=f"admin_download_backup_{backup_file}")],
                [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_backup")]
            ])
        )
    
    async def admin_list_backups(self, callback: CallbackQuery):
        """Backuplar ro'yxati"""
        user_id = callback.from_user.id
        
        if user_id not in Config.ADMIN_IDS:
            return
        
        backups = await self.backup_service.list_backups()
        
        if not backups:
            await callback.message.edit_text(
                "❌ Backuplar mavjud emas!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_backup")]
                ])
            )
            return
        
        text = "📋 **Backuplar ro'yxati:**\n\n"
        buttons = []
        
        for i, backup in enumerate(backups[:10], 1):
            text += f"{i}. {backup['name']}\n"
            text += f"   📅 {backup['created'].strftime('%Y-%m-%d %H:%M')}\n"
            text += f"   📏 {backup['size']}\n\n"
            buttons.append([InlineKeyboardButton(
                text=f"📥 {backup['name'][:20]}", 
                callback_data=f"admin_download_backup_{backup['name']}"
            )])
        
        buttons.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_backup")])
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    
    async def admin_broadcast_start(self, callback: CallbackQuery, state: FSMContext):
        """Broadcast boshlash"""
        user_id = callback.from_user.id
        
        if user_id not in Config.ADMIN_IDS:
            return
        
        await callback.message.edit_text(
            "📢 **Broadcast xabar yuborish**\n\n"
            "Yubormoqchi bo'lgan xabaringizni yozing:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Bekor qilish", callback_data="menu_admin")]
            ])
        )
        await state.set_state(AdminState.waiting_for_broadcast)
    
    async def admin_broadcast_process(self, message: Message, state: FSMContext):
        """Broadcast xabarni yuborish"""
        text = message.text
        
        await message.answer(
            f"📢 **Broadcast xabar**\n\n"
            f"{text}\n\n"
            f"Bu xabarni barcha foydalanuvchilarga yuborishni tasdiqlaysizmi?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Ha, yuborish", callback_data="admin_broadcast_confirm")],
                [InlineKeyboardButton(text="❌ Yo'q, bekor qilish", callback_data="menu_admin")]
            ])
        )
        await state.update_data(broadcast_text=text)
    
    @self.dp.callback_query(F.data == "admin_broadcast_confirm")
    async def admin_broadcast_confirm(self, callback: CallbackQuery, state: FSMContext):
        """Broadcastni tasdiqlash"""
        data = await state.get_data()
        text = data.get('broadcast_text', '')
        
        await callback.message.edit_text("📢 Xabar yuborilmoqda...")
        
        await self.channel.broadcast(text)
        
        await callback.message.edit_text(
            "✅ Broadcast muvaffaqiyatli yakunlandi!",
            reply_markup=self.create_main_menu(callback.from_user.id)
        )
        await state.clear()
    
    # ==================== UMUMIY METODLAR ====================
    
    async def show_statistics(self, callback: CallbackQuery):
        """Tizim statistikasini ko'rsatish"""
        user_id = callback.from_user.id
        
        if user_id not in self.sessions:
            await callback.answer("Avval tizimga kiring!", show_alert=True)
            return
        
        stats = await self.db.get_system_stats()
        
        text = (
            f"📊 **Tizim statistikasi**\n\n"
            f"👥 Umumiy foydalanuvchilar: {stats['total_users']}\n"
            f"⭐ Premium foydalanuvchilar: {stats['premium_users']}\n"
            f"🔒 2FA yoqilgan: {stats['two_factor_users']}\n"
            f"🟢 Hozir aktiv: {len(self.sessions)}\n"
            f"📈 Bugungi kirishlar: {stats['today_logins']}"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=self.create_main_menu(user_id)
        )
    
    async def settings_menu(self, callback: CallbackQuery):
        """Sozlamalar menyusi"""
        user_id = callback.from_user.id
        
        if user_id not in self.sessions:
            await callback.answer("Avval tizimga kiring!", show_alert=True)
            return
        
        text = (
            "⚙️ **Sozlamalar**\n\n"
            "Bu yerda tizim sozlamalarini o'zgartirishingiz mumkin."
        )
        
        buttons = [
            [InlineKeyboardButton(text="🌐 Tilni o'zgartirish", callback_data="menu_language")],
            [InlineKeyboardButton(text="🔔 Bildirishnomalar", callback_data="settings_notifications")],
            [InlineKeyboardButton(text="🎨 Mavzu", callback_data="settings_theme")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu_profile")]
        ]
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    
    async def logout(self, callback: CallbackQuery):
        """Tizimdan chiqish"""
        user_id = callback.from_user.id
        
        if user_id in self.sessions:
            async with aiosqlite.connect(Config.DB_FILE) as db:
                cursor = await db.execute(
                    "SELECT id FROM users WHERE login = ?",
                    (self.sessions[user_id].login,)
                )
                user_id_db = await cursor.fetchone()
                if user_id_db:
                    await self.audit.log(db, user_id_db[0], "LOGOUT", "Tizimdan chiqish")
                    
                    # Sessiyani o'chirish
                    await db.execute(
                        "UPDATE sessions SET active = 0 WHERE session_id = ?",
                        (self.sessions[user_id].session_id,)
                    )
                    await db.commit()
            
            del self.sessions[user_id]
        
        await callback.message.edit_text(
            "👋 Tizimdan chiqdingiz. Qaytganingizda xush kelibsiz!",
            reply_markup=self.create_main_menu()
        )
    
    async def cancel_operation(self, callback: CallbackQuery, state: FSMContext):
        """Amaliyotni bekor qilish"""
        await state.clear()
        user_id = callback.from_user.id
        
        await callback.message.edit_text(
            "❌ Amaliyot bekor qilindi.",
            reply_markup=self.create_main_menu(user_id if user_id in self.sessions else None)
        )
    
    async def handle_backspace(self, callback: CallbackQuery, state: FSMContext):
        """Backspace handler"""
        current_state = await state.get_state()
        data = await state.get_data()
        
        if current_state in [
            RegisterState.waiting_for_login.state,
            RegisterState.waiting_for_account_name.state,
            LoginState.waiting_for_login.state,
            ResetPasswordState.waiting_for_login.state,
            ProfileState.waiting_for_new_account.state
        ]:
            field_map = {
                RegisterState.waiting_for_login.state: "login",
                RegisterState.waiting_for_account_name.state: "account",
                LoginState.waiting_for_login.state: "login",
                ResetPasswordState.waiting_for_login.state: "login",
                ProfileState.waiting_for_new_account.state: "new_account"
            }
            
            field = field_map.get(current_state)
            if field:
                current = data.get(field, "")
                if current:
                    new_value = current[:-1]
                    await state.update_data({field: new_value})
                    
                    await callback.message.edit_text(
                        f"📝 {new_value}\n\n"
                        "Kiritishni davom eting yoki ✅ bosing:",
                        reply_markup=self.create_alphabet_keyboard()
                    )
    
    # ==================== BACKGROUND TASKS ====================
    
    async def cleanup_sessions(self):
        """Eski sessiyalarni tozalash"""
        while True:
            await asyncio.sleep(300)  # 5 daqiqa
            
            current_time = datetime.now()
            expired = []
            
            for user_id, session in self.sessions.items():
                # Premium darajaga qarab timeout
                timeout = PREMIUM_FEATURES.get(
                    session.premium_tier, 
                    PREMIUM_FEATURES['free']
                )['session_timeout']
                
                if (current_time - session.last_activity).seconds > timeout:
                    expired.append(user_id)
            
            for user_id in expired:
                del self.sessions[user_id]
                
                try:
                    await self.bot.send_message(
                        user_id,
                        "⏰ Sessiyangiz tugadi. Qaytadan kiring.",
                        reply_markup=self.create_main_menu()
                    )
                except:
                    pass
    
    async def auto_backup(self):
        """Avtomatik backup"""
        while True:
            await asyncio.sleep(24 * 60 * 60)  # Har kuni
            try:
                backup_file = await self.backup_service.create_backup()
                print(f"✅ Avtomatik backup yaratildi: {backup_file}")
                
                # Adminlarga xabar yuborish
                for admin_id in Config.ADMIN_IDS:
                    try:
                        await self.bot.send_message(
                            admin_id,
                            f"✅ Avtomatik backup yaratildi:\n{backup_file}"
                        )
                    except:
                        pass
            except Exception as e:
                print(f"❌ Avtomatik backupda xato: {e}")
    
    async def run(self):
        """Botni ishga tushirish"""
        # Ma'lumotlar bazasini yaratish
        await self.db.init()
        
        # Background vazifalarni ishga tushirish
        asyncio.create_task(self.cleanup_sessions())
        asyncio.create_task(self.auto_backup())
        asyncio.create_task(self.monitoring.check_system_health())
        
        # Logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f"{Config.LOG_DIR}/bot.log"),
                logging.StreamHandler()
            ]
        )
        
        print("=" * 50)
        print("🚀 PERFECT SECURITY SYSTEM v3.0")
        print("=" * 50)
        print(f"📱 Microsoft Authenticator: {Config.TOTP_INTERVAL} sekund")
        print(f"👑 Adminlar: {Config.ADMIN_IDS}")
        print(f"💾 Backup papkasi: {Config.BACKUP_DIR}")
        print(f"📁 Log papkasi: {Config.LOG_DIR}")
        print("=" * 50)
        print("⏰ Bot ishga tushdi!")
        print("=" * 50)
        
        # Kanalga xabar yuborish
        try:
            await self.bot.send_message(
                Config.CHANNEL_ID,
                "🚀 **Perfect Security System v3.0 ishga tushdi!**\n\n"
                "Barcha tizimlar normal ishlayapti."
            )
        except:
            pass
        
        await self.dp.start_polling(self.bot)

# ==================== ASOSIY FUNKSIYA ====================

async def main():
    """Asosiy funksiya"""
    bot = PerfectSecurityBot(Config.BOT_TOKEN)
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot to'xtatildi")
    except Exception as e:
        print(f"❌ Xatolik: {e}")
        logging.error(f"Kutilmagan xatolik: {e}", exc_info=True)

# pip install aiogram==3.13.0 aiosqlite pyotp qrcode pillow python-dateutil matplotlib seaborn numpy requests psutil