import asyncio
import re
import html
import db
from UserSettings import UserSettings
from bots import monitor_bot, bot
from logger_config import logger
from send_to_ai import ask_local_model
from config import default_delay, system_prompt_for_russian_market, get_text_from, base_system_prompt


class PostProcessor:
    def __init__(self, post_info):
        self.post_info = post_info

    async def distribute_post(self):
        for uid in self.post_info["user_ids"]:
            settings = db.get_settings(uid)
            delay = settings.get("delay", default_delay)
            asyncio.create_task(self.monitor_post(delay, uid))

    async def monitor_post(self, delay, uid):
        logger.debug(f"⏳ Проверяем пост {self.post_info['post_id']} в канале {self.post_info['channel_username']}, для пользователя {uid}, спим {delay} секунд")
        await asyncio.sleep(delay)

        user_settings = UserSettings(uid)

        if user_settings.uid == 1278128637 or user_settings.uid == 252718031 or user_settings.uid == 283201225:
            await self.russian_market_processing(user_settings)
        else:
            await self.default_processing(user_settings)

    async def need_to_send(self, min_forward_rate):
        post = await monitor_bot.get_messages(
            chat_id=self.post_info["channel_username"],
            message_ids=self.post_info["post_id"],
        )
        views = post.views
        forwards = post.forwards
        forward_rate = (forwards / views) * 100

        if forward_rate >= min_forward_rate:
            return True, forward_rate, forwards
        else:
            return False, forward_rate, forwards

    async def default_processing(self, user_settings):
        is_need_to_send, forward_rate, forwards = await self.need_to_send(user_settings.min_forward_rate)
        logger.debug(f"отправим: {is_need_to_send}. пользователь {user_settings.uid}")
        if not is_need_to_send:
            return

        message_html = self.post_info["html"]
        answer = message_html
        system_prompt = base_system_prompt + user_settings.system_prompt
        if user_settings.ai_enabled:
            try:
                answer = await ask_local_model(message_html, system_prompt)
            except Exception as e:
                logger.error(f"Ошибка ИИ (default_processing): {e}")

        text_from = get_text_from(self.post_info["message_link"], self.post_info["channel_title"],
                                  forward_rate, forwards)

        mode = db.get_settings(user_settings.uid).get("mode", "delayed_check")
        if mode == "periodic_collection":
            return

        try:
            message = await bot.send_message(user_settings.uid, answer, parse_mode="HTML")
            await message.reply(text_from, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {user_settings.uid}: {e}")

    async def russian_market_processing(self, user_settings):
        post_text = ''
        text = self.post_info["message_text"]
        is_need_to_send, forward_rate, forwards = await self.need_to_send(user_settings.min_forward_rate)
        logger.debug(f"отправим: {is_need_to_send}. пользователь {user_settings.uid}")
        if not is_need_to_send:
            return
        tries = 0

        for i in range(3):
            try:
                answer = await ask_local_model(text, system_prompt_for_russian_market)
            except Exception as e:
                logger.error(f"Ошибка ИИ (russian_market_processing): {e}")
                answer = text
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

        text_from = get_text_from(self.post_info["message_link"], self.post_info["channel_title"],
                                  forward_rate, forwards)

        mode = db.get_settings(user_settings.uid).get("mode", "delayed_check")
        if mode == "periodic_collection":
            return

        try:
            message = await bot.send_message(user_settings.uid, post_text[:4096], parse_mode="HTML",
                                             disable_web_page_preview=True)
            await message.reply(text_from, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения пользователю {user_settings.uid}: {e}")
