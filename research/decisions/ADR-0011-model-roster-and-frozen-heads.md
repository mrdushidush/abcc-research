# ADR-0011 — Three champions by axis, and a finite enumerated set of prompt heads

- **Status:** ✅ Accepted
- **Date:** 2026-08-28
- **Deciders:** David (the roster is his to spend, 2026-08-28), Claude Code (the measurements)
- **Sources:** W1 F68, F77, F79, F80, F87–F92 · `research/W1-batch2-results.md` (batch 2, 27 cells,
  2026-08-28) · W2 F81, F82, F83, F84, F85, F86 · W11 F238, F239, F240, F241, F245, F246, F248 ·
  W4 F377, F386
- **Depends on:** ADR-0003 (one slot, one resident model)

## Context

🚨 **Model choice here is settled by measurement, not by prior art.** Batch 2 ran three arms, 27
cells, in one session — because F59 showed the token baseline steps ~10% between sessions, so
cross-session numbers are not safely comparable:

| arm | effective bpw | right | wrong | timeout | wall | price |
|---|---|---|---|---|---|---|
| A champion `qwen3.6-35b-a3b-mtp@iq3_s` | 3.064 | 6 | 3 | 0 | **1,352 s** | — |
| B byteshape `Qwen3.8-27B-IQ4_XS-3.67bpw` | 3.674 | 8 | 0 | 1 | 11,202 s | 8.3× |
| C unsloth `Qwen3.8-27B-UD-Q3_K_XL` | **3.933** | **9** | 0 | 0 | 6,615 s | **4.9×** |

⚠ **A filename is not a specification.** Measured from the tensor table, byteshape's "IQ4_XS" build
is **3.674 bpw** — only 35.6% IQ4_XS, majority **IQ3_XXS**, plus IQ2_XXS in three `ffn_gate` tensors
— landing **0.26 bpw below** the build batch 1 had already tested. It is a **context** build (64k
resident), not a quality one, and it lost on every axis measured. C's 4.9× reproduces batch 1's 5.2×
closely, which is a good cross-session reproducibility signal.

The serving side was measured too. **The prefix cache saves 79.7% of TTFT, and one token changed at
the *front* annihilates it** — an 18,470-token prompt costs 11.399 s changed against 11.549 s cold
(F81). And **the server holds at least twelve distinct heads warm** on a default nobody configured:
twelve heads over the same ~16.9k-token body cost 10.58–10.83 s on first sight and **2.53–2.60 s on
the second pass**, with no eviction at twelve — a restore, not a recompute. **It costs 473 MiB per
state at ~16.9k tokens (≈28.7 KiB/token)**, so ~1.7 GiB for one warm head at the daily driver's
61,440 (F240).

## Decision

### 1. Three champions, chosen per axis, never compiled in

- ▶ **SPEED — `qwen3.6-35b-a3b-mtp@iq3_s`**, 3.064 bpw. The default working model, and the one every
  rate in the corpus was measured on. **MTP is on by default for this model, so the baseline is
  MTP-on.**
- **QUALITY — `unsloth/Qwen3.8-27B-UD-Q3_K_XL`**, 3.933 bpw, 9/9 at **4.9×** the wall clock. **If a
  27B is ever crowned, crown unsloth.**
- **CONTEXT — the byteshape 3.67 bpw build**, 64k resident, and the weakest brain of the three.

**Nothing is crowned by this ADR.** The roster is an operating choice made per session — the price
is 4.9× and it is David's to spend — which is why the model name is configuration, not a constant.

⚠ **Residency is orthogonal to quality.** The "spilling model" rule is a *speed* argument only, so a
matched-bpw quality run is valid even when the arm spills — but **force the expert split**
(`--n-cpu-moe` / `numCpuExpertLayersRatio`) rather than letting the driver page, and label it
quality-only.

### 2. Enumerate the tool-head set and freeze it per attempt

🚨 **F81's ruling was right and "freeze" is the wrong verb: the correct rule is *enumerate*.** A
finite, compile-time set of heads is affordable in both time (one cold prefill each, once per body)
and RAM (473 MiB each at 17k). **An unbounded set is unaffordable twice over** — a cold prefill per
variant *and* 473 MiB per variant. So:

- **The system prefix is immutable within an attempt, and the tool schema goes in it once.**
- **A system prompt must never carry a task id, a timestamp, or anything else that varies.**
- **A tool registry that grows on demand is the failure case**, not the feature.
- **Append the failure context; never prepend it** (ADR-0010).
- ⚠ **What the warm-head store does *not* buy is free per-phase heads.** In production the body under
  the head is task-specific, so every (head, task) pair is a first sight and pays the ~8.5 s anyway.
  What it really buys is two things: **retries are warm** — a failed Measure sends the task back to
  Change with the same head and context — and **two concurrent attempts do not evict each other.**

### 3. Structured output is constrained, budgeted, and honest about overrun

- **`response_format: json_schema, strict: true` for every structured artifact** — because it makes
  malformation *unrepresentable*, not because the unconstrained arm was measured failing (it was
  not, F248). **Never `json_object`** — the server rejects it, HTTP 400.
- **8192 output tokens for every model phase that emits a structured artifact**, twice the largest
  successful completion observed (4,006). **No `max_tokens` is safe by construction**, because the
  quantity being bounded is the reasoning trace, which varies **9,942–16,564 characters on identical
  input** and returned nothing in one call in five at four times the donor's cap (F246).
- **`finish_reason == "length"` with an empty payload is `Uncertain(TraceOverran)`** — never a
  verdict, never a zero (ADR-0009). Log
  `usage.completion_tokens_details.reasoning_tokens` **on every call**: it is already on the wire,
  it is the quantity that overran, and without it the failure is invisible in the record.

### 4. Serving

- **One shared LM Studio server**, with 2.0 written to assume it does **not** own the model:
  re-resolve the `llama-server` pid, tolerate the reload 400, and expect the prefix cache to be
  shared and evictable.
- **Keep the HTTP boundary; do not build FFI bindings.** The crash-isolation argument is stronger
  than the latency one, on a workload that is 96% prefill.
- **The command line is the only complete witness** (F86) — and ⚠ **an absent flag does not prove an
  absent feature**: the RAM prompt cache above arrives with no `--cache-ram` and no
  `--slot-save-path` on the line.
- **Short structured calls go direct to the bare server.** Two OpenAI fields are silently dropped by
  the proxy at HTTP 200 — `chat_template_kwargs` (F377) and `logprobs` (F386) — and the bare server
  is where `enable_thinking: false` actually takes effect. ⚠ **The subject behaves differently
  there**, so a number measured on one endpoint is not a number about the other.
- **The model-reload retry is re-earned, not ported.** W2 said *port
  `post_with_model_reload_retry`* because its **six matched surface forms** are accumulated field
  knowledge; under ADR-0001 the **six forms are the specification** and the code is written fresh.
  A swap-per-gate design exercises it far harder than the donor ever did.

## Consequences

- **Changing a unit's loadout mid-mission genuinely costs 11–34 seconds of the console going
  quiet.** That is not a wart to hide behind a spinner — it is a supply line the operator can learn
  to respect, and W5 wants it on screen.
- **Constrained decoding is what lets the console render verdicts and diffs as *interface*** rather
  than as text a parser hopes to survive.
- **The KV bound is Σ(sequence lengths) ≤ window, not window/N** (ADR-0003), and KV is allocated in
  full at load — so the window is a load-time decision, not a per-request one.
- **A model load is a cache wipe** (F241): a head warm at 2.626 s came back at 10.584 s after
  unloading and loading the same model.

## Alternatives rejected

- **In-process `llama-cpp-2` FFI** — no crash isolation, and the latency saved is invisible on a
  96%-prefill workload. Reconsider only if 2.0 ever needs logit-level access HTTP cannot express.
- **Two model servers, one per tool** — co-residency does not fit (ADR-0003) and time-sharing is
  23.77 s per switch.
- **`response_format: json_object`** — HTTP 400. Not a style preference.
- **On-demand tool groups as a prompt-size optimisation** — the trade is inverted on this workload:
  ~33 KB of prompt saved against a full cold prefill (11.4 s at 18k, 33.9 s at 55k). Keep the
  *mechanism* for capability scoping; stop calling it a token saving.
- **Crowning the byteshape 27B on its filename** — 8+1 timeout against 9/9, 11,202 s against 6,615,
  and the only arm to exceed its context pin (102%).
- **Reporting a concurrency "instability point"** — it does not exist up to N=6; reporting one would
  have been a fabricated cliff.

## What would falsify this

**A bigger card.** Every line here is downstream of 16,311 MiB: the roster, the swap price, the
enumerated head set and the 473 MiB-per-state ceiling. ⚠ Also watch the **matched-bpw speed
comparison** — it is the one arm that still needs a card with room to spill honestly, and until it
runs, the speed champion's crown rests on an unmatched-bpw comparison.
