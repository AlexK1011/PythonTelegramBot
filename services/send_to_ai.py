import collections
import random
import time
import os
import asyncio
import httpx
from dotenv import load_dotenv
import json

from core.config import rate_limit, time_window, base_delay
from core.logger_config import logger

load_dotenv()

MODEL_NAME = os.getenv("GEN_MODEL", "deepseek-v3")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", -1))
API_URL = os.getenv("GEN_API_URL", "https://api.gen-api.ru/api/v1/networks/deepseek-v3")
API_KEY = os.getenv("GEN_API_KEY")
MAX_RETRIES = 3
BASE_DELAY = 1.0

_call_times = collections.deque()
_rate_lock = asyncio.Lock()

async def _rate_limit():
    async with _rate_lock:
        now = time.monotonic()
        while _call_times and now - _call_times[0] > time_window:
            _call_times.popleft()

        if len(_call_times) >= rate_limit:
            sleep_for = time_window - (now - _call_times[0]) + 0.01
            await asyncio.sleep(max(sleep_for, 0))

        _call_times.append(time.monotonic())


async def ask_gen_api(text, system_prompt) -> str:
    """Отправляет запрос к локальной модели Ollama"""
    if not API_KEY:
        raise RuntimeError("GEN_API_KEY не задан")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": str(text)},
        ],
        "max_tokens": MAX_TOKENS if MAX_TOKENS > 0 else None,
        "stream": False,
        "is_sync": True,
    }

    # Убираем None значения из payload
    payload = {k: v for k, v in payload.items() if v is not None}

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=None)) as client:
        last_resp = None
        for attempt in range(MAX_RETRIES):
            await _rate_limit()
            try:
                logger.debug(f"Отправляем запрос к {API_URL} (попытка {attempt + 1})")
                resp = await client.post(API_URL, headers=headers, json=payload)
                last_resp = resp

                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        # logger.debug(f"Ответ успешно получен: {data}")
                    except json.JSONDecodeError:
                        logger.error(f"Невалидный JSON ответ: {resp.text}")
                        raise

                    answer = data["response"][0]["choices"][0]["message"]["content"]

                    logger.debug("Ответ успешно получен")
                    return answer

                # Обработка ошибок
                logger.warning(f"Статус код {resp.status_code}: {resp.text}")

                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        delay = int(retry_after)
                    else:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                    await asyncio.sleep(delay)
                    continue

                if 500 <= resp.status_code < 600:
                    await asyncio.sleep(base_delay * (2 ** attempt) + random.uniform(0, 0.5))
                    continue

                resp.raise_for_status()

            except (httpx.TimeoutException, httpx.NetworkError, json.JSONDecodeError, ValueError) as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(base_delay * (2 ** attempt) + random.uniform(0, 0.5))

        if last_resp is not None:
            last_resp.raise_for_status()
        raise RuntimeError("Не удалось получить ответ от gen-api.ru после ретраев.")


async def test_gen_api():
    """Тестовая функция для проверки работы с локальной моделью"""
    prompt = "Привет! Как тебя зовут и что ты умеешь?"
    system_prompt = "Ты полезный AI-ассистент. Отвечай на русском языке."

    try:
        response = await ask_gen_api(prompt, system_prompt)

        return response

    except Exception as e:
        logger.exception("Ошибка при тестировании модели")
        return f"Ошибка: {str(e)}"



async def test_parallel_requests():
    prompt = "привет, как у тебя дела?"
    system_prompt = "Ты полезный AI-ассистент. Отвечай на русском языке."
    tasks = []
    for i in range(5):
        task = asyncio.create_task(ask_gen_api(prompt, system_prompt))
        tasks.append(task)

    # Ждем завершения всех задач
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        print(result)
        print("=" * 40)



if __name__ == "__main__":
    response = asyncio.run(test_gen_api())
    print(response)