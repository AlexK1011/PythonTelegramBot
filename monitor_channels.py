import asyncio
from pyrogram.errors import FloodWait

import db
from bots import monitor_bot
from post_processor import PostProcessor

delay_for_channel = 3


async def monitor_channels():
    while True:
        try:
            unique_channels = db.get_unique_channels()
            print(f"📡 Проверяем {len(unique_channels)} каналов...")

            for channel_id, title, username in unique_channels:
                await asyncio.sleep(delay_for_channel)
                try:
                    last_id = db.get_last_post_id(channel_id)
                    print(f"🔍 Канал {title} ({username}), последний ID = {last_id}")

                    if last_id is None:
                        async for msg in monitor_bot.get_chat_history(
                                chat_id=username,
                                limit=1
                            ):
                            db.set_last_post_id(channel_id, msg.id)
                            print(f"⏳ Инициализировали last_id = {msg.id} для канала {title}")
                        continue

                    all_msgs = [msg async for msg in monitor_bot.get_chat_history(
                        chat_id=username,
                        limit=5
                    )]
                    new_msgs = [m for m in all_msgs if m.id > last_id]
                    if not new_msgs:
                        continue

                    for msg in reversed(new_msgs):
                        post_info = {
                            "channel_id": channel_id,
                            "post_id": msg.id,
                            "user_ids": db.get_users_for_channel(channel_id),
                            "message_text": msg.text or msg.caption or "Медиа-сообщение"
                        }
                        processor = PostProcessor(post_info)
                        await processor.distribute_post()
                        print(f"✅ Новый пост {msg.id} в {title}")
                        db.set_last_post_id(channel_id, msg.id)

                except FloodWait as e:
                    print(f"FloodWait: жду {e.value} секунд")
                    await asyncio.sleep(e.value)
                except Exception as e:
                    print(f"❌ Ошибка мониторинга канала {username}: {e}")
                    continue

        except Exception as e:
            print(f"❌ Общая ошибка мониторинга: {e}")

        await asyncio.sleep(60)


