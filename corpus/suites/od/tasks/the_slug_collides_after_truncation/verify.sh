#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
# Asserts uniqueness AND the twenty-character limit, because the fix has to hold
# both.
#
# The tempting fix is a longer truncation. It separates a1 from a2 -- the pair in
# the ticket -- and leaves a3 and a4, which share their first forty characters,
# on one URL. `longest_slug` catches the other half.
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
[ -f data/articles.json ] || {
  echo "RESULT: INVALID data/articles.json is missing — the fixture was not copied intact"
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

printf '%s' "$OUT" | grep -q '^SLUG RUN$' \
  || fail "output is missing the SLUG RUN header; got: $(printf '%s' "$OUT" | tr '\n' ' ' | cut -c1-160)"
printf '%s' "$OUT" | grep -qx 'articles: 6' \
  || fail "expected 'articles: 6', got: $(got articles) — data/articles.json was changed"
printf '%s' "$OUT" | grep -qx 'distinct_slugs: 6' \
  || fail "expected 'distinct_slugs: 6', got: $(got distinct_slugs) — 4 is the unfixed batch; 5 is a longer truncation that still collides"
printf '%s' "$OUT" | grep -qx 'collisions: 0' \
  || fail "expected 'collisions: 0', got: $(got collisions) — 1 means a3 and a4 still publish at the same URL"
printf '%s' "$OUT" | grep -qx 'longest_slug: 20' \
  || fail "expected 'longest_slug: 20', got: $(got longest_slug) — 40 breaks the catalogue column, which is not ours to change"
printf '%s' "$OUT" | grep -qx 'slug_a1: how-to-build-a-resil' \
  || fail "expected 'slug_a1: how-to-build-a-resil', got: $(got slug_a1) — a longer slug means MAX_LEN was raised"
printf '%s' "$OUT" | grep -qx 'slug_a4: everything-you-eve-2' \
  || fail "expected 'slug_a4: everything-you-eve-2', got: $(got slug_a4) — the suffix comes out of the twenty, not on top of it"

echo "RESULT: PASS six distinct slugs, none longer than twenty characters"
exit 0
