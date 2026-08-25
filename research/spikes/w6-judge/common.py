"""W6 item 7 — verifying what has no test to run.

The brief asks about documentation and review output, "where there is no test to
run", and about LLM-as-judge reliability. The trap in that phrasing is that a
population with no test also has no ground truth, so any reliability number
measured on it is an opinion about an opinion.

This spike takes the one population in the repository that is the unrunnable case
*with an answer key*: the **29 real agent failures on the Q56 `control` and
`gated` arms**. F321 and F322 established what makes them special — on those 280
cells not one deterministic rung in five languages went red on a single one of
the 29, the free structural check found 0 untouched trees, and the fixture's own
visible tests are green on every one of them. Q56's design is the reason
(`Q03/task.toml`, caveat 3): *"The fixture ships only happy-path visible tests on
purpose: a PASS is possible only if the subject handled an edge the prompt
implies but does not state."*

So at the moment the agent stopped, there was no test it could have run that
would have told it the truth. That is the unrunnable case exactly, and the hidden
reviewer tests are an answer key nobody in the loop can see.

Ground truth is `../w6-headroom/results-q56.json`, whose `truth` field is the
suite verifier re-run rather than the verdict a campaign recorded.

Held constants: champion `qwen3.6-35b-a3b-mtp@iq3_s`, `-c 65536 --gpu max
--parallel 1 -y`, LM Studio on :1234, temperature 0, `max_tokens` 8192; the
server's own command line records `--cache-type-k/v q8_0 --flash-attn on
--kv-unified --batch-size 2048 --spec-type draft-mtp` (recorded per run by
`held.py`).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
HEADROOM = HERE.parent / "w6-headroom"


def _load(name, path):
    """Import a module under an explicit name.

    Item 4's plumbing is also called `common.py`, and a plain `sys.path` insert
    makes `import common` resolve to whichever one is already in `sys.modules` —
    here, this file. Naming it is the whole fix.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


HC = _load("w6hr_common", HEADROOM / "common.py")

BASE = "http://localhost:1234"
CHAMPION = "qwen3.6-35b-a3b-mtp@iq3_s"

Q56 = HC.Q56_TASKS
RESULTS_Q56 = json.loads((HEADROOM / "results-q56.json").read_text(encoding="utf-8"))

SKIP_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
              "target", "node_modules", ".git", "dist", "build"}
SOURCE_SUFFIXES = {".py", ".rs", ".mjs", ".js", ".ts", ".sh", ".bash", ".toml",
                   ".json", ".md", ".txt"}


# ── the population ───────────────────────────────────────────────────


def _rel_text(root: pathlib.Path) -> dict[str, str]:
    """Every readable file under `root`, CRLF-normalised, keyed by posix path."""
    out = {}
    for p in sorted(pathlib.Path(root).rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in SKIP_PARTS for part in rel.parts):
            continue
        if p.suffix and p.suffix not in SOURCE_SUFFIXES:
            continue
        try:
            out[rel.as_posix()] = p.read_text(encoding="utf-8",
                                              errors="replace").replace("\r\n", "\n")
        except OSError:
            continue
    return out


_WD = None


def workdirs() -> dict[str, pathlib.Path]:
    """`_uid` -> preserved workdir, for every recorded Q56 cell."""
    global _WD
    if _WD is None:
        _WD = {d["_uid"]: d["_wd"] for d in HC.cells(suite="q56")}
    return _WD


def cells(verdict=None, arms=("control", "gated")):
    """Q56 result rows, filtered to the arms where the agent was left alone."""
    for r in RESULTS_Q56:
        if r["variant"] not in arms:
            continue
        if verdict and r["truth"]["verdict"] != verdict:
            continue
        yield r


def artifact(row: dict) -> dict | None:
    """What the agent left, with the verifier's own residue removed.

    The residue is the hidden reviewer tests the verifier writes into the tree at
    grade time (`results-q56.json`'s `residue`, measured in item 4 by diffing a
    pristine fixture across a verify run). Showing them to a judge is showing it
    the answer key, which is how a post-hoc harness accidentally reports a
    perfect reviewer.
    """
    wd = workdirs().get(row["id"])
    if wd is None:
        return None
    task = row["task"]
    fixture = _rel_text(Q56 / task / "fixture")
    work = _rel_text(wd)
    for r in row.get("residue") or []:
        work.pop(r, None)
    changed = sorted(k for k, v in work.items() if fixture.get(k) != v)
    added = sorted(k for k in work if k not in fixture)
    deleted = sorted(k for k in fixture if k not in work)
    body = json.dumps({k: work[k] for k in sorted(work)}, sort_keys=True)
    return {
        "uid": row["id"],
        "task": task,
        "lang": row["lang"],
        "variant": row["variant"],
        "truth": row["truth"]["verdict"],
        "truth_line": row["truth"]["line"],
        "files": work,
        "fixture": fixture,
        "changed": changed,
        "added": added,
        "deleted": deleted,
        "content_sha": hashlib.sha256(body.encode()).hexdigest()[:16],
    }


def ticket(task: str) -> str:
    return (Q56 / task / "prompt.txt").read_text(encoding="utf-8").strip()


def refsol(task: str) -> dict[str, str]:
    d = Q56 / task / "refsol"
    return _rel_text(d) if d.is_dir() else {}


def hidden_tests(task: str) -> str:
    """The verifier's heredoc body — the answer key. Never shown to a model."""
    return (Q56 / task / "verify.sh").read_text(encoding="utf-8", errors="replace")


def population():
    """The 29 clean-arm failures and the 36 clean-arm passes on the same tasks.

    Deduplicated by the *content* of the tree the agent left: repeated campaign
    runs at temperature 0 produce byte-identical answers, and paying for the same
    forward pass five times measures nothing. `n_cells` records the multiplicity
    so a rate can still be quoted per cell.
    """
    fails = [a for a in (artifact(r) for r in cells(verdict="FAIL")) if a]
    tasks = sorted({a["task"] for a in fails})
    passes = [a for a in (artifact(r) for r in cells(verdict="PASS"))
              if a and a["task"] in tasks]
    out = []
    seen: dict[tuple, dict] = {}
    for a in fails + passes:
        key = (a["task"], a["content_sha"])
        if key in seen:
            seen[key]["n_cells"] += 1
            seen[key]["uids"].append(a["uid"])
            continue
        a["n_cells"] = 1
        a["uids"] = [a["uid"]]
        seen[key] = a
        out.append(a)
    return out


# ── what the judge is shown ──────────────────────────────────────────


def source_block(a: dict) -> str:
    """The tree the agent left, as files. These tasks are one to three files."""
    parts = []
    for path in sorted(a["files"]):
        if path.endswith((".json", ".lock")) or path == "Cargo.lock":
            continue
        parts.append(f"--- {path} ---\n{a['files'][path]}")
    return "\n".join(parts).rstrip()


def visible_tests(a: dict) -> str:
    """What the agent could actually run, and what it said. Always green here."""
    return ("The project's own test suite is GREEN: every test the repository "
            "ships passes against this tree. There are no other tests.")


HEAD_JUDGE = """\
You are the Judge. You are one model call with no tools. You cannot run anything \
and you cannot edit anything. You are shown a ticket and the final state of the \
files a coding agent left behind. The project's own tests already pass — that is \
a fact about what was measured and nothing more, and it is not evidence that the \
ticket was satisfied.
"""

HEAD_REVIEWER = """\
You are the Reviewer. You are one model call with no tools. You cannot run \
anything and you cannot edit anything. You are shown a ticket and the final \
state of the files a coding agent left behind. The project's own tests already \
pass, so any defect that remains is one those tests do not cover.
"""


def user_verdict(a: dict) -> str:
    return f"""\
TICKET (this is what the agent was asked to do, verbatim and complete):
{ticket(a['task'])}

FINAL STATE OF THE WORKSPACE:
{source_block(a)}

MEASUREMENT (no model involved):
  {visible_tests(a)}

Decide whether the work satisfies the ticket."""


def user_edge(a: dict) -> str:
    return f"""\
TICKET (this is what the agent was asked to do, verbatim and complete):
{ticket(a['task'])}

FINAL STATE OF THE WORKSPACE:
{source_block(a)}

MEASUREMENT (no model involved):
  {visible_tests(a)}

Find inputs on which this code does not do what the ticket asks. For each one \
give the exact call and the exact value the ticket implies it should produce. \
Only report a case you are confident the ticket decides; if the code is correct \
on every input the ticket speaks about, return an empty list."""


# ── schemas ──────────────────────────────────────────────────────────

VERDICT_SCHEMA = json.loads(
    (HERE.parent / "w11-artifacts/schemas/verdict.json").read_text(encoding="utf-8")
)

# Reasoning first, the decidable field last — F263 measured that as 0/14 against
# 17/17, and it is not a style choice. `cases` here is the reasoning: a concrete
# input and the value the ticket implies, which is the part `check.py` can run.
EDGE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "EdgeReport",
    "type": "object",
    "properties": {
        "reading": {
            "type": "string",
            "description": "What the ticket asks for, in your own words, in one or two sentences.",
        },
        "cases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "why": {
                        "type": "string",
                        "description": "Which clause of the ticket decides this case.",
                    },
                    "call": {
                        "type": "string",
                        "description": "The exact call, in the language of the code, e.g. split_bill(10, 4).",
                    },
                    "expected": {
                        "type": "string",
                        "description": "The exact value the ticket implies, e.g. [3, 3, 2, 2].",
                    },
                    "actual": {
                        "type": "string",
                        "description": "What this code produces instead, or 'panics'/'throws'/'hangs'.",
                    },
                },
                "additionalProperties": False,
                "required": ["why", "call", "expected", "actual"],
            },
        },
        "call": {"type": "string", "enum": ["pass", "fail"]},
    },
    "additionalProperties": False,
    "required": ["reading", "cases", "call"],
}


# ── backend ──────────────────────────────────────────────────────────


def call(messages, schema=None, model=CHAMPION, max_tokens=8192, temperature=0.0,
         timeout=1800, schema_name="verdict"):
    body = {
        "model": model,
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if schema is not None:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": schema},
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


def parsed(res: dict):
    """The JSON payload, or None. An empty payload is a classified outcome.

    F282's arm returned nothing at all 42% of the time and F284's second model
    3 of 3 on the correct answer, so `None` here is data and never an exception.
    """
    txt = (res.get("content") or "").strip()
    if not txt:
        return None
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        start = txt.find("{")
        end = txt.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(txt[start:end + 1])
            except json.JSONDecodeError:
                return None
        return None


def resumable(path: pathlib.Path):
    """Load a partial result file keyed by cell id, so a run can be continued."""
    if path.exists():
        return {r["key"]: r for r in json.loads(path.read_text(encoding="utf-8"))}
    return {}


def save(path: pathlib.Path, rows: dict):
    path.write_text(json.dumps(list(rows.values()), indent=1), encoding="utf-8")
