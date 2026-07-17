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

# --- Обработчик команды /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    chat_id = update.effective_chat.id
    CHAT_ID = chat_id
    await update.message.reply_text(
        f"✅ Бот активирован! Ваш ID: `{chat_id}`\n"
        f"Буду уведомлять при {BREAK_THRESHOLD} брейках ПОДРЯД."
    )

# --- Обработчик текстовых сообщений ---
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает. Ожидайте уведомлений.")

# --- Анализ матчей (заглушка) ---
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

# --- Отправка уведомлений ---
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

# --- Фоновый цикл анализа ---
async def main_loop():
    logging.info("🔄 Запущен цикл анализа матчей...")
    while True:
        try:
            # Временные тестовые данные
            test_matches = [{"id": 1}, {"id": 2}, {"id": 3}]
            for match in test_matches:
                result = analyze_match(match)
                if result:
                    await send_notification(result)
            await asyncio.sleep(25)
        except Exception as e:
            logging.error(f"Ошибка в цикле: {e}")
            await asyncio.sleep(60)

# --- ГЛАВНАЯ ФУНКЦИЯ ---
def main():
    logging.info("🚀 Бот запущен! Ожидание команд...")
    
    # Создаём приложение
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Получаем цикл событий
    loop = asyncio.get_event_loop()
    
    # Запускаем фоновую задачу в этом же цикле
    loop.create_task(main_loop())
    
    # Запускаем поллинг (основной цикл бота)
    app.run_polling()

if __name__ == "__main__":
    main()
