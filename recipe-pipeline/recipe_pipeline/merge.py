"""把结构化草稿最终化为完整 recipe:分配 id、算营养、抽封面/步骤图、合并。"""
from __future__ import annotations
import json
import os
import re
import shutil

from . import config, frames, nutrition


def next_id(recipes: list[dict]) -> int:
    ids = [r["id"] for r in recipes if isinstance(r.get("id"), int)]
    return (max(ids) + 1) if ids else 1


def normalize_quantity(q):
    """把结构化产出的 quantity 归一化为 schema(schema.py:66-69)允许的形式:数字 或 '适量'。
    - 数字 → 原样;'适量'/空 → '适量'
    - 区间('4-5'/'2~3'/'4-5个')→ 取第一个数字(下界),整数则转 int
    - 纯文字('少许'/'半个'等无数字)→ '适量'
    同时避免 nutrition.compute 遇到非数字字符串报错(merge.py:52)。"""
    if isinstance(q, bool):  # 防 True/False 被当数字
        return "适量"
    if isinstance(q, (int, float)):
        return q
    if not isinstance(q, str):
        return "适量"
    s = q.strip()
    if s == "" or s == "适量":
        return "适量"
    m = re.search(r"\d+(?:\.\d+)?", s)
    if m:
        v = float(m.group())
        return int(v) if v.is_integer() else v
    return "适量"


def finalize(draft: dict, aweme_id: str, video_path: str, cfg: dict,
             recipes_existing: list[dict], images_out: str) -> dict:
    """draft(来自结构化, 含 _meta) → 完整 recipe(已校验前的对象)。同时抽出图片到 images_out。"""
    os.makedirs(images_out, exist_ok=True)
    rid = next_id(recipes_existing)
    meta = draft.get("_meta", {})
    duration = frames.probe_duration(video_path) if os.path.exists(video_path) else 0.0

    # 封面
    cover_t = meta.get("cover_frame")
    if cover_t is None:
        cover_t = round(duration * 0.92, 1) if duration else 1.0
    cover_name = f"recipe_{rid}.png"
    frames.grab_frame(video_path, float(cover_t), os.path.join(images_out, cover_name))
    image_url = f"images/{cover_name}"

    # 步骤图:把对象步骤的 imageUrl 重写为 recipe_<id>_step_<n>.png 并抽帧
    step_frames = {str(k): v for k, v in (meta.get("step_image_frames") or {}).items()}
    instructions = []
    for idx, step in enumerate(draft["instructions"], start=1):
        if isinstance(step, dict):
            name = f"recipe_{rid}_step_{idx}.png"
            t = step_frames.get(str(idx))
            if t is not None:
                frames.grab_frame(video_path, float(t), os.path.join(images_out, name))
            instructions.append({"text": step["text"], "imageUrl": f"images/{name}"})
        else:
            instructions.append(step)

    # 归一化用量(区间→下界数字、文字→"适量"),保证营养计算与 schema 校验都不挂
    for ing in draft.get("ingredients", []):
        if isinstance(ing, dict):
            ing["quantity"] = normalize_quantity(ing.get("quantity"))

    recipe = {
        "id": rid,
        "title": draft["title"],
        "category": draft["category"],
        "imageUrl": image_url,
        "description": draft["description"],
        "ingredients": draft["ingredients"],
        "instructions": instructions,
        "nutrition": nutrition.compute(draft["ingredients"], cfg),
        "source": draft["source"],
    }
    return recipe


def append_to_recipes(recipe: dict, recipes_path: str) -> None:
    with open(recipes_path, "r", encoding="utf-8") as f:
        recipes = json.load(f)
    recipes.append(recipe)
    tmp = recipes_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)
    os.replace(tmp, recipes_path)


def _recipe_image_paths(recipe: dict) -> list[str]:
    """recipe 里引用的所有图片相对路径(imageUrl + 步骤图)。"""
    paths = [recipe["imageUrl"]]
    for s in recipe["instructions"]:
        if isinstance(s, dict) and s.get("imageUrl"):
            paths.append(s["imageUrl"])
    return paths


def merge_into_clone(recipe: dict, clone_dir: str, images_src: str) -> dict:
    """把 recipe 合并进 clone_dir/recipes.json 并拷图。按 id 与 source 防重。
    返回 {status: merged|skipped_dup, ...}。"""
    recipes_path = os.path.join(clone_dir, "recipes.json")
    recipes = json.load(open(recipes_path, encoding="utf-8"))
    if any(r.get("id") == recipe["id"] for r in recipes):
        return {"status": "skipped_dup", "reason": f"id {recipe['id']} 已存在"}
    if recipe.get("source") and any(r.get("source") == recipe["source"] for r in recipes):
        return {"status": "skipped_dup", "reason": "source 已存在"}
    # 拷图
    dst_dir = os.path.join(clone_dir, "images")
    os.makedirs(dst_dir, exist_ok=True)
    copied = []
    for rel in _recipe_image_paths(recipe):
        src = os.path.join(images_src, os.path.basename(rel))
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(clone_dir, rel))
            copied.append(rel)
    append_to_recipes(recipe, recipes_path)
    return {"status": "merged", "id": recipe["id"], "images": copied}
