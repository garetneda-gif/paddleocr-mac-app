"""
PaddleOCR PP-OCRv5 → ONNX 转换脚本

将 PP-OCRv5 mobile/server 检测+识别模型转换为 ONNX，
输出到 /Volumes/MOVESPEED/存储/models/<model_name>/inference.onnx

用法（请在自己的终端里运行，不要通过 Claude Code）：
    cd /Users/jikunren/Documents/paddleocr
    source .venv/bin/activate
    python tools/convert_to_onnx.py [--models mobile|server|all]

依赖：
    paddle2onnx >= 2.0
    paddlepaddle >= 3.0
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ["FLAGS_call_stack_level"] = "0"
os.environ["OMP_NUM_THREADS"] = "2"

# 模型存储在外置硬盘
MODEL_ROOT = Path("/Volumes/MOVESPEED/存储/models")

# 模型名 → (检测/识别类型)
MODELS: dict[str, dict] = {
    "PP-OCRv5_mobile_det":    {"type": "det"},
    "PP-OCRv5_server_det":    {"type": "det"},
    "PP-OCRv5_mobile_rec":    {"type": "rec"},
    "PP-OCRv5_server_rec":    {"type": "rec"},
    "en_PP-OCRv5_mobile_rec": {"type": "rec"},
}

MOBILE_SET = {"PP-OCRv5_mobile_det", "PP-OCRv5_mobile_rec", "en_PP-OCRv5_mobile_rec"}
SERVER_SET = {"PP-OCRv5_server_det", "PP-OCRv5_server_rec"}


# ─────────────────────────────────────────────
# 1. 确保模型已下载
# ─────────────────────────────────────────────

def ensure_downloaded(model_names: list[str]) -> None:
    """检查模型文件是否已存在于外置硬盘。"""
    for name in model_names:
        model_dir = MODEL_ROOT / name
        if not model_dir.exists():
            print(f"[警告] 模型目录不存在: {model_dir}")
        else:
            model_file = model_dir / "inference.json"
            params_file = model_dir / "inference.pdiparams"
            if model_file.exists() and params_file.exists():
                size = params_file.stat().st_size / 1024 / 1024
                print(f"[OK] {name} 已存在 ({size:.1f} MB params)")
            else:
                print(f"[警告] {name} 模型文件不完整")


# ─────────────────────────────────────────────
# 2. 找到模型文件
# ─────────────────────────────────────────────

def _find_model_files(model_dir: Path) -> tuple[Path | None, Path | None]:
    """
    在 model_dir 中查找静态推理模型文件。
    PaddlePaddle 3.x 新格式：inference.json + inference.pdiparams
    PaddlePaddle 旧格式：inference.pdmodel + inference.pdiparams
    返回 (model_file, params_file)
    """
    # 新格式 (PIR JSON)
    json_file = model_dir / "inference.json"
    params_file = model_dir / "inference.pdiparams"
    if json_file.exists() and params_file.exists():
        return json_file, params_file

    # 旧格式
    pdmodel = model_dir / "inference.pdmodel"
    if pdmodel.exists() and params_file.exists():
        return pdmodel, params_file

    # 扫描
    for f in model_dir.rglob("*.json"):
        p = f.with_suffix(".pdiparams")
        if p.exists():
            return f, p
    for f in model_dir.rglob("*.pdmodel"):
        p = f.with_suffix("").with_suffix("").parent / (f.stem + ".pdiparams")
        alt = f.parent / "inference.pdiparams"
        if p.exists():
            return f, p
        if alt.exists():
            return f, alt

    return None, None


# ─────────────────────────────────────────────
# 3. 转换单个模型
# ─────────────────────────────────────────────

def convert_model(model_name: str, opset: int = 11) -> bool:
    """
    将 model_name 对应的 Paddle 模型转换为 ONNX，
    输出到 MODEL_ROOT/<model_name>/inference.onnx
    返回是否成功。
    """
    model_dir = MODEL_ROOT / model_name
    onnx_path = model_dir / "inference.onnx"

    if onnx_path.exists():
        size_mb = onnx_path.stat().st_size / 1024 / 1024
        print(f"[跳过] {model_name}: 已存在 inference.onnx ({size_mb:.1f} MB)")
        return True

    if not model_dir.exists():
        print(f"[错误] 模型目录不存在: {model_dir}")
        print("       请先运行下载步骤。")
        return False

    model_file, params_file = _find_model_files(model_dir)
    if model_file is None:
        print(f"[错误] 在 {model_dir} 中未找到推理模型文件")
        print("       目录内容：")
        for f in sorted(model_dir.rglob("*")):
            print(f"         {f.relative_to(model_dir)}")
        return False

    print(f"[转换] {model_name}")
    print(f"       模型文件: {model_file.name}")
    print(f"       参数文件: {params_file.name}")
    print(f"       输出: {onnx_path}")

    try:
        import paddle2onnx
        paddle2onnx.export(
            model_filename=str(model_file),
            params_filename=str(params_file),
            save_file=str(onnx_path),
            opset_version=opset,
            enable_onnx_checker=True,
            optimize_tool="None",
            deploy_backend="onnxruntime",
        )
        size_mb = onnx_path.stat().st_size / 1024 / 1024
        print(f"[完成] {onnx_path.name}  {size_mb:.1f} MB\n")
        return True
    except Exception as e:
        print(f"[失败] {model_name}: {e}\n")
        if onnx_path.exists():
            onnx_path.unlink()
        return False


# ─────────────────────────────────────────────
# 4. 创建 inference.yml（如果不存在）
# ─────────────────────────────────────────────

DET_YML_TEMPLATE = """\
PostProcess:
  thresh: 0.3
  box_thresh: 0.6
  unclip_ratio: 1.5
  max_candidates: 1000
"""

REC_YML_TEMPLATE = """\
PostProcess:
  character_dict: {char_list}
"""


def ensure_yml(model_name: str) -> None:
    """确保 inference.yml 存在，供 onnx_engine.py 读取。"""
    model_dir = MODEL_ROOT / model_name
    yml_path = model_dir / "inference.yml"
    if yml_path.exists():
        return

    mtype = MODELS[model_name]["type"]
    if mtype == "det":
        yml_path.write_text(DET_YML_TEMPLATE)
        print(f"[yml] 已创建检测配置: {yml_path}")
    else:
        # 识别模型：从 paddlex 包内读取字符字典
        char_list = _get_char_dict(model_name)
        if char_list:
            import json
            yml_path.write_text(
                "PostProcess:\n"
                f"  character_dict: {json.dumps(char_list, ensure_ascii=False)}\n"
            )
            print(f"[yml] 已创建识别配置: {yml_path}  ({len(char_list)} chars)")
        else:
            yml_path.write_text("PostProcess:\n  character_dict: []\n")
            print(f"[警告] 未找到字符字典，{yml_path} 写入空列表")


def _get_char_dict(model_name: str) -> list[str]:
    """从模型目录或 paddlex 内置资源中获取字符字典。"""
    model_dir = MODEL_ROOT / model_name

    # 优先从模型目录里找
    for fname in ("dict.txt", "ppocr_keys_v1.txt", "character_dict.txt"):
        p = model_dir / fname
        if p.exists():
            return [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]

    # 从 paddleocr 内置字典找
    try:
        import paddleocr
        pkg_dir = Path(paddleocr.__file__).parent
        for pattern in ("ppocr/utils/ppocr_keys_v1.txt", "utils/ppocr_keys_v1.txt", "**/*.txt"):
            for p in pkg_dir.glob(pattern):
                lines = [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
                if len(lines) > 1000:  # 字符字典通常很大
                    print(f"  (使用字典: {p})")
                    return lines
    except Exception:
        pass

    return []


# ─────────────────────────────────────────────
# 5. 验证 ONNX 推理
# ─────────────────────────────────────────────

def verify_onnx(model_name: str) -> bool:
    """用随机输入验证 ONNX 模型能跑通。"""
    import numpy as np
    import onnxruntime as ort

    onnx_path = MODEL_ROOT / model_name / "inference.onnx"
    if not onnx_path.exists():
        return False

    try:
        sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        inp = sess.get_inputs()[0]
        # 构造合法的随机输入
        shape = [d if isinstance(d, int) and d > 0 else 1 for d in inp.shape]
        if len(shape) == 4 and shape[2] == 0:
            shape[2] = 32
        if len(shape) == 4 and shape[3] == 0:
            shape[3] = 320
        dummy = np.random.randn(*shape).astype(np.float32)
        sess.run(None, {inp.name: dummy})
        print(f"[验证] {model_name}: ONNX 推理正常 ✓")
        return True
    except Exception as e:
        print(f"[验证] {model_name}: ONNX 推理失败 — {e}")
        return False


# ─────────────────────────────────────────────
# 主入口
# ─────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="PaddleOCR → ONNX 模型转换")
    parser.add_argument(
        "--models",
        choices=["mobile", "server", "all"],
        default="mobile",
        help="要转换的模型集 (default: mobile)",
    )
    parser.add_argument("--opset", type=int, default=11, help="ONNX opset version")
    parser.add_argument("--no-download", action="store_true", help="跳过下载步骤")
    args = parser.parse_args()

    if args.models == "mobile":
        target_models = list(MOBILE_SET)
    elif args.models == "server":
        target_models = list(SERVER_SET)
    else:
        target_models = list(MOBILE_SET | SERVER_SET)

    # 检查外置硬盘
    if not MODEL_ROOT.exists():
        print(f"错误：外置硬盘未挂载: {MODEL_ROOT}")
        print("请插入 MOVESPEED 硬盘后重试。")
        sys.exit(1)

    print("=" * 60)
    print(f"PP-OCRv5 → ONNX 转换  ({args.models})")
    print(f"目标模型: {sorted(target_models)}")
    print(f"模型目录: {MODEL_ROOT}")
    print("=" * 60 + "\n")

    # 检查模型文件
    ensure_downloaded(target_models)

    # 转换 + YML + 验证
    results = {}
    for name in sorted(target_models):
        ok = convert_model(name, opset=args.opset)
        if ok:
            ensure_yml(name)
            verify_onnx(name)
        results[name] = ok

    # 汇总
    print("\n" + "=" * 60)
    print("转换结果汇总")
    print("=" * 60)
    for name, ok in sorted(results.items()):
        status = "✓ 成功" if ok else "✗ 失败"
        print(f"  {status}  {name}")

    if all(results.values()):
        print("\n所有模型转换完成！ONNX 文件保存在各模型目录下。")
        print("下一步：回到 Claude Code，ONNX 引擎会自动加载这些文件。")
    else:
        print("\n部分模型转换失败，请检查上方日志。")
        sys.exit(1)


if __name__ == "__main__":
    main()
