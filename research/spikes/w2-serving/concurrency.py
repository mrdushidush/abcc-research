"""N parallel builders: per-request latency, aggregate throughput, and the ceiling.

The brief wants "the point where the machine becomes unstable, reported as a hard
limit, not a tuning suggestion". Two separate limits exist and they must not be
conflated:

  - the KV limit: with --kv-unified the slots POOL the context, so the bound is
    sum(active sequence lengths) <= --ctx-size, not ctx/N per slot.
  - the throughput limit: where adding a builder stops buying aggregate tokens/s.

Each worker sends a DISTINCT prompt (different slice of the corpus) so the run
cannot be flattered by prefix-cache hits between workers.
"""

import concurrent.futures as cf
import json
import pathlib
import statistics
import sys
import time
import urllib.request

BASE = "http://localhost:1234"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen3.6-35b-a3b-mtp@iq3_s"
PER_PROMPT = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
MAX_OUT = int(sys.argv[3]) if len(sys.argv) > 3 else 100

REPO = pathlib.Path(r"D:/dev/ABCC_20_powerd_by_claudette")
corpus = "\n\n".join(
    p.read_text(encoding="utf-8", errors="replace")
    for p in sorted(REPO.glob("prestudy/*.md")) + sorted(REPO.glob("research/*.md"))
)
while len(corpus) < PER_PROMPT * 3.3 * 8:
    corpus += corpus
SLICE = int(PER_PROMPT * 3.3)


def one(worker_id):
    # Distinct slice per worker -> no cross-worker prefix sharing.
    text = corpus[worker_id * SLICE : (worker_id + 1) * SLICE]
    body = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": text + f"\n\nIn one sentence, summarise section {worker_id}."}
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
    first, usage = None, None
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
                if obj.get("error"):
                    return {"worker": worker_id, "error": json.dumps(obj["error"])[:200]}
                for ch in obj.get("choices") or []:
                    d = ch.get("delta") or {}
                    if (d.get("content") or d.get("reasoning_content")) and first is None:
                        first = time.perf_counter() - t0
    except Exception as e:  # noqa: BLE001 - a failed worker IS the result at the ceiling
        return {"worker": worker_id, "error": f"{type(e).__name__}: {e}"}
    total = time.perf_counter() - t0
    return {
        "worker": worker_id,
        "ttft_s": round(first, 3) if first else None,
        "total_s": round(total, 3),
        "prompt_tokens": (usage or {}).get("prompt_tokens"),
        "completion_tokens": (usage or {}).get("completion_tokens"),
    }


for n in (1, 2, 4, 6):
    t0 = time.perf_counter()
    with cf.ThreadPoolExecutor(max_workers=n) as ex:
        res = list(ex.map(one, range(n)))
    wall = time.perf_counter() - t0
    errs = [r for r in res if r.get("error")]
    ok = [r for r in res if not r.get("error")]
    ttfts = [r["ttft_s"] for r in ok if r.get("ttft_s")]
    ptoks = sum(r.get("prompt_tokens") or 0 for r in ok)
    ctoks = sum(r.get("completion_tokens") or 0 for r in ok)
    print(
        f"N={n}  wall {wall:6.2f}s  ok {len(ok)}/{n}  "
        f"ttft med {statistics.median(ttfts) if ttfts else float('nan'):6.2f}s  "
        f"max {max(ttfts) if ttfts else float('nan'):6.2f}s  "
        f"prompt_tok {ptoks}  agg_prefill {ptoks/wall:7.1f} tok/s  "
        f"agg_decode {ctoks/wall:6.1f} tok/s",
        flush=True,
    )
    for e in errs:
        print(f"    worker {e['worker']} FAILED: {e['error']}", flush=True)
