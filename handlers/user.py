import random
from datetime import datetime

from aiogram import types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import bot, logger
from database.file_manager import load_users, save_users, load_promocodes, save_promocodes
from utils.helpers import check_access, get_default_user, check_subscription
from services.currency import currency_rates

class TradeStates(StatesGroup):
    waiting_for_amount = State()

class SupportStates(StatesGroup):
    waiting_for_message = State()

def register_user_handlers(dp):
    
    async def get_main_menu(user_id):
        users = await load_users()
        user = users.get(str(user_id), get_default_user())
        
        currency_rates.update_rates()
        
        text = (
            f"Главное меню\n\n"
            f"Баланс: {user['money']:,.0f}₽\n"
            f"BRcoins: {user['brcoins']}\n"
            f"BTC: {user['portfolio'].get('BTC', 0)}\n"
            f"WETcoin: {user['portfolio'].get('WETcoin', 0)}\n"
            f"NotCoin: {user['portfolio'].get('NotCoin', 0)}"
        )
        
        keyboard = [
            [InlineKeyboardButton(text="💼 Работы", callback_data="works")],
            [InlineKeyboardButton(text="💎 Донат", callback_data="donate")],
            [InlineKeyboardButton(text="🏆 Форбс", callback_data="forbes")],
            [InlineKeyboardButton(text="🏠 Гараж", callback_data="garage")],
            [InlineKeyboardButton(text="📦 Инвентарь", callback_data="inventory_main")],
            [InlineKeyboardButton(text="🔄 Скупщик", callback_data="buyer")],
            [InlineKeyboardButton(text="🏢 Бизнес", callback_data="business")],
            [InlineKeyboardButton(text="🎰 Казино", callback_data="casino")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton(text="🆘 Тех.поддержка", callback_data="support")]
        ]
        
        return text, InlineKeyboardMarkup(inline_keyboard=keyboard)

    @dp.message(Command("start"))
    async def start_command(message: types.Message):
        user_id = str(message.from_user.id)
        
        try:
            if not await check_subscription(message.from_user.id):
                await message.answer(
                    "📢 Подпишитесь на канал @WeteroRussia!\n\n"
                    "👉 [Подписаться](https://t.me/+TAhbj7PhoWhhZTQ6)\n\n"
                    "После подписки нажмите /start",
                    parse_mode="Markdown"
                )
                return
            
            users = await load_users()
            
            if user_id not in users:
                users[user_id] = get_default_user()
                await save_users(users)
            
            if not await check_access(message):
                return
            
            text, keyboard = await get_main_menu(message.from_user.id)
            await message.answer(text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка в start_command: {e}")
            await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")

    @dp.callback_query(F.data == "back_main")
    async def back_main(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        try:
            text, keyboard = await get_main_menu(callback.from_user.id)
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка в back_main: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== ПРОМОКОДЫ (ИСПРАВЛЕНО) =====
    # ==========================================

    @dp.message(F.text, ~F.text.startswith('/'))
    async def handle_promo(message: types.Message, state: FSMContext):
        """Обработка промокодов"""
        # Проверяем, что мы не в другом состоянии
        current_state = await state.get_state()
        if current_state is not None:
            return
        
        if not await check_access(message):
            return
        
        try:
            user_id = str(message.from_user.id)
            users = await load_users()
            user = users.get(user_id)
            
            if not user:
                return
            
            # Проверяем, что это похоже на промокод (короткое сообщение из букв/цифр)
            text = message.text.strip()
            if len(text) > 20 or not text.isalnum():
                return
            
            promocodes = await load_promocodes()
            code = text.upper()
            
            if code in promocodes:
                promo = promocodes[code]
                if promo["used"] >= promo["uses"]:
                    await message.answer("❌ Промокод уже использован!")
                    return
                
                if promo["type"] == "brcoins":
                    user["brcoins"] += promo["amount"]
                    user["donate_received"] += promo["amount"]
                    currency_name = "BRcoins"
                else:
                    user["money"] += promo["amount"]
                    user["total_earned"] += promo["amount"]
                    currency_name = "₽"
                
                promo["used"] += 1
                users[user_id] = user
                
                await save_promocodes(promocodes)
                await save_users(users)
                
                await message.answer(
                    f"✅ Промокод активирован!\n"
                    f"💰 +{promo['amount']:,} {currency_name}"
                )
            else:
                # Не показываем ошибку для обычных сообщений
                pass
        except Exception as e:
            logger.error(f"Ошибка в handle_promo: {e}")
