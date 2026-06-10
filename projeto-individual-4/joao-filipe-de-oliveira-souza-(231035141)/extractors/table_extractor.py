import pdfplumber
import time
from datetime import datetime


def log_step(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [table] {message}")


def extract_tables(pdf_path: str):
    started_at = time.time()
    result = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        log_step(f"Iniciando extracao de tabelas em {total_pages} pagina(s).")

        for page_index, page in enumerate(pdf.pages):
            current_page = page_index + 1
            page_started_at = time.time()
            tables = page.extract_tables()
            log_step(
                f"Pagina {current_page}/{total_pages}: {len(tables)} tabela(s) encontrada(s)."
            )

            for table_index, table in enumerate(tables):
                result.append({
                    "page": current_page,
                    "table_index": table_index + 1,
                    "data": table
                })

            log_step(
                f"Pagina {current_page}/{total_pages} finalizada em {time.time() - page_started_at:.1f}s."
            )

    log_step(
        f"Extracao de tabelas concluida em {time.time() - started_at:.1f}s. Total: {len(result)} tabela(s)."
    )
    return result