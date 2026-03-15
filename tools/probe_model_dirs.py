"""
探针脚本：触发 PaddleOCR 下载 PP-OCRv5_mobile 模型，然后打印目录结构。
只做 mobile 版本以节省时间。

用法：
    .venv/bin/python tools/probe_model_dirs.py
"""
import os
import sys

# 屏蔽下载时的冗余日志
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ["FLAGS_call_stack_level"] = "0"

from pathlib import Path

def show_tree(root: Path, depth: int = 2) -> None:
    if not root.exists():
        print(f"  [不存在] {root}")
        return
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        parts = rel.parts
        if len(parts) > depth:
            continue
        indent = "  " * (len(parts) - 1)
        size = f"  ({p.stat().st_size:,} bytes)" if p.is_file() else ""
        print(f"  {indent}{p.name}{size}")


def main() -> None:
    print("=" * 60)
    print("步骤 1：初始化 PaddleOCR（触发 mobile 模型下载）")
    print("=" * 60)

    from paddleocr import PaddleOCR
    ocr = PaddleOCR(
        text_detection_model_name="PP-OCRv5_mobile_det",
        text_recognition_model_name="PP-OCRv5_mobile_rec",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        lang="ch",
        device="cpu",
    )
    print("初始化完成。\n")

    print("=" * 60)
    print("步骤 2：扫描 ~/.paddlex 目录结构")
    print("=" * 60)
    paddlex_dir = Path.home() / ".paddlex"
    official_dir = paddlex_dir / "official_models"
    show_tree(official_dir, depth=3)

    print("\n" + "=" * 60)
    print("步骤 3：搜索所有 .pdmodel / .pdiparams / .json / .onnx 文件")
    print("=" * 60)
    for ext in ("*.pdmodel", "*.pdiparams", "*.json", "*.onnx", "*.yml", "*.yaml"):
        hits = list(paddlex_dir.rglob(ext))
        if hits:
            print(f"\n[{ext}]")
            for h in hits[:10]:
                print(f"  {h}")


if __name__ == "__main__":
    main()
