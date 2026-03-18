"""统一日志配置 — 输出到 stderr + 文件。"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_LOG_DIR = Path.home() / ".paddleocr" / "logs"
_CONFIGURED = False


def setup_logging(level: int = logging.INFO) -> None:
    """初始化全局日志（仅执行一次）。"""
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = _LOG_DIR / "paddleocr.log"

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # stderr handler
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(fmt)

    # file handler（追加模式，最大 5MB 自动轮转）
    from logging.handlers import RotatingFileHandler

    file_handler = RotatingFileHandler(
        str(log_file), maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)

    root = logging.getLogger("paddleocr")
    root.setLevel(level)
    root.addHandler(stderr_handler)
    root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """获取子 logger，自动挂在 paddleocr 命名空间下。"""
    setup_logging()
    return logging.getLogger(f"paddleocr.{name}")
