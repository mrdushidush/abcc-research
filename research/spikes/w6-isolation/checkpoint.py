"""W6 item 6 — the workspace checkpoint W3 asked for, end to end.

W3's requirement (item 4, recommendation 5): *"the checkpoint row must carry an
identifier that can restore the workspace, and `Holding`/fork must refuse to
promise resumability without one."*

This builds that identifier out of git plumbing and then tries to break it:

  1. snapshot   temp index -> `add -A` -> `write-tree` -> `commit-tree`  = one sha
  2. an agent   edits two tracked files, creates three, deletes one, and writes
                into an ignored build directory
  3. snapshot   again; the diff between the two shas is the change list, for free
  4. restore    `read-tree -u --reset` + `clean -fd`, then every file is compared
                byte for byte with the pre-agent state
  5. survival   does an unreferenced snapshot survive `git gc --prune=now`?

Runs in a throwaway clone. Nothing here touches a real repository.

Usage:  python checkpoint.py
"""

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

SRC = r"D:\dev\claudette"
SCRATCH = Path(r"D:\dev\ABCC_20_powerd_by_claudette\scratch\w6-isolation")
REPO = SCRATCH / "ckpt-repo"
IDX = SCRATCH / "ckpt-index"
OUT = Path(__file__).with_name("checkpoint-results.json")


def git(args, cwd=REPO, env=None, check=True):
    t0 = time.perf_counter()
    p = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    dt = time.perf_counter() - t0
    if check and p.returncode != 0:
        raise RuntimeError(f"git {args} -> {p.returncode}: {p.stderr[:500]}")
    return dt, p.stdout.strip()


def rmtree(path):
    path = Path(path)
    if path.exists():
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(path)], capture_output=True)
        shutil.rmtree(path, ignore_errors=True)


def snapshot(parent=None, message="checkpoint"):
    """A commit that contains the working tree, without touching index or tree."""
    if IDX.exists():
        IDX.unlink()
    env = dict(os.environ, GIT_INDEX_FILE=str(IDX))
    t0 = time.perf_counter()
    git(["read-tree", "HEAD"], env=env)
    git(["add", "-A"], env=env)
    _, tree = git(["write-tree"], env=env)
    args = ["commit-tree", tree, "-m", message]
    if parent:
        args += ["-p", parent]
    _, commit = git(args, env=env)
    return round(time.perf_counter() - t0, 3), commit


def fingerprint(root):
    """Every file under root except .git: path -> sha256. Ignored files included."""
    out = {}
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in files:
            p = Path(dirpath) / f
            rel = str(p.relative_to(root)).replace("\\", "/")
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    rmtree(REPO)
    if IDX.exists():
        IDX.unlink()
    t_clone, _ = git(["clone", "--no-hardlinks", "--quiet", SRC, str(REPO)], cwd=str(SCRATCH))
    res = {"clone_s": round(t_clone, 2)}

    # A build directory the toolchain owns and .gitignore hides.
    cache = REPO / "target" / "debug"
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "artifact.bin").write_bytes(os.urandom(4 * 1024 * 1024))
    _, ign = git(["check-ignore", "-v", "target/debug/artifact.bin"], check=False)
    res["build_cache_is_ignored"] = bool(ign)

    before = fingerprint(REPO)
    t_s0, s0 = snapshot(message="pre-attempt")
    res["snapshot_s0"] = {"s": t_s0, "sha": s0, "files_in_tree": len(before)}

    # --- the attempt ---------------------------------------------------------
    edited = ["README.md", "crates/claudette/src/main.rs"]
    for rel in edited:
        p = REPO / rel
        p.write_text(p.read_text(encoding="utf-8") + "\n// agent edit\n", encoding="utf-8")
    created = ["NEWFILE.md", "crates/claudette/src/new_module.rs", "docs/new-doc.md"]
    for rel in created:
        p = REPO / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("created by the agent\n", encoding="utf-8")
    deleted = "LICENSE-MIT"
    (REPO / deleted).unlink()
    (cache / "artifact.bin").write_bytes(os.urandom(4 * 1024 * 1024))  # rebuild output
    after_attempt = fingerprint(REPO)

    t_s1, s1 = snapshot(parent=s0, message="post-attempt")
    res["snapshot_s1"] = {"s": t_s1, "sha": s1}

    t_diff, names = git(["diff", "--name-status", s0, s1])
    changes = [l.split("\t") for l in names.splitlines()]
    res["change_list"] = {
        "s": round(t_diff, 3),
        "entries": [{"status": c[0], "path": c[1]} for c in changes],
        "n": len(changes),
        "expected": sorted(edited + created + [deleted]),
        "correct": sorted(c[1] for c in changes) == sorted(edited + created + [deleted]),
        "ignored_file_present": any("target/" in c[1] for c in changes),
    }

    # `git status` for comparison: what the family's tools would have used.
    t_status, st = git(["status", "--porcelain"])
    res["status_for_comparison"] = {"s": round(t_status, 3), "lines": len(st.splitlines())}

    # --- the composition: an isolated tree AT the snapshot --------------------
    # `git worktree add` takes a commit, and S1 is a commit, so the operator's
    # uncommitted work — including files git never tracked — can be handed to an
    # isolated attempt without committing anything to a branch.
    wt = SCRATCH / "ckpt-wt"
    rmtree(wt)
    t_wt, _ = git(["worktree", "add", "--detach", str(wt), s1])
    wt_files = fingerprint(wt)
    res["worktree_at_snapshot"] = {
        "s": round(t_wt, 3),
        "has_created_files": all(c in wt_files for c in created),
        "has_edits": all(wt_files.get(e) == after_attempt.get(e) for e in edited),
        "deleted_file_absent": deleted not in wt_files,
        "build_cache_absent": not any(k.startswith("target/") for k in wt_files),
        "files": len(wt_files),
    }
    # The edits above were written by Python in text mode, i.e. with CRLF, into
    # a repository whose .gitattributes says `* text=auto eol=lf`. What the
    # snapshot captures is therefore the *normalised* content, not the bytes —
    # measure that rather than infer it.
    probe = "README.md"
    disk = (REPO / probe).read_bytes()
    blob = subprocess.run(
        ["git", "cat-file", "blob", f"{s1}:{probe}"], cwd=REPO, capture_output=True
    ).stdout
    inwt = (wt / probe).read_bytes()
    _, attrs = git(["check-attr", "text", "eol", "--", probe], check=False)
    res["eol_round_trip"] = {
        "attributes": attrs.splitlines(),
        "working_tree_crlf": disk.count(b"\r\n"),
        "snapshot_blob_crlf": blob.count(b"\r\n"),
        "worktree_at_snapshot_crlf": inwt.count(b"\r\n"),
        "bytes_identical_disk_vs_worktree": disk == inwt,
        "identical_ignoring_cr": disk.replace(b"\r\n", b"\n") == inwt.replace(b"\r\n", b"\n"),
    }

    git(["worktree", "remove", "--force", str(wt)], check=False)
    rmtree(wt)
    git(["worktree", "prune"])

    # --- restore -------------------------------------------------------------
    t0 = time.perf_counter()
    git(["read-tree", "-u", "--reset", s0])
    git(["clean", "-fd"])  # untracked, but NOT -x: the build cache stays
    t_restore = round(time.perf_counter() - t0, 3)
    restored = fingerprint(REPO)

    tracked_before = {k: v for k, v in before.items() if not k.startswith("target/")}
    tracked_after = {k: v for k, v in restored.items() if not k.startswith("target/")}
    res["restore"] = {
        "s": t_restore,
        "exact_tracked_match": tracked_before == tracked_after,
        "missing": sorted(set(tracked_before) - set(tracked_after))[:5],
        "extra": sorted(set(tracked_after) - set(tracked_before))[:5],
        "differing": sorted(
            k for k in set(tracked_before) & set(tracked_after) if tracked_before[k] != tracked_after[k]
        )[:5],
        "build_cache_survived": (REPO / "target" / "debug" / "artifact.bin").exists(),
        "build_cache_is_post_attempt_copy": restored.get("target/debug/artifact.bin")
        == after_attempt.get("target/debug/artifact.bin"),
    }

    # --- does an unreferenced snapshot survive gc? ---------------------------
    _, loose = snapshot(message="unreferenced")
    _, reffed = snapshot(message="reffed")
    git(["update-ref", "refs/abcc/checkpoints/probe", reffed])
    t_gc, _ = git(["gc", "--prune=now", "--quiet"])
    def exists(sha):
        p = subprocess.run(["git", "cat-file", "-e", sha], cwd=REPO, capture_output=True)
        return p.returncode == 0
    res["gc"] = {
        "s": round(t_gc, 2),
        "unreferenced_survived": exists(loose),
        "reffed_survived": exists(reffed),
        "s0_survived": exists(s0),
        "s1_survived": exists(s1),
    }

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps(res, indent=1))
    rmtree(REPO)
    if IDX.exists():
        IDX.unlink()
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
