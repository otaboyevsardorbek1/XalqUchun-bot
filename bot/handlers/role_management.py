from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func

from db.database import AsyncSessionLocal
from db.models import User
from config import OWNER_ID, ALL_OWNER_IDS
from utils.referral import get_user_by_tid

router = Router()

# Role hierarchy (simplified)
ROLE_HIERARCHY = {
    "owner": ["admin", "manager", "worker", "diller", "dastafka", "guest"],
    "admin": ["manager", "worker", "diller", "dastafka", "guest"],
    "manager": ["worker", "diller", "dastafka", "guest"],
    "worker": ["dastafka", "guest"],
    "diller": ["diller", "guest"],
    "dastafka": ["guest", "dastafka"],
    "guest": ["guest"]
}

def can_assign_role(actor_role: str, target_role: str) -> bool:
    return target_role in ROLE_HIERARCHY.get(actor_role, [])

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
        return await message.reply("telegram_id raqam boʻlishi kerak.")
    new_role = parts[2].lower()
    allowed_roles = ["owner", "admin", "manager", "worker", "diller", "dastafka", "guest"]
    if new_role not in allowed_roles:
        return await message.reply(f"Notoʻgʻri rol. Mavjudlar: {', '.join(allowed_roles)}")
    # Check if actor can assign this role
    async with AsyncSessionLocal() as session:
        actor = await get_user_by_tid(session, message.from_user.id)
        if not actor:
            return await message.reply("Siz roʻyxatda yoʻq.")
        if not can_assign_role(actor.role, new_role):
            return await message.reply("Siz bu rolni bera olmaysiz.")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm_setrole:{message.from_user.id}:{target}:{new_role}"),
            InlineKeyboardButton(text="❌ Bekor", callback_data="cancel_setrole")
        ]
    ])
    await message.reply(f"🔔 {target} ga {new_role} rolini berishni tasdiqlaysizmi?", reply_markup=kb)

@router.callback_query(F.data.startswith("confirm_setrole"))
async def confirm_setrole(call: types.CallbackQuery):
    _, admin_id, target, role = call.data.split(":")
    admin_id = int(admin_id)
    target = int(target)
    if call.from_user.id != admin_id:
        return await call.answer("Siz bu amalni tasdiqlay olmaysiz!", show_alert=True)
    async with AsyncSessionLocal() as session:
        user = await get_user_by_tid(session, target)
        if not user:
            user = User(telegram_id=target, role=role)
            session.add(user)
        else:
            user.role = role
        await session.commit()
    try:
        await call.bot.send_message(target, f"🔔 Sizga '{role}' roli berildi.")
    except:
        pass
    await call.message.edit_text(f"✅ Rol oʻrnatildi: {target} -> {role}")

@router.callback_query(F.data == "cancel_setrole")
async def cancel_setrole(call: types.CallbackQuery):
    await call.message.edit_text("❌ Amal bekor qilindi.")

@router.message(Command("users"))
async def cmd_users(message: types.Message):
    if message.from_user.id not in ALL_OWNER_IDS:
        return
    per_page = 10
    page = 1
    async with AsyncSessionLocal() as session:
        total = (await session.execute(select(func.count(User.id)))).scalar_one()
        total_pages = max((total + per_page - 1) // per_page, 1)
        result = await session.execute(select(User).order_by(User.id).limit(per_page).offset(0))
        users = result.scalars().all()
    lines = [f"📋 Foydalanuvchilar — Sahifa {page}/{total_pages}"]
    for u in users:
        lines.append(f"{u.telegram_id} | {u.full_name or u.username} | {u.role} | bal:{u.balance:.2f} | ref:{u.referrer_telegram_id}")
    kb = None
    if page < total_pages:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton("Keyingi ➡", callback_data=f"users_page:{page+1}")]])
    await message.reply("\n".join(lines), reply_markup=kb)

@router.callback_query(F.data.startswith("users_page:"))
async def paginate_users(call: types.CallbackQuery):
    if call.from_user.id not in ALL_OWNER_IDS:
        return await call.answer("Ruxsat yoʻq", show_alert=True)
    page = int(call.data.split(":")[1])
    per_page = 10
    async with AsyncSessionLocal() as session:
        total = (await session.execute(select(func.count(User.id)))).scalar_one()
        total_pages = max((total + per_page - 1) // per_page, 1)
        offset = (page - 1) * per_page
        result = await session.execute(select(User).order_by(User.id).limit(per_page).offset(offset))
        users = result.scalars().all()
    lines = [f"📋 Foydalanuvchilar — Sahifa {page}/{total_pages}"]
    for u in users:
        lines.append(f"{u.telegram_id} | {u.full_name or u.username} | {u.role} | bal:{u.balance:.2f} | ref:{u.referrer_telegram_id}")
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton("⬅ Oldingi", callback_data=f"users_page:{page-1}"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton("Keyingi ➡", callback_data=f"users_page:{page+1}"))
    kb = InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None
    await call.message.delete()
    await call.bot.send_message(call.message.chat.id, "\n".join(lines), reply_markup=kb)