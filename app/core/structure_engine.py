"""结构化引擎封装 — 将 PPStructureV3 原始输出标准化为 DocumentResult。"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

from app.models import BlockResult, BlockType, DocumentResult, PageResult

# PPStructureV3 layout label -> BlockType 映射
_LABEL_MAP: dict[str, BlockType] = {
    "title": BlockType.TITLE,
    "text": BlockType.PARAGRAPH,
    "table": BlockType.TABLE,
    "figure": BlockType.FIGURE,
    "figure_caption": BlockType.CAPTION,
    "table_caption": BlockType.CAPTION,
    "header": BlockType.OTHER,
    "footer": BlockType.OTHER,
    "reference": BlockType.PARAGRAPH,
    "equation": BlockType.FORMULA,
    "formula": BlockType.FORMULA,
    "list": BlockType.LIST,
    "abstract": BlockType.PARAGRAPH,
    "content": BlockType.PARAGRAPH,
}


class StructureEngine:
    """封装 PPStructureV3，提供统一的 predict -> DocumentResult 接口。"""

    def __init__(self, lang: str = "ch") -> None:
        self._lang = lang
        self._pipeline = None

    def _ensure_model(self) -> None:
        if self._pipeline is not None:
            return
        from paddleocr import PPStructureV3

        self._pipeline = PPStructureV3(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            lang=self._lang,
        )

    def predict(self, image_path: Path) -> DocumentResult:
        self._ensure_model()
        raw_results = self._pipeline.predict(str(image_path))

        pages: list[PageResult] = []
        all_texts: list[str] = []

        for page_raw in raw_results:
            if page_raw is None:
                continue

            page_idx = page_raw.get("page_index", len(pages))
            width = page_raw.get("width", 0)
            height = page_raw.get("height", 0)

            blocks: list[BlockResult] = []

            # 从 parsing_res_list 提取结构化块（LayoutBlock 对象）
            parsing_list = page_raw.get("parsing_res_list", [])
            for item in parsing_list:
                label = getattr(item, "label", "other")
                block_type = _LABEL_MAP.get(label, BlockType.OTHER)

                raw_bbox = getattr(item, "bbox", [0, 0, 0, 0])
                bbox = (
                    float(raw_bbox[0]),
                    float(raw_bbox[1]),
                    float(raw_bbox[2]),
                    float(raw_bbox[3]),
                )

                content = getattr(item, "content", "") or ""

                blocks.append(
                    BlockResult(
                        block_type=block_type,
                        bbox=bbox,
                        text=content,
                    )
                )
                if content:
                    all_texts.append(content)

            # 补充表格结果
            for tbl in page_raw.get("table_res_list", []):
                if not isinstance(tbl, dict):
                    continue
                html = tbl.get("html", "")
                cell_data = tbl.get("cell_data")
                coord = tbl.get("bbox", tbl.get("coordinate", [0, 0, 0, 0]))
                bbox = (
                    float(coord[0]),
                    float(coord[1]),
                    float(coord[2]),
                    float(coord[3]),
                )
                blocks.append(
                    BlockResult(
                        block_type=BlockType.TABLE,
                        bbox=bbox,
                        text="",
                        html=html if html else None,
                        table_cells=cell_data,
                    )
                )

            pages.append(
                PageResult(
                    page_index=page_idx,
                    width=int(width),
                    height=int(height),
                    blocks=blocks,
                )
            )

        return DocumentResult(
            source_path=image_path,
            page_count=len(pages),
            pages=pages,
            plain_text="\n".join(all_texts),
        )
