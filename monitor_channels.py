import asyncio
import json
import os

from redis.asyncio import Redis
from pyrogram.errors import FloodWait

import db
from dotenv import load_dotenv
from pyrogram import Client
from bots import monitor_bot, bot


r = Redis(host='localhost', port=6379, db=0)



async def monitor_channels():
    """Мониторинг новых постов во всех уникальных каналах"""
    while True:
        try:
            unique_channels = db.get_unique_channels()
            print(f"📡 Проверяем {len(unique_channels)} каналов...")

            for channel_id, title in unique_channels:
                try:
                    last_id = db.get_last_post_id(channel_id)
                    print(f"🔍 Канал {title} (ID: {channel_id}), последний ID = {last_id}")

                    if last_id is None:
                        # Первый запуск – сохраняем самый последний пост и не шлем старые
                        async for msg in monitor_bot.get_chat_history(
                                chat_id=channel_id,
                                limit=1
                            ):
                            db.set_last_post_id(channel_id, msg.id)
                            print(f"⏳ Инициализировали last_id = {msg.id} для канала {title}")
                        continue

                    # 1) Берём N последних сообщений (по умолчанию: от новых → к старым)
                    all_msgs = [msg async for msg in monitor_bot.get_chat_history(
                        chat_id=channel_id,
                        limit=5
                    )]
                    # 2) Оставляем только те, что ещё не обрабатывали (ID > last_id)
                    new_msgs = [m for m in all_msgs if m.id > last_id]
                    if not new_msgs:
                        continue  # ничего нового

                    # 3) API вернул их от новых к старым, поэтому разворачиваем
                    for msg in reversed(new_msgs):
                        post_info = {
                            "channel_id": channel_id,
                            "post_id": msg.id,
                            "user_ids": db.get_users_for_channel(channel_id),
                            "message_text": msg.text or msg.caption or "Медиа-сообщение"
                        }
                        # Публикуем сообщение в канал 'new_posts'
                        await r.publish("new_posts", json.dumps(post_info))
                        print(f"✅ Новый пост {msg.id} из {title} опубликован в Redis.")
                        db.set_last_post_id(channel_id, msg.id)

                except FloodWait as e:
                    print(f"FloodWait: жду {e.value} секунд")
                    await asyncio.sleep(e.value)
                except Exception as e:
                    print(f"❌ Ошибка мониторинга канала {channel_id}: {e}")
                    continue

        except Exception as e:
            print(f"❌ Общая ошибка мониторинга: {e}")

        # Пауза между проверками
        await asyncio.sleep(15)



async def main():
    await monitor_bot.start()
    await monitor_channels()

if __name__ == "__main__":
    asyncio.run(main())