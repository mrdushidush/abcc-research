"""W4 item 3: ask the champion to be the estimator, and time it.

OQ-W6-7 asks whether v1's Haiku semantic pass is worth paying for, or whether
the local base agent can score complexity itself for free.  Item 1 (F366) killed
the "rules vs model" half of that -- v1's rule half never exceeds 6 on a real
task, so the `rules <= 8` gate never blocks and the model half is called on
149 of 149.  There is no rules-only arm.  And item 2 (F374) raised the bar: one
OBSERVED failure moves P(pass) by 44.6 points on Q56, and it arrives ~19 s after
dispatch.  So an a-priori estimator is scored on TWO axes at once:

    (a) does it correlate with the outcome better than a free word count?
       (the bar is rho = +0.219, BCF's rule_score; word count is +0.187)
    (b) what does it cost, in the same seconds a first attempt costs?
       (Q56's median attempt is 19.1 s)

Six arms.  Held constant: champion `qwen3.6-35b-a3b-mtp@iq3_s`, -c 65536,
--parallel 1, temperature 0.0 (the value claudette sends in production,
api.rs:783), max_tokens 6000.

  v1_verbatim    v1's `complexityAssessor.ts:47-67` prompt byte-for-byte with no
                 response_format -- the call v1 makes to Haiku, pointed at the
                 local model.  JSON regex-extracted from free text the way
                 `complexityAssessor.ts:95` does it.
  v1_schema      the same rubric under json_schema, complexity BEFORE reasoning
                 (v1's own field order).
  v1_schema_rf   the same schema with reasoning emitted FIRST.  W11 item 3 found
                 a schema's emission order decides the answer a constrained model
                 gives; this is that test on a routing input.
  pass_pct       the question a router actually has -- will ONE attempt pass the
                 hidden tests -- as a whole percent under an integer schema.
  v1_nothink     v1's rubric, schema, and NO reasoning trace.
  pass_pct_nothink  pass_pct with no reasoning trace.

The two `nothink` arms go to the BARE llama-server, not to LM Studio's proxy:
`chat_template_kwargs: {"enable_thinking": false}` is honoured there (0 trace
chars, 6.4 s) and silently DROPPED by the proxy on :1234, which answers the same
request with a full trace and HTTP 200.  Same weights, same load, same sampler --
the only difference is the hop.  Those two arms are the cheapest estimator this
box can build; the other four are what the estimator costs on the path claudette
actually uses today.

⚠ Two traps this harness exists to avoid, both found in the pilot:
  * The first `pass_prob` arm asked for "the probability" and constrained the
    answer to an INTEGER.  The model answered 0.95 and the grammar emitted
    `{"p_pass": 0}` -- valid JSON, HTTP 200, a plausible wrong number on every
    task.  Name the units in the prompt AND in the field name.
  * The unconstrained reasoning trace is spent first (W2 F82) and it is long.
    At max_tokens 3000 whole cells came back `finish_reason: length` with
    `content: ""`.  6000 here, and `completion_tokens` is recorded so the
    truncation rate at any lower budget is derivable.
"""
import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROXY = "http://localhost:1234/v1/chat/completions"
BARE = "http://127.0.0.1:64703/v1/chat/completions"
BARE_KEY = "zNKTod22FwP7bKCQPnoJc6Ofil9HM-8tmQGKZBBrmiM"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"
TEMPERATURE = 0.0
MAX_TOKENS = 6000

# --- v1's prompt, byte-for-byte from complexityAssessor.ts:47-67 --------------
V1_PROMPT = """You are a task complexity assessor for a coding agent system.

Assess the complexity of this programming task on a scale of 1-10:
- 1-3: Simple (single function, basic logic, no dependencies)
- 4-5: Medium (multiple functions, some validation, basic tests)
- 6-7: Moderate (multiple files, external APIs, error handling)
- 8-9: Complex (architecture design, multiple systems, advanced patterns)
- 10: Very Complex (distributed systems, complex algorithms, extensive testing)

Task Title: {title}

Task Description:
{description}

Respond with ONLY a JSON object in this exact format:
{{
  "complexity": <number 1-10>,
  "reasoning": "<1-2 sentence explanation>",
  "factors": ["<factor1>", "<factor2>", "<factor3>"]
}}"""

# The same rubric, minus the hand-rolled output contract the schema replaces.
V1_RUBRIC = """You are a task complexity assessor for a coding agent system.

Assess the complexity of this programming task on a scale of 1-10:
- 1-3: Simple (single function, basic logic, no dependencies)
- 4-5: Medium (multiple functions, some validation, basic tests)
- 6-7: Moderate (multiple files, external APIs, error handling)
- 8-9: Complex (architecture design, multiple systems, advanced patterns)
- 10: Very Complex (distributed systems, complex algorithms, extensive testing)

Task Title: {title}

Task Description:
{description}"""

PASS_PROMPT = """An autonomous coding agent will be given the task below, in a working \
directory that already contains the project's files. It works alone, with file-read, \
file-write and shell tools, for up to 40 rounds. When it stops, hidden tests it never \
saw are run against whatever it left on disk.

Estimate the chance that it passes those hidden tests on this single attempt, as a \
whole number of percent from 0 to 100.

Task Title: {title}

Task Description:
{description}"""


def schema(name, props, order):
    return {"type": "json_schema",
            "json_schema": {"name": name, "strict": True,
                            "schema": {"type": "object", "properties": props,
                                       "required": order,
                                       "additionalProperties": False}}}


C = {"type": "integer", "minimum": 1, "maximum": 10}
P = {"type": "integer", "minimum": 0, "maximum": 100}
R = {"type": "string"}

CPLX = schema("complexity_assessment", {"complexity": C, "reasoning": R},
              ["complexity", "reasoning"])
CPLX_RF = schema("complexity_assessment", {"reasoning": R, "complexity": C},
                 ["reasoning", "complexity"])
PASS_FMT = schema("pass_estimate", {"p_pass_percent": P}, ["p_pass_percent"])

NOTHINK = {"enable_thinking": False}

ARMS = {
    "v1_verbatim":      dict(prompt=V1_PROMPT,   format=None,     field="complexity",
                             scale=(1, 10),  endpoint="proxy", kwargs=None),
    "v1_schema":        dict(prompt=V1_RUBRIC,   format=CPLX,     field="complexity",
                             scale=(1, 10),  endpoint="proxy", kwargs=None),
    "v1_schema_rf":     dict(prompt=V1_RUBRIC,   format=CPLX_RF,  field="complexity",
                             scale=(1, 10),  endpoint="proxy", kwargs=None),
    "pass_pct":         dict(prompt=PASS_PROMPT, format=PASS_FMT, field="p_pass_percent",
                             scale=(0, 100), endpoint="proxy", kwargs=None),
    "v1_nothink":       dict(prompt=V1_RUBRIC,   format=CPLX,     field="complexity",
                             scale=(1, 10),  endpoint="bare",  kwargs=NOTHINK),
    "pass_pct_nothink": dict(prompt=PASS_PROMPT, format=PASS_FMT, field="p_pass_percent",
                             scale=(0, 100), endpoint="bare",  kwargs=NOTHINK),
}


def call(prompt, spec):
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "temperature": TEMPERATURE, "max_tokens": MAX_TOKENS}
    if spec["format"]:
        body["response_format"] = spec["format"]
    if spec["kwargs"] is not None:
        body["chat_template_kwargs"] = spec["kwargs"]
    headers = {"Content-Type": "application/json"}
    url = PROXY
    if spec["endpoint"] == "bare":
        url = BARE
        headers["Authorization"] = "Bearer " + BARE_KEY
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers=headers)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            raw = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"wall_s": round(time.perf_counter() - t0, 3),
                "finish_reason": "http_%d" % e.code,
                "content": e.read().decode("utf-8", "replace")[:500],
                "reasoning_content": "", "usage": {}}
    wall = time.perf_counter() - t0
    ch = raw["choices"][0]
    msg = ch["message"]
    return {"wall_s": round(wall, 3), "finish_reason": ch.get("finish_reason"),
            "content": msg.get("content") or "",
            "reasoning_content": msg.get("reasoning_content") or "",
            "usage": raw.get("usage", {})}


def extract(arm, content):
    """v1 pulls JSON out of free text with a greedy brace regex
    (complexityAssessor.ts:95).  Reproduce that for the unconstrained arm; a
    constrained arm parses the same way and never needs the leniency."""
    m = re.search(r"\{[\s\S]*\}", content)
    if not m:
        return None, "no_json"
    try:
        obj = json.loads(m.group(0))
    except Exception:
        return None, "bad_json"
    v = obj.get(ARMS[arm]["field"])
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None, "no_field"
    lo, hi = ARMS[arm]["scale"]
    return max(lo, min(hi, v)), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--rep-offset", type=int, default=0)
    ap.add_argument("--tasks", default="")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    rows = [json.loads(l) for l in open(os.path.join(HERE, "tasks.jsonl"),
                                        encoding="utf-8")]
    if a.tasks:
        want = set(a.tasks.split(","))
        rows = [r for r in rows if "%s/%s" % (r["suite"], r["id"]) in want]
    if a.limit:
        rows = rows[:a.limit]
    arms = a.arms.split(",")

    out = open(os.path.join(HERE, a.out), "a", encoding="utf-8")
    n, t0 = 0, time.perf_counter()
    total = len(rows) * len(arms) * a.repeats
    for rep in range(a.rep_offset, a.rep_offset + a.repeats):
        for r in rows:
            for arm in arms:
                spec = ARMS[arm]
                prompt = spec["prompt"].format(title=r["title"], description=r["prompt"])
                res = call(prompt, spec)
                val, err = extract(arm, res["content"])
                rec = {"suite": r["suite"], "id": r["id"], "arm": arm, "rep": rep,
                       "value": val, "parse_error": err,
                       "wall_s": res["wall_s"], "finish_reason": res["finish_reason"],
                       "prompt_tokens": res["usage"].get("prompt_tokens"),
                       "completion_tokens": res["usage"].get("completion_tokens"),
                       "reasoning_chars": len(res["reasoning_content"]),
                       "content": res["content"][:2000],
                       "reasoning": res["reasoning_content"][:3000]}
                out.write(json.dumps(rec) + "\n")
                out.flush()
                n += 1
                el = time.perf_counter() - t0
                print("[{}/{}] {}/{:<32s} {:<17s} r{} {:6.2f}s val={} {} out={} "
                      "think={} eta={:.1f}m".format(
                          n, total, r["suite"], r["id"], arm, rep, res["wall_s"], val,
                          res["finish_reason"], res["usage"].get("completion_tokens"),
                          len(res["reasoning_content"]), el / n * (total - n) / 60),
                      flush=True)
    out.close()


if __name__ == "__main__":
    main()
