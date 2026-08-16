"""Prefix caching, and what a mutable ToolRegistry costs.

The brief (W2) says four builders sharing a system prompt is the best case for
prefix caching and the worst case for on-demand tool groups, because Claudette's
`ToolRegistry` is mutable per turn (api.rs:169 ToolsProvider::Dynamic, read fresh
on every request at :740). The measured workload is 27.8:1 prefill:decode, so the
question is worth a number rather than an argument.

Four requests, same long prefix, measured by time-to-first-token:

  A  cold      first sight of the prefix
  B  reuse     identical prefix, different question       -> should hit
  C  head-edit ONE token changed at the FRONT of the prefix -> models a changed
                tools array, which the chat template renders before the messages
  D  tail-edit one token changed at the END of the prefix   -> models a changed
                last user message, the benign case

If C costs the same as A, the tool registry invalidates everything and the
on-demand tool-group design is paying full prefill on every change.
"""

import json
import sys
import time
import urllib.request
import pathlib

BASE = "http://localhost:1234"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen3.6-35b-a3b-mtp@iq3_s"
TARGET = int(sys.argv[2]) if len(sys.argv) > 2 else 20000

REPO = pathlib.Path(r"D:/dev/ABCC_20_powerd_by_claudette")
corpus = "\n\n".join(
    p.read_text(encoding="utf-8", errors="replace")
    for p in sorted(REPO.glob("prestudy/*.md")) + sorted(REPO.glob("research/*.md"))
)
while len(corpus) < TARGET * 3.3:
    corpus += corpus
PREFIX = corpus[: int(TARGET * 3.3)]


def ttft(label, system, question, max_tokens=40):
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ],
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    first = None
    usage = None
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
    pt = (usage or {}).get("prompt_tokens")
    rate = round(pt / first, 1) if pt and first else None
    print(f"{label:<28} ttft {first:7.3f}s   prompt_tokens {pt}   apparent prefill {rate} tok/s",
          flush=True)
    return first


print(f"prefix ~{TARGET} tokens, model {MODEL}\n")
a = ttft("A cold", PREFIX, "Name the single most load-bearing measurement above.")
b = ttft("B reuse (same prefix)", PREFIX, "Now name the second most load-bearing one.")
c = ttft("C head-edit (tools change)", "X " + PREFIX, "Now name the second most load-bearing one.")
d = ttft("D tail-edit (message change)", PREFIX + " X", "Now name the second most load-bearing one.")
b2 = ttft("B2 reuse again", PREFIX, "And the third most load-bearing one.")

print()
print(f"reuse saves        {a - b:6.3f}s vs cold  ({(1 - b/a)*100:5.1f}% faster)")
print(f"head-edit costs    {c - b:6.3f}s vs reuse ({c/b:5.2f}x)   -- the ToolRegistry case")
print(f"tail-edit costs    {d - b:6.3f}s vs reuse ({d/b:5.2f}x)")
print(f"head-edit vs cold  {c - a:6.3f}s          ({c/a:5.2f}x)")
