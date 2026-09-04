#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts every regional median, not the one the ticket names.
#
# The tempting fix is the midpoint with integer division. It produces the
# ticket's 4300 for north and turns south -- which the fixture was accidentally
# right about -- into 1000 where the standard says 1001. So `median_south_cents`
# is the discriminating line.
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

printf '%s' "$OUT" | grep -q '^MEDIAN RUN$' \
  || fail "output is missing the MEDIAN RUN header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'orders: 11' \
  || fail "expected 'orders: 11', got: $(got orders) — data/orders.json was changed"
printf '%s' "$OUT" | grep -qx 'median_all_cents: 1001' \
  || fail "expected 'median_all_cents: 1001', got: $(got median_all_cents) — eleven orders is an odd cohort; this line does not separate anything"
printf '%s' "$OUT" | grep -qx 'median_east_cents: 205' \
  || fail "expected 'median_east_cents: 205', got: $(got median_east_cents) — three orders is an odd cohort"
printf '%s' "$OUT" | grep -qx 'median_north_cents: 4300' \
  || fail "expected 'median_north_cents: 4300', got: $(got median_north_cents) — 4400 is the upper middle, which is the number in the ticket"
printf '%s' "$OUT" | grep -qx 'median_south_cents: 1001' \
  || fail "expected 'median_south_cents: 1001', got: $(got median_south_cents) — 1000 is a truncated midpoint â€” the standard rounds half up"

echo "RESULT: PASS every median is the midpoint rounded half up (north 4300, south 1001)"
exit 0
