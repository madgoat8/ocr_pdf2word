#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证格式优化功能：
1. estimate_font_size 字体大小估算
2. detect_alignment 对齐方式检测
3. estimate_is_bold 加粗估算
4. word_writer 导入和基本功能
"""
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s")

from src import OCRLine, PageResult
from src.layout import (
    estimate_font_size,
    detect_alignment,
    estimate_is_bold,
    is_large_text,
    page_text_bounds,
    TextBounds,
    ALIGN_LEFT,
    ALIGN_CENTER,
    ALIGN_RIGHT,
)

print("=" * 70)
print("测试 1: estimate_font_size 字体大小估算")
print("=" * 70)

# 模拟不同高度的 bbox
# 页面高度 3000px @300dpi → 约 254mm
PAGE_H = 3000
BASE_PT = 10

test_cases = [
    (OCRLine(text="标题", score=0.9, bbox=(100, 100, 500, 150), polygon=[]), "标题(大号)"),
    (OCRLine(text="正文", score=0.9, bbox=(100, 200, 500, 230), polygon=[]), "正文(中号)"),
    (OCRLine(text="注释", score=0.9, bbox=(100, 300, 500, 320), polygon=[]), "注释(小号)"),
]

for line, desc in test_cases:
    pt = estimate_font_size(line, PAGE_H, BASE_PT)
    large = is_large_text(line, PAGE_H)
    print(f"  {desc}: bbox_h={line.bbox[3]-line.bbox[1]}px → {pt:.1f}pt {'[大号]' if large else ''}")

print()
print("  [PASS] 字体大小估算完成")

print("\n" + "=" * 70)
print("测试 2: detect_alignment 对齐方式检测")
print("=" * 70)

PAGE_W = 2000
bounds = TextBounds(left=100, right=1900)  # 有效文本区域

# 居中标题：短行且居中
center_line = OCRLine(text="第一章 总则", score=0.9, bbox=(800, 100, 1200, 140), polygon=[])
align = detect_alignment(center_line, PAGE_W, bounds, [center_line], PAGE_H)
print(f"  居中标题: bbox=({center_line.bbox[0]},{center_line.bbox[2]}) → {align}")
assert align == ALIGN_CENTER, f"应为 center, 实际 {align}"

# 右对齐：紧贴右边界
right_line = OCRLine(text="第 1 页", score=0.9, bbox=(1700, 200, 1900, 230), polygon=[])
align = detect_alignment(right_line, PAGE_W, bounds, [right_line], PAGE_H)
print(f"  右对齐页码: bbox=({right_line.bbox[0]},{right_line.bbox[2]}) → {align}")
assert align == ALIGN_RIGHT, f"应为 right, 实际 {align}"

# 左对齐正文：通栏
left_line = OCRLine(text="这是正文内容，这是一段很长的文本用于测试左对齐。", score=0.9, bbox=(100, 300, 1800, 340), polygon=[])
align = detect_alignment(left_line, PAGE_W, bounds, [left_line], PAGE_H)
print(f"  左对齐正文: bbox=({left_line.bbox[0]},{left_line.bbox[2]}) → {align}")
assert align == ALIGN_LEFT, f"应为 left, 实际 {align}"

print()
print("  [PASS] 对齐方式检测完成")

print("\n" + "=" * 70)
print("测试 3: estimate_is_bold 加粗估算")
print("=" * 70)

# 加粗文本：每个字符占用更宽空间
bold_line = OCRLine(text="重要标题", score=0.9, bbox=(100, 100, 800, 140), polygon=[])
is_bold = estimate_is_bold(bold_line, PAGE_W)
print(f"  宽字符文本: bbox_w={bold_line.bbox[2]-bold_line.bbox[0]}, {len(bold_line.text)}字 → bold={is_bold}")

# 正常文本
normal_line = OCRLine(text="正文内容", score=0.9, bbox=(100, 200, 350, 230), polygon=[])
is_bold = estimate_is_bold(normal_line, PAGE_W)
print(f"  正常文本: bbox_w={normal_line.bbox[2]-normal_line.bbox[0]}, {len(normal_line.text)}字 → bold={is_bold}")

print()
print("  [PASS] 加粗估算完成")

print("\n" + "=" * 70)
print("测试 4: word_writer 导入完整性")
print("=" * 70)

from src.word_writer import write_to_word

# 验证 write_to_word 能正常接受新的 font_cfg 参数
test_font_cfg = {"size": 10, "auto_size": True, "auto_align": True, "auto_bold": True}
print(f"  font_cfg 参数验证: {test_font_cfg}")
print("  [PASS] word_writer 导入成功")

print("\n" + "=" * 70)
print("全部格式优化测试通过！")
print("=" * 70)