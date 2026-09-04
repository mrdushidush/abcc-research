#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts all five report lines, because the point of the task is that there are
# four consumers and the ticket's symptom is visible in one of them.
#
# The local wrong answer patches `entitlement/access.py`, which is where the
# ticket's symptom is. It makes `premium` correct and leaves `digest`, `seats`
# and `priority` counting lapsed trials -- so the assertions below are on all
# four, and a solution that fixes only the reported one fails on `digest`.
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
[ -f data/accounts.json ] || {
  echo "RESULT: INVALID data/accounts.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^ENTITLEMENT REPORT$' \
  || fail "output is missing the ENTITLEMENT REPORT header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'as_of: 2026-09-01' \
  || fail "expected 'as_of: 2026-09-01', got: $(got as_of) — AS_OF moved â€” the report must stay pinned"
printf '%s' "$OUT" | grep -qx 'accounts: 8' \
  || fail "expected 'accounts: 8', got: $(got accounts) — data/accounts.json was changed"
printf '%s' "$OUT" | grep -qx 'premium: 4' \
  || fail "expected 'premium: 4', got: $(got premium) — 6 means lapsed trials still hold premium features"
printf '%s' "$OUT" | grep -qx 'digest: 4' \
  || fail "expected 'digest: 4', got: $(got digest) — 6 means the digest still mails lapsed trials"
printf '%s' "$OUT" | grep -qx 'seats: 21' \
  || fail "expected 'seats: 21', got: $(got seats) — 36 means lapsed trial seats are still billable"
printf '%s' "$OUT" | grep -qx 'priority: 1' \
  || fail "expected 'priority: 1', got: $(got priority) — 3 means lapsed trials are still on the priority rota"

echo "RESULT: PASS all four consumers honour trial expiry (premium 4, digest 4, seats 21, priority 1)"
exit 0
