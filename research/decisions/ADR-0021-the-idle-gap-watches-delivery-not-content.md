# ADR-0021 — The idle gap watches whether the stream is delivering, not whether the model is saying anything

- **Status:** ✅ Accepted · **amends [ADR-0015](ADR-0015-what-the-first-real-runs-corrected.md) §1**,
  which established that the idle gap is ours rather than the HTTP client's. That stands; **what a
  gap *is* was left implicit and was implemented wrongly.** ⚠ It also **withdraws the deferred
  120 s candidate** recorded in ADR-0015 and `PLAN.md`.
- **Date:** 2026-08-30
- **Deciders:** Claude Code, on the FLEET probe; the fix is code and is falsifiable by one test
- **Sources:** `research/FLEET-P1-two-slots.md` F537, F538 · F506, F511, F513 · ADR-0006 F198/F199 ·
  ADR-0016
- **Depends on:** ADR-0006 (threads own the work; the gap is applied on the consuming side),
  ADR-0015 (the gap is ours)

## Context

ADR-0006 set a per-request budget and ADR-0015 §1 corrected its mechanism: `reqwest`'s timeout is a
**total duration** on both 0.12.28 and 0.13.4, so `openai.rs` builds its client with no timeout,
reads the response on its own thread, and applies the gap with `recv_timeout` on the consuming side.
`Limits::idle_gap` is 90 s and the ending is `Why::Timeout { after_ms }`.

Both documents describe the gap in the same words: **a stream silent this long is a hang.** Neither
says what *silent* means, and the implementation answered it by accident: **silent = no `Delta`
arrived.**

`OpenAiCompat::fragment` folds a tool-call argument fragment into its slot and **emits no `Delta`
at all**; a `Delta::ToolCall` exists only once `finish_reason` arrives and `flush_calls` runs. So
while a model writes one large tool call — an `apply_patch` diff, which is the Builders phase's
entire job — the reader thread receives SSE bytes continuously and the consumer's `recv_timeout`
receives nothing.

**The first sequential arm of the probe failed 2 of 2 at exactly 90,000 ms, with one turn in
flight.** `hw-probe` was sampling the GPU at ~107 ms throughout:

| window | samples | GPU util median | ≥50% | power median |
|---|---|---|---|---|
| slot A, normal work | 466 | 61% | 86% | 92.1 W |
| **slot A, the 90 s "silence"** | 828 | **75%** | **100%** | **115.1 W** |
| slot B, normal work | 557 | 60% | 90% | 89.2 W |
| **slot B, the 90 s "silence"** | 828 | **75%** | **97%** | **115.3 W** |

**The server never stopped.** It was flatter out during the "hang" than during the work — power
pinned at 115 W ±3 W against 89 W swinging to 167 W, which is a uniform compute loop, not a dead
socket. ▶ **A stream delivering ~380 characters per second was being called idle** (F537).

⚠ **And the deferred 120 s candidate was this bug wearing a tuning knob's clothes.** Its entire
evidence was *"it fired 2 of 5 at the 16k budget against 0 of 20 before"*: raising the completion
budget from 8,192 to 16,384 simply **doubled how long a turn could spend writing one tool call**,
and nothing was watching that time. Raising the threshold would have hidden the defect and delayed
the one real hang by 30 s.

## Decision

🚨 **The idle gap is a claim about whether the stream is DELIVERING. Every kind of body byte resets
it, including bytes that carry no content the phase will ever read.**

`Delta::ToolCallProgress { chars }`, emitted by `OpenAiCompat::fragment` per fragment:

- **It carries the count and nothing else.** The assembled call still arrives exactly once, whole,
  as `Delta::ToolCall` at the ending — because **a half-written argument is not a request** (F506),
  and a turn cut at the cap must still run none of its calls.
- `Accumulator` folds it into `tool_call_chars` and clears `reasoning_open`, so the ADR-0010 §7
  trace signal reads correctly in flight rather than only at flush.
- 🚨 **`Event::LivenessMark` now names it**, and that matters as much as the fix: liveness is
  sampled *between* deltas, so before this a turn writing one tool call produced **no marks at all**
  and the log had nothing in it between the call starting and the timeout. It now reads:

  ```
  + 97.8s builders streaming: 0 chars of answer, 428 of trace,  1698 of tool-call arguments
  +163.6s builders streaming: 112 chars of answer, 336 of trace, 19039 of tool-call arguments
  +233.7s builders streaming: 112 chars of answer, 336 of trace, 44939 of tool-call arguments
  ```

**`Limits::idle_gap` stays at 90 s and the 120 s candidate is withdrawn** (see Context).

### The falsifier is the existing test with one substitution

`tests/http.rs` already pinned the property, for text —
`a_turn_whose_body_outlasts_the_budget_completes_while_every_gap_stays_inside_it`: six pieces 120 ms
apart under a 400 ms budget must complete. Swap the text chunks for tool-call argument fragments,
change nothing else, and before the fix it fails with

```
the stream delivered a fragment every 120ms and was called idle after 400 ms
```

That test ships as `a_turn_writing_only_tool_call_arguments_is_not_silent_and_must_not_read_as_a_hang`.
⚠ **The neighbouring `tool_calls_are_assembled_from_their_fragments` could never have caught this:
every pause in it is `Duration::ZERO`.** It asserts assembly and says nothing about time.

## Consequences

- **A turn may now legitimately run for many minutes.** Measured post-fix: **121.9 s / 45,583
  argument characters / 16,384 completion tokens**, ending honestly at `TruncatedAtCap`; the longest
  of the session was **213.7 s**. Under the old code every one of those was a `Timeout`.
- 🚨 **The historic timeout population is not trustworthy and cannot be re-adjudicated.** This
  project's own log carries **2 timeouts in 27 attempts** and nothing in it says whether the server
  was working. ▶ **An idle-gap ending is not evidence of a hang unless something outside the process
  says the server was idle.**
- ✅ **The true positive still fires, and the same instrument tells the two apart.** Post-fix, one
  attempt's stream produced 11,069 characters of trace and 119 of answer and then stopped for
  **90.3 s at 0% GPU utilisation and 29.1 W** (F538). That is the class the gap exists for, and
  after the fix it is the only class that reaches it.
- **The dominant real failure mode is now visible and is not the gap's.** Five of eight post-fix
  attempts ended at a budget — one tool call eating 16,384 tokens, or 24 rounds of context growth.
  **That is a Builders-phase problem**, and it was previously being logged as a hang.
- **`Delta` gained a variant, and exactly one exhaustive match had to change** (`Accumulator::take`).
  `scripted.rs` needs no new arm to be correct, because a scripted stream simply never emits one.

## Alternatives rejected

- **Raising `idle_gap` to 120 s** — the deferred candidate. It treats the symptom, hides the defect,
  and delays the real hang. The measured turn was **213.7 s**; no threshold that is still a hang
  detector would have covered it.
- **Resetting the timer on any raw byte from the socket, inside the reader thread.** Simpler, and it
  discards the one thing the consuming side is for: a reader that is receiving but never *parsing*
  a delta — a proxy dribbling keep-alive whitespace, say — is a case the gap should still catch.
  The reset must be a parsed delta, which is why this is a `Delta` variant and not a heartbeat.
- **Emitting the partial `ToolCall` as it grows.** It would reset the gap and it would break F506:
  the loop would see a call whose arguments are not yet a request, and `ADR-0016`'s `Finish::Length`
  rule depends on a cut turn running **none** of its calls.
- **Counting argument bytes only in `LivenessMark` and leaving the gap alone.** The log would tell
  the truth while the detector kept killing the turn.

## What would falsify this

**A stream that delivers tool-call fragments forever without finishing** would now never time out —
the gap resets on each one, and only `Limits::rounds` and the completion budget bound the turn. That
is the correct trade (a server producing tokens is not hung), but it means **the budget and the
round count are now the only backstop for a runaway turn**, and neither was chosen for that job.
⚠ If a turn is ever observed streaming arguments past its own completion budget, this is where to
look.
