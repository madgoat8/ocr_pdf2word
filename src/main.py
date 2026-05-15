import argparse
import logging
import time
from pathlib import Path

from src import PageResult
from src.config import load_config
from src.pdf_loader import pdf_to_images, should_skip_page
from src.ocr_engine import OcrEngine
from src.word_writer import write_to_word

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/ocr.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

DEFAULT_CONFIG = "config.yaml"


def main():
    parser = argparse.ArgumentParser(description="扫描PDF手写文档 → Word")
    parser.add_argument("input", type=str, help="输入PDF路径")
    parser.add_argument("-o", "--output", type=str, default="", help="输出Word路径")
    parser.add_argument("--dpi", type=int, default=300, help="PDF导出DPI (默认300)")
    parser.add_argument(
        "-c", "--config", type=str, default=DEFAULT_CONFIG, help="配置文件路径"
    )
    args = parser.parse_args()

    pdf_path = Path(args.input)
    if not pdf_path.exists():
        log.error(f"文件不存在: {pdf_path}")
        return 1

    config = load_config(args.config)

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    output_path = args.output or str(
        output_dir / f"{pdf_path.stem}_ocr.docx"
    )

    total_start = time.time()
    log.info("=" * 50)
    log.info(f"输入: {pdf_path}")
    log.info(f"配置: {args.config}")
    log.info(f"API: {config['api']['base_url']}")
    log.info(f"模型: {config['api']['model_name']}")

    log.info("Step 1/3: PDF → 图片")
    images = pdf_to_images(pdf_path, dpi=args.dpi)
    log.info(f"  -> {len(images)} 页")

    log.info("Step 2/3: VL-OCR 识别")
    ocr = OcrEngine(config)
    page_results: list[PageResult] = []
    for page_num, img in images:
        if should_skip_page(img):
            log.info(f"  Page {page_num}: 跳过 (空白页)")
            pr = PageResult(page_num=page_num)
            pr.skip_reason = "空白页"
            page_results.append(pr)
            continue
        t0 = time.time()
        pr = ocr.process_page(img, page_num)
        elapsed = time.time() - t0
        n = len(pr.lines)
        log.info(f"  Page {page_num}: {n} 行文字, {elapsed:.1f}s")
        page_results.append(pr)

    log.info("Step 3/3: 生成 Word")
    out = write_to_word(page_results, output_path, font_cfg=config.get("font", {}))
    total = time.time() - total_start
    log.info(f"完成: {out}")
    log.info(f"总耗时: {total:.1f}s")
    log.info("=" * 50)


if __name__ == "__main__":
    main()
