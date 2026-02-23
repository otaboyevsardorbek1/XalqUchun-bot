from aiogram import Router, types, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
import re
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.utils.cart import get_cart, remove_from_cart, update_cart_item_qty, clear_cart
from bot.db.models import User, Product
from bot.db.database import AsyncSessionLocal
from bot.keyboards.cart import cart_kb
from bot.keyboards.main import main_menu
from bot.states.checkout import EditCustomItem

router = Router()

@router.message(F.text == "🛒 Savat")
async def show_cart(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    cart_data = get_cart(user_id)
    if not cart_data:
        await message.answer("Savat boʻsh.")
        return

    # Mahsulot nomlarini olish (oddiy mahsulotlar uchun)
    product_ids = [pid for pid in cart_data.keys() if pid > 0]
    products = {}
    if product_ids:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Product).where(Product.id.in_(product_ids)))
            products = {p.id: p.name for p in result.scalars().all()}

    lines = []
    for item_id, item in cart_data.items():
        if item_id > 0:  # oddiy mahsulot
            name = products.get(item_id, "Noma'lum")
            lines.append(f"{name} x{item['qty']} - {item['qty']*item['price']} so'm")
        else:  # maxsus mahsulot
            name = item['name']
            lines.append(f"📦 {name} x{item['qty']} {item['unit']} (maxsus)")

    text = "Savat:\n" + "\n".join(lines)
    
    # Savat klaviaturasini yaratish (maxsus mahsulotlar uchun alohida callback)
    builder = InlineKeyboardBuilder()
    for item_id, item in cart_data.items():
        if item_id > 0:
            name = products.get(item_id, "Noma'lum")
            builder.button(text=f"❌ {name} ({item['qty']} dona)", callback_data=f"remove_{item_id}")
        else:
            builder.button(text=f"❌ {item['name']} ({item['qty']} {item['unit']})", callback_data=f"edit_custom_{item_id}")
    builder.button(text="✅ Buyurtma berish", callback_data="checkout")
    builder.button(text="⬅️ Orqaga", callback_data="back_to_main")
    builder.adjust(1)
    
    await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("remove_"))
async def remove_item(callback: CallbackQuery):
    pid = int(callback.data.split("_")[1])
    remove_from_cart(callback.from_user.id, pid)
    await callback.answer("Mahsulot olib tashlandi")
    # Savatni qayta ko'rsatish
    await callback.message.delete()
    await show_cart(callback.message, state=None)  # state ni uzatish kerak emas

@router.callback_query(F.data.startswith("edit_custom_"))
async def edit_custom_item(callback: CallbackQuery, state: FSMContext):
    custom_id = int(callback.data.split("_")[2])  # edit_custom_-1
    cart = get_cart(callback.from_user.id)
    item = cart.get(custom_id)
    if not item:
        await callback.answer("Mahsulot topilmadi")
        return
    
    await state.update_data(edit_item_id=custom_id, edit_item_name=item['name'], edit_item_unit=item['unit'])
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"edit_delete_{custom_id}")],
        [InlineKeyboardButton(text="✏️ Miqdorni o'zgartirish", callback_data=f"edit_qty_{custom_id}")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_cart")]
    ])
    await callback.message.edit_text(
        f"Mahsulot: {item['name']}\n"
        f"Hozirgi miqdor: {item['qty']} {item['unit']}\n\n"
        "Nima qilmoqchisiz?",
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(F.data.startswith("edit_delete_"))
async def edit_delete_item(callback: CallbackQuery):
    custom_id = int(callback.data.split("_")[2])
    remove_from_cart(callback.from_user.id, custom_id)
    await callback.answer("Mahsulot o'chirildi")
    # Savatga qaytish
    await callback.message.delete()
    await show_cart(callback.message, state=None)

@router.callback_query(F.data.startswith("edit_qty_"))
async def edit_qty_start(callback: CallbackQuery, state: FSMContext):
    custom_id = int(callback.data.split("_")[2])
    await state.update_data(edit_item_id=custom_id)
    await callback.message.edit_text(
        "Yangi miqdorni kiriting (son va birlik bilan, masalan: 2 kg, 1.5 dona):"
    )
    await state.set_state(EditCustomItem.waiting_for_new_quantity)
    await callback.answer()

@router.message(EditCustomItem.waiting_for_new_quantity)
async def edit_qty_received(message: types.Message, state: FSMContext):
    text = message.text.strip()
    pattern = r'^(\d+(?:[.,]\d+)?)\s*(kg|dona|litr|gr|gramm|kilogram|gram|l)$'
    match = re.match(pattern, text, re.IGNORECASE)
    if not match:
        await message.answer("❌ Noto'g'ri format. Iltimos, son va birlikni kiriting (masalan: 2 kg)")
        return
    
    qty_str = match.group(1).replace(',', '.')
    try:
        qty = float(qty_str)
    except ValueError:
        await message.answer("❌ Noto'g'ri son")
        return
    unit = match.group(2).lower()
    
    data = await state.get_data()
    item_id = data['edit_item_id']
    
    # Yangilash
    update_cart_item_qty(message.from_user.id, item_id, qty)
    # Birlikni ham yangilash kerak bo'lsa, lekin hozir unit o'zgarmaydi, faqat qty
    # Agar unit o'zgarishi mumkin bo'lsa, uni ham yangilash kerak, lekin hozircha qoldiramiz
    
    await message.answer("✅ Miqdor yangilandi.")
    await state.clear()
    # Savatni ko'rsatish
    await show_cart(message, state=None)

@router.callback_query(F.data == "back_to_cart")
async def back_to_cart(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await show_cart(callback.message, state=None)

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Asosiy menyu:", reply_markup=main_menu)