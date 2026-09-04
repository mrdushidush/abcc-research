#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts every order, because the rule has two halves and the ticket names one.
#
# The tempting fix is to add the percentages. That gives o-1 exactly right -- the
# order in the complaint -- and puts o-2 out at 70% off and o-4 at 60%, where
# finance set the floor at 50. So o-2 and o-4 are the discriminating lines.
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
[ -f data/orders.json ] || {
  echo "RESULT: INVALID data/orders.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^DISCOUNT RUN$' \
  || fail "output is missing the DISCOUNT RUN header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'orders: 4' \
  || fail "expected 'orders: 4', got: $(got orders) — data/orders.json was changed"
printf '%s' "$OUT" | grep -qx 'o1_cents: 7000' \
  || fail "expected 'o1_cents: 7000', got: $(got o1_cents) — 7200 is the compounded price in the complaint"
printf '%s' "$OUT" | grep -qx 'o2_cents: 10000' \
  || fail "expected 'o2_cents: 10000', got: $(got o2_cents) — 6000 is 70% off â€” past the floor margin"
printf '%s' "$OUT" | grep -qx 'o3_cents: 4250' \
  || fail "expected 'o3_cents: 4250', got: $(got o3_cents) — one code, unchanged by any of this"
printf '%s' "$OUT" | grep -qx 'o4_cents: 4000' \
  || fail "expected 'o4_cents: 4000', got: $(got o4_cents) — 3200 is 60% off â€” past the floor margin"
printf '%s' "$OUT" | grep -qx 'payable_total_cents: 25250' \
  || fail "expected 'payable_total_cents: 25250', got: $(got payable_total_cents) — 23900 is compounding; 20450 is adding with no cap"

echo "RESULT: PASS discounts add and stop at the cap (o-1 7000, o-2 10000, o-4 4000)"
exit 0
