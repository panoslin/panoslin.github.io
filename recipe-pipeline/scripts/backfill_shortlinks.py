"""一次性 backfill:把现有 recipes.json 里的 v.douyin.com 短链解析成 aweme_id,
种进 seen.json(status=seed),避免首次全量增量时重复收录历史食谱。

用法: ./.venv/bin/python scripts/backfill_shortlinks.py
"""
from __future__ import annotations
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from recipe_pipeline import config, state  # noqa: E402

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/148 Safari/537.36"
AWEME_RE = re.compile(r"/(?:video|note|modal_id=)/?(\d{15,21})")


def resolve(short_url: str) -> str | None:
    try:
        req = urllib.request.Request(short_url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            final = resp.geturl()
        m = AWEME_RE.search(final) or re.search(r"(\d{15,21})", final)
        return m.group(1) if m else None
    except Exception as e:
        print(f"  解析失败 {short_url}: {e}", file=sys.stderr)
        return None


def main():
    cfg = config.load_config()
    recipes_path = os.path.join(config.DIRS["cache"], "repo", "recipes.json")
    if not os.path.exists(recipes_path):
        url = f"https://raw.githubusercontent.com/{cfg['repo']['slug']}/main/{cfg['repo']['recipes_json']}"
        os.makedirs(os.path.dirname(recipes_path), exist_ok=True)
        urllib.request.urlretrieve(url, recipes_path)
    recipes = json.load(open(recipes_path, encoding="utf-8"))

    seen = state.load_seen()
    short = [(r["id"], r["source"]) for r in recipes
             if isinstance(r.get("source"), str) and "v.douyin.com" in r["source"]]
    print(f"待解析短链 {len(short)} 条")
    ok = 0
    for rid, url in short:
        aid = resolve(url)
        if aid:
            state.mark(seen, aid, status="seed", recipe_id=rid, source=url)
            ok += 1
            print(f"  recipe {rid}: {url} -> {aid}")
    state.save_seen(seen)
    print(f"完成:{ok}/{len(short)} 解析成功,已种入 seen.json")


if __name__ == "__main__":
    main()
