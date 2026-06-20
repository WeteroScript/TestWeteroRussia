import random
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from config import AUCTION_CARS, AUCTION_CONFIG, bot, logger
from database.file_manager import load_users, save_users
from database.file_manager import load_auction_data, save_auction_data, get_active_lots, update_lot_status
from utils.helpers import is_function_disabled

# Глобальные переменные
auction_running = False
auction_update_task: Optional[asyncio.Task] = None
auction_timers: Dict[int, asyncio.Task] = {}

# Редкости для отображения звёзд
RARITY_STARS = {
    "Экзотическая": "★★★★★",
    "Легендарная": "★★★★☆",
    "Очень редкая": "★★★☆☆",
    "Редкая": "★★☆☆☆",
    "Доступная": "★☆☆☆☆"
}

# Шансы появления на аукционе
RARITY_CHANCES = {
    "Экзотическая": 0.005,  # 0.5%
    "Легендарная": 0.05,    # 5%
    "Очень редкая": 0.01,   # 1%
    "Редкая": 0.30,         # 30%
    "Доступная": 0.50       # 50%
}

def get_stars_by_rarity(rarity: str) -> str:
    return RARITY_STARS.get(rarity, "★☆☆☆☆")

def get_stars_display(stars: int) -> str:
    return "⭐" * stars + "☆" * (5 - stars)

def generate_auction_lots(count: int = 15) -> List[Dict]:
    """Генерирует список лотов для аукциона"""
    lots = []
    
    # Собираем все машины из AUCTION_CARS
    available_cars = []
    for car_name, car_data in AUCTION_CARS.items():
        rarity = car_data.get("rarity", "Доступная")
        chance = RARITY_CHANCES.get(rarity, 0.01)
        available_cars.append((car_name, car_data, chance))
    
    # Выбираем машины с учётом шансов
    selected_cars = []
    attempts = 0
    while len(selected_cars) < count and attempts < 1000:
        attempts += 1
        total_weight = sum(chance for _, _, chance in available_cars)
        if total_weight == 0:
            break
            
        rand = random.random() * total_weight
        cumulative = 0
        for car_name, car_data, chance in available_cars:
            cumulative += chance
            if rand <= cumulative:
                if (car_name, car_data) not in selected_cars:
                    selected_cars.append((car_name, car_data))
                break
    
    # Если машин меньше чем нужно, добираем случайными
    while len(selected_cars) < count and available_cars:
        car_name, car_data, _ = random.choice(available_cars)
        if (car_name, car_data) not in selected_cars:
            selected_cars.append((car_name, car_data))
    
    # Создаём лоты
    for car_name, car_data in selected_cars[:count]:
        base_price = car_data.get("base_price", 1000000)
        start_bid = car_data.get("start_bid", int(base_price * random.uniform(0.3, 0.6)))
        start_bid = max(start_bid, 100000)
        
        lots.append({
            "car_name": car_name,
            "car_data": car_data,
            "start_bid": start_bid,
            "current_bid": start_bid,
            "current_bidder": None,
            "stars": car_data.get("stars", 1),
            "rarity": car_data.get("rarity", "Доступная"),
            "last_bid_time": datetime.now().isoformat(),
            "is_active": True,
            "sold": False,
            "added_by_admin": False
        })
    
    return lots

async def update_auction_lots(force: bool = False):
    """Обновляет список лотов аукциона"""
    global auction_timers
    
    # Загружаем текущие данные
    data = await load_auction_data()
    lots = data.get("lots", [])
    
    # Проверяем и удаляем проданные лоты (если не force)
    if not force:
        lots = [lot for lot in lots if not lot.get("sold", False)]
    
    # Если лотов меньше 15 или force, добавляем новые
    if len(lots) < AUCTION_CONFIG["max_lots"] or force:
        # Очищаем старые таймеры
        for timer in auction_timers.values():
            timer.cancel()
        auction_timers.clear()
        
        new_lots = generate_auction_lots(AUCTION_CONFIG["max_lots"])
        
        if force:
            lots = new_lots
        else:
            # Добавляем новые лоты, сохраняя старые активные
            existing_names = [lot["car_name"] for lot in lots]
            for new_lot in new_lots:
                if new_lot["car_name"] not in existing_names:
                    lots.append(new_lot)
                    existing_names.append(new_lot["car_name"])
            
            # Обрезаем до максимального количества
            lots = lots[:AUCTION_CONFIG["max_lots"]]
    
    # Сохраняем
    data["lots"] = lots
    data["last_update"] = datetime.now().isoformat()
    await save_auction_data(data)
    
    # Запускаем таймеры для активных лотов
    for i, lot in enumerate(lots):
        if lot.get("is_active", True) and not lot.get("sold", False):
            await start_auction_timer(i)
    
    logger.info(f"🔄 Аукцион обновлён. Лотов: {len(lots)}")

async def auction_update_loop():
    """Цикл обновления аукциона каждые 30 минут"""
    global auction_running
    while auction_running:
        try:
            await update_auction_lots()
        except Exception as e:
            logger.error(f"❌ Ошибка обновления аукциона: {e}")
        await asyncio.sleep(AUCTION_CONFIG["update_interval"])

async def place_bid(user_id: str, lot_index: int, amount: int) -> Tuple[bool, str]:
    """Размещает ставку на лот"""
    # Проверяем, не отключена ли функция аукциона
    if await is_function_disabled("menubutton_11"):
        return False, "⛔ Аукцион временно остановлен администратором!"
    
    lots = await get_active_lots()
    
    if lot_index < 0 or lot_index >= len(lots):
        return False, "❌ Лот не найден!"
    
    lot = lots[lot_index]
    
    if not lot.get("is_active", True) or lot.get("sold", False):
        return False, "❌ Этот лот уже продан или неактивен!"
    
    if amount <= lot["current_bid"]:
        return False, f"❌ Ставка должна быть выше текущей ({lot['current_bid']:,}₽)!"
    
    # Проверяем баланс пользователя
    users = await load_users()
    if user_id not in users:
        return False, "❌ Пользователь не найден!"
    
    if users[user_id]["money"] < amount:
        return False, f"❌ Недостаточно средств! У вас {users[user_id]['money']:,}₽"
    
    # Обновляем ставку в данных
    data = await load_auction_data()
    all_lots = data.get("lots", [])
    
    # Находим реальный индекс в полном списке
    real_index = None
    current_active = 0
    for i, l in enumerate(all_lots):
        if not l.get("sold", False) and l.get("is_active", True):
            if current_active == lot_index:
                real_index = i
                break
            current_active += 1
    
    if real_index is None:
        return False, "❌ Ошибка: лот не найден!"
    
    # Обновляем лот
    all_lots[real_index]["current_bid"] = amount
    all_lots[real_index]["current_bidder"] = user_id
    all_lots[real_index]["last_bid_time"] = datetime.now().isoformat()
    
    await save_auction_data(data)
    
    # Перезапускаем таймер
    await start_auction_timer(real_index)
    
    return True, f"✅ Ставка {amount:,}₽ принята!"

async def start_auction_timer(lot_index: int):
    """Запускает таймер для лота"""
    global auction_timers
    
    # Отменяем старый таймер
    if lot_index in auction_timers:
        auction_timers[lot_index].cancel()
    
    # Создаём новый таймер
    auction_timers[lot_index] = asyncio.create_task(
        auction_timer(lot_index)
    )

async def auction_timer(lot_index: int):
    """Таймер ожидания перебития ставки (15 минут)"""
    try:
        await asyncio.sleep(AUCTION_CONFIG["bid_timeout"])
        
        # Загружаем актуальные данные
        data = await load_auction_data()
        lots = data.get("lots", [])
        
        if lot_index >= len(lots):
            return
        
        lot = lots[lot_index]
        if lot.get("sold", False) or not lot.get("is_active", True):
            return
        
        # Проверяем, есть ли победитель
        user_id = lot.get("current_bidder")
        if user_id:
            car_name = lot["car_name"]
            final_price = lot["current_bid"]
            
            # Добавляем машину в гараж пользователя
            users = await load_users()
            if user_id in users:
                # Проверяем достаточно ли денег
                if users[user_id]["money"] < final_price:
                    # Недостаточно денег - лот уходит обратно на аукцион
                    lot["current_bidder"] = None
                    lot["is_active"] = True
                    await save_auction_data(data)
                    await save_users(users)
                    return
                
                # Списываем деньги
                users[user_id]["money"] -= final_price
                
                # Добавляем машину в инвентарь
                if "inventory" not in users[user_id]:
                    users[user_id]["inventory"] = []
                
                users[user_id]["inventory"].append({
                    "name": car_name,
                    "price": AUCTION_CARS.get(car_name, {}).get("base_price", 0),
                    "from_auction": True,
                    "bought_at": final_price
                })
                
                await save_users(users)
                
                # Отмечаем лот как проданный
                lot["sold"] = True
                lot["is_active"] = False
                await save_auction_data(data)
                
                # Уведомляем пользователя
                try:
                    await bot.send_message(
                        int(user_id),
                        f"🎉 ВЫ ВЫИГРАЛИ АУКЦИОН!\n\n"
                        f"🚗 {car_name}\n"
                        f"⭐ {get_stars_display(lot['stars'])} {lot['rarity']}\n"
                        f"💰 Цена: {final_price:,}₽\n\n"
                        f"Машина добавлена в ваш гараж!"
                    )
                except Exception as e:
                    logger.warning(f"Не удалось уведомить пользователя {user_id}: {e}")
                
                logger.info(f"✅ Машина {car_name} продана пользователю {user_id} за {final_price:,}₽")
        
        # Удаляем таймер
        if lot_index in auction_timers:
            del auction_timers[lot_index]
            
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"❌ Ошибка в auction_timer: {e}")

async def get_auction_lots_for_display() -> List[Dict]:
    """Возвращает список лотов для отображения пользователю"""
    return await get_active_lots()

async def set_admin_auction_lots(car_name: str, start_bid: int, count: int = 1) -> Tuple[bool, str]:
    """Устанавливает лоты от админа"""
    if car_name not in AUCTION_CARS:
        return False, f"❌ Машина '{car_name}' не найдена!"
    
    car_data = AUCTION_CARS[car_name]
    
    # Создаём лоты
    new_lots = []
    for _ in range(count):
        new_lots.append({
            "car_name": car_name,
            "car_data": car_data,
            "start_bid": start_bid,
            "current_bid": start_bid,
            "current_bidder": None,
            "stars": car_data.get("stars", 1),
            "rarity": car_data.get("rarity", "Доступная"),
            "last_bid_time": datetime.now().isoformat(),
            "is_active": True,
            "sold": False,
            "added_by_admin": True
        })
    
    # Загружаем текущие данные
    data = await load_auction_data()
    lots = data.get("lots", [])
    
    # Удаляем старые проданные лоты
    lots = [lot for lot in lots if not lot.get("sold", False)]
    
    # Добавляем новые лоты
    lots.extend(new_lots)
    
    # Обрезаем до максимума
    lots = lots[:AUCTION_CONFIG["max_lots"]]
    
    data["lots"] = lots
    data["last_update"] = datetime.now().isoformat()
    await save_auction_data(data)
    
    return True, f"✅ Добавлено {count} шт. {car_name} на аукцион!"

async def refresh_auction_for_all():
    """Обновляет аукцион для всех пользователей"""
    await update_auction_lots(force=True)
    return True, "✅ Аукцион обновлён для всех пользователей!"
