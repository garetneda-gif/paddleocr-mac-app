"""English translations."""

STRINGS: dict[str, str] = {
    # ── App ──
    "app_title": "PaddleOCR — Smart Document Recognition",

    # ── Sidebar ──
    "nav_convert": "Convert",
    "nav_preview": "Preview",
    "nav_settings": "Settings",
    "sidebar_processing": "Processing...",

    # ── Convert Panel ──
    "convert_title": "Quick Convert",
    "select_output_format": "Output format:",
    "ocr_language": "OCR language:",
    "mode_label": "Mode:",
    "mode_balanced": "Balanced (Server model)",
    "mode_speed": "Speed (Mobile model, 8x faster)",
    "mode_tooltip": "Different modes use different ONNX models; Server is more accurate, Mobile uses less memory",
    "start_convert": "Start",
    "select_file_first": "Please select a file first",
    "parallel_workers": "Parallel workers:",
    "parallel_tooltip": "Number of concurrent OCR subprocesses. 2 is good for most cases; more = faster but uses more memory",
    "force_ocr": "Force OCR (ignore existing PDF text layer)",
    "force_ocr_tooltip": "By default, PDFs with existing text layers are extracted directly (milliseconds).\nCheck this to force re-OCR, useful when the text layer is inaccurate.",
    "pdf_page_range": "PDF page range:",
    "pdf_page_hint": "For large PDFs, test with a few pages first. >50 pages auto-reduces DPI",
    "advanced_options": "Advanced options (engine-specific)",
    "advanced_collapsed": "▶ Advanced options (engine-specific)",
    "advanced_expanded": "▼ Advanced options (engine-specific)",
    "server_onnx_unavailable": "Server ONNX models not found, only Mobile mode available",

    # Advanced - Pipeline
    "pipeline_group": "Recognition Mode",
    "pipeline_label": "Pipeline:",
    "pipeline_auto": "Auto (based on output format)",
    "pipeline_ocr": "OCR (ONNX Runtime / Paddle)",
    "pipeline_structure": "PPStructureV3 (structured analysis)",
    "pipeline_auto_hint": "Auto mode: TXT/PDF/RTF use OCR; Word/HTML/Excel prefer structured analysis. Falls back to plain-text OCR if structured backend unavailable.",
    "preserve_layout": "TXT/RTF preserve layout",
    "preserve_layout_hint": "Uses PPStructureV3 for TXT/RTF export to preserve paragraph and heading hierarchy",
    "preserve_layout_tooltip": "Only available for TXT/RTF when structured backend is available",
    "no_paddle_hint": "⚠ PPStructureV3 unavailable (requires PaddlePaddle). Word/HTML/Excel will fall back to plain-text OCR export.",
    "onnx_lang_hint": "Only ONNX-supported languages available: Chinese, English.",

    # Advanced - Preprocessing
    "preprocess_group": "Document Preprocessing",
    "orientation_check": "Document orientation detection (use_doc_orientation_classify)",
    "orientation_hint": "Auto-detect and correct 90°/180°/270° rotation, useful for scanned documents with uncertain orientation",
    "unwarp_check": "Document unwarping (use_doc_unwarping)",
    "unwarp_hint": "Correct perspective distortion from phone-captured documents. Auto-disabled when ONNX OCR doesn't support it",
    "unwarp_tooltip": "ONNX OCR does not support document unwarping",
    "textline_ori_check": "Text line orientation detection (use_textline_orientation)",
    "textline_ori_hint": "Detect horizontal vs vertical text lines and process them separately, useful for vertical text documents",

    # Advanced - Detection
    "det_group": "Text Detection (OCR)",
    "det_limit_side": "Detection image long side limit:",
    "det_limit_side_hint": "Input image is scaled to this size before detection. Larger = more precise but slower, default 2048",
    "det_limit_type": "Limit type:",
    "det_limit_max": "max — limit long side",
    "det_limit_min": "min — limit short side",
    "det_limit_type_hint": "max: scale by long side (default); min: scale by short side, for very long/narrow images",
    "det_thresh": "Text area threshold (det_thresh):",
    "det_thresh_hint": "DB binarization threshold. Lower = detects faint/blurry text but may false-detect noise. Default 0.3",
    "det_box_thresh": "Text box confidence threshold (box_thresh):",
    "det_box_thresh_hint": "Minimum average confidence for detection boxes. Lower retains more weak text areas. Default 0.45",
    "det_unclip": "Text box expansion ratio (unclip_ratio):",
    "det_unclip_hint": "How much to expand detection boxes outward. Larger = looser boxes capturing more edge text. Default 2.0",

    # Advanced - Recognition
    "rec_group": "Text Recognition (OCR)",
    "rec_score_thresh": "Recognition confidence filter:",
    "rec_score_thresh_hint": "Results below this confidence are discarded. Set to 0 to keep all results. Increase to remove garbled text",
    "rec_batch": "Recognition batch size:",
    "rec_batch_hint": "Number of text lines per recognition batch. More = faster but uses more memory. CPU recommended: 1",
    "return_word_box": "Return word-level boxes (return_word_box)",
    "return_word_box_hint": "Return precise positions for each word in addition to line-level boxes. Only available with PaddleOCR, auto-disabled in ONNX mode",
    "return_word_box_tooltip": "ONNX OCR does not return word-level boxes",

    # Advanced - PPStructureV3
    "struct_group": "Structured Analysis (PPStructureV3)",
    "struct_hint": "These toggles only take effect when using the PPStructureV3 pipeline",
    "use_table": "Table recognition (use_table_recognition)",
    "use_table_hint": "Recognize tables and restore structured data (rows/columns/cells), core feature for Excel/Word table export",
    "use_formula": "Formula recognition (use_formula_recognition)",
    "use_formula_hint": "Recognize math formulas and convert to LaTeX. Disable to speed up non-academic documents",
    "use_chart": "Chart recognition (use_chart_recognition)",
    "use_chart_hint": "Recognize bar/pie/line charts and convert to structured table data. Requires PP-Chart2Table model (1.3GB)",
    "use_seal": "Seal recognition (use_seal_recognition)",
    "use_seal_hint": "Recognize curved text in circular/elliptical seals. Useful for contracts and certificates",
    "use_region_det": "Region detection (use_region_detection)",
    "use_region_det_hint": "Further detect mixed text-image regions on top of layout analysis, improving complex layout parsing accuracy",

    # Advanced - Layout
    "layout_group": "Layout Analysis (PPStructureV3)",
    "layout_thresh": "Layout detection threshold:",
    "layout_thresh_hint": "Minimum confidence for layout regions. Lower detects more regions but may introduce false positives. Default 0.5",
    "layout_nms": "Layout NMS threshold:",
    "layout_nms_hint": "Non-maximum suppression threshold for merging overlapping layout region boxes. Higher = more overlapping boxes retained",
    "layout_unclip": "Layout box expansion ratio:",
    "layout_unclip_hint": "How much layout region boxes expand outward, 0 uses default",
    "layout_merge_mode": "Region merge mode:",
    "layout_merge_default": "Default",
    "layout_merge_large": "large — merge large regions",
    "layout_merge_small": "small — merge small regions",
    "layout_merge_hint": "Controls how adjacent layout regions are merged. large suits newspaper/magazine multi-column layouts",

    # Advanced - Seal
    "seal_group": "Seal Detection (PPStructureV3)",
    "seal_det_thresh": "Seal detection threshold:",
    "seal_det_thresh_hint": "Binarization threshold for seal text detection. Lower for light-colored seals",
    "seal_box_thresh": "Seal box confidence threshold:",
    "seal_box_thresh_hint": "Minimum confidence for seal text boxes",
    "seal_unclip": "Seal box expansion ratio:",
    "seal_unclip_hint": "How much seal text boxes expand outward",
    "seal_rec_thresh": "Seal recognition confidence filter:",
    "seal_rec_thresh_hint": "Seal text recognition results below this value are discarded",

    # Advanced - PDF
    "pdf_input_group": "PDF Input Settings",
    "render_dpi": "Render DPI:",
    "render_dpi_hint": "PDF page rendering resolution. Default 200 suits most cases; 300 for better scan quality, max 600",

    # Backend hints
    "backend_structure": "Current backend: PPStructureV3 (requires PaddlePaddle)",
    "backend_onnx": "Current backend: ONNX OCR. Orientation detection, text line orientation, detection thresholds, recognition thresholds, batch size are active; unwarping and word-level boxes unavailable.",
    "backend_paddle": "Current backend: PaddleOCR. Selected OCR advanced parameters will be passed to Paddle.",
    "backend_missing": "Required OCR backend not found. Please adjust language or speed mode.",

    # ── Drop Zone ──
    "file_filter": "Supported files ({ext});;All files (*)",
    "drop_idle": "Drag images, PDFs, or folders here",
    "drop_sub": "Click to select  |  Drag files  |  Cmd+V paste screenshot",
    "drop_hover": "Release to add files",
    "drop_select_files": "Select files (multi-select)",
    "drop_reselect": "{size}  --  Click to reselect",
    "drop_multi_files": "{count} files selected ({size} MB)",
    "drop_multi_reselect": "{name} etc.  --  Click to reselect",

    # ── Format Cards ──
    "fmt_txt": "Plain text",
    "fmt_pdf": "Searchable PDF",
    "fmt_word": "Preserve layout",
    "fmt_html": "Web format",
    "fmt_excel": "Table data",
    "fmt_rtf": "Rich text format",

    # ── Preview Panel ──
    "preview_title": "OCR Result Preview",
    "preview_empty_sub": "Results will appear here after conversion",
    "preview_step_1": "1.  Select a file on the \"Convert\" page and start recognition",
    "preview_step_2": "2.  Wait for OCR processing to complete",
    "preview_step_3": "3.  Results will be displayed here automatically",
    "preview_start_btn": "Select file to start",
    "preview_search_placeholder": "Search text...",
    "preview_search_btn": "Search",
    "preview_copy_all": "Copy all",
    "preview_copied": "Copied",
    "preview_zoom_fit": "Fit",
    "preview_loading": "Loading preview...",
    "preview_char_count": "{page_chars:,} / {total_chars:,} chars",
    "preview_pages": "{count} pages",

    # ── Settings Panel ──
    "settings_title": "Settings",
    "settings_ui_language": "Interface Language",
    "settings_ocr_language": "Default OCR Language",
    "settings_output_dir": "Default Output Directory",
    "settings_select": "Browse",
    "settings_open": "Open",
    "settings_model_cache": "Model Cache",
    "settings_calculating": "Calculating...",
    "settings_refresh": "Refresh",
    "settings_delete_paddle": "Delete PaddleX Models",
    "settings_about": "About",
    "settings_about_text": (
        "PaddleOCR Desktop v{version}\n\n"
        "OCR Engine: ONNX Runtime (PP-OCRv5) + Optional PaddlePaddle (PPStructureV3)\n"
        "UI Framework: PySide6 (Qt 6)\n\n"
        "Supported formats: TXT / PDF / Word / HTML / Excel / RTF"
    ),
    "settings_select_output_dir": "Select default output directory",
    "settings_cache_not_found": "No model directories found",
    "settings_cache_onnx": "ONNX Models",
    "settings_cache_paddlex": "PaddleX Cache",
    "settings_cache_read_error": "Read failed",
    "settings_cache_models": "Cached models: {count}",
    "settings_cache_size": "Disk usage: {size} MB",
    "settings_delete_title": "⚠️ Delete Model Files",
    "settings_delete_confirm": (
        "Permanently delete PaddleX model files ({size} MB):\n"
        "  {path}\n\n"
        "You will need to re-download models when using the PaddlePaddle engine.\n"
        "ONNX models are not affected.\n\n"
        "Are you sure?"
    ),
    "settings_deleted_title": "Deleted",
    "settings_deleted_msg": "PaddleX model files deleted. They will be re-downloaded on next use.",

    # ── Progress Dialog ──
    "progress_title": "Processing",
    "progress_init": "Initializing model...",
    "progress_page": "Page {page}/{total}  ({pct}%)",
    "progress_speed": "{speed} pages/sec  \u2022  Est. remaining {remaining}",
    "progress_cancel": "Cancel",
    "progress_cancelling": "Cancelling...",

    # ── Main Window Dialogs ──
    "batch_prefix": "File {index}/{total}: ",
    "time_seconds": "{seconds} sec",
    "time_minutes": "{minutes} min {seconds} sec",
    "batch_done_title": "Batch Conversion Complete",
    "batch_done_msg": "Batch complete  {success}/{total} succeeded  Time: {time}",
    "batch_done_fail": "  Failed: {files}",
    "batch_notify_title": "PaddleOCR Batch Conversion Complete",
    "open_dir": "Open Folder",
    "close": "Close",
    "convert_done_title": "Conversion Complete",
    "convert_done_msg": "Complete  {time}  {pages}  {chars} chars",
    "page_count": "{count} pages",
    "notify_done_title": "PaddleOCR Conversion Complete",
    "open_file": "Open File",
    "export_error": "Export Failed",
    "process_error": "Processing Error",
    "notify_error_title": "PaddleOCR Processing Error",
}
