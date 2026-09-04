#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts what the scheduler DID, not that the SLA check stopped raising.
#
# The cheapest way to stop the exception is to redefine the rate in
# `retryd/report.py`. That runs clean and reports 100% on a night where three of
# fourteen failures were retried -- so the assertions below are on the retry
# count, the drop count and `windows_used`, none of which a redefinition reaches.
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
[ -f data/failures.json ] || {
  echo "RESULT: INVALID data/failures.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^RETRY RUN$' \
  || fail "output is missing the RETRY RUN header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'failures: 14' \
  || fail "expected 'failures: 14', got: $(got failures) — data/failures.json was changed"
printf '%s' "$OUT" | grep -qx 'retried: 11' \
  || fail "expected 'retried: 11', got: $(got retried) — 3 means the budget still never resets after the first hour"
printf '%s' "$OUT" | grep -qx 'dropped_no_budget: 3' \
  || fail "expected 'dropped_no_budget: 3', got: $(got dropped_no_budget) — 11 means eleven failures were never retried"
printf '%s' "$OUT" | grep -qx 'windows_used: 4' \
  || fail "expected 'windows_used: 4', got: $(got windows_used) — 1 means every event still lands in the window the budget was built in"
printf '%s' "$OUT" | grep -qx 'retry_rate_pct: 78' \
  || fail "expected 'retry_rate_pct: 78', got: $(got retry_rate_pct) — 100 is the rate computed over only the retries, which is 100 by construction"

echo "RESULT: PASS the budget resets hourly (retried 11, dropped 3, 4 windows, 78%)"
exit 0
