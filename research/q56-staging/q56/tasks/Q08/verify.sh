#!/usr/bin/env bash
# Imported from Claudette Q56 `verify/Q08.sh` (battery/q50-quality-corpus @ 43d6b34).
#
# Three rewrites, all recorded in task.toml's caveats and none of them touching an assertion:
#   1. `_lib.sh` is inlined — a W8 task directory is self-contained (SPEC §2). Only the four lines
#      Q56 actually uses are carried; the tc/tcre/tcount transcript helpers are dropped as dead
#      (F41: no Q56 verifier reads the transcript).
#   2. `cargo` resolves through the environment per SPEC §8, so the same task runs on the host and
#      in a container.
#   3. A missing toolchain prints INVALID, not FAIL. The donor harness fails such a task, which
#      conflates "the verifier did not run" with "the artifact is wrong" — the F35 lesson, and the
#      whole reason SPEC §8 has a third verdict the donor contract does not.
#
# The hidden test body below is byte-identical to the donor's.

WORKDIR="${1:?workdir}"; TRANSCRIPT="${2:?transcript}"
pass(){ echo "RESULT: PASS — ${1:-ok}"; exit 0; }
fail(){ echo "RESULT: FAIL — ${1:-no reason}"; exit 0; }
invalid(){ echo "RESULT: INVALID — ${1:-the verifier could not run}"; exit 0; }

CARGO="${CARGO:-cargo}"

cd "$WORKDIR" || invalid "cannot cd into workdir $WORKDIR"
# Probe by executing, never by looking: a name on PATH is not a working interpreter (F27).
"$CARGO" --version >/dev/null 2>&1 || invalid "no working cargo on PATH (CARGO=$CARGO)"

# Hidden reviewer tests: left-associative chained subtraction, with precedence
# and mixed operators still intact.
mkdir -p tests
cat > tests/hidden_gate.rs <<'RS'
use q08::evaluate;
#[test] fn precedence() { assert_eq!(evaluate("2 + 3 * 4"), 14); }
#[test] fn single_subtraction() { assert_eq!(evaluate("10 - 3"), 7); }
#[test] fn chained_subtraction() { assert_eq!(evaluate("10 - 3 - 2"), 5); }
#[test] fn long_subtraction_chain() { assert_eq!(evaluate("100 - 10 - 5 - 1"), 84); }
#[test] fn mixed_precedence_and_sub() { assert_eq!(evaluate("20 - 2 * 3 - 4"), 10); }
#[test] fn all_subtraction() { assert_eq!(evaluate("50 - 20 - 10 - 5"), 15); }
RS

out=$("$CARGO" test --test hidden_gate --quiet 2>&1)
if [ $? -ne 0 ]; then
  fail "hidden tests failed: $(echo "$out" | grep -iE 'panicked|assertion|error\[|FAILED' | head -4 | tr '\n' ' ')"
fi
echo "$out" | grep -qE 'test result: ok' \
  && pass "all hidden evaluator tests passed" \
  || fail "no green result: $(echo "$out" | tail -3 | tr '\n' ' ')"
