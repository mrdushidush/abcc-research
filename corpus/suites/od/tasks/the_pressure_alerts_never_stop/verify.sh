#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts the pressures, not that the pager stopped.
#
# The cheapest way to stop the storm is to rescale inside `baro/report.py` when
# the breaker would trip. That runs clean and lands at 10125 rather than 10130,
# because dividing by ten divided the bench offset too -- so the per-sensor
# assertion below, on the one sensor that has an offset, is the discriminating
# one: 10132 against 10150.
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
[ -f data/readings.json ] || {
  echo "RESULT: INVALID data/readings.json is missing — the fixture was not copied intact"
  exit 0
}
[ -f data/offsets.json ] || {
  echo "RESULT: INVALID data/offsets.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^PRESSURE RUN$' \
  || fail "output is missing the PRESSURE RUN header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'readings: 24' \
  || fail "expected 'readings: 24', got: $(got readings) — data/readings.json was changed"
printf '%s' "$OUT" | grep -qx 'mean_ckpa: 10130' \
  || fail "expected 'mean_ckpa: 10130', got: $(got mean_ckpa) — 101300 is the double conversion; 10125 is a rescale that divided the calibration too"
printf '%s' "$OUT" | grep -qx 's2_mean_ckpa: 10150' \
  || fail "expected 's2_mean_ckpa: 10150', got: $(got s2_mean_ckpa) — 10132 means the bench offset was scaled away with the error"
printf '%s' "$OUT" | grep -qx 'below_min: 0' \
  || fail "expected 'below_min: 0', got: $(got below_min) — a real reading below 90.00 kPa would be a fault"
printf '%s' "$OUT" | grep -qx 'above_max: 0' \
  || fail "expected 'above_max: 0', got: $(got above_max) — 24 is the whole batch ten times high"

echo "RESULT: PASS the readings are calibrated once and in range (mean 10130, s2 10150, no alerts)"
exit 0
