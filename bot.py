import logging
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== НАСТРОЙКИ =====
TOKEN = "8831841766:AAGrxasQomUdSAat5KIspw2FhEsvv98mMI4"  # Вставьте ваш реальный токен
BREAK_THRESHOLD = 4
CHECK_INTERVAL = 25
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

# --- Функции для работы с Sofascore API (УЛУЧШЕННЫЕ) ---
async def get_live_tennis_matches():
    """Получает список живых теннисных матчей с полными заголовками"""
    url = "https://api.sofascore.com/api/v1/sport/tennis/events/live"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.sofascore.com/",
        "Origin": "https://www.sofascore.com",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Cache-Control": "no-cache"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    events = data.get('events', [])
                    logging.info(f"Найдено живых теннисных матчей: {len(events)}")
                    return events
                else:
                    logging.warning(f"API вернул статус: {response.status}")
                    # Попробуем прочитать тело ответа для диагностики
                    try:
                        text = await response.text()
                        logging.warning(f"Тело ответа: {text[:200]}")
                    except:
                        pass
                    return []
    except Exception as e:
        logging.error(f"Ошибка получения матчей: {e}")
        return []

async def get_match_incidents(match_id):
    """Получает инциденты матча с полными заголовками"""
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/incidents"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.sofascore.com/",
        "Origin": "https://www.sofascore.com"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('incidents', [])
                else:
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
    
    for incident in sorted_incidents:
        if incident.get('type') == 'game':
            game_num = incident.get('game', {}).get('number', 0)
            if game_num <= last_game:
                continue
            winner = incident.get('winner', {}).get('id')
            server = incident.get('server', {}).get('id')
            if server and winner and server != winner:
                new_breaks += 1
            else:
                track["breaks"] = 0
            last_game = game_num
    
    if new_breaks > 0:
        track["breaks"] += new_breaks
    track["last_game"] = last_game
    
    if track["breaks"] >= BREAK_THRESHOLD:
        track["notified"] = True
        return True, track["breaks"]
    
    return False, None

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
async def analysis_loop():
    logging.info("🔄 Запущен цикл анализа матчей...")
    while True:
        try:
            matches = await get_live_tennis_matches()
            if not matches:
                logging.info("Нет живых теннисных матчей")
            else:
                logging.info(f"Найдено живых теннисных матчей: {len(matches)}")
                for match in matches:
                    match_id = match.get('id')
                    if not match_id:
                        continue
                    incidents = await get_match_incidents(match_id)
                    if incidents:
                        triggered, count = analyze_breaks(match_id, incidents)
                        if triggered:
                            home = match.get('homeTeam', {}).get('name', 'Игрок 1')
                            away = match.get('awayTeam', {}).get('name', 'Игрок 2')
                            await send_notification(
                                f"🎾 {BREAK_THRESHOLD} БРЕЙКА ПОДРЯД!\n"
                                f"Матч: {home} - {away}\n"
                                f"Серия: {count}"
                            )
            await asyncio.sleep(CHECK_INTERVAL)
        except Exception as e:
            logging.error(f"Ошибка в цикле: {e}")
            await asyncio.sleep(60)

# --- Запуск бота ---
async def main():
    logging.info("🚀 Бот запущен! Ожидание команд...")
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Запускаем фоновую задачу
    asyncio.create_task(analysis_loop())
    
    # Запускаем поллинг
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
