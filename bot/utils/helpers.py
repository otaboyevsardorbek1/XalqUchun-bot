# bot/utils/helpers.py
import re
import random
import string
from datetime import datetime
from typing import Dict, Dict, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

def generate_order_number() -> str:
    """Unikal buyurtma raqamini generatsiya qilish"""
    timestamp = datetime.now().strftime("%y%m%d")
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD-{timestamp}-{random_part}"

def generate_transaction_number() -> str:
    """Unikal tranzaksiya raqamini generatsiya qilish"""
    timestamp = datetime.now().strftime("%y%m%d%H%M")
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"TXN-{timestamp}-{random_part}"

def validate_uz_phone(phone: str) -> Tuple[bool, Optional[str]]:
    """O'zbekiston telefon raqamini tekshirish va normallashtirish"""
    if not phone:
        return False, None
    
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # +998 XX XXX XX XX format
    if re.match(r'^\+998\d{9}$', cleaned):
        return True, cleaned
    
    # 998 XX XXX XX XX format
    if re.match(r'^998\d{9}$', cleaned):
        return True, '+' + cleaned
    
    # 9 ta raqam (XX XXX XX XX)
    if re.match(r'^\d{9}$', cleaned):
        return True, '+998' + cleaned
    
    return False, None

def format_phone_for_display(phone: str) -> str:
    """Telefon raqamni chiroyli formatda ko'rsatish"""
    if not phone:
        return "❌"
    
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    if cleaned.startswith('+998') and len(cleaned) == 13:
        return f"+998 {cleaned[4:6]} {cleaned[6:9]}-{cleaned[9:11]}-{cleaned[11:13]}"
    
    return phone

def format_price(price: float) -> str:
    """Narxni formatlash"""
    return f"{price:,.0f}".replace(',', ' ')

def parse_product_line(line: str) -> Optional[Dict[str, any]]:
    """Mahsulot qatorini parse qilish"""
    # Pattern: Product Name - quantity unit
    patterns = [
        # Asosiy pattern
        r'^([A-Za-zА-Яа-я0-9\s\-\(\)\[\]]+?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*([A-Za-zА-Яа-я]+)$',
        # Vergul bilan ajratilgan
        r'^([^,]+?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*([^,\s]+)',
    ]
    
    line = line.strip()
    
    for pattern in patterns:
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            quantity_str = match.group(2).replace(',', '.')
            unit = match.group(3).strip().lower()
            
            try:
                quantity = float(quantity_str)
                if quantity.is_integer():
                    quantity = int(quantity)
                
                return {
                    'name': name,
                    'quantity': quantity,
                    'unit': unit
                }
            except ValueError:
                continue
    
    return None

def parse_multiple_products(text: str) -> Tuple[List[Dict], List[str]]:
    """Bir nechta mahsulotlarni parse qilish"""
    products = []
    errors = []
    
    # Avval qatorlarga ajratamiz
    lines = text.split('\n')
    
    for line_idx, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        
        # Vergul bilan ajratilgan bo'lishi mumkin
        parts = line.split(',')
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            product = parse_product_line(part)
            if product:
                products.append(product)
            else:
                errors.append(f"Qator {line_idx}: {part}")
    
    return products, errors

def unit_map() -> Dict[str, str]:
    """Birliklar mapping"""
    return {
        # Og'irlik
        'kg': 'kg', 'kilogram': 'kg', 'kilogramm': 'kg', 'kilo': 'kg',
        'gramm': 'gr', 'gram': 'gr', 'gr': 'gr', 'g': 'gr',
        'tonna': 'tonna', 'ton': 'tonna', 't': 'tonna', 'т': 'tonna',
        
        # Hajm
        'l': 'litr', 'litr': 'litr', 'liter': 'litr', 'л': 'litr',
        'ml': 'ml', 'millilitr': 'ml', 'milliliter': 'ml',
        
        # Uzunlik
        'metr': 'metr', 'meter': 'metr', 'm': 'metr', 'м': 'metr',
        'sm': 'sm', 'santimetr': 'sm', 'centimeter': 'sm',
        
        # Soniya
        'dona': 'dona', 'dono': 'dona', 'та': 'dona', 'шт': 'dona', 
        'штук': 'dona', 'piece': 'dona', 'pcs': 'dona',
        
        # O'ram
        'quti': 'quti', 'box': 'quti', 'korobka': 'quti',
        'paket': 'paket', 'pack': 'paket', 'пaket': 'paket',
        
        # Suyuqlik idishi
        'butilka': 'butilka', 'bottle': 'butilka',
        'bank': 'bank', 'jar': 'bank', 'банка': 'bank',
        
        # Boshqa
        'juft': 'juft', 'pair': 'juft',
        'komplekt': 'komplekt', 'set': 'komplekt',
        'list': 'list', 'sheet': 'list',
        'rulon': 'rulon', 'roll': 'rulon'
    }

def normalize_unit(unit: str) -> str:
    """Birlikni normallashtirish"""
    unit_map_dict = unit_map()
    return unit_map_dict.get(unit.lower(), unit)

def create_progress_bar(current: int, total: int, length: int = 20) -> str:
    """Progress bar yaratish"""
    filled = int(length * current / total)
    empty = length - filled
    return f"[{'█' * filled}{'░' * empty}]"