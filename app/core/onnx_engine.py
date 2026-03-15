"""ONNX Runtime OCR 引擎 — 替换 PaddlePaddle，更快更省内存。

完整实现 DB 文本检测 + CRNN 文本识别的前后处理。
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import yaml

from app.models import BlockResult, BlockType, DocumentResult, PageResult

# 模型存放在外置硬盘（MOVESPEED）
_EXTERNAL_MODEL_ROOT = Path("/Volumes/MOVESPEED/存储/models")
# 内置备用路径（paddlex 默认下载目录）
_INTERNAL_MODEL_ROOT = Path.home() / ".paddlex" / "official_models"


def _check_path_accessible(path: Path, timeout: float = 2.0) -> bool:
    """检测路径是否可访问（带超时，防止外置硬盘休眠时阻塞）。"""
    import threading

    result = [False]

    def _probe() -> None:
        result[0] = path.exists()

    t = threading.Thread(target=_probe, daemon=True)
    t.start()
    t.join(timeout=timeout)
    return result[0]


def _get_model_root() -> Path:
    """返回可用的模型根目录。优先外置硬盘，回退内置目录。"""
    if _check_path_accessible(_EXTERNAL_MODEL_ROOT):
        return _EXTERNAL_MODEL_ROOT
    return _INTERNAL_MODEL_ROOT


def _load_char_dict(yml_path: Path) -> list[str]:
    """从 inference.yml 加载字符字典。"""
    with open(yml_path) as f:
        cfg = yaml.safe_load(f)
    chars = cfg["PostProcess"]["character_dict"]
    return ["blank"] + chars + [""]  # blank + chars + space


# ═══════════════════════════════════════════════════════
# 文本检测（DB）
# ═══════════════════════════════════════════════════════

class DBDetector:
    """DB 文本检测器。"""

    def __init__(self, model_dir: Path) -> None:
        import onnxruntime as ort

        onnx_path = model_dir / "inference.onnx"
        self.session = ort.InferenceSession(
            str(onnx_path),
            providers=["CPUExecutionProvider"],
        )
        self.input_name = self.session.get_inputs()[0].name

        # 加载配置
        with open(model_dir / "inference.yml") as f:
            cfg = yaml.safe_load(f)
        post = cfg.get("PostProcess", {})
        self.thresh = post.get("thresh", 0.3)
        self.box_thresh = post.get("box_thresh", 0.6)
        self.unclip_ratio = post.get("unclip_ratio", 1.5)
        self.max_candidates = post.get("max_candidates", 1000)
        self.limit_side_len = 960

    def detect(self, img: np.ndarray) -> list[np.ndarray]:
        """检测文本区域，返回多边形列表。"""
        h, w = img.shape[:2]
        resized, ratio_h, ratio_w = self._preprocess(img)

        outputs = self.session.run(None, {self.input_name: resized})
        pred = outputs[0][0, 0]  # (H, W)

        boxes = self._postprocess(pred, h, w, ratio_h, ratio_w)
        return boxes

    def _preprocess(self, img: np.ndarray) -> tuple[np.ndarray, float, float]:
        h, w = img.shape[:2]

        # 限制长边
        ratio = 1.0
        if max(h, w) > self.limit_side_len:
            ratio = self.limit_side_len / max(h, w)
        new_h = max(int(h * ratio / 32) * 32, 32)
        new_w = max(int(w * ratio / 32) * 32, 32)

        resized = cv2.resize(img, (new_w, new_h))

        # Normalize
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        resized = (resized.astype(np.float32) / 255.0 - mean) / std

        # HWC -> CHW, add batch
        resized = resized.transpose(2, 0, 1)[np.newaxis, ...]

        return resized.astype(np.float32), h / new_h, w / new_w

    def _postprocess(
        self, pred: np.ndarray, src_h: int, src_w: int,
        ratio_h: float, ratio_w: float
    ) -> list[np.ndarray]:
        """DB 后处理：二值化 → 轮廓 → unclip → 多边形。"""
        import pyclipper
        from shapely.geometry import Polygon

        # 二值化
        bitmap = (pred > self.thresh).astype(np.uint8)
        contours, _ = cv2.findContours(bitmap, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        boxes = []
        for contour in contours[:self.max_candidates]:
            if contour.shape[0] < 4:
                continue

            # 最小外接矩形
            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect)

            # 计算得分
            score = self._box_score(pred, contour)
            if score < self.box_thresh:
                continue

            # Unclip
            poly = Polygon(box)
            if poly.area < 1:
                continue
            distance = poly.area * self.unclip_ratio / poly.length
            offset = pyclipper.PyclipperOffset()
            offset.AddPath(
                [(int(p[0]), int(p[1])) for p in box],
                pyclipper.JT_ROUND,
                pyclipper.ET_CLOSEDPOLYGON,
            )
            expanded = offset.Execute(distance)
            if not expanded:
                continue

            expanded_box = np.array(expanded[0], dtype=np.float32)
            if len(expanded_box) < 4:
                continue

            # 再取最小外接矩形
            rect = cv2.minAreaRect(expanded_box)
            box = cv2.boxPoints(rect)

            # 映射回原图坐标
            box[:, 0] = box[:, 0] * ratio_w
            box[:, 1] = box[:, 1] * ratio_h

            # 排序点（左上、右上、右下、左下）
            box = self._order_points(box)
            boxes.append(box)

        return boxes

    def _box_score(self, pred: np.ndarray, contour: np.ndarray) -> float:
        h, w = pred.shape
        box = contour.reshape(-1, 2)
        xmin = max(0, int(box[:, 0].min()))
        xmax = min(w, int(box[:, 0].max()) + 1)
        ymin = max(0, int(box[:, 1].min()))
        ymax = min(h, int(box[:, 1].max()) + 1)

        mask = np.zeros((ymax - ymin, xmax - xmin), dtype=np.uint8)
        box[:, 0] -= xmin
        box[:, 1] -= ymin
        cv2.fillPoly(mask, [box.astype(np.int32)], 1)
        return float(cv2.mean(pred[ymin:ymax, xmin:xmax], mask)[0])

    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        rect = np.zeros((4, 2), dtype=np.float32)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        d = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(d)]
        rect[3] = pts[np.argmax(d)]
        return rect


# ═══════════════════════════════════════════════════════
# 文本识别（CRNN + CTC）
# ═══════════════════════════════════════════════════════

class CRNNRecognizer:
    """CRNN 文本识别器 + CTC 解码。"""

    def __init__(self, model_dir: Path) -> None:
        import onnxruntime as ort

        onnx_path = model_dir / "inference.onnx"
        self.session = ort.InferenceSession(
            str(onnx_path),
            providers=["CPUExecutionProvider"],
        )
        self.input_name = self.session.get_inputs()[0].name
        self.char_dict = _load_char_dict(model_dir / "inference.yml")
        self.rec_image_shape = (3, 48, 320)

    def recognize(self, img: np.ndarray, boxes: list[np.ndarray]) -> list[tuple[str, float]]:
        """识别所有文本框，返回 [(text, score), ...]。"""
        if not boxes:
            return []

        results = []
        for box in boxes:
            crop = self._crop_and_resize(img, box)
            inp = self._preprocess(crop)
            outputs = self.session.run(None, {self.input_name: inp})
            text, score = self._ctc_decode(outputs[0])
            results.append((text, score))

        return results

    def _crop_and_resize(self, img: np.ndarray, box: np.ndarray) -> np.ndarray:
        """透视变换裁剪文本区域。"""
        x_min = max(0, int(box[:, 0].min()))
        x_max = min(img.shape[1], int(box[:, 0].max()))
        y_min = max(0, int(box[:, 1].min()))
        y_max = min(img.shape[0], int(box[:, 1].max()))

        crop_w = x_max - x_min
        crop_h = y_max - y_min
        if crop_w < 1 or crop_h < 1:
            return np.zeros((48, 320, 3), dtype=np.uint8)

        crop = img[y_min:y_max, x_min:x_max].copy()
        return crop

    def _preprocess(self, crop: np.ndarray) -> np.ndarray:
        _, target_h, target_w = self.rec_image_shape
        h, w = crop.shape[:2]
        if h < 1 or w < 1:
            return np.zeros((1, 3, target_h, target_w), dtype=np.float32)

        ratio = target_h / h
        new_w = min(int(w * ratio), target_w)
        resized = cv2.resize(crop, (new_w, target_h))

        # Pad to target_w
        padded = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        padded[:, :new_w, :] = resized

        # Normalize
        padded = padded.astype(np.float32) / 255.0
        padded = (padded - 0.5) / 0.5  # PaddleOCR rec normalize

        # HWC -> CHW, add batch
        padded = padded.transpose(2, 0, 1)[np.newaxis, ...]
        return padded.astype(np.float32)

    def _ctc_decode(self, output: np.ndarray) -> tuple[str, float]:
        """CTC 贪心解码。"""
        preds = output[0]  # (T, vocab_size)
        pred_indices = preds.argmax(axis=1)
        pred_scores = preds.max(axis=1)

        chars = []
        scores = []
        prev_idx = 0  # blank

        for i, idx in enumerate(pred_indices):
            if idx != 0 and idx != prev_idx:  # 非 blank 且非重复
                if idx < len(self.char_dict):
                    chars.append(self.char_dict[idx])
                    scores.append(float(pred_scores[i]))
            prev_idx = idx

        text = "".join(chars)
        avg_score = float(np.mean(scores)) if scores else 0.0
        return text, avg_score


# ═══════════════════════════════════════════════════════
# 完整 OCR 引擎
# ═══════════════════════════════════════════════════════

class OnnxOCREngine:
    """ONNX Runtime OCR 引擎，与 OCREngine 接口兼容。"""

    def __init__(
        self,
        det_model_dir: Path | None = None,
        rec_model_dir: Path | None = None,
        speed_mode: str = "server",
    ) -> None:
        model_root = _get_model_root()

        if det_model_dir is None:
            if speed_mode == "mobile":
                det_model_dir = model_root / "PP-OCRv5_mobile_det"
            else:
                det_model_dir = model_root / "PP-OCRv5_server_det"
        if rec_model_dir is None:
            if speed_mode == "mobile":
                rec_model_dir = model_root / "PP-OCRv5_mobile_rec"
            else:
                rec_model_dir = model_root / "PP-OCRv5_server_rec"

        self._det_dir = det_model_dir
        self._rec_dir = rec_model_dir
        self._detector: DBDetector | None = None
        self._recognizer: CRNNRecognizer | None = None

    def _ensure_model(self) -> None:
        if self._detector is not None:
            return
        self._detector = DBDetector(self._det_dir)
        self._recognizer = CRNNRecognizer(self._rec_dir)

    def predict(self, image_path: Path) -> DocumentResult:
        self._ensure_model()

        img = cv2.imread(str(image_path))
        if img is None:
            return DocumentResult(
                source_path=image_path, page_count=1, pages=[], plain_text=""
            )

        h, w = img.shape[:2]

        # 检测
        boxes = self._detector.detect(img)

        # 按 y 坐标排序（阅读顺序）
        boxes.sort(key=lambda b: (b[:, 1].min(), b[:, 0].min()))

        # 识别
        results = self._recognizer.recognize(img, boxes)

        # 构建结果
        blocks = []
        texts = []
        for box, (text, score) in zip(boxes, results):
            if not text.strip():
                continue
            x1, y1 = float(box[:, 0].min()), float(box[:, 1].min())
            x2, y2 = float(box[:, 0].max()), float(box[:, 1].max())
            blocks.append(
                BlockResult(
                    block_type=BlockType.PARAGRAPH,
                    bbox=(x1, y1, x2, y2),
                    text=text,
                    confidence=score,
                )
            )
            texts.append(text)

        page = PageResult(
            page_index=0,
            width=w,
            height=h,
            blocks=blocks,
        )

        return DocumentResult(
            source_path=image_path,
            page_count=1,
            pages=[page],
            plain_text="\n".join(texts),
        )
