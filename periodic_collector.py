import asyncio
from format_time import format_time

import db
from bots import monitor_bot, bot
from config import get_text_from
from logger_config import logger
from send_to_ai import ask_local_model

# Хранилище фоновых задач по пользователям
_user_tasks = {}


def start_periodic_collection_for_user(user_id: int):
    logger.info(f"запускаем периодическую коллекцию для пользователя {user_id}")
    task = _user_tasks.get(user_id)
    if task and not task.done():
        return
    _user_tasks[user_id] = asyncio.create_task(_user_periodic_collector(user_id))


def stop_periodic_collection_for_user(user_id: int):
    logger.info(f"останавливаем периодическую коллекцию для пользователя {user_id}")
    task = _user_tasks.get(user_id)
    if task and not task.done():
        task.cancel()
    _user_tasks.pop(user_id, None)


def start_for_all_users():
    users = db.get_users_by_mode("periodic_collection")
    for uid in users:
        start_periodic_collection_for_user(uid)


async def _user_periodic_collector(user_id: int):
    try:
        while True:
            settings = db.get_settings(user_id)
            if settings.get("mode", "delayed_check") != "periodic_collection":
                break

            interval = int(settings.get("interval", 3600))
            formated_time = format_time(interval)
            number_of_posts = int(settings.get("number_of_posts", 5))
            logger.debug("засыпаем. пользователь %s", user_id)
            await asyncio.sleep(interval)
            logger.debug("проснулись. пользователь %s", user_id)
            new_posts = db.get_posts(user_id, interval)
            posts = []
            for post_id, username in new_posts:
                post = await monitor_bot.get_messages(
                    chat_id=username,
                    message_ids=post_id,
                )
                views = post.views
                forwards = post.forwards
                forward_rate = (forwards / views) * 100
                post_info = {
                    "channel_id": username,
                    "post_id": post_id,
                    "message_text": post.text or post.caption or "Медиа-сообщение",
                    "message_link": f"https://t.me/{username}/{post_id}",
                    "channel_title": post.chat.title,
                    "views": views,
                    "forwards": forwards,
                    "forward_rate": forward_rate,
                }
                posts.append(post_info)

            sorted_posts = sorted(posts, key=lambda x: x['forward_rate'], reverse=True)
            logger.debug("отправляем в ИИ...")
            replies = await process_posts_concurrently(settings, sorted_posts[:number_of_posts])
            logger.info("начинаем отправку %d постов пользователю %s", number_of_posts, user_id)
            if len(sorted_posts) < number_of_posts:
                await bot.send_message(user_id,
                                       f"за {formated_time} вышло менее {number_of_posts} постов. "
                                       f"всего было {len(sorted_posts)}")
                for reply in replies:
                    message = await bot.send_message(user_id, reply["answer"], disable_notification=True)
                    await message.reply(reply["text_from"], parse_mode="HTML", disable_web_page_preview=True,
                                        disable_notification=True)
            else:
                await bot.send_message(user_id,
                                       f"За {formated_time} всего было {len(sorted_posts)} постов. "
                                       f"Вот топ {number_of_posts} из них:")
                for reply in replies:
                    message = await bot.send_message(user_id, reply["answer"], disable_notification=True)
                    await message.reply(reply["text_from"], parse_mode="HTML", disable_web_page_preview=True,
                                        disable_notification=True)



    except asyncio.CancelledError:
        # корректное завершение по cancel()
        pass
        logger.debug("удаляем задачу")
    except Exception as e:
        logger.error(f"Periodic: критическая ошибка у пользователя {user_id}: {e}")


async def process_posts_concurrently(settings, posts):
    """
    Параллельно обрабатывает посты через ИИ
    """
    if not posts:
        return []

    # Создаем задачи для параллельной обработки
    tasks = []
    for post in posts:
        task = asyncio.create_task(process_single_post(settings, post))
        tasks.append(task)

    # Ждем завершения всех задач
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Фильтруем результаты, исключая исключения
    replies = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Ошибка при обработке поста {posts[i]['post_id']}: {result}")
            replies.append({
                "answer": posts[i]["message_text"],
                "text_from": get_text_from(posts[i]["message_link"], posts[i]["channel_title"],
                                           posts[i]["forward_rate"], posts[i]["forwards"])
            })
        else:
            replies.append(result)

    return replies


async def process_single_post(settings, post):
    """
    Обрабатывает один пост и возвращает готовый ответ
    """
    try:
        answer = await process_post(settings, post["message_text"])
        return {
            "answer": answer,
            "text_from": get_text_from(post["message_link"], post["channel_title"],
                                       post["forward_rate"], post["forwards"])
        }
    except Exception as e:
        logger.error(f"Ошибка при обработке поста {post['post_id']}: {e}")
        raise e


async def process_post(settings, text):
    system_prompt = settings.get("system_prompt", "")
    ai_enabled = int(settings.get("ai_enabled", False))
    answer = text
    if ai_enabled:
        try:
            answer = await ask_local_model(text, system_prompt)
        except Exception as e:
            logger.error(f"Ошибка ИИ: {e}")

    return answer
