#!/usr/bin/env python3
"""Capture what `cargo test` really prints in the five states a run can end in.

Companion to ``v1_parser.py``, which does the same for pytest and unittest. These
captures exist so the ported Claudette gate (``report/tests/donor_gate.rs``) is
run against real bytes and real exit statuses rather than against strings someone
typed while reading the donor.

The state that matters most here is the first one: a crate with no tests at all.
``cargo test`` exits **0** and prints ``test result: ok. 0 passed``, which is a
green process exit for a run that measured nothing -- and unlike pytest, cargo has
no distinct exit code for it.

Usage:  python cargo_endings.py <scratch dir>
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

LF = "\n"

CARGO_TOML = """[package]
name = "endings"
version = "0.1.0"
edition = "2021"

[lib]
path = "src/lib.rs"

[workspace]
"""

BODIES = {
    "cargo__no-tests-at-all": "pub fn f() -> u32 { 1 }\n",
    "cargo__2-of-2-pass": (
        "pub fn f() -> u32 { 1 }\n\n"
        "#[cfg(test)]\nmod tests {\n    use super::*;\n"
        "    #[test] fn t1() { assert_eq!(f(), 1); }\n"
        "    #[test] fn t2() { assert_eq!(f(), 1); }\n}\n"
    ),
    "cargo__1-passes_2-fail": (
        "pub fn f() -> u32 { 1 }\n\n"
        "#[cfg(test)]\nmod tests {\n    use super::*;\n"
        "    #[test] fn t1() { assert_eq!(f(), 1); }\n"
        "    #[test] fn t2() { assert_eq!(f(), 2); }\n"
        "    #[test] fn t3() { assert_eq!(f(), 3); }\n}\n"
    ),
    "cargo__3-of-3-fail": (
        "pub fn f() -> u32 { 1 }\n\n"
        "#[cfg(test)]\nmod tests {\n    use super::*;\n"
        "    #[test] fn t1() { assert_eq!(f(), 2); }\n"
        "    #[test] fn t2() { assert_eq!(f(), 3); }\n"
        "    #[test] fn t3() { panic!(\"boom\"); }\n}\n"
    ),
    "cargo__does-not-compile": (
        "pub fn f() -> u32 { 1 }\n\n"
        "#[cfg(test)]\nmod tests {\n    use super::*;\n"
        "    #[test] fn t1() { assert_eq!(f(), \"one\"); }\n}\n"
    ),
}

TEST_RESULT = re.compile(r"test result:.*")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "scratch/w6-honesty-cargo")
    root.mkdir(parents=True, exist_ok=True)
    captured = Path(__file__).with_name("captured")
    captured.mkdir(exist_ok=True)

    rows = []
    for name, body in BODIES.items():
        t = root / name
        if t.exists():
            shutil.rmtree(t)
        (t / "src").mkdir(parents=True)
        (t / "Cargo.toml").write_text(CARGO_TOML, encoding="utf-8", newline=LF)
        (t / "src" / "lib.rs").write_text(body, encoding="utf-8", newline=LF)
        # Each tree keeps its own build directory: sharing one across trees that
        # hold the same package name makes cargo run the wrong binary and say so
        # nowhere (shared_target.py).
        proc = subprocess.run(
            ["cargo", "test", "--quiet"], cwd=t, capture_output=True, text=True
        )
        out = (proc.stdout + proc.stderr).strip()
        (captured / f"{name}.txt").write_text(out, encoding="utf-8", newline=LF)
        (captured / f"{name}.exit").write_text(str(proc.returncode), encoding="utf-8", newline=LF)
        rows.append(
            {
                "case": name,
                "exit": proc.returncode,
                "result_lines": TEST_RESULT.findall(out),
                "compiled": "could not compile" not in out,
            }
        )
        print(f'{name:28} exit={proc.returncode}  {rows[-1]["result_lines"]}', file=sys.stderr)

    print(json.dumps(rows, indent=1))
    zero = next(r for r in rows if r["case"].endswith("no-tests-at-all"))
    print(
        f'\ncargo on a crate with no tests: exit {zero["exit"]}, '
        f'{zero["result_lines"]} -- green, and nothing distinguishes it from a real pass '
        "but the number in the line.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
