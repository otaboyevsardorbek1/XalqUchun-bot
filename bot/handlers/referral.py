import io
import csv
import tempfile
import os
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from sqlalchemy import select, func
from datetime import datetime

from bot.db.database import AsyncSessionLocal
from bot.db.models import User, Transaction
from bot.utils.referral import (
    get_children, count_downline, build_tree_text,
    create_withdraw_request, list_user_transactions, list_pending_withdrawals,
    process_withdraw, manual_payout, get_user_by_tid
)
from bot.data import ALL_OWNER_IDS, MAX_TREE_DEPTH, OWNER_ID

# Logger sozlash
logger = logging.getLogger(__name__)

try:
    from graphviz import Digraph
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False

router = Router()

# ==================== YORDAMCHI FUNKSIYALAR ====================

def safe_message(text: str) -> str:
    """Xabarlarni HTML dan tozalaydi va xavfsiz qiladi"""
    # < va > belgilarini almashtirish
    return text.replace('<', '&lt;').replace('>', '&gt;')

# ==================== REFERAL DARAXT ====================

@router.message(Command("tree"))
async def cmd_tree(message: types.Message):
    """Referal daraxtini matn ko'rinishida ko'rsatish"""
    try:
        tree = await build_tree_text(message.from_user.id, max_depth=MAX_TREE_DEPTH)
        if not tree:
            await message.reply("📭 Siz hali hech kimni taklif qilmagansiz.")
            return
        
        # HTML teglaridan xoli matn
        await message.reply(
            f"🌳 <b>Sizning referal daraxtingiz:</b>\n\n<pre>{safe_message(tree)}</pre>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Tree xatosi: {e}")
        await message.reply("❌ Daraxtni yaratishda xatolik yuz berdi.")

# ==================== REFERAL DARAXT RASM ====================

ROLE_COLOR = {
    "owner": "red",
    "admin": "orange",
    "manager": "gold",
    "worker": "green",
    "diller": "blue",
    "dastafka": "purple",
    "guest": "gray"
}

@router.message(Command("treeimg"))
async def cmd_treeimg(message: types.Message):
    """Referal daraxtini rasm ko'rinishida ko'rsatish"""
    if not GRAPHVIZ_AVAILABLE:
        await message.reply(
            "⚠️ Graphviz o'rnatilmagan.\n"
            "O'rnatish: <code>pip install graphviz</code> va sistema graphviz",
            parse_mode="HTML"
        )
        return
    
    try:
        root = message.from_user.id
        nodes = {}
        edges = []
        queue = [(root, 0)]
        visited = set()
        
        async with AsyncSessionLocal() as session:
            while queue:
                cur_tid, level = queue.pop(0)
                if cur_tid in visited:
                    continue
                visited.add(cur_tid)
                
                res = await session.execute(
                    select(User).where(User.telegram_id == cur_tid)
                )
                cur_user = res.scalar_one_or_none()
                
                if cur_user:
                    label = (f"{cur_user.full_name or cur_user.username or 'ID:'+str(cur_tid)}\\n"
                            f"ID:{cur_tid}\\n"
                            f"Bal:{cur_user.balance:.2f}\\n"
                            f"Ref:{cur_user.referrals_count}")
                    color = ROLE_COLOR.get(cur_user.role, "lightgray")
                else:
                    label = f"ID:{cur_tid}"
                    color = "lightgray"
                
                nodes[cur_tid] = {"label": label, "color": color}
                
                if level < MAX_TREE_DEPTH:
                    children = await session.execute(
                        select(User.telegram_id).where(User.referrer_telegram_id == cur_tid)
                    )
                    for child_tid in children.scalars().all():
                        edges.append((cur_tid, child_tid))
                        queue.append((child_tid, level + 1))
        
        # Graphviz diagrammasini yaratish
        dot = Digraph(format='png')
        dot.attr('node', shape='record', fontsize='10')
        
        for tid, meta in nodes.items():
            dot.node(str(tid), label=meta["label"], style="filled", fillcolor=meta["color"])
        
        for a, b in edges:
            dot.edge(str(a), str(b))
        
        # Rasmni saqlash va yuborish
        tmpdir = tempfile.mkdtemp()
        out_path = os.path.join(tmpdir, f"tree_{root}")
        png_path = dot.render(filename=out_path, cleanup=True)
        
        await message.reply_photo(
            photo=FSInputFile(png_path),
            caption="🌳 <b>Referal daraxtingiz</b>",
            parse_mode="HTML"
        )
        
        # Vaqtinchalik faylni tozalash
        try:
            os.unlink(png_path)
            os.rmdir(tmpdir)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Treeimg xatosi: {e}")
        await message.reply("❌ Rasm yaratishda xatolik yuz berdi.")

# ==================== AVLODLAR SONI ====================

@router.message(Command("downline"))
async def cmd_downline(message: types.Message):
    """Barcha avlodlar sonini ko'rsatish"""
    try:
        total = await count_downline(message.from_user.id)
        await message.reply(f"👥 <b>Barcha avlodlaringiz soni:</b> {total}", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Downline xatosi: {e}")
        await message.reply("❌ Avlodlar sonini hisoblashda xatolik yuz berdi.")

# ==================== FOYDALANUVCHI MA'LUMOTLARI ====================

@router.message(Command("me"))
async def cmd_me(message: types.Message):
    """Foydalanuvchi ma'lumotlarini ko'rsatish"""
    try:
        async with AsyncSessionLocal() as session:
            user = await get_user_by_tid(session, message.from_user.id)
        
        if not user:
            await message.reply("❌ Siz roʻyxatdan oʻtmagan. /start ni bosing.")
            return
        
        # Bloklanganlik holati
        blocked_status = "✅" if user.blocked else "❌"
        
        await message.reply(
            f"👤 <b>Profilingiz</b>\n\n"
            f"📝 Ism: {safe_message(user.full_name or '—')}\n"
            f"🆔 ID: <code>{user.telegram_id}</code>\n"
            f"👤 Username: @{safe_message(user.username or '—')}\n"
            f"🎭 Rol: <b>{user.role}</b>\n"
            f"👥 Takliflar: {user.referrals_count}\n"
            f"💰 Balans: <b>{user.balance:.2f} soʻm</b>\n"
            f"🔒 Bloklangan: {blocked_status}",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Me xatosi: {e}")
        await message.reply("❌ Ma'lumotlarni olishda xatolik yuz berdi.")

# ==================== BALANS ====================

@router.message(Command("balance"))
async def cmd_balance(message: types.Message):
    """Balansni ko'rsatish"""
    try:
        async with AsyncSessionLocal() as session:
            user = await get_user_by_tid(session, message.from_user.id)
        
        bal = user.balance if user else 0.0
        
        await message.reply(
            f"💰 <b>Balansingiz:</b> {bal:.2f} soʻm",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Balance xatosi: {e}")
        await message.reply("❌ Balansni olishda xatolik yuz berdi.")

# ==================== PUL YECHISH ====================

@router.message(Command("withdraw"))
async def cmd_withdraw(message: types.Message):
    """Pul yechish so'rovini yuborish"""
    try:
        parts = message.text.split()
        
        # Argumentlar sonini tekshirish
        if len(parts) < 2:
            await message.reply(
                "❌ <b>Foydalanish:</b> /withdraw <summa>\n\n"
                "Misol: /withdraw 50000",
                parse_mode="HTML"
            )
            return
        
        # Summani tekshirish
        try:
            amount = float(parts[1])
        except ValueError:
            await message.reply(
                "❌ <b>Xato:</b> Summa notoʻgʻri formatda.\n\n"
                "Misol: /withdraw 50000",
                parse_mode="HTML"
            )
            return
        
        if amount <= 0:
            await message.reply(
                "❌ <b>Xato:</b> Summa musbat boʻlishi kerak.",
                parse_mode="HTML"
            )
            return
        
        # Foydalanuvchini tekshirish
        async with AsyncSessionLocal() as session:
            user = await get_user_by_tid(session, message.from_user.id)
            
            if not user:
                await message.reply(
                    "❌ Siz roʻyxatdan oʻtmagan. /start ni bosing.",
                    parse_mode="HTML"
                )
                return
            
            if (user.balance or 0.0) < amount:
                await message.reply(
                    f"❌ <b>Xato:</b> Balansingizda yetarli mablagʻ yoʻq.\n"
                    f"💰 Joriy balans: <b>{user.balance:.2f} soʻm</b>",
                    parse_mode="HTML"
                )
                return
        
        # So'rovni yaratish
        tx = await create_withdraw_request(message.from_user.id, amount)
        
        # Foydalanuvchiga xabar
        await message.reply(
            f"✅ <b>Soʻrov qabul qilindi!</b>\n\n"
            f"📝 TX ID: <code>{tx.id}</code>\n"
            f"💰 Summa: <b>{amount:.2f} soʻm</b>\n"
            f"⏳ Holat: <b>Kutilmoqda</b>\n\n"
            f"Admin tasdiqlashini kuting.",
            parse_mode="HTML"
        )
        
        # Adminlarga xabar
        for admin in ALL_OWNER_IDS:
            try:
                await message.bot.send_message(
                    admin,
                    f"💸 <b>Yangi withdraw soʻrovi</b>\n\n"
                    f"👤 User: {safe_message(message.from_user.full_name)} (ID: <code>{message.from_user.id}</code>)\n"
                    f"💰 Summa: <b>{amount:.2f} soʻm</b>\n"
                    f"📝 TX ID: <code>{tx.id}</code>\n\n"
                    f"/confirm_withdraw {tx.id} - ✅ Tasdiqlash\n"
                    f"/decline_withdraw {tx.id} - ❌ Rad etish",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Admin {admin} ga xabar yuborilmadi: {e}")
                
    except Exception as e:
        logger.error(f"Withdraw xatosi: {e}")
        await message.reply("❌ So'rovni yuborishda xatolik yuz berdi.")

# ==================== TRANZAKSIYALAR ====================

@router.message(Command("transactions"))
async def cmd_transactions(message: types.Message):
    """Tranzaksiyalar tarixini ko'rsatish"""
    try:
        txs = await list_user_transactions(message.from_user.id)
        
        if not txs:
            await message.reply("📭 <b>Tranzaksiyalar topilmadi.</b>", parse_mode="HTML")
            return
        
        lines = ["🧾 <b>Sizning tranzaksiyalaringiz:</b>\n"]
        
        for t in txs:
            status_emoji = {
                "approved": "✅",
                "pending": "⏳",
                "declined": "❌"
            }.get(t.status, "❓")
            
            lines.append(
                f"{status_emoji} <code>TX:{t.id}</code> | {t.type} | "
                f"<b>{t.amount:.2f} soʻm</b> | {t.status} | "
                f"{t.created_at.strftime('%d.%m.%Y %H:%M')}"
            )
        
        await message.reply("\n".join(lines), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Transactions xatosi: {e}")
        await message.reply("❌ Tranzaksiyalarni olishda xatolik yuz berdi.")

# ==================== ADMIN: WITHDRAW SO'ROVLARI ====================

@router.message(Command("withdraw_requests"))
async def cmd_withdraw_requests(message: types.Message):
    """Kutilayotgan withdraw so'rovlarini ko'rsatish (faqat admin)"""
    if message.from_user.id not in ALL_OWNER_IDS:
        return
    
    try:
        pending = await list_pending_withdrawals()
        
        if not pending:
            await message.reply("📭 <b>Kutilayotgan soʻrovlar yoʻq.</b>", parse_mode="HTML")
            return
        
        lines = ["🔔 <b>Kutilayotgan withdraw soʻrovlari:</b>\n"]
        
        for t in pending:
            lines.append(
                f"📝 <code>TX:{t.id}</code> | 👤 User: <code>{t.user_telegram_id}</code> | "
                f"💰 <b>{t.amount:.2f} soʻm</b> | 🕒 {t.created_at.strftime('%d.%m.%Y %H:%M')}"
            )
        
        await message.reply("\n".join(lines), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Withdraw_requests xatosi: {e}")
        await message.reply("❌ So'rovlarni olishda xatolik yuz berdi.")

# ==================== ADMIN: WITHDRAW TASDIQLASH ====================

@router.message(Command("confirm_withdraw"))
async def cmd_confirm_withdraw(message: types.Message):
    """Withdraw so'rovini tasdiqlash (faqat admin)"""
    if message.from_user.id not in ALL_OWNER_IDS:
        return
    
    try:
        parts = message.text.split(maxsplit=2)
        
        if len(parts) < 2 or not parts[1].isdigit():
            await message.reply(
                "❌ <b>Foydalanish:</b> /confirm_withdraw <tx_id> [izoh]",
                parse_mode="HTML"
            )
            return
        
        tx_id = int(parts[1])
        note = parts[2] if len(parts) > 2 else None
        
        res = await process_withdraw(tx_id, message.from_user.id, approve=True, note=note)
        
        if res == "not_found":
            await message.reply("❌ <b>TX topilmadi.</b>", parse_mode="HTML")
        elif res == "already_processed":
            await message.reply("⚠️ <b>TX allaqachon qayta ishlangan.</b>", parse_mode="HTML")
        elif res == "insufficient_balance":
            await message.reply("⚠️ <b>Foydalanuvchi balansida yetarli mablagʻ yoʻq.</b>", parse_mode="HTML")
        elif res == "approved":
            await message.reply(f"✅ <b>Tranzaksiya tasdiqlandi.</b> (TX: {tx_id})", parse_mode="HTML")
            
            # Foydalanuvchiga xabar
            async with AsyncSessionLocal() as session:
                tx = await session.get(Transaction, tx_id)
                if tx:
                    try:
                        await message.bot.send_message(
                            tx.user_telegram_id,
                            f"💰 <b>Withdraw soʻrovingiz tasdiqlandi!</b>\n\n"
                            f"📝 TX ID: <code>{tx_id}</code>",
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        logger.error(f"Foydalanuvchiga xabar yuborilmadi: {e}")
        else:
            await message.reply("❌ <b>Nomaʼlum xatolik.</b>", parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Confirm_withdraw xatosi: {e}")
        await message.reply("❌ Tasdiqlashda xatolik yuz berdi.")

# ==================== ADMIN: WITHDRAW RAD ETISH ====================

@router.message(Command("decline_withdraw"))
async def cmd_decline_withdraw(message: types.Message):
    """Withdraw so'rovini rad etish (faqat admin)"""
    if message.from_user.id not in ALL_OWNER_IDS:
        return
    
    try:
        parts = message.text.split(maxsplit=2)
        
        if len(parts) < 2 or not parts[1].isdigit():
            await message.reply(
                "❌ <b>Foydalanish:</b> /decline_withdraw <tx_id> [izoh]",
                parse_mode="HTML"
            )
            return
        
        tx_id = int(parts[1])
        note = parts[2] if len(parts) > 2 else None
        
        res = await process_withdraw(tx_id, message.from_user.id, approve=False, note=note)
        
        if res == "not_found":
            await message.reply("❌ <b>TX topilmadi.</b>", parse_mode="HTML")
        elif res == "already_processed":
            await message.reply("⚠️ <b>TX allaqachon qayta ishlangan.</b>", parse_mode="HTML")
        elif res == "declined":
            await message.reply(f"❌ <b>Tranzaksiya rad etildi.</b> (TX: {tx_id})", parse_mode="HTML")
            
            # Foydalanuvchiga xabar
            async with AsyncSessionLocal() as session:
                tx = await session.get(Transaction, tx_id)
                if tx:
                    try:
                        await message.bot.send_message(
                            tx.user_telegram_id,
                            f"❌ <b>Withdraw soʻrovingiz rad etildi</b>\n\n"
                            f"📝 TX ID: <code>{tx_id}</code>\n"
                            f"📌 Sabab: {note or 'Koʻrsatilmagan'}",
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        logger.error(f"Foydalanuvchiga xabar yuborilmadi: {e}")
        else:
            await message.reply("❌ <b>Nomaʼlum xatolik.</b>", parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Decline_withdraw xatosi: {e}")
        await message.reply("❌ Rad etishda xatolik yuz berdi.")

# ==================== ADMIN: WITHDRAW EKSPORT ====================

@router.message(Command("export_withdraws"))
async def cmd_export_withdraws(message: types.Message):
    """Withdraw so'rovlarini CSV formatida eksport qilish (faqat admin)"""
    if message.from_user.id not in ALL_OWNER_IDS:
        return
    
    try:
        pending = await list_pending_withdrawals()
        
        if not pending:
            await message.reply("📭 <b>Eksport qilish uchun soʻrovlar yoʻq.</b>", parse_mode="HTML")
            return
        
        # CSV yaratish
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "User ID", "Username", "Amount", "Method", "Status", "Created At", "Note"])
        
        async with AsyncSessionLocal() as session:
            for tx in pending:
                user = await get_user_by_tid(session, tx.user_telegram_id)
                username = user.username if user else ""
                writer.writerow([
                    tx.id,
                    tx.user_telegram_id,
                    username,
                    f"{tx.amount:.2f}",
                    tx.method,
                    tx.status,
                    tx.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    tx.note or ""
                ])
        
        csv_bytes = output.getvalue().encode('utf-8')
        
        # Vaqtinchalik fayl yaratish
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='wb') as tmp:
            tmp.write(csv_bytes)
            tmp_path = tmp.name
        
        # Faylni yuborish
        await message.reply_document(
            FSInputFile(tmp_path),
            caption=f"📊 <b>Withdraw soʻrovlari</b>\n📅 {datetime.now().strftime('%d.%m.%Y')}",
            parse_mode="HTML"
        )
        
        # Vaqtinchalik faylni o'chirish
        try:
            os.unlink(tmp_path)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Export_withdraws xatosi: {e}")
        await message.reply("❌ Eksport qilishda xatolik yuz berdi.")

# ==================== ADMIN: MANUAL PAYOUT ====================

@router.message(Command("manual_payout"))
async def cmd_manual_payout(message: types.Message):
    """Qo'lda to'lov qilish (faqat admin)"""
    if message.from_user.id not in ALL_OWNER_IDS:
        return
    
    try:
        parts = message.text.split()
        
        if len(parts) < 3:
            await message.reply(
                "❌ <b>Foydalanish:</b> /manual_payout <user_id> <summa> [metod] [izoh]\n\n"
                "Misol: /manual_payout 123456789 50000 paynet Bonus",
                parse_mode="HTML"
            )
            return
        
        try:
            user_tid = int(parts[1])
            amount = float(parts[2])
        except ValueError:
            await message.reply(
                "❌ <b>Xato:</b> User ID va summa raqam boʻlishi kerak.",
                parse_mode="HTML"
            )
            return
        
        method = parts[3] if len(parts) > 3 else "manual"
        note = " ".join(parts[4:]) if len(parts) > 4 else None
        
        res = await manual_payout(message.from_user.id, user_tid, amount, method, note)
        
        if res == "user_not_found":
            await message.reply(f"❌ <b>Foydalanuvchi topilmadi:</b> <code>{user_tid}</code>", parse_mode="HTML")
        elif res == "insufficient_balance":
            await message.reply("⚠️ <b>Foydalanuvchi balansida yetarli mablagʻ yoʻq.</b>", parse_mode="HTML")
        elif res == "ok":
            await message.reply(
                f"✅ <b>Manual payout muvaffaqiyatli!</b>\n\n"
                f"👤 User: <code>{user_tid}</code>\n"
                f"💰 Summa: <b>{amount:.2f} soʻm</b>\n"
                f"📌 Metod: {method}\n"
                f"📝 Izoh: {note or '—'}",
                parse_mode="HTML"
            )
            
            # Foydalanuvchiga xabar
            try:
                await message.bot.send_message(
                    user_tid,
                    f"💸 <b>Sizga toʻlov qilindi!</b>\n\n"
                    f"💰 Summa: <b>{amount:.2f} soʻm</b>\n"
                    f"📌 Metod: {method}\n"
                    f"📝 Izoh: {note or '—'}",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Foydalanuvchiga xabar yuborilmadi: {e}")
        else:
            await message.reply("❌ <b>Nomaʼlum xatolik.</b>", parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Manual_payout xatosi: {e}")
        await message.reply("❌ To'lov qilishda xatolik yuz berdi.")