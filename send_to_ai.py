import os
import time
import random
import asyncio
import collections
import httpx
from dotenv import load_dotenv

from config import rate_limit, max_tokens, max_retries, base_delay, time_window

load_dotenv()

API_URL = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
API_KEY = os.getenv("OPENROUTER_API_KEY")


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


async def send_to_deepseek(text, system_prompt) -> str:
    """Отправляет запрос к DeepSeek‑R1‑0528 с бэкоффом, honoring Retry-After, и локальным rate limit."""
    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY не задан")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    payload = {
        "model": "deepseek/deepseek-r1-0528:free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": str(text)},
        ],
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=None)) as client:
        last_resp = None
        for attempt in range(max_retries):
            await _rate_limit()
            try:
                resp = await client.post(API_URL, headers=headers, json=payload)
                last_resp = resp

                rl_rem = resp.headers.get("X-RateLimit-Remaining")
                rl_min_rem = resp.headers.get("X-RateLimit-Remaining-Minute")
                if rl_rem or rl_min_rem:
                    print(f"RateLimit remaining: total={rl_rem}, per_min={rl_min_rem}")

                if resp.status_code == 200:
                    data = resp.json()
                    msg = data["choices"][0]["message"]
                    reasoning = msg.get("reasoning_content")
                    answer = msg.get("content", "")

                    if reasoning:
                        print("=== Рассуждения модели: ===")
                        print(reasoning)
                        print("============================")

                    return answer

                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        await asyncio.sleep(int(retry_after))
                    else:
                        await asyncio.sleep(base_delay * (2 ** attempt) + random.uniform(0, 0.5))
                    continue

                if 500 <= resp.status_code < 600:
                    await asyncio.sleep(base_delay * (2 ** attempt) + random.uniform(0, 0.5))
                    continue

                resp.raise_for_status()

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(base_delay * (2 ** attempt) + random.uniform(0, 0.5))

        if last_resp is not None:
            last_resp.raise_for_status()
        raise RuntimeError("Не удалось получить ответ от OpenRouter после ретраев.")


async def get_openrouter_key_info():
    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY не задан")
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get("https://openrouter.ai/api/v1/auth/key", headers={"Authorization": f"Bearer {API_KEY}"})
        r.raise_for_status()
        return r.json()

