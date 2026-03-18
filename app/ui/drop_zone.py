"""拖拽区域组件 — 支持拖入多文件、文件夹和点击多选。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget, QFileDialog

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".pdf"}


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


class DropZone(QWidget):
    file_dropped = Signal(Path)
    files_dropped = Signal(list)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel("拖拽图片、PDF 或文件夹到此处\n或点击选择文件（支持多选）")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("color: #888; font-size: 14px;")
        layout.addWidget(self._label)

    def mousePressEvent(self, event):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择文件（可多选）",
            "",
            "支持的文件 (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.pdf);;所有文件 (*)",
        )
        if paths:
            file_list = [Path(p) for p in paths]
            if len(file_list) == 1:
                self.file_dropped.emit(file_list[0])
            self.files_dropped.emit(file_list)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("#dropZone { border-color: #1A73E8; background-color: #F0F4FF; }")

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")

    def dropEvent(self, event):
        self.setStyleSheet("")
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

    def set_file_info(self, path: Path) -> None:
        self._label.setText(f"已选择: {path.name}\n({path.stat().st_size / 1024:.1f} KB)")

    def set_files_info(self, paths: list[Path]) -> None:
        if len(paths) == 1:
            self.set_file_info(paths[0])
            return
        total_size = sum(p.stat().st_size for p in paths)
        size_mb = total_size / (1024 * 1024)
        self._label.setText(
            f"已选择 {len(paths)} 个文件（共 {size_mb:.1f} MB）\n"
            f"首个: {paths[0].name}"
        )
