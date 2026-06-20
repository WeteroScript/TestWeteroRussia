from aiogram import types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_IDS, bot, logger, BUSINESS_CONFIG
from database.file_manager import (
    load_users, save_users, load_business, save_business,
    load_settings, save_settings, load_promocodes, save_promocodes,
    load_disabled_functions, save_disabled_functions
)
from utils.helpers import is_admin
from services.currency import currency_rates
from services.tasks import promo_running, promo_task, promo_auto_loop
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
            "`/stopfunction function_id` - блокировка/разблокировка функции"
        )
        
        await message.answer(help_text, parse_mode="Markdown")

    # ========== КОМАНДА /stopfunction (ИСПРАВЛЕНА) ==========
    @dp.message(Command("stopfunction"))
    async def stop_function(message: types.Message):
        if not is_admin(message.from_user.id):
            await message.answer("⛔ У вас нет прав!")
            return
        
        args = message.text.split()
        if len(args) < 2:
            await message.answer("❌ Использование: /stopfunction function_id")
            return
        
        function_id = args[1]
        disabled = await load_disabled_functions()
        
        if function_id in disabled["functions"]:
            disabled["functions"].remove(function_id)
            await message.answer(f"✅ Функция {function_id} снова активна.")
        else:
            disabled["functions"].append(function_id)
            await message.answer(f"⛔ Функция {function_id} заблокирована.")
        
        await save_disabled_functions(disabled)

    # ========== ОСТАЛЬНЫЕ АДМИН-КОМАНДЫ ==========
    # (здесь должны быть остальные команды: resetbusiness, givebusiness, 
    # giverub, givedonate, promostart, technical, status, getdb, mailall, 
    # createpromo, update_rates_admin и т.д.)
    # Они остаются без изменений, просто убедитесь, что они не используют 
    # CONTAINERS и AUCTION
