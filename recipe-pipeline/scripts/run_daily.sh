#!/usr/bin/env bash
# 每日 10:00 由 launchd/cron 调用。起一个无头 Claude Code 会话执行增量编排。
# 前提:Chrome 常驻并已登录抖音、claude-in-chrome 扩展已授权 douyin.com。
set -euo pipefail
cd "$(dirname "$0")/.."
export HF_HOME="$PWD/.cache/hf"

# 防撞:全量回填进行时跳过本次定时(两者都会动 .cache/clone 的 git)
if [ -f .cache/backfill.lock ]; then
  echo "[$(date)] backfill 进行中(.cache/backfill.lock 存在),跳过本次定时" | tee -a data/last_run.log
  exit 0
fi

claude -p "$(cat prompts/daily_update.md)" \
  --permission-mode acceptEdits \
  --allowedTools "Bash Read Write Edit mcp__claude-in-chrome__*" \
  2>&1 | tee -a data/last_run.log

# 提交推送(默认关闭;确认无误后取消注释,并在 config.yaml 配 repo.local_clone)
# if [ -n "${PUSH:-}" ]; then
#   cd "$(yq -r .repo.local_clone config.yaml)" && git add recipes.json images/ && \
#   git commit -m "chore: 增量更新菜谱 $(date +%F)" && git push
# fi
