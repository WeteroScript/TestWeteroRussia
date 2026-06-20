#!/usr/bin/env python3
import asyncio
import sys
from config import bot, dp, logger, ADMIN_IDS
from database.file_manager import load_settings
from services.tasks import (
    promo_auto_loop, check_business_loop
)
from core.handlers import register_handlers

promo_running = False
promo_task = None
business_running = False
business_check_task = None

async def main():
    global promo_running, promo_task, business_running, business_check_task
    
    logger.info("🤖 Бот запущен!")
    logger.info(f"👑 Админы: {ADMIN_IDS}")
    
    register_handlers(dp)
    
    try:
        business_running = True
        business_check_task = asyncio.create_task(check_business_loop())
        logger.info("🏢 Цикл проверки бизнесов запущен!")
        
        settings = await load_settings()
        
        if settings.get("promo_auto", False):
            promo_running = True
            promo_task = asyncio.create_task(promo_auto_loop())
            logger.info("📢 Авто-промокоды запущены!")
        
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Завершение работы")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)
