#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts the rounding rule over the whole batch, not the parcel in the ticket.
#
# The tempting fix is a tolerance: round up past 0.2 kg, down below it. That
# makes p-1 -- the parcel reconciliation flagged -- exactly right, and leaves p-2
# at 2.1 kg quoted as 2.0. So p-2 is the discriminating line and the two totals
# carry it as well.
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
[ -f data/parcels.json ] || {
  echo "RESULT: INVALID data/parcels.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^SHIPPING RUN$' \
  || fail "output is missing the SHIPPING RUN header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'parcels: 8' \
  || fail "expected 'parcels: 8', got: $(got parcels) — data/parcels.json was changed"
printf '%s' "$OUT" | grep -qx 'billable_total_dg: 290' \
  || fail "expected 'billable_total_dg: 290', got: $(got billable_total_dg) — 265 is round-to-nearest; 275 is a tolerance that still rounds 2.1 kg down"
printf '%s' "$OUT" | grep -qx 'charged_total_cents: 6292' \
  || fail "expected 'charged_total_cents: 6292', got: $(got charged_total_cents) — any lower total is quoting below what the carrier bills"
printf '%s' "$OUT" | grep -qx 'p1_billable_dg: 25' \
  || fail "expected 'p1_billable_dg: 25', got: $(got p1_billable_dg) — 20 is the parcel in the ticket, still rounded down"
printf '%s' "$OUT" | grep -qx 'p2_billable_dg: 25' \
  || fail "expected 'p2_billable_dg: 25', got: $(got p2_billable_dg) — 20 means 2.1 kg is still being rounded down â€” a tolerance, not the rule"
printf '%s' "$OUT" | grep -qx 'p5_billable_dg: 10' \
  || fail "expected 'p5_billable_dg: 10', got: $(got p5_billable_dg) — 5 means 0.7 kg is still rounded down to half a kilo"

echo "RESULT: PASS every parcel is billed at the step above its weight (total 290 dg, 6292 cents)"
exit 0
