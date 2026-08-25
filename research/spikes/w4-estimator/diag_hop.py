"""Diagnostic 3: separate the HOP from the TRACE, because the main run confounds them.

The four expensive arms go through LM Studio's proxy on :1234 (the path claudette
actually uses) and the two cheap arms go to the bare `llama-server` on :64703,
because `chat_template_kwargs: {"enable_thinking": false}` appeared to work on one
and not the other.  That is two changes at once.  This is the 2x2 that separates
them: identical prompt, identical schema, identical sampler, one server, four
combinations of {endpoint} x {kwarg present}.

What it has to establish:
  1. Does the proxy DROP the kwarg, or does the model ignore it?  If the bare
     server answers the same request with no trace and the proxy answers it with
     a full trace, the difference is the hop, and the request still returns 200 --
     a silent capability loss, not an error.
  2. What does the hop itself cost?  The `endpoint=bare, no kwarg` cell is the
     control that prices it, so the main run's cost table can say how much of the
     cheap arms' saving is "no trace" and how much is "one less hop".
"""
import json
import os
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROXY = "http://localhost:1234/v1/chat/completions"
BARE = "http://127.0.0.1:64703/v1/chat/completions"
BARE_KEY = "zNKTod22FwP7bKCQPnoJc6Ofil9HM-8tmQGKZBBrmiM"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"

rows = {"%s/%s" % (r["suite"], r["id"]): r
        for r in (json.loads(l) for l in open(os.path.join(HERE, "tasks.jsonl"),
                                              encoding="utf-8"))}

RUBRIC = """You are a task complexity assessor for a coding agent system.

Assess the complexity of this programming task on a scale of 1-10:
- 1-3: Simple (single function, basic logic, no dependencies)
- 4-5: Medium (multiple functions, some validation, basic tests)
- 6-7: Moderate (multiple files, external APIs, error handling)
- 8-9: Complex (architecture design, multiple systems, advanced patterns)
- 10: Very Complex (distributed systems, complex algorithms, extensive testing)

Task Title: {title}

Task Description:
{description}"""

FMT = {"type": "json_schema",
       "json_schema": {"name": "complexity_assessment", "strict": True,
                       "schema": {"type": "object",
                                  "properties": {
                                      "complexity": {"type": "integer",
                                                     "minimum": 1, "maximum": 10},
                                      "reasoning": {"type": "string"}},
                                  "required": ["complexity", "reasoning"],
                                  "additionalProperties": False}}}


def call(url, key, prompt, kwargs):
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0, "max_tokens": 6000, "response_format": FMT}
    if kwargs is not None:
        body["chat_template_kwargs"] = kwargs
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers=headers)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            raw = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return (round(time.perf_counter() - t0, 2), "http_%d" % e.code,
                e.read().decode("utf-8", "replace")[:200], "", {})
    ch = raw["choices"][0]
    return (round(time.perf_counter() - t0, 2), ch.get("finish_reason"),
            ch["message"].get("content") or "",
            ch["message"].get("reasoning_content") or "", raw.get("usage", {}))


CELLS = [("proxy", PROXY, "", None),
         ("proxy", PROXY, "", {"enable_thinking": False}),
         ("bare", BARE, BARE_KEY, None),
         ("bare", BARE, BARE_KEY, {"enable_thinking": False})]

print("=== the 2x2: same prompt, same schema, same weights, same sampler ===")
print("  %-6s %-14s %8s %9s %8s %8s  %s"
      % ("hop", "enable_think", "wall_s", "out_tok", "think_ch", "finish", "content"))
for tid in ("q56/Q03", "q56/Q46", "q56/Q02"):
    r = rows[tid]
    p = RUBRIC.format(title=r["title"], description=r["prompt"])
    print("  -- %s" % tid)
    for hop, url, key, kwargs in CELLS:
        wall, fin, content, reasoning, usage = call(url, key, p, kwargs)
        print("  %-6s %-14s %8.2f %9s %8d %8s  %s"
              % (hop, "absent" if kwargs is None else "false", wall,
                 usage.get("completion_tokens"), len(reasoning), fin,
                 content[:70].replace("\n", " ")))
print()
print("Read the table this way: the two `absent` rows price the HOP, and the")
print("proxy `false` row against the bare `false` row says whether the kwarg")
print("survives the hop at all.")
