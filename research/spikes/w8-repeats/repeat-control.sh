#!/usr/bin/env bash
# W8 session 15: three more repetitions of the 56 `control` cells of q56, taking control to n=5.
#
# WHY CONTROL, AND WHY NOW. The n=5 top-up (session 14) put redirect and deny at five runs each and
# left control and gated at two. Every headline number in the campaign is a DELTA AGAINST CONTROL,
# so the baseline is now the weakest term in the comparison: F55's "a denial saves tokens" moved by
# 70% between n=2 and n=5 and is measured against a control that has not moved at all. This is the
# cheapest way to firm that up - control has the lowest flip rate of the four variants (F56: 11%),
# so three runs buy a lot of confidence for ~40 min of GPU each.
#
# WHY --out ../runs/q56 (the same dir as sessions 11 and 14). These runs must POOL with the two
# 224-cell campaign runs, and the aggregator globs w8-* in whatever directory it is given. Pooling a
# 56-cell run with a 224-cell run needs the variant filter, or the aggregator keeps the MAJORITY
# cell set and three 56-cell runs silently outvote and DROP the two full ones:
#
#   python research/spikes/w8-repeats/aggregate.py runs/q56 --variant control
#
# ⚠ HARNESS DELTA - STATE IT WHEREVER THESE NUMBERS GO. Runs 1-2 of control were measured with NO
# verifier timeout at all. F57 was fixed on 2026-08-14, so these three runs bound each verifier at
# 300 s and kill the process tree on expiry. The two harnesses are behaviourally identical on any
# cell that does not hang, and control fires no gate and has never hung - but they are not the same
# instrument, so runmeta.json records `verify_timeout_s` and a run without that key is a pre-fix
# run. Check it rather than remembering it.
#
# HELD CONSTANTS. Unchanged from sessions 11 and 14: kv_cache_type q8_0 from LM Studio's per-model
# sticky config (~/.lmstudio/.internal/user-concrete-model-default-config/byteshape/...json,
# unmodified since 2026-08-08 14:59, which is before every run in this pool); ctx 65536 loaded
# against CLAUDETTE_NUM_CTX 61440; PARALLEL 1; full GPU offload. `lms load` has no KV flag and
# neither `lms ps` nor GET /api/v0/models reports one, so the file is the only witness.
#
# PRE-FLIGHT, NOT OPTIONAL. The runner cannot load the model, and LM Studio has dropped it by itself
# during an idle gap despite `lms ps` showing no TTL:
#
#   lms load qwen3.6-35b-a3b-mtp@iq3_s -c 65536 --gpu max --parallel 1 -y
#
# The F50 guard then checks loaded_context_length >= CLAUDETTE_NUM_CTX and ABORTS on a shortfall.
#
# TWO TRAPS, both already paid for:
#
# 1. To stop this loop, kill the ROOT bash: `taskkill /F /T /PID <pid>` from PowerShell (from Git
#    Bash the flags must be doubled or MSYS rewrites /F as F:/). Killing w8-run or claudette only
#    lets the loop advance to the next repetition, which is how a stopped series once quietly
#    produced another round of invalid data. A process list that comes back with NEW pids is the
#    loop advancing, not a failed kill.
# 2. ~/.cargo/bin/claudette is OLDER than af3f804 and reports the same --version, hence --bin.
#
# 🚨 AND A KILLED RUN LOSES EVERY CELL IT HAD MEASURED. w8-run holds all cell records in memory and
# writes cells.jsonl in one call at the very end, so stop the loop BETWEEN repetitions or accept
# losing the whole current one. Check what banked with the STATUS COUNTS, never `wc -l`: a degraded
# run emits a full-length, well-formed file.
set -u
cd /d/dev/ABCC_20_powerd_by_claudette/harness || exit 1

LOG=/d/dev/ABCC_20_powerd_by_claudette/runs/q56/repeat-control.log
mkdir -p /d/dev/ABCC_20_powerd_by_claudette/runs/q56

# COOLING PAUSE between repetitions, kept from session 14 (David's instruction after the machine ran
# hot enough that a run was called off). Deliberately not after the last one. It is a gap BETWEEN
# runs, so no cell's measurement spans it and no held constant changes.
PAUSE_S=300

echo "===== SESSION 15 CONTROL n=5 $(date -Is) =====" >>"$LOG"
for i in 3 4 5; do
  echo "===== repetition $i starting $(date -Is) =====" >>"$LOG"
  cargo run -q -p w8-run --bin w8-run -- ../corpus \
    --suite q56 \
    --subject claudette-af3f804 \
    --model 'qwen3.6-35b-a3b-mtp@iq3_s' \
    --out ../runs/q56 \
    --variant control \
    --bin /d/dev/claudette/target/release/claudette.exe >>"$LOG" 2>&1
  echo "===== repetition $i exit=$? $(date -Is) =====" >>"$LOG"
  if [ "$i" != "5" ]; then
    echo "===== cooling pause ${PAUSE_S}s after repetition $i $(date -Is) =====" >>"$LOG"
    sleep "$PAUSE_S"
  fi
done
echo "ALL DONE $(date -Is)" >>"$LOG"
