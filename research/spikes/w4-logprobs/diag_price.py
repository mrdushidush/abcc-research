"""W4 item 4, step 0c: what does reading logprobs COST, and is the restored
array really the target model's distribution?

diag_degenerate.py established that the per-request flat key
`"speculative.n_max": 0` is what restores a real distribution: MTP-accepted
tokens are reported as `logprob 0.0` with no alternatives.  MTP is ON BY DEFAULT
for the champion, so this is not telemetry that rides along for free -- it is a
serving-mode change on every worker call that wants the signal.  Two things have
to be measured before item 4 can design anything:

  1. THE PRICE.  Same prompt, same budget, MTP on vs off, with and without the
     logprobs request.  The prompt is identical in all cells so the prefill is
     cached after the first (W2 F81) and the difference is decode.  If turning
     MTP off costs a large fraction of the worker's wall clock, the confidence
     signal is charged against the very budget F385 says a retry should buy.

  2. THE INSTRUMENT.  At temperature 0.0 the sampler is greedy, so the emitted
     token MUST be the argmax of whatever distribution is being reported.  If
     `top_logprobs[0].token` equals the emitted token on ~every token, the array
     is the model's own distribution.  If it does not, the array is something
     else and no correlation computed from it means anything.
"""
import json
import os
import statistics
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BARE = "http://127.0.0.1:64703/v1/chat/completions"
BARE_KEY = "zNKTod22FwP7bKCQPnoJc6Ofil9HM-8tmQGKZBBrmiM"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"

# long enough that decode dominates and the two modes are separable
PROMPT = ("Write a Python module implementing a small LRU cache class with get, "
          "put, __len__ and eviction, plus docstrings and five unit tests using "
          "unittest. Return only code, no explanation.")
MAX_TOKENS = 600
REPEATS = 3


def call(logprobs, spec_off):
    body = {"model": MODEL, "messages": [{"role": "user", "content": PROMPT}],
            "temperature": 0.0, "max_tokens": MAX_TOKENS,
            "chat_template_kwargs": {"enable_thinking": False}}
    if logprobs:
        body["logprobs"] = True
        body["top_logprobs"] = 5
    if spec_off:
        body["speculative.n_max"] = 0
    req = urllib.request.Request(
        BARE, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + BARE_KEY})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=900) as r:
        raw = json.loads(r.read().decode("utf-8"))
    return raw, time.perf_counter() - t0


def main():
    rows = []
    for spec_off in (False, True):
        for logprobs in (False, True):
            secs, tps, agree, ents_seen, texts = [], [], [0, 0], 0, set()
            for _ in range(REPEATS):
                raw, s = call(logprobs, spec_off)
                ct = raw["usage"]["completion_tokens"]
                secs.append(s)
                tps.append(ct / s)
                texts.add(raw["choices"][0]["message"]["content"] or "")
                ents = ((raw["choices"][0].get("logprobs") or {}).get("content")) or []
                ents_seen += len(ents)
                for e in ents:
                    tl = e.get("top_logprobs") or []
                    if tl:
                        agree[1] += 1
                        if tl[0].get("token") == e.get("token"):
                            agree[0] += 1
            row = {"spec": "off" if spec_off else "default",
                   "logprobs": logprobs,
                   "p50_secs": round(statistics.median(secs), 2),
                   "p50_tok_per_s": round(statistics.median(tps), 2),
                   "entries": ents_seen,
                   "top1_is_emitted": "%d/%d" % (agree[0], agree[1]),
                   "distinct_outputs": len(texts)}
            rows.append(row)
            print(json.dumps(row), flush=True)

    base = [r for r in rows if r["spec"] == "default" and not r["logprobs"]][0]
    print("\n=== price, relative to MTP-on / no logprobs (%s tok/s) ===" %
          base["p50_tok_per_s"])
    print("%-9s %-10s %12s %12s %8s %14s" %
          ("spec", "logprobs", "p50_secs", "tok/s", "ratio", "top1==emit"))
    for r in rows:
        print("%-9s %-10s %12s %12s %8s %14s" %
              (r["spec"], r["logprobs"], r["p50_secs"], r["p50_tok_per_s"],
               round(base["p50_tok_per_s"] / r["p50_tok_per_s"], 2),
               r["top1_is_emitted"]))
    with open(os.path.join(HERE, "diag_price.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main()
