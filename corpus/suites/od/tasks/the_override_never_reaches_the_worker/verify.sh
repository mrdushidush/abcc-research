#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts the configuration the worker will run on, not that it started.
#
# The cheapest way to get past the floor is to make `bootcfg/capacity.py` read
# the declared configuration. The process then starts on concurrency 1 and batch
# 100 while printing a throughput of 4000 -- so the assertions below are on the
# three running values, which the capacity check cannot reach.
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
[ -f data/env.json ] || {
  echo "RESULT: INVALID data/env.json is missing — the fixture was not copied intact"
  exit 0
}
[ -f data/declared.json ] || {
  echo "RESULT: INVALID data/declared.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^BOOT RUN$' \
  || fail "output is missing the BOOT RUN header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'concurrency: 8' \
  || fail "expected 'concurrency: 8', got: $(got concurrency) — 1 means the environment override never landed"
printf '%s' "$OUT" | grep -qx 'batch_size: 500' \
  || fail "expected 'batch_size: 500', got: $(got batch_size) — 100 means the environment override never landed"
printf '%s' "$OUT" | grep -qx 'timeout_s: 45' \
  || fail "expected 'timeout_s: 45', got: $(got timeout_s) — 30 is the shipped laptop default"
printf '%s' "$OUT" | grep -qx 'throughput: 4000' \
  || fail "expected 'throughput: 4000', got: $(got throughput) — 4000 beside concurrency 1 means the floor is reading the declared file"

echo "RESULT: PASS the environment overrides reach the worker (concurrency 8, batch 500, timeout 45)"
exit 0
