import time
import requests
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# ===== НАСТРОЙКИ =====
TOKEN = "8831841766:AAGrxasQomUdSAat5KIspw2FhEsvv98mMI4"  # Вставьте сюда токен от BotFather
# =====================

# Глобальная переменная для хранения ID чата
CHAT_ID = None

# --- Обработчик команды /start ---
async def start(update: Update, context):
    global CHAT_ID
    chat_id = update.effective_chat.id
    CHAT_ID = chat_id
    await update.message.reply_text(
        f"✅ Бот активирован! Ваш ID: `{chat_id}`\n"
        "Теперь я буду отправлять уведомления сюда."
    )

# --- Обработчик текстовых сообщений ---
async def echo(update: Update, context):
    await update.message.reply_text("Бот работает. Ожидайте уведомлений.")

# --- Основная функция ---
def main():
    print("🚀 Бот запущен! Ожидание команд...")
    
    # Создаём приложение
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Запускаем бота
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
