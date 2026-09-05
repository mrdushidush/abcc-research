import json, sys, time, urllib.request

BASE = "http://127.0.0.1:1234/v1"

def post(path, payload, stream=False, timeout=900):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    return urllib.request.urlopen(req, timeout=timeout)

def loaded_id():
    with urllib.request.urlopen(BASE + "/models", timeout=30) as r:
        d = json.load(r)
    return [m["id"] for m in d.get("data", [])]

def run(model, prompt, max_tokens, label):
    """Streamed. prefill rate = prompt_tokens/TTFT; decode = completion_tokens/(total-TTFT).
    Liveness is read from usage.completion_tokens, never message.content -- a reasoning
    model puts every token in reasoning_content and content reads empty."""
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "max_tokens": max_tokens, "temperature": 0.0, "stream": True,
               "stream_options": {"include_usage": True}}
    t0 = time.perf_counter(); ttft = None; usage = None; nchunks = 0
    resp = post("/chat/completions", payload, stream=True)
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
        ch = ev.get("choices") or []
        if ch:
            d = ch[0].get("delta") or {}
            if (d.get("content") or d.get("reasoning_content")) and ttft is None:
                ttft = time.perf_counter() - t0
            if d.get("content") or d.get("reasoning_content"):
                nchunks += 1
    total = time.perf_counter() - t0
    pt = (usage or {}).get("prompt_tokens", 0)
    ct = (usage or {}).get("completion_tokens", 0)
    out = {"label": label, "model": model, "prompt_tokens": pt, "completion_tokens": ct,
           "ttft_s": round(ttft, 3) if ttft else None, "total_s": round(total, 3),
           "chunks": nchunks}
    if ttft and pt:
        out["prefill_tok_s"] = round(pt / ttft, 1)
    if ttft and ct and total > ttft:
        out["decode_tok_s"] = round(ct / (total - ttft), 2)
    return out

if __name__ == "__main__":
    model = sys.argv[1]; label = sys.argv[2]
    words = int(sys.argv[3]) if len(sys.argv) > 3 else 5200
    maxtok = int(sys.argv[4]) if len(sys.argv) > 4 else 200
    # A deterministic, cache-hostile filler: unique numbered lines so no two
    # arms share a prefix cache state, and the token count is stable per arm.
    filler = "\n".join(
        "line %05d: the quick brown fox jumps over the lazy dog near bank %04d"
        % (i, (i * 7919) % 9973) for i in range(words))
    prompt = ("Below is a log. Do not summarise it. Answer only the final question.\n\n"
              + filler + "\n\nQuestion: reply with exactly the word ACKNOWLEDGED and nothing else.")
    print(json.dumps(run(model, prompt, maxtok, label), indent=2))
