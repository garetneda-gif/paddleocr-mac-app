# PaddleOCR Desktop

A macOS desktop application for converting scanned PDFs and images into searchable PDFs with selectable text. Built with PySide6 and powered by dual OCR backends: ONNX Runtime and PaddlePaddle (PP-OCRv5 + PPStructureV3).

## Features

- **Searchable PDF output** — invisible text layer precisely aligned to original text positions
- **Dual OCR backends** — ONNX Runtime for speed, PaddlePaddle PPStructureV3 for layout-aware analysis
- **Multi-format export** — PDF, Word (.docx), Excel, HTML, RTF, plain text
- **Drag-and-drop UI** — drop files or folders, one-click conversion
- **Batch processing** — process entire directories with progress tracking
- **macOS native feel** — clean PySide6 interface following macOS design conventions

## Architecture

```
User drops file → QuickConvertPanel
  → OCRWorker (QThread) → ocr_subprocess (ProcessPoolExecutor, spawn)
    → OnnxOCREngine or PaddleOCR or StructureEngine
  → DocumentResult (pages → blocks → text/bbox/confidence)
  → ExportRouter → Converter (PDF/Word/HTML/Excel/RTF/TXT)
  → PreviewPanel displays result
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Subprocess OCR execution | Avoids GIL blocking the UI thread |
| `spawn` context for ProcessPoolExecutor | Prevents fork-related crashes with numpy/cv2 |
| Width-first fontsize for PDF text layer | Matches text width to detection bbox (Umi-OCR approach) |
| Line-level blocks from both backends | Each text line has its own bbox for precise overlay |
| CPU thread limiting (`OMP_NUM_THREADS=2`) | Prevents OCR from saturating all cores |

### Module Overview

| Module | Purpose |
|--------|---------|
| `app/core/onnx_engine.py` | ONNX backend: DB text detection + CRNN recognition |
| `app/core/structure_engine.py` | PaddlePaddle backend: PPStructureV3 layout analysis |
| `app/core/ocr_subprocess.py` | Singleton ProcessPoolExecutor for subprocess OCR |
| `app/core/pdf_processor.py` | PDF text detection + page rendering (PyMuPDF) |
| `app/converters/pdf_converter.py` | Searchable PDF export with transparent text layer |
| `app/converters/` | Format-specific exporters sharing `layout_analyzer.py` |
| `app/ui/main_window.py` | Central coordinator: file handling, export, preview |

## Getting Started

### Prerequisites

- Python 3.12
- macOS (tested on Apple Silicon)

### Setup

```bash
# Create virtual environment and install dependencies
bash setup_venv.sh

# Or manually:
python -m venv .venv
source .venv/bin/activate
pip install paddlepaddle==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
pip install -r requirements.txt
```

### Run

```bash
source .venv/bin/activate
python main.py
```

### Build macOS App

```bash
.venv/bin/python -m PyInstaller packaging/pyinstaller.spec --noconfirm
# Output: dist/PaddleOCR.app
```

## How the Searchable PDF Text Layer Works

The text layer overlay follows the approach used by [Umi-OCR](https://github.com/hiroi-sora/Umi-OCR) and [RapidOCR](https://github.com/RapidAI/RapidOCR):

1. **Line-level blocks** — each detected text line has its own bounding box (not merged into paragraphs)
2. **Width-first fontsize** — `fontsize = bbox_width / font.text_length(text, fontsize=1)`, capped by line height
3. **Baseline at bbox bottom** — `insert_point = (x0, y_bottom)`
4. **Invisible but selectable** — `render_mode=3` (PDF spec Tr=3)

This produces text selections that precisely match the original text positions.

## OCR Backend Selection

| Condition | Backend |
|-----------|---------|
| ONNX models available + language is `ch` or `en` | ONNX Runtime |
| PaddlePaddle installed | PaddlePaddle PPStructureV3 |
| Neither available | Error |

ONNX Runtime is preferred for its faster inference and smaller footprint. PaddlePaddle PPStructureV3 provides richer layout analysis (tables, figures, captions).

## Testing

```bash
pytest tests/
pytest tests/test_onnx_engine.py -k "test_detect"  # single test

# End-to-end smoke test (requires ONNX models)
python tools/smoke_real_ocr.py
```

## Acknowledgments

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) — OCR models and PaddlePaddle framework
- [Umi-OCR](https://github.com/hiroi-sora/Umi-OCR) — PDF text layer overlay approach
- [RapidOCR](https://github.com/RapidAI/RapidOCR) — Detection box post-processing and reading-order sort
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) — PDF rendering and text insertion

## License

MIT
