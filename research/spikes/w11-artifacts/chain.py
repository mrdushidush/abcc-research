"""W11 item 3: does the Rust type actually reach the model?

The brief's whole case for typing the handoffs is one sentence: *"Rust's type
system should make these contracts enforceable rather than hopeful, which is a
real advantage over V1's JSON-by-convention approach"* (`RESEARCH_BRIEF.md:543`).
That claim is a chain, and a chain is only as good as its worst link:

    Rust type  ->  JSON Schema (schemars)  ->  the server's grammar  ->
    the model's bytes  ->  serde_json::from_str back into the Rust type

Item 2 already recommended `response_format: json_schema, strict: true` for
every structured artifact (F248). What nobody has run is the *derived* schema:
w11-tier's `verdict.py` sent a schema hand-written to be flat and easy --
no `$ref`, no `$defs`, no nullable field, every property required. That is not
what `schemars` emits from a real Rust type. It emits `$defs` + `$ref` for every
named struct and enum, `type: ["string","null"]` for `Option<T>`, and -- the
interesting one -- it leaves `Option` fields OUT of `required`, which is exactly
what OpenAI's strict mode forbids.

So three arms per artifact:

  strict    the schemars output, verbatim, as response_format
  repaired  the same schema with every property forced into `required`
            (the OpenAI strict-mode rule), to tell a schema problem from an
            optionality problem if `strict` fails
  prompt    no response_format at all; the schema pasted into the prompt and
            the format asked for in words -- what all three donors do, and the
            fair version of that arm per F248

and then the payload goes back through the real `serde_json::from_str` for the
real type, because a server that accepts the schema and emits conforming bytes
still has to satisfy `deny_unknown_fields`.

Fixture: `corpus/suites/k/tasks/finish_the_cancelled_status`, which is in this
repo, so this probe is re-runnable without a scratchpad clone. 16 files, ~9.4k
tokens, a real four-site bug and one correct decoy consumer.
"""

import json
import pathlib
import subprocess
import time
import urllib.error
import urllib.request

BASE = "http://localhost:1234"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
FIXTURE = REPO / "corpus/suites/k/tasks/finish_the_cancelled_status/fixture"
SCHEMAS = HERE / "schemas"
OUT = HERE / "payloads"
BIN = HERE / "artifacts/target/debug/artifacts.exe"

OUT.mkdir(exist_ok=True)

# ── the tree, as A1 and M1 would see it ──────────────────────────────

tree_files = sorted(
    str(p.relative_to(FIXTURE)).replace("\\", "/")
    for p in FIXTURE.rglob("*")
    if p.is_file()
)
TREE = "\n".join(tree_files)

TICKET = (FIXTURE.parent / "prompt.txt").read_text(encoding="utf-8")

# Two files pasted in, the way a Localize phase would after a grep.
STATUS_PY = (FIXTURE / "jobs/status.py").read_text(encoding="utf-8")
SLA_PY = (FIXTURE / "jobs/sla.py").read_text(encoding="utf-8")

# ── the sham fix, as A2 Change would have produced it ────────────────

DIFF = """\
--- a/jobs/sla.py
+++ b/jobs/sla.py
@@ -25,7 +25,7 @@ def finished_at(job, now):
     is measured against the current time, because an unfinished job keeps
     accruing.
     \"\"\"
-    if job.status in (st.DONE, st.FAILED):
+    if job.status in (st.DONE, st.FAILED, st.CANCELLED):
         return job.ended_at if job.ended_at is not None else now
     return now
"""

MEASUREMENTS = """\
MEASUREMENT SET (phase A3, no model involved):
  build          Measured(ok)    python3 -c 'import jobs' -> exit 0, 0.06s
  project suite  Measured(ok)    pytest -q -> 24 passed, 1.21s
  criterion      Measured(fail)  bash verify.sh . -> exit 0, stdout:
                                 "RESULT: FAIL COUNTS must show cancelled=4 -
                                  got: COUNTS done=11 failed=5 running=2 queued=2 other=4"
  diff scan      Measured(ok)    1 file, +1 -1, no secrets, no new dependencies
"""

# ── phase heads ──────────────────────────────────────────────────────

HEAD_LOCALIZE = """\
You are Recon. You localize a task in an existing repository. You have read-only \
tools and you do not edit anything. Your output is a grounded brief: every path \
you name must be a path that exists in the tree you were shown, exactly as it \
appears there.
"""

HEAD_PLAN = """\
You are Engineering. You plan missions over an existing repository. You have \
read-only tools and you do not edit anything. Every task carries exactly one \
acceptance criterion that is a command a machine can run, that fails today and \
passes when the task is done. Prose criteria are not criteria. Every path you \
name must exist in the tree you were shown.
"""

HEAD_JUDGE = """\
You are the Judge. You are one model call with no tools. You see the brief, the \
diff and the measurement set. You do not run anything and you do not edit \
anything. A measurement that says fail is a fact, not an opinion: a verdict of \
pass while a required measurement failed is itself a defect.
"""

BRIEF_TEXT = """\
BRIEF (phase A1): `cancelled` was added as a status in 4.2 and the SLA report \
now counts cancelled jobs as breaches. Sites: jobs/sla.py (finished_at measures \
a cancelled job against `now`, so it accrues forever). The acceptance criterion \
is `bash verify.sh .`, which runs the report and asserts the counts.
"""

USER_LOCALIZE = f"""\
REPOSITORY TREE (workspace root is the tree root):
{TREE}

jobs/status.py:
{STATUS_PY}

jobs/sla.py:
{SLA_PY}

TICKET:
{TICKET}
Produce the brief."""

USER_PLAN = f"""\
REPOSITORY TREE (workspace root is the tree root):
{TREE}

jobs/status.py:
{STATUS_PY}

MISSION:
{TICKET}
Produce the task set."""

USER_JUDGE = f"""\
{BRIEF_TEXT}
--- git diff HEAD ---
{DIFF}--- end diff ---

{MEASUREMENTS}
Return your verdict."""

CASES = [
    ("brief", HEAD_LOCALIZE, USER_LOCALIZE),
    ("task_set", HEAD_PLAN, USER_PLAN),
    ("verdict", HEAD_JUDGE, USER_JUDGE),
]


def repair_required(node):
    """Force every property into `required`, recursively — the OpenAI strict-mode
    rule that schemars does not follow for `Option<T>`."""
    if isinstance(node, dict):
        if "properties" in node and isinstance(node["properties"], dict):
            node["required"] = list(node["properties"].keys())
        for v in node.values():
            repair_required(v)
    elif isinstance(node, list):
        for v in node:
            repair_required(v)
    return node


def call(label, kind, system, user, schema, max_tokens=8192):
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    if schema is not None:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": kind, "strict": True, "schema": schema},
        }
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    content, reasoning, finish, usage, http = "", "", None, None, 200
    try:
        with urllib.request.urlopen(req, timeout=1800) as resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    obj = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if obj.get("usage"):
                    usage = obj["usage"]
                for ch in obj.get("choices") or []:
                    d = ch.get("delta") or {}
                    content += d.get("content") or ""
                    reasoning += d.get("reasoning_content") or ""
                    if ch.get("finish_reason"):
                        finish = ch["finish_reason"]
    except urllib.error.HTTPError as e:
        http = e.code
        content = e.read().decode("utf-8", errors="replace")[:400]
    wall = time.perf_counter() - t0

    json_ok = False
    if http == 200:
        try:
            json.loads(content)
            json_ok = True
        except Exception:
            pass

    path = OUT / f"{label}.json"
    path.write_text(content, encoding="utf-8")

    # The last link: does serde accept it as the real Rust type?
    serde = "-"
    if json_ok:
        r = subprocess.run(
            [str(BIN), "check", kind, str(path)], capture_output=True, text=True
        )
        serde = r.stdout.strip()

    ct = (usage or {}).get("completion_tokens")
    rt = ((usage or {}).get("completion_tokens_details") or {}).get("reasoning_tokens")
    print(
        f"{label:<22} http={http} finish={str(finish):<6} "
        f"comp_tok={str(ct):>5} reas_tok={str(rt):>5} bytes={len(content):>5} "
        f"json={'OK ' if json_ok else 'NO '} {wall:6.1f}s",
        flush=True,
    )
    if http != 200:
        print(f"{'':<22}   server said: {content[:220]}", flush=True)
    elif serde != "-":
        print(f"{'':<22}   {serde}", flush=True)
    return {
        "label": label,
        "kind": kind,
        "http": http,
        "finish": finish,
        "completion_tokens": ct,
        "reasoning_tokens": rt,
        "bytes": len(content),
        "json_ok": json_ok,
        "serde": serde,
        "wall_s": round(wall, 2),
    }


def main():
    print(f"fixture: {FIXTURE}")
    print(f"tree: {len(tree_files)} files;  Localize prompt {len(USER_LOCALIZE)} chars, "
          f"Plan {len(USER_PLAN)} chars, Judge {len(USER_JUDGE)} chars")
    print()
    rows = []

    for kind, system, user in CASES:
        raw = json.loads((SCHEMAS / f"{kind}.json").read_text())

        print(f"-- {kind} --")
        rows.append(call(f"{kind}-strict", kind, system, user, raw))

        repaired = repair_required(json.loads(json.dumps(raw)))
        rows.append(call(f"{kind}-repaired", kind, system, user, repaired))

        prompt_arm = (
            system
            + "\nReturn ONLY a JSON object conforming to this schema, with no "
            "markdown fences and no commentary:\n"
            + json.dumps(raw, separators=(",", ":"))
        )
        rows.append(call(f"{kind}-prompt", kind, prompt_arm, user, None))
        print()

    (HERE / "chain-results.json").write_text(json.dumps(rows, indent=2))

    # Grounding: of the paths that survived the schema, how many exist?
    print("-- grounding: schema-valid is not grounded --")
    for r in rows:
        if not r["json_ok"] or r["kind"] not in ("brief", "task_set"):
            continue
        p = OUT / f"{r['label']}.json"
        g = subprocess.run(
            [str(BIN), "ground", str(FIXTURE), str(p)], capture_output=True, text=True
        )
        print(f"{r['label']}:")
        print(g.stdout.rstrip())


if __name__ == "__main__":
    main()
