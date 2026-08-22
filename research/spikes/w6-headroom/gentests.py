"""What does a *generated test* buy, and does it matter when it was written?

W11 item 3 (F279) measured generated acceptance *criteria* -- shell one-liners --
and found they bought approximately nothing: 24 of 35 accepted the shipped sham.
A test is a different artifact: it executes, it asserts behaviour, and it is the
thing BCF's TESTER stage was supposed to produce. So it gets its own measurement.

Two arms, because *when* the test is written is the whole question:

  * **tdd**      -- the model sees the ticket and the repository, and writes the
                   test BEFORE any change exists. BCF's stage order.
  * **posthoc**  -- the model sees the ticket, the repository AND the diff of the
                   change, and writes tests for it. What "add tests for your
                   change" produces, and the trap: a test that mirrors the change
                   passes by construction.

Scoring runs each generated file against three trees whose truth is known:

    unfixed  must be RED    (a test green on the unfixed tree measures nothing)
    sham     must be RED    (the local wrong answer)
    refsol   must be GREEN  (or the gate stops correct work)

Only a file that is red-red-green *discriminates*. Everything else is recorded
as what it actually was, including the ones that do not import.

Held constants: champion `qwen3.6-35b-a3b-mtp@iq3_s`, `-c 65536 --gpu max
--parallel 1 -y`, LM Studio on :1234, temperature 0, `max_tokens` 8192.

    python gentests.py [reps=3] [arms=tdd,posthoc]
"""

import json
import pathlib
import shutil
import sys
import time
import urllib.request

import common as C

BASE = "http://localhost:1234"
CHAMPION = "qwen3.6-35b-a3b-mtp@iq3_s"
OUT = C.HERE / "gentests-results.json"

SYSTEM = (
    "You are a careful engineer writing pytest tests for an existing Python "
    "repository. You write tests that fail when the described defect is present "
    "and pass when it is fixed. You output one complete test file and nothing "
    "else."
)


def sources(task_id):
    """Every source and doc file in the fixture, as the model would read them."""
    fx = C.K_TASKS / task_id / "fixture"
    parts = []
    for p in sorted(fx.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(fx).as_posix()
        if any(s in rel for s in ("__pycache__", ".pytest_cache")):
            continue
        if p.suffix not in (".py", ".md"):
            continue
        parts.append("===== " + rel + " =====\n" + p.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


def diff_of(task_id, overlay):
    """The unified diff between the fixture and an overlay, as text.

    Newlines are normalised first: the fixtures are LF and the overlays are CRLF,
    so a byte diff reports every line of every touched file as changed, which is
    a fact about the corpus and not about the change.
    """
    import difflib

    task = C.K_TASKS / task_id
    out = []
    for p in sorted((task / overlay).rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(task / overlay).as_posix()
        before = task / "fixture" / rel
        a = before.read_text(encoding="utf-8").replace("\r\n", "\n").splitlines(True)
        b = p.read_text(encoding="utf-8").replace("\r\n", "\n").splitlines(True)
        out.append(
            "".join(difflib.unified_diff(a, b, "a/" + rel, "b/" + rel, n=3)).rstrip()
        )
    return "\n".join(out)


def prompt(task_id, arm):
    ticket = (C.K_TASKS / task_id / "prompt.txt").read_text(encoding="utf-8")
    body = [
        "# The ticket",
        ticket.strip(),
        "",
        "# The repository, in full",
        sources(task_id),
    ]
    if arm in ("posthoc", "posthoc_sham"):
        overlay = "refsol" if arm == "posthoc" else "sham"
        body += [
            "",
            "# The change that was just made",
            "```diff",
            diff_of(task_id, overlay).strip(),
            "```",
        ]
        ask = (
            "Write a pytest test file covering the change above. It must fail on "
            "the code as it was before the change and pass after it."
        )
    elif arm == "property":
        ask = (
            "No fix has been written yet. Write a PROPERTY-BASED test file using "
            "hypothesis (`from hypothesis import given, strategies as st`) that "
            "states the invariants the ticket and the repository's own docs "
            "require, generates inputs, and FAILS on the repository exactly as "
            "shown above. It must pass once the ticket is correctly and "
            "completely resolved. Do not assert on any single hand-picked "
            "example unless it is a genuine boundary of a stated invariant."
        )
    else:
        ask = (
            "No fix has been written yet. Write a pytest test file that FAILS on "
            "the repository exactly as shown above, and that will pass once the "
            "ticket is correctly and completely resolved."
        )
    body += [
        "",
        "# Your task",
        ask,
        "",
        "Rules:",
        "- Output ONLY the contents of the file, starting with the first import.",
        "- No markdown fence, no prose, no explanation.",
        "- The file will be written to tests/test_generated.py and run with "
        "'pytest -q' from the repository root.",
        "- Import the repository's own modules; do not re-implement them.",
    ]
    return "\n".join(body)


def call(text, max_tokens=8192, timeout=1800):
    payload = {
        "model": CHAMPION,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": text},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": False,
    }
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode("utf-8"))
    ch = d["choices"][0]
    return {
        "content": ch["message"].get("content") or "",
        "finish_reason": ch.get("finish_reason"),
        "usage": d.get("usage", {}),
        "wall_s": round(time.time() - t0, 1),
    }


def strip_fence(s):
    s = s.strip()
    if s.startswith("```"):
        lines = s.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines)
    return s.strip()


def score(task_id, test_src):
    """Run one generated file against the three trees whose truth is known."""
    res = {}
    for art_id, make in C.constructed(task_id):
        tmp = pathlib.Path(C.tempfile.mkdtemp(prefix="w6hr-gt-"))
        try:
            work = make(tmp / "work")
            tdir = work / "tests"
            tdir.mkdir(exist_ok=True)
            # the generated file is the ONLY test that runs, so a green here is
            # this file's green and not the fixture suite's
            for old in tdir.glob("test_*.py"):
                old.unlink()
            (tdir / "test_generated.py").write_text(test_src, encoding="utf-8")
            code, out, ms = C.run(
                [C.REAL_PYTHON, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                work,
                timeout=180,
            )
            tail = ([l for l in out.splitlines() if l.strip()][-1:] or [""])[0]
            if code is None:
                verdict, detail = "error", "<timeout>"
            elif code == 0:
                verdict, detail = "green", tail[:160]
            elif code == 1:
                verdict, detail = "red", tail[:160]
            else:
                # 2 usage, 3 internal, 4 cmdline, 5 no tests collected
                verdict, detail = "error", tail[:160]
            res[art_id] = {"verdict": verdict, "detail": detail, "ms": ms, "exit": code}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    discriminates = (
        res.get("unfixed", {}).get("verdict") == "red"
        and res.get("sham", {}).get("verdict") == "red"
        and res.get("refsol", {}).get("verdict") == "green"
    )
    return res, discriminates


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    arms = sys.argv[2].split(",") if len(sys.argv) > 2 else ["tdd", "posthoc"]
    rows = []
    if OUT.exists():
        rows = json.loads(OUT.read_text(encoding="utf-8"))
    for arm in arms:
        for task_id in C.k_task_ids():
            for rep in range(1, reps + 1):
                key = (arm, task_id, rep)
                if any((r["arm"], r["task"], r["rep"]) == key for r in rows):
                    continue
                p = prompt(task_id, arm)
                try:
                    r = call(p)
                except Exception as e:  # noqa: BLE001
                    rows.append(
                        {"arm": arm, "task": task_id, "rep": rep, "error": str(e)[:200]}
                    )
                    print(arm, task_id, "r%d" % rep, "ERROR", str(e)[:120], flush=True)
                    OUT.write_text(json.dumps(rows, indent=1), encoding="utf-8")
                    continue
                src = strip_fence(r["content"])
                res, disc = score(task_id, src) if src else ({}, False)
                rows.append(
                    {
                        "arm": arm,
                        "task": task_id,
                        "rep": rep,
                        "prompt_chars": len(p),
                        "finish_reason": r["finish_reason"],
                        "usage": r["usage"],
                        "wall_s": r["wall_s"],
                        "empty": not src,
                        "chars": len(src),
                        "scores": res,
                        "discriminates": disc,
                        "source": src,
                    }
                )
                v = {k: res[k]["verdict"] for k in res}
                print(
                    "%-8s %-34s r%d %6.1fs %5dtok unfixed=%-6s sham=%-6s refsol=%-6s disc=%s"
                    % (
                        arm,
                        task_id,
                        rep,
                        r["wall_s"],
                        r["usage"].get("completion_tokens", 0),
                        v.get("unfixed", "-"),
                        v.get("sham", "-"),
                        v.get("refsol", "-"),
                        disc,
                    ),
                    flush=True,
                )
                OUT.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    OUT.write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
