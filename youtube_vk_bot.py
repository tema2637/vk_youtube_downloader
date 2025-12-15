import os
import tempfile
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram import F
import yt_dlp
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Создание бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Обработчик команды /start
@dp.message(Command(commands=['start']))
async def start_command(message: Message):
    await message.answer(
        "Привет! Отправьте мне ссылку на видео с YouTube или ВКонтакте.\n\n"
        "Для получения аудио добавьте слово 'аудио' или 'audio' к ссылке.\n"
        "Для получения видео просто отправьте ссылку."
    )

# Обработчик ссылок
@dp.message(F.text.contains("youtube.com") | F.text.contains("youtu.be") | F.text.contains("vk.com"))
async def ask_download_format(message: Message):
    url = message.text.strip()

    # Создаём инлайн-клавиатуру с вариантами
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="🎵 Аудио", callback_data=f"audio_{url}"),
            types.InlineKeyboardButton(text="🎥 Видео", callback_data=f"video_{url}")
        ]
    ])

    await message.answer("Что вы хотите скачать?", reply_markup=keyboard)


# Обработчик нажатий на инлайн-кнопки
@dp.callback_query(F.data.startswith('audio_') | F.data.startswith('video_'))
async def download_media_callback(callback_query: CallbackQuery):
    # Отвечаем на callback сразу, чтобы избежать таймаута
    await callback_query.answer()

    # Определяем тип и URL из callback_data
    if callback_query.data.startswith('audio_'):
        is_audio_only = True
        url = callback_query.data[6:]  # 'audio_' составляет 6 символов
    else:
        is_audio_only = False
        url = callback_query.data[6:]  # 'video_' также 6 символов

    # Отправляем сообщение пользователю о начале загрузки
    loading_msg = await callback_query.message.answer("Загружаем файл, пожалуйста подождите...")

    actual_filename = None  # Инициализируем переменную для пути к файлу

    try:
        # Используем yt-dlp для получения информации о видео без загрузки
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'unknown_title')
            # Очищаем название от недопустимых символов для имён файлов
            clean_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_', '.', '!'))

        # Создаём имя файла на основе названия видео
        download_dir = "downloads"
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

        # Создаём полный путь к файлу
        if is_audio_only:
            file_path = os.path.join(download_dir, clean_title + ".%(ext)s")
        else:
            file_path = os.path.join(download_dir, clean_title + ".%(ext)s")

        # Параметры yt-dlp
        if is_audio_only:
            # Проверяем наличие ffmpeg перед попыткой извлечения аудио
            ydl_opts = {
                'outtmpl': file_path,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'postprocessor_args': [
                    '-fflags', '+bitexact',
                    '-flags:v', '+bitexact',
                    '-flags:a', '+bitexact',
                ],
            }
            # Если установлен путь к ffmpeg, добавляем его
            ffmpeg_path = os.getenv('FFMPEG_PATH')
            if ffmpeg_path:
                ydl_opts['postprocessor_args'].extend(['-ffmpeg', ffmpeg_path])
        else:  # Для видео
            ydl_opts = {
                'outtmpl': file_path,
            }
            # Если установлен путь к ffmpeg, добавляем его
            ffmpeg_path = os.getenv('FFMPEG_PATH')
            if ffmpeg_path:
                ydl_opts['ffmpeg_location'] = ffmpeg_path

        # Загрузка медиа
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        # Определяем фактическое имя файла после загрузки
        if is_audio_only:
            # Если просили аудио, и не возникло ошибки при постобработке
            ext = 'mp3'  # при извлечении аудио всегда mp3
            actual_filename = os.path.join(download_dir, clean_title + ".mp3")
        else:
            ext = info.get('ext', 'mp4')
            actual_filename = os.path.join(download_dir, clean_title + "." + ext)

        # Проверяем, существует ли файл перед отправкой
        if os.path.exists(actual_filename):
            # Отправляем медиа пользователю
            if is_audio_only:
                await callback_query.message.answer_audio(audio=types.FSInputFile(actual_filename), caption="Ваше аудио")
            else:
                await callback_query.message.answer_video(video=types.FSInputFile(actual_filename), caption="Ваше видео")
        else:
            # Если файл аудио не был создан из-за отсутствия ffmpeg
            if is_audio_only:
                await callback_query.message.answer("Не удалось извлечь аудио. Установите FFmpeg для извлечения аудио или запросите видео-файл.")
                # Пытаемся отправить видео вместо аудио
                ext = info.get('ext', 'mp4')
                alt_filename = os.path.join(download_dir, clean_title + "." + ext)
                if os.path.exists(alt_filename):
                    await callback_query.message.answer_video(video=types.FSInputFile(alt_filename), caption="Видео-файл вместо аудио")
                    os.unlink(alt_filename)  # Удаляем альтернативный файл
            else:
                await callback_query.message.answer(f"Произошла ошибка при обработке: файл {actual_filename} не найден")

    except yt_dlp.DownloadError as e:
        if "ffprobe" in str(e) or "ffmpeg" in str(e):
            await callback_query.message.answer("Для извлечения аудио необходима установка FFmpeg. Установите FFmpeg в систему и попробуйте снова.")
        else:
            await callback_query.message.answer(f"Ошибка загрузки: {str(e)}")
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка при загрузке: {str(e)}")
    finally:
        # Удаляем файл после отправки (если он существует)
        if actual_filename and os.path.exists(actual_filename):
            os.unlink(actual_filename)

        # Удаляем сообщение о загрузке
        await loading_msg.delete()

if __name__ == '__main__':
    import asyncio

    async def main():
        await dp.start_polling(bot)

    asyncio.run(main())