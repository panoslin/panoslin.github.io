"""纯逻辑单元测试:schema 校验闸门、ASR 幻觉过滤、OCR 去重。"""
from __future__ import annotations
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from recipe_pipeline import schema
from recipe_pipeline.providers.asr_faster_whisper import _is_usable
from recipe_pipeline.providers.ocr_rapidocr import build_timeline


def test_schema_accepts_golden_sample():
    recipe = json.load(open(os.path.join(ROOT, "sample", "recipe_95.json"), encoding="utf-8"))
    assert schema.validate(recipe) == []


def test_schema_rejects_missing_field():
    bad = {"id": 1, "title": "x"}  # 缺一堆字段
    assert schema.validate(bad)


def test_schema_quantity_string_must_be_shiliang():
    recipe = json.load(open(os.path.join(ROOT, "sample", "recipe_95.json"), encoding="utf-8"))
    recipe["ingredients"].append({"name": "胡椒", "quantity": "一点点", "unit": ""})
    errs = schema.validate(recipe)
    assert any("适量" in e for e in errs), errs


def test_schema_allows_shiliang_and_object_steps():
    recipe = json.load(open(os.path.join(ROOT, "sample", "recipe_95.json"), encoding="utf-8"))
    # 样本里已含 "适量" 食材与 {text,imageUrl} 步骤
    assert any(i["quantity"] == "适量" for i in recipe["ingredients"])
    assert any(isinstance(s, dict) for s in recipe["instructions"])
    assert schema.validate(recipe) == []


def test_asr_hallucination_filtered():
    markers = ["请不吝点赞", "订阅", "打赏", "明镜", "点点栏目"]
    halluc = [{"start": 0.0, "end": 2.9, "text": "请不吝点赞 订阅 转发 打赏支持明镜与点点栏目"}]
    assert _is_usable(halluc, markers) is False


def test_asr_real_speech_usable():
    markers = ["请不吝点赞", "订阅", "打赏"]
    real = [{"start": 0.0, "end": 5.0, "text": "鸡胸肉三百克冷水下锅焯水撇去浮沫然后捞出放凉"},
            {"start": 5.0, "end": 9.0, "text": "加入老抽生抽蚝油盐糖玉米油拌匀倒入面包机"}]
    assert _is_usable(real, markers) is True


def test_ocr_timeline_dedup(monkeypatch):
    # 用同一句重复多帧 + 一句新句, 应去重为 2 条, 保留最早时间戳
    import recipe_pipeline.providers.ocr_rapidocr as o
    fake = {"a.jpg": ["鸡胸肉300克"], "b.jpg": ["鸡胸肉300克"], "c.jpg": ["料汁 老抽5g"]}
    monkeypatch.setattr(o, "ocr_image", lambda p: fake[os.path.basename(p)])
    tl = build_timeline([(0.5, "a.jpg"), (1.0, "b.jpg"), (2.0, "c.jpg")])
    assert [r["t"] for r in tl] == [0.5, 2.0]
    assert tl[0]["text"] == "鸡胸肉300克"


def test_state_new_ids_skips_seen_and_seed():
    from recipe_pipeline import state
    seen = {"a": {"status": "done"}, "b": {"status": "seed"}, "c": {"status": "failed"}}
    # a/b 已处理跳过; c 失败可重试; d 全新
    assert state.new_ids(["a", "b", "c", "d"], seen) == ["c", "d"]


def test_dedup_detects_similar_title():
    from recipe_pipeline import dedup
    existing = [{"id": 1, "title": "炝黄瓜🥒"}, {"id": 2, "title": "红烧肉"}]
    hits = dedup.find_title_dups("炝黄瓜", existing)
    assert hits and hits[0]["id"] == 1


def test_dedup_no_false_positive():
    from recipe_pipeline import dedup
    existing = [{"id": 1, "title": "红烧牛肉面"}, {"id": 2, "title": "可乐鸡翅"}]
    assert dedup.find_title_dups("面包机鸡胸肉松", existing) == []


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
