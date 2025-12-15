import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Получаем токен из переменной окружения
TOKEN = os.getenv('BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Привет! Отправь мне аудио или видео файл, и я сохраню его.')

async def download_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Получаем тип документа
    file_type = None
    file_extension = ""
    
    if update.message.document:
        doc = update.message.document
        file_id = doc.file_id
        file_name = doc.file_name or "downloaded_file"
        file_type = "document"
        
        # Определяем расширение файла
        if '.' in file_name:
            file_extension = file_name.split('.')[-1].lower()
    elif update.message.audio:
        audio = update.message.audio
        file_id = audio.file_id
        file_name = f"audio_{audio.file_unique_id}.mp3"
        file_type = "audio"
        file_extension = "mp3"
    elif update.message.video:
        video = update.message.video
        file_id = video.file_id
        file_name = f"video_{video.file_unique_id}.mp4"
        file_type = "video"
        file_extension = "mp4"
    else:
        await update.message.reply_text("Отправьте аудио или видео файл.")
        return

    # Проверяем, является ли файл аудио или видео
    audio_video_extensions = ['mp3', 'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv', 'm4a', 'wav', 'aac', 'ogg', 'webm']
    
    if file_extension in audio_video_extensions:
        # Получаем объект файла
        file = await context.bot.get_file(file_id)
        
        # Создаем папку downloads, если её нет
        download_dir = "downloads"
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            
        # Составляем путь для сохранения файла
        file_path = os.path.join(download_dir, file_name)
        
        # Скачиваем файл
        await file.download_to_drive(custom_path=file_path)
        
        await update.message.reply_text(f'Файл "{file_name}" успешно скачан и сохранён!')
        print(f'Файл "{file_name}" успешно скачан и сохранён в папку downloads.')
    else:
        await update.message.reply_text(f'Файл "{file_name}" не является аудио или видео файлом.')

def main():
    # Создаём приложение и отключаем JobQueue
    builder = ApplicationBuilder().token(TOKEN)
    builder.job_queue(None)  # Отключаем JobQueue
    application = builder.build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    # Просто обрабатываем все документы, аудио и видео, а проверку типа файла будем делать внутри функции
    application.add_handler(MessageHandler(filters.Document.ALL | filters.AUDIO | filters.VIDEO, download_file))

    # Запускаем бота
    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    application.run_polling()

if __name__ == '__main__':
    main()