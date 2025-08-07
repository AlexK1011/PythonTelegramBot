import os

from aiogram import Bot
from pyrogram import Client
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# Основной бот для взаимодействия с пользователями
bot = Bot(token=BOT_TOKEN)

# Userbot для мониторинга каналов
monitor_bot = Client(
    "monitor_userbot",
    api_id=API_ID,
    api_hash=API_HASH
)