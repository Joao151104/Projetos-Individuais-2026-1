import fitz
import os
import time
from datetime import datetime


def log_step(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [image] {message}")


def extract_images(pdf_path: str, file_id: str):
    started_at = time.time()
    doc = fitz.open(pdf_path)
    image_dir = f"outputs/{file_id}/images"

    os.makedirs(image_dir, exist_ok=True)

    images = []
    total_pages = len(doc)
    log_step(f"Iniciando extracao de imagens em {total_pages} pagina(s).")

    for page_index, page in enumerate(doc):
        current_page = page_index + 1
        page_started_at = time.time()
        image_list = page.get_images(full=True)
        log_step(
            f"Pagina {current_page}/{total_pages}: {len(image_list)} imagem(ns) encontrada(s)."
        )

        for image_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)

            image_bytes = base_image["image"]
            image_ext = base_image["ext"]

            image_name = f"page_{page_index + 1}_image_{image_index + 1}.{image_ext}"
            image_path = f"{image_dir}/{image_name}"

            with open(image_path, "wb") as image_file:
                image_file.write(image_bytes)

            images.append({
                "page": current_page,
                "image_index": image_index + 1,
                "path": image_path,
                "extension": image_ext
            })

        log_step(
            f"Pagina {current_page}/{total_pages} finalizada em {time.time() - page_started_at:.1f}s."
        )

    doc.close()
    log_step(
        f"Extracao de imagens concluida em {time.time() - started_at:.1f}s. Total: {len(images)} imagem(ns)."
    )

    return images