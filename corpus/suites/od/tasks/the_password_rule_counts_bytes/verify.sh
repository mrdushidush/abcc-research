#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts five verdicts and the total, because the review names one sign-up.
#
# The tempting fix counts the ASCII a password reduces to. It refuses c1 -- the
# password in the review -- and also c5, c7 and c8, which are twelve, thirteen
# and twelve characters and are fine. So the accepted count and the three `yes`
# verdicts below are the discriminating lines.
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
[ -f data/candidates.json ] || {
  echo "RESULT: INVALID data/candidates.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^PASSWORD RUN$' \
  || fail "output is missing the PASSWORD RUN header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'candidates: 8' \
  || fail "expected 'candidates: 8', got: $(got candidates) — data/candidates.json was changed"
printf '%s' "$OUT" | grep -qx 'accepted: 4' \
  || fail "expected 'accepted: 4', got: $(got accepted) — 6 is the byte count; 1 means legitimate non-ASCII passwords are being refused"
printf '%s' "$OUT" | grep -qx 'c1_accepted: no' \
  || fail "expected 'c1_accepted: no', got: $(got c1_accepted) — yes means the eight-character password from the review is still accepted"
printf '%s' "$OUT" | grep -qx 'c2_accepted: no' \
  || fail "expected 'c2_accepted: no', got: $(got c2_accepted) — yes means a ten-character password still reaches twelve bytes"
printf '%s' "$OUT" | grep -qx 'c5_accepted: yes' \
  || fail "expected 'c5_accepted: yes', got: $(got c5_accepted) — no means a twelve-character Swedish password is being refused"
printf '%s' "$OUT" | grep -qx 'c7_accepted: yes' \
  || fail "expected 'c7_accepted: yes', got: $(got c7_accepted) — no means a thirteen-character Japanese password is being refused"
printf '%s' "$OUT" | grep -qx 'c8_accepted: yes' \
  || fail "expected 'c8_accepted: yes', got: $(got c8_accepted) — no means cafÃ©-au-lait, twelve characters, is being refused"

echo "RESULT: PASS length is twelve characters, in any alphabet (4 accepted of 8)"
exit 0
