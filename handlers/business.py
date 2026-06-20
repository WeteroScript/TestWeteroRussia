from aiogram import types
from aiogram import F
from aiogram.fsm.context import FSMContext
from config import BUSINESS_CONFIG, bot, logger
from database.file_manager import load_users, save_users, load_business, save_business, load_inventory, save_inventory
from utils.helpers import check_access, get_default_user

def register_business_handlers(dp):
    
    @dp.callback_query(F.data == "business")
    async def business_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        if not await check_access(callback):
            return
        
        try:
            # ... бизнес-логика
            pass
        except Exception as e:
            logger.error(f"Ошибка в business_menu: {e}")
            await callback.answer("⚠️ Ошибка!", show_alert=True)
        
        await callback.answer()
