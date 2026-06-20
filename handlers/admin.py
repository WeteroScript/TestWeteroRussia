from aiogram import types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_IDS, bot, logger, BUSINESS_CONFIG, AUCTION_CARS
from database.file_manager import (
    load_users, save_users, load_business, save_business,
    load_settings, save_settings, load_promocodes, save_promocodes,
    load_disabled_functions, save_disabled_functions
)
from database.auction_manager import set_auction_lots
from utils.helpers import is_admin
from services.currency import currency_rates
from services.tasks import promo_running, promo_task, promo_auto_loop
from services.auction import set_admin_auction_lots, refresh_auction_for_all, update_auction_lots
import asyncio
import random
import string

def register_admin_handlers(dp):
    
    @dp.message(Command("ahelp"))
    async def admin_help(message: types.Message):
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        help_text = (
            "👑 **Админ-команды:**\n\n"
            "**Бизнесы:**\n"
            "`/resetbusiness @username (причина)` - сброс бизнесов у пользователя\n"
            "`/resetallbusiness` - сброс всех бизнесов у всех пользователей\n"
            "`/givebusiness @username кол-во id_бизнеса` - выдача бизнеса\n\n"
            "**ID бизнесов:**\n"
            "`auto_mine` - Авто-Шахта (2 места)\n"
            "`tech_center` - Технический центр (5 мест)\n"
            "`tire_center` - Шиномонтажный центр (5 мест)\n"
            "`styling_center` - Стайлинг центр (5 мест)\n"
            "`shop_24` - Магазин 24/7 (20 мест)\n\n"
            "**Выдача валют:**\n"
            "`/giverub @username кол-во (сообщение)` - выдача рублей\n"
            "`/givedonate @username кол-во (сообщение)` - выдача BRcoins\n\n"
            "**Управление ботом:**\n"
            "`/promostart on/off` - авто-промокоды\n"
            "`/promostatus` - статус промокодов\n"
            "`/coinrun on/off` - CoinRun\n"
            "`/technical on/off` - техобслуживание\n"
            "`/status` - статус бота\n"
            "`/getdb` - получить базу данных\n"
            "`/mailall текст` - рассылка\n"
            "`/createpromo (1/0) (использований) (кол-во)` - создать промокод\n"
            "`/update_rates_admin` - обновить курсы\n"
            "`/stopfunction function_id` - блокировка/разблокировка функции\n\n"
            "**Аукцион (НОВОЕ):**\n"
            "`/setcarauction (id машины) (начальная ставка) (кол-во)` - добавить машину на аукцион\n"
            "`/refreshauction` - обновить список машин на аукционе\n"
            "`/carlist` - список всех машин с ID"
        )
        
        await message.answer(help_text, parse_mode="Markdown")

    # ========== НОВЫЕ АДМИН-КОМАНДЫ ДЛЯ АУКЦИОНА ==========
    
    @dp.message(Command("carlist"))
    async def car_list(message: types.Message):
        """Список всех машин с ID для админов"""
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        try:
            text = "🚗 **СПИСОК ВСЕХ МАШИН:**\n\n"
            car_list = list(AUCTION_CARS.keys())
            
            for i, name in enumerate(car_list, 1):
                data = AUCTION_CARS[name]
                stars = "⭐" * data['stars'] + "☆" * (5 - data['stars'])
                text += f"**{i}. {name}**\n"
                text += f"   ID: `{name}`\n"
                text += f"   {stars} ({data['rarity']})\n"
                text += f"   💰 {data['base_price']:,.0f}₽\n\n"
            
            if len(text) > 4000:
                parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for part in parts:
                    await message.answer(part, parse_mode="Markdown")
            else:
                await message.answer(text, parse_mode="Markdown")
                
        except Exception as e:
            logger.error(f"Ошибка в carlist: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.message(Command("setcarauction"))
    async def set_car_auction(message: types.Message):
        """Добавить машину на аукцион"""
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split(maxsplit=3)
        if len(parts) < 4:
            await message.answer(
                "❌ Использование: /setcarauction (id машины) (начальная ставка) (кол-во)\n\n"
                "Пример: /setcarauction \"Монстр трак\" 1000000 1\n"
                "Для просмотра всех машин используйте /carlist"
            )
            return
        
        try:
            # Собираем название машины (может содержать пробелы)
            car_name = parts[1].strip()
            start_bid = int(parts[2])
            count = int(parts[3])
            
            if count <= 0 or start_bid <= 0:
                await message.answer("❌ Количество и ставка должны быть положительными!")
                return
            
            # Проверяем существование машины
            if car_name not in AUCTION_CARS:
                # Пробуем найти по частичному совпадению
                found = None
                for name in AUCTION_CARS.keys():
                    if car_name.lower() in name.lower():
                        found = name
                        break
                
                if found:
                    car_name = found
                else:
                    await message.answer(
                        f"❌ Машина '{car_name}' не найдена!\n"
                        f"Используйте /carlist для просмотра всех машин"
                    )
                    return
            
            # Добавляем на аукцион
            success, msg = await set_admin_auction_lots(car_name, start_bid, count)
            await message.answer(msg)
            
        except ValueError:
            await message.answer("❌ Введите корректные числа для ставки и количества!")
        except Exception as e:
            logger.error(f"Ошибка в setcarauction: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.message(Command("refreshauction"))
    async def refresh_auction(message: types.Message):
        """Обновить аукцион для всех пользователей"""
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        try:
            await message.answer("🔄 Обновляю аукцион...")
            success, msg = await refresh_auction_for_all()
            await message.answer(msg)
        except Exception as e:
            logger.error(f"Ошибка в refreshauction: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    # ========== ОСТАЛЬНЫЕ АДМИН-КОМАНДЫ (без изменений) ==========
    
    # ... остальные команды остаются без изменений ...
