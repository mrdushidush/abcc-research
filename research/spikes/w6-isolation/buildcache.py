"""W6 item 6 — does an isolated attempt have to pay a cold build?

W11 F249 priced Integrate on a real Rust workspace: 104.2 s from a fresh clone
against 22.3 s incremental, and recorded the ~4.7x as the price of workspace
isolation, "because a fresh worktree does not share `target/`".

A worktree does not have to have its own `target/`. `CARGO_TARGET_DIR` points
anywhere, so N isolated worktrees can share one build directory — which trades
the cold build for cargo's lock on that directory. This measures both sides, and
what two parallel attempts cost in RAM against the 32 GB ceiling.

Phases (all on `claudette`, the real Rust workspace):

  A cold_private     wt1, target inside the worktree, nothing warm     the F249 case
  B cold_shared      wt2, CARGO_TARGET_DIR=<empty shared dir>          same work, other place
  C warm_cross       wt1, CARGO_TARGET_DIR=<shared, populated by B>    THE question
  D noop_shared      wt1 again, nothing changed                        the floor
  E edit_shared      wt1, one source file edited                       the per-attempt case
  F conc_shared      wt1 + wt2 at once, both on the shared dir         lock contention
  G conc_private     wt1 + wt2 at once, private targets                true parallelism + RAM

Usage:  python buildcache.py [--keep]
"""

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = r"D:\dev\claudette"
SCRATCH = Path(r"D:\dev\ABCC_20_powerd_by_claudette\scratch\w6-isolation")
OUT = Path(__file__).with_name("buildcache-results.json")
BUILD = ["cargo", "test", "--workspace", "--no-run", "--offline"]
EDIT_FILE = "crates/claudette/src/main.rs"

results = {"repo": REPO, "cmd": BUILD, "phases": {}}


def sh(args, cwd=None, env=None, check=True):
    p = subprocess.run(
        args, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if check and p.returncode != 0:
        raise RuntimeError(f"{args} -> {p.returncode}\n{p.stdout[-2000:]}\n{p.stderr[-2000:]}")
    return p


def rmtree(path):
    path = Path(path)
    if path.exists():
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(path)], capture_output=True)
        shutil.rmtree(path, ignore_errors=True)


def tree_size(path):
    total = files = 0
    for root, _dirs, fs in os.walk(path):
        for f in fs:
            try:
                total += os.lstat(os.path.join(root, f)).st_size
                files += 1
            except OSError:
                pass
    return total, files


class Sampler:
    """Total working set of the toolchain processes, plus free physical RAM.

    One long-lived PowerShell loop rather than a spawn per tick, so the sampler
    does not compete with the build it is measuring.
    """

    PS = (
        "while($true){"
        " $p=Get-Process cargo,rustc,rustdoc,link,lld-link -ErrorAction SilentlyContinue;"
        " $s=($p|Measure-Object WorkingSet64 -Sum).Sum;"
        " $n=($p|Measure-Object).Count;"
        " $f=(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory;"
        " Write-Output \"$n,$s,$f\";"
        " Start-Sleep -Milliseconds 400 }"
    )

    def __init__(self):
        self.rows = []
        self.proc = None
        self._t = None

    def _pump(self):
        for line in self.proc.stdout:
            parts = line.strip().split(",")
            if len(parts) == 3:
                try:
                    self.rows.append((int(parts[0]), int(parts[1] or 0), int(parts[2]) * 1024))
                except ValueError:
                    pass

    def __enter__(self):
        self.proc = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", self.PS],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self._t = threading.Thread(target=self._pump, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *exc):
        if self.proc:
            self.proc.kill()
        return False

    def stats(self):
        if not self.rows:
            return {}
        return {
            "samples": len(self.rows),
            "peak_procs": max(r[0] for r in self.rows),
            "peak_toolchain_ws_mb": round(max(r[1] for r in self.rows) / 1e6, 1),
            "min_free_ram_mb": round(min(r[2] for r in self.rows) / 1e6, 1),
            "max_free_ram_mb": round(max(r[2] for r in self.rows) / 1e6, 1),
        }


def build(cwd, target_dir=None, label=""):
    env = dict(os.environ)
    if target_dir:
        env["CARGO_TARGET_DIR"] = str(target_dir)
    else:
        env.pop("CARGO_TARGET_DIR", None)
    t0 = time.perf_counter()
    p = subprocess.run(
        BUILD, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    dt = time.perf_counter() - t0
    blocking = [l for l in p.stderr.splitlines() if "Blocking waiting for file lock" in l]
    compiled = len(re.findall(r"^\s*Compiling ", p.stderr, re.M))
    return {
        "label": label,
        "s": round(dt, 2),
        "rc": p.returncode,
        "crates_compiled": compiled,
        "blocked_on_lock": bool(blocking),
        "lock_lines": blocking[:3],
        "stderr_tail": p.stderr.strip().splitlines()[-3:],
    }


def timed(name, fn):
    print(f"--- {name}", flush=True)
    with Sampler() as s:
        out = fn()
    if isinstance(out, dict):
        out["ram"] = s.stats()
    else:
        out = {"runs": out, "ram": s.stats()}
    results["phases"][name] = out
    OUT.write_text(json.dumps(results, indent=1), encoding="utf-8", newline="\n")
    print(f"    {json.dumps(out)[:300]}", flush=True)
    return out


def edit(wt, marker):
    f = Path(wt) / EDIT_FILE
    src = f.read_text(encoding="utf-8")
    src = re.sub(r"\n// w6-isolation edit .*\n$", "\n", src)
    f.write_text(src.rstrip("\n") + f"\n// w6-isolation edit {marker}\n", encoding="utf-8")


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    wt1, wt2 = SCRATCH / "bc-wt1", SCRATCH / "bc-wt2"
    shared = SCRATCH / "bc-shared-target"
    priv2 = SCRATCH / "bc-priv2-target"
    for d in (wt1, wt2):
        if d.exists():
            sh(["git", "worktree", "remove", "--force", str(d)], cwd=REPO, check=False)
            rmtree(d)
    rmtree(shared)
    rmtree(priv2)
    sh(["git", "worktree", "prune"], cwd=REPO)
    sh(["git", "worktree", "add", "--detach", str(wt1), "HEAD"], cwd=REPO)
    sh(["git", "worktree", "add", "--detach", str(wt2), "HEAD"], cwd=REPO)

    timed("A_cold_private", lambda: build(wt1, None, "wt1 private target"))
    b, f = tree_size(wt1 / "target")
    results["phases"]["A_cold_private"]["target_bytes"] = b
    results["phases"]["A_cold_private"]["target_files"] = f

    timed("B_cold_shared", lambda: build(wt2, shared, "wt2 shared target, empty"))
    b, f = tree_size(shared)
    results["phases"]["B_cold_shared"]["target_bytes"] = b
    results["phases"]["B_cold_shared"]["target_files"] = f

    timed("C_warm_cross", lambda: build(wt1, shared, "wt1 onto wt2's shared cache"))
    timed("D_noop_shared", lambda: build(wt1, shared, "wt1 again, unchanged"))

    edit(wt1, "E")
    timed("E_edit_shared", lambda: build(wt1, shared, "wt1, one file edited"))

    # F: both worktrees, one shared build dir, at the same time.
    edit(wt1, "F1")
    edit(wt2, "F2")

    def concurrent(target1, target2):
        out = {}
        threads = []

        def go(key, cwd, target):
            out[key] = build(cwd, target, key)

        t0 = time.perf_counter()
        for key, cwd, tgt in (("wt1", wt1, target1), ("wt2", wt2, target2)):
            th = threading.Thread(target=go, args=(key, cwd, tgt))
            th.start()
            threads.append(th)
        for th in threads:
            th.join()
        out["wall_s"] = round(time.perf_counter() - t0, 2)
        return out

    timed("F_conc_shared", lambda: concurrent(shared, shared))

    # G: private targets. wt2 needs one of its own first (cold), then both edit
    # and rebuild at the same time.
    timed("G_prep_cold_priv2", lambda: build(wt2, priv2, "wt2 private target, cold"))
    edit(wt1, "G1")
    edit(wt2, "G2")
    timed("G_conc_private", lambda: concurrent(wt1 / "target", priv2))

    results["disk"] = {
        "private_target_bytes": results["phases"]["A_cold_private"]["target_bytes"],
        "shared_target_bytes": tree_size(shared)[0],
        "priv2_target_bytes": tree_size(priv2)[0],
        "worktree_checkout_bytes": tree_size(wt2)[0] - tree_size(priv2)[0],
    }
    OUT.write_text(json.dumps(results, indent=1), encoding="utf-8", newline="\n")

    if "--keep" not in sys.argv:
        for d in (wt1, wt2):
            sh(["git", "worktree", "remove", "--force", str(d)], cwd=REPO, check=False)
            rmtree(d)
        sh(["git", "worktree", "prune"], cwd=REPO)
        rmtree(shared)
        rmtree(priv2)
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
