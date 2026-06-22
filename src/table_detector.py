"""
表格检测模块

支持两种方式检测 PDF 中的表格：
1. PyMuPDF 原生表格提取（适用于有文本层的数字 PDF）
2. OCR 坐标空间分析（适用于扫描件，通过 OCR 文本位置推测表格结构）
"""
import logging
from statistics import median

from src import OCRLine, CellData, TableData

log = logging.getLogger(__name__)

# ─── 空间分析表格检测（扫描件备用） ─────────────────────


def _line_center_y(line) -> float:
    return (line.bbox[1] + line.bbox[3]) / 2


def _line_center_x(line) -> float:
    return (line.bbox[0] + line.bbox[2]) / 2


def _overlap_1d(a1, a2, b1, b2) -> float:
    """一维重叠长度"""
    return max(0.0, min(a2, b2) - max(a1, b1))


def _iou_y(line_a, line_b) -> float:
    """两个 line 在 y 轴上的 IoU"""
    a1, a2 = line_a.bbox[1], line_a.bbox[3]
    b1, b2 = line_b.bbox[1], line_b.bbox[3]
    overlap = _overlap_1d(a1, a2, b1, b2)
    union = max(a2, b2) - min(a1, b1)
    if union <= 0:
        return 0.0
    return overlap / union


def _group_into_rows(lines: list[OCRLine]) -> list[list[OCRLine]]:
    """按 y 坐标将 OCR lines 分组为行"""
    if not lines:
        return []
    ordered = sorted(lines, key=lambda ln: (_line_center_y(ln), ln.bbox[0]))
    heights = [ln.bbox[3] - ln.bbox[1] for ln in ordered]
    avg_h = median(heights) if heights else 20
    threshold = max(avg_h * 0.6, 6.0)

    rows: list[list[OCRLine]] = []
    row_centers: list[float] = []
    for ln in ordered:
        cy = _line_center_y(ln)
        if rows and abs(cy - row_centers[-1]) <= threshold:
            rows[-1].append(ln)
            # 更新行中心为平均值
            cy_list = [_line_center_y(x) for x in rows[-1]]
            row_centers[-1] = sum(cy_list) / len(cy_list)
        else:
            rows.append([ln])
            row_centers.append(cy)

    # 每行内按 x 排序
    for row in rows:
        row.sort(key=lambda ln: ln.bbox[0])
    return rows


def _detect_column_boundaries(
    rows: list[list[OCRLine]], page_w: int, page_h: int
) -> list[float]:
    """
    检测列边界位置。
    策略：对每一行检测文本块之间的 gap，统计所有 gap 位置，
    找出多行共有的 gap → 视为列边界。
    返回 x 坐标列表（按升序排序，包含 0 和 page_w 作为起止）。
    """
    if not rows or len(rows) < 2:
        return [0.0, float(page_w)]

    # 对每一行，收集文本块间隙位置
    # 间隙 = 前一个 block 的右边界到后一个 block 的左边界
    min_gap = page_w * 0.01  # 最小间隙宽度（1% 页宽）
    row_gap_positions: list[list[tuple[float, float]]] = []  # per row: list of (gap_center, gap_size)

    for row in rows:
        if len(row) < 2:
            continue
        gaps = []
        for i in range(len(row) - 1):
            gap_start = row[i].bbox[2]
            gap_end = row[i + 1].bbox[0]
            gap_size = gap_end - gap_start
            if gap_size >= min_gap:
                gaps.append(((gap_start + gap_end) / 2, gap_size))
        if gaps:
            row_gap_positions.append(gaps)

    if len(row_gap_positions) < 2:
        return [0.0, float(page_w)]

    # 统计 gap 位置是否被多行共享
    # 对每个 gap 位置，检查多少行在附近（±tolerance）也有 gap
    tolerance = page_w * 0.015  # 容忍度
    column_boundaries = [0.0, float(page_w)]
    all_gap_centers = []
    for gaps in row_gap_positions:
        for center, _ in gaps:
            all_gap_centers.append(center)

    # 聚类：找出被多行共享的 gap 位置
    used = set()
    for i, c1 in enumerate(all_gap_centers):
        if i in used:
            continue
        cluster = [c1]
        used.add(i)
        for j in range(i + 1, len(all_gap_centers)):
            if j in used:
                continue
            if abs(c1 - all_gap_centers[j]) <= tolerance:
                cluster.append(all_gap_centers[j])
                used.add(j)
        # 至少来自不同行的 3 个 gap 则认为是一个列边界
        # 简单判断：cluster 大小 >= 3
        if len(cluster) >= 3:
            boundary = sum(cluster) / len(cluster)
            column_boundaries.append(boundary)

    column_boundaries.sort()
    # 去重：移除相距太近的边界
    deduped = [column_boundaries[0]]
    for b in column_boundaries[1:]:
        if b - deduped[-1] > tolerance:
            deduped.append(b)
    return deduped


def _build_table_from_grid(
    rows: list[list[OCRLine]],
    boundaries: list[float],
    page_num: int,
) -> TableData | None:
    """根据行分组和列边界构建 TableData"""
    if len(rows) < 2 or len(boundaries) < 3:
        return None  # 至少 2 行 2 列

    num_rows = len(rows)
    num_cols = len(boundaries) - 1
    if num_cols < 2:
        return None

    cells: list[list[CellData]] = []
    bbox_x1, bbox_y1 = float("inf"), float("inf")
    bbox_x2, bbox_y2 = float("-inf"), float("-inf")

    for ri, row_lines in enumerate(rows):
        row_cells = []
        for ci in range(num_cols):
            col_x1 = boundaries[ci]
            col_x2 = boundaries[ci + 1]
            col_cx = (col_x1 + col_x2) / 2

            # 查找落在该列区域内的文本
            cell_text_parts = []
            cell_bbox = None
            for ln in row_lines:
                ln_cx = _line_center_x(ln)
                ln_x1 = ln.bbox[0]
                ln_x2 = ln.bbox[2]
                # 判断文本是否在该列范围内
                overlap = _overlap_1d(ln_x1, ln_x2, col_x1, col_x2)
                if overlap > 0 and overlap >= (ln_x2 - ln_x1) * 0.3:
                    cell_text_parts.append(ln.text)
                    if cell_bbox is None:
                        cell_bbox = list(ln.bbox)
                    else:
                        cell_bbox[0] = min(cell_bbox[0], ln.bbox[0])
                        cell_bbox[1] = min(cell_bbox[1], ln.bbox[1])
                        cell_bbox[2] = max(cell_bbox[2], ln.bbox[2])
                        cell_bbox[3] = max(cell_bbox[3], ln.bbox[3])

            text = " ".join(cell_text_parts) if cell_text_parts else ""
            cb = tuple(cell_bbox) if cell_bbox else (int(col_x1), 0, int(col_x2), 0)
            row_cells.append(CellData(text=text, bbox=cb, row=ri, col=ci))

            if cell_bbox:
                bbox_x1 = min(bbox_x1, cell_bbox[0])
                bbox_y1 = min(bbox_y1, cell_bbox[1])
                bbox_x2 = max(bbox_x2, cell_bbox[2])
                bbox_y2 = max(bbox_y2, cell_bbox[3])

        cells.append(row_cells)

    bbox = (int(bbox_x1), int(bbox_y1), int(bbox_x2), int(bbox_y2))

    # 检查是否有足够的填充单元格（至少 1/3 的单元格有内容）
    filled = sum(1 for row in cells for c in row if c.text.strip())
    total = num_rows * num_cols
    if total == 0 or filled / total < 0.2:
        return None

    return TableData(
        cells=cells,
        bbox=bbox,
        num_rows=num_rows,
        num_cols=num_cols,
        page_num=page_num,
    )


def detect_tables_spatial(
    lines: list[OCRLine], page_w: int, page_h: int, page_num: int
) -> list[TableData]:
    """
    基于 OCR 坐标空间分析的表格检测，用于扫描件/无文本层 PDF。

    Args:
        lines: OCR 识别行列表
        page_w: 页面宽度(px)
        page_h: 页面高度(px)
        page_num: 页码

    Returns:
        检测到的表格列表
    """
    if len(lines) < 6:  # 行数太少，不可能成表
        return []

    # 1. 按 y 分组为行
    rows = _group_into_rows(lines)
    if len(rows) < 3:  # 至少 3 行才可能是表
        return []

    log.debug("  Table spatial: %d 行分组为 %d 行", len(lines), len(rows))

    # 2. 检测列边界
    boundaries = _detect_column_boundaries(rows, page_w, page_h)
    if len(boundaries) < 3:
        return []

    # 3. 构建表格
    table = _build_table_from_grid(rows, boundaries, page_num)
    if table is None:
        return []

    log.info(
        "  Table spatial: 检测到 %d×%d 表格 (bbox: %s)",
        table.num_rows, table.num_cols, table.bbox,
    )
    return [table]


# ─── PyMuPDF 原生表格提取 ──────────────────────────────


def _overlap_iou(
    x1: float, y1: float, x2: float, y2: float,
    bx1: float, by1: float, bx2: float, by2: float,
) -> float:
    """计算两个 bbox 的 IoU"""
    ix1 = max(x1, bx1)
    iy1 = max(y1, by1)
    ix2 = min(x2, bx2)
    iy2 = min(y2, by2)
    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)
    if iw <= 0 or ih <= 0:
        return 0.0
    inter = iw * ih
    area_a = (x2 - x1) * (y2 - y1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter
    if union <= 0:
        return 0.0
    return inter / union


def _match_ocr_text(ocr_lines: list[OCRLine], cell_bbox: tuple) -> str:
    """将 OCR 文本匹配到表格单元格区域（IoU 最大且 > 阈值）"""
    best_text = ""
    best_iou = 0.0
    cx1, cy1, cx2, cy2 = cell_bbox

    for ln in ocr_lines:
        lx1, ly1, lx2, ly2 = ln.bbox
        iou = _overlap_iou(lx1, ly1, lx2, ly2, cx1, cy1, cx2, cy2)
        if iou > best_iou and iou > 0.15:
            best_iou = iou
            best_text = ln.text

    return best_text


def _match_ocr_lines_to_cell(ocr_lines: list[OCRLine], cell_bbox: tuple) -> str:
    """将多个 OCR lines 匹配到同一单元格（用于合并多行文本）"""
    parts = []
    cx1, cy1, cx2, cy2 = cell_bbox
    for ln in ocr_lines:
        lx1, ly1, lx2, ly2 = ln.bbox
        overlap_x = _overlap_1d(lx1, lx2, cx1, cx2)
        overlap_y = _overlap_1d(ly1, ly2, cy1, cy2)
        if overlap_x > 0 and overlap_y > (ly2 - ly1) * 0.5:
            parts.append(ln.text)
    return " ".join(parts)


def detect_tables_from_pdf(
    page, ocr_lines: list[OCRLine], page_num: int
) -> list[TableData]:
    """
    使用 PyMuPDF 原生表格检测（仅适用于有文本层的数字 PDF）。

    Args:
        page: fitz.Page 对象
        ocr_lines: OCR 识别行列表（用于补充/替换 PDF 文本）
        page_num: 页码

    Returns:
        检测到的表格列表
    """
    try:
        tables = page.find_tables()
    except Exception as exc:
        log.debug("  Page %d: PyMuPDF find_tables() 失败: %s", page_num, exc)
        return []

    result = []
    table_list = list(tables)
    if not table_list:
        return []

    for table in table_list:
        cells_text: list[list[CellData]] = []
        for ri, row in enumerate(table.cells):
            row_cells = []
            for ci, cell in enumerate(row):
                # PyMuPDF 的 cell.bbox 格式: (x0, y0, x1, y1)
                cell_bbox = cell.bbox
                # 获取 PDF 文本
                pdf_text = cell.text.strip()
                # 优先使用 OCR 文本（更准确，特别是手写体）
                ocr_text = _match_ocr_lines_to_cell(ocr_lines, cell_bbox)
                final_text = ocr_text if ocr_text else pdf_text

                # 处理合并单元格
                rowspan = 1
                colspan = 1
                # PyMuPDF 不直接暴露 rowspan/colspan，但我们可以通过位置推断
                # 如果单元格跨越了多行/多列的边界，则可能是合并单元格
                # 简化处理：暂时不处理合并单元格

                row_cells.append(CellData(
                    text=final_text,
                    bbox=cell_bbox,
                    row=ri,
                    col=ci,
                    rowspan=rowspan,
                    colspan=colspan,
                ))
            cells_text.append(row_cells)

        # 获取表格整体 bbox
        table_bbox = table.bbox if hasattr(table, "bbox") else (
            cells_text[0][0].bbox[0] if cells_text and cells_text[0] else 0,
            cells_text[0][0].bbox[1] if cells_text and cells_text[0] else 0,
            cells_text[-1][-1].bbox[2] if cells_text and cells_text[-1] else 0,
            cells_text[-1][-1].bbox[3] if cells_text and cells_text[-1] else 0,
        )

        num_rows = len(cells_text)
        num_cols = len(cells_text[0]) if cells_text else 0

        if num_rows < 2 or num_cols < 2:
            continue

        result.append(TableData(
            cells=cells_text,
            bbox=table_bbox,
            num_rows=num_rows,
            num_cols=num_cols,
            page_num=page_num,
        ))

        log.info(
            "  Page %d: PyMuPDF 检测到 %d×%d 表格",
            page_num, num_rows, num_cols,
        )

    return result


# ─── 统一的表格检测入口 ────────────────────────────────


def detect_tables(
    page,  # fitz.Page | None
    ocr_lines: list[OCRLine],
    page_w: int,
    page_h: int,
    page_num: int,
    prefer_pymupdf: bool = True,
) -> list[TableData]:
    """
    统一的表格检测入口。
    
    优先使用 PyMuPDF 原生检测，若无结果则降级为空间分析。

    Args:
        page: fitz.Page 对象（可为 None）
        ocr_lines: OCR 识别行
        page_w: 页面宽度(px)
        page_h: 页面高度(px)
        page_num: 页码
        prefer_pymupdf: 是否优先使用 PyMuPDF

    Returns:
        检测到的表格列表
    """
    tables: list[TableData] = []

    if prefer_pymupdf and page is not None:
        tables = detect_tables_from_pdf(page, ocr_lines, page_num)

    if not tables:
        tables = detect_tables_spatial(ocr_lines, page_w, page_h, page_num)

    return tables