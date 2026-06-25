#!/usr/bin/env python3
"""并行回填(赶时间版):重活(下载/ASR/OCR/结构化)用进程池并发产出 draft.json,
建 PR(动 git)在主进程串行、按 id 顺序。可续跑、限并发下载。

  ./.venv/bin/python scripts/backfill_parallel.py [--workers 5]
监控: tail -f data/backfill.log
"""
from __future__ import annotations
import argparse
import concurrent.futures as cf
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
    out = git("branch", "--list", "recipe-*", check=False).stdout
    ids = [int(m.group(1)) for ln in out.splitlines() if (m := re.search(r"recipe-(\d+)", ln))]
    return f"recipe-{max(ids)}" if ids else "main"


def produce(aid: str, cap: str) -> str:
    """worker 进程:产出 draft.json(+保留 video)。幂等。"""
    cfg = config.load_config()
    ddir = config.work_dir(aid)
    dpath = os.path.join(ddir, "draft.json")
    if os.path.exists(dpath):
        return aid
    time.sleep(random.uniform(0, 6))  # 错峰下载, 缓解风控
    bundle_mod.build_bundle(aid, caption=cap, cfg=cfg)
    b = json.load(open(os.path.join(ddir, "bundle.json"), encoding="utf-8"))
    draft = structure_mod.structure_bundle(b)
    json.dump(draft, open(dpath + ".tmp", "w"), ensure_ascii=False, indent=2)
    os.replace(dpath + ".tmp", dpath)
    return aid


def publish(aid: str, cfg: dict, seen: dict) -> str:
    """主进程串行:finalize + git/PR。返回状态字符串。"""
    ddir = config.work_dir(aid)
    draft = json.load(open(os.path.join(ddir, "draft.json"), encoding="utf-8"))
    b = json.load(open(os.path.join(ddir, "bundle.json"), encoding="utf-8"))
    tip = current_tip()
    git("checkout", tip)
    recipes = json.load(open(os.path.join(CLONE, "recipes.json"), encoding="utf-8"))
    video = os.path.join(ROOT, b["video_path"])
    recipe = merge.finalize(draft, aid, video, cfg, recipes, os.path.join(CLONE, "images"))
    errs = schema.validate(recipe)
    if errs:
        raise ValueError(f"schema 失败: {errs}")
    if dedup.find_title_dups(recipe["title"], recipes):
        state.mark(seen, aid, "review", source=recipe["source"]); state.save_seen(seen)
        return "review"
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
    return "done"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=5)
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
    log(f"=== 并行回填开始: 待处理 {len(todo)} 条, workers={args.workers} ===")
    ok = fail = review = 0
    with cf.ProcessPoolExecutor(max_workers=args.workers) as ex:
        fut = {ex.submit(produce, it["id"], it.get("cap", "")): it["id"] for it in todo}
        byid = {v: k for k, v in fut.items()}
        for i, it in enumerate(todo, 1):
            aid = it["id"]
            seen = state.load_seen()
            if seen.get(aid, {}).get("status") in ("done", "review"):
                continue
            try:
                byid[aid].result(timeout=1500)  # 等该条 draft 就绪
            except Exception as e:
                state.mark(seen, aid, "failed", source=f"https://www.douyin.com/video/{aid}"); state.save_seen(seen)
                json.dump({"stage": "produce", "error": str(e)[:800]}, open(os.path.join(config.DIRS["failed"], f"{aid}.json"), "w"), ensure_ascii=False)
                log(f"[{i}/{len(todo)}] {aid} 产出失败: {str(e)[:150]}"); fail += 1
                continue
            try:
                st = publish(aid, cfg, seen)
                if st == "done":
                    ok += 1
                elif st == "review":
                    review += 1; log(f"[{i}/{len(todo)}] {aid} 菜名疑重复 → review")
            except Exception as e:
                state.mark(seen, aid, "failed", source=f"https://www.douyin.com/video/{aid}"); state.save_seen(seen)
                json.dump({"stage": "publish", "error": str(e)[:800]}, open(os.path.join(config.DIRS["failed"], f"{aid}.json"), "w"), ensure_ascii=False)
                log(f"[{i}/{len(todo)}] {aid} 发布失败: {str(e)[:150]}"); fail += 1
                git("checkout", "--", ".", check=False)
            if i % 10 == 0:
                log(f"--- 进度 {i}/{len(todo)} | 成功{ok} 复核{review} 失败{fail} ---")
    log(f"=== 并行回填结束: 成功 {ok} / 复核 {review} / 失败 {fail} ===")


if __name__ == "__main__":
    main()
