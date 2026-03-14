# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — PaddleOCR macOS 桌面应用
# 用法: cd /Users/jikunren/Documents/paddleocr && source .venv/bin/activate && pyinstaller packaging/pyinstaller.spec

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

block_cipher = None
ROOT = Path(SPECPATH).parent

# ---- 自动收集 PaddlePaddle 生态的所有模块和数据 ----
paddle_datas, paddle_binaries, paddle_hiddenimports = collect_all('paddle')
paddleocr_datas, paddleocr_bins, paddleocr_hi = collect_all('paddleocr')
paddlex_datas, paddlex_bins, paddlex_hi = collect_all('paddlex')

# PySide6 Qt 插件、翻译等
pyside_datas, pyside_bins, pyside_hi = collect_all('PySide6')

# OpenCV 需要 collect_all 以包含 .so/.dylib
cv2_datas, cv2_bins, cv2_hi = collect_all('cv2')

# 其他依赖
extra_hi = collect_submodules('fitz') + collect_submodules('docx') + \
           collect_submodules('openpyxl') + collect_submodules('reportlab') + \
           collect_submodules('lxml') + collect_submodules('PIL') + \
           collect_submodules('numpy') + \
           collect_submodules('yaml') + collect_submodules('ruamel') + \
           collect_submodules('ruamel.yaml')

all_datas = paddle_datas + paddleocr_datas + paddlex_datas + pyside_datas + cv2_datas + [
    (str(ROOT / "resources"), "resources"),
]
all_binaries = paddle_binaries + paddleocr_bins + paddlex_bins + pyside_bins + cv2_bins
all_hiddenimports = (
    paddle_hiddenimports + paddleocr_hi + paddlex_hi + pyside_hi + cv2_hi + extra_hi + [
        'app', 'app.models', 'app.core', 'app.converters', 'app.ui', 'app.utils',
    ]
)

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'IPython', 'notebook', 'jupyter'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PaddleOCR",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX 对大型 native 库可能有问题
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=str(ROOT / "packaging" / "entitlements.plist"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PaddleOCR",
)

app = BUNDLE(
    coll,
    name="PaddleOCR.app",
    icon=None,  # TODO: 添加 .icns 图标
    bundle_identifier="com.paddleocr.desktop",
    info_plist={
        "CFBundleDisplayName": "PaddleOCR",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
)
