import asyncio
import collections
import os
import time

from aiogram import Bot
from pyrogram import Client
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

bot = Bot(token=BOT_TOKEN)
_monitor_call_times = collections.deque()
_monitor_rate_lock = asyncio.Lock()
_monitor_rate_limit = 1
_monitor_time_window = 1


async def monitor_rate_limit():
    """Ограничивает частоту запросов к monitor_bot"""
    async with _monitor_rate_lock:
        now = time.monotonic()
        while _monitor_call_times and now - _monitor_call_times[0] > _monitor_time_window:
            _monitor_call_times.popleft()

        if len(_monitor_call_times) >= _monitor_rate_limit:
            sleep_for = _monitor_time_window - (now - _monitor_call_times[0]) + 0.01
            await asyncio.sleep(max(sleep_for, 0))

        _monitor_call_times.append(now)


class RateLimitedMonitorBot:
    """Обертка для monitor_bot с автоматическим ограничением частоты запросов"""

    def __init__(self, client):
        self._client = client

    async def get_chat_history(self, *args, **kwargs):
        """Получение истории чата с автоматическим лимитом"""
        await monitor_rate_limit()
        messages = []
        async for message in self._client.get_chat_history(*args, **kwargs):
            messages.append(message)
        return messages

    async def get_messages(self, *args, **kwargs):
        """Получение сообщений с автоматическим лимитом"""
        await monitor_rate_limit()
        return await self._client.get_messages(*args, **kwargs)

    async def start(self):
        """Запуск клиента"""
        return await self._client.start()


monitor_client = Client(
    "monitor_userbot",
    api_id=API_ID,
    api_hash=API_HASH
)

monitor_bot = RateLimitedMonitorBot(monitor_client)
