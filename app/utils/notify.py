"""macOS 系统通知 — 使用 osascript 发送原生通知。"""

from __future__ import annotations

import subprocess
import sys

from app.utils.log import get_logger

_log = get_logger("notify")


def send_notification(title: str, message: str, sound: str = "Glass") -> None:
    """发送 macOS 系统通知。非 macOS 平台静默忽略。"""
    if sys.platform != "darwin":
        return
    try:
        script = (
            f'display notification "{_escape(message)}" '
            f'with title "{_escape(title)}" '
            f'sound name "{sound}"'
        )
        subprocess.Popen(
            ["osascript", "-e", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        _log.debug("发送系统通知失败: %s", e)


def _escape(text: str) -> str:
    """转义 AppleScript 字符串中的特殊字符。"""
    return text.replace("\\", "\\\\").replace('"', '\\"')
