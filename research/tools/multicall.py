#!/usr/bin/env python3
"""F637 — is the markup the model's, or the server's parser?

The open question from DEBUG P2 §8. Thirty-two of forty-six refused
`apply_patch` payloads carry literal `<tool_call>` / `<function=` /
`<parameter=` text inside the `diff` argument, several attempted calls
concatenated with the model's prose between them. Two explanations fit:

  A. the model emits ONE call whose argument really does contain all that
  B. the model emits SEVERAL `<tool_call>` blocks in one turn, and LM Studio's
     parser takes the first function name and everything after it as one
     argument

They are distinguishable on the wire, and only on the wire — the log records
what abcc was handed, which is the same under both.

What to look at in the output:
  * `delta.content` carrying `<tool_call>` text  -> the server did NOT parse it
    as a call, so the markup reaching an argument means the model wrote it
    inside one (A)
  * several `tool_calls` entries with distinct `index` values -> the server
    parsed them apart, so concatenation is not what happens (against B)
  * ONE `tool_calls` entry whose argument contains `<tool_call>` -> B, and the
    parser is the place to fix it

⚠ Run it when nothing else holds the GPU: LM Studio is loaded `--parallel 1`,
so a second caller queues behind a sortie and both timings become meaningless.

    python multicall.py --out ../spikes/f637-multicall
"""
import argparse
import json
import time
import urllib.request

BASE = "http://127.0.0.1:1234"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"

# abcc's own two write tools, so the turn has a real choice to make.
TOOLS = [
    {
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
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write a whole file into the workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
]

SYSTEM = (
    "You are a build agent. You make changes by calling tools, never by "
    "describing them. Do not answer in prose when a tool will do."
)

# 🚨 The shape that produced the failure in the field: several small edits across
# several files, which is what invites more than one call in one turn.
USER = (
    "Make these three edits with apply_patch, as unified diffs.\n\n"
    "1. In `a.rs`, which contains exactly:\n"
    "pub fn one() -> u32 { 1 }\n"
    "change the body to return 2.\n\n"
    "2. In `b.rs`, which contains exactly:\n"
    "pub fn two() -> u32 { 2 }\n"
    "change the body to return 3.\n\n"
    "3. In `c.rs`, which contains exactly:\n"
    "pub fn three() -> u32 { 3 }\n"
    "change the body to return 4."
)


def run(out_dir: str, max_tokens: int) -> dict:
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER},
        ],
        "tools": TOOLS,
        "tool_choice": "auto",
        "stream": True,
        "stream_options": {"include_usage": True},
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        f"{BASE}/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )

    path = f"{out_dir}/multicall.sse.jsonl"
    t0 = time.monotonic()
    calls, content_markup, indices, lines = [], 0, set(), 0
    with urllib.request.urlopen(req) as r, open(path, "w", encoding="utf-8") as cap:
        for raw in r:
            line = raw.decode("utf-8", "replace").rstrip("\n")
            if not line:
                continue
            lines += 1
            cap.write(json.dumps({"t_ms": round((time.monotonic() - t0) * 1000), "line": line}) + "\n")
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            try:
                payload = json.loads(line[6:])
            except json.JSONDecodeError:
                continue
            for choice in payload.get("choices") or []:
                delta = choice.get("delta") or {}
                if "<tool_call>" in (delta.get("content") or ""):
                    content_markup += 1
                for c in delta.get("tool_calls") or []:
                    indices.add(c.get("index"))
                    fn = c.get("function") or {}
                    if fn.get("name"):
                        calls.append({"index": c.get("index"), "name": fn["name"], "args": ""})
                    if fn.get("arguments") and calls:
                        calls[-1]["args"] += fn["arguments"]

    markup_in_args = sum(
        1 for c in calls if any(m in c["args"] for m in ("<tool_call>", "<function=", "<parameter="))
    )
    summary = {
        "sse_lines": lines,
        "total_ms": round((time.monotonic() - t0) * 1000),
        "calls_parsed": len(calls),
        "distinct_indices": sorted(i for i in indices if i is not None),
        "content_chunks_carrying_tool_call_markup": content_markup,
        "parsed_calls_whose_ARGUMENT_carries_markup": markup_in_args,
        "call_names": [c["name"] for c in calls],
        "argument_chars": [len(c["args"]) for c in calls],
        "capture": path,
        "verdict": (
            "B: one call swallowed the rest -> the server's parser"
            if markup_in_args
            else "A or neither: no parsed argument carries markup in this turn"
        ),
    }
    with open(f"{out_dir}/multicall.summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-tokens", type=int, default=16384)
    a = ap.parse_args()
    print(json.dumps(run(a.out, a.max_tokens), indent=2))
