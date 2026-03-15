"""转换面板 — 文件选择 + 格式 + 语言 + 折叠高级选项（完整参数）+ 开始。"""

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

from app.models.enums import OutputFormat
from app.ui.drop_zone import DropZone
from app.ui.format_card import FormatCard

_LANGUAGES = [
    ("ch", "中文（含中英混合）"),
    ("en", "English"),
    ("japan", "日本語"),
    ("korean", "한국어"),
    ("french", "Français"),
    ("german", "Deutsch"),
    ("it", "Italiano"),
    ("es", "Español"),
    ("pt", "Português"),
    ("ru", "Русский"),
    ("ar", "العربية"),
    ("chinese_cht", "繁體中文"),
    ("latin", "Latin"),
    ("cyrillic", "Cyrillic"),
    ("devanagari", "Devanagari"),
]


def _hint(text: str) -> QLabel:
    """创建灰色小字说明标签。"""
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet("font-size: 11px; color: #888; margin-left: 24px;")
    return lbl


def _spin_row(label: str, spin: QSpinBox | QDoubleSpinBox, suffix: str = "") -> QHBoxLayout:
    row = QHBoxLayout()
    row.addWidget(QLabel(label))
    spin.setFixedWidth(90)
    row.addWidget(spin)
    if suffix:
        row.addWidget(QLabel(suffix))
    row.addStretch()
    return row


class QuickConvertPanel(QWidget):
    start_requested = Signal(Path, OutputFormat, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._selected_file: Path | None = None
        self._selected_format: OutputFormat = OutputFormat.TXT

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("快速转换")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        # ── 拖拽区域 ──
        self._drop_zone = DropZone()
        self._drop_zone.file_dropped.connect(self._on_file_selected)
        layout.addWidget(self._drop_zone)

        # ── 格式卡片 ──
        fmt_label = QLabel("选择输出格式：")
        fmt_label.setStyleSheet("font-size: 13px; color: #555;")
        layout.addWidget(fmt_label)

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
        bottom.addWidget(QLabel("识别语言："))
        self._lang_combo = QComboBox()
        for code, name in _LANGUAGES:
            self._lang_combo.addItem(name, code)
        self._lang_combo.setFixedWidth(200)
        bottom.addWidget(self._lang_combo)
        bottom.addSpacing(20)
        bottom.addWidget(QLabel("模式："))
        self._speed_combo = QComboBox()
        self._speed_combo.addItem("均衡（Server 模型）", "server")
        self._speed_combo.addItem("速度优先（Mobile 模型，快 8x）", "mobile")
        self._speed_combo.setFixedWidth(260)
        self._speed_combo.setToolTip("Mobile 模型推理速度约为 Server 的 8 倍，精度略低")
        bottom.addWidget(self._speed_combo)

        bottom.addStretch()
        self._start_btn = QPushButton("开始转换")
        self._start_btn.setObjectName("startButton")
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._on_start)
        bottom.addWidget(self._start_btn)
        layout.addLayout(bottom)

        # ── 并行 + 强制 OCR ──
        parallel_row = QHBoxLayout()
        parallel_row.addWidget(QLabel("并行进程数："))
        self._parallel_spin = QSpinBox()
        self._parallel_spin.setRange(1, 4)
        self._parallel_spin.setValue(2)
        self._parallel_spin.setFixedWidth(60)
        self._parallel_spin.setToolTip("同时运行的 OCR 子进程数量。2 适合大多数情况，增大可加速但消耗更多内存")
        parallel_row.addWidget(self._parallel_spin)
        parallel_row.addSpacing(20)

        self._force_ocr_check = QCheckBox("强制 OCR（忽略 PDF 已有文字层）")
        self._force_ocr_check.setToolTip(
            "默认会自动检测 PDF 是否有文字层，有则直接提取（毫秒级）。\n"
            "勾选此项可强制重新 OCR，适合文字层不准确需要重新识别的场景。"
        )
        parallel_row.addWidget(self._force_ocr_check)
        parallel_row.addStretch()
        layout.addLayout(parallel_row)

        # ── PDF 页码范围 ──
        page_row = QHBoxLayout()
        page_row.addWidget(QLabel("PDF 页码范围："))
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
        self._page_end.setToolTip("设为 9999 表示处理到最后一页")
        page_row.addWidget(self._page_end)
        page_row.addWidget(_hint("大 PDF 建议先处理部分页面测试效果。>50 页自动降 DPI"))
        page_row.addStretch()
        layout.addLayout(page_row)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 折叠高级选项
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        self._adv_toggle = QPushButton("▶ 高级选项（全部 PaddleOCR 参数）")
        self._adv_toggle.setStyleSheet(
            "QPushButton { border: none; color: #1A73E8; font-size: 13px; "
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

        # ─── 1. Pipeline 选择 ───
        grp_pipeline = QGroupBox("识别模式")
        gl = QVBoxLayout(grp_pipeline)
        pl_row = QHBoxLayout()
        pl_row.addWidget(QLabel("Pipeline："))
        self._pipeline_combo = QComboBox()
        self._pipeline_combo.addItem("自动（按输出格式决定）", "auto")
        self._pipeline_combo.addItem("PP-OCRv5（纯文本识别）", "ocr")
        self._pipeline_combo.addItem("PPStructureV3（结构化解析）", "structure")
        self._pipeline_combo.setFixedWidth(280)
        pl_row.addWidget(self._pipeline_combo)
        pl_row.addStretch()
        gl.addLayout(pl_row)
        gl.addWidget(_hint("自动模式：TXT/PDF/RTF → PP-OCRv5，Word/HTML/Excel → PPStructureV3"))

        self._preserve_layout_check = QCheckBox("TXT/RTF 保留版面结构")
        gl.addWidget(self._preserve_layout_check)
        gl.addWidget(_hint("勾选后 TXT/RTF 导出也走 PPStructureV3，以保留段落和标题层次"))

        # 检查 PaddlePaddle 是否可用，不可用则禁用 PPStructureV3
        self._paddle_ok = self._check_paddle()
        if not self._paddle_ok:
            model = self._pipeline_combo.model()
            model.item(2).setEnabled(False)  # 禁用 "PPStructureV3" 选项
            self._preserve_layout_check.setEnabled(False)
            self._no_paddle_hint = _hint(
                "⚠ PPStructureV3 不可用（需要 PaddlePaddle）。"
                "Word/HTML/Excel 输出将使用 ONNX 纯文本模式。"
            )
            self._no_paddle_hint.setStyleSheet(
                "font-size: 11px; color: #e67e22; margin-left: 24px;"
            )
            gl.addWidget(self._no_paddle_hint)

        adv.addWidget(grp_pipeline)

        # ─── 2. 文档预处理 ───
        grp_preproc = QGroupBox("文档预处理")
        gp = QVBoxLayout(grp_preproc)

        self._orientation_check = QCheckBox("文档方向检测与校正（use_doc_orientation_classify）")
        gp.addWidget(self._orientation_check)
        gp.addWidget(_hint("自动检测文档是否旋转了 90°/180°/270° 并校正到正向，适合扫描件方向不确定的场景"))

        self._unwarp_check = QCheckBox("文档弯曲矫正（use_doc_unwarping）")
        gp.addWidget(self._unwarp_check)
        gp.addWidget(_hint("对手机拍摄的弯曲/透视变形文档做几何校正，使文字行恢复水平"))

        self._textline_ori_check = QCheckBox("文本行方向检测（use_textline_orientation）")
        gp.addWidget(self._textline_ori_check)
        gp.addWidget(_hint("检测每行文字是横排还是竖排并分别处理，适合中日韩竖排古籍。仅 PP-OCRv5 可用"))
        adv.addWidget(grp_preproc)

        # ─── 3. 文本检测参数 ───
        grp_det = QGroupBox("文本检测参数（PP-OCRv5）")
        gd = QVBoxLayout(grp_det)

        self._det_limit_side = QSpinBox()
        self._det_limit_side.setRange(320, 4096)
        self._det_limit_side.setValue(960)
        self._det_limit_side.setSingleStep(32)
        gd.addLayout(_spin_row("检测图像长边限制：", self._det_limit_side, "px"))
        gd.addWidget(_hint("输入图像会缩放到此尺寸再检测。值越大检测越精细但越慢，默认 960"))

        self._det_limit_type = QComboBox()
        self._det_limit_type.addItem("max — 限制长边", "max")
        self._det_limit_type.addItem("min — 限制短边", "min")
        self._det_limit_type.setFixedWidth(200)
        lr = QHBoxLayout()
        lr.addWidget(QLabel("限制类型："))
        lr.addWidget(self._det_limit_type)
        lr.addStretch()
        gd.addLayout(lr)
        gd.addWidget(_hint("max：按长边缩放（默认）；min：按短边缩放，适合超长条形图像"))

        self._det_thresh = QDoubleSpinBox()
        self._det_thresh.setRange(0.01, 1.0)
        self._det_thresh.setValue(0.3)
        self._det_thresh.setSingleStep(0.05)
        self._det_thresh.setDecimals(2)
        gd.addLayout(_spin_row("文本区域阈值（det_thresh）：", self._det_thresh))
        gd.addWidget(_hint("DB 二值化阈值，越低越容易检测到浅色/模糊文字，但也可能误检噪点。默认 0.3"))

        self._det_box_thresh = QDoubleSpinBox()
        self._det_box_thresh.setRange(0.01, 1.0)
        self._det_box_thresh.setValue(0.6)
        self._det_box_thresh.setSingleStep(0.05)
        self._det_box_thresh.setDecimals(2)
        gd.addLayout(_spin_row("文本框置信阈值（box_thresh）：", self._det_box_thresh))
        gd.addWidget(_hint("检测框的最低平均置信度，低于此值的框被丢弃。调低可保留更多弱文本区域。默认 0.6"))

        self._det_unclip = QDoubleSpinBox()
        self._det_unclip.setRange(0.5, 5.0)
        self._det_unclip.setValue(1.5)
        self._det_unclip.setSingleStep(0.1)
        self._det_unclip.setDecimals(1)
        gd.addLayout(_spin_row("文本框扩展比例（unclip_ratio）：", self._det_unclip))
        gd.addWidget(_hint("检测框向外扩展的比例，值越大框越宽松，可包含更多边缘文字。默认 1.5"))

        adv.addWidget(grp_det)

        # ─── 4. 文本识别参数 ───
        grp_rec = QGroupBox("文本识别参数")
        gr = QVBoxLayout(grp_rec)

        self._rec_score_thresh = QDoubleSpinBox()
        self._rec_score_thresh.setRange(0.0, 1.0)
        self._rec_score_thresh.setValue(0.0)
        self._rec_score_thresh.setSingleStep(0.05)
        self._rec_score_thresh.setDecimals(2)
        gr.addLayout(_spin_row("识别置信度过滤：", self._rec_score_thresh))
        gr.addWidget(_hint("低于此置信度的识别结果被丢弃。设为 0 表示不过滤（保留所有结果）。调高可去掉乱码"))

        self._rec_batch = QSpinBox()
        self._rec_batch.setRange(1, 64)
        self._rec_batch.setValue(1)
        gr.addLayout(_spin_row("识别 batch size：", self._rec_batch))
        gr.addWidget(_hint("一次送入识别模型的文本行数量。增大可加速但消耗更多内存。CPU 推荐 1"))

        self._return_word_box = QCheckBox("返回单词级边框（return_word_box）")
        gr.addWidget(self._return_word_box)
        gr.addWidget(_hint("除了行级边框外，额外返回每个单词的精确位置。用于搜索型 PDF 精确定位"))

        adv.addWidget(grp_rec)

        # ─── 5. PPStructureV3 功能开关 ───
        grp_struct = QGroupBox("结构化解析功能（PPStructureV3）")
        gs = QVBoxLayout(grp_struct)
        gs.addWidget(_hint("以下开关仅在使用 PPStructureV3 pipeline 时生效"))

        self._use_table = QCheckBox("表格识别（use_table_recognition）")
        self._use_table.setChecked(True)
        gs.addWidget(self._use_table)
        gs.addWidget(_hint("识别文档中的表格并还原为结构化数据（行/列/单元格），导出 Excel/Word 表格的核心功能"))

        self._use_formula = QCheckBox("公式识别（use_formula_recognition）")
        self._use_formula.setChecked(True)
        gs.addWidget(self._use_formula)
        gs.addWidget(_hint("识别数学公式并转为 LaTeX 格式。关闭可加速处理非学术文档"))

        self._use_chart = QCheckBox("图表识别（use_chart_recognition）")
        self._use_chart.setChecked(True)
        gs.addWidget(self._use_chart)
        gs.addWidget(_hint("识别柱状图/饼图/折线图等，转为结构化表格数据。需要 PP-Chart2Table 模型（1.3GB）"))

        self._use_seal = QCheckBox("印章识别（use_seal_recognition）")
        self._use_seal.setChecked(True)
        gs.addWidget(self._use_seal)
        gs.addWidget(_hint("识别圆形/椭圆形印章中的弯曲文字。适合合同、证书等盖章文档"))

        self._use_region_det = QCheckBox("区域检测（use_region_detection）")
        self._use_region_det.setChecked(True)
        gs.addWidget(self._use_region_det)
        gs.addWidget(_hint("在版面分析基础上进一步检测图文混排区域，提升复杂版面的解析精度"))

        if not self._paddle_ok:
            grp_struct.setEnabled(False)
        adv.addWidget(grp_struct)

        # ─── 6. 版面分析参数 ───
        grp_layout = QGroupBox("版面分析参数（PPStructureV3）")
        gla = QVBoxLayout(grp_layout)

        self._layout_thresh = QDoubleSpinBox()
        self._layout_thresh.setRange(0.01, 1.0)
        self._layout_thresh.setValue(0.5)
        self._layout_thresh.setSingleStep(0.05)
        self._layout_thresh.setDecimals(2)
        gla.addLayout(_spin_row("版面检测阈值：", self._layout_thresh))
        gla.addWidget(_hint("版面区域的最低置信度。降低可检测出更多区域块，但可能引入误检。默认 0.5"))

        self._layout_nms = QDoubleSpinBox()
        self._layout_nms.setRange(0.01, 1.0)
        self._layout_nms.setValue(0.5)
        self._layout_nms.setSingleStep(0.05)
        self._layout_nms.setDecimals(2)
        gla.addLayout(_spin_row("版面 NMS 阈值：", self._layout_nms))
        gla.addWidget(_hint("非极大值抑制阈值，用于合并重叠的版面区域框。值越高保留的重叠框越多"))

        self._layout_unclip = QDoubleSpinBox()
        self._layout_unclip.setRange(0.0, 3.0)
        self._layout_unclip.setValue(0.0)
        self._layout_unclip.setSingleStep(0.1)
        self._layout_unclip.setDecimals(1)
        gla.addLayout(_spin_row("版面框扩展比例：", self._layout_unclip))
        gla.addWidget(_hint("版面区域框向外扩展的比例，0 表示使用默认值"))

        self._layout_merge = QComboBox()
        self._layout_merge.addItem("默认", "")
        self._layout_merge.addItem("large — 合并大区域", "large")
        self._layout_merge.addItem("small — 合并小区域", "small")
        self._layout_merge.setFixedWidth(200)
        mr = QHBoxLayout()
        mr.addWidget(QLabel("区域合并模式："))
        mr.addWidget(self._layout_merge)
        mr.addStretch()
        gla.addLayout(mr)
        gla.addWidget(_hint("控制如何合并相邻的版面区域。large 适合报纸/杂志等大分栏版面"))

        if not self._paddle_ok:
            grp_layout.setEnabled(False)
        adv.addWidget(grp_layout)

        # ─── 7. 印章检测参数 ───
        grp_seal = QGroupBox("印章检测参数（PPStructureV3）")
        gse = QVBoxLayout(grp_seal)

        self._seal_det_thresh = QDoubleSpinBox()
        self._seal_det_thresh.setRange(0.01, 1.0)
        self._seal_det_thresh.setValue(0.3)
        self._seal_det_thresh.setSingleStep(0.05)
        self._seal_det_thresh.setDecimals(2)
        gse.addLayout(_spin_row("印章检测阈值：", self._seal_det_thresh))
        gse.addWidget(_hint("印章文字检测的二值化阈值。印章颜色较浅时可适当降低"))

        self._seal_box_thresh = QDoubleSpinBox()
        self._seal_box_thresh.setRange(0.01, 1.0)
        self._seal_box_thresh.setValue(0.6)
        self._seal_box_thresh.setSingleStep(0.05)
        self._seal_box_thresh.setDecimals(2)
        gse.addLayout(_spin_row("印章框置信阈值：", self._seal_box_thresh))
        gse.addWidget(_hint("印章文字框的最低置信度"))

        self._seal_unclip = QDoubleSpinBox()
        self._seal_unclip.setRange(0.5, 5.0)
        self._seal_unclip.setValue(1.5)
        self._seal_unclip.setSingleStep(0.1)
        self._seal_unclip.setDecimals(1)
        gse.addLayout(_spin_row("印章框扩展比例：", self._seal_unclip))
        gse.addWidget(_hint("印章文字框向外扩展的比例"))

        self._seal_rec_thresh = QDoubleSpinBox()
        self._seal_rec_thresh.setRange(0.0, 1.0)
        self._seal_rec_thresh.setValue(0.0)
        self._seal_rec_thresh.setSingleStep(0.05)
        self._seal_rec_thresh.setDecimals(2)
        gse.addLayout(_spin_row("印章识别置信过滤：", self._seal_rec_thresh))
        gse.addWidget(_hint("低于此值的印章文字识别结果被丢弃"))

        if not self._paddle_ok:
            grp_seal.setEnabled(False)
        adv.addWidget(grp_seal)

        # ─── 8. PDF 输入 ───
        grp_pdf = QGroupBox("PDF 输入设置")
        gpdf = QVBoxLayout(grp_pdf)
        self._dpi_spin = QSpinBox()
        self._dpi_spin.setRange(72, 600)
        self._dpi_spin.setValue(300)
        gpdf.addLayout(_spin_row("渲染 DPI：", self._dpi_spin))
        gpdf.addWidget(_hint("PDF 页面渲染为图片的分辨率。300 适合正常文档，扫描件可试 200 加速。最高 600"))
        adv.addWidget(grp_pdf)

        layout.addWidget(self._adv_widget)
        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── 事件处理 ──

    @staticmethod
    def _check_paddle() -> bool:
        """检查 PaddlePaddle 是否可用。"""
        try:
            from app.core.onnx_engine import paddle_available
            return paddle_available()
        except Exception:
            return False

    def _on_file_selected(self, path: Path) -> None:
        self._selected_file = path
        self._drop_zone.set_file_info(path)
        self._start_btn.setEnabled(True)

    def _on_format_selected(self, fmt: OutputFormat) -> None:
        self._selected_format = fmt
        for card in self._cards:
            card.set_selected(card._fmt == fmt)

    def _toggle_advanced(self) -> None:
        visible = not self._adv_widget.isVisible()
        self._adv_widget.setVisible(visible)
        self._adv_toggle.setText(
            "▼ 高级选项（全部 PaddleOCR 参数）" if visible
            else "▶ 高级选项（全部 PaddleOCR 参数）"
        )

    def _on_start(self) -> None:
        if self._selected_file is None:
            return
        lang = self._lang_combo.currentData()
        self.start_requested.emit(self._selected_file, self._selected_format, lang)

    def get_advanced_params(self) -> dict:
        """供 MainWindow 读取全部高级参数。"""
        return {
            # 速度模式
            "speed_mode": self._speed_combo.currentData(),
            # pipeline
            "pipeline": self._pipeline_combo.currentData(),
            "preserve_layout": self._preserve_layout_check.isChecked(),
            # 文档预处理
            "use_doc_orientation_classify": self._orientation_check.isChecked(),
            "use_doc_unwarping": self._unwarp_check.isChecked(),
            "use_textline_orientation": self._textline_ori_check.isChecked(),
            # 文本检测
            "text_det_limit_side_len": self._det_limit_side.value(),
            "text_det_limit_type": self._det_limit_type.currentData(),
            "text_det_thresh": self._det_thresh.value(),
            "text_det_box_thresh": self._det_box_thresh.value(),
            "text_det_unclip_ratio": self._det_unclip.value(),
            # 文本识别
            "text_rec_score_thresh": self._rec_score_thresh.value(),
            "text_recognition_batch_size": self._rec_batch.value(),
            "return_word_box": self._return_word_box.isChecked(),
            # PPStructureV3 开关
            "use_table_recognition": self._use_table.isChecked(),
            "use_formula_recognition": self._use_formula.isChecked(),
            "use_chart_recognition": self._use_chart.isChecked(),
            "use_seal_recognition": self._use_seal.isChecked(),
            "use_region_detection": self._use_region_det.isChecked(),
            # 版面分析
            "layout_threshold": self._layout_thresh.value(),
            "layout_nms": self._layout_nms.value(),
            "layout_unclip_ratio": self._layout_unclip.value() or None,
            "layout_merge_bboxes_mode": self._layout_merge.currentData() or None,
            # 印章
            "seal_det_thresh": self._seal_det_thresh.value(),
            "seal_det_box_thresh": self._seal_box_thresh.value(),
            "seal_det_unclip_ratio": self._seal_unclip.value(),
            "seal_rec_score_thresh": self._seal_rec_thresh.value(),
            # PDF
            "render_dpi": self._dpi_spin.value(),
            # 并行 + PDF
            "parallel_workers": self._parallel_spin.value(),
            "force_ocr": self._force_ocr_check.isChecked(),
            "page_start": self._page_start.value(),
            "page_end": self._page_end.value(),
        }
