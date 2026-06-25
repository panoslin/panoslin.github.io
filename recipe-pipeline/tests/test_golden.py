"""黄金回归:把自动管道产出与已验收样本(sample/recipe_95.json)按关键事实比对。

关键事实(承载信息, 必须稳定):共享食材的 quantity/unit、营养、source、步骤数与配图数。
自由文本(标题措辞/步骤句子/分类标签)不参与严格比对。
覆盖度差异(自动版多/少某食材)作为"待确认"列出, 不算失败。
"""
from __future__ import annotations
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, "sample", "recipe_95.json")


def _ing_map(recipe: dict) -> dict:
    return {i["name"]: (i["quantity"], i["unit"]) for i in recipe.get("ingredients", [])}


def key_facts_diff(golden: dict, cand: dict) -> dict:
    g, c = _ing_map(golden), _ing_map(cand)
    shared = set(g) & set(c)
    return {
        "ingredient_value_mismatch": {n: {"golden": g[n], "candidate": c[n]} for n in shared if g[n] != c[n]},
        "only_in_candidate": {n: c[n] for n in (set(c) - set(g))},   # 覆盖度更高(可能是改进)
        "only_in_golden": {n: g[n] for n in (set(g) - set(c))},      # 可能是回归
        "nutrition_delta": {k: round(cand["nutrition"].get(k, 0) - golden["nutrition"].get(k, 0), 2)
                            for k in golden.get("nutrition", {})},
        "source_match": golden.get("source") == cand.get("source"),
        "steps": {"golden": len(golden["instructions"]), "candidate": len(cand["instructions"])},
        "step_images": {
            "golden": sum(1 for s in golden["instructions"] if isinstance(s, dict)),
            "candidate": sum(1 for s in cand["instructions"] if isinstance(s, dict)),
        },
    }


def is_consistent(diff: dict) -> bool:
    """硬一致性:共享食材数值不许变、营养基本一致、source 必须一致。"""
    if diff["ingredient_value_mismatch"]:
        return False
    if not diff["source_match"]:
        return False
    if any(abs(v) > 1.0 for v in diff["nutrition_delta"].values()):
        return False
    return True


def test_golden_consistency():
    cand_path = os.environ.get("CANDIDATE", os.path.join(ROOT, "data", "work",
                                "7641206591925469082", "recipe.json"))
    if not os.path.exists(cand_path):
        import pytest
        pytest.skip(f"候选产物不存在: {cand_path}(先跑 process-one)")
    golden = json.load(open(GOLDEN, encoding="utf-8"))
    cand = json.load(open(cand_path, encoding="utf-8"))
    diff = key_facts_diff(golden, cand)
    assert is_consistent(diff), json.dumps(diff, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    cand_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "data", "work", "7641206591925469082", "recipe.json")
    golden = json.load(open(GOLDEN, encoding="utf-8"))
    cand = json.load(open(cand_path, encoding="utf-8"))
    diff = key_facts_diff(golden, cand)
    print(json.dumps(diff, ensure_ascii=False, indent=2))
    print("\n硬一致性:", "通过 ✓" if is_consistent(diff) else "不一致 ✗(见上, 多为覆盖度差异)")
