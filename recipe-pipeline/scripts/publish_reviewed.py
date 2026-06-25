#!/usr/bin/env python3
"""把人工复核判为 distinct(确为不同菜)的复核项发 PR。
从 data/review_verdicts.json 取 verdict=distinct 的条目,内容来源:
- 抖音: work_dir(aid)/draft.json + bundle.json(有视频可抽图)
- 下厨房文字: data/failed/xcf_<rid>.review.json(已 finalize 的 recipe)
每条单独 PR,stacked,id 全局唯一。强制跳过 dedup(已人工确认非重复)。

  ./.venv/bin/python scripts/publish_reviewed.py
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from recipe_pipeline import config, merge, schema, state  # noqa: E402

CLONE = os.path.join(config.DIRS["cache"], "clone")
REPO = "panoslin/panoslin.github.io"
TRAILER = "🤖 Generated with [Claude Code](https://claude.com/claude-code)"


def git(*a, check=True):
    return subprocess.run(["git", "-C", CLONE, *a], check=check, capture_output=True, text=True)


def current_tip() -> str:
    out = git("branch", "--list", "recipe-*", check=False).stdout
    ids = [int(m.group(1)) for ln in out.splitlines() if (m := re.search(r"recipe-(\d+)", ln))]
    return f"recipe-{max(ids)}" if ids else "main"


def next_unique_id(recipes):
    existing = {r["id"] for r in recipes if isinstance(r.get("id"), int)}
    rid = merge.next_id(recipes)
    while rid in existing:
        rid += 1
    return rid


def publish(key, cfg, seen):
    is_xcf = key.startswith("xcf:")
    tip = current_tip()
    git("checkout", tip)
    recipes = json.load(open(os.path.join(CLONE, "recipes.json"), encoding="utf-8"))

    if is_xcf:
        rid_x = key[4:]
        dump = json.load(open(os.path.join(config.DIRS["failed"], f"xcf_{rid_x}.review.json"), encoding="utf-8"))
        recipe = dump["recipe"]
        recipe["id"] = next_unique_id(recipes)               # 重新取号(避免与已发撞)
        for ing in recipe["ingredients"]:                    # 用量归一化
            ing["quantity"] = merge.normalize_quantity(ing.get("quantity"))
        src_label = "下厨房"
        local_imgs = []                                       # 图片热链 CDN,无本地文件
    else:
        wd = config.work_dir(key)
        draft = json.load(open(os.path.join(wd, "draft.json"), encoding="utf-8"))
        b = json.load(open(os.path.join(wd, "bundle.json"), encoding="utf-8"))
        video = os.path.join(ROOT, b["video_path"])
        recipe = merge.finalize(draft, key, video, cfg, recipes, os.path.join(CLONE, "images"))
        src_label = "抖音"
        local_imgs = [recipe["imageUrl"]] + [s["imageUrl"] for s in recipe["instructions"]
                                             if isinstance(s, dict) and s.get("imageUrl")]

    errs = schema.validate(recipe)
    if errs:
        raise ValueError(f"schema 失败: {errs[:3]}")
    rid = recipe["id"]
    assert not any(r.get("id") == rid for r in recipes), f"id {rid} 撞号!"

    branch = f"recipe-{rid}"
    git("checkout", "-b", branch)
    recipes.append(recipe)
    json.dump(recipes, open(os.path.join(CLONE, "recipes.json"), "w"), ensure_ascii=False, indent=2)
    git("add", "recipes.json")
    for f in local_imgs:
        git("add", f, check=False)
    git("commit", "-m", f"feat(recipe): {rid} {recipe['title']}\n\n来源({src_label},人工复核确认非重复): {recipe['source']}\n\nCo-Authored-By: Claude Fable 5 <noreply@anthropic.com>")
    git("push", "-u", "origin", branch)
    pr = subprocess.run(
        ["gh", "pr", "create", "-R", REPO, "--base", tip, "--head", branch,
         "--title", f"新增食谱:{recipe['title']} (id {rid})",
         "--body", f"复核项经人工对比食材/用量/做法,确认与库内同名条目实为不同菜,故收录。\n来源: {recipe['source']}\n\n{TRAILER}"],
        cwd=CLONE, capture_output=True, text=True)
    prurl = (pr.stdout or pr.stderr).strip().splitlines()[-1] if (pr.stdout or pr.stderr) else "?"
    state.mark(seen, key, "done", recipe_id=rid, source=recipe["source"])
    seen[key]["pr"] = prurl
    state.save_seen(seen)
    print(f"  ✓ id={rid} {recipe['title'][:22]} PR={prurl}", flush=True)
    return prurl


def main():
    cfg = config.load_config()
    config.ensure_dirs()
    lock = os.path.join(config.DIRS["cache"], "backfill.lock")
    if os.path.exists(lock):
        print("有回填进行中(锁存在),退出避免抢 git"); return
    open(lock, "w").write(str(os.getpid()))
    import atexit
    atexit.register(lambda: os.path.exists(lock) and os.remove(lock))

    verdicts = json.load(open(os.path.join(config.DATA, "review_verdicts.json"), encoding="utf-8"))
    dist = [x for x in verdicts if x["verdict"] == "distinct"]
    seen = state.load_seen()
    print(f"=== 发布 distinct 复核项: {len(dist)} 条 ===")
    ok = fail = 0
    for x in dist:
        key = x["key"]
        if seen.get(key, {}).get("status") == "done":
            print(f"  - 已发, 跳过 {x['title'][:20]}"); continue
        try:
            publish(key, cfg, seen); ok += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {x['title'][:20]} 失败: {str(e)[:140]}"); fail += 1
            git("checkout", "--", ".", check=False)
    print(f"=== 完成: 成功 {ok} / 失败 {fail} ===")


if __name__ == "__main__":
    main()
