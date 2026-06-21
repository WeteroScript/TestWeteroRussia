import random
from datetime import datetime

from aiogram import types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import bot, logger
from database.file_manager import load_users, save_users, load_promocodes, save_promocodes, load_inventory
from utils.helpers import check_access, get_default_user, check_subscription
from services.currency import currency_rates

class TradeStates(StatesGroup):
    waiting_for_amount = State()

class SupportStates(StatesGroup):
    waiting_for_message = State()

class CasinoStates(StatesGroup):
    waiting_for_bet = State()
    waiting_for_mines = State()
    waiting_for_field_size = State()

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
    # ===== КУБИК (ИСПРАВЛЕННЫЙ) =====
    # ==========================================
    
    @dp.callback_query(F.data == "casino_dice")
    async def casino_dice(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        if await is_function_disabled("casinogame_1"):
            await callback.answer("⛔ Эта функция остановлена администратором!", show_alert=True)
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            bet = user.get("casino", {}).get("bet", 0)
            if bet <= 0:
                await callback.answer("❌ Сначала установите ставку!", show_alert=True)
                return
            
            if user["money"] < bet:
                await callback.answer(f"❌ Недостаточно средств! У вас {user['money']:,.0f}₽", show_alert=True)
                return
            
            keyboard = [
                [InlineKeyboardButton(text="🎲 Четное", callback_data="dice_even")],
                [InlineKeyboardButton(text="🎲 Нечетное", callback_data="dice_odd")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="casino")]
            ]
            
            await callback.message.edit_text(
                f"🎲 КУБИК\n\n"
                f"💰 Ставка: {bet:,.0f}₽\n"
                f"Коэффициент: 1.3x\n\n"
                f"Выберите: Четное или Нечетное",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в casino_dice: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    @dp.callback_query(F.data.startswith("dice_"))
    async def dice_play(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            choice = callback.data.replace("dice_", "")
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            bet = user.get("casino", {}).get("bet", 0)
            if bet <= 0:
                await callback.answer("❌ Ставка не установлена!", show_alert=True)
                return
            
            if user["money"] < bet:
                await callback.answer(f"❌ Недостаточно средств!", show_alert=True)
                return
            
            # Шанс выигрыша 35%
            win_chance = 0.35
            multiplier = 1.3
            
            dice_result = random.randint(1, 6)
            is_even = dice_result % 2 == 0
            
            is_win = (choice == "even" and is_even) or (choice == "odd" and not is_even)
            
            # Проверяем шанс выигрыша
            if random.random() > win_chance:
                is_win = False
            
            if is_win:
                win = int(bet * multiplier)
                user["money"] += win
                user["total_earned"] += win
                result_text = f"✅ ВЫИГРЫШ!\n🎲 Выпало: {dice_result}\n💰 +{win:,.0f}₽ (x{multiplier})"
            else:
                user["money"] -= bet
                result_text = f"❌ ПРОИГРЫШ!\n🎲 Выпало: {dice_result}\n💸 -{bet:,.0f}₽"
            
            users[user_id] = user
            await save_users(users)
            
            await callback.message.edit_text(
                f"🎲 КУБИК\n\n{result_text}\n\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎲 Играть ещё", callback_data="casino_dice")],
                    [InlineKeyboardButton(text="🔙 В казино", callback_data="casino")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в dice_play: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== СЛОТЫ (ИСПРАВЛЕННЫЕ) =====
    # ==========================================
    
    @dp.callback_query(F.data == "slots_spin")
    async def slots_spin(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        try:
            user_id = str(callback.from_user.id)
            users = await load_users()
            user = users.get(user_id, get_default_user())
            
            bet = user.get("casino", {}).get("bet", 0)
            if bet <= 0:
                await callback.answer("❌ Ставка не установлена!", show_alert=True)
                return
            
            if user["money"] < bet:
                await callback.answer(f"❌ Недостаточно средств!", show_alert=True)
                return
            
            symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣"]
            result = [random.choice(symbols) for _ in range(3)]
            
            win = 0
            
            # Проверяем выигрышные комбинации
            if result[0] == result[1] == result[2]:
                # Три одинаковых
                if result[0] == "7️⃣":
                    win = bet * 5
                elif result[0] == "💎":
                    win = bet * 3
                else:
                    win = bet * 2
            elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
                # Два одинаковых
                win = int(bet * 1.5)
            else:
                # Нет совпадений - маленький шанс на выигрыш
                if random.random() < 0.05:
                    win = int(bet * 0.5)
            
            win = int(win)
            
            if win > 0:
                user["money"] += win
                user["total_earned"] += win
                result_text = f"✅ ВЫИГРЫШ!\n🎰 {result[0]} {result[1]} {result[2]}\n💰 +{win:,.0f}₽"
            else:
                user["money"] -= bet
                result_text = f"❌ ПРОИГРЫШ!\n🎰 {result[0]} {result[1]} {result[2]}\n💸 -{bet:,.0f}₽"
            
            users[user_id] = user
            await save_users(users)
            
            await callback.message.edit_text(
                f"🎰 СЛОТЫ\n\n{result_text}\n\n"
                f"💳 Новый баланс: {user['money']:,.0f}₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎰 Крутить ещё", callback_data="slots_spin")],
                    [InlineKeyboardButton(text="🔙 В казино", callback_data="casino")]
                ])
            )
        except Exception as e:
            logger.error(f"Ошибка в slots_spin: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()

    # ==========================================
    # ===== ПРОМОКОДЫ =====
    # ==========================================

    @dp.message(F.text, ~F.text.startswith('/'))
    async def handle_promo(message: types.Message, state: FSMContext):
        """Обработка промокодов"""
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
        except Exception as e:
            logger.error(f"Ошибка в handle_promo: {e}")
