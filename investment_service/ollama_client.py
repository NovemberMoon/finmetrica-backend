import httpx

from core.config import settings


async def ask_ollama(prompt: str) -> str:
    url = f"{settings.OLLAMA_URL}/api/generate"

    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.4,
            "num_predict": 700,
        },
    }

    async with httpx.AsyncClient(timeout=90.0, trust_env=False) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    return data.get("response", "Модель не вернула текст рекомендации.")