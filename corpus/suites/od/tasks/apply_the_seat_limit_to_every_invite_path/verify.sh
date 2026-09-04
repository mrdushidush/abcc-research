#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts the accepted count on every path AND the seat total the run ends at.
#
# The local wrong answer caps `invites/bulk_csv.py`, which is where finance traced
# the overage. It makes `accepted_bulk` correct and leaves SSO and the API adding
# five more members with no seats left -- so the assertions below cover all four
# paths, and a fix at the traced path fails on `accepted_sso`.
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
[ -f data/pending.json ] || {
  echo "RESULT: INVALID data/pending.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^INVITE RUN$' \
  || fail "output is missing the INVITE RUN header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'seat_limit: 10' \
  || fail "expected 'seat_limit: 10', got: $(got seat_limit) — data/pending.json was changed"
printf '%s' "$OUT" | grep -qx 'accepted_direct: 2' \
  || fail "expected 'accepted_direct: 2', got: $(got accepted_direct) — the direct path already checked the limit; a change here is a regression"
printf '%s' "$OUT" | grep -qx 'accepted_bulk: 1' \
  || fail "expected 'accepted_bulk: 1', got: $(got accepted_bulk) — 4 means the CSV importer still ignores the limit"
printf '%s' "$OUT" | grep -qx 'accepted_sso: 0' \
  || fail "expected 'accepted_sso: 0', got: $(got accepted_sso) — 3 means SSO provisioning still adds members with no seats left"
printf '%s' "$OUT" | grep -qx 'accepted_api: 0' \
  || fail "expected 'accepted_api: 0', got: $(got accepted_api) — 2 means the API still adds members with no seats left"
printf '%s' "$OUT" | grep -qx 'seats_used: 10' \
  || fail "expected 'seats_used: 10', got: $(got seats_used) — anything above 10 breaks the invariant in docs/seats.md"

echo "RESULT: PASS every invite path enforces the seat limit (direct 2, bulk 1, sso 0, api 0, seats_used 10)"
exit 0
