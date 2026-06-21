#!/usr/bin/env python3
import asyncio
import sys
from config import bot, dp, logger, ADMIN_IDS
from database.file_manager import load_settings
from services.tasks import promo_auto_loop, check_business_loop, promo_running, promo_task, business_running, business_check_task
from services.auction import auction_update_loop, update_auction_lots, auction_running
from handlers.admin import register_admin_handlers
from handlers.business import register_business_handlers
from handlers.user import register_user_handlers

async def main():
    global promo_running, promo_task, business_running, business_check_task, auction_running
    
    logger.info("🤖 Бот запущен!")
    logger.info(f"👑 Админы: {ADMIN_IDS}")
    
    # Регистрируем все обработчики
    register_user_handlers(dp)
    register_admin_handlers(dp)
    register_business_handlers(dp)
    
    try:
        # Запускаем бизнес-цикл
        business_running = True
        business_check_task = asyncio.create_task(check_business_loop())
        logger.info("🏢 Цикл проверки бизнесов запущен!")
        
        # Запускаем цикл аукциона
        auction_running = True
        auction_task = asyncio.create_task(auction_update_loop())
        logger.info("🚗 Цикл обновления аукциона запущен!")
        
        # Инициализируем аукцион
        await update_auction_lots()
        logger.info("🚗 Аукцион инициализирован!")
        
        # Запускаем промокоды если включены
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
