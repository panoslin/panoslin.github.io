"""把一个视频处理成 bundle.json(三路原始信号),供 Claude Code 结构化。"""
from __future__ import annotations
import json
import os

from . import config, download, frames
from .providers import asr_faster_whisper as asr
from .providers import ocr_rapidocr as ocr


def build_bundle(aweme_id: str, caption: str = "", author: str = "", cfg: dict | None = None) -> dict:
    cfg = cfg or config.load_config()
    config.ensure_dirs()
    wdir = config.work_dir(aweme_id)

    video = download.download_with_fallback(aweme_id, config.DIRS["videos"])
    duration = frames.probe_duration(video)

    # ASR
    wav = frames.extract_audio(video, wdir)
    transcript, asr_usable = asr.transcribe(wav, cfg)

    # 密集抽帧 + OCR 时间线
    fcfg = cfg["frames"]
    dense = frames.dense_frames(video, wdir, fps=fcfg["ocr_fps"], height=fcfg["ocr_height"])
    timeline = ocr.build_timeline(dense)

    bundle = {
        "aweme_id": aweme_id,
        "source": download.video_url(aweme_id),
        "title_caption": caption,
        "author": author,
        "duration": duration,
        "ocr_timeline": timeline,
        "transcript": transcript,
        "asr_usable": asr_usable,
        "keyframes": [{"t": t, "path": os.path.relpath(p, config.ROOT)} for t, p in dense],
        "video_path": os.path.relpath(video, config.ROOT),
    }
    with open(os.path.join(wdir, "bundle.json"), "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)

    if not cfg["storage"].get("keep_video", False):
        pass  # 视频在 merge 取完步骤图后再删; 此处保留
    return bundle
