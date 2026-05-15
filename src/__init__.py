from dataclasses import dataclass, field


@dataclass
class OCRLine:
    text: str
    score: float
    bbox: tuple[int, int, int, int]
    polygon: list[list[float]]


@dataclass
class PageResult:
    page_num: int
    lines: list[OCRLine] = field(default_factory=list)
    width: int = 0
    height: int = 0
    skip_reason: str = ""
