"""简体中文翻译。"""

STRINGS: dict[str, str] = {
    # ── 应用 ──
    "app_title": "PaddleOCR — 智能文档识别",

    # ── 侧边栏 ──
    "nav_convert": "转换",
    "nav_preview": "预览",
    "nav_settings": "设置",
    "sidebar_processing": "处理中...",

    # ── 转换面板 ──
    "convert_title": "快速转换",
    "select_output_format": "选择输出格式：",
    "ocr_language": "识别语言：",
    "mode_label": "模式：",
    "mode_balanced": "均衡（Server 模型）",
    "mode_speed": "速度优先（Mobile 模型，快 8x）",
    "mode_tooltip": "不同模式会切换不同 ONNX 模型；Server 更准，Mobile 更省内存",
    "start_convert": "开始转换",
    "select_file_first": "请先选择文件",
    "parallel_workers": "并行进程数：",
    "parallel_tooltip": "同时运行的 OCR 子进程数量。2 适合大多数情况，增大可加速但消耗更多内存",
    "force_ocr": "强制 OCR（忽略 PDF 已有文字层）",
    "force_ocr_tooltip": "默认会自动检测 PDF 是否有文字层，有则直接提取（毫秒级）。\n勾选此项可强制重新 OCR，适合文字层不准确需要重新识别的场景。",
    "pdf_page_range": "PDF 页码范围：",
    "pdf_page_hint": "大 PDF 建议先处理部分页面测试效果。>50 页自动降 DPI",
    "advanced_options": "高级选项（按当前引擎生效）",
    "advanced_collapsed": "▶ 高级选项（按当前引擎生效）",
    "advanced_expanded": "▼ 高级选项（按当前引擎生效）",
    "server_onnx_unavailable": "当前环境未找到 Server ONNX 模型，仅可使用 Mobile 模式",

    # 高级选项 - Pipeline
    "pipeline_group": "识别模式",
    "pipeline_label": "Pipeline：",
    "pipeline_auto": "自动（按输出格式决定）",
    "pipeline_ocr": "OCR（ONNX Runtime / Paddle）",
    "pipeline_structure": "PPStructureV3（结构化解析）",
    "pipeline_auto_hint": "自动模式：TXT/PDF/RTF 走 OCR；Word/HTML/Excel 优先结构化。若结构化后端不可用，会降级为纯文本 OCR 导出。",
    "preserve_layout": "TXT/RTF 保留版面结构",
    "preserve_layout_hint": "勾选后 TXT/RTF 导出也走 PPStructureV3，以保留段落和标题层次",
    "preserve_layout_tooltip": "仅 TXT/RTF 且结构化后端可用时生效",
    "no_paddle_hint": "⚠ PPStructureV3 不可用（需要 PaddlePaddle）。Word/HTML/Excel 将降级为纯文本 OCR 导出。",
    "onnx_lang_hint": "当前仅提供 ONNX 可用语言：中文、英文。",

    # 高级选项 - 预处理
    "preprocess_group": "文档预处理",
    "orientation_check": "文档方向检测与校正（use_doc_orientation_classify）",
    "orientation_hint": "自动检测文档是否旋转了 90°/180°/270° 并校正到正向，适合扫描件方向不确定的场景",
    "unwarp_check": "文档弯曲矫正（use_doc_unwarping）",
    "unwarp_hint": "对手机拍摄的弯曲/透视变形文档做几何校正。当前 ONNX OCR 不支持时会自动禁用",
    "unwarp_tooltip": "当前 ONNX OCR 不支持文档弯曲矫正",
    "textline_ori_check": "文本行方向检测（use_textline_orientation）",
    "textline_ori_hint": "检测每行文字是横排还是竖排并分别处理，适合竖排文档。ONNX OCR 与 PaddleOCR 都会消费该项",

    # 高级选项 - 检测参数
    "det_group": "文本检测参数（OCR）",
    "det_limit_side": "检测图像长边限制：",
    "det_limit_side_hint": "输入图像会缩放到此尺寸再检测。值越大检测越精细但越慢，默认 2048",
    "det_limit_type": "限制类型：",
    "det_limit_max": "max — 限制长边",
    "det_limit_min": "min — 限制短边",
    "det_limit_type_hint": "max：按长边缩放（默认）；min：按短边缩放，适合超长条形图像",
    "det_thresh": "文本区域阈值（det_thresh）：",
    "det_thresh_hint": "DB 二值化阈值，越低越容易检测到浅色/模糊文字，但也可能误检噪点。默认 0.3",
    "det_box_thresh": "文本框置信阈值（box_thresh）：",
    "det_box_thresh_hint": "检测框的最低平均置信度，低于此值的框被丢弃。调低可保留更多弱文本区域。默认 0.45",
    "det_unclip": "文本框扩展比例（unclip_ratio）：",
    "det_unclip_hint": "检测框向外扩展的比例，值越大框越宽松，可包含更多边缘文字。默认 2.0",

    # 高级选项 - 识别参数
    "rec_group": "文本识别参数（OCR）",
    "rec_score_thresh": "识别置信度过滤：",
    "rec_score_thresh_hint": "低于此置信度的识别结果被丢弃。设为 0 表示不过滤（保留所有结果）。调高可去掉乱码",
    "rec_batch": "识别 batch size：",
    "rec_batch_hint": "一次送入识别模型的文本行数量。增大可加速但消耗更多内存。CPU 推荐 1",
    "return_word_box": "返回单词级边框（return_word_box）",
    "return_word_box_hint": "除了行级边框外，额外返回每个单词的精确位置。当前仅 PaddleOCR 提供，ONNX 模式会自动禁用",
    "return_word_box_tooltip": "当前 ONNX OCR 不返回单词级边框",

    # 高级选项 - PPStructureV3
    "struct_group": "结构化解析功能（PPStructureV3）",
    "struct_hint": "以下开关仅在使用 PPStructureV3 pipeline 时生效",
    "use_table": "表格识别（use_table_recognition）",
    "use_table_hint": "识别文档中的表格并还原为结构化数据（行/列/单元格），导出 Excel/Word 表格的核心功能",
    "use_formula": "公式识别（use_formula_recognition）",
    "use_formula_hint": "识别数学公式并转为 LaTeX 格式。关闭可加速处理非学术文档",
    "use_chart": "图表识别（use_chart_recognition）",
    "use_chart_hint": "识别柱状图/饼图/折线图等，转为结构化表格数据。需要 PP-Chart2Table 模型（1.3GB）",
    "use_seal": "印章识别（use_seal_recognition）",
    "use_seal_hint": "识别圆形/椭圆形印章中的弯曲文字。适合合同、证书等盖章文档",
    "use_region_det": "区域检测（use_region_detection）",
    "use_region_det_hint": "在版面分析基础上进一步检测图文混排区域，提升复杂版面的解析精度",

    # 高级选项 - 版面分析
    "layout_group": "版面分析参数（PPStructureV3）",
    "layout_thresh": "版面检测阈值：",
    "layout_thresh_hint": "版面区域的最低置信度。降低可检测出更多区域块，但可能引入误检。默认 0.5",
    "layout_nms": "版面 NMS 阈值：",
    "layout_nms_hint": "非极大值抑制阈值，用于合并重叠的版面区域框。值越高保留的重叠框越多",
    "layout_unclip": "版面框扩展比例：",
    "layout_unclip_hint": "版面区域框向外扩展的比例，0 表示使用默认值",
    "layout_merge_mode": "区域合并模式：",
    "layout_merge_default": "默认",
    "layout_merge_large": "large — 合并大区域",
    "layout_merge_small": "small — 合并小区域",
    "layout_merge_hint": "控制如何合并相邻的版面区域。large 适合报纸/杂志等大分栏版面",

    # 高级选项 - 印章
    "seal_group": "印章检测参数（PPStructureV3）",
    "seal_det_thresh": "印章检测阈值：",
    "seal_det_thresh_hint": "印章文字检测的二值化阈值。印章颜色较浅时可适当降低",
    "seal_box_thresh": "印章框置信阈值：",
    "seal_box_thresh_hint": "印章文字框的最低置信度",
    "seal_unclip": "印章框扩展比例：",
    "seal_unclip_hint": "印章文字框向外扩展的比例",
    "seal_rec_thresh": "印章识别置信过滤：",
    "seal_rec_thresh_hint": "低于此值的印章文字识别结果被丢弃",

    # 高级选项 - PDF
    "pdf_input_group": "PDF 输入设置",
    "render_dpi": "渲染 DPI：",
    "render_dpi_hint": "PDF 页面渲染为图片的分辨率。默认 200 适合大多数场景；扫描件提质可调到 300，最高 600",

    # 后端提示
    "backend_structure": "当前实际后端：PPStructureV3（需要 PaddlePaddle）",
    "backend_onnx": "当前实际后端：ONNX OCR。方向检测、文本行方向、检测阈值、识别阈值、batch size 会生效；弯曲矫正和单词级边框不可用。",
    "backend_paddle": "当前实际后端：PaddleOCR。所选 OCR 高级参数会传给 Paddle。",
    "backend_missing": "当前环境缺少所选 OCR 后端，请调整语言或速度模式。",

    # ── 拖拽区域 ──
    "file_filter": "支持的文件 ({ext});;所有文件 (*)",
    "drop_idle": "拖拽图片、PDF 或文件夹到此处",
    "drop_sub": "点击选择  |  拖拽文件  |  Cmd+V 粘贴截图",
    "drop_hover": "松开以添加文件",
    "drop_select_files": "选择文件（可多选）",
    "drop_reselect": "{size}  --  点击重新选择",
    "drop_multi_files": "已选择 {count} 个文件（{size} MB）",
    "drop_multi_reselect": "{name} 等  --  点击重新选择",

    # ── 格式卡片 ──
    "fmt_txt": "纯文本",
    "fmt_pdf": "可搜索 PDF",
    "fmt_word": "保留版面结构",
    "fmt_html": "网页格式",
    "fmt_excel": "表格数据",
    "fmt_rtf": "富文本格式",

    # ── 预览面板 ──
    "preview_title": "OCR 结果预览",
    "preview_empty_sub": "完成转换后自动显示识别结果",
    "preview_step_1": "1.  在「转换」页选择文件并开始识别",
    "preview_step_2": "2.  等待 OCR 处理完成",
    "preview_step_3": "3.  结果将在此处自动展示",
    "preview_start_btn": "选择文件开始转换",
    "preview_search_placeholder": "搜索文本...",
    "preview_search_btn": "搜索",
    "preview_copy_all": "复制全文",
    "preview_copied": "已复制",
    "preview_zoom_fit": "适应",
    "preview_loading": "正在加载预览图...",
    "preview_char_count": "{page_chars:,} / {total_chars:,} 字",
    "preview_pages": "{count} 页",

    # ── 设置面板 ──
    "settings_title": "设置",
    "settings_ui_language": "界面语言",
    "settings_ocr_language": "默认识别语言",
    "settings_output_dir": "默认输出目录",
    "settings_select": "选择",
    "settings_open": "打开",
    "settings_model_cache": "模型缓存",
    "settings_calculating": "正在计算...",
    "settings_refresh": "刷新",
    "settings_delete_paddle": "删除 PaddleX 模型",
    "settings_about": "关于",
    "settings_about_text": (
        "PaddleOCR 桌面版 v{version}\n\n"
        "识别引擎：ONNX Runtime（PP-OCRv5）+ 可选 PaddlePaddle（PPStructureV3）\n"
        "UI 框架：PySide6 (Qt 6)\n\n"
        "支持格式：TXT / PDF / Word / HTML / Excel / RTF"
    ),
    "settings_select_output_dir": "选择默认输出目录",
    "settings_cache_not_found": "未找到模型目录",
    "settings_cache_onnx": "ONNX 模型",
    "settings_cache_paddlex": "PaddleX 缓存",
    "settings_cache_read_error": "读取失败",
    "settings_cache_models": "已缓存模型：{count} 个",
    "settings_cache_size": "占用空间：{size} MB",
    "settings_delete_title": "⚠️ 删除模型文件",
    "settings_delete_confirm": (
        "即将永久删除 PaddleX 模型文件（{size} MB）：\n"
        "  {path}\n\n"
        "删除后使用 PaddlePaddle 引擎时需要重新下载模型。\n"
        "ONNX 模型不受影响。\n\n"
        "确定要删除吗？"
    ),
    "settings_deleted_title": "已删除",
    "settings_deleted_msg": "PaddleX 模型文件已删除。下次使用时将重新下载。",

    # ── 模型管理 ──
    "settings_onnx_models": "ONNX 模型管理",
    "model_mobile": "Mobile 模型（速度优先）",
    "model_server": "Server 模型（精度优先）",
    "model_available": "✓ 可用",
    "model_missing": "✗ 未找到",
    "model_download": "下载 Server 模型",
    "model_downloading": "正在下载... {pct}%",
    "model_download_done": "下载完成",
    "model_download_error": "下载失败：{error}",
    "model_download_confirm_title": "下载 Server 模型",
    "model_download_confirm": (
        "将从 GitHub 下载 PP-OCRv5 Server 模型（约 165 MB）\n"
        "保存到：{path}\n\n"
        "下载完成后即可使用「均衡」模式获得更高识别精度。\n\n"
        "继续下载？"
    ),

    # ── 进度对话框 ──
    "progress_title": "正在处理",
    "progress_init": "正在初始化模型...",
    "progress_page": "第 {page}/{total} 页  ({pct}%)",
    "progress_speed": "{speed} 页/秒  \u2022  预计剩余 {remaining}",
    "progress_cancel": "取消",
    "progress_cancelling": "正在取消...",

    # ── 主窗口对话框 ──
    "batch_prefix": "文件 {index}/{total}: ",
    "time_seconds": "{seconds} 秒",
    "time_minutes": "{minutes} 分 {seconds} 秒",
    "batch_done_title": "批量转换完成",
    "batch_done_msg": "批量转换完成  {success}/{total} 成功  耗时 {time}",
    "batch_done_fail": "  失败: {files}",
    "batch_notify_title": "PaddleOCR 批量转换完成",
    "open_dir": "打开目录",
    "close": "关闭",
    "convert_done_title": "转换完成",
    "convert_done_msg": "转换完成  {time}  {pages}  {chars} 字",
    "page_count": "{count} 页",
    "notify_done_title": "PaddleOCR 转换完成",
    "open_file": "打开文件",
    "export_error": "导出失败",
    "process_error": "处理出错",
    "notify_error_title": "PaddleOCR 处理出错",
}
