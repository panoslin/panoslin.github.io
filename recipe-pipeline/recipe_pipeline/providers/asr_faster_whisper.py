"""ASR provider: faster-whisper。含纯 BGM 幻觉检测。"""
from __future__ import annotations
import os

from .. import config

_MODEL = None


def _get_model(model_size: str):
    global _MODEL
    if _MODEL is None:
        # 模型缓存到项目 .cache/hf; 直连 huggingface.co(不要用 hf-mirror, 它只跳转)
        os.environ.setdefault("HF_HOME", os.path.join(config.DIRS["cache"], "hf"))
        os.environ.pop("HF_ENDPOINT", None)
        from faster_whisper import WhisperModel
        _MODEL = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _MODEL


def transcribe(wav_path: str, cfg: dict) -> tuple[list[dict], bool]:
    """返回 (segments, asr_usable)。asr_usable=False 表示纯 BGM/幻觉, 应忽略。"""
    acfg = cfg["asr"]
    model = _get_model(acfg["model"])
    segments, _info = model.transcribe(
        wav_path, language=acfg["language"], vad_filter=True, beam_size=5,
        initial_prompt="这是一个中文美食食谱视频，主播会口播食材和具体用量，例如克、毫升、勺、个、适量。",
    )
    segs = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segments]
    return segs, _is_usable(segs, acfg.get("hallucination_markers", []))


def _is_usable(segs: list[dict], markers: list[str]) -> bool:
    """启发式:文本太少或被幻觉短语主导 → 不可用。"""
    full = "".join(s["text"] for s in segs)
    if len(full) < 8:
        return False
    hits = sum(1 for m in markers if m in full)
    # 命中点赞/订阅类幻觉, 且总文本很短(典型 BGM 幻觉是一两句套话)
    if hits >= 1 and len(full) < 60:
        return False
    if hits >= 2:
        return False
    return True
