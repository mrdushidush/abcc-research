"""Diagnostic: the pass_prob arm returned {"p_pass": 0} on every pilot task while
its own reasoning trace concluded "Estimate: 90%".  Before that is written down
as a finding about the MODEL, find out whether it is a fact about the SCHEMA.

Five variants of the same question on the same task, changing one thing at a
time: no constraint at all, integer with the 0-100 bounds, integer with no
bounds, number with no bounds, and a bounded integer preceded by a reasoning
field.  Whatever differs between them is the cause.
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

PASS_PROMPT = """An autonomous coding agent will be given the task below, in a working \
directory that already contains the project's files. It works alone, with file-read, \
file-write and shell tools, for up to 40 rounds. When it stops, hidden tests it never \
saw are run against whatever it left on disk.

Estimate the probability that it passes those hidden tests on this single attempt.

Task Title: {title}

Task Description:
{description}"""


def fmt(props, order):
    return {"type": "json_schema",
            "json_schema": {"name": "pass_estimate", "strict": True,
                            "schema": {"type": "object", "properties": props,
                                       "required": order,
                                       "additionalProperties": False}}}


VARIANTS = [
    ("no_constraint", None),
    ("int_0_100", fmt({"p_pass": {"type": "integer", "minimum": 0, "maximum": 100}},
                      ["p_pass"])),
    ("int_unbounded", fmt({"p_pass": {"type": "integer"}}, ["p_pass"])),
    ("number_unbounded", fmt({"p_pass": {"type": "number"}}, ["p_pass"])),
    ("reason_then_int", fmt({"reasoning": {"type": "string"},
                             "p_pass": {"type": "integer", "minimum": 0, "maximum": 100}},
                            ["reasoning", "p_pass"])),
    ("string_pct", fmt({"p_pass_percent": {"type": "string"}}, ["p_pass_percent"])),
]


def call(prompt, rf, max_tokens=3000):
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0, "max_tokens": max_tokens}
    if rf:
        body["response_format"] = rf
    req = urllib.request.Request(URL, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=900) as r:
        raw = json.loads(r.read().decode("utf-8"))
    ch = raw["choices"][0]
    return (round(time.perf_counter() - t0, 2), ch.get("finish_reason"),
            ch["message"].get("content") or "",
            ch["message"].get("reasoning_content") or "", raw.get("usage", {}))


for tid in ("q56/Q03", "q56/Q46"):
    r = rows[tid]
    p = PASS_PROMPT.format(title=r["title"], description=r["prompt"])
    print(f"########## {tid}   control pass rate {r['control_rate']:.2f}")
    for name, rf in VARIANTS:
        wall, fin, content, reasoning, usage = call(p, rf)
        print(f"  -- {name:18s} {wall:6.2f}s  {fin:8s} "
              f"out={usage.get('completion_tokens')}")
        print(f"     content : {content[:300]!r}")
        if name == "no_constraint":
            print(f"     reason  : ...{reasoning[-200:]!r}")
    print()
