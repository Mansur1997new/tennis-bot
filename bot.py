import logging
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== НАСТРОЙКИ =====
TOKEN = "8831841766:AAGrxasQomUdSAat5KIspw2FhEsvv98mMI4"  # Вставьте ваш реальный токен
BREAK_THRESHOLD = 4        # Количество брейков подряд для уведомления
CHECK_INTERVAL = 25        # Интервал проверки в секундах
# =====================

logging.basicConfig(level=logging.INFO)
CHAT_ID = None
matches_tracking = {}

# --- Обработчики команд ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    chat_id = update.effective_chat.id
    CHAT_ID = chat_id
    await update.message.reply_text(
        f"✅ Бот активирован! Ваш ID: `{chat_id}`\n"
        f"Отслеживаю теннисные матчи. Уведомлю при {BREAK_THRESHOLD} брейках подряд!"
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает. Ожидайте уведомлений.")

# --- Функции для работы с Sofascore API ---
async def get_live_tennis_matches():
    url = "https://api.sofascore.com/api/v1/sport/tennis/events/live"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('events', [])
                return []
    except Exception as e:
        logging.error(f"Ошибка получения матчей: {e}")
        return []

async def get_match_incidents(match_id):
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/incidents"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('incidents', [])
                return []
    except Exception as e:
        logging.error(f"Ошибка получения инцидентов: {e}")
        return []

# --- Логика анализа брейков ---
def analyze_breaks(match_id, incidents):
    if match_id not in matches_tracking:
        matches_tracking[match_id] = {"breaks": 0, "notified": False, "last_game": 0}
    
    track = matches_tracking[match_id]
    if track["notified"]:
        return False, None
    
    sorted_incidents = sorted(incidents, key=lambda x: x.get('time', 0))
    new_breaks = 0
    last_game = track["last_game"]
    server_id = None
    
    for incident in sorted_incidents:
        if incident.get('type') == 'game':
            game_num = incident.get('game', {}).get('number', 0)
            if game_num <= last_game:
                continue
            winner = incident.get('winner', {}).get('id')
            server = incident.get('server', {}).get('id')
            # Если подающий есть и он не победитель -> брейк
            if server and winner and server != winner:
                new_breaks += 1
            else:
                # Если брейка не было, сбрасываем серию
                track["breaks"] = 0
            last_game = game_num
    
    if new_breaks > 0:
        track["breaks"] += new_breaks
    track["last_game"] = last_game
    
    if track["breaks"] >= BREAK_THRESHOLD:
        track["notified"] = True
        return True, track["breaks"]
    
    return False, None

# --- Фоновый цикл ---
async def analysis_loop():
    while True:
        try:
            matches = await get_live_tennis_matches()
            for match in matches:
                match_id = match.get('id')
                if not match_id:
                    continue
                incidents = await get_match_incidents(match_id)
                if incidents:
                    triggered, count = analyze_breaks(match_id, incidents)
                    if triggered:
                        await send_notification(
                            f"🎾 {BREAK_THRESHOLD} БРЕЙКА ПОДРЯД!\n"
                            f"Матч: {match.get('homeTeam', {}).get('name', '')} - {match.get('awayTeam', {}).get('name', '')}\n"
                            f"Серия: {count}"
                        )
            await asyncio.sleep(CHECK_INTERVAL)
        except Exception as e:
            logging.error(f"Ошибка в цикле: {e}")
            await asyncio.sleep(60)

# --- Отправка уведомлений ---
async def send_notification(text):
    global CHAT_ID
    if CHAT_ID is None:
        logging.warning("CHAT_ID не установлен")
        return
    try:
        app = Application.builder().token(TOKEN).build()
        await app.bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        logging.error(f"Ошибка отправки: {e}")

# --- Запуск бота (исправленный) ---
def main():
    logging.info("🚀 Бот запущен! Ожидание команд...")
    
    # Создаём приложение
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Запускаем фоновую задачу
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(analysis_loop())
    
    # Запускаем бота в том же цикле
    try:
        app.run_polling()
    finally:
        loop.close()

if __name__ == "__main__":
    main()
