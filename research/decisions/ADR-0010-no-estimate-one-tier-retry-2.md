# ADR-0010 — No pre-dispatch estimate; one tier; retry budget 2; the breaker reports

- **Status:** ✅ Accepted
- **Date:** 2026-08-28
- **Deciders:** Claude Code (W4, all six items), ratified with `research/SUMMARY.md`
- **Sources:** W4 F360–F399 — esp. F360–F366 (the complexity model, run), F368–F375 (three axes),
  F376–F385 (the estimator), F386–F390 (logprobs), F391–F396 (the ladder), F397–F399 (fine-tune) ·
  W1 F77, F79, F80 · W2 F81, F83
- **Closes:** OQ-W6-7 (twice deferred)

## Context

🚨 **W4 is the workstream where every item inverted its brief.** §11 asked how to rescale v1's
complexity model, how to route on required context length, whether logprobs correlate with quality,
and expected a *"no, and say why"* on fine-tuning. Four questions, and the first three came back
"the axis does not exist."

- **The complexity model does not need rescaling; it needs deleting.** Both donors' scorers were
  executed over **149 real coding tasks** and joined to **952 measured agent attempts**: v1's puts
  **149 of 149 tasks in one tier** and predicts nothing.
- **Required context length is not a property of the request.** ρ = **+0.048** against the
  workspace's bytes, **+0.836** against the rounds the agent actually ran. The part that is knowable
  — preamble plus bytes on disk — is measurable exactly, for free, and does not vary within a
  corpus. **The part that varies is the loop, and it is the same quantity as effort.**
- **The estimator is not free and not better than counting bytes.** The champion was run as the
  estimator, **414 calls over the 69 tasks that have an answer key**: it costs **20.5 s against a
  19.1 s median attempt**, and at n = 56 nothing in the comparison is distinguishable from anything
  else. **F385: even a perfect estimator loses to reacting.**
- **There is nothing to escalate to.** The swap costs 1.24 Q56 attempts *before* 4.6× the decode
  (7.75× measured end to end on K); the head rewrite is **4.60×**; co-residency does not fit
  (ADR-0003); the cloud rung does not exist under zero cloud spend.

## Decision

**Ship no pre-dispatch estimate. There is one tier, and the only purchase a router can make is
another attempt.**

### 1. No estimate, and the type says so

```rust
pub struct RequestFacts {
    pub prompt_tokens: u32,          // counted, not estimated
    pub workspace_bytes: u64,
    pub workspace_files: u32,
    pub preamble_tokens: u32,        // system prompt + tool schemas, measured at warmup
    pub window_tokens: u32,          // num_ctx, so the fit check is arithmetic
    pub toolchain: ToolchainProfile,
    // NO complexity score. BCF's typed RoutingResult survives with
    // `complexity: Option<f32>`, and 2.0 emits `None`.
}
```

**Nothing in the routing input is a prediction: every field is either a fact about the request or a
count of work already done.**

### 2. The decision is a stopping rule, not a tier choice

```rust
pub enum NextAction {
    Attempt { round_budget: u32 },
    Stop(StopReason),
    HandToOperator(Evidence),
}
```

**One counter, and it is the budget — there is no separate ladder to keep in sync with it.**
`Attempt` twice, then `HandToOperator`. **The per-attempt budget and the total budget must not be
independently settable**: if 2.0 ever exposes a knob it exposes **one**, and the type makes the other
derivable. 🚨 *An operator knob that can silently remove a tier is worse than no knob* — the donor
bug (F392) is only possible because two mechanisms shared one integer.

### 3. Retry budget 2, and the third attempt is a per-population decision

Two attempts capture **6.4 of Q56's 10 available points, 10.5 of U100's 11, and 20.0 of K's 33**. A
third is worth paying for only where the outcome history says the population is not bimodal — **which
the event log can answer and a config file cannot.**

### 4. The breaker reports and never gates

It **reads the event log, not a field on the task** — a rate over recent attempts, threshold learned
per population, shipped as a **report the operator can act on**. One failure takes Q56 from 88.2% to
43.6% and U100 from 88.8% to 81.9%, so **ship the update rule, not the number.** This is
ADR-0008's ruling applied to a statistical verdict rather than a model's, for the same reason.

**`HandToOperator` is a durable state on the event log, never a socket event** — the WebSocket emit
is a notification *about* a state, not the state.

### 5. Do not route on required context length — do a window check instead

Where the fixture *does* change by two orders of magnitude, the right response is arithmetic: **does
the workspace plus the preamble plus a working margin fit in `num_ctx`?** One honest answer per
workspace, no tier involved.

### 6. 2.0 reads no logprobs, and fine-tunes nothing

**No logprobs on the worker path** — not *"not yet"*. Four changes are the price, three of them fail
silently, the measured gain is negative in both questions, and no corpus this project can generate
would resolve the difference. ⚠ If anything ever reads one, **the integrity check is ALTERNATIVES ON
EVERY TOKEN** and the flat `"speculative.n_max": 0` — the nested form is silently ignored, and array
length equal to `completion_tokens` **passed on 29 of 29 fabricated calls**, so it is not a check.

**No fine-tune, and the real reason is three absent preconditions**, any one of which closes it:
**no second destination to route to** (F397), **no label column to learn from** (F398), and **no
machine to train on** (F399). ▶ **Capture the by-product anyway, because it is free**: an escalation
is by construction the label *"this needed more than the router gave it"*. Add **nothing** for
training's sake — the moment a capture exists *for* training it is a collection project. 🚨 **Write
the target column**: v1's single most expensive omission here is a one-line `undefined`.

### 7. The one in-flight signal worth wiring

**At token 200, has the reasoning trace closed?** If not, this turn is far likelier to end at the
ceiling with nothing. 🚨 **It is a stop, not a score** — it feeds `Uncertain(OutputBudgetOverrun)`
and `NextAction`, and **it never becomes a number displayed next to an answer.** Where a human wants
a confidence number, give them the verifier's result: 547 ms, p90 767 ms, and checkable.

## Consequences

- **Append the failure context, never prepend it.** A retry that rewrites the prompt head costs a
  full cold prefill at **4.60×**, against the **79.7%** TTFT saving one changed token at the front
  annihilates (ADR-0011).
- **The operator is the only tier above the worker**, so escalation is a hand-off to a human rather
  than to a bill. That is what makes the breaker acceptable rather than paternalistic.
- **Two open questions stay open and are answerable from W8 cells, not from a spike:** the minimum
  history before a learned breaker threshold beats the constant 2 (OQ-W4-16), and whether
  `HandToOperator` should distinguish *budget exhausted* from *the breaker tripped early*
  (OQ-W4-17).
- **Two OpenAI fields are known to be dropped at HTTP 200** — `chat_template_kwargs` and `logprobs`
  — so **no field may be called "unsupported" until it has been tested one hop closer to the metal.**
- ⚠ **The reopen condition for the fine-tune is written down so a future session does not
  re-litigate it:** a second destination exists **and** ≥ N escalation pairs carry both an attempt
  and a better answer for the same task **and** the training run has somewhere to run.

## Alternatives rejected

- **A complexity router, a tier ladder, an escalation estimator** — all three of W4's first items.
- **Exponential backoff between attempts** — nothing here is rate-limited or contended; there is one
  local server. Backoff buys nothing.
- **A `needs_human` status distinct from `failed`** — ADR-0004's nine states settle it; a fourth
  terminal state is how v1 got two that disagreed.
- **Porting `humanEscalation`'s reverse path** — taking work back from an operator who has not
  answered is a fleet behaviour, and in a single-operator tool it loses a decision the operator was
  still making.
- **Self-consistency / n-sample voting as the confidence signal** — n× an 18.6 s attempt to
  approximate what the verifier gives exactly in 547 ms.
- **Turning MTP off globally so the logprob array stops being fabricated** — measured cheap (106.01
  vs 102.90 tok/s), and it makes the logprobs *real*, not *useful*.
- **A LoRA at inference quant, or distilling from a cloud teacher** — IQ3_S weights are not a
  training target, the card has 0.3–0.9 GB of margin, and cloud spend is zero, standing.
- **Training on the Q56 / U100 corpora** — they are the **instrument**. A worker trained on the
  benchmark it is scored against stops being a baseline and becomes a memorised answer key.

## What would falsify this

**A second destination appears** — a bigger card, a second box that is a *device* (ADR-0013), or a
policy change on cloud spend. Then "one tier" stops being a fact about the hardware, and the
routing question genuinely reopens: on F397's precondition alone, not on a rescaled score.
