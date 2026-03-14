#!/usr/bin/env bash
# =============================================================
# setup_venv.sh — 一键搭建 paddleocr macOS 开发环境
# 用法：bash setup_venv.sh
# =============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"

# ----------------------------------------------------------
# 1. 定位 python3.12
# ----------------------------------------------------------
PYTHON312=""

# 优先使用 brew --prefix 定位（架构无关）
if command -v brew &>/dev/null; then
    BREW_PYTHON="$(brew --prefix python@3.12 2>/dev/null)/bin/python3.12"
    if [ -x "${BREW_PYTHON}" ]; then
        PYTHON312="${BREW_PYTHON}"
    fi
fi

# 回退：直接检查常见路径
if [ -z "${PYTHON312}" ]; then
    for candidate in \
        /opt/homebrew/bin/python3.12 \
        /usr/local/bin/python3.12; do
        if [ -x "${candidate}" ]; then
            PYTHON312="${candidate}"
            break
        fi
    done
fi

# 回退：检查 PATH
if [ -z "${PYTHON312}" ] && command -v python3.12 &>/dev/null; then
    PYTHON312="$(command -v python3.12)"
fi

if [ -z "${PYTHON312}" ]; then
    echo ""
    echo "错误：未找到 python3.12"
    echo ""
    echo "请先安装 Python 3.12："
    echo "  brew install python@3.12"
    echo ""
    echo "Apple Silicon 安装后路径通常为：/opt/homebrew/bin/python3.12"
    echo "Intel Mac 安装后路径通常为：/usr/local/bin/python3.12"
    exit 1
fi

PYTHON_VER="$("${PYTHON312}" --version)"
echo "Python: ${PYTHON312} (${PYTHON_VER})"

# ----------------------------------------------------------
# 2. 创建虚拟环境
# ----------------------------------------------------------
if [ ! -d "${VENV_DIR}" ]; then
    echo ""
    echo "创建虚拟环境: ${VENV_DIR}"
    "${PYTHON312}" -m venv "${VENV_DIR}"
else
    echo ""
    echo "虚拟环境已存在，跳过创建: ${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
echo "激活虚拟环境: $(which python)"

# 升级 pip
python -m pip install --upgrade pip -q

# ----------------------------------------------------------
# 3. 安装 paddlepaddle（官方 CPU index，非 PyPI）
# ----------------------------------------------------------
echo ""
echo "安装 paddlepaddle==3.3.0 (官方 CPU wheel)..."
pip install paddlepaddle==3.3.0 \
    -i https://www.paddlepaddle.org.cn/packages/stable/cpu/ \
    --quiet

# ----------------------------------------------------------
# 4. 安装其余依赖
# ----------------------------------------------------------
echo ""
echo "安装 requirements.txt..."
pip install -r "${SCRIPT_DIR}/requirements.txt" --quiet

# ----------------------------------------------------------
# 5. 验证关键导入
# ----------------------------------------------------------
echo ""
echo "验证导入..."
python - <<'PYEOF'
from paddleocr import PaddleOCR, PPStructureV3
import paddle
print(f"  paddlepaddle : {paddle.__version__}")
import paddleocr
print(f"  paddleocr    : {paddleocr.__version__}")
import PySide6
print(f"  PySide6      : {PySide6.__version__}")
import fitz
print(f"  pymupdf      : {fitz.__version__}")
print()
print("阶段 0 验证通过：所有模块可导入。")
print()
print("下一步（阶段 1）：运行垂直切片 POC")
print("  source .venv/bin/activate")
print("  python poc/poc_ocr.py <image_path>")
PYEOF

echo ""
echo "环境搭建完成。激活命令："
echo "  source ${VENV_DIR}/bin/activate"
