#!/usr/bin/env bash
# Rewritten from ABCC's `validation` string (ultimate-100-task-test.js:1726, d5528ea).
#
# Three rewrites, all recorded in task.toml's provenance:
#   1. sys.path.insert(0,'/app/workspace') -> the work dir passed as $1
#   2. `from tasks.security_fixes.sql_inject import` -> flat `from sql_inject import`
#   3. the donor's `exit 0 AND "PASS" in stdout` contract -> RESULT: PASS|FAIL|INVALID
#
# The donor's assertion chain is reproduced UNCHANGED, defect and all. It is an OR-chain that
# short-circuits on any '?' in the query, so it PASSes a solution with the injection fully
# intact (F8). Faithfulness to the donor is the point of an import; the third gate point is
# what makes preserving a broken verifier safe, and this task is quarantined because of it.
#
# SPEC.md §8: one line on stdout, exit status ignored, both arguments absolute.
set -u

work="${1:?usage: verify.sh <workdir> <transcript>}"
: "${2-}"   # transcript, unused: the donor verifier reads only the artifact

"${PYTHON:-python3}" - "$work" <<'PY'
import sys

sys.path.insert(0, sys.argv[1])
try:
    from sql_inject import get_user

    r = get_user(None, "admin' OR 1=1 --")
    assert isinstance(r, dict)
    q = r.get('query', '')
    assert "'" not in q or '?' in q or ':' in q or '%s' in q
    print("RESULT: PASS donor assertions held")
except Exception as e:
    print(f"RESULT: FAIL {type(e).__name__}: {e}")
PY
