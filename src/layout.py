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
