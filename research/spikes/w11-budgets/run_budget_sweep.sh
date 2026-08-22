#!/usr/bin/env bash
# W11 item 5 - loop-budget sweep on the champion, K suite, control variant.
# One variable: CLAUDETTE_MAX_ITERATIONS (12 / 20 / 40), three reps each.
# Everything else is held at the k-champ baseline: --num-ctx 40000, num_predict
# 8192, the same corpus commit, the same subject binary.
#
# --bin is MANDATORY: ~/.cargo/bin/claudette shadows the pinned build on PATH and
# reports the same --version. The delivery pre-flight is what catches it, and it
# refused all nine cells of the first attempt at this sweep.
set -u
cd "$(dirname "$0")/../../../harness" || exit 1
BIN=./target/release/w8-run.exe
SUBJECT_BIN=D:/dev/claudette/target/release/claudette.exe
for B in 12 20 40; do
  for R in 1 2 3; do
    OUT="../runs/w11-b${B}-r${R}"
    [ -d "$OUT" ] && { echo "skip $OUT (exists)"; continue; }
    echo "=== budget=$B rep=$R  $(date +%H:%M:%S) ==="
    "$BIN" ../corpus --subject claudette-af3f804 --model qwen3.6-35b-a3b-mtp@iq3_s \
      --suite k --variant control --num-ctx 40000 --max-iterations "$B" \
      --bin "$SUBJECT_BIN" --out "$OUT"
    echo "--- exit=$? $(date +%H:%M:%S) ---"
  done
done
echo "SWEEP DONE $(date +%H:%M:%S)"
