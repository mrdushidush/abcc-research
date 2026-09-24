#!/usr/bin/env bash
# PLAN-TOOL A3 — the overnight baseline. abcc-e5eef90 vs claudette-af3f804, champion at 40960.
# R x3, K x3, Q56 x1. w8-run has no repeat flag, so n=3 is three invocations.
#
# Order interleaves the subjects inside every pass (abcc R, claudette R, abcc K, claudette K, ...)
# so a stop at any point still leaves a paired comparison. Q56 goes last: it is the broad
# regression check, not the question A3 asks.
#
# claudette runs `--variant control` only: abcc has no permission gate, so control is the only
# variant with a pair. `--bin` pins the same claudette.exe every earlier claudette baseline used
# (af3f804 + dependency bumps; the ~/.cargo/bin copy predates af3f804 and lacks the sentinels).
#
# Every invocation's full output goes to its own log; one line per invocation goes to INDEX.
# A failing invocation is recorded and the driver moves on.
#
# Run from Git Bash:  bash a3-overnight.sh          (cwd must be harness/)

set -u
cd "$(dirname "$0")" || exit 1

MODEL="qwen3.6-35b-a3b-mtp@iq3_s"
CLAUDETTE_BIN="D:/dev/claudette/target/release/claudette.exe"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOGDIR="runs/a3-$STAMP"
INDEX="$LOGDIR/INDEX.tsv"
mkdir -p "$LOGDIR"
printf 'seq\tpass\tsuite\tsubject\tstart\tend\texit\trun_dir\tlog\n' > "$INDEX"

seq=0
one() {  # one <pass> <suite> <subject>
    local pass="$1" suite="$2" subject="$3"
    seq=$((seq + 1))
    local log
    log="$LOGDIR/$(printf '%02d' "$seq")-$suite-p$pass-$subject.log"
    local extra=()
    if [[ "$subject" == claudette-* ]]; then
        extra=(--bin "$CLAUDETTE_BIN" --variant control)
    fi
    local start end rc run_dir
    start="$(date -Iseconds)"
    echo "[$start] #$seq pass $pass $suite $subject"
    target/release/w8-run.exe ../corpus --subject "$subject" --suite "$suite" \
        --model "$MODEL" --num-ctx 40960 --verify-timeout-s 1200 "${extra[@]}" \
        > "$log" 2>&1
    rc=$?
    end="$(date -Iseconds)"
    run_dir="$(grep -a '^→ ' "$log" | tail -1 | sed 's/^→ //')"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$seq" "$pass" "$suite" "$subject" "$start" "$end" "$rc" "${run_dir:-?}" "$log" >> "$INDEX"
    echo "[$end]   exit $rc  ${run_dir:-no run dir}"
}

for pass in 1 2 3; do
    for suite in r k; do
        one "$pass" "$suite" abcc-e5eef90
        one "$pass" "$suite" claudette-af3f804
    done
done
one 1 q56 abcc-e5eef90
one 1 q56 claudette-af3f804

echo "[$(date -Iseconds)] A3 driver done — $INDEX"
touch "$LOGDIR/DONE"
