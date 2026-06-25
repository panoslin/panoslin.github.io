"""配置与路径。所有路径相对项目根。"""
from __future__ import annotations
import os
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ffmpeg 在 PATH 之外时的兜底位置(Homebrew)
FFMPEG = os.environ.get("FFMPEG_BIN") or (
    "/opt/homebrew/bin/ffmpeg" if os.path.exists("/opt/homebrew/bin/ffmpeg") else "ffmpeg"
)
FFPROBE = os.environ.get("FFPROBE_BIN") or (
    "/opt/homebrew/bin/ffprobe" if os.path.exists("/opt/homebrew/bin/ffprobe") else "ffprobe"
)

DATA = os.path.join(ROOT, "data")
DIRS = {
    "queue": os.path.join(DATA, "queue"),
    "work": os.path.join(DATA, "work"),
    "images": os.path.join(DATA, "images"),
    "videos": os.path.join(DATA, "videos"),
    "failed": os.path.join(DATA, "failed"),
    "state": os.path.join(DATA, "state"),
    "cache": os.path.join(ROOT, ".cache"),
}


def load_config(path: str | None = None) -> dict:
    path = path or os.path.join(ROOT, "config.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dirs() -> None:
    for d in DIRS.values():
        os.makedirs(d, exist_ok=True)


def work_dir(aweme_id: str) -> str:
    d = os.path.join(DIRS["work"], aweme_id)
    os.makedirs(os.path.join(d, "frames"), exist_ok=True)
    return d
