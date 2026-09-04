"""Emit the boilerplate half of an OD-suite task: `task.toml` and `verify.sh`.

    python harness/scripts/od_new_task.py corpus/suites/od/tasks/<id> <<'JSON'
    { ... }
    JSON

**What it does NOT author is the half that matters.** The fixture, the refsol,
the sham and the prompt are the task; this writes the two files whose shape is
fixed by `corpus/SPEC.md` §3 and §8 and whose per-task content is a handful of
values. Every task in this suite would otherwise carry the same forty lines of
interpreter resolution, and a forty-line block retyped twenty-four times is a
block nobody reads by the fourth copy.

⚠ The `[gate]` table it writes is `not_run` between `# GATE BEGIN` / `# GATE
END`. `gate-task.sh WRITE=1` measures the three points and replaces it. A task
whose gate block still says `not_run` has not been gated, and that is the
intended reading rather than an oversight.

The spec, as JSON on stdin:

```json
{
  "title":   "human-readable, not an identifier",
  "kind":    "bugfix",
  "timeout_s": 900,
  "gate3_rank": 1,
  "reason":  "why [disposition].verifiable is `full`",
  "caveats": ["...", "..."],
  "donor_tags": {"shape": "outside_cover", ...},
  "verify": {
    "entry":  "run.py",
    "args":   [],
    "header": "ENTITLEMENT REPORT",
    "needs":  ["data/accounts.json"],
    "why":    "the comment at the top of verify.sh — what the local wrong answer is",
    "checks": [
      {"key": "premium", "want": "4", "hint": "6 means lapsed trials keep premium"}
    ]
  }
}
```

A `check` asserts one whole line `<key>: <want>` and reports the line it got.
A task whose verifier needs more than that hand-writes its own `verify.sh` and
does not call this.
"""

import json
import os
import sys

VOCAB = [
    "id", "title", "lang", "kind", "timeout_s", "turn", "prompt", "fixture", "verify",
    "refsol", "sham", "variants", "disposition", "selection", "gate", "donor_tags",
]

NO_BASELINE = (
    "NO HUMAN BASELINE. The refsol was authored alongside the task, so point 2 establishes "
    "that the task is solvable and that the verifier accepts a correct answer. It does not "
    "calibrate difficulty against a human engineer"
)


def wrap(text, width=96, indent="  "):
    """A TOML multi-line basic string, hard-wrapped with trailing backslashes.

    The corpus's own house style (`suites/k/**/task.toml`): a caveat is prose and
    prose that runs to 400 characters on one line is prose nobody diffs.
    """
    words = text.split()
    lines, cur = [], ""
    for word in words:
        candidate = word if not cur else cur + " " + word
        if len(candidate) > width - len(indent) - 2 and cur:
            lines.append(cur)
            cur = word
        else:
            cur = candidate
    if cur:
        lines.append(cur)
    body = " \\\n".join(indent + line for line in lines)
    return '  """\n' + body + "\\\n" + '  """'


def task_toml(ident, spec):
    tags = spec.get("donor_tags", {})
    caveats = list(spec.get("caveats", [])) + [NO_BASELINE]
    out = []
    out.append("schema    = 1")
    out.append('id        = "{}"'.format(ident))
    out.append('title     = "{}"'.format(spec["title"]))
    out.append('lang      = "python"')
    out.append('kind      = "{}"'.format(spec.get("kind", "bugfix")))
    out.append("")
    out.append("# Smaller than K's 2400 because the fixture is a fraction of K's size: this suite")
    out.append("# measures a reviewer over a patch, not a subject under context pressure")
    out.append("# (suite.toml). 900 was K's original ceiling and it bound only the 2.5x-slower")
    out.append("# model on 12k-token fixtures.")
    out.append("timeout_s = {}".format(spec.get("timeout_s", 900)))
    out.append("")
    out.append("[[turn]]")
    out.append('send_file = "prompt.txt"')
    out.append("")
    out.append("[verify]")
    out.append('kind   = "script"')
    out.append('script = "verify.sh"')
    out.append("")
    out.append("[disposition]")
    out.append('verifiable = "full"')
    out.append('quarantine = "none"')
    out.append("reason = " + wrap(spec["reason"]).lstrip())
    out.append("")
    out.append("[selection]")
    out.append("gate3      = true")
    out.append("gate3_rank = {}".format(spec.get("gate3_rank", 1)))
    out.append("")
    out.append("# GATE BEGIN")
    out.append("[gate]")
    out.append('point1 = "not_run"')
    out.append('point2 = "not_run"')
    out.append('point3 = "not_run"')
    out.append("# GATE END")
    out.append("")
    out.append("[provenance]")
    out.append('donor       = "od-series"')
    out.append('imported_at = "2026-09-04"')
    out.append("")
    out.append("verbatim    = []")
    out.append("rewritten   = []")
    out.append("synthesized = [" + ", ".join('"{}"'.format(n) for n in VOCAB[:7]) + ",")
    out.append("               " + ", ".join('"{}"'.format(n) for n in VOCAB[7:13]) + ",")
    out.append("               " + ", ".join('"{}"'.format(n) for n in VOCAB[13:]) + "]")
    out.append("")
    out.append("caveats = [")
    for caveat in caveats:
        out.append(wrap(caveat) + ",")
        out.append("")
    if caveats:
        out.pop()
    out.append("]")
    out.append("")
    out.append("[donor_tags]")
    width = max([len(k) for k in tags] or [1])
    for key, value in tags.items():
        rendered = json.dumps(value) if not isinstance(value, str) else '"{}"'.format(value)
        out.append("{} = {}".format(key.ljust(width), rendered))
    return "\n".join(out) + "\n"


VERIFY_HEAD = '''#!/usr/bin/env bash
# verify.sh <workdir> <transcript>   — SPEC.md §8
#
{why}
#
# Expected values were produced by fixture+refsol and are reproducible with:
#   python {entry}{argline}

set -u

WORKDIR="${{1:?usage: verify.sh <workdir> <transcript>}}"

cd "$WORKDIR" 2>/dev/null || {{
  echo "RESULT: INVALID cannot cd to workdir '$WORKDIR'"
  exit 0
}}

# Resolve an interpreter BY EXECUTING IT (SPEC.md §8): on Windows a Microsoft
# Store alias shim named python3.exe sits on PATH, is found by `command -v`, and
# prints an advert instead of running the code.
PY=""
for cand in "${{PYTHON:-}}" python3 python; do
  [ -z "$cand" ] && continue
  if "$cand" -c '' >/dev/null 2>&1; then PY="$cand"; break; fi
done
if [ -z "$PY" ]; then
  echo "RESULT: INVALID no working python interpreter (tried \\$PYTHON, python3, python)"
  exit 0
fi

[ -f {entry} ] || {{ echo "RESULT: FAIL {entry} is missing from the workdir"; exit 0; }}
{needs}
OUT="$("$PY" {entry}{argline} 2>&1)"
STATUS=$?
if [ $STATUS -ne 0 ]; then
  FIRST="$(printf '%s' "$OUT" | tr '\\n' ' ' | cut -c1-200)"
  echo "RESULT: FAIL {entry} exited $STATUS: ${{FIRST}}"
  exit 0
fi

fail() {{ echo "RESULT: FAIL $1"; exit 0; }}
got()  {{ printf '%s' "$OUT" | grep -E "^$1:" || echo "<no $1 line>"; }}

printf '%s' "$OUT" | grep -q '^{header}$' \\
  || fail "output is missing the {header} header; got: $(printf '%s' "$OUT" | tr '\\n' ' ' | cut -c1-160)"
'''

NEEDS = '''[ -f {path} ] || {{
  echo "RESULT: INVALID {path} is missing — the fixture was not copied intact"
  exit 0
}}
'''

CHECK = '''printf '%s' "$OUT" | grep -qx '{key}: {want}' \\
  || fail "expected '{key}: {want}', got: $(got {key}) — {hint}"
'''


def verify_sh(spec):
    verify = spec["verify"]
    entry = verify.get("entry", "run.py")
    args = verify.get("args", [])
    argline = ("" if not args else " " + " ".join(args))
    why = "\n".join("# " + line if line else "#" for line in verify["why"].split("\n"))
    needs = "".join(NEEDS.format(path=p) for p in verify.get("needs", []))
    body = VERIFY_HEAD.format(
        why=why, entry=entry, argline=argline, header=verify["header"], needs=needs
    )
    for check in verify["checks"]:
        body += CHECK.format(**check)
    body += '\necho "RESULT: PASS {}"\nexit 0\n'.format(verify["pass"])
    return body


def main(argv):
    if len(argv) != 2:
        sys.stderr.write(__doc__)
        return 2
    task = argv[1].rstrip("/\\")
    ident = os.path.basename(task)
    spec = json.load(sys.stdin)

    # ENCODE FIRST, THEN OPEN. Both files are rendered in full before either is
    # created, so a spec that is missing a key leaves no half-written task
    # behind — `open(path, "w")` truncates before it writes.
    toml_text = task_toml(ident, spec)
    verify_text = verify_sh(spec) if "verify" in spec else None

    os.makedirs(task, exist_ok=True)
    with open(os.path.join(task, "task.toml"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(toml_text)
    if verify_text is not None:
        path = os.path.join(task, "verify.sh")
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(verify_text)
        os.chmod(path, 0o755)
    print("wrote {}/task.toml{}".format(task, " and verify.sh" if verify_text else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
