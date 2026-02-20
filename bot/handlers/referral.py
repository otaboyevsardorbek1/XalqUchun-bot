import io
import csv
import tempfile
import os
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from sqlalchemy import select, func

from bot.db.database import AsyncSessionLocal
from bot.db.models import User, Transaction
from bot.utils.referral import (
    get_children, count_downline, build_tree_text,
    create_withdraw_request, list_user_transactions, list_pending_withdrawals,
    process_withdraw, manual_payout, get_user_by_tid
)
from bot.data import ALL_OWNER_IDS, MAX_TREE_DEPTH, OWNER_ID

try:
    from graphviz import Digraph
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False

router = Router()

# Tree text
@router.message(Command("tree"))
async def cmd_tree(message: types.Message):
    tree = await build_tree_text(message.from_user.id, max_depth=MAX_TREE_DEPTH)
    if not tree:
        await message.reply("Siz hali hech kimni taklif qilmagansiz.")
        return
    await message.reply(f"🌳 Sizning referal daraxtingiz:\n\n<pre>{tree}</pre>")

# Tree image (graphviz)
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
        await message.reply("Graphviz mavjud emas. Oʻrnatish: `pip install graphviz` va system graphviz.")
        return
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
            res = await session.execute(select(User).where(User.telegram_id == cur_tid))
            cur_user = res.scalar_one_or_none()
            if cur_user:
                label = f"{cur_user.full_name or cur_user.username or 'ID:'+str(cur_tid)}\\nID:{cur_tid}\\nBal:{cur_user.balance:.2f}\\nRef:{cur_user.referrals_count}"
                color = ROLE_COLOR.get(cur_user.role, "lightgray")
            else:
                label = f"ID:{cur_tid}"
                color = "lightgray"
            nodes[cur_tid] = {"label": label, "color": color}
            if level < MAX_TREE_DEPTH:
                children = await session.execute(select(User.telegram_id).where(User.referrer_telegram_id == cur_tid))
                for child_tid in children.scalars().all():
                    edges.append((cur_tid, child_tid))
                    queue.append((child_tid, level+1))
    dot = Digraph(format='png')
    dot.attr('node', shape='record', fontsize='10')
    for tid, meta in nodes.items():
        dot.node(str(tid), label=meta["label"], style="filled", fillcolor=meta["color"])
    for a,b in edges:
        dot.edge(str(a), str(b))
    try:
        tmpdir = tempfile.mkdtemp()
        out_path = os.path.join(tmpdir, f"tree_{root}")
        png_path = dot.render(filename=out_path, cleanup=True)
        await message.reply_photo(photo=FSInputFile(png_path), caption="🌳 Referal daraxtingiz")
    except Exception as e:
        await message.reply(f"Rasm yaratishda xato: {e}")

@router.message(Command("downline"))
async def cmd_downline(message: types.Message):
    total = await count_downline(message.from_user.id)
    await message.reply(f"👥 Barcha avlodlaringiz soni: {total}")

@router.message(Command("me"))
async def cmd_me(message: types.Message):
    async with AsyncSessionLocal() as session:
        user = await get_user_by_tid(session, message.from_user.id)
    if not user:
        await message.reply("Siz roʻyxatdan oʻtmagan. /start ni bosing.")
        return
    await message.reply(
        f"👤 {user.full_name or user.username} (@{user.username or '—'})\n"
        f"ID: {user.telegram_id}\n"
        f"Rol: {user.role}\n"
        f"Toʻgʻridan-toʻgʻri takliflar: {user.referrals_count}\n"
        f"Balans: {user.balance:.2f} soʻm\n"
        f"Bloklangan: {'✅' if user.blocked else '❌'}"
    )

@router.message(Command("balance"))
async def cmd_balance(message: types.Message):
    async with AsyncSessionLocal() as session:
        user = await get_user_by_tid(session, message.from_user.id)
    bal = user.balance if user else 0.0
    await message.reply(f"💳 Balansingiz: {bal:.2f} soʻm")

@router.message(Command("withdraw"))
async def cmd_withdraw(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        return await message.reply("Foydalanish: /withdraw <sum>")
    try:
        amount = float(parts[1])
    except:
        return await message.reply("Summa notoʻgʻri. Raqam kiriting.")
    if amount <= 0:
        return await message.reply("Summa musbat boʻlishi kerak.")
    async with AsyncSessionLocal() as session:
        user = await get_user_by_tid(session, message.from_user.id)
        if not user:
            return await message.reply("Siz roʻyxatdan oʻtmagan.")
        if (user.balance or 0.0) < amount:
            return await message.reply("Balansingizda yetarli mablagʻ yoʻq.")
    tx = await create_withdraw_request(message.from_user.id, amount)
    await message.reply(f"💸 Yechib olish soʻrovingiz qabul qilindi. TX_ID: {tx.id}. Admin tasdiqlashini kuting.")
    for admin in ALL_OWNER_IDS:
        try:
            await message.bot.send_message(
                admin,
                f"💸 Yangi withdraw soʻrovi\nUser: {message.from_user.id}\nSumma: {amount:.2f}\nTX_ID: {tx.id}\n/confirm_withdraw {tx.id} yoki /decline_withdraw {tx.id}"
            )
        except:
            pass

@router.message(Command("transactions"))
async def cmd_transactions(message: types.Message):
    txs = await list_user_transactions(message.from_user.id)
    if not txs:
        await message.reply("Tranzaksiyalar topilmadi.")
        return
    lines = []
    for t in txs:
        lines.append(f"ID:{t.id} | {t.type} | {t.amount:.2f} | {t.status} | {t.created_at.strftime('%Y-%m-%d %H:%M')}")
    await message.reply("🧾 Sizning tranzaksiyalaringiz:\n\n" + "\n".join(lines))

# Admin withdraw commands
@router.message(Command("withdraw_requests"))
async def cmd_withdraw_requests(message: types.Message):
    if message.from_user.id not in ALL_OWNER_IDS:
        return
    pending = await list_pending_withdrawals()
    if not pending:
        await message.reply("Hozircha kutilayotgan soʻrovlar yoʻq.")
        return
    lines = [f"ID:{t.id} | User:{t.user_telegram_id} | {t.amount:.2f} | {t.created_at.strftime('%Y-%m-%d %H:%M')}" for t in pending]
    await message.reply("🔔 Kutilayotgan withdrawlar:\n\n" + "\n".join(lines))

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
        await message.reply("TX topilmadi.")
    elif res == "already_processed":
        await message.reply("TX allaqachon qayta ishlangan.")
    elif res == "insufficient_balance":
        await message.reply("Foydalanuvchi balansida yetarli mablagʻ yoʻq.")
    elif res == "approved":
        await message.reply("✅ Tranzaksiya tasdiqlandi.")
        async with AsyncSessionLocal() as session:
            tx = await session.get(Transaction, tx_id)
            if tx:
                try:
                    await message.bot.send_message(tx.user_telegram_id, f"💰 Sizning withdraw soʻrovingiz (ID:{tx_id}) tasdiqlandi.")
                except:
                    pass
    else:
        await message.reply("Nomaʼlum xatolik.")

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
        await message.reply("TX topilmadi.")
    elif res == "already_processed":
        await message.reply("TX allaqachon qayta ishlangan.")
    elif res == "declined":
        await message.reply("❌ Tranzaksiya rad etildi.")
        async with AsyncSessionLocal() as session:
            tx = await session.get(Transaction, tx_id)
            if tx:
                try:
                    await message.bot.send_message(tx.user_telegram_id, f"❌ Sizning withdraw soʻrovingiz (ID:{tx_id}) rad etildi. Sabab: {note or '—'}")
                except:
                    pass
    else:
        await message.reply("Nomaʼlum xatolik.")

@router.message(Command("export_withdraws"))
async def cmd_export_withdraws(message: types.Message):
    if message.from_user.id not in ALL_OWNER_IDS:
        return
    pending = await list_pending_withdrawals()
    if not pending:
        await message.reply("Eksport qilish uchun soʻrovlar yoʻq.")
        return
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "user_telegram_id", "username", "amount", "method", "status", "created_at", "note"])
    async with AsyncSessionLocal() as session:
        for tx in pending:
            user = await get_user_by_tid(session, tx.user_telegram_id)
            username = user.username if user else ""
            writer.writerow([tx.id, tx.user_telegram_id, username, f"{tx.amount:.2f}", tx.method, tx.status, tx.created_at.strftime("%Y-%m-%d %H:%M:%S"), tx.note or ""])
    csv_bytes = output.getvalue().encode('utf-8')
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    tmp.write(csv_bytes)
    tmp.flush()
    tmp.close()
    try:
        await message.reply_document(FSInputFile(tmp.name), caption="Pending withdraws CSV")
    finally:
        os.unlink(tmp.name)

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
        return await message.reply("Notoʻgʻri format.")
    method = parts[3] if len(parts) > 3 else "manual"
    note = " ".join(parts[4:]) if len(parts) > 4 else None
    res = await manual_payout(message.from_user.id, user_tid, amount, method, note)
    if res == "user_not_found":
        await message.reply("Foydalanuvchi topilmadi.")
    elif res == "insufficient_balance":
        await message.reply("Balans yetarli emas.")
    elif res == "ok":
        await message.reply(f"✅ Manual payout: {amount:.2f} soʻm user {user_tid} ga oʻtkazildi.")
        try:
            await message.bot.send_message(user_tid, f"💸 Sizga {amount:.2f} soʻm qoʻlda toʻlov qilindi ({method}).")
        except:
            pass
    else:
        await message.reply("Nomaʼlum xatolik.")