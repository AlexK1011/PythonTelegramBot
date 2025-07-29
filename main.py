import asyncio
import json
import os
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.storage.memory import MemoryStorage
from redis.asyncio import Redis
from dotenv import load_dotenv

import db
from keyboards import Keyboard, add_or_not
from monitor_channels import monitor_channels
from handlers import router  # Импортируем router с хендлерами


# Загрузка переменных окружения
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

# Redis
r = Redis(host='localhost', port=6379, db=0)

db.init_db()

# Redis PubSub: рассылка сообщений пользователям
async def process_pubsub_messages(bot):
    pubsub = r.pubsub()
    await pubsub.subscribe("new_posts")
    while True:
        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if msg and msg["type"] == "message":
            data = json.loads(msg["data"])
            text = data["message_text"]
            for uid in data["user_ids"]:
                try:
                    await bot.send_message(uid, text[:4096])
                except Exception as e:
                    print(f"Ошибка отправки сообщения пользователю {uid}: {e}")
        await asyncio.sleep(0.1)

async def main():
    bot = Bot(token=API_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)

    # Запуск фоновой задачи
    asyncio.create_task(process_pubsub_messages(bot))

    # Запуск polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
