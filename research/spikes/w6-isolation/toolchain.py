"""W6 item 6 — what an isolated worktree does not contain, and whether the
toolchain profile survives the move (OQ-W6-11).

Item 5's answer to "what is language-specific" was a toolchain profile: a marker
file, a build command, a test command, a resolved binary path. The marker files
are tracked, so the profile resolves the same in a worktree. Everything the
profile *names* — the installed dependencies, the build cache, the secrets, the
data a probe reads — is ignored by git, so a worktree has none of it.

For each repository this records: the ignored top-level entries and their size,
the profile resolved in the main tree and in a fresh worktree, and one executed
command per repo showing what the isolated tree actually does.

Usage:  python toolchain.py
"""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

SCRATCH = Path(r"D:\dev\ABCC_20_powerd_by_claudette\scratch\w6-isolation")
OUT = Path(__file__).with_name("toolchain-results.json")

REPOS = {
    "bcf": r"D:\dev\battle-command-forge",
    "claudette": r"D:\dev\claudette",
    "v1": r"D:\dev\agent-battle-command-center",
    "abcc20": r"D:\dev\ABCC_20_powerd_by_claudette",
}

# Item 5's profile, minus the parsers it deleted: a marker file chooses a
# toolchain, and the toolchain names a binary and two commands.
PROFILE = [
    ("Cargo.toml", "cargo", ["cargo", "build"], ["cargo", "test"]),
    ("package.json", "npm", ["npm", "run", "build"], ["npm", "test"]),
    ("pyproject.toml", "python", [], ["pytest"]),
    ("requirements.txt", "python", [], ["pytest"]),
    ("go.mod", "go", ["go", "build", "./..."], ["go", "test", "./..."]),
]

# One executed check per repo: what the isolated tree says when the profile's
# test command is run in it. Short timeouts — the point is the failure mode, not
# the suite.
CHECKS = {
    # (subdirectory to run in, argv). The node rows resolve a dependency the
    # tree's own package.json declares — the question a worktree has to answer
    # before any test command in it can run.
    "claudette": (".", ["cargo", "metadata", "--offline", "--format-version", "1"]),
    "bcf": (".", ["cargo", "metadata", "--offline", "--format-version", "1"]),
    "v1": ("packages/api", ["node", "-e", "console.log(require.resolve('typescript'))"]),
    "abcc20": (
        "research/spikes/w6-language",
        ["node", "-e", "console.log(require.resolve('typescript'))"],
    ),
}


def sh(args, cwd=None, timeout=120):
    t0 = time.perf_counter()
    try:
        p = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return {
            "rc": p.returncode,
            "s": round(time.perf_counter() - t0, 2),
            "out": (p.stdout or "").strip().splitlines()[:4],
            "err": (p.stderr or "").strip().splitlines()[:6],
        }
    except subprocess.TimeoutExpired:
        return {"rc": None, "s": timeout, "out": [], "err": ["TIMEOUT"]}
    except FileNotFoundError as e:
        return {"rc": None, "s": 0, "out": [], "err": [f"not found: {e}"]}


def rmtree(path):
    path = Path(path)
    if path.exists():
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(path)], capture_output=True)
        shutil.rmtree(path, ignore_errors=True)


def tree_size(path, cap_files=200000):
    total = files = 0
    for root, _d, fs in os.walk(path):
        for f in fs:
            try:
                total += os.lstat(os.path.join(root, f)).st_size
                files += 1
            except OSError:
                pass
            if files >= cap_files:
                return total, files, True
    return total, files, False


def resolve_profile(tree):
    """Which toolchains does this tree declare, and is the binary on PATH?"""
    found = []
    for marker, binary, build_cmd, test_cmd in PROFILE:
        hits = []
        for root, dirs, files in os.walk(tree):
            dirs[:] = [
                d
                for d in dirs
                if d
                not in (".git", "node_modules", "target", "runs", "__pycache__", "dist", "scratch")
            ]
            if marker in files:
                hits.append(os.path.relpath(os.path.join(root, marker), tree))
            if len(hits) > 6:
                break
        if hits:
            found.append(
                {
                    "marker": marker,
                    "sites": hits[:6],
                    "binary": binary,
                    "binary_path": shutil.which(binary),
                    "build": build_cmd,
                    "test": test_cmd,
                }
            )
    return found


def ignored_entries(repo):
    """Top-level ignored paths, the way `git clean -nXd` sees them."""
    p = subprocess.run(
        [
            "git",
            "ls-files",
            "--others",
            "--ignored",
            "--exclude-standard",
            "--directory",
            "--no-empty-directory",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = []
    for line in p.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        full = Path(repo) / line
        if full.is_dir():
            size, files, capped = tree_size(full)
        else:
            try:
                size, files, capped = full.stat().st_size, 1, False
            except OSError:
                size, files, capped = 0, 0, False
        out.append({"path": line, "bytes": size, "files": files, "capped": capped})
    out.sort(key=lambda r: -r["bytes"])
    return out


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    results = {}
    for name, repo in REPOS.items():
        print(f"=== {name}", flush=True)
        wt = SCRATCH / f"tc-{name}"
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=repo, capture_output=True)
        rmtree(wt)
        subprocess.run(["git", "worktree", "prune"], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(wt), "HEAD"],
            cwd=repo,
            capture_output=True,
            check=True,
        )
        r = {
            "ignored": ignored_entries(repo),
            "profile_main": resolve_profile(repo),
            "profile_worktree": resolve_profile(wt),
            "check_cmd": CHECKS[name][1],
            "check_cwd": CHECKS[name][0],
            "check_main": sh(CHECKS[name][1], cwd=str(Path(repo) / CHECKS[name][0])),
            "check_worktree": sh(CHECKS[name][1], cwd=str(wt / CHECKS[name][0])),
        }
        r["ignored_total_bytes"] = sum(e["bytes"] for e in r["ignored"])
        r["ignored_total_files"] = sum(e["files"] for e in r["ignored"])
        r["profiles_identical"] = [p["marker"] for p in r["profile_main"]] == [
            p["marker"] for p in r["profile_worktree"]
        ]
        results[name] = r
        print(
            f"  ignored {r['ignored_total_bytes']/1e6:.0f} MB / {r['ignored_total_files']} files; "
            f"profile same={r['profiles_identical']}; "
            f"check main rc={r['check_main']['rc']} worktree rc={r['check_worktree']['rc']}",
            flush=True,
        )
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=repo, capture_output=True)
        rmtree(wt)
        subprocess.run(["git", "worktree", "prune"], cwd=repo, capture_output=True)
        OUT.write_text(json.dumps(results, indent=1), encoding="utf-8", newline="\n")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
