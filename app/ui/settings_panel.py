"""设置面板 — 默认配置、模型缓存管理、关于。"""

from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt
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

from app.utils.language_map import LANGUAGES
from app.utils.paths import default_output_dir

_PADDLEX_CACHE = Path.home() / ".paddlex" / "official_models"


def _find_model_dirs() -> list[tuple[str, Path]]:
    """返回所有实际存在的模型目录 [(label, path), ...]。"""
    dirs: list[tuple[str, Path]] = []
    try:
        from app.core.onnx_engine import _find_onnx_dir
        onnx_dir = _find_onnx_dir()
        if onnx_dir:
            dirs.append(("ONNX 模型", onnx_dir))
    except Exception:
        pass
    if _PADDLEX_CACHE.exists():
        dirs.append(("PaddleX 缓存", _PADDLEX_CACHE))
    return dirs


class SettingsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("设置")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        # ── 默认语言 ──
        lang_group = QGroupBox("默认识别语言")
        lang_layout = QHBoxLayout(lang_group)
        self._lang_combo = QComboBox()
        for code, name in LANGUAGES.items():
            self._lang_combo.addItem(f"{name} ({code})", code)
        self._lang_combo.setFixedWidth(280)
        lang_layout.addWidget(self._lang_combo)
        lang_layout.addStretch()
        layout.addWidget(lang_group)

        # ── 默认输出目录 ──
        dir_group = QGroupBox("默认输出目录")
        dir_layout = QHBoxLayout(dir_group)
        self._dir_edit = QLineEdit(str(default_output_dir()))
        dir_layout.addWidget(self._dir_edit)
        dir_btn = QPushButton("选择")
        dir_btn.setFixedWidth(60)
        dir_btn.clicked.connect(self._browse_dir)
        dir_layout.addWidget(dir_btn)
        open_btn = QPushButton("打开")
        open_btn.setFixedWidth(60)
        open_btn.clicked.connect(self._open_dir)
        dir_layout.addWidget(open_btn)
        layout.addWidget(dir_group)

        # ── 模型缓存 ──
        cache_group = QGroupBox("模型缓存")
        cache_layout = QVBoxLayout(cache_group)

        self._cache_info = QLabel()
        self._update_cache_info()
        cache_layout.addWidget(self._cache_info)

        cache_btn_row = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        refresh_btn.setFixedWidth(80)
        refresh_btn.clicked.connect(self._update_cache_info)
        cache_btn_row.addWidget(refresh_btn)

        clear_btn = QPushButton("清除缓存")
        clear_btn.setFixedWidth(100)
        clear_btn.setStyleSheet("color: #D32F2F;")
        clear_btn.clicked.connect(self._clear_cache)
        cache_btn_row.addWidget(clear_btn)
        cache_btn_row.addStretch()
        cache_layout.addLayout(cache_btn_row)

        layout.addWidget(cache_group)

        # ── 关于 ──
        about_group = QGroupBox("关于")
        about_layout = QVBoxLayout(about_group)
        about_text = QLabel(
            "PaddleOCR 桌面版 v1.0.0\n\n"
            "基于 PaddleOCR 3.4.0 / PaddlePaddle 3.3.0\n"
            "识别引擎：PP-OCRv5 + PPStructureV3\n"
            "UI 框架：PySide6 (Qt 6)\n\n"
            "支持格式：TXT / PDF / Word / HTML / Excel / RTF"
        )
        about_text.setWordWrap(True)
        about_text.setStyleSheet("color: #555; line-height: 1.5;")
        about_layout.addWidget(about_text)
        layout.addWidget(about_group)

        layout.addStretch()

    def _browse_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "选择默认输出目录")
        if d:
            self._dir_edit.setText(d)

    def _open_dir(self) -> None:
        import subprocess, sys
        path = self._dir_edit.text()
        if sys.platform == "darwin":
            subprocess.run(["open", path])

    def _update_cache_info(self) -> None:
        dirs = _find_model_dirs()
        if not dirs:
            self._cache_info.setText("未找到模型目录")
            return

        lines: list[str] = []
        total_size = 0
        total_models = 0
        for label, d in dirs:
            models = [p for p in d.iterdir() if p.is_dir() or p.suffix == ".onnx"]
            size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            total_size += size
            total_models += len(models)
            lines.append(f"{label}：{d}")

        size_mb = total_size / (1024 * 1024)
        lines.append(f"已缓存模型：{total_models} 个")
        lines.append(f"占用空间：{size_mb:.0f} MB")
        self._cache_info.setText("\n".join(lines))

    def _clear_cache(self) -> None:
        reply = QMessageBox.question(
            self, "确认清除",
            "仅清除 PaddleX 缓存（~/.paddlex/official_models）。\n"
            "ONNX 模型不受影响。确定要清除吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if _PADDLEX_CACHE.exists():
                shutil.rmtree(_PADDLEX_CACHE)
                _PADDLEX_CACHE.mkdir(parents=True, exist_ok=True)
            self._update_cache_info()
            QMessageBox.information(self, "已清除", "PaddleX 模型缓存已清除。")
