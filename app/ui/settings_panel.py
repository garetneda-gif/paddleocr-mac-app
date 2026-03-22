"""设置面板 — 默认配置、模型缓存管理、关于。"""

from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal as _Signal, QSettings
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.i18n import tr, set_language, current_language, on_language_changed, UI_LANGUAGE_NAMES
from app.ui.theme import ACCENT, DANGER, TEXT_PRIMARY, TEXT_SECONDARY, __version__
from app.utils.language_map import LANGUAGES
from app.utils.paths import default_output_dir

_PADDLEX_CACHE = Path.home() / ".paddlex" / "official_models"


def _find_model_dirs() -> list[tuple[str, Path]]:
    """返回所有实际存在的模型目录 [(label_key, path), ...]。"""
    dirs: list[tuple[str, Path]] = []
    try:
        from app.core.onnx_engine import _find_onnx_dir
        onnx_dir = _find_onnx_dir()
        if onnx_dir:
            dirs.append(("settings_cache_onnx", onnx_dir))
    except Exception:
        pass
    if _PADDLEX_CACHE.exists():
        dirs.append(("settings_cache_paddlex", _PADDLEX_CACHE))
    return dirs


class _CacheInfoWorker(QThread):
    """后台计算模型缓存大小。"""

    finished = _Signal(str)

    def run(self):
        dirs = _find_model_dirs()
        if not dirs:
            self.finished.emit(tr("settings_cache_not_found"))
            return

        lines: list[str] = []
        total_size = 0
        total_models = 0
        for label_key, d in dirs:
            try:
                models = [p for p in d.iterdir() if p.is_dir() or p.suffix == ".onnx"]
                size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
                total_size += size
                total_models += len(models)
                lines.append(f"{tr(label_key)}：{d}")
            except Exception:
                lines.append(f"{tr(label_key)}：{tr('settings_cache_read_error')}")

        size_mb = total_size / (1024 * 1024)
        lines.append(tr("settings_cache_models").format(count=total_models))
        lines.append(tr("settings_cache_size").format(size=f"{size_mb:.0f}"))
        self.finished.emit("\n".join(lines))


class SettingsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = QSettings("PaddleOCR", "Desktop")
        self._cache_worker: _CacheInfoWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        self._title = QLabel(tr("settings_title"))
        self._title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {TEXT_PRIMARY};")
        layout.addWidget(self._title)

        # ── 界面语言 ──
        self._ui_lang_group = QGroupBox(tr("settings_ui_language"))
        ui_lang_layout = QHBoxLayout(self._ui_lang_group)
        self._ui_lang_combo = QComboBox()
        for code, name in UI_LANGUAGE_NAMES.items():
            self._ui_lang_combo.addItem(name, code)
        self._ui_lang_combo.setFixedWidth(280)

        # 设置当前语言
        idx = self._ui_lang_combo.findData(current_language())
        if idx >= 0:
            self._ui_lang_combo.setCurrentIndex(idx)
        self._ui_lang_combo.currentIndexChanged.connect(self._on_ui_language_changed)

        ui_lang_layout.addWidget(self._ui_lang_combo)
        ui_lang_layout.addStretch()
        layout.addWidget(self._ui_lang_group)

        # ── 默认语言 ──
        self._lang_group = QGroupBox(tr("settings_ocr_language"))
        lang_layout = QHBoxLayout(self._lang_group)
        self._lang_combo = QComboBox()
        for code, name in LANGUAGES.items():
            self._lang_combo.addItem(f"{name} ({code})", code)
        self._lang_combo.setFixedWidth(280)

        # 从 QSettings 恢复
        saved_lang = self._settings.value("ocr/language", "ch")
        idx = self._lang_combo.findData(saved_lang)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
        self._lang_combo.currentIndexChanged.connect(self._save_language)

        lang_layout.addWidget(self._lang_combo)
        lang_layout.addStretch()
        layout.addWidget(self._lang_group)

        # ── 默认输出目录 ──
        self._dir_group = QGroupBox(tr("settings_output_dir"))
        dir_layout = QHBoxLayout(self._dir_group)

        saved_dir = self._settings.value("output/directory", "")
        self._dir_edit = QLineEdit(saved_dir or str(default_output_dir()))
        self._dir_edit.editingFinished.connect(self._save_directory)
        dir_layout.addWidget(self._dir_edit)

        self._dir_select_btn = QPushButton(tr("settings_select"))
        self._dir_select_btn.setFixedWidth(60)
        self._dir_select_btn.clicked.connect(self._browse_dir)
        dir_layout.addWidget(self._dir_select_btn)
        self._dir_open_btn = QPushButton(tr("settings_open"))
        self._dir_open_btn.setFixedWidth(60)
        self._dir_open_btn.clicked.connect(self._open_dir)
        dir_layout.addWidget(self._dir_open_btn)
        layout.addWidget(self._dir_group)

        # ── 模型缓存 ──
        self._cache_group = QGroupBox(tr("settings_model_cache"))
        cache_layout = QVBoxLayout(self._cache_group)

        self._cache_info = QLabel(tr("settings_calculating"))
        cache_layout.addWidget(self._cache_info)

        cache_btn_row = QHBoxLayout()
        self._refresh_btn = QPushButton(tr("settings_refresh"))
        self._refresh_btn.setFixedWidth(80)
        self._refresh_btn.clicked.connect(self._update_cache_info)
        cache_btn_row.addWidget(self._refresh_btn)

        self._clear_btn = QPushButton(tr("settings_delete_paddle"))
        self._clear_btn.setMinimumWidth(140)
        self._clear_btn.setStyleSheet(f"color: {DANGER};")
        self._clear_btn.clicked.connect(self._clear_cache)
        cache_btn_row.addWidget(self._clear_btn)
        cache_btn_row.addStretch()
        cache_layout.addLayout(cache_btn_row)

        layout.addWidget(self._cache_group)

        # ── 关于 ──
        self._about_group = QGroupBox(tr("settings_about"))
        about_layout = QVBoxLayout(self._about_group)
        self._about_text = QLabel(tr("settings_about_text").format(version=__version__))
        self._about_text.setWordWrap(True)
        self._about_text.setStyleSheet(f"color: {TEXT_SECONDARY}; line-height: 1.5;")
        about_layout.addWidget(self._about_text)
        layout.addWidget(self._about_group)

        layout.addStretch()

        # 异步加载缓存信息
        self._update_cache_info()

        on_language_changed(self._retranslate)

    def _retranslate(self) -> None:
        self._title.setText(tr("settings_title"))
        self._ui_lang_group.setTitle(tr("settings_ui_language"))
        self._lang_group.setTitle(tr("settings_ocr_language"))
        self._dir_group.setTitle(tr("settings_output_dir"))
        self._dir_select_btn.setText(tr("settings_select"))
        self._dir_open_btn.setText(tr("settings_open"))
        self._cache_group.setTitle(tr("settings_model_cache"))
        self._refresh_btn.setText(tr("settings_refresh"))
        self._clear_btn.setText(tr("settings_delete_paddle"))
        self._about_group.setTitle(tr("settings_about"))
        self._about_text.setText(tr("settings_about_text").format(version=__version__))

    def _on_ui_language_changed(self) -> None:
        lang = self._ui_lang_combo.currentData()
        if lang and lang != current_language():
            set_language(lang)

    def _save_language(self) -> None:
        self._settings.setValue("ocr/language", self._lang_combo.currentData())

    def _save_directory(self) -> None:
        self._settings.setValue("output/directory", self._dir_edit.text())

    def _browse_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, tr("settings_select_output_dir"))
        if d:
            self._dir_edit.setText(d)
            self._save_directory()

    def _open_dir(self) -> None:
        import subprocess, sys
        path = self._dir_edit.text()
        if sys.platform == "darwin":
            subprocess.run(["open", path])

    def _update_cache_info(self) -> None:
        self._cache_info.setText(tr("settings_calculating"))
        self._cache_worker = _CacheInfoWorker(self)
        self._cache_worker.finished.connect(self._on_cache_info_ready)
        self._cache_worker.start()

    def _on_cache_info_ready(self, text: str) -> None:
        self._cache_info.setText(text)
        self._cache_worker = None

    def _clear_cache(self) -> None:
        size_mb = 0
        if _PADDLEX_CACHE.exists():
            size_mb = sum(
                f.stat().st_size for f in _PADDLEX_CACHE.rglob("*") if f.is_file()
            ) / (1024 * 1024)

        reply = QMessageBox.warning(
            self, tr("settings_delete_title"),
            tr("settings_delete_confirm").format(size=f"{size_mb:.0f}", path=_PADDLEX_CACHE),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if _PADDLEX_CACHE.exists():
                shutil.rmtree(_PADDLEX_CACHE)
                _PADDLEX_CACHE.mkdir(parents=True, exist_ok=True)
            self._update_cache_info()
            QMessageBox.information(
                self, tr("settings_deleted_title"), tr("settings_deleted_msg")
            )

    def get_output_dir(self) -> str:
        """供外部读取当前输出目录。"""
        return self._dir_edit.text()
