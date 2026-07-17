import logging
import asyncio
import time
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ПРАВИЛЬНЫЙ ИМПОРТ ДЛЯ БИБЛИОТЕКИ sofascrape==0.1.2
from sofascrape import SofaScore

# ===== НАСТРОЙКИ =====
TOKEN = "8831841766:AAGrxasQomUdSAat5KIspw2FhEsvv98mMI4"  # Вставьте ваш реальный токен
BREAK_THRESHOLD = 4        # Количество брейков подряд для уведомления
CHECK_INTERVAL = 25        # Интервал проверки в секундах
# =====================

logging.basicConfig(level=logging.INFO)
CHAT_ID = None
matches_tracking = {}

# ПРАВИЛЬНАЯ ИНИЦИАЛИЗАЦИЯ КЛИЕНТА
client = SofaScore()

# --- Обработчик команды /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    chat_id = update.effective_chat.id
    CHAT_ID = chat_id
    await update.message.reply_text(
        f"✅ Бот активирован! Ваш ID: `{chat_id}`\n"
        f"Отслеживаю теннисные матчи в реальном времени.\n"
        f"Уведомлю при {BREAK_THRESHOLD} брейках подряд!"
    )

# --- Обработчик текстовых сообщений ---
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает. Ожидайте уведомлений.")

# --- Функция получения живых теннисных матчей ---
def get_live_tennis_matches():
    """Получает список всех живых теннисных матчей с Sofascore"""
    try:
        # Получаем все живые события
        live_events = client.get_live_events()
        
        # Фильтруем только теннис
        tennis_matches = []
        for event in live_events:
            if event.get('sport') == 'Tennis' or event.get('category') == 'Tennis':
                tennis_matches.append(event)
        
        logging.info(f"Найдено живых теннисных матчей: {len(tennis_matches)}")
        return tennis_matches
    except Exception as e:
        logging.error(f"Ошибка получения матчей: {e}")
        return []

# --- Функция получения детальной статистики матча ---
def get_match_statistics(match_id):
    """Получает детальную статистику матча (включая брейки)"""
    try:
        match_data = client.get_event_data(match_id)
        return match_data
    except Exception as e:
        logging.error(f"Ошибка получения статистики матча {match_id}: {e}")
        return None

# --- Функция анализа матча на наличие брейков ---
def analyze_match(match_data):
    match_id = match_data.get('id')
    if not match_id:
        return False, None, None
    
    if match_id not in matches_tracking:
        matches_tracking[match_id] = {"breaks": 0, "notified": False, "last_score": ""}
    
    track = matches_tracking[match_id]
    if track["notified"]:
        return False, None, match_id
    
    try:
        # ВРЕМЕННАЯ ЗАГЛУШКА: случайная симуляция брейков
        is_break = random.choice([True, False, False])
        
        if is_break:
            track["breaks"] += 1
            logging.info(f"Матч {match_id}: брейк! Серия: {track['breaks']}")
        else:
            track["breaks"] = 0
        
        if track["breaks"] >= BREAK_THRESHOLD:
            track["notified"] = True
            player1 = match_data.get('homeTeam', {}).get('name', 'Игрок 1')
            player2 = match_data.get('awayTeam', {}).get('name', 'Игрок 2')
            score = match_data.get('score', {})
            current_score = f"{score.get('period1', '')} {score.get('period2', '')}"
            message = (
                f"🎾 {BREAK_THRESHOLD} БРЕЙКА ПОДРЯД!\n"
                f"Матч: {player1} vs {player2}\n"
                f"Счёт: {current_score}\n"
                f"Серия брейков: {track['breaks']}"
            )
            return True, message, match_id
        
        return False, None, match_id
        
    except Exception as e:
        logging.error(f"Ошибка анализа матча {match_id}: {e}")
        return False, None, match_id

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

# --- Основной цикл анализа ---
async def main_loop():
    logging.info("🔄 Запущен цикл анализа матчей...")
    while True:
        try:
            live_matches = get_live_tennis_matches()
            if not live_matches:
                logging.info("Нет живых теннисных матчей")
            else:
                for match in live_matches:
                    match_id = match.get('id')
                    if not match_id:
                        continue
                    
                    match_data = get_match_statistics(match_id)
                    if not match_data:
                        continue
                    
                    triggered, message, _ = analyze_match(match_data)
                    if triggered and message:
                        await send_notification(message)
            
            await asyncio.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            logging.error(f"Ошибка в цикле: {e}")
            await asyncio.sleep(60)

# --- ГЛАВНАЯ ФУНКЦИЯ ---
async def main():
    logging.info("🚀 Бот запущен! Ожидание команд...")
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    asyncio.create_task(main_loop())
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
