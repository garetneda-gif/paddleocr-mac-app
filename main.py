"""PaddleOCR 桌面应用入口。"""

import os
import sys

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")


def _patch_frozen_deps() -> None:
    """PyInstaller 打包后 importlib.metadata 可能找不到包元数据，
    导致 paddlex 依赖检查失败（DependencyError）。
    在 frozen 模式下跳过依赖版本检查——打包时依赖已确定。"""
    if not getattr(sys, "frozen", False):
        return

    import paddlex.utils.deps as deps
    deps.is_dep_available = lambda dep, /, check_version=False: True


def _preload_heavy_modules() -> None:
    """在主线程预导入重型模块，避免 QThread 子线程递归导入爆栈。"""
    import numpy  # noqa: F401
    import numpy.linalg  # noqa: F401
    import paddle  # noqa: F401

    _patch_frozen_deps()

    import paddleocr  # noqa: F401
    import cv2  # noqa: F401


def main() -> None:
    _preload_heavy_modules()

    from PySide6.QtWidgets import QApplication
    from app.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("PaddleOCR")
    app.setApplicationDisplayName("PaddleOCR — 智能文档识别")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
