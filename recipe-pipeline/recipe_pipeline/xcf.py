"""下厨房(xiachufang)菜谱抓取与解析。

要点(均经真实页验证):
- 单个菜谱页 `/recipe/<id>/` 是**公开**的,无需登录;但站点按 TLS 指纹封锁普通客户端
  (urllib/curl 返回 404/418),用 curl_cffi 的 `impersonate="chrome"` 可正常 200。
- 标题 = `h1`;封面 = `meta[property=og:image]`(带 CDN 缩放参数,需重写宽度);
  食材 = `.ings tr` 内 `.name`/`.unit`;步骤 = `.steps li` 内 `.text` + `img`。
"""
from __future__ import annotations
import re
import time

from curl_cffi import requests as cr
from bs4 import BeautifulSoup

IMPERSONATE = "chrome"
BASE = "https://www.xiachufang.com"


class CaptchaError(RuntimeError):
    """命中下厨房的频率验证码('滑动验证'页)。"""


def is_captcha(html: str) -> bool:
    # 验证码页极小(~4.4KB)、标题"滑动验证"、无菜谱 h1
    return ("滑动验证" in html[:3000]) and (len(html) < 8000)

# 标题关键词 → 粗分类(下厨房页面无可靠分类字段,按标题就近归类,优于固定单值)
_CAT_RULES = [
    (("吐司", "面包", "蛋糕", "饼干", "曲奇", "可颂", "贝果", "马芬", "蛋挞", "司康", "泡芙", "排包", "欧包"), "烘焙"),
    (("慕斯", "布丁", "冰淇淋", "雪糕", "果冻", "甜品", "提拉米苏", "班戟", "舒芙蕾"), "甜品"),
    (("茶", "咖啡", "奶昔", "果汁", "饮", "奶茶", "气泡", "特调", "拿铁"), "饮品"),
    (("汤", "羹", "煲", "粥"), "汤羹"),
    (("鸡", "鸭", "牛", "猪", "羊", "鱼", "虾", "蟹", "排骨", "肉", "培根", "香肠", "五花", "鸡蛋羹"), "荤菜"),
    (("面", "饭", "馒头", "包子", "饺", "馄饨", "年糕", "米线", "河粉", "炒粉", "焖饭", "盖饭"), "主食"),
    (("沙拉", "凉拌", "素", "菇", "豆腐", "茄", "瓜", "菜", "笋"), "素菜"),
    (("酱", "卤", "腌", "泡菜", "辣椒油"), "酱料腌菜"),
]


def classify(title: str) -> list[str]:
    t = title or ""
    for kws, cat in _CAT_RULES:
        if any(k in t for k in kws):
            return [cat]
    return ["其他"]


def split_amount(raw: str):
    """'250克' -> (250,'克'); '2个' -> (2,'个'); '适量' -> ('适量',''); '少许' -> ('适量','少许')。
    保证 quantity 满足 schema(数字 或 '适量'),描述性用量保留在 unit 里。"""
    raw = (raw or "").strip()
    if not raw or raw in ("适量", "随意", "随喜", "按需", "各适量"):
        return "适量", ""
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(.*)$", raw)
    if m:
        v = float(m.group(1))
        return (int(v) if v.is_integer() else v), m.group(2).strip()
    return "适量", raw  # 半个/一把/少许 等纯文字:数量记"适量",原文作单位


def _resize(url: str, w: int) -> str | None:
    """重写下厨房 CDN 缩放参数到指定宽度(原 url 常带 ?imageView2/1/w/280/)。"""
    if not url:
        return None
    base = url.split("?")[0]
    return f"{base}?imageView2/1/w/{w}"


def fetch(rid: str, retries: int = 3) -> str:
    last = None
    for i in range(retries):
        try:
            r = cr.get(f"{BASE}/recipe/{rid}/", impersonate=IMPERSONATE, timeout=25,
                       headers={"Referer": BASE + "/", "Accept-Language": "zh-CN,zh;q=0.9"})
            if r.status_code == 200:
                if is_captcha(r.text):
                    raise CaptchaError(f"recipe {rid} 命中滑动验证")
                return r.text
            last = f"HTTP {r.status_code}"
        except CaptchaError:
            raise
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        time.sleep(2 + i * 2)
    raise RuntimeError(f"fetch {rid} 失败: {last}")


def parse(rid: str, html: str) -> dict:
    """解析为 draft(字段对齐 recipe,图片为远端 URL,封面待下载)。"""
    s = BeautifulSoup(html, "lxml")
    h1 = s.select_one("h1")
    title = h1.get_text(strip=True) if h1 else ""
    if not title:
        raise ValueError("无标题(可能非菜谱页/已下架)")

    ingredients = []
    for tr in s.select(".ings tr"):
        nm = tr.select_one(".name")
        un = tr.select_one(".unit")
        name = nm.get_text(strip=True) if nm else ""
        if not name:
            continue
        q, u = split_amount(un.get_text(strip=True) if un else "")
        ingredients.append({"name": name, "quantity": q, "unit": u})

    instructions = []
    for li in s.select(".steps li"):
        t = li.select_one(".text")
        img = li.select_one("img")
        text = t.get_text(strip=True) if t else ""
        if not text and not (img and img.has_attr("src")):
            continue
        if img and img.has_attr("src"):
            instructions.append({"text": text or "见图", "imageUrl": _resize(img["src"], 660)})
        else:
            instructions.append(text)

    og = s.select_one('meta[property="og:image"]')
    cover = _resize(og["content"], 800) if (og and og.has_attr("content")) else None

    dm = s.select_one('meta[name="description"]')
    desc = (dm["content"].strip() if (dm and dm.has_attr("content")) else "")
    desc = re.sub(r"^【.*?】", "", desc).strip()[:140] or title

    return {
        "title": title,
        "category": classify(title),
        "description": desc,
        "ingredients": ingredients,
        "instructions": instructions,
        "_cover_url": cover,
        "source": f"{BASE}/recipe/{rid}/",
    }


def download_image(url: str, dst: str) -> bool:
    try:
        r = cr.get(url, impersonate=IMPERSONATE, timeout=30,
                   headers={"Referer": BASE + "/"})
        if r.status_code == 200 and r.content:
            with open(dst, "wb") as f:
                f.write(r.content)
            return True
    except Exception:  # noqa: BLE001
        pass
    return False
