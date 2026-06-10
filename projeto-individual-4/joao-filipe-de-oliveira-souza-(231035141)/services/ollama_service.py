import base64
import os
import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_TEXT_MODEL = os.getenv("OLLAMA_TEXT_MODEL", "llama3.1:8b")
DEFAULT_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava")

# Ajustes para reduzir consumo de RAM no Ollama.
# Sugestao para ambiente com pouca memoria:
# - OLLAMA_TEXT_MODEL=llama3.2:3b
# - OLLAMA_NUM_CTX=1024
# - OLLAMA_KEEP_ALIVE=0s
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "1024"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "400"))
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "0s")


def ask_ollama_vision(image_path: str, prompt: str, model: str = DEFAULT_VISION_MODEL):
    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_base64],
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": {
            "num_ctx": OLLAMA_NUM_CTX,
            "num_predict": OLLAMA_NUM_PREDICT,
        },
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=60)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise requests.HTTPError(
            f"Falha ao chamar Ollama em {OLLAMA_URL} (status {response.status_code}). "
            "Verifique se o Ollama esta ativo e se o endpoint/modelo de visao existe."
        ) from exc

    return response.json()["response"]


def ask_ollama_text(prompt: str, model: str = DEFAULT_TEXT_MODEL):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": {
            "num_ctx": OLLAMA_NUM_CTX,
            "num_predict": OLLAMA_NUM_PREDICT,
        },
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=15)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise requests.HTTPError(
            f"Falha ao chamar Ollama em {OLLAMA_URL} (status {response.status_code}). "
            f"Verifique se o Ollama esta ativo e se o modelo textual '{model}' existe."
        ) from exc

    return response.json()["response"]