"""ffmpeg 抽帧:密集均匀帧(供 OCR)、补抽帧、封面帧、音频。"""
from __future__ import annotations
import glob
import os
import subprocess

from . import config


def _run(args: list[str]) -> None:
    subprocess.run([config.FFMPEG, "-y", *args], check=True, capture_output=True, text=True)


def probe_duration(video: str) -> float:
    out = subprocess.run(
        [config.FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def extract_audio(video: str, out_dir: str) -> str:
    """抽 16k 单声道 wav 供 ASR。"""
    wav = os.path.join(out_dir, "audio.wav")
    _run(["-i", video, "-ac", "1", "-ar", "16000", wav])
    return wav


def dense_frames(video: str, out_dir: str, fps: int, height: int) -> list[tuple[float, str]]:
    """均匀 fps 抽帧 → [(timestamp, path)]。timestamp = index / fps。"""
    frames_dir = os.path.join(out_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    pat = os.path.join(frames_dir, "f_%04d.jpg")
    _run(["-i", video, "-vf", f"fps={fps},scale=-1:{height}", "-q:v", "3", pat])
    out = []
    for i, p in enumerate(sorted(glob.glob(os.path.join(frames_dir, "f_*.jpg")))):
        out.append((round((i + 0.5) / fps, 2), p))  # 帧中点时间戳
    return out


def redense_frames(video: str, out_dir: str, t: float, fps: int, height: int, window: float = 2.0) -> list[tuple[float, str]]:
    """对时间戳 t 附近 ±window 秒以更高 fps 补抽(完整性补抽)。"""
    sub = os.path.join(out_dir, "frames", f"redense_{int(t)}")
    os.makedirs(sub, exist_ok=True)
    start = max(0.0, t - window)
    pat = os.path.join(sub, "r_%04d.jpg")
    _run(["-ss", str(start), "-t", str(window * 2), "-i", video,
          "-vf", f"fps={fps},scale=-1:{height}", "-q:v", "2", pat])
    out = []
    for i, p in enumerate(sorted(glob.glob(os.path.join(sub, "r_*.jpg")))):
        out.append((round(start + (i + 0.5) / fps, 2), p))
    return out


def grab_frame(video: str, t: float, dest: str, height: int = 1280) -> str:
    """抽单帧到 dest(用于封面/步骤图)。"""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    _run(["-ss", str(t), "-i", video, "-frames:v", "1", "-vf", f"scale=-1:{height}", "-q:v", "2", dest])
    return dest
