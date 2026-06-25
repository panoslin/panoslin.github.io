# 食谱增量抓取 / 结构化工作流(抖音 + 下厨房)

把**抖音「菜谱」收藏夹**和**下厨房收藏的菜谱**增量抓取、用多模态(文案 + ASR + 关键帧 OCR + Claude 结构化)提取**精确食材用量(克/毫升)、制作步骤、配图**,去重后以**「每个食谱单独一个 PR」**的方式合入 GitHub Pages 仓库 `panoslin/panoslin.github.io` 的根 `recipes.json`。

> 本目录是**与站点物理隔离的工具代码 + 断点续跑状态**,放在仓库子目录 `recipe-pipeline/`,**不改动站点任何文件**(`recipes.json`、`images/`、`main.js` 等都由各食谱 PR 单独增改)。
> 设计见 `docs/superpowers/specs/2026-06-12-douyin-recipe-scraper-design.md`。

## 进度快照(截至本次提交)

| 来源 | 已发 PR | 真重复(dup_skip) | 失败 | 处理总数 |
|---|---|---|---|---|
| 抖音 | 234 | 23 | 8 | 262 |
| 下厨房 | 155 | 21 | 0 | 176 |

库内食谱从 32 增至 ~487。**所有进度记录在 `data/state/seen.json`,新会话克隆后续跑会自动跳过这些,不重复处理。**

---

## 1. 环境搭建

```bash
cd recipe-pipeline
bash scripts/setup.sh        # 一键:venv + 依赖(走公网 PyPI)+ 提示装 ffmpeg
# 或手动:
python3 -m venv .venv
./.venv/bin/pip install --index-url https://pypi.org/simple/ -r requirements.txt
brew install ffmpeg          # 系统级 ffmpeg / ffprobe(frames.py 依赖)
```

- **whisper 模型**:`faster-whisper` 首次运行自动从 **huggingface.co 直连**下载 `medium` 模型。
  **不要设 `HF_ENDPOINT`**(hf-mirror.com 只回 308 跳转会失败)。建议 `export HF_HOME="$PWD/.cache/hf"` 缓存到本目录。
- **pip 源**:若内网镜像 `bytedpypi` 连不上,必须 `--index-url https://pypi.org/simple/`。
- **营养计算**:`recipe_pipeline/nutrition.py` 首次运行从公开 raw.githubusercontent 拉取本仓库的
  `calculate_nutrition.py` + `nutrition_db.json` 并缓存到 `.cache/repo/`(口径与站点一致,需联网)。
- **ffmpeg 路径**:`config.py` 默认找 Homebrew 路径,否则回退 PATH 上的 `ffmpeg`;可用 `FFMPEG_BIN`/`FFPROBE_BIN` 覆盖。

## 2. 前置条件

1. **`gh` 已认证**且对 `panoslin.github.io` 有写权限:`gh auth status` 应已登录(repo scope)。
   git push 走 gh 的凭证助手——**本工具从不读写任何 token**。
2. **panoslin.github.io 工作副本**:发 PR 的脚本在 `.cache/clone/` 操作。新会话需先克隆:
   ```bash
   gh repo clone panoslin/panoslin.github.io .cache/clone
   ```
   脚本在此副本上建 `recipe-<id>` 分支、提交、push、`gh pr create`。
3. **下厨房抓取**:Chrome 已装 claude-in-chrome 扩展并授权 `xiachufang.com`(公开菜谱页无需登录,但需浏览器绕 IP 反爬,见 §6)。
4. **抖音抓取**:Chrome 已登录抖音、claude-in-chrome 已授权 `douyin.com`(用于增量采集收藏夹列表)。

## 3. `seen.json` 状态机(`data/state/seen.json`)

键 = 抖音 `aweme_id` 或下厨房 `xcf:<recipe_id>`;值含 `status` / `recipe_id` / `source` / `pr` / `dup_of`。

| status | 含义 | 续跑是否跳过 |
|---|---|---|
| `done` | 已结构化并开 PR(`pr` 字段是链接) | ✅ 跳过 |
| `seed` | 站点已有(source 重复)或原始种子,不重复添加 | ✅ 跳过 |
| `review` | 菜名疑重复待裁定(历史状态,现已全部裁定) | ✅ 跳过 |
| `dup_skip` | 读内容确认为真重复,不收录(`dup_of` 记重复于哪个 id) | ✅ 跳过 |
| `video_pending` | 下厨房视频菜谱待视频管道补全(现已无残留) | ✅ 跳过 |
| `failed` | 处理失败(纯 BGM/无文案等),**默认会被重试** | ❌ 重试 |

> 跳过逻辑见各脚本 `main()` 的 `todo = [... not in ("done","seed","review","dup_skip","video_pending")]`。
> `failed` 不在跳过集 → 重跑会重试;要彻底放弃某条,把它在 seen.json 改成 `dup_skip`/`seed`。

## 4. 脚本一览(`scripts/`)

**抖音**
- `backfill_parallel.py` — 主力:进程池并发产出 draft、串行发 PR(stacked)。`--workers N`。
- `backfill.py` — 串行版(限速 `--sleep`),逻辑同上。
- `backfill_loop.sh` — 跨 5h 额度重置窗口自动续跑(限额耗尽时等重置再继续)。
- `backfill_shortlinks.py` — 解析 `v.douyin.com` 短链为 `aweme_id`。

**下厨房**
- `xcf_exfil_server.py` — 本地 CORS 接收服务器(端口 8799):浏览器页内采集的 JSON / 视频二进制 POST 到此落盘,避免大数据经对话回传。**先起它再做浏览器采集**。
- `publish_xcf.py` — 把 `data/xcf_harvest.jsonl`(浏览器采到的文字菜谱)逐条发 PR(图片热链下厨房 CDN)。
- `backfill_xcf.py` — 纯本地 curl_cffi 抓取版(**受 IP 反爬限制基本只能抓 ~4 条,实战用浏览器采集**,留作参考)。
- `backfill_xcf_video.py` — 下厨房「视频菜谱」:对已下载到 `data/xcf_videos/<id>.mp4` 的视频走多模态管道发 PR。

**通用/复核**
- `publish_reviewed.py` — 把人工复核判为 distinct(确为不同菜)的复核项发 PR(读 `data/review_verdicts.json`)。
- `apply_frontend_guard.py` — 给站点 `main.js` 加 2 行守卫以正确显示 quantity="适量"(一次性,已应用)。
- `run_daily.sh` / `com.panoslin.recipe-daily.plist` — 每日 22:00 launchd 定时(见 §7)。
- `setup.sh` — 一键环境初始化。

**结构化契约**:`prompts/structuring.md` 是冻结契约(交互运行与无头 `claude -p` 共用)。`prompts/daily_update.md` 是每日增量编排提示词。

### 手动处理单条(调试用)
```bash
P=./.venv/bin/python
$P -m recipe_pipeline bundle    --aweme-id <id> --caption "<文案>" --author "<作者>"
$P -m recipe_pipeline structure --aweme-id <id>     # 无头 claude -p 结构化
$P -m recipe_pipeline finalize  --aweme-id <id>     # 算营养/抽图/校验
$P -m recipe_pipeline process-one --aweme-id <id> --caption "..." --author "..."   # 一步到位
```

## 5. ID 唯一性 与 每食谱单独 PR(硬约定)

- **每个食谱单独一个 PR**,分支 `recipe-<id>`,**stacked**(base 为上一条分支),保证每个 PR diff 干净。
- **ID 全局唯一(三重保证)**:① `merge.next_id()` 每次读**链尾最新** `recipes.json` 取 `max+1`;
  ② finalize 时显式 `while rid in existing_ids: rid += 1`;③ commit 前 `assert not any(r["id"]==rid ...)`。
- **去重**:先按 `source` URL,再按标题相似度(`dedup.find_title_dups`)拦疑似项进 `review`;
  标题相似但**读食材/用量/步骤后确为不同菜**的,走 `publish_reviewed.py` 收录。
- ⚠️ resume 时 `next_id` 依赖 `.cache/clone` 的 `recipes.json`。若之前的 `recipe-<id>` PR **尚未合并到 main**,
  重新克隆的 main 仍是旧的 → 新条目取号可能与未合并 PR 冲突。**建议:续跑前先把已开食谱 PR 合并,或确认 clone 反映最新已收录食谱。**`seen.json` 保证不重复处理,但取号基准需正确。

## 6. 下厨房反爬要点(关键,另见记忆 `xcf-scraping-pipeline`)

- 单菜谱页 `/recipe/<id>/` 公开,但站点按 **TLS 指纹**封锁普通客户端(urllib→404,curl→418)。
  `curl_cffi` 的 `impersonate="chrome"` 可 200——但 **IP+频率验证码("滑动验证"页 ~4.4KB)**:即便每 18s 一条也只放行 ~4 条就死封,**纯本地不可行**。
- **可行方案 = 浏览器内同源 iframe 采集**:在已登录 xcf 标签页跑 JS,用隐藏 iframe 加载 `/recipe/<id>/`
  (整页加载会跑反爬 JS、刷新放行 token),解析 DOM,结果 POST 到本地服务器(`xcf_exfil_server.py`)。Chrome 放行 https→http://localhost。
  **后台标签会被节流** → 由会话**主动逐批驱动**(每批 ≤4,iframe onload 不受计时器节流)。
- **视频菜谱**(`recipe-vod-video` iframe → `/vod_video/<vid>/`):HTML 无食材表,mp4 是签名 URL(扩展会打码)。
  做法:**页内 JS `fetch(video.src)` 取 blob → POST 到 `/video?id=<rid>`** 落盘为 `data/xcf_videos/<rid>.mp4`,再用 `backfill_xcf_video.py` 走多模态管道。
- 解析器(`recipe_pipeline/xcf.py`):标题=`h1`、封面=`meta[og:image]`、食材=`.ings tr` 内 `.name`/`.unit`、步骤=`.steps li` 内 `.text`+`img`;`split_amount("250克")→(250,"克")`;`classify(title)` 关键词粗分类。

## 7. 每日定时(launchd,每晚 22:00 抖音增量)

```bash
# 装(先把 plist 里路径改成你的克隆路径):
cp scripts/com.panoslin.recipe-daily.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.panoslin.recipe-daily.plist
launchctl list | grep panoslin       # 确认已挂载
# 卸:
launchctl bootout gui/$(id -u)/com.panoslin.recipe-daily
```

`run_daily.sh` 起无头 `claude -p`(读 `prompts/daily_update.md`),用 claude-in-chrome 采集收藏夹新增并增量处理;
若 `.cache/backfill.lock` 存在(有全量回填在跑)则跳过本次,避免抢 git。

## 8. 在新会话如何接着跑(步骤清单)

```bash
# 0) 克隆仓库,进入工具子目录
gh repo clone panoslin/panoslin.github.io && cd panoslin.github.io/recipe-pipeline

# 1) 环境(§1)
bash scripts/setup.sh
export HF_HOME="$PWD/.cache/hf"

# 2) 准备发 PR 用的工作副本(§2)
gh repo clone panoslin/panoslin.github.io .cache/clone

# 3) 确认续跑状态已就位
./.venv/bin/python -c "import json,collections; d=json.load(open('data/state/seen.json')); \
  print(collections.Counter(v['status'] for v in d.values()))"

# 4) 续跑(任选;都会自动跳过 done/seed/review/dup_skip/video_pending)
#   抖音增量(先用浏览器采集收藏夹新 id 写入 data/queue/new_ids.json,再):
./.venv/bin/python scripts/backfill_parallel.py --workers 4
#   下厨房文字菜谱(先用浏览器 iframe 采集补充 data/xcf_harvest.jsonl):
./.venv/bin/python scripts/publish_xcf.py
#   下厨房视频菜谱(先把视频下到 data/xcf_videos/):
./.venv/bin/python scripts/backfill_xcf_video.py

# 5) 跑测试确认管道完好
./.venv/bin/python -m pytest tests/ -q
```

**要点**:抖音/下厨房的**新增 id 采集**仍需浏览器(claude-in-chrome,见 §6 与 `prompts/`),已处理过的不会重做;
大额度操作(每条一次 Claude 结构化)宜后台 + `caffeinate -i` 防休眠,限额耗尽用 `backfill_loop.sh` 跨窗口续跑;
复核裁定记录在 `data/review_verdicts.json`(每条含证据)。

## 9. 已知事项

- `av`(faster-whisper)与 `opencv`(rapidocr)各自打包 libav*,启动有 `objc[...] Class ... implemented in both` 警告;**实测不影响运行**。若遇崩溃,改装 `opencv-python-headless`。
- 营养计算对 quantity="适量"/未知食材会打印 `计算食材 X 时出错` 警告并取默认 0——**预期行为,无害**(无法对"适量"算克数)。
- "适量"食材:`recipes.json` 数据安全;前端份数缩放/营养贡献需 2 行护栏(见 spec §6.1,已由 `apply_frontend_guard.py` 应用)。

## 10. 目录结构

```
recipe-pipeline/
├── recipe_pipeline/        # 核心包:config/download/frames/bundle/structure/merge/schema/dedup/state/nutrition/xcf + providers/
├── scripts/                # 回填/发布/采集/定时脚本(见 §4)
├── prompts/                # structuring.md(冻结结构化契约)、daily_update.md
├── docs/                   # 设计 spec
├── tests/                  # test_units.py + test_golden.py(11 项)+ sample/
├── data/
│   ├── state/seen.json     # ★ 断点续跑状态机
│   ├── queue/*.json        # 待处理 id 队列(new_ids / xcf_ids / harvested)
│   ├── review_verdicts.json / review_compare.json / review_table.json  # 复核裁定+证据
│   └── xcf_harvest.jsonl   # 下厨房浏览器采集的菜谱原料
├── config.yaml             # 管道配置(无任何凭证)
├── requirements.txt
├── .gitignore
└── README.md
```
