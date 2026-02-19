from bot.data import ADMIN_IDS
# from bot.config import ADMIN_IDS

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def is_owner(user_id: int) -> bool:
    from bot.data import OWNER_ID
    return user_id == OWNER_ID