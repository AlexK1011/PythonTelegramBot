import os

from aiogram import Bot
from pyrogram import Client
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

bot = Bot(token=BOT_TOKEN)

monitor_bot = Client(
    "monitor_userbot",
    api_id=API_ID,
    api_hash=API_HASH
)
