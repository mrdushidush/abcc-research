#!/usr/bin/env bash
# W8 session 12: three more repetitions of the 112 redirect/deny cells of q56.
#
# WHY ONLY TWO VARIANTS. Session 11 ran all 224 q56 cells twice and F56 measured how often a cell's
# verdict changes between runs: control 11%, gated 11%, redirect-first-edit 25%, deny-first-edit
# 39%. control and gated are therefore defensible at n=2 and are deliberately NOT re-run; the two
# intervening variants are soft to about +/-4 passes and are taken to n=5 by these three runs.
#
# WHY --out ../runs/q56 (the same dir as session 11, not a new one). These runs must POOL with
# session 11's two, and the aggregator globs w8-* in whatever directory it is given. Pooling a
# 112-cell run with a 224-cell run needs the variant filter:
#
#   python research/spikes/w8-repeats/aggregate.py runs/q56 \
#       --variant redirect-first-edit --variant deny-first-edit
#
# WITHOUT that filter the aggregator keeps the MAJORITY cell set, and three 112-cell runs outvote
# two 224-cell runs — so session 11's full runs would be silently dropped.
#
# HELD CONSTANTS. kv_cache_type is q8_0, set in LM Studio's per-model sticky config at
# ~/.lmstudio/.internal/user-concrete-model-default-config/byteshape/Qwen3.6-35B-A3B-MTP-GGUF/
# Qwen3.6-35B-A3B-IQ3_S-3.06bpw.gguf.json. That file has not been modified since 2026-08-08 14:59,
# which is BEFORE session 11's two runs, and loading a model does not rewrite it — so these three
# runs and session 11's two share the setting. `lms load` has no KV flag and neither `lms ps`
# (table or --json) nor GET /api/v0/models reports one, so the file is the only witness.
#
# TWO TRAPS, both already paid for:
#
# 1. To stop this loop, kill the ROOT bash: `taskkill /F /T /PID <pid>`. Killing w8-run or
#    claudette only lets the loop advance to the next repetition, which is how a stopped series
#    once quietly produced another round of invalid data.
# 2. ~/.cargo/bin/claudette is OLDER than af3f804 and reports the same --version, hence --bin.
set -u
cd /d/dev/ABCC_20_powerd_by_claudette/harness || exit 1

LOG=/d/dev/ABCC_20_powerd_by_claudette/runs/q56/repeat-rd3.log
mkdir -p /d/dev/ABCC_20_powerd_by_claudette/runs/q56

for i in 3 4 5; do
  echo "===== repetition $i starting $(date -Is) =====" >>"$LOG"
  cargo run -q -p w8-run --bin w8-run -- ../corpus \
    --suite q56 \
    --subject claudette-af3f804 \
    --model 'qwen3.6-35b-a3b-mtp@iq3_s' \
    --out ../runs/q56 \
    --variant redirect-first-edit \
    --variant deny-first-edit \
    --bin /d/dev/claudette/target/release/claudette.exe >>"$LOG" 2>&1
  echo "===== repetition $i exit=$? $(date -Is) =====" >>"$LOG"
done
echo "ALL DONE $(date -Is)" >>"$LOG"
