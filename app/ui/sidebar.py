"""左侧导航侧边栏。"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget, QLabel


class Sidebar(QWidget):
    page_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(4)

        app_label = QLabel("PaddleOCR")
        app_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1A73E8; padding: 8px;")
        layout.addWidget(app_label)
        layout.addSpacing(16)

        self._buttons: list[QPushButton] = []
        pages = ["转换", "预览", "设置"]
        for i, title in enumerate(pages):
            btn = QPushButton(title)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=i: self._on_click(idx))
            layout.addWidget(btn)
            self._buttons.append(btn)

        layout.addStretch()
        self._buttons[0].setChecked(True)

    def _on_click(self, index: int) -> None:
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == index)
        self.page_changed.emit(index)
