"""Prefill/decode throughput + KV growth probe against LM Studio's OpenAI-compat endpoint.

Sends a prompt of a requested approximate token size, streams the reply, and reports
time-to-first-token, prefill tok/s, decode tok/s and the server's own usage counts.
Deliberately mirrors what Claudette actually sends (api.rs:769-785): stream=true,
stream_options.include_usage, temperature 0.0, max_tokens.
"""

import json
import sys
import time
import urllib.request

BASE = "http://localhost:1234"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen3.6-35b-a3b-mtp@iq3_s"
TARGET_TOKENS = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
MAX_OUT = int(sys.argv[3]) if len(sys.argv) > 3 else 200
LABEL = sys.argv[4] if len(sys.argv) > 4 else "bench"

# Build filler from real source text so the prefill is a realistic token mix,
# not a degenerate repeat that a tokenizer or cache could exploit.
import pathlib

REPO = pathlib.Path(r"D:/dev/ABCC_20_powerd_by_claudette")
chunks = []
for p in sorted(REPO.glob("prestudy/*.md")) + sorted(REPO.glob("research/*.md")):
    try:
        chunks.append(p.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        pass
corpus = "\n\n".join(chunks)
# Claudette's own CHARS_PER_TOKEN is 4, but that is a budgeting SAFETY constant.
# Measured on this corpus against this tokenizer, markdown runs ~3.39 chars/token,
# so sizing at 4 overshoots the window by ~18% and the server rejects the request.
need_chars = int(TARGET_TOKENS * 3.3)
while len(corpus) < need_chars:
    corpus += corpus
filler = corpus[:need_chars]

body = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "You are a terse engineering assistant."},
        {
            "role": "user",
            "content": filler
            + "\n\nIn one short sentence, what is the single most load-bearing "
            "measurement described above?",
        },
    ],
    "stream": True,
    "stream_options": {"include_usage": True},
    "temperature": 0.0,
    "max_tokens": MAX_OUT,
}

req = urllib.request.Request(
    BASE + "/v1/chat/completions",
    data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json"},
)

t0 = time.perf_counter()
ttft = None
n_deltas = 0
usage = None
text = []
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
        if obj.get("error"):
            print("SERVER ERROR: " + json.dumps(obj["error"])[:600], file=sys.stderr)
        if obj.get("usage"):
            usage = obj["usage"]
        for ch in obj.get("choices") or []:
            delta = ch.get("delta") or {}
            # LM Studio streams a reasoning model's trace as `reasoning_content`.
            # TTFT must count the FIRST token of any kind, or a reply that is all
            # reasoning reports no first token at all.
            d = delta.get("content") or delta.get("reasoning_content")
            if d:
                if ttft is None:
                    ttft = time.perf_counter() - t0
                n_deltas += 1
                text.append(d)
t_total = time.perf_counter() - t0

pt = (usage or {}).get("prompt_tokens")
ct = (usage or {}).get("completion_tokens")
decode_s = t_total - (ttft or 0)
out = {
    "label": LABEL,
    "model": MODEL,
    "target_prompt_tokens": TARGET_TOKENS,
    "usage": usage,
    "ttft_s": round(ttft, 3) if ttft else None,
    "total_s": round(t_total, 3),
    "decode_s": round(decode_s, 3),
    "prefill_tok_s": round(pt / ttft, 1) if pt and ttft else None,
    "decode_tok_s": round(ct / decode_s, 2) if ct and decode_s > 0 else None,
    "n_deltas": n_deltas,
    "reply_chars": len("".join(text)),
}
print(json.dumps(out, indent=2))
