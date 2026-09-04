#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts every channel's audience count, not merely that the plan runs.
#
# The local wrong answer patches `outbound/winback.py`, which is the channel the
# ticket complains about. It makes `winback` correct and leaves `promo_sms` and
# `push` mailing the three suppressed contacts -- so the assertions below cover
# all four channels, and a fix at the complaint fails on `promo_sms`.
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
[ -f data/contacts.json ] || {
  echo "RESULT: INVALID data/contacts.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^OUTBOUND PLAN$' \
  || fail "output is missing the OUTBOUND PLAN header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'contacts: 7' \
  || fail "expected 'contacts: 7', got: $(got contacts) — data/contacts.json was changed"
printf '%s' "$OUT" | grep -qx 'newsletter: 4' \
  || fail "expected 'newsletter: 4', got: $(got newsletter) — the newsletter already honoured the flag; a change here is a regression"
printf '%s' "$OUT" | grep -qx 'winback: 2' \
  || fail "expected 'winback: 2', got: $(got winback) — 4 means the win-back campaign still mails suppressed contacts"
printf '%s' "$OUT" | grep -qx 'promo_sms: 3' \
  || fail "expected 'promo_sms: 3', got: $(got promo_sms) — 6 means the Tuesday SMS still texts suppressed contacts"
printf '%s' "$OUT" | grep -qx 'push: 4' \
  || fail "expected 'push: 4', got: $(got push) — 5 means the push campaign still reaches a suppressed contact"

echo "RESULT: PASS every marketing channel honours do-not-contact (newsletter 4, winback 2, promo_sms 3, push 4)"
exit 0
