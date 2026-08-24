"""W6 item 6 — does a worktree created AFTER the cache is warm still hit it?

`buildcache.py` phase C found a second worktree compiling 0 crates against a
shared `CARGO_TARGET_DIR`. Both worktrees in that run were created before either
build, so their source files were older than every artifact — which is exactly
the condition cargo's mtime-based freshness check wants. The realistic case is
the opposite: an attempt starts, and its worktree is created now, against a build
directory that was warm an hour ago.

This runs that case: cold-fill a shared target dir from one worktree, then create
a second worktree and build it into the same dir.

Usage:  python freshwt.py
"""

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

REPO = r"D:\dev\claudette"
SCRATCH = Path(r"D:\dev\ABCC_20_powerd_by_claudette\scratch\w6-isolation")
OUT = Path(__file__).with_name("freshwt-results.json")
BUILD = ["cargo", "test", "--workspace", "--no-run", "--offline"]


def sh(args, cwd=None, env=None, check=True):
    p = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        raise RuntimeError(f"{args} -> {p.returncode}\n{p.stderr[-1500:]}")
    return p


def rmtree(path):
    path = Path(path)
    if path.exists():
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(path)], capture_output=True)
        shutil.rmtree(path, ignore_errors=True)


def build(cwd, target):
    env = dict(os.environ, CARGO_TARGET_DIR=str(target))
    t0 = time.perf_counter()
    p = subprocess.run(BUILD, cwd=cwd, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return {
        "s": round(time.perf_counter() - t0, 2),
        "rc": p.returncode,
        "crates_compiled": len(re.findall(r"^\s*Compiling ", p.stderr, re.M)),
        "tail": p.stderr.strip().splitlines()[-2:],
    }


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    wt_a, wt_b, wt_c = SCRATCH / "fw-a", SCRATCH / "fw-b", SCRATCH / "fw-c"
    shared = SCRATCH / "fw-shared"
    for d in (wt_a, wt_b, wt_c):
        sh(["git", "worktree", "remove", "--force", str(d)], cwd=REPO, check=False)
        rmtree(d)
    rmtree(shared)
    sh(["git", "worktree", "prune"], cwd=REPO)

    res = {}
    sh(["git", "worktree", "add", "--detach", str(wt_a), "HEAD"], cwd=REPO)
    res["A_cold_fill"] = build(wt_a, shared)
    print("A", res["A_cold_fill"], flush=True)

    # created after the cache is warm: every source file is newer than every artifact
    sh(["git", "worktree", "add", "--detach", str(wt_b), "HEAD"], cwd=REPO)
    newest_src = max(
        os.path.getmtime(os.path.join(r, f))
        for r, _d, fs in os.walk(wt_b / "crates")
        for f in fs
    )
    res["B_fresh_worktree"] = build(wt_b, shared)
    res["B_fresh_worktree"]["src_newer_than_cache"] = newest_src > os.path.getmtime(shared)
    print("B", res["B_fresh_worktree"], flush=True)

    res["B2_second_run"] = build(wt_b, shared)
    print("B2", res["B2_second_run"], flush=True)

    # and back to the first tree, which is now the older one again
    res["C_back_to_a"] = build(wt_a, shared)
    print("C", res["C_back_to_a"], flush=True)

    # a copied pre-image tree — no .git at all — against the same cache
    wt_c.mkdir(parents=True, exist_ok=True)
    prefix = str(wt_c).replace("\\", "/") + "/"
    sh(["git", "checkout-index", "-a", "-f", f"--prefix={prefix}"], cwd=REPO)
    res["D_copied_tree"] = build(wt_c, shared)
    print("D", res["D_copied_tree"], flush=True)

    # --- the 32 GB question: two cold builds at once, private targets --------
    import threading

    ta, tb = SCRATCH / "fw-target-a", SCRATCH / "fw-target-b"
    rmtree(ta)
    rmtree(tb)
    out = {}

    def go(key, cwd, target):
        out[key] = build(cwd, target)

    sampler = subprocess.Popen(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "while($true){ $p=Get-Process cargo,rustc,rustdoc,link,lld-link -ErrorAction SilentlyContinue;"
            " $s=($p|Measure-Object WorkingSet64 -Sum).Sum; $n=($p|Measure-Object).Count;"
            " $f=(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory;"
            ' Write-Output "$n,$s,$f"; Start-Sleep -Milliseconds 400 }',
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    rows = []

    def pump():
        for line in sampler.stdout:
            parts = line.strip().split(",")
            if len(parts) == 3:
                try:
                    rows.append((int(parts[0]), int(parts[1] or 0), int(parts[2]) * 1024))
                except ValueError:
                    pass

    threading.Thread(target=pump, daemon=True).start()
    t0 = time.perf_counter()
    threads = [
        threading.Thread(target=go, args=("a", wt_a, ta)),
        threading.Thread(target=go, args=("b", wt_b, tb)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = round(time.perf_counter() - t0, 2)
    sampler.kill()
    res["E_two_cold_at_once"] = {
        "wall_s": wall,
        "a": out["a"],
        "b": out["b"],
        "ram": {
            "samples": len(rows),
            "peak_procs": max((r[0] for r in rows), default=0),
            "peak_toolchain_ws_mb": round(max((r[1] for r in rows), default=0) / 1e6, 1),
            "min_free_ram_mb": round(min((r[2] for r in rows), default=0) / 1e6, 1),
            "max_free_ram_mb": round(max((r[2] for r in rows), default=0) / 1e6, 1),
        },
    }
    print("E", json.dumps(res["E_two_cold_at_once"])[:400], flush=True)
    rmtree(ta)
    rmtree(tb)

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8", newline="\n")
    for d in (wt_a, wt_b):
        sh(["git", "worktree", "remove", "--force", str(d)], cwd=REPO, check=False)
        rmtree(d)
    rmtree(wt_c)
    sh(["git", "worktree", "prune"], cwd=REPO)
    rmtree(shared)
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
