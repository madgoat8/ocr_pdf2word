import numpy as np

from src import OCRLine
from src.layout import normalize_bbox

try:
    import cv2
except ImportError:  # pragma: no cover - depends on local optional dependency
    cv2 = None


def detect_large_braces(
    img: np.ndarray,
    existing_lines: list[OCRLine],
    cfg: dict,
) -> list[OCRLine]:
    if not cfg.get("detect_braces", True):
        return []
    if cv2 is None:
        return []

    page_h, page_w = img.shape[:2]
    if page_h <= 0 or page_w <= 0:
        return []

    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        35,
        15,
    )

    close_h = max(9, int(page_h * 0.012))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, close_h))
    connected = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_h = int(page_h * float(cfg.get("brace_min_height_ratio", 0.08)))
    min_h = max(min_h, _median_line_height(existing_lines) * 2)
    max_w = int(page_w * float(cfg.get("brace_max_width_ratio", 0.12)))
    min_w = max(4, int(page_w * 0.004))

    braces: list[OCRLine] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if h < min_h or w < min_w or w > max_w:
            continue
        if h / max(w, 1) < float(cfg.get("brace_min_aspect", 2.4)):
            continue

        bbox = normalize_bbox((x, y, x + w, y + h), page_w, page_h)
        if _overlaps_existing_text_too_much(bbox, existing_lines):
            continue

        component = binary[y : y + h, x : x + w]
        density = float(np.count_nonzero(component)) / max(component.size, 1)
        if not 0.015 <= density <= 0.55:
            continue

        text = _classify_brace(component)
        braces.append(
            OCRLine(
                text=text,
                score=0.55,
                bbox=bbox,
                polygon=[
                    [float(bbox[0]), float(bbox[1])],
                    [float(bbox[2]), float(bbox[1])],
                    [float(bbox[2]), float(bbox[3])],
                    [float(bbox[0]), float(bbox[3])],
                ],
            )
        )

    return _dedupe_braces(braces)


def _median_line_height(lines: list[OCRLine]) -> int:
    heights = sorted(max(ln.bbox[3] - ln.bbox[1], 1) for ln in lines)
    if not heights:
        return 24
    return heights[len(heights) // 2]


def _overlaps_existing_text_too_much(
    bbox: tuple[int, int, int, int],
    lines: list[OCRLine],
) -> bool:
    area = max((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]), 1)
    overlap = 0
    for ln in lines:
        ix1 = max(bbox[0], ln.bbox[0])
        iy1 = max(bbox[1], ln.bbox[1])
        ix2 = min(bbox[2], ln.bbox[2])
        iy2 = min(bbox[3], ln.bbox[3])
        if ix2 > ix1 and iy2 > iy1:
            overlap += (ix2 - ix1) * (iy2 - iy1)
    return overlap / area > 0.35


def _classify_brace(component: np.ndarray) -> str:
    h, w = component.shape[:2]
    if h < 3 or w < 3:
        return "{"

    top = component[: max(1, h // 3), :]
    middle = component[h // 3 : max(h // 3 + 1, 2 * h // 3), :]
    bottom = component[2 * h // 3 :, :]
    top_bottom_center = (_ink_center_x(top) + _ink_center_x(bottom)) / 2
    middle_center = _ink_center_x(middle)
    return "{" if middle_center < top_bottom_center else "}"


def _ink_center_x(region: np.ndarray) -> float:
    ys, xs = np.nonzero(region)
    if len(xs) == 0:
        return region.shape[1] / 2
    return float(np.mean(xs))


def _dedupe_braces(lines: list[OCRLine]) -> list[OCRLine]:
    result: list[OCRLine] = []
    for line in sorted(lines, key=lambda ln: (ln.bbox[1], ln.bbox[0])):
        if any(_iou(line.bbox, kept.bbox) > 0.45 for kept in result):
            continue
        result.append(line)
    return result


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ix1 = max(a[0], b[0])
    iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2])
    iy2 = min(a[3], b[3])
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    area_a = max((a[2] - a[0]) * (a[3] - a[1]), 1)
    area_b = max((b[2] - b[0]) * (b[3] - b[1]), 1)
    return inter / (area_a + area_b - inter)
