#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts all four refunds, because support raised one of them.
#
# The tempting fix is `28 if month == 2 else 30`. It gives x-1 exactly right --
# the cancellation in the ticket -- and leaves x-2, a leap February, 37 cents
# short and x-3, a 31-day month, 103 cents short. Those two are the
# discriminating lines.
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
[ -f data/cancellations.json ] || {
  echo "RESULT: INVALID data/cancellations.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^PRORATE RUN$' \
  || fail "output is missing the PRORATE RUN header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'cancellations: 4' \
  || fail "expected 'cancellations: 4', got: $(got cancellations) — data/cancellations.json was changed"
printf '%s' "$OUT" | grep -qx 'x1_refund_cents: 1928' \
  || fail "expected 'x1_refund_cents: 1928', got: $(got x1_refund_cents) — 2000 is the thirty-day denominator from the ticket"
printf '%s' "$OUT" | grep -qx 'x2_refund_cents: 1965' \
  || fail "expected 'x2_refund_cents: 1965', got: $(got x2_refund_cents) — 1928 means February 2028 was treated as twenty-eight days"
printf '%s' "$OUT" | grep -qx 'x3_refund_cents: 1703' \
  || fail "expected 'x3_refund_cents: 1703', got: $(got x3_refund_cents) — 1600 means July was treated as thirty days"
printf '%s' "$OUT" | grep -qx 'x4_refund_cents: 1250' \
  || fail "expected 'x4_refund_cents: 1250', got: $(got x4_refund_cents) — April really is thirty days; this line separates nothing"
printf '%s' "$OUT" | grep -qx 'refund_total_cents: 6846' \
  || fail "expected 'refund_total_cents: 6846', got: $(got refund_total_cents) — 6850 is the constant; 6706 is the February special case"

echo "RESULT: PASS every refund uses its own month's length (x-1 1928, x-2 1965, x-3 1703)"
exit 0
