import asyncio
from pyrogram.errors import FloodWait
from core.config import delay_for_channel, monitor_interval
import core.db as db
from utils.bots import monitor_bot
from core.logger_config import logger
from services.post_processor import PostProcessor


async def monitor_channels():
    while True:
        try:
            unique_channels = db.get_unique_channels()
            logger.info(f"Проверяем {len(unique_channels)} каналов...")

            for channel_id, title, username in unique_channels:
                await asyncio.sleep(delay_for_channel)
                try:
                    last_id = db.get_last_post_id(channel_id)
                    logger.debug(f"Канал {title} ({username}), последний ID = {last_id}")

                    if last_id is None:
                        msgs = await monitor_bot.get_chat_history(
                            chat_id=username,
                            limit=1
                        )
                        msg = msgs[0]
                        db.set_last_post_id(channel_id, msg.id)
                        logger.info(f"⏳ Инициализировали last_id = {msg.id} для канала {title}")
                        continue

                    all_msgs = await monitor_bot.get_chat_history(
                        chat_id=username,
                        limit=20
                    )
                    new_msgs = [m for m in all_msgs if m.id > last_id]
                    if not new_msgs:
                        continue

                    for msg in reversed(new_msgs):
                        text_html = msg.text.html if msg.text is not None else None
                        cap_html = msg.caption.html if msg.caption is not None else None
                        message_html = text_html or cap_html or "Медиа-сообщение"
                        post_info = {
                            "channel_id": channel_id,
                            "channel_username": username,
                            "post_id": msg.id,
                            "user_ids": db.get_users_for_channel(channel_id),
                            "html": message_html,
                            "message_text": msg.text or msg.caption or "Медиа-сообщение",
                            "message_link": f"https://t.me/{username}/{msg.id}",
                            "channel_title": title
                        }
                        db.set_post(channel_id, msg.id)
                        processor = PostProcessor(post_info)
                        await processor.distribute_post()
                        logger.info(f"✅ Новый пост {msg.id} в {title}")
                        db.set_last_post_id(channel_id, msg.id)

                except FloodWait as e:
                    logger.warning(f"FloodWait: жду {e.value} секунд")
                    await asyncio.sleep(e.value)
                except Exception as e:
                    logger.error(f"❌ Ошибка мониторинга канала {username}: {e}")
                    continue

        except Exception as e:
            logger.critical(f"❌ Общая ошибка мониторинга: {e}")

        await asyncio.sleep(monitor_interval)
