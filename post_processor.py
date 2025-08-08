import asyncio
import re
import html
import db
from bots import monitor_bot, bot
from send_to_ai import send_to_deepseek
from config import default_delay, default_min_forward_rate


class PostProcessor:
    def __init__(self, post_info):
        self.post_info = post_info

    async def distribute_post(self):
        for uid in self.post_info["user_ids"]:
            settings = db.get_settings(uid)
            delay = settings.get("delay", default_delay)
            min_forward_rate = settings.get("min_forward_rate", default_min_forward_rate)
            asyncio.create_task(self.monitor_post(delay, min_forward_rate, uid))

    async def monitor_post(self, delay, min_forward_rate, uid):
        print(f"⏳ Проверяем пост {self.post_info['post_id']} в канале {self.post_info['channel_id']}, спим {delay} секунд")
        await asyncio.sleep(delay)

        if uid == 1278128637 or uid == 252718031 or uid == 283201225:
            await self.russian_market_processing(min_forward_rate, uid)
        else:
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
            return True, forward_rate, forwards
        else:
            return False, forward_rate, forwards


    async def default_processing(self, min_forward_rate, uid):
        print("⏳ Проверяем пост")
        is_need_to_send, forward_rate, forwards = await self.need_to_send(min_forward_rate)
        print(f"отправим: {is_need_to_send}")
        if not is_need_to_send:
            return

        text_from = f"<a href='{self.post_info['message_link']}'>исходный пост</a> в {self.post_info['channel_title']}\nПроцент репостов: <b>{round(forward_rate, 2)}%</b>\nВсего поделились: <b>{forwards} раз</b>"

        try:
            message = await bot.send_message(uid, self.post_info["message_text"][:4096])
            await message.reply(text_from, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            print(f"Ошибка отправки сообщения пользователю {uid}: {e}")


    async def russian_market_processing(self, min_forward_rate, uid):
        global post_text
        text = self.post_info["message_text"]
        print("⏳ Проверяем пост")
        is_need_to_send, forward_rate, forwards = await self.need_to_send(min_forward_rate)
        print(f"отправим: {is_need_to_send}")
        if not is_need_to_send:
            return
        tries = 0

        for i in range(3):
            print(f"Попытка {i}. Отправляем в DeepSeek")
            answer = send_to_deepseek(text)
            safe_response = html.escape(answer)

            match = re.search(r'\|\|%HEADER%\|\|(.+?)\|\|%HEADER%\|\|(.*)', safe_response, re.DOTALL)

            if match:
                header = match.group(1).strip()
                body = match.group(2).strip()
                post_text = f"<b>{header}</b>\n\n{body}"
                post_text += "\n\n<a href='https://t.me/russianmarkt'>Russian Market</a>"
                break
            else:
                tries += 1
                if tries == 3:
                    post_text = answer
                else:
                    continue

        text_from = f"<a href='{self.post_info['message_link']}'>исходный пост</a> в {self.post_info['channel_title']}\nПроцент репостов: <b>{round(forward_rate, 2)}%</b>\nВсего поделились: <b>{forwards} раз</b>"

        try:
            message = await bot.send_message(uid, post_text[:4096], parse_mode="HTML", disable_web_page_preview=True)
            await message.reply(text_from, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            print(f"Ошибка отправки сообщения пользователю {uid}: {e}")