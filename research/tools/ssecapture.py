#!/usr/bin/env python3
"""F606 — read the raw SSE beside the log.

The question the fold could not answer: when a tool call is cut at the cap,
do the argument deltas cross the socket at all?

Two arms against the same prompt and the same tool schema, differing only in
`max_tokens`:
  control  a cap the call fits inside -> the call completes
  cut      a cap the call cannot fit  -> finish_reason == "length"

Every SSE line is written to <arm>.sse.jsonl with a millisecond offset from
the request, so "did bytes arrive" and "when" are both answerable afterwards
without re-running anything.
"""
import argparse, json, sys, time
import urllib.request

BASE = "http://127.0.0.1:1234"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"

# abcc's own schema, crates/abcc-engine/src/tools.rs:245.
APPLY_PATCH = {
    "type": "function",
    "function": {
        "name": "apply_patch",
        "description": "Apply a unified diff to the workspace.",
        "parameters": {
            "type": "object",
            "properties": {"diff": {"type": "string"}},
            "required": ["diff"],
            "additionalProperties": False,
        },
    },
}

# One prompt that forces a long `diff` argument. The builders head's shape:
# a task, a tool, and an instruction to use it rather than answer in prose.
SYSTEM = (
    "You are a build agent. You make changes by calling tools, never by "
    "describing them. Do not answer in prose when a tool will do."
)
USER = (
    "Create a new file `metrics.py` holding a complete Python module for a "
    "streaming statistics accumulator. It must implement, with full docstrings "
    "and type hints: a Welford mean/variance accumulator, a P-square quantile "
    "estimator for p50/p90/p95/p99, an exponentially weighted moving average, "
    "a reservoir sampler, a bounded histogram with configurable bucket edges, "
    "and a `Summary` dataclass that renders all of them as an aligned table. "
    "Include a `__main__` block that demonstrates every class on synthetic "
    "data. Write it in one `apply_patch` call as a unified diff creating the "
    "file. Do not abbreviate and do not elide any function body."
)


USER_SMALL = (
    "Create a new file `hello.py` holding a small Python module with a "
    "greet(name) function returning a greeting, and a `__main__` block that "
    "calls it. Write it in one `apply_patch` call as a unified diff creating "
    "the file."
)


def run(arm: str, max_tokens: int, outdir: str) -> dict:
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER_SMALL if arm.startswith("complete") else USER},
        ],
        "tools": [APPLY_PATCH],
        "tool_choice": "auto",
        "stream": True,
        "stream_options": {"include_usage": True},
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    path = f"{outdir}/{arm}.sse.jsonl"
    t0 = time.monotonic()
    lines = 0
    arg_chars = 0          # characters of function.arguments seen ON THE WIRE
    arg_deltas = 0
    first_arg_ms = None
    last_arg_ms = None
    text_chars = 0
    reasoning_chars = 0
    first_byte_ms = None
    finish = None
    usage = None
    names = []
    with open(path, "w", encoding="utf-8") as sink:
        with urllib.request.urlopen(req, timeout=900) as resp:
            for raw in resp:
                now_ms = round((time.monotonic() - t0) * 1000)
                if first_byte_ms is None:
                    first_byte_ms = now_ms
                line = raw.decode("utf-8", "replace").rstrip("\r\n")
                if not line:
                    continue
                lines += 1
                sink.write(json.dumps({"t_ms": now_ms, "line": line}) + "\n")
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    continue
                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    # A chunk we cannot parse is itself a finding; it is on
                    # disk either way.
                    continue
                if chunk.get("usage"):
                    usage = chunk["usage"]
                for choice in chunk.get("choices") or []:
                    delta = choice.get("delta") or {}
                    if delta.get("content"):
                        text_chars += len(delta["content"])
                    if delta.get("reasoning_content"):
                        reasoning_chars += len(delta["reasoning_content"])
                    for frag in delta.get("tool_calls") or []:
                        fn = frag.get("function") or {}
                        if fn.get("name"):
                            names.append(fn["name"])
                        args = fn.get("arguments")
                        if args:
                            arg_deltas += 1
                            arg_chars += len(args)
                            if first_arg_ms is None:
                                first_arg_ms = now_ms
                            last_arg_ms = now_ms
                    if choice.get("finish_reason"):
                        finish = choice["finish_reason"]
    total_ms = round((time.monotonic() - t0) * 1000)
    return {
        "arm": arm,
        "max_tokens": max_tokens,
        "sse_lines": lines,
        "first_byte_ms": first_byte_ms,
        "total_ms": total_ms,
        "finish_reason": finish,
        "usage": usage,
        "tool_names": names,
        "wire_argument_chars": arg_chars,
        "wire_argument_deltas": arg_deltas,
        "first_arg_delta_ms": first_arg_ms,
        "last_arg_delta_ms": last_arg_ms,
        "wire_text_chars": text_chars,
        "wire_reasoning_chars": reasoning_chars,
        "capture": path,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--max-tokens", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    summary = run(a.arm, a.max_tokens, a.out)
    print(json.dumps(summary, indent=2))
    with open(f"{a.out}/{a.arm}.summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
