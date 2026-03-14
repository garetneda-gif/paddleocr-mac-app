"""OCR 后台工作线程 — 逐页处理，内存友好。"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.models import DocumentResult, PageResult
from app.models.enums import OutputFormat
from app.models.job import OCRJob

# 从 job 上读取 UI 传入的高级参数
def _get_adv(job: OCRJob, key: str, default=None):
    return getattr(job, '_adv_params', {}).get(key, default)

_WORKER_STACK_SIZE = 64 * 1024 * 1024


class OCRWorker(QThread):
    progress = Signal(str, int, int)  # stage, current_page, total_pages
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
        suffix = job.source_path.suffix.lower()
        is_pdf = suffix == ".pdf"

        # ── 1. 确定页数 ──
        if is_pdf:
            from app.core.pdf_processor import get_page_count
            self.progress.emit("正在读取 PDF 信息...", 0, 0)
            total = get_page_count(job.source_path)
        else:
            total = 1

        self.progress.emit(f"共 {total} 页，正在初始化模型...", 0, total)

        # ── 2. 初始化引擎 ──
        speed_mode = _get_adv(job, "speed_mode", "server")
        use_structure = self._should_use_structure(job)
        if use_structure:
            from app.core.structure_engine import StructureEngine
            engine = StructureEngine(lang=job.language)
        else:
            from app.core.ocr_engine import OCREngine
            engine = OCREngine(lang=job.language, speed_mode=speed_mode)

        engine._ensure_model()
        if self._cancel:
            return

        self.progress.emit("模型就绪，开始识别...", 0, total)

        # ── 3. 逐页渲染+识别（不一次性加载所有页面） ──
        all_pages: list[PageResult] = []
        all_texts: list[str] = []

        for i in range(total):
            if self._cancel:
                self.error.emit("用户取消了操作")
                return

            self.progress.emit(f"正在识别第 {i + 1}/{total} 页...", i + 1, total)

            if is_pdf:
                from app.core.pdf_processor import render_page
                img_path = render_page(job.source_path, i)
            else:
                img_path = job.source_path

            page_result = engine.predict(img_path)

            # 用完立即删除临时文件
            if is_pdf and img_path.exists():
                os.unlink(img_path)

            for page in page_result.pages:
                page.page_index = len(all_pages)
                all_pages.append(page)

            if page_result.plain_text:
                all_texts.append(page_result.plain_text)

        result = DocumentResult(
            source_path=job.source_path,
            page_count=len(all_pages),
            pages=all_pages,
            plain_text="\n".join(all_texts),
        )

        self.progress.emit("处理完成", total, total)
        self.finished.emit(result)

    def _should_use_structure(self, job: OCRJob) -> bool:
        fmt = job.output_format
        if fmt in (OutputFormat.WORD, OutputFormat.HTML, OutputFormat.EXCEL):
            return True
        if job.preserve_layout and fmt in (OutputFormat.TXT, OutputFormat.RTF):
            return True
        return False
