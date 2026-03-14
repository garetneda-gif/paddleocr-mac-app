"""ExportRouter 单元测试 — 纯逻辑测试，不依赖 PaddleOCR。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.export_router import BaseConverter, ExportRouter
from app.models.enums import OutputFormat


class DummyConverter(BaseConverter):
    def convert(self, result, output_path) -> None:
        pass


def test_register_and_select():
    router = ExportRouter()
    converter = DummyConverter()
    router.register(OutputFormat.TXT, converter)
    assert router.select_converter(OutputFormat.TXT) is converter


def test_select_unregistered_raises():
    router = ExportRouter()
    with pytest.raises(ValueError, match="No converter registered"):
        router.select_converter(OutputFormat.WORD)


def test_supported_formats():
    router = ExportRouter()
    router.register(OutputFormat.TXT, DummyConverter())
    router.register(OutputFormat.PDF, DummyConverter())
    assert set(router.supported_formats) == {OutputFormat.TXT, OutputFormat.PDF}
