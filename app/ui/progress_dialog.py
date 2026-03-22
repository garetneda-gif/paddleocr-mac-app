"""OCR 进度对话框 — 显示处理阶段、页进度、耗时、速度、取消按钮。"""

from __future__ import annotations

import time

from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from app.i18n import tr
from app.ui.theme import (
    ACCENT, ACCENT_LIGHT, BG_PRIMARY, BG_SECONDARY, BORDER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
)

_DIALOG_STYLE = f"""
    QDialog {{
        background-color: {BG_PRIMARY};
        border-radius: 16px;
    }}
    QLabel#stageLabel {{
        font-size: 15px;
        font-weight: 600;
        color: {TEXT_PRIMARY};
    }}
    QLabel#detailLabel {{
        font-size: 12px;
        color: {TEXT_SECONDARY};
    }}
    QLabel#timerLabel {{
        font-size: 12px;
        color: {TEXT_TERTIARY};
        font-variant-numeric: tabular-nums;
    }}
    QProgressBar {{
        border: none;
        border-radius: 5px;
        background-color: {BORDER};
        text-align: center;
        height: 10px;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {ACCENT}, stop:1 {ACCENT_LIGHT}
        );
        border-radius: 5px;
    }}
    QPushButton#cancelBtn {{
        background-color: {BG_SECONDARY};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 8px 24px;
        font-size: 13px;
        color: {TEXT_SECONDARY};
    }}
    QPushButton#cancelBtn:hover {{
        background-color: {BORDER};
        color: {TEXT_PRIMARY};
    }}
    QPushButton#cancelBtn:disabled {{
        color: {TEXT_TERTIARY};
        background-color: {BORDER};
    }}
"""


def _fmt_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s"


class ProgressDialog(QDialog):
    cancel_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("progress_title"))
        self.setFixedSize(480, 200)
        # 移除关闭按钮和 Windows ? 帮助按钮
        self.setWindowFlags(
            self.windowFlags()
            & ~Qt.WindowType.WindowCloseButtonHint
            & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self.setStyleSheet(_DIALOG_STYLE)

        self._start_time = time.monotonic()
        self._last_page = 0
        self._total_pages = 0
        self._cancelled = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(10)

        self._stage_label = QLabel(tr("progress_init"))
        self._stage_label.setObjectName("stageLabel")
        layout.addWidget(self._stage_label)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        # 详情行：左侧页码，右侧计时
        detail_row = QHBoxLayout()
        self._detail_label = QLabel("")
        self._detail_label.setObjectName("detailLabel")
        detail_row.addWidget(self._detail_label)
        detail_row.addStretch()
        self._timer_label = QLabel("0.0s")
        self._timer_label.setObjectName("timerLabel")
        detail_row.addWidget(self._timer_label)
        layout.addLayout(detail_row)

        # 速度/预估行
        self._speed_label = QLabel("")
        self._speed_label.setObjectName("detailLabel")
        layout.addWidget(self._speed_label)

        self._cancel_btn = QPushButton(tr("progress_cancel"))
        self._cancel_btn.setObjectName("cancelBtn")
        self._cancel_btn.setFixedWidth(100)
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.clicked.connect(self._on_cancel)
        layout.addWidget(self._cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # 每秒刷新计时器
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(500)

    def _tick(self) -> None:
        elapsed = time.monotonic() - self._start_time
        self._timer_label.setText(_fmt_duration(elapsed))

    def update_progress(self, stage: str, page: int, total: int) -> None:
        self._stage_label.setText(stage)
        self._last_page = page
        self._total_pages = total

        if total > 0:
            pct = int(page / total * 100)
            self._progress.setValue(pct)
            self._detail_label.setText(
                tr("progress_page").format(page=page, total=total, pct=pct)
            )

            elapsed = time.monotonic() - self._start_time
            if page > 0 and elapsed > 0.5:
                speed = page / elapsed
                remaining = (total - page) / speed if speed > 0 else 0
                self._speed_label.setText(
                    tr("progress_speed").format(
                        speed=f"{speed:.1f}", remaining=_fmt_duration(remaining)
                    )
                )
            else:
                self._speed_label.setText("")
        else:
            self._progress.setValue(0)
            self._detail_label.setText("")
            self._speed_label.setText("")

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self._start_time

    def _on_cancel(self) -> None:
        if self._cancelled:
            return
        self._cancelled = True
        self._stage_label.setText(tr("progress_cancelling"))
        self._cancel_btn.setEnabled(False)
        self._tick_timer.stop()
        self._progress.setStyleSheet(
            f"QProgressBar {{ background-color: {BORDER}; border: none; border-radius: 5px; height: 10px; }}"
            f"QProgressBar::chunk {{ background-color: {TEXT_TERTIARY}; border-radius: 5px; }}"
        )
        self.cancel_requested.emit()
