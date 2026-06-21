import json
import os
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from config import (
    USERS_FILE, PROMOCODES_FILE, INVENTORY_FILE, 
    SETTINGS_FILE, BUSINESS_FILE,
    DISABLED_FUNCTIONS_FILE, AUCTION_FILE, file_locks, logger
)

# ========== ДЕФОЛТНЫЙ ПОЛЬЗОВАТЕЛЬ ==========
def get_default_user():
    return {
        "money": 1000000,
        "brcoins": 1000,
        "energy": 100,
        "total_earned": 0,
        "trades_count": 0,
        "role": "user",
        "donate_spent": 0,
        "donate_received": 0,
        "inventory": [],
        "mine_attempts": 100,
        "last_mine_reset": datetime.now().isoformat(),
        "portfolio": {
            "BTC": 0,
            "WETcoin": 0,
            "NotCoin": 0
        },
        "business": {
            "auto_mine": {"owned": False, "last_collect": None, "auto_collect": False},
            "tech_center": {"owned": False, "last_collect": None, "auto_collect": False},
            "tire_center": {"owned": False, "last_collect": None, "auto_collect": False},
            "styling_center": {"owned": False, "last_collect": None, "auto_collect": False},
            "shop_24": {"owned": False, "last_collect": None, "auto_collect": False}
        },
        "farm": {
            "milk": 0,
            "hay": 0,
            "eggs": 0,
            "wheat": 0,
            "meat": 0,
            "last_collect": None
        },
        "casino": {
            "bet": 0,
            "mines_count": 4,
            "field_size": 5
        },
        "banned": False
    }

# ========== USERS ==========
async def load_users():
    async with file_locks['users']:
        try:
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при загрузке users: {e}")
        return {}

async def save_users(users):
    async with file_locks['users']:
        try:
            os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
            with open(USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Ошибка при сохранении users: {e}")

# ========== PROMOCODES ==========
async def load_promocodes():
    async with file_locks['promocodes']:
        try:
            if os.path.exists(PROMOCODES_FILE):
                with open(PROMOCODES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при загрузке promocodes: {e}")
        return {}

async def save_promocodes(promocodes):
    async with file_locks['promocodes']:
        try:
            os.makedirs(os.path.dirname(PROMOCODES_FILE), exist_ok=True)
            with open(PROMOCODES_FILE, 'w', encoding='utf-8') as f:
                json.dump(promocodes, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Ошибка при сохранении promocodes: {e}")

# ========== INVENTORY ==========
async def load_inventory():
    async with file_locks['inventory']:
        try:
            if os.path.exists(INVENTORY_FILE):
                with open(INVENTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при загрузке inventory: {e}")
        return {}

async def save_inventory(inventory):
    async with file_locks['inventory']:
        try:
            os.makedirs(os.path.dirname(INVENTORY_FILE), exist_ok=True)
            with open(INVENTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(inventory, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Ошибка при сохранении inventory: {e}")

# ========== SETTINGS ==========
async def load_settings():
    async with file_locks['settings']:
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при загрузке settings: {e}")
        return {
            "bot_enabled": True,
            "promo_auto": False,
            "coinrun_enabled": False,
            "coinrun_total": 0
        }

async def save_settings(settings):
    async with file_locks['settings']:
        try:
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Ошибка при сохранении settings: {e}")

# ========== BUSINESS ==========
async def load_business():
    async with file_locks['business']:
        try:
            if os.path.exists(BUSINESS_FILE):
                with open(BUSINESS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при загрузке business: {e}")
        return {}

async def save_business(business):
    async with file_locks['business']:
        try:
            os.makedirs(os.path.dirname(BUSINESS_FILE), exist_ok=True)
            with open(BUSINESS_FILE, 'w', encoding='utf-8') as f:
                json.dump(business, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Ошибка при сохранении business: {e}")

# ========== DISABLED FUNCTIONS ==========
async def load_disabled_functions():
    async with file_locks['disabled_functions']:
        try:
            if os.path.exists(DISABLED_FUNCTIONS_FILE):
                with open(DISABLED_FUNCTIONS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при загрузке disabled_functions: {e}")
        return {"functions": []}

async def save_disabled_functions(disabled):
    async with file_locks['disabled_functions']:
        try:
            os.makedirs(os.path.dirname(DISABLED_FUNCTIONS_FILE), exist_ok=True)
            with open(DISABLED_FUNCTIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(disabled, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Ошибка при сохранении disabled_functions: {e}")

# ========== AUCTION ==========
async def load_auction_data() -> Dict:
    """Загружает данные аукциона из файла"""
    async with file_locks['auction']:
        try:
            if os.path.exists(AUCTION_FILE):
                with open(AUCTION_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при загрузке auction: {e}")
        return {"lots": [], "last_update": None}

async def save_auction_data(data: Dict):
    """Сохраняет данные аукциона в файл"""
    async with file_locks['auction']:
        try:
            os.makedirs(os.path.dirname(AUCTION_FILE), exist_ok=True)
            with open(AUCTION_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Ошибка при сохранении auction: {e}")

async def get_active_lots() -> List[Dict]:
    """Возвращает активные лоты аукциона"""
    data = await load_auction_data()
    lots = data.get("lots", [])
    active_lots = [
        lot for lot in lots 
        if lot.get("is_active", True) and not lot.get("sold", False)
    ]
    return active_lots

async def get_lot_by_index(index: int) -> Optional[Dict]:
    """Возвращает лот по индексу"""
    lots = await get_active_lots()
    if 0 <= index < len(lots):
        return lots[index]
    return None

async def update_lot_status(lot_index: int, sold: bool = True):
    """Обновляет статус лота"""
    data = await load_auction_data()
    lots = data.get("lots", [])
    if 0 <= lot_index < len(lots):
        lots[lot_index]["sold"] = sold
        lots[lot_index]["is_active"] = not sold
        await save_auction_data(data)
        return True
    return False

async def set_auction_lots(lots: List[Dict]):
    """Устанавливает список лотов (для админов)"""
    data = await load_auction_data()
    data["lots"] = lots
    data["last_update"] = datetime.now().isoformat()
    await save_auction_data(data)
