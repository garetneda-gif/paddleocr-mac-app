"""主窗口 — 侧边栏 + 转换面板（含折叠高级选项）+ 预览 + 设置。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QWidget,
)

from app.core.export_router import create_default_router
from app.core.ocr_worker import OCRWorker
from app.i18n import tr, on_language_changed
from app.models import DocumentResult
from app.models.enums import OutputFormat
from app.models.job import OCRJob
from app.ui.preview_panel import PreviewPanel
from app.ui.progress_dialog import ProgressDialog
from app.ui.quick_convert_panel import QuickConvertPanel
from app.ui.settings_panel import SettingsPanel
from app.ui.sidebar import Sidebar
from app.utils.log import get_logger
from app.utils.notify import send_notification
from app.utils.paths import default_output_dir

_log = get_logger("main_window")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(tr("app_title"))
        self.setMinimumSize(900, 560)
        self.resize(1100, 720)

        self._worker: OCRWorker | None = None
        self._progress_dialog: ProgressDialog | None = None
        self._router = create_default_router()
        self._current_job: OCRJob | None = None

        # 批量处理状态
        self._batch_files: list[Path] = []
        self._batch_index: int = 0
        self._batch_results: list[tuple[Path, bool]] = []
        self._batch_fmt: OutputFormat = OutputFormat.TXT
        self._batch_lang: str = "ch"

        self._setup_ui()
        self._load_styles()
        self._setup_shortcuts()

        on_language_changed(self._retranslate)

    def _retranslate(self) -> None:
        self.setWindowTitle(tr("app_title"))

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

    def _setup_shortcuts(self) -> None:
        from PySide6.QtGui import QKeySequence, QShortcut
        paste = QShortcut(QKeySequence.StandardKey.Paste, self)
        paste.activated.connect(self._on_paste)

    def _on_paste(self) -> None:
        """全局 Cmd+V：转发给转换面板的 DropZone。"""
        if self._stack.currentIndex() != 0:
            self._sidebar._on_click(0)
            self._stack.setCurrentIndex(0)
        self._convert_panel._drop_zone._paste_from_clipboard()

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

        self._sidebar.set_processing(True)
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

        self._sidebar.set_processing(True)
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
            prefix = tr("batch_prefix").format(
                index=self._batch_index + 1, total=len(self._batch_files)
            )
            self._progress_dialog.update_progress(prefix + stage, current, total)

    def _on_batch_file_finished(self, result: DocumentResult) -> None:
        file_path = self._batch_files[self._batch_index]
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
            self._batch_results.append((file_path, True))
        except Exception as e:
            _log.warning("批量导出失败: %s -- %s", file_path.name, e)
            self._batch_results.append((file_path, False))

        self._batch_index += 1
        self._start_next_batch_file()

    def _on_batch_file_error(self, msg: str) -> None:
        file_path = self._batch_files[self._batch_index]
        _log.warning("批量处理文件失败: %s -- %s", file_path.name, msg)
        self._batch_results.append((file_path, False))
        self._batch_index += 1
        self._start_next_batch_file()

    def _on_batch_all_finished(self) -> None:
        elapsed = 0.0
        if self._progress_dialog:
            elapsed = self._progress_dialog.elapsed_seconds()
            self._progress_dialog.close()
            self._progress_dialog = None

        self._sidebar.set_processing(False)

        success_count = sum(1 for _, ok in self._batch_results if ok)
        errors = [fp.name for fp, ok in self._batch_results if not ok]

        time_str = self._format_time(elapsed)

        msg = tr("batch_done_msg").format(
            success=success_count, total=len(self._batch_files), time=time_str
        )
        if errors:
            msg += tr("batch_done_fail").format(files=", ".join(errors[:3]))

        output_dir = default_output_dir()
        send_notification(tr("batch_notify_title"), msg)

        icon = QMessageBox.Icon.Information if not errors else QMessageBox.Icon.Warning
        dlg = QMessageBox(self)
        dlg.setWindowTitle(tr("batch_done_title"))
        dlg.setText(msg)
        dlg.setIcon(icon)
        open_btn = dlg.addButton(tr("open_dir"), QMessageBox.ButtonRole.AcceptRole)
        dlg.addButton(tr("close"), QMessageBox.ButtonRole.RejectRole)
        dlg.exec()
        if dlg.clickedButton() == open_btn:
            self._open_file(output_dir)

    # ── 进度 / 完成 / 错误 ──

    def _on_progress(self, stage: str, current: int, total: int) -> None:
        if self._progress_dialog:
            self._progress_dialog.update_progress(stage, current, total)

    def _on_finished(self, result: DocumentResult) -> None:
        elapsed = 0.0
        if self._progress_dialog:
            elapsed = self._progress_dialog.elapsed_seconds()
            self._progress_dialog.close()
            self._progress_dialog = None

        self._sidebar.set_processing(False)

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

            time_str = self._format_time(elapsed)
            page_info = tr("page_count").format(count=result.page_count) if result.page_count > 1 else ""
            char_count = len(result.plain_text.replace("\n", "").replace(" ", ""))

            msg = tr("convert_done_msg").format(
                time=time_str, pages=page_info, chars=char_count
            )
            send_notification(tr("notify_done_title"), msg)

            dlg = QMessageBox(self)
            dlg.setWindowTitle(tr("convert_done_title"))
            dlg.setText(msg)
            dlg.setIcon(QMessageBox.Icon.Information)
            open_btn = dlg.addButton(tr("open_file"), QMessageBox.ButtonRole.AcceptRole)
            dlg.addButton(tr("close"), QMessageBox.ButtonRole.RejectRole)
            dlg.exec()
            if dlg.clickedButton() == open_btn:
                self._open_file(output_path)

            # 自动切换到预览页
            self._sidebar._on_click(1)
            self._stack.setCurrentIndex(1)

        except Exception as e:
            QMessageBox.critical(self, tr("export_error"), str(e))

    def _on_error(self, msg: str) -> None:
        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None

        self._sidebar.set_processing(False)

        short_msg = msg[:200] + "..." if len(msg) > 200 else msg
        QMessageBox.critical(self, tr("process_error"), short_msg)
        send_notification(tr("notify_error_title"), msg[:100])

    def _on_cancel(self) -> None:
        if self._worker:
            self._worker.cancel()

    @staticmethod
    def _format_time(elapsed: float) -> str:
        if elapsed < 60:
            return tr("time_seconds").format(seconds=f"{elapsed:.1f}")
        m, s = divmod(int(elapsed), 60)
        return tr("time_minutes").format(minutes=m, seconds=s)

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
