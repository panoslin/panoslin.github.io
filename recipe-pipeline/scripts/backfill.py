#!/usr/bin/env python3
"""全量回填:对 data/queue/new_ids.json 的每个新 aweme_id 端到端处理,
每条单独一个 PR(stacked 在上一条之上)。可续跑(跳过已 done/seed/review)、限速、命中菜名重复则标 review 不开 PR。

用法: ./.venv/bin/python scripts/backfill.py [--limit N] [--sleep 20]
监控: tail -f data/backfill.log
"""
from __future__ import annotations
import argparse
import json
import os
import random
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from recipe_pipeline import (config, bundle as bundle_mod, structure as structure_mod,  # noqa: E402
                             merge, schema, dedup, state)

CLONE = os.path.join(config.DIRS["cache"], "clone")
REPO = "panoslin/panoslin.github.io"
LOG = os.path.join(config.DATA, "backfill.log")
TRAILER = "🤖 Generated with [Claude Code](https://claude.com/claude-code)"


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def git(*args, check=True):
    return subprocess.run(["git", "-C", CLONE, *args], check=check, capture_output=True, text=True)


def current_tip() -> str:
    """stacked 链尾 = id 最大的 recipe-<n> 本地分支;无则 main。"""
    out = git("branch", "--list", "recipe-*", check=False).stdout
    ids = []
    for ln in out.splitlines():
        m = re.search(r"recipe-(\d+)", ln)
        if m:
            ids.append((int(m.group(1)), f"recipe-{m.group(1)}" if ln.strip().lstrip("* ").strip() == f"recipe-{m.group(1)}" else ln.strip().lstrip("* ").strip()))
    return max(ids)[1] if ids else "main"


def process_one(aid: str, cap: str, cfg: dict, seen: dict) -> None:
    bundle_mod.build_bundle(aid, caption=cap, cfg=cfg)
    b = json.load(open(os.path.join(config.work_dir(aid), "bundle.json"), encoding="utf-8"))
    draft = structure_mod.structure_bundle(b)
    json.dump(draft, open(os.path.join(config.work_dir(aid), "draft.json"), "w"), ensure_ascii=False, indent=2)

    tip = current_tip()
    git("checkout", tip)
    recipes = json.load(open(os.path.join(CLONE, "recipes.json"), encoding="utf-8"))
    video = os.path.join(ROOT, b["video_path"])
    recipe = merge.finalize(draft, aid, video, cfg, recipes, os.path.join(CLONE, "images"))

    errs = schema.validate(recipe)
    if errs:
        raise ValueError(f"schema 失败: {errs}")
    dups = dedup.find_title_dups(recipe["title"], recipes)
    if dups:
        state.mark(seen, aid, "review", source=recipe["source"])
        state.save_seen(seen)
        json.dump({"recipe": recipe, "dups": dups},
                  open(os.path.join(config.DIRS["failed"], f"{aid}.review.json"), "w"),
                  ensure_ascii=False, indent=2)
        log(f"  ↪ 菜名疑重复, 标 review 不开 PR: {[d['title'] for d in dups[:2]]}")
        return

    rid = recipe["id"]
    branch = f"recipe-{rid}"
    git("checkout", "-b", branch)
    recipes.append(recipe)
    json.dump(recipes, open(os.path.join(CLONE, "recipes.json"), "w"), ensure_ascii=False, indent=2)
    git("add", "recipes.json", recipe["imageUrl"])
    for s in recipe["instructions"]:
        if isinstance(s, dict) and s.get("imageUrl"):
            git("add", s["imageUrl"], check=False)
    git("commit", "-m", f"feat(recipe): {rid} {recipe['title']}\n\n来源: {recipe['source']}\n\nCo-Authored-By: Claude Fable 5 <noreply@anthropic.com>")
    git("push", "-u", "origin", branch)
    pr = subprocess.run(
        ["gh", "pr", "create", "-R", REPO, "--base", tip, "--head", branch,
         "--title", f"新增食谱:{recipe['title']} (id {rid})",
         "--body", f"由抖音「菜谱」收藏夹增量管道自动抓取并由 Claude Code 结构化。\n来源: {recipe['source']}\n\n{TRAILER}"],
        cwd=CLONE, capture_output=True, text=True)
    prurl = (pr.stdout or pr.stderr).strip().splitlines()[-1] if (pr.stdout or pr.stderr) else "?"
    state.mark(seen, aid, "done", recipe_id=rid, source=recipe["source"])
    seen[aid]["pr"] = prurl
    state.save_seen(seen)
    log(f"  ✓ id={rid} {recipe['title']} PR={prurl}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=20.0)
    args = ap.parse_args()
    cfg = config.load_config()
    config.ensure_dirs()
    lock = os.path.join(config.DIRS["cache"], "backfill.lock")
    open(lock, "w").write(str(os.getpid()))
    import atexit
    atexit.register(lambda: os.path.exists(lock) and os.remove(lock))
    items = json.load(open(os.path.join(config.DIRS["queue"], "new_ids.json"), encoding="utf-8"))
    items = [it if isinstance(it, dict) else {"id": it, "cap": ""} for it in items]
    seen = state.load_seen()
    todo = [it for it in items if seen.get(it["id"], {}).get("status") not in ("done", "seed", "review", "dup_skip", "video_pending")]
    if args.limit:
        todo = todo[:args.limit]
    log(f"=== backfill 开始: 待处理 {len(todo)} 条 (sleep~{args.sleep}s) ===")
    ok = fail = 0
    for i, it in enumerate(todo, 1):
        aid = it["id"]
        log(f"[{i}/{len(todo)}] {aid} ...")
        try:
            process_one(aid, it.get("cap", ""), cfg, seen)
            ok += 1
        except Exception as e:
            state.mark(seen, aid, "failed", source=f"https://www.douyin.com/video/{aid}")
            state.save_seen(seen)
            json.dump({"error": str(e)[:1000]}, open(os.path.join(config.DIRS["failed"], f"{aid}.json"), "w"), ensure_ascii=False, indent=2)
            log(f"  ✗ 失败: {str(e)[:200]}")
            fail += 1
            try:
                git("checkout", "--", ".", check=False)
            except Exception:
                pass
        time.sleep(args.sleep + random.uniform(0, 10))
    log(f"=== backfill 结束: 成功 {ok} / 失败 {fail} ===")


if __name__ == "__main__":
    main()
