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

# Хранилище для отслеживания матчей
# { match_id: {"breaks": 0, "notified": False, "last_game_index": 0, "server_id": None} }
matches_tracking = {}

# --- Обработчик команды /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    chat_id = update.effective_chat.id
    CHAT_ID = chat_id
    await update.message.reply_text(
        f"✅ Бот активирован! Ваш ID: `{chat_id}`\n"
        f"Отслеживаю теннисные матчи в реальном времени.\n"
        f"Уведомлю при {BREAK_THRESHOLD} брейках подряд (суммарно, любым игроком)!"
    )

# --- Обработчик текстовых сообщений ---
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает. Ожидайте уведомлений.")

# --- Функция получения живых теннисных матчей ---
async def get_live_tennis_matches():
    """Получает список живых теннисных матчей через Sofascore API"""
    url = "https://api.sofascore.com/api/v1/sport/tennis/events/live"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    events = data.get('events', [])
                    logging.info(f"Найдено живых теннисных матчей: {len(events)}")
                    return events
                else:
                    logging.error(f"Ошибка API: {response.status}")
                    return []
    except Exception as e:
        logging.error(f"Ошибка получения матчей: {e}")
        return []

# --- Функция получения детальной информации о матче (инциденты) ---
async def get_match_incidents(match_id):
    """Получает список инцидентов (геймов) матча для анализа брейков"""
    url = f"https://api.sofascore.com/api/v1/event/{match_id}/incidents"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('incidents', [])
                else:
                    return []
    except Exception as e:
        logging.error(f"Ошибка получения инцидентов матча {match_id}: {e}")
        return []

# --- Функция определения брейка по инцидентам (ОБНОВЛЕННАЯ ЛОГИКА) ---
def detect_break(incidents, match_id):
    """
    Анализирует инциденты матча и определяет, был ли брейк.
    Считает общую серию брейков подряд (любым игроком).
    Возвращает (is_break, server_id, game_index)
    """
    if not incidents:
        return False, None, 0
    
    # Сортируем инциденты по времени
    sorted_incidents = sorted(incidents, key=lambda x: x.get('time', 0))
    
    # Инициализируем отслеживание для матча
    if match_id not in matches_tracking:
        matches_tracking[match_id] = {
            "breaks": 0,
            "notified": False,
            "last_game_index": 0,
            "server_id": None
        }
    
    track = matches_tracking[match_id]
    
    # Если уже уведомили — пропускаем
    if track["notified"]:
        return False, None, 0
    
    # Ищем новые геймы
    new_breaks = 0
    latest_game_index = track["last_game_index"]
    server_id = track["server_id"]
    
    for incident in sorted_incidents:
        if incident.get('type') == 'game':
            game_index = incident.get('game', {}).get('number', 0)
            if game_index <= latest_game_index:
                continue
            
            # Определяем подающего в этом гейме
            new_server = incident.get('server', {}).get('id')
            if not new_server:
                # Если поле server отсутствует, пытаемся определить по winner/loser
                winner = incident.get('winner', {}).get('id')
                loser = incident.get('loser', {}).get('id')
                # Если победитель гейма — тот же, кто выиграл предыдущий гейм, то это брейк
                # В реальности лучше использовать явное поле server
                continue
            
            # Если подающий сменился, значит предыдущий гейм выиграл принимающий -> ЭТО БРЕЙК
            if server_id and server_id != new_server:
                new_breaks += 1
                logging.info(f"Матч {match_id}: брейк! Общая серия: {track['breaks'] + new_breaks}")
            else:
                # Если брейка не было, СБРАСЫВАЕМ серию (прерывание подряд идущих брейков)
                # Важно: мы сбрасываем только если был гейм без брейка
                # Но нам нужно сбросить всю серию, так как брейки перестали идти подряд
                track["breaks"] = 0
                logging.info(f"Матч {match_id}: серия брейков сброшена (не было брейка)")
            
            # Обновляем данные
            latest_game_index = game_index
            server_id = new_server
    
    # Обновляем состояние, если были новые брейки
    if new_breaks > 0:
        track["breaks"] += new_breaks
    # Если новых брейков не было, серия уже сброшена внутри цикла
    
    track["last_game_index"] = latest_game_index
    track["server_id"] = server_id
    
    # Проверяем условие: достигли ли 4 брейков подряд
    if track["breaks"] >= BREAK_THRESHOLD:
        track["notified"] = True
        return True, server_id, latest_game_index
    
    return False, server_id, latest_game_index

# --- Функция анализа матча ---
async def analyze_match(match_data):
    match_id = match_data.get('id')
    if not match_id:
        return False, None
    
    # Получаем инциденты матча
    incidents = await get_match_incidents(match_id)
    if not incidents:
        return False, None
    
    # Определяем брейк
    is_break, server_id, game_index = detect_break(incidents, match_id)
    
    if is_break:
        home_team = match_data.get('homeTeam', {}).get('name', 'Игрок 1')
        away_team = match_data.get('awayTeam', {}).get('name', 'Игрок 2')
        score = match_data.get('score', {})
        current_score = f"{score.get('home', '')}:{score.get('away', '')}"
        track = matches_tracking[match_id]
        message = (
            f"🎾 {BREAK_THRESHOLD} БРЕЙКА ПОДРЯД!\n"
            f"Матч: {home_team} vs {away_team}\n"
            f"Счёт: {current_score}\n"
            f"Общая серия брейков: {track['breaks']}"
        )
        return True, message
    
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

# --- Основной цикл анализа ---
async def main_loop():
    logging.info("🔄 Запущен цикл анализа матчей...")
    while True:
        try:
            live_matches = await get_live_tennis_matches()
            if not live_matches:
                logging.info("Нет живых теннисных матчей")
            else:
                for match in live_matches:
                    match_id = match.get('id')
                    if not match_id:
                        continue
                    
                    triggered, message = await analyze_match(match)
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
