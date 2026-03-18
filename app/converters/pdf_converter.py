"""可搜索 PDF 导出器 — 在原始图像上叠加透明文字层。"""

from __future__ import annotations

from pathlib import Path

from app.converters.base_converter import BaseConverter
from app.models import BlockResult, DocumentResult
from app.core.pdf_processor import RENDER_DPI

# CJK Unicode 范围（中日韩统一表意文字 + 常用扩展）
_CJK_RANGES = (
    (0x3000, 0x303F),  # CJK 符号和标点
    (0x3040, 0x30FF),  # 平假名 + 片假名
    (0x4E00, 0x9FFF),  # CJK 统一表意文字
    (0x3400, 0x4DBF),  # CJK 扩展 A
    (0xAC00, 0xD7AF),  # 韩文音节
    (0xFF00, 0xFFEF),  # 全角字符
)


def _needs_cjk_font(text: str) -> bool:
    for ch in text:
        cp = ord(ch)
        for lo, hi in _CJK_RANGES:
            if lo <= cp <= hi:
                return True
    return False


def _pick_font(text: str) -> str:
    """逐块选择字体：含 CJK 字符用 china-s，否则用 helv。"""
    return "china-s" if _needs_cjk_font(text) else "helv"


class PdfConverter(BaseConverter):
    @property
    def file_extension(self) -> str:
        return ".pdf"

    def convert(self, result: DocumentResult, output_path: Path) -> Path:
        import fitz

        doc = fitz.open()

        source = result.source_path
        is_pdf_input = source.suffix.lower() == ".pdf"
        if is_pdf_input:
            src_doc = fitz.open(str(source))
        else:
            src_doc = None

        # 建立 page_index → PageResult 映射
        page_result_map: dict[int, object] = {}
        for pr in result.pages:
            page_result_map[pr.page_index] = pr

        if src_doc:
            # PDF 输入：先复制所有原始页面，再叠加文字层（防止丢页）
            for pi in range(len(src_doc)):
                pdf_page = doc.new_page(
                    width=src_doc[pi].rect.width,
                    height=src_doc[pi].rect.height,
                )
                pdf_page.show_pdf_page(pdf_page.rect, src_doc, pi)

                page_result = page_result_map.get(pi)
                if page_result is None:
                    continue
                scale = pdf_page.rect.width / page_result.width if page_result.width else 1
                for block in page_result.blocks:
                    if not block.text:
                        continue
                    self._overlay_block(pdf_page, block, scale)
        else:
            # 图片输入
            for page_result in result.pages:
                img_path = result.source_path
                scale = 72.0 / RENDER_DPI
                pdf_rect = fitz.Rect(
                    0, 0,
                    page_result.width * scale,
                    page_result.height * scale,
                )
                pdf_page = doc.new_page(width=pdf_rect.width, height=pdf_rect.height)
                pdf_page.insert_image(pdf_rect, filename=str(img_path))

                for block in page_result.blocks:
                    if not block.text:
                        continue
                    self._overlay_block(pdf_page, block, scale)

        if src_doc:
            src_doc.close()

        doc.save(str(output_path))
        doc.close()
        return output_path

    @staticmethod
    def _overlay_block(pdf_page, block: BlockResult, scale: float) -> None:
        """将单个 block 的文本叠加到 PDF 页面上。

        对多行文本逐行插入，每行独立计算字号和位置，
        确保文本层精确覆盖原始文档的对应区域。
        """
        import fitz

        x1, y1, x2, y2 = block.bbox
        fontname = _pick_font(block.text)

        # 将 block 的多行文本拆分为单独行
        lines = block.text.split("\n")
        lines = [ln for ln in lines if ln.strip()]
        if not lines:
            return

        block_h_pt = (y2 - y1) * scale

        # 每行分得的垂直空间
        line_h = block_h_pt / len(lines) if len(lines) > 1 else block_h_pt

        for i, line_text in enumerate(lines):
            if not line_text.strip():
                continue

            # 字号：取行高的 70%，为 ascender/descender 留余量，最小 4pt
            fontsize = max(line_h * 0.7, 4)

            # baseline = 行顶部 + fontsize（PDF 中 baseline 在 ascender 下方）
            baseline = fitz.Point(
                x1 * scale,
                y1 * scale + i * line_h + fontsize,
            )
            pdf_page.insert_text(
                baseline,
                line_text,
                fontname=fontname,
                fontsize=fontsize,
                render_mode=3,  # 不可见但可搜索/选取/复制
            )
