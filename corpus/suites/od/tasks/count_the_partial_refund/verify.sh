#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts all four renderers' totals, because the total is computed four times.
#
# The local wrong answer patches `statement/csv_out.py`, the renderer in the
# ticket. It makes `csv_total` correct and leaves the other three at 15000 --
# which is not merely stale, it is the partial refund added instead of
# subtracted, so the three disagree with the fixed one by twice the refund.
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
[ -f data/ledger.json ] || {
  echo "RESULT: INVALID data/ledger.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^STATEMENT TOTALS$' \
  || fail "output is missing the STATEMENT TOTALS header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'transactions: 4' \
  || fail "expected 'transactions: 4', got: $(got transactions) — data/ledger.json was changed"
printf '%s' "$OUT" | grep -qx 'csv_total: 9000' \
  || fail "expected 'csv_total: 9000', got: $(got csv_total) — 15000 is the partial refund added instead of subtracted"
printf '%s' "$OUT" | grep -qx 'json_total: 9000' \
  || fail "expected 'json_total: 9000', got: $(got json_total) — 15000 means the portal still adds the partial refund"
printf '%s' "$OUT" | grep -qx 'html_total: 9000' \
  || fail "expected 'html_total: 9000', got: $(got html_total) — 15000 means the emailed statement still adds the partial refund"
printf '%s' "$OUT" | grep -qx 'summary_total: 9000' \
  || fail "expected 'summary_total: 9000', got: $(got summary_total) — 15000 means the support console still adds the partial refund"

echo "RESULT: PASS every renderer subtracts the partial refund (csv, json, html, summary all 9000)"
exit 0
