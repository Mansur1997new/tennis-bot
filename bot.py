import logging
import asyncio
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== НАСТРОЙКИ =====
TOKEN = "8831841766:AAGrxasQomUdSAat5KIspw2FhEsvv98mMI4"  # Вставьте ваш реальный токен
BREAK_THRESHOLD = 4
# =====================

logging.basicConfig(level=logging.INFO)
CHAT_ID = None
matches_tracking = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    chat_id = update.effective_chat.id
    CHAT_ID = chat_id
    await update.message.reply_text(
        f"✅ Бот активирован! Ваш ID: `{chat_id}`\n"
        f"Буду уведомлять при {BREAK_THRESHOLD} брейках ПОДРЯД."
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает. Ожидайте уведомлений.")

def analyze_match(match_data):
    match_id = match_data.get("id")
    if not match_id:
        return None
    if match_id not in matches_tracking:
        matches_tracking[match_id] = {"breaks": 0, "notified": False}
    
    track = matches_tracking[match_id]
    if track["notified"]:
        return None
    
    # Симуляция брейка (25% шанс)
    is_break = random.choice([True, False, False, False])
    if is_break:
        track["breaks"] += 1
        logging.info(f"Матч {match_id}: брейк! Серия: {track['breaks']}")
    else:
        track["breaks"] = 0
    
    if track["breaks"] >= BREAK_THRESHOLD:
        track["notified"] = True
        return f"🎾 {BREAK_THRESHOLD} БРЕЙКА ПОДРЯД в матче {match_id}!"
    return None

async def send_notification(text):
    global CHAT_ID
    if CHAT_ID is None:
        logging.warning("CHAT_ID не установлен. Напишите /start")
        return
    try:
        app = Application.builder().token(TOKEN).build()
        await app.bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        logging.error(f"Ошибка отправки: {e}")

async def main_loop():
    logging.info("🔄 Запущен цикл анализа матчей...")
    while True:
        try:
            test_matches = [{"id": 1}, {"id": 2}, {"id": 3}]
            for match in test_matches:
                result = analyze_match(match)
                if result:
                    await send_notification(result)
            await asyncio.sleep(25)
        except Exception as e:
            logging.error(f"Ошибка в цикле: {e}")
            await asyncio.sleep(60)

# ===== ОСНОВНАЯ ФУНКЦИЯ (исправлена) =====
async def main():
    logging.info("🚀 Бот запущен! Ожидание команд...")
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Запускаем фоновый цикл как задачу
    asyncio.create_task(main_loop())
    
    # Запускаем поллинг
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
