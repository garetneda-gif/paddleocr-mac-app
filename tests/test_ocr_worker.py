"""OCRWorker 单元测试 — 验证 pipeline 选择、参数透传和页码映射。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.ocr_worker import OCRWorker
from app.models import BlockType
from app.models.enums import OutputFormat
from app.models.job import OCRJob


def _run_worker(worker: OCRWorker) -> dict[str, object]:
    captured: dict[str, object] = {}
    worker.finished.connect(lambda doc: captured.setdefault("doc", doc))
    worker.error.connect(lambda msg: captured.setdefault("error", msg))
    worker.run()
    return captured


def test_word_output_uses_structure_pipeline_and_keeps_absolute_page_index(
    monkeypatch, tmp_path
):
    import app.core.onnx_engine as onnx_engine
    import app.core.pdf_processor as pdf_processor
    import app.core.ocr_subprocess as ocr_subprocess

    monkeypatch.setattr(onnx_engine, "paddle_available", lambda: True)
    monkeypatch.setattr(pdf_processor, "get_page_count", lambda _: 20)
    monkeypatch.setattr(pdf_processor, "has_text_layer", lambda _: False)

    def fake_render_page(_pdf_path: Path, page_index: int, dpi: int) -> Path:
        out = tmp_path / f"page_{page_index}.png"
        out.write_text(f"dpi={dpi}")
        return out

    captured_call: dict[str, object] = {}

    def fake_run_pipeline_parallel(
        batches,
        *,
        lang,
        speed_mode,
        pipeline,
        options,
        max_workers,
    ):
        captured_call.update(
            {
                "lang": lang,
                "speed_mode": speed_mode,
                "pipeline": pipeline,
                "options": options,
                "max_workers": max_workers,
            }
        )
        results = []
        for batch in batches:
            batch_result = []
            for image_path in batch:
                page_no = int(Path(image_path).stem.split("_")[-1])
                batch_result.append(
                    {
                        "plain_text": f"title-{page_no}",
                        "pages": [
                            {
                                "width": 800,
                                "height": 600,
                                "blocks": [
                                    {
                                        "block_type": "title",
                                        "bbox": [10, 20, 300, 80],
                                        "text": f"title-{page_no}",
                                        "confidence": 0.99,
                                        "html": None,
                                        "markdown": None,
                                        "table_cells": None,
                                    }
                                ],
                            }
                        ],
                    }
                )
            results.append(batch_result)
        return results

    monkeypatch.setattr(pdf_processor, "render_page", fake_render_page)
    monkeypatch.setattr(ocr_subprocess, "run_pipeline_parallel", fake_run_pipeline_parallel)

    job = OCRJob(
        source_path=Path("/tmp/demo.pdf"),
        output_format=OutputFormat.WORD,
        language="ch",
    )
    job._adv_params = {
        "page_start": 11,
        "page_end": 12,
        "speed_mode": "mobile",
        "parallel_workers": 2,
        "use_table_recognition": False,
    }

    result = _run_worker(OCRWorker(job))

    assert "error" not in result
    doc = result["doc"]
    assert [page.page_index for page in doc.pages] == [10, 11]
    assert [page.blocks[0].block_type for page in doc.pages] == [BlockType.TITLE, BlockType.TITLE]
    assert captured_call["pipeline"] == "structure"
    assert captured_call["speed_mode"] == "mobile"
    assert captured_call["max_workers"] == 2
    assert captured_call["options"]["use_table_recognition"] is False
    assert captured_call["options"]["text_detection_model_name"] == "PP-OCRv5_mobile_det"
    assert "return_word_box" not in captured_call["options"]


def test_pdf_output_uses_ocr_pipeline_and_passes_ocr_options(monkeypatch, tmp_path):
    import app.core.onnx_engine as onnx_engine
    import app.core.pdf_processor as pdf_processor
    import app.core.ocr_subprocess as ocr_subprocess

    monkeypatch.setattr(onnx_engine, "resolve_ocr_backend", lambda *_: "onnx")
    monkeypatch.setattr(pdf_processor, "get_page_count", lambda _: 1)
    monkeypatch.setattr(pdf_processor, "has_text_layer", lambda _: False)

    def fake_render_page(_pdf_path: Path, page_index: int, dpi: int) -> Path:
        out = tmp_path / f"ocr_{page_index}.png"
        out.write_text(f"dpi={dpi}")
        return out

    captured_call: dict[str, object] = {}

    def fake_run_pipeline_parallel(
        batches,
        *,
        lang,
        speed_mode,
        pipeline,
        options,
        max_workers,
    ):
        captured_call.update(
            {
                "lang": lang,
                "speed_mode": speed_mode,
                "pipeline": pipeline,
                "options": options,
                "max_workers": max_workers,
            }
        )
        return [
            [
                {
                    "plain_text": "hello world",
                    "pages": [
                        {
                            "width": 640,
                            "height": 480,
                            "blocks": [
                                {
                                    "block_type": "paragraph",
                                    "bbox": [0, 0, 100, 20],
                                    "text": "hello world",
                                    "confidence": 0.88,
                                    "html": None,
                                    "markdown": None,
                                    "table_cells": None,
                                }
                            ],
                        }
                    ],
                }
            ]
        ]

    monkeypatch.setattr(pdf_processor, "render_page", fake_render_page)
    monkeypatch.setattr(ocr_subprocess, "run_pipeline_parallel", fake_run_pipeline_parallel)

    job = OCRJob(
        source_path=Path("/tmp/demo.pdf"),
        output_format=OutputFormat.PDF,
        language="en",
    )
    job._adv_params = {
        "speed_mode": "mobile",
        "parallel_workers": 1,
        "use_doc_orientation_classify": True,
        "use_doc_unwarping": True,
        "use_textline_orientation": True,
        "text_det_limit_side_len": 1536,
        "text_det_limit_type": "min",
        "text_det_thresh": 0.2,
        "text_det_box_thresh": 0.5,
        "text_det_unclip_ratio": 1.8,
        "text_recognition_batch_size": 4,
        "text_rec_score_thresh": 0.1,
        "return_word_box": True,
    }

    result = _run_worker(OCRWorker(job))

    assert "error" not in result
    doc = result["doc"]
    assert doc.pages[0].blocks[0].block_type == BlockType.PARAGRAPH
    assert doc.pages[0].page_index == 0
    assert captured_call["pipeline"] == "ocr"
    assert captured_call["speed_mode"] == "mobile"
    assert captured_call["max_workers"] == 1
    assert captured_call["options"]["use_doc_orientation_classify"] is True
    assert captured_call["options"]["use_doc_unwarping"] is True
    assert captured_call["options"]["use_textline_orientation"] is True
    assert captured_call["options"]["text_det_limit_side_len"] == 1536
    assert captured_call["options"]["text_det_limit_type"] == "min"
    assert captured_call["options"]["text_recognition_batch_size"] == 4
    assert captured_call["options"]["return_word_box"] is True


def test_invalid_pdf_page_range_emits_error(monkeypatch):
    import app.core.pdf_processor as pdf_processor

    monkeypatch.setattr(pdf_processor, "get_page_count", lambda _: 10)

    job = OCRJob(
        source_path=Path("/tmp/demo.pdf"),
        output_format=OutputFormat.TXT,
        language="ch",
    )
    job._adv_params = {
        "page_start": 8,
        "page_end": 3,
    }

    result = _run_worker(OCRWorker(job))

    assert "doc" not in result
    assert "页码范围无效" in result["error"]
