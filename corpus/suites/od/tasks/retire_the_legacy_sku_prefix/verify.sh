#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Replays yesterday's traffic and asserts how much of it resolved on EACH reader.
#
# The local wrong answer folds in `catalog/search.py`, which is the reader the
# support ticket is about. It makes `search_hits` correct and leaves `cart_priced`
# and `inventory_applied` at 1 of 3 -- so the assertions below cover all four
# readers, and a fix at the ticket fails on `cart_priced`.
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
[ -f data/products.json ] || {
  echo "RESULT: INVALID data/products.json is missing — the fixture was not copied intact"
  exit 0
}
[ -f data/traffic.json ] || {
  echo "RESULT: INVALID data/traffic.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^CATALOG RECONCILIATION$' \
  || fail "output is missing the CATALOG RECONCILIATION header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'products: 6' \
  || fail "expected 'products: 6', got: $(got products) — data/products.json was changed"
printf '%s' "$OUT" | grep -qx 'search_hits: 4' \
  || fail "expected 'search_hits: 4', got: $(got search_hits) — 1 means only the one canonical query resolves"
printf '%s' "$OUT" | grep -qx 'cart_priced: 3' \
  || fail "expected 'cart_priced: 3', got: $(got cart_priced) — 1 means the cart still drops legacy-spelled lines"
printf '%s' "$OUT" | grep -qx 'inventory_applied: 3' \
  || fail "expected 'inventory_applied: 3', got: $(got inventory_applied) — 1 means the warehouse feed still discards its own spelling"
printf '%s' "$OUT" | grep -qx 'export_rows: 6' \
  || fail "expected 'export_rows: 6', got: $(got export_rows) — the export already folded; a change here is a regression"

echo "RESULT: PASS every reader folds the SKU (search 4, cart 3, inventory 3, export 6)"
exit 0
