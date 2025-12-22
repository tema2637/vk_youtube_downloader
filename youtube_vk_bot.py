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
        "Привет! Отправьте мне ссылку на видео с YouTube.\n\n"
        "Для получения аудио добавьте слово 'аудио' или 'audio' к ссылке.\n"
        "Для получения видео просто отправьте ссылку.\n\n"
        "Используйте команду /search для поиска видео по названию."
    )


from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# Определяем состояния для поиска
class SearchStates(StatesGroup):
    waiting_for_query = State()

# Обработчик команды /search
@dp.message(Command(commands=['search']))
async def search_command(message: Message, state: FSMContext):
    await state.set_state(SearchStates.waiting_for_query)
    await message.answer(
        "Введите название видео, которое вы хотите найти."
    )

# Обработчик ввода запроса для поиска
@dp.message(SearchStates.waiting_for_query)
async def process_search_query(message: Message, state: FSMContext):
    query = message.text.strip()
    print(f"DEBUG (Command Search): Received search query: '{query}' from user {message.from_user.id}")

    # Проверяем, не состоит ли сообщение только из пробельных символов
    if not query or query.isspace():
        await message.answer("Пожалуйста, введите корректный запрос для поиска.")
        await state.clear()
        return

    await state.clear()

    # Отправляем сообщение о поиске
    search_msg = await message.answer("Поиск видео, пожалуйста подождите...")

    try:
        # Используем yt-dlp для поиска видео
        search_query = f"ytsearch5:{query}"  # ищем 5 первых результатов
        print(f"DEBUG (Command Search): Searching with query: {search_query}")

        ydl_opts = {
            'quiet': True,
            'extract_flat': True,  # получаем только информацию без загрузки
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(search_query, download=False)

        print(f"DEBUG (Command Search): Search returned {len(result['entries']) if 'entries' in result else 0} results")

        if 'entries' in result and result['entries']:
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])

            for i, entry in enumerate(result['entries']):
                title = entry.get('title', 'Без названия')
                video_id = entry.get('id', '')
                url = f"https://www.youtube.com/watch?v={video_id}"

                print(f"DEBUG (Command Search): Found video {i+1}: {title[:50]}... (ID: {video_id})")

                # Ограничиваем длину названия для кнопки
                button_text = title[:50] + "..." if len(title) > 50 else title
                callback_data = f"search_video_{url}"

                # Добавляем кнопку в клавиатуру
                keyboard.inline_keyboard.append([
                    types.InlineKeyboardButton(
                        text=f"{i+1}. {button_text}",
                        callback_data=callback_data
                    )
                ])

            # Добавляем кнопку "Отмена"
            keyboard.inline_keyboard.append([
                types.InlineKeyboardButton(
                    text="Отмена",
                    callback_data="cancel_search"
                )
            ])

            await message.answer("Выберите видео для загрузки:", reply_markup=keyboard)
        else:
            print(f"DEBUG (Command Search): No results found for query: {query}")
            await message.answer("К сожалению, ничего не найдено по вашему запросу.")

    except yt_dlp.DownloadError as e:
        print(f"DEBUG (Command Search): yt-dlp download error: {str(e)}")
        await message.answer(f"Ошибка при поиске: {str(e)}")
    except Exception as e:
        print(f"DEBUG (Command Search): General error during search: {str(e)}")
        await message.answer(f"Произошла ошибка при поиске: {str(e)}")
    finally:
        await search_msg.delete()

# Обработчик текстовых сообщений для поиска по названию
@dp.message(F.text & ~F.text.startswith('/') & ~F.text.contains("youtube.com") & ~F.text.contains("youtu.be"))
async def search_by_text(message: Message, state: FSMContext):
    # Проверяем, не находится ли пользователь в состоянии ожидания ввода запроса для /search
    current_state = await state.get_state()
    if current_state is not None:
        # Если пользователь уже в каком-то состоянии, не продолжаем обработку
        print(f"DEBUG: User {message.from_user.id} is in state {current_state}, skipping search")
        return

    query = message.text.strip()
    print(f"DEBUG: Received search query: '{query}' from user {message.from_user.id}")

    # Проверяем, не состоит ли сообщение только из пробельных символов
    if not query or query.isspace():
        print(f"DEBUG: Query consists only of whitespace characters, skipping search")
        return

    # Отправляем сообщение о поиске
    search_msg = await message.answer("Поиск видео по названию, пожалуйста подождите...")

    try:
        # Используем yt-dlp для поиска видео
        search_query = f"ytsearch5:{query}"  # ищем 5 первых результатов
        print(f"DEBUG: Searching with query: {search_query}")

        ydl_opts = {
            'quiet': True,
            'extract_flat': True,  # получаем только информацию без загрузки
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(search_query, download=False)

        print(f"DEBUG: Search returned {len(result['entries']) if 'entries' in result else 0} results")

        if 'entries' in result and result['entries']:
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])

            for i, entry in enumerate(result['entries']):
                title = entry.get('title', 'Без названия')
                video_id = entry.get('id', '')
                url = f"https://www.youtube.com/watch?v={video_id}"

                print(f"DEBUG: Found video {i+1}: {title[:50]}... (ID: {video_id})")

                # Ограничиваем длину названия для кнопки
                button_text = title[:50] + "..." if len(title) > 50 else title
                callback_data = f"search_video_{url}"

                # Добавляем кнопку в клавиатуру
                keyboard.inline_keyboard.append([
                    types.InlineKeyboardButton(
                        text=f"{i+1}. {button_text}",
                        callback_data=callback_data
                    )
                ])

            # Добавляем кнопку "Отмена"
            keyboard.inline_keyboard.append([
                types.InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="cancel_search"
                )
            ])

            await message.answer("Выберите видео для загрузки:", reply_markup=keyboard)
        else:
            print(f"DEBUG: No results found for query: {query}")
            await message.answer("К сожалению, ничего не найдено по вашему запросу.")

    except yt_dlp.DownloadError as e:
        print(f"DEBUG: yt-dlp download error: {str(e)}")
        await message.answer(f"Ошибка при поиске: {str(e)}")
    except Exception as e:
        print(f"DEBUG: General error during search: {str(e)}")
        await message.answer(f"Произошла ошибка при поиске: {str(e)}")
    finally:
        await search_msg.delete()

# Обработчик ссылок
@dp.message(F.text.contains("youtube.com") | F.text.contains("youtu.be"))
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
@dp.callback_query(F.data.startswith('audio_') | F.data.startswith('video_') | F.data.startswith('search_video_') | F.data.startswith('cancel_search'))
async def download_media_callback(callback_query: CallbackQuery):
    # Проверяем, является ли callback от кнопки отмены
    if callback_query.data == 'cancel_search':
        await callback_query.answer("Поиск отменен.")
        await callback_query.message.edit_text("Поиск отменен.")
        return

    # Проверяем, является ли callback от кнопки результата поиска
    if callback_query.data.startswith('search_video_'):
        # Извлекаем URL из callback_data
        url = callback_query.data[13:]  # 'search_video_' составляет 13 символов
        # По умолчанию предлагаем как аудио, так и видео
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="🎵 Аудио", callback_data=f"audio_{url}"),
                types.InlineKeyboardButton(text="🎥 Видео", callback_data=f"video_{url}")
            ]
        ])

        await callback_query.message.edit_text("Что вы хотите скачать?", reply_markup=keyboard)
        await callback_query.answer()
        return

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