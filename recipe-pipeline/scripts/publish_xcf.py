#!/usr/bin/env python3
"""把浏览器 harvester 采到的 data/xcf_harvest.jsonl 逐条发布为 PR。

每条 = {id,title,ings:[{name,amt}],steps:[{text,img}],cover,cats,desc,source}。
转成 recipe → finalize(图片热链 CDN,不下载)→ schema → 去重(source+标题)→ 每条单独 PR
(stacked 在抖音链尾之上,id 全局唯一)。可续跑(seen.json 记 xcf:<id>)。

用法: ./.venv/bin/python scripts/publish_xcf.py [--limit N]
监控: tail -f data/backfill_xcf.log
"""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from recipe_pipeline import config, xcf, merge, nutrition, schema, dedup, state  # noqa: E402

CLONE = os.path.join(config.DIRS["cache"], "clone")
REPO = "panoslin/panoslin.github.io"
LOG = os.path.join(config.DATA, "backfill_xcf.log")
HARVEST = os.path.join(config.DATA, "xcf_harvest.jsonl")
TRAILER = "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
# 导航/电器/标签噪声,不作为菜谱分类
_CAT_NOISE = {"菜谱分类", "菜谱", "视频菜谱", "作品", "作品动态", "菜单", "首页",
              "烤箱", "电饭煲", "料理机", "破壁机", "空气炸锅", "微波炉", "电压力锅",
              "烤箱菜", "面包机", "烤箱食谱", "更多"}


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


def wait_for_douyin_lock() -> None:
    lock = os.path.join(config.DIRS["cache"], "backfill.lock")
    while os.path.exists(lock):
        try:
            pid = int(open(lock).read().strip())
            os.kill(pid, 0)
            log(f"抖音回填(PID {pid})进行中,等待释放锁... 60s 后重试")
            time.sleep(60)
        except (ValueError, ProcessLookupError, PermissionError):
            log("陈旧锁,清除继续"); os.remove(lock); break


def record_to_draft(rec: dict) -> dict:
    ingredients = []
    for ing in rec.get("ings", []):
        q, u = xcf.split_amount(ing.get("amt", ""))
        ingredients.append({"name": ing["name"], "quantity": q, "unit": u})
    instructions = []
    for st in rec.get("steps", []):
        text = (st.get("text") or "").strip()
        img = st.get("img")
        if img:
            instructions.append({"text": text or "见图", "imageUrl": xcf._resize(img, 660)})
        elif text:
            instructions.append(text)
    cats = [c for c in dict.fromkeys(rec.get("cats") or []) if c and c not in _CAT_NOISE]
    category = cats[:3] if cats else xcf.classify(rec.get("title", ""))
    desc = re.sub(r"^【.*?】", "", (rec.get("desc") or "")).strip()[:140] or rec.get("title", "")
    cover = xcf._resize(rec.get("cover"), 800) if rec.get("cover") else None
    return {
        "title": rec["title"], "category": category, "description": desc,
        "ingredients": ingredients, "instructions": instructions,
        "_cover_url": cover, "source": rec["source"],
    }


def finalize(draft: dict, cfg: dict, recipes_existing: list[dict]):
    existing_ids = {r["id"] for r in recipes_existing if isinstance(r.get("id"), int)}
    rid = merge.next_id(recipes_existing)
    while rid in existing_ids:                 # id 唯一性硬保证
        rid += 1
    for ing in draft["ingredients"]:
        ing["quantity"] = merge.normalize_quantity(ing.get("quantity"))
    image_url = draft.get("_cover_url")
    if not image_url:                          # 无封面 → 退化用首个步骤图
        for s in draft["instructions"]:
            if isinstance(s, dict) and s.get("imageUrl"):
                image_url = s["imageUrl"]; break
    recipe = {
        "id": rid, "title": draft["title"], "category": draft["category"],
        "imageUrl": image_url or "", "description": draft["description"],
        "ingredients": draft["ingredients"], "instructions": draft["instructions"],
        "nutrition": nutrition.compute(draft["ingredients"], cfg),
        "source": draft["source"],
    }
    return recipe, rid


def publish(rec: dict, cfg: dict, seen: dict) -> str:
    rid_xcf = str(rec["id"])
    draft = record_to_draft(rec)
    if not draft["ingredients"] or not draft["instructions"]:
        raise ValueError("空食材/步骤")
    tip = current_tip()
    git("checkout", tip)
    recipes = json.load(open(os.path.join(CLONE, "recipes.json"), encoding="utf-8"))
    if any(r.get("source") == draft["source"] for r in recipes):
        state.mark(seen, f"xcf:{rid_xcf}", "seed", source=draft["source"]); state.save_seen(seen)
        log(f"  ↪ source 已存在跳过: {draft['title'][:24]}"); return "dup_source"
    recipe, rid = finalize(draft, cfg, recipes)
    errs = schema.validate(recipe)
    if errs:
        raise ValueError(f"schema 失败: {errs[:3]}")
    if dedup.find_title_dups(recipe["title"], recipes):
        state.mark(seen, f"xcf:{rid_xcf}", "review", source=recipe["source"]); state.save_seen(seen)
        json.dump({"recipe": recipe}, open(os.path.join(config.DIRS["failed"], f"xcf_{rid_xcf}.review.json"), "w"), ensure_ascii=False, indent=2)
        log(f"  ↪ 菜名疑重复 → review: {recipe['title'][:24]}"); return "review"
    assert not any(r.get("id") == rid for r in recipes), f"id {rid} 撞号!"
    branch = f"recipe-{rid}"
    git("checkout", "-b", branch)
    recipes.append(recipe)
    json.dump(recipes, open(os.path.join(CLONE, "recipes.json"), "w"), ensure_ascii=False, indent=2)
    git("add", "recipes.json")
    git("commit", "-m", f"feat(recipe): {rid} {recipe['title']}\n\n来源(下厨房): {recipe['source']}\n\nCo-Authored-By: Claude Fable 5 <noreply@anthropic.com>")
    git("push", "-u", "origin", branch)
    pr = subprocess.run(
        ["gh", "pr", "create", "-R", REPO, "--base", tip, "--head", branch,
         "--title", f"新增食谱:{recipe['title']} (id {rid})",
         "--body", f"由下厨房收藏夹增量管道自动抓取并结构化(图片热链下厨房 CDN)。\n来源: {recipe['source']}\n\n{TRAILER}"],
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
    args = ap.parse_args()
    cfg = config.load_config()
    config.ensure_dirs()
    if not os.path.exists(HARVEST):
        log("无 xcf_harvest.jsonl,先跑浏览器 harvester"); return

    # 去重读取(同一 id 可能被采多次,保留最后一条)
    recs = {}
    for ln in open(HARVEST, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            o = json.loads(ln)
        except Exception:
            continue
        if o.get("title") and o.get("id"):
            recs[str(o["id"])] = o
    items = list(recs.values())
    if args.limit:
        items = items[:args.limit]

    wait_for_douyin_lock()
    lock = os.path.join(config.DIRS["cache"], "backfill.lock")
    open(lock, "w").write(str(os.getpid()))
    import atexit
    atexit.register(lambda: os.path.exists(lock) and os.remove(lock))

    seen = state.load_seen()
    todo = [r for r in items if seen.get(f"xcf:{r['id']}", {}).get("status") not in ("done", "seed", "review", "dup_skip", "video_pending")]
    log(f"=== xcf 发布开始: 采到 {len(items)} 条, 待发布 {len(todo)} 条 ===")
    ok = fail = review = dup = 0
    for i, rec in enumerate(todo, 1):
        seen = state.load_seen()
        try:
            st = publish(rec, cfg, seen)
            ok += st == "done"; review += st == "review"; dup += st == "dup_source"
        except Exception as e:  # noqa: BLE001
            state.mark(seen, f"xcf:{rec['id']}", "failed", source=rec.get("source", "")); state.save_seen(seen)
            json.dump({"error": str(e)[:800]}, open(os.path.join(config.DIRS["failed"], f"xcf_{rec['id']}.json"), "w"), ensure_ascii=False)
            log(f"  ✗ {rec['id']} 失败: {str(e)[:140]}"); fail += 1
            git("checkout", "--", ".", check=False)
        if i % 10 == 0:
            log(f"--- 进度 {i}/{len(todo)} | 成功{ok} 复核{review} 重复{dup} 失败{fail} ---")
    log(f"=== xcf 发布结束: 成功 {ok} / 复核 {review} / 重复 {dup} / 失败 {fail} ===")


if __name__ == "__main__":
    main()
