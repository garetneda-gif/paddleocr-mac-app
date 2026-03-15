# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — PaddleOCR macOS 桌面应用（ONNX Runtime 版）
# 用法: cd /Users/jikunren/Documents/paddleocr && source .venv/bin/activate && pyinstaller packaging/pyinstaller.spec

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

block_cipher = None
ROOT = Path(SPECPATH).parent


def _drop_nested_app_bundles(items):
    filtered = []
    for src, dest in items:
        if ".app/" in src or src.endswith(".app"):
            continue
        if ".app/" in dest or dest.endswith(".app"):
            continue
        filtered.append((src, dest))
    return filtered

# ---- ONNX Runtime（替代 PaddlePaddle） ----
onnx_datas, onnx_bins, onnx_hi = collect_all('onnxruntime')

# PySide6 Qt 插件、翻译等
pyside_datas, pyside_bins, pyside_hi = collect_all('PySide6')
pyside_datas = _drop_nested_app_bundles(pyside_datas)
pyside_bins = _drop_nested_app_bundles(pyside_bins)

# OpenCV 需要 collect_all 以包含 .so/.dylib
cv2_datas, cv2_bins, cv2_hi = collect_all('cv2')

# ONNX 引擎 DB 后处理依赖
pyclipper_d, pyclipper_b, pyclipper_h = collect_all('pyclipper')
shapely_d, shapely_b, shapely_h = collect_all('shapely')

extra_hi = (
    collect_submodules('fitz')
    + collect_submodules('docx')
    + collect_submodules('openpyxl')
    + collect_submodules('reportlab')
    + collect_submodules('lxml')
    + collect_submodules('PIL')
    + collect_submodules('numpy')
    + collect_submodules('yaml')
)

all_datas = (
    onnx_datas + pyside_datas + cv2_datas
    + pyclipper_d + shapely_d
    + [(str(ROOT / "resources"), "resources")]
)
all_binaries = (
    onnx_bins + pyside_bins + cv2_bins
    + pyclipper_b + shapely_b
)
all_hiddenimports = (
    onnx_hi + pyside_hi + cv2_hi
    + pyclipper_h + shapely_h + extra_hi
    + ['app', 'app.models', 'app.core', 'app.converters', 'app.ui', 'app.utils']
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
    excludes=['tkinter', 'matplotlib', 'IPython', 'notebook', 'jupyter',
              'paddle', 'paddleocr', 'paddlex', 'transformers', 'tokenizers'],
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
    upx=False,
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
    icon=None,
    bundle_identifier="com.paddleocr.desktop",
    info_plist={
        "CFBundleDisplayName": "PaddleOCR",
        "CFBundleShortVersionString": "2.0.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
)
