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

# ========== БИЗНЕС (АВТО-СБОР) ==========
async def check_business_loop():
    """Цикл автоматического сбора бизнесов"""
    global business_running, business_notified
    while business_running:
        try:
            business = await load_business()
            users = await load_users()
            inventory = await load_inventory()
            
            for user_id, data in users.items():
                user_business = data.get("business", {})
                
                for biz_key, biz_data in user_business.items():
                    if biz_data.get("owned", False) and biz_data.get("auto_collect", False):
                        last_collect = biz_data.get("last_collect")
                        if last_collect:
                            last_time = datetime.fromisoformat(last_collect)
                            elapsed = (datetime.now() - last_time).total_seconds()
                            cooldown = BUSINESS_CONFIG[biz_key]["cooldown"]
                            
                            if elapsed >= cooldown:
                                # Автоматический сбор
                                config = BUSINESS_CONFIG[biz_key]
                                
                                if config["profit_type"] == "money":
                                    profit = random.randint(config["profit_min"], config["profit_max"])
                                    data["money"] += profit
                                    data["total_earned"] += profit
                                    
                                    if biz_key in business:
                                        business[biz_key]["total_earned"] = business[biz_key].get("total_earned", 0) + profit
                                    
                                    # Уведомление
                                    try:
                                        await bot.send_message(
                                            int(user_id),
                                            f"🏢 {config['emoji']} {config['name']}\n"
                                            f"💰 Авто-сбор: +{profit:,.0f}₽"
                                        )
                                    except:
                                        pass
                                    
                                elif config["profit_type"] == "resources":
                                    if user_id not in inventory:
                                        inventory[user_id] = []
                                    
                                    num_resources = random.randint(config["min_resources"], config["max_resources"])
                                    resources_text = []
                                    
                                    for _ in range(num_resources):
                                        resources = config["resources"]
                                        total_chance = sum(r["chance"] for r in resources)
                                        roll = random.random() * total_chance
                                        cumulative = 0
                                        selected_resource = resources[0]["name"]
                                        
                                        for res in resources:
                                            cumulative += res["chance"]
                                            if roll <= cumulative:
                                                selected_resource = res["name"]
                                                break
                                        
                                        inventory[user_id].append(selected_resource)
                                        resources_text.append(selected_resource)
                                    
                                    if biz_key in business:
                                        business[biz_key]["total_earned"] = business[biz_key].get("total_earned", 0) + num_resources
                                    
                                    # Уведомление
                                    try:
                                        resource_counts = {}
                                        for res in resources_text:
                                            resource_counts[res] = resource_counts.get(res, 0) + 1
                                        
                                        text = f"🏢 {config['emoji']} {config['name']}\n"
                                        text += f"📦 Авто-сбор: +{num_resources} ресурсов\n"
                                        for res_name, count in resource_counts.items():
                                            text += f"   • {res_name}: {count} шт.\n"
                                        
                                        await bot.send_message(int(user_id), text)
                                    except:
                                        pass
                                
                                # Обновляем время последнего сбора
                                biz_data["last_collect"] = datetime.now().isoformat()
                                user_business[biz_key]["last_collect"] = datetime.now().isoformat()
                                
                                # Сохраняем изменения
                                users[user_id] = data
                                await save_users(users)
                                await save_inventory(inventory)
                                await save_business(business)
            
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле проверки бизнеса: {e}")
        await asyncio.sleep(60)
