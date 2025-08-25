import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from utils.bots import monitor_bot

import core.db as db
from core.logger_config import logger
from services.monitor_channels import monitor_channels
from handlers.base_handler import base_router
from handlers.channel_handler import channel_router
from handlers.settings_handler import settings_router
from services.periodic_collector import start_for_all_users
from utils.clean_old_logs import regular_cleaning

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")


async def main():
    logger.info("Запуск Telegram бота")
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
    asyncio.create_task(regular_cleaning())
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
