"""可搜索 PDF 导出器 — 在原始图像上叠加透明文字层。"""

from __future__ import annotations

import math
from pathlib import Path

from app.converters.base_converter import BaseConverter
from app.core.pdf_processor import RENDER_DPI
from app.models import BlockResult, DocumentResult
from app.utils.log import get_logger

_log = get_logger("pdf_converter")

# CJK Unicode 范围（中日韩统一表意文字 + 常用扩展）
_CJK_RANGES = (
    (0x3000, 0x303F),  # CJK 符号和标点
    (0x3040, 0x30FF),  # 平假名 + 片假名
    (0x4E00, 0x9FFF),  # CJK 统一表意文字
    (0x3400, 0x4DBF),  # CJK 扩展 A
    (0xAC00, 0xD7AF),  # 韩文音节
    (0xFF00, 0xFFEF),  # 全角字符
)
_FONT_PROBE_CANDIDATES = ("helv", "china-s", "cour")
_METRIC_EPSILON = 1e-6
_MIN_FONT_SIZE = 0.1


def _is_finite_number(value: float) -> bool:
    return math.isfinite(value)


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


def _normalize_line_text(text: str) -> str:
    cleaned = text.replace("\r", "")
    return "".join(ch for ch in cleaned if ch == "\t" or ch.isprintable())




def _is_retryable_font_error(exc: Exception) -> bool:
    message = str(exc).lower()
    markers = (
        "glyph",
        "cmap",
        "unknown font",
        "cannot encode",
    )
    return any(marker in message for marker in markers)


class PdfConverter(BaseConverter):
    strict_text_layer = False

    @property
    def file_extension(self) -> str:
        return ".pdf"

    def convert(self, result: DocumentResult, output_path: Path) -> Path:
        import fitz

        doc = fitz.open()
        font_cache: dict[str, object | None] = {}
        available_fallback_fonts = self._probe_available_fonts(fitz, font_cache)
        overlay_error_state = {"count": 0, "samples": []}

        source = result.source_path
        is_pdf_input = source.suffix.lower() == ".pdf"
        src_doc = None
        try:
            if is_pdf_input:
                src_doc = fitz.open(str(source))

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
                        self._overlay_block(
                            pdf_page,
                            block,
                            scale,
                            font_cache=font_cache,
                            fallback_fonts=available_fallback_fonts,
                            overlay_error_state=overlay_error_state,
                        )
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
                        self._overlay_block(
                            pdf_page,
                            block,
                            scale,
                            font_cache=font_cache,
                            fallback_fonts=available_fallback_fonts,
                            overlay_error_state=overlay_error_state,
                        )

            if overlay_error_state["count"]:
                preview = "; ".join(overlay_error_state["samples"])
                message = (
                    "PDF 文本层存在非法块："
                    f" count={overlay_error_state['count']} sample={preview}"
                )
                if self.strict_text_layer:
                    raise RuntimeError(message)
                _log.warning(message)

            doc.save(str(output_path))
            return output_path
        finally:
            if src_doc:
                src_doc.close()
            doc.close()

    @staticmethod
    def _get_font(fitz, fontname: str, font_cache: dict[str, object | None]) -> object | None:
        if fontname in font_cache:
            return font_cache[fontname]
        try:
            font = fitz.Font(fontname)
        except Exception:
            font_cache[fontname] = None
            return None
        font_cache[fontname] = font
        return font

    @classmethod
    def _probe_available_fonts(
        cls,
        fitz,
        font_cache: dict[str, object | None],
    ) -> tuple[str, ...]:
        available: list[str] = []
        for fontname in _FONT_PROBE_CANDIDATES:
            if cls._get_font(fitz, fontname, font_cache) is not None:
                available.append(fontname)
        if available:
            return tuple(available)
        # 某些环境下 Font 探测会失败，但内置字体名仍可能可写入。
        return ("helv", "cour")

    @classmethod
    def _measure_text_unit_width(
        cls,
        fitz,
        fontname: str,
        font_cache: dict[str, object | None],
        text: str,
    ) -> float | None:
        if not text:
            return None
        try:
            width = fitz.get_text_length(text, fontname=fontname, fontsize=1)
        except Exception:
            font = cls._get_font(fitz, fontname, font_cache)
            if font is None or not hasattr(font, "text_length"):
                return None
            try:
                width = font.text_length(text, fontsize=1)
            except Exception:
                return None
        if not _is_finite_number(float(width)) or width <= _METRIC_EPSILON:
            return None
        return float(width)

    @classmethod
    def _compute_text_layout(
        cls,
        fitz,
        line_text: str,
        fontname: str,
        line_top: float,
        line_bottom: float,
        block_w_pt: float,
        font_cache: dict[str, object | None],
    ) -> tuple[float, float]:
        """宽度优先计算 fontsize 和基线位置（参照 Umi-OCR 方式）。"""
        line_h = line_bottom - line_top

        # 宽度优先：fontsize = bbox_width / text_length_at_1pt
        unit_width = cls._measure_text_unit_width(
            fitz, fontname, font_cache, line_text
        )
        if unit_width is not None and block_w_pt > _METRIC_EPSILON:
            fontsize = block_w_pt / unit_width
        else:
            fontsize = line_h * 0.7  # 回退

        # 高度约束：不超出行高
        if line_h > _METRIC_EPSILON:
            fontsize = min(fontsize, line_h)
        fontsize = max(fontsize, _MIN_FONT_SIZE)

        # 基线 = 行底部（Umi-OCR 惯例）
        baseline_y = line_bottom
        return fontsize, baseline_y

    @staticmethod
    def _iter_font_attempts(
        preferred_font: str,
        line_text: str,
        fallback_fonts: tuple[str, ...],
    ) -> tuple[str, ...]:
        ordered = [preferred_font]
        if _needs_cjk_font(line_text):
            ordered.extend(["helv", "china-s", "cour"])
        else:
            ordered.extend(["helv", "cour", "china-s"])

        attempts: list[str] = []
        for fontname in ordered:
            if not fontname:
                continue
            if fontname != preferred_font and fontname not in fallback_fonts:
                continue
            if fontname not in attempts:
                attempts.append(fontname)
        return tuple(attempts)

    @classmethod
    def _try_insert_line(
        cls,
        pdf_page,
        line_text: str,
        x_pos: float,
        line_top: float,
        line_bottom: float,
        block_w_pt: float,
        preferred_font: str,
        fitz,
        font_cache: dict[str, object | None],
        fallback_fonts: tuple[str, ...],
    ) -> None:
        last_exc: Exception | None = None
        font_attempts = cls._iter_font_attempts(preferred_font, line_text, fallback_fonts)

        for fontname in font_attempts:
            fontsize, baseline_y = cls._compute_text_layout(
                fitz,
                line_text,
                fontname,
                line_top,
                line_bottom,
                block_w_pt,
                font_cache,
            )
            baseline = fitz.Point(x_pos, baseline_y)
            try:
                pdf_page.insert_text(
                    baseline,
                    line_text,
                    fontname=fontname,
                    fontsize=fontsize,
                    render_mode=3,
                )
                return
            except Exception as exc:
                last_exc = exc
                if getattr(pdf_page, "parent", object()) is None:
                    raise RuntimeError(
                        "PDF 文本层写入失败："
                        f" font={fontname} top={line_top:.2f} kind=page-state"
                    ) from exc
                if not _is_retryable_font_error(exc):
                    raise RuntimeError(
                        "PDF 文本层写入失败："
                        f" font={fontname} top={line_top:.2f} kind=insert"
                    ) from exc
                _log.debug(
                    "PDF 文本层写入失败，字体回退：font=%s err=%s",
                    fontname,
                    exc,
                )

        if last_exc is not None:
            raise RuntimeError(
                "PDF 文本层写入失败："
                f" font={preferred_font} top={line_top:.2f}"
                f" chars={len(line_text)} cjk={_needs_cjk_font(line_text)}"
                f" cause={type(last_exc).__name__}"
            ) from last_exc

    @classmethod
    def _overlay_block(
        cls,
        pdf_page,
        block: BlockResult,
        scale: float,
        *,
        font_cache: dict[str, object | None] | None = None,
        fallback_fonts: tuple[str, ...] = (),
        overlay_error_state: dict[str, object] | None = None,
    ) -> None:
        """将单个 block 的文本叠加到 PDF 页面上。

        当前实现面向轴对齐 bbox。它会按原始分行保留空行占位，
        但在缺少逐行 bbox / 旋转信息时，无法保证复杂版式的精确覆盖。
        """
        import fitz

        x1, y1, x2, y2 = block.bbox
        if font_cache is None:
            font_cache = {}
        if overlay_error_state is None:
            overlay_error_state = {"count": 0, "samples": []}

        if not all(_is_finite_number(value) for value in (x1, y1, x2, y2, scale)):
            message = f"invalid-coord bbox={block.bbox} scale={scale}"
            overlay_error_state["count"] += 1
            if len(overlay_error_state["samples"]) < 5:
                overlay_error_state["samples"].append(message)
            _log.warning("PDF 文本层记录非法坐标块：%s", message)
            return

        layout_lines = [ln for ln in block.text.split("\n") if ln.strip()]
        if not layout_lines:
            return

        block_h_pt = (y2 - y1) * scale
        block_w_pt = (x2 - x1) * scale
        if scale <= _METRIC_EPSILON or block_h_pt <= _METRIC_EPSILON or block_w_pt <= 0:
            message = f"invalid-size bbox={block.bbox} scale={scale}"
            overlay_error_state["count"] += 1
            if len(overlay_error_state["samples"]) < 5:
                overlay_error_state["samples"].append(message)
            _log.warning("PDF 文本层记录异常尺寸块：%s", message)
            return

        line_h = block_h_pt / len(layout_lines)
        x_pos = x1 * scale

        for i, raw_line in enumerate(layout_lines):
            line_text = _normalize_line_text(raw_line)
            if not line_text:
                continue
            line_top = y1 * scale + i * line_h
            line_bottom = y1 * scale + (i + 1) * line_h
            preferred_font = _pick_font(line_text)
            cls._try_insert_line(
                pdf_page,
                line_text,
                x_pos,
                line_top,
                line_bottom,
                block_w_pt,
                preferred_font,
                fitz,
                font_cache,
                fallback_fonts,
            )
