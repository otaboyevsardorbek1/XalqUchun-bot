import os
import sys
import asyncio
import io
import csv
import tempfile
from datetime import datetime
from typing import Optional, List

# Windows asyncio policy fix
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from dotenv import load_dotenv
load_dotenv()

# Aiogram
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.client.default import DefaultBotProperties # type: ignore
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, BotCommandScopeChat
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.enums import ParseMode

# SQLAlchemy async
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, select, func

# Graphviz (we'll use /treeimg in later parts)
try:
    from graphviz import Digraph
    GRAPHVIZ_AVAILABLE = True
except Exception:
    GRAPHVIZ_AVAILABLE = False

# Logging
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("referral_bot")

# -----------------------
# CONFIG
# -----------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "8425142685:AAH_RIP1J4kbuqQtoS5M3a_QQNpfPCV-byI")
OWNER_ID = int(os.getenv("OWNER_ID", "6646928202"))
ADMINS_FROM_ENV = os.getenv("ADMINS", "")
ADDITIONAL_ADMINS = [int(x) for x in ADMINS_FROM_ENV.split(",") if x.strip().isdigit()]
ALL_OWNER_IDS = [OWNER_ID] + ADDITIONAL_ADMINS

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///referrals.db")

# referral rewards config (can be changed by editing constants)
LEVEL_REWARDS = {1: 100.0, 2: 50.0, 3: 25.0, 4: 10.0, 5: 5.0}
MAX_REWARD_LEVEL = max(LEVEL_REWARDS.keys())

MAX_TREE_DEPTH = int(os.getenv("MAX_TREE_DEPTH", "10"))

# -----------------------
# DB SETUP
# -----------------------
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionMaker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    referrer_telegram_id = Column(Integer, nullable=True)
    role = Column(String, default="guest", nullable=False)
    balance = Column(Float, default=0.0)
    referrals_count = Column(Integer, default=0)
    blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    sender_telegram_id = Column(Integer, nullable=False)
    receiver_telegram_id = Column(Integer, nullable=False)
    text = Column(String, nullable=False)
    message_type = Column(String, default="text")
    created_at = Column(DateTime, default=datetime.utcnow)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    user_telegram_id = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String, default="withdraw")  # withdraw, bonus, manual
    method = Column(String, default="manual")   # payme/qiwi/bank/manual/system
    status = Column(String, default="pending")  # pending/approved/declined
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    admin_telegram_id = Column(Integer, nullable=True)
    note = Column(String, nullable=True)

# -----------------------
# BOT SETUP - TO'G'RILANGAN
# -----------------------
if not BOT_TOKEN:
    logger.warning("BOT_TOKEN not set. Set BOT_TOKEN env var before running.")
    sys.exit(1)

try:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    router = Router()
    dp.include_router(router)
    logger.info("Bot va Dispatcher muvaffaqiyatli yaratildi")
except Exception as e:
    logger.error(f"Bot yaratishda xato: {e}")
    sys.exit(1)

# -----------------------
# DB helpers
# -----------------------
async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database created / ready.")

async def get_user_by_tid(session: AsyncSession, tid: int) -> Optional[User]:
    res = await session.execute(select(User).where(User.telegram_id == tid))
    return res.scalar_one_or_none()

async def add_user(telegram_id: int, username: Optional[str], first_name: Optional[str], referrer_tid: Optional[int] = None) -> bool:
    """
    Adds user if not exists. If referrer provided and exists, distributes level rewards up the chain.
    Returns True if new user added, False if already exists.
    """
    async with AsyncSessionMaker() as session:
        existing = await get_user_by_tid(session, telegram_id)
        if existing:
            return False
        user = User(telegram_id=telegram_id, username=username, first_name=first_name, referrer_telegram_id=referrer_tid, role="guest")
        session.add(user)
        # rewards distribution
        if referrer_tid:
            ref = await get_user_by_tid(session, referrer_tid)
            if ref:
                ref.referrals_count = (ref.referrals_count or 0) + 1
                current_ref = ref
                level = 1
                while current_ref and level <= MAX_REWARD_LEVEL:
                    reward = LEVEL_REWARDS.get(level, 0.0)
                    if reward:
                        current_ref.balance = (current_ref.balance or 0.0) + float(reward)
                        tx = Transaction(
                            user_telegram_id=current_ref.telegram_id,
                            amount=float(reward),
                            type="bonus",
                            method="system",
                            status="approved",
                            processed_at=datetime.utcnow(),
                            admin_telegram_id=OWNER_ID,
                            note=f"Referral level {level} bonus from new user {telegram_id}"
                        )
                        session.add(tx)
                    if current_ref.referrer_telegram_id:
                        current_ref = await get_user_by_tid(session, current_ref.referrer_telegram_id)
                    else:
                        current_ref = None
                    level += 1
        await session.commit()
        return True

async def set_role(telegram_id: int, role: str):
    async with AsyncSessionMaker() as session:
        u = await get_user_by_tid(session, telegram_id)
        if not u:
            u = User(telegram_id=telegram_id, role=role, created_at=datetime.utcnow())
            session.add(u)
        else:
            u.role = role
        await session.commit()
        return u

async def block_user(telegram_id: int):
    async with AsyncSessionMaker() as session:
        u = await get_user_by_tid(session, telegram_id)
        if not u:
            u = User(telegram_id=telegram_id, blocked=True)
            session.add(u)
        else:
            u.blocked = True
        await session.commit()

async def unblock_user(telegram_id: int):
    async with AsyncSessionMaker() as session:
        u = await get_user_by_tid(session, telegram_id)
        if u:
            u.blocked = False
            await session.commit()

async def save_message(sender: int, receiver: int, text: str, message_type: str = "text"):
    async with AsyncSessionMaker() as session:
        m = Message(sender_telegram_id=sender, receiver_telegram_id=receiver, text=text, message_type=message_type)
        session.add(m)
        await session.commit()

async def get_children(telegram_id: int) -> List[User]:
    async with AsyncSessionMaker() as session:
        res = await session.execute(select(User).where(User.referrer_telegram_id == telegram_id).order_by(User.id))
        return res.scalars().all()

async def count_downline(telegram_id: int) -> int:
    total = 0
    queue = [telegram_id]
    visited = set()
    async with AsyncSessionMaker() as session:
        while queue:
            cur = queue.pop(0)
            if cur in visited:
                continue
            visited.add(cur)
            res = await session.execute(select(User.telegram_id).where(User.referrer_telegram_id == cur))
            rows = res.scalars().all()
            for r in rows:
                total += 1
                queue.append(r)
    return total

async def build_tree_text(root_tid: int, max_depth: int = 7) -> str:
    lines: List[str] = []
    async def _recurse(tid: int, level: int, prefix: str):
        children = await get_children(tid)
        if not children:
            return
        for idx, child in enumerate(children):
            is_last = (idx == len(children) - 1)
            branch = "└── " if is_last else "├── "
            name = child.username or child.first_name or f"ID:{child.telegram_id}"
            lines.append(f"{prefix}{branch}{name} (ID:{child.telegram_id})")
            new_prefix = prefix + ("    " if is_last else "│   ")
            if level + 1 < max_depth:
                await _recurse(child.telegram_id, level + 1, new_prefix)
    await _recurse(root_tid, 0, "")
    return "\n".join(lines)

# -----------------------
# Transaction helpers (basic) - will expand in next parts
# -----------------------
async def create_withdraw_request(user_tid: int, amount: float, method: str = "manual", note: Optional[str] = None) -> Transaction:
    async with AsyncSessionMaker() as session:
        tx = Transaction(user_telegram_id=user_tid, amount=float(amount), type="withdraw", method=method, status="pending", note=note)
        session.add(tx)
        await session.commit()
        await session.refresh(tx)
        return tx

async def list_user_transactions(user_tid: int) -> List[Transaction]:
    async with AsyncSessionMaker() as session:
        res = await session.execute(select(Transaction).where(Transaction.user_telegram_id == user_tid).order_by(Transaction.created_at.desc()))
        return res.scalars().all()

async def list_pending_withdrawals() -> List[Transaction]:
    async with AsyncSessionMaker() as session:
        res = await session.execute(select(Transaction).where(Transaction.type == "withdraw", Transaction.status == "pending").order_by(Transaction.created_at.asc()))
        return res.scalars().all()

async def process_withdraw(tx_id: int, admin_tid: int, approve: bool, note: Optional[str] = None) -> str:
    async with AsyncSessionMaker() as session:
        res = await session.execute(select(Transaction).where(Transaction.id == tx_id))
        tx = res.scalar_one_or_none()
        if not tx:
            return "not_found"
        if tx.status != "pending":
            return "already_processed"
        if approve:
            # check user balance
            u = await get_user_by_tid(session, tx.user_telegram_id)
            if not u:
                tx.status = "declined"
                tx.processed_at = datetime.utcnow()
                tx.admin_telegram_id = admin_tid
                await session.commit()
                return "user_not_found"
            if (u.balance or 0.0) < tx.amount:
                tx.status = "declined"
                tx.processed_at = datetime.utcnow()
                tx.admin_telegram_id = admin_tid
                tx.note = (tx.note or "") + " | declined: insufficient balance"
                await session.commit()
                return "insufficient_balance"
            # deduct and mark approved
            u.balance = (u.balance or 0.0) - tx.amount
            tx.status = "approved"
            tx.processed_at = datetime.utcnow()
            tx.admin_telegram_id = admin_tid
            tx.note = (tx.note or "") + (f" | approved by {admin_tid}: {note}" if note else f" | approved by {admin_tid}")
            await session.commit()
            return "approved"
        else:
            tx.status = "declined"
            tx.processed_at = datetime.utcnow()
            tx.admin_telegram_id = admin_tid
            tx.note = (tx.note or "") + (f" | declined by {admin_tid}: {note}" if note else f" | declined by {admin_tid}")
            await session.commit()
            return "declined"

# CSV export helper (will be used by admin)
async def export_withdraws_csv() -> Optional[str]:
    pending = await list_pending_withdrawals()
    if not pending:
        return None
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "user_telegram_id", "username", "amount", "method", "status", "created_at", "note"])
    async with AsyncSessionMaker() as session:
        for tx in pending:
            res = await session.execute(select(User).where(User.telegram_id == tx.user_telegram_id))
            user = res.scalar_one_or_none()
            username = user.username if user else ""
            writer.writerow([tx.id, tx.user_telegram_id, username, f"{tx.amount:.2f}", tx.method, tx.status, tx.created_at.strftime("%Y-%m-%d %H:%M:%S"), tx.note or ""])
    csv_bytes = output.getvalue().encode('utf-8')
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    tmp.write(csv_bytes)
    tmp.flush()
    tmp.close()
    return tmp.name

async def manual_payout(admin_tid: int, user_tid: int, amount: float, method: str = "manual", note: Optional[str] = None) -> str:
    async with AsyncSessionMaker() as session:
        u = await get_user_by_tid(session, user_tid)
        if not u:
            return "user_not_found"
        if (u.balance or 0.0) < amount:
            return "insufficient_balance"
        u.balance = (u.balance or 0.0) - amount
        tx = Transaction(user_telegram_id=user_tid, amount=amount, type="manual", method=method, status="approved", processed_at=datetime.utcnow(), admin_telegram_id=admin_tid, note=note)
        session.add(tx)
        await session.commit()
        return "ok"

# -----------------------
# STARTUP / ERROR HANDLERS
# -----------------------
async def notify_owners_startup():
    for owner in ALL_OWNER_IDS:
        try:
            await bot.send_message(owner, f"✅ Bot ishga tushdi — {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} (UTC)", disable_notification=True)
        except Exception:
            logger.exception("notify owners startup failed")

async def notify_owners_shutdown():
    for owner in ALL_OWNER_IDS:
        try:
            await bot.send_message(owner, f"⚠️ Bot to'xtadi — {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} (UTC)", disable_notification=True)
        except Exception:
            logger.exception("notify owners shutdown failed")

# async def error_handler(update: types.Update, exception: Exception):
#     logger.exception("Error: %s", exception)
#     for owner in ALL_OWNER_IDS:
#         try:
#             await bot.send_message(owner, f"❗ Xato yuz berdi:\n{exception}\nUpdate: {update}")
#         except Exception:
#             pass

# -----------------------
# PUBLIC HANDLERS
# -----------------------
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    args = message.text.split()
    ref = None
    if len(args) > 1:
        a = args[1].strip()
        if a.isdigit():
            ref = int(a)
    created = await add_user(message.from_user.id, message.from_user.username, message.from_user.first_name, ref)
    bot_username = (await bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={message.from_user.id}"
    if not created:
        await message.reply(f"Siz allaqachon ro'yxatda bo'lgansiz ✅\nSizning referal link: {ref_link}")
        return
    else:
        await message.reply(
            f"🎉 Salom, {message.from_user.first_name}!\nSiz muvaffaqiyatli ro'yxatdan o'tdingiz.\n\n"
            f"👥 Sizning referal linkingiz:\n{ref_link}\n\n"
            f"🌳 /tree — referal daraxt\n"
            f"🖼 /treeimg — daraxt rasm (agar Graphviz mavjud bo'lsa)\n"
            f"📊 /downline — avlodlar soni\n"
            f"👤 /me — profil va balans\n"
            f"💳 /balance — balansni ko'rish\n"
            f"💸 /withdraw <sum> — yechib olish so'rovi yuborish\n"
            f"🧾 /transactions — tranzaksiyalar tarixi"
        )
        return

@router.message(Command("tree"))
async def cmd_tree(message: types.Message):
    tree = await build_tree_text(message.from_user.id, max_depth=MAX_TREE_DEPTH)
    if not tree:
        await message.reply("Siz hali hech kimni taklif qilmagansiz 🌱")
        return
    await message.reply(f"🌳 Sizning referal daraxtingiz:\n\n<pre>{tree}</pre>")

# Graphviz coloring & node info
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
    if not GRAPHVIZ_AVAILABLE:
        await message.reply("Graphviz (python package yoki system 'dot') mavjud emas. O'rnatish: system: apt/brew/choco install graphviz; python: pip install graphviz")
        return
    root = message.from_user.id
    nodes = {}
    edges = []
    queue = [(root, 0)]
    visited = set()
    async with AsyncSessionMaker() as session:
        while queue:
            cur_tid, level = queue.pop(0)
            if cur_tid in visited:
                continue
            visited.add(cur_tid)
            res = await session.execute(select(User).where(User.telegram_id == cur_tid))
            cur_user = res.scalar_one_or_none()
            if cur_user:
                label = f"{cur_user.first_name or cur_user.username or 'ID:'+str(cur_tid)}\\nID:{cur_tid}\\nBal:{cur_user.balance:.2f}\\nRef:{cur_user.referrals_count}"
                color = ROLE_COLOR.get((cur_user.role or "guest").lower(), "lightgray")
            else:
                label = f"ID:{cur_tid}"
                color = "lightgray"
            nodes[cur_tid] = {"label": label, "color": color, "role": getattr(cur_user, "role", "guest") if cur_user else "guest"}
            if level < MAX_TREE_DEPTH:
                res2 = await session.execute(select(User.telegram_id).where(User.referrer_telegram_id == cur_tid))
                children = res2.scalars().all()
                for child_tid in children:
                    edges.append((cur_tid, child_tid))
                    queue.append((child_tid, level+1))
    # draw graph
    dot = Digraph(format='png')
    dot.attr('node', shape='record', fontsize='10')
    for tid, meta in nodes.items():
        dot.node(str(tid), label=meta["label"], style="filled", fillcolor=meta["color"])
    for a,b in edges:
        dot.edge(str(a), str(b))
    # render to temp and send
    try:
        tmpdir = tempfile.mkdtemp()
        out_path = os.path.join(tmpdir, f"tree_{root}")
        png_path = dot.render(filename=out_path, cleanup=True)
        await message.reply_photo(photo=FSInputFile(png_path), caption="🌳 Sizning referal daraxtingiz (rasm)")
    except Exception as e:
        logger.exception("Graphviz render error: %s", e)
        await message.reply("Rasm yaratishda xato yuz berdi. Graphviz o'rnatilganligini va python 'graphviz' paketini tekshiring.")

@router.message(Command("downline"))
async def cmd_downline(message: types.Message):
    total = await count_downline(message.from_user.id)
    await message.reply(f"👥 Sizning barcha avlodlaringiz soni: {total}")

@router.message(Command("me"))
async def cmd_me(message: types.Message):
    async with AsyncSessionMaker() as session:
        u = await get_user_by_tid(session, message.from_user.id)
    if not u:
        await message.reply("Siz ro'yxatda yo'q.")
        return
    await message.reply(
        f"👤 {u.first_name or u.username} (@{u.username or '—'})\n"
        f"ID: {u.telegram_id}\n"
        f"Rol: {u.role}\n"
        f"Direct referrals: {u.referrals_count}\n"
        f"Balance: {u.balance:.2f}\n"
        f"Blocked: {'✅' if u.blocked else '❌'}"
    )

@router.message(Command("balance"))
async def cmd_balance(message: types.Message):
    async with AsyncSessionMaker() as session:
        u = await get_user_by_tid(session, message.from_user.id)
    bal = u.balance if u else 0.0
    await message.reply(f"💳 Sizning balansingiz: {bal:.2f}")

@router.message(Command("withdraw"))
async def cmd_withdraw(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        return await message.reply("Foydalanish: /withdraw <sum> (masalan: /withdraw 100)")
    try:
        amount = float(parts[1])
    except:
        return await message.reply("Summa noto'g'ri. Raqam kiriting (masalan 100 yoki 50.5).")
    if amount <= 0:
        return await message.reply("Summa musbat bo'lishi kerak.")
    # check balance
    async with AsyncSessionMaker() as session:
        u = await get_user_by_tid(session, message.from_user.id)
    if not u:
        return await message.reply("Siz ro'yxatda mavjud emassiz.")
    if (u.balance or 0.0) < amount:
        return await message.reply("Sizning balansingizda yetarli mablag' yo'q.")
    tx = await create_withdraw_request(message.from_user.id, amount, method="manual")
    await message.reply(f"💸 Yechib olish so'rovi qabul qilindi. TX_ID: {tx.id}. Admin tasdiqlashini kuting.")
    # notify owners
    for owner in ALL_OWNER_IDS:
        try:
            await bot.send_message(owner, f"💸 Yangi withdraw so'rovi\nUser: {message.from_user.id}\nAmount: {amount:.2f}\nTX_ID: {tx.id}\n/confirm_withdraw {tx.id}  yoki /decline_withdraw {tx.id}")
        except Exception:
            pass

@router.message(Command("transactions"))
async def cmd_transactions(message: types.Message):
    txs = await list_user_transactions(message.from_user.id)
    if not txs:
        return await message.reply("Tranzaksiyalar topilmadi.")
    lines = []
    for t in txs:
        lines.append(f"ID:{t.id} | {t.type} | {t.amount:.2f} | {t.status} | {t.created_at.strftime('%Y-%m-%d %H:%M')}")
    await message.reply("🧾 Sizning tranzaksiyalaringiz:\n\n" + "\n".join(lines))

# -----------------------
# ADMIN HANDLERS (owner/admins)
# -----------------------
def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌳 Mening daraxtim", callback_data="admin_tree_me"),
         InlineKeyboardButton(text="🔍 Foydalanuvchi qidir", callback_data="admin_find")],
        [InlineKeyboardButton(text="📤 Foydalanuvchiga yozish", callback_data="admin_write")],
        [InlineKeyboardButton(text="🚫 Bloklash", callback_data="admin_block"),
         InlineKeyboardButton(text="✅ Blokdan chiqarish", callback_data="admin_unblock")],
        [InlineKeyboardButton(text="📊 Statistikalar", callback_data="admin_stats"),
         InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_users")]
    ])

@router.message(Command("panel"))
async def cmd_panel(message: types.Message):
    if message.from_user.id not in ALL_OWNER_IDS:
        return
    await message.reply("🛠 Admin panel", reply_markup=admin_kb())

@router.message(Command("withdraw_requests"))
async def cmd_withdraw_requests(message: types.Message):
    if message.from_user.id not in ALL_OWNER_IDS:
        return
    pending = await list_pending_withdrawals()
    if not pending:
        return await message.reply("Hozircha pending withdraw so'rovlar yo'q.")
    lines = []
    for t in pending:
        lines.append(f"ID:{t.id} | User:{t.user_telegram_id} | {t.amount:.2f} | created:{t.created_at.strftime('%Y-%m-%d %H:%M')}")
    await message.reply("🔔 Pending withdraws:\n\n" + "\n".join(lines) + "\n\nUse /confirm_withdraw <tx_id> yoki /decline_withdraw <tx_id>")

@router.message(Command("confirm_withdraw"))
async def cmd_confirm_withdraw(message: types.Message):
    if message.from_user.id not in ALL_OWNER_IDS:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.reply("Foydalanish: /confirm_withdraw <tx_id> [note]")
    tx_id = int(parts[1])
    note = parts[2] if len(parts) > 2 else None
    res = await process_withdraw(tx_id, message.from_user.id, approve=True, note=note)
    if res == "not_found":
        return await message.reply("TX topilmadi.")
    if res == "already_processed":
        return await message.reply("TX allaqachon qayta ishlangan.")
    if res == "insufficient_balance":
        return await message.reply("Foydalanuvchi balansida yetarli mablag' yo'q — tranzaksiya bekor qilindi.")
    if res == "approved":
        await message.reply("✅ Tranzaksiya tasdiqlandi va balansdan yechildi.")
        # notify user
        user_tid = await get_user_tid_from_tx(tx_id)
        if user_tid:
            try:
                await bot.send_message(user_tid, f"💰 Sizning withdraw so'rovingiz (ID:{tx_id}) tasdiqlandi. Sizga tashqi to'lov amalga oshirilgan.")
            except Exception:
                pass
        return

@router.message(Command("decline_withdraw"))
async def cmd_decline_withdraw(message: types.Message):
    if message.from_user.id not in ALL_OWNER_IDS:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.reply("Foydalanish: /decline_withdraw <tx_id> [note]")
    tx_id = int(parts[1])
    note = parts[2] if len(parts) > 2 else None
    res = await process_withdraw(tx_id, message.from_user.id, approve=False, note=note)
    if res == "not_found":
        return await message.reply("TX topilmadi.")
    if res == "already_processed":
        return await message.reply("TX allaqachon qayta ishlangan.")
    if res == "declined":
        await message.reply("❌ Tranzaksiya rad etildi.")
        user_tid = await get_user_tid_from_tx(tx_id)
        if user_tid:
            try:
                await bot.send_message(user_tid, f"❌ Sizning withdraw so'rovingiz (ID:{tx_id}) rad etildi. Sabab: {note or '—'}")
            except Exception:
                pass
        return

async def get_user_tid_from_tx(tx_id: int) -> Optional[int]:
    async with AsyncSessionMaker() as session:
        res = await session.execute(select(Transaction).where(Transaction.id == tx_id))
        tx = res.scalar_one_or_none()
        return tx.user_telegram_id if tx else None

@router.message(Command("export_withdraws"))
async def cmd_export_withdraws(message: types.Message):
    if message.from_user.id not in ALL_OWNER_IDS:
        return
    path = await export_withdraws_csv()
    if not path:
        return await message.reply("Pending withdraw topilmadi — eksport qilishga hojati yo'q.")
    try:
        await bot.send_document(message.chat.id, FSInputFile(path), caption="Pending withdraws CSV")
    except Exception as e:
        await message.reply(f"CSV yuborishda xato: {e}")
    finally:
        try:
            os.remove(path)
        except Exception:
            pass

@router.message(Command("manual_payout"))
async def cmd_manual_payout(message: types.Message):
    if message.from_user.id not in ALL_OWNER_IDS:
        return
    parts = message.text.split()
    if len(parts) < 3:
        return await message.reply("Foydalanish: /manual_payout <user_telegram_id> <amount> [method] [note]")
    try:
        user_tid = int(parts[1])
        amount = float(parts[2])
    except:
        return await message.reply("telegram_id va amount to'g'ri formatda bo'lishi kerak.")
    method = parts[3] if len(parts) > 3 else "manual"
    note = " ".join(parts[4:]) if len(parts) > 4 else None
    res = await manual_payout(message.from_user.id, user_tid, amount, method=method, note=note)
    if res == "user_not_found":
        return await message.reply("Foydalanuvchi topilmadi.")
    if res == "insufficient_balance":
        return await message.reply("Foydalanuvchining balansida yetarli mablag' yo'q.")
    await message.reply(f"✅ Manual payout: {amount:.2f} to user {user_tid} (method: {method})")
    try:
        await bot.send_message(user_tid, f"💸 Sizga {amount:.2f} summa qo'lda to'lov sifatida yuborildi (method: {method}). Agar siz real pul olsangiz, tekshirib oling.")
    except Exception:
        pass

# ROLE management (simple)
@router.message(Command("setrole"))
async def cmd_setrole(message: types.Message):
    if message.from_user.id not in ALL_OWNER_IDS:
        return
    parts = message.text.split()
    if len(parts) != 3:
        return await message.reply("Foydalanish: /setrole <telegram_id> <role>")
    try:
        target = int(parts[1])
    except:
        return await message.reply("telegram_id raqam bo'lishi kerak.")
    new_role = parts[2].strip().lower()
    allowed_roles = ["owner", "admin", "manager", "worker", "diller", "dastafka", "guest"]
    if new_role not in allowed_roles:
        return await message.reply(f"Noto'g'ri rol. Mavjud rollar: {', '.join(allowed_roles)}")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm_setrole:{message.from_user.id}:{target}:{new_role}"),
            InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_setrole")
        ]
    ])
    await message.reply(f"🔔 Siz <b>{target}</b> ga <b>{new_role}</b> rolini berishni tasdiqlaysizmi?", reply_markup=kb)

@router.callback_query(F.data.startswith("confirm_setrole"))
async def cb_confirm_setrole(call: types.CallbackQuery):
    _, admin_id_s, target_s, role = call.data.split(":")
    admin_id = int(admin_id_s); target = int(target_s)
    if call.from_user.id != admin_id:
        return await call.answer("Siz bu amalni tasdiqlay olmaysiz!", show_alert=True)
    await set_role(target, role)
    try:
        await bot.send_message(target, f"🔔 Sizga '{role}' roli berildi.")
    except Exception:
        pass
    await call.message.edit_text(f"✅ Rol muvaffaqiyatli o'rnatildi: {target} -> {role}")

@router.callback_query(F.data == "cancel_setrole")
async def cb_cancel_setrole(call: types.CallbackQuery):
    await call.message.edit_text("❌ Amal bekor qilindi.")

# Users list (paginated)
@router.message(Command("users"))
async def cmd_users(message: types.Message):
    if message.from_user.id not in ALL_OWNER_IDS:
        return
    per_page = 10; page = 1
    async with AsyncSessionMaker() as session:
        total = (await session.execute(select(func.count(User.id)))).scalar_one()
        total_pages = max((total + per_page - 1) // per_page, 1)
        res = await session.execute(select(User).order_by(User.id).limit(per_page).offset(0))
        users = res.scalars().all()
    lines = [f"📋 Foydalanuvchilar — Sahifa {page}/{total_pages}"]
    for u in users:
        lines.append(f"{u.telegram_id} | {u.first_name or u.username} | {u.role} | bal:{u.balance:.2f} | ref:{u.referrer_telegram_id}")
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("Keyingi ➡", callback_data=f"users_page:{page+1}")]] ) if page < total_pages else None
    await message.reply("\n".join(lines), reply_markup=kb)

@router.callback_query(F.data.startswith("users_page:"))
async def cb_users_page(call: types.CallbackQuery):
    if call.from_user.id not in ALL_OWNER_IDS:
        return await call.answer("Ruxsat yo'q", show_alert=True)
    page = int(call.data.split(":",1)[1]); per_page = 10
    async with AsyncSessionMaker() as session:
        total = (await session.execute(select(func.count(User.id)))).scalar_one()
        total_pages = max((total + per_page - 1) // per_page, 1)
        offset = (page - 1) * per_page
        res = await session.execute(select(User).order_by(User.id).limit(per_page).offset(offset))
        users = res.scalars().all()
    lines = [f"📋 Foydalanuvchilar — Sahifa {page}/{total_pages}"]
    for u in users:
        lines.append(f"{u.telegram_id} | {u.first_name or u.username} | {u.role} | bal:{u.balance:.2f} | ref:{u.referrer_telegram_id}")
    buttons = []
    if page > 1: buttons.append(InlineKeyboardButton("⬅ Oldingi", callback_data=f"users_page:{page-1}"))
    if page < total_pages: buttons.append(InlineKeyboardButton("Keyingi ➡", callback_data=f"users_page:{page+1}"))
    kb = InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None
    await call.message.delete()
    await bot.send_message(call.message.chat.id, "\n".join(lines), reply_markup=kb)

# set owner commands
async def set_owner_commands():
    try:
        await bot.set_my_commands(
            commands=[
                types.BotCommand(command="panel", description="Admin panel"),
                types.BotCommand(command="users", description="Foydalanuvchilar"),
                types.BotCommand(command="withdraw_requests", description="Withdraw so'rovlari"),
                types.BotCommand(command="export_withdraws", description="Export withdraws CSV"),
                types.BotCommand(command="setrole", description="Rol berish"),
                types.BotCommand(command="manual_payout", description="Qo'lda payout"),
            ],
            scope=BotCommandScopeChat(chat_id=OWNER_ID)
        )
    except TelegramUnauthorizedError:
        logger.error("set_owner_commands failed: Unauthorized — tekshiring BOT_TOKEN.")
    except Exception:
        logger.exception("set_owner_commands failed")

# -----------------------
# MAIN - TO'G'RILANGAN
# -----------------------
async def check_bot_token() -> bool:
    try:
        me = await bot.get_me()
        logger.info(f"Bot connected as @{me.username} (id={me.id})")
        return True
    except TelegramUnauthorizedError:
        logger.error("BOT_TOKEN noto'g'ri yoki Unauthorized — iltimos tokenni tekshiring.")
        return False
    except Exception as e:
        logger.exception("Bot get_me() xato berdi: %s", e)
        return False

async def main():
    if not BOT_TOKEN:
        logger.error("Please set BOT_TOKEN env var.")
        return

    # Avval tokenni tekshiramiz
    ok = await check_bot_token()
    if not ok:
        logger.error("Bot token invalid — dastur to'xtatildi.")
        return

    # Keyin handlerlarni registratsiya qilamiz
    # dp.errors.register(error_handler)
    dp.startup.register(create_db)
    dp.startup.register(notify_owners_startup)
    dp.shutdown.register(notify_owners_shutdown)

    await set_owner_commands()
    logger.info("Bot launching...")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Pollingda xato: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtatildi")
    except Exception as e:
        logger.error(f"Asosiy dasturda xato: {e}")