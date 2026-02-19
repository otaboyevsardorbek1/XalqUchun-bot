from sqlalchemy import select, func
from db.database import AsyncSessionLocal
from db.models import User, Transaction
from typing import Optional, List
from datetime import datetime
from bot.data import OWNER_ID, LEVEL_REWARDS, MAX_REWARD_LEVEL
from sqlalchemy.exc import IntegrityError

async def get_user_by_tid(session, tid: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.telegram_id == tid))
    return result.scalar_one_or_none()

async def add_user(telegram_id: int, username: str, first_name: str, referrer_tid: Optional[int] = None) -> bool:
    async with AsyncSessionLocal() as session:
        # 1. Mavjudlikni tekshirish
        existing = await get_user_by_tid(session, telegram_id)
        if existing:
            return False

        try:
            # 2. Yangi foydalanuvchi yaratish
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=first_name,
                referrer_telegram_id=referrer_tid,
                role="guest"
            )
            session.add(user)

            # 3. Agar referrer (taklif qiluvchi) bo‘lsa, bonuslarni taqsimlash
            if referrer_tid:
                ref = await get_user_by_tid(session, referrer_tid)
                if ref:
                    ref.referrals_count = (ref.referrals_count or 0) + 1
                    current = ref
                    level = 1
                    while current and level <= MAX_REWARD_LEVEL:
                        reward = LEVEL_REWARDS.get(level, 0.0)
                        if reward:
                            current.balance = (current.balance or 0.0) + reward
                            tx = Transaction(
                                user_telegram_id=current.telegram_id,
                                amount=reward,
                                type="bonus",
                                method="system",
                                status="approved",
                                processed_at=datetime.utcnow(),
                                admin_telegram_id=OWNER_ID,
                                note=f"Level {level} bonus from {telegram_id}"
                            )
                            session.add(tx)
                        if current.referrer_telegram_id:
                            current = await get_user_by_tid(session, current.referrer_telegram_id)
                        else:
                            current = None
                        level += 1

            # 4. O‘zgarishlarni saqlash
            await session.commit()
            return True

        except IntegrityError:
            # 5. Parallel so‘rov tufayli yozuv qo‘shilgan bo‘lishi mumkin
            await session.rollback()
            return False

async def get_children(tid: int) -> List[User]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.referrer_telegram_id == tid).order_by(User.id)
        )
        return result.scalars().all()

async def count_downline(tid: int) -> int:
    total = 0
    queue = [tid]
    visited = set()
    async with AsyncSessionLocal() as session:
        while queue:
            cur = queue.pop(0)
            if cur in visited:
                continue
            visited.add(cur)
            result = await session.execute(select(User.telegram_id).where(User.referrer_telegram_id == cur))
            rows = result.scalars().all()
            for r in rows:
                total += 1
                queue.append(r)
    return total

async def build_tree_text(root_tid: int, max_depth: int = 7) -> str:
    lines = []
    async def recurse(tid: int, level: int, prefix: str):
        children = await get_children(tid)
        if not children:
            return
        for idx, child in enumerate(children):
            is_last = (idx == len(children) - 1)
            branch = "└── " if is_last else "├── "
            name = child.username or child.full_name or f"ID:{child.telegram_id}"
            lines.append(f"{prefix}{branch}{name} (ID:{child.telegram_id})")
            new_prefix = prefix + ("    " if is_last else "│   ")
            if level + 1 < max_depth:
                await recurse(child.telegram_id, level + 1, new_prefix)
    await recurse(root_tid, 0, "")
    return "\n".join(lines)

# Transaction helpers
async def create_withdraw_request(user_tid: int, amount: float, method: str = "manual", note: str = None) -> Transaction:
    async with AsyncSessionLocal() as session:
        tx = Transaction(
            user_telegram_id=user_tid,
            amount=amount,
            type="withdraw",
            method=method,
            status="pending",
            note=note
        )
        session.add(tx)
        await session.commit()
        await session.refresh(tx)
        return tx

async def list_user_transactions(user_tid: int) -> List[Transaction]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Transaction).where(Transaction.user_telegram_id == user_tid).order_by(Transaction.created_at.desc())
        )
        return result.scalars().all()

async def list_pending_withdrawals() -> List[Transaction]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Transaction).where(Transaction.type == "withdraw", Transaction.status == "pending").order_by(Transaction.created_at.asc())
        )
        return result.scalars().all()

async def process_withdraw(tx_id: int, admin_tid: int, approve: bool, note: str = None) -> str:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Transaction).where(Transaction.id == tx_id))
        tx = result.scalar_one_or_none()
        if not tx:
            return "not_found"
        if tx.status != "pending":
            return "already_processed"
        if approve:
            user = await get_user_by_tid(session, tx.user_telegram_id)
            if not user:
                tx.status = "declined"
                tx.processed_at = datetime.utcnow()
                tx.admin_telegram_id = admin_tid
                await session.commit()
                return "user_not_found"
            if (user.balance or 0.0) < tx.amount:
                tx.status = "declined"
                tx.processed_at = datetime.utcnow()
                tx.admin_telegram_id = admin_tid
                tx.note = (tx.note or "") + " | insufficient balance"
                await session.commit()
                return "insufficient_balance"
            user.balance -= tx.amount
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

async def manual_payout(admin_tid: int, user_tid: int, amount: float, method: str = "manual", note: str = None) -> str:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_tid(session, user_tid)
        if not user:
            return "user_not_found"
        if (user.balance or 0.0) < amount:
            return "insufficient_balance"
        user.balance -= amount
        tx = Transaction(
            user_telegram_id=user_tid,
            amount=amount,
            type="manual",
            method=method,
            status="approved",
            processed_at=datetime.utcnow(),
            admin_telegram_id=admin_tid,
            note=note
        )
        session.add(tx)
        await session.commit()
        return "ok"