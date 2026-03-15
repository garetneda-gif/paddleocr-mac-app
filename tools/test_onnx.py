"""
ONNX 引擎快速测试脚本 — 在终端运行验证速度。

用法：
    cd /Users/jikunren/Documents/paddleocr
    source .venv/bin/activate
    python tools/test_onnx.py [image_path]
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    image_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/fixtures/test_en.png")

    if not image_path.exists():
        print(f"图片不存在: {image_path}")
        sys.exit(1)

    print("=" * 60)
    print("ONNX Runtime OCR 引擎测试")
    print("=" * 60)
    print(f"图片: {image_path}")
    print()

    # 1. 导入
    t0 = time.time()
    from app.core.onnx_engine import OnnxOCREngine, onnx_available
    t_import = time.time() - t0
    print(f"模块导入: {t_import:.2f}s")
    print(f"Mobile 可用: {onnx_available('mobile')}")
    print(f"Server 可用: {onnx_available('server')}")

    for mode in ["mobile", "server"]:
        if not onnx_available(mode):
            print(f"\n跳过 {mode}（模型不可用）")
            continue

        print(f"\n--- {mode.upper()} 模式 ---")

        t1 = time.time()
        engine = OnnxOCREngine(speed_mode=mode)
        result = engine.predict(image_path)
        elapsed = time.time() - t1

        block_count = len(result.pages[0].blocks) if result.pages else 0
        print(f"推理耗时: {elapsed:.2f}s")
        print(f"识别块数: {block_count}")
        print(f"纯文本长度: {len(result.plain_text)}")
        print()

        for i, block in enumerate(result.pages[0].blocks if result.pages else []):
            bbox = tuple(round(v) for v in block.bbox)
            print(f"  [{i+1}] conf={block.confidence:.3f} bbox={bbox}")
            print(f"       {block.text!r}")

    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
