#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts the roll-up's numbers, not merely that it stopped crashing.
#
# That distinction is the entire task. The symptom is a ZeroDivisionError in
# stats.py, and the cheapest way to silence it is a guard at the crash site.
# That guard works, produces no error, and silently discards every rev-B
# sample -- half the fleet -- leaving a report that looks completely normal.
# So passing requires the CORRECT sample count and the CORRECT means, which
# are only reachable by fixing the flag normalisation upstream in ingest.py.
#
# Expected values were produced by fixture+refsol and are reproducible with:
#   python3 run.py data/samples.jsonl

set -u

WORKDIR="${1:?usage: verify.sh <workdir> <transcript>}"
TRANSCRIPT="${2:-}"

cd "$WORKDIR" 2>/dev/null || {
  echo "RESULT: INVALID cannot cd to workdir '$WORKDIR'"
  exit 0
}

# Resolve an interpreter BY EXECUTING IT, never by looking (SPEC.md §8): on
# Windows a Microsoft Store alias shim named python3.exe sits on PATH, is found
# by `command -v`, and prints an advert instead of running the code.
PY=""
for cand in "${PYTHON:-}" python3 python; do
  [ -z "$cand" ] && continue
  if "$cand" -c '' >/dev/null 2>&1; then PY="$cand"; break; fi
done
if [ -z "$PY" ]; then
  echo "RESULT: INVALID no working python interpreter (tried \$PYTHON, python3, python)"
  exit 0
fi

if [ ! -f run.py ]; then
  echo "RESULT: FAIL run.py is missing from the workdir"
  exit 0
fi
if [ ! -f data/samples.jsonl ]; then
  echo "RESULT: INVALID data/samples.jsonl is missing — the fixture was not copied intact"
  exit 0
fi

OUT="$("$PY" run.py data/samples.jsonl 2>&1)"
STATUS=$?

if [ $STATUS -ne 0 ]; then
  FIRST="$(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-200)"
  echo "RESULT: FAIL run.py exited $STATUS: ${FIRST}"
  exit 0
fi

fail() { echo "RESULT: FAIL $1"; exit 0; }

# Guard against a solution that prints the right lines without running the
# pipeline: the header must be present and the pipeline must have produced
# the full 12 windows.
printf '%s' "$OUT" | grep -q '^TELEMETRY ROLL-UP$' \
  || fail "output is missing the TELEMETRY ROLL-UP header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"

printf '%s' "$OUT" | grep -qx 'windows: 12' \
  || fail "expected 'windows: 12', got: $(printf '%s' "$OUT" | grep -E '^windows:' || echo '<no windows line>')"

# THE discriminating assertion. 54 is every usable sample from BOTH firmware
# revisions. 30 is what you get when rev B is still being dropped -- which is
# exactly what a guard at the crash site produces.
printf '%s' "$OUT" | grep -qx 'samples: 54' \
  || fail "expected 'samples: 54' (both firmware revisions accepted), got: $(printf '%s' "$OUT" | grep -E '^samples:' || echo '<no samples line>') — 30 means rev-B samples are still being dropped"

check_channel() {
  local chan="$1" want_n="$2" want_mean="$3"
  local line
  line="$(printf '%s' "$OUT" | grep -E "^channel ${chan} " || true)"
  [ -n "$line" ] || fail "no report line for channel ${chan}"
  printf '%s' "$line" | grep -q "n=${want_n} " \
    || fail "${chan}: expected n=${want_n}, got: ${line}"
  printf '%s' "$line" | grep -q "mean=${want_mean}" \
    || fail "${chan}: expected mean=${want_mean}, got: ${line}"
}

check_channel temp_c         15 25.450
check_channel pressure_kpa   15 381.450
check_channel flow_lpm       12 66.458
check_channel vibration_mm_s 12 9.708

echo "RESULT: PASS all four channels report both firmware revisions (54 samples, 12 windows)"
exit 0
