"""拖拽区域组件 — 支持拖入多文件、文件夹、点击多选和剪贴板粘贴图片。"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import Signal, Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QKeySequence, QShortcut, QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QFileDialog

from app.i18n import tr, on_language_changed
from app.ui.theme import (
    ACCENT, BG_PRIMARY, BORDER, BORDER_LIGHT, SUCCESS, SUCCESS_BG,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
    ANIM_NORMAL,
)

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".pdf"}

_EXT_FILTER = " ".join(f"*{e}" for e in sorted(SUPPORTED_EXTENSIONS))


def _collect_files(path: Path) -> list[Path]:
    """收集路径下所有支持的文件（如果是文件夹则递归扫描）。"""
    if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
        return [path]
    if path.is_dir():
        found: list[Path] = []
        for child in sorted(path.rglob("*")):
            if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS:
                found.append(child)
        return found
    return []


_IDLE_STYLE = f"""
    #dropZone {{
        border: 2px dashed {BORDER};
        border-radius: 16px;
        background-color: #FAFAFA;
        min-height: 140px;
    }}
"""

_HOVER_STYLE = f"""
    #dropZone {{
        border: 2.5px solid {ACCENT};
        border-radius: 16px;
        background-color: #EEF4FD;
        min-height: 140px;
    }}
"""

_HAS_FILE_STYLE = f"""
    #dropZone {{
        border: 2px solid {SUCCESS};
        border-radius: 16px;
        background-color: {SUCCESS_BG};
        min-height: 140px;
    }}
"""


class DropZone(QWidget):
    file_dropped = Signal(Path)
    files_dropped = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(_IDLE_STYLE)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)

        # 上传图标区域
        self._icon = QLabel()
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setStyleSheet(
            f"font-size: 36px; color: {BORDER_LIGHT}; background: transparent; border: none;"
        )
        self._icon.setText("\u2191")  # 上箭头
        layout.addWidget(self._icon)

        self._label = QLabel(tr("drop_idle"))
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet(
            f"font-size: 14px; color: {TEXT_SECONDARY}; font-weight: 500; "
            "background: transparent; border: none;"
        )
        layout.addWidget(self._label)

        self._sub = QLabel(tr("drop_sub"))
        self._sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub.setStyleSheet(
            f"font-size: 11px; color: {TEXT_TERTIARY}; background: transparent; border: none;"
        )
        layout.addWidget(self._sub)

        # 剪贴板粘贴快捷键（Cmd+V / Ctrl+V）
        self._paste_shortcut = QShortcut(QKeySequence.StandardKey.Paste, self)
        self._paste_shortcut.activated.connect(self._paste_from_clipboard)

        # 拖入高亮脉冲动画
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(600)
        self._pulse_on = False

        # 当前是否有文件（用于 retranslate 判断状态）
        self._has_file = False

        on_language_changed(self._retranslate)

    def _retranslate(self) -> None:
        if not self._has_file:
            self._label.setText(tr("drop_idle"))
            self._sub.setText(tr("drop_sub"))

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        file_filter = tr("file_filter").format(ext=_EXT_FILTER)
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            tr("drop_select_files"),
            "",
            file_filter,
        )
        if paths:
            file_list = [Path(p) for p in paths]
            if len(file_list) == 1:
                self.file_dropped.emit(file_list[0])
            self.files_dropped.emit(file_list)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(_HOVER_STYLE)
            self._icon.setText("\u2B07")  # 下箭头
            self._icon.setStyleSheet(
                f"font-size: 36px; color: {ACCENT}; background: transparent; border: none;"
            )
            self._label.setText(tr("drop_hover"))
            self._label.setStyleSheet(
                f"font-size: 14px; color: {ACCENT}; font-weight: 600; "
                "background: transparent; border: none;"
            )

    def dragLeaveEvent(self, event):
        self._reset_idle()

    def dropEvent(self, event):
        self._reset_idle()
        all_files: list[Path] = []
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            all_files.extend(_collect_files(path))

        if not all_files:
            return

        # 去重并保持顺序
        seen: set[Path] = set()
        unique: list[Path] = []
        for f in all_files:
            if f not in seen:
                seen.add(f)
                unique.append(f)

        if len(unique) == 1:
            self.file_dropped.emit(unique[0])
        self.files_dropped.emit(unique)

    def _reset_idle(self) -> None:
        """恢复到空闲态。"""
        self._has_file = False
        self.setStyleSheet(_IDLE_STYLE)
        self._icon.setText("\u2191")
        self._icon.setStyleSheet(
            f"font-size: 36px; color: {BORDER_LIGHT}; background: transparent; border: none;"
        )
        self._label.setText(tr("drop_idle"))
        self._label.setStyleSheet(
            f"font-size: 14px; color: {TEXT_SECONDARY}; font-weight: 500; "
            "background: transparent; border: none;"
        )

    def set_file_info(self, path: Path) -> None:
        self._has_file = True
        self.setStyleSheet(_HAS_FILE_STYLE)
        self._icon.setText("\u2713")
        self._icon.setStyleSheet(
            f"font-size: 28px; font-weight: 700; color: {SUCCESS}; background: transparent; border: none;"
        )
        size = path.stat().st_size
        if size > 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        else:
            size_str = f"{size / 1024:.1f} KB"

        # 文件类型标签
        ext = path.suffix.upper().lstrip(".")
        self._label.setText(f"{ext}  {path.name}")
        self._label.setStyleSheet(
            f"font-size: 13px; color: {TEXT_PRIMARY}; font-weight: 600; "
            "background: transparent; border: none;"
        )
        self._sub.setText(tr("drop_reselect").format(size=size_str))
        self._sub.setStyleSheet(
            f"font-size: 11px; color: {TEXT_SECONDARY}; background: transparent; border: none;"
        )

    def _paste_from_clipboard(self) -> None:
        """从剪贴板粘贴图片，保存为临时文件后触发信号。"""
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()

        # 优先检查文件 URL（复制的文件）
        if mime.hasUrls():
            all_files: list[Path] = []
            for url in mime.urls():
                path = Path(url.toLocalFile())
                all_files.extend(_collect_files(path))
            if all_files:
                seen: set[Path] = set()
                unique: list[Path] = []
                for f in all_files:
                    if f not in seen:
                        seen.add(f)
                        unique.append(f)
                if len(unique) == 1:
                    self.file_dropped.emit(unique[0])
                self.files_dropped.emit(unique)
                return

        # 检查剪贴板图片（截图 / 复制的图片）
        image = clipboard.image()
        if image.isNull():
            return

        with tempfile.NamedTemporaryFile(
            suffix=".png", prefix="paddleocr_paste_", delete=False
        ) as f:
            tmp = Path(f.name)
        image.save(str(tmp), "PNG")
        if tmp.exists():
            self.file_dropped.emit(tmp)
            self.files_dropped.emit([tmp])

    def set_files_info(self, paths: list[Path]) -> None:
        if len(paths) == 1:
            self.set_file_info(paths[0])
            return
        self._has_file = True
        self.setStyleSheet(_HAS_FILE_STYLE)
        self._icon.setText("\u2713")
        self._icon.setStyleSheet(
            f"font-size: 28px; font-weight: 700; color: {SUCCESS}; background: transparent; border: none;"
        )
        total_size = sum(p.stat().st_size for p in paths)
        size_mb = total_size / (1024 * 1024)
        self._label.setText(tr("drop_multi_files").format(count=len(paths), size=f"{size_mb:.1f}"))
        self._label.setStyleSheet(
            f"font-size: 13px; color: {TEXT_PRIMARY}; font-weight: 600; "
            "background: transparent; border: none;"
        )
        self._sub.setText(tr("drop_multi_reselect").format(name=paths[0].name))
        self._sub.setStyleSheet(
            f"font-size: 11px; color: {TEXT_SECONDARY}; background: transparent; border: none;"
        )
