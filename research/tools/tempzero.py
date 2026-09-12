#!/usr/bin/env python3
"""Is `temperature: 0` repeatable on this stack, and does a seed add anything?

The K-series question, and it is not the one the queue had written down. The
subject those cells were flown with (`claudette`, `api.rs`) sends
`temperature: 0.0`, `max_tokens`, `stream` and **no seed and no top_p** — so
the arms were never at the server's own sampling, they were greedy. A seed is
inert under greedy decoding *in the sampler*; whether the ANSWERS repeat is a
property of the whole stack (MTP draft acceptance, batching, GPU float
associativity) and only a measurement settles it.

Three arms, and the third is the negative control that stops the other two
being a story about a blind instrument:

  A  temperature 0, no seed     exactly what the K-series subject sends
  B  temperature 0, seed pinned does a seed change anything at all at temp 0
  C  temperature 0.8, no seed   the instrument MUST see several answers here

🚨 Read BOTH `content` and `reasoning_content`. This model puts a short
answer's every token in `reasoning_content` and leaves `content` empty, and a
probe that hashed `content` alone compared five empty strings and printed
`1 distinct of 5` under the heading it was meant to falsify.

⚠ Run it when nothing else holds the GPU: LM Studio is loaded `--parallel 1`,
so a second caller queues behind it.

    python tempzero.py qwen3.6-35b-a3b-mtp@iq3_s
"""

import hashlib
import json
import sys
import time
import urllib.request

# The console here is cp1252; a probe must not die on its own warning line.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:1234/v1"

PROMPT = (
    "In one line of Rust, and with no explanation, give the expression that "
    "returns the median of a `&mut Vec<u64>` you may sort in place."
)


def call(model, temperature, seed, max_tokens=400, timeout=900):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if seed is not None:
        payload["seed"] = seed
    req = urllib.request.Request(
        BASE + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    content, reasoning, usage = [], [], None
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            body = line[5:].strip()
            if body == "[DONE]":
                break
            try:
                ev = json.loads(body)
            except Exception:
                continue
            if ev.get("usage"):
                usage = ev["usage"]
            for ch in ev.get("choices") or []:
                d = ch.get("delta") or {}
                if d.get("content"):
                    content.append(d["content"])
                if d.get("reasoning_content"):
                    reasoning.append(d["reasoning_content"])
    c, r = "".join(content), "".join(reasoning)
    return {
        "content": c,
        "reasoning": r,
        "content_chars": len(c),
        "reasoning_chars": len(r),
        # Hashed over BOTH halves, because either one alone can be empty.
        "digest": hashlib.sha256((c + "\x00" + r).encode()).hexdigest()[:12],
        "completion_tokens": (usage or {}).get("completion_tokens", 0),
        "wall_s": round(time.perf_counter() - t0, 2),
    }


def arm(model, label, temperature, seed, n):
    rows = [call(model, temperature, seed) for _ in range(n)]
    digests = [row["digest"] for row in rows]
    distinct = len(set(digests))
    print(f"\n{label}  temperature={temperature} seed={seed}")
    for k, row in enumerate(rows):
        print(
            f"  {k + 1}  {row['digest']}  content {row['content_chars']:>5} ch  "
            f"reasoning {row['reasoning_chars']:>6} ch  "
            f"{row['completion_tokens']:>4} tok  {row['wall_s']:>6.2f} s"
        )
    if all(row["content_chars"] == 0 for row in rows):
        print("  🚨 every `content` was EMPTY — the digest is carrying `reasoning` alone")
    print(f"  -> {distinct} distinct of {len(rows)}")
    return distinct, rows


if __name__ == "__main__":
    model = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    print(f"model {model}, n={n} per arm, prompt {len(PROMPT)} chars")
    a, _ = arm(model, "A  what the K-series subject sends", 0.0, None, n)
    b, _ = arm(model, "B  the same, with a seed", 0.0, 424242, n)
    c, rows = arm(model, "C  the control — this one MUST vary", 0.8, None, n)
    print("\nverdict")
    print(f"  temp 0, no seed   {a} distinct of {n}")
    print(f"  temp 0, seeded    {b} distinct of {n}")
    print(f"  temp 0.8 control  {c} distinct of {n}")
    if c == 1:
        print("  🚨 THE CONTROL DID NOT VARY — the instrument cannot see a difference,")
        print("     so arms A and B say nothing. Do not quote them.")
    if len(sys.argv) > 3:
        with open(sys.argv[3], "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=1)
