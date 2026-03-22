"""OCR 结果预览面板 — 左侧原图 + 右侧识别文本，支持翻页、缩放和搜索。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal as _Signal
from PySide6.QtGui import (
    QPixmap, QImage, QFont, QColor, QKeySequence, QShortcut, QTextCharFormat,
)
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.i18n import tr, on_language_changed
from app.models import DocumentResult
from app.ui.theme import (
    ACCENT, ACCENT_BG, ACCENT_HOVER,
    BG_PRIMARY, BG_SECONDARY, BG_SUNKEN, BORDER, BORDER_SUBTLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
    RADIUS, RADIUS_SM,
    SHADOW_SUBTLE, SHADOW_MEDIUM,
    FONT_FAMILY,
    ANIM_FAST,
)


# ── 样式常量 ──

_TOOLBAR_STYLE = f"""
    background-color: {BG_PRIMARY};
    border: 1px solid {BORDER_SUBTLE};
    border-radius: 10px;
"""

_NAV_BTN_STYLE = f"""
    QPushButton {{
        background-color: transparent;
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 5px 10px;
        font-size: 13px;
        font-weight: 500;
        color: {TEXT_PRIMARY};
        min-width: 28px;
    }}
    QPushButton:hover {{
        background-color: {ACCENT_BG};
        border-color: {ACCENT};
        color: {ACCENT};
    }}
    QPushButton:disabled {{
        color: {TEXT_TERTIARY};
        border-color: {BORDER_SUBTLE};
        background-color: transparent;
    }}
"""

_TEXT_EDIT_STYLE = f"""
    QTextEdit {{
        font-size: 14px;
        line-height: 1.8;
        color: {TEXT_PRIMARY};
        background-color: {BG_PRIMARY};
        border: none;
        border-radius: 8px;
        padding: 16px;
        selection-background-color: {ACCENT_BG};
    }}
"""

_SCROLL_AREA_STYLE = f"""
    QScrollArea {{
        background-color: {BG_SUNKEN};
        border: none;
        border-radius: 8px;
    }}
    QScrollArea > QWidget > QWidget {{
        background-color: {BG_SUNKEN};
    }}
"""

_COPY_BTN_STYLE = f"""
    QPushButton {{
        background-color: {ACCENT};
        border: none;
        border-radius: 6px;
        padding: 4px 14px;
        font-size: 12px;
        font-weight: 500;
        color: white;
    }}
    QPushButton:hover {{
        background-color: {ACCENT_HOVER};
    }}
"""

_SEARCH_STYLE = f"""
    QLineEdit {{
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 3px 8px;
        font-size: 12px;
        background-color: {BG_PRIMARY};
        color: {TEXT_PRIMARY};
    }}
    QLineEdit:focus {{
        border-color: {ACCENT};
    }}
"""


def _apply_shadow(widget: QWidget, params: tuple) -> None:
    """给 widget 添加阴影效果。"""
    blur, x, y, opacity = params
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(x, y)
    shadow.setColor(QColor(0, 0, 0, int(255 * opacity)))
    widget.setGraphicsEffect(shadow)


# ── 异步图片加载线程 ──

class _PageImageLoader(QThread):
    """后台加载页面图片，避免大 PDF 冻结 UI。"""

    finished = _Signal(list)  # list[QPixmap]

    def __init__(self, source: Path, pages: list, parent=None):
        super().__init__(parent)
        self._source = source
        self._pages = pages

    def run(self):
        images: list[QPixmap] = []
        is_pdf = self._source.suffix.lower() == ".pdf"

        if is_pdf:
            try:
                import fitz
                doc = fitz.open(str(self._source))
                for page in self._pages:
                    pi = page.page_index
                    if pi < len(doc):
                        pix = doc[pi].get_pixmap(dpi=150)
                        img = QImage(
                            pix.samples, pix.width, pix.height,
                            pix.stride, QImage.Format.Format_RGB888,
                        )
                        images.append(QPixmap.fromImage(img))
                    else:
                        images.append(QPixmap())
                doc.close()
            except Exception:
                for _ in self._pages:
                    images.append(QPixmap())
        else:
            pix = QPixmap(str(self._source))
            for _ in self._pages:
                images.append(pix)

        self.finished.emit(images)


class PreviewPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BG_SECONDARY};")

        self._result: DocumentResult | None = None
        self._page_images: list[QPixmap] = []
        self._scaled_cache: dict[int, tuple[int, QPixmap]] = {}
        self._current_page: int = 0
        self._loader: _PageImageLoader | None = None
        self._zoom_factor: float = 1.0
        self._font_size: int = 14

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(12)

        # ── 空状态占位 ──
        self._empty_widget = QWidget()
        self._empty_widget.setStyleSheet(f"background-color: {BG_SECONDARY};")
        empty_layout = QVBoxLayout(self._empty_widget)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        empty_layout.addStretch(2)

        self._empty_title = QLabel(tr("preview_title"))
        self._empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_title.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {TEXT_PRIMARY}; background: transparent;"
        )
        empty_layout.addWidget(self._empty_title)
        empty_layout.addSpacing(6)

        self._empty_sub = QLabel(tr("preview_empty_sub"))
        self._empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_sub.setStyleSheet(
            f"font-size: 14px; color: {TEXT_SECONDARY}; background: transparent;"
        )
        empty_layout.addWidget(self._empty_sub)
        empty_layout.addSpacing(20)

        self._step_labels: list[QLabel] = []
        for key in ("preview_step_1", "preview_step_2", "preview_step_3"):
            step = QLabel(tr(key))
            step.setAlignment(Qt.AlignmentFlag.AlignCenter)
            step.setStyleSheet(
                f"font-size: 13px; color: {TEXT_TERTIARY}; background: transparent; "
                "padding: 2px 0;"
            )
            empty_layout.addWidget(step)
            self._step_labels.append(step)

        # 空状态快捷按钮
        empty_layout.addSpacing(20)
        self._start_btn = QPushButton(tr("preview_start_btn"))
        self._start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_btn.setStyleSheet(
            f"QPushButton {{ background-color: {ACCENT}; color: white; "
            f"border: none; border-radius: 8px; padding: 10px 24px; "
            f"font-size: 14px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}"
        )
        self._start_btn.setFixedWidth(200)
        self._start_btn.clicked.connect(self._go_to_convert)
        empty_layout.addWidget(self._start_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        empty_layout.addStretch(3)
        layout.addWidget(self._empty_widget, 1)

        # ── 内容区域 ──
        self._content = QWidget()
        self._content.setStyleSheet(f"background-color: {BG_SECONDARY};")
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        # 顶部工具栏
        toolbar = QWidget()
        toolbar.setStyleSheet(_TOOLBAR_STYLE)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(14, 8, 14, 8)
        toolbar_layout.setSpacing(8)

        self._title_label = QLabel(tr("preview_title"))
        self._title_label.setStyleSheet(
            f"font-size: 15px; font-weight: 600; color: {TEXT_PRIMARY}; "
            "background: transparent; border: none;"
        )
        toolbar_layout.addWidget(self._title_label)

        self._page_badge = QLabel()
        self._page_badge.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {ACCENT}; "
            f"background-color: {ACCENT_BG}; border-radius: 4px; "
            "padding: 2px 8px; border: none;"
        )
        self._page_badge.setVisible(False)
        toolbar_layout.addWidget(self._page_badge)

        toolbar_layout.addStretch()

        # 搜索框
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText(tr("preview_search_placeholder"))
        self._search_input.setStyleSheet(_SEARCH_STYLE)
        self._search_input.setFixedWidth(160)
        self._search_input.setVisible(False)
        self._search_input.textChanged.connect(self._on_search)
        toolbar_layout.addWidget(self._search_input)

        self._search_btn = QPushButton(tr("preview_search_btn"))
        self._search_btn.setStyleSheet(_NAV_BTN_STYLE)
        self._search_btn.setFixedSize(48, 28)
        self._search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._search_btn.clicked.connect(self._toggle_search)
        toolbar_layout.addWidget(self._search_btn)

        # 字数统计
        self._char_count_label = QLabel()
        self._char_count_label.setStyleSheet(
            f"font-size: 11px; color: {TEXT_TERTIARY}; "
            "border: none; background: transparent;"
        )
        toolbar_layout.addWidget(self._char_count_label)

        # 复制全文按钮
        self._copy_btn = QPushButton(tr("preview_copy_all"))
        self._copy_btn.setStyleSheet(_COPY_BTN_STYLE)
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.clicked.connect(self._copy_all_text)
        toolbar_layout.addWidget(self._copy_btn)

        # 分隔线
        sep = QWidget()
        sep.setFixedSize(1, 20)
        sep.setStyleSheet(f"background-color: {BORDER}; border: none;")
        toolbar_layout.addWidget(sep)

        # 翻页导航
        self._prev_btn = QPushButton("<")
        self._prev_btn.setStyleSheet(_NAV_BTN_STYLE)
        self._prev_btn.setFixedSize(32, 28)
        self._prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._prev_btn.clicked.connect(self._prev_page)
        toolbar_layout.addWidget(self._prev_btn)

        self._page_label = QLabel("0 / 0")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_label.setFixedWidth(52)
        self._page_label.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {TEXT_SECONDARY}; "
            "background: transparent; border: none;"
        )
        toolbar_layout.addWidget(self._page_label)

        self._next_btn = QPushButton(">")
        self._next_btn.setStyleSheet(_NAV_BTN_STYLE)
        self._next_btn.setFixedSize(32, 28)
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.clicked.connect(self._next_page)
        toolbar_layout.addWidget(self._next_btn)

        _apply_shadow(toolbar, SHADOW_SUBTLE)
        content_layout.addWidget(toolbar)

        # 分栏
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)

        # 左侧：原图预览
        left_card = QWidget()
        left_card.setStyleSheet(
            f"background-color: {BG_PRIMARY}; border: 1px solid {BORDER_SUBTLE}; "
            f"border-radius: {RADIUS};"
        )
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(4)

        self._image_scroll = QScrollArea()
        self._image_scroll.setWidgetResizable(True)
        self._image_scroll.setStyleSheet(_SCROLL_AREA_STYLE)
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("background: transparent; padding: 4px;")
        self._image_scroll.setWidget(self._image_label)
        left_layout.addWidget(self._image_scroll, 1)

        # 缩放指示器
        zoom_row = QHBoxLayout()
        zoom_row.setContentsMargins(4, 0, 4, 0)
        zoom_out_btn = QPushButton("-")
        zoom_out_btn.setFixedSize(24, 24)
        zoom_out_btn.setStyleSheet(_NAV_BTN_STYLE)
        zoom_out_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        zoom_out_btn.clicked.connect(self._zoom_out)
        zoom_row.addWidget(zoom_out_btn)

        self._zoom_label = QLabel("100%")
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_label.setFixedWidth(50)
        self._zoom_label.setStyleSheet(
            f"font-size: 11px; color: {TEXT_TERTIARY}; background: transparent; border: none;"
        )
        zoom_row.addWidget(self._zoom_label)

        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(24, 24)
        zoom_in_btn.setStyleSheet(_NAV_BTN_STYLE)
        zoom_in_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        zoom_in_btn.clicked.connect(self._zoom_in)
        zoom_row.addWidget(zoom_in_btn)

        self._zoom_fit_btn = QPushButton(tr("preview_zoom_fit"))
        self._zoom_fit_btn.setFixedSize(40, 24)
        self._zoom_fit_btn.setStyleSheet(_NAV_BTN_STYLE)
        self._zoom_fit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._zoom_fit_btn.clicked.connect(self._zoom_fit)
        zoom_row.addWidget(self._zoom_fit_btn)

        zoom_row.addStretch()
        left_layout.addLayout(zoom_row)

        _apply_shadow(left_card, SHADOW_SUBTLE)
        splitter.addWidget(left_card)

        # 右侧：OCR 文本
        right_card = QWidget()
        right_card.setStyleSheet(
            f"background-color: {BG_PRIMARY}; border: 1px solid {BORDER_SUBTLE}; "
            f"border-radius: {RADIUS};"
        )
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(0)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setStyleSheet(_TEXT_EDIT_STYLE)
        font = QFont()
        font.setFamilies(["PingFang SC", "SF Pro Text", "Helvetica Neue", "sans-serif"])
        font.setPointSize(self._font_size)
        self._text_edit.setFont(font)
        right_layout.addWidget(self._text_edit, 1)

        _apply_shadow(right_card, SHADOW_SUBTLE)
        splitter.addWidget(right_card)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        content_layout.addWidget(splitter, 1)

        self._content.setVisible(False)
        layout.addWidget(self._content, 1)

        # 键盘快捷键
        self._setup_shortcuts()

        on_language_changed(self._retranslate)

    def _retranslate(self) -> None:
        self._empty_title.setText(tr("preview_title"))
        self._empty_sub.setText(tr("preview_empty_sub"))
        step_keys = ("preview_step_1", "preview_step_2", "preview_step_3")
        for label, key in zip(self._step_labels, step_keys):
            label.setText(tr(key))
        self._start_btn.setText(tr("preview_start_btn"))
        self._title_label.setText(tr("preview_title"))
        self._search_input.setPlaceholderText(tr("preview_search_placeholder"))
        self._search_btn.setText(tr("preview_search_btn"))
        self._copy_btn.setText(tr("preview_copy_all"))
        self._zoom_fit_btn.setText(tr("preview_zoom_fit"))

    def _setup_shortcuts(self) -> None:
        """设置键盘快捷键。"""
        left = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        left.activated.connect(self._prev_page)
        right = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        right.activated.connect(self._next_page)

        find = QShortcut(QKeySequence.StandardKey.Find, self)
        find.activated.connect(self._toggle_search)

        zoom_in = QShortcut(QKeySequence.StandardKey.ZoomIn, self)
        zoom_in.activated.connect(self._increase_font)
        zoom_out = QShortcut(QKeySequence.StandardKey.ZoomOut, self)
        zoom_out.activated.connect(self._decrease_font)

    def _go_to_convert(self) -> None:
        """跳转到转换页。"""
        window = self.window()
        if hasattr(window, "_sidebar") and hasattr(window, "_stack"):
            window._sidebar._on_click(0)
            window._stack.setCurrentIndex(0)

    def _stop_loader(self) -> None:
        """安全停止旧的图片加载线程。"""
        if self._loader is not None:
            self._loader.finished.disconnect()
            self._loader.quit()
            self._loader.wait(2000)
            self._loader = None

    def set_result(self, result: DocumentResult) -> None:
        """接收 OCR 结果并显示预览。"""
        self._stop_loader()
        self._page_images.clear()
        self._scaled_cache.clear()

        self._result = result
        self._current_page = 0
        self._zoom_factor = 1.0

        # 异步加载页面图片
        self._page_images = [QPixmap()] * len(result.pages)
        self._image_label.setText(tr("preview_loading"))
        self._image_label.setStyleSheet(
            f"color: {TEXT_TERTIARY}; font-size: 14px; background: transparent;"
        )

        self._loader = _PageImageLoader(result.source_path, result.pages, self)
        self._loader.finished.connect(self._on_images_loaded)
        self._loader.start()

        self._empty_widget.setVisible(False)
        self._content.setVisible(True)

        total = len(result.pages) if result.pages else 0
        if total > 1:
            self._page_badge.setText(tr("preview_pages").format(count=total))
            self._page_badge.setVisible(True)
        else:
            self._page_badge.setVisible(False)

        self._show_page(0)

    def _on_images_loaded(self, images: list[QPixmap]) -> None:
        """图片加载完成回调。"""
        self._page_images = images
        self._loader = None
        self._show_page(self._current_page)

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

        # 单页时隐藏翻页按钮但保留页码标签
        single = total <= 1
        self._prev_btn.setVisible(not single)
        self._next_btn.setVisible(not single)

        # 左侧图片
        self._update_image()

        # 右侧文本
        page_result = self._result.pages[idx]
        text_parts: list[str] = []
        for block in page_result.blocks:
            if block.text:
                text_parts.append(block.text)
        full_text = "\n\n".join(text_parts)
        self._text_edit.setPlainText(full_text)

        # 滚动到顶部
        self._text_edit.verticalScrollBar().setValue(0)

        # 字符统计
        char_count = len(full_text.replace("\n", "").replace(" ", ""))
        total_chars = sum(
            len(b.text.replace("\n", "").replace(" ", ""))
            for p in self._result.pages for b in p.blocks if b.text
        )
        self._char_count_label.setText(
            tr("preview_char_count").format(page_chars=char_count, total_chars=total_chars)
        )

    def _update_image(self) -> None:
        """根据当前缩放更新图片显示。"""
        idx = self._current_page
        if idx < len(self._page_images) and not self._page_images[idx].isNull():
            base_w = max(400, self._image_scroll.width() - 30)
            target_w = int(base_w * self._zoom_factor)
            scaled = self._page_images[idx].scaledToWidth(
                target_w,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._image_label.setPixmap(scaled)
            self._zoom_label.setText(f"{int(self._zoom_factor * 100)}%")
        else:
            self._image_label.setText(tr("preview_loading"))
            self._image_label.setStyleSheet(
                f"color: {TEXT_TERTIARY}; font-size: 14px; background: transparent;"
            )

    def _zoom_in(self) -> None:
        self._zoom_factor = min(3.0, self._zoom_factor + 0.2)
        self._update_image()

    def _zoom_out(self) -> None:
        self._zoom_factor = max(0.3, self._zoom_factor - 0.2)
        self._update_image()

    def _zoom_fit(self) -> None:
        self._zoom_factor = 1.0
        self._update_image()

    def _toggle_search(self) -> None:
        """切换搜索框显示。"""
        visible = not self._search_input.isVisible()
        self._search_input.setVisible(visible)
        if visible:
            self._search_input.setFocus()
        else:
            self._search_input.clear()

    def _on_search(self, text: str) -> None:
        """搜索高亮。"""
        cursor = self._text_edit.textCursor()
        cursor.select(cursor.SelectionType.Document)
        fmt_normal = QTextCharFormat()
        cursor.setCharFormat(fmt_normal)
        cursor.clearSelection()
        self._text_edit.setTextCursor(cursor)

        if not text:
            return

        fmt_highlight = QTextCharFormat()
        fmt_highlight.setBackground(QColor(ACCENT_BG))
        fmt_highlight.setForeground(QColor(ACCENT))

        doc = self._text_edit.document()
        cursor = doc.find(text)
        first = True
        while not cursor.isNull():
            cursor.mergeCharFormat(fmt_highlight)
            if first:
                self._text_edit.setTextCursor(cursor)
                first = False
            cursor = doc.find(text, cursor)

    def _increase_font(self) -> None:
        self._font_size = min(28, self._font_size + 1)
        font = self._text_edit.font()
        font.setPointSize(self._font_size)
        self._text_edit.setFont(font)

    def _decrease_font(self) -> None:
        self._font_size = max(10, self._font_size - 1)
        font = self._text_edit.font()
        font.setPointSize(self._font_size)
        self._text_edit.setFont(font)

    def _copy_all_text(self) -> None:
        """复制所有页的 OCR 文本到剪贴板。"""
        if self._result is None:
            return
        all_texts: list[str] = []
        for page in self._result.pages:
            for block in page.blocks:
                if block.text:
                    all_texts.append(block.text)
        QApplication.clipboard().setText("\n\n".join(all_texts))
        self._copy_btn.setText(tr("preview_copied"))
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self._copy_btn.setText(tr("preview_copy_all")))

    def _prev_page(self) -> None:
        self._show_page(self._current_page - 1)

    def _next_page(self) -> None:
        self._show_page(self._current_page + 1)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._scaled_cache.clear()

    def clear(self) -> None:
        self._stop_loader()
        self._result = None
        self._page_images.clear()
        self._scaled_cache.clear()
        self._current_page = 0
        self._empty_widget.setVisible(True)
        self._content.setVisible(False)
        self._image_label.clear()
        self._text_edit.clear()
        self._char_count_label.clear()
        self._page_badge.setVisible(False)
