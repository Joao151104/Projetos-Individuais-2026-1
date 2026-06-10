import json
import os
import uuid
import hashlib
import time
from datetime import datetime


def load_dotenv(dotenv_path: str = ".env"):
    if not os.path.exists(dotenv_path):
        return

    with open(dotenv_path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            raw_line = line.strip()
            if not raw_line or raw_line.startswith("#") or "=" not in raw_line:
                continue

            key, value = raw_line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            # Mantem variaveis ja definidas no ambiente do sistema.
            os.environ.setdefault(key, value)


load_dotenv()

from extractors.text_extractor import extract_text
from extractors.table_extractor import extract_tables
from extractors.image_extractor import extract_images
from extractors.vision_extractor import extract_tables_from_images

PDF_PATH = os.getenv("PDF_PATH", "PDF/dados.pdf")
OUTPUT_DIR = "outputs"
PROCESSED_INDEX_FILE = os.path.join(OUTPUT_DIR, "processed_index.json")
ENABLE_VISION_EXTRACTION = os.getenv("ENABLE_VISION_EXTRACTION", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

os.makedirs(OUTPUT_DIR, exist_ok=True)


def log_step(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [app] {message}")


def calculate_file_sha256(file_path: str) -> str:
    log_step("Calculando hash SHA-256 do documento...")
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as source_file:
        while True:
            chunk = source_file.read(8192)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


def load_processed_index() -> dict:
    log_step("Carregando indice de documentos processados...")
    if not os.path.exists(PROCESSED_INDEX_FILE):
        log_step("Indice ainda nao existe. Um novo sera criado apos o primeiro processamento.")
        return {"documents": {}}

    try:
        with open(PROCESSED_INDEX_FILE, "r", encoding="utf-8") as index_file:
            data = json.load(index_file)
        if not isinstance(data, dict):
            return {"documents": {}}
        if "documents" not in data or not isinstance(data["documents"], dict):
            data["documents"] = {}
        return data
    except (json.JSONDecodeError, OSError):
        return {"documents": {}}


def save_processed_index(index_data: dict):
    log_step("Salvando indice de documentos processados...")
    with open(PROCESSED_INDEX_FILE, "w", encoding="utf-8") as index_file:
        json.dump(index_data, index_file, ensure_ascii=False, indent=2)


def process_pdf(pdf_path: str):
    started_at = time.time()
    log_step(f"Iniciando processamento do arquivo: {pdf_path}")
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF nao encontrado: {pdf_path}")

    document_hash = calculate_file_sha256(pdf_path)
    log_step(f"Hash do documento: {document_hash}")
    processed_index = load_processed_index()
    existing_document = processed_index["documents"].get(document_hash)

    if existing_document:
        existing_output_file = existing_document.get("output_file")
        if existing_output_file and os.path.exists(existing_output_file):
            log_step("Documento duplicado detectado. Reutilizando resultado existente.")
            with open(existing_output_file, "r", encoding="utf-8") as existing_file:
                existing_result = json.load(existing_file)
            return existing_result, existing_output_file, True

    log_step("Documento novo. Iniciando extracao de dados.")
    file_id = str(uuid.uuid4())

    log_step("Extraindo texto...")
    text_started_at = time.time()
    texts = extract_text(pdf_path)
    log_step(f"Extracao de texto finalizada em {time.time() - text_started_at:.1f}s.")

    log_step("Extraindo tabelas...")
    table_started_at = time.time()
    tables = extract_tables(pdf_path)
    log_step(f"Extracao de tabelas finalizada em {time.time() - table_started_at:.1f}s.")

    log_step("Extraindo imagens...")
    image_started_at = time.time()
    images = extract_images(pdf_path, file_id)
    log_step(f"Extracao de imagens finalizada em {time.time() - image_started_at:.1f}s.")

    image_tables = []
    vision_error = None

    if ENABLE_VISION_EXTRACTION:
        log_step("Extracao por visao habilitada. Processando tabelas em imagens...")
        vision_started_at = time.time()
        try:
            image_tables = extract_tables_from_images(images)
            log_step(f"Extracao por visao finalizada em {time.time() - vision_started_at:.1f}s.")
        except Exception as exc:
            vision_error = str(exc)
            log_step(f"Falha na extracao por visao: {vision_error}")
    else:
        log_step("Extracao por visao desabilitada.")

    result = {
        "file_id": file_id,
        "document_hash": document_hash,
        "source_file": os.path.abspath(pdf_path),
        "text_extraction": texts,
        "table_from_image_extraction": image_tables,
    }

    output_file = os.path.join(OUTPUT_DIR, f"{file_id}.json")
    log_step(f"Salvando resultado em: {output_file}")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    processed_index["documents"][document_hash] = {
        "file_id": file_id,
        "output_file": output_file,
        "source_file": os.path.abspath(pdf_path),
    }
    save_processed_index(processed_index)
    log_step(f"Processamento finalizado com sucesso em {time.time() - started_at:.1f}s.")

    return result, output_file, False


if __name__ == "__main__":
    result, output_path, already_processed = process_pdf(PDF_PATH)
    if already_processed:
        print(f"Documento ja processado anteriormente. Resultado existente: {output_path}")
    else:
        print(f"Processamento concluido. JSON salvo em: {output_path}")