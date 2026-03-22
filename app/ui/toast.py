"""Toast 通知组件 — 替代 QMessageBox，底部/顶部滑入消息。"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from app.ui.theme import (
    ACCENT, ACCENT_BG,
    BG_PRIMARY, BORDER,
    DANGER, SUCCESS, SUCCESS_BG, WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
    ANIM_NORMAL, ANIM_SLOW,
    SHADOW_MEDIUM,
)


class Toast(QWidget):
    """浮动通知 Toast，显示在父组件底部，自动消失或手动关闭。"""

    # 跟踪当前显示的 Toast，避免重叠
    _active_toast: Toast | None = None

    def __init__(
        self,
        parent: QWidget,
        message: str,
        level: str = "info",
        duration: int = 4000,
        action_text: str = "",
        action_callback=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setObjectName("toastWidget")
        self.setFixedHeight(52)

        # 配色
        colors = {
            "success": (SUCCESS, SUCCESS_BG, "#1B5E20"),
            "error": (DANGER, "#FFF0F0", DANGER),
            "warning": (WARNING, "#FFF8E1", "#E65100"),
            "info": (ACCENT, ACCENT_BG, ACCENT),
        }
        border_color, bg_color, text_color = colors.get(level, colors["info"])

        self.setStyleSheet(
            f"#toastWidget {{ background-color: {bg_color}; border: 1px solid {border_color}; "
            f"border-radius: 10px; }}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        # 指示条
        indicator = QWidget()
        indicator.setFixedSize(4, 28)
        indicator.setStyleSheet(f"background-color: {border_color}; border-radius: 2px;")
        layout.addWidget(indicator)

        # 消息文本
        label = QLabel(message)
        label.setStyleSheet(
            f"font-size: 13px; font-weight: 500; color: {text_color}; "
            "background: transparent; border: none;"
        )
        label.setWordWrap(True)
        layout.addWidget(label, 1)

        # 操作按钮
        if action_text and action_callback:
            action_btn = QPushButton(action_text)
            action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            action_btn.setStyleSheet(
                f"QPushButton {{ background-color: {border_color}; color: white; "
                f"border: none; border-radius: 6px; padding: 4px 12px; "
                f"font-size: 12px; font-weight: 500; }}"
                f"QPushButton:hover {{ opacity: 0.9; }}"
            )
            action_btn.clicked.connect(action_callback)
            action_btn.clicked.connect(self._dismiss)
            layout.addWidget(action_btn)

        # 关闭按钮
        close_btn = QPushButton("x")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {TEXT_TERTIARY}; "
            f"border: none; font-size: 14px; font-weight: 600; }}"
            f"QPushButton:hover {{ color: {TEXT_PRIMARY}; }}"
        )
        close_btn.clicked.connect(self._dismiss)
        layout.addWidget(close_btn)

        # 阴影
        shadow = QGraphicsDropShadowEffect(self)
        blur, x, y, opacity = SHADOW_MEDIUM
        shadow.setBlurRadius(blur)
        shadow.setOffset(x, y)
        shadow.setColor(QColor(0, 0, 0, int(255 * opacity)))
        self.setGraphicsEffect(shadow)

        # 自动消失定时器
        self._auto_close = QTimer(self)
        self._auto_close.setSingleShot(True)
        if duration > 0:
            self._auto_close.timeout.connect(self._dismiss)
            self._auto_close.start(duration)

    def show_toast(self) -> None:
        """定位到父组件底部并滑入显示。"""
        # 先关闭已有的 Toast
        if Toast._active_toast is not None:
            try:
                Toast._active_toast.deleteLater()
            except RuntimeError:
                pass
        Toast._active_toast = self

        parent = self.parentWidget()
        if not parent:
            self.show()
            return

        w = min(parent.width() - 40, 600)
        self.setFixedWidth(w)
        x = (parent.width() - w) // 2
        y_target = parent.height() - self.height() - 20
        y_start = parent.height() + 10

        self.move(x, y_start)
        self.show()
        self.raise_()

        self._slide_anim = QPropertyAnimation(self, b"pos")
        self._slide_anim.setDuration(ANIM_NORMAL)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide_anim.setStartValue(QPoint(x, y_start))
        self._slide_anim.setEndValue(QPoint(x, y_target))
        self._slide_anim.start()

    def _dismiss(self) -> None:
        """滑出并销毁。"""
        self._auto_close.stop()
        parent = self.parentWidget()
        if not parent:
            self.deleteLater()
            return

        x = self.x()
        y_end = parent.height() + 10

        anim = QPropertyAnimation(self, b"pos")
        anim.setDuration(ANIM_NORMAL)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.setStartValue(self.pos())
        anim.setEndValue(QPoint(x, y_end))
        anim.finished.connect(self.deleteLater)
        anim.start()
        self._dismiss_anim = anim  # prevent GC


def show_toast(
    parent: QWidget,
    message: str,
    level: str = "info",
    duration: int = 4000,
    action_text: str = "",
    action_callback=None,
) -> Toast:
    """便捷函数：创建并显示一个 Toast。"""
    toast = Toast(parent, message, level, duration, action_text, action_callback)
    toast.show_toast()
    return toast
