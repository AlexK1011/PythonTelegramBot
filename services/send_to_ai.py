import os
import asyncio
import httpx
from dotenv import load_dotenv
from core.logger_config import logger

load_dotenv()

# Настройки Ollama
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = os.getenv("OLLAMA_MODEL", "gemma3:4b")  # Измените на вашу модель
MAX_TOKENS = int(os.getenv("MAX_TOKENS", -1))  # Перенесено из config
MAX_RETRIES = 3
BASE_DELAY = 1.0


async def ask_local_model(text, system_prompt) -> str:
    """Отправляет запрос к локальной модели Ollama"""
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": str(text)},
        ],
        "options": {
            "num_predict": MAX_TOKENS
        },
        "stream": False
    }

    async with httpx.AsyncClient(timeout=None) as client:
        for attempt in range(MAX_RETRIES):
            try:
                logger.debug(f"Запрос к локальной модели {MODEL_NAME}")
                logger.debug(f"{text} {system_prompt[:20]}...")
                resp = await client.post(OLLAMA_URL, json=payload)
                resp.raise_for_status()

                data = resp.json()
                answer = data["message"]["content"]
                logger.debug("Успешный ответ от модели")
                print(answer)
                return answer

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.error(f"Модель {MODEL_NAME} не найдена")
                    raise ValueError(f"Модель {MODEL_NAME} недоступна") from e

                logger.warning(f"HTTP ошибка: {str(e)}, попытка {attempt + 1}/{MAX_RETRIES}")
                await asyncio.sleep(BASE_DELAY * (2 ** attempt))

            except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as e:
                logger.warning(f"Сетевая ошибка: {str(e)}, попытка {attempt + 1}/{MAX_RETRIES}")
                await asyncio.sleep(BASE_DELAY * (2 ** attempt))

            except Exception as e:
                logger.error(f"Неожиданная ошибка: {str(e)}")
                if attempt == MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(BASE_DELAY * (2 ** attempt))

        raise RuntimeError("Не удалось получить ответ после ретраев")


async def test_local_model():
    """Тестовая функция для проверки работы с локальной моделью"""
    prompt = "Привет! Как тебя зовут и что ты умеешь?"
    system_prompt = "Ты полезный AI-ассистент. Отвечай на русском языке."

    try:
        start_time = asyncio.get_event_loop().time()
        response = await ask_local_model(prompt, system_prompt)
        elapsed = asyncio.get_event_loop().time() - start_time

        print(f"\n{'=' * 40}")
        print(f"Модель: {MODEL_NAME}")
        print(f"Время ответа: {elapsed:.2f} сек")
        print(f"Ответ:\n{response}")
        print(f"{'=' * 40}\n")
        return response

    except Exception as e:
        logger.exception("Ошибка при тестировании модели")
        return f"Ошибка: {str(e)}"


def check_ollama_connection():
    """Проверяет доступность Ollama сервера"""
    try:
        response = httpx.get("http://localhost:11434", timeout=5.0)
        if response.status_code == 200:
            return True, "✅ Ollama сервер доступен"
        return False, f"⚠️ Ollama сервер недоступен (код: {response.status_code})"
    except Exception as e:
        return False, f"❌ Ошибка подключения: {str(e)}"


async def test():
    prompt = "привет, как у тебя дела?"
    system_prompt = "Ты полезный AI-ассистент. Отвечай на русском языке."
    tasks = []
    for i in range(5):
        task = asyncio.create_task(ask_local_model(prompt, system_prompt))
        tasks.append(task)

    # Ждем завершения всех задач
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        print(result)
        print("=" * 40)

if __name__ == "__main__":
    # Проверка подключения
    # status, message = check_ollama_connection()
    # print(message)
    #
    # if "доступен" in message:
    #     # Получение информации о доступных моделях
    #     try:
    #         models = httpx.get("http://localhost:11434/api/tags").json().get("models", [])
    #         print("\nДоступные модели:")
    #         for model in models:
    #             print(f"  - {model['name']} (размер: {model.get('size', 'N/A')})")
    #     except Exception:
    #         print("Не удалось получить список моделей")
    #
    #     # Запуск теста
    #     asyncio.run(test_local_model())


    asyncio.run(test())