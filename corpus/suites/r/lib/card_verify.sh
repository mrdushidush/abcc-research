#!/usr/bin/env bash
# card_verify.sh <workdir> <transcript> <target-file> <hidden.rs> [stdin-text]  — SPEC.md §8
#
# The shared verifier for every R task. Each task's own verify.sh is one line that calls this
# with its card's target file and hidden test.
#
# WHAT IT GRADES, in three independent parts, all required for a PASS:
#
#   behaviour  the card author's red test, appended to the target file as its OWN module
#              `#[cfg(test)] mod w8_hidden { use super::*; ... }`. Appended, not merged, so it
#              cannot collide with anything the subject wrote into `mod tests`. It is red on the
#              unfixed tree (gate point 1) — that is what closes F832 for the bench: the subject's
#              own test is never what decides the verdict.
#   others     every other test in the claudette lib still passes (the same run).
#   standard   `cargo fmt --check` and `cargo clippy --all-targets -D warnings` on the tree AS THE
#              SUBJECT LEFT IT, before the hidden module is added — the merge requirement F673
#              found the model is graded by. Every R prompt states it.
#
# The verdict line names all three, so a post-pass can split "right fix, lint wrong" from
# "wrong fix" without re-running anything.
#
# IT NEVER BUILDS IN THE WORK DIR. The tree is copied (minus target/) to one fixed scratch path
# and built there against one shared CARGO_TARGET_DIR. A fixed path keeps the local crates'
# metadata hashes stable across cells, so the target dir is reused instead of growing by a
# claudette-sized build per cell, and the work dir stays exactly what the subject left.
#
# ⚠ stdin-text (SHELL-10): the test is only red when the test binary HAS a live stdin — the
# defect is a child that inherits it. With stdin at EOF the unfixed tree passes (F832, recorded
# 2026-09-21: `echo x | cargo test` reads 24 bytes). Tasks that do not pass it get /dev/null.

set -u

WORKDIR="${1:?usage: card_verify.sh <workdir> <transcript> <target> <hidden.rs> [stdin-text]}"
TARGET="${3:?target file}"
HIDDEN="${4:?hidden test}"
STDIN_TEXT="${5-}"

command -v cargo >/dev/null 2>&1 || { echo "RESULT: INVALID cargo is not on PATH"; exit 0; }
[ -f "$HIDDEN" ] || { echo "RESULT: INVALID hidden test $HIDDEN is missing"; exit 0; }
[ -d "$WORKDIR" ] || { echo "RESULT: INVALID cannot find workdir '$WORKDIR'"; exit 0; }
[ -f "$WORKDIR/Cargo.toml" ] \
  || { echo "RESULT: INVALID no Cargo.toml in the workdir — the fixture was not materialized"; exit 0; }
[ -f "$WORKDIR/$TARGET" ] || { echo "RESULT: FAIL $TARGET is gone from the tree"; exit 0; }

SCRATCH="${W8_R_SCRATCH:-${TMPDIR:-/tmp}/w8-r-verify}"
export CARGO_TARGET_DIR="${W8_CARGO_TARGET_DIR:-$SCRATCH/target}"
export CARGO_TERM_COLOR=never
TREE="$SCRATCH/tree"
LOGS="$SCRATCH/logs"
rm -rf "$TREE" "$LOGS"
mkdir -p "$TREE" "$LOGS" "$CARGO_TARGET_DIR"

# tar, not cp -r: it can leave a subject's own target/ (gigabytes, if it built in place) behind.
( cd "$WORKDIR" && tar --exclude=./target --exclude=./.git -cf - . ) | ( cd "$TREE" && tar -xf - ) \
  || { echo "RESULT: INVALID could not copy the workdir to $TREE"; exit 0; }
cd "$TREE" || { echo "RESULT: INVALID cannot cd to $TREE"; exit 0; }

first() { grep -m1 -E "$1" "$2" | tr -d '\r' | cut -c1-160; }

# ── standard, on the subject's tree ──────────────────────────────────────────────────────────
if cargo fmt --all -- --check >"$LOGS/fmt.log" 2>&1; then
  FMT=pass
else
  FMT=fail
  FMT_WHY="$(first '^Diff in' "$LOGS/fmt.log")"
fi
if cargo clippy --workspace --all-targets -- -D warnings >"$LOGS/clippy.log" 2>&1; then
  CLIPPY=pass
else
  CLIPPY=fail
  CLIPPY_WHY="$(first '^error' "$LOGS/clippy.log")"
fi

# ── behaviour + others, one run ──────────────────────────────────────────────────────────────
{ printf '\n'; cat "$HIDDEN"; } >>"$TARGET"
if [ -n "$STDIN_TEXT" ]; then
  printf '%s\n' "$STDIN_TEXT" | cargo test -p claudette --lib >"$LOGS/test.log" 2>&1
else
  cargo test -p claudette --lib </dev/null >"$LOGS/test.log" 2>&1
fi
tr -d '\r' <"$LOGS/test.log" >"$LOGS/test.lf"

if ! grep -qE '^test result:' "$LOGS/test.lf"; then
  # No test ran at all: the tree (or the hidden module against the subject's API) does not build.
  WHY="$(first '^error' "$LOGS/test.lf")"
  echo "RESULT: FAIL behaviour=nobuild others=nobuild fmt=$FMT clippy=$CLIPPY: the lib test build failed: ${WHY:-see $LOGS/test.log}"
  exit 0
fi

HIDDEN_OK="$(grep -cE '^test (.*::)?w8_hidden::[A-Za-z0-9_]+ \.\.\. ok$' "$LOGS/test.lf")"
HIDDEN_BAD="$(grep -E '^test (.*::)?w8_hidden::[A-Za-z0-9_]+ \.\.\. FAILED$' "$LOGS/test.lf" | sed -E 's/^test (.*) \.\.\. FAILED$/\1/' | tr '\n' ' ')"
OTHERS_BAD="$(grep -E '^test .* \.\.\. FAILED$' "$LOGS/test.lf" | grep -v 'w8_hidden::' | sed -E 's/^test (.*) \.\.\. FAILED$/\1/' | tr '\n' ' ')"
EXPECTED="$(grep -cE '^ *#\[test\]' "$HIDDEN")"

if [ "$HIDDEN_OK" -eq 0 ] && [ -z "$HIDDEN_BAD" ]; then
  echo "RESULT: INVALID the hidden module ran no tests — was it appended inside another item?"
  exit 0
fi
if [ -z "$HIDDEN_BAD" ] && [ "$HIDDEN_OK" -ge "$EXPECTED" ]; then BEHAVIOUR=pass; else BEHAVIOUR=fail; fi
if [ -z "$OTHERS_BAD" ]; then
  OTHERS=pass
else
  # ⚠ claudette's lib suite has env-mutating tests that race under the parallel runner: measured
  # 2026-09-23 on the SHELL-04 refsol, `list_dir_classifies_file_and_subdir_correctly` failed 2 of
  # 2 on "path is outside $HOME (…claudette-temphome-…)" — another test's temporary $HOME — and a
  # different test failed on the untouched base. So a failing OTHER test gets exactly one serial
  # re-run of itself alone. The hidden test never gets one: its verdict is the first run's.
  # shellcheck disable=SC2086 # the names are split into one filter each on purpose
  NAMED="$(printf '%s' "$OTHERS_BAD" | wc -w | tr -d ' ')"
  if cargo test -p claudette --lib -- --exact --test-threads=1 $OTHERS_BAD </dev/null \
    >"$LOGS/retry.log" 2>&1 \
    && tr -d '\r' <"$LOGS/retry.log" | grep -qE "^test result: ok\. $NAMED passed"; then
    OTHERS=flaky
  else
    OTHERS=fail
  fi
fi

TAGS="behaviour=$BEHAVIOUR others=$OTHERS fmt=$FMT clippy=$CLIPPY"
case "$BEHAVIOUR$OTHERS$FMT$CLIPPY" in
  passpasspasspass)
    echo "RESULT: PASS $TAGS: the card's hidden test passes ($HIDDEN_OK), nothing else broke, fmt and clippy are clean"
    exit 0 ;;
  passflakypasspass)
    echo "RESULT: PASS $TAGS: the card's hidden test passes ($HIDDEN_OK); red in the parallel run and green alone: $OTHERS_BAD"
    exit 0 ;;
esac
WHY=""
[ "$BEHAVIOUR" = fail ] && WHY="$WHY hidden test red: ${HIDDEN_BAD:-only $HIDDEN_OK of $EXPECTED ran};"
[ "$OTHERS" = fail ] && WHY="$WHY other tests red: $OTHERS_BAD;"
[ "$FMT" = fail ] && WHY="$WHY fmt: ${FMT_WHY:-see $LOGS/fmt.log};"
[ "$CLIPPY" = fail ] && WHY="$WHY clippy: ${CLIPPY_WHY:-see $LOGS/clippy.log};"
echo "RESULT: FAIL $TAGS:$WHY"
exit 0
