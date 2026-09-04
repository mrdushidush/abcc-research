"""Print what a task's three trees actually do — fixture, +refsol, +sham.

    python harness/scripts/od_show.py corpus/suites/od/tasks/<id>

The authoring loop for this suite is *predict the three outputs, then look*, and
this is the looking half. `gate-task.sh` answers PASS/FAIL against the verifier;
this shows the numbers the verifier is grading, which is what a wrong expected
value looks like before it becomes a verify.sh nobody can satisfy.

⚠ It builds each tree the way `tests/corpus.rs` does — fixture copied, overlay
copied on top — and not `cp refsol tree`, which would produce a tree with no
entry point and read exactly like a real failure.
"""

import os
import shutil
import subprocess
import sys
import tempfile

ENTRY = "run.py"
SKIP = {"__pycache__", ".pytest_cache"}


def copy(src, dst):
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*SKIP))


def build_and_run(task, overlay, tests=False):
    root = tempfile.mkdtemp(prefix="od-show-")
    tree = os.path.join(root, "t")
    try:
        copy(os.path.join(task, "fixture"), tree)
        if overlay:
            path = os.path.join(task, overlay)
            if not os.path.isdir(path):
                return "<no {}/>".format(overlay)
            copy(path, tree)
        out = subprocess.run(
            [sys.executable, ENTRY], cwd=tree, capture_output=True, text=True
        )
        text = out.stdout + (("\n[stderr]\n" + out.stderr) if out.returncode else "")
        if tests:
            got = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"], cwd=tree, capture_output=True, text=True
            )
            last = [l for l in got.stdout.strip().split("\n") if l.strip()]
            text += "\n[pytest] " + (last[-1] if last else "<no output>")
        return "exit {}\n{}".format(out.returncode, text)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main(argv):
    if len(argv) < 2:
        sys.stderr.write(__doc__)
        return 2
    for task in argv[1:]:
        task = task.rstrip("/\\")
        print("=" * 70)
        print(task)
        for overlay in (None, "refsol", "sham"):
            print("-" * 70)
            print("--- {}".format(overlay or "fixture"))
            print(build_and_run(task, overlay, tests=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
