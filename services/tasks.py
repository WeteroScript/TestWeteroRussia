import asyncio
import random
import string
from datetime import datetime
from database.file_manager import (
    load_users, load_settings, save_settings, 
    load_business, save_business, 
    load_inventory, save_inventory, 
    load_promocodes, save_promocodes
)
from config import PROMO_CHANNEL_ID, bot, logger, BUSINESS_CONFIG

promo_running = False
promo_task = None
business_running = False
business_check_task = None
business_notified = {}

# ========== ПРОМОКОДЫ ==========
async def generate_and_send_promo():
    try:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        is_brcoins = random.choice([True, False])
        
        if is_brcoins:
            amount = random.randint(100, 1000)
            uses = random.randint(1, 3)
            promo_type = "brcoins"
            type_text = "BRcoins"
        else:
            amount = random.randint(20000000, 100000000)
            uses = random.randint(3, 5)
            promo_type = "money"
            type_text = "₽"
        
        promocodes = await load_promocodes()
        promocodes[code] = {
            "type": promo_type,
            "uses": uses,
            "used": 0,
            "amount": amount
        }
        await save_promocodes(promocodes)
        
        message_text = (
            f"🎁 **Новый промокод!**\n\n"
            f"📌 Код: `{code}`\n"
            f"🎁 Награда: {amount:,} {type_text}\n"
            f"🔄 Активаций: {uses}\n\n"
            f"👉 Забирай быстрее!"
        )
        await bot.send_message(
            PROMO_CHANNEL_ID,
            message_text,
            parse_mode="Markdown"
        )
        logger.info(f"✅ Промокод отправлен: {code}")
    except Exception as e:
        logger.error(f"❌ Ошибка при генерации промокода: {e}")

async def promo_auto_loop():
    global promo_running
    while promo_running:
        try:
            settings = await load_settings()
            if settings.get("promo_auto", False):
                await generate_and_send_promo()
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле промокодов: {e}")
        await asyncio.sleep(5400)

# ========== БИЗНЕС ==========
async def check_business_loop():
    global business_running, business_notified
    while business_running:
        try:
            business = await load_business()
            users = await load_users()
            
            for user_id, data in users.items():
                user_business = data.get("business", {})
                notified_biz = business_notified.get(user_id, [])
                
                for biz_key, biz_data in user_business.items():
                    if biz_data.get("owned", False):
                        last_collect = biz_data.get("last_collect")
                        if last_collect:
                            last_time = datetime.fromisoformat(last_collect)
                            elapsed = (datetime.now() - last_time).total_seconds()
                            cooldown = BUSINESS_CONFIG[biz_key]["cooldown"]
                            
                            if elapsed >= cooldown and not biz_data.get("auto_collect", False):
                                if biz_key not in notified_biz:
                                    try:
                                        config = BUSINESS_CONFIG[biz_key]
                                        await bot.send_message(
                                            int(user_id),
                                            f"🏢 {config['emoji']} {config['name']} готов к сбору дохода!\n"
                                            f"Нажмите /start и зайдите в раздел Бизнес"
                                        )
                                        if user_id not in business_notified:
                                            business_notified[user_id] = []
                                        business_notified[user_id].append(biz_key)
                                    except Exception as e:
                                        logger.warning(f"Не удалось уведомить пользователя {user_id}: {e}")
                            else:
                                if biz_key in notified_biz:
                                    business_notified[user_id].remove(biz_key)
            
            business_notified = {k: v for k, v in business_notified.items() if v}
            
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле проверки бизнеса: {e}")
        await asyncio.sleep(60)
