# FLEET build — the receiver for `Landed::next`, and the two things it found in the design

**Status: the centre of gravity is built and green.** Findings **F548–F549**; next free number is
**F550**. Built 2026-08-31 against `D:\dev\abcc` at `e51d633`, landed as `8ef4bfa` (the fix) and
`6065687` (the crate). **345 tests passing, 10 ignored, clippy clean under `-D warnings`, rustfmt
clean.** No GPU time was spent: everything below is against a real git repository and a scripted
model, because what is under test is the fleet's arithmetic and the state machine underneath it.

✅ **BOTH CALLS TAKEN BY DAVID, 2026-08-31 — written up as ADR-0022.**

1. 🚨 **A retryable ending lands `Queued`, not `Failed`** — the recommendation and the landing
   were in contradiction and the landing won, silently, for the whole of Skeleton and Gate.
2. 🚨 **"Retry budget 2" means two attempts in total, of which at most one is a retry** — the
   name reads the other way against the shipped types, and the evidence settles it.

## Why nothing had noticed either of them

`abcc-drive`'s own module doc, rule 5: *"`Landed::next` is a `NextAction` **the fleet has not been
built to receive yet** — admission, slots and retry budget 2 are the Fleet milestone — so the
driver runs one attempt and hands back its recommendation rather than acting on it."*

That sentence is the reason. **A recommendation nothing receives is a recommendation nothing
checks**, and both findings are of the same shape: a value that was correct in isolation, beside a
value that was correct in isolation, that had never been read together. This is the third time this
project has found that shape — F392 is the donor's version (a retry budget and an escalation ladder
sharing one integer), F393 the second (two paths to a human writing different terminal states) —
and it is the argument for building the receiver rather than reasoning about it.

---

## 🚨🚨 F548 — the driver's landing forecloses its own recommendation

`ending()` for a retryable `PhaseEnded::Unmeasured` returned **both** of these, computed in the
same struct literal, from the same match:

```rust
next:    Some(NextAction::Attempt { cause: Cause::Retry { of: attempt } }),
landing: Landing::Failed,          // → Command::Fail → TaskState::Failed
```

`TaskState::Failed` is terminal. `TaskState::apply` checks `is_terminal()` **first, before it
consults the transition table**, and returns `Refused::Terminal`. `Driver::run` opens with
`Command::Deploy`. So the recommended retry was unreachable from the state the recommendation was
returned beside, and **the retry budget could not have been spent from anywhere**.

⚠ **The evidence was already in the test suite, asserted, and passing.**
`a_localize_that_produces_nothing_ends_the_attempt_before_builders_runs` has asserted
`state: Failed` and `next: Attempt { Retry }` since Skeleton. Both assertions are correct. Neither
asks whether the second is reachable from the first, and no test could have, because acting on a
`NextAction` is precisely what nothing did.

**The falsifier was written the other way round and it passed on the first run** — it took the
`Landed`, did what a fleet would do, and asserted the refusal:

| | before `8ef4bfa` | after |
|---|---|---|
| `landed.state` | `Failed` (terminal) | `Queued`, with an attempt in hand |
| the recommended retry | `Err(Refused::Terminal)` | runs, as `Cause::Retry { of }` |
| the same ending, no attempt in hand | `Failed` | `AwaitingOrders`, question names the budget |

### What it is not

* **Not a bug in `ending()`'s judgement.** What the attempt *was* — `Uncertain`, retryable — is
  right, and so is `Attempt` as the recommendation. Only the landing is wrong.
* **Not the `Refused` case.** A deterministic rung refusing already lands `AwaitingOrders` and
  recommends `Attempt`, and those two do **not** disagree: `AwaitingOrders` is non-terminal and
  `OrdersGiven` re-opens it. The driver's comment says so, in the same function. The contradiction
  is only on the `Unmeasured` path, which is why reading the arm above it reassured rather than
  warned.
* 🚨 **Not caught by the type system, and it could not have been.** `Landing` and `NextAction` are
  two enums that are correct separately. The invariant — *the landing must admit the
  recommendation* — is a relation between them, and it lived in a comment.

### The fix, and where the budget is not

`Landing::Requeue { of }` on the `Engaged → Queued` edge that already existed, with a fourth
`RequeueReason::AttemptRetryable { of }`. `Queued`'s contract is *eligible for admission*, which is
exactly what a recommendation to attempt again needs. ⚠ The `Why` is deliberately **not** copied on
to the requeue reason: `AttemptEnded` is written one event earlier and carries it, and two copies of
a reason are two things that can disagree — which is the finding above, again, in miniature.

🚨 **`Driver::retry_available` is a boolean and not a count, and that is load-bearing.** The budget
is the fleet's (ADR-0010) and `abcc-fleet::budget::ATTEMPTS` is the only copy of the number. The
driver has to be told *something*, because **a task can only be handed to a person from inside the
attempt that ran** — `RequestOrders` is an edge out of `Engaged`, and by the time a fleet reads
`Landed::next` the attempt is over and that edge is gone. So the driver receives a derived fact, one
bit wide, and F392's shape — one integer read by two mechanisms — is not reintroduced.

⚠ **Default `false`, which changes `abcc run`.** A bare single attempt that produces an absence now
lands `AwaitingOrders` with `brief::exhausted` rather than `Failed`. That is the honest reading: one
attempt was bought, it produced an absence, and there is no fleet behind it to buy another.

---

## 🚨 F549 — "retry budget 2" reads two ways, and the shipped types read it the wrong one

`Cause::spends_retry_budget()` returns true for `Retry` and false for `Fresh`. A budget of 2
counted against that predicate is **two retries, so three attempts**. ADR-0010 §2 appears to agree:
*"`Attempt` twice, then `HandToOperator`."*

**The evidence says two attempts in total.** F373's table is `pass@k` where *k is total attempts*:

| | pass@1 | @2 | @3 | @4 |
|---|---|---|---|---|
| Q56, 56 × 5 | 88.2% | **94.6%** (+6.4) | 96.8% (+2.1) | 97.9% (+1.1) |
| U100, 10 × 8 | 88.8% | **99.3%** (+10.5) | 100.0% (+0.7) | 100.0% |
| K champion, 3 × 6 | 66.7% | **86.7%** (+20.0) | 93.3% (+6.7) | 97.8% (+4.4) |

And ADR-0010's own §3 heading is *"Retry budget 2, and **the third attempt is a per-population
decision**"* — **a sentence that only parses if budget 2 gets you attempts 1 and 2.** §2's *"Attempt
twice"* is then the scheduler dispatching `Attempt` for both, which is what a scheduler with no
`Fresh` in its vocabulary does; the shipped `Cause` enum has one, and that is where the two readings
part.

▶ **David's call, 2026-08-31: two attempts, one retry.** The difference is 50% of the GPU time
spent on every failing task, so it is worth the paragraph.

### A budget is spent on a line of enquiry, not on a task

`budget::spent` walks the causes forward and the chain resets when the operator changes the
question — `Edit` and `Rescope` set it to 1, `Retry` increments, `Replay` spends nothing. ⚠ **None
of that is new**: it is `Cause`'s own distinction, written on `spends_retry_budget` when the enum
was designed — *"a rescope or an edit is the operator changing the question, so it does not [count]
— v1 folded all four into one counter and then could not explain the number."* The only thing added
is that `Fresh` now counts as the first attempt of its own chain.

---

## What the milestone now has, and what it still owes

| owed by `PLAN.md` §3 | state |
|---|---|
| admission as a projection of the store | ✅ `Fleet::admit`, folded from the log, no queue object |
| one slot with a resident model | ✅ `UnitId(0)`, sequential by construction |
| workspaces isolated, **the gate serialized** | ✅ free with one slot — F542's 34.4 s is not paid |
| `NextAction` with **retry budget 2** | ✅ `budget`, and F548 is what it cost to make it spendable |
| a tool policy per slot | ⏸ meets POSTURE's ADR-0014; not built |
| the tool-head set enumerated and **frozen** per attempt | ⏸ ADR-0011; not built |
| the breaker, whose input is a **real one-token completion** | ⏸ F539; not built |

**The exit criterion — one attempt at a time with a worktree and a real build, reported as delta +
`min_avail_mib` + the blind window — has not been run.** Nothing above spent GPU time. That
measurement is the next thing FLEET owes and it is the only part that needs the box.

⚠ Two open ends inherited from P1 and untouched: `--parallel 1` versus `2` was never compared
**under load**, and F539's wedge has one occurrence and no cause. The breaker is the item that
answers the second, and it is not built.
