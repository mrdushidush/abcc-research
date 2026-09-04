#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts what all four registries knew, not merely that the tax stopped being zero.
#
# The local wrong answer adds the rate and nothing else. `tax_cents` moves off
# 10499 -- and lands on 27749 rather than 21999, because the Irish book order is
# now taxed at 23% instead of being zero-rated. `labelled`, `filings` and
# `exempt_lines` all stay where the bug left them.
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

printf '%s' "$OUT" | grep -q '^TAX QUOTE RUN$' \
  || fail "output is missing the TAX QUOTE RUN header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'orders: 6' \
  || fail "expected 'orders: 6', got: $(got orders) — data/orders.json was changed"
printf '%s' "$OUT" | grep -qx 'unsupported: 0' \
  || fail "expected 'unsupported: 0', got: $(got unsupported) — EU-IE is already in regions.SUPPORTED; removing it is not the fix"
printf '%s' "$OUT" | grep -qx 'tax_cents: 21999' \
  || fail "expected 'tax_cents: 21999', got: $(got tax_cents) — 10499 is the missing rate; 27749 is the rate added without the exemption"
printf '%s' "$OUT" | grep -qx 'labelled: 6' \
  || fail "expected 'labelled: 6', got: $(got labelled) — 4 means two Irish invoices still have an unnamed tax line"
printf '%s' "$OUT" | grep -qx 'filings: 5' \
  || fail "expected 'filings: 5', got: $(got filings) — 4 means compliance has no filing period for Ireland"
printf '%s' "$OUT" | grep -qx 'exempt_lines: 2' \
  || fail "expected 'exempt_lines: 2', got: $(got exempt_lines) — 1 means the Irish book order is being taxed"

echo "RESULT: PASS EU-IE is live in all four registries (tax 21999, labelled 6, filings 5, exempt 2)"
exit 0
