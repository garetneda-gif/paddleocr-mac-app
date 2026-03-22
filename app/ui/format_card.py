"""格式选择卡片组件 — 图标 + 点击选中带视觉高亮 + hover 浮起。"""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect, QLabel, QVBoxLayout, QWidget,
)

from app.i18n import tr, on_language_changed
from app.models.enums import OutputFormat
from app.ui.theme import (
    ACCENT, ACCENT_BG, BG_PRIMARY, BORDER, TEXT_PRIMARY, TEXT_SECONDARY,
    ANIM_FAST, FORMAT_ICONS, SHADOW_SUBTLE,
)

_FORMAT_INFO: dict[OutputFormat, tuple[str, str]] = {
    OutputFormat.TXT: ("TXT", "fmt_txt"),
    OutputFormat.PDF: ("PDF", "fmt_pdf"),
    OutputFormat.WORD: ("Word", "fmt_word"),
    OutputFormat.HTML: ("HTML", "fmt_html"),
    OutputFormat.EXCEL: ("Excel", "fmt_excel"),
    OutputFormat.RTF: ("RTF", "fmt_rtf"),
}

_NORMAL_STYLE = f"""
    QWidget#formatCard {{
        background-color: {BG_PRIMARY};
        border: 1.5px solid {BORDER};
        border-radius: 10px;
    }}
    QWidget#formatCard:hover {{
        border-color: {ACCENT};
        background-color: #FAFBFF;
    }}
"""

_SELECTED_STYLE = f"""
    QWidget#formatCard {{
        background-color: {ACCENT_BG};
        border: 2px solid {ACCENT};
        border-radius: 10px;
    }}
"""

_ICON_NORMAL = (
    f"font-size: 18px; font-weight: 700; color: {TEXT_SECONDARY}; "
    "background: transparent; border: none;"
)
_ICON_SELECTED = (
    f"font-size: 18px; font-weight: 700; color: {ACCENT}; "
    "background: transparent; border: none;"
)
_TITLE_NORMAL = (
    f"font-size: 13px; font-weight: 600; color: {TEXT_PRIMARY}; "
    "background: transparent; border: none;"
)
_TITLE_SELECTED = (
    f"font-size: 13px; font-weight: 600; color: {ACCENT}; "
    "background: transparent; border: none;"
)
_DESC_NORMAL = (
    f"font-size: 10px; color: {TEXT_SECONDARY}; "
    "background: transparent; border: none;"
)
_DESC_SELECTED = (
    f"font-size: 10px; color: {ACCENT}; "
    "background: transparent; border: none;"
)


class FormatCard(QWidget):
    selected = Signal(OutputFormat)

    def __init__(self, fmt: OutputFormat, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fmt = fmt
        self._is_selected = False
        self.setObjectName("formatCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(100, 80)
        self.setStyleSheet(_NORMAL_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 8, 6, 6)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title, desc_key = _FORMAT_INFO.get(fmt, (fmt.value.upper(), ""))

        # 格式图标
        icon_text = FORMAT_ICONS.get(title, title[0])
        self._icon_label = QLabel(icon_text)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet(_ICON_NORMAL)
        layout.addWidget(self._icon_label)

        # 格式名
        self._title_label = QLabel(title)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet(_TITLE_NORMAL)
        layout.addWidget(self._title_label)

        # 描述
        self._desc_key = desc_key
        self._desc_label = QLabel(tr(desc_key) if desc_key else "")
        self._desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._desc_label.setStyleSheet(_DESC_NORMAL)
        layout.addWidget(self._desc_label)

        # 阴影效果
        self._shadow = QGraphicsDropShadowEffect(self)
        blur, x, y, opacity = SHADOW_SUBTLE
        self._shadow.setBlurRadius(blur)
        self._shadow.setOffset(x, y)
        self._shadow.setColor(QColor(0, 0, 0, int(255 * opacity)))
        self.setGraphicsEffect(self._shadow)

        on_language_changed(self._retranslate)

    def _retranslate(self) -> None:
        if self._desc_key:
            self._desc_label.setText(tr(self._desc_key))

    def mousePressEvent(self, event):
        self.selected.emit(self._fmt)

    def enterEvent(self, event):
        """Hover 时阴影加深。"""
        if not self._is_selected:
            self._shadow.setBlurRadius(14)
            self._shadow.setOffset(0, 3)
            self._shadow.setColor(QColor(0, 0, 0, int(255 * 0.10)))

    def leaveEvent(self, event):
        """离开时恢复阴影。"""
        blur, x, y, opacity = SHADOW_SUBTLE
        self._shadow.setBlurRadius(blur)
        self._shadow.setOffset(x, y)
        self._shadow.setColor(QColor(0, 0, 0, int(255 * opacity)))

    def set_selected(self, is_selected: bool) -> None:
        self._is_selected = is_selected
        if is_selected:
            self.setStyleSheet(_SELECTED_STYLE)
            self._icon_label.setStyleSheet(_ICON_SELECTED)
            self._title_label.setStyleSheet(_TITLE_SELECTED)
            self._desc_label.setStyleSheet(_DESC_SELECTED)
            self._shadow.setBlurRadius(16)
            self._shadow.setOffset(0, 4)
            self._shadow.setColor(QColor(ACCENT))
            self._shadow.setColor(QColor(26, 115, 232, 30))
        else:
            self.setStyleSheet(_NORMAL_STYLE)
            self._icon_label.setStyleSheet(_ICON_NORMAL)
            self._title_label.setStyleSheet(_TITLE_NORMAL)
            self._desc_label.setStyleSheet(_DESC_NORMAL)
            blur, x, y, opacity = SHADOW_SUBTLE
            self._shadow.setBlurRadius(blur)
            self._shadow.setOffset(x, y)
            self._shadow.setColor(QColor(0, 0, 0, int(255 * opacity)))
