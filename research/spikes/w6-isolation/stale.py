"""W6 item 6 — is `git status` clean a claim about content?

Found while pricing the mechanisms: touching one file's mtime in the v1 donor
turned a clean tree into a 500-line modification. The file had differed from its
blob for months; git's index stat cache (size + mtime) matched, so `git status`
never re-hashed it.

This scans every tracked file in each repository, hashes it the way git would
(attributes and filters applied, via `git hash-object`), and compares with the
index entry — then reports what `git status` says about the same tree.

Nothing is written. Read-only, including mtimes: `git hash-object` does not
touch the files it reads.

Usage:  python stale.py
"""

import json
import subprocess
from pathlib import Path

OUT = Path(__file__).with_name("stale-results.json")

REPOS = {
    "bcf": r"D:\dev\battle-command-forge",
    "claudette": r"D:\dev\claudette",
    "v1": r"D:\dev\agent-battle-command-center",
    "abcc20": r"D:\dev\ABCC_20_powerd_by_claudette",
}


def git(args, cwd, stdin=None):
    p = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if p.returncode != 0:
        raise RuntimeError(f"git {args} -> {p.returncode}: {p.stderr[:400]}")
    return p.stdout


def scan(repo):
    entries = []
    for line in git(["ls-files", "-s"], repo).splitlines():
        meta, path = line.split("\t", 1)
        mode, sha, stage = meta.split()
        if mode in ("160000", "120000"):  # submodule, symlink
            continue
        entries.append((path, sha))

    present = [(p, s) for p, s in entries if (Path(repo) / p).is_file()]
    paths = "\n".join(p for p, _ in present) + "\n"
    hashes = git(["hash-object", "--stdin-paths"], repo, stdin=paths).split()
    assert len(hashes) == len(present), (len(hashes), len(present))

    differs = [
        {"path": p, "index": s, "disk": h}
        for (p, s), h in zip(present, hashes)
        if s != h
    ]
    status = [l for l in git(["status", "--porcelain"], repo).splitlines() if l.strip()]
    status_paths = {l[3:].strip().strip('"') for l in status}
    hidden = [d for d in differs if d["path"] not in status_paths]

    # Classify the hidden ones: EOL-only, or a real content difference?
    for d in hidden:
        blob = subprocess.run(
            ["git", "cat-file", "blob", d["index"]], cwd=repo, capture_output=True
        ).stdout
        disk = (Path(repo) / d["path"]).read_bytes()
        d["eol_only"] = blob.replace(b"\r\n", b"\n") == disk.replace(b"\r\n", b"\n")
        d["blob_bytes"] = len(blob)
        d["disk_bytes"] = len(disk)
        d["direction"] = (
            "disk_crlf_blob_lf"
            if b"\r\n" in disk and b"\r\n" not in blob
            else ("disk_lf_blob_crlf" if b"\r\n" in blob and b"\r\n" not in disk else "other")
        )
    return {
        "tracked": len(entries),
        "checked": len(present),
        "content_differs": len(differs),
        "status_reports": len(status),
        "hidden_from_status": hidden,
    }


def main():
    out = {}
    for name, repo in REPOS.items():
        print(f"=== {name}", flush=True)
        out[name] = scan(repo)
        h = out[name]["hidden_from_status"]
        print(
            f"  tracked={out[name]['tracked']} status={out[name]['status_reports']} "
            f"hidden={len(h)}" + (f" e.g. {h[0]['path']}" if h else ""),
            flush=True,
        )
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8", newline="\n")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
