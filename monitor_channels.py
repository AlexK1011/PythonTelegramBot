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
delay_for_channel = 3


async def monitor_channels(monitor_bot):
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
                        await distribute_post(monitor_bot, post_info)
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


async def distribute_post(monitor_bot, post_info):
    for uid in post_info["user_ids"]:
        settings = db.get_settings(uid)
        delay = settings.get("delay", 3600)
        min_forward_rate = settings.get("min_forward_rate", 1)
        asyncio.create_task(monitor_post(monitor_bot, delay, min_forward_rate, post_info, uid))


async def monitor_post(monitor_bot, delay, min_forward_rate, post_info, uid):
    print(f"⏳ Проверяем пост {post_info['post_id']} в канале {post_info['channel_id']}, спим {delay} секунд")
    await asyncio.sleep(delay)
    print("⏳ Проверяем пост")
    is_need_to_send = await need_to_send(monitor_bot, post_info, min_forward_rate)
    print(f"отправим: {is_need_to_send}")
    if not is_need_to_send:
        return
    info = {
        "channel_id": post_info["channel_id"],
        "post_id": post_info["post_id"],
        "message_text": post_info["message_text"],
        "user_id": uid,
    }
    await r.publish("new_posts", json.dumps(info))


async def need_to_send(monitor_bot, post_info, min_forward_rate):
    post = await monitor_bot.get_messages(
        chat_id=post_info["channel_id"],
        message_ids=post_info["post_id"],
    )
    views = post.views
    forwards = post.forwards
    forward_rate = (forwards / views) * 100

    if forward_rate >= min_forward_rate:
        return True
    else:
        return False
