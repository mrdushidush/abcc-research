#!/usr/bin/env bash
# Run the three-point import gate against the ON-DISK v1 example task (THROWAWAY).
#
# Not a copy of the sweep's numbers: this runs the *rewritten* verifier that corpus/ actually
# ships, which imports flat where the donor's imported through a package path. SPEC.md §9 says
# a sham must be tested against the rewritten verifier, so this is the run that counts.
#
# Usage: bash gate_example.sh [corpus-root]      (default: ./corpus)
set -u

ROOT="${1:-corpus}"
T="$ROOT/suites/u100/tasks/fix_sql_inject"
W="$(mktemp -d)"
trap 'rm -rf "$W"' EXIT
# Resolve an interpreter that actually runs. `command -v python3` is NOT enough on Windows:
# there is a Microsoft Store alias shim named python3.exe on PATH that resolves, executes, and
# prints an advert instead of running the code. Probe by executing, not by looking.
if [ -z "${PYTHON:-}" ]; then
  for cand in python3 python py; do
    if "$cand" -c '' >/dev/null 2>&1; then PYTHON="$cand"; break; fi
  done
fi
: "${PYTHON:?no working python interpreter found (tried python3, python, py)}"
export PYTHON

# The generated null-implementation stub, per SPEC.md §9. Dunders must still raise, or the
# import machinery reads a stub __path__ and treats the module as a package.
stub_py () {
  printf 'def __getattr__(name):\n'
  printf '    if name.startswith("__") and name.endswith("__"):\n'
  printf '        raise AttributeError(name)\n'
  printf '    def _stub(*a, **k):\n'
  printf '        return None\n'
  printf '    return _stub\n'
}

run_tier () {
  name="$1"
  w="$W/$name"; rm -rf "$w"; mkdir -p "$w"
  case "$name" in
    absent)  : ;;                                              # nothing was produced
    stub)    stub_py > "$w/sql_inject.py" ;;                   # produced, inert
    fixture) cp "$T"/fixture/* "$w/" ;;                        # produced, unfixed
    refsol)  cp "$T"/fixture/* "$w/"; cp "$T"/refsol/* "$w/" ;;
    sham)    cp "$T"/fixture/* "$w/"; cp "$T"/sham/*   "$w/" ;;
  esac
  : > "$W/transcript.log"
  printf '  %-9s %s\n' "$name" "$(bash "$T/verify.sh" "$w" "$W/transcript.log" 2>&1)"
}

echo "gate point 1 - every pre-state is a wrong answer and MUST FAIL"
run_tier absent
run_tier stub
run_tier fixture
echo "gate point 2 - fixture + refsol MUST PASS"
run_tier refsol
echo "gate point 3 - fixture + sham MUST FAIL"
run_tier sham
echo
echo "Expected: three FAILs, one PASS, then a PASS that must not happen (F8)."
