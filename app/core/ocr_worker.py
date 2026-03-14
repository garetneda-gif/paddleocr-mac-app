"""OCR 后台工作线程 — 按 OutputFormat 路由到正确的 pipeline。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.models import DocumentResult
from app.models.enums import OutputFormat
from app.models.job import OCRJob


# QThread 默认栈仅 544KB，PaddlePaddle + numpy/OpenBLAS 递归导入链
# 会直接爆栈（SIGBUS）。设为 64MB 留足余量。
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

        # ── 1. PDF 页面提取 ──
        suffix = job.source_path.suffix.lower()
        if suffix == ".pdf":
            self.progress.emit("正在提取 PDF 页面（可能需要较长时间）...", 0, 0)
            image_paths = self._extract_pdf_pages(job.source_path)
            if self._cancel:
                self.error.emit("用户取消了操作")
                return
        else:
            image_paths = [job.source_path]

        total = len(image_paths)
        self.progress.emit(f"PDF 共 {total} 页，正在初始化模型...", 0, total)

        # ── 2. 选择并初始化引擎 ──
        use_structure = self._should_use_structure(job)

        if use_structure:
            from app.core.structure_engine import StructureEngine
            engine = StructureEngine(lang=job.language)
        else:
            from app.core.ocr_engine import OCREngine
            engine = OCREngine(lang=job.language)

        engine._ensure_model()

        if self._cancel:
            self.error.emit("用户取消了操作")
            return

        self.progress.emit("模型就绪，开始识别...", 0, total)

        # ── 3. 逐页识别 ──
        all_pages = []
        all_texts = []

        for i, img_path in enumerate(image_paths):
            if self._cancel:
                self.error.emit("用户取消了操作")
                return

            self.progress.emit(f"正在识别第 {i + 1}/{total} 页...", i + 1, total)
            page_result = engine.predict(img_path)

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

    def _extract_pdf_pages(self, pdf_path: Path) -> list[Path]:
        from app.core.pdf_processor import extract_pages
        return extract_pages(pdf_path)
