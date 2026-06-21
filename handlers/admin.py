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
    USERS_FILE, PROMOCODES_FILE, SETTINGS_FILE, BUSINESS_FILE, AUCTION_FILE,
    AUCTION_CONFIG
)
from database.file_manager import (
    load_users, save_users, load_business, save_business,
    load_settings, save_settings, load_promocodes, save_promocodes,
    load_disabled_functions, save_disabled_functions,
    load_auction_data, save_auction_data
)
from database.file_manager import set_auction_lots
from utils.helpers import is_admin
from services.currency import currency_rates
from services.tasks import promo_running, promo_task, promo_auto_loop
from services.auction import (
    set_admin_auction_lots_with_slot, 
    refresh_auction_for_all, 
    update_auction_lots,
    user_auction_page,
    frozen_bids
)

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
            "`/givecar @username кол-во id_машины` - выдача машины\n"
            "`/ban @username (причина)` - заблокировать игрока\n"
            "`/unban @username (причина)` - разблокировать игрока\n\n"
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
            "`/setcarauction (id машины) (начальная ставка) (кол-во) (слот 1-15)` - добавить машину в слот\n"
            "`/refreshauction` - обновить аукцион\n"
            "`/stopauctionlot (номер лота)` - остановить лот и вернуть деньги"
        )
        await message.answer(help_text, parse_mode="Markdown")

    # ==========================================
    # ===== КОМАНДЫ: BAN / UNBAN =====
    # ==========================================
    
    @dp.message(Command("ban"))
    async def ban_user(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            await message.answer("❌ Использование: /ban @username (причина/необязательно)")
            return
        
        username = parts[1].replace("@", "").lower()
        reason = parts[2] if len(parts) > 2 else "Без причины"
        
        try:
            users = await load_users()
            found = False
            
            for user_id, data in users.items():
                try:
                    user = await bot.get_chat(int(user_id))
                    if user.username and user.username.lower() == username:
                        if data.get("banned", False):
                            await message.answer(f"ℹ️ @{username} уже заблокирован!")
                            return
                        
                        data["banned"] = True
                        users[user_id] = data
                        await save_users(users)
                        
                        try:
                            await bot.send_message(
                                int(user_id),
                                f"🚫 Вас заблокировали!\n\nПричина: {reason}"
                            )
                        except:
                            pass
                        
                        await message.answer(f"✅ @{username} заблокирован!\nПричина: {reason}")
                        found = True
                        break
                except Exception as e:
                    logger.warning(f"Ошибка при поиске пользователя: {e}")
                    continue
            
            if not found:
                await message.answer(f"❌ @{username} не найден!")
                
        except Exception as e:
            logger.error(f"Ошибка в ban_user: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.message(Command("unban"))
    async def unban_user(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            await message.answer("❌ Использование: /unban @username (причина/необязательно)")
            return
        
        username = parts[1].replace("@", "").lower()
        reason = parts[2] if len(parts) > 2 else "Без причины"
        
        try:
            users = await load_users()
            found = False
            
            for user_id, data in users.items():
                try:
                    user = await bot.get_chat(int(user_id))
                    if user.username and user.username.lower() == username:
                        if not data.get("banned", False):
                            await message.answer(f"ℹ️ @{username} не заблокирован!")
                            return
                        
                        data["banned"] = False
                        users[user_id] = data
                        await save_users(users)
                        
                        try:
                            await bot.send_message(
                                int(user_id),
                                f"✅ Вас разблокировали!\n\nПричина: {reason}"
                            )
                        except:
                            pass
                        
                        await message.answer(f"✅ @{username} разблокирован!\nПричина: {reason}")
                        found = True
                        break
                except Exception as e:
                    logger.warning(f"Ошибка при поиске пользователя: {e}")
                    continue
            
            if not found:
                await message.answer(f"❌ @{username} не найден!")
                
        except Exception as e:
            logger.error(f"Ошибка в unban_user: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    # ==========================================
    # ===== КОМАНДА: STOPAUCTIONLOT =====
    # ==========================================
    
    @dp.message(Command("stopauctionlot"))
    async def stop_auction_lot(message: types.Message):
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Использование: /stopauctionlot (номер лота 1-15)")
            return
        
        try:
            lot_number = int(parts[1])
            
            if lot_number < 1 or lot_number > AUCTION_CONFIG["max_lots"]:
                await message.answer(f"❌ Номер лота должен быть от 1 до {AUCTION_CONFIG['max_lots']}!")
                return
            
            data = await load_auction_data()
            lots = data.get("lots", [])
            
            real_index = None
            active_count = 0
            for i, lot in enumerate(lots):
                if not lot.get("sold", False) and lot.get("is_active", True):
                    active_count += 1
                    if active_count == lot_number:
                        real_index = i
                        break
            
            if real_index is None:
                await message.answer(f"❌ Лот #{lot_number} не найден или уже продан!")
                return
            
            lot = lots[real_index]
            bidder_id = lot.get("current_bidder")
            bid_amount = lot.get("current_bid", 0)
            
            lot["is_active"] = False
            lot["sold"] = True
            
            if bidder_id and bid_amount > 0:
                users = await load_users()
                if bidder_id in users:
                    if bidder_id in frozen_bids:
                        frozen_bids[bidder_id] = max(0, frozen_bids.get(bidder_id, 0) - bid_amount)
                    
                    users[bidder_id]["money"] += bid_amount
                    await save_users(users)
                    
                    try:
                        await bot.send_message(
                            int(bidder_id),
                            f"🔄 Лот #{lot_number} ({lot['car_name']}) был остановлен администратором!\n"
                            f"💰 Ваши {bid_amount:,}₽ возвращены на баланс."
                        )
                    except:
                        pass
                    
                    refund_msg = f"💰 {bid_amount:,}₽ возвращены пользователю"
                else:
                    refund_msg = "⚠️ Пользователь не найден, деньги не возвращены"
            else:
                refund_msg = "ℹ️ Ставок не было"
            
            await save_auction_data(data)
            
            await message.answer(
                f"✅ Лот #{lot_number} остановлен!\n"
                f"🚗 {lot['car_name']}\n"
                f"{refund_msg}"
            )
            
        except ValueError:
            await message.answer("❌ Введите корректный номер лота!")
        except Exception as e:
            logger.error(f"Ошибка в stop_auction_lot: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    # ==========================================
    # ===== АДМИН-КОМАНДЫ ДЛЯ АУКЦИОНА =====
    # ==========================================
    
    @dp.message(Command("carlist"))
    async def car_list(message: types.Message):
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
        if not await is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        parts = message.text.split(maxsplit=4)
        if len(parts) < 5:
            await message.answer(
                "❌ Использование: /setcarauction (id машины) (начальная ставка) (кол-во) (слот 1-15)\n\n"
                "Пример: /setcarauction \"Монстр трак\" 1000000 1 3\n"
                "Для просмотра всех машин используйте /carlist\n"
                "Слоты: 1-15 (если слот занят, машина заменит существующую)"
            )
            return
        
        try:
            car_name = parts[1].strip()
            start_bid = int(parts[2])
            count = int(parts[3])
            slot = int(parts[4])
            
            if count <= 0 or start_bid <= 0:
                await message.answer("❌ Количество и ставка должны быть положительными!")
                return
            
            if slot < 1 or slot > AUCTION_CONFIG["max_lots"]:
                await message.answer(f"❌ Слот должен быть от 1 до {AUCTION_CONFIG['max_lots']}!")
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
            
            success, msg = await set_admin_auction_lots_with_slot(car_name, start_bid, count, slot)
            await message.answer(msg)
            
        except ValueError:
            await message.answer("❌ Введите корректные числа для ставки, количества и слота!")
        except Exception as e:
            logger.error(f"Ошибка в setcarauction: {e}")
            await message.answer(f"❌ Ошибка: {e}")

    @dp.message(Command("refreshauction"))
    async def refresh_auction(message: types.Message):
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
                f"<b>👤 ПРОФИЛЬ @{username}</b>\n\n"
                f"💰 Баланс: {found_user['money']:,.0f}₽\n"
                f"💎 BRcoins: {found_user['brcoins']}\n"
                f"📈 Заработано: {found_user['total_earned']:,.0f}₽\n"
                f"🤝 Сделок: {found_user['trades_count']}\n"
                f"⛔ Забанен: {'Да' if found_user.get('banned', False) else 'Нет'}\n\n"
                f"<b>📊 Портфель:</b>\n"
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
            
            await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
            
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
            
            if car_id.startswith("car_"):
                try:
                    index = int(car_id.replace("car_", "")) - 1
                    if 0 <= index < len(car_list):
                        car_name = car_list[index]
                except ValueError:
                    pass
            
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
                "📋 СПИСОК ID ФУНКЦИЙ:\n\n"
                "Работы:\n"
                "• job_1 - Шахта\n"
                "• job_2 - Ферма\n"
                "• job_3 - Трейдинг\n"
                "• job_4 - Водолаз\n\n"
                "Кнопки меню:\n"
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
                "Казино:\n"
                "• casinogame_1 - Кубик\n"
                "• casinogame_2 - Слоты\n"
                "• casinogame_3 - Мины\n\n"
                "Трейдинг:\n"
                "• trading_1 - BTC\n"
                "• trading_2 - WETcoin\n"
                "• trading_3 - NotCoin"
            )
            
            await message.answer(text)
            
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
            await message.answer(f"
