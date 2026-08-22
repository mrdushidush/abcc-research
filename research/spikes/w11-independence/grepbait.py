"""The five criteria that discriminated, against a sham that knows what they grep for.

`criteria_vs_shams.py` found 5 of 35 criteria that accept the reference solution
and reject all three wrong answers. Every one of the five is a `grep` for
`is_terminal` or `CANCELLED` in a named file, and the `comment` artifact's
annotations happen to be written in lower case, so the greps stayed red by
accident of wording.

SPEC.md §9's generated sham for the K-suite's 24 `presence_only` tasks is exactly
the counter to this: *"a file whose entire content is a comment holding every
substring the verifier searches for."* This builds that sham for these five
criteria — the same three annotated files, with the two searched tokens written
into the comment — and re-runs them.

Nothing here needs a GPU, and the whole thing is ten seconds.
"""

import json
import pathlib
import shutil
import tempfile

import common as C

CRITERIA = json.loads(
    (C.HERE.parent / "w11-artifacts/criterion-results.json").read_text("utf-8")
)
DISC = json.loads((C.HERE / "criteria-vs-shams.json").read_text("utf-8"))
BAIT = "    # CANCELLED is handled: is_terminal covers it upstream\n"


def bait_tree():
    """`comment`, with the annotations rewritten to carry the searched tokens."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="w11bait-"))
    work = C.materialise(C.ARTIFACT_BY_ID["comment"], tmp)
    for f, anchor in (
        ("summary.py", "    # cancelled jobs are accounted for by the terminal-status handling above\n"),
        ("charges.py", "    # cancellation is covered: a cancelled job never reaches a chargeable state\n"),
        ("retry.py", "    # cancelled jobs are excluded upstream by the scheduler, nothing to do here\n"),
    ):
        p = work / "jobs" / f
        t = p.read_text(encoding="utf-8")
        assert anchor in t, f
        p.write_text(t.replace(anchor, BAIT, 1), encoding="utf-8", newline="")
    return tmp, work


def main():
    tmp, work = bait_tree()
    assert C.bash("exit 3", work)[0] == 3

    # The bait changes comments only, so the behaviour is still the sham's.
    posix = str(C.TASK / "verify.sh").replace("\\", "/")
    _, out = C.bash(f'bash "{posix}" . ""', work, timeout=180)
    line = next((l for l in out.splitlines() if l.startswith("RESULT:")), "")
    print(f"suite verifier on the bait tree: {line[:90]}")
    assert line.startswith("RESULT: FAIL"), "the bait tree must still be a wrong answer"

    disc = [r for r in DISC if r["discriminating"]]
    print(f"\n{len(disc)} criteria discriminated against the plain shams:\n")
    flipped = 0
    for r in disc:
        cmd = CRITERIA[r["n"] - 1]["command"]
        code, _ = C.bash(cmd, work)
        if code == 0:
            flipped += 1
        print(
            f"  #{r['n']:<3} {'GREEN — defeated' if code == 0 else 'red   — survives'}  {cmd[:78]}"
        )
    shutil.rmtree(tmp, ignore_errors=True)
    print(
        f"\n{flipped}/{len(disc)} defeated by a comment carrying the tokens they search for."
    )
    (C.HERE / "grepbait-results.json").write_text(
        json.dumps({"discriminating": len(disc), "defeated": flipped}, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
