"""W4 item 4, step 0b: WHY is every token after the first reported as certain?

diag_logprobs.py got a complete array back from the bare server (24 entries for
24 completion tokens) and it is nearly useless: entry 0 carries `logprob -0.024`
and five alternatives, and entries 1..n carry `logprob 0.0` (probability 1.0)
with an EMPTY `top_logprobs` list.  A signal that says "certain" on every token
is not a confidence signal.

Two candidate causes, and they have different consequences for 2.0:

  (a) THE SAMPLER.  llama.cpp reports post-sampler-chain probabilities.  At
      `temperature 0.0` the chain is greedy, the distribution collapses to a
      delta on the argmax, and every token is p = 1.0 by construction.  If this
      is it, the signal exists but is destroyed by the sampler claudette
      actually sends (`api.rs:783`, temperature 0.0) -- so reading it costs a
      sampler change, which changes the worker's OUTPUT, not just its telemetry.

  (b) MTP.  Under speculative decoding the draft head proposes and the target
      verifies; if the server reports the accepted draft tokens without their
      target-model distribution, the number is a fact about acceptance, not
      about the worker.  MTP is ON BY DEFAULT for this model, so this would make
      the signal unavailable in the deployed configuration.

The grid separates them: {temperature 0.0, 0.7} x {spec left alone, spec off via
the per-request `speculative.n_max: 0`}.  If (a), temperature moves it.  If (b),
`n_max` moves it.  If both matter they are separable here and nowhere else.

Also re-runs the PROXY hop with a budget big enough to finish, because in
diag_logprobs.py all four proxy cells stopped at `length` with empty content --
F377's dropped `chat_template_kwargs` -- which confounds "the proxy dropped
logprobs" with "the response never got to the content".
"""
import json
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


def call(url, key, extra, max_tokens=200, nothink=True):
    body = {"model": MODEL, "messages": [{"role": "user", "content": PROMPT}],
            "temperature": 0.0, "max_tokens": max_tokens,
            "logprobs": True, "top_logprobs": 5}
    if nothink:
        body["chat_template_kwargs"] = {"enable_thinking": False}
    body.update(extra)
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers=headers)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            return json.loads(r.read().decode("utf-8")), time.perf_counter() - t0, None
    except urllib.error.HTTPError as e:
        return None, time.perf_counter() - t0, "HTTP %s: %s" % (e.code, e.read()[:300])
    except Exception as e:  # noqa: BLE001
        return None, time.perf_counter() - t0, repr(e)


def stats(raw):
    ch = raw["choices"][0]
    ents = ((ch.get("logprobs") or {}).get("content")) or []
    n = len(ents)
    if not n:
        return {"n": 0, "finish": ch.get("finish_reason"),
                "tokens": raw.get("usage", {}).get("completion_tokens"),
                "chars": len(ch["message"].get("content") or "")}
    exact0 = sum(1 for e in ents if e.get("logprob") == 0.0)
    withalts = sum(1 for e in ents if (e.get("top_logprobs") or []))
    vals = [e["logprob"] for e in ents]
    return {"n": n, "finish": ch.get("finish_reason"),
            "tokens": raw.get("usage", {}).get("completion_tokens"),
            "chars": len(ch["message"].get("content") or ""),
            "exact_zero": "%d/%d" % (exact0, n),
            "with_alts": "%d/%d" % (withalts, n),
            "mean_lp": round(sum(vals) / n, 5), "min_lp": round(min(vals), 4),
            "sample": [{"tok": e["token"], "lp": round(e["logprob"], 3),
                        "nalt": len(e.get("top_logprobs") or [])} for e in ents[1:5]]}


def main():
    rows = []
    # --- the 2x2 that separates the sampler from MTP, bare server only --------
    for temp in (0.0, 0.7):
        for spec_name, spec in (("spec_default", {}),
                                ("spec_off", {"speculative.n_max": 0}),
                                ("spec_off_nested", {"speculative": {"n_max": 0}})):
            extra = dict(spec)
            extra["temperature"] = temp
            raw, secs, err = call(BARE, BARE_KEY, extra)
            row = {"cell": "bare/temp=%s/%s" % (temp, spec_name),
                   "secs": round(secs, 2), "error": err}
            if raw:
                row.update(stats(raw))
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False)[:520], flush=True)

    # --- the proxy, with a budget big enough to finish -----------------------
    for mt in (3000,):
        raw, secs, err = call(PROXY, None, {}, max_tokens=mt)
        row = {"cell": "proxy/max_tokens=%d/logprobs=true" % mt,
               "secs": round(secs, 2), "error": err}
        if raw:
            row.update(stats(raw))
            row["logprobs_key_present"] = raw["choices"][0].get("logprobs") is not None
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False)[:520], flush=True)

    with open(os.path.join(HERE, "diag_degenerate.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("\n=== %-34s %6s %10s %10s %10s %8s" %
          ("cell", "n", "exact0", "with_alts", "mean_lp", "secs"))
    for r in rows:
        print("    %-34s %6s %10s %10s %10s %8s" %
              (r["cell"], r.get("n"), r.get("exact_zero"), r.get("with_alts"),
               r.get("mean_lp"), r.get("secs")))


if __name__ == "__main__":
    main()
