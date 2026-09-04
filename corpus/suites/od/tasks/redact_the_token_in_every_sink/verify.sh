#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Audits what each sink actually rendered, with a canary that is independent of
# the scrubber -- so this grades the payload and not the call site.
#
# The local wrong answer patches `observe/errors.py`, the sink in the security
# report. It makes `leaked_errors` zero and leaves three keys in the log file and
# one in a metric tag, so the assertions below cover all four sinks and a fix at
# the reported one fails on `leaked_logfile`.
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
[ -f data/events.json ] || {
  echo "RESULT: INVALID data/events.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^SINK AUDIT$' \
  || fail "output is missing the SINK AUDIT header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'events: 5' \
  || fail "expected 'events: 5', got: $(got events) — data/events.json was changed"
printf '%s' "$OUT" | grep -qx 'leaked_console: 0' \
  || fail "expected 'leaked_console: 0', got: $(got leaked_console) — the console already scrubbed; a leak here is a regression"
printf '%s' "$OUT" | grep -qx 'leaked_logfile: 0' \
  || fail "expected 'leaked_logfile: 0', got: $(got leaked_logfile) — 3 means the structured log still writes live keys to disk"
printf '%s' "$OUT" | grep -qx 'leaked_errors: 0' \
  || fail "expected 'leaked_errors: 0', got: $(got leaked_errors) — 2 means the error tracker still receives live keys"
printf '%s' "$OUT" | grep -qx 'leaked_metrics: 0' \
  || fail "expected 'leaked_metrics: 0', got: $(got leaked_metrics) — 1 means a live key is still going out as a metric tag"

echo "RESULT: PASS no sink leaks a live key (console 0, logfile 0, errors 0, metrics 0)"
exit 0
