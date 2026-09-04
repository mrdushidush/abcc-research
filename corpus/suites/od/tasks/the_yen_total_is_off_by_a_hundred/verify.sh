#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts the per-currency totals as well as the reconciliation.
#
# The cheapest way to unblock settlement is to divide the yen side inside
# `till/reconcile.py`. The check then passes and `total_jpy_minor` reads 528000
# where the customers paid 5280 -- so the assertion below is on the total, which
# a change to the comparison cannot reach.
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

printf '%s' "$OUT" | grep -q '^RECONCILE RUN$' \
  || fail "output is missing the RECONCILE RUN header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'orders: 5' \
  || fail "expected 'orders: 5', got: $(got orders) — data/orders.json was changed"
printf '%s' "$OUT" | grep -qx 'reconciled: 5' \
  || fail "expected 'reconciled: 5', got: $(got reconciled) — fewer means the reconciler did not run over every order"
printf '%s' "$OUT" | grep -qx 'total_eur_minor: 1999' \
  || fail "expected 'total_eur_minor: 1999', got: $(got total_eur_minor) — EUR was always right; a change here is a regression"
printf '%s' "$OUT" | grep -qx 'total_jpy_minor: 5280' \
  || fail "expected 'total_jpy_minor: 5280', got: $(got total_jpy_minor) — 528000 means the yen total is still scaled as if yen had cents"
printf '%s' "$OUT" | grep -qx 'total_usd_minor: 11750' \
  || fail "expected 'total_usd_minor: 11750', got: $(got total_usd_minor) — USD was always right; a change here is a regression"

echo "RESULT: PASS every total is in its own currency's minor units (JPY 5280, USD 11750, EUR 1999)"
exit 0
