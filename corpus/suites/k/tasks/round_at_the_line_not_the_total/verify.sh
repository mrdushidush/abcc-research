#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# The prompt reports ONE invoice. This checks all EIGHTEEN, and that is the task.
#
# Three layers of assertion, each closing a different wrong answer:
#
#   1. MISMATCHES 0 of 18  — every invoice's printed lines must sum to its printed
#      total. Closes "fix the one invoice the ticket named".
#   2. Every expected total — the 18 correct values. Eight of them differ from what
#      round-at-the-end produces, and they differ IN BOTH DIRECTIONS: five need the
#      total higher, three need it lower. That closes the other tempting local
#      answer, changing the rounding direction at the end (ceil instead of half-up),
#      which would satisfy the five and break the three.
#   3. AUDIT clean — no linesum_mismatch, no export_mismatch, no unquantized_total.
#      Closes a display-only fix that leaves the ledger exports disagreeing.
#
# Expected values were produced by fixture+refsol and are reproducible with:
#   python3 run.py data/orders.json

set -u

WORKDIR="${1:?usage: verify.sh <workdir> <transcript>}"
TRANSCRIPT="${2:-}"

cd "$WORKDIR" 2>/dev/null || {
  echo "RESULT: INVALID cannot cd to workdir '$WORKDIR'"
  exit 0
}

# Resolve an interpreter BY EXECUTING IT, never by looking (SPEC.md §8): Windows
# ships a Store alias shim named python3.exe that `command -v` finds and that
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

if [ ! -f run.py ]; then
  echo "RESULT: FAIL run.py is missing from the workdir"
  exit 0
fi
if [ ! -f data/orders.json ]; then
  echo "RESULT: INVALID data/orders.json is missing — the fixture was not copied intact"
  exit 0
fi

OUT="$("$PY" run.py data/orders.json 2>&1)"
STATUS=$?

if [ $STATUS -ne 0 ]; then
  FIRST="$(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-200)"
  echo "RESULT: FAIL run.py exited $STATUS: ${FIRST}"
  exit 0
fi

fail() { echo "RESULT: FAIL $1"; exit 0; }

printf '%s' "$OUT" | grep -aq 'INVOICE INV-1001' \
  || fail "output does not look like the receipt batch; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"

# ── Layer 1: every invoice reconciles ───────────────────────────────────────
printf '%s' "$OUT" | grep -aqx 'MISMATCHES 0 of 18' \
  || fail "expected 'MISMATCHES 0 of 18', got: $(printf '%s' "$OUT" | grep -aE '^MISMATCHES' || echo '<no MISMATCHES line>') — the ticket named INV-1005, but the same defect affects eight invoices in this batch"

# ── Layer 2: every total is the round-per-line value ────────────────────────
# `!` marks the eight the round-at-the-end code gets wrong. Direction noted
# because it is what makes a ceil/floor hack fail.
# 🚨 Compares the NUMBER, never the currency glyph.
#
# The receipt prints `£`, and Python on Windows encodes stdout as cp1252 — so the
# glyph arrives as the single byte 0xA3 while this file, being UTF-8, contains
# 0xC2 0xA3. Matching the glyph therefore FAILED against a CORRECT solution and
# reported it as a wrong total. That is the F8 shape and it is a verifier defect,
# not a subject defect: the instrument was reporting its own encoding assumption
# as the artifact being wrong. Extracting the digits sidesteps the question
# entirely and works on any platform, in any locale, for any currency symbol.
# Drop every byte above ASCII before matching, which removes the currency glyph
# whatever it encoded to, and leaves `INV-1001 total=1212.88 linesum=... ok`.
# `sed` and `grep` both refuse to match a pattern across an invalid multibyte
# sequence, so normalising first is what makes this work in any locale rather
# than only in the one the author happened to have.
ascii() { printf '%s' "$1" | tr -d '\200-\377'; }

check_total() {
  local num="$1" want="$2"
  local line
  line="$(ascii "$(printf '%s' "$OUT" | grep -aE "^${num} total=" || true)")"
  [ -n "$line" ] || fail "no summary line for ${num}"
  case "$line" in
    *"total=${want} "*) : ;;
    *) fail "${num}: expected total ${want} — line: ${line}" ;;
  esac
}

check_total INV-1001 1212.88
check_total INV-1002 181.65
check_total INV-1003 477.25
check_total INV-1004 2350.31
check_total INV-1005 4888.00   # ! the reported one; round-at-the-end gives 4887.99 (higher)
check_total INV-1006 165.46
check_total INV-1007 952.97
check_total INV-1008 387.13
check_total INV-1009 3788.76   # ! 3788.75 (higher)
check_total INV-1010 1568.73
check_total INV-1011 57.59
check_total INV-1012 1638.69
check_total INV-1013 2223.73   # ! 2223.72 (higher)
check_total INV-1014 75.63     # ! 75.64  (LOWER)
check_total INV-1015 57.30     # ! 57.31  (LOWER)
check_total INV-1016 346.58    # ! 346.57 (higher)
check_total INV-1017 84.66     # ! 84.67  (LOWER)
check_total INV-1018 4030.32   # ! 4030.31 (higher)

# ── Layer 3: the audit must be clean ───────────────────────────────────────
printf '%s' "$OUT" | grep -aqx 'AUDIT clean' \
  || fail "audit is not clean: $(printf '%s' "$OUT" | grep -aA4 '^AUDIT' | tr '\n' ' ' | cut -c1-240)"

echo "RESULT: PASS all 18 invoices reconcile and every total is the round-per-line value"
exit 0
