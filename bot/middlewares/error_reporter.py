import io
import traceback
import asyncio
from datetime import datetime
from aiogram import BaseMiddleware, types, Bot
from aiogram.exceptions import TelegramBadRequest
import logging
from typing import List  # <-- qo'shildi

logger = logging.getLogger(__name__)

class ErrorReporterMiddleware(BaseMiddleware):
    def __init__(self, bot: Bot, admin_ids: List[int], max_msg_len: int = 3500):  # list[int] -> List[int]
        self.bot = bot
        self.admin_ids = admin_ids
        self.max_msg_len = max_msg_len
        self._lock = asyncio.Lock()
        self._last_sent = 0.0

    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as exc:
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            tb_safe = tb.replace(self.bot.token, "[TOKEN]")
            ctx_lines = [f"🕒 UTC: {datetime.utcnow().isoformat()}"]
            if isinstance(event, types.Message):
                ctx_lines.append(f"👤 User: {event.from_user.full_name} (@{event.from_user.username}) [{event.from_user.id}]")
                ctx_lines.append(f"💬 Text: {event.text or event.caption or '—'}")
            elif isinstance(event, types.CallbackQuery):
                ctx_lines.append(f"👤 User: {event.from_user.full_name} [{event.from_user.id}]")
                ctx_lines.append(f"🔘 Callback: {event.data}")
            message_text = "🚨 *Bot xatosi!*\n\n" + "\n".join(ctx_lines) + f"\n\n*Xato:* `{exc}`"

            try:
                async with self._lock:
                    now = asyncio.get_event_loop().time()
                    if now - self._last_sent < 0.8:
                        await asyncio.sleep(0.8)
                    self._last_sent = now

                    if len(tb_safe) > self.max_msg_len:
                        file_obj = io.BytesIO(tb_safe.encode("utf-8"))
                        file_obj.name = "traceback.txt"
                        for admin_id in self.admin_ids:
                            await self.bot.send_message(admin_id, message_text, parse_mode="Markdown")
                            await self.bot.send_document(admin_id, file_obj, caption="📄 To'liq traceback")
                    else:
                        full = message_text + "\n\n```" + tb_safe[:self.max_msg_len] + "```"
                        for admin_id in self.admin_ids:
                            await self.bot.send_message(admin_id, full, parse_mode="Markdown")
            except TelegramBadRequest:
                for admin_id in self.admin_ids:
                    await self.bot.send_message(admin_id, f"Xato: {exc}\n\n{tb_safe[:1500]}")
            except Exception:
                pass
            return None