from pathlib import Path

import fitz
import numpy as np
from PIL import Image


def pdf_to_images(pdf_path: str | Path, dpi: int = 300) -> list[tuple[int, np.ndarray]]:
    pages = []
    doc = fitz.open(str(pdf_path))
    for i in range(doc.page_count):
        page = doc[i]
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        pages.append((i + 1, np.array(img)))
    doc.close()
    return pages


def should_skip_page(img: np.ndarray, empty_threshold: float = 0.02) -> bool:
    gray = np.mean(img, axis=2)
    std = np.std(gray)
    if std < 10:
        return True
    return False
