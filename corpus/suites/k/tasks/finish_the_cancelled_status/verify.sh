#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# The ticket names ONE symptom: cancelled jobs showing as SLA breaches. Four
# separate modules branch on status and get `cancelled` wrong. This checks all
# four, and it also checks that the fix did not achieve its numbers by switching
# the features off.
#
# Assertions, and what each one closes:
#
#   A. cancelled=4 / other=0 in COUNTS  — summary.py gave it its own bucket
#   B. SLA breaches 2                   — sla.py stopped the clock at cancellation
#   C. CHARGES across 13 job(s), 37615.00p — charges.py stopped billing it
#   D. RETRY candidates 7               — retry.py stopped requeueing it
#
#   POSITIVE CONTROLS, and they are the reason this verifier is trustworthy:
#   E. J-007 and J-008 must STILL be SLA breaches. They are genuinely late
#      done-jobs. Without this, disabling SLA evaluation entirely would satisfy B.
#   F. No cancelled job (J-017..J-020) may appear in the breach or retry lists.
#   G. RETRY must still contain the genuinely failed J-009, J-010, J-023.
#      Without this, returning False from should_retry would satisfy D.
#
# Expected values produced by fixture+refsol:
#   python3 run.py data/jobs.json

set -u

WORKDIR="${1:?usage: verify.sh <workdir> <transcript>}"
TRANSCRIPT="${2:-}"

cd "$WORKDIR" 2>/dev/null || {
  echo "RESULT: INVALID cannot cd to workdir '$WORKDIR'"
  exit 0
}

PY=""
for cand in "${PYTHON:-}" python3 python; do
  [ -z "$cand" ] && continue
  if "$cand" -c '' >/dev/null 2>&1; then PY="$cand"; break; fi
done
if [ -z "$PY" ]; then
  echo "RESULT: INVALID no working python interpreter (tried \$PYTHON, python3, python)"
  exit 0
fi

if [ ! -f run.py ]; then
  echo "RESULT: FAIL run.py is missing from the workdir"
  exit 0
fi
if [ ! -f data/jobs.json ]; then
  echo "RESULT: INVALID data/jobs.json is missing — the fixture was not copied intact"
  exit 0
fi

OUT="$("$PY" run.py data/jobs.json 2>&1)"
STATUS=$?

if [ $STATUS -ne 0 ]; then
  FIRST="$(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-200)"
  echo "RESULT: FAIL run.py exited $STATUS: ${FIRST}"
  exit 0
fi

fail() { echo "RESULT: FAIL $1"; exit 0; }
has() { printf '%s' "$OUT" | grep -aq "$1"; }

has '^JOBS 24 at now=100000' \
  || fail "output does not look like the report; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"

COUNTS_LINE="$(printf '%s' "$OUT" | grep -aE '^COUNTS' || echo '<none>')"
SLA_LINE="$(printf '%s' "$OUT" | grep -aE '^SLA breaches' || echo '<none>')"
CHARGE_LINE="$(printf '%s' "$OUT" | grep -aE '^CHARGES' || echo '<none>')"
RETRY_LINE="$(printf '%s' "$OUT" | grep -aE '^RETRY candidates' || echo '<none>')"

# ── A. cancelled has its own bucket ────────────────────────────────────────
has 'cancelled=4' || fail "COUNTS must show cancelled=4 — got: ${COUNTS_LINE}"
has 'other=0' || fail "COUNTS must show other=0; a status in 'other' is a status nobody looks at — got: ${COUNTS_LINE}"

# ── B/E/F. SLA ─────────────────────────────────────────────────────────────
has '^SLA breaches 2$' \
  || fail "expected 'SLA breaches 2' (only the genuinely late J-007 and J-008) — got: ${SLA_LINE}"

SLA_BLOCK="$(printf '%s' "$OUT" | sed -n '/^SLA breaches/,/^CHARGES/p')"
printf '%s' "$SLA_BLOCK" | grep -aq 'J-007' \
  || fail "J-007 is a genuinely late 'done' job and must STILL be an SLA breach — the SLA check was switched off rather than corrected"
printf '%s' "$SLA_BLOCK" | grep -aq 'J-008' \
  || fail "J-008 is a genuinely late 'done' job and must STILL be an SLA breach"
for j in J-017 J-018 J-019 J-020; do
  printf '%s' "$SLA_BLOCK" | grep -aq "$j" \
    && fail "$j is cancelled and must not be an SLA breach: the clock stops at cancellation"
done

# ── C. charges ─────────────────────────────────────────────────────────────
has 'across 13 job(s)' \
  || fail "expected 13 chargeable jobs (24 minus 5 failed, 4 cancelled, 2 zero-cpu queued) — got: ${CHARGE_LINE}"
has 'CHARGES total 37615.00p' \
  || fail "expected 'CHARGES total 37615.00p' — got: ${CHARGE_LINE}"

# ── D/F/G. retry ───────────────────────────────────────────────────────────
has '^RETRY candidates 7$' \
  || fail "expected 'RETRY candidates 7' — got: ${RETRY_LINE}"

RETRY_BLOCK="$(printf '%s' "$OUT" | sed -n '/^RETRY candidates/,/^NOTIFY/p')"
for j in J-009 J-010 J-023; do
  printf '%s' "$RETRY_BLOCK" | grep -aq "$j" \
    || fail "$j genuinely failed and must STILL be a retry candidate — the retry policy was switched off rather than corrected"
done
for j in J-017 J-018 J-019 J-020; do
  printf '%s' "$RETRY_BLOCK" | grep -aq "$j" \
    && fail "$j is cancelled and must not be retried: a cancellation is an operator instruction"
done

echo "RESULT: PASS cancelled is handled at all four sites, and the genuine breaches and retries survive"
exit 0
