"""OQ-W11-2: is M1 Plan skippable for a single-task mission, and what does it cost?

Item 1 put M1 Plan at one model call per mission, read-only, emitting a task set
where every task carries ONE executable acceptance criterion (F236's ruling, since
the criterion is the only thing in the family that ever bound). It left open
whether a mission that is obviously one task should pay for the call at all --
v1 always decomposes, paying a model call to produce a list of one
(`orchestratorService.ts`), and BCF deleted decomposition outright and gave a
greenfield-only reason (F237).

That is two questions and they need different evidence:

  COST      -- what does one Plan call cost on this box, at a realistic prompt
               (a repository file listing plus a mission statement)?
  BEHAVIOUR -- given a mission that is plainly one task, does the model emit a
               list of one, or does it manufacture a decomposition? If it emits
               one, "skip Plan for single-task missions" is an optimisation of
               something that already costs one call. If it inflates, skipping is
               a correctness fix, not an optimisation.

Two missions over the same real tree (the Claudette clone), n=3 each, schema-
constrained so the task set is a data structure rather than prose.
"""

import json
import pathlib
import time
import urllib.request

BASE = "http://localhost:1234"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"
TREE_ROOT = pathlib.Path(
    r"C:/Users/david/AppData/Local/Temp/claude/D--dev-ABCC-20-powerd-by-claudette"
    r"/42b00185-4a5a-4806-9e97-33bd4fcebc29/scratchpad/w11-integrate/claudette"
)

files = sorted(
    str(p.relative_to(TREE_ROOT)).replace("\\", "/")
    for p in TREE_ROOT.rglob("*.rs")
    if "target" not in p.parts
)
TREE = "\n".join(files)

SYSTEM = """\
You are Engineering. You plan missions over an EXISTING repository. You have \
read-only tools and you do not edit anything.

Decompose the mission into the smallest set of tasks that actually does the work. \
Every task must carry exactly one acceptance criterion that is a command a machine \
can run and that fails today and passes when the task is done. Prose criteria are \
not criteria. Do not invent tasks to fill out a list: a mission that is one change \
is one task.
"""

MISSION_SINGLE = """\
MISSION: `UsageTracker` double-counts tokens when a session is resumed — the tracker \
is seeded from the saved session and then only ever adds, so a resumed session \
reports the previous session's totals plus its own. Fix it so a resumed session \
reports only the current turn's usage.
"""

MISSION_MULTI = """\
MISSION: add a `--json` output mode to the CLI. Every command that prints a report \
to the terminal today must be able to emit the same information as a single JSON \
object on stdout instead, with the human output suppressed, and the schema must be \
stable enough to be tested.
"""

SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "task_set",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "files": {"type": "array", "items": {"type": "string"}},
                            "acceptance_command": {"type": "string"},
                        },
                        "required": ["id", "title", "files", "acceptance_command"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["tasks"],
            "additionalProperties": False,
        },
    },
}


def plan(label, mission, max_tokens=8192):
    user = f"REPOSITORY ({len(files)} Rust source files):\n{TREE}\n\n{mission}\nEmit the task set."
    body = {
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": user}],
        "stream": True, "stream_options": {"include_usage": True},
        "temperature": 0.0, "max_tokens": max_tokens,
        "response_format": SCHEMA,
    }
    req = urllib.request.Request(BASE + "/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    first = None
    content, reasoning, finish, usage = "", "", None, None
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
                if (d.get("content") or d.get("reasoning_content")) and first is None:
                    first = time.perf_counter() - t0
                content += d.get("content") or ""
                reasoning += d.get("reasoning_content") or ""
                if ch.get("finish_reason"):
                    finish = ch["finish_reason"]
    wall = time.perf_counter() - t0
    try:
        tasks = json.loads(content)["tasks"]
    except Exception:
        tasks = None
    u = usage or {}
    n = len(tasks) if tasks is not None else None
    runnable = None
    if tasks:
        runnable = sum(1 for t in tasks if t["acceptance_command"].strip()
                       and not t["acceptance_command"].strip().startswith(("Verify", "Ensure", "Check that")))
    print(f"{label:<24} tasks={str(n):>4} runnable_criteria={str(runnable):>4} "
          f"prompt_tok={u.get('prompt_tokens')} completion_tok={u.get('completion_tokens')} "
          f"reasoning_chars={len(reasoning):>6} ttft={first:6.2f}s wall={wall:6.1f}s finish={finish}",
          flush=True)
    if tasks:
        for t in tasks:
            print(f"{'':<26}- {t['title'][:64]:<64} | {t['acceptance_command'][:56]}", flush=True)
    return {"label": label, "n_tasks": n, "runnable": runnable, "wall_s": round(wall, 2),
            "ttft_s": round(first, 2) if first else None, "finish": finish,
            "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
            "reasoning_chars": len(reasoning), "tasks": tasks}


rows = []
print(f"tree: {len(files)} .rs files, {len(TREE)} chars\n")
print("-- mission that is plainly ONE task --")
for i in range(3):
    rows.append(plan(f"single r{i+1}", MISSION_SINGLE))
print("\n-- mission that is plainly MANY tasks --")
for i in range(3):
    rows.append(plan(f"multi r{i+1}", MISSION_MULTI))

single = [r["n_tasks"] for r in rows if r["label"].startswith("single")]
multi = [r["n_tasks"] for r in rows if r["label"].startswith("multi")]
print(f"\nsingle-task mission -> task counts {single}")
print(f"multi-task mission  -> task counts {multi}")
print(f"wall clock {[r['wall_s'] for r in rows]}")

pathlib.Path(__file__).with_name("plan-results.json").write_text(
    json.dumps(rows, indent=1), encoding="utf-8")
print("wrote plan-results.json")
