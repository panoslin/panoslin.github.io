"""recipe 对象的 JSON Schema 校验(对齐用户现有 recipes.json + 两处扩展)。"""
from __future__ import annotations
import jsonschema

RECIPE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "title", "category", "imageUrl", "description",
                 "ingredients", "instructions", "nutrition", "source"],
    "properties": {
        "id": {"type": "integer", "minimum": 1},
        "title": {"type": "string", "minLength": 1},
        "category": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "imageUrl": {"type": "string"},
        "description": {"type": "string"},
        "ingredients": {
            "type": "array", "minItems": 1,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["name", "quantity", "unit"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    # 数值用量 或 字符串 "适量"
                    "quantity": {"oneOf": [{"type": "number"}, {"type": "string"}]},
                    "unit": {"type": "string"},
                },
            },
        },
        "instructions": {
            "type": "array", "minItems": 1,
            "items": {
                "oneOf": [
                    {"type": "string", "minLength": 1},
                    {
                        # imageUrl 可选: 你库里存在只有 text 的对象步骤(如 id=32)
                        "type": "object", "additionalProperties": False,
                        "required": ["text"],
                        "properties": {
                            "text": {"type": "string", "minLength": 1},
                            "imageUrl": {"type": "string", "minLength": 1},
                        },
                    },
                ]
            },
        },
        "nutrition": {
            "type": "object", "additionalProperties": False,
            "required": ["calories", "protein", "carbs", "fat", "salt"],
            "properties": {k: {"type": "number"} for k in
                           ["calories", "protein", "carbs", "fat", "salt"]},
        },
        "source": {"type": "string"},
    },
}

_validator = jsonschema.Draft7Validator(RECIPE_SCHEMA)


def validate(recipe: dict) -> list[str]:
    """返回错误信息列表;空列表 = 通过。"""
    errs = []
    for e in sorted(_validator.iter_errors(recipe), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errs.append(f"{loc}: {e.message}")
    # 业务规则:每个食材必须有数值用量或 "适量"
    for i, ing in enumerate(recipe.get("ingredients", [])):
        q = ing.get("quantity")
        if isinstance(q, str) and q != "适量":
            errs.append(f"ingredients/{i}/quantity: 字符串用量只允许 '适量', 实为 {q!r}")
    return errs
