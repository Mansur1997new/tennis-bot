import logging
import asyncio
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== НАСТРОЙКИ =====
TOKEN = "8831841766:AAGrxasQomUdSAat5KIspw2FhEsvv98mMI4"  # Вставьте ваш реальный токен
BREAK_THRESHOLD = 4        # Количество брейков подряд для уведомления
# =====================

logging.basicConfig(level=logging.INFO)
CHAT_ID = None

# Хранилище для отслеживания матчей
# Структура: { match_id: {"breaks": 0, "notified": False} }
matches_tracking = {}

# --- Обработчик команды /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHAT_ID
    chat_id = update.effective_chat.id
    CHAT_ID = chat_id
    await update.message.reply_text(
        f"✅ Бот активирован! Ваш ID: `{chat_id}`\n"
        f"Буду уведомлять при {BREAK_THRESHOLD} брейках ПОДРЯД в матче."
    )

# --- Обработчик текстовых сообщений ---
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает. Ожидайте уведомлений.")

# --- Функция анализа матча ---
def analyze_match(match_data):
    """
    Анализирует матч на наличие 4 брейков подряд.
    match_data — словарь с данными матча (id, счёт, статистика).
    """
    match_id = match_data.get("id")
    if not match_id:
        return None

    # Инициализируем отслеживание для нового матча
    if match_id not in matches_tracking:
        matches_tracking[match_id] = {
            "breaks": 0,          # Текущая серия брейков подряд
            "notified": False
        }

    track = matches_tracking[match_id]

    # Если уже уведомили — больше не анализируем этот матч
    if track["notified"]:
        return None

    # ============================================
    # ЗДЕСЬ ДОЛЖЕН БЫТЬ РЕАЛЬНЫЙ ПАРСИНГ С SOFASCORE
    # Сейчас вместо этого — симуляция (случайный брейк)
    # ============================================
    # В реальном боте вы будете получать данные о геймах и определять,
    # был ли брейк в последнем гейме.
    is_break = random.choice([True, False, False, False])  # 25% шанс брейка
    # ============================================

    if is_break:
        # Если брейк случился — увеличиваем счётчик
        track["breaks"] += 1
        print(f"Матч {match_id}: брейк! Серия: {track['breaks']}")
    else:
        # Если брейка не было — сбрасываем серию
        track["breaks"] = 0

    # Проверяем: если серия достигла 4 — отправляем уведомление
    if track["breaks"] >= BREAK_THRESHOLD and not track["notified"]:
        track["notified"] = True
        return f"🎾 {BREAK_THRESHOLD} БРЕЙКА ПОДРЯД в матче {match_id}!"

    return None

# --- Функция отправки уведомлений ---
async def send_notification(text):
    global CHAT_ID
    if CHAT_ID is None:
        print("⚠️ CHAT_ID не установлен. Напишите /start")
        return
    try:
        app = Application.builder().token(TOKEN).build()
        await app.bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# --- Основной цикл анализа (запускается в фоне) ---
async def main_loop():
    print("🔄 Запущен цикл анализа матчей...")
    while True:
        try:
            # ВРЕМЕННО: тестовые матчи (замените на реальный список с Sofascore)
            test_matches = [{"id": 1}, {"id": 2}, {"id": 3}]

            for match in test_matches:
                result = analyze_match(match)
                if result:
                    await send_notification(result)

            await asyncio.sleep(25)  # Пауза 25 секунд

        except Exception as e:
            print(f"Ошибка в цикле: {e}")
            await asyncio.sleep(60)

# --- Запуск бота и фонового цикла ---
def main():
    print("🚀 Бот запущен! Ожидание команд...")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Запускаем фоновый цикл анализа
    loop = asyncio.get_event_loop()
    loop.create_task(main_loop())

    # Запускаем обработку команд
    app.run_polling()

if __name__ == "__main__":
    main()
