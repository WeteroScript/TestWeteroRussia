# test_handlers.py - временный файл для тестирования

from aiogram import Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import bot, logger

def register_test_handlers(dp: Dispatcher):
    
    # ==========================================
    # ТЕСТОВАЯ КНОПКА
    # ==========================================
    
    @dp.message(Command("test"))
    async def test_command(message: types.Message):
        logger.info("✅ /test КОМАНДА ВЫЗВАНА!")
        print("✅ /test КОМАНДА ВЫЗВАНА!")
        
        keyboard = [
            [InlineKeyboardButton(text="🧪 ТЕСТ КАЗИНО", callback_data="test_casino")],
            [InlineKeyboardButton(text="🧪 ТЕСТ БИЗНЕС", callback_data="test_business")],
            [InlineKeyboardButton(text="🧪 ТЕСТ ПОДДЕРЖКА", callback_data="test_support")],
            [InlineKeyboardButton(text="🧪 ТЕСТ АУКЦИОН", callback_data="test_auction")],
            [InlineKeyboardButton(text="🧪 ТЕСТ ПРОМОКОД", callback_data="test_promo")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
        ]
        
        await message.answer(
            "🧪 ТЕСТОВОЕ МЕНЮ\n\nНажми на кнопку для теста:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    @dp.callback_query(F.data == "test_casino")
    async def test_casino(callback: types.CallbackQuery):
        print("✅✅✅ КНОПКА КАЗИНО НАЖАТА!")
        logger.info("✅✅✅ КНОПКА КАЗИНО НАЖАТА!")
        await callback.answer("✅ Казино работает! Ставка: 1000", show_alert=True)

    @dp.callback_query(F.data == "test_business")
    async def test_business(callback: types.CallbackQuery):
        print("✅✅✅ КНОПКА БИЗНЕС НАЖАТА!")
        logger.info("✅✅✅ КНОПКА БИЗНЕС НАЖАТА!")
        await callback.answer("✅ Бизнес работает!", show_alert=True)

    @dp.callback_query(F.data == "test_support")
    async def test_support(callback: types.CallbackQuery):
        print("✅✅✅ КНОПКА ПОДДЕРЖКА НАЖАТА!")
        logger.info("✅✅✅ КНОПКА ПОДДЕРЖКА НАЖАТА!")
        await callback.answer("✅ Поддержка работает!", show_alert=True)

    @dp.callback_query(F.data == "test_auction")
    async def test_auction(callback: types.CallbackQuery):
        print("✅✅✅ КНОПКА АУКЦИОН НАЖАТА!")
        logger.info("✅✅✅ КНОПКА АУКЦИОН НАЖАТА!")
        await callback.answer("✅ Аукцион работает!", show_alert=True)

    @dp.callback_query(F.data == "test_promo")
    async def test_promo(callback: types.CallbackQuery):
        print("✅✅✅ КНОПКА ПРОМОКОД НАЖАТА!")
        logger.info("✅✅✅ КНОПКА ПРОМОКОД НАЖАТА!")
        await callback.answer("✅ Промокод работает!", show_alert=True)

    logger.info("✅ Тестовые обработчики зарегистрированы!")
