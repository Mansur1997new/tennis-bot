import logging
import asyncio
import threading
import aiohttp
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== НАСТРОЙКИ =====
TOKEN = "8831841766:AAGrxasQomUdSAat5KIspw2FhEsvv98mMI4"  # Вставьте ваш Telegram токен
BREAK_THRESHOLD = 4
CHECK_INTERVAL = 30
# =====================

logging.basicConfig(level=logging.INFO)
CHAT_ID = None
matches_tracking = {}

# --- HTTP-сервер для Render ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_http_server():
    server = HTTPServer(('0.0.0.0', 10000), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()

# --- Обработчики команд ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    chat_id = update.effective_chat.id
    CHAT_ID = chat_id
    await update.message.reply_text(
        f"✅ Бот активирован! Ваш ID: `{chat_id}`\n"
        f"Отслеживаю теннисные матчи (TheSportsDB).\n"
        f"Уведомлю при {BREAK_THRESHOLD} брейках подряд!"
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает. Ожидайте уведомлений.")

# --- Функции для работы с TheSportsDB API ---
async def get_live_tennis_matches():
    """Получает список живых теннисных матчей через TheSportsDB"""
    # TheSportsDB не имеет прямого эндпоинта для live-матчей,
    # поэтому получаем расписание на сегодня
    url = "https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d=2026-07-19&s=Tennis"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    events = data.get('events', [])
                    logging.info(f"Найдено теннисных матчей на сегодня: {len(events)}")
                    return events
                else:
                    logging.warning(f"API вернул статус: {response.status}")
                    return []
    except Exception as e:
        logging.error(f"Ошибка получения матчей: {e}")
        return []

async def get_match_details(match_id):
    """Получает детали матча по ID"""
    url = f"https://www.thesportsdb.com/api/v1/json/3/lookuptable.php?e={match_id}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('table', [])
                else:
                    return []
    except Exception as e:
        logging.error(f"Ошибка получения деталей матча: {e}")
        return []

# --- Логика анализа (упрощённая для TheSportsDB) ---
def analyze_match(match):
    """
    Анализирует матч на наличие брейков.
    TheSportsDB не даёт детальной статистики, поэтому используем счёт.
    """
    match_id = match.get('idEvent')
    if not match_id:
        return False, None
    
    if match_id not in matches_tracking:
        matches_tracking[match_id] = {"breaks": 0, "notified": False}
    
    track = matches_tracking[match_id]
    if track["notified"]:
        return False, None
    
    # Получаем счёт по сетам
    home_score = match.get('intHomeScore', 0)
    away_score = match.get('intAwayScore', 0)
    
    # Если разница в счёте больше 1 — возможно, был брейк
    # Это упрощённая логика для демонстрации
    if abs(home_score - away_score) > 1:
        track["breaks"] += 1
        logging.info(f"Матч {match_id}: возможный брейк! Серия: {track['breaks']}")
    else:
        track["breaks"] = 0
    
    if track["breaks"] >= BREAK_THRESHOLD:
        track["notified"] = True
        home = match.get('strHomeTeam', 'Игрок 1')
        away = match.get('strAwayTeam', 'Игрок 2')
        return True, f"🎾 {BREAK_THRESHOLD} БРЕЙКА ПОДРЯД!\nМатч: {home} - {away}"
    
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
                logging.info("Нет теннисных матчей на сегодня")
            else:
                for match in matches:
                    triggered, message = analyze_match(match)
                    if triggered and message:
                        await send_notification(message)
            await asyncio.sleep(CHECK_INTERVAL)
        except Exception as e:
            logging.error(f"Ошибка в цикле: {e}")
            await asyncio.sleep(60)

# --- Запуск бота ---
def main():
    logging.info("🚀 Бот запущен! Ожидание команд...")
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(analysis_loop())
    
    try:
        loop.run_until_complete(app.run_polling())
    except KeyboardInterrupt:
        logging.info("Бот остановлен")
    finally:
        loop.close()

if __name__ == "__main__":
    main()
