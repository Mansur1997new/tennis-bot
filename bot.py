import time
import requests
from telegram import Bot, Update
from telegram.ext import CommandHandler, MessageHandler, filters, Application

# ===== НАСТРОЙКИ =====
TOKEN = "8831841766:AAGrxasQomUdSAat5KIspw2FhEsvv98mMI4"  # Вставьте сюда токен от BotFather
# =====================

# Глобальная переменная для хранения ID чата
CHAT_ID = None

# --- Обработчик команды /start ---
async def start(update: Update, context):
    global CHAT_ID
    chat_id = update.effective_chat.id
    CHAT_ID = chat_id  # Сохраняем ID
    await update.message.reply_text(
        f"✅ Бот активирован! Ваш ID: `{chat_id}`\n"
        "Теперь я буду отправлять уведомления сюда."
    )

# --- Обработчик текстовых сообщений ---
async def echo(update: Update, context):
    await update.message.reply_text("Бот работает. Ожидайте уведомлений.")

# --- Функция отправки уведомлений ---
def send_message(text):
    global CHAT_ID
    if CHAT_ID is None:
        print("⚠️ CHAT_ID ещё не установлен. Напишите боту /start")
        return
    try:
        bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# --- Тестовые функции для анализа (пока заглушки) ---
def get_live_matches():
    """Замените на реальный парсинг Sofascore"""
    return [{"id": 1, "player1": "Игрок А", "player2": "Игрок Б"}]

def check_breaks(match):
    """Позже добавим логику брейков"""
    return False, ""

# --- Основной цикл ---
def main():
    print("🚀 Бот запущен! Ожидание команд...")

    # Создаём приложение для обработки команд
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Запускаем обработку команд (в фоновом режиме)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

# --- Если вы хотите использовать цикл с опросом, раскомментируйте этот блок ---
# def main_loop():
#     print("🔄 Запуск цикла анализа матчей...")
#     while True:
#         try:
#             matches = get_live_matches()
#             for match in matches:
#                 triggered, msg = check_breaks(match)
#                 if triggered:
#                     send_message(msg)
#             time.sleep(25)
#         except Exception as e:
#             print(f"Ошибка в цикле: {e}")
#             time.sleep(60)

if __name__ == "__main__":
    main()
