"""F832's check by hand, for the H1 cells: apply ONLY the attempt's test hunk to its
opening checkpoint and run that test. Red = the test proves the fix."""
import os
import re
import shutil
import subprocess
import sys

REPO = "D:/dev/claudette"
SCRATCH = os.environ.get("RED_CHECK_SCRATCH", os.path.join(os.environ["TEMP"], "red-check"))
FILE = "crates/claudette/src/tools/semantic.rs"


def run(args, cwd, env=None, check=True):
    p = subprocess.run(args, cwd=cwd, env=env, capture_output=True)
    if check and p.returncode != 0:
        raise SystemExit(f"{args} exited {p.returncode}: {p.stderr.decode('utf-8', 'replace')}")
    return p


def pair(task):
    out = run(["abcc", "diff", task, "--repo", REPO], cwd="D:/dev/abcc").stdout.decode("utf-8")
    m = re.search(r"^checkpoints (\w+)\.\.(\w+)$", out, re.M)
    return m.group(1), m.group(2)


for task in sys.argv[1:]:
    frm, to = pair(task)
    patch = run(["git", "diff", frm, to, "--", FILE], cwd=REPO).stdout  # bytes, LF kept
    head, *hunks = re.split(rb"(?m)^(?=@@ )", patch)
    tests = [h for h in hunks if b"#[test]" in h]
    fixes = [h for h in hunks if b"#[test]" not in h]
    names = re.findall(rb"fn (\w+)\(\)", b"".join(tests))
    wt = f"{SCRATCH}/red-{task}"
    if os.path.exists(wt):
        run(["git", "worktree", "remove", "--force", wt], cwd=REPO, check=False)
        shutil.rmtree(wt, ignore_errors=True)
    run(["git", "worktree", "add", "--detach", wt, frm], cwd=REPO)
    try:
        only_test = head + b"".join(tests)
        p = subprocess.run(["git", "apply", "--recount", "-"], cwd=wt, input=only_test, capture_output=True)
        if p.returncode != 0:
            print(task, "test hunk does not apply alone:", p.stderr.decode())
            continue
        env = dict(os.environ, CARGO_TARGET_DIR=f"{SCRATCH}/red-target")
        name = names[-1].decode() if names else ""
        t = run(["cargo", "test", "-p", "claudette", "--lib", name], cwd=wt, env=env, check=False)
        out = t.stdout.decode("utf-8", "replace")
        verdict = "RED (proves the fix)" if t.returncode != 0 else "GREEN (regression guard only)"
        summary = [l for l in out.splitlines() if l.startswith("test ") and name in l]
        print(f"{task} {frm}..{to} fix hunks {len(fixes)} test hunks {len(tests)} test {name}: {verdict}")
        for l in summary:
            print("   ", l)
    finally:
        run(["git", "worktree", "remove", "--force", wt], cwd=REPO, check=False)
