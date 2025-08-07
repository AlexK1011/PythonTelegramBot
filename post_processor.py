import asyncio

import db
from bots import monitor_bot, bot


class PostProcessor:
    def __init__(self, post_info):
        self.post_info = post_info

    async def distribute_post(self):
        for uid in self.post_info["user_ids"]:
            settings = db.get_settings(uid)
            delay = settings.get("delay", 3600)
            min_forward_rate = settings.get("min_forward_rate", 1)
            asyncio.create_task(self.monitor_post(delay, min_forward_rate, uid))

    async def monitor_post(self, delay, min_forward_rate, uid):
        print(f"⏳ Проверяем пост {self.post_info['post_id']} в канале {self.post_info['channel_id']}, спим {delay} секунд")
        await asyncio.sleep(delay)
        await self.default_processing(min_forward_rate, uid)

    async def need_to_send(self, min_forward_rate):
        post = await monitor_bot.get_messages(
            chat_id=self.post_info["channel_id"],
            message_ids=self.post_info["post_id"],
        )
        views = post.views
        forwards = post.forwards
        forward_rate = (forwards / views) * 100

        if forward_rate >= min_forward_rate:
            return True
        else:
            return False


    async def default_processing(self, min_forward_rate, uid):
        print("⏳ Проверяем пост")
        is_need_to_send = await self.need_to_send(min_forward_rate)
        print(f"отправим: {is_need_to_send}")
        if not is_need_to_send:
            return

        try:
            await bot.send_message(uid, self.post_info["message_text"][:4096])
        except Exception as e:
            print(f"Ошибка отправки сообщения пользователю {uid}: {e}")