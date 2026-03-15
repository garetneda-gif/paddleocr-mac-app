"""OCR 引擎封装 — 将 PaddleOCR (PP-OCRv5) 原始输出标准化为 DocumentResult。

注意：此模块依赖 PaddlePaddle + paddleocr，仅在安装了这些包时可用。
ONNX-only 模式下此模块不会被导入（自动回退到 OnnxOCREngine）。
"""

from __future__ import annotations

from pathlib import Path

from app.models import BlockResult, BlockType, DocumentResult, PageResult


def _bbox_from_polygon(polygon: list) -> tuple[float, float, float, float]:
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return (float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys)))


class OCREngine:
    def __init__(
        self,
        lang: str = "ch",
        speed_mode: str = "server",
        options: dict[str, object] | None = None,
    ) -> None:
        self._lang = lang
        self._speed_mode = speed_mode
        self._options = {k: v for k, v in (options or {}).items() if v is not None}
        self._ocr = None

    def _ensure_model(self) -> None:
        if self._ocr is not None:
            return
        from paddleocr import PaddleOCR

        kwargs = dict(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            lang=self._lang,
        )

        if self._speed_mode == "mobile":
            kwargs["text_detection_model_name"] = "PP-OCRv5_mobile_det"
            kwargs["text_recognition_model_name"] = "PP-OCRv5_mobile_rec"

        kwargs.update(self._options)
        self._ocr = PaddleOCR(**kwargs)

    def predict(self, image_path: Path) -> DocumentResult:
        self._ensure_model()
        raw_results = self._ocr.predict(str(image_path))

        pages: list[PageResult] = []
        all_texts: list[str] = []

        for page_idx, page_raw in enumerate(raw_results):
            if page_raw is None:
                continue

            rec_texts = page_raw.get("rec_texts", [])
            rec_scores = page_raw.get("rec_scores", [])
            rec_boxes = page_raw.get("rec_boxes", [])
            dt_polys = page_raw.get("dt_polys", [])

            blocks: list[BlockResult] = []
            for i, (text, score) in enumerate(zip(rec_texts, rec_scores)):
                if i < len(rec_boxes) and rec_boxes[i] is not None:
                    b = rec_boxes[i]
                    bbox = (float(b[0]), float(b[1]), float(b[2]), float(b[3]))
                elif i < len(dt_polys) and dt_polys[i] is not None:
                    bbox = _bbox_from_polygon(dt_polys[i])
                else:
                    bbox = (0.0, 0.0, 0.0, 0.0)

                blocks.append(
                    BlockResult(
                        block_type=BlockType.PARAGRAPH,
                        bbox=bbox,
                        text=text,
                        confidence=float(score),
                    )
                )
                all_texts.append(text)

            max_x = max((b.bbox[2] for b in blocks), default=0)
            max_y = max((b.bbox[3] for b in blocks), default=0)
            pages.append(
                PageResult(
                    page_index=page_idx,
                    width=int(max_x) if max_x > 0 else 0,
                    height=int(max_y) if max_y > 0 else 0,
                    blocks=blocks,
                )
            )

        return DocumentResult(
            source_path=image_path,
            page_count=len(pages),
            pages=pages,
            plain_text="\n".join(all_texts),
        )
