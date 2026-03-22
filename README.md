# PaddleOCR Desktop

[English](#english) | [简体中文](#简体中文)

---

## English

A macOS desktop application for converting scanned PDFs and images into searchable PDFs with selectable text. Built with PySide6 and powered by dual OCR backends: ONNX Runtime and PaddlePaddle (PP-OCRv5 + PPStructureV3).

### Features

- **Searchable PDF output** — invisible text layer precisely aligned to original text positions
- **Dual OCR backends** — ONNX Runtime for speed, PaddlePaddle PPStructureV3 for layout-aware analysis
- **Multi-format export** — PDF, Word (.docx), Excel, HTML, RTF, plain text
- **Drag-and-drop UI** — drop files or folders, one-click conversion
- **Batch processing** — process entire directories with progress tracking
- **Multi-language UI** — supports Chinese and English interface
- **macOS native feel** — clean PySide6 interface following macOS design conventions

### Architecture

```
User drops file → QuickConvertPanel
  → OCRWorker (QThread) → ocr_subprocess (ProcessPoolExecutor, spawn)
    → OnnxOCREngine or PaddleOCR or StructureEngine
  → DocumentResult (pages → blocks → text/bbox/confidence)
  → ExportRouter → Converter (PDF/Word/HTML/Excel/RTF/TXT)
  → PreviewPanel displays result
```

#### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Subprocess OCR execution | Avoids GIL blocking the UI thread |
| `spawn` context for ProcessPoolExecutor | Prevents fork-related crashes with numpy/cv2 |
| Width-first fontsize for PDF text layer | Matches text width to detection bbox (Umi-OCR approach) |
| Line-level blocks from both backends | Each text line has its own bbox for precise overlay |
| CPU thread limiting (`OMP_NUM_THREADS=2`) | Prevents OCR from saturating all cores |
| Dictionary-based i18n | Lightweight, no .ts/.qm compilation needed |

#### Module Overview

| Module | Purpose |
|--------|---------|
| `app/core/onnx_engine.py` | ONNX backend: DB text detection + CRNN recognition |
| `app/core/structure_engine.py` | PaddlePaddle backend: PPStructureV3 layout analysis |
| `app/core/ocr_subprocess.py` | Singleton ProcessPoolExecutor for subprocess OCR |
| `app/core/pdf_processor.py` | PDF text detection + page rendering (PyMuPDF) |
| `app/converters/pdf_converter.py` | Searchable PDF export with transparent text layer |
| `app/converters/` | Format-specific exporters sharing `layout_analyzer.py` |
| `app/ui/main_window.py` | Central coordinator: file handling, export, preview |
| `app/i18n/` | Internationalization: `zh_CN.py`, `en_US.py`, `tr()` lookup |

### Getting Started

#### Prerequisites

- Python 3.12
- macOS (tested on Apple Silicon)

#### Setup

```bash
# Create virtual environment and install dependencies
bash setup_venv.sh

# Or manually:
python -m venv .venv
source .venv/bin/activate
pip install paddlepaddle==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
pip install -r requirements.txt
```

#### Run

```bash
source .venv/bin/activate
python main.py
```

#### Build macOS App

```bash
.venv/bin/python -m PyInstaller packaging/pyinstaller.spec --noconfirm
# Output: dist/PaddleOCR.app
```

### How the Searchable PDF Text Layer Works

The text layer overlay follows the approach used by [Umi-OCR](https://github.com/hiroi-sora/Umi-OCR) and [RapidOCR](https://github.com/RapidAI/RapidOCR):

1. **Line-level blocks** — each detected text line has its own bounding box (not merged into paragraphs)
2. **Width-first fontsize** — `fontsize = bbox_width / font.text_length(text, fontsize=1)`, capped by line height
3. **Baseline at bbox bottom** — `insert_point = (x0, y_bottom)`
4. **Invisible but selectable** — `render_mode=3` (PDF spec Tr=3)

This produces text selections that precisely match the original text positions.

### OCR Backend Selection

| Condition | Backend |
|-----------|---------|
| ONNX models available + language is `ch` or `en` | ONNX Runtime |
| PaddlePaddle installed | PaddlePaddle PPStructureV3 |
| Neither available | Error |

ONNX Runtime is preferred for its faster inference and smaller footprint. PaddlePaddle PPStructureV3 provides richer layout analysis (tables, figures, captions).

### Testing

```bash
pytest tests/
pytest tests/test_onnx_engine.py -k "test_detect"  # single test

# End-to-end smoke test (requires ONNX models)
python tools/smoke_real_ocr.py
```

### Acknowledgments

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) — OCR models and PaddlePaddle framework
- [Umi-OCR](https://github.com/hiroi-sora/Umi-OCR) — PDF text layer overlay approach
- [RapidOCR](https://github.com/RapidAI/RapidOCR) — Detection box post-processing and reading-order sort
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) — PDF rendering and text insertion

### License

MIT

---

## 简体中文

macOS 桌面应用，可将扫描版 PDF 和图片转换为可搜索的 PDF（含可选中文字层）。基于 PySide6 构建，支持双 OCR 后端：ONNX Runtime 和 PaddlePaddle（PP-OCRv5 + PPStructureV3）。

### 功能特性

- **可搜索 PDF 输出** — 不可见文字层精确对齐原文位置
- **双 OCR 后端** — ONNX Runtime 追求速度，PaddlePaddle PPStructureV3 支持版面分析
- **多格式导出** — PDF、Word (.docx)、Excel、HTML、RTF、纯文本
- **拖拽式 UI** — 拖入文件或文件夹，一键转换
- **批量处理** — 支持整个目录批量处理，实时进度跟踪
- **多语言界面** — 支持中文和英文界面切换
- **macOS 原生风格** — 简洁的 PySide6 界面，遵循 macOS 设计规范

### 架构

```
用户拖入文件 → QuickConvertPanel
  → OCRWorker (QThread) → ocr_subprocess (ProcessPoolExecutor, spawn)
    → OnnxOCREngine 或 PaddleOCR 或 StructureEngine
  → DocumentResult (pages → blocks → text/bbox/confidence)
  → ExportRouter → Converter (PDF/Word/HTML/Excel/RTF/TXT)
  → PreviewPanel 显示结果
```

#### 关键设计决策

| 决策 | 原因 |
|------|------|
| 子进程执行 OCR | 避免 GIL 阻塞 UI 线程 |
| ProcessPoolExecutor 使用 `spawn` 上下文 | 防止 numpy/cv2 fork 相关崩溃 |
| PDF 文字层宽度优先字号 | 文字宽度匹配检测框（Umi-OCR 方案） |
| 双后端统一行级文本块 | 每行文字有独立 bbox，精确覆盖 |
| CPU 线程限制 (`OMP_NUM_THREADS=2`) | 防止 OCR 吃满所有核心 |
| 基于字典的 i18n | 轻量级，无需编译 .ts/.qm 文件 |

#### 模块概览

| 模块 | 职责 |
|------|------|
| `app/core/onnx_engine.py` | ONNX 后端：DB 文本检测 + CRNN 文本识别 |
| `app/core/structure_engine.py` | PaddlePaddle 后端：PPStructureV3 版面分析 |
| `app/core/ocr_subprocess.py` | 单例 ProcessPoolExecutor，子进程执行 OCR |
| `app/core/pdf_processor.py` | PDF 文字层检测 + 页面渲染（PyMuPDF） |
| `app/converters/pdf_converter.py` | 可搜索 PDF 导出（透明文字层） |
| `app/converters/` | 各格式导出器，共享 `layout_analyzer.py` |
| `app/ui/main_window.py` | 中央协调器：文件处理、导出、预览 |
| `app/i18n/` | 国际化：`zh_CN.py`、`en_US.py`、`tr()` 查找 |

### 快速开始

#### 环境要求

- Python 3.12
- macOS（已在 Apple Silicon 上测试）

#### 安装

```bash
# 创建虚拟环境并安装依赖
bash setup_venv.sh

# 或手动安装：
python -m venv .venv
source .venv/bin/activate
pip install paddlepaddle==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
pip install -r requirements.txt
```

#### 运行

```bash
source .venv/bin/activate
python main.py
```

#### 打包 macOS App

```bash
.venv/bin/python -m PyInstaller packaging/pyinstaller.spec --noconfirm
# 输出：dist/PaddleOCR.app
```

### 可搜索 PDF 文字层原理

文字层叠加方案参考 [Umi-OCR](https://github.com/hiroi-sora/Umi-OCR) 和 [RapidOCR](https://github.com/RapidAI/RapidOCR)：

1. **行级文本块** — 每个检测文本行有独立边界框（不合并为段落）
2. **宽度优先字号** — `fontsize = bbox_width / font.text_length(text, fontsize=1)`，受行高限制
3. **基线在框底部** — `insert_point = (x0, y_bottom)`
4. **不可见但可选中** — `render_mode=3`（PDF 规范 Tr=3）

这样生成的文字选区能精确匹配原文位置。

### OCR 后端选择

| 条件 | 后端 |
|------|------|
| ONNX 模型可用 + 语言为 `ch` 或 `en` | ONNX Runtime |
| PaddlePaddle 已安装 | PaddlePaddle PPStructureV3 |
| 均不可用 | 报错 |

ONNX Runtime 推理更快、体积更小，优先使用。PaddlePaddle PPStructureV3 提供更丰富的版面分析（表格、图片、标题等）。

### 测试

```bash
pytest tests/
pytest tests/test_onnx_engine.py -k "test_detect"  # 单个测试

# 端到端冒烟测试（需要 ONNX 模型）
python tools/smoke_real_ocr.py
```

### 致谢

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) — OCR 模型和 PaddlePaddle 框架
- [Umi-OCR](https://github.com/hiroi-sora/Umi-OCR) — PDF 文字层叠加方案
- [RapidOCR](https://github.com/RapidAI/RapidOCR) — 检测框后处理和阅读顺序排序
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) — PDF 渲染和文字插入

### 许可证

MIT
