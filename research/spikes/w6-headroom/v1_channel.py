"""Can v1's validation channel even express the instruments item 4 is pricing?

A faithful replay of `POST /run-validation`
(`agent-battle-command-center/packages/agents/src/main.py:513-589`, HEAD d5528ea):

    command    = request.command.strip()
    first_word = command.split()[0]
    if first_word in ("go","php","python","python3","node","tsx"):
        cmd = shlex.split(command)
    else:
        cmd = ["python3", "-c", command]        # for language == "python"
    result  = subprocess.run(cmd, cwd=WORKSPACE_PATH, ...)
    success = result.returncode == 0 and "PASS" in result.stdout

Nothing here talks to v1: the rule is 6 lines and it is reimplemented verbatim,
then run against real trees in this repository — the reference solution and the
shipped sham for each K task. The question is not whether v1's ladder is a good
ladder. It is whether a linter, a type checker or a test run can be *put on it*.
"""

import json
import shlex
import sys

import common as C

PREFIXES = ("go", "php", "python", "python3", "node", "tsx")

CANDIDATES = [
    # what the donor's own benchmarks put in the field
    ("v1 benchmark shape", 'python3 -c "import run; print(\'PASS\')"'),
    # the five rungs item 4 is pricing, written the way an operator would
    ("linter", "ruff check ."),
    ("type check", "mypy ."),
    ("tests", "pytest -q"),
    # ... and written so the dispatcher at least recognises the binary
    ("linter, dispatched", "python3 -m ruff check ."),
    ("type check, dispatched", "python3 -m mypy ."),
    ("tests, dispatched", "python3 -m pytest -q"),
    # the task's own entry point, which is what a repository task would name
    ("the task's runner", "python3 run.py data/jobs.json"),
]


def v1_run_validation(command, work, language="python"):
    """The endpoint's body, reimplemented. Returns (success, exit_code, output)."""
    command = command.strip()
    first_word = command.split()[0] if command else ""
    if first_word in PREFIXES:
        cmd = shlex.split(command)
    else:
        if language == "python":
            cmd = ["python3", "-c", command]
        else:
            return False, -1, f"Unsupported language: {language}"
    # v1 runs this inside its agents container, where `python3` is the
    # interpreter. On this host `python3` on PATH is the Windows Store alias, and
    # CreateProcess resolves argv[0] against the *caller's* PATH whatever env we
    # pass — so argv[0] is rewritten to the interpreter that exists here. The rule
    # under test is the dispatch and the success condition, not the spelling.
    if cmd and cmd[0] in ("python3", "python"):
        cmd = [C.REAL_PYTHON] + cmd[1:]
    code, out, _ms = C.run(cmd, work, timeout=120)
    if code is None:
        return False, -1, "Validation timed out"
    # the endpoint splits stdout/stderr; `success` reads stdout only
    stdout = out
    success = code == 0 and "PASS" in stdout
    return success, code, out


def main():
    task_id = sys.argv[1] if len(sys.argv) > 1 else "finish_the_cancelled_status"
    task = C.K_TASKS / task_id
    rows = []
    for art_id, make in C.constructed(task_id):
        if art_id == "unfixed":
            continue
        tmp = C.pathlib.Path(C.tempfile.mkdtemp(prefix="w6hr-v1-"))
        try:
            work = make(tmp / "work")
            for label, cmd in CANDIDATES:
                ok, code, out = v1_run_validation(cmd, work)
                first = " ".join(out.split())[:90]
                rows.append({"artifact": art_id, "label": label, "command": cmd,
                             "v1_success": ok, "exit_code": code, "output": first})
                print(f"{art_id:7} {label:24} v1_success={str(ok):5} exit={str(code):4} {first[:70]}",
                      flush=True)
        finally:
            C.shutil.rmtree(tmp, ignore_errors=True)
    (C.HERE / "v1-channel-results.json").write_text(
        json.dumps({"task": task_id, "rows": rows}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
