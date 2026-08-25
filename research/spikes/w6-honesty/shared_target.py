#!/usr/bin/env python3
"""A green test run that measured nothing, produced by cargo and not by a model.

Found while building ``visible.py``: sharing one ``CARGO_TARGET_DIR`` across two
work trees that hold the same package name and version makes the second tree's
tests silently disappear. Cargo prints ``Fresh <crate>``, runs the FIRST tree's
test binary, and reports ``test result: ok. 0 passed`` with exit status 0.

Why it matters here: item 6 (F331) recommends sharing the build directory across
per-attempt worktrees, because a warm cache turns 204 dependency units into one
crate in 24.7 s. That saving is real and this is its edge -- OQ-W6-14 asked
whether two attempts at different commits can share one build directory, and the
answer is that they can share it for *building* and must not share it for
*testing*, because the collision is silent and it is green.

Three trees, one package name, one assertion per arm. No donors involved.

Usage:  python shared_target.py <scratch dir>
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

CARGO_TOML = """[package]
name = "collide"
version = "0.1.0"
edition = "2021"

[lib]
path = "src/lib.rs"

[workspace]
"""

NO_TESTS = "pub fn f() -> u32 { 1 }\n"

THREE_TESTS = """pub fn f() -> u32 { 1 }

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn t1() { assert_eq!(f(), 1); }
    #[test] fn t2() { assert_eq!(f(), 1); }
    #[test] fn t3() { assert_eq!(f(), 1); }
}
"""

TEST_RESULT = re.compile(r"test result:\s+(ok|FAILED)\.\s+(\d+) passed")


def tree(root: Path, name: str, body: str) -> Path:
    t = root / name
    if t.exists():
        shutil.rmtree(t)
    (t / "src").mkdir(parents=True)
    (t / "Cargo.toml").write_text(CARGO_TOML, encoding="utf-8", newline="\n")
    (t / "src" / "lib.rs").write_text(body, encoding="utf-8", newline="\n")
    return t


def cargo_test(t: Path, target_dir: Path | None) -> dict:
    env = dict(os.environ)
    if target_dir is None:
        env.pop("CARGO_TARGET_DIR", None)
    else:
        env["CARGO_TARGET_DIR"] = str(target_dir)
    proc = subprocess.run(
        ["cargo", "test", "--quiet"], cwd=t, capture_output=True, text=True, env=env
    )
    out = proc.stdout + proc.stderr
    hits = TEST_RESULT.findall(out)
    return {
        "exit": proc.returncode,
        "passed": sum(int(h[1]) for h in hits),
        "fresh": "Fresh collide" in out,
    }


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "scratch/w6-honesty-shared")
    root.mkdir(parents=True, exist_ok=True)
    shared = root / "_shared"
    own = root / "_own"

    a = tree(root, "A", NO_TESTS)  # zero tests
    b = tree(root, "B", THREE_TESTS)  # three tests

    arms = {
        "A first, shared dir": cargo_test(a, shared),
        "B second, SAME shared dir": cargo_test(b, shared),
        "B again, its own dir": cargo_test(b, own),
        "B again, cargo's default dir": cargo_test(b, None),
    }
    checks = {
        "A really has no tests": arms["A first, shared dir"]["passed"] == 0,
        "B has three when it does not share": arms["B again, its own dir"]["passed"] == 3
        and arms["B again, cargo's default dir"]["passed"] == 3,
        "B reports zero when it shares": arms["B second, SAME shared dir"]["passed"] == 0,
        "and it reports success while doing so": arms["B second, SAME shared dir"]["exit"] == 0,
    }
    out = {"arms": arms, "checks": checks, "reproduced": all(checks.values())}
    print(json.dumps(out, indent=2))
    for name, r in arms.items():
        print(f'  {name:32} exit={r["exit"]}  passed={r["passed"]}', file=sys.stderr)
    for k, v in checks.items():
        print(f'  {"OK " if v else "BAD"}  {k}', file=sys.stderr)
    return 0 if out["reproduced"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
