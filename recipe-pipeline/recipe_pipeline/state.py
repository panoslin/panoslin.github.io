"""增量状态:seen.json 记录已见/已收录的 aweme_id,据此算增量。"""
from __future__ import annotations
import datetime as _dt
import json
import os

from . import config

SEEN_PATH = os.path.join(config.DIRS["state"], "seen.json")


def load_seen() -> dict:
    if os.path.exists(SEEN_PATH):
        return json.load(open(SEEN_PATH, encoding="utf-8"))
    return {}


def save_seen(seen: dict) -> None:
    config.ensure_dirs()
    tmp = SEEN_PATH + ".tmp"
    json.dump(seen, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    os.replace(tmp, SEEN_PATH)


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def new_ids(harvested_ids: list[str], seen: dict) -> list[str]:
    """返回未处理的新 id(已 done/seed 的跳过;failed 的允许重试)。"""
    out = []
    for aid in harvested_ids:
        st = seen.get(aid, {}).get("status")
        if st in ("done", "seed"):
            continue
        out.append(aid)
    return out


def mark(seen: dict, aweme_id: str, status: str, recipe_id: int | None = None,
         source: str | None = None) -> None:
    rec = seen.get(aweme_id, {})
    rec.update({"status": status, "updated": _now()})
    if "first_seen" not in rec:
        rec["first_seen"] = _now()
    if recipe_id is not None:
        rec["recipe_id"] = recipe_id
    if source is not None:
        rec["source"] = source
    seen[aweme_id] = rec
