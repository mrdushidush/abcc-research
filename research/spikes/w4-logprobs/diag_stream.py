"""W4 item 4, step 0d: does the signal survive the shape the SUBJECT actually uses?

Everything measured so far was a non-streaming, tool-free call, and that is not
what the worker sends.  `api.rs:773-784` shows claudette's real body:
`stream: true`, `stream_options.include_usage`, a `tools` array, temperature 0.0.
Three things have to hold before a recording proxy is worth building:

  1. `logprobs` come back in SSE DELTAS, not only in a whole response.
  2. `speculative.n_max: 0` is still honoured on the streaming path, i.e. the
     deltas carry a real distribution and not MTP's p = 1.0 sentinel.
  3. The bare server still emits TOOL CALLS.  The subject's runs all went through
     LM Studio's proxy (`runmeta.json: endpoint http://localhost:1234`); if the
     bare server's tool handling differs, pointing the subject at it changes the
     agent loop and not just the telemetry.

If any of the three fails the population has to be generated some other way.
"""
import json
import os
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BARE = "http://127.0.0.1:64703/v1/chat/completions"
BARE_KEY = "zNKTod22FwP7bKCQPnoJc6Ofil9HM-8tmQGKZBBrmiM"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"

TOOLS = [{"type": "function",
          "function": {"name": "read_file",
                       "description": "Read a file from the workspace.",
                       "parameters": {"type": "object",
                                      "properties": {"path": {"type": "string"}},
                                      "required": ["path"]}}}]


def stream(body, attempts=3):
    for i in range(attempts):
        try:
            return _stream(body)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:200]
            if i == attempts - 1:
                return {"error": "HTTP %s: %s" % (e.code, detail), "chunks": None,
                        "n_logprob_entries": None, "exact_zero": None,
                        "with_alts": None, "finish": None, "tool_calls": None}
            time.sleep(2.0)


def _stream(body):
    req = urllib.request.Request(
        BARE, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + BARE_KEY})
    t0 = time.perf_counter()
    chunks, lps, tool_names, content, usage, finish = 0, [], [], [], None, None
    with urllib.request.urlopen(req, timeout=900) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                obj = json.loads(payload)
            except ValueError:
                continue
            chunks += 1
            if obj.get("usage"):
                usage = obj["usage"]
            for ch in obj.get("choices") or []:
                if ch.get("finish_reason"):
                    finish = ch["finish_reason"]
                d = ch.get("delta") or {}
                if d.get("content"):
                    content.append(d["content"])
                for tc in d.get("tool_calls") or []:
                    fn = (tc.get("function") or {}).get("name")
                    if fn:
                        tool_names.append(fn)
                lp = ch.get("logprobs")
                if lp and lp.get("content"):
                    for e in lp["content"]:
                        lps.append((e.get("token"), e.get("logprob"),
                                    len(e.get("top_logprobs") or [])))
    secs = time.perf_counter() - t0
    n = len(lps)
    exact0 = sum(1 for _, v, _ in lps if v == 0.0)
    withalts = sum(1 for _, _, a in lps if a)
    return {"chunks": chunks, "n_logprob_entries": n,
            "exact_zero": "%d/%d" % (exact0, n) if n else "0/0",
            "with_alts": "%d/%d" % (withalts, n) if n else "0/0",
            "mean_lp": round(sum(v for _, v, _ in lps) / n, 5) if n else None,
            "completion_tokens": (usage or {}).get("completion_tokens"),
            "finish": finish, "tool_calls": tool_names,
            "content_chars": len("".join(content)), "secs": round(secs, 2)}


def body(prompt, tools, logprobs, spec_off):
    b = {"model": MODEL, "messages": [{"role": "user", "content": prompt}],
         "stream": True, "stream_options": {"include_usage": True},
         "temperature": 0.0, "max_tokens": 400}
    if tools:
        b["tools"] = TOOLS
    if logprobs:
        b["logprobs"] = True
        b["top_logprobs"] = 5
    if spec_off:
        b["speculative.n_max"] = 0
    return b


CODE = ("Write a Python function `split_bill(total, people)` returning the "
        "per-person share rounded to 2 decimals. Return only the code. /no_think")
TOOLY = ("Read the file `src/main.py` and tell me what it does. Use the "
         "read_file tool. /no_think")

if __name__ == "__main__":
    rows = []
    for name, prompt, tools, lp, so in (
            ("stream/notools/lp/spec_off", CODE, False, True, True),
            ("stream/notools/lp/spec_on", CODE, False, True, False),
            ("stream/tools/lp/spec_off", TOOLY, True, True, True),
            ("stream/tools/nolp/spec_off", TOOLY, True, False, True),
            ("stream/tools/lp/spec_on", TOOLY, True, True, False)):
        r = stream(body(prompt, tools, lp, so))
        r["cell"] = name
        rows.append(r)
        print(json.dumps(r, ensure_ascii=False)[:400], flush=True)
    with open(os.path.join(HERE, "diag_stream.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("\n%-30s %8s %8s %12s %10s %10s %s" %
          ("cell", "chunks", "entries", "exact0", "with_alts", "finish", "tools"))
    for r in rows:
        print("%-30s %8s %8s %12s %10s %10s %s" %
              (r["cell"], r["chunks"], r["n_logprob_entries"], r["exact_zero"],
               r["with_alts"], r["finish"], r["tool_calls"]))
