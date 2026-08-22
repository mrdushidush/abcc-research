"""Shared plumbing for W6 item 4 — the verification headroom ladder.

The question is what type checks, linters, generated tests, property tests and
sandboxed execution buy **over v1's syntax-error auto-retry**, so every
instrument here is scored the same way: does it separate a change the suite's own
verifier accepts from one it rejects, and what does it cost to run?

Two populations, both already in this repository:

  * **constructed** — for each K task, the unfixed fixture, the reference
    solution and the shipped sham. Ground truth by construction, re-measured.
  * **real** — every preserved agent workdir under `runs/`, with the verdict its
    run recorded. These are the actual mistakes a local model makes, not
    mistakes chosen to be interesting.

No scratchpad paths: everything is relative to this file. Workdirs are copied to
a fresh temp directory before an instrument touches them, because pytest and
cargo both write into the tree.
"""

import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
RUNS = REPO / "runs"
K_TASKS = REPO / "corpus/suites/k/tasks"
Q56_TASKS = REPO / "corpus/suites/q56/tasks"

REAL_PYTHON = shutil.which("python")
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

SKIP = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "target"}


# ── running things ───────────────────────────────────────────────────


def kill_tree(pid):
    """Kill a process AND its descendants.

    `subprocess.run(timeout=...)` kills the direct child only, and then blocks in
    `communicate()` until the pipes close — which a surviving grandchild holds
    open forever. That is F220's mechanism, and this probe hit it live: a Q56
    verifier's `pytest` running an agent solution that spins, orphaned by the
    timeout, held the pipe and stalled the whole run for 22 minutes. The fix is
    the one W3 item 7 specifies for 2.0 — kill the tree, not the process.
    """
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                       capture_output=True)
    else:                                            # pragma: no cover
        import signal
        os.killpg(os.getpgid(pid), signal.SIGKILL)


def run(cmd, cwd, timeout=180, env=None):
    """A subprocess with a wall-clock reading. Returns (code, output, ms).

    Timeout is a *classified* outcome, not an exception and not a zero: the
    return code is None and the output carries whatever was captured before the
    kill, which is item 2's `Uncertain(timeout)` rule applied to the probe itself.
    """
    t0 = time.time()
    p = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=True,
        errors="replace",
        env=env,
    )
    try:
        out, err = p.communicate(timeout=timeout)
        return p.returncode, (out or "") + (err or ""), int((time.time() - t0) * 1000)
    except subprocess.TimeoutExpired:
        kill_tree(p.pid)
        try:
            out, err = p.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            out, err = "", ""
        partial = ((out or "") + (err or ""))[-2000:]
        return None, "<timeout>\n" + partial, int((time.time() - t0) * 1000)


_SHIM = None


def shim_env():
    """PATH with a `python3` that exists on this host (the Store alias does not run)."""
    global _SHIM
    if _SHIM is None:
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="w6hr-shim-"))
        shim = tmp / "python3"
        shim.write_text(
            f'#!/usr/bin/env bash\nexec "{REAL_PYTHON}" "$@"\n', encoding="utf-8"
        )
        os.chmod(shim, 0o755)
        _SHIM = str(tmp).replace("\\", "/")
    env = dict(os.environ)
    env["PATH"] = _SHIM + os.pathsep + env["PATH"]
    return env


def bash(cmd, cwd, timeout=300):
    return run([BASH, "-c", cmd], cwd, timeout=timeout, env=shim_env())


def copy_tree(src, dest):
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns(*SKIP))
    return dest


class Work:
    """A disposable copy of a tree."""

    def __init__(self, src):
        self.src = pathlib.Path(src)
        self.tmp = None

    def __enter__(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="w6hr-"))
        return copy_tree(self.src, self.tmp / "work")

    def __exit__(self, *a):
        shutil.rmtree(self.tmp, ignore_errors=True)


# ── ground truth ─────────────────────────────────────────────────────


def verify(work, verify_sh, transcript="", timeout=300):
    """Run a suite verifier against a workdir. Returns (verdict, line, ms).

    The Q56 verifiers take the transcript as a required second argument
    (`${2:?transcript}`) and refuse to run without it; the K verifiers default it.
    """
    posix = str(verify_sh).replace("\\", "/")
    tpath = str(transcript).replace("\\", "/") if transcript else ""
    code, out, ms = bash(f'bash "{posix}" . "{tpath}"', work, timeout=timeout)
    line = next((l for l in out.splitlines() if l.startswith("RESULT:")), "")
    verdict = line.split()[1].strip("—") if line.startswith("RESULT:") else "UNKNOWN"
    return verdict, line.strip(), ms


# ── populations ──────────────────────────────────────────────────────


def k_task_ids():
    return sorted(p.name for p in K_TASKS.iterdir() if p.is_dir())


def constructed(task_id):
    """(artifact_id, materialiser) for the unfixed fixture, refsol and sham."""
    task = K_TASKS / task_id

    def make(overlay):
        def _m(dest):
            copy_tree(task / "fixture", dest)
            if overlay:
                for p in (task / overlay).rglob("*"):
                    if p.is_file():
                        rel = p.relative_to(task / overlay)
                        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(p, dest / rel)
            return dest

        return _m

    return [
        ("unfixed", make(None)),
        ("refsol", make("refsol")),
        ("sham", make("sham")),
    ]


def cells(suite=None):
    """Every recorded cell, with its workdir resolved and existence checked."""
    for jl in sorted(RUNS.glob("*/*/cells.jsonl")):
        for line in jl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            if suite and d.get("suite") != suite:
                continue
            wd = d.get("workdir", "")
            p = (REPO / wd.replace("../", "").replace("\\", "/")) if wd else None
            d["_wd"] = p if (p and p.is_dir()) else None
            d["_run"] = jl.parent.parent.name
            d["_id"] = f"{d['_run']}/{d['task']}__{d.get('variant', '-')}"
            # `_run` is not unique: every Q56 campaign run lives under runs/q56/,
            # so six run directories share the name and `_id` collides across
            # them. `_uid` adds the inner directory. (The K runs are one
            # directory each, so their `_id` is already unique and is left
            # alone — results-k.json and residue-results.json join on it.)
            d["_uid"] = f"{d['_run']}/{jl.parent.name}/{d['task']}__{d.get('variant', '-')}"
            yield d
