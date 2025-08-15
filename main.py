import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from bots import monitor_bot

import db
from monitor_channels import monitor_channels
from handlers.base_handler import base_router
from handlers.channel_handler import channel_router
from handlers.settings_handler import settings_router
from periodic_collector import start_for_all_users

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")


async def main():
    db.init_db()

    bot = Bot(token=API_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(base_router)
    dp.include_router(channel_router)
    dp.include_router(settings_router)

    await monitor_bot.start()
    start_for_all_users()
    asyncio.create_task(monitor_channels())

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
