"""How many distinct per-phase prompt heads does the server hold at once?

phases.py step 4 was the surprise: after head B had displaced head A on a
`--parallel 1` server, going BACK to head A was warm (2.770 s against a 10.944 s
cold). A single slot cannot hold two 17k prefixes, and the llama-server command
line carries no `--cache-ram` / `--slot-save-path` flag -- so this is a DEFAULT of
the backend (llama.cpp b2.27.1), restoring evicted prompt states from host RAM.

That default decides W11 item 2's central design question. If it holds one state,
per-phase heads cost a cold prefill on every transition. If it holds many, they
cost one cold prefill EACH, once per session, and alternation afterwards is warm.

Pass 1 sends N distinct heads over the same body -- every one should be cold.
Pass 2 sends the same N in the same order -- whichever come back warm are the ones
the cache still holds, and the first cold one in pass 2 is the eviction boundary.
"""

import json
import time
import urllib.request
import pathlib
import sys

BASE = "http://localhost:1234"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"
TARGET = 18000
N = int(sys.argv[1]) if len(sys.argv) > 1 else 6

REPO = pathlib.Path(r"D:/dev/ABCC_20_powerd_by_claudette")
corpus = "\n\n".join(
    p.read_text(encoding="utf-8", errors="replace")
    for p in sorted(REPO.glob("prestudy/*.md")) + sorted(REPO.glob("research/*.md"))
)
while len(corpus) < TARGET * 3.3:
    corpus += corpus
BODY = corpus[: int(TARGET * 3.3)]

ROLES = ["Recon", "Builders", "Commandos", "Engineering", "Sentinel", "Quartermaster",
         "Signals", "Sappers", "Artillery", "Scouts", "Medics", "Logistics"]


def head(i):
    role = ROLES[i % len(ROLES)]
    tools = [
        {"name": f"{role.lower()}_read", "description": f"Read a file as {role}.",
         "parameters": {"path": "string", "start_line": "integer"}},
        {"name": f"{role.lower()}_search", "description": f"Search as {role}.",
         "parameters": {"pattern": "string", "glob": "string"}},
        {"name": f"{role.lower()}_act", "description": f"Act as {role}.",
         "parameters": {"target": "string", "argument": "string"}},
    ]
    return (f"You are {role}, unit {i} of the ABCC 2.0 attempt pipeline.\n"
            f"Available tools:\n{json.dumps(tools, indent=1)}\n"
            "Use only the tools listed.\n\n")


def ttft(label, system, user, max_tokens=32):
    body = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "stream": True, "stream_options": {"include_usage": True},
        "temperature": 0.0, "max_tokens": max_tokens,
    }
    req = urllib.request.Request(BASE + "/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
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
    print(f"{label:<26} ttft {first:7.3f}s   prompt_tokens {pt:>6}", flush=True)
    return first


QUESTION = "Name the single most load-bearing measurement in the material above."

print(f"{N} distinct heads over one ~{TARGET}-token body, model {MODEL}\n")
print("-- pass 1: first sight of each head --")
p1 = [ttft(f"H{i} {ROLES[i % len(ROLES)]}", head(i) + BODY, QUESTION) for i in range(N)]
print("\n-- pass 2: same heads, same order --")
p2 = [ttft(f"H{i} {ROLES[i % len(ROLES)]}", head(i) + BODY, QUESTION) for i in range(N)]

print()
cold = sum(p1) / len(p1)
print(f"pass 1 mean (cold)  {cold:6.3f}s")
warm = [i for i, t in enumerate(p2) if t < cold * 0.5]
print(f"pass 2 warm heads   {warm}")
print(f"pass 2 cold heads   {[i for i, t in enumerate(p2) if t >= cold * 0.5]}")
for i, (a, b) in enumerate(zip(p1, p2)):
    print(f"  H{i}: {a:6.3f}s -> {b:6.3f}s  ({b/a:5.2f}x)")
