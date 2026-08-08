#!/usr/bin/env bash
# W8 step 2: n=5 repeats of the 31 section-4B fix_* cells, subject claudette-af3f804.
# Each invocation makes its own runs/w8-<ms>/ with runmeta.json + cells.jsonl.
#
# ⚠ TWO THINGS LEARNED THE HARD WAY, 2026-08-08:
#
# 1. `--suite u100` is passed explicitly even though the corpus holds one suite today. The moment
#    q56 lands, `w8-run` makes --suite mandatory and a loop without it fails on every repetition.
#
# 2. **To stop this loop, kill the ROOT bash, not the runner.** Killing w8-run or claudette just
#    lets the loop advance to the next repetition — which is how a stopped series quietly kept
#    running and produced another round of invalid data. `taskkill /F /T /PID <root bash>`.
set -u
cd /d/dev/ABCC_20_powerd_by_claudette/harness || exit 1

TASKS=(fix_hardcoded_secret fix_info_leak fix_insecure_random fix_missing_validation
       fix_open_redirect fix_path_traversal fix_sql_inject fix_type_confusion
       fix_weak_hash fix_xss_reflect)
ARGS=()
for t in "${TASKS[@]}"; do ARGS+=(--task "$t"); done

LOG=/d/dev/ABCC_20_powerd_by_claudette/runs/repeat5.log
mkdir -p /d/dev/ABCC_20_powerd_by_claudette/runs

for i in 1 2 3 4 5; do
  echo "===== repetition $i starting $(date -Is) =====" >>"$LOG"
  cargo run -q -p w8-run --bin w8-run -- ../corpus \
    --suite u100 \
    --subject claudette-af3f804 \
    --model 'qwen3.6-35b-a3b-mtp@iq3_s' \
    --out ../runs \
    --bin /d/dev/claudette/target/release/claudette.exe \
    "${ARGS[@]}" >>"$LOG" 2>&1
  echo "===== repetition $i exit=$? $(date -Is) =====" >>"$LOG"
done
echo "ALL DONE $(date -Is)" >>"$LOG"
