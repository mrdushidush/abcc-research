"""Materialise the four candidate changes and measure them. No model involved.

Two numbers per artifact, both run rather than asserted:

  criterion   the symptom-scoped acceptance criterion an M1 Plan phase would
              emit from this ticket. Every artifact here is GREEN on it — that
              is the point of the set.
  truth       the K-suite's own four-consumer verifier, `verify.sh`, which was
              gated at all three SPEC.md §9 points on 2026-08-17.

The self-test runs first and refuses to write results if the runner cannot tell
exit 0 from exit 1, cannot find a python, or disagrees with the two ground truths
the task file already records (unfixed -> FAIL, refsol -> PASS). Item 3 threw
away two confident, complete and wrong runs for exactly this reason.
"""

import json
import pathlib
import shutil
import tempfile

import common as C

VERIFY = C.TASK / "verify.sh"
OUT = C.HERE / "ground-truth.json"


def run_criterion(work):
    return C.bash(C.CRITERION, work)


def run_truth(work):
    posix = str(VERIFY).replace("\\", "/")
    code, out = C.bash(f'bash "{posix}" . ""', work, timeout=180)
    line = next((l for l in out.splitlines() if l.startswith("RESULT:")), "")
    verdict = line.split()[1] if line.startswith("RESULT:") else "UNKNOWN"
    return verdict, line


def with_tree(artifact, fn):
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="w11ind-"))
    try:
        work = C.materialise(artifact, tmp)
        return fn(work)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def selftest():
    checks = []

    code, _ = C.bash("exit 0", C.HERE)
    checks.append(("runner sees exit 0", code == 0, code))
    code, _ = C.bash("exit 3", C.HERE)
    checks.append(("runner sees exit 3", code == 3, code))
    code, out = C.bash("python3 -c 'print(7*6)'", C.HERE)
    checks.append(("python3 shim runs", code == 0 and "42" in out, out.strip()[:40]))
    checks.append(("fixture exists", C.FIXTURE.is_dir(), str(C.FIXTURE)))
    checks.append(("verify.sh exists", VERIFY.is_file(), str(VERIFY)))

    unfixed = {"id": "unfixed", "edits": [], "diff": "", "missing": []}
    code, _ = with_tree(unfixed, run_criterion)
    checks.append(("criterion is RED on the unfixed tree", code == 1, code))
    verdict, line = with_tree(unfixed, run_truth)
    checks.append(("verifier FAILs the unfixed tree", verdict == "FAIL", line[:70]))

    verdict, line = with_tree(C.ARTIFACT_BY_ID["refsol"], run_truth)
    checks.append(("verifier PASSes the refsol", verdict == "PASS", line[:70]))

    ok = True
    for name, passed, detail in checks:
        print(f"  [{'ok ' if passed else 'FAIL'}] {name:<42} {detail}")
        ok = ok and passed
    return ok


def main():
    print("-- self-test --")
    if not selftest():
        raise SystemExit("self-test failed; not writing results")
    print()

    rows = []
    for a in C.ARTIFACTS:

        def measure(work, a=a):
            ccode, cout = run_criterion(work)
            verdict, line = run_truth(work)
            _, report = C.bash("python3 run.py data/jobs.json", work)
            return ccode, cout, verdict, line, report

        ccode, cout, verdict, line, report = with_tree(a, measure)
        rows.append(
            {
                "id": a["id"],
                "what": a["what"],
                "criterion_exit": ccode,
                "criterion_out": cout.strip(),
                "criterion": "pass" if ccode == 0 else "fail",
                "truth": verdict,
                "truth_line": line,
                "missing": a["missing"],
                "report": report.strip(),
            }
        )
        print(
            f"{a['id']:<10} criterion={'pass' if ccode == 0 else 'fail':<5} "
            f"truth={verdict:<5} {line[:88]}"
        )

    OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")

    greens = [r for r in rows if r["criterion"] == "pass"]
    print(
        f"\n{len(greens)}/{len(rows)} artifacts are green on the criterion; "
        f"of those, {sum(1 for r in greens if r['truth'] == 'FAIL')} are wrong."
    )


if __name__ == "__main__":
    main()
