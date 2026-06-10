import json
import os
import time
import threading

from services.gpt_service import ask_gpt_vision


VISION_REQUEST_INTERVAL_MS = int(os.getenv("OPENAI_VISION_REQUEST_INTERVAL_MS", "250"))


def _spinner(stop_event: threading.Event, prefix: str):
    frames = [".", "..", "..."]
    frame_index = 0

    while not stop_event.is_set():
        print(f"\r{prefix}{frames[frame_index % len(frames)]}", end="", flush=True)
        frame_index += 1
        time.sleep(0.25)


def _ask_gpt_vision_with_loading(image_path: str, prompt: str, progress_label: str):
    stop_event = threading.Event()
    spinner_thread = threading.Thread(
        target=_spinner,
        args=(stop_event, f"[vision] {progress_label} - aguardando GPT"),
        daemon=True,
    )

    spinner_thread.start()
    started_at = time.time()
    try:
        return ask_gpt_vision(image_path=image_path, prompt=prompt)
    finally:
        stop_event.set()
        spinner_thread.join()
        elapsed = time.time() - started_at
        print(f"\r[vision] {progress_label} - concluido em {elapsed:.1f}s{' ' * 15}")


def extract_tables_from_images(images: list):
    result = []
    total_images = len(images)

    if total_images == 0:
        print("[vision] Nenhuma imagem para processar.")
        return result

    print(f"[vision] Iniciando extracao por visao em {total_images} imagem(ns).")

    prompt = """
        Você é um especialista em OCR, análise documental e extração estruturada de tabelas.

Sua única função é analisar imagens contendo tabelas, relatórios, planilhas, documentos digitalizados, PDFs convertidos em imagem, gráficos tabulares ou documentos financeiros e converter todas as informações encontradas para JSON estruturado.

# OBJETIVO

Transformar tabelas presentes na imagem em JSON válido, completo e consistente.

A extração deve preservar:

- Estrutura hierárquica
- Cabeçalhos
- Subcabeçalhos
- Agrupamentos de colunas
- Agrupamentos de linhas
- Totais
- Subtotais
- Unidades de medida
- Contexto da tabela

Nunca simplifique os dados.

Nunca resuma.

Nunca omita linhas.

Nunca invente valores.

Nunca faça cálculos que não estejam explícitos na imagem.

--------------------------------------------------
REGRAS DE EXTRAÇÃO
--------------------------------------------------

1. Analise a imagem inteira antes de iniciar a extração.

2. Detecte todas as tabelas existentes.

3. Extraia cada tabela separadamente.

4. Preserve a hierarquia dos cabeçalhos.

5. Preserve agrupamentos visuais.

6. Preserve títulos e subtítulos.

7. Preserve linhas de totalização.

8. Preserve observações de rodapé.

9. Preserve fontes citadas.

10. Preserve unidades de medida.

--------------------------------------------------
REGRA CRÍTICA
--------------------------------------------------

Se houver dúvida entre inventar um valor ou retornar nulo:

RETORNE NULL.

Exemplo:

{
  "saldo": null
}

Jamais estime.

Jamais deduza.

Jamais complete números faltantes.

--------------------------------------------------
NORMALIZAÇÃO DE NÚMEROS
--------------------------------------------------

Converter automaticamente formatos brasileiros.

Exemplos:

"5.894,2"
→ 5894.2

"31.507"
→ 31507

"752.485"
→ 752485

"13.205"
→ 13205

Remover:

- espaços
- R$
- %
- quebras de linha

--------------------------------------------------
PERCENTUAIS
--------------------------------------------------

Converter:

"-2,45%"
→ -2.45

"11,9%"
→ 11.9

Manter como número.

Nunca retornar string.

--------------------------------------------------
MOEDAS
--------------------------------------------------

Converter:

"R$ 12.602,0"
→ 12602.0

Armazenar como número.

--------------------------------------------------
DATAS
--------------------------------------------------

Converter automaticamente:

Jan → 01
Fev → 02
Mar → 03
Abr → 04
Mai → 05
Jun → 06
Jul → 07
Ago → 08
Set → 09
Out → 10
Nov → 11
Dez → 12

Exemplos:

"Mar/2026"
→ "2026-03"

"Jan/2025"
→ "2025-01"

--------------------------------------------------
IDENTIFICAÇÃO DE TABELAS
--------------------------------------------------

Para cada tabela encontrada:

{
  "table_name": "...",
  "data": [...]
}

Se houver múltiplas tabelas:

{
  "tables": [...]
}

--------------------------------------------------
DETECÇÃO DE HIERARQUIA
--------------------------------------------------

Exemplo visual:

                2025
           Março
      R$      Unidades

Resultado:

{
  "2025": {
    "marco": {
      "rs_milhoes": ...,
      "unidades": ...
    }
  }
}

Nunca achate hierarquias.

--------------------------------------------------
EXEMPLO
--------------------------------------------------

Tabela:

Agente | Mar/2026 | Ano 2026

Resultado:

{
  "table_name": "Aquisição",
  "data": [
    {
      "agente": "CAIXA",
      "mar_2026": {
        "rs_milhoes": 5894.2,
        "unidades": 18550
      },
      "ano_2026": {
        "rs_milhoes": 14015.2,
        "unidades": 44672
      }
    }
  ]
}

--------------------------------------------------
TOTAIS
--------------------------------------------------

Sempre incluir.

Exemplo:

{
  "totals": {
    "rs_milhoes": 31165.1,
    "unidades": 77867
  }
}

--------------------------------------------------
FONTES
--------------------------------------------------

Quando existirem:

Fontes: Abecip e Banco Central

Extrair:

{
  "source": [
    "Abecip",
    "Banco Central"
  ]
}

--------------------------------------------------
CONFIANÇA
--------------------------------------------------

Adicionar score:

{
  "confidence": 0.98
}

Escala:

1.00 = totalmente legível

0.90 = pequenos ruídos

0.70 = alguns campos duvidosos

0.50 = vários campos ilegíveis

--------------------------------------------------
VALORES ILEGÍVEIS
--------------------------------------------------

Exemplo:

{
  "captacao_liquida": null
}

Nunca inventar.

--------------------------------------------------
GRÁFICOS
--------------------------------------------------

Se houver gráficos:

Extrair apenas:

{
  "graph": {
    "title": "...",
    "x_axis": "...",
    "y_axis": "...",
    "series": [...]
  }
}

Somente se os valores forem legíveis.

Caso contrário:

{
  "graph": {
    "title": "...",
    "data_available": false
  }
}

--------------------------------------------------
VALIDAÇÃO
--------------------------------------------------

Antes de responder:

1. Verifique se todas as linhas foram extraídas.

2. Verifique se todos os totais existem.

3. Verifique se todos os números são válidos.

4. Verifique se o JSON é válido.

5. Verifique se não há texto fora do JSON.

--------------------------------------------------
FORMATO DE SAÍDA
--------------------------------------------------

RETORNE EXCLUSIVAMENTE JSON.

NÃO utilize markdown.

NÃO utilize explicações.

NÃO utilize comentários.

NÃO utilize blocos de código.

NÃO escreva nenhum texto antes ou depois do JSON.

A resposta deve ser um JSON válido pronto para ser processado por sistemas automatizados.
        """

    for index, image in enumerate(images):
        progress = f"Imagem {index + 1}/{total_images}"
        print(f"[vision] {progress} - pagina {image['page']}, indice {image['image_index']}")

        if index > 0 and VISION_REQUEST_INTERVAL_MS > 0:
            print(f"[vision] Aguardando {VISION_REQUEST_INTERVAL_MS}ms antes da proxima requisicao...")
            time.sleep(VISION_REQUEST_INTERVAL_MS / 1000.0)

        response = _ask_gpt_vision_with_loading(
            image_path=image["path"],
            prompt=prompt,
            progress_label=progress,
        )

        try:
          parsed_response = json.loads(response)
        except json.JSONDecodeError:
          print(f"[vision] {progress} - resposta JSON invalida, ignorando item.")
          continue

        # Mantem somente itens que realmente contem tabela.
        if isinstance(parsed_response, dict):
          if parsed_response.get("has_table") is False:
            continue
          if "graph" in parsed_response and "tables" not in parsed_response and "table_name" not in parsed_response:
            continue
          if parsed_response.get("tables") == []:
            continue

        result.append(parsed_response)

    print("[vision] Extracao por visao concluida.")
    return result