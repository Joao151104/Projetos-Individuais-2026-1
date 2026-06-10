import json
import time
from datetime import datetime

import fitz  # PyMuPDF

from services.gpt_service import ask_gpt_text


def log_step(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [text] {message}")


def extract_text(pdf_path: str):
    started_at = time.time()
    pages = []

    with fitz.open(pdf_path) as doc:
        total_pages = len(doc)
        log_step(f"Iniciando extracao textual em {total_pages} pagina(s).")

        for page_index, page in enumerate(doc):
            current_page = page_index + 1
            page_started_at = time.time()
            log_step(f"Processando pagina {current_page}/{total_pages}...")
            text = page.get_text()

            prompt = '''Você é um assistente especialista em transformar textos extraídos de PDFs em dados estruturados.

Receberei um JSON com páginas extraídas de um PDF. O texto pode conter quebras ruins, cabeçalhos, rodapés, títulos quebrados e informações espalhadas.

Extraia e organize o conteúdo em JSON válido.

Regras:
1. Retorne apenas JSON válido.
2. Não invente dados.
3. Preserve valores, datas e percentuais exatamente como aparecem.
4. Remova ruídos como rodapés repetidos, endereço, telefone e "PÁGINA X".
5. Una frases quebradas.
6. Agrupe as informações por seção.
7. Quando encontrar indicadores, coloque em formato chave-valor.
8. Quando houver texto explicativo, coloque em arrays de parágrafos.
9. Se não encontrar alguma informação, use null ou array vazio.

Formato de saída:

{
  "titulo": "",
  "data_referencia": "",
  "fonte": "",
  "destaques": {},
  "secoes": [
    {
      "titulo": "",
      "paragrafos": [],
      "indicadores": {}
    }
  ]
}

Entrada:
{{TEXT_EXTRACTION_JSON}}'''

            input_payload = {
                "page": page_index + 1,
                "text": text.strip()
            }

            final_prompt = prompt.replace(
                "{{TEXT_EXTRACTION_JSON}}",
                json.dumps(input_payload, ensure_ascii=False)
            )

            structured_text = None
            llm_error = None

            try:
                llm_response = ask_gpt_text(final_prompt)
                llm_response = llm_response.strip()

                if llm_response.startswith("```"):
                    lines = llm_response.splitlines()
                    if lines and lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    llm_response = "\n".join(lines).strip()

                structured_text = json.loads(llm_response)
            except Exception as exc:
                llm_error = str(exc)

            pages.append({
                "page": current_page,
                "structured_text": structured_text,
                "llm_error": llm_error
            })

            log_step(
                f"Pagina {current_page}/{total_pages} finalizada em {time.time() - page_started_at:.1f}s."
            )

    log_step(f"Extracao textual concluida em {time.time() - started_at:.1f}s.")
    return pages
