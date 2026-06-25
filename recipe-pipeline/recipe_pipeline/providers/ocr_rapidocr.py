"""OCR provider: RapidOCR(PaddleOCR 模型的 ONNX 版)。逐帧识别并按文本去重成时间线。"""
from __future__ import annotations
import re

_OCR = None


def _get_ocr():
    global _OCR
    if _OCR is None:
        from rapidocr_onnxruntime import RapidOCR
        _OCR = RapidOCR()
    return _OCR


def ocr_image(path: str) -> list[str]:
    res, _ = _get_ocr()(path)
    return [item[1].strip() for item in (res or []) if item[1] and item[1].strip()]


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def build_timeline(frames: list[tuple[float, str]]) -> list[dict]:
    """逐帧 OCR → 按归一化文本去重(同句只留最早时间戳)。
    返回 [{"t": 秒, "text": "该帧所有文字 用 / 连接"}]。"""
    seen: set[str] = set()
    timeline: list[dict] = []
    for t, path in frames:
        lines = ocr_image(path)
        fresh = [ln for ln in lines if _norm(ln) and _norm(ln) not in seen and len(_norm(ln)) >= 2]
        for ln in fresh:
            seen.add(_norm(ln))
        if fresh:
            timeline.append({"t": t, "text": " / ".join(fresh)})
    return timeline
