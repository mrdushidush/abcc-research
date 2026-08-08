#!/usr/bin/env python3
"""Run ABCC's own fix_path_traversal verifier against three inputs, verbatim.

Same shape as ../w8-pipe-drive/gate_fix_sql_inject.py, which established F8.
Donor: agent-battle-command-center @ d5528ea, ultimate-100-task-test.js
  fixture   BUGGY_FILES['path_traversal.py']   :1709
  verifier  SECTION_4B fix_path_traversal      :1738-1743

The claim under test: the verifier's `except (ValueError, Exception): pass` also
catches the AssertionError raised by `assert r is None`, so the verifier prints
PASS for any implementation that imports — including one with the traversal intact.

Run: python gate_fix_path_traversal.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Verbatim from BUGGY_FILES['path_traversal.py'] (:1709)
FIXTURE = (
    "import os\n"
    "def read_file(base_dir, filename):\n"
    "    path = os.path.join(base_dir, filename)\n"
    "    with open(path) as f:\n"
    "        return f.read()\n"
)

# A correct fix, per the task description (:1737): reject '..', confine to base_dir.
REFSOL = (
    "import os\n"
    "def read_file(base_dir, filename):\n"
    "    if '..' in filename:\n"
    "        return None\n"
    "    path = os.path.realpath(os.path.join(base_dir, filename))\n"
    "    if not path.startswith(os.path.realpath(base_dir) + os.sep):\n"
    "        return None\n"
    "    with open(path) as f:\n"
    "        return f.read()\n"
)

# The sham: traversal fully intact, but it never raises on the probe path because
# the file it reaches exists and is readable. This is the fixture with a cosmetic
# edit — the kind of "fix" that looks like work in a diff and fixes nothing.
SHAM = (
    "import os\n"
    "def read_file(base_dir, filename):\n"
    "    # 'validated' path handling\n"
    "    path = os.path.normpath(os.path.join(base_dir, filename))\n"
    "    with open(path) as f:\n"
    "        return f.read()\n"
)

# Verbatim from the donor's validation field (:1738-1743), with the container path
# /app/workspace swapped for the temp workdir. Nothing else changed.
VERIFIER = """import sys; sys.path.insert(0,{workspace!r}); from tasks.security_fixes.path_traversal import read_file
try:
    r=read_file({base!r},'../etc/passwd')
    assert r is None
except (ValueError, Exception):
    pass
print('PASS')
"""


def run_case(label, source):
    work = Path(tempfile.mkdtemp(prefix="w8gate_"))
    try:
        pkg = work / "tasks" / "security_fixes"
        pkg.mkdir(parents=True)
        (work / "tasks" / "__init__.py").write_text("")
        (pkg / "__init__.py").write_text("")
        (pkg / "path_traversal.py").write_text(source)

        # The traversal target. The donor probes '../etc/passwd' relative to a base
        # dir; recreate that shape so the vulnerable read actually succeeds.
        base = work / "base"
        base.mkdir()
        (work / "etc").mkdir()
        (work / "etc" / "passwd").write_text("root:x:0:0:root:/root:/bin/sh\n")

        code = VERIFIER.format(workspace=str(work), base=str(base))
        p = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, timeout=60
        )
        verdict = "PASS" if "PASS" in p.stdout else "FAIL"
        detail = (p.stderr.strip().splitlines() or [""])[-1]
        print(f"  {label:<34} donor verdict: {verdict}   {detail}")

        # Independently: is the traversal actually still open?
        probe = (
            f"import sys; sys.path.insert(0,{str(work)!r});"
            "from tasks.security_fixes.path_traversal import read_file;"
            f"\nr=read_file({str(base)!r},'../etc/passwd');"
            "print('LEAKED:'+repr(r) if r else 'contained')"
        )
        q = subprocess.run(
            [sys.executable, "-c", probe], capture_output=True, text=True, timeout=60
        )
        out = q.stdout.strip() or (q.stderr.strip().splitlines() or [""])[-1]
        print(f"  {'':<34} ground truth:  {out}")
        return verdict
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    print("ABCC fix_path_traversal — three-point import gate (R8)\n")
    print("--- gate step 1: untouched fixture must FAIL ---")
    a = run_case("fixture (vulnerable)", FIXTURE)
    print("\n--- gate step 2: fixture + refsol must PASS ---")
    b = run_case("refsol (correct fix)", REFSOL)
    print("\n--- gate step 3: sham must FAIL ---")
    c = run_case("sham (traversal intact)", SHAM)

    print("\n=== gate result ===")
    ok = (a == "FAIL") and (b == "PASS") and (c == "FAIL")
    print(f"  fixture={a}  refsol={b}  sham={c}   ->  {'PASSES' if ok else 'FAILS'} the gate")
