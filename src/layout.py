from dataclasses import dataclass
from statistics import median

from src import OCRLine


SIDE_THRESHOLD = 0.45
MAX_INDENT_RATIO = 0.9


@dataclass(frozen=True)
class TextBounds:
    left: int
    right: int


def normalize_bbox(
    bbox: tuple[int, int, int, int],
    page_w: int,
    page_h: int,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = bbox
    left, right = sorted((int(round(x1)), int(round(x2))))
    top, bottom = sorted((int(round(y1)), int(round(y2))))
    left = max(0, min(left, page_w))
    right = max(0, min(right, page_w))
    top = max(0, min(top, page_h))
    bottom = max(0, min(bottom, page_h))
    return left, top, right, bottom


def line_height(line: OCRLine) -> int:
    return max(line.bbox[3] - line.bbox[1], 1)


def _center_y(line: OCRLine) -> float:
    return (line.bbox[1] + line.bbox[3]) / 2


def _row_threshold(lines: list[OCRLine]) -> float:
    if not lines:
        return 8.0
    return max(median(line_height(ln) for ln in lines) * 0.7, 8.0)


def group_lines_by_y(lines: list[OCRLine]) -> list[list[OCRLine]]:
    ordered = sorted(lines, key=lambda ln: (_center_y(ln), ln.bbox[0]))
    threshold = _row_threshold(ordered)
    rows: list[list[OCRLine]] = []
    row_centers: list[float] = []

    for ln in ordered:
        center = _center_y(ln)
        if rows and abs(center - row_centers[-1]) <= threshold:
            rows[-1].append(ln)
            row_centers[-1] = sum(_center_y(item) for item in rows[-1]) / len(rows[-1])
        else:
            rows.append([ln])
            row_centers.append(center)

    for row in rows:
        row.sort(key=lambda ln: ln.bbox[0])
    return rows


def sort_lines(lines: list[OCRLine], page_w: int) -> list[OCRLine]:
    result: list[OCRLine] = []
    for row in group_lines_by_y(lines):
        row.sort(
            key=lambda ln: (
                1 if is_side_annotation(ln, page_w) else 0,
                ln.bbox[0],
            )
        )
        result.extend(row)
    return result


def calc_vertical_gap(prev: OCRLine | None, curr: OCRLine) -> float:
    if prev is None:
        return 0.0
    gap = curr.bbox[1] - prev.bbox[3]
    return max(gap, 0)


def is_side_annotation(line: OCRLine, page_w: int) -> bool:
    return line.bbox[0] / max(page_w, 1) >= SIDE_THRESHOLD


def is_wide_line(line: OCRLine, page_w: int) -> bool:
    return (line.bbox[2] - line.bbox[0]) / max(page_w, 1) > 0.6


def _percentile(values: list[int], pct: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * pct
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return int(round(ordered[lo] * (1 - frac) + ordered[hi] * frac))


def page_text_bounds(lines: list[OCRLine], page_w: int) -> TextBounds:
    if not lines:
        return TextBounds(left=0, right=max(page_w, 1))

    lefts = [ln.bbox[0] for ln in lines]
    rights = [ln.bbox[2] for ln in lines]
    if len(lines) >= 8:
        left = min(min(lefts), _percentile(lefts, 0.1))
        right = max(max(rights), _percentile(rights, 0.9))
    else:
        left = min(lefts)
        right = max(rights)

    left = max(0, min(left, page_w))
    right = max(0, min(right, page_w))
    if right <= left:
        right = min(page_w, left + 1)
    return TextBounds(left=left, right=right)


# ─── 字体大小估算 ────────────────────────────────────────


def estimate_font_size(line: OCRLine, page_h: int, base_pt: float = 10.0) -> float:
    """根据 bbox 高度估算字体大小(pt)。"""
    bbox_h = line.bbox[3] - line.bbox[1]
    if bbox_h <= 0 or page_h <= 0:
        return base_pt
    # 典型 PDF 300dpi 下，10pt ≈ 36-40px 高度
    # 以 300dpi 为基准，pt = px * 72 / dpi
    # 但 OCR 返回的坐标已经是缩放后的像素值，我们用相对比例
    ratio = bbox_h / page_h
    # 假设一页 A4 210mm ≈ 2480px @300dpi
    # 10pt 文字高度约 36px, ratio ≈ 36/2480 ≈ 0.0145
    estimated_pt = ratio * 2480 * 72 / 300
    # 限制在合理范围
    estimated_pt = max(base_pt * 0.6, min(estimated_pt, base_pt * 3.0))
    # 四舍五入到 0.5pt
    return round(estimated_pt * 2) / 2


def is_large_text(line: OCRLine, page_h: int) -> bool:
    """判断是否为明显较大的文本（如标题）。"""
    return estimate_font_size(line, page_h) > 12.0


# ─── 对齐方式检测 ────────────────────────────────────────

ALIGN_LEFT = "left"
ALIGN_CENTER = "center"
ALIGN_RIGHT = "right"


def detect_alignment(
    line: OCRLine,
    page_w: int,
    bounds: TextBounds,
    lines_on_page: list[OCRLine],
    page_h: int,
) -> str:
    """
    检测行对齐方式：
    - 短行且居中 → center
    - 行靠近右边界 → right
    - 其余 → left
    """
    line_w = line.bbox[2] - line.bbox[0]
    line_h = line.bbox[3] - line.bbox[1]
    if line_w <= 0 or line_h <= 0:
        return ALIGN_LEFT

    page_span = max(bounds.right - bounds.left, 1)

    # 居中检测：短行（宽度 < 页面 40%）且左右边距大致相等
    left_gap = line.bbox[0] - bounds.left
    right_gap = bounds.right - line.bbox[2]

    is_short_line = line_w / page_span < 0.40
    is_near_center = (
        is_short_line
        and left_gap > page_span * 0.12
        and right_gap > page_span * 0.12
        and abs(left_gap - right_gap) / max(page_span, 1) < 0.15
    )

    # 右对齐检测：紧贴右边界
    is_near_right = right_gap < page_span * 0.05 and left_gap > page_span * 0.25

    if is_near_center and is_large_text(line, page_h):
        return ALIGN_CENTER
    if is_near_right:
        return ALIGN_RIGHT
    if is_short_line and is_near_center:
        return ALIGN_CENTER
    return ALIGN_LEFT


# ─── 加粗估算 ────────────────────────────────────────────


def estimate_is_bold(line: OCRLine, page_w: int) -> bool:
    """根据字符宽度与 bbox 宽度的比值估算是否加粗。"""
    text = line.text.strip()
    if not text:
        return False
    bbox_w = line.bbox[2] - line.bbox[0]
    if bbox_w <= 0:
        return False
    # 粗略：字符数 * 平均字宽 vs bbox 宽度
    # 正常文本：每个字约占 bbox 宽度的 1/字符数
    # 加粗文本：每个字占更宽空间
    avg_char_width = bbox_w / len(text)
    page_ratio = bbox_w / max(page_w, 1)
    # 如果平均字符宽度 > 页面宽度 * 0.06，认为可能是加粗（经验值）
    return avg_char_width / max(page_w, 1) > 0.055


# ─── 原有函数 ────────────────────────────────────────────

def indent_for_line(line: OCRLine, bounds: TextBounds, usable_w_cm: float) -> float:
    span = max(bounds.right - bounds.left, 1)
    ratio = (line.bbox[0] - bounds.left) / span
    ratio = max(0.0, min(ratio, MAX_INDENT_RATIO))
    return round(ratio * usable_w_cm, 2)


def space_before_for_line(prev: OCRLine | None, curr: OCRLine) -> float:
    if prev is None:
        return 0.0
    gap = calc_vertical_gap(prev, curr)
    if gap <= 0:
        return 0.0

    reference_height = max((line_height(prev) + line_height(curr)) / 2, 1)
    gap_ratio = gap / reference_height
    if gap_ratio < 0.45:
        return 0.0
    if gap_ratio < 1.2:
        return 3.0
    return round(min(gap_ratio * 4.0, 18.0), 2)
