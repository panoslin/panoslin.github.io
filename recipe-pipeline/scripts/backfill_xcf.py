#!/usr/bin/env python3
"""下厨房(xiachufang)收藏夹全量回填:对 data/queue/xcf_ids.json 每个 recipe_id
端到端处理,每条单独一个 PR(stacked 在抖音链尾之上,保证 id 全局唯一不重复)。

设计要点:
- 抓取走 recipe_pipeline.xcf(curl_cffi 模拟 Chrome 指纹),公开页直抓;命中频率验证码抛 CaptchaError。
- **不与抖音回填并发**:启动前等 .cache/backfill.lock 释放(避免两条线同时取号/动 git)。
- **id 唯一性三重保证**:next_id 读链尾最新 recipes.json + 显式去重 bump + commit 前断言。
- 按 source(菜谱 URL)去重已存在;按标题相似度命中则标 review 不开 PR。
- 限速 + 验证码退避:连续命中验证码则暂停退出(留 seen.json 断点),重新验证后再跑可续。

用法: ./.venv/bin/python scripts/backfill_xcf.py [--limit N] [--sleep 18]
监控: tail -f data/backfill_xcf.log
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
from recipe_pipeline import (config, xcf, merge, nutrition, schema, dedup, state)  # noqa: E402

CLONE = os.path.join(config.DIRS["cache"], "clone")
REPO = "panoslin/panoslin.github.io"
LOG = os.path.join(config.DATA, "backfill_xcf.log")
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
    ids = [int(m.group(1)) for ln in out.splitlines() if (m := re.search(r"recipe-(\d+)", ln))]
    return f"recipe-{max(ids)}" if ids else "main"


def wait_for_douyin_lock() -> None:
    """抖音回填持有 .cache/backfill.lock 时等待;PID 已死则视为陈旧锁清掉。"""
    lock = os.path.join(config.DIRS["cache"], "backfill.lock")
    while os.path.exists(lock):
        try:
            pid = int(open(lock).read().strip())
            os.kill(pid, 0)  # 探活
            log(f"抖音回填(PID {pid})进行中,等待其释放锁... 60s 后重试")
            time.sleep(60)
        except (ValueError, ProcessLookupError, PermissionError):
            log("发现陈旧锁(持有进程已退出),清除并继续")
            os.remove(lock)
            break


def finalize_xcf(draft: dict, cfg: dict, recipes_existing: list[dict], images_out: str):
    """xcf draft → 完整 recipe + 本地图片清单。封面下载到本地;步骤图沿用 CDN(省仓库体积)。"""
    os.makedirs(images_out, exist_ok=True)
    existing_ids = {r["id"] for r in recipes_existing if isinstance(r.get("id"), int)}
    rid = merge.next_id(recipes_existing)
    while rid in existing_ids:        # id 唯一性硬保证(防与抖音/历史撞号)
        rid += 1

    for ing in draft["ingredients"]:  # 归一化用量,确保营养与 schema 不挂
        ing["quantity"] = merge.normalize_quantity(ing.get("quantity"))

    local_files = []
    image_url = None
    if draft.get("_cover_url"):
        fn = f"recipe_{rid}.jpg"
        if xcf.download_image(draft["_cover_url"], os.path.join(images_out, fn)):
            image_url = f"images/{fn}"
            local_files.append(image_url)
    if not image_url:  # 封面下载失败:退化用首个步骤图(CDN 热链)
        for s in draft["instructions"]:
            if isinstance(s, dict) and s.get("imageUrl"):
                image_url = s["imageUrl"]
                break
    if not image_url:
        image_url = draft.get("_cover_url") or ""

    recipe = {
        "id": rid,
        "title": draft["title"],
        "category": draft["category"],
        "imageUrl": image_url,
        "description": draft["description"],
        "ingredients": draft["ingredients"],
        "instructions": draft["instructions"],
        "nutrition": nutrition.compute(draft["ingredients"], cfg),
        "source": draft["source"],
    }
    return recipe, rid, local_files


def process_one(rid_xcf: str, cfg: dict, seen: dict) -> str:
    html = xcf.fetch(rid_xcf, retries=2)          # 可能抛 CaptchaError → 由上层捕获
    draft = xcf.parse(rid_xcf, html)

    tip = current_tip()
    git("checkout", tip)
    recipes = json.load(open(os.path.join(CLONE, "recipes.json"), encoding="utf-8"))

    # source 去重(已在库 → 不重复添加)
    if any(r.get("source") == draft["source"] for r in recipes):
        state.mark(seen, f"xcf:{rid_xcf}", "seed", source=draft["source"]); state.save_seen(seen)
        log(f"  ↪ source 已存在, 跳过: {draft['title'][:24]}")
        return "dup_source"

    recipe, rid, local_files = finalize_xcf(draft, cfg, recipes, os.path.join(CLONE, "images"))

    errs = schema.validate(recipe)
    if errs:
        raise ValueError(f"schema 失败: {errs[:3]}")

    if dedup.find_title_dups(recipe["title"], recipes):
        state.mark(seen, f"xcf:{rid_xcf}", "review", source=recipe["source"]); state.save_seen(seen)
        json.dump({"recipe": recipe}, open(os.path.join(config.DIRS["failed"], f"xcf_{rid_xcf}.review.json"), "w"), ensure_ascii=False, indent=2)
        log(f"  ↪ 菜名疑重复 → review: {recipe['title'][:24]}")
        return "review"

    assert not any(r.get("id") == rid for r in recipes), f"id {rid} 撞号!"  # 第三重断言

    branch = f"recipe-{rid}"
    git("checkout", "-b", branch)
    recipes.append(recipe)
    json.dump(recipes, open(os.path.join(CLONE, "recipes.json"), "w"), ensure_ascii=False, indent=2)
    git("add", "recipes.json")
    for f in local_files:
        git("add", f, check=False)
    git("commit", "-m", f"feat(recipe): {rid} {recipe['title']}\n\n来源(下厨房): {recipe['source']}\n\nCo-Authored-By: Claude Fable 5 <noreply@anthropic.com>")
    git("push", "-u", "origin", branch)
    pr = subprocess.run(
        ["gh", "pr", "create", "-R", REPO, "--base", tip, "--head", branch,
         "--title", f"新增食谱:{recipe['title']} (id {rid})",
         "--body", f"由下厨房收藏夹增量管道自动抓取并结构化。\n来源: {recipe['source']}\n\n{TRAILER}"],
        cwd=CLONE, capture_output=True, text=True)
    prurl = (pr.stdout or pr.stderr).strip().splitlines()[-1] if (pr.stdout or pr.stderr) else "?"
    state.mark(seen, f"xcf:{rid_xcf}", "done", recipe_id=rid, source=recipe["source"])
    seen[f"xcf:{rid_xcf}"]["pr"] = prurl
    state.save_seen(seen)
    log(f"  ✓ id={rid} {recipe['title'][:24]} PR={prurl}")
    return "done"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=18.0)
    args = ap.parse_args()
    cfg = config.load_config()
    config.ensure_dirs()

    wait_for_douyin_lock()
    lock = os.path.join(config.DIRS["cache"], "backfill.lock")
    open(lock, "w").write(str(os.getpid()))
    import atexit
    atexit.register(lambda: os.path.exists(lock) and os.remove(lock))

    items = json.load(open(os.path.join(config.DIRS["queue"], "xcf_ids.json"), encoding="utf-8"))
    items = [it if isinstance(it, dict) else {"id": str(it)} for it in items]
    seen = state.load_seen()
    todo = [it for it in items if seen.get(f"xcf:{it['id']}", {}).get("status") not in ("done", "seed", "review", "dup_skip", "video_pending")]
    if args.limit:
        todo = todo[:args.limit]
    log(f"=== xcf 回填开始: 待处理 {len(todo)} 条 (sleep~{args.sleep}s) ===")

    ok = fail = review = dup = 0
    captcha_streak = 0
    for i, it in enumerate(todo, 1):
        rid_xcf = it["id"]
        seen = state.load_seen()
        log(f"[{i}/{len(todo)}] xcf {rid_xcf} ...")
        try:
            st = process_one(rid_xcf, cfg, seen)
            captcha_streak = 0
            if st == "done":
                ok += 1
            elif st == "review":
                review += 1
            elif st == "dup_source":
                dup += 1
        except xcf.CaptchaError:
            captcha_streak += 1
            log(f"  ✗ 命中滑动验证(连续 {captcha_streak} 次)")
            git("checkout", "--", ".", check=False)
            if captcha_streak >= 3:
                log("=== 连续 3 次验证码,IP 被限。暂停退出,请在浏览器重新滑动验证后重跑本脚本(会从断点续) ===")
                break
            time.sleep(90)  # 退避后重试下一条
            continue
        except Exception as e:  # noqa: BLE001
            state.mark(seen, f"xcf:{rid_xcf}", "failed", source=f"https://www.xiachufang.com/recipe/{rid_xcf}/"); state.save_seen(seen)
            json.dump({"error": str(e)[:800]}, open(os.path.join(config.DIRS["failed"], f"xcf_{rid_xcf}.json"), "w"), ensure_ascii=False)
            log(f"  ✗ 失败: {str(e)[:160]}")
            fail += 1
            git("checkout", "--", ".", check=False)
        if i % 10 == 0:
            log(f"--- 进度 {i}/{len(todo)} | 成功{ok} 复核{review} 重复{dup} 失败{fail} ---")
        time.sleep(args.sleep + random.uniform(0, 6))
    log(f"=== xcf 回填结束: 成功 {ok} / 复核 {review} / 重复 {dup} / 失败 {fail} ===")


if __name__ == "__main__":
    main()
