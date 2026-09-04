#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts BOTH consumers of the calendar, and the lookup's own answer.
#
# The cheapest way to stop the exception is to nudge the due date inside
# `worksched/sla.py`. That produces exactly the right ticket dates -- so the
# ticket assertions below cannot separate it -- and leaves every payment due date
# on a closed day. `invoice_due_closed` and `holidays_2026` are the discriminating
# lines.
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
[ -f data/work.json ] || {
  echo "RESULT: INVALID data/work.json is missing — the fixture was not copied intact"
  exit 0
}
[ -f data/closures.json ] || {
  echo "RESULT: INVALID data/closures.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^CALENDAR RUN$' \
  || fail "output is missing the CALENDAR RUN header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'tickets: 6' \
  || fail "expected 'tickets: 6', got: $(got tickets) — data/work.json was changed"
printf '%s' "$OUT" | grep -qx 'holidays_2026: 5' \
  || fail "expected 'holidays_2026: 5', got: $(got holidays_2026) — 4 is 2025's table: the lookup is still a year off"
printf '%s' "$OUT" | grep -qx 'ticket_due_closed: 0' \
  || fail "expected 'ticket_due_closed: 0', got: $(got ticket_due_closed) — a due date on a closed day is not a due date"
printf '%s' "$OUT" | grep -qx 'invoice_due_closed: 0' \
  || fail "expected 'invoice_due_closed: 0', got: $(got invoice_due_closed) — 4 means collections is still chasing on days the office is shut"
printf '%s' "$OUT" | grep -qx 'first_ticket_due: 2026-04-06' \
  || fail "expected 'first_ticket_due: 2026-04-06', got: $(got first_ticket_due) — 2026-04-03 is Good Friday, which the lookup did not know about"
printf '%s' "$OUT" | grep -qx 'last_invoice_due: 2026-12-30' \
  || fail "expected 'last_invoice_due: 2026-12-30', got: $(got last_invoice_due) — 2026-12-28 is a company holiday the payment arithmetic walked straight through"

echo "RESULT: PASS both consumers run on this year's holidays (5 holidays, no due date on a closed day)"
exit 0
