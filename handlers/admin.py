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
    frozen_bids  # Импортируем frozen_bids для возврата денег
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
    # ===== НОВЫЕ КОМАНДЫ: BAN / UNBAN =====
    # ==========================================
    
    @dp.message(Command("ban"))
    async def ban_user(message: types.Message):
        """Блокировка пользователя"""
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
                        
                        # Уведомляем пользователя
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
        """Разблокировка пользователя"""
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
                        
                        # Уведомляем пользователя
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
    # ===== НОВАЯ КОМАНДА: STOPAUCTIONLOT =====
    # ==========================================
    
    @dp.message(Command("stopauctionlot"))
    async def stop_auction_lot(message: types.Message):
        """Остановить лот аукциона и вернуть деньги"""
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
            
            # Проверяем реальный индекс (учитывая, что некоторые лоты могут быть проданы)
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
            
            # Останавливаем лот
            lot["is_active"] = False
            lot["sold"] = True
            
            # Возвращаем деньги, если была ставка
            if bidder_id and bid_amount > 0:
                users = await load_users()
                if bidder_id in users:
                    # Возвращаем замороженные средства
                    if bidder_id in frozen_bids:
                        frozen_bids[bidder_id] = max(0, frozen_bids.get(bidder_id, 0) - bid_amount)
                    
                    users[bidder_id]["money"] += bid_amount
                    await save_users(users)
                    
                    # Уведомляем пользователя
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

    # ... (остальные админ-команды остаются без изменений)
