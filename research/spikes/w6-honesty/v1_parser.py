#!/usr/bin/env python3
"""Feed REAL test-runner output to v1's own test-result parser.

``packages/agents/src/validators/test_validator.py`` opens with *"Prevents
agents from hallucinating test success."*  Its dispatcher, ``parse_test_output``,
chooses the pytest parser with::

    if '===' in output and 'passed' in output.lower():

so the question this probe asks is not a reading question: what does that
dispatcher return for output that a real runner really produced, in the six
states a run can end in?

Every string below is captured by executing the runner in a scratch tree, never
by hand.  The parser is imported from the donor at ``d5528ea``.

Usage:  PYTHONPATH=<dir with pydantic and pytest> python v1_parser.py [scratch]
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import types
from pathlib import Path

# Written with an explicit LF so the captured fixtures do not pick up CRLF on
# this host; the Rust probe next door compares them line for line.
LF = "\n"

V1 = Path("D:/dev/agent-battle-command-center")
PKG = V1 / "packages" / "agents" / "src"


def load_parser():
    root = types.ModuleType("v1src")
    root.__path__ = [str(PKG)]
    sys.modules["v1src"] = root
    m = types.ModuleType("v1src.validators")
    m.__path__ = [str(PKG / "validators")]
    sys.modules["v1src.validators"] = m
    spec = importlib.util.spec_from_file_location(
        "v1src.validators.test_validator", PKG / "validators" / "test_validator.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# name -> (test file body, argv).  An empty body means "no tests to collect".
FIXTURES = {
    "pytest: 2 of 2 pass": (
        "def test_a(): assert 1 == 1\ndef test_b(): assert 2 == 2\n",
        [sys.executable, "-m", "pytest", "tests/", "-v"],
    ),
    "pytest: 1 passes, 2 fail": (
        "def test_a(): assert 1 == 1\ndef test_b(): assert 1 == 2\ndef test_c(): assert 1 == 3\n",
        [sys.executable, "-m", "pytest", "tests/", "-v"],
    ),
    "pytest: 3 of 3 fail": (
        'def test_a(): assert 1 == 2\ndef test_b(): assert "x" == "y"\ndef test_c(): raise ValueError("boom")\n',
        [sys.executable, "-m", "pytest", "tests/", "-v"],
    ),
    "pytest: nothing to collect": ("# no tests here\n", [sys.executable, "-m", "pytest", "tests/", "-v"]),
    "pytest: collection error": (
        "import a_module_that_does_not_exist\ndef test_a(): assert True\n",
        [sys.executable, "-m", "pytest", "tests/", "-v"],
    ),
    "unittest: 2 of 2 pass": (
        "import unittest\n"
        "class T(unittest.TestCase):\n"
        "    def test_a(self): self.assertTrue(True)\n"
        "    def test_b(self): self.assertTrue(True)\n",
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
    ),
    "unittest: 2 of 2 fail": (
        "import unittest\n"
        "class T(unittest.TestCase):\n"
        "    def test_a(self): self.assertTrue(False)\n"
        "    def test_b(self): self.assertEqual(1, 2)\n",
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
    ),
    "unittest: nothing to collect": (
        "# no tests here\n",
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
    ),
}


def slug(name: str) -> str:
    return name.replace(": ", "__").replace(", ", "_").replace(" ", "-")


def capture(scratch: Path, name: str, body: str, argv: list[str]) -> tuple[str, int]:
    tree = scratch / name.replace(":", "").replace(" ", "_")
    if tree.exists():
        shutil.rmtree(tree)
    (tree / "tests").mkdir(parents=True)
    (tree / "tests" / "test_upload.py").write_text(body, encoding="utf-8")
    proc = subprocess.run(argv, cwd=tree, capture_output=True, text=True)
    return (proc.stdout + proc.stderr).strip(), proc.returncode


def main() -> int:
    scratch = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("scratch/w6-honesty-parser")
    scratch.mkdir(parents=True, exist_ok=True)
    tv = load_parser()

    # The captured bytes are also written out as files, so the Rust probe next
    # door reads the same output rather than a re-typed copy of it.
    captured = Path(__file__).with_name("captured")
    captured.mkdir(exist_ok=True)

    rows = []
    for name, (body, argv) in FIXTURES.items():
        out, exit_code = capture(scratch, name, body, argv)
        (captured / f"{slug(name)}.txt").write_text(out, encoding="utf-8", newline=LF)
        (captured / f"{slug(name)}.exit").write_text(str(exit_code), encoding="utf-8", newline=LF)
        r = tv.parse_test_output(out)
        rows.append(
            {
                "case": name,
                "truth": name.split(": ", 1)[1],
                "exit": exit_code,
                # The dispatcher's two gates, evaluated on the real bytes.
                "has_===": "===" in out,
                "has_passed": "passed" in out.lower(),
                "framework": r.framework,
                "tests_run": r.tests_run,
                "tests_passed": r.tests_passed,
                "tests_failed": r.tests_failed,
                "tests_errors": r.tests_errors,
                "is_valid_success": r.is_valid_success,
                "summary": r.summary,
                # This is the predicate v1's shipped status check keys on.
                "fix_can_fire": r.tests_run > 0 and not r.is_valid_success,
                "raw_tail": out.splitlines()[-1] if out else "",
                # Kept in full so the downstream probe can feed v1's status
                # determination the same bytes a real runner produced.
                "raw": out,
            }
        )
    print(json.dumps(rows, indent=1))

    w = max(len(r["case"]) for r in rows)
    for r in rows:
        print(
            f'{r["case"]:{w}}  run={r["tests_run"]:<3} pass={r["tests_passed"]:<3} '
            f'fail={r["tests_failed"]:<3}  fix_fires={str(r["fix_can_fire"]):5}  {r["summary"]}',
            file=sys.stderr,
        )
    reds = [r for r in rows if "fail" in r["truth"] or "error" in r["truth"]]
    print(
        f'\nruns that really went red: {len(reds)}; on which v1 can report a failure: '
        f'{sum(1 for r in reds if r["fix_can_fire"])}',
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
