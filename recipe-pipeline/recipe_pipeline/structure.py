"""结构化:调用 Claude Code(headless `claude -p`)按冻结契约把 bundle 变成草稿。
交互运行时也可由当前 agent 直接执行同一契约;此模块用于无头/定时路径。"""
from __future__ import annotations
import json
import os
import re
import subprocess

from . import config


def _claude_bin() -> str:
    for c in (os.path.expanduser("~/.local/bin/claude"), "claude"):
        if os.path.sep not in c or os.path.exists(c):
            return c
    return "claude"


def _extract_json(text: str) -> dict:
    """从模型输出里抽出 JSON 对象(容忍 ```json 围栏与前后解释)。"""
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    raw = fence.group(1) if fence else text[text.find("{"): text.rfind("}") + 1]
    return json.loads(raw)


def structure_bundle(bundle: dict, contract_path: str | None = None) -> dict:
    contract_path = contract_path or os.path.join(config.ROOT, "prompts", "structuring.md")
    contract = open(contract_path, encoding="utf-8").read()
    prompt = (
        contract
        + "\n\n## 本次输入 bundle.json\n```json\n"
        + json.dumps(bundle, ensure_ascii=False)
        + "\n```\n\n"
        + "如某帧 OCR 文本可疑(如单位 g 被误读为数字),你可以用 Read 工具查看对应 keyframe 的 path 图片来核对。"
        + "完成后**只输出 JSON 草稿对象**,不要任何解释文字。"
    )
    proc = subprocess.run(
        [_claude_bin(), "-p", prompt, "--output-format", "json", "--allowedTools", "Read"],
        check=True, capture_output=True, text=True, cwd=config.ROOT,
    )
    envelope = json.loads(proc.stdout)
    result_text = envelope.get("result", proc.stdout)
    return _extract_json(result_text)
