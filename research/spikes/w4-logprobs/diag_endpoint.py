"""W4 item 4, step 0e: the two endpoints do not produce the same GENERATION.

The attribution probe ruled out both forced changes as the cause of the runaway
turns.  Same five tasks, same session, same server process, streaming off in
both arms, MTP the only variable: identical outcomes (fail/pass/pass/timeout/
timeout).  And streaming cannot be the cause either -- `api.rs:883` shows the
non-streaming parser emits the same `StreamMeta { finish_reason,
reasoning_chars }` the SSE path does, so the empty-turn retry sees the same
inputs; and the harness deadline is the whole CELL's, not an idle watchdog
(`driver.rs:456`), so a silent generation is not penalised for being silent.

What is left is the endpoint itself, and the control run says so directly: the
same five tasks on `:1234` -- the recorded configuration -- come back
fail/pass/pass/**pass**/**pass**, no timeouts, where the bare server timed Q43
and Q49 out in both arms.

This asks the mechanism question with one variable: an identical
non-streaming, tool-carrying, temperature-0 request to each hop, no
`chat_template_kwargs` (claudette sends none), repeated.  If the bare server
generates a systematically longer reasoning trace for the same prompt, then the
hop is changing the sampler or the template -- and F377 already showed the proxy
manages the template itself, since it discards the client's kwargs.

That matters beyond item 4: every recorded number in this project was produced
through `:1234`, and the bare server is where item 3 sent its cheap calls.
"""
import json
import os
import statistics
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROXY = "http://localhost:1234/v1/chat/completions"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"
REPEATS = 3
MAX_TOKENS = 8192          # claudette's num_predict in every recorded run

TOOLS = [{"type": "function",
          "function": {"name": "read_file", "description": "Read a file.",
                       "parameters": {"type": "object",
                                      "properties": {"path": {"type": "string"}},
                                      "required": ["path"]}}},
         {"type": "function",
          "function": {"name": "apply_diff", "description": "Apply a unified diff.",
                       "parameters": {"type": "object",
                                      "properties": {"diff": {"type": "string"}},
                                      "required": ["diff"]}}}]

# The shape that ran away: a real refactor ask with an ambiguity in it, which is
# what sends this model into a long deliberation.
PROMPT = ("In a Python module there is a function `summarise(rows, key=None, "
          "reverse=False)` that sorts rows by `key`, groups them, and returns "
          "per-group totals. Users report that when `key` is None the ordering "
          "is non-deterministic across runs, and that `reverse=True` sometimes "
          "reverses the groups but not the rows inside them. Decide what the "
          "correct behaviour should be, justify it, and give the fix.")


def discover_bare():
    import subprocess
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-CimInstance Win32_Process -Filter \"Name='llama-server.exe'\")"
         ".CommandLine"],
        capture_output=True, text=True, timeout=60).stdout
    parts = out.split()
    port = key = None
    for i, p in enumerate(parts):
        if p == "--port" and i + 1 < len(parts):
            port = int(parts[i + 1])
        elif p == "--api-key" and i + 1 < len(parts):
            key = parts[i + 1]
    return port, key


def call(url, key):
    body = {"model": MODEL, "messages": [{"role": "user", "content": PROMPT}],
            "tools": TOOLS, "temperature": 0.0, "max_tokens": MAX_TOKENS}
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers=headers)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            raw = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": "HTTP %s: %s" % (e.code, e.read()[:200])}
    ch = raw["choices"][0]
    msg = ch.get("message") or {}
    return {"secs": round(time.perf_counter() - t0, 2),
            "completion_tokens": raw.get("usage", {}).get("completion_tokens"),
            "finish": ch.get("finish_reason"),
            "reasoning_chars": len(msg.get("reasoning_content") or ""),
            "content_chars": len(msg.get("content") or ""),
            "tool_calls": len(msg.get("tool_calls") or [])}


def main():
    port, key = discover_bare()
    bare = "http://127.0.0.1:%d/v1/chat/completions" % port
    rows = []
    for name, url, k in (("bare", bare, key), ("proxy", PROXY, None)):
        for i in range(REPEATS):
            r = call(url, k)
            r["hop"] = name
            r["rep"] = i
            rows.append(r)
            print(json.dumps(r), flush=True)
    with open(os.path.join(HERE, "diag_endpoint.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    print("\n%-7s %14s %14s %14s %10s" %
          ("hop", "p50 tokens", "p50 reason ch", "p50 secs", "finishes"))
    for name in ("bare", "proxy"):
        g = [r for r in rows if r.get("hop") == name and "error" not in r]
        if not g:
            continue
        print("%-7s %14s %14s %14s %10s" %
              (name,
               statistics.median(r["completion_tokens"] for r in g),
               statistics.median(r["reasoning_chars"] for r in g),
               statistics.median(r["secs"] for r in g),
               ",".join(sorted({r["finish"] for r in g}))))


if __name__ == "__main__":
    main()
