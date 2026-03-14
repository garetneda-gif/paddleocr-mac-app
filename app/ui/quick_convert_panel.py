"""快速转换主面板 — 拖拽区域 + 格式卡片 + 语言选择 + 开始按钮。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models.enums import OutputFormat
from app.ui.drop_zone import DropZone
from app.ui.format_card import FormatCard

_LANGUAGES = [
    ("ch", "中文（含中英混合）"),
    ("en", "English"),
    ("japan", "日本語"),
    ("korean", "한국어"),
    ("french", "Français"),
    ("german", "Deutsch"),
]


class QuickConvertPanel(QWidget):
    start_requested = Signal(Path, OutputFormat, str)  # file, format, lang

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._selected_file: Path | None = None
        self._selected_format: OutputFormat = OutputFormat.TXT

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("快速转换")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        # 拖拽区域
        self._drop_zone = DropZone()
        self._drop_zone.file_dropped.connect(self._on_file_selected)
        layout.addWidget(self._drop_zone)

        # 格式卡片行
        fmt_label = QLabel("选择输出格式：")
        fmt_label.setStyleSheet("font-size: 13px; color: #555;")
        layout.addWidget(fmt_label)

        fmt_layout = QHBoxLayout()
        fmt_layout.setSpacing(10)
        self._cards: list[FormatCard] = []
        for fmt in OutputFormat:
            card = FormatCard(fmt)
            card.selected.connect(self._on_format_selected)
            fmt_layout.addWidget(card)
            self._cards.append(card)
        fmt_layout.addStretch()
        layout.addLayout(fmt_layout)

        # 默认选中 TXT
        self._cards[0].set_selected(True)

        # 语言选择 + 开始按钮行
        bottom = QHBoxLayout()

        lang_label = QLabel("识别语言：")
        lang_label.setStyleSheet("font-size: 13px; color: #555;")
        bottom.addWidget(lang_label)

        self._lang_combo = QComboBox()
        for code, name in _LANGUAGES:
            self._lang_combo.addItem(name, code)
        self._lang_combo.setFixedWidth(140)
        bottom.addWidget(self._lang_combo)

        bottom.addStretch()

        self._start_btn = QPushButton("开始转换")
        self._start_btn.setObjectName("startButton")
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._on_start)
        bottom.addWidget(self._start_btn)

        layout.addLayout(bottom)
        layout.addStretch()

    def _on_file_selected(self, path: Path) -> None:
        self._selected_file = path
        self._drop_zone.set_file_info(path)
        self._start_btn.setEnabled(True)

    def _on_format_selected(self, fmt: OutputFormat) -> None:
        self._selected_format = fmt
        for card in self._cards:
            card.set_selected(card._fmt == fmt)

    def _on_start(self) -> None:
        if self._selected_file is None:
            return
        lang = self._lang_combo.currentData()
        self.start_requested.emit(self._selected_file, self._selected_format, lang)
