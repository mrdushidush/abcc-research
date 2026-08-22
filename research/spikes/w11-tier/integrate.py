"""OQ-W11-1: what does M2 Integrate cost on this box?

W11 item 1 put M2 Integrate at the mission level with NO model: build and test the
assembled workspace, `Measured | Uncertain` per check. It left one measurement
owed -- what that costs here -- because the answer decides a policy question the
item could not settle: does Integrate run once at the end of a mission, or after
every task?

It also decides something W6 item 6 owns (OQ-W3-12): if each attempt gets a fresh
workspace, the build cache is empty and every Integrate is a COLD build. If the
workspace persists, it is incremental. The gap between those two numbers is the
price of workspace isolation, and nobody has quoted it.

Two subjects, because Integrate's cost is a property of the TARGET project and not
of 2.0:

  * the K-suite's Python fixture -- 15 files, a pytest suite and an executable
    acceptance criterion (`python run.py data/jobs.json`). The cheap end.
  * a fresh clone of Claudette (`D:/dev/claudette`, af3f804) -- a real Rust
    workspace, and the closest thing on this disk to what 2.0 itself will be.
    The expensive end.

For each: cold (no build cache), warm (nothing changed), and incremental (one
source file touched, which is what M2 actually faces after a task lands).
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

SCRATCH = pathlib.Path(
    r"C:/Users/david/AppData/Local/Temp/claude/D--dev-ABCC-20-powerd-by-claudette"
    r"/42b00185-4a5a-4806-9e97-33bd4fcebc29/scratchpad/w11-integrate"
)
REPO = pathlib.Path(r"D:/dev/ABCC_20_powerd_by_claudette")
CLAUDETTE = pathlib.Path(r"D:/dev/claudette")
FIXTURE = REPO / "corpus/suites/k/tasks/finish_the_cancelled_status/fixture"

rows = []


def run(label, cmd, cwd, timeout=3600):
    t0 = time.perf_counter()
    try:
        p = subprocess.run(cmd, cwd=str(cwd), shell=True, capture_output=True,
                           text=True, timeout=timeout, encoding="utf-8", errors="replace")
        rc, tail = p.returncode, (p.stdout + p.stderr).strip().splitlines()[-1:] or [""]
    except subprocess.TimeoutExpired:
        rc, tail = None, ["TIMEOUT"]
    dt = time.perf_counter() - t0
    row = {"label": label, "cmd": cmd, "secs": round(dt, 2), "rc": rc, "tail": tail[0][:120]}
    rows.append(row)
    print(f"{label:<44} {dt:8.2f}s  rc={rc}  {tail[0][:70]}", flush=True)
    return dt


def fresh(dst, src, clone=False):
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if clone:
        subprocess.run(f'git clone --no-hardlinks --quiet "{src}" "{dst}"', shell=True, check=True)
    else:
        shutil.copytree(src, dst)


which = "python" if os.name == "nt" else "python3"

# ── subject 1: the Python fixture ───────────────────────────────────────────
RUST_ONLY = "--rust-only" in sys.argv

if not RUST_ONLY:
  print("== subject: K-suite Python fixture (15 files, pytest + an executable criterion) ==")
  py = SCRATCH / "fixture"
  fresh(py, FIXTURE)
  run("py  criterion, cold (run.py)", f"{which} run.py data/jobs.json", py)
  run("py  suite, cold (pytest)", f"{which} -m pytest -q", py)
  run("py  suite, warm (pytest again)", f"{which} -m pytest -q", py)
  (py / "jobs" / "status.py").touch()
  run("py  suite, one file touched", f"{which} -m pytest -q", py)
  run("py  criterion, warm (run.py)", f"{which} run.py data/jobs.json", py)

  # ── subject 2: a real Rust workspace ────────────────────────────────────────
if "--python-only" not in sys.argv:
    print("\n== subject: Claudette, a real Rust workspace, fresh clone (empty target/) ==")
    rs = SCRATCH / "claudette"
    fresh(rs, CLAUDETTE, clone=True)
    run("rs  fetch deps (cargo fetch)", "cargo fetch", rs)
    run("rs  build, COLD (empty target)", "cargo build --workspace", rs)
    run("rs  test compile, cold (--no-run)", "cargo test --workspace --no-run", rs)
    run("rs  test run, cold", "cargo test --workspace", rs)
    run("rs  build, warm (nothing changed)", "cargo build --workspace", rs)
    run("rs  test, warm (nothing changed)", "cargo test --workspace", rs)
    src = next(iter(sorted((rs / "crates").rglob("src/lib.rs"))), None)
    if src:
        with open(src, "a", encoding="utf-8") as f:
            f.write("\n// touched by W11 item 2's Integrate probe\n")
        run(f"rs  build, incremental ({src.parent.parent.name})",
            "cargo build --workspace", rs)
        run(f"rs  test, incremental ({src.parent.parent.name})",
            "cargo test --workspace", rs)

out = pathlib.Path(__file__).with_name("integrate-results.json")
prior = json.loads(out.read_text(encoding="utf-8")) if out.exists() else []
prior = [r for r in prior if r["label"] not in {x["label"] for x in rows}]
out.write_text(json.dumps(prior + rows, indent=1), encoding="utf-8")
print(f"\nwrote {out}")