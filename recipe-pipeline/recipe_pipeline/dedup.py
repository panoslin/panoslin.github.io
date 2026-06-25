"""二次去重:按菜名相似度,防止与历史食谱(尤其 32 条无 source 的)重复收录。

按 aweme_id 的一级去重在 state.seen 里做;这里是菜名层面的安全网,
命中则标 needs_review,交人工裁决,不自动合并。
"""
from __future__ import annotations
import difflib
import re


def _norm(s: str) -> str:
    # 去 emoji/标点/空白,只留中英数字
    return re.sub(r"[^一-龥a-zA-Z0-9]", "", s or "")


def find_title_dups(title: str, recipes: list[dict], threshold: float = 0.82) -> list[dict]:
    """返回与 title 高度相似的现有食谱。"""
    nt = _norm(title)
    hits = []
    for r in recipes:
        rt = _norm(r.get("title", ""))
        if not rt:
            continue
        ratio = difflib.SequenceMatcher(None, nt, rt).ratio()
        # 相似度高,或一方菜名核心被另一方包含(>=3 字)
        contained = len(nt) >= 3 and len(rt) >= 3 and (nt in rt or rt in nt)
        if ratio >= threshold or contained:
            hits.append({"id": r["id"], "title": r["title"], "ratio": round(ratio, 2)})
    return sorted(hits, key=lambda h: -h["ratio"])
