import os
import asyncio
import logging
from datetime import datetime

# ========== ЛОГИРОВАНИЕ ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== КОНФИГУРАЦИЯ ==========
API_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [5877790074, 1218587495]
CHANNEL_ID = "-1004461974511"
PROMO_CHANNEL_ID = "-1003853479476"

if not API_TOKEN:
    raise ValueError("❌ BOT_TOKEN не установлен в переменных окружения!")

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ========== ПУТИ К ФАЙЛАМ ==========
DATA_DIR = os.getenv('SHARED_DIR', '/app/shared')
if not os.path.exists(DATA_DIR):
    DATA_DIR = '.'

USERS_FILE = os.path.join(DATA_DIR, 'users_data.json')
PROMOCODES_FILE = os.path.join(DATA_DIR, 'promocodes.json')
INVENTORY_FILE = os.path.join(DATA_DIR, 'inventory.json')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')
BUSINESS_FILE = os.path.join(DATA_DIR, 'business.json')
DISABLED_FUNCTIONS_FILE = os.path.join(DATA_DIR, 'disabled_functions.json')

os.makedirs(DATA_DIR, exist_ok=True)

# ========== ФАЙЛОВЫЕ БЛОКИРОВКИ ==========
file_locks = {
    'users': asyncio.Lock(),
    'promocodes': asyncio.Lock(),
    'inventory': asyncio.Lock(),
    'settings': asyncio.Lock(),
    'business': asyncio.Lock(),
    'disabled_functions': asyncio.Lock()
}

# ========== КОНСТАНТЫ ДЛЯ ШАХТЫ ==========
MINE_RESOURCES = [
    {"name": "Красный алмаз", "price": 50000000000, "chance": 0.0005},
    {"name": "Цветной алмаз", "price": 10000000000, "chance": 0.001},
    {"name": "Красная шпинель", "price": 5000000000, "chance": 0.004},
    {"name": "Александрит", "price": 2500000000, "chance": 0.007},
    {"name": "Рубин", "price": 1500000000, "chance": 0.015},
    {"name": "Падпараджа", "price": 750000000, "chance": 0.05},
    {"name": "Демантоид", "price": 150000000, "chance": 0.10},
    {"name": "Черный опал", "price": 10000000, "chance": 0.20},
    {"name": "Танзанит", "price": 5000000, "chance": 0.25},
    {"name": "Шпинель", "price": 1500000, "chance": 0.30}
]

FARM_RESOURCES = [
    {"name": "Молоко", "price": 8000000, "min": 1, "max": 5},
    {"name": "Сено", "price": 6000000, "min": 1, "max": 5},
    {"name": "Яйца", "price": 5000000, "min": 1, "max": 5},
    {"name": "Пшеница", "price": 3000000, "min": 1, "max": 5},
    {"name": "Мясо", "price": 10000000, "min": 1, "max": 3}
]

# ========== БИЗНЕС ==========
BUSINESS_CONFIG = {
    "auto_mine": {
        "name": "Авто-Шахта",
        "price": 30000000000,
        "max_owners": 2,
        "emoji": "⛏️",
        "profit_type": "resources",
        "resources": [
            {"name": "Красный алмаз", "chance": 0.05},
            {"name": "Цветной алмаз", "chance": 0.08},
            {"name": "Рубин", "chance": 0.15},
            {"name": "Александрит", "chance": 0.10},
            {"name": "Падпараджа", "chance": 0.12},
            {"name": "Демантоид", "chance": 0.15},
            {"name": "Черный опал", "chance": 0.20},
            {"name": "Танзанит", "chance": 0.25},
            {"name": "Шпинель", "chance": 0.30}
        ],
        "min_resources": 1,
        "max_resources": 3,
        "cooldown": 600
    },
    "tech_center": {
        "name": "Технический центр",
        "price": 20000000000,
        "max_owners": 5,
        "emoji": "🔧",
        "profit_type": "money",
        "profit_min": 100000000,
        "profit_max": 350000000,
        "cooldown": 12600
    },
    "tire_center": {
        "name": "Шиномонтажный центр",
        "price": 15000000000,
        "max_owners": 5,
        "emoji": "🛞",
        "profit_type": "money",
        "profit_min": 75000000,
        "profit_max": 150000000,
        "cooldown": 9000
    },
    "styling_center": {
        "name": "Стайлинг центр",
        "price": 15000000000,
        "max_owners": 5,
        "emoji": "🎨",
        "profit_type": "money",
        "profit_min": 75000000,
        "profit_max": 150000000,
        "cooldown": 9000
    },
    "shop_24": {
        "name": "Магазин 24/7",
        "price": 1000000000,
        "max_owners": 20,
        "emoji": "🏪",
        "profit_type": "money",
        "profit_min": 30000000,
        "profit_max": 70000000,
        "cooldown": 3600
    }
}

# ========== МАШИНЫ ДЛЯ АУКЦИОНА (ОСТАВЛЕНЫ, НО АУКЦИОН УДАЛЁН) ==========
AUCTION_CARS = {
    # ★★★★★ (Экзотические, шанс 0.5%)
    "Монстр трак": {"stars": 5, "rarity": "Экзотическая", "base_price": 1000000000, "chance": 0.005},
    "Истребитель": {"stars": 5, "rarity": "Экзотическая", "base_price": 1500000000, "chance": 0.005},
    "БРДМ": {"stars": 5, "rarity": "Экзотическая", "base_price": 800000000, "chance": 0.005},
    "Танк": {"stars": 5, "rarity": "Экзотическая", "base_price": 2000000000, "chance": 0.005},
    "Вертолёт": {"stars": 5, "rarity": "Экзотическая", "base_price": 1200000000, "chance": 0.005},
    "RcCar": {"stars": 5, "rarity": "Экзотическая", "base_price": 50000000, "chance": 0.005},
    "Игрушечный вертолетик": {"stars": 5, "rarity": "Экзотическая", "base_price": 30000000, "chance": 0.005},
    "Лимузин": {"stars": 5, "rarity": "Экзотическая", "base_price": 2500000000, "chance": 0.005},
    
    # ★★★★☆ (Легендарные, шанс 5%)
    "Koenigsegg CCX": {"stars": 4, "rarity": "Легендарная", "base_price": 450000000, "chance": 0.05},
    "Pagani Zonda Cinque": {"stars": 4, "rarity": "Легендарная", "base_price": 500000000, "chance": 0.05},
    "McLaren F1 GTR": {"stars": 4, "rarity": "Легендарная", "base_price": 550000000, "chance": 0.05},
    "Porsche 959": {"stars": 4, "rarity": "Легендарная", "base_price": 300000000, "chance": 0.05},
    "DeLorean DMC-12": {"stars": 4, "rarity": "Легендарная", "base_price": 250000000, "chance": 0.05},
    "Ferrari 365 GTB/4 Daytona": {"stars": 4, "rarity": "Легендарная", "base_price": 400000000, "chance": 0.05},
    "Lamborghini Miura": {"stars": 4, "rarity": "Легендарная", "base_price": 480000000, "chance": 0.05},
    "Alfa Romeo 33 Stradale": {"stars": 4, "rarity": "Легендарная", "base_price": 350000000, "chance": 0.05},
    "Mercedes-Benz 300SL Gullwing": {"stars": 4, "rarity": "Легендарная", "base_price": 420000000, "chance": 0.05},
    "Aston Martin DB4 GT": {"stars": 4, "rarity": "Легендарная", "base_price": 380000000, "chance": 0.05},
    "Jaguar E-Type Lightweight": {"stars": 4, "rarity": "Легендарная", "base_price": 320000000, "chance": 0.05},
    "Shelby Cobra 427": {"stars": 4, "rarity": "Легендарная", "base_price": 360000000, "chance": 0.05},
    "Ford GT40": {"stars": 4, "rarity": "Легендарная", "base_price": 470000000, "chance": 0.05},
    "Bugatti Veyron Super Sport": {"stars": 4, "rarity": "Легендарная", "base_price": 600000000, "chance": 0.05},
    "Lamborghini Reventón": {"stars": 4, "rarity": "Легендарная", "base_price": 520000000, "chance": 0.05},
    "Ferrari F40 Competizione": {"stars": 4, "rarity": "Легендарная", "base_price": 580000000, "chance": 0.05},
    "Aston Martin Vulcan": {"stars": 4, "rarity": "Легендарная", "base_price": 490000000, "chance": 0.05},
    "Zenvo ST1": {"stars": 4, "rarity": "Легендарная", "base_price": 510000000, "chance": 0.05},
    "Rimac Nevera": {"stars": 4, "rarity": "Легендарная", "base_price": 560000000, "chance": 0.05},
    "Pininfarina Battista": {"stars": 4, "rarity": "Легендарная", "base_price": 540000000, "chance": 0.05},
    
    # ★★★☆☆ (Очень редкие, шанс 1%)
    "Mercedes-Benz CLK GTR": {"stars": 3, "rarity": "Очень редкая", "base_price": 200000000, "chance": 0.01},
    "Ferrari 308 GTB": {"stars": 3, "rarity": "Очень редкая", "base_price": 150000000, "chance": 0.01},
    "Lamborghini Countach 2022": {"stars": 3, "rarity": "Очень редкая", "base_price": 280000000, "chance": 0.01},
    "Porsche 930 Turbo": {"stars": 3, "rarity": "Очень редкая", "base_price": 180000000, "chance": 0.01},
    "BMW M1": {"stars": 3, "rarity": "Очень редкая", "base_price": 120000000, "chance": 0.01},
    "Jaguar XJ220": {"stars": 3, "rarity": "Очень редкая", "base_price": 220000000, "chance": 0.01},
    "Lamborghini Jalpa": {"stars": 3, "rarity": "Очень редкая", "base_price": 130000000, "chance": 0.01},
    "Maserati Merak": {"stars": 3, "rarity": "Очень редкая", "base_price": 110000000, "chance": 0.01},
    "De Tomaso Pantera": {"stars": 3, "rarity": "Очень редкая", "base_price": 140000000, "chance": 0.01},
    "Iso Grifo": {"stars": 3, "rarity": "Очень редкая", "base_price": 160000000, "chance": 0.01},
    "Bizzarrini 5300 GT": {"stars": 3, "rarity": "Очень редкая", "base_price": 170000000, "chance": 0.01},
    "Jensen Interceptor": {"stars": 3, "rarity": "Очень редкая", "base_price": 90000000, "chance": 0.01},
    "Lotus Esprit V8": {"stars": 3, "rarity": "Очень редкая", "base_price": 100000000, "chance": 0.01},
    "TVR Cerbera": {"stars": 3, "rarity": "Очень редкая", "base_price": 85000000, "chance": 0.01},
    "Noble M600": {"stars": 3, "rarity": "Очень редкая", "base_price": 190000000, "chance": 0.01},
    "Ultima GTR": {"stars": 3, "rarity": "Очень редкая", "base_price": 210000000, "chance": 0.01},
    "Ascari A10": {"stars": 3, "rarity": "Очень редкая", "base_price": 195000000, "chance": 0.01},
    "Gumpert Apollo": {"stars": 3, "rarity": "Очень редкая", "base_price": 205000000, "chance": 0.01},
    "Spyker C8": {"stars": 3, "rarity": "Очень редкая", "base_price": 175000000, "chance": 0.01},
    "Morgan Aero 8": {"stars": 3, "rarity": "Очень редкая", "base_price": 95000000, "chance": 0.01},
    "Bristol Fighter": {"stars": 3, "rarity": "Очень редкая", "base_price": 105000000, "chance": 0.01},
    "Gillet Vertigo": {"stars": 3, "rarity": "Очень редкая", "base_price": 115000000, "chance": 0.01},
    "Artega GT": {"stars": 3, "rarity": "Очень редкая", "base_price": 125000000, "chance": 0.01},
    "KTM X-Bow": {"stars": 3, "rarity": "Очень редкая", "base_price": 75000000, "chance": 0.01},
    "BAC Mono": {"stars": 3, "rarity": "Очень редкая", "base_price": 80000000, "chance": 0.01},
    "Caterham Seven 620R": {"stars": 3, "rarity": "Очень редкая", "base_price": 70000000, "chance": 0.01},
    "Ariel Atom 500": {"stars": 3, "rarity": "Очень редкая", "base_price": 65000000, "chance": 0.01},
    "Caparo T1": {"stars": 3, "rarity": "Очень редкая", "base_price": 185000000, "chance": 0.01},
    "Radical SR8": {"stars": 3, "rarity": "Очень редкая", "base_price": 155000000, "chance": 0.01},
    "Apollo Intensa Emozione": {"stars": 3, "rarity": "Очень редкая", "base_price": 230000000, "chance": 0.01},
    "Drako GTE": {"stars": 3, "rarity": "Очень редкая", "base_price": 215000000, "chance": 0.01},
    "Czinger 21C": {"stars": 3, "rarity": "Очень редкая", "base_price": 225000000, "chance": 0.01},
    "Lotus Evija": {"stars": 3, "rarity": "Очень редкая", "base_price": 240000000, "chance": 0.01},
    "NIO EP9": {"stars": 3, "rarity": "Очень редкая", "base_price": 235000000, "chance": 0.01},
    "Aspark Owl": {"stars": 3, "rarity": "Очень редкая", "base_price": 245000000, "chance": 0.01},
    "Hispano Suiza Carmen": {"stars": 3, "rarity": "Очень редкая", "base_price": 255000000, "chance": 0.01},
    "SCG 003": {"stars": 3, "rarity": "Очень редкая", "base_price": 265000000, "chance": 0.01},
    "Trion Nemesis": {"stars": 3, "rarity": "Очень редкая", "base_price": 275000000, "chance": 0.01},
    "Keating Berus": {"stars": 3, "rarity": "Очень редкая", "base_price": 285000000, "chance": 0.01},
    "Wiesmann MF5": {"stars": 3, "rarity": "Очень редкая", "base_price": 135000000, "chance": 0.01},
    "Donkervoort D8 GTO": {"stars": 3, "rarity": "Очень редкая", "base_price": 145000000, "chance": 0.01},
    
    # ★★☆☆☆ (Редкие, шанс 30%)
    "BMW 635CSi (E24)": {"stars": 2, "rarity": "Редкая", "base_price": 30000000, "chance": 0.30},
    "Mercedes-Benz 500 SL R107": {"stars": 2, "rarity": "Редкая", "base_price": 35000000, "chance": 0.30},
    "Toyota Supra A70 Mk3": {"stars": 2, "rarity": "Редкая", "base_price": 40000000, "chance": 0.30},
    "Mazda RX-7 Veilside": {"stars": 2, "rarity": "Редкая", "base_price": 45000000, "chance": 0.30},
    "Subaru Impreza WRX STI GC8": {"stars": 2, "rarity": "Редкая", "base_price": 25000000, "chance": 0.30},
    "Mitsubishi Lancer Evo VII": {"stars": 2, "rarity": "Редкая", "base_price": 28000000, "chance": 0.30},
    "Mitsubishi Galant 8": {"stars": 2, "rarity": "Редкая", "base_price": 20000000, "chance": 0.30},
    "Ford RS200": {"stars": 2, "rarity": "Редкая", "base_price": 38000000, "chance": 0.30},
    "Lancia Delta S4": {"stars": 2, "rarity": "Редкая", "base_price": 42000000, "chance": 0.30},
    "Audi Sport Quattro S1": {"stars": 2, "rarity": "Редкая", "base_price": 48000000, "chance": 0.30},
    "Peugeot 205 T16": {"stars": 2, "rarity": "Редкая", "base_price": 32000000, "chance": 0.30},
    "Renault 5 Turbo": {"stars": 2, "rarity": "Редкая", "base_price": 30000000, "chance": 0.30},
    "MG Metro 6R4": {"stars": 2, "rarity": "Редкая", "base_price": 34000000, "chance": 0.30},
    "VAZ-2105 Street 1996": {"stars": 2, "rarity": "Редкая", "base_price": 15000000, "chance": 0.30},
    "Volvo 240 GL": {"stars": 2, "rarity": "Редкая", "base_price": 18000000, "chance": 0.30},
    "Hummer H3T Alpha": {"stars": 2, "rarity": "Редкая", "base_price": 50000000, "chance": 0.30},
    "LADA Niva 2121 ГБР": {"stars": 2, "rarity": "Редкая", "base_price": 22000000, "chance": 0.30},
    "Tesla Cybertruck": {"stars": 2, "rarity": "Редкая", "base_price": 60000000, "chance": 0.30},
    "Dodge Charger Police": {"stars": 2, "rarity": "Редкая", "base_price": 45000000, "chance": 0.30},
    "Lenco BearCat": {"stars": 2, "rarity": "Редкая", "base_price": 55000000, "chance": 0.30},
    "Rolls-Royce Wraith": {"stars": 2, "rarity": "Редкая", "base_price": 65000000, "chance": 0.30},
    "Rolls-Royce Spectre": {"stars": 2, "rarity": "Редкая", "base_price": 70000000, "chance": 0.30},
    "Plymouth Hemi Cuda": {"stars": 2, "rarity": "Редкая", "base_price": 40000000, "chance": 0.30},
    "Chevrolet Chevelle SS": {"stars": 2, "rarity": "Редкая", "base_price": 43000000, "chance": 0.30},
    "Dodge Challenger SRT Demon": {"stars": 2, "rarity": "Редкая", "base_price": 52000000, "chance": 0.30},
    "Toyota 2000GT": {"stars": 2, "rarity": "Редкая", "base_price": 47000000, "chance": 0.30},
    "Lancia Stratos HF": {"stars": 2, "rarity": "Редкая", "base_price": 49000000, "chance": 0.30},
    "Renault Alpine A110": {"stars": 2, "rarity": "Редкая", "base_price": 37000000, "chance": 0.30},
    "BMW 507": {"stars": 2, "rarity": "Редкая", "base_price": 53000000, "chance": 0.30},
    "Ford Mustang Boss 429": {"stars": 2, "rarity": "Редкая", "base_price": 56000000, "chance": 0.30},
    "Pontiac GTO Judge": {"stars": 2, "rarity": "Редкая", "base_price": 41000000, "chance": 0.30},
    "Oldsmobile 442": {"stars": 2, "rarity": "Редкая", "base_price": 39000000, "chance": 0.30},
    "Buick GNX": {"stars": 2, "rarity": "Редкая", "base_price": 44000000, "chance": 0.30},
    
    # ★☆☆☆☆ (Доступные, шанс 50%)
    "Ford Sierra RS Cosworth": {"stars": 1, "rarity": "Доступная", "base_price": 8000000, "chance": 0.50},
    "Opel Manta GT/E": {"stars": 1, "rarity": "Доступная", "base_price": 7000000, "chance": 0.50},
    "VW Golf GTI Mk1": {"stars": 1, "rarity": "Доступная", "base_price": 6000000, "chance": 0.50},
    "Peugeot 306 GTI-6": {"stars": 1, "rarity": "Доступная", "base_price": 5000000, "chance": 0.50},
    "Renault Clio Williams": {"stars": 1, "rarity": "Доступная", "base_price": 5500000, "chance": 0.50},
    "Fiat Uno Turbo i.e.": {"stars": 1, "rarity": "Доступная", "base_price": 4500000, "chance": 0.50}
}

# ========== ID ДЛЯ ФУНКЦИЙ ==========
FUNCTION_IDS = {
    # Работы
    "job_1": "Шахта",
    "job_2": "Ферма",
    "job_3": "Трейдинг",
    "job_4": "Водолаз",
    
    # Кнопки меню
    "menubutton_1": "Работы",
    "menubutton_2": "Донат",
    "menubutton_3": "Форбс",
    "menubutton_4": "Гараж",
    "menubutton_5": "Инвентарь",
    "menubutton_6": "Скупщик",
    "menubutton_7": "Бизнес",
    "menubutton_8": "Казино",
    "menubutton_9": "Статистика",
    "menubutton_10": "Техподдержка",
    
    # Казино
    "casinogame_1": "Кубик",
    "casinogame_2": "Слоты",
    "casinogame_3": "Мины",
    
    # Трейдинг
    "trading_1": "BTC",
    "trading_2": "WETcoin",
    "trading_3": "NotCoin",
}

logger.info(f"📁 Данные хранятся в: {DATA_DIR}")
logger.info(f"👑 Админы: {ADMIN_IDS}")
