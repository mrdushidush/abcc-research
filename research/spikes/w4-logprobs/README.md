# w4-logprobs — the one confidence signal nobody had measured

Spike for **W4 item 4** (`research/W4-routing.md`). Run 2026-08-26 on the champion
`qwen3.6-35b-a3b-mtp@iq3_s`.

§11 asks: *"Confidence scoring on worker output: logprobs, self-critique, test results, static
analysis. Which correlate with real quality?"* **Three of the four were already answered** by W6 on
728 real attempts and are not re-run here:

| signal | answer | where |
|---|---|---|
| static analysis | a type or syntax check caught **1 of 160** failures | W6 item 5, F311–F324 |
| generated tests | **ratify a wrong change 6 times in 9** | W6 item 4, F297–F310 |
| self-critique | a model verdict is **3 of 23**, 1 false fail in 34 | W6 item 7, F336–F348 |

That leaves **logprobs**, which no run on this project has ever captured — and getting them turned
out to be most of the work.

## Held constants

| | |
|---|---|
| model | `qwen3.6-35b-a3b-mtp@iq3_s`, `-c 65536 --gpu max --parallel 1`, `--spec-type draft-mtp --spec-draft-n-max 2`. Diagnostics ran on pid 20848 / `:64703`; the model was offloaded and reloaded mid-session, so the campaign ran on pid 10968 / `:61039`. **Both the port and the `--api-key` are regenerated on every `lms load`**, which is why `recorder.py` discovers them from the live process rather than holding a constant |
| subject | `claudette-af3f804` (v0.17.0), the binary every recorded Q56 control run used |
| suite | `q56`, `--variant control`, `--num-ctx 61440 --num-predict 8192 --max-iterations 40 --verify-timeout-s 300 --delivery verbatim` |
| sampler | `temperature: 0.0` — what `api.rs:783` sends |
| endpoints | bare `llama-server` `:64703` for completions; LM Studio `:1234` for everything w8-run probes |

**Three things are deliberately different from the recorded control runs, and each one is forced by
a finding below**: the endpoint (the proxy drops the field), streaming (the server refuses the
combination), and MTP (the array is otherwise fabricated). The run's own pass rate against the
recorded 49/50/48 of 56 is the check on whether those three moved the subject.

## What the diagnostics established, in the order they bind

Everything here is a **serving** result, and every one of them is silent except the third.

1. **LM Studio's proxy drops `logprobs`, HTTP 200, no warning.** Asked with a budget large enough to
   finish (`stop`, 344 completion tokens, 80 content chars), the reply simply has no `logprobs` key.
   The first attempt looked like a drop too but was confounded — all four proxy cells stopped at
   `length` with empty content, which is item 3's **F377** (`chat_template_kwargs` dropped, so the
   trace ate the budget); the re-test with `max_tokens: 3000` separates them. **This is the second
   OpenAI field the proxy silently discards, and it partially closes OQ-W4-15.**
   `diag_logprobs.py`, `diag_degenerate.py`

2. 🚨 **Under MTP the array does not describe the emitted text — and it is complete, well-formed,
   in range, and wrong.** Non-streaming, the drafted tokens are padded with `logprob 0.0`
   (probability 1.0) and an empty alternatives list: **23 of 24**, **42 of 44**, **1,681 of 1,800**.
   Streaming, they are **omitted** instead — 39 entries for 400 completion tokens. Only the
   positions MTP could not draft carry a real distribution. **MTP is on by default for the
   champion**, so this is what a naive reading of "confidence" on this deployment would have
   measured: draft acceptance.

   The cause is separable and was separated. The 2×2 over {temperature 0.0, 0.7} × {spec default,
   spec off} moves **only** with spec: at temperature 0.7 the default arm is still 42 of 44 certain,
   and the flat per-request key **`"speculative.n_max": 0`** restores alternatives on **24 of 24**.
   The nested form `{"speculative": {"n_max": 0}}` is **silently ignored** — a third field accepted
   and discarded. `diag_degenerate.py`

3. 🚨 **The bare server refuses the subject's own request shape**:
   `HTTP 400 — "logprobs is not supported with tools + stream"`. `api.rs:773-784` sends exactly
   `tools` + `stream: true`. So on the path the worker actually uses, the signal is not degraded,
   it is **unavailable**. The escape route is non-streaming — verified to return `94/94` entries
   with alternatives *and* a correct `tool_calls` reply — and it is safe to take because
   `api.rs:614-632` already falls back to the non-streaming parser when the reply is not SSE.
   `diag_stream.py`

4. **The instrument checks out once MTP is off.** At temperature 0.0 the sampler is greedy, so the
   emitted token must be the argmax of whatever is being reported: **1,800 of 1,800** agree. Under
   MTP the same check passes vacuously — 119 of 119, on the only 119 of 1,800 entries that carry
   alternatives at all. `diag_price.py`

5. **The price.** Same prompt, same 600-token budget, prefill cached:

   | | tok/s | vs deployed |
   |---|---|---|
   | MTP on, no logprobs *(the deployed path)* | 102.90 | 1.00× |
   | MTP on, logprobs asked | 101.97 | 1.01× — free, because fabricated |
   | MTP off, no logprobs | 106.01 | 0.97× |
   | **MTP off, logprobs asked** | **86.95** | **1.18×** |

   So a real logprob costs **1.18× decode** against the deployed configuration (1.22× against
   MTP-off), plus giving up streaming, on **every** worker call. ⚠ On this prompt MTP is not buying
   speed at all (102.90 against 106.01 with it off), which is a fact about one code-generation
   prompt at n=3, not a re-measurement of W1/W2's MTP result — but it does mean the 1.18× is
   the cost of *computing* the distribution, not of losing the draft head.

6. **MTP is nondeterministic at temperature 0.0 and MTP-off is not.** Three byte-identical calls:
   **2 distinct outputs** with MTP on, **1** with it off. Small n, but it is a candidate mechanism
   for item 3's **F383** (identical calls at temperature 0.0 that drift), and it is independent of
   the trace.

7. **The bare server names the model by GGUF path, not by the LM Studio id**, so w8-run's
   model-confirmation step (`main.rs` step 3) aborts the run. The recorder does not defeat that
   check — it requires the served path to carry the champion's fingerprint before echoing the
   requested id back.

## What would count as a positive result — written before the analysis was run

Item 3 spent its last finding taking an ordering away from everyone, so this one says in advance
what it would take to keep one. A logprob signal is worth shipping only if **all three** hold:

1. **It beats the coin.** Its AUC for predicting "this attempt failed" has a 95% task-clustered
   bootstrap interval that **excludes 0.5**. Six of nine intervals in item 3's F379 did not.
2. **It beats what is already free.** The paired bootstrap difference against the best free signal
   on the same resampled tasks — `iterations`, `tokens_out`, `wall_clock_s`, or the structural ones
   (`n_length_stops`, `n_empty_turns`, `retry_fired`) — **excludes zero**. Every paired difference
   in F379 spanned it.
3. **It survives the within-task test.** On tasks that both pass and fail across repeats, the
   failing attempt is the less confident one, consistently enough for a sign test to see it. This
   is the only form that holds task difficulty exactly constant, and it is the only form in which
   an in-flight number could route anything.

Anything less is a story about 56 tasks. And even all three would still have to be worth **1.18×
decode on every call plus no streaming** (F389) — against a verifier that costs a **median 547 ms,
2.9% of an 18.6 s attempt** over 166 recorded control cells, and answers exactly instead of
estimating (item 3's F385). ⚠ The "0.16 s" the handoff carried for this is W6 **item 6**'s git
checkpoint (F330), not the cost of verifying.

**The repeat count is set by `power.py`, before any of it was run, and it is the reason five is not
three.** At the failure rate this configuration actually produces (~4%), three repeats give ~7
failures and a ±0.221 half-width — a true AUC of 0.70 would sit at [0.48, 0.92] and fail to exclude
the coin. Five give ~12 failures and ±0.169 → [0.53, 0.87], which excludes it. **Stopping at three
would have manufactured a null**, so the run goes to five even though the timeouts make each repeat
~96 minutes.

## Files

| file | what it is |
|---|---|
| `diag_logprobs.py` | the {hop} × {asked} × {free, schema} grid — does the field survive each hop |
| `diag_degenerate.py` | why every token reads as certain: {temperature} × {spec} , and the proxy re-test with a budget that finishes |
| `diag_price.py` | tok/s in all four modes, and the greedy-argmax instrument check |
| `diag_stream.py` | the subject's real shape: SSE + tools; where the 400 lives |
| `diag_endpoint.py` | the two hops on an identical non-streaming tool-carrying request — same median, different tail |
| `recorder.py` | the recording proxy — rewrites the subject's streaming request to non-streaming + `logprobs` + `speculative.n_max: 0`, records every call, keys it to the cell by the workdir in the prompt |
| `campaign.sh` | five repeats of Q56 control, one recorder instance per repeat |
| `analyze.py` | instrument check, AUC + task-clustered bootstrap, best-logprob-vs-best-free-counter, and the within-task paired comparison |
| `power.py` | OQ-W4-12 in closed form — how many cells it takes to separate a signal from the coin, and to separate two signals 0.05 apart |
| `lp-rep*.jsonl` | one row per completion call — **gitignored**, regenerate with `campaign.sh` |
| `cell-features.jsonl` | the per-cell reduction the analysis actually scores |

Regenerate:

```sh
python diag_logprobs.py && python diag_degenerate.py && python diag_price.py && python diag_stream.py
bash campaign.sh            # ~5 h, 5 x 56 cells
python analyze.py
```

## Traps

1. 🚨 **A complete, well-formed logprob array can be a fact about the draft head.** Check
   `n_entries == completion_tokens` *and* that alternatives are present on every token, on every
   call, before computing anything. Under MTP the first check passes and the second does not.
2. 🚨 **The two endpoints are still not interchangeable, and the difference is still silent.**
   `logprobs` joins `chat_template_kwargs` on the dropped list. Assume nothing survives the proxy
   until it is tested there.
3. 🚨 **`"speculative.n_max": 0` works and `{"speculative": {"n_max": 0}}` does not.** Same server,
   same meaning, no error either way.
4. **The array covers the reasoning trace as well as the answer**, and the trace is usually the
   larger part — a per-call mean is mostly a measurement of the trace. Split on the `</think>`
   token (verified: 363 reasoning chars = the first 99 tokens exactly).
5. 🚨 **Five repeats of 56 tasks are 56 clusters, not 280 independent trials.** The bootstrap
   resamples *tasks*. Resampling cells reports an interval several times too narrow.
6. **Reading the signal changes the run.** Three held constants move at once (endpoint, streaming,
   MTP), so the run's pass rate has to be checked against the recorded control runs before any
   correlation from it is quoted.
7. **Item 3's traps 4 and 5 still bind**: use AUC over "did this attempt fail" rather than ρ against
   a mostly-constant outcome, and quote no ordering without the bootstrap.
8. 🚨 **A proxy that outlives its client starves a single-slot server, and the damage lands on the
   NEXT cells.** `llama-server` runs `--parallel 1`. When the harness times a cell out it kills the
   subject, but a plain `urlopen` in the middle keeps the upstream generation running to completion,
   so the orphan holds the only slot. In the first campaign that turned **5 real runaways into 13
   timeouts**: Q35 and Q50–Q56 each recorded **one 2-second call and then starved for 600 s**. The
   shape to recognise is a cell with almost no recorded model time that times out anyway, always
   immediately after an expensive cell. Fixed with a watchdog on the client socket that closes the
   upstream connection the moment the subject goes away.
9. 🚨 **A banner is not a readiness signal.** The first campaign printed "recorder on :1235" and then
   died binding a port the previous repeat's recorder still held, so four of five repeats reported
   "connection refused" against a proxy that had apparently started. Bind first, print second, use a
   fresh port per repeat, and poll `/v1/models` before launching the subject.
10. **The recorded control runs are not timeout-free.** Run `w8-1786808290277` has Q35 and Q49 as
    timeouts of its own. "49/50/48 pass of 56" is a pass count, not a clean sheet — do not read the
    campaign's timeouts against an imaginary zero.
11. 🚨 **Changing the endpoint changes the SUBJECT, not just the fields you get back.** Q43 and Q49
    pass on `:1234` and time out on the bare server, in both MTP arms (F390). Attribute a behaviour
    change by elimination and a control run, not by picking the most interesting-sounding variable —
    the first two hypotheses here (MTP, then streaming) were both wrong, and the partial output of a
    running arm is what made the first one look right.
12. **Neither hop is deterministic at temperature 0.0.** Three byte-identical requests gave three
    different completion lengths on both. Any per-cell number from a single run is a draw, not a
    measurement.
