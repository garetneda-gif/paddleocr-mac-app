"""
阶段 1 垂直切片 POC
验证内容：
  1. PaddleOCR (PP-OCRv5) 单图推理 -> 控制台输出 + TXT 文件
  2. PPStructureV3 单图推理 -> 控制台输出结构化结果
  3. 确认 bbox 格式（xyxy 像素坐标）

用法：
  source .venv/bin/activate
  python poc/poc_ocr.py [image_path]

  若未提供 image_path，自动使用 tests/fixtures/test_en.png
"""

import sys
import time
import os
from pathlib import Path

# 抑制 paddlepaddle 的部分警告
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

REPO_ROOT = Path(__file__).parent.parent
TEST_IMG = REPO_ROOT / "tests" / "fixtures" / "test_en.png"


def bbox_from_polygon(polygon: list) -> tuple[float, float, float, float]:
    """将 PaddleOCR 原始多边形坐标转为 xyxy 轴对齐矩形（最小外接矩形）。"""
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return (min(xs), min(ys), max(xs), max(ys))


def run_ocr_pipeline(image_path: Path) -> None:
    """验证 PaddleOCR (PP-OCRv5) pipeline。"""
    from paddleocr import PaddleOCR

    print("\n" + "=" * 60)
    print("Pipeline 1: PaddleOCR (PP-OCRv5)")
    print("=" * 60)

    t0 = time.time()
    ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        lang="en",
    )
    print(f"  模型初始化耗时: {time.time() - t0:.2f}s")

    t1 = time.time()
    results = ocr.predict(str(image_path))
    print(f"  推理耗时: {time.time() - t1:.2f}s")

    # results 是一个列表，每个元素对应一页
    lines = []
    block_count = 0
    for page_result in results:
        if page_result is None:
            continue
        # PaddleOCR 3.x 返回 OCRResult 对象，通过 dict 接口访问
        # 实际 keys: rec_texts, rec_scores, dt_polys, rec_boxes(xyxy)
        rec_texts = page_result.get("rec_texts", [])
        rec_scores = page_result.get("rec_scores", [])
        # rec_boxes 是 [x1,y1,x2,y2] 格式（已是轴对齐矩形），优先使用
        rec_boxes = page_result.get("rec_boxes", [])
        # 若无 rec_boxes，从 dt_polys 多边形计算最小外接矩形
        dt_polys = page_result.get("dt_polys", [])

        print(f"\n  识别到 {len(rec_texts)} 个文本块：")
        for i, (text, score) in enumerate(zip(rec_texts, rec_scores)):
            if i < len(rec_boxes) and rec_boxes[i] is not None:
                b = rec_boxes[i]
                bbox = (float(b[0]), float(b[1]), float(b[2]), float(b[3]))
            elif i < len(dt_polys) and dt_polys[i] is not None:
                bbox = bbox_from_polygon(dt_polys[i])
            else:
                bbox = (0.0, 0.0, 0.0, 0.0)
            print(f"    [{i+1}] conf={score:.3f} bbox={tuple(round(v) for v in bbox)} | {text!r}")
            lines.append(text)
            block_count += 1

    # 写出 TXT 文件
    out_txt = image_path.parent / (image_path.stem + "_ocr.txt")
    out_txt.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  TXT 输出: {out_txt}")
    print(f"  共 {block_count} 个文本块，{len(lines)} 行")


def run_structure_pipeline(image_path: Path) -> None:
    """验证 PPStructureV3 pipeline。"""
    from paddleocr import PPStructureV3

    print("\n" + "=" * 60)
    print("Pipeline 2: PPStructureV3")
    print("=" * 60)

    t0 = time.time()
    pipeline = PPStructureV3(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        lang="en",
    )
    print(f"  模型初始化耗时: {time.time() - t0:.2f}s")

    t1 = time.time()
    results = pipeline.predict(str(image_path))
    print(f"  推理耗时: {time.time() - t1:.2f}s")

    # 输出原始结果的 key 结构
    for i, page_result in enumerate(results):
        if page_result is None:
            continue
        print(f"\n  第 {i} 页结果 keys: {list(page_result.keys())}")
        print(f"  页面尺寸: {page_result.get('width')}x{page_result.get('height')}")

        # 版面检测结果
        layout_det = page_result.get("layout_det_res")
        if layout_det:
            boxes = layout_det.get("boxes", [])
            print(f"  layout_det_res 区域数: {len(boxes)}")
            for j, box in enumerate(boxes[:8]):
                label = box.get("label", "?")
                score = box.get("score", 0)
                coord = box.get("coordinate", [])
                print(f"    [{j}] label={label!r} score={score:.3f} coord={coord}")

        # 整体 OCR 结果
        ocr_res = page_result.get("overall_ocr_res")
        if ocr_res:
            texts = ocr_res.get("rec_texts", [])
            print(f"  overall_ocr_res 文本块数: {len(texts)}")
            for j, t in enumerate(texts[:5]):
                print(f"    [{j}] {t!r}")

        # 结构化解析结果
        parsing_res = page_result.get("parsing_res_list", [])
        if parsing_res:
            print(f"  parsing_res_list 块数: {len(parsing_res)}")
            for j, block in enumerate(parsing_res[:8]):
                if isinstance(block, dict):
                    print(f"    [{j}] keys={list(block.keys())}")
                    block_type = block.get("block_type", block.get("type", "unknown"))
                    text = block.get("text", "")
                    bbox_raw = block.get("bbox", block.get("coordinate", []))
                    print(f"         type={block_type!r} bbox={bbox_raw} text={text[:80]!r}")
                else:
                    print(f"    [{j}] type={type(block).__name__}: {str(block)[:120]}")

        # 表格结果
        table_res = page_result.get("table_res_list", [])
        if table_res:
            print(f"  table_res_list 表格数: {len(table_res)}")
            for j, tbl in enumerate(table_res[:3]):
                if isinstance(tbl, dict):
                    print(f"    [{j}] keys={list(tbl.keys())}")
                    html = tbl.get("html", "")
                    if html:
                        print(f"         html 长度={len(html)}, 前100字: {html[:100]!r}")

        # 公式结果
        formula_res = page_result.get("formula_res_list", [])
        if formula_res:
            print(f"  formula_res_list 公式数: {len(formula_res)}")

    print("\n  （结构化结果探查完毕）")


def main():
    image_path = Path(sys.argv[1]) if len(sys.argv) > 1 else TEST_IMG

    if not image_path.exists():
        print(f"错误：图片不存在: {image_path}")
        sys.exit(1)

    print(f"输入图片: {image_path}")
    print(f"图片大小: {image_path.stat().st_size / 1024:.1f} KB")

    run_ocr_pipeline(image_path)
    run_structure_pipeline(image_path)

    print("\n" + "=" * 60)
    print("阶段 1 POC 完成：两条 pipeline 均可运行。")
    print("=" * 60)


if __name__ == "__main__":
    main()
