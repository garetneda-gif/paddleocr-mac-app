# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行应用
python main.py

# 运行测试
pytest tests/
pytest tests/test_onnx_engine.py -k "test_detect"   # 单个测试

# 打包 macOS .app
.venv/bin/python -m PyInstaller packaging/pyinstaller.spec --noconfirm

# 端到端验证（需要 ONNX 模型可用）
python tools/smoke_real_ocr.py
```

环境搭建用 `bash setup_venv.sh`（创建 .venv、安装 PaddlePaddle + requirements.txt）。

## 架构

PySide6 桌面应用，双 OCR 后端（ONNX Runtime / PaddlePaddle），子进程执行推理。

**数据流：**
```
用户拖入文件 → QuickConvertPanel
  → OCRWorker (QThread) → ocr_subprocess (ProcessPoolExecutor, spawn)
    → OnnxOCREngine 或 PaddleOCR 或 StructureEngine
  → DocumentResult (pages → blocks → text/bbox/confidence)
  → ExportRouter → Converter (TXT/PDF/Word/HTML/Excel/RTF)
  → PreviewPanel 显示结果
```

**关键模块：**

| 模块 | 职责 |
|------|------|
| `app/core/onnx_engine.py` | ONNX 后端：DBDetector（文本检测）+ CRNNRecognizer（文本识别）+ 段落合并 |
| `app/core/ocr_engine.py` | PaddlePaddle 后端封装 |
| `app/core/ocr_subprocess.py` | 单例 ProcessPoolExecutor，子进程执行 OCR，JSON 序列化结果 |
| `app/core/ocr_worker.py` | QThread 封装，signal/slot 通知 UI（progress/finished/error） |
| `app/core/pdf_processor.py` | PDF 文字层检测 + 页面渲染（PyMuPDF），大 PDF 自动降 DPI |
| `app/core/export_router.py` | 根据 OutputFormat 选择 Converter |
| `app/converters/` | 各格式导出器，共享 `layout_analyzer.py` 做版面分析 |
| `app/ui/main_window.py` | 中央协调器：单文件/批量处理流程、导出、预览切换 |
| `app/ui/theme.py` | 设计令牌（颜色/圆角）+ 版本号（打包读取） |
| `app/models/` | DocumentResult / PageResult / BlockResult / OCRJob 数据结构 |

**OCR 后端选择逻辑（`resolve_ocr_backend`）：**
- ONNX 可用 + 语言支持（ch/en）→ 用 ONNX
- 否则 PaddlePaddle 可用 → 用 Paddle
- 都不可用 → 抛异常

## 重要约束

- **CPU 线程限制**：`main.py` 设置 `OMP_NUM_THREADS=2`，ONNX SessionOptions 也限制为 `intra_op_num_threads=2`，防止吃满 CPU
- **模块预加载**：numpy/cv2/onnxruntime 必须在主线程 import，否则 QThread 递归崩溃
- **子进程用 spawn**：避免 GIL 问题，ProcessPoolExecutor 使用 `mp.get_context("spawn")`
- **SSL 冲突**：cv2 自带旧版 libcrypto 与 Python _ssl 冲突，打包后用 Homebrew OpenSSL 替换（pyinstaller.spec 后处理）
- **ONNX 模型搜索顺序**：环境变量 → 外置硬盘 → `~/.paddlex/onnx_models` → 打包资源（带超时检测防硬盘休眠阻塞）

## 样式

全局样式在 `resources/styles.qss`，组件内联样式引用 `app/ui/theme.py` 的设计令牌。遵循 macOS 原生风格。
