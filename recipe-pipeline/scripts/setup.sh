#!/usr/bin/env bash
# 一次性环境搭建。注意:pip 必须走公网(本机内网镜像 bytedpypi 连不上)。
set -euo pipefail
cd "$(dirname "$0")/.."

command -v ffmpeg >/dev/null 2>&1 || brew install ffmpeg

[ -d .venv ] || /opt/homebrew/bin/python3 -m venv .venv
./.venv/bin/python -m pip install --index-url https://pypi.org/simple/ -U pip
./.venv/bin/python -m pip install --index-url https://pypi.org/simple/ -r requirements.txt

echo "✅ 完成。"
echo "提示:faster-whisper 首次运行会从 huggingface.co 下载模型到 .cache/hf(勿设 HF_ENDPOINT)。"
