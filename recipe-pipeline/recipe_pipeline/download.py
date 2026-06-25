"""下载抖音视频。优先无 cookie(公开视频实测可下),失败回退浏览器 cookie。"""
from __future__ import annotations
import os
import subprocess
import sys

from . import config


def _ytdlp() -> str:
    venv = os.path.join(config.ROOT, ".venv", "bin", "yt-dlp")
    return venv if os.path.exists(venv) else "yt-dlp"


def video_url(aweme_id: str) -> str:
    return f"https://www.douyin.com/video/{aweme_id}"


def download(aweme_id: str, out_dir: str, use_cookies: bool = False) -> str:
    """下载到 out_dir/<aweme_id>.<ext>，返回视频文件路径。"""
    out_tmpl = os.path.join(out_dir, "%(id)s.%(ext)s")
    cmd = [
        _ytdlp(),
        "--ffmpeg-location", os.path.dirname(config.FFMPEG),
        "-o", out_tmpl,
        "--no-playlist",
        video_url(aweme_id),
    ]
    if use_cookies:
        cmd[1:1] = ["--cookies-from-browser", "chrome"]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    for ext in ("mp4", "webm", "mkv"):
        p = os.path.join(out_dir, f"{aweme_id}.{ext}")
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f"下载后未找到视频文件: {aweme_id}")


def download_with_fallback(aweme_id: str, out_dir: str) -> str:
    try:
        return download(aweme_id, out_dir, use_cookies=False)
    except subprocess.CalledProcessError as e:
        print(f"  无 cookie 下载失败, 回退浏览器 cookie: {e.stderr[:200]}", file=sys.stderr)
        return download(aweme_id, out_dir, use_cookies=True)
