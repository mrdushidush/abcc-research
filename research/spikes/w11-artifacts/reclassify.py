"""Re-run the criteria `criterion.py` collected, with a runner that works.

`criterion.py`'s first run classified almost every criterion as `binds` on an
exit code of 9009 — this host's `python3` on PATH is the Microsoft Store
shortcut, which prints an advertisement and exits non-zero no matter what
follows it. "Exits non-zero" was therefore true and meaningless, which is the
exact failure mode item 2 recommendation 6 warns about: *cannot run* is not
*fails*, and a runner that cannot tell them apart turns every criterion into a
binding one.

Two passes over the same commands, so both numbers are on the record:

  as-written   Git Bash, this host's PATH untouched. Answers "would this
               criterion run on the machine it was written for?"
  shimmed      Git Bash with a shim directory in front of PATH mapping
               `python3` to the interpreter that actually exists. Answers
               "what does the criterion measure, once it can run at all?"

Classification (item 2 recommendation 6):
  exit != 0 for a reason that is not "cannot run"  -> binds
  exit == 0                                        -> does-not-discriminate
  cannot run                                       -> unrunnable, never a fail
"""

import json
import os
import pathlib
import shutil
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
FIXTURE = REPO / "corpus/suites/k/tasks/finish_the_cancelled_status/fixture"

REAL_PYTHON = shutil.which("python")

# `bash` on PATH here is WSL's, which cannot see a Windows working directory and
# fails every command with `execvpe(/bin/bash)`. Git Bash is the shell these
# criteria assume, and naming it explicitly is the difference between measuring
# the criteria and measuring the host.
BASH = next(
    (
        c
        for c in (
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files\Git\usr\bin\bash.exe",
        )
        if pathlib.Path(c).exists()
    ),
    "bash",
)

CANNOT_RUN = (
    "was not found",              # the Microsoft Store python3 shim
    "not recognized",
    "command not found",
    "No such file or directory",
)


def make_shim(dirpath):
    """A `python3` that is the python this host actually has."""
    p = pathlib.Path(dirpath) / "python3"
    p.write_text(f'#!/usr/bin/env bash\nexec "{REAL_PYTHON}" "$@"\n', encoding="utf-8")
    os.chmod(p, 0o755)


def run(cmd, cwd_rel, shim):
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="w11crit-"))
    work = tmp / "fixture"
    shutil.copytree(FIXTURE, work)
    cwd = work / (cwd_rel or ".")
    if not cwd.is_dir():
        shutil.rmtree(tmp, ignore_errors=True)
        return ("unrunnable", None, f"cwd does not exist: {cwd_rel}")
    env = dict(os.environ)
    if shim:
        shimdir = tmp / "shim"
        shimdir.mkdir()
        make_shim(shimdir)
        env["PATH"] = str(shimdir).replace("\\", "/") + os.pathsep + env["PATH"]
    try:
        r = subprocess.run(
            [BASH, "-c", cmd],
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
        )
        out = (r.stdout + r.stderr).strip().replace("\n", " ")[:200]
        code = r.returncode
        if code == 9009 or code == 127 or any(s in out for s in CANNOT_RUN):
            return ("unrunnable", code, out)
        return (("does-not-discriminate" if code == 0 else "binds"), code, out)
    except subprocess.TimeoutExpired:
        return ("unrunnable", None, "timeout after 90s")
    except Exception as e:  # noqa: BLE001
        return ("unrunnable", None, str(e)[:150])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def selftest():
    """Refuse to report numbers from a runner nobody has shown to work.

    The first two attempts at this probe both produced a full table of
    confident nonsense — one because `python3` on this host is the Microsoft
    Store shim, one because `bash` on this host is WSL's. Both would have
    reported every criterion as `binds`.
    """
    checks = [
        ("exit 0 is seen as 0", "true", False, "does-not-discriminate"),
        ("exit 1 is seen as non-zero", "false", False, "binds"),
        ("the fixture is really there", "test -f run.py", False, "does-not-discriminate"),
        ("posix tools work", "grep -q CANCELLED jobs/status.py", False, "does-not-discriminate"),
        ("python3 absent unshimmed", "python3 --version", False, "unrunnable"),
        ("python3 works shimmed", "python3 --version", True, "does-not-discriminate"),
        ("the fixture suite is green", "python3 -m pytest -q tests/", True, "does-not-discriminate"),
    ]
    ok = True
    print("-- runner self-test --")
    for label, cmd, shim, want in checks:
        got, code, out = run(cmd, ".", shim)
        if got != want:
            ok = False
        print(
            f"  {'ok ' if got == want else 'BAD'} {label:<28} want={want:<21} "
            f"got={got:<21} exit={code} {out[:50]}"
        )
    print()
    return ok


def main():
    if not selftest():
        print("runner self-test FAILED — not reporting criterion numbers")
        return
    rows = json.loads((HERE / "criterion-results.json").read_text())
    print(f"host python: {REAL_PYTHON}")
    print(f"criteria to re-run: {len(rows)}")
    print()
    for r in rows:
        aw, aw_code, aw_out = run(r["command"], r.get("cwd", "."), shim=False)
        sh, sh_code, sh_out = run(r["command"], r.get("cwd", "."), shim=True)
        r["as_written"] = aw
        r["as_written_exit"] = aw_code
        r["shimmed"] = sh
        r["shimmed_exit"] = sh_code
        r["shimmed_output"] = sh_out
        print(
            f"{r['arm'][:1]}{r['run']}.{r['task']}  as-written={aw:<21} "
            f"shimmed={sh:<21} exit={str(sh_code):<5} {r['command'][:60]}"
        )
        if sh != "binds":
            print(f"        -> {sh_out[:130]}")

    (HERE / "criterion-results.json").write_text(json.dumps(rows, indent=2))

    print()
    print("-- tally --")
    for arm in sorted({r["arm"] for r in rows}):
        got = [r for r in rows if r["arm"] == arm]
        for pass_name in ("as_written", "shimmed"):
            b = sum(1 for r in got if r[pass_name] == "binds")
            z = sum(1 for r in got if r[pass_name] == "does-not-discriminate")
            u = sum(1 for r in got if r[pass_name] == "unrunnable")
            print(f"  {arm:<20} {pass_name:<11} n={len(got):<3} binds={b}  "
                  f"does-not-discriminate={z}  unrunnable={u}")
    print()
    print("-- of the criteria that could be run at all --")
    for arm in sorted({r["arm"] for r in rows}):
        got = [r for r in rows if r["arm"] == arm and r["shimmed"] != "unrunnable"]
        b = sum(1 for r in got if r["shimmed"] == "binds")
        print(f"  {arm:<20} binds {b}/{len(got)}")


if __name__ == "__main__":
    main()
