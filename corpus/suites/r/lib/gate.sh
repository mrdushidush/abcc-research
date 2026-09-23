#!/usr/bin/env bash
# gate.sh <task-dir>...  — SPEC.md §9 points 1 and 2 for an R task, on this host.
#
#   point 1: the pinned base tree, untouched          → must FAIL, and FAIL on behaviour
#   point 2: the base tree + refsol/fix.patch          → must PASS
#   point 3: base + sham/fix.patch, only if one exists → must FAIL
#
# Prints one line per point, `<task> point<N> <RESULT line>`, to paste into [[gate.evidence]].
# Never touches the corpus: each input is exported to a scratch dir with `git archive`.

set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRATCH="${W8_R_GATE:-${TMPDIR:-/tmp}/w8-r-gate}"

rev_of()  { sed -nE 's/^rev *= *"([0-9a-f]{40})".*/\1/p' "$1/task.toml"; }
repo_of() { sed -nE 's/^repo *= *"([^"]+)".*/\1/p' "$1/task.toml"; }

one() {
  local task="$1" point="$2" patch="${3-}"
  local id wd
  id="$(basename "$task")"
  wd="$SCRATCH/$id-p$point"
  rm -rf "$wd" && mkdir -p "$wd"
  git -C "$(repo_of "$task")" archive "$(rev_of "$task")" | tar -xf - -C "$wd" \
    || { echo "$id point$point RESULT: INVALID could not export the base"; return; }
  if [ -n "$patch" ]; then
    (cd "$wd" && git apply "$patch") \
      || { echo "$id point$point RESULT: INVALID $(basename "$(dirname "$patch")")/fix.patch does not apply"; return; }
  fi
  printf '%s point%s ' "$id" "$point"
  bash "$task/verify.sh" "$wd" /dev/null | grep -m1 '^RESULT:'
}

for t in "$@"; do
  t="$(cd "$t" && pwd)"
  one "$t" 1
  one "$t" 2 "$t/refsol/fix.patch"
  [ -f "$t/sham/fix.patch" ] && one "$t" 3 "$t/sham/fix.patch"
done
