"""Independence without a second opinion: ablate the change, re-run the criterion.

The K-suite validates its own verifiers at three points (SPEC.md §9): red on the
unfixed tree, green on the reference solution, and red on the sham. At runtime a
pipeline has the first and cannot have the other two — there is no reference
solution and no sham to hand.

But there is a third thing the pipeline does have, which the suite does not need:
**the change itself, in hunks**. Revert one hunk and re-run the criterion. If the
criterion is still green, that hunk is not measured by anything — the gate would
have passed the change without it. Run it per hunk and the output is a coverage
map of the acceptance criterion over the diff, produced deterministically, with
no model and no second model.

This is the cheap half of gate independence, and it detects exactly the failure
class item 4's model arms are being tested on: a change whose measured part is
one site and whose unmeasured part is three.

Two subjects:

  refsol   four hunks, all four needed for correctness. How many does the
           symptom-scoped criterion actually bind?
  sham     one hunk. The degenerate case, and the control: if a one-hunk change
           has one binding hunk, the map says "1/1 covered" and says nothing
           about the three sites that are not in the diff at all.

Also reported: the same map against the K-suite's own four-consumer verifier,
which is what a criterion would look like if it were complete. The gap between
the two maps is the number the console should show.
"""

import json
import pathlib
import shutil
import tempfile

import common as C

VERIFY = C.TASK / "verify.sh"
OUT = C.HERE / "ablation-results.json"

# A hunk here is "one file's worth of the change", which is the granularity a
# `git diff` names and the granularity a revert is trivial at.
SUBJECTS = {
    "refsol": ["sla.py", "summary.py", "charges.py", "retry.py"],
    "sham": ["sla.py"],
}


def build(files, reverted=None):
    """A tree with `files` taken from the refsol, minus `reverted`."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="w11abl-"))
    work = tmp / "work"
    shutil.copytree(C.FIXTURE, work, ignore=shutil.ignore_patterns(*C.SKIP))
    for f in files:
        if f == reverted:
            continue
        shutil.copyfile(C.REFSOL / "jobs" / f, work / "jobs" / f)
    return tmp, work


def measure(work):
    ccode, _ = C.bash(C.CRITERION, work)
    posix = str(VERIFY).replace("\\", "/")
    _, out = C.bash(f'bash "{posix}" . ""', work, timeout=180)
    line = next((l for l in out.splitlines() if l.startswith("RESULT:")), "")
    truth = line.split()[1] if line.startswith("RESULT:") else "UNKNOWN"
    return ("pass" if ccode == 0 else "fail"), truth


def run(name, files):
    rows = []
    tmp, work = build(files)
    base_crit, base_truth = measure(work)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{name}: whole change -> criterion {base_crit}, suite verifier {base_truth}")
    if base_crit != "pass":
        print("  (the criterion is not green on the whole change; ablation says nothing)")

    for f in files:
        tmp, work = build(files, reverted=f)
        crit, truth = measure(work)
        shutil.rmtree(tmp, ignore_errors=True)
        binds = crit == "fail"
        rows.append(
            {
                "subject": name,
                "hunk": f"jobs/{f}",
                "criterion_without_it": crit,
                "suite_without_it": truth,
                "criterion_binds": binds,
                "suite_binds": truth == "FAIL",
            }
        )
        print(
            f"  revert jobs/{f:<12} criterion={crit:<5} "
            f"{'BINDS' if binds else 'unmeasured':<10} suite={truth}"
        )

    covered = sum(1 for r in rows if r["criterion_binds"])
    suite_cov = sum(1 for r in rows if r["suite_binds"])
    print(
        f"  -> the acceptance criterion binds on {covered}/{len(rows)} hunks; "
        f"the four-consumer verifier binds on {suite_cov}/{len(rows)}"
    )
    return rows


def main():
    all_rows = []
    for name, files in SUBJECTS.items():
        all_rows += run(name, files)
    OUT.write_text(json.dumps(all_rows, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
