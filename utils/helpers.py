import random
import string
from datetime import datetime
from config import ADMIN_IDS, CHANNEL_ID, logger, bot, file_locks
from database.file_manager import load_users, load_settings, save_settings, load_disabled_functions

async def is_admin(user_id):
    return user_id in ADMIN_IDS

async def is_bot_enabled():
    settings = await load_settings()
    return settings.get("bot_enabled", True)

async def check_subscription(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.warning(f"Ошибка проверки подписки: {e}")
        return False

async def is_function_disabled(function_id):
    """Проверяет, отключена ли функция"""
    disabled = await load_disabled_functions()
    return function_id in disabled.get("functions", [])

async def check_access(message_or_callback):
    user_id = message_or_callback.from_user.id
    
    if await is_admin(user_id):
        return True
    
    if not await check_subscription(user_id):
        channel_username = "@WeteroRussia"
        message = (
            f"📢 Для использования бота подпишитесь на наш канал {channel_username}!\n\n"
            f"👉 [Подписаться](https://t.me/+TAhbj7PhoWhhZTQ6)\n\n"
            "После подписки нажмите /start"
        )
        
        try:
            if isinstance(message_or_callback, types.Message):
                await message_or_callback.answer(message, parse_mode="Markdown")
            elif isinstance(message_or_callback, types.CallbackQuery):
                await message_or_callback.answer(
                    f"📢 Подпишитесь на канал {channel_username}!",
                    show_alert=True
                )
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения доступа: {e}")
        return False
    
    if not await is_bot_enabled():
        try:
            if isinstance(message_or_callback, types.Message):
                await message_or_callback.answer("🔧 Бот на техническом обслуживании!")
            elif isinstance(message_or_callback, types.CallbackQuery):
                await message_or_callback.answer("🔧 Бот на техобслуживании!", show_alert=True)
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения о техобслуживании: {e}")
        return False
    
    return True

def get_default_user():
    return {
        "money": 1000000,
        "brcoins": 1000,
        "energy": 100,
        "total_earned": 0,
        "trades_count": 0,
        "role": "user",
        "donate_spent": 0,
        "donate_received": 0,
        "inventory": [],
        "mine_attempts": 100,
        "last_mine_reset": datetime.now().isoformat(),
        "portfolio": {
            "BTC": 0,
            "WETcoin": 0,
            "NotCoin": 0
        },
        "business": {
            "auto_mine": {"owned": False, "last_collect": None, "auto_collect": False},
            "tech_center": {"owned": False, "last_collect": None, "auto_collect": False},
            "tire_center": {"owned": False, "last_collect": None, "auto_collect": False},
            "styling_center": {"owned": False, "last_collect": None, "auto_collect": False},
            "shop_24": {"owned": False, "last_collect": None, "auto_collect": False}
        },
        "farm": {
            "milk": 0,
            "hay": 0,
            "eggs": 0,
            "wheat": 0,
            "meat": 0,
            "last_collect": None
        },
        "casino": {
            "bet": 0,
            "mines_count": 4,
            "field_size": 5
        },
        "banned": False
    }
