# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — PaddleOCR macOS 桌面应用（ONNX + PaddlePaddle 双后端）
# 用法: .venv/bin/python -m PyInstaller packaging/pyinstaller.spec --noconfirm

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

block_cipher = None
ROOT = Path(SPECPATH).parent

# 从 theme.py 读取版本号
sys.path.insert(0, str(ROOT))
from app.ui.theme import __version__ as APP_VERSION
EXTERNAL_ONNX_DIR = Path("/Volumes/MOVESPEED/存储/models/onnx")
EXTERNAL_CHAR_DICT = Path("/Volumes/MOVESPEED/存储/models/ppocr_keys_v5.txt")


def _drop_nested_app_bundles(items):
    filtered = []
    for src, dest in items:
        if ".app/" in src or src.endswith(".app"):
            continue
        if ".app/" in dest or dest.endswith(".app"):
            continue
        filtered.append((src, dest))
    return filtered


def _drop_cv2_ssl_conflict(items):
    """不再使用：保留 cv2 的 SSL 库，后处理中用正确版本覆盖。"""
    return items


def _optional_data(src: Path, dest: str):
    return [(str(src), dest)] if src.exists() else []


def _optional_data_if_missing(src: Path, dest: str, existing: Path):
    return [(str(src), dest)] if src.exists() and not existing.exists() else []


def _safe_collect_all(pkg):
    """collect_all 的安全包装，失败时返回空列表。"""
    try:
        d, b, h = collect_all(pkg)
        return d, b, h
    except Exception:
        return [], [], []


# ---- ONNX Runtime ----
onnx_datas, onnx_bins, onnx_hi = collect_all('onnxruntime')

# ---- PaddlePaddle（可选后端，用于 PPStructureV3） ----
paddle_datas, paddle_bins, paddle_hi = _safe_collect_all('paddle')
paddlex_datas, paddlex_bins, paddlex_hi = _safe_collect_all('paddlex')
paddleocr_datas, paddleocr_bins, paddleocr_hi = _safe_collect_all('paddleocr')

# ---- PPStructureV3 额外依赖 ----
pypdfium2_d, pypdfium2_b, pypdfium2_h = _safe_collect_all('pypdfium2')
tiktoken_d, tiktoken_b, tiktoken_h = _safe_collect_all('tiktoken')
sentencepiece_d, sentencepiece_b, sentencepiece_h = _safe_collect_all('sentencepiece')

# PySide6 Qt 插件、翻译等
pyside_datas, pyside_bins, pyside_hi = collect_all('PySide6')
pyside_datas = _drop_nested_app_bundles(pyside_datas)
pyside_bins = _drop_nested_app_bundles(pyside_bins)

# OpenCV 需要 collect_all 以包含 .so/.dylib
cv2_datas, cv2_bins, cv2_hi = collect_all('cv2')
# 移除 cv2 自带的 libcrypto/libssl（与 Python _ssl 冲突导致 HTTPS 不可用）
cv2_datas = _drop_cv2_ssl_conflict(cv2_datas)
cv2_bins = _drop_cv2_ssl_conflict(cv2_bins)

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
    + collect_submodules('google.protobuf')
    + collect_submodules('httpx')
    + collect_submodules('filelock')
    + collect_submodules('pypdfium2')
    + collect_submodules('tiktoken')
    + collect_submodules('sentencepiece')
    + collect_submodules('regex')
    + collect_submodules('bs4')
    + collect_submodules('einops')
    + collect_submodules('scipy')
    + collect_submodules('sklearn')
    + collect_submodules('safetensors')
)

all_datas = (
    onnx_datas + pyside_datas + cv2_datas
    + pyclipper_d + shapely_d
    + paddle_datas + paddlex_datas + paddleocr_datas
    + pypdfium2_d + tiktoken_d + sentencepiece_d
    + [(str(ROOT / "resources"), "resources")]
    + _optional_data(EXTERNAL_ONNX_DIR / "PP-OCRv5_server_det.onnx", "resources/models/onnx")
    + _optional_data(EXTERNAL_ONNX_DIR / "PP-OCRv5_server_rec.onnx", "resources/models/onnx")
    + _optional_data_if_missing(
        EXTERNAL_CHAR_DICT,
        "resources/models",
        ROOT / "resources" / "models" / "ppocr_keys_v5.txt",
    )
)
all_binaries = (
    onnx_bins + pyside_bins + cv2_bins
    + pyclipper_b + shapely_b
    + paddle_bins + paddlex_bins + paddleocr_bins
    + pypdfium2_b + tiktoken_b + sentencepiece_b
)
all_hiddenimports = (
    onnx_hi + pyside_hi + cv2_hi
    + pyclipper_h + shapely_h + extra_hi
    + paddle_hi + paddlex_hi + paddleocr_hi
    + pypdfium2_h + tiktoken_h + sentencepiece_h
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
              'transformers', 'tokenizers'],
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
    argv_emulation=False,
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
    icon=os.path.join(ROOT, "resources", "AppIcon.icns"),
    bundle_identifier="com.paddleocr.desktop",
    info_plist={
        "CFBundleDisplayName": "PaddleOCR",
        "CFBundleShortVersionString": APP_VERSION,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
)

# ---- 后处理：用 Homebrew OpenSSL 替换 cv2 的旧版 libcrypto/libssl ----
# cv2 自带的 OpenSSL 版本过低，缺少 X509_STORE_get1_objects 等符号，
# 导致 Python _ssl 模块无法使用 HTTPS。
# 打包后 cv2 的 dylib 目录名为 __dot__dylibs（PyInstaller 编码），
# 故 glob 用 *dylibs 匹配。替换后修正 install name 以脱离 Homebrew 绝对路径。
import glob, shutil, subprocess as _sp
_app_path = os.path.join(DISTPATH, "PaddleOCR.app")
_brew_ssl = "/opt/homebrew/opt/openssl@3/lib"
_replaced = {}  # lib_name -> [replaced_paths]
for _lib in ["libcrypto.3.dylib", "libssl.3.dylib"]:
    _src = os.path.join(_brew_ssl, _lib)
    if not os.path.exists(_src):
        print(f"POST-BUILD: WARNING — Homebrew OpenSSL not found: {_src}")
        continue
    _replaced[_lib] = []
    for _cv2_lib in glob.glob(os.path.join(_app_path, "**", "*dylibs", _lib), recursive=True):
        shutil.copy2(_src, _cv2_lib)
        # 修正 install name，脱离 Homebrew 绝对路径
        _sp.run(["install_name_tool", "-id", f"@loader_path/{_lib}", _cv2_lib],
                check=False, capture_output=True)
        _rc = _sp.run(["codesign", "--force", "--sign", "-", _cv2_lib], capture_output=True)
        if _rc.returncode != 0:
            print(f"POST-BUILD: WARNING — codesign failed for {_cv2_lib}: {_rc.stderr}")
        _replaced[_lib].append(_cv2_lib)
        print(f"POST-BUILD: replaced {_cv2_lib} with Homebrew OpenSSL")

# 修正 libssl 对 libcrypto 的引用（Homebrew 用绝对路径，需改为 @loader_path）
for _ssl_path in _replaced.get("libssl.3.dylib", []):
    # 找出 libssl 当前引用的 libcrypto 绝对路径
    _otool = _sp.run(["otool", "-L", _ssl_path], capture_output=True, text=True)
    for _line in _otool.stdout.splitlines():
        _line = _line.strip()
        if "libcrypto" in _line and ("homebrew" in _line.lower() or "Cellar" in _line):
            _old_ref = _line.split("(")[0].strip()
            _sp.run(["install_name_tool", "-change", _old_ref,
                     "@loader_path/libcrypto.3.dylib", _ssl_path],
                    check=False, capture_output=True)
            _sp.run(["codesign", "--force", "--sign", "-", _ssl_path], capture_output=True)
            print(f"POST-BUILD: fixed libssl->libcrypto ref: {_old_ref} -> @loader_path/")
            break

if not any(_replaced.values()):
    print("POST-BUILD: WARNING — no cv2 dylibs found to replace! SSL may be broken.")
