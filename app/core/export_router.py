"""导出路由 — 根据 OutputFormat 选择对应的 converter。"""

from __future__ import annotations

from app.models.enums import OutputFormat


class BaseConverter:
    """导出器基类，各格式导出器继承并实现 convert 方法。"""

    def convert(self, result, output_path) -> None:
        raise NotImplementedError


class ExportRouter:
    """根据 OutputFormat 路由到正确的 converter 实例。"""

    def __init__(self) -> None:
        self._converters: dict[OutputFormat, BaseConverter] = {}

    def register(self, fmt: OutputFormat, converter: BaseConverter) -> None:
        self._converters[fmt] = converter

    def select_converter(self, fmt: OutputFormat) -> BaseConverter:
        converter = self._converters.get(fmt)
        if converter is None:
            raise ValueError(f"No converter registered for format: {fmt.value}")
        return converter

    @property
    def supported_formats(self) -> list[OutputFormat]:
        return list(self._converters.keys())
