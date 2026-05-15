import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from src import OCRLine, PageResult
from src.api_client import OcrVlApiClient, parse_spotting
from src.brace_detector import detect_large_braces
from src.correction import correct_text, set_correction_map
from src.layout import normalize_bbox, sort_lines


DEFAULT_LOC_GRID_SIZE = 1000


def preprocess_image(img: np.ndarray, ocr_cfg: dict) -> np.ndarray:
    if not ocr_cfg.get("preprocess", False):
        return img

    pil = Image.fromarray(img)
    pil = ImageOps.autocontrast(pil, cutoff=1)

    contrast = float(ocr_cfg.get("contrast", 1.25))
    if contrast != 1.0:
        pil = ImageEnhance.Contrast(pil).enhance(contrast)

    sharpen = float(ocr_cfg.get("sharpen", 1.1))
    if sharpen != 1.0:
        pil = ImageEnhance.Sharpness(pil).enhance(sharpen)

    denoise = bool(ocr_cfg.get("denoise", False))
    if denoise:
        pil = pil.filter(ImageFilter.MedianFilter(size=3))

    return np.asarray(pil, dtype=np.uint8)


class OcrEngine:
    def __init__(self, config: dict):
        api_cfg = config["api"]
        self._ocr_cfg = config.get("ocr", {})
        set_correction_map(config.get("correction", {}))
        self._client = OcrVlApiClient(
            base_url=api_cfg["base_url"],
            api_key=api_cfg["api_key"],
            model_name=api_cfg["model_name"],
            prompt=api_cfg.get("prompt", "Spotting:"),
            max_tokens=api_cfg.get("max_tokens", 8192),
        )

    def process_page(self, img, page_num: int) -> PageResult:
        h, w = img.shape[:2]
        result = PageResult(page_num=page_num, width=w, height=h)

        request_img = preprocess_image(img, self._ocr_cfg)
        lines_data = self._process_with_retry(request_img)
        if not lines_data:
            return result

        loc_grid_size = float(self._ocr_cfg.get("loc_grid_size", DEFAULT_LOC_GRID_SIZE))
        if loc_grid_size <= 0:
            loc_grid_size = DEFAULT_LOC_GRID_SIZE
        scale_x = w / loc_grid_size
        scale_y = h / loc_grid_size

        for line_text, bbox, polygon in lines_data:
            x1, y1, x2, y2 = bbox
            scaled_bbox = normalize_bbox(
                (
                    int(round(x1 * scale_x)),
                    int(round(y1 * scale_y)),
                    int(round(x2 * scale_x)),
                    int(round(y2 * scale_y)),
                ),
                w,
                h,
            )
            scaled_polygon = [
                [
                    max(0.0, min(float(p[0]) * scale_x, float(w))),
                    max(0.0, min(float(p[1]) * scale_y, float(h))),
                ]
                for p in polygon
            ]

            line_text = correct_text(line_text)
            result.lines.append(
                OCRLine(
                    text=line_text,
                    score=0.8,
                    bbox=scaled_bbox,
                    polygon=scaled_polygon,
                )
            )

        result.lines.extend(detect_large_braces(request_img, result.lines, self._ocr_cfg))
        result.lines = sort_lines(result.lines, w)
        return result

    def _process_with_retry(self, img) -> list:
        max_attempts = 1
        if self._ocr_cfg.get("retry_abnormal", False):
            max_attempts += max(0, int(self._ocr_cfg.get("max_retries", 1)))

        last_lines = []
        last_error = None
        for _ in range(max_attempts):
            try:
                text = self._client.process_image(img)
            except Exception as exc:
                last_error = exc
                continue
            last_lines = parse_spotting(text)
            if last_lines:
                return last_lines
        if last_error is not None:
            raise last_error
        return last_lines
