import json
import os
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from config import AUCTION_FILE, file_locks, logger, AUCTION_CONFIG, AUCTION_CARS

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
    # Фильтруем только активные и непроданные лоты
    active_lots = [
        lot for lot in lots 
        if lot.get("is_active", True) and not lot.get("sold", False)
    ]
    return active_lots

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

async def get_lot_by_index(index: int) -> Optional[Dict]:
    """Возвращает лот по индексу"""
    lots = await get_active_lots()
    if 0 <= index < len(lots):
        return lots[index]
    return None

def get_stars_display(stars: int) -> str:
    """Возвращает строку звёзд для отображения"""
    return "⭐" * stars + "☆" * (5 - stars)

def get_rarity_color(rarity: str) -> str:
    """Возвращает цвет для редкости"""
    colors = {
        "Экзотическая": "🟣",
        "Легендарная": "🟠",
        "Очень редкая": "🔴",
        "Редкая": "🟡",
        "Доступная": "🟢"
    }
    return colors.get(rarity, "⚪")
