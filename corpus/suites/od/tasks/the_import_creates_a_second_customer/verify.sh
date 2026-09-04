#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts the shape of the store after the import, not that the import survived.
#
# The cheapest way to stop the traceback is to make `crm/link.py` count instead
# of raise. That runs clean and leaves seven customer rows for four people, with
# one person's three orders on three separate rows -- so the assertions below are
# on the row count and the largest history, which a relaxed check cannot reach.
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
[ -f data/store.json ] || {
  echo "RESULT: INVALID data/store.json is missing — the fixture was not copied intact"
  exit 0
}
[ -f data/incoming.json ] || {
  echo "RESULT: INVALID data/incoming.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^CRM IMPORT$' \
  || fail "output is missing the CRM IMPORT header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'incoming: 6' \
  || fail "expected 'incoming: 6', got: $(got incoming) — data/incoming.json was changed"
printf '%s' "$OUT" | grep -qx 'customers: 4' \
  || fail "expected 'customers: 4', got: $(got customers) — 7 means the import is still creating a second row per person"
printf '%s' "$OUT" | grep -qx 'distinct_people: 4' \
  || fail "expected 'distinct_people: 4', got: $(got distinct_people) — the folded count was always 4; it is not the discriminating number"
printf '%s' "$OUT" | grep -qx 'orders_linked: 6' \
  || fail "expected 'orders_linked: 6', got: $(got orders_linked) — fewer means an order was dropped rather than attached"
printf '%s' "$OUT" | grep -qx 'largest_customer_orders: 3' \
  || fail "expected 'largest_customer_orders: 3', got: $(got largest_customer_orders) — 1 means Ana's three orders are still on three different rows"

echo "RESULT: PASS one row per person and every order attached to it (customers 4, orders 6, largest 3)"
exit 0
