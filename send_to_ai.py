import os
from config import system_prompt_for_russian_market
import requests


API_URL = os.getenv("OPENROUTER_API_URL")
API_KEY = os.getenv("OPENROUTER_API_KEY")



def send_to_deepseek(prompt) -> str:
    """Отправляет запрос к DeepSeek‑R1‑0528 и возвращает только финальный ответ."""
    try:

        max_context_tokens = 33000

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }

        json_request = {
            "model": "deepseek/deepseek-r1-0528:free",
            "messages": [
                {"role": "system", "content": system_prompt_for_russian_market},
                {"role": "user", "content": str(prompt)}
            ],
            "max_tokens": max_context_tokens
        }

        response = requests.post(API_URL, headers=headers, json=json_request, timeout=None)
        response.raise_for_status()
        data = response.json()


        reasoning = data['choices'][0]['message'].get('reasoning_content')
        answer = data['choices'][0]['message']['content']

        # Для отладки можно вывести рассуждения:
        if reasoning:
            print("=== Рассуждения модели: ===")
            print(reasoning)
            print("============================")

        return answer

    except Exception as e:
        print(f"Ошибка при запросе DeepSeek: {e}")
        raise
