#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证脚本：测试修复后的数据管道完整性
1. parse_spotting 函数：验证坐标不全行是否正确保留
2. correct_text 函数：验证纠错映射是否异常删除内容
3. 完整性校验日志验证
"""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

# ============================================================
# 测试 1: parse_spotting 坐标不全保留逻辑
# ============================================================
print("\n" + "=" * 70)
print("测试 1: parse_spotting 坐标不全行保留逻辑")
print("=" * 70)

from src.api_client import parse_spotting

# 测试用例 1: 正常带完整坐标的行
normal_input = "变压器 <|LOC_100|><|LOC_200|><|LOC_300|><|LOC_200|><|LOC_300|><|LOC_400|><|LOC_100|><|LOC_400|>"
results = parse_spotting(normal_input)
assert len(results) == 1, f"正常行应解析出 1 条，实际 {len(results)}"
r_text, r_bbox, _ = results[0]
assert r_text == "变压器", f"文本应为'变压器'，实际为'{r_text}'"
assert r_bbox == (100, 200, 300, 400), f"bbox 应为 (100,200,300,400)，实际为 {r_bbox}"
print("  [PASS] 正常坐标行正确解析 ✓")

# 测试用例 2: 坐标不全的行（只有 4 个坐标值）
partial_input = "缺失坐标文本 <|LOC_50|><|LOC_60|><|LOC_70|><|LOC_80|>"
results = parse_spotting(partial_input)
assert len(results) == 1, f"坐标不全行应解析出 1 条，实际 {len(results)}"
r_text, r_bbox, _ = results[0]
assert r_text == "缺失坐标文本", f"文本应保留，实际为'{r_text}'"
assert r_bbox[0] == 0, f"估算 bbox left 应为 0，实际为 {r_bbox[0]}"
print("  [PASS] 坐标不全行正确保留文本 ✓")

# 测试用例 3: 完全无坐标的行
no_loc_input = "纯文本行\n第二行"
results = parse_spotting(no_loc_input)
assert len(results) == 2, f"无坐标行应解析出 2 条，实际 {len(results)}"
for i, (t, _, _) in enumerate(results):
    assert t in ("纯文本行", "第二行"), f"文本应保留，实际为'{t}'"
print("  [PASS] 无坐标行正确保留文本 ✓")

# 测试用例 4: 混合行（部分有坐标，部分无坐标）
mixed_input = "正常行 <|LOC_0|><|LOC_0|><|LOC_10|><|LOC_0|><|LOC_10|><|LOC_10|><|LOC_0|><|LOC_10|>\n缺失坐标 <|LOC_1|><|LOC_2|>"
results = parse_spotting(mixed_input)
assert len(results) == 2, f"混合行应解析出 2 条，实际 {len(results)}"
assert results[0][0] == "正常行", f"第一行文本应为'正常行'，实际为'{results[0][0]}'"
assert results[1][0] == "缺失坐标", f"第二行文本应为'缺失坐标'，实际为'{results[1][0]}'"
print("  [PASS] 混合行全部正确保留 ✓")

# 测试用例 5: 大量坐标不全行（验证不丢失）
many_lines = "\n".join([f"行{i} <|LOC_{i*10}|><|LOC_{i*10+1}|>" for i in range(100)])
results = parse_spotting(many_lines)
assert len(results) == 100, f"100 行坐标不全行应全部保留，实际 {len(results)}"
print(f"  [PASS] 100 行坐标不全行全部保留 ✓")

# 测试用例 6: 空输入
results = parse_spotting("")
assert len(results) == 0, f"空输入应返回空列表，实际 {len(results)}"
print("  [PASS] 空输入正确处理 ✓")

# 测试用例 7: 坐标值顺序不同的情况（x1,y1,x2,y2 顺序）
swapped_input = "倒序坐标 <|LOC_300|><|LOC_400|><|LOC_100|><|LOC_200|><|LOC_300|><|LOC_200|><|LOC_100|><|LOC_400|>"
results = parse_spotting(swapped_input)
assert len(results) == 1
r_text, r_bbox, _ = results[0]
# 确保 bbox 被正确排序（min/max）
assert r_bbox[0] == 100, f"left 应为 100（最小值），实际为 {r_bbox[0]}"
print(f"  [PASS] 坐标顺序不影响 bbox 计算 ✓ (bbox={r_bbox})")

print("\n[SUMMARY] parse_spotting 全部测试通过！")

# ============================================================
# 测试 2: correct_text 纠错映射测试
# ============================================================
print("\n" + "=" * 70)
print("测试 2: correct_text 纠错映射")
print("=" * 70)

from src.correction import correct_text, set_correction_map

# 加载配置文件中的纠错映射
from src.config import load_config
cfg = load_config("src/config.yaml")
set_correction_map(cfg.get("correction", {}))
print(f"  加载了 {len(cfg.get('correction', {}))} 条纠错规则")

# 测试常见纠错
test_cases = [
    ("D4/T 123", "DL/T 123", "D4/T → DL/T"),
    ("功宰", "功率", "功宰 → 功率"),
    ("跳间", "跳闸", "跳间 → 跳闸"),
    ("正常文本", "正常文本", "正常文本不变"),
    ("电三", "电压", "电三 → 电压"),
    ("药电池", "蓄电池", "药电池 → 蓄电池"),
]
all_pass = True
for input_text, expected, desc in test_cases:
    result = correct_text(input_text)
    if result == expected:
        print(f"  [PASS] {desc}: '{input_text}' → '{result}'")
    else:
        print(f"  [FAIL] {desc}: 期望 '{expected}'，实际 '{result}'")
        all_pass = False

# 验证不会错误删除正常内容
normal_texts = [
    "变压器额定容量",
    "系统标称电压为110V",
    "负荷电流测量值",
    "断路器跳闸信号",
]
for text in normal_texts:
    result = correct_text(text)
    if len(result) < len(text) * 0.5:
        print(f"  [WARN] 内容异常缩短: '{text}' → '{result}'")
        all_pass = False
    elif result == text:
        print(f"  [PASS] 正常内容不变: '{text}'")
    else:
        print(f"  [INFO] 正常内容被纠错: '{text}' → '{result}'")

if all_pass:
    print("\n[SUMMARY] correct_text 测试通过！")
else:
    print("\n[SUMMARY] correct_text 测试发现异常！")

# ============================================================
# 测试 3: API 原始响应解析测试（模拟截断场景）
# ============================================================
print("\n" + "=" * 70)
print("测试 3: 模拟 API 截断响应解析")
print("=" * 70)

# 模拟 ctx-size 截断场景：最后一行坐标不完整
truncated_response = (
    "变压器 <|LOC_0|><|LOC_0|><|LOC_100|><|LOC_0|><|LOC_100|><|LOC_30|><|LOC_0|><|LOC_30|>\n"
    "负荷电流 <|LOC_0|><|LOC_30|><|LOC_100|><|LOC_30|><|LOC_100|><|LOC_60|><|LOC_0|><|LOC_60|>\n"
    "电压测量 <|LOC_50|><|LOC_80|>"  # ← 坐标不全（截断导致）
)
results = parse_spotting(truncated_response)
expected_count = 3  # 应该全部保留
actual_count = len(results)
if actual_count == expected_count:
    print(f"  [PASS] 截断场景：{actual_count}/{expected_count} 行全部保留")
else:
    print(f"  [FAIL] 截断场景：仅保留 {actual_count}/{expected_count} 行")
for text, bbox, _ in results:
    print(f"    文本: '{text}', bbox: {bbox}")

# 模拟超长页面：超过 token 限制时部分行丢失
long_input = "\n".join([f"测试行_{i:04d} <|LOC_0|><|LOC_{i*30}|><|LOC_200|><|LOC_{i*30}|><|LOC_200|><|LOC_{i*30+20}|><|LOC_0|><|LOC_{i*30+20}|>" for i in range(200)])
results = parse_spotting(long_input)
print(f"  200 行长输入: 解析出 {len(results)} 行")
if len(results) == 200:
    print("  [PASS] 全部保留 ✓")
else:
    print(f"  [WARN] 丢失 {200 - len(results)} 行")

# ============================================================
# 汇总
# ============================================================
print("\n" + "=" * 70)
print("验证完成！")
print("=" * 70)
print("\n修复内容清单:")
print("  1. parse_spotting: 坐标不全行改用估算坐标保留文本")
print("  2. max_tokens: 8192 → 3072（匹配服务端 ctx-size 4096）")
print("  3. JPEG quality: 90 → 95")
print("  4. 增加各级日志（空结果、坐标不全、重试信息）")
print("  5. 增加完整性校验日志（行数/字符数）")
sys.exit(0 if all_pass else 1)