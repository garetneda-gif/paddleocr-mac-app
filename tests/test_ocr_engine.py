"""OCREngine 集成测试 — 验证 PaddleOCR 封装输出标准化 DocumentResult。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.ocr_engine import OCREngine
from app.models import BlockResult, BlockType, DocumentResult, PageResult

TEST_IMG = Path(__file__).parent / "fixtures" / "test_en.png"


@pytest.fixture(scope="module")
def ocr_result() -> DocumentResult:
    engine = OCREngine(lang="en")
    return engine.predict(TEST_IMG)


def test_returns_document_result(ocr_result: DocumentResult):
    assert isinstance(ocr_result, DocumentResult)


def test_source_path(ocr_result: DocumentResult):
    assert ocr_result.source_path == TEST_IMG


def test_has_pages(ocr_result: DocumentResult):
    assert ocr_result.page_count >= 1
    assert len(ocr_result.pages) == ocr_result.page_count


def test_page_has_blocks(ocr_result: DocumentResult):
    page = ocr_result.pages[0]
    assert isinstance(page, PageResult)
    assert len(page.blocks) > 0


def test_block_structure(ocr_result: DocumentResult):
    block = ocr_result.pages[0].blocks[0]
    assert isinstance(block, BlockResult)
    assert isinstance(block.block_type, BlockType)
    assert len(block.bbox) == 4
    assert all(isinstance(v, float) for v in block.bbox)
    assert isinstance(block.text, str) and len(block.text) > 0
    assert isinstance(block.confidence, float)


def test_bbox_xyxy_format(ocr_result: DocumentResult):
    for block in ocr_result.pages[0].blocks:
        x1, y1, x2, y2 = block.bbox
        assert x2 >= x1, f"x2 ({x2}) < x1 ({x1})"
        assert y2 >= y1, f"y2 ({y2}) < y1 ({y1})"


def test_plain_text_not_empty(ocr_result: DocumentResult):
    assert len(ocr_result.plain_text) > 0
    assert "PaddleOCR" in ocr_result.plain_text or "Hello" in ocr_result.plain_text
