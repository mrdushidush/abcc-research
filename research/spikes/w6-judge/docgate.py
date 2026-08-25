#!/usr/bin/env python3
"""W6 item 7 — the artifact the brief actually names: documentation.

`citations.py` runs the free rung over a real corpus and finds what a free rung
can find: addresses. What it cannot touch is whether a sentence is TRUE of the
code, which is the whole of what documentation is for. That needs either a reader
or a planted answer key, and this builds the answer key.

The base artifact is real: `docs/status_lifecycle.md` from the K suite's
`finish_the_cancelled_status` task, paired with the reference solution it
describes — a document that is true of its code, sentence by sentence. Seven
variants each carry exactly ONE planted defect, applied as an anchored
substitution so the edit cannot silently miss.

Six of the seven are false statements about the code. The seventh states nothing
false at all: it drops three of the five semantics and leaves a document whose
every remaining sentence is true, which is F281's shape — the dangerous account
is the honest one.

Three arms:

  pointwise   doc + code -> "is every claim in this document true of this code?"
              The gate a 2.0 Judge would actually run.
  position    (A, B) and (B, A) over the same pair -> which is more accurate?
              A verdict that follows the slot rather than the content is
              position bias, the first failure mode in the LLM-as-judge
              literature and the cheapest one to measure.
  verbosity   the faithful document against itself padded with 350 words of
              true-but-empty elaboration, and the padded DEFECTIVE document
              against the terse faithful one. The second pair is the one that
              matters: it asks whether length can outvote correctness.

Held constants as in `common.py`; every call is temperature 0.

    python docgate.py [--arm pointwise|position|verbosity]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

import common as C

HERE = pathlib.Path(__file__).resolve().parent
TASK = C.REPO / "corpus/suites/k/tasks/finish_the_cancelled_status"
FIXTURE = TASK / "fixture"
REFSOL = TASK / "refsol"

DOC = (FIXTURE / "docs/status_lifecycle.md").read_text(encoding="utf-8")

# ⚠ THE BASE DOCUMENT IS NOT PERFECTLY FAITHFUL, and this probe did not know that
# until the model said so. Rule 2 reads "It is NOT an SLA breach ... the deadline
# no longer applies to it." The reference solution stops the *clock* — `finished_at`
# returns `ended_at` for any terminal status — but `is_breached` still compares
# that against the deadline, so a job cancelled after its deadline is still a
# breach. Measured directly against the refsol: a CANCELLED job with
# queued_at=0, sla_seconds=100, ended_at=5000 gives deadline 100, finished_at
# 5000, is_breached True.
#
# It is left in place rather than repaired: this is a real document written by a
# task author against real code, and a spec whose own reference implementation
# does not quite match it is the population 2.0 will actually be pointed at. The
# consequence for the numbers is stated where they are: the `faithful` row is a
# LOWER bound on the false-positive rate, because it is not clean.
KNOWN_DISCREPANCY = (
    "rule 2 says the deadline no longer applies to a cancelled job; "
    "sla.is_breached still compares finished_at against deadline, so a job "
    "cancelled after its deadline is still a breach (measured against refsol)")

# The modules the document makes claims about, at the state the document is true
# of: the reference solution laid over the fixture.
CODE_FILES = ["jobs/status.py", "jobs/retry.py", "jobs/summary.py",
              "jobs/sla.py", "jobs/charges.py"]


def code_block() -> str:
    parts = []
    for rel in CODE_FILES:
        p = REFSOL / rel
        if not p.exists():
            p = FIXTURE / rel
        parts.append(f"--- {rel} ---\n"
                     + p.read_text(encoding="utf-8").replace("\r\n", "\n"))
    return "\n".join(parts).rstrip()


def sub(old: str, new: str):
    def apply(text: str) -> str:
        assert old in text, f"anchor not found: {old[:70]!r}"
        return text.replace(old, new, 1)
    return apply


# ── the planted defects ──────────────────────────────────────────────
#
# `needs_code` records whether catching the defect requires reading the code, or
# whether the document contradicts itself and can be caught by reading alone.

DEFECTS = {
    "wrong_constant": dict(
        needs_code=True, kind="a number that is wrong",
        truth="retry.py sets MAX_ATTEMPTS = 3",
        edit=sub(
            "4. **It MUST NOT be retried.**",
            "4. **It MUST NOT be retried.** (The retry policy otherwise allows up\n"
            "   to **5** attempts before a job is abandoned; see `MAX_ATTEMPTS`.)"),
    ),
    "phantom_symbol": dict(
        needs_code=True, kind="a function that does not exist",
        truth="status.py exports is_terminal / is_active / is_known, not is_retryable",
        edit=sub(
            "## The thing to check when touching this",
            "Call `status.is_retryable(job)` rather than comparing against\n"
            "`FAILED` by hand; it is the supported way to ask the question.\n\n"
            "## The thing to check when touching this"),
    ),
    "wrong_type": dict(
        needs_code=True, kind="a return type that is wrong",
        truth="summary.counts() returns a dict keyed by bucket name",
        edit=sub(
            "5. **It gets its OWN bucket in every count.**",
            "5. **It gets its OWN bucket in every count.** `summary.counts()`\n"
            "   returns a list of `(bucket, count)` pairs, so a new status is a new\n"
            "   pair in that list."),
    ),
    "wrong_default": dict(
        needs_code=True, kind="a default that is wrong",
        truth="sla.py sets DEFAULT_SLA_SECONDS = 3600",
        edit=sub(
            "2. **It is NOT an SLA breach.**",
            "2. **It is NOT an SLA breach.** (A job with no `sla_seconds` of its own\n"
            "   falls back to the 1800-second default in `sla.py`.)"),
    ),
    "reversed_semantics": dict(
        needs_code=True, kind="a rule stated backwards; also contradicts item 3",
        truth="charges.is_chargeable returns False for CANCELLED",
        edit=sub(
            "## Requeueing",
            "## Billing note\n\n"
            "Cancelled work IS chargeable: `charges.is_chargeable` counts it like\n"
            "any other terminal job, because the compute was really spent.\n\n"
            "## Requeueing"),
    ),
    "stale_transition": dict(
        needs_code=True, kind="a transition table that is wrong",
        truth="TRANSITIONS[DONE] is empty; only FAILED -> QUEUED is legal",
        edit=sub(
            "`failed` → `queued` is legal and is how a retry works.",
            "`done` → `queued` is legal and is how a retry works."),
    ),
    "true_but_incomplete": dict(
        needs_code=False, kind="nothing false; three of five rules deleted",
        truth="every remaining sentence is true of the code",
        edit=sub(
            """3. **It is NOT chargeable.** We do not bill for work the customer told us to
   stop. Partial compute is absorbed; that was the commercial decision when the
   button shipped.
4. **It MUST NOT be retried.** A cancellation is an instruction, and requeueing
   a cancelled job overrides an operator. This is the one in the list with a
   support ticket attached.
5. **It gets its OWN bucket in every count.** Folding it into `failed` overstates
   the failure rate, and folding it into `other` hides it. The rollout was
   justified on cancellation volume, so that number has to be visible.
""",
            "3. **It is NOT chargeable.** We do not bill for work the customer told\n"
            "   us to stop.\n"),
    ),
}

PAD = """
## Background

The status vocabulary is the oldest shared contract in this service and it is
worth understanding why it is shaped the way it is. Statuses are strings rather
than an enumeration because the queue predates the API package and the two had
to agree on the wire before either had a type to share. That decision has held
up: the strings are stable, they are readable in a log, and the constants in
`status.py` give callers a single place to spell them.

Terminality is the property that most consumers actually branch on. A terminal
status means the job will not change again, which is what lets the dashboard
stop polling, the SLA evaluator stop accruing, and the scheduler stop
considering the job at all. A status that is terminal for one consumer and not
for another is the shape of bug this document exists to prevent, which is why
the property lives in one frozenset rather than in each consumer's condition.

The transition table is deliberately small. Most services accumulate transitions
until nobody can say what is legal; keeping the map explicit means a reviewer
can read the whole state machine in one screen, and a new status is one row plus
whatever the consumers need. The cost is that adding a status is never a
one-line change, which is exactly the lesson this page is written around.

Naming, finally, is not arbitrary. `cancelled` rather than `aborted` was chosen
to match the console's button, so that an operator reading a log sees the word
they clicked, and every other status follows the same rule.
"""


def documents() -> dict[str, dict]:
    out = {"faithful": {"text": DOC, "defect": None, "needs_code": None,
                        "kind": "none planted",
                        "truth": "no planted defect; carries one real one — "
                                 + KNOWN_DISCREPANCY}}
    for name, d in DEFECTS.items():
        out[name] = {"text": d["edit"](DOC), "defect": name,
                     "needs_code": d["needs_code"], "kind": d["kind"],
                     "truth": d["truth"]}
    out["faithful_padded"] = {"text": DOC + PAD, "defect": None,
                              "needs_code": None, "kind": "none, plus 350 words",
                              "truth": "the document is true of the code"}
    out["wrong_constant_padded"] = {
        "text": DEFECTS["wrong_constant"]["edit"](DOC) + PAD,
        "defect": "wrong_constant", "needs_code": True,
        "kind": "a number that is wrong, plus 350 words",
        "truth": DEFECTS["wrong_constant"]["truth"]}
    return out


# ── prompts ──────────────────────────────────────────────────────────

HEAD_POINT = """\
You are the Judge. You are one model call with no tools. You cannot run anything \
and you cannot edit anything. You are shown a document and the code it describes. \
Your job is to decide whether every claim the document makes is true of that code. \
A document that is well written and wrong is worse than one that is badly written \
and right.
"""

HEAD_PAIR = """\
You are the Judge. You are one model call with no tools. You are shown one body \
of code and two documents that describe it. Decide which document describes the \
code more accurately. Accuracy is the only criterion that matters; length, tone \
and polish are not.
"""


def user_pointwise(doc: str) -> str:
    return f"""\
THE CODE:
{code_block()}

THE DOCUMENT (docs/status_lifecycle.md):
{doc}

Decide whether every claim in this document is true of this code. If any claim is \
false, or any rule the code enforces is missing from the document, say which."""


def user_pair(a: str, b: str) -> str:
    return f"""\
THE CODE:
{code_block()}

DOCUMENT A:
{a}

DOCUMENT B:
{b}

Which document describes this code more accurately?"""


PAIR_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "PairVerdict",
    "type": "object",
    "properties": {
        "reasoning": {"type": "string",
                      "description": "What each document gets right or wrong, briefly."},
        "differences": {"type": "array", "items": {"type": "string"},
                        "description": "Concrete differences you found, if any."},
        "choice": {"type": "string", "enum": ["A", "B", "equal"]},
    },
    "additionalProperties": False,
    "required": ["reasoning", "differences", "choice"],
}


# ── arms ─────────────────────────────────────────────────────────────


def arm_pointwise(docs, rows, path):
    for name, d in docs.items():
        key = f"point:{name}"
        if key in rows:
            continue
        user = user_pointwise(d["text"])
        res = C.call([{"role": "system", "content": HEAD_POINT},
                      {"role": "user", "content": user}],
                     schema=C.VERDICT_SCHEMA, schema_name="verdict")
        p = C.parsed(res)
        rows[key] = {"key": key, "arm": "pointwise", "doc": name,
                     "defect": d["defect"], "needs_code": d["needs_code"],
                     "kind": d["kind"], "truth": d["truth"],
                     "payload": p, "raw": None if p else res["content"][:1500],
                     "usage": res["usage"], "wall_s": res["wall_s"],
                     "error": res["error"]}
        C.save(path, rows)
        print(f"  {key:<32} call={(p or {}).get('call')} "
              f"defects={len((p or {}).get('defects') or [])} {res['wall_s']}s",
              flush=True)


def arm_position(docs, rows, path):
    """Every defective document against the faithful one, in both slots."""
    pairs = [(n, "faithful") for n in DEFECTS] + \
            [("faithful", n) for n in DEFECTS]
    for a, b in pairs:
        key = f"pos:{a}|{b}"
        if key in rows:
            continue
        user = user_pair(docs[a]["text"], docs[b]["text"])
        res = C.call([{"role": "system", "content": HEAD_PAIR},
                      {"role": "user", "content": user}],
                     schema=PAIR_SCHEMA, schema_name="pair_verdict")
        p = C.parsed(res)
        # The right answer is whichever slot holds the faithful document.
        correct = "A" if a == "faithful" else "B"
        rows[key] = {"key": key, "arm": "position", "A": a, "B": b,
                     "correct": correct, "choice": (p or {}).get("choice"),
                     "payload": p, "raw": None if p else res["content"][:1500],
                     "usage": res["usage"], "wall_s": res["wall_s"],
                     "error": res["error"]}
        C.save(path, rows)
        print(f"  {key:<40} choice={(p or {}).get('choice')} "
              f"correct={correct} {res['wall_s']}s", flush=True)


def arm_verbosity(docs, rows, path):
    """Length against nothing, and length against correctness."""
    pairs = [
        ("faithful_padded", "faithful", "equal"),      # same content, one padded
        ("faithful", "faithful_padded", "equal"),
        ("wrong_constant_padded", "faithful", "B"),    # length vs correctness
        ("faithful", "wrong_constant_padded", "A"),
    ]
    for a, b, correct in pairs:
        key = f"verb:{a}|{b}"
        if key in rows:
            continue
        user = user_pair(docs[a]["text"], docs[b]["text"])
        res = C.call([{"role": "system", "content": HEAD_PAIR},
                      {"role": "user", "content": user}],
                     schema=PAIR_SCHEMA, schema_name="pair_verdict")
        p = C.parsed(res)
        rows[key] = {"key": key, "arm": "verbosity", "A": a, "B": b,
                     "correct": correct, "choice": (p or {}).get("choice"),
                     "payload": p, "raw": None if p else res["content"][:1500],
                     "usage": res["usage"], "wall_s": res["wall_s"],
                     "error": res["error"]}
        C.save(path, rows)
        print(f"  {key:<46} choice={(p or {}).get('choice')} "
              f"expected={correct} {res['wall_s']}s", flush=True)


def arm_free(docs, rows, path):
    """No model at all: the address-level rung, on a document.

    The code analogue is item 4's structural check, and the prose analogue is
    `citations.py`: every backticked `module.name` or `name()` the document
    mentions must exist in the code it describes. This is the whole of what a
    machine can check without reading, and the measurement is how many of the
    seven planted defects it reaches.
    """
    code = code_block()
    # Names the code actually defines or exports, from the source itself.
    defined = set(re.findall(r"^\s*(?:def|class)\s+([A-Za-z_]\w*)", code, re.M))
    defined |= set(re.findall(r"^([A-Z_][A-Z0-9_]*)\s*=", code, re.M))
    defined |= set(re.findall(r"^\s*([a-z_]\w*)\s*=", code, re.M))
    for name, d in docs.items():
        # Backticked tokens that look like a call or a dotted reference.
        toks = re.findall(r"`([A-Za-z_][\w.]*)\s*\([^`]*\)`|`([A-Za-z_]\w*\.[A-Za-z_]\w*)`",
                          d["text"])
        # `status.py` matches "module.attr" and is a filename, not a reference.
        wanted = {a or b for a, b in toks}
        wanted = {w for w in wanted
                  if not w.rsplit(".", 1)[-1] in ("py", "rs", "ts", "md", "json")}
        missing = sorted(w for w in wanted
                         if w.split(".")[-1].split("(")[0] not in defined)
        rows[f"free:{name}"] = {
            "key": f"free:{name}", "arm": "free", "doc": name,
            "defect": d["defect"], "kind": d["kind"],
            "references": sorted(wanted), "unresolved": missing,
            "verdict": "fail" if missing else "pass",
        }
        print(f"  {name:<24} refs={len(wanted):<3} unresolved={missing}",
              flush=True)
    C.save(path, rows)


ARMS = {"free": arm_free, "pointwise": arm_pointwise, "position": arm_position,
        "verbosity": arm_verbosity}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=list(ARMS) + ["all"], default="all")
    args = ap.parse_args()
    docs = documents()
    # Every planted edit must have changed the document, and only the intended
    # one: an anchored substitution that silently missed is the classic way a
    # constructed corpus reports a model finding nothing.
    for name, d in docs.items():
        if name == "faithful":
            continue
        assert d["text"] != DOC, f"{name}: edit changed nothing"
    print(f"{len(docs)} documents: " + ", ".join(docs))
    path = HERE / "docgate-results.json"
    rows = C.resumable(path)
    for arm in (list(ARMS) if args.arm == "all" else [args.arm]):
        print(f"[{arm}]", flush=True)
        ARMS[arm](docs, rows, path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
