"""自动翻译的 Qt 组件 — 语言切换时自动更新文本。"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel

from app.i18n import tr, on_language_changed


class TrLabel(QLabel):
    """语言切换时自动更新文本的 QLabel。"""

    def __init__(self, key: str, parent=None, **style_kwargs):
        super().__init__(tr(key), parent)
        self._tr_key = key
        on_language_changed(self._retranslate)

    def _retranslate(self) -> None:
        self.setText(tr(self._tr_key))
