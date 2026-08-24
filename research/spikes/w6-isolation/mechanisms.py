"""W6 item 6 — what the three isolation mechanisms cost on real trees.

OQ-W3-12 names three candidates for a workspace checkpoint / per-task isolation
marker: a git worktree, a git stash object, or a copied pre-image tree. This
prices all three (plus the plumbing snapshot the stash object cannot do) against
the four real repositories on this machine.

Nothing here mutates a source repository beyond a worktree add that is removed
again, and `git stash create`, which writes objects and prints a sha without
touching the index, the worktree or any ref. Every repo's `git status` and
`git worktree list` are asserted clean before and after.

Usage:  python mechanisms.py [--quick]     (--quick skips the full-tree copies)
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCRATCH = Path(r"D:\dev\ABCC_20_powerd_by_claudette\scratch\w6-isolation")
OUT = Path(__file__).with_name("mechanisms-results.json")

REPOS = {
    "bcf": r"D:\dev\battle-command-forge",
    "claudette": r"D:\dev\claudette",
    "v1": r"D:\dev\agent-battle-command-center",
    "abcc20": r"D:\dev\ABCC_20_powerd_by_claudette",
}

REPS = 3


def run(args, cwd=None, env=None, check=True):
    t0 = time.perf_counter()
    p = subprocess.run(
        args, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    dt = time.perf_counter() - t0
    if check and p.returncode != 0:
        raise RuntimeError(f"{args} -> {p.returncode}\n{p.stdout}\n{p.stderr}")
    return dt, p


def tree_size(path):
    """(bytes, files) under path. Reparse points are not followed."""
    total = 0
    count = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total += os.lstat(fp).st_size
                count += 1
            except OSError:
                pass
    return total, count


def clean(path):
    if Path(path).exists():
        # git worktrees leave read-only objects on Windows; force them writable
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(path)], capture_output=True)
        if Path(path).exists():
            shutil.rmtree(path, ignore_errors=True)


def assert_clean(repo, allow_untracked=False):
    _, p = run(["git", "status", "--porcelain"], cwd=repo)
    lines = [l for l in p.stdout.splitlines() if l.strip()]
    if allow_untracked:
        lines = [l for l in lines if not l.startswith("??")]
    if lines:
        raise SystemExit("REFUSING: {} is dirty:\n{}".format(repo, "\n".join(lines)))


def pick_victim(repo):
    """A tracked text file whose bytes on disk really do hash to its index entry.

    `git status` is not enough: in the v1 donor 241 of 539 tracked files differ
    from their blobs while the tree reports clean (stale.py), and touching one
    promotes it to a whole-file modification. Restoring such a file byte-for-byte
    still leaves the repo dirty, because the difference was there all along.
    """
    _, p = run(["git", "ls-files", "-s"], cwd=repo)
    for line in p.stdout.splitlines():
        meta, path = line.split("\t", 1)
        mode, sha, _stage = meta.split()
        if mode != "100644" or not path.endswith((".rs", ".ts", ".py", ".md")):
            continue
        f = Path(repo) / path
        if not f.is_file():
            continue
        _, h = run(["git", "hash-object", path], cwd=repo)
        if h.stdout.strip() == sha:
            return f
    raise SystemExit(f"no content-true victim file in {repo}")


def measure_worktree(repo, name):
    """git worktree add --detach HEAD, then remove. n=REPS."""
    rows = []
    for i in range(REPS):
        dest = SCRATCH / f"wt-{name}-{i}"
        clean(dest)
        t_add, _ = run(["git", "worktree", "add", "--detach", str(dest), "HEAD"], cwd=repo)
        size, files = tree_size(dest)
        t_rm, _ = run(["git", "worktree", "remove", "--force", str(dest)], cwd=repo)
        rows.append({"add_s": t_add, "remove_s": t_rm, "bytes": size, "files": files})
    run(["git", "worktree", "prune"], cwd=repo)
    return rows


def measure_checkout_index(repo, name):
    """Materialise HEAD's tracked files with no .git at all."""
    rows = []
    for i in range(REPS):
        dest = SCRATCH / f"ci-{name}-{i}"
        clean(dest)
        dest.mkdir(parents=True)
        prefix = str(dest).replace("\\", "/") + "/"
        t, _ = run(["git", "checkout-index", "-a", "-f", f"--prefix={prefix}"], cwd=repo)
        size, files = tree_size(dest)
        rows.append({"s": t, "bytes": size, "files": files})
        clean(dest)
    return rows


def measure_copy(repo, name, mt=None):
    """robocopy the whole working directory, ignored files included."""
    dest = SCRATCH / f"cp-{name}"
    clean(dest)
    args = ["robocopy", repo, str(dest), "/E", "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/R:0", "/W:0"]
    if mt:
        args.append(f"/MT:{mt}")
    t, p = run(args, check=False)
    size, files = tree_size(dest)
    t_del, _ = run(["cmd", "/c", "rmdir", "/s", "/q", str(dest)], check=False)
    return {"s": t, "bytes": size, "files": files, "delete_s": t_del, "rc": p.returncode}


def measure_stash_create(repo, name):
    """`git stash create` on a tree dirtied by one edit + one new file.

    Records what the resulting object actually contains, which is the whole
    question: a checkpoint that drops the agent's new files is not a checkpoint.
    """
    assert_clean(repo, allow_untracked=True)
    victim = pick_victim(repo)
    original = victim.read_bytes()
    newfile = Path(repo) / "w6-isolation-probe-untracked.txt"
    rows = []
    try:
        victim.write_bytes(original + b"\n// w6-isolation probe\n")
        newfile.write_text("w6-isolation probe: an untracked file the agent just created\n")
        for _ in range(REPS):
            t, p = run(["git", "stash", "create", "w6-probe"], cwd=repo)
            sha = p.stdout.strip()
            rows.append({"s": t, "sha": sha})
        sha = rows[-1]["sha"]
        _, d = run(["git", "diff", "--stat", "HEAD", sha], cwd=repo, check=False)
        _, names = run(["git", "diff", "--name-status", "HEAD", sha], cwd=repo, check=False)
        captured = names.stdout.strip().splitlines()
    finally:
        victim.write_bytes(original)
        if newfile.exists():
            newfile.unlink()
        assert_clean(repo, allow_untracked=True)
    return {
        "runs": rows,
        "captured_paths": captured,
        "captured_untracked": any("w6-isolation-probe-untracked" in c for c in captured),
        "diffstat": d.stdout.strip().splitlines()[-1:] if d.stdout.strip() else [],
    }


def measure_temp_index_snapshot(repo, name):
    """The plumbing snapshot: a temp index, `add -A`, write-tree, commit-tree.

    Captures untracked files as well, and touches neither the real index nor the
    working tree. This is the mechanism `git stash create` cannot express.
    """
    assert_clean(repo, allow_untracked=True)
    victim = pick_victim(repo)
    original = victim.read_bytes()
    newfile = Path(repo) / "w6-isolation-probe-untracked.txt"
    idx = SCRATCH / f"tmp-index-{name}"
    rows = []
    captured = []
    try:
        victim.write_bytes(original + b"\n// w6-isolation probe\n")
        newfile.write_text("w6-isolation probe: an untracked file the agent just created\n")
        for _ in range(REPS):
            if idx.exists():
                idx.unlink()
            env = dict(os.environ, GIT_INDEX_FILE=str(idx))
            t0 = time.perf_counter()
            run(["git", "read-tree", "HEAD"], cwd=repo, env=env)
            run(["git", "add", "-A"], cwd=repo, env=env)
            _, tp = run(["git", "write-tree"], cwd=repo, env=env)
            tree = tp.stdout.strip()
            _, cp = run(
                ["git", "commit-tree", tree, "-p", "HEAD", "-m", "w6-isolation snapshot"],
                cwd=repo,
                env=env,
            )
            dt = time.perf_counter() - t0
            rows.append({"s": dt, "commit": cp.stdout.strip()})
        _, names = run(
            ["git", "diff", "--name-status", "HEAD", rows[-1]["commit"]], cwd=repo, check=False
        )
        captured = names.stdout.strip().splitlines()
    finally:
        victim.write_bytes(original)
        if newfile.exists():
            newfile.unlink()
        if idx.exists():
            idx.unlink()
        assert_clean(repo, allow_untracked=True)
    return {
        "runs": rows,
        "captured_paths": captured,
        "captured_untracked": any("w6-isolation-probe-untracked" in c for c in captured),
    }


def main():
    quick = "--quick" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    SCRATCH.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        results = json.loads(OUT.read_text(encoding="utf-8"))
        results.setdefault("host", {})["reps"] = REPS
    else:
        results = {"host": {"reps": REPS}, "repos": {}}
    for name, repo in REPOS.items():
        if only and name not in only:
            continue
        print(f"=== {name} ({repo})", flush=True)
        assert_clean(repo, allow_untracked=True)
        _, p = run(["git", "ls-files"], cwd=repo)
        tracked = len(p.stdout.splitlines())
        _, wt = run(["git", "worktree", "list"], cwd=repo)
        r = {
            "path": repo,
            "tracked_files": tracked,
            "worktrees_before": wt.stdout.strip().splitlines(),
        }
        print("  worktree...", flush=True)
        r["quick"] = quick
        r["worktree"] = measure_worktree(repo, name)
        print("  checkout-index...", flush=True)
        r["checkout_index"] = measure_checkout_index(repo, name)
        print("  stash create...", flush=True)
        r["stash_create"] = measure_stash_create(repo, name)
        print("  temp-index snapshot...", flush=True)
        r["temp_index"] = measure_temp_index_snapshot(repo, name)
        if not quick:
            print("  full copy (single thread)...", flush=True)
            r["copy_1t"] = measure_copy(repo, name)
            print("  full copy (/MT:8)...", flush=True)
            r["copy_8t"] = measure_copy(repo, name, mt=8)
        _, wt2 = run(["git", "worktree", "list"], cwd=repo)
        r["worktrees_after"] = wt2.stdout.strip().splitlines()
        assert_clean(repo, allow_untracked=True)
        results["repos"][name] = r
        OUT.write_text(json.dumps(results, indent=1), encoding="utf-8", newline="\n")
        print(f"  written -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
