#!/usr/bin/env python3
"""Run v1's OWN completion parser over v1's OWN log shape, and read the status.

The brief's charge against v1 (§11 line 823) is that *"an agent claimed two
passing tests on a run that executed zero"*.  v1 has a documented fix for a
neighbouring bug -- ``docs/FIX_FALSE_POSITIVE_COMPLETIONS.md``, IMPLEMENTED
2026-02-12 -- and the module that carries it opens with the docstring
*"Prevents agents from hallucinating test success."*

This probe does not read that code.  It imports it, at ``d5528ea``, and calls
``_parse_from_execution_logs`` and ``parse_agent_output`` on execution logs of
exactly the shape v1's own tool layer produces, then prints the ``status`` and
``confidence`` the task record would have carried.

Usage:  PYTHONPATH=<dir with pydantic> python v1_output.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

V1 = Path("D:/dev/agent-battle-command-center")
PKG = V1 / "packages" / "agents" / "src"


def load_donor():
    """Import the donor's schemas.output with its relative imports intact."""
    root = types.ModuleType("v1src")
    root.__path__ = [str(PKG)]
    sys.modules["v1src"] = root
    for sub in ("validators", "schemas"):
        m = types.ModuleType(f"v1src.{sub}")
        m.__path__ = [str(PKG / sub)]
        sys.modules[f"v1src.{sub}"] = m
    for name, rel in (
        ("v1src.validators.test_validator", "validators/test_validator.py"),
        ("v1src.schemas.output", "schemas/output.py"),
    ):
        spec = importlib.util.spec_from_file_location(name, PKG / rel)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules["v1src.schemas.output"]


# --- observations: the real bytes, captured by v1_parser.py ------------------
# Nothing here is hand-written.  ``v1_parser.py`` executes pytest and unittest in
# a scratch tree and records what they printed; this probe reads that file, so the
# status determination below is fed the same output a real runner produced.

_PARSED = json.loads((Path(__file__).with_name("v1_parser-results.json")).read_text(encoding="utf-8"))
_RAW = {r["case"]: r["raw"] for r in _PARSED}

PYTEST_ZERO = _RAW["pytest: nothing to collect"]
PYTEST_TWO_PASS = _RAW["pytest: 2 of 2 pass"]
PYTEST_THREE_FAIL = _RAW["pytest: 3 of 3 fail"]
PYTEST_ONE_PASS_TWO_FAIL = _RAW["pytest: 1 passes, 2 fail"]
PYTEST_COLLECT_ERROR = _RAW["pytest: collection error"]

# The one observation with no runner behind it: on this host the name resolves to
# a Store alias that spawns and exits 9009 (F27), so what the tool layer records
# is the shell's own line.
NO_INTERPRETER = "[stderr] python3: command not found"

# What a model emits when it is asked for structured output.  `parse_agent_output`
# looks for exactly this before it looks at anything else.
MODEL_SELF_REPORT = """Thought: I have completed the task.
Final Answer:
{
  "status": "SUCCESS",
  "confidence": 1.0,
  "summary": "Implemented the upload handler; 2 tests passed.",
  "files_created": ["/app/workspace/upload_handler.py"],
  "files_modified": [],
  "commands_executed": ["pytest tests/ -v"],
  "test_results": "2 passed in 0.04s",
  "what_succeeded": ["wrote upload_handler.py", "ran the test suite"],
  "what_failed": []
}"""

WROTE = "Successfully wrote 1284 bytes to /app/workspace/upload_handler.py"


def logs(*, wrote=True, command=None, observation=""):
    out = []
    if wrote:
        out.append(
            {
                "action": "file_write",
                "actionInput": {"path": "/app/workspace/upload_handler.py"},
                "observation": WROTE,
            }
        )
    if command is not None:
        out.append({"action": "shell_run", "actionInput": {"command": command}, "observation": observation})
    return out


CASES = [
    # The brief's charge, in v1's own log shape.
    ("pytest discovered zero tests", logs(command="pytest tests/ -v", observation=PYTEST_ZERO),
     "Implemented the upload handler. All tests pass."),
    # The bug the documented fix was written for -- the control that shows the fix works.
    ("pytest ran 3 and all 3 failed", logs(command="pytest tests/ -v", observation=PYTEST_THREE_FAIL),
     "Implemented the upload handler. All tests pass."),
    # One passed and two failed -- the arm where v1's fix does fire, and the
    # place to read the number it reports.
    ("pytest ran 3, one passed", logs(command="pytest tests/ -v", observation=PYTEST_ONE_PASS_TWO_FAIL),
     "Implemented the upload handler. All tests pass."),
    # A real pass, for the third corner of the table.
    ("pytest ran 2 and both passed", logs(command="pytest tests/ -v", observation=PYTEST_TWO_PASS),
     "Implemented the upload handler. All tests pass."),
    # Collection blew up: nothing was measured, and the reason is in the observation.
    ("pytest failed to collect", logs(command="pytest tests/ -v", observation=PYTEST_COLLECT_ERROR),
     "Implemented the upload handler. All tests pass."),
    # The interpreter is not there at all (F27's shape on this host).
    ("the test command could not spawn", logs(command="pytest tests/ -v", observation=NO_INTERPRETER),
     "Implemented the upload handler. All tests pass."),
    # No test command was ever issued, and the model says they pass anyway.
    ("no test command was issued", logs(), "Implemented the upload handler. All tests pass."),
    # The model emits its own structured self-report.  The logs disagree with it:
    # one file written, no shell command of any kind.
    ("the model reports its own result", logs(), MODEL_SELF_REPORT),
]


def main() -> int:
    donor = load_donor()
    rows = []
    for name, log, raw in CASES:
        # Two entry points, and they are two different questions.
        #   _parse_from_execution_logs(logs, raw)  -- the path taken when the API
        #       returns the tool layer's own record of what happened.
        #   parse_agent_output(raw, task_id=None)  -- the fallback path, taken
        #       whenever no task id is passed or the log fetch fails (it catches
        #       every exception and falls through).  This one never sees the logs.
        for fn in ("_parse_from_execution_logs", "parse_agent_output"):
            f = getattr(donor, fn)
            out = f(log, raw) if fn == "_parse_from_execution_logs" else f(raw, None)
            rows.append(
                {
                    "case": name,
                    "fn": fn,
                    "status": out.status,
                    "confidence": round(out.confidence, 3),
                    "summary": out.summary,
                    "test_results": getattr(out, "test_results", None),
                    "what_failed": list(getattr(out, "what_failed", []) or []),
                    "failure_reason": getattr(out, "failure_reason", None),
                    "requires_human_review": getattr(out, "requires_human_review", None),
                }
            )
    print(json.dumps(rows, indent=1))

    for r in rows:
        flag = "  <-- reports SUCCESS" if r["status"] == "SUCCESS" else ""
        print(f'{r["fn"]:28} {r["case"]:32} {r["status"]:14} conf={r["confidence"]}{flag}', file=sys.stderr)
    # The reachability question the source raises: `test_results` is set to a
    # literal that does not contain "NO TESTS RAN", so the branch guarding on
    # that substring cannot fire from this path.  Assert it rather than assert it.
    zero = [r for r in rows if r["case"] == "pytest discovered zero tests"]
    print(
        "\nzero-test rows whose test_results contains 'NO TESTS RAN': "
        f'{sum(1 for r in zero if "NO TESTS RAN" in (r["test_results"] or ""))} of {len(zero)}',
        file=sys.stderr,
    )
    print(
        "zero-test rows that recorded the miss in what_failed: "
        f'{sum(1 for r in zero if any("Test execution" in w for w in r["what_failed"]))} of {len(zero)}',
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
