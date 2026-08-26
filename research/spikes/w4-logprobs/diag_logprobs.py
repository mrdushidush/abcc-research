"""W4 item 4, step 0: does `logprobs` survive each hop, and is it usable?

OQ-W4-15.  Item 3's F377 proved LM Studio's proxy silently DROPS a request field
it does not understand (`chat_template_kwargs`) and returns HTTP 200 with no
warning.  `logprobs` / `top_logprobs` are OpenAI fields that bare `llama-server`
supports and that NOBODY has tested through the proxy.  Item 4's whole population
depends on the answer, so it is measured before anything is designed.

The grid, one change at a time:

    {endpoint: bare :64703, proxy :1234}
  x {logprobs: absent, true+top_logprobs 5}
  x {response_format: none (free text), json_schema (constrained)}

What it has to establish:
  1. Does the field come back at all on each hop?  A dropped field here looks
     exactly like a model with no confidence signal.
  2. Is the array COMPLETE -- one entry per completion token -- or truncated?
  3. Does the top-1 entry match the token actually emitted?  Under MTP
     speculative decoding the drafted tokens are verified by the target model;
     if the returned logprob is the DRAFT's, the signal is a fact about the
     draft head, not about the worker.
  4. Does a constrained grammar change what is reported?  A json_schema masks
     the logits before sampling, so a "confident" token may only be confident
     because the grammar left one legal continuation -- which would make the
     signal a fact about the SCHEMA (item 3's F378 shape, one layer down).
  5. What does asking for it cost?
"""
import json
import math
import os
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROXY = "http://localhost:1234/v1/chat/completions"
BARE = "http://127.0.0.1:64703/v1/chat/completions"
BARE_KEY = "zNKTod22FwP7bKCQPnoJc6Ofil9HM-8tmQGKZBBrmiM"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"

PROMPT = ("Write a Python function `split_bill(total, people)` that returns the "
          "per-person share as a float, rounded to 2 decimals. Return only the code.")

FMT = {"type": "json_schema",
       "json_schema": {"name": "patch", "strict": True,
                       "schema": {"type": "object",
                                  "properties": {"code": {"type": "string"}},
                                  "required": ["code"],
                                  "additionalProperties": False}}}


def call(url, key, logprobs, fmt, max_tokens=200):
    body = {"model": MODEL,
            "messages": [{"role": "user", "content": PROMPT}],
            "temperature": 0.0, "max_tokens": max_tokens,
            "chat_template_kwargs": {"enable_thinking": False}}
    if logprobs:
        body["logprobs"] = True
        body["top_logprobs"] = 5
    if fmt:
        body["response_format"] = FMT
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers=headers)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            raw = json.loads(r.read().decode("utf-8"))
        return raw, time.perf_counter() - t0, None
    except urllib.error.HTTPError as e:
        return None, time.perf_counter() - t0, "HTTP %s: %s" % (e.code, e.read()[:400])
    except Exception as e:  # noqa: BLE001
        return None, time.perf_counter() - t0, repr(e)


def describe(raw):
    """Everything item 4 needs to know about one response's logprobs block."""
    ch = raw["choices"][0]
    usage = raw.get("usage", {})
    lp = ch.get("logprobs")
    out = {"finish": ch.get("finish_reason"),
           "completion_tokens": usage.get("completion_tokens"),
           "content_chars": len(ch["message"].get("content") or ""),
           "logprobs_present": lp is not None,
           "n_entries": None, "top_n": None, "top1_is_emitted": None,
           "mean_lp": None, "min_lp": None, "n_below_ln0_5": None,
           "sample": None}
    if not lp:
        return out
    ents = lp.get("content") or []
    out["n_entries"] = len(ents)
    if not ents:
        return out
    tops = [len(e.get("top_logprobs") or []) for e in ents]
    out["top_n"] = (min(tops), max(tops))
    agree = 0
    for e in ents:
        tl = e.get("top_logprobs") or []
        if tl and tl[0].get("token") == e.get("token"):
            agree += 1
    out["top1_is_emitted"] = "%d/%d" % (agree, len(ents))
    vals = [e["logprob"] for e in ents if e.get("logprob") is not None]
    if vals:
        out["mean_lp"] = round(sum(vals) / len(vals), 4)
        out["min_lp"] = round(min(vals), 4)
        out["n_below_ln0_5"] = sum(1 for v in vals if v < math.log(0.5))
    out["sample"] = [{"tok": e.get("token"), "lp": round(e.get("logprob", 0.0), 3),
                      "alts": [(t.get("token"), round(t.get("logprob", 0.0), 2))
                               for t in (e.get("top_logprobs") or [])[:3]]}
                     for e in ents[:6]]
    return out


def main():
    rows = []
    for ep_name, url, key in (("bare", BARE, BARE_KEY), ("proxy", PROXY, None)):
        for lp_req in (False, True):
            for fmt_name, fmt in (("free", None), ("schema", FMT)):
                raw, secs, err = call(url, key, lp_req, fmt)
                row = {"endpoint": ep_name, "logprobs_requested": lp_req,
                       "format": fmt_name, "secs": round(secs, 2), "error": err}
                if raw:
                    row.update(describe(raw))
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False)[:700], flush=True)
    with open(os.path.join(HERE, "diag_logprobs.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("\n=== grid ===")
    print("%-6s %-8s %-7s %8s %6s %8s %10s %12s" %
          ("hop", "asked", "format", "present", "n_ent", "tokens", "top1==emit", "mean_lp"))
    for r in rows:
        print("%-6s %-8s %-7s %8s %6s %8s %10s %12s" %
              (r["endpoint"], r["logprobs_requested"], r["format"],
               r.get("logprobs_present"), r.get("n_entries"),
               r.get("completion_tokens"), r.get("top1_is_emitted"),
               r.get("mean_lp")))


if __name__ == "__main__":
    main()
