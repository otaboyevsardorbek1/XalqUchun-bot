import io
import traceback
import asyncio
from datetime import datetime
from aiogram import BaseMiddleware, types, Bot
from aiogram.exceptions import TelegramBadRequest
import time
import sys
import logging
from aiogram import BaseMiddleware, Bot
from aiogram.dispatcher.event.bases import UNHANDLED
from typing import Callable, Awaitable, Any, Dict
LOG_FILE = "bot.log"
# ========logging=======
# ✅ Log sozlamalari
def loggers(log_name):
    logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - (%(filename)s:%(lineno)d) - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),  # Faylga yozish
        logging.StreamHandler(sys.stdout)  # Konsolga chiqarish
    ])
    logger = logging.getLogger(log_name)
    return logger
midwer_log=loggers(log_name="Midlwers")
class ErrorReporterMiddleware(BaseMiddleware):
    """
    Har qanday handlerda xato yuz bersa — shu middleware uni tutadi va admin(lar)ga yuboradi.
    """

    def __init__(self, bot: Bot, admin_ids: list[int], *, max_msg_len: int = 3500):
        super().__init__()
        self.bot = bot
        self.admin_ids = admin_ids
        self.max_msg_len = max_msg_len
        self._lock = asyncio.Lock()
        self._last_sent = 0.0  # oddiy rate limit uchun

    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as exc:
            # traceback olish
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            tb_safe = tb.replace(self.bot.token, "[TOKEN]")

            # update konteksti
            ctx_lines = [f"🕒 UTC vaqt: {datetime.utcnow().isoformat()}"]
            if isinstance(event, types.Message):
                ctx_lines.append(f"👤 Foydalanuvchi: {event.from_user.full_name} (@{event.from_user.username}) [{event.from_user.id}]")
                ctx_lines.append(f"💬 Matn: {event.text or event.caption or '—'}")
                ctx_lines.append(f"💭 Chat: {event.chat.id} ({event.chat.type})")
            else:
                ctx_lines.append(f"🧩 Event turi: {type(event).__name__}")

            # xabar tayyorlash
            message_text = (
                "🚨 *Botda xato yuz berdi!*\n\n"
                + "\n".join(ctx_lines)
                + f"\n\n*Xato turi:* `{type(exc).__name__}`\n"
                + f"*Tafsilot:* `{exc}`"
            )

            try:
                async with self._lock:
                    now_ts = asyncio.get_event_loop().time()
                    if now_ts - self._last_sent < 0.8:
                        await asyncio.sleep(0.8)
                    self._last_sent = asyncio.get_event_loop().time()

                    # traceback uzun bo‘lsa, fayl qilib yubor
                    if len(tb_safe) > self.max_msg_len:
                        file_obj = io.BytesIO(tb_safe.encode("utf-8"))
                        file_obj.name = "traceback.txt"
                        for admin_id in self.admin_ids:
                            await self.bot.send_message(admin_id, message_text, parse_mode="Markdown")
                            await self.bot.send_document(admin_id, file_obj, caption="📄 To‘liq traceback fayl")
                            midwer_log.info(f"Adminga tizimdagi hatolar jo`natildi.!\nAdmin_id: {admin_id}")
                    else:
                        text_full = message_text + "\n\n```" + tb_safe[: self.max_msg_len] + "```"
                        for admin_id in self.admin_ids:
                            await self.bot.send_message(admin_id, text_full, parse_mode="Markdown")
                            midwer_log.info(f"Adminga tizimdagi hatolar jo`natildi.!\nAdmin_id: {admin_id}")
            except TelegramBadRequest:
                # agar markdown formati buzilgan bo‘lsa — oddiy matn yubor
                for admin_id in self.admin_ids:
                    await self.bot.send_message(admin_id, f"Xato: {exc}\n\n{tb_safe[:1500]}")
            except Exception:
                pass  # xatoni qayta ko‘tarmaslik kerak

            return None  # bot ishini davom ettiradi


# start stop midwer
class StartStopNotifyMiddleware(BaseMiddleware):
    """
    Bot ishga tushganda yoki to‘xtaganda admin(lar)ga avtomatik xabar yuboruvchi middleware.
    """

    def __init__(self, bot: Bot, admin_ids: list[int]):
        super().__init__()
        self.bot = bot
        self.admin_ids = admin_ids

    async def startup(self):
        """Bot ishga tushganda adminlarga xabar yuborish."""
        date_now = time.strftime("%Y-%m-%d", time.localtime())
        time_now = time.strftime("%H:%M:%S", time.localtime())

        midwer_log.info("Adminga bot ishga tushganini bildirish boshlandi")
        for admin in self.admin_ids:
            try:
                await self.bot.send_message(
                    admin,
                    text=(
                        f"✅ *Bot ishga tushdi!* ✅\n"
                        f"📅 Sana: {date_now}\n"
                        f"⏰ Vaqt: {time_now}\n"
                    ),
                    parse_mode="Markdown",
                    disable_notification=True
                )
            except Exception as e:
                midwer_log.error(f"Admin {admin} ga start xabari yuborilmadi: {e}")

    async def shutdown(self):
        """Bot to‘xtaganda adminlarga xabar yuborish."""
        date_now = time.strftime("%Y-%m-%d", time.localtime())
        time_now = time.strftime("%H:%M:%S", time.localtime())

        midwer_log.info("Adminga bot to‘xtagani haqida xabar yuborish")
        for admin in self.admin_ids:
            try:
                await self.bot.send_message(
                    admin,
                    text=(
                        "❌ *Bot to‘xtadi!* ❌\n"
                        f"📅 Sana: {date_now}\n"
                        f"⏰ Vaqt: {time_now}\n"
                        "Sababni /log buyrug‘i orqali tekshiring."
                    ),
                    parse_mode="Markdown",
                    disable_notification=True
                )
            except Exception as e:
                midwer_log.error(f"Admin {admin} ga stop xabari yuborilmadi: {e}")

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        """
        Bu middleware eventlarga aralashmaydi (faqat startup/shutdown).
        """
        return await handler(event, data)