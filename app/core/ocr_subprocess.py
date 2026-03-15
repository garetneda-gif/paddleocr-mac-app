"""子进程 OCR/结构化解析 — 批量处理 + 并行支持，退出后 OS 回收所有内存。"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import json
import os
import tempfile
from pathlib import Path

BATCH_SIZE = 20


def _safe_temp_path(*, suffix: str, prefix: str) -> Path:
    fd, name = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    os.close(fd)
    return Path(name)


def _serialize_document_result(result) -> dict[str, object]:
    pages: list[dict[str, object]] = []
    for page in result.pages:
        blocks: list[dict[str, object]] = []
        for block in page.blocks:
            blocks.append(
                {
                    "block_type": block.block_type.value,
                    "bbox": [float(v) for v in block.bbox],
                    "text": block.text,
                    "confidence": block.confidence,
                    "html": block.html,
                    "markdown": block.markdown,
                    "table_cells": block.table_cells,
                }
            )
        pages.append(
            {
                "width": page.width,
                "height": page.height,
                "blocks": blocks,
            }
        )
    return {
        "plain_text": result.plain_text,
        "pages": pages,
    }


def _subprocess_batch_worker(args_json: str) -> str:
    """子进程入口：批量执行 OCR 或结构化解析，返回结果文件路径。"""
    os.environ["OMP_NUM_THREADS"] = "2"
    os.environ["OPENBLAS_NUM_THREADS"] = "2"
    os.environ["MKL_NUM_THREADS"] = "2"
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

    args = json.loads(args_json)
    image_paths = args["image_paths"]
    lang = args["lang"]
    speed_mode = args["speed_mode"]
    pipeline = args["pipeline"]
    options = args.get("options", {})
    out_path = args["out_path"]

    try:
        if pipeline == "structure":
            from app.core.structure_engine import StructureEngine

            engine = StructureEngine(lang=lang, options=options)
        else:
            # 优先 ONNX 引擎（无需 PaddlePaddle，更快更省内存）
            engine = None
            try:
                from app.core.onnx_engine import OnnxOCREngine, onnx_available

                if onnx_available(speed_mode):
                    engine = OnnxOCREngine(lang=lang, speed_mode=speed_mode, options=options)
            except Exception:
                pass

            if engine is None:
                from app.core.ocr_engine import OCREngine

                engine = OCREngine(lang=lang, speed_mode=speed_mode, options=options)

        all_results = []
        for img_path in image_paths:
            result = engine.predict(Path(img_path))
            all_results.append(_serialize_document_result(result))

        Path(out_path).write_text(json.dumps(all_results, ensure_ascii=False))
    except Exception as e:
        Path(out_path).write_text(json.dumps({"error": str(e)}))

    return out_path


def run_ocr_batch(image_paths: list[Path], lang: str, speed_mode: str) -> list[dict]:
    """单批次子进程 OCR（兼容旧接口）。"""
    return run_pipeline_parallel(
        [image_paths],
        lang=lang,
        speed_mode=speed_mode,
        pipeline="ocr",
        options={},
        max_workers=1,
    )[0]


def run_pipeline_parallel(
    batches: list[list[Path]],
    *,
    lang: str,
    speed_mode: str,
    pipeline: str,
    options: dict[str, object] | None = None,
    max_workers: int = 2,
) -> list[list[dict]]:
    """并行多批次执行 OCR 或结构化解析。"""
    import multiprocessing as mp

    # 准备每个批次的参数
    task_args = []
    for batch in batches:
        out_path = str(_safe_temp_path(suffix=".json", prefix="pocr_res_"))
        args = {
            "image_paths": [str(p) for p in batch],
            "lang": lang,
            "speed_mode": speed_mode,
            "pipeline": pipeline,
            "options": options or {},
            "out_path": out_path,
        }
        task_args.append(json.dumps(args, ensure_ascii=False))

    # 用 spawn context 的 ProcessPoolExecutor 并行执行
    ctx = mp.get_context("spawn")
    results_by_batch: list[list[dict]] = []

    with ProcessPoolExecutor(
        max_workers=min(max_workers, len(batches)),
        mp_context=ctx,
    ) as pool:
        futures = list(pool.map(_subprocess_batch_worker, task_args, timeout=600))

    for out_path in futures:
        p = Path(out_path)
        if not p.exists():
            results_by_batch.append([{"error": "子进程未产生结果"}])
            continue
        raw = json.loads(p.read_text())
        p.unlink(missing_ok=True)
        if isinstance(raw, dict) and "error" in raw:
            results_by_batch.append([raw])
        else:
            results_by_batch.append(raw)

    return results_by_batch


def run_ocr_parallel(
    batches: list[list[Path]], lang: str, speed_mode: str, max_workers: int = 2
) -> list[list[dict]]:
    """兼容旧接口。"""
    return run_pipeline_parallel(
        batches,
        lang=lang,
        speed_mode=speed_mode,
        pipeline="ocr",
        options={},
        max_workers=max_workers,
    )
