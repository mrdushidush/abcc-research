#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts the whole eight-attempt schedule, because the policy has two halves.
#
# The tempting fix is to double and stop there. That reproduces the runbook's
# table for the first six attempts -- every number the ticket mentions -- and
# waits 64 and 128 seconds at seven and eight, where the runbook says sixty. So
# `schedule_8`, `attempt8_s` and `longest_wait_s` are the discriminating lines.
#
# Expected values were produced by fixture+refsol and are reproducible with:
#   python run.py

set -u

WORKDIR="${1:?usage: verify.sh <workdir> <transcript>}"

cd "$WORKDIR" 2>/dev/null || {
  echo "RESULT: INVALID cannot cd to workdir '$WORKDIR'"
  exit 0
}

# Resolve an interpreter BY EXECUTING IT (SPEC.md §8): on Windows a Microsoft
# Store alias shim named python3.exe sits on PATH, is found by `command -v`, and
# prints an advert instead of running the code.
PY=""
for cand in "${PYTHON:-}" python3 python; do
  [ -z "$cand" ] && continue
  if "$cand" -c '' >/dev/null 2>&1; then PY="$cand"; break; fi
done
if [ -z "$PY" ]; then
  echo "RESULT: INVALID no working python interpreter (tried \$PYTHON, python3, python)"
  exit 0
fi

[ -f run.py ] || { echo "RESULT: FAIL run.py is missing from the workdir"; exit 0; }
[ -f data/jobs.json ] || {
  echo "RESULT: INVALID data/jobs.json is missing — the fixture was not copied intact"
  exit 0
}

OUT="$("$PY" run.py 2>&1)"
STATUS=$?
if [ $STATUS -ne 0 ]; then
  FIRST="$(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-200)"
  echo "RESULT: FAIL run.py exited $STATUS: ${FIRST}"
  exit 0
fi

fail() { echo "RESULT: FAIL $1"; exit 0; }
got()  { printf '%s' "$OUT" | grep -E "^$1:" || echo "<no $1 line>"; }

printf '%s' "$OUT" | grep -q '^BACKOFF RUN$' \
  || fail "output is missing the BACKOFF RUN header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'jobs: 5' \
  || fail "expected 'jobs: 5', got: $(got jobs) — data/jobs.json was changed"
printf '%s' "$OUT" | grep -qx 'schedule_8: 1,2,4,8,16,32,60,60' \
  || fail "expected 'schedule_8: 1,2,4,8,16,32,60,60', got: $(got schedule_8) — 1,2,3,... is linear; 1,2,4,...,64,128 is doubling with no ceiling"
printf '%s' "$OUT" | grep -qx 'attempt5_s: 16' \
  || fail "expected 'attempt5_s: 16', got: $(got attempt5_s) — 5 is the linear schedule the ticket complains about"
printf '%s' "$OUT" | grep -qx 'attempt8_s: 60' \
  || fail "expected 'attempt8_s: 60', got: $(got attempt8_s) — 128 means MAX_S is still unread"
printf '%s' "$OUT" | grep -qx 'longest_wait_s: 60' \
  || fail "expected 'longest_wait_s: 60', got: $(got longest_wait_s) — any value above 60 breaks the second half of the policy"
printf '%s' "$OUT" | grep -qx 'total_wait_s: 345' \
  || fail "expected 'total_wait_s: 345', got: $(got total_wait_s) — 86 is linear, 421 is uncapped doubling"
printf '%s' "$OUT" | grep -qx 'sync_ceiling_wait_s: 183' \
  || fail "expected 'sync_ceiling_wait_s: 183', got: $(got sync_ceiling_wait_s) — 255 is the uncapped schedule run to the queue's ceiling"

echo "RESULT: PASS the schedule doubles and flattens at MAX_S (1,2,4,8,16,32,60,60)"
exit 0
