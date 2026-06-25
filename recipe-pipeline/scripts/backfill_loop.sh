#!/usr/bin/env bash
# 跨 5h 额度重置窗口自动续跑回填,直到补完(或 6 轮上限)。
set -uo pipefail
cd "$(dirname "$0")/.."
export HF_HOME="$PWD/.cache/hf"
PY=./.venv/bin/python
rem_fn='import json;d=json.load(open("data/state/seen.json"));print(262-sum(1 for v in d.values() if v.get("status")=="done" and (v.get("recipe_id") or 0)>=101)-sum(1 for v in d.values() if v.get("status")=="review"))'
for cycle in $(seq 1 6); do
  echo "--- chip 轮 $cycle 开始 $(date) ---" >> data/backfill.log
  $PY scripts/backfill_parallel.py --workers 4 >> data/backfill.parallel.out 2>&1
  rem=$($PY -c "$rem_fn" 2>/dev/null || echo 999)
  echo "--- chip 轮 $cycle 结束, 剩余 $rem $(date) ---" >> data/backfill.log
  [ "$rem" -le 0 ] 2>/dev/null && { echo "全部补完!" >> data/backfill.log; break; }
  sleep 18000   # 等下个额度重置(~5h)
done
rm -f .cache/backfill.lock