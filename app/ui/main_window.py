"""主窗口 — 侧边栏 + 转换面板（含折叠高级选项）+ 预览 + 设置。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QWidget,
)

from app.core.export_router import create_default_router
from app.core.ocr_worker import OCRWorker
from app.models import DocumentResult
from app.models.enums import OutputFormat
from app.models.job import OCRJob
from app.ui.preview_panel import PreviewPanel
from app.ui.progress_dialog import ProgressDialog
from app.ui.quick_convert_panel import QuickConvertPanel
from app.ui.settings_panel import SettingsPanel
from app.ui.sidebar import Sidebar
from app.utils.log import get_logger
from app.utils.paths import default_output_dir

_log = get_logger("main_window")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PaddleOCR — 智能文档识别")
        self.setMinimumSize(900, 560)
        self.resize(1100, 720)

        self._worker: OCRWorker | None = None
        self._progress_dialog: ProgressDialog | None = None
        self._router = create_default_router()
        self._current_job: OCRJob | None = None

        # 批量处理状态
        self._batch_files: list[Path] = []
        self._batch_index: int = 0
        self._batch_results: list[tuple[Path, DocumentResult]] = []
        self._batch_fmt: OutputFormat = OutputFormat.TXT
        self._batch_lang: str = "ch"

        self._setup_ui()
        self._load_styles()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._sidebar = Sidebar()
        self._sidebar.page_changed.connect(self._on_page_changed)
        main_layout.addWidget(self._sidebar)

        self._stack = QStackedWidget()
        main_layout.addWidget(self._stack, 1)

        # 页面 0：转换（含折叠高级选项）
        self._convert_panel = QuickConvertPanel()
        self._convert_panel.start_requested.connect(self._on_start)
        self._convert_panel.batch_start_requested.connect(self._on_batch_start)
        self._stack.addWidget(self._convert_panel)

        # 页面 1：预览
        self._preview_panel = PreviewPanel()
        self._stack.addWidget(self._preview_panel)

        # 页面 2：设置
        self._settings_panel = SettingsPanel()
        self._stack.addWidget(self._settings_panel)

    def _load_styles(self) -> None:
        from app.utils.paths import resources_dir
        qss_path = resources_dir() / "styles.qss"
        if qss_path.exists():
            self.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    def _on_page_changed(self, index: int) -> None:
        self._stack.setCurrentIndex(index)

    # ── 单文件处理 ──

    def _on_start(self, file_path: Path, fmt: OutputFormat, lang: str) -> None:
        adv = self._convert_panel.get_advanced_params()

        job = OCRJob(
            source_path=file_path,
            output_format=fmt,
            language=lang,
            preserve_layout=adv.get("preserve_layout", False),
        )
        job._adv_params = adv

        self._current_job = job
        self._batch_files = []

        self._worker = OCRWorker(job)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)

        self._progress_dialog = ProgressDialog(self)
        self._progress_dialog.cancel_requested.connect(self._on_cancel)
        self._progress_dialog.show()

        self._worker.start()

    # ── 批量处理 ──

    def _on_batch_start(self, files: list[Path], fmt: OutputFormat, lang: str) -> None:
        _log.info("批量处理: %d 个文件", len(files))
        self._batch_files = files
        self._batch_index = 0
        self._batch_results = []
        self._batch_fmt = fmt
        self._batch_lang = lang

        self._progress_dialog = ProgressDialog(self)
        self._progress_dialog.cancel_requested.connect(self._on_cancel)
        self._progress_dialog.show()

        self._start_next_batch_file()

    def _start_next_batch_file(self) -> None:
        if self._batch_index >= len(self._batch_files):
            self._on_batch_all_finished()
            return

        file_path = self._batch_files[self._batch_index]
        adv = self._convert_panel.get_advanced_params()

        job = OCRJob(
            source_path=file_path,
            output_format=self._batch_fmt,
            language=self._batch_lang,
            preserve_layout=adv.get("preserve_layout", False),
        )
        job._adv_params = adv
        self._current_job = job

        self._worker = OCRWorker(job)
        self._worker.progress.connect(self._on_batch_progress)
        self._worker.finished.connect(self._on_batch_file_finished)
        self._worker.error.connect(self._on_batch_file_error)
        self._worker.start()

    def _on_batch_progress(self, stage: str, current: int, total: int) -> None:
        if self._progress_dialog:
            prefix = f"文件 {self._batch_index + 1}/{len(self._batch_files)}: "
            self._progress_dialog.update_progress(prefix + stage, current, total)

    def _on_batch_file_finished(self, result: DocumentResult) -> None:
        self._batch_results.append((self._batch_files[self._batch_index], result))
        self._batch_index += 1
        self._start_next_batch_file()

    def _on_batch_file_error(self, msg: str) -> None:
        file_name = self._batch_files[self._batch_index].name
        _log.warning("批量处理文件失败: %s — %s", file_name, msg)
        # 跳过失败的文件，继续下一个
        self._batch_index += 1
        self._start_next_batch_file()

    def _on_batch_all_finished(self) -> None:
        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

        success_count = 0
        errors: list[str] = []

        for file_path, result in self._batch_results:
            try:
                converter = self._router.select_converter(self._batch_fmt)
                output_dir = default_output_dir()
                ext = converter.file_extension
                output_path = output_dir / (file_path.stem + ext)

                counter = 1
                while output_path.exists():
                    output_path = output_dir / f"{file_path.stem}_{counter}{ext}"
                    counter += 1

                converter.convert(result, output_path)
                success_count += 1
            except Exception as e:
                errors.append(f"{file_path.name}: {e}")

        msg = f"批量转换完成！\n成功: {success_count}/{len(self._batch_files)}"
        if errors:
            msg += f"\n\n失败文件:\n" + "\n".join(errors[:5])
        if success_count > 0:
            msg += f"\n\n输出目录: {default_output_dir()}"

        reply = QMessageBox.information(
            self, "批量转换完成", msg,
            QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Ok,
        )
        if reply == QMessageBox.StandardButton.Open:
            self._open_file(default_output_dir())

    # ── 进度 / 完成 / 错误 ──

    def _on_progress(self, stage: str, current: int, total: int) -> None:
        if self._progress_dialog:
            self._progress_dialog.update_progress(stage, current, total)

    def _on_finished(self, result: DocumentResult) -> None:
        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

        # 将结果传给预览面板
        self._preview_panel.set_result(result)

        try:
            job = self._current_job
            converter = self._router.select_converter(job.output_format)

            output_dir = default_output_dir()
            ext = converter.file_extension
            output_path = output_dir / (job.source_path.stem + ext)

            counter = 1
            while output_path.exists():
                output_path = output_dir / f"{job.source_path.stem}_{counter}{ext}"
                counter += 1

            converter.convert(result, output_path)

            reply = QMessageBox.information(
                self,
                "转换完成",
                f"文件已保存到:\n{output_path}\n\n是否打开文件？\n（预览已在【预览】页显示）",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._open_file(output_path)

            # 自动切换到预览页
            self._sidebar._on_click(1)
            self._stack.setCurrentIndex(1)

        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _on_error(self, msg: str) -> None:
        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None
        QMessageBox.warning(self, "处理出错", msg)

    def _on_cancel(self) -> None:
        if self._worker:
            self._worker.cancel()

    def _open_file(self, path: Path) -> None:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)])
        elif sys.platform == "win32":
            subprocess.run(["start", str(path)], shell=True)
        else:
            subprocess.run(["xdg-open", str(path)])

    def closeEvent(self, event) -> None:
        """应用退出时清理进程池。"""
        from app.core.ocr_subprocess import shutdown_pool
        shutdown_pool()
        super().closeEvent(event)
