# ADR-0022 — The retry budget is two attempts, and a landing may not foreclose the recommendation beside it

- **Status:** ✅ Accepted · **amends [ADR-0010](ADR-0010-no-estimate-one-tier-retry-2.md)
  §2 and §3**, which set the budget and stated it in two ways that the shipped `Cause` enum reads
  differently. The stopping rule, the single counter, the absent tier and the breaker all stand;
  **what the number counts** is fixed here. ⚠ It also adds a fourth caller to
  [ADR-0004](ADR-0004-task-lifecycle.md)'s `Requeue` edge, and a fourth
  `RequeueReason`, without touching the transition table.
- **Date:** 2026-08-30
- **Deciders:** David, two calls, on the Fleet build; the first is falsifiable by one test and the
  test was written the wrong way round first
- **Sources:** `research/FLEET-P2-the-receiver.md` F548, F549 · W4 F373 (the `pass@k` curve),
  F392 (the donor's shared counter), F393 (two paths to a human) · W3 F150, F166 · ADR-0010,
  ADR-0004, ADR-0020
- **Depends on:** ADR-0004 (the transition function is the authority), ADR-0010 (budget 2, one
  tier), ADR-0020 (one slot, so the receiver is a loop)

## Context

`abcc-drive` has returned a `NextAction` since the Skeleton milestone and its module doc says why
nothing acts on it: *"the fleet has not been built to receive [it] yet."* Building the receiver is
the Fleet milestone, and building it asked the design two questions it had never been asked.

**The first is a contradiction that was already asserted, in a passing test.** `ending()` computes,
in one struct literal, `next: Attempt { Retry }` beside `landing: Failed`. `Failed` is terminal;
`TaskState::apply` refuses every command on a terminal state *before* it reaches the transition
table; `Driver::run` opens with `Deploy`. The recommendation was unreachable from the state it was
returned beside, so **the retry budget could not have been spent from anywhere in the system.**
`a_localize_that_produces_nothing_ends_the_attempt_before_builders_runs` has asserted both halves
since Skeleton. Both are correct. The relation between them lived in a comment.

**The second is an ambiguity in this ADR's parent.** "Retry budget 2" counted against
`Cause::spends_retry_budget()` — which is true for `Retry` and false for `Fresh` — is two retries
and therefore three attempts. ADR-0010 §2 seems to agree (*"`Attempt` twice, then
`HandToOperator`"*) and ADR-0010 §3's heading contradicts it (*"the third attempt is a
per-population decision"*), a sentence that only parses if budget 2 is attempts 1 and 2.

## Decision

### 1. The budget is **two attempts in total**, of which at most one is a retry

F373 is the evidence and it is `pass@k` over *total* attempts: the second buys **6.4 to 21.1
points** and the third buys **0.7 to 6.7**. §2's *"Attempt twice"* is a scheduler dispatching
`Attempt` for both, which is what a scheduler with no `Fresh` in its vocabulary does; the shipped
enum has one, and that is where the two readings part. The third attempt stays exactly what ADR-0010
§3 called it — **a per-population decision the event log can answer and a config file cannot** — and
it is not the default.

▶ The difference is 50% of the GPU time spent on every failing task, which is why it is written
down rather than inferred.

### 2. The budget is spent on a **line of enquiry**, not on a task

`Fresh`, `Edit` and `Rescope` each start a chain at 1; `Retry` increments it; `Replay` spends
nothing. 🚨 **None of that is new** — it is `Cause`'s own distinction, written when the enum was
designed: *"a rescope or an edit is the operator changing the question, so it does not [count] — v1
folded all four into one counter and then could not explain the number"* (F150). The only addition
is that `Fresh` counts as the first attempt of its own chain, which is what §1 above requires.

### 3. 🚨 A landing may not foreclose the recommendation returned beside it

**A retryable ending lands `Queued`**, through `Landing::Requeue` on ADR-0004's existing
`Engaged → Queued` edge, with a fourth `RequeueReason::AttemptRetryable { of }`. `Queued`'s
contract is *eligible for admission*, which is exactly what a recommendation to attempt again needs.

⚠ The `Why` is **not** copied on to the requeue reason. `AttemptEnded` is written one event earlier
and carries it on the `AttemptOutcome`; two copies of a reason are two things that can disagree,
which is the defect this ADR exists for, in miniature.

▶ This does **not** make the driver act on its recommendation. It stops the driver acting on it —
landing a terminal state beside `Attempt` *was* an action, the action of refusing it.

### 4. The driver is told **one bit**, never the number

`Driver::retry_available: bool`, default `false`. The budget lives in `abcc-fleet::budget::ATTEMPTS`
and nothing else in the workspace holds a copy.

The driver has to be told *something*, and the reason is a property of the state machine rather than
a convenience: **a task can only be handed to a person from inside the attempt that ran.**
`RequestOrders` is an edge out of `Engaged`, and by the time a fleet has read `Landed::next` the
attempt is over and that edge is gone. So the ending that has no attempt behind it must know so
while it is still landing.

🚨 **One bit and not a count, because F392 is the donor defect where a retry budget and an
escalation ladder read the same integer** — and raising a per-phase budget by one silently deleted
the top tier, then labelled the outcome with the phase that never ran. A boolean cannot be raised.

### 5. The default changes what a bare `abcc run` does, and that is the honest reading

With `retry_available` false, a single attempt that produces an absence lands `AwaitingOrders` with
a question that names the attempts and says a budget is what ran out — not `Failed`. One attempt was
bought, it produced an absence, and there is no fleet behind it to buy another. This is ADR-0010
§4's *"`HandToOperator` is a durable state on the event log"* reaching the one path that never had
it.

## Consequences

- **`Failed` keeps its contract.** It stays terminal, holds nothing and stands at boot. The
  alternative — a `Failed → Deployed` edge for retries — was considered and rejected: it makes
  `is_terminal()` a lie and `StateContract` unenforceable.
- **The fleet writes no terminal state of its own**, and needs no third recovery path. Every ending
  is still landed by the driver, from inside the attempt, which is what keeps F166 — v1's second
  recovery path, shipped and never run when it was needed — from having a place to happen.
- **A `Queued` task whose budget is gone is now representable and is not silently re-run.**
  `Admission::HeldBack` grounds the sortie and writes a `Note`. It should be unreachable; it is a
  variant rather than a panic because *unreachable* is a claim about code that changes, and the
  alternative to noticing is spending the GPU forever.
- ⏸ **ADR-0010's two open questions stay open**, and one of them is now cheaper to answer: whether
  `HandToOperator` should distinguish *budget exhausted* from *the breaker tripped early*
  (OQ-W4-17). `brief::exhausted` is the first half of that distinction and the breaker is not built.

## What would overturn this

- **§1** — an outcome history showing a population that is not bimodal, where the third attempt's
  0.7–6.7 points are worth their minutes. ADR-0010 already says the event log is what answers this
  and a config file is not.
- **§3 and §4** — a landing that has to be terminal *and* retryable at once, which would mean the
  nine states are missing one. None of the endings need it today.
- ⚠ **Nothing here is overturned by the budget being wrong in a particular case.** The number is
  ADR-0010's and this ADR only says what it counts.
