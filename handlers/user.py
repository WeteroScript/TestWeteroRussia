from aiogram import types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import bot, logger
from database.file_manager import load_users, save_users
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

    # ========== ИГРА "КУБИК" (НОВЫЕ КОЭФФИЦИЕНТЫ) ==========
    @dp.callback_query(F.data == "dice_game")
    async def dice_game(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        # НОВЫЕ ПАРАМЕТРЫ:
        win_chance = 0.45  # 45% (было 50%)
        multiplier = 1.3   # 1.3x (было 2.0)
        
        user_id = str(callback.from_user.id)
        users = await load_users()
        user = users.get(user_id, get_default_user())
        
        bet = user.get("casino", {}).get("bet", 0)
        if bet <= 0:
            await callback.answer("💰 Сначала сделайте ставку через /bet", show_alert=True)
            return
        
        if user["money"] < bet:
            await callback.answer("❌ Недостаточно средств!", show_alert=True)
            return
        
        # Расчет выигрыша
        is_win = random.random() < win_chance
        
        if is_win:
            win_amount = int(bet * multiplier)
            user["money"] += win_amount
            result_text = f"🎉 Вы выиграли {win_amount:,}₽ (коэффициент {multiplier}x)!"
        else:
            user["money"] -= bet
            result_text = f"😔 Вы проиграли {bet:,}₽"
        
        await save_users(users)
        
        await callback.message.edit_text(
            f"{result_text}\n\n"
            f"💰 Баланс: {user['money']:,}₽\n"
            f"🎲 Шанс выигрыша: {win_chance*100:.0f}%",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🎲 Ещё раз", callback_data="dice_game")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="casino")]
                ]
            )
        )
        await callback.answer()

    # ========== ИГРА "МИНЫ" (НОВЫЕ КОЭФФИЦИЕНТЫ) ==========
    @dp.callback_query(F.data == "mines_game")
    async def mines_game(callback: types.CallbackQuery):
        if not await check_access(callback):
            return
        
        # НОВЫЕ КОЭФФИЦИЕНТЫ для мин:
        multipliers = {
            1: 0.8,
            2: 1.0,
            3: 1.1,
            4: 1.25,
            5: 1.35,
            6: 1.50
        }
        # для 7+ добавляем по 0.15
        def get_multiplier(cells):
            if cells <= 6:
                return multipliers.get(cells, 1.0)
            return 1.50 + (cells - 6) * 0.15
        
        user_id = str(callback.from_user.id)
        users = await load_users()
        user = users.get(user_id, get_default_user())
        
        bet = user.get("casino", {}).get("bet", 0)
        if bet <= 0:
            await callback.answer("💰 Сначала сделайте ставку через /bet", show_alert=True)
            return
        
        # Здесь должна быть логика игры "Мины" с использованием get_multiplier()
        # Например, при открытии N клеток:
        # cells_opened = 3
        # multiplier = get_multiplier(cells_opened)
        
        await callback.answer("🔄 Логика мин с новыми коэффициентами готова, доработайте UI", show_alert=True)
