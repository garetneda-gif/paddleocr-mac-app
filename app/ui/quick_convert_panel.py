"""转换面板 — 文件选择 + 格式 + 语言 + 按当前后端生效的高级选项。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtCore import QTimer

from app.i18n import tr, on_language_changed
from app.i18n.widgets import TrLabel
from app.models.enums import OutputFormat
from app.ui.drop_zone import DropZone
from app.ui.format_card import FormatCard
from app.ui.theme import ACCENT, TEXT_SECONDARY, WARNING
from app.utils.language_map import LANGUAGES


def _hint(key: str) -> TrLabel:
    """创建自动翻译的灰色小字说明标签。"""
    lbl = TrLabel(key)
    lbl.setWordWrap(True)
    lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY}; margin-left: 24px;")
    return lbl


def _spin_row(key: str, spin: QSpinBox | QDoubleSpinBox, suffix: str = "") -> QHBoxLayout:
    row = QHBoxLayout()
    row.addWidget(TrLabel(key))
    spin.setFixedWidth(90)
    row.addWidget(spin)
    if suffix:
        row.addWidget(QLabel(suffix))
    row.addStretch()
    return row


class QuickConvertPanel(QWidget):
    start_requested = Signal(Path, OutputFormat, str)
    batch_start_requested = Signal(list, OutputFormat, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._selected_file: Path | None = None
        self._selected_files: list[Path] = []
        self._selected_format: OutputFormat = OutputFormat.TXT
        self._paddle_ok = False
        self._server_onnx_ok = False
        self._onnx_langs: set[str] = {"ch", "en"}

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setAcceptDrops(True)
        scroll.viewport().setAcceptDrops(True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        self._title_label = TrLabel("convert_title")
        self._title_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {ACCENT};")
        layout.addWidget(self._title_label)

        # ── 拖拽区域 ──
        self._drop_zone = DropZone()
        self._drop_zone.file_dropped.connect(self._on_file_selected)
        self._drop_zone.files_dropped.connect(self._on_files_selected)
        layout.addWidget(self._drop_zone)

        # ── 格式卡片 ──
        self._fmt_label = TrLabel("select_output_format")
        self._fmt_label.setStyleSheet(f"font-size: 13px; color: {TEXT_SECONDARY};")
        layout.addWidget(self._fmt_label)

        fmt_layout = QHBoxLayout()
        fmt_layout.setSpacing(10)
        self._cards: list[FormatCard] = []
        for fmt in OutputFormat:
            card = FormatCard(fmt)
            card.selected.connect(self._on_format_selected)
            fmt_layout.addWidget(card)
            self._cards.append(card)
        fmt_layout.addStretch()
        layout.addLayout(fmt_layout)
        self._cards[0].set_selected(True)

        # ── 语言 + 开始 ──
        bottom = QHBoxLayout()
        bottom.addWidget(TrLabel("ocr_language"))
        self._lang_combo = QComboBox()
        for code, name in LANGUAGES.items():
            self._lang_combo.addItem(name, code)
        self._lang_combo.setFixedWidth(200)
        bottom.addWidget(self._lang_combo)
        bottom.addSpacing(20)
        bottom.addWidget(TrLabel("mode_label"))
        self._speed_combo = QComboBox()
        self._speed_combo.addItem(tr("mode_balanced"), "server")
        self._speed_combo.addItem(tr("mode_speed"), "mobile")
        self._speed_combo.setFixedWidth(260)
        self._speed_combo.setToolTip(tr("mode_tooltip"))
        bottom.addWidget(self._speed_combo)

        bottom.addStretch()
        self._start_btn = QPushButton(tr("start_convert"))
        self._start_btn.setObjectName("startButton")
        self._start_btn.setEnabled(False)
        self._start_btn.setToolTip(tr("select_file_first"))
        self._start_btn.clicked.connect(self._on_start)
        bottom.addWidget(self._start_btn)
        layout.addLayout(bottom)

        # ── 并行 + 强制 OCR ──
        parallel_row = QHBoxLayout()
        parallel_row.addWidget(TrLabel("parallel_workers"))
        self._parallel_spin = QSpinBox()
        self._parallel_spin.setRange(1, 4)
        self._parallel_spin.setValue(2)
        self._parallel_spin.setFixedWidth(60)
        self._parallel_spin.setToolTip(tr("parallel_tooltip"))
        parallel_row.addWidget(self._parallel_spin)
        parallel_row.addSpacing(20)

        self._force_ocr_check = QCheckBox(tr("force_ocr"))
        self._force_ocr_check.setToolTip(tr("force_ocr_tooltip"))
        parallel_row.addWidget(self._force_ocr_check)
        parallel_row.addStretch()
        layout.addLayout(parallel_row)

        # ── PDF 页码范围 ──
        page_row = QHBoxLayout()
        page_row.addWidget(TrLabel("pdf_page_range"))
        self._page_start = QSpinBox()
        self._page_start.setRange(1, 9999)
        self._page_start.setValue(1)
        self._page_start.setFixedWidth(80)
        page_row.addWidget(self._page_start)
        page_row.addWidget(QLabel(" ~ "))
        self._page_end = QSpinBox()
        self._page_end.setRange(1, 9999)
        self._page_end.setValue(9999)
        self._page_end.setFixedWidth(80)
        page_row.addWidget(self._page_end)
        page_row.addWidget(_hint("pdf_page_hint"))
        page_row.addStretch()
        layout.addLayout(page_row)

        # ━━━ 折叠高级选项 ━━━
        self._adv_toggle = QPushButton(tr("advanced_collapsed"))
        self._adv_toggle.setStyleSheet(
            f"QPushButton {{ border: none; color: {ACCENT}; font-size: 13px; "
            "text-align: left; padding: 4px 0; } "
            "QPushButton:hover { text-decoration: underline; }"
        )
        self._adv_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._adv_toggle.clicked.connect(self._toggle_advanced)
        layout.addWidget(self._adv_toggle)

        self._adv_widget = QWidget()
        self._adv_widget.setVisible(False)
        adv = QVBoxLayout(self._adv_widget)
        adv.setContentsMargins(0, 4, 0, 8)
        adv.setSpacing(12)

        # ─── 1. Pipeline ───
        self._pipeline_group = QGroupBox(tr("pipeline_group"))
        gl = QVBoxLayout(self._pipeline_group)
        pl_row = QHBoxLayout()
        pl_row.addWidget(TrLabel("pipeline_label"))
        self._pipeline_combo = QComboBox()
        self._pipeline_combo.addItem(tr("pipeline_auto"), "auto")
        self._pipeline_combo.addItem(tr("pipeline_ocr"), "ocr")
        self._pipeline_combo.addItem(tr("pipeline_structure"), "structure")
        self._pipeline_combo.setFixedWidth(280)
        pl_row.addWidget(self._pipeline_combo)
        pl_row.addStretch()
        gl.addLayout(pl_row)
        gl.addWidget(_hint("pipeline_auto_hint"))

        self._preserve_layout_check = QCheckBox(tr("preserve_layout"))
        gl.addWidget(self._preserve_layout_check)
        gl.addWidget(_hint("preserve_layout_hint"))

        self._no_paddle_hint = _hint("no_paddle_hint")
        self._no_paddle_hint.setStyleSheet(f"font-size: 11px; color: {WARNING}; margin-left: 24px;")
        self._no_paddle_hint.setVisible(False)
        gl.addWidget(self._no_paddle_hint)

        self._onnx_lang_hint = _hint("onnx_lang_hint")
        self._onnx_lang_hint.setStyleSheet(f"font-size: 11px; color: {ACCENT}; margin-left: 24px;")
        self._onnx_lang_hint.setVisible(False)
        gl.addWidget(self._onnx_lang_hint)

        self._backend_hint = QLabel("")
        self._backend_hint.setWordWrap(True)
        self._backend_hint.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY}; margin-left: 24px;")
        gl.addWidget(self._backend_hint)
        adv.addWidget(self._pipeline_group)

        # ─── 2. 预处理 ───
        self._preproc_group = QGroupBox(tr("preprocess_group"))
        gp = QVBoxLayout(self._preproc_group)
        self._orientation_check = QCheckBox(tr("orientation_check"))
        gp.addWidget(self._orientation_check)
        gp.addWidget(_hint("orientation_hint"))
        self._unwarp_check = QCheckBox(tr("unwarp_check"))
        gp.addWidget(self._unwarp_check)
        gp.addWidget(_hint("unwarp_hint"))
        self._textline_ori_check = QCheckBox(tr("textline_ori_check"))
        gp.addWidget(self._textline_ori_check)
        gp.addWidget(_hint("textline_ori_hint"))
        adv.addWidget(self._preproc_group)

        # ─── 3. 文本检测 ───
        self._det_group = QGroupBox(tr("det_group"))
        gd = QVBoxLayout(self._det_group)
        self._det_limit_side = QSpinBox()
        self._det_limit_side.setRange(320, 4096)
        self._det_limit_side.setValue(2048)
        self._det_limit_side.setSingleStep(32)
        gd.addLayout(_spin_row("det_limit_side", self._det_limit_side, "px"))
        gd.addWidget(_hint("det_limit_side_hint"))

        self._det_limit_type = QComboBox()
        self._det_limit_type.addItem(tr("det_limit_max"), "max")
        self._det_limit_type.addItem(tr("det_limit_min"), "min")
        self._det_limit_type.setFixedWidth(200)
        lr = QHBoxLayout()
        lr.addWidget(TrLabel("det_limit_type"))
        lr.addWidget(self._det_limit_type)
        lr.addStretch()
        gd.addLayout(lr)
        gd.addWidget(_hint("det_limit_type_hint"))

        self._det_thresh = QDoubleSpinBox()
        self._det_thresh.setRange(0.01, 1.0)
        self._det_thresh.setValue(0.3)
        self._det_thresh.setSingleStep(0.05)
        self._det_thresh.setDecimals(2)
        gd.addLayout(_spin_row("det_thresh", self._det_thresh))
        gd.addWidget(_hint("det_thresh_hint"))

        self._det_box_thresh = QDoubleSpinBox()
        self._det_box_thresh.setRange(0.01, 1.0)
        self._det_box_thresh.setValue(0.45)
        self._det_box_thresh.setSingleStep(0.05)
        self._det_box_thresh.setDecimals(2)
        gd.addLayout(_spin_row("det_box_thresh", self._det_box_thresh))
        gd.addWidget(_hint("det_box_thresh_hint"))

        self._det_unclip = QDoubleSpinBox()
        self._det_unclip.setRange(0.5, 5.0)
        self._det_unclip.setValue(2.0)
        self._det_unclip.setSingleStep(0.1)
        self._det_unclip.setDecimals(1)
        gd.addLayout(_spin_row("det_unclip", self._det_unclip))
        gd.addWidget(_hint("det_unclip_hint"))
        adv.addWidget(self._det_group)

        # ─── 4. 文本识别 ───
        self._rec_group = QGroupBox(tr("rec_group"))
        gr = QVBoxLayout(self._rec_group)
        self._rec_score_thresh = QDoubleSpinBox()
        self._rec_score_thresh.setRange(0.0, 1.0)
        self._rec_score_thresh.setValue(0.0)
        self._rec_score_thresh.setSingleStep(0.05)
        self._rec_score_thresh.setDecimals(2)
        gr.addLayout(_spin_row("rec_score_thresh", self._rec_score_thresh))
        gr.addWidget(_hint("rec_score_thresh_hint"))

        self._rec_batch = QSpinBox()
        self._rec_batch.setRange(1, 64)
        self._rec_batch.setValue(1)
        gr.addLayout(_spin_row("rec_batch", self._rec_batch))
        gr.addWidget(_hint("rec_batch_hint"))

        self._return_word_box = QCheckBox(tr("return_word_box"))
        gr.addWidget(self._return_word_box)
        gr.addWidget(_hint("return_word_box_hint"))
        adv.addWidget(self._rec_group)

        # ─── 5. PPStructureV3 ───
        self._struct_group = QGroupBox(tr("struct_group"))
        gs = QVBoxLayout(self._struct_group)
        gs.addWidget(_hint("struct_hint"))
        self._use_table = QCheckBox(tr("use_table"))
        self._use_table.setChecked(True)
        gs.addWidget(self._use_table)
        gs.addWidget(_hint("use_table_hint"))
        self._use_formula = QCheckBox(tr("use_formula"))
        gs.addWidget(self._use_formula)
        gs.addWidget(_hint("use_formula_hint"))
        self._use_chart = QCheckBox(tr("use_chart"))
        gs.addWidget(self._use_chart)
        gs.addWidget(_hint("use_chart_hint"))
        self._use_seal = QCheckBox(tr("use_seal"))
        gs.addWidget(self._use_seal)
        gs.addWidget(_hint("use_seal_hint"))
        self._use_region_det = QCheckBox(tr("use_region_det"))
        self._use_region_det.setChecked(True)
        gs.addWidget(self._use_region_det)
        gs.addWidget(_hint("use_region_det_hint"))
        adv.addWidget(self._struct_group)

        # ─── 6. 版面分析 ───
        self._layout_group = QGroupBox(tr("layout_group"))
        gla = QVBoxLayout(self._layout_group)
        self._layout_thresh = QDoubleSpinBox()
        self._layout_thresh.setRange(0.01, 1.0)
        self._layout_thresh.setValue(0.5)
        self._layout_thresh.setSingleStep(0.05)
        self._layout_thresh.setDecimals(2)
        gla.addLayout(_spin_row("layout_thresh", self._layout_thresh))
        gla.addWidget(_hint("layout_thresh_hint"))

        self._layout_nms = QDoubleSpinBox()
        self._layout_nms.setRange(0.01, 1.0)
        self._layout_nms.setValue(0.5)
        self._layout_nms.setSingleStep(0.05)
        self._layout_nms.setDecimals(2)
        gla.addLayout(_spin_row("layout_nms", self._layout_nms))
        gla.addWidget(_hint("layout_nms_hint"))

        self._layout_unclip = QDoubleSpinBox()
        self._layout_unclip.setRange(0.0, 3.0)
        self._layout_unclip.setValue(0.0)
        self._layout_unclip.setSingleStep(0.1)
        self._layout_unclip.setDecimals(1)
        gla.addLayout(_spin_row("layout_unclip", self._layout_unclip))
        gla.addWidget(_hint("layout_unclip_hint"))

        self._layout_merge = QComboBox()
        self._layout_merge.addItem(tr("layout_merge_default"), "")
        self._layout_merge.addItem(tr("layout_merge_large"), "large")
        self._layout_merge.addItem(tr("layout_merge_small"), "small")
        self._layout_merge.setFixedWidth(200)
        mr = QHBoxLayout()
        mr.addWidget(TrLabel("layout_merge_mode"))
        mr.addWidget(self._layout_merge)
        mr.addStretch()
        gla.addLayout(mr)
        gla.addWidget(_hint("layout_merge_hint"))
        adv.addWidget(self._layout_group)

        # ─── 7. 印章检测 ───
        self._seal_group = QGroupBox(tr("seal_group"))
        gse = QVBoxLayout(self._seal_group)
        self._seal_det_thresh = QDoubleSpinBox()
        self._seal_det_thresh.setRange(0.01, 1.0)
        self._seal_det_thresh.setValue(0.3)
        self._seal_det_thresh.setSingleStep(0.05)
        self._seal_det_thresh.setDecimals(2)
        gse.addLayout(_spin_row("seal_det_thresh", self._seal_det_thresh))
        gse.addWidget(_hint("seal_det_thresh_hint"))

        self._seal_box_thresh = QDoubleSpinBox()
        self._seal_box_thresh.setRange(0.01, 1.0)
        self._seal_box_thresh.setValue(0.6)
        self._seal_box_thresh.setSingleStep(0.05)
        self._seal_box_thresh.setDecimals(2)
        gse.addLayout(_spin_row("seal_box_thresh", self._seal_box_thresh))
        gse.addWidget(_hint("seal_box_thresh_hint"))

        self._seal_unclip = QDoubleSpinBox()
        self._seal_unclip.setRange(0.5, 5.0)
        self._seal_unclip.setValue(1.5)
        self._seal_unclip.setSingleStep(0.1)
        self._seal_unclip.setDecimals(1)
        gse.addLayout(_spin_row("seal_unclip", self._seal_unclip))
        gse.addWidget(_hint("seal_unclip_hint"))

        self._seal_rec_thresh = QDoubleSpinBox()
        self._seal_rec_thresh.setRange(0.0, 1.0)
        self._seal_rec_thresh.setValue(0.0)
        self._seal_rec_thresh.setSingleStep(0.05)
        self._seal_rec_thresh.setDecimals(2)
        gse.addLayout(_spin_row("seal_rec_thresh", self._seal_rec_thresh))
        gse.addWidget(_hint("seal_rec_thresh_hint"))
        adv.addWidget(self._seal_group)

        # ─── 8. PDF 输入 ───
        self._pdf_group = QGroupBox(tr("pdf_input_group"))
        gpdf = QVBoxLayout(self._pdf_group)
        self._dpi_spin = QSpinBox()
        self._dpi_spin.setRange(72, 600)
        self._dpi_spin.setValue(200)
        gpdf.addLayout(_spin_row("render_dpi", self._dpi_spin))
        gpdf.addWidget(_hint("render_dpi_hint"))
        adv.addWidget(self._pdf_group)

        layout.addWidget(self._adv_widget)
        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._pipeline_combo.currentIndexChanged.connect(self._refresh_runtime_options)
        self._speed_combo.currentIndexChanged.connect(self._refresh_runtime_options)
        self._lang_combo.currentIndexChanged.connect(self._refresh_runtime_options)
        self._preserve_layout_check.toggled.connect(self._refresh_runtime_options)

        QTimer.singleShot(0, self._deferred_init)
        on_language_changed(self._retranslate)

    def _retranslate(self) -> None:
        self._start_btn.setText(tr("start_convert"))
        self._force_ocr_check.setText(tr("force_ocr"))
        self._adv_toggle.setText(
            tr("advanced_expanded") if self._adv_widget.isVisible()
            else tr("advanced_collapsed")
        )
        # Group titles
        self._pipeline_group.setTitle(tr("pipeline_group"))
        self._preproc_group.setTitle(tr("preprocess_group"))
        self._det_group.setTitle(tr("det_group"))
        self._rec_group.setTitle(tr("rec_group"))
        self._struct_group.setTitle(tr("struct_group"))
        self._layout_group.setTitle(tr("layout_group"))
        self._seal_group.setTitle(tr("seal_group"))
        self._pdf_group.setTitle(tr("pdf_input_group"))
        # Checkboxes
        self._preserve_layout_check.setText(tr("preserve_layout"))
        self._orientation_check.setText(tr("orientation_check"))
        self._unwarp_check.setText(tr("unwarp_check"))
        self._textline_ori_check.setText(tr("textline_ori_check"))
        self._return_word_box.setText(tr("return_word_box"))
        self._use_table.setText(tr("use_table"))
        self._use_formula.setText(tr("use_formula"))
        self._use_chart.setText(tr("use_chart"))
        self._use_seal.setText(tr("use_seal"))
        self._use_region_det.setText(tr("use_region_det"))
        # ComboBox items
        self._speed_combo.setItemText(0, tr("mode_balanced"))
        self._speed_combo.setItemText(1, tr("mode_speed"))
        self._pipeline_combo.setItemText(0, tr("pipeline_auto"))
        self._pipeline_combo.setItemText(1, tr("pipeline_ocr"))
        self._pipeline_combo.setItemText(2, tr("pipeline_structure"))
        self._det_limit_type.setItemText(0, tr("det_limit_max"))
        self._det_limit_type.setItemText(1, tr("det_limit_min"))
        self._layout_merge.setItemText(0, tr("layout_merge_default"))
        self._layout_merge.setItemText(1, tr("layout_merge_large"))
        self._layout_merge.setItemText(2, tr("layout_merge_small"))
        # Backend hint
        self._refresh_runtime_options()
        # TrLabel instances auto-retranslate, no need to handle here.

    def _deferred_init(self) -> None:
        self._paddle_ok = self._check_paddle()
        self._server_onnx_ok = self._check_server_onnx()
        self._onnx_langs = set(self._supported_onnx_languages())

        if not self._paddle_ok:
            for i in range(self._lang_combo.count() - 1, -1, -1):
                code = self._lang_combo.itemData(i)
                if code not in self._onnx_langs:
                    self._lang_combo.removeItem(i)

        from PySide6.QtCore import QSettings
        settings = QSettings("PaddleOCR", "Desktop")
        saved_lang = settings.value("ocr/language", "")
        if saved_lang:
            idx = self._lang_combo.findData(saved_lang)
            if idx >= 0:
                self._lang_combo.setCurrentIndex(idx)

        if not self._server_onnx_ok:
            self._speed_combo.model().item(0).setEnabled(False)
            self._speed_combo.setCurrentIndex(1)
            self._speed_combo.setToolTip(tr("server_onnx_unavailable"))

        if not self._paddle_ok:
            model = self._pipeline_combo.model()
            model.item(2).setEnabled(False)
            self._preserve_layout_check.setEnabled(False)
            self._struct_group.setEnabled(False)
            self._layout_group.setEnabled(False)
            self._seal_group.setEnabled(False)
            self._no_paddle_hint.setVisible(True)
            self._onnx_lang_hint.setVisible(True)

        self._refresh_runtime_options()

    @staticmethod
    def _check_paddle() -> bool:
        try:
            from app.core.onnx_engine import paddle_available
            return paddle_available()
        except Exception:
            return False

    @staticmethod
    def _check_server_onnx() -> bool:
        try:
            from app.core.onnx_engine import onnx_available
            return onnx_available("server")
        except Exception:
            return False

    @staticmethod
    def _supported_onnx_languages() -> tuple[str, ...]:
        try:
            from app.core.onnx_engine import supported_onnx_languages
            return supported_onnx_languages()
        except Exception:
            return ("ch", "en")

    def _effective_pipeline(self) -> str:
        pipeline = self._pipeline_combo.currentData()
        if pipeline in ("ocr", "structure"):
            return pipeline
        if self._selected_format in (OutputFormat.WORD, OutputFormat.HTML, OutputFormat.EXCEL):
            return "structure" if self._paddle_ok else "ocr"
        if (
            self._selected_format in (OutputFormat.TXT, OutputFormat.RTF)
            and self._preserve_layout_check.isEnabled()
            and self._preserve_layout_check.isChecked()
        ):
            return "structure" if self._paddle_ok else "ocr"
        return "ocr"

    def _selected_is_pdf(self) -> bool:
        return self._selected_file is not None and self._selected_file.suffix.lower() == ".pdf"

    @staticmethod
    def _set_enabled(widget, enabled: bool, tooltip: str | None = None) -> None:
        widget.setEnabled(enabled)
        if not enabled and hasattr(widget, "setChecked") and widget.isChecked():
            widget.setChecked(False)
        if tooltip:
            widget.setToolTip(tooltip)

    def _refresh_runtime_options(self) -> None:
        effective_pipeline = self._effective_pipeline()
        structure_active = effective_pipeline == "structure"
        is_pdf = self._selected_is_pdf()

        ocr_backend = None
        if not structure_active:
            try:
                from app.core.onnx_engine import resolve_ocr_backend
                ocr_backend = resolve_ocr_backend(
                    self._lang_combo.currentData(),
                    self._speed_combo.currentData(),
                )
            except Exception:
                ocr_backend = None

        onnx_ocr = (not structure_active) and ocr_backend == "onnx"

        preserve_layout_enabled = self._paddle_ok and self._selected_format in (
            OutputFormat.TXT, OutputFormat.RTF,
        )
        self._set_enabled(self._preserve_layout_check, preserve_layout_enabled, tr("preserve_layout_tooltip"))

        structure_enabled = structure_active and self._paddle_ok
        self._struct_group.setEnabled(structure_enabled)
        self._layout_group.setEnabled(structure_enabled)
        self._seal_group.setEnabled(structure_enabled)

        self._set_enabled(self._unwarp_check, not onnx_ocr, tr("unwarp_tooltip"))
        self._set_enabled(self._return_word_box, not onnx_ocr, tr("return_word_box_tooltip"))

        self._parallel_spin.setEnabled(is_pdf)
        self._force_ocr_check.setEnabled(is_pdf)
        self._page_start.setEnabled(is_pdf)
        self._page_end.setEnabled(is_pdf)
        self._pdf_group.setEnabled(is_pdf)

        if structure_active:
            self._backend_hint.setText(tr("backend_structure"))
        elif onnx_ocr:
            self._backend_hint.setText(tr("backend_onnx"))
        elif ocr_backend == "paddle":
            self._backend_hint.setText(tr("backend_paddle"))
        else:
            self._backend_hint.setText(tr("backend_missing"))

    def _on_file_selected(self, path: Path) -> None:
        self._selected_file = path
        self._selected_files = [path]
        self._drop_zone.set_file_info(path)
        self._start_btn.setEnabled(True)
        self._start_btn.setToolTip("")
        self._refresh_runtime_options()

    def _on_files_selected(self, paths: list[Path]) -> None:
        if not paths:
            return
        self._selected_files = paths
        self._selected_file = paths[0]
        self._drop_zone.set_files_info(paths)
        self._start_btn.setEnabled(True)
        self._start_btn.setToolTip("")
        self._refresh_runtime_options()

    def _on_format_selected(self, fmt: OutputFormat) -> None:
        self._selected_format = fmt
        for card in self._cards:
            card.set_selected(card._fmt == fmt)
        self._refresh_runtime_options()

    def _toggle_advanced(self) -> None:
        visible = not self._adv_widget.isVisible()
        self._adv_widget.setVisible(visible)
        self._adv_toggle.setText(tr("advanced_expanded") if visible else tr("advanced_collapsed"))

    def _on_start(self) -> None:
        if not self._selected_files:
            return
        lang = self._lang_combo.currentData()
        from PySide6.QtCore import QSettings
        QSettings("PaddleOCR", "Desktop").setValue("ocr/language", lang)
        if len(self._selected_files) == 1:
            self.start_requested.emit(self._selected_files[0], self._selected_format, lang)
        else:
            self.batch_start_requested.emit(self._selected_files, self._selected_format, lang)

    def get_advanced_params(self) -> dict:
        return {
            "speed_mode": self._speed_combo.currentData(),
            "pipeline": self._pipeline_combo.currentData(),
            "preserve_layout": self._preserve_layout_check.isEnabled() and self._preserve_layout_check.isChecked(),
            "use_doc_orientation_classify": self._orientation_check.isChecked(),
            "use_doc_unwarping": self._unwarp_check.isEnabled() and self._unwarp_check.isChecked(),
            "use_textline_orientation": self._textline_ori_check.isChecked(),
            "text_det_limit_side_len": self._det_limit_side.value(),
            "text_det_limit_type": self._det_limit_type.currentData(),
            "text_det_thresh": self._det_thresh.value(),
            "text_det_box_thresh": self._det_box_thresh.value(),
            "text_det_unclip_ratio": self._det_unclip.value(),
            "text_rec_score_thresh": self._rec_score_thresh.value(),
            "text_recognition_batch_size": self._rec_batch.value(),
            "return_word_box": self._return_word_box.isEnabled() and self._return_word_box.isChecked(),
            "use_table_recognition": self._struct_group.isEnabled() and self._use_table.isChecked(),
            "use_formula_recognition": self._struct_group.isEnabled() and self._use_formula.isChecked(),
            "use_chart_recognition": self._struct_group.isEnabled() and self._use_chart.isChecked(),
            "use_seal_recognition": self._struct_group.isEnabled() and self._use_seal.isChecked(),
            "use_region_detection": self._struct_group.isEnabled() and self._use_region_det.isChecked(),
            "layout_threshold": self._layout_thresh.value() if self._layout_group.isEnabled() else None,
            "layout_nms": self._layout_nms.value() if self._layout_group.isEnabled() else None,
            "layout_unclip_ratio": (self._layout_unclip.value() or None) if self._layout_group.isEnabled() else None,
            "layout_merge_bboxes_mode": (self._layout_merge.currentData() or None) if self._layout_group.isEnabled() else None,
            "seal_det_thresh": self._seal_det_thresh.value() if self._seal_group.isEnabled() else None,
            "seal_det_box_thresh": self._seal_box_thresh.value() if self._seal_group.isEnabled() else None,
            "seal_det_unclip_ratio": self._seal_unclip.value() if self._seal_group.isEnabled() else None,
            "seal_rec_score_thresh": self._seal_rec_thresh.value() if self._seal_group.isEnabled() else None,
            "render_dpi": self._dpi_spin.value(),
            "parallel_workers": self._parallel_spin.value(),
            "force_ocr": self._force_ocr_check.isEnabled() and self._force_ocr_check.isChecked(),
            "page_start": self._page_start.value(),
            "page_end": self._page_end.value(),
        }
