#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts the order the file will be WRITTEN in, not that the pre-flight passed.
#
# The cheapest way to stop the refusal is to sort inside `ledgerout/sequence.py`.
# The pre-flight then passes on a file whose second record is seq-10 and whose
# last is seq-9 -- so the assertions below are on the emitted order and on the
# running balance, neither of which the pre-flight touches.
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
[ -f data/records.json ] || {
  echo "RESULT: INVALID data/records.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^LEDGER RUN$' \
  || fail "output is missing the LEDGER RUN header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'records: 12' \
  || fail "expected 'records: 12', got: $(got records) — data/records.json was changed"
printf '%s' "$OUT" | grep -qx 'first_written: seq-1' \
  || fail "expected 'first_written: seq-1', got: $(got first_written) — seq-1 sorts first either way; it is not the discriminating line"
printf '%s' "$OUT" | grep -qx 'second_written: seq-2' \
  || fail "expected 'second_written: seq-2', got: $(got second_written) — seq-10 means the file is still ordered as text"
printf '%s' "$OUT" | grep -qx 'last_written: seq-12' \
  || fail "expected 'last_written: seq-12', got: $(got last_written) — seq-9 means the file is still ordered as text"
printf '%s' "$OUT" | grep -qx 'balance_after_two: 300' \
  || fail "expected 'balance_after_two: 300', got: $(got balance_after_two) — 1100 is the balance the reader would rebuild from the wrong order"

echo "RESULT: PASS the file is written in sequence order (seq-1, seq-2, ... seq-12; balance 300 after two)"
exit 0
