import logging
import os
import yt_dlp
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes
)
from dotenv import load_dotenv
import re

# Загружаем переменные окружения
load_dotenv()

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Получаем токен бота из переменной окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    await update.message.reply_text(
        "Привет! Отправь мне ссылку на видео с YouTube, и я помогу тебе скачать его.\n"
        "Ты можешь получить видео или только аудио.\n"
        "Также можешь воспользоваться командой /search <запрос> для поиска видео на YouTube."
    )

async def search_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск видео на YouTube с помощью Public API"""
    if not context.args:
        await update.message.reply_text(
            "Пожалуйста, укажи поисковый запрос. Пример: /search funny cats"
        )
        return

    query = " ".join(context.args)
    
    # Используем YouTube Data API через Public APIs
    api_url = f"https://api.ytube.ml/search/videos?q={query}&limit=5"
    
    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            
            if 'videos' in data and len(data['videos']) > 0:
                message = f"Результаты поиска для '{query}':\n\n"
                
                for idx, video in enumerate(data['videos'][:5], 1):
                    title = video.get('title', 'Без названия')
                    video_id = video.get('id', '')
                    url = f"https://www.youtube.com/watch?v={video_id}"
                    
                    message += f"{idx}. <a href='{url}'>{title}</a>\n"
                
                await update.message.reply_text(message, parse_mode='HTML')
            else:
                await update.message.reply_text("Не удалось найти видео по вашему запросу.")
        else:
            # Если первый API не работает, пробуем альтернативный способ
            await alternative_search(update, query)
    except Exception as e:
        logger.error(f"Ошибка при поиске видео: {str(e)}")
        await alternative_search(update, query)

async def alternative_search(update: Update, query: str):
    """
    Альтернативный метод поиска видео (например, через другое API из репозитория)
    """
    # Попробуем использовать другой API из списка public-apis
    # Используем API от RapidAPI с YouTube API
    api_key = os.getenv('RAPIDAPI_KEY', '')  # Необязательно, если API не требует ключа
    
    headers = {}
    if api_key:
        headers = {'X-RapidAPI-Key': api_key, 'X-RapidAPI-Host': 'youtube-v31.p.rapidapi.com'}
    
    # URL поиска YouTube через RapidAPI
    url = f"https://youtube-v31.p.rapidapi.com/search"
    params = {
        'q': query,
        'part': 'snippet',
        'maxResults': '5'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            
            if 'items' in data and len(data['items']) > 0:
                message = f"Результаты поиска для '{query}':\n\n"
                
                for idx, item in enumerate(data['items'][:5], 1):
                    title = item['snippet']['title']
                    video_id = item['id'].get('videoId', '')
                    
                    if video_id:  # Проверяем, что это видео (а не канал или плейлист)
                        url = f"https://www.youtube.com/watch?v={video_id}"
                        message += f"{idx}. <a href='{url}'>{title}</a>\n"
                
                await update.message.reply_text(message, parse_mode='HTML')
            else:
                await update.message.reply_text("Не удалось найти видео по вашему запросу.")
        else:
            await update.message.reply_text("Ошибка при поиске видео. Попробуйте другой запрос.")
    except Exception as e:
        logger.error(f"Ошибка при альтернативном поиске видео: {str(e)}")
        await update.message.reply_text("Произошла ошибка при поиске видео. Попробуйте позже.")

async def download_youtube_content(url: str, format_type: str):
    """
    Скачивает видео или аудио с YouTube

    :param url: Ссылка на YouTube видео
    :param format_type: 'video' для видео или 'audio' для аудио
    :return: Путь к скаченному файлу
    """
    ydl_opts = {}

    if format_type == "audio":
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'postprocessor_args': [
                '-ar', '16000'
            ],
            'prefer_ffmpeg': True,
            'audioquality': '0',
            'extractaudio': True,
            'keepvideo': False
        }
    elif format_type == "video":
        ydl_opts = {
            'format': 'best[height<=720]',  # Ограничение на 720p для экономии места
            'outtmpl': '%(title)s.%(ext)s',  # Имя файла будет соответствовать названию видео
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            # Если это аудио, yt-dlp меняет расширение на .mp3
            if format_type == "audio":
                filename = filename.replace('.webm', '.mp3').replace('.m4a', '.mp3').replace('.mp4', '.mp3')

            return filename
    except yt_dlp.DownloadError as e:
        logger.error(f"Ошибка при скачивании YouTube контента: {str(e)}")
        raise Exception(f"Не удалось скачать видео: {str(e)}")
    except Exception as e:
        logger.error(f"Неизвестная ошибка при скачивании: {str(e)}")
        raise Exception(f"Произошла ошибка при скачивании: {str(e)}")

async def send_content_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, format_type: str):
    """
    Скачивает и отправляет контент пользователю
    """
    processing_msg = None
    try:
        # Отправляем сообщение о начале загрузки
        processing_msg = await update.message.reply_text("Начинаю загрузку, подожди немного...")

        # Скачиваем контент
        filepath = await download_youtube_content(url, format_type)

        # Отправляем файл пользователю
        if format_type == "video":
            with open(filepath, 'rb') as video_file:
                await update.message.reply_video(video=video_file)
        else:  # audio
            with open(filepath, 'rb') as audio_file:
                await update.message.reply_audio(audio=audio_file)

        # Удаляем временный файл после отправки
        if os.path.exists(filepath):
            os.remove(filepath)

        # Редактируем сообщение об обработке
        if processing_msg:
            await processing_msg.edit_text("Загрузка завершена!")

    except Exception as e:
        if processing_msg:
            await processing_msg.edit_text(f"Произошла ошибка при загрузке: {str(e)}")
        else:
            await update.message.reply_text(f"Произошла ошибка при загрузке: {str(e)}")

def is_valid_youtube_url(url: str) -> bool:
    """
    Проверяет, является ли строка действительной ссылкой на YouTube
    """
    youtube_regex = re.compile(
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    return youtube_regex.match(url) is not None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает текстовые сообщения от пользователя
    """
    text = update.message.text.strip()

    # Проверяем, является ли сообщение ссылкой на YouTube
    if is_valid_youtube_url(text):
        # Предлагаем пользователю выбрать формат
        keyboard = [
            [
                InlineKeyboardButton("Видео 📹", callback_data=f"format_video_{text}"),
                InlineKeyboardButton("Аудио 🔊", callback_data=f"format_audio_{text}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("Выбери, что хочешь скачать:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Пожалуйста, отправь корректную ссылку на YouTube.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатие кнопок"""
    query = update.callback_query

    # Отвечаем на callback, чтобы убрать "часики" в интерфейсе
    await query.answer()

    # Разбираем данные из callback
    data_parts = query.data.split('_')
    format_type = data_parts[1]  # 'video' или 'audio'
    url = '_'.join(data_parts[2:])  # Восстанавливаем оригинальный URL

    # Отправляем сообщение о начале загрузки
    await send_content_to_user(update, context, url, format_type)

def main():
    """Запуск бота"""
    # Создаем приложение с использованием ApplicationBuilder
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search_youtube))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()