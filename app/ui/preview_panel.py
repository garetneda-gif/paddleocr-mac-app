"""OCR 结果预览面板 — 左侧原图 + 右侧识别文本，支持翻页。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models import DocumentResult


class PreviewPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._result: DocumentResult | None = None
        self._page_images: list[QPixmap] = []
        self._current_page: int = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 标题
        title = QLabel("OCR 结果预览")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        # 空状态提示
        self._empty_label = QLabel("完成转换后自动显示预览")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("color: #888; font-size: 14px; padding: 40px;")
        layout.addWidget(self._empty_label)

        # 内容区域（左右分栏）
        self._content = QWidget()
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：原图预览
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)

        left_header = QLabel("原始文档")
        left_header.setStyleSheet("font-size: 13px; font-weight: 600; color: #555;")
        left_layout.addWidget(left_header)

        self._image_scroll = QScrollArea()
        self._image_scroll.setWidgetResizable(True)
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_scroll.setWidget(self._image_label)
        left_layout.addWidget(self._image_scroll, 1)

        splitter.addWidget(left)

        # 右侧：OCR 文本
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 0, 0, 0)

        right_header = QLabel("识别结果")
        right_header.setStyleSheet("font-size: 13px; font-weight: 600; color: #555;")
        right_layout.addWidget(right_header)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setStyleSheet(
            "QTextEdit { font-size: 13px; line-height: 1.6; "
            "border: 1px solid #ddd; border-radius: 4px; padding: 8px; }"
        )
        right_layout.addWidget(self._text_edit, 1)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        content_layout.addWidget(splitter, 1)

        # 底部：翻页导航
        nav = QHBoxLayout()
        nav.addStretch()

        self._prev_btn = QPushButton("上一页")
        self._prev_btn.setFixedWidth(80)
        self._prev_btn.clicked.connect(self._prev_page)
        nav.addWidget(self._prev_btn)

        self._page_label = QLabel("0 / 0")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_label.setFixedWidth(80)
        self._page_label.setStyleSheet("font-size: 13px; color: #555;")
        nav.addWidget(self._page_label)

        self._next_btn = QPushButton("下一页")
        self._next_btn.setFixedWidth(80)
        self._next_btn.clicked.connect(self._next_page)
        nav.addWidget(self._next_btn)

        nav.addStretch()
        content_layout.addLayout(nav)

        self._content.setVisible(False)
        layout.addWidget(self._content, 1)

    def set_result(self, result: DocumentResult) -> None:
        """接收 OCR 结果并显示预览。"""
        self._result = result
        self._current_page = 0
        self._load_page_images()

        self._empty_label.setVisible(False)
        self._content.setVisible(True)
        self._show_page(0)

    def _load_page_images(self) -> None:
        """为每页加载对应的图片。"""
        self._page_images.clear()
        if self._result is None:
            return

        source = self._result.source_path
        is_pdf = source.suffix.lower() == ".pdf"

        if is_pdf:
            try:
                import fitz
                doc = fitz.open(str(source))
                for page in self._result.pages:
                    pi = page.page_index
                    if pi < len(doc):
                        pix = doc[pi].get_pixmap(dpi=150)
                        img = QImage(
                            pix.samples, pix.width, pix.height,
                            pix.stride, QImage.Format.Format_RGB888,
                        )
                        self._page_images.append(QPixmap.fromImage(img))
                    else:
                        self._page_images.append(QPixmap())
                doc.close()
            except Exception:
                for _ in self._result.pages:
                    self._page_images.append(QPixmap())
        else:
            # 图片输入
            pix = QPixmap(str(source))
            for _ in self._result.pages:
                self._page_images.append(pix)

    def _show_page(self, idx: int) -> None:
        """显示指定页。"""
        if self._result is None or not self._result.pages:
            return

        total = len(self._result.pages)
        idx = max(0, min(idx, total - 1))
        self._current_page = idx

        # 更新页码
        self._page_label.setText(f"{idx + 1} / {total}")
        self._prev_btn.setEnabled(idx > 0)
        self._next_btn.setEnabled(idx < total - 1)

        # 左侧图片
        if idx < len(self._page_images) and not self._page_images[idx].isNull():
            scaled = self._page_images[idx].scaledToWidth(
                max(400, self._image_scroll.width() - 30),
                Qt.TransformationMode.SmoothTransformation,
            )
            self._image_label.setPixmap(scaled)
        else:
            self._image_label.setText("无法加载预览图")

        # 右侧文本
        page_result = self._result.pages[idx]
        text_parts: list[str] = []
        for block in page_result.blocks:
            if block.text:
                text_parts.append(block.text)
        self._text_edit.setPlainText("\n\n".join(text_parts))

    def _prev_page(self) -> None:
        self._show_page(self._current_page - 1)

    def _next_page(self) -> None:
        self._show_page(self._current_page + 1)

    def clear(self) -> None:
        self._result = None
        self._page_images.clear()
        self._current_page = 0
        self._empty_label.setVisible(True)
        self._content.setVisible(False)
        self._image_label.clear()
        self._text_edit.clear()
