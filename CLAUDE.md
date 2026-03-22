# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
# Activate virtual environment / 激活虚拟环境
source .venv/bin/activate

# Run the app / 运行应用
python main.py

# Run tests / 运行测试
pytest tests/
pytest tests/test_onnx_engine.py -k "test_detect"   # single test / 单个测试

# Build macOS .app / 打包 macOS .app
.venv/bin/python -m PyInstaller packaging/pyinstaller.spec --noconfirm

# Create DMG / 创建 DMG
hdiutil create -volname PaddleOCR -srcfolder dist/PaddleOCR.app -ov -format UDZO dist/PaddleOCR.dmg

# End-to-end smoke test (requires ONNX models) / 端到端验证（需要 ONNX 模型）
python tools/smoke_real_ocr.py
```

Setup with `bash setup_venv.sh` (creates .venv, installs PaddlePaddle + requirements.txt).

环境搭建用 `bash setup_venv.sh`（创建 .venv、安装 PaddlePaddle + requirements.txt）。

## Architecture / 架构

PySide6 desktop app with dual OCR backends (ONNX Runtime / PaddlePaddle), subprocess-based inference.

PySide6 桌面应用，双 OCR 后端（ONNX Runtime / PaddlePaddle），子进程执行推理。

**Data flow / 数据流：**
```
User drops file → QuickConvertPanel
  → OCRWorker (QThread) → ocr_subprocess (ProcessPoolExecutor, spawn)
    → OnnxOCREngine or PaddleOCR or StructureEngine
  → DocumentResult (pages → blocks → text/bbox/confidence)
  → ExportRouter → Converter (TXT/PDF/Word/HTML/Excel/RTF)
  → PreviewPanel displays result
```

**Key modules / 关键模块：**

| Module / 模块 | Purpose / 职责 |
|------|------|
| `app/core/onnx_engine.py` | ONNX backend: DBDetector (text detection) + CRNNRecognizer (text recognition) |
| `app/core/ocr_engine.py` | PaddlePaddle backend wrapper |
| `app/core/ocr_subprocess.py` | Singleton ProcessPoolExecutor, subprocess OCR with JSON serialization |
| `app/core/ocr_worker.py` | QThread wrapper, signal/slot for UI (progress/finished/error) |
| `app/core/pdf_processor.py` | PDF text layer detection + page rendering (PyMuPDF), auto DPI reduction for large PDFs |
| `app/core/export_router.py` | Select Converter by OutputFormat |
| `app/converters/` | Format exporters, sharing `layout_analyzer.py` for layout analysis |
| `app/ui/main_window.py` | Central coordinator: single/batch processing, export, preview switching |
| `app/ui/theme.py` | Design tokens (colors/radius) + version number (read by PyInstaller) |
| `app/i18n/` | Internationalization: `zh_CN.py`, `en_US.py`, `tr()` lookup function |
| `app/models/` | DocumentResult / PageResult / BlockResult / OCRJob data structures |

**OCR backend selection logic (`resolve_ocr_backend`):**
- ONNX available + language supported (ch/en) → use ONNX
- Otherwise PaddlePaddle available → use Paddle
- Neither available → raise exception

## Important Constraints / 重要约束

- **CPU thread limiting / CPU 线程限制**: `main.py` sets `OMP_NUM_THREADS=2`, ONNX SessionOptions also limits `intra_op_num_threads=2` to prevent CPU saturation
- **Module preloading / 模块预加载**: numpy/cv2/onnxruntime must be imported in the main thread, otherwise QThread recursive crash
- **Subprocess uses spawn / 子进程用 spawn**: Avoids GIL issues, ProcessPoolExecutor uses `mp.get_context("spawn")`
- **SSL conflict / SSL 冲突**: cv2 ships old libcrypto conflicting with Python _ssl, replaced with Homebrew OpenSSL post-build (pyinstaller.spec)
- **ONNX model search order / ONNX 模型搜索顺序**: env var → external drive → `~/.paddlex/onnx_models` → bundled resources (with timeout for drive sleep detection)

## Styling / 样式

Global styles in `resources/styles.qss`, component inline styles reference `app/ui/theme.py` design tokens. Follows macOS native style.

全局样式在 `resources/styles.qss`，组件内联样式引用 `app/ui/theme.py` 的设计令牌。遵循 macOS 原生风格。

## i18n / 国际化

Dictionary-based translation system in `app/i18n/`. Use `tr("key")` for all UI strings. Language files: `zh_CN.py` (Chinese), `en_US.py` (English). Language switching is live via Settings panel.

基于字典的翻译系统在 `app/i18n/`。所有 UI 字符串使用 `tr("key")`。语言文件：`zh_CN.py`（中文）、`en_US.py`（英文）。通过设置面板实时切换语言。
