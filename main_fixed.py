import os
import asyncio
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
import sqlite3
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import F
import random

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Создание бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Тут должны быть все ваши функции обработчики, которые были в оригинальном файле

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())