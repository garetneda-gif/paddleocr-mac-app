"""左侧导航侧边栏 — 图标 + 指示条选中态 + 滑动动画。"""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QWidget, QLabel, QGraphicsOpacityEffect,
)
from PySide6.QtGui import QPainter, QColor

from app.i18n import tr, on_language_changed
from app.ui.theme import (
    ACCENT, ACCENT_BG, BORDER, BORDER_LIGHT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
    BG_PRIMARY, BG_SECONDARY,
    ANIM_NORMAL,
    NAV_ICONS,
    __version__,
)


_NAV_KEYS = [
    "nav_convert",
    "nav_preview",
    "nav_settings",
]

_NAV_STYLE_NORMAL = (
    "font-size: 13px; font-weight: 500; color: #3C3C43; "
    "background: transparent; border: none;"
)
_NAV_STYLE_CHECKED = (
    f"font-size: 13px; font-weight: 600; color: {ACCENT}; "
    "background: transparent; border: none;"
)
_NAV_ICON_NORMAL = (
    "font-size: 15px; color: #3C3C43; background: transparent; border: none;"
)
_NAV_ICON_CHECKED = (
    f"font-size: 15px; color: {ACCENT}; background: transparent; border: none;"
)


class _NavButton(QWidget):
    """导航按钮 — 固定宽度图标区域 + 文字标签，确保对齐。"""

    clicked = Signal()

    def __init__(self, icon_text: str, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        self._icon_label = QLabel(icon_text)
        self._icon_label.setFixedWidth(20)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet(_NAV_ICON_NORMAL)
        layout.addWidget(self._icon_label)

        self._text_label = QLabel(label)
        self._text_label.setStyleSheet(_NAV_STYLE_NORMAL)
        layout.addWidget(self._text_label)
        layout.addStretch()

    def setChecked(self, checked: bool) -> None:
        self._checked = checked
        if checked:
            self._icon_label.setStyleSheet(_NAV_ICON_CHECKED)
            self._text_label.setStyleSheet(_NAV_STYLE_CHECKED)
            self.setStyleSheet(
                f"_NavButton {{ background-color: {ACCENT_BG}; border-radius: 8px; }}"
            )
        else:
            self._icon_label.setStyleSheet(_NAV_ICON_NORMAL)
            self._text_label.setStyleSheet(_NAV_STYLE_NORMAL)
            self.setStyleSheet("_NavButton { background: transparent; border-radius: 8px; }")

    def isChecked(self) -> bool:
        return self._checked

    def set_label(self, text: str) -> None:
        self._text_label.setText(text)

    def enterEvent(self, event) -> None:
        if not self._checked:
            self.setStyleSheet(
                "_NavButton { background-color: #F2F2F7; border-radius: 8px; }"
            )

    def leaveEvent(self, event) -> None:
        if not self._checked:
            self.setStyleSheet("_NavButton { background: transparent; border-radius: 8px; }")

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class _Indicator(QWidget):
    """侧边栏选中指示条 — 带滑动动画。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(3)
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(ANIM_NORMAL)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def slide_to(self, target: QRect) -> None:
        """滑动到目标按钮的位置。"""
        x = 0
        y = target.y()
        h = target.height()
        new_geo = QRect(x, y, 3, h)
        if self.geometry() == new_geo:
            return
        self._anim.stop()
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(new_geo)
        self._anim.start()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(ACCENT))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 1.5, 1.5)


class Sidebar(QWidget):
    page_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(150)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 18, 10, 18)
        layout.setSpacing(2)

        app_label = QLabel("PaddleOCR")
        app_label.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {ACCENT}; "
            "padding: 6px 8px 2px 8px; letter-spacing: 0.3px;"
        )
        layout.addWidget(app_label)

        ver_label = QLabel(f"v{__version__}")
        ver_label.setStyleSheet(
            f"font-size: 9px; color: {TEXT_TERTIARY}; padding: 0 8px 0 8px;"
        )
        layout.addWidget(ver_label)
        layout.addSpacing(20)

        self._buttons: list[_NavButton] = []
        self._nav_keys = _NAV_KEYS
        for i, key in enumerate(_NAV_KEYS):
            icon = NAV_ICONS.get(key, "")
            btn = _NavButton(icon, tr(key))
            btn.clicked.connect(lambda idx=i: self._on_click(idx))
            layout.addWidget(btn)
            self._buttons.append(btn)

        layout.addStretch()

        # 状态 badge 区
        self._status_label = QLabel()
        self._status_label.setStyleSheet(
            f"font-size: 9px; color: {TEXT_TERTIARY}; padding: 2px 8px;"
        )
        self._status_label.setVisible(False)
        layout.addWidget(self._status_label)

        footer = QLabel("Powered by PP-OCRv5")
        footer.setStyleSheet(
            f"font-size: 9px; color: {BORDER_LIGHT}; padding: 2px 8px;"
        )
        layout.addWidget(footer)

        # 指示条
        self._indicator = _Indicator(self)
        self._indicator.setGeometry(0, 0, 3, 36)

        self._current_index = 0
        self._buttons[0].setChecked(True)

        on_language_changed(self._retranslate)

    def _retranslate(self) -> None:
        for i, key in enumerate(self._nav_keys):
            self._buttons[i].set_label(tr(key))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # 首次显示时定位指示条
        if self._buttons:
            btn = self._buttons[self._current_index]
            self._indicator.setGeometry(0, btn.y(), 3, btn.height())

    def _on_click(self, index: int) -> None:
        if index == self._current_index:
            return
        self._current_index = index
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == index)
        # 滑动指示条
        target_btn = self._buttons[index]
        self._indicator.slide_to(
            QRect(0, target_btn.y(), 3, target_btn.height())
        )
        self.page_changed.emit(index)

    def set_processing(self, active: bool) -> None:
        """转换中时在侧边栏显示状态。"""
        self._status_label.setVisible(active)
        self._status_label.setText(tr("sidebar_processing") if active else "")
