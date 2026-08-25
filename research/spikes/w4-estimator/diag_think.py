"""Diagnostic 2: two things the first diagnostic exposed have to be settled before
the real run, because both of them decide the estimator's PRICE.

1.  The units.  The prompt said "estimate the probability" and the model answered
    0.95; an `integer` schema turned that into `{"p_pass": 0}` -- valid JSON, HTTP
    200, a plausible wrong number.  Fix the prompt to name the units and keep the
    integer bound, and check the two agree.

2.  The reasoning trace.  Every call so far spent 800-3000 completion tokens on an
    unconstrained trace before reaching a two-token answer, which is the whole
    reason an estimate costs 15-50 s.  The chat template this server is running
    (`--chat-template-file`, `.../chat-template.jinja`) references `enable_thinking`,
    so a no-think estimator may be reachable.  Two ways to ask for it:
    `chat_template_kwargs: {"enable_thinking": false}` on the request, and Qwen's
    `/no_think` token in the message.  If either works, the estimator's real price
    is the no-think price and pricing it with the trace would be pricing a choice.
"""
import json
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
URL = "http://localhost:1234/v1/chat/completions"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"

rows = {f"{r['suite']}/{r['id']}": r
        for r in (json.loads(l) for l in open(os.path.join(HERE, "tasks.jsonl"),
                                              encoding="utf-8"))}

PCT_PROMPT = """An autonomous coding agent will be given the task below, in a working \
directory that already contains the project's files. It works alone, with file-read, \
file-write and shell tools, for up to 40 rounds. When it stops, hidden tests it never \
saw are run against whatever it left on disk.

Estimate the chance that it passes those hidden tests on this single attempt, as a \
whole number of percent from 0 to 100.

Task Title: {title}

Task Description:
{description}"""

INT_FMT = {"type": "json_schema",
           "json_schema": {"name": "pass_estimate", "strict": True,
                           "schema": {"type": "object",
                                      "properties": {"p_pass_percent": {
                                          "type": "integer",
                                          "minimum": 0, "maximum": 100}},
                                      "required": ["p_pass_percent"],
                                      "additionalProperties": False}}}


def call(prompt, rf, max_tokens=3000, kwargs=None):
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0, "max_tokens": max_tokens}
    if rf:
        body["response_format"] = rf
    if kwargs is not None:
        body["chat_template_kwargs"] = kwargs
    req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            raw = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return (round(time.perf_counter() - t0, 2), f"HTTP {e.code}",
                e.read().decode("utf-8")[:200], "", {})
    ch = raw["choices"][0]
    return (round(time.perf_counter() - t0, 2), ch.get("finish_reason"),
            ch["message"].get("content") or "",
            ch["message"].get("reasoning_content") or "", raw.get("usage", {}))


CASES = [
    ("pct_prompt_int_schema", PCT_PROMPT, INT_FMT, None, ""),
    ("kwargs_enable_thinking_false", PCT_PROMPT, INT_FMT, {"enable_thinking": False}, ""),
    ("slash_no_think", PCT_PROMPT, INT_FMT, None, " /no_think"),
    ("kwargs_and_slash", PCT_PROMPT, INT_FMT, {"enable_thinking": False}, " /no_think"),
]

for tid in ("q56/Q03", "q56/Q46", "q56/Q02"):
    r = rows[tid]
    print(f"########## {tid}   control pass rate {r['control_rate']:.2f}")
    for name, tmpl, rf, kwargs, suffix in CASES:
        p = tmpl.format(title=r["title"], description=r["prompt"]) + suffix
        wall, fin, content, reasoning, usage = call(p, rf, kwargs=kwargs)
        print(f"  -- {name:30s} {wall:6.2f}s {str(fin):8s} "
              f"out={usage.get('completion_tokens')} think_chars={len(reasoning)}")
        print(f"     {content[:160]!r}")
    print()
