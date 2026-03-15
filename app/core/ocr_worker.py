"""OCR 后台工作线程 — 按 pipeline 分流并在子进程中分批处理。"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.core.ocr_subprocess import BATCH_SIZE
from app.models import BlockResult, BlockType, DocumentResult, PageResult
from app.models.enums import OutputFormat
from app.models.job import OCRJob

_WORKER_STACK_SIZE = 64 * 1024 * 1024


def _get_adv(job: OCRJob, key: str, default=None):
    return job._adv_params.get(key, default)


def _auto_dpi(page_count: int, user_dpi: int) -> int:
    if page_count <= 50:
        return user_dpi
    if page_count > 200:
        return min(user_dpi, 100)
    return min(user_dpi, 150)


def _resolve_pipeline(job: OCRJob) -> str:
    from app.core.onnx_engine import paddle_available

    pipeline = _get_adv(job, "pipeline", "auto")
    if pipeline == "ocr":
        return "ocr"
    if pipeline == "structure":
        return "structure" if paddle_available() else "ocr"

    # auto 模式
    if job.output_format in (OutputFormat.WORD, OutputFormat.HTML, OutputFormat.EXCEL):
        return "structure" if paddle_available() else "ocr"
    if job.preserve_layout and job.output_format in (OutputFormat.TXT, OutputFormat.RTF):
        return "structure" if paddle_available() else "ocr"
    return "ocr"


def _resolve_page_range(job: OCRJob, total: int) -> tuple[int, int]:
    if total <= 0:
        return 0, 0

    page_start = max(1, int(_get_adv(job, "page_start", 1)))
    page_end = int(_get_adv(job, "page_end", total))

    if page_start > total:
        raise ValueError(f"起始页超出总页数：{page_start} > {total}")

    page_end = min(total, page_end)
    if page_end < page_start:
        raise ValueError(f"页码范围无效：{page_start} - {page_end}")

    return page_start - 1, page_end


def _ocr_options(job: OCRJob) -> dict[str, object]:
    return {
        "use_doc_orientation_classify": _get_adv(job, "use_doc_orientation_classify", False),
        "use_doc_unwarping": _get_adv(job, "use_doc_unwarping", False),
        "use_textline_orientation": _get_adv(job, "use_textline_orientation", False),
        "text_det_limit_side_len": _get_adv(job, "text_det_limit_side_len"),
        "text_det_limit_type": _get_adv(job, "text_det_limit_type"),
        "text_det_thresh": _get_adv(job, "text_det_thresh"),
        "text_det_box_thresh": _get_adv(job, "text_det_box_thresh"),
        "text_det_unclip_ratio": _get_adv(job, "text_det_unclip_ratio"),
        "text_recognition_batch_size": _get_adv(job, "text_recognition_batch_size"),
        "text_rec_score_thresh": _get_adv(job, "text_rec_score_thresh"),
        "return_word_box": _get_adv(job, "return_word_box", False),
    }


def _structure_options(job: OCRJob, speed_mode: str) -> dict[str, object]:
    options = _ocr_options(job)
    if speed_mode == "mobile":
        options.update(
            {
                "text_detection_model_name": "PP-OCRv5_mobile_det",
                "text_recognition_model_name": "PP-OCRv5_mobile_rec",
            }
        )
    options.update(
        {
            "use_table_recognition": _get_adv(job, "use_table_recognition", True),
            "use_formula_recognition": _get_adv(job, "use_formula_recognition", True),
            "use_chart_recognition": _get_adv(job, "use_chart_recognition", True),
            "use_seal_recognition": _get_adv(job, "use_seal_recognition", True),
            "use_region_detection": _get_adv(job, "use_region_detection", True),
            "layout_threshold": _get_adv(job, "layout_threshold"),
            "layout_nms": _get_adv(job, "layout_nms"),
            "layout_unclip_ratio": _get_adv(job, "layout_unclip_ratio"),
            "layout_merge_bboxes_mode": _get_adv(job, "layout_merge_bboxes_mode"),
            "seal_det_thresh": _get_adv(job, "seal_det_thresh"),
            "seal_det_box_thresh": _get_adv(job, "seal_det_box_thresh"),
            "seal_det_unclip_ratio": _get_adv(job, "seal_det_unclip_ratio"),
            "seal_rec_score_thresh": _get_adv(job, "seal_rec_score_thresh"),
        }
    )
    return options


def _deserialize_block(block_data: dict[str, object]) -> BlockResult:
    block_type_value = str(block_data.get("block_type", BlockType.PARAGRAPH.value))
    try:
        block_type = BlockType(block_type_value)
    except ValueError:
        block_type = BlockType.OTHER

    bbox_data = block_data.get("bbox", [0, 0, 0, 0])
    bbox = tuple(float(v) for v in bbox_data)
    return BlockResult(
        block_type=block_type,
        bbox=bbox,
        text=str(block_data.get("text", "")),
        confidence=(
            float(block_data["confidence"])
            if block_data.get("confidence") is not None
            else None
        ),
        html=block_data.get("html"),
        markdown=block_data.get("markdown"),
        table_cells=block_data.get("table_cells"),
    )


class OCRWorker(QThread):
    progress = Signal(str, int, int)
    finished = Signal(DocumentResult)
    error = Signal(str)

    def __init__(self, job: OCRJob, parent=None) -> None:
        super().__init__(parent)
        self.setStackSize(_WORKER_STACK_SIZE)
        self._job = job
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            self._do_work()
        except Exception as e:
            self.error.emit(str(e))

    def _do_work(self) -> None:
        job = self._job
        is_pdf = job.source_path.suffix.lower() == ".pdf"
        pipeline = _resolve_pipeline(job)
        text_only = (
            job.output_format in (OutputFormat.TXT, OutputFormat.RTF)
            and pipeline == "ocr"
            and not job.preserve_layout
        )

        if is_pdf:
            from app.core.pdf_processor import extract_text_direct, get_page_count, has_text_layer

            self.progress.emit("正在读取 PDF...", 0, 0)
            total = get_page_count(job.source_path)
            page_start, page_end = _resolve_page_range(job, total)
        else:
            total = 1
            page_start, page_end = 0, 1

        actual = page_end - page_start
        force_ocr = _get_adv(job, "force_ocr", False)
        if is_pdf and text_only and not force_ocr and has_text_layer(job.source_path):
            self.progress.emit("检测到 PDF 文字层，直接提取（无需 OCR）...", 0, actual)
            texts = extract_text_direct(job.source_path, page_start, page_end)
            doc = DocumentResult(
                source_path=job.source_path,
                page_count=actual,
                pages=[],
                plain_text="\n\n".join(t for t in texts if t.strip()),
            )
            self.progress.emit("提取完成", actual, actual)
            self.finished.emit(doc)
            return

        user_dpi = _get_adv(job, "render_dpi", 200)
        dpi = _auto_dpi(actual, user_dpi)
        speed_mode = _get_adv(job, "speed_mode", "server")
        max_workers = max(1, int(_get_adv(job, "parallel_workers", 2)))
        pipeline_label = "PPStructureV3" if pipeline == "structure" else "PP-OCRv5"
        options = (
            _structure_options(job, speed_mode)
            if pipeline == "structure"
            else _ocr_options(job)
        )

        mode_label = "Mobile" if speed_mode == "mobile" else "Server"
        self.progress.emit(
            f"{actual} 页 | DPI {dpi} | {pipeline_label} | {mode_label} | {max_workers} 并行",
            0,
            actual,
        )

        from app.core.ocr_subprocess import run_pipeline_parallel

        all_pages: list[PageResult] = []
        all_texts: list[str] = []
        pages_done = 0
        page_indices = list(range(page_start, page_end))
        all_batches_indices: list[list[int]] = []
        for i in range(0, len(page_indices), BATCH_SIZE):
            all_batches_indices.append(page_indices[i:i + BATCH_SIZE])

        for group_start in range(0, len(all_batches_indices), max_workers):
            if self._cancel:
                self.error.emit("用户取消了操作")
                return

            group = all_batches_indices[group_start:group_start + max_workers]
            group_page_count = sum(len(batch) for batch in group)
            self.progress.emit(
                f"正在识别第 {pages_done + 1}~{pages_done + group_page_count}/{actual} 页"
                f"（{len(group)} 批并行）...",
                pages_done,
                actual,
            )

            batch_images: list[list[Path]] = []
            for batch_indices in group:
                if is_pdf:
                    from app.core.pdf_processor import render_page

                    images = [render_page(job.source_path, pi, dpi) for pi in batch_indices]
                else:
                    images = [job.source_path]
                batch_images.append(images)

            try:
                group_results = run_pipeline_parallel(
                    batch_images,
                    lang=job.language,
                    speed_mode=speed_mode,
                    pipeline=pipeline,
                    options=options,
                    max_workers=max_workers,
                )
            finally:
                if is_pdf:
                    for images in batch_images:
                        for image in images:
                            if image.exists():
                                os.unlink(image)

            for batch_indices, batch_result in zip(group, group_results):
                if batch_result and "error" in batch_result[0]:
                    self.error.emit(batch_result[0]["error"])
                    return

                for image_idx, image_result in enumerate(batch_result):
                    plain_text = str(image_result.get("plain_text", "") or "")
                    if plain_text:
                        all_texts.append(plain_text)

                    if text_only:
                        continue

                    for page_offset, page_data in enumerate(image_result.get("pages", [])):
                        blocks = [
                            _deserialize_block(block_data)
                            for block_data in page_data.get("blocks", [])
                        ]
                        absolute_page_index = (
                            batch_indices[image_idx] + page_offset
                            if is_pdf
                            else len(all_pages)
                        )
                        all_pages.append(
                            PageResult(
                                page_index=absolute_page_index,
                                width=int(page_data.get("width", 0) or 0),
                                height=int(page_data.get("height", 0) or 0),
                                blocks=blocks,
                            )
                        )

                pages_done += len(batch_indices)

            self.progress.emit(f"已完成 {pages_done}/{actual} 页", pages_done, actual)

        doc = DocumentResult(
            source_path=job.source_path,
            page_count=actual if is_pdf else len(all_pages) or actual,
            pages=all_pages,
            plain_text="\n\n".join(all_texts),
        )
        self.progress.emit("处理完成", actual, actual)
        self.finished.emit(doc)
