"""命令行入口:分阶段运行管道,便于测试与定时调度。

  python -m recipe_pipeline bundle    --aweme-id <id> [--caption ..] [--author ..]
  python -m recipe_pipeline structure --aweme-id <id>
  python -m recipe_pipeline finalize  --aweme-id <id> [--out path]
  python -m recipe_pipeline process-one --aweme-id <id> [--caption ..] [--author ..] [--out path]
"""
from __future__ import annotations
import argparse
import json
import os
import urllib.request

from . import config, schema, bundle as bundle_mod, structure as structure_mod, merge, dedup  # noqa: F401


def _ensure_recipes_json(cfg: dict) -> str:
    repo_dir = os.path.join(config.DIRS["cache"], "repo")
    os.makedirs(repo_dir, exist_ok=True)
    path = os.path.join(repo_dir, "recipes.json")
    if not os.path.exists(path):
        url = f"https://raw.githubusercontent.com/{cfg['repo']['slug']}/main/{cfg['repo']['recipes_json']}"
        urllib.request.urlretrieve(url, path)
    return path


def _load_bundle(aweme_id: str) -> dict:
    return json.load(open(os.path.join(config.work_dir(aweme_id), "bundle.json"), encoding="utf-8"))


def cmd_bundle(args, cfg):
    b = bundle_mod.build_bundle(args.aweme_id, caption=args.caption or "", author=args.author or "", cfg=cfg)
    print(f"bundle: ocr_timeline={len(b['ocr_timeline'])} 行, asr_usable={b['asr_usable']}, "
          f"keyframes={len(b['keyframes'])}")
    print(os.path.join(config.work_dir(args.aweme_id), "bundle.json"))


def cmd_structure(args, cfg):
    b = _load_bundle(args.aweme_id)
    draft = structure_mod.structure_bundle(b)
    out = os.path.join(config.work_dir(args.aweme_id), "draft.json")
    json.dump(draft, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"draft: title={draft.get('title')!r}, ingredients={len(draft.get('ingredients', []))}")
    print(out)


def cmd_finalize(args, cfg):
    draft = json.load(open(os.path.join(config.work_dir(args.aweme_id), "draft.json"), encoding="utf-8"))
    b = _load_bundle(args.aweme_id)
    recipes = json.load(open(_ensure_recipes_json(cfg), encoding="utf-8"))
    video = os.path.join(config.ROOT, b["video_path"])
    recipe = merge.finalize(draft, args.aweme_id, video, cfg, recipes, config.DIRS["images"])
    errs = schema.validate(recipe)
    # 菜名二次去重(防与历史食谱重复, 尤其 32 条无 source 的)
    dups = dedup.find_title_dups(recipe["title"], recipes)
    if dups:
        json.dump(dups, open(os.path.join(config.work_dir(args.aweme_id), "dedup.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    out = args.out or os.path.join(config.work_dir(args.aweme_id), "recipe.json")
    json.dump(recipe, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("校验:", "通过 ✓" if not errs else f"失败 ✗ {errs}")
    print("菜名去重:", "无重复 ✓" if not dups else f"⚠ 疑似重复 needs_review -> {[(d['id'], d['title']) for d in dups[:3]]}")
    print(out)
    return recipe, errs


def cmd_process_one(args, cfg):
    cmd_bundle(args, cfg)
    cmd_structure(args, cfg)
    return cmd_finalize(args, cfg)


def main():
    p = argparse.ArgumentParser(prog="recipe_pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("bundle", "structure", "finalize", "process-one"):
        sp = sub.add_parser(name)
        sp.add_argument("--aweme-id", required=True)
        sp.add_argument("--caption", default="")
        sp.add_argument("--author", default="")
        sp.add_argument("--out", default="")
    args = p.parse_args()
    cfg = config.load_config()
    {"bundle": cmd_bundle, "structure": cmd_structure,
     "finalize": cmd_finalize, "process-one": cmd_process_one}[args.cmd](args, cfg)


if __name__ == "__main__":
    main()
