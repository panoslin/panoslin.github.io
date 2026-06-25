"""给克隆仓库的 js/main.js 打 2 行护栏:让"适量"(非数值 quantity)在
份数缩放与营养贡献处不产生 NaN。幂等(已打过则跳过)。

用法: ./.venv/bin/python scripts/apply_frontend_guard.py [clone_dir]
"""
from __future__ import annotations
import os
import sys

CLONE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache", "clone")
MAIN_JS = os.path.join(CLONE, "js", "main.js")

GUARD1_ANCHOR = "        const originalQuantity = parseFloat(element.getAttribute('data-quantity'));\n        const unit = element.getAttribute('data-unit');\n"
GUARD1 = GUARD1_ANCHOR + "        if (isNaN(originalQuantity)) return; // 适量等非数值: 保持原样不缩放\n"

GUARD2_ANCHOR = "    const name = ingredient.name.trim();\n    const quantity = ingredient.quantity;\n    const unit = ingredient.unit;\n"
GUARD2 = GUARD2_ANCHOR + "    if (typeof quantity !== 'number') return 0; // 适量等非数值: 不计入营养贡献\n"


def main():
    src = open(MAIN_JS, encoding="utf-8").read()
    changed = []
    if "适量等非数值: 保持原样不缩放" not in src and GUARD1_ANCHOR in src:
        src = src.replace(GUARD1_ANCHOR, GUARD1, 1); changed.append("updatePortion 缩放护栏")
    if "适量等非数值: 不计入营养贡献" not in src and GUARD2_ANCHOR in src:
        src = src.replace(GUARD2_ANCHOR, GUARD2, 1); changed.append("calculateIngredientContribution 护栏")
    if changed:
        open(MAIN_JS, "w", encoding="utf-8").write(src)
        print("已打护栏:", changed)
    else:
        print("无需改动(已打过 或 未匹配锚点)")


if __name__ == "__main__":
    main()
