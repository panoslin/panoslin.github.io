#!/usr/bin/env python3
"""下厨房「视频菜谱」回填:对已下载到 data/xcf_videos/<rid>.mp4 的视频,
复用抖音多模态管道(帧+ASR+OCR+Claude 结构化)提取食材用量/步骤,每条单独 PR。

与抖音的区别:① 视频是本地文件(跳过下载);② source/title 用下厨房页面的权威值;
③ seen.json 用 xcf:<rid>;④ stacked 在现有链尾,id 全局唯一。
串行 + 等锁(不与其它回填并发)。可续跑。耗额度(每条一次 Claude 结构化),宜后台跑。

  ./.venv/bin/python scripts/backfill_xcf_video.py [--limit N]
监控: tail -f data/backfill_xcf.log
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from recipe_pipeline import config, frames, merge, schema, dedup, state, structure as structure_mod  # noqa: E402
from recipe_pipeline.providers import asr_faster_whisper as asr  # noqa: E402
from recipe_pipeline.providers import ocr_rapidocr as ocr  # noqa: E402

CLONE = os.path.join(config.DIRS["cache"], "clone")
REPO = "panoslin/panoslin.github.io"
LOG = os.path.join(config.DATA, "backfill_xcf.log")
VIDDIR = os.path.join(config.DATA, "xcf_videos")
HARVEST = os.path.join(config.DATA, "xcf_harvest.jsonl")
TRAILER = "🤖 Generated with [Claude Code](https://claude.com/claude-code)"


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def git(*args, check=True):
    return subprocess.run(["git", "-C", CLONE, *args], check=check, capture_output=True, text=True)


def current_tip() -> str:
    import re
    out = git("branch", "--list", "recipe-*", check=False).stdout
    ids = [int(m.group(1)) for ln in out.splitlines() if (m := re.search(r"recipe-(\d+)", ln))]
    return f"recipe-{max(ids)}" if ids else "main"


def wait_for_lock() -> None:
    lock = os.path.join(config.DIRS["cache"], "backfill.lock")
    while os.path.exists(lock):
        try:
            pid = int(open(lock).read().strip()); os.kill(pid, 0)
            log(f"其它回填(PID {pid})持锁,等待... 60s"); time.sleep(60)
        except (ValueError, ProcessLookupError, PermissionError):
            log("陈旧锁,清除"); os.remove(lock); break


def build_bundle_local(rid: str, video: str, caption: str, source: str, cfg: dict) -> dict:
    """与 bundle.build_bundle 同,但视频是本地文件(跳过下载),source 用下厨房 URL。"""
    wdir = config.work_dir(f"xcf_{rid}")
    duration = frames.probe_duration(video)
    wav = frames.extract_audio(video, wdir)
    transcript, asr_usable = asr.transcribe(wav, cfg)
    fcfg = cfg["frames"]
    dense = frames.dense_frames(video, wdir, fps=fcfg["ocr_fps"], height=fcfg["ocr_height"])
    timeline = ocr.build_timeline(dense)
    bundle = {
        "aweme_id": f"xcf_{rid}", "source": source, "title_caption": caption, "author": "",
        "duration": duration, "ocr_timeline": timeline, "transcript": transcript,
        "asr_usable": asr_usable,
        "keyframes": [{"t": t, "path": os.path.relpath(p, config.ROOT)} for t, p in dense],
        "video_path": os.path.relpath(video, config.ROOT),
    }
    json.dump(bundle, open(os.path.join(wdir, "bundle.json"), "w"), ensure_ascii=False, indent=2)
    return bundle


def load_meta() -> dict:
    """从 harvest jsonl 取下厨房标题/描述/封面/source(权威值)。"""
    meta = {}
    for ln in open(HARVEST, encoding="utf-8"):
        try:
            o = json.loads(ln)
        except Exception:
            continue
        if o.get("id"):
            meta[str(o["id"])] = o
    return meta


def process_one(rid: str, meta: dict, cfg: dict, seen: dict) -> str:
    video = os.path.join(VIDDIR, f"{rid}.mp4")
    if not os.path.exists(video):
        raise FileNotFoundError(f"无本地视频 {video}")
    m = meta.get(rid, {})
    xcf_title = m.get("title", "").strip()
    xcf_source = m.get("source", f"https://www.xiachufang.com/recipe/{rid}/")
    caption = f"{xcf_title}。{m.get('desc','')}".strip("。")

    b = build_bundle_local(rid, video, caption, xcf_source, cfg)
    draft = structure_mod.structure_bundle(b)
    # 用下厨房页面的权威标题/来源覆盖(食材/步骤来自视频结构化)
    if xcf_title:
        draft["title"] = xcf_title
    draft["source"] = xcf_source

    tip = current_tip()
    git("checkout", tip)
    recipes = json.load(open(os.path.join(CLONE, "recipes.json"), encoding="utf-8"))
    if any(r.get("source") == xcf_source for r in recipes):
        state.mark(seen, f"xcf:{rid}", "seed", source=xcf_source); state.save_seen(seen)
        return "dup_source"
    recipe = merge.finalize(draft, f"xcf_{rid}", os.path.join(ROOT, b["video_path"]), cfg, recipes, os.path.join(CLONE, "images"))
    errs = schema.validate(recipe)
    if errs:
        raise ValueError(f"schema 失败: {errs[:3]}")
    if dedup.find_title_dups(recipe["title"], recipes):
        state.mark(seen, f"xcf:{rid}", "review", source=xcf_source); state.save_seen(seen)
        log(f"  ↪ 菜名疑重复 → review: {recipe['title'][:24]}"); return "review"
    rid_new = recipe["id"]
    assert not any(r.get("id") == rid_new for r in recipes), f"id {rid_new} 撞号!"
    branch = f"recipe-{rid_new}"
    git("checkout", "-b", branch)
    recipes.append(recipe)
    json.dump(recipes, open(os.path.join(CLONE, "recipes.json"), "w"), ensure_ascii=False, indent=2)
    git("add", "recipes.json", recipe["imageUrl"])
    for s in recipe["instructions"]:
        if isinstance(s, dict) and s.get("imageUrl"):
            git("add", s["imageUrl"], check=False)
    git("commit", "-m", f"feat(recipe): {rid_new} {recipe['title']}\n\n来源(下厨房视频): {xcf_source}\n\nCo-Authored-By: Claude Fable 5 <noreply@anthropic.com>")
    git("push", "-u", "origin", branch)
    pr = subprocess.run(
        ["gh", "pr", "create", "-R", REPO, "--base", tip, "--head", branch,
         "--title", f"新增食谱:{recipe['title']} (id {rid_new})",
         "--body", f"由下厨房收藏夹「视频菜谱」自动抓取:视频经 ASR+OCR+Claude 结构化提取用量与步骤。\n来源: {xcf_source}\n\n{TRAILER}"],
        cwd=CLONE, capture_output=True, text=True)
    prurl = (pr.stdout or pr.stderr).strip().splitlines()[-1] if (pr.stdout or pr.stderr) else "?"
    state.mark(seen, f"xcf:{rid}", "done", recipe_id=rid_new, source=xcf_source)
    seen[f"xcf:{rid}"]["pr"] = prurl
    state.save_seen(seen)
    log(f"  ✓ id={rid_new} {recipe['title'][:24]} PR={prurl}")
    return "done"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    cfg = config.load_config()
    config.ensure_dirs()
    meta = load_meta()
    vids = sorted(f[:-4] for f in os.listdir(VIDDIR) if f.endswith(".mp4"))
    seen = state.load_seen()
    todo = [r for r in vids if seen.get(f"xcf:{r}", {}).get("status") not in ("done", "seed", "review", "dup_skip", "video_pending")]
    if args.limit:
        todo = todo[:args.limit]

    wait_for_lock()
    lock = os.path.join(config.DIRS["cache"], "backfill.lock")
    open(lock, "w").write(str(os.getpid()))
    import atexit
    atexit.register(lambda: os.path.exists(lock) and os.remove(lock))

    log(f"=== xcf 视频回填开始: 待处理 {len(todo)} 条 ===")
    ok = fail = review = dup = 0
    for i, rid in enumerate(todo, 1):
        seen = state.load_seen()
        log(f"[{i}/{len(todo)}] xcf视频 {rid} ...")
        try:
            st = process_one(rid, meta, cfg, seen)
            ok += st == "done"; review += st == "review"; dup += st == "dup_source"
        except Exception as e:  # noqa: BLE001
            state.mark(seen, f"xcf:{rid}", "failed", source=f"https://www.xiachufang.com/recipe/{rid}/"); state.save_seen(seen)
            json.dump({"error": str(e)[:800]}, open(os.path.join(config.DIRS["failed"], f"xcfvid_{rid}.json"), "w"), ensure_ascii=False)
            log(f"  ✗ {rid} 失败: {str(e)[:160]}"); fail += 1
            git("checkout", "--", ".", check=False)
    log(f"=== xcf 视频回填结束: 成功 {ok} / 复核 {review} / 重复 {dup} / 失败 {fail} ===")


if __name__ == "__main__":
    main()
