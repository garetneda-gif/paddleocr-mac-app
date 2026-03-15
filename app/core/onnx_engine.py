"""ONNX Runtime OCR 引擎 — 完全替换 PaddlePaddle，更快更省内存。

实现 DB 文本检测 + CRNN 文本识别的完整前后处理。
使用预转换的 PP-OCRv5 ONNX 模型，无需安装 PaddlePaddle。
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from app.models import BlockResult, BlockType, DocumentResult, PageResult

# ─── 模型路径 ───────────────────────────────────────────
_EXTERNAL_ONNX_DIR = Path("/Volumes/MOVESPEED/存储/models/onnx")
_INTERNAL_ONNX_DIR = Path.home() / ".paddlex" / "onnx_models"
_CHAR_DICT_PATH = Path("/Volumes/MOVESPEED/存储/models/ppocr_keys_v5.txt")

# 模型文件名映射
_MODEL_FILES = {
    "mobile_det": "PP-OCRv5_mobile_det.onnx",
    "mobile_rec": "PP-OCRv5_mobile_rec.onnx",
    "server_det": "PP-OCRv5_server_det.onnx",
    "server_rec": "PP-OCRv5_server_rec.onnx",
}


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


def _find_onnx_dir() -> Path | None:
    """返回包含 ONNX 模型的目录，不存在则返回 None。"""
    if _check_path_accessible(_EXTERNAL_ONNX_DIR):
        return _EXTERNAL_ONNX_DIR
    if _INTERNAL_ONNX_DIR.exists():
        return _INTERNAL_ONNX_DIR
    return None


def onnx_available(speed_mode: str = "mobile") -> bool:
    """检查 ONNX 引擎是否可用（模型文件+运行时都存在）。"""
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return False

    onnx_dir = _find_onnx_dir()
    if onnx_dir is None:
        return False

    det_key = f"{speed_mode}_det"
    rec_key = f"{speed_mode}_rec"
    return (
        (onnx_dir / _MODEL_FILES[det_key]).exists()
        and (onnx_dir / _MODEL_FILES[rec_key]).exists()
    )


def _load_char_dict() -> list[str]:
    """从 ppocr_keys_v5.txt 加载字符字典。"""
    # 优先外置硬盘，回退内置
    for candidate in [_CHAR_DICT_PATH, _INTERNAL_ONNX_DIR / "ppocr_keys_v5.txt"]:
        if candidate.exists():
            lines = candidate.read_text(encoding="utf-8").splitlines()
            chars = [line for line in lines if line]  # 保留空格等字符
            # CTC 格式：[blank] + chars + [space]
            return ["blank"] + chars + [" "]
    raise FileNotFoundError("未找到字符字典 ppocr_keys_v5.txt")


# ═══════════════════════════════════════════════════════
# 文本检测（DB）
# ═══════════════════════════════════════════════════════

class DBDetector:
    """DB 文本检测器（PP-OCRv5）。"""

    def __init__(self, onnx_path: Path) -> None:
        import onnxruntime as ort

        self.session = ort.InferenceSession(
            str(onnx_path),
            providers=["CPUExecutionProvider"],
        )
        self.input_name = self.session.get_inputs()[0].name
        self.thresh = 0.3
        self.box_thresh = 0.6
        self.unclip_ratio = 1.5
        self.max_candidates = 1000
        self.limit_side_len = 960

    def detect(self, img: np.ndarray) -> list[np.ndarray]:
        """检测文本区域，返回四点多边形列表。"""
        h, w = img.shape[:2]
        resized, ratio_h, ratio_w = self._preprocess(img)
        outputs = self.session.run(None, {self.input_name: resized})
        pred = outputs[0][0, 0]  # (H, W)
        return self._postprocess(pred, h, w, ratio_h, ratio_w)

    def _preprocess(self, img: np.ndarray) -> tuple[np.ndarray, float, float]:
        h, w = img.shape[:2]
        ratio = 1.0
        if max(h, w) > self.limit_side_len:
            ratio = self.limit_side_len / max(h, w)
        new_h = max(int(h * ratio / 32) * 32, 32)
        new_w = max(int(w * ratio / 32) * 32, 32)

        resized = cv2.resize(img, (new_w, new_h))

        # ImageNet 标准化
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        resized = (resized.astype(np.float32) / 255.0 - mean) / std

        # HWC → CHW，加 batch 维
        resized = resized.transpose(2, 0, 1)[np.newaxis, ...]
        return resized.astype(np.float32), h / new_h, w / new_w

    def _postprocess(
        self, pred: np.ndarray, src_h: int, src_w: int,
        ratio_h: float, ratio_w: float
    ) -> list[np.ndarray]:
        """DB 后处理：二值化 → 轮廓 → unclip → 多边形。"""
        import pyclipper
        from shapely.geometry import Polygon

        bitmap = (pred > self.thresh).astype(np.uint8)
        contours, _ = cv2.findContours(bitmap, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        boxes = []
        for contour in contours[:self.max_candidates]:
            if contour.shape[0] < 4:
                continue

            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect)

            score = self._box_score(pred, contour)
            if score < self.box_thresh:
                continue

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

            rect = cv2.minAreaRect(expanded_box)
            box = cv2.boxPoints(rect)

            # 映射回原图坐标
            box[:, 0] *= ratio_w
            box[:, 1] *= ratio_h
            box = self._order_points(box)
            boxes.append(box)

        return boxes

    def _box_score(self, pred: np.ndarray, contour: np.ndarray) -> float:
        h, w = pred.shape
        pts = contour.reshape(-1, 2).copy()
        xmin = max(0, int(pts[:, 0].min()))
        xmax = min(w, int(pts[:, 0].max()) + 1)
        ymin = max(0, int(pts[:, 1].min()))
        ymax = min(h, int(pts[:, 1].max()) + 1)

        mask = np.zeros((ymax - ymin, xmax - xmin), dtype=np.uint8)
        pts[:, 0] -= xmin
        pts[:, 1] -= ymin
        cv2.fillPoly(mask, [pts.astype(np.int32)], 1)
        return float(cv2.mean(pred[ymin:ymax, xmin:xmax], mask)[0])

    @staticmethod
    def _order_points(pts: np.ndarray) -> np.ndarray:
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
    """CRNN 文本识别器 + CTC 贪心解码。"""

    def __init__(self, onnx_path: Path) -> None:
        import onnxruntime as ort

        self.session = ort.InferenceSession(
            str(onnx_path),
            providers=["CPUExecutionProvider"],
        )
        self.input_name = self.session.get_inputs()[0].name
        self.char_dict = _load_char_dict()
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
        # 计算裁剪宽高
        w = int(max(
            np.linalg.norm(box[0] - box[1]),
            np.linalg.norm(box[2] - box[3]),
        ))
        h = int(max(
            np.linalg.norm(box[0] - box[3]),
            np.linalg.norm(box[1] - box[2]),
        ))
        if w < 1 or h < 1:
            return np.zeros((48, 320, 3), dtype=np.uint8)

        # 透视变换
        dst = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
        M = cv2.getPerspectiveTransform(box.astype(np.float32), dst)
        crop = cv2.warpPerspective(img, M, (w, h))
        return crop

    def _preprocess(self, crop: np.ndarray) -> np.ndarray:
        _, target_h, target_w = self.rec_image_shape
        h, w = crop.shape[:2]
        if h < 1 or w < 1:
            return np.zeros((1, 3, target_h, target_w), dtype=np.float32)

        ratio = target_h / h
        new_w = min(int(w * ratio), target_w)
        if new_w < 1:
            new_w = 1
        resized = cv2.resize(crop, (new_w, target_h))

        # 填充到 target_w
        padded = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        padded[:, :new_w, :] = resized

        # PaddleOCR rec 标准化：(x/255 - 0.5) / 0.5
        padded = (padded.astype(np.float32) / 255.0 - 0.5) / 0.5

        # HWC → CHW，加 batch 维
        return padded.transpose(2, 0, 1)[np.newaxis, ...].astype(np.float32)

    def _ctc_decode(self, output: np.ndarray) -> tuple[str, float]:
        """CTC 贪心解码。"""
        preds = output[0]  # (T, vocab_size)
        pred_indices = preds.argmax(axis=1)
        pred_scores = preds.max(axis=1)

        chars = []
        scores = []
        prev_idx = 0  # blank

        for i, idx in enumerate(pred_indices):
            if idx != 0 and idx != prev_idx:
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
        lang: str = "ch",
        speed_mode: str = "server",
        options: dict[str, object] | None = None,
    ) -> None:
        self._speed_mode = speed_mode
        self._detector: DBDetector | None = None
        self._recognizer: CRNNRecognizer | None = None

    def _ensure_model(self) -> None:
        if self._detector is not None:
            return

        onnx_dir = _find_onnx_dir()
        if onnx_dir is None:
            raise FileNotFoundError("ONNX 模型目录不存在")

        det_key = f"{self._speed_mode}_det"
        rec_key = f"{self._speed_mode}_rec"
        det_path = onnx_dir / _MODEL_FILES[det_key]
        rec_path = onnx_dir / _MODEL_FILES[rec_key]

        if not det_path.exists():
            raise FileNotFoundError(f"检测模型不存在: {det_path}")
        if not rec_path.exists():
            raise FileNotFoundError(f"识别模型不存在: {rec_path}")

        self._detector = DBDetector(det_path)
        self._recognizer = CRNNRecognizer(rec_path)

    def predict(self, image_path: Path) -> DocumentResult:
        """与 OCREngine.predict() 接口一致。"""
        self._ensure_model()

        img = cv2.imread(str(image_path))
        if img is None:
            return DocumentResult(
                source_path=image_path, page_count=1, pages=[], plain_text=""
            )

        h, w = img.shape[:2]

        # 检测
        boxes = self._detector.detect(img)

        # 按阅读顺序排序（先 y 后 x）
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
