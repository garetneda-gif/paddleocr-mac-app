"""格式选择卡片组件 — 点击选中带视觉高亮。"""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.models.enums import OutputFormat

_FORMAT_INFO: dict[OutputFormat, tuple[str, str]] = {
    OutputFormat.TXT: ("TXT", "纯文本"),
    OutputFormat.PDF: ("PDF", "可搜索 PDF"),
    OutputFormat.WORD: ("Word", "保留版面结构"),
    OutputFormat.HTML: ("HTML", "网页格式"),
    OutputFormat.EXCEL: ("Excel", "表格数据"),
    OutputFormat.RTF: ("RTF", "富文本格式"),
}

_NORMAL_STYLE = """
    QWidget#formatCard {
        background-color: #FFFFFF;
        border: 2px solid #E0E0E0;
        border-radius: 12px;
    }
    QWidget#formatCard:hover {
        border-color: #1A73E8;
    }
"""

_SELECTED_STYLE = """
    QWidget#formatCard {
        background-color: #E8F0FE;
        border: 2px solid #1A73E8;
        border-radius: 12px;
    }
"""


class FormatCard(QWidget):
    selected = Signal(OutputFormat)

    def __init__(self, fmt: OutputFormat, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fmt = fmt
        self._is_selected = False
        self.setObjectName("formatCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(105, 72)
        self.setStyleSheet(_NORMAL_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title, desc = _FORMAT_INFO.get(fmt, (fmt.value.upper(), ""))
        self._title_label = QLabel(title)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; background: transparent; border: none;")
        layout.addWidget(self._title_label)

        self._desc_label = QLabel(desc)
        self._desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._desc_label.setStyleSheet("font-size: 11px; color: #888; background: transparent; border: none;")
        layout.addWidget(self._desc_label)

    def mousePressEvent(self, event):
        self.selected.emit(self._fmt)

    def set_selected(self, is_selected: bool) -> None:
        self._is_selected = is_selected
        if is_selected:
            self.setStyleSheet(_SELECTED_STYLE)
            self._title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1A73E8; background: transparent; border: none;")
        else:
            self.setStyleSheet(_NORMAL_STYLE)
            self._title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; background: transparent; border: none;")
