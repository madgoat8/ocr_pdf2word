from dataclasses import dataclass, field


@dataclass
class OCRLine:
    text: str
    score: float
    bbox: tuple[int, int, int, int]
    polygon: list[list[float]]


@dataclass
class CellData:
    text: str = ""
    bbox: tuple = (0, 0, 0, 0)
    row: int = 0
    col: int = 0
    rowspan: int = 1
    colspan: int = 1


@dataclass
class TableData:
    cells: list[list[CellData]] = field(default_factory=list)
    bbox: tuple = (0, 0, 0, 0)
    num_rows: int = 0
    num_cols: int = 0
    page_num: int = 0


@dataclass
class PageResult:
    page_num: int
    lines: list[OCRLine] = field(default_factory=list)
    tables: list[TableData] = field(default_factory=list)
    width: int = 0
    height: int = 0
    skip_reason: str = ""
