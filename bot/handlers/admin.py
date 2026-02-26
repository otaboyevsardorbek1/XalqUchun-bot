# bot/handlers/admin.py
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from typing import Union
from aiogram.types import Message, CallbackQuery
import re
import asyncio
import csv
import io
import os
import tempfile
from aiogram.types import FSInputFile
from bot.states.admin import BroadcastState, CourierState
from aiogram.exceptions import TelegramBadRequest
from bot.keyboards.main import get_admin_menu, get_back_button
from bot.utils.helpers import format_price, format_phone_for_display, create_progress_bar
from bot.data import ADMIN_IDS, OWNER_ID, ALL_OWNER_IDS
from bot.db.database import AsyncSessionLocal
from bot.db.models import Order, OrderItem, User, Transaction, Product, Category
import logging

MAINTENANCE_MODE = False  # Global flag - bu o'zgaruvchi admin_settings orqali o'zgartiriladi

router = Router()
logger = logging.getLogger(__name__)

# ==================== ADMIN TEKSHIRISH ====================

def is_admin(user_id: int) -> bool:
    """Foydalanuvchi admin ekanligini tekshirish"""
    return user_id in ADMIN_IDS or user_id == OWNER_ID

def is_owner(user_id: int) -> bool:
    """Foydalanuvchi owner ekanligini tekshirish"""
    return user_id == OWNER_ID

# ==================== ADMIN PANEL ASOSIY ====================

@router.message(F.text == "👑 Admin panel")
@router.message(Command("admin"))
async def admin_panel(message: types.Message):
    """Admin panel asosiy menyusi"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Siz admin emassiz!")
        return
    
    text = """
👑 *ADMIN PANELI* 👑
{0}
*Asosiy bo'limlar:*

📦 *Buyurtmalar* - Yangi buyurtmalarni ko'rish va boshqarish
👥 *Foydalanuvchilar* - Foydalanuvchilar ro'yxati va boshqaruvi
💰 *To'lovlar* - Pul yechish so'rovlarini boshqarish
📊 *Statistika* - Bot statistikasi
📢 *Xabarlar* - Ommaviy xabar yuborish
⚙️ *Sozlamalar* - Bot sozlamalari

Kerakli bo'limni tanlang:
    """.format('═' * 30)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Buyurtmalar", callback_data="admin_orders")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_users")],
        [InlineKeyboardButton(text="💰 To'lovlar", callback_data="admin_payments")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="admin_settings")],
        [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_to_main")]
    ])
    
    await message.answer(text, parse_mode="Markdown", reply_markup=kb)

# ==================== BUYURTMALAR ====================

@router.message(Command("orders"))
@router.callback_query(F.data == "admin_orders")
async def list_orders(event: Union[ Message ,CallbackQuery]):
    """Buyurtmalar ro'yxati"""
    if not is_admin(event.from_user.id):
        if isinstance(event, types.Message):
            await event.answer("❌ Siz admin emassiz!")
        else:
            await event.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    
    try:
        async with AsyncSessionLocal() as session:
            # Yangi buyurtmalar
            new_orders = await session.execute(
                select(Order).where(Order.status == "new")
                .options(selectinload(Order.items))
                .order_by(Order.created_at.desc())
            )
            new_orders = new_orders.scalars().all()
            
            # Tayyorlanayotgan buyurtmalar
            processing_orders = await session.execute(
                select(Order).where(Order.status == "processing")
                .options(selectinload(Order.items))
                .order_by(Order.created_at.desc())
            )
            processing_orders = processing_orders.scalars().all()
            
            # Tayyor buyurtmalar
            ready_orders = await session.execute(
                select(Order).where(Order.status == "ready")
                .options(selectinload(Order.items))
                .order_by(Order.created_at.desc())
            )
            ready_orders = ready_orders.scalars().all()
        
        text = f"""
📦 *BUYURTMALAR BOSHQARMASI*
{'═' * 30}

🆕 *Yangi:* {len(new_orders)} ta
⚙️ *Jarayonda:* {len(processing_orders)} ta
✅ *Tayyor:* {len(ready_orders)} ta

Quyidagi tugmalardan birini tanlang:
        """
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🆕 Yangi ({len(new_orders)})", callback_data="admin_orders_new")],
            [InlineKeyboardButton(text=f"⚙️ Jarayonda ({len(processing_orders)})", callback_data="admin_orders_processing")],
            [InlineKeyboardButton(text=f"✅ Tayyor ({len(ready_orders)})", callback_data="admin_orders_ready")],
            [InlineKeyboardButton(text="📋 Barcha buyurtmalar", callback_data="admin_orders_all")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]
        ])
        
        if isinstance(event, types.Message):
            await event.answer(text, parse_mode="Markdown", reply_markup=kb)
        else:
            await event.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
            await event.answer()
            
    except Exception as e:
        logger.error(f"Buyurtmalarni ko'rsatishda xato: {e}")
        error_msg = "❌ Xatolik yuz berdi."
        if isinstance(event, types.Message):
            await event.answer(error_msg)
        else:
            await event.message.answer(error_msg)
            await event.answer()

@router.callback_query(F.data.startswith("admin_orders_"))
async def show_orders_by_status(callback: CallbackQuery):
    """Status bo'yicha buyurtmalarni ko'rsatish"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    
    try:
        status_map = {
            "new": "🆕 YANGI",
            "processing": "⚙️ JARAYONDA",
            "ready": "✅ TAYYOR",
            "all": "📋 BARCHA"
        }
        
        status = callback.data.split("_")[2]
        status_text = status_map.get(status, "📋 BUYURTMALAR")
        
        async with AsyncSessionLocal() as session:
            query = select(Order).options(
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.user)
            ).order_by(Order.created_at.desc())
            
            if status != "all":
                query = query.where(Order.status == status)
            
            result = await session.execute(query)
            orders = result.scalars().all()
        
        if not orders:
            await callback.message.edit_text(
                f"{status_text} BUYURTMALAR YO'Q",
                reply_markup=get_back_button("admin_orders")
            )
            await callback.answer()
            return
        
        # Har bir buyurtmani alohida ko'rsatish
        await callback.message.delete()
        
        for order in orders[:5]:  # Eng ko'pi bilan 5 ta
            await show_order_details(callback.message, order)
        
        if len(orders) > 5:
            await callback.message.answer(
                f"📌 va yana {len(orders) - 5} ta buyurtma...",
                reply_markup=get_back_button("admin_orders")
            )
        else:
            await callback.message.answer(
                "📌 Boshqa buyurtmalar yo'q",
                reply_markup=get_back_button("admin_orders")
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Status bo'yicha buyurtmalarni ko'rsatishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

async def show_order_details(message: types.Message, order: Order):
    """Buyurtma detallarini ko'rsatish"""
    try:
        # Mahsulotlar ro'yxati
        items_text = ""
        total = 0
        
        for item in order.items:
            if item.product:
                name = item.product.name
            else:
                name = item.product_name or "Maxsus"
            
            if item.price > 0:
                subtotal = item.quantity * item.price
                total += subtotal
                items_text += f"• {name} x{item.quantity} = {format_price(subtotal)} so'm\n"
            else:
                items_text += f"• 📦 {name} x{item.quantity} {item.unit} (maxsus)\n"
        
        # Status emoji
        status_emoji = {
            "new": "🆕",
            "processing": "⚙️",
            "ready": "✅",
            "delivered": "📦",
            "cancelled": "❌"
        }.get(order.status, "📋")
        
        # Foydalanuvchi ma'lumoti
        user_info = f"@{order.user.username}" if order.user and order.user.username else f"ID: {order.user_id}"
        
        text = f"""
{status_emoji} *BUYURTMA #{order.id}*
{'─' * 30}

👤 *Mijoz:* {user_info}
📞 *Telefon:* {format_phone_for_display(order.phone)}
📍 *Lokatsiya:* [Xarita]({order.location_link})
📅 *Vaqt:* {order.created_at.strftime('%d.%m.%Y %H:%M')}

📦 *Mahsulotlar:*
{items_text}
{'─' * 30}
💰 *Jami:* {format_price(total)} so'm
📋 *Holat:* {order.status}
        """
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="⚙️ Jarayonga", callback_data=f"order_process_{order.id}"),
                InlineKeyboardButton(text="✅ Tayyor", callback_data=f"order_ready_{order.id}")
            ],
            [
                InlineKeyboardButton(text="📦 Yetkazildi", callback_data=f"order_delivered_{order.id}"),
                InlineKeyboardButton(text="❌ Bekor", callback_data=f"order_cancel_{order.id}")
            ]
        ])
        
        await message.answer(text, parse_mode="Markdown", reply_markup=kb, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Buyurtma detallarini ko'rsatishda xato: {e}")

@router.callback_query(F.data.startswith("order_"))
async def order_action(callback: CallbackQuery, state: FSMContext):
    """Buyurtma ustida amallar"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    
    try:
        action, order_id = callback.data.split("_")[1], int(callback.data.split("_")[2])
        
        if action == "process":
            async with AsyncSessionLocal() as session:
                order = await session.get(Order, order_id)
                if order:
                    order.status = "processing"
                    await session.commit()
                    
                    # Foydalanuvchiga xabar
                    if order.user and order.user.telegram_id:
                        try:
                            await callback.bot.send_message(
                                order.user.telegram_id,
                                f"⚙️ *Buyurtmangiz #{order.id} tayyorlanmoqda!*\n\nTez orada tayyor bo'ladi.",
                                parse_mode="Markdown"
                            )
                        except:
                            pass
                    
                    await callback.answer("✅ Buyurtma jarayonga o'tkazildi")
            
        elif action == "ready":
            await state.update_data(order_id=order_id)
            await callback.message.edit_text(
                "📞 *Kuryer telefon raqamini kiriting:*\n\nFormat: `+998 XX XXX XX XX`",
                parse_mode="Markdown"
            )
            await state.set_state(CourierState.waiting_for_courier_phone)
            await callback.answer()
            return
            
        elif action == "delivered":
            async with AsyncSessionLocal() as session:
                order = await session.get(Order, order_id)
                if order:
                    order.status = "delivered"
                    await session.commit()
                    
                    # Foydalanuvchiga xabar
                    if order.user and order.user.telegram_id:
                        try:
                            await callback.bot.send_message(
                                order.user.telegram_id,
                                f"✅ *Buyurtmangiz #{order.id} yetkazildi!*\n\nXaridingiz uchun rahmat!",
                                parse_mode="Markdown"
                            )
                        except:
                            pass
                    
                    await callback.answer("✅ Buyurtma yetkazildi deb belgilandi")
            
        elif action == "cancel":
            await state.update_data(order_id=order_id)
            await callback.message.edit_text(
                "📝 *Bekor qilish sababini kiriting:*",
                parse_mode="Markdown"
            )
            await state.set_state(CourierState.waiting_for_cancel_reason)
            await callback.answer()
            return
        
        # Buyurtmalar ro'yxatiga qaytish
        await list_orders(callback.message, None)
        await callback.message.delete()
        
    except Exception as e:
        logger.error(f"Buyurtma amalida xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.message(CourierState.waiting_for_courier_phone)
async def courier_phone_received(message: types.Message, state: FSMContext):
    """Kuryer telefon raqamini qabul qilish"""
    try:
        from bot.utils.helpers import validate_uz_phone, format_phone_for_display
        
        phone = message.text.strip()
        is_valid, cleaned = validate_uz_phone(phone)
        
        if not is_valid:
            await message.answer(
                "❌ *Noto'g'ri format.*\n\n"
                "Iltimos, telefon raqamni `+998 XX XXX XX XX` formatida kiriting.",
                parse_mode="Markdown"
            )
            return
        
        data = await state.get_data()
        order_id = data['order_id']
        
        # AsyncSession ni to'g'ri ishlatish
        async with AsyncSessionLocal() as session:
            order = await session.get(Order, order_id)
            if order:
                order.status = "ready"
                await session.commit()
                
                # Foydalanuvchiga xabar
                if order.user and order.user.telegram_id:
                    try:
                        await message.bot.send_message(
                            order.user.telegram_id,
                            f"✅ *Buyurtmangiz #{order.id} tayyor!*\n\n"
                            f"📞 *Kuryer telefon raqami:* {format_phone_for_display(cleaned)}\n\n"
                            f"U bilan bog'lanib, yetib kelish vaqtini bilib oling.",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logger.error(f"Foydalanuvchiga xabar yuborishda xato: {e}")
        
        await message.answer(
            f"✅ Buyurtma tayyor deb belgilandi va foydalanuvchiga xabar yuborildi.\n\n"
            f"📞 Kuryer raqami: {format_phone_for_display(cleaned)}",
            parse_mode="Markdown"
        )
        await state.clear()
        
        # Buyurtmalar ro'yxatiga qaytish
        await list_orders(message, None)
        
    except Exception as e:
        logger.error(f"Kuryer raqamini qabul qilishda xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        await state.clear()

@router.message(CourierState.waiting_for_cancel_reason)
async def cancel_reason_received(message: types.Message, state: FSMContext):
    """Bekor qilish sababini qabul qilish"""
    try:
        reason = message.text.strip()
        data = await state.get_data()
        order_id = data['order_id']
        
        async with AsyncSessionLocal() as session:
            order = await session.get(Order, order_id)
            if order:
                order.status = "cancelled"
                await session.commit()
                
                # Foydalanuvchiga xabar
                if order.user and order.user.telegram_id:
                    try:
                        await message.bot.send_message(
                            order.user.telegram_id,
                            f"❌ *Buyurtmangiz #{order.id} bekor qilindi.*\n\n"
                            f"📝 *Sabab:* {reason}\n\n"
                            f"Batafsil ma'lumot uchun admin bilan bog'lanishingiz mumkin.",
                            parse_mode="Markdown"
                        )
                    except:
                        pass
        
        await message.answer(
            f"✅ Buyurtma bekor qilindi va foydalanuvchiga xabar yuborildi.\n\n"
            f"📝 Sabab: {reason}",
            parse_mode="Markdown"
        )
        await state.clear()
        
        # Buyurtmalar ro'yxatiga qaytish
        await list_orders(message, None)
        
    except Exception as e:
        logger.error(f"Bekor qilish sababini qabul qilishda xato: {e}")
        await message.answer("❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        await state.clear()

# ==================== FOYDALANUVCHILAR ====================

@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    """Foydalanuvchilar bo'limi"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    
    try:
        async with AsyncSessionLocal() as session:
            total_users = await session.execute(select(func.count(User.id)))
            total_users = total_users.scalar()
            
            active_today = await session.execute(
                select(func.count(User.id)).where(
                    User.updated_at >= datetime.utcnow() - timedelta(days=1)
                )
            )
            active_today = active_today.scalar()
            
            new_today = await session.execute(
                select(func.count(User.id)).where(
                    User.created_at >= datetime.utcnow() - timedelta(days=1)
                )
            )
            new_today = new_today.scalar()
        
        text = f"""
👥 *FOYDALANUVCHILAR BOSHQARMASI*
{'═' * 30}

📊 *Statistika:*
• Jami foydalanuvchilar: {total_users} ta
• Yangi (24 soat): {new_today} ta
• Faol (24 soat): {active_today} ta

Quyidagi tugmalardan birini tanlang:
        """
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Barcha foydalanuvchilar", callback_data="admin_users_list_1")],
            [InlineKeyboardButton(text="🔍 Qidirish", callback_data="admin_users_search")],
            [InlineKeyboardButton(text="📊 Batafsil statistika", callback_data="admin_users_stats")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]
        ])
        
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Foydalanuvchilar bo'limida xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data.startswith("admin_users_list_"))
async def admin_users_list(callback: CallbackQuery):
    """Foydalanuvchilar ro'yxati"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    
    try:
        page = int(callback.data.split("_")[3])
        per_page = 10
        offset = (page - 1) * per_page
        
        async with AsyncSessionLocal() as session:
            total = await session.execute(select(func.count(User.id)))
            total = total.scalar()
            total_pages = max((total + per_page - 1) // per_page, 1)
            
            result = await session.execute(
                select(User).order_by(User.id).limit(per_page).offset(offset)
            )
            users = result.scalars().all()
        
        lines = [f"📋 *Foydalanuvchilar* (sahifa {page}/{total_pages})"]
        
        for u in users:
            role_emoji = {
                'owner': '👑', 'admin': '🔰', 'manager': '⭐',
                'worker': '⚙️', 'diller': '💎', 'dastafka': '🔧', 'guest': '👤'
            }.get(u.role, '👤')
            
            phone = format_phone_for_display(u.phone_number) if u.phone_number else "❌"
            lines.append(
                f"\n{role_emoji} `{u.telegram_id}` | {u.full_name or '—'}\n"
                f"   📞 {phone} | 💰 {format_price(u.balance)} so'm | 👥 {u.referrals_count}"
            )
        
        # Pagination tugmalari
        buttons = []
        if page > 1:
            buttons.append(InlineKeyboardButton("⬅️", callback_data=f"admin_users_list_{page-1}"))
        
        buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
        
        if page < total_pages:
            buttons.append(InlineKeyboardButton("➡️", callback_data=f"admin_users_list_{page+1}"))
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            buttons,
            [InlineKeyboardButton(text="🔍 Qidirish", callback_data="admin_users_search")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_users")]
        ])
        
        await callback.message.edit_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Foydalanuvchilar ro'yxatida xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

# ==================== TO'LOVLAR ====================

@router.callback_query(F.data == "admin_payments")
async def admin_payments(callback: CallbackQuery):
    """To'lovlar bo'limi"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    
    try:
        from bot.utils.referral import list_pending_withdrawals
        
        pending = await list_pending_withdrawals()
        
        async with AsyncSessionLocal() as session:
            # Kunlik to'lovlar
            daily_payments = await session.execute(
                select(func.sum(Transaction.amount))
                .where(
                    Transaction.type == "withdraw",
                    Transaction.status == "approved",
                    Transaction.processed_at >= datetime.utcnow() - timedelta(days=1)
                )
            )
            daily_payments = daily_payments.scalar() or 0
            
            # Oylik to'lovlar
            monthly_payments = await session.execute(
                select(func.sum(Transaction.amount))
                .where(
                    Transaction.type == "withdraw",
                    Transaction.status == "approved",
                    Transaction.processed_at >= datetime.utcnow() - timedelta(days=30)
                )
            )
            monthly_payments = monthly_payments.scalar() or 0
        
        text = f"""
💰 *TO'LOVLAR BOSHQARMASI*
{'═' * 30}

⏳ *Kutilayotgan so'rovlar:* {len(pending)} ta
📊 *Bugun to'langan:* {format_price(daily_payments)} so'm
📅 *30 kunlik:* {format_price(monthly_payments)} so'm

Quyidagi tugmalardan birini tanlang:
        """
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⏳ Kutilayotgan ({len(pending)})", callback_data="admin_pending_withdraws")],
            [InlineKeyboardButton(text="✅ Tasdiqlangan", callback_data="admin_approved_withdraws")],
            [InlineKeyboardButton(text="📤 Eksport CSV", callback_data="admin_export_withdraws")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]
        ])
        
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"To'lovlar bo'limida xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data == "admin_pending_withdraws")
async def admin_pending_withdraws(callback: CallbackQuery):
    """Kutilayotgan to'lov so'rovlari"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    
    try:
        from bot.utils.referral import list_pending_withdrawals
        
        pending = await list_pending_withdrawals()
        
        if not pending:
            await callback.message.edit_text(
                "📭 *Kutilayotgan so'rovlar yo'q*",
                reply_markup=get_back_button("admin_payments")
            )
            await callback.answer()
            return
        
        await callback.message.delete()
        
        for tx in pending[:5]:
            async with AsyncSessionLocal() as session:
                user = await session.execute(
                    select(User).where(User.telegram_id == tx.user_telegram_id)
                )
                user = user.scalar_one_or_none()
            
            username = f"@{user.username}" if user and user.username else f"ID: {tx.user_telegram_id}"
            
            text = f"""
⏳ *PUL YECHISH SO'ROVI #{tx.id}*
{'─' * 30}

👤 *Foydalanuvchi:* {username}
💰 *Summa:* {format_price(tx.amount)} so'm
📝 *Metod:* {tx.method}
📅 *Vaqt:* {tx.created_at.strftime('%d.%m.%Y %H:%M')}
📌 *Izoh:* {tx.note or '—'}

Tasdiqlaysizmi?
            """
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm_withdraw_{tx.id}"),
                    InlineKeyboardButton(text="❌ Rad etish", callback_data=f"decline_withdraw_{tx.id}")
                ]
            ])
            
            await callback.message.answer(text, parse_mode="Markdown", reply_markup=kb)
        
        if len(pending) > 5:
            await callback.message.answer(
                f"📌 va yana {len(pending) - 5} ta so'rov...",
                reply_markup=get_back_button("admin_payments")
            )
        else:
            await callback.message.answer(
                "📌 Boshqa so'rovlar yo'q",
                reply_markup=get_back_button("admin_payments")
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Kutilayotgan to'lovlarni ko'rsatishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data.startswith("confirm_withdraw_"))
async def confirm_withdraw(callback: CallbackQuery):
    """To'lov so'rovini tasdiqlash"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    
    try:
        from bot.utils.referral import process_withdraw
        
        tx_id = int(callback.data.split("_")[2])
        result = await process_withdraw(tx_id, callback.from_user.id, approve=True)
        
        if result == "approved":
            await callback.answer("✅ So'rov tasdiqlandi", show_alert=True)
            
            # Foydalanuvchiga xabar
            async with AsyncSessionLocal() as session:
                tx = await session.get(Transaction, tx_id)
                if tx and tx.user_telegram_id:
                    try:
                        await callback.bot.send_message(
                            tx.user_telegram_id,
                            f"💰 *Pul yechish so'rovingiz tasdiqlandi!*\n\n"
                            f"📝 TX ID: `{tx_id}`\n"
                            f"💸 Summa: {format_price(tx.amount)} so'm",
                            parse_mode="Markdown"
                        )
                    except:
                        pass
        
        elif result == "insufficient_balance":
            await callback.answer("⚠️ Foydalanuvchi balansida yetarli mablag' yo'q", show_alert=True)
        
        else:
            await callback.answer("❌ Xatolik yuz berdi", show_alert=True)
        
        # To'lovlar bo'limiga qaytish
        await admin_payments(callback)
        
    except Exception as e:
        logger.error(f"To'lovni tasdiqlashda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data.startswith("decline_withdraw_"))
async def decline_withdraw(callback: CallbackQuery):
    """To'lov so'rovini rad etish"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    
    try:
        from bot.utils.referral import process_withdraw
        
        tx_id = int(callback.data.split("_")[2])
        result = await process_withdraw(tx_id, callback.from_user.id, approve=False)
        
        if result == "declined":
            await callback.answer("✅ So'rov rad etildi", show_alert=True)
            
            # Foydalanuvchiga xabar
            async with AsyncSessionLocal() as session:
                tx = await session.get(Transaction, tx_id)
                if tx and tx.user_telegram_id:
                    try:
                        await callback.bot.send_message(
                            tx.user_telegram_id,
                            f"❌ *Pul yechish so'rovingiz rad etildi.*\n\n"
                            f"📝 TX ID: `{tx_id}`\n"
                            f"📌 Batafsil ma'lumot uchun admin bilan bog'lanishingiz mumkin.",
                            parse_mode="Markdown"
                        )
                    except:
                        pass
        
        else:
            await callback.answer("❌ Xatolik yuz berdi", show_alert=True)
        
        # To'lovlar bo'limiga qaytish
        await admin_payments(callback)
        
    except Exception as e:
        logger.error(f"To'lovni rad etishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

@router.callback_query(F.data == "admin_export_withdraws")
async def admin_export_withdraws(callback: CallbackQuery):
    """To'lov so'rovlarini eksport qilish"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    
    try:
        from bot.utils.referral import list_pending_withdrawals
        
        pending = await list_pending_withdrawals()
        
        if not pending:
            await callback.answer("📭 Eksport qilish uchun so'rovlar yo'q", show_alert=True)
            return
        
        # CSV yaratish
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "User ID", "Username", "Amount", "Method", "Status", "Created At", "Note"])
        
        async with AsyncSessionLocal() as session:
            for tx in pending:
                user = await session.execute(
                    select(User).where(User.telegram_id == tx.user_telegram_id)
                )
                user = user.scalar_one_or_none()
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
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='wb') as tmp:
            tmp.write(csv_bytes)
            tmp_path = tmp.name
        
        await callback.message.answer_document(
            FSInputFile(tmp_path),
            caption=f"📊 *Withdraw so'rovlari*\n📅 {datetime.now().strftime('%d.%m.%Y')}",
            parse_mode="Markdown"
        )
        
        os.unlink(tmp_path)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Eksport qilishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

# ==================== STATISTIKA ====================

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Bot statistikasi"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    
    try:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        
        async with AsyncSessionLocal() as session:
            # Foydalanuvchilar
            total_users = await session.execute(select(func.count(User.id)))
            total_users = total_users.scalar()
            
            new_today = await session.execute(
                select(func.count(User.id)).where(User.created_at >= today_start)
            )
            new_today = new_today.scalar()
            
            new_week = await session.execute(
                select(func.count(User.id)).where(User.created_at >= week_start)
            )
            new_week = new_week.scalar()
            
            new_month = await session.execute(
                select(func.count(User.id)).where(User.created_at >= month_start)
            )
            new_month = new_month.scalar()
            
            # Buyurtmalar
            total_orders = await session.execute(select(func.count(Order.id)))
            total_orders = total_orders.scalar()
            
            orders_today = await session.execute(
                select(func.count(Order.id)).where(Order.created_at >= today_start)
            )
            orders_today = orders_today.scalar()
            
            orders_week = await session.execute(
                select(func.count(Order.id)).where(Order.created_at >= week_start)
            )
            orders_week = orders_week.scalar()
            
            # Buyurtmalar statuslari
            new_orders = await session.execute(
                select(func.count(Order.id)).where(Order.status == "new")
            )
            new_orders = new_orders.scalar()
            
            processing_orders = await session.execute(
                select(func.count(Order.id)).where(Order.status == "processing")
            )
            processing_orders = processing_orders.scalar()
            
            ready_orders = await session.execute(
                select(func.count(Order.id)).where(Order.status == "ready")
            )
            ready_orders = ready_orders.scalar()
            
            delivered_orders = await session.execute(
                select(func.count(Order.id)).where(Order.status == "delivered")
            )
            delivered_orders = delivered_orders.scalar()
            
            cancelled_orders = await session.execute(
                select(func.count(Order.id)).where(Order.status == "cancelled")
            )
            cancelled_orders = cancelled_orders.scalar()
            
            # Mahsulotlar
            total_products = await session.execute(select(func.count(Product.id)))
            total_products = total_products.scalar()
            
            total_categories = await session.execute(select(func.count(Category.id)))
            total_categories = total_categories.scalar()
        
        text = f"""
📊 *BOT STATISTIKASI*
{'═' * 30}

👥 *FOYDALANUVCHILAR*
• Jami: {total_users} ta
• Yangi (bugun): {new_today} ta
• Yangi (7 kun): {new_week} ta
• Yangi (30 kun): {new_month} ta

📦 *BUYURTMALAR*
• Jami: {total_orders} ta
• Bugun: {orders_today} ta
• 7 kun: {orders_week} ta

📋 *BUYURTMA STATUSLARI*
• 🆕 Yangi: {new_orders} ta
• ⚙️ Jarayonda: {processing_orders} ta
• ✅ Tayyor: {ready_orders} ta
• 📦 Yetkazilgan: {delivered_orders} ta
• ❌ Bekor: {cancelled_orders} ta

📦 *MAHSULOTLAR*
• Mahsulotlar: {total_products} ta
• Kategoriyalar: {total_categories} ta

{create_progress_bar(new_orders, max(1, total_orders))} Yangi buyurtmalar
        """
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Batafsil statistika", callback_data="admin_stats_detailed")],
            [InlineKeyboardButton(text="📈 Grafiklar", callback_data="admin_stats_charts")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]
        ])
        
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Statistika ko'rsatishda xato: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)

# ==================== XABAR YUBORISH ====================

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    """Ommaviy xabar yuborish"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    
    text = """
📢 *OMMAVIY XABAR YUBORISH*

Xabar turini tanlang:
    """
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Faqat matn", callback_data="broadcast_type_text")],
        [InlineKeyboardButton(text="🖼 Rasm", callback_data="broadcast_type_photo")],
        [InlineKeyboardButton(text="🎥 Video", callback_data="broadcast_type_video")],
        [InlineKeyboardButton(text="📄 Hujjat", callback_data="broadcast_type_document")],
        [InlineKeyboardButton(text="📝+🖼 Matn va rasm", callback_data="broadcast_type_text_photo")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

# ==================== SOZLAMALAR ====================

@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    """Admin sozlamalari"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    
    from bot.middlewares.maintenance import MAINTENANCE_MODE
    
    maintenance_status = "✅ Yoqilgan" if MAINTENANCE_MODE else "❌ O'chirilgan"
    
    text = f"""
⚙️ *ADMIN SOZLAMALARI*
{'═' * 30}

🛠 *Texnik rejim:* {maintenance_status}

Quyidagi sozlamalarni o'zgartirishingiz mumkin:
    """
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔧 Texnik rejimni o'zgartirish",
                callback_data="admin_toggle_maintenance"
            )
        ],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "admin_toggle_maintenance")
async def admin_toggle_maintenance(callback: CallbackQuery):
    """Texnik rejimni o'zgartirish"""
    if not is_owner(callback.from_user.id):
        await callback.answer("❌ Faqat owner bu amalni bajarishi mumkin!", show_alert=True)
        return
    
    global MAINTENANCE_MODE
    from bot.middlewares.maintenance import MAINTENANCE_MODE as imported_maintenance
    
    MAINTENANCE_MODE = not MAINTENANCE_MODE
    
    status = "YOQILDI" if MAINTENANCE_MODE else "O'CHIRILDI"
    await callback.answer(f"✅ Texnik rejim {status}", show_alert=True)
    
    # Sozlamalar bo'limiga qaytish
    await admin_settings(callback)

# ==================== ORQAGA QAYTISH ====================

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Admin panelga qaytish"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return
    
    await admin_panel(callback.message)
    await callback.answer()

@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    """Hech narsa qilmaydigan callback"""
    await callback.answer()