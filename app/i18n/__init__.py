"""轻量级 i18n 模块 — 基于字典的多语言支持。

用法：
    from app.i18n import tr, set_language, current_language

    label.setText(tr("nav_convert"))       # 根据当前语言返回翻译
    set_language("en_US")                  # 切换语言（触发回调）
"""

from __future__ import annotations

import weakref
from typing import Callable

from PySide6.QtCore import QSettings

from app.i18n.zh_CN import STRINGS as _ZH
from app.i18n.en_US import STRINGS as _EN

LANGUAGES: dict[str, dict[str, str]] = {
    "zh_CN": _ZH,
    "en_US": _EN,
}

# 界面语言显示名
UI_LANGUAGE_NAMES: dict[str, str] = {
    "zh_CN": "简体中文",
    "en_US": "English",
}

_current: str = "zh_CN"
_callbacks: list[weakref.ref] = []


def current_language() -> str:
    return _current


def tr(key: str) -> str:
    """查找当前语言的翻译字符串，找不到则回退中文，再找不到返回 key。"""
    strings = LANGUAGES.get(_current, _ZH)
    return strings.get(key) or _ZH.get(key) or key


def set_language(lang: str) -> None:
    """切换界面语言并通知所有注册的回调。"""
    global _current
    if lang not in LANGUAGES:
        return
    _current = lang
    QSettings("PaddleOCR", "Desktop").setValue("ui/language", lang)
    _notify()


def on_language_changed(callback: Callable[[], None]) -> None:
    """注册语言变化回调（弱引用，防止内存泄漏）。"""
    # 对于 bound methods，weakref.ref 无法直接使用，改用 weakref.WeakMethod
    try:
        ref = weakref.WeakMethod(callback)
    except TypeError:
        ref = weakref.ref(callback)
    _callbacks.append(ref)


def _notify() -> None:
    alive: list[weakref.ref] = []
    for ref in _callbacks:
        cb = ref()
        if cb is not None:
            cb()
            alive.append(ref)
    _callbacks[:] = alive


def load_saved_language() -> None:
    """从 QSettings 加载保存的语言偏好。"""
    global _current
    saved = QSettings("PaddleOCR", "Desktop").value("ui/language", "zh_CN")
    if saved in LANGUAGES:
        _current = saved
