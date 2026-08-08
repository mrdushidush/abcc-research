#!/usr/bin/env python3
"""Gate step 1 across all 10 of ABCC's section 4B: does the untouched buggy fixture FAIL?

This is the cheapest point of the three-point gate (R8) and the one that needs no
authored content: seed the donor's own buggy file, run the donor's own verifier, and
see whether the verifier notices the bug it was written to catch.

A verifier that PASSES its own unfixed fixture has never measured anything.

Donor: agent-battle-command-center @ d5528ea, scripts/ultimate-100-task-test.js
  BUGGY_FILES   :1706-1717   (seeded by seedBuggyFiles(), :2662-2686)
  SECTION_4B    :1719-1804

Run: python gate_step1_section4b.py [path-to-abcc-repo]
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
DEFAULT_REPO = Path(r"D:\dev\agent-battle-command-center")

# task name -> the buggy file it seeds. From the description field of each 4B task.
TASK_FILE = {
    "fix_sql_inject": "sql_inject.py",
    "fix_xss_reflect": "xss_reflect.py",
    "fix_path_traversal": "path_traversal.py",
    "fix_weak_hash": "weak_hash.py",
    "fix_hardcoded_secret": "hardcoded_secret.py",
    "fix_insecure_random": "insecure_random.py",
    "fix_missing_validation": "missing_validation.py",
    "fix_info_leak": "info_leak.py",
    "fix_open_redirect": "open_redirect.py",
    "fix_type_confusion": "type_confusion.py",
}


def buggy_files(repo):
    """Parse the BUGGY_FILES map out of the donor source."""
    src = (repo / "scripts" / "ultimate-100-task-test.js").read_text(encoding="utf-8")
    start = src.index("const BUGGY_FILES = {")
    end = src.index("\n};", start)
    block = src[start:end]
    out = {}
    for m in re.finditer(r"'([\w.]+)':\s*`((?:[^`\\]|\\.)*)`", block):
        # The map stores literal \n escapes inside a template literal.
        out[m.group(1)] = m.group(2).encode().decode("unicode_escape")
    return out


def run_case(name, verifier, filename, source):
    work = Path(tempfile.mkdtemp(prefix="w8g1_"))
    try:
        pkg = work / "tasks" / "security_fixes"
        pkg.mkdir(parents=True)
        (work / "tasks" / "__init__.py").write_text("")
        (pkg / "__init__.py").write_text("")
        (pkg / filename).write_text(source)
        # fix_path_traversal probes a base dir and reaches outside it.
        base = work / "base"
        base.mkdir()
        (work / "etc").mkdir(exist_ok=True)
        (work / "etc" / "passwd").write_text("root:x:0:0:root:/root:/bin/sh\n")

        code = verifier.replace("/app/workspace", str(work).replace("\\", "\\\\"))
        code = code.replace("'/tmp'", repr(str(base)))
        p = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, timeout=60
        )
        if "PASS" in p.stdout:
            return "PASS", ""
        last = (p.stderr.strip().splitlines() or [""])[-1]
        return "FAIL", last[:60]
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_REPO
    tasks = {t["name"]: t for t in json.loads((HERE / "tasks.json").read_text("utf-8"))}
    files = buggy_files(repo)

    print("Gate step 1 — the untouched buggy fixture must FAIL\n")
    print("  task                      verdict on its own unfixed fixture")
    print("  " + "-" * 68)
    broken = []
    for name, fname in TASK_FILE.items():
        t = tasks[name]
        v = t.get("validation")
        if not v or v.strip() == "null":
            print(f"  {name:<25} NO VERIFIER")
            broken.append(name)
            continue
        verdict, detail = run_case(name, v, fname, files[fname])
        flag = "  <-- verifier passes its own bug" if verdict == "PASS" else ""
        print(f"  {name:<25} {verdict:<5} {detail:<40}{flag}")
        if verdict == "PASS":
            broken.append(name)

    print(f"\n  {len(broken)} of {len(TASK_FILE)} section-4B verifiers fail gate step 1: {broken}")


if __name__ == "__main__":
    main()
