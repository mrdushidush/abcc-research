#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts all six percentiles, because the ticket names one window of three.
#
# The tempting fix subtracts one from the index. That is right whenever n times p
# is whole -- the reported window, and the ten-sample windows in the test suite --
# and wrong everywhere else. `search_p95_ms` is the discriminating line: 260 ms
# under the rule, 14 ms under the sham.
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
[ -f data/windows.json ] || {
  echo "RESULT: INVALID data/windows.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^LATENCY RUN$' \
  || fail "output is missing the LATENCY RUN header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'windows: 3' \
  || fail "expected 'windows: 3', got: $(got windows) — data/windows.json was changed"
printf '%s' "$OUT" | grep -qx 'checkout_p50_ms: 33' \
  || fail "expected 'checkout_p50_ms: 33', got: $(got checkout_p50_ms) — 36 is int(n*p) on an even window"
printf '%s' "$OUT" | grep -qx 'checkout_p95_ms: 120' \
  || fail "expected 'checkout_p95_ms: 120', got: $(got checkout_p95_ms) — 400 is the maximum, which is the number in the ticket"
printf '%s' "$OUT" | grep -qx 'profile_p50_ms: 31' \
  || fail "expected 'profile_p50_ms: 31', got: $(got profile_p50_ms) — 35 is int(n*p) on a ten-sample window"
printf '%s' "$OUT" | grep -qx 'profile_p95_ms: 61' \
  || fail "expected 'profile_p95_ms: 61', got: $(got profile_p95_ms) — 50 means the index was moved down a rank"
printf '%s' "$OUT" | grep -qx 'search_p50_ms: 9' \
  || fail "expected 'search_p50_ms: 9', got: $(got search_p50_ms) — 7 means the index was moved down a rank on a seven-sample window"
printf '%s' "$OUT" | grep -qx 'search_p95_ms: 260' \
  || fail "expected 'search_p95_ms: 260', got: $(got search_p95_ms) — 14 means p95 now reports the sixth of seven samples"

echo "RESULT: PASS every percentile is the nearest-rank observation (checkout p95 120, search p95 260)"
exit 0
