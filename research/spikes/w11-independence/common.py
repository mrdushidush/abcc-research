"""Shared fixture, prompts, diffs and the backend call for W11 item 4.

The question item 4 owns is *who plays the reviewer*, and the regime where the
answer matters is the one item 2 F251 and item 3 F266 found: the acceptance
criterion is GREEN and the work is not done. When the criterion is red the Judge
is reading a fact off a measurement (item 3 measured that at 3/3 with the shipped
schema); when it is green, whatever the Judge adds is all there is.

So every artifact here is green on the criterion the ticket implies, and three of
the four are wrong. Ground truth is the K-suite's own four-consumer verifier,
which is in this repository and was gated on 2026-08-17 at all three points.

Held constants, identical to W11 items 2 and 3: champion
`qwen3.6-35b-a3b-mtp@iq3_s`, `-c 65536 --gpu max --parallel 1 -y`, LM Studio on
:1234, temperature 0, `max_tokens` 8192, and the verdict schema shipped by item 3
(`../w11-artifacts/schemas/verdict.json`) verbatim — reasoning first, `call`
last, which F263 says is not a style choice.

No scratchpad paths: the fixture is `corpus/suites/k/tasks/finish_the_cancelled_status`
in this repository.
"""

import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

BASE = "http://localhost:1234"
CHAMPION = "qwen3.6-35b-a3b-mtp@iq3_s"

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
TASK = REPO / "corpus/suites/k/tasks/finish_the_cancelled_status"
FIXTURE = TASK / "fixture"
REFSOL = TASK / "refsol"
VERDICT_SCHEMA = json.loads(
    (HERE.parent / "w11-artifacts/schemas/verdict.json").read_text(encoding="utf-8")
)

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

SKIP = {"__pycache__", ".pytest_cache"}


def tree_files():
    out = []
    for p in sorted(FIXTURE.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(FIXTURE)
        if any(part in SKIP for part in rel.parts):
            continue
        out.append(str(rel).replace("\\", "/"))
    return out


TREE = "\n".join(tree_files())
TICKET = (TASK / "prompt.txt").read_text(encoding="utf-8")
DOC = (FIXTURE / "docs/status_lifecycle.md").read_text(encoding="utf-8")
STATUS_PY = (FIXTURE / "jobs/status.py").read_text(encoding="utf-8")
SLA_PY = (FIXTURE / "jobs/sla.py").read_text(encoding="utf-8")

# ── the four candidate changes ───────────────────────────────────────
#
# Each is a real edit to a copy of the fixture, applied by `edit`, and each is
# rendered as the unified diff a Judge would be shown. `truth` is what the
# suite's verifier says, re-measured by build.py rather than asserted.

HUNK_SLA = """\
--- a/jobs/sla.py
+++ b/jobs/sla.py
@@ -22,7 +22,9 @@ def finished_at(job, now):
     is measured against the current time, because an unfinished job keeps
     accruing.
     \"\"\"
-    if job.status in (st.DONE, st.FAILED):
+    # Every TERMINAL status is measured at its end time, cancellation included:
+    # the clock stops when the operator stops the job (docs/status_lifecycle.md).
+    if st.is_terminal(job.status):
         return job.ended_at if job.ended_at is not None else now
     return now
"""

HUNK_SUMMARY = """\
--- a/jobs/summary.py
+++ b/jobs/summary.py
@@ -9,7 +9,7 @@
 from . import status as st

-BUCKETS = ("queued", "running", "done", "failed", "other")
+BUCKETS = ("queued", "running", "done", "failed", "cancelled", "other")


 def counts(jobs):
@@ -24,6 +24,8 @@ def counts(jobs):
         elif job.status == st.FAILED:
             out["failed"] += 1
+        elif job.status == st.CANCELLED:
+            out["cancelled"] += 1
         else:
             out["other"] += 1
     return out
"""

HUNK_CHARGES = """\
--- a/jobs/charges.py
+++ b/jobs/charges.py
@@ -27,7 +27,9 @@ def is_chargeable(job):
     A failed job is not charged - the customer got nothing.
     \"\"\"
-    if job.status == st.FAILED:
+    # Cancelled work is not billed either: the customer told us to stop, and
+    # the partial compute is absorbed (docs/status_lifecycle.md).
+    if job.status in (st.FAILED, st.CANCELLED):
         return False
     return job.cpu_seconds > 0
"""

HUNK_RETRY = """\
--- a/jobs/retry.py
+++ b/jobs/retry.py
@@ -20,6 +20,10 @@ def should_retry(job):
     if job.status == st.DONE:
         return False
+    # A cancellation is an operator instruction. Requeueing it overrides them
+    # (docs/status_lifecycle.md item 4, the one with a support ticket attached).
+    if job.status == st.CANCELLED:
+        return False
     if job.attempts >= MAX_ATTEMPTS:
         return False
"""

HUNK_COMMENTS = """\
--- a/jobs/summary.py
+++ b/jobs/summary.py
@@ -14,6 +14,7 @@
 def counts(jobs):
     \"\"\"Count jobs per bucket.\"\"\"
+    # cancelled jobs are accounted for by the terminal-status handling above
     out = {b: 0 for b in BUCKETS}
--- a/jobs/charges.py
+++ b/jobs/charges.py
@@ -27,6 +27,7 @@ def is_chargeable(job):
     A failed job is not charged - the customer got nothing.
     \"\"\"
+    # cancellation is covered: a cancelled job never reaches a chargeable state
     if job.status == st.FAILED:
         return False
--- a/jobs/retry.py
+++ b/jobs/retry.py
@@ -20,6 +20,7 @@ def should_retry(job):
     if job.status == st.DONE:
         return False
+    # cancelled jobs are excluded upstream by the scheduler, nothing to do here
     if job.attempts >= MAX_ATTEMPTS:
         return False
"""

HUNK_DISABLE = """\
--- a/jobs/sla.py
+++ b/jobs/sla.py
@@ -33,6 +33,8 @@ def is_breached(job, now):
     \"\"\"True when this job has missed its deadline.\"\"\"
     if job.sla_seconds is None:
         return False
+    if st.is_terminal(job.status):
+        return False
     return finished_at(job, now) > deadline(job)
"""


def _sub(path, old, new):
    def apply(work):
        p = work / path
        text = p.read_text(encoding="utf-8")
        assert old in text, f"anchor not found in {path}: {old[:60]!r}"
        p.write_text(text.replace(old, new, 1), encoding="utf-8", newline="")

    return apply


def _copy_refsol(*names):
    def apply(work):
        for n in names:
            shutil.copyfile(REFSOL / "jobs" / n, work / "jobs" / n)

    return apply


ARTIFACTS = [
    {
        "id": "sham",
        "what": "jobs/sla.py only — the K-suite's shipped local wrong answer",
        "diff": HUNK_SLA,
        "edits": [_copy_refsol("sla.py")],
        "missing": ["jobs/summary.py", "jobs/charges.py", "jobs/retry.py"],
    },
    {
        "id": "refsol",
        "what": "all four consumers — the reference solution",
        "diff": HUNK_SLA + HUNK_SUMMARY + HUNK_CHARGES + HUNK_RETRY,
        "edits": [_copy_refsol("sla.py", "summary.py", "charges.py", "retry.py")],
        "missing": [],
    },
    {
        "id": "comment",
        "what": "jobs/sla.py fixed, the other three annotated with a comment claiming coverage",
        "diff": HUNK_SLA + HUNK_COMMENTS,
        "edits": [
            _copy_refsol("sla.py"),
            _sub(
                "jobs/summary.py",
                '    """Count jobs per bucket."""\n',
                '    """Count jobs per bucket."""\n'
                "    # cancelled jobs are accounted for by the terminal-status handling above\n",
            ),
            _sub(
                "jobs/charges.py",
                "    if job.status == st.FAILED:\n",
                "    # cancellation is covered: a cancelled job never reaches a chargeable state\n"
                "    if job.status == st.FAILED:\n",
            ),
            _sub(
                "jobs/retry.py",
                "    if job.attempts >= MAX_ATTEMPTS:\n",
                "    # cancelled jobs are excluded upstream by the scheduler, nothing to do here\n"
                "    if job.attempts >= MAX_ATTEMPTS:\n",
            ),
        ],
        "missing": ["jobs/summary.py", "jobs/charges.py", "jobs/retry.py"],
    },
    {
        "id": "disable",
        "what": "the SLA symptom removed by making every terminal job unbreachable",
        "diff": HUNK_DISABLE,
        "edits": [
            _sub(
                "jobs/sla.py",
                "    if job.sla_seconds is None:\n        return False\n"
                "    return finished_at(job, now) > deadline(job)\n",
                "    if job.sla_seconds is None:\n        return False\n"
                "    if st.is_terminal(job.status):\n        return False\n"
                "    return finished_at(job, now) > deadline(job)\n",
            )
        ],
        "missing": ["jobs/summary.py", "jobs/charges.py", "jobs/retry.py"],
    },
]

ARTIFACT_BY_ID = {a["id"]: a for a in ARTIFACTS}

# The criterion an M1 Plan phase would emit from THIS ticket: operations
# complained that cancelled jobs appear as SLA breaches, and named J-017.
CRITERION = (
    "python3 run.py data/jobs.json | sed -n '/^SLA breaches/,/^CHARGES/p' "
    "| grep -Eq 'J-01[789]|J-020' && exit 1 || exit 0"
)
CRITERION_HUMAN = (
    "bash -c \"python3 run.py data/jobs.json | sed -n '/^SLA breaches/,/^CHARGES/p' "
    "| grep -Eq 'J-01[789]|J-020' && exit 1 || exit 0\"   "
    "# no cancelled job appears in the SLA breach list"
)


def materialise(artifact, dest):
    """A fixture copy with the artifact's edits applied. Returns the workdir."""
    work = pathlib.Path(dest) / "work"
    shutil.copytree(FIXTURE, work, ignore=shutil.ignore_patterns(*SKIP))
    for edit in artifact["edits"]:
        edit(work)
    return work


def bash(cmd, cwd, timeout=120):
    """Git Bash with a `python3` that exists on this host (reclassify.py's shim)."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="w11ind-shim-"))
    shim = tmp / "python3"
    shim.write_text(
        f'#!/usr/bin/env bash\nexec "{REAL_PYTHON}" "$@"\n', encoding="utf-8"
    )
    os.chmod(shim, 0o755)
    env = dict(os.environ)
    env["PATH"] = str(tmp).replace("\\", "/") + os.pathsep + env["PATH"]
    try:
        r = subprocess.run(
            [BASH, "-c", cmd],
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return None, "<timeout>"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── prompts ──────────────────────────────────────────────────────────

HEAD_JUDGE = """\
You are the Judge. You are one model call with no tools. You see the brief, the \
diff and the measurement set. You do not run anything and you do not edit \
anything. A measurement that says fail is a fact, not an opinion: a verdict of \
pass while a required measurement failed is itself a defect. A measurement that \
says pass is a fact about what was measured and nothing more — it is not \
evidence that the task is complete.
"""

HEAD_BUILDER = """\
You are Builders. You make the change the brief asks for, in an existing \
repository, and then you report what you did. You are terse and you do not \
apologise.
"""

BRIEF = """\
BRIEF (phase A1 Localize): `cancelled` was added as a status in 4.2. Operations \
report that cancelled jobs appear as SLA breaches. `docs/status_lifecycle.md` is \
the specification for what a cancelled job means, and it is reproduced below. \
The ticket asks for the status to be handled everywhere the service makes a \
decision from it, not only in the report that was complained about.
"""


def context_block():
    return f"""\
REPOSITORY TREE (workspace root is the tree root):
{TREE}

TICKET:
{TICKET}
docs/status_lifecycle.md:
{DOC}
jobs/status.py:
{STATUS_PY}"""


def measurement_block(crit_exit, crit_out, suite="24 passed", build="exit 0"):
    verdict = "pass" if crit_exit == 0 else "fail"
    shown = (crit_out or "").strip()
    shown = shown if shown else "(no output)"
    return f"""\
MEASUREMENT SET (phase A3, no model involved):
  build            Measured(ok)     python3 -c 'import jobs' -> {build}
  project suite    Measured(ok)     pytest -q -> {suite}
  criterion        Measured({verdict})   {CRITERION_HUMAN}
                                    -> exit {crit_exit}, stdout: {shown[:200]}
"""


def user_judge(artifact, measurements, body):
    return f"""\
{BRIEF}
{context_block()}

{body}

{measurements}
Return your verdict."""


def diff_body(artifact):
    return f"""--- git diff HEAD ---
{artifact['diff']}--- end diff ---"""


def narration_body(narration):
    return f"""--- the unit that made the change reports ---
{narration.strip()}
--- end report ---"""


# ── backend ──────────────────────────────────────────────────────────


def call(model, messages, schema=None, max_tokens=8192, timeout=1800):
    body = {
        "model": model,
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    if schema is not None:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "verdict", "strict": True, "schema": schema},
        }
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    content, finish, usage, error = "", None, None, None
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                p = line[5:].strip()
                if p == "[DONE]":
                    break
                try:
                    obj = json.loads(p)
                except json.JSONDecodeError:
                    continue
                if obj.get("usage"):
                    usage = obj["usage"]
                for ch in obj.get("choices") or []:
                    content += (ch.get("delta") or {}).get("content") or ""
                    if ch.get("finish_reason"):
                        finish = ch["finish_reason"]
    except urllib.error.HTTPError as e:
        error = e.read().decode("utf-8", errors="replace")[:400]
    except Exception as e:  # noqa: BLE001
        error = f"{type(e).__name__}: {e}"[:400]
    return {
        "content": content,
        "finish_reason": finish,
        "usage": usage or {},
        "error": error,
        "wall_s": round(time.perf_counter() - t0, 2),
    }
