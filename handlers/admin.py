import os
import random
import string
import asyncio
from datetime import datetime

from aiogram import types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

from config import (
    ADMIN_IDS, bot, logger, BUSINESS_CONFIG, AUCTION_CARS,
    USERS_FILE, PROMOCODES_FILE, SETTINGS_FILE, BUSINESS_FILE, AUCTION_FILE
)
from database.file_manager import (
    load_users, save_users, load_business, save_business,
    load_settings, save_settings, load_promocodes, save_promocodes,
    load_disabled_functions, save_disabled_functions
)
from database.file_manager import set_auction_lots
from utils.helpers import is_admin
from services.currency import currency_rates
from services.tasks import promo_running, promo_task, promo_auto_loop
from services.auction import set_admin_auction_lots, refresh_auction_for_all, update_auction_lots

def register_admin_handlers(dp):
    
    @dp.message(Command("ahelp"))
    async def admin_help(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        help_text = (
            "👑 **Админ-команды:**\n\n"
            "**👤 Игроки:**\n"
            "`/getplayeracc @username` - меню игрока\n"
            "`/givecar @username кол-во id_машины` - выдача машины\n\n"
            "**🏢 Бизнес:**\n"
            "`/resetbusiness @username (причина)` - сброс бизнеса\n"
            "`/resetallbusiness` - сброс всех бизнесов\n"
            "`/givebusiness @username кол-во id_бизнеса` - выдача бизнеса\n\n"
            "**ID бизнесов:**\n"
            "`auto_mine` - Авто-Шахта\n"
            "`tech_center` - Техцентр\n"
            "`tire_center` - Шиномонтаж\n"
            "`styling_center` - Стайлинг\n"
            "`shop_24` - Магазин 24/7\n\n"
            "**💰 Выдача валют:**\n"
            "`/giverub @username кол-во (сообщение)` - выдача рублей\n"
            "`/givedonate @username кол-во (сообщение)` - выдача BRcoins\n\n"
            "**🎰 Управление:**\n"
            "`/promostart on/off` - авто-промокоды\n"
            "`/promostatus` - статус промокодов\n"
            "`/coinrun on/off` - CoinRun\n"
            "`/technical on/off` - техобслуживание\n"
            "`/status` - статус бота\n"
            "`/getdb` - получить базу\n"
            "`/mailall текст` - рассылка\n"
            "`/createpromo (1/0) (использований) (кол-во)` - создать промокод\n"
            "`/update_rates_admin` - обновить курсы\n\n"
            "**⛔ Отключение функций:**\n"
            "`/idfunctionlist` - список ID функций\n"
            "`/stopfunction айди` - остановить функцию\n"
            "`/returnfunction айди` - вернуть функцию\n\n"
            "**🚗 Аукцион:**\n"
            "`/carlist` - список всех машин с ID\n"
            "`/setcarauction (id машины) (начальная ставка) (кол-во)` - добавить машину\n"
            "`/refreshauction` - обновить аукцион"
        )
        await message.answer(help_text, parse_mode="Markdown")

    # ==========================================
    # ===== АДМИН-КОМАНДЫ ДЛЯ АУКЦИОНА =====
    # ==========================================
    
    @dp.message(Command("carlist"))
    async def car_list(message: types.Message):
        """Список всех машин с ID для админов"""
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        try:
            text = "🚗 **СПИСОК ВСЕХ МАШИН:**\n\n"
            car_list = list(AUCTION_CARS.keys())
            
            for i, name in enumerate(car_list, 1):
                data = AUCTION_CARS[name]
                stars = "⭐" * data['stars'] + "☆" * (5 - data['stars'])
                text += f"**{i}. {name}**\n"
                text += f"   🆔 ID: `car_{i}`\n"
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
        if not await is_admin(message.from_user.id):
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
            car_name = parts[1].strip()
            start_bid = int(parts[2])
            count = int(parts[3])
            
            if count <= 0 or start_bid <= 0:
                await message.answer("❌ Количество и ставка должны быть положительными!")
                return
            
            if car_name not in AUCTION_CARS:
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
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        try:
            await message.answer("🔄 Обновляю аукцион...")
            success, msg = await refresh_auction_for_all()
            await message.answer(msg)
        except Exception as e:
            logger.error(f"Ошибка в refreshauction: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    # ==========================================
    # ===== ОСТАЛЬНЫЕ АДМИН-КОМАНДЫ =====
    # ==========================================

    @dp.message(Command("getplayeracc"))
    async def get_player_acc(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Использование: /getplayeracc @username")
            return
        
        username = parts[1].replace("@", "").lower()
        
        try:
            users = await load_users()
            found_user = None
            found_id = None
            
            for user_id, data in users.items():
                try:
                    user = await bot.get_chat(int(user_id))
                    if user.username and user.username.lower() == username:
                        found_user = data
                        found_id = user_id
                        break
                except:
                    continue
            
            if not found_user:
                await message.answer(f"❌ Пользователь @{username} не найден!")
                return
            
            text = (
                f"👤 **ПРОФИЛЬ @{username}**\n\n"
                f"💰 Баланс: {found_user['money']:,.0f}₽\n"
                f"💎 BRcoins: {found_user['brcoins']}\n"
                f"📈 Заработано: {found_user['total_earned']:,.0f}₽\n"
                f"🤝 Сделок: {found_user['trades_count']}\n"
                f"⛔ Забанен: {'Да' if found_user.get('banned', False) else 'Нет'}\n\n"
                f"**📊 Портфель:**\n"
                f"₿ BTC: {found_user['portfolio'].get('BTC', 0)}\n"
                f"💧 WETcoin: {found_user['portfolio'].get('WETcoin', 0)}\n"
                f"🪙 NotCoin: {found_user['portfolio'].get('NotCoin', 0)}\n\n"
                f"🚗 Машин в гараже: {len(found_user.get('inventory', []))}"
            )
            
            keyboard = [
                [InlineKeyboardButton(text="💰 Обнулить баланс ₽", callback_data=f"admin_reset_money_{found_id}")],
                [InlineKeyboardButton(text="💎 Обнулить BRcoins", callback_data=f"admin_reset_br_{found_id}")],
                [InlineKeyboardButton(text="🪙 Обнулить трейдинг", callback_data=f"admin_reset_trade_{found_id}")],
                [InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"admin_ban_{found_id}")],
                [InlineKeyboardButton(text="🚗 Гараж игрока", callback_data=f"admin_garage_{found_id}")],
                [InlineKeyboardButton(text="🏢 Бизнес игрока", callback_data=f"admin_business_{found_id}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
            ]
            
            await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Ошибка в getplayeracc: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.callback_query(F.data.startswith("admin_reset_money_"))
    async def admin_reset_money(callback: types.CallbackQuery):
        if not await is_admin(callback.from_user.id):
            await callback.answer("⛔ Нет прав!", show_alert=True)
            return
        
        user_id = callback.data.replace("admin_reset_money_", "")
        try:
            users = await load_users()
            if user_id in users:
                users[user_id]["money"] = 0
                await save_users(users)
                await callback.answer("✅ Баланс обнулен!", show_alert=True)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback.answer("❌ Ошибка!", show_alert=True)
        await callback.answer()

    @dp.callback_query(F.data.startswith("admin_reset_br_"))
    async def admin_reset_br(callback: types.CallbackQuery):
        if not await is_admin(callback.from_user.id):
            await callback.answer("⛔ Нет прав!", show_alert=True)
            return
        
        user_id = callback.data.replace("admin_reset_br_", "")
        try:
            users = await load_users()
            if user_id in users:
                users[user_id]["brcoins"] = 0
                await save_users(users)
                await callback.answer("✅ BRcoins обнулены!", show_alert=True)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback.answer("❌ Ошибка!", show_alert=True)
        await callback.answer()

    @dp.callback_query(F.data.startswith("admin_reset_trade_"))
    async def admin_reset_trade(callback: types.CallbackQuery):
        if not await is_admin(callback.from_user.id):
            await callback.answer("⛔ Нет прав!", show_alert=True)
            return
        
        user_id = callback.data.replace("admin_reset_trade_", "")
        try:
            users = await load_users()
            if user_id in users:
                users[user_id]["portfolio"] = {"BTC": 0, "WETcoin": 0, "NotCoin": 0}
                await save_users(users)
                await callback.answer("✅ Трейдинг обнулен!", show_alert=True)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback.answer("❌ Ошибка!", show_alert=True)
        await callback.answer()

    @dp.callback_query(F.data.startswith("admin_ban_"))
    async def admin_ban(callback: types.CallbackQuery):
        if not await is_admin(callback.from_user.id):
            await callback.answer("⛔ Нет прав!", show_alert=True)
            return
        
        user_id = callback.data.replace("admin_ban_", "")
        try:
            users = await load_users()
            if user_id in users:
                users[user_id]["banned"] = True
                await save_users(users)
                await callback.answer("✅ Пользователь забанен!", show_alert=True)
                try:
                    await bot.send_message(int(user_id), "🚫 Ваш аккаунт заблокирован администратором!")
                except:
                    pass
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback.answer("❌ Ошибка!", show_alert=True)
        await callback.answer()

    @dp.callback_query(F.data.startswith("admin_garage_"))
    async def admin_garage(callback: types.CallbackQuery):
        if not await is_admin(callback.from_user.id):
            await callback.answer("⛔ Нет прав!", show_alert=True)
            return
        
        user_id = callback.data.replace("admin_garage_", "")
        try:
            users = await load_users()
            if user_id not in users:
                await callback.answer("❌ Пользователь не найден!", show_alert=True)
                return
            
            inventory = users[user_id].get("inventory", [])
            if not inventory:
                await callback.answer("🚗 У игрока нет машин!", show_alert=True)
                return
            
            text = f"🚗 **Гараж игрока:**\n\n"
            for i, car in enumerate(inventory, 1):
                if isinstance(car, dict):
                    text += f"{i}. {car.get('name', 'Неизвестно')} - {car.get('price', 0):,.0f}₽\n"
                else:
                    text += f"{i}. {car}\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                ]),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback.answer("❌ Ошибка!", show_alert=True)
        await callback.answer()

    @dp.callback_query(F.data.startswith("admin_business_"))
    async def admin_business(callback: types.CallbackQuery):
        if not await is_admin(callback.from_user.id):
            await callback.answer("⛔ Нет прав!", show_alert=True)
            return
        
        user_id = callback.data.replace("admin_business_", "")
        try:
            users = await load_users()
            if user_id not in users:
                await callback.answer("❌ Пользователь не найден!", show_alert=True)
                return
            
            business = users[user_id].get("business", {})
            has_business = False
            text = f"🏢 **Бизнес игрока:**\n\n"
            
            for key, data in business.items():
                if data.get("owned", False):
                    has_business = True
                    config = BUSINESS_CONFIG.get(key, {})
                    text += f"{config.get('emoji', '')} {config.get('name', key)} - Активен\n"
                    if data.get("auto_collect", False):
                        text += f"   🔄 Авто-сбор включен\n"
            
            if not has_business:
                await callback.answer("🏢 У игрока нет бизнеса!", show_alert=True)
                return
            
            await callback.message.edit_text(
                text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await callback.answer("❌ Ошибка!", show_alert=True)
        await callback.answer()

    @dp.message(Command("givecar"))
    async def give_car(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split(maxsplit=3)
        if len(parts) < 4:
            await message.answer("❌ Использование: /givecar @username кол-во id_машины\n\nПример: /givecar @user 1 car_1\nДля просмотра всех ID используйте /carlist")
            return
        
        try:
            username = parts[1].replace("@", "").lower()
            amount = int(parts[2])
            car_id = parts[3].lower()
            
            if amount <= 0:
                await message.answer("❌ Количество должно быть положительным!")
                return
            
            car_name = None
            car_list = list(AUCTION_CARS.keys())
            
            # Поддержка car_1, car_2 и т.д.
            if car_id.startswith("car_"):
                try:
                    index = int(car_id.replace("car_", "")) - 1
                    if 0 <= index < len(car_list):
                        car_name = car_list[index]
                except ValueError:
                    pass
            
            # Если не нашли по car_N, ищем по названию
            if not car_name:
                for name in car_list:
                    if car_id in name.lower():
                        car_name = name
                        break
            
            if not car_name:
                await message.answer(f"❌ Машина '{car_id}' не найдена!\nИспользуйте /carlist для списка")
                return
            
            users = await load_users()
            found = False
            
            for user_id, data in users.items():
                try:
                    user = await bot.get_chat(int(user_id))
                    if user.username and user.username.lower() == username:
                        if "inventory" not in data:
                            data["inventory"] = []
                        
                        car_price = AUCTION_CARS.get(car_name, {}).get("base_price", 0)
                        for _ in range(amount):
                            data["inventory"].append({
                                "name": car_name,
                                "price": car_price,
                                "from_admin": True
                            })
                        
                        users[user_id] = data
                        await save_users(users)
                        
                        await message.answer(f"✅ @{username} получил {amount} шт. {car_name}!")
                        try:
                            await bot.send_message(
                                int(user_id),
                                f"🎁 Вы получили {amount} шт. {car_name} от администратора!"
                            )
                        except:
                            pass
                        found = True
                        break
                except Exception as e:
                    logger.warning(f"Ошибка при поиске пользователя: {e}")
                    continue
            
            if not found:
                await message.answer(f"❌ @{username} не найден!")
                
        except ValueError:
            await message.answer("❌ Введите корректное число!")
        except Exception as e:
            logger.error(f"Ошибка в givecar: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.message(Command("idfunctionlist"))
    async def id_function_list(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        try:
            text = (
                "📋 **СПИСОК ID ФУНКЦИЙ:**\n\n"
                "**Работы:**\n"
                "• job_1 - Шахта\n"
                "• job_2 - Ферма\n"
                "• job_3 - Трейдинг\n"
                "• job_4 - Водолаз\n\n"
                "**Кнопки меню:**\n"
                "• menubutton_1 - Работы\n"
                "• menubutton_2 - Донат\n"
                "• menubutton_3 - Форбс\n"
                "• menubutton_4 - Гараж\n"
                "• menubutton_5 - Инвентарь\n"
                "• menubutton_6 - Скупщик\n"
                "• menubutton_7 - Бизнес\n"
                "• menubutton_8 - Казино\n"
                "• menubutton_9 - Статистика\n"
                "• menubutton_10 - Техподдержка\n"
                "• menubutton_11 - Аукцион\n\n"
                "**Казино:**\n"
                "• casinogame_1 - Кубик\n"
                "• casinogame_2 - Слоты\n"
                "• casinogame_3 - Мины\n\n"
                "**Трейдинг:**\n"
                "• trading_1 - BTC\n"
                "• trading_2 - WETcoin\n"
                "• trading_3 - NotCoin"
            )
            
            await message.answer(text, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Ошибка в idfunctionlist: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.message(Command("stopfunction"))
    async def stop_function(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Использование: /stopfunction айди_функции\n\nПример: /stopfunction job_1")
            return
        
        function_id = parts[1]
        
        all_ids = [
            "job_1", "job_2", "job_3", "job_4",
            "menubutton_1", "menubutton_2", "menubutton_3", "menubutton_4",
            "menubutton_5", "menubutton_6", "menubutton_7", "menubutton_8",
            "menubutton_9", "menubutton_10", "menubutton_11",
            "casinogame_1", "casinogame_2", "casinogame_3",
            "trading_1", "trading_2", "trading_3"
        ]
        
        if function_id not in all_ids:
            await message.answer(f"❌ Функция '{function_id}' не найдена!\nИспользуйте /idfunctionlist для просмотра всех ID")
            return
        
        try:
            disabled = await load_disabled_functions()
            if "functions" not in disabled:
                disabled["functions"] = []
            
            if function_id not in disabled["functions"]:
                disabled["functions"].append(function_id)
                await save_disabled_functions(disabled)
                await message.answer(f"✅ Функция '{function_id}' остановлена!")
            else:
                await message.answer(f"ℹ️ Функция '{function_id}' уже остановлена")
                
        except Exception as e:
            logger.error(f"Ошибка в stopfunction: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.message(Command("returnfunction"))
    async def return_function(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Использование: /returnfunction айди_функции\n\nПример: /returnfunction job_1")
            return
        
        function_id = parts[1]
        
        try:
            disabled = await load_disabled_functions()
            if "functions" in disabled and function_id in disabled["functions"]:
                disabled["functions"].remove(function_id)
                await save_disabled_functions(disabled)
                await message.answer(f"✅ Функция '{function_id}' возвращена!")
            else:
                await message.answer(f"ℹ️ Функция '{function_id}' не была остановлена")
                
        except Exception as e:
            logger.error(f"Ошибка в returnfunction: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.message(Command("resetbusiness"))
    async def reset_business(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            await message.answer("❌ Использование: /resetbusiness @username (причина)")
            return
        
        username = parts[1].replace("@", "").lower()
        reason = parts[2] if len(parts) > 2 else "Без причины"
        
        try:
            users = await load_users()
            business_data = await load_business()
            found = False
            
            for user_id, data in users.items():
                try:
                    user = await bot.get_chat(int(user_id))
                    if user.username and user.username.lower() == username:
                        if "business" in data:
                            for biz_key in data["business"]:
                                if biz_key in business_data and user_id in business_data[biz_key]["owners"]:
                                    business_data[biz_key]["owners"].remove(user_id)
                            data["business"] = {}
                        
                        users[user_id] = data
                        await save_users(users)
                        await save_business(business_data)
                        
                        await message.answer(f"✅ Бизнесы @{username} сброшены!\nПричина: {reason}")
                        await bot.send_message(
                            int(user_id),
                            f"⚠️ Ваши бизнесы были сброшены администратором!\nПричина: {reason}"
                        )
                        found = True
                        break
                except Exception as e:
                    logger.warning(f"Ошибка при поиске пользователя: {e}")
                    continue
            
            if not found:
                await message.answer(f"❌ @{username} не найден!")
        except Exception as e:
            logger.error(f"Ошибка в resetbusiness: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.message(Command("resetallbusiness"))
    async def reset_all_business(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        try:
            users = await load_users()
            business_data = await load_business()
            count = 0
            
            for user_id, data in users.items():
                if "business" in data and data["business"]:
                    for biz_key in data["business"]:
                        if biz_key in business_data and user_id in business_data[biz_key]["owners"]:
                            business_data[biz_key]["owners"].remove(user_id)
                    data["business"] = {}
                    count += 1
                    users[user_id] = data
            
            await save_users(users)
            await save_business(business_data)
            
            await message.answer(f"✅ Сброшены бизнесы у {count} пользователей!")
        except Exception as e:
            logger.error(f"Ошибка в resetallbusiness: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.message(Command("givebusiness"))
    async def give_business(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split()
        if len(parts) != 4:
            await message.answer("❌ Использование: /givebusiness @username кол-во id_бизнеса")
            return
        
        try:
            username = parts[1].replace("@", "").lower()
            amount = int(parts[2])
            business_id = parts[3]
            
            if business_id not in BUSINESS_CONFIG:
                await message.answer(f"❌ Бизнес '{business_id}' не найден!\nДоступные: auto_mine, tech_center, tire_center, styling_center, shop_24")
                return
            
            users = await load_users()
            business_data = await load_business()
            found = False
            
            for user_id, data in users.items():
                try:
                    user = await bot.get_chat(int(user_id))
                    if user.username and user.username.lower() == username:
                        user_business_count = 0
                        for biz in data.get("business", {}).values():
                            if biz.get("owned", False):
                                user_business_count += 1
                        
                        if user_business_count >= 1:
                            await message.answer(f"❌ @{username} уже владеет бизнесом!")
                            return
                        
                        config = BUSINESS_CONFIG[business_id]
                        owners = business_data.get(business_id, {}).get("owners", [])
                        if len(owners) >= config["max_owners"]:
                            await message.answer(f"❌ Все места для {config['name']} заняты!")
                            return
                        
                        if user_id in owners:
                            await message.answer(f"❌ @{username} уже владеет {config['name']}!")
                            return
                        
                        if "business" not in data:
                            data["business"] = {}
                        if business_id not in data["business"]:
                            data["business"][business_id] = {"owned": False, "last_collect": None, "auto_collect": False}
                        data["business"][business_id]["owned"] = True
                        data["business"][business_id]["last_collect"] = datetime.now().isoformat()
                        
                        if business_id not in business_data:
                            business_data[business_id] = {"owners": [], "total_earned": 0}
                        business_data[business_id]["owners"].append(user_id)
                        
                        users[user_id] = data
                        await save_users(users)
                        await save_business(business_data)
                        
                        await message.answer(f"✅ @{username} получил {config['emoji']} {config['name']}!")
                        await bot.send_message(
                            int(user_id),
                            f"🎉 Вы получили {config['emoji']} {config['name']} от администратора!"
                        )
                        found = True
                        break
                except Exception as e:
                    logger.warning(f"Ошибка при поиске пользователя: {e}")
                    continue
            
            if not found:
                await message.answer(f"❌ @{username} не найден!")
        except ValueError:
            await message.answer("❌ Введите корректное число!")
        except Exception as e:
            logger.error(f"Ошибка в givebusiness: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.message(Command("giverub"))
    async def give_rub(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split(maxsplit=3)
        if len(parts) < 3:
            await message.answer("❌ Использование: /giverub @username кол-во (сообщение)")
            return
        
        try:
            username = parts[1].replace("@", "").lower()
            amount = int(parts[2])
            admin_message = parts[3] if len(parts) > 3 else "Без сообщения"
            
            if amount <= 0:
                await message.answer("❌ Количество должно быть положительным!")
                return
            
            users = await load_users()
            found = False
            
            for user_id, data in users.items():
                try:
                    user = await bot.get_chat(int(user_id))
                    if user.username and user.username.lower() == username:
                        data["money"] += amount
                        data["total_earned"] += amount
                        await save_users(users)
                        await message.answer(f"✅ @{username} +{amount:,}₽")
                        await bot.send_message(
                            int(user_id),
                            f"💰 +{amount:,}₽ от админа!\n\n📝 Сообщение: {admin_message}"
                        )
                        found = True
                        break
                except Exception as e:
                    logger.warning(f"Ошибка при поиске пользователя: {e}")
                    continue
            
            if not found:
                await message.answer(f"❌ @{username} не найден!")
        except ValueError:
            await message.answer("❌ Введите корректное число!")
        except Exception as e:
            logger.error(f"Ошибка в giverub: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.message(Command("givedonate"))
    async def give_donate(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split(maxsplit=3)
        if len(parts) < 3:
            await message.answer("❌ Использование: /givedonate @username кол-во (сообщение)")
            return
        
        try:
            username = parts[1].replace("@", "").lower()
            amount = int(parts[2])
            admin_message = parts[3] if len(parts) > 3 else "Без сообщения"
            
            if amount <= 0:
                await message.answer("❌ Количество должно быть положительным!")
                return
            
            users = await load_users()
            found = False
            
            for user_id, data in users.items():
                try:
                    user = await bot.get_chat(int(user_id))
                    if user.username and user.username.lower() == username:
                        data["brcoins"] += amount
                        data["donate_received"] += amount
                        await save_users(users)
                        await message.answer(f"✅ @{username} +{amount} BRcoins")
                        await bot.send_message(
                            int(user_id),
                            f"💎 +{amount} BRcoins от админа!\n\n📝 Сообщение: {admin_message}"
                        )
                        found = True
                        break
                except Exception as e:
                    logger.warning(f"Ошибка при поиске пользователя: {e}")
                    continue
            
            if not found:
                await message.answer(f"❌ @{username} не найден!")
        except ValueError:
            await message.answer("❌ Введите корректное число!")
        except Exception as e:
            logger.error(f"Ошибка в givedonate: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.message(Command("createpromo"))
    async def create_promo(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split()
        if len(parts) != 4:
            await message.answer("❌ /createpromo (1/0) (использований) (кол-во)\n1 - BRcoins, 0 - рубли")
            return
        
        try:
            promo_type = int(parts[1])
            uses = int(parts[2])
            amount = int(parts[3])
            
            if uses <= 0 or amount <= 0:
                await message.answer("❌ Значения должны быть положительными!")
                return
            
            if promo_type not in [0, 1]:
                await message.answer("❌ Тип должен быть 0 или 1!")
                return
            
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            promocodes = await load_promocodes()
            promocodes[code] = {
                "type": "brcoins" if promo_type == 1 else "money",
                "uses": uses,
                "used": 0,
                "amount": amount
            }
            await save_promocodes(promocodes)
            
            await message.answer(
                f"✅ Промокод создан!\n"
                f"Код: `{code}`\n"
                f"Тип: {'BRcoins' if promo_type == 1 else 'Рубли'}\n"
                f"Количество: {amount:,}\n"
                f"Использований: {uses}"
            )
        except ValueError:
            await message.answer("❌ Введите корректные числа!")
        except Exception as e:
            logger.error(f"Ошибка в createpromo: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.message(Command("mailall"))
    async def mail_all(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        text = message.text.replace("/mailall", "").strip()
        if not text:
            await message.answer("❌ Пример: /mailall Привет всем!")
            return
        
        try:
            users = await load_users()
            sent = 0
            for user_id in users:
                try:
                    await bot.send_message(int(user_id), f"📢 {text}")
                    sent += 1
                    await asyncio.sleep(0.05)
                except Exception as e:
                    logger.warning(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
            await message.answer(f"✅ Отправлено {sent} пользователям!")
        except Exception as e:
            logger.error(f"Ошибка в mailall: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.message(Command("getdb"))
    async def get_db(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        try:
            await message.answer("📦 Собираю базу...")
            files_sent = 0
            for file in [USERS_FILE, PROMOCODES_FILE, SETTINGS_FILE, BUSINESS_FILE, AUCTION_FILE]:
                if os.path.exists(file):
                    with open(file, 'r', encoding='utf-8') as f:
                        await message.answer_document(
                            BufferedInputFile(
                                f.read().encode('utf-8'),
                                filename=os.path.basename(file)
                            )
                        )
                        files_sent += 1
                        await asyncio.sleep(0.3)
            await message.answer(f"✅ Отправлено {files_sent} файлов!")
        except Exception as e:
            logger.error(f"Ошибка в get_db: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.message(Command("promostart"))
    async def promo_start_command(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split()
        if len(parts) != 2 or parts[1].lower() not in ["on", "off"]:
            await message.answer("❌ Использование: /promostart on  или  /promostart off")
            return
        
        status = parts[1].lower()
        settings = await load_settings()
        settings["promo_auto"] = (status == "on")
        await save_settings(settings)
        
        global promo_running, promo_task
        
        if status == "on":
            if not promo_running:
                promo_running = True
                promo_task = asyncio.create_task(promo_auto_loop())
                await message.answer("✅ Авто-генерация промокодов ЗАПУЩЕНА!")
            else:
                await message.answer("ℹ️ Уже запущена")
        else:
            if promo_running:
                promo_running = False
                if promo_task:
                    promo_task.cancel()
                await message.answer("❌ Авто-генерация ОСТАНОВЛЕНА!")

    @dp.message(Command("promostatus"))
    async def promo_status_command(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        settings = await load_settings()
        status = "✅ Включена" if settings.get("promo_auto", False) else "❌ Выключена"
        await message.answer(f"📢 Статус: {status}")

    @dp.message(Command("coinrun"))
    async def coinrun_command(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split()
        if len(parts) != 2 or parts[1].lower() not in ["on", "off"]:
            await message.answer("❌ Использование: /coinrun on  или  /coinrun off")
            return
        
        settings = await load_settings()
        settings["coinrun_enabled"] = (parts[1].lower() == "on")
        await save_settings(settings)
        await message.answer(
            f"🪙 Добыча BRcoins на работах "
            f"{'ВКЛЮЧЕНА' if settings['coinrun_enabled'] else 'ВЫКЛЮЧЕНА'}!"
        )

    @dp.message(Command("technical"))
    async def technical_command(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split()
        if len(parts) != 2 or parts[1].lower() not in ["on", "off"]:
            await message.answer("❌ Использование: /technical on  или  /technical off")
            return
        
        settings = await load_settings()
        settings["bot_enabled"] = (parts[1].lower() == "on")
        await save_settings(settings)
        await message.answer(f"🔧 Бот {'ВКЛЮЧЕН' if settings['bot_enabled'] else 'ВЫКЛЮЧЕН'}!")

    @dp.message(Command("status"))
    async def status_command(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        settings = await load_settings()
        await message.answer(
            f"🔧 Бот: {'✅ Включен' if settings.get('bot_enabled', True) else '❌ Выключен'}\n"
            f"📢 Промокоды: {'✅ Включены' if settings.get('promo_auto', False) else '❌ Выключены'}\n"
            f"🪙 CoinRun: {'✅ Включен' if settings.get('coinrun_enabled', False) else '❌ Выключен'}\n"
            f"📊 Всего добыто BRcoins: {settings.get('coinrun_total', 0):,}"
        )

    @dp.message(Command("update_rates_admin"))
    async def update_rates_admin(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        try:
            currency_rates.force_update()
            await message.answer("✅ Курсы обновлены!")
        except Exception as e:
            logger.error(f"Ошибка в update_rates_admin: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    logger.info("✅ Все админ-обработчики зарегистрированы!")
