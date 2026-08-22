"""W11 item 3: does the ordering rule reach past the verdict, into the criterion?

`order.py`/`enumbias.py`/`prefix.py` established, on the Judge, that a decision
field emitted before the reasoning that justifies it is wrong 0/14 and right
17/17 the other way round. The Judge is not the only phase that emits a
decision inside a structured artifact. M1 Plan emits an acceptance criterion,
and `schemars` sorts `TaskWire`'s properties alphabetically, so the criterion
comes out FIRST — before `intent`, before `title`, before `touches`. The model
picks the command that will grade the work before it has written down what the
work is.

W11 F251 measured that six of eleven generated criteria exit 0 on the unfixed
tree. That probe is not the explanation of this one and must not be quoted as
if it were: its schema already put `acceptance_command` last, after `id`,
`title` and `files` (`w11-tier/plan.py:82-87`). So the ordering question is
open on its own, and this measures it.

  K  schemars order: criterion, depends_on, intent, title, touches     n=5
  L  criterion last: title, intent, touches, depends_on, criterion     n=5

Every emitted criterion is then run against the UNCHANGED fixture, in a copy,
and classified the way item 2 recommendation 6 classifies them:

  exit != 0  binds          — the criterion can fail, so it can pass meaningfully
  exit == 0  does not       — satisfied before the work starts (F251)
  cannot run unrunnable     — never a fail

The fixture's own 24 tests pass on the unfixed code by construction (its
`task.toml` says so), so `pytest` is the trap sitting in plain sight.
"""

import json
import pathlib
import shutil
import subprocess
import tempfile
import time
import urllib.request

BASE = "http://localhost:1234"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"
HERE = pathlib.Path(__file__).resolve().parent

import chain  # noqa: E402

FIXTURE = chain.FIXTURE
SYSTEM = chain.HEAD_PLAN
USER = chain.USER_PLAN

CRIT = {
    "type": "object",
    "properties": {
        "command": {"type": "string"},
        "cwd": {"type": "string"},
        "shell": {"type": "string", "enum": ["sh", "powershell", "cmd"]},
    },
    "required": ["command", "cwd", "shell"],
    "additionalProperties": False,
}

FIELDS = {
    "criterion": CRIT,
    "depends_on": {"type": "array", "items": {"type": "integer", "minimum": 0}},
    "intent": {"type": "string"},
    "title": {"type": "string"},
    "touches": {"type": "array", "items": {"type": "string"}},
}


def task_set_schema(order):
    return {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {k: FIELDS[k] for k in order},
                    "required": list(order),
                    "additionalProperties": False,
                },
            }
        },
        "required": ["tasks"],
        "additionalProperties": False,
    }


def plan(label, sch, max_tokens=8192):
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER},
        ],
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "task_set", "strict": True, "schema": sch},
        },
    }
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    content, usage = "", None
    with urllib.request.urlopen(req, timeout=1800) as resp:
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
    wall = time.perf_counter() - t0
    try:
        parsed = json.loads(content)
    except Exception:
        parsed = None
    ct = (usage or {}).get("completion_tokens")
    print(f"{label:<22} tasks={len((parsed or {}).get('tasks') or []):<2} "
          f"comp_tok={str(ct):>5} {wall:5.1f}s", flush=True)
    return parsed


def run_criterion(cmd, cwd_rel):
    """Run one criterion against a pristine copy of the unchanged fixture."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="w11crit-"))
    work = tmp / "fixture"
    shutil.copytree(FIXTURE, work)
    cwd = work / (cwd_rel or ".")
    if not cwd.is_dir():
        shutil.rmtree(tmp, ignore_errors=True)
        return ("unrunnable", None, f"cwd does not exist: {cwd_rel}")
    try:
        r = subprocess.run(
            cmd, shell=True, cwd=str(cwd), capture_output=True, text=True, timeout=90
        )
        out = (r.stdout + r.stderr).strip().replace("\n", " ")[:150]
        code = r.returncode
        # Distinguish "ran and returned non-zero" from "could not run at all".
        if code == 127 or "not recognized" in out or "command not found" in out:
            verdict = "unrunnable"
        elif code == 0:
            verdict = "does-not-discriminate"
        else:
            verdict = "binds"
        return (verdict, code, out)
    except subprocess.TimeoutExpired:
        return ("unrunnable", None, "timeout after 90s")
    except Exception as e:  # noqa: BLE001
        return ("unrunnable", None, str(e)[:120])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    arms = [
        ("K-criterion-first", ["criterion", "depends_on", "intent", "title", "touches"], 5),
        ("L-criterion-last", ["title", "intent", "touches", "depends_on", "criterion"], 5),
    ]
    rows = []
    for name, order, n in arms:
        print(f"-- {name}: {order} --")
        sch = task_set_schema(order)
        for i in range(n):
            ts = plan(f"{name}-{i+1}", sch)
            for j, t in enumerate((ts or {}).get("tasks") or []):
                c = t.get("criterion") or {}
                verdict, code, out = run_criterion(c.get("command", ""), c.get("cwd", "."))
                print(f"    task{j+1} {verdict:<22} exit={str(code):<5} {c.get('command','')[:70]}")
                if out:
                    print(f"            -> {out[:110]}")
                rows.append({
                    "arm": name, "run": i + 1, "task": j + 1,
                    "title": t.get("title", ""), "command": c.get("command", ""),
                    "cwd": c.get("cwd", "."), "shell": c.get("shell", ""),
                    "verdict": verdict, "exit": code, "output": out,
                })
        print()

    (HERE / "criterion-results.json").write_text(json.dumps(rows, indent=2))

    print("-- tally: a criterion that exits 0 on the unfixed tree measures nothing --")
    for name, _, _ in arms:
        got = [r for r in rows if r["arm"] == name]
        binds = sum(1 for r in got if r["verdict"] == "binds")
        zero = sum(1 for r in got if r["verdict"] == "does-not-discriminate")
        unr = sum(1 for r in got if r["verdict"] == "unrunnable")
        print(f"  {name:<20} criteria={len(got):<3} binds={binds}  "
              f"does-not-discriminate={zero}  unrunnable={unr}")


if __name__ == "__main__":
    main()
