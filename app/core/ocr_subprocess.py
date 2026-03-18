"""子进程 OCR/结构化解析 — 批量处理 + 并行支持，退出后 OS 回收所有内存。"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import json
import logging
import os
import tempfile
from pathlib import Path

BATCH_SIZE = 20

# ─── 单例进程池 ───
_pool: ProcessPoolExecutor | None = None
_pool_ctx = None


def get_pool(max_workers: int = 2) -> ProcessPoolExecutor:
    """返回或创建单例进程池（spawn context）。"""
    import multiprocessing as mp

    global _pool, _pool_ctx
    if _pool is not None:
        return _pool
    _pool_ctx = mp.get_context("spawn")
    _pool = ProcessPoolExecutor(max_workers=max_workers, mp_context=_pool_ctx)
    _log.info("创建进程池: max_workers=%d", max_workers)
    return _pool


def shutdown_pool() -> None:
    """关闭单例进程池（应用退出时调用）。"""
    global _pool
    if _pool is not None:
        _log.info("关闭进程池")
        _pool.shutdown(wait=False, cancel_futures=True)
        _pool = None

_log = logging.getLogger("paddleocr.ocr_subprocess")


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


def _hide_dock_icon() -> None:
    """macOS: 将子进程标记为后台进程，防止在 Dock 显示额外图标。"""
    import sys
    if sys.platform != "darwin":
        return
    try:
        import AppKit
        AppKit.NSApplication.sharedApplication().setActivationPolicy_(2)
    except (ImportError, AttributeError, RuntimeError):
        pass


def _subprocess_batch_worker(args_json: str) -> str:
    """子进程入口：批量执行 OCR 或结构化解析，返回结果文件路径。"""
    _hide_dock_icon()
    os.environ["OMP_NUM_THREADS"] = "2"
    os.environ["OPENBLAS_NUM_THREADS"] = "2"
    os.environ["MKL_NUM_THREADS"] = "2"
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

    args = json.loads(args_json)
    image_paths = args["image_paths"]
    lang = args["lang"]
    speed_mode = args["speed_mode"]
    pipeline = args["pipeline"]
    options = args.get("options", {})
    out_path = args["out_path"]

    try:
        if pipeline == "structure":
            try:
                from app.core.structure_engine import StructureEngine

                engine = StructureEngine(lang=lang, options=options)
            except ImportError:
                Path(out_path).write_text(json.dumps({
                    "error": "结构化解析（PPStructureV3）需要 PaddlePaddle，当前环境不可用。请使用 TXT/PDF/RTF 格式输出。"
                }))
                return out_path
        else:
            from app.core.onnx_engine import OnnxOCREngine, resolve_ocr_backend

            backend = resolve_ocr_backend(lang, speed_mode)
            if backend == "onnx":
                engine = OnnxOCREngine(lang=lang, speed_mode=speed_mode, options=options)
            else:
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
    """并行多批次执行 OCR 或结构化解析（复用单例进程池）。"""
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

    # 复用单例进程池
    pool = get_pool(max_workers=max(max_workers, 2))
    results_by_batch: list[list[dict]] = []
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
