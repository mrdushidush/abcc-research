#!/usr/bin/env bash
# gate-task.sh <task-dir> [...]  — SPEC.md §9's three points, run, not assumed.
#
#   gate(task) := verify(pre_state)        == FAIL
#              && verify(fixture + refsol) == PASS
#              && verify(fixture + sham)   == FAIL
#
# It prints the `[[gate.evidence]]` lines a `task.toml` owes, so the evidence in
# a task file is a transcript rather than a claim. Nothing here writes to the
# corpus; paste what it prints.
#
# 🚨 IT ALSO RUNS THE VISIBLE TESTS, and that is not decoration. The Judge probe
# needs the SHAM TREE TO BE GREEN on the deterministic ladder -- if
# `python -m pytest -q` fails on fixture+sham, the ladder refuses the tree, the
# reviewer is shown a red rung and the tier stops measuring what it was built
# for. A sham that fails the visible tests is a bug in the task, not a hard task.
#
# ⚠ A FAILED COMMAND EARLIER IN A CHAIN MAKES WHAT FOLLOWS PROVE NOTHING
# (verify-claims-against-code-not-docs). Every copy is checked before the tree
# it produced is graded, and a copy that did not happen is reported as such
# rather than being graded as an empty tree.
#
# Scratch lives under $GATE_SCRATCH (default D:/ac/gate) because MAX_PATH is
# real on this box (F519).

set -u

SCRATCH="${GATE_SCRATCH:-D:/ac/gate}"
PY="${PYTHON:-python}"

# Resolve the interpreter BY EXECUTING IT (SPEC.md §8): a Store alias shim named
# python3.exe is on PATH here and prints an advert instead of running anything.
"$PY" -c '' >/dev/null 2>&1 || { echo "no working interpreter: $PY" >&2; exit 1; }

fails=0

copy_tree() { # <src> <dst>
  mkdir -p "$2" || return 1
  ( cd "$1" && tar -cf - --exclude=__pycache__ --exclude=.pytest_cache . ) \
    | ( cd "$2" && tar -xf - ) || return 1
}

grade() { # <workdir> <verify.sh>  -> echoes PASS|FAIL|INVALID and the detail
  local out
  out="$(bash "$2" "$1" "" 2>&1 | grep -m1 '^RESULT:' || true)"
  [ -n "$out" ] || out="RESULT: INVALID verify.sh printed no RESULT line"
  printf '%s' "${out#RESULT: }"
}

# TOML-safe: a detail line can carry a Windows traceback with backslashes and
# double quotes in it, and pasting that into a basic string makes a task.toml
# that will not parse. 🚨 It can also carry a CARRIAGE RETURN, and eight of
# these files were written with one before anything tried to parse them: a raw
# CR inside a basic string is an illegal character, `tr '\n' ' '` in a verify.sh
# does not touch it, and nothing prints it. Strip all three.
toml_safe() { printf '%s' "$1" | tr -d '\\"\r' | tr -s ' 	' ' ' | cut -c1-160; }

visible_tests() { # <workdir> -> PASS|FAIL
  ( cd "$1" && "$PY" -m pytest -q >/dev/null 2>&1 ) && echo PASS || echo FAIL
}

for task in "$@"; do
  task="${task%/}"
  id="$(basename "$task")"
  [ -f "$task/task.toml" ] || { echo "!! $task has no task.toml"; fails=$((fails+1)); continue; }
  [ -f "$task/verify.sh" ] || { echo "!! $task has no verify.sh"; fails=$((fails+1)); continue; }

  work="$SCRATCH/$id"
  rm -rf "$work" 2>/dev/null
  mkdir -p "$work" || { echo "!! cannot make $work"; exit 1; }

  echo
  echo "### $id"

  # --- point 1: the unmodified buggy fixture ------------------------------
  copy_tree "$task/fixture" "$work/p1" || { echo "!! copy failed"; fails=$((fails+1)); continue; }
  p1="$(grade "$work/p1" "$task/verify.sh")"
  t1="$(visible_tests "$work/p1")"

  # --- point 2: fixture + refsol -----------------------------------------
  copy_tree "$task/fixture" "$work/p2" || { echo "!! copy failed"; fails=$((fails+1)); continue; }
  copy_tree "$task/refsol"  "$work/p2" || { echo "!! refsol copy failed"; fails=$((fails+1)); continue; }
  p2="$(grade "$work/p2" "$task/verify.sh")"
  t2="$(visible_tests "$work/p2")"

  # --- point 3: fixture + sham -------------------------------------------
  p3="not_run"; t3="n/a"
  if [ -d "$task/sham" ]; then
    copy_tree "$task/fixture" "$work/p3" || { echo "!! copy failed"; fails=$((fails+1)); continue; }
    copy_tree "$task/sham"    "$work/p3" || { echo "!! sham copy failed"; fails=$((fails+1)); continue; }
    p3="$(grade "$work/p3" "$task/verify.sh")"
    t3="$(visible_tests "$work/p3")"
  fi

  printf '  point1 fixture   %-6s  visible tests %s\n' "${p1%% *}" "$t1"
  printf '  point2 refsol    %-6s  visible tests %s\n' "${p2%% *}" "$t2"
  printf '  point3 sham      %-6s  visible tests %s\n' "${p3%% *}" "$t3"

  ok=1
  case "$p1" in FAIL*) ;; *) echo "  🚨 point 1 must FAIL, got: $p1"; ok=0 ;; esac
  case "$p2" in PASS*) ;; *) echo "  🚨 point 2 must PASS, got: $p2"; ok=0 ;; esac
  if [ -d "$task/sham" ]; then
    case "$p3" in FAIL*) ;; *) echo "  🚨 point 3 must FAIL, got: $p3"; ok=0 ;; esac
    [ "$t3" = PASS ] || { echo "  🚨 the sham tree must be GREEN on the visible tests"; ok=0; }
  fi
  [ "$t2" = PASS ] || { echo "  🚨 fixture+refsol must be GREEN on the visible tests"; ok=0; }
  [ "$t1" = PASS ] || echo "  ⚠ the plain fixture fails its own visible tests (K design says it should pass)"

  if [ "$ok" = 1 ]; then
    echo "  ✅ gate sound"
    # WRITE=1 puts the block straight into task.toml, between the `# GATE BEGIN`
    # and `# GATE END` markers the OD suite's task files carry. Retyping a
    # transcript by hand is how a `[gate]` block stops being one.
    if [ "${WRITE:-}" = 1 ]; then
      GATE_ID="$id" GATE_SUITE="$(basename "$(dirname "$(dirname "$task")")")"       GATE_P1="$(toml_safe "${p1#FAIL }")" GATE_P2="$(toml_safe "${p2#PASS }")"       GATE_P3="$(toml_safe "${p3#FAIL }")" GATE_HAS_SHAM="$([ -d "$task/sham" ] && echo 1 || echo 0)"       GATE_DATE="$(date +%Y-%m-%d)"         "$PY" "$(dirname "$0")/gate_write.py" "$task/task.toml" || {
          echo "  🚨 could not write the gate block into task.toml"; fails=$((fails+1)); continue; }
      echo "  ✎ gate block written into task.toml"
      rm -rf "$work" 2>/dev/null
      continue
    fi
    RUN="corpus/suites/$(basename "$(dirname "$(dirname "$task")")")/tasks/$id/verify.sh, host, $(date +%Y-%m-%d)"
    cat <<TOML
  --- paste into task.toml ---
[gate]
point1 = "sound"
point2 = "sound"
point3 = "$([ -d "$task/sham" ] && echo sound || echo not_run)"

[[gate.evidence]]
point    = 1
tier     = "donor_fixture"
verdict  = "FAIL"
detail   = "$(toml_safe "${p1#FAIL }")"
verifier = "rewritten"
run      = "$RUN"

[[gate.evidence]]
point    = 2
tier     = "refsol"
verdict  = "PASS"
detail   = "$(toml_safe "${p2#PASS }")"
verifier = "rewritten"
run      = "$RUN"
TOML
    if [ -d "$task/sham" ]; then
      cat <<TOML

[[gate.evidence]]
point    = 3
tier     = "sham"
verdict  = "FAIL"
detail   = "$(toml_safe "${p3#FAIL }")"
verifier = "rewritten"
run      = "$RUN"
TOML
    fi
  else
    fails=$((fails+1))
  fi
  rm -rf "$work" 2>/dev/null
done

echo
if [ "$fails" -eq 0 ]; then echo "all gated tasks sound"; else echo "🚨 $fails task(s) NOT sound"; fi
exit "$fails"
