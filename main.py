"""PaddleOCR 桌面应用入口。"""

from multiprocessing import freeze_support
import os
import sys

# 限制 CPU 线程，防止 OpenBLAS 吃满所有核心导致 UI 卡死
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")


def _preload_heavy_modules() -> None:
    """在主线程预导入重型模块，避免 QThread 子线程递归导入爆栈。"""
    import numpy  # noqa: F401
    import numpy.linalg  # noqa: F401
    import cv2  # noqa: F401
    import onnxruntime  # noqa: F401


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
    freeze_support()
    main()
