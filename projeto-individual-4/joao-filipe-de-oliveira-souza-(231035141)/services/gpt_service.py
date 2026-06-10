import json
import os
import base64
import time
import re
from urllib import error, request


OPENAI_API_URL = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")
DEFAULT_GPT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_GPT_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", DEFAULT_GPT_MODEL)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "500"))
OPENAI_VISION_MAX_TOKENS = int(os.getenv("OPENAI_VISION_MAX_TOKENS", "1000"))
OPENAI_VISION_DETAIL = os.getenv("OPENAI_VISION_DETAIL", "low")
OPENAI_MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "5"))
OPENAI_RETRY_BASE_DELAY_MS = int(os.getenv("OPENAI_RETRY_BASE_DELAY_MS", "300"))


def _compute_retry_delay_seconds(http_error: error.HTTPError, error_body: str, attempt: int) -> float:
    retry_after = http_error.headers.get("Retry-After")
    if retry_after:
        try:
            # Add a small safety buffer to reduce repeated 429s on tight limits.
            return max(float(retry_after), 0.1) + 0.15
        except ValueError:
            pass

    message_delay_match = re.search(r"try again in\s*(\d+)\s*ms", error_body, flags=re.IGNORECASE)
    if message_delay_match:
        delay_ms = int(message_delay_match.group(1))
        # Add jitter/buffer so next attempt is less likely to hit the same window.
        return max(delay_ms / 1000.0, 0.1) + 0.20

    base_delay = max(OPENAI_RETRY_BASE_DELAY_MS, 100) / 1000.0
    return (base_delay * (2 ** attempt)) + 0.10


def _send_openai_request(payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")

    for attempt in range(OPENAI_MAX_RETRIES + 1):
        http_request = request.Request(
            OPENAI_API_URL,
            data=data,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            is_rate_limit = exc.code == 429

            if is_rate_limit and attempt < OPENAI_MAX_RETRIES:
                delay_seconds = _compute_retry_delay_seconds(exc, error_body, attempt)
                time.sleep(delay_seconds)
                continue

            raise RuntimeError(
                f"Falha ao chamar GPT em {OPENAI_API_URL} (status {exc.code}). {error_body}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"Falha ao conectar com GPT em {OPENAI_API_URL}. {exc.reason}") from exc


def ask_gpt_text(prompt: str, model: str = DEFAULT_GPT_MODEL):
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY nao configurada. Defina a variavel de ambiente para usar GPT."
        )

    if OPENAI_MAX_TOKENS <= 0:
        raise ValueError("OPENAI_MAX_TOKENS deve ser maior que zero.")

    if OPENAI_MAX_RETRIES < 0:
        raise ValueError("OPENAI_MAX_RETRIES nao pode ser negativo.")

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "max_tokens": OPENAI_MAX_TOKENS,
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    response_data = _send_openai_request(payload, timeout=60)

    return response_data["choices"][0]["message"]["content"]


def ask_gpt_vision(image_path: str, prompt: str, model: str = DEFAULT_GPT_VISION_MODEL):
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY nao configurada. Defina a variavel de ambiente para usar GPT."
        )

    if OPENAI_VISION_MAX_TOKENS <= 0:
        raise ValueError("OPENAI_VISION_MAX_TOKENS deve ser maior que zero.")

    if OPENAI_MAX_RETRIES < 0:
        raise ValueError("OPENAI_MAX_RETRIES nao pode ser negativo.")

    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}",
                            "detail": OPENAI_VISION_DETAIL,
                        },
                    },
                ],
            }
        ],
        "max_tokens": OPENAI_VISION_MAX_TOKENS,
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    response_data = _send_openai_request(payload, timeout=90)

    return response_data["choices"][0]["message"]["content"]