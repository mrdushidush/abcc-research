"""W11 item 3: is the order of a schema's fields causal for the answer?

`chain.py` produced a result that has to be chased rather than reported. Both
schema-constrained Judge arms emitted:

    {"call": "pass", "defects": [], "rationale": "... Therefore the overall
     verdict must be FAIL."}

— the constrained field and the free-text field of the same object contradict
each other, and the field the gate reads is the wrong one. The unconstrained
arm, given the same prompt, answered `fail`.

The suspect is field order. `schemars` emits `properties` from a sorted map, so
the Rust declaration order (`call`, `rationale`, `defects`) survives as
alphabetical order (`call`, `defects`, `rationale`) — and llama.cpp's
json-schema-to-grammar walks `properties` in the order it finds them, so the
model must commit to `call` before it writes a word of justification. Whether
`call` precedes `rationale` in the emitted object is decided by the letter C
preceding the letter R, and nothing else.

Four arms, same prompt, same measurement set, ground truth `fail` (the
acceptance criterion returned RESULT: FAIL):

  A  call-first     the schemars order, verbatim                       n=5
  B  reordered      same names, `rationale` moved ahead of `call`      n=5
  C  renamed        `rationale` -> `assessment`, so it sorts first     n=3
  D  prompt-only    no response_format at all                          n=3

plus one enforcement control: a schema whose `call` enum holds two words the
model would never volunteer. If the payload comes back holding one of them, the
grammar is being applied and arms A-C are measuring the grammar rather than the
model's manners.
"""

import json
import pathlib
import time
import urllib.error
import urllib.request

BASE = "http://localhost:1234"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"
HERE = pathlib.Path(__file__).resolve().parent

# Same Judge prompt as chain.py, kept here verbatim so this probe stands alone.
import chain  # noqa: E402

SYSTEM = chain.HEAD_JUDGE
USER = chain.USER_JUDGE

DEFECT = {
    "type": "object",
    "properties": {
        "path": {"type": ["string", "null"]},
        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
        "description": {"type": "string"},
    },
    "required": ["path", "severity", "description"],
    "additionalProperties": False,
}


def schema(order, call_key="call", rationale_key="rationale", call_enum=None):
    props = {
        call_key: {"type": "string", "enum": call_enum or ["pass", "fail"]},
        rationale_key: {"type": "string"},
        "defects": {"type": "array", "items": DEFECT},
    }
    ordered = {k: props[k] for k in order}
    return {
        "type": "object",
        "properties": ordered,
        "required": list(order),
        "additionalProperties": False,
    }


def call(label, sys_prompt, sch, max_tokens=8192):
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": USER},
        ],
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    if sch is not None:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "verdict", "strict": True, "schema": sch},
        }
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    content, finish, usage = "", None, None
    try:
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
                    if ch.get("finish_reason"):
                        finish = ch["finish_reason"]
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8", errors="replace")[:300]
    wall = time.perf_counter() - t0

    parsed, first_key = None, None
    try:
        parsed = json.loads(content)
        first_key = next(iter(parsed))
    except Exception:
        pass

    verdict = None
    rationale = ""
    if isinstance(parsed, dict):
        verdict = parsed.get("call") or parsed.get("outcome")
        rationale = parsed.get("rationale") or parsed.get("assessment") or ""

    # Does the prose contradict the field? Look for the ground truth in words.
    says_fail = any(
        s in rationale.upper() for s in ("MUST BE FAIL", "VERDICT MUST BE FAIL",
                                         "MANDATES A FAIL", "THEREFORE FAIL",
                                         "OVERALL VERDICT MUST BE FAIL")
    )
    ct = (usage or {}).get("completion_tokens")
    rt = ((usage or {}).get("completion_tokens_details") or {}).get("reasoning_tokens")
    flag = ""
    if verdict == "pass" and says_fail:
        flag = "   <- field says pass, prose says fail"
    print(
        f"{label:<24} first_key={str(first_key):<11} call={str(verdict):<6} "
        f"comp_tok={str(ct):>5} reas={str(rt):>5} {wall:5.1f}s{flag}",
        flush=True,
    )
    return {
        "label": label,
        "first_key": first_key,
        "call": verdict,
        "rationale": rationale,
        "contradicts": bool(verdict == "pass" and says_fail),
        "completion_tokens": ct,
        "reasoning_tokens": rt,
        "wall_s": round(wall, 2),
        "raw": content[:2000],
    }


def main():
    rows = []

    print("-- enforcement control: an enum the model would never volunteer --")
    ctl = schema(["call", "rationale", "defects"], call_enum=["affirmative", "negative"])
    rows.append(call("control-enum", SYSTEM, ctl))
    print()

    print("-- A: schemars order (call before rationale) --")
    a = schema(["call", "defects", "rationale"])
    for i in range(5):
        rows.append(call(f"A-call-first-{i+1}", SYSTEM, a))
    print()

    print("-- B: same names, rationale moved ahead of call --")
    b = schema(["rationale", "defects", "call"])
    for i in range(5):
        rows.append(call(f"B-reordered-{i+1}", SYSTEM, b))
    print()

    print("-- C: rationale renamed `assessment`, so it sorts first --")
    c = schema(["assessment", "call", "defects"], rationale_key="assessment")
    for i in range(3):
        rows.append(call(f"C-renamed-{i+1}", SYSTEM, c))
    print()

    print("-- D: no response_format at all --")
    d_sys = (
        SYSTEM
        + "\nReturn ONLY a JSON object with keys `call` (\"pass\" or \"fail\"), "
        "`rationale` (string) and `defects` (array), no fences, no commentary."
    )
    for i in range(3):
        rows.append(call(f"D-prompt-{i+1}", d_sys, None))
    print()

    (HERE / "order-results.json").write_text(json.dumps(rows, indent=2))

    print("-- tally (ground truth: fail; the criterion returned RESULT: FAIL) --")
    for arm in ("A-call-first", "B-reordered", "C-renamed", "D-prompt"):
        got = [r for r in rows if r["label"].startswith(arm)]
        fails = sum(1 for r in got if r["call"] == "fail")
        contra = sum(1 for r in got if r["contradicts"])
        print(f"  {arm:<14} correct(fail) {fails}/{len(got)}   "
              f"field-contradicts-prose {contra}/{len(got)}")


if __name__ == "__main__":
    main()
