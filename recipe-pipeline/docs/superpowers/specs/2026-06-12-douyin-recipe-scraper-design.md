# 抖音「菜谱」收藏夹增量爬取与结构化管道 — 设计 Spec

- 日期: 2026-06-12
- 状态: 已通过单条样本(id=95)验证,进入实现
- 黄金用例: 抖音视频 `7641206591925469082`(「面包机鸡胸肉松」),手工产出已被用户验收,见 `sample/recipe_95.json`

## 1. 目标

把用户抖音账号里名为 **「菜谱」** 的自定义收藏夹中的食谱视频,**增量**抓取并结构化,**合并进**用户的 GitHub Pages 仓库 `panoslin/panoslin.github.io` 根目录的 `recipes.json`。每条食谱包含:原链接、食材(尽量精确到克/毫升)、制作步骤(关键步骤附截图)、营养、封面图。

- 收藏夹入口: `https://www.douyin.com/user/self?showSubTab=favorite_folder&showTab=favorite_collection` → 「菜谱」夹(验证时 314 个视频)。
- 运行模式: **方案 1**——Claude Code 编排(交互式先跑通),再用**本地 cron 每天 10:00** 触发**无头 `claude -p`** 周期跑(用 claude-in-chrome)。

## 2. 输出契约(必须严格对齐用户现有 `recipes.json`)

顶层是 JSON 数组。每条 9 个字段,key 集合必须与现有条目完全一致:

```jsonc
{
  "id": 95,                               // 整数, 递增 = 现有 max + 1
  "title": "面包机鸡胸肉松🍗",            // 可带 emoji
  "category": ["中餐", "下饭菜"],         // 1-2 个中文标签, 取自现有词表
  "imageUrl": "images/recipe_95.png",     // 仓库内相对路径; 命名 recipe_<id>.png
  "description": "…的详细制作方法",       // 主流模板 "<标题>的详细制作方法"
  "ingredients": [
    {"name": "鸡胸肉", "quantity": 300, "unit": "克"},   // 有量: quantity 数字, unit 中文(克/毫升为主)
    {"name": "黑芝麻", "quantity": "适量", "unit": ""}    // 无精确量: quantity = "适量", unit = ""
  ],
  "instructions": [
    "纯文字步骤",                                          // 普通步骤: 字符串
    {"text": "技法步骤", "imageUrl": "images/recipe_95_step_3.png"}  // 图像化细节动作: {text, imageUrl}
  ],
  "nutrition": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0, "salt": 0},  // 整份总量
  "source": "https://www.douyin.com/video/<aweme_id>"     // 抖音原链接(长链, 含 id 便于去重)
}
```

**两处 schema 扩展(前端已部分支持,证据见下)**:
- `instructions` 元素可为字符串**或** `{text, imageUrl}`。前端 `js/main.js:1152-1166` 已兼容两种格式 → **零前端改动**。仅给"偏图像化的细节动作"(技法/状态)配图,普通步骤保持纯文字。
- `ingredient.quantity` 可为数字**或** `"适量"`(unit 留 `""`)。前端展示 `js/main.js:1141` 直接拼接 → 显示"适量"。**但**份数缩放 `main.js:1377` 与营养贡献分解 `main.js:2586` 对非数值会算出 `NaN`,需 2 行护栏(见 §6)。离线 `calculate_nutrition.py:223-232` 已 try/except 安全跳过。

## 3. 架构

```
触发: 你说"更新菜谱"  /  cron 每天 10:00 → claude -p
  └── Claude Code(编排 + 结构化大脑; 交互或无头同一个)
        1) claude-in-chrome 打开「菜谱」夹 → 滚动 → 抓 [aweme_id, url, 文案, 作者] → data/queue/harvested.json
        2) 调确定性 Python 内核处理每个"新" aweme:
        3) 读 work/<id>/bundle.json → 按"结构化契约"(prompts/structuring.md)融合 → 产出 schema JSON
        4) 校验 → 合并进 recipes.json + 拷图进 images/ → (可选)提交推送
  └── 确定性 Python 内核 `python -m recipe_pipeline`(无 LLM 依赖, 可单测):
        download(yt-dlp) → frames(ffmpeg 密集 2fps) → ocr(RapidOCR) → asr(faster-whisper)
        → nutrition(复用用户 calculate_nutrition.py) → schema 校验 → 合并/写文件 → 状态
```

**两个文件边界**(使内核可脱离浏览器/模型测试):浏览器→内核用 `harvested.json`;内核→Claude 用 `bundle.json`。

**智能层 = Claude Code 本身**(不接独立 LLM API)。结构化规则写死在 `prompts/structuring.md`,交互跑由当前 agent 执行,cron 跑由 `claude -p "$(cat prompts/structuring.md ...)"` 执行 —— 同模型、同提示词、同工具。

## 4. 处理流水线(单个视频)

1. **下载**: `yt-dlp`(公开视频无需 cookie;私有/区域限制再加 `--cookies-from-browser chrome`)。HEVC/720p 实测可下,6MB 量级。
2. **抽帧**: ffmpeg **密集均匀 2 帧/秒**(用于 OCR,**不靠场景切变**——场景切变会漏字幕,见 §6 黄金案例);另抽封面帧与候选步骤帧。
3. **OCR**: RapidOCR(PaddleOCR 模型的 ONNX 版,onnxruntime 已随 faster-whisper 装好;质量等同、装起来省心)。逐帧识别 → **按归一化文本去重**(同句只留最早时间戳),得"画面字幕时间线"。
4. **ASR**: faster-whisper(`medium`,中文,`vad_filter`,`initial_prompt` 注入"克/毫升/勺/适量"偏置)。**注意**:纯 BGM 无人声视频会出 whisper 幻觉(如"请点赞订阅"),需识别并丢弃 → 这类视频靠 OCR(本黄金案例即如此)。
5. **融合/结构化(Claude Code)**: 读 `bundle.json`(文案 + OCR 时间线 + 转写 + 关键帧路径),按 `prompts/structuring.md` 产出 schema JSON。含**完整性补抽**:画面在加调料却没抓到用量 → 对该时间戳加密抽帧(如 5fps)重 OCR 再判。
6. **营养**: 复用用户 `calculate_nutrition.py` + `nutrition_db.json`(只喂数值食材,"适量"项自动跳过),口径与现有 94 条一致。
7. **校验 + 合并**: jsonschema 硬校验通过 → `id = max+1`、拷封面/步骤图进 `images/recipe_<id>*.png` → append 进 `recipes.json`(原子写)。失败 → `data/failed/<id>.json` 重试。

## 5. 增量与去重

- 真值来源 = 现有 `recipes.json` + 我们维护的 `data/state/seen.json`(`aweme_id → recipe_id`)。
- 每次运行:抓「菜谱」当前全部 aweme_id → `new = 抓到 − seen` → 只处理 new。
- **遗留去重坑**:现有 37 条抖音来源是 `v.douyin.com/<短码>/` 短链,**不含 aweme_id、无法直接比对**。首次运行前可选**一次性 backfill**:解析这些短链 → aweme_id 存入 seen,避免重复收录;否则首跑可能与历史条目重复,靠人工复核兜底。
- 幂等:按 aweme_id 去重,原子写(tmp→rename),重复跑不产生重复。

## 6. 一致性机制(保证自动化输出 == 手工验收质量)

确定性部分(下载/抽帧/OCR/ASR/营养/命名/schema)逐次一致。模型判断部分用以下钉死:

1. **冻结结构化契约** `prompts/structuring.md`:把验收时的规则写死(密集 OCR、ASR×OCR 交叉验证、每食材必须有量或"适量"、加料无量则先补抽再放弃、仅技法/状态步骤配图、营养必须调脚本)。
2. **schema 硬校验闸门**:字段/类型/("适量"或数值)不合规 → 判失败、进重试,绝不写入。
3. **完整性闸门(代码)**:画面有加料动作但 N 项无量 → 强制补抽循环;仍缺 → 标 `低置信`。
4. **对抗式复核**:二次独立校验"用量在 OCR/ASR 原文可溯源?有无编造食材?"。
5. **黄金回归测试**:`7641206591925469082` 钉为 golden;管道每次改动重跑,关键事实 diff 必须为零。
6. **置信度分流**:高置信自动合并;被标记的进**人工复核队列**(无人值守的下限保障)。
- 另:每条留存原始三路信号(文案/OCR/转写)于 `data/work/<id>/`,可不重下重构。

> 自由文本(标题措辞、步骤句子、分类标签)可能轻微不同(LLM 采样/版本);承载信息的事实由"原信号 grounding + 校验 + 黄金测试 + 复核"四重锁定。

### 6.1 前端 2 行护栏(支持"适量",更新仓库时一并提交)
```js
// js/main.js updatePortion(): 缩放前
if (isNaN(originalQuantity)) return;                       // 非数值(适量)不缩放
// js/main.js calculateIngredientContribution(): 取到 quantity 后
if (typeof ingredient.quantity !== 'number') return 0;    // 非数值不计入营养贡献
```

## 7. 每天 10:00 定时(phase 2)

`launchd`/`crontab` 10:00 → `scripts/run_daily.sh` → `claude -p "$(cat prompts/daily_update.md)" --permission-mode acceptEdits --allowedTools ...`。前提:机器唤醒、Chrome 常驻并登录抖音、claude-in-chrome 扩展已授权 douyin.com。

**PR 策略(用户硬性要求):一菜一 PR。** 每个新食谱单独分支 `recipe-<id>-<slug>` + 单独 commit + 单独 PR(标题=菜名),**不批量合并**。同次多条时后一条 stacked 在前一条之上(diff 只含自己那条),按 id 顺序合并。前端"适量"护栏(§6.1)是一次性基础改动,随首条食谱 PR 合入。推送需用户的 git 凭证(本环境无 HTTPS cred/SSH key,我不代输凭证)。

## 8. 工具与环境(实测)

- **可用**: `/opt/homebrew/bin/ffmpeg` 8.1.1、`claude` CLI 2.1.177、Python 3.13、Node 25。
- **已装(项目 venv)**: `yt-dlp 2026.6.9`、`faster-whisper 1.2.1`(含 onnxruntime/ctranslate2/av)。待装: `rapidocr-onnxruntime`、`jsonschema`、`pyyaml`。
- **关键环境坑**:
  - pip 默认走内网 `bytedpypi.byted.org`(本机连不上,超时)→ **必须** `pip install --index-url https://pypi.org/simple/ ...`。
  - HuggingFace **直连可用**;`hf-mirror.com` 只 308 跳回 HF、反而下载失败 → faster-whisper 下模型**不要**设 `HF_ENDPOINT`,用默认 huggingface.co。模型缓存于 `.cache/hf`。
- 复用用户仓库: `calculate_nutrition.py`、`nutrition_db.json`(从 raw.githubusercontent 拉取/缓存)。

## 9. 风险

1. **claude-in-chrome 无头可用性(最高未知)**:`claude -p` 定时会话能否连上 Chrome 扩展待验。先手动验;不行则取列表改 Playwright + 保存登录态,其余不变。
2. **抖音风控/登录过期**:无人值守可能撞验证码;harvest 阶段检测、失败即停+通知,不污染数据。
3. **play URL / yt-dlp**:优先 yt-dlp(实测公开视频无 cookie 可下);失败兜底 `--cookies-from-browser chrome`。
4. **ASR 幻觉(BGM 视频)**:已知;识别并丢弃,靠 OCR。
5. **磁盘**:视频默认处理后删除(`keep_video: false`),保留转写/OCR/截图。
6. **合规**:仅个人收藏自用;harvest 控频 + 随机延时。

## 10. 测试

- 单元(纯逻辑): 状态 diff、schema 校验("适量"/对象步骤合法性)、ASR 幻觉过滤、OCR 文本去重、短链→aweme_id 解析。
- 集成/**黄金**: 对 `7641206591925469082` 跑全自动管道 → 与 `sample/recipe_95.json` diff,关键事实(用量/食材/步骤实质/营养/source/配图)必须一致。
- 端到端 dry-run: `python -m recipe_pipeline --url <单条> --no-merge` 手动验一条。

## 11. 项目结构

```
tiktok_recipe/
  requirements.txt  config.yaml  README.md
  recipe_pipeline/
    cli.py  config.py  paths.py  state.py  schema.py
    download.py  frames.py  nutrition.py  merge.py
    providers/{asr_faster_whisper.py, ocr_rapidocr.py}
  prompts/{structuring.md, daily_update.md}   # 冻结的结构化契约 + cron 编排提示词
  scripts/{setup.sh, run_daily.sh}
  data/{queue,work/<id>,images,videos(临时),failed,state}/
  sample/                                      # 黄金用例产物(recipe_95.json + 图 + 原信号)
  tests/
  docs/superpowers/specs/2026-06-12-douyin-recipe-scraper-design.md
```
最终交付物是合并进用户仓库的 `recipes.json` + `images/`,本项目是生成它的工具。
