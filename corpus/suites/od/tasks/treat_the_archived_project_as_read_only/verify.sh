#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts each path's accepted count AND the revisions recorded against archived
# projects, which is the number the compliance export is built on.
#
# The local wrong answer guards `workspace/importer.py`, the path the reviewer
# traced. It makes `importer_writes` correct and leaves `scheduler_writes` and
# `webhook_writes` touching archived projects, so `archived_touched` falls from
# six to three rather than to zero.
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
[ -f data/projects.json ] || {
  echo "RESULT: INVALID data/projects.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^WRITE AUDIT$' \
  || fail "output is missing the WRITE AUDIT header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'projects: 3' \
  || fail "expected 'projects: 3', got: $(got projects) — data/projects.json was changed"
printf '%s' "$OUT" | grep -qx 'editor_writes: 2' \
  || fail "expected 'editor_writes: 2', got: $(got editor_writes) — the editor already asked the guard; a change here is a regression"
printf '%s' "$OUT" | grep -qx 'importer_writes: 1' \
  || fail "expected 'importer_writes: 1', got: $(got importer_writes) — 4 means the importer still loads rows into archived projects"
printf '%s' "$OUT" | grep -qx 'scheduler_writes: 0' \
  || fail "expected 'scheduler_writes: 0', got: $(got scheduler_writes) — 2 means the scheduler still stamps archived projects"
printf '%s' "$OUT" | grep -qx 'webhook_writes: 2' \
  || fail "expected 'webhook_writes: 2', got: $(got webhook_writes) — 3 means an inbound webhook still writes to an archived project"
printf '%s' "$OUT" | grep -qx 'archived_touched: 0' \
  || fail "expected 'archived_touched: 0', got: $(got archived_touched) — any revision on an archived project is a hole in the audit trail"

echo "RESULT: PASS no write path touches an archived project (editor 2, importer 1, scheduler 0, webhook 2, archived_touched 0)"
exit 0
