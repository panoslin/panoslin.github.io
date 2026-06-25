"""营养计算:复用用户仓库的 calculate_nutrition.py + nutrition_db.json(口径一致)。"""
from __future__ import annotations
import contextlib
import importlib.util
import os
import urllib.request

from . import config

_MOD = None


@contextlib.contextmanager
def _chdir(path: str):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def _cache_repo_files(cfg: dict) -> str:
    repo_dir = os.path.join(config.DIRS["cache"], "repo")
    os.makedirs(repo_dir, exist_ok=True)
    targets = {
        "calculate_nutrition.py": cfg["nutrition"]["calc_script_url"],
        "nutrition_db.json": cfg["nutrition"]["db_url"],
    }
    for name, url in targets.items():
        dest = os.path.join(repo_dir, name)
        if not os.path.exists(dest):
            urllib.request.urlretrieve(url, dest)
    return repo_dir


def _get_module(cfg: dict):
    global _MOD
    if _MOD is None:
        repo_dir = _cache_repo_files(cfg)
        script = os.path.join(repo_dir, "calculate_nutrition.py")
        spec = importlib.util.spec_from_file_location("user_calc_nutrition", script)
        mod = importlib.util.module_from_spec(spec)
        with _chdir(repo_dir):  # 模块加载时从 cwd 读 nutrition_db.json
            spec.loader.exec_module(mod)
        _MOD = mod
    return _MOD


def compute(ingredients: list[dict], cfg: dict | None = None) -> dict:
    """对 ingredients 计算整份营养。非数值('适量')项由脚本 try/except 自动跳过。"""
    cfg = cfg or config.load_config()
    mod = _get_module(cfg)
    return mod.calculate_recipe_nutrition({"ingredients": ingredients})
