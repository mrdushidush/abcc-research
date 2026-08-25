#!/usr/bin/env python3
"""W6 item 7 — running the reviewer's own findings.

A model reviewer's output is prose, and prose is the artifact this workstream has
no instrument for. But a finding shaped `call → expected → actual` is not prose:
it names an input, and an input can be fed to the code.

So every case the `edge` arm produced is executed here, twice — against the tree
the agent left and against the suite's reference solution — and classified:

  discriminates  the two trees disagree on this input. The finding is TRUE: the
                 agent's code really does something the reference does not.
  agrees         both trees produce the same value. The finding is FALSE, however
                 well argued — this is the positive control F277 said the donors'
                 generated criteria never carry.
  unrunnable     the call does not execute at all (wrong name, wrong arity, a
                 pseudo-call, a shell one-liner that needs input nobody wrote).
                 A finding that cannot be run is not a finding.

The reference solution is used as an ORACLE here and would not exist in a real
run; what the number is for is the *precision of a model reviewer's concrete
claims*, which is a property of the reviewer, not of the corpus.

    python check.py
"""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import sys
import tempfile

import common as C

HERE = pathlib.Path(__file__).resolve().parent
HC = C.HC


# ── per-language drivers ─────────────────────────────────────────────
#
# Each returns (ok, output). `ok` is False when the harness itself could not run
# the call; a panic, an exception or a non-zero exit is a legitimate *value* and
# is captured as text, because "panics" is exactly what several findings claim.


def _write(root: pathlib.Path, files: dict[str, str]):
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")


def drive_python(work: pathlib.Path, call: str):
    driver = (
        "import sys, traceback\n"
        "sys.path.insert(0, '.')\n"
        "import solution\n"
        "from solution import *\n"
        "try:\n"
        f"    print('VALUE', repr({call}))\n"
        "except Exception as e:\n"
        "    print('RAISED', type(e).__name__)\n"
    )
    (work / "_judge_probe.py").write_text(driver, encoding="utf-8", newline="\n")
    code, out, _ = HC.run([HC.REAL_PYTHON, "_judge_probe.py"], work, timeout=30)
    line = next((l for l in out.splitlines()
                 if l.startswith(("VALUE", "RAISED"))), None)
    if line is None:
        return False, out.strip()[-300:]
    return True, line


CRATE = re.compile(r'^name\s*=\s*"([^"]+)"', re.M)


def drive_rust(work: pathlib.Path, call: str):
    toml = (work / "Cargo.toml").read_text(encoding="utf-8")
    m = CRATE.search(toml)
    if not m:
        return False, "no crate name"
    crate = m.group(1).replace("-", "_")
    driver = (
        f"use {crate}::*;\n"
        "fn main() {\n"
        "    let r = std::panic::catch_unwind(|| format!(\"{:?}\", "
        f"{call}));\n"
        "    match r {\n"
        "        Ok(v) => println!(\"VALUE {}\", v),\n"
        "        Err(_) => println!(\"RAISED panic\"),\n"
        "    }\n"
        "}\n"
    )
    _write(work, {"examples/judge_probe.rs": driver})
    code, out, _ = HC.run(
        ["cargo", "run", "--quiet", "--example", "judge_probe"], work, timeout=180)
    line = next((l for l in out.splitlines()
                 if l.startswith(("VALUE", "RAISED"))), None)
    if line is None:
        return False, out.strip()[-300:]
    return True, line


def _js_driver(module: str, call: str) -> str:
    return (
        f"const m = await import('./{module}');\n"
        "Object.assign(globalThis, m);\n"
        "try {\n"
        f"  console.log('VALUE', JSON.stringify({call}));\n"
        "} catch (e) {\n"
        "  console.log('RAISED', e && e.constructor && e.constructor.name);\n"
        "}\n"
    )


def drive_node(work: pathlib.Path, call: str):
    name = "_judge_probe.mjs"
    (work / name).write_text(_js_driver("solution.mjs", call),
                             encoding="utf-8", newline="\n")
    code, out, _ = HC.run(["node", name], work, timeout=60)
    line = next((l for l in out.splitlines()
                 if l.startswith(("VALUE", "RAISED"))), None)
    if line is None:
        return False, out.strip()[-300:]
    return True, line


def drive_typescript(work: pathlib.Path, call: str):
    name = "_judge_probe.ts"
    (work / name).write_text(_js_driver("solution.ts", call),
                             encoding="utf-8", newline="\n")
    code, out, _ = HC.run(["node", name], work, timeout=60)
    line = next((l for l in out.splitlines()
                 if l.startswith(("VALUE", "RAISED"))), None)
    if line is None:
        return False, out.strip()[-300:]
    return True, line


def drive_shell(work: pathlib.Path, call: str):
    """The call IS a command line here. Run it verbatim, with a hard timeout.

    Two of the 23 trees do not terminate (taxonomy `mechanical`), so the timeout
    is a value and not an error: `<timeout>` is what the code produces.
    """
    code, out, _ = HC.bash(call, work, timeout=25)
    if code is None:
        return True, "RAISED timeout"
    return True, "VALUE " + json.dumps(out.strip()[:400])


DRIVERS = {
    "python": drive_python,
    "rust": drive_rust,
    "node": drive_node,
    "typescript": drive_typescript,
    "shell": drive_shell,
}


# ── the two trees ────────────────────────────────────────────────────


def materialise(files: dict[str, str], dest: pathlib.Path) -> pathlib.Path:
    dest.mkdir(parents=True, exist_ok=True)
    _write(dest, files)
    return dest


def refsol_tree(task: str, agent_files: dict[str, str]) -> dict[str, str]:
    """The fixture with the reference solution's files laid over it."""
    files = dict(C._rel_text(C.Q56 / task / "fixture"))
    files.update(C.refsol(task))
    # Keep any support file the agent's tree has that the fixture does not touch
    # (Cargo.toml is in the fixture; nothing else matters here).
    return files


def run_case(task: str, lang: str, agent_files: dict[str, str], call: str):
    driver = DRIVERS.get(lang)
    if driver is None:
        return {"status": "unrunnable", "why": f"no driver for {lang}"}
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="w6j-"))
    try:
        a = materialise(agent_files, tmp / "agent")
        b = materialise(refsol_tree(task, agent_files), tmp / "refsol")
        ok_a, out_a = driver(a, call)
        ok_b, out_b = driver(b, call)
        if not ok_a or not ok_b:
            return {"status": "unrunnable",
                    "agent": out_a[:300], "refsol": out_b[:300]}
        return {"status": "discriminates" if out_a != out_b else "agrees",
                "agent": out_a[:300], "refsol": out_b[:300]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    edge = json.loads((HERE / "judge-edge.json").read_text(encoding="utf-8"))
    pop = {f"{a['task']}:{a['content_sha']}": a for a in C.population()}
    out_path = HERE / "check-results.json"
    rows = C.resumable(out_path)
    todo = [r for r in edge if (r["payload"] or {}).get("cases")]
    print(f"{len(todo)} trees with at least one case", flush=True)
    for r in todo:
        a = pop[r["key"]]
        for i, case in enumerate(r["payload"]["cases"]):
            key = f"{r['key']}#{i}"
            if key in rows:
                continue
            res = run_case(a["task"], a["lang"], a["files"], case["call"])
            rows[key] = {
                "key": key, "tree": r["key"], "task": a["task"], "lang": a["lang"],
                "truth": a["truth"], "n_cells": a["n_cells"],
                "call": case["call"], "expected": case["expected"],
                "claimed_actual": case["actual"], **res,
            }
            C.save(out_path, rows)
            print(f"  {key:<28} {res['status']:<14} {case['call'][:52]}",
                  flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
