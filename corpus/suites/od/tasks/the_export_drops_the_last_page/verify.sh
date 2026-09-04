#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts that the export is complete, not that the audit stopped raising.
#
# The cheapest way to stop the traceback is to make `expo/audit.py` compute what
# it expected from the pages it got. That runs clean on an export that is seven
# rows short -- so the assertions below are on the page count, the last page's
# size and the exported amount, none of which a redefined audit reaches.
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
[ -f data/rows.json ] || {
  echo "RESULT: INVALID data/rows.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^EXPORT RUN$' \
  || fail "output is missing the EXPORT RUN header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'rows: 47' \
  || fail "expected 'rows: 47', got: $(got rows) — data/rows.json was changed"
printf '%s' "$OUT" | grep -qx 'pages: 5' \
  || fail "expected 'pages: 5', got: $(got pages) — 4 means the remainder page is still never emitted"
printf '%s' "$OUT" | grep -qx 'rows_written: 47' \
  || fail "expected 'rows_written: 47', got: $(got rows_written) — 40 means seven rows never reached the sink"
printf '%s' "$OUT" | grep -qx 'last_page_rows: 7' \
  || fail "expected 'last_page_rows: 7', got: $(got last_page_rows) — 10 means the short final page is still missing"
printf '%s' "$OUT" | grep -qx 'amount_written: 112800' \
  || fail "expected 'amount_written: 112800', got: $(got amount_written) — 82000 is the warehouse total running under the source system"

echo "RESULT: PASS the export carries every row including the short last page (5 pages, 47 rows, 112800)"
exit 0
