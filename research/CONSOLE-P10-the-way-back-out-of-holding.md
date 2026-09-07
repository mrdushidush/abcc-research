# CONSOLE P10 — the way back out of `Holding`, and a timeout that was arithmetic all along

**Status: `redirect` and `resume` ship. ADR-0012 §4's five console verbs all have a mechanism at a
sortie for the first time, and the two that did not were not missing an edge — they were missing a
*reader*. `Fleet::admit` now has a second pass over `Holding`, and `Driver::run` picks `Resume` over
`Deploy` from the task's own state. Separately, `Limits::tool_call_gap` drops 480 s → 400 s, derived
against 833 logged calls instead of the two wire captures it had been resting on. And a sortie on
the E0004 subject, which did not reproduce E0004 — it reproduced the `apply_patch` fold at 100% and
spent 1.28 M input tokens producing nothing.** Findings **F645–F648**; next free number is **F649**. Built 2026-09-07 against `D:\dev\abcc` at `c1c50d9`,
shipped as **`5f6ee08`**, **`0e14e2f`** and **`f2434d5`**. **541 tests passing (up from 526), 19
ignored, clippy clean under `-D warnings`, `cargo fmt --check` clean.** Fifteen new tests across three
files, and **thirteen mutations run one at a time** — of which **two survived the first pass**, which
is §8's subject.

▶ This closes **F585**, which CONSOLE-P4 raised and CONSOLE-P8 explicitly declined to close:
*"`abcc take` does not close F585's gap… wiring `resume` is still David's question."* It was put to
him on 2026-09-07 and he chose to have it wired.

**The session's shape: F585 read as two verbs that needed building. It was one verb that needed
building and one verb that had been fully built for weeks with nothing at the other end. The desk has
been writing the operator's `resume` to the durable log since CONSOLE-P4 — the row is there, in the
right order, on the right task. Nothing folded over it. And the thing that makes that not an
oversight is that `resume` could never have worked the way the other four do.**

---

## 1. What shipped

* **`Fleet::held`** (`abcc-fleet/src/lib.rs`) — the fold. Given a `Holding` task and the `since` of
  the transition that held it, it answers `Stays`, `Asked`, or `Redirected { prompt }`.
* **`Admission::Resume { task, cause, redirect }`** — a third admission, scanned *after* `Queued`.
* **`Fleet::affordable`** — the budget check both admissions share, asked **beside the cause**.
* **`budget::spent_with` / `admits` / `in_hand_beside`** — the cause-aware half of the retry budget.
* **`Driver::redirect(Option<String>)`** and the `Deploy`/`Resume` choice in `Driver::run`.
* **`brief::redirected`** — the addendum that carries the operator's prompt into both working briefs.
* **`desk::Behind`** and a scope-aware `caveat`, because the two desks now differ.
* **`Limits::tool_call_gap` = 400 s**, and a test that asserts the arithmetic rather than the number.

---

## 2. 🚨🚨 F646 — `resume` was never a control-channel verb, and the code said so in a doc comment

The old ledger, from CONSOLE-P4: *"`Command::Resume`, the lifecycle's only edge out of `Holding`, has
**no caller in the binary at all**."* True, and it framed the fix as *wire the channel up*. The
channel is not where it goes.

`ControlPoint::check` drains the queue and latches the first *stop*. `Control::Resume` is not a stop,
so `disposition` returns `None` and the point drops it — deliberately, with the reason written down:

> `Control::Resume` is not a stop and is ignored here — **it belongs to a task in `Holding`, which by
> definition has no worker to receive it.**

That sentence is the whole finding. A control channel is a way to reach *a running attempt*. A held
task has no running attempt; that is what `Holding` means. So there is no version of this where a
`resume` travels down a channel and something at the far end acts on it. **The verb lives entirely on
the log side**, and the only thing that could ever have honoured it is a fold.

And the log side was already complete. `FleetDesk::request` writes `ControlRequested` **before** it
pokes the channel (ADR-0006's ordering, so that a verb which is not on the log did not happen), on
its own second connection. Every `resume` an operator has ever typed at a fleet desk is on the log,
against the right task, in the right order. **The mechanism was one fold short, and the missing half
was a reader rather than a writer.**

⚠ **And it is the mirror of F587, which is worth holding side by side.** There, three of the six fun
queries have no instrument because the console is a *reader by construction* and installing them
would make it a writer — a missing **producer**, and an ADR-level question. Here the producer was
always there and nothing read it. Both are one-sided wiring; only one of them is a decision.

---

## 3. The `since` guard — how a request that is read and never consumed cannot loop

The obvious hazard: the fold reads `ControlRequested { Resume }` and never marks it used, so what
stops it resuming the same task for ever?

There is no acknowledgement row on purpose. Marking an event as consumed would be a mutation of the
log, which ADR-0004 does not have, and a second `used` flag beside the event is two things that can
disagree. What does the work instead is already there: **`TaskRow::since`, the seq of the transition
that produced the current state.**

* A `resume` **newer** than `since` belongs to *this* hold.
* A `resume` **older** than `since` belonged to a hold the task has already left.

So a task that is resumed, runs, and is stopped again gets a **new** `since`, and the old request
falls behind it in the same motion. The guard is not a check bolted on — it is the ordering the log
already has, read the right way round.

▶ The test for it walks a task through *two* holds with one `resume` between them and asserts
`Admission::Quiet`. Removing `logged.seq > since` fails exactly that test and no other.

---

## 4. A redirect needs no second verb, and that is a claim about what the operator meant

`pause` and `halt` are stops: the operator wants the work to stop, and it stays stopped until they say
otherwise. `redirect` is not a stop wearing a note — it is *"do this instead"*, an **answer**. The
driver has always agreed: a `Keep::AndFork` landing returns `NextAction::Attempt { Cause::Edit }`, a
recommendation that nothing had ever received.

So the fold reads the hold's own cause. The verb that caused the current hold is the last
`ControlApplied` for the task, because the transition into `Holding` follows it immediately and a
later `resume` writes `ControlRequested` rather than `ControlApplied` — the two event kinds keep
themselves apart without a marker.

⚠ **And `Queued` is still scanned first.** `Queued` is the state whose contract *is* eligible for
admission; `Holding` is the operator having stopped this one. A redirect issued mid-sortie is
therefore picked up on the **next** turn of the admission loop rather than jumping the board. That is
additive by construction: nothing that used to be admitted is now admitted later than it was.

---

## 5. 🚨 The budget had to be asked *beside* the cause, and asking it before was silently wrong

ADR-0010's budget is spent on **one question asked repeatedly** — so `Cause::Edit` *resets* the chain
(`budget::spent` sets it to 1) while `Cause::Retry` extends it. Admission used to compute
`budget::available(&causes)` from the causes on the log and then derive the cause afterwards, which is
correct only while every dispatch is a retry.

It stopped being true the moment `Holding` grew a way back onto a slot. An exhausted task that the
operator redirects has **bought a fresh line of enquiry** — that is what changing the question means —
and a budget asked before the cause refuses the very attempt the redirect just paid for.

`budget::spent_with(causes, next)` pushes the dispatch onto the chain before measuring, and
`Fleet::affordable` is the one place that can answer `HeldBack`. `in_hand_after` (which carried the
off-by-one for a retry) becomes `in_hand_beside` (which carries it for whatever the cause turns out
to be), and the sortie uses it when telling the driver whether a retry is in hand.

🚨 **And the cause-blind pair was removed rather than kept beside the new one.** `available` and
`in_hand_after` had no production callers left, and leaving them there would have been *two ways to
ask one budget, one of which is now wrong for two of the three causes a sortie can dispatch* — F392's
donor defect in miniature, where two mechanisms shared one integer and raising a per-phase budget by
one silently deleted the top tier. Their tests were re-expressed against the cause they dispatch,
which is a small improvement in its own right: `an_edit_or_a_rescope_resets_the_chain` now asserts
the reset **beside an exhausted chain**, which is where the reset actually matters, instead of only
counting a chain that already had the `Edit` on it.

▶ The test asserts both halves **against the same exhausted task**: redirect it and it flies, resume
it and it is `HeldBack`. Asked before the cause, both come back `HeldBack` and the test fails.

⚠ **A consequence worth stating plainly: a `resume` spends a retry.** It is the same question asked
again, from the checkpoint, which is exactly what `Cause::Retry` denotes — so `pause` is not free, and
a task paused and resumed twice is `HeldBack` on the second. That follows from the budget as designed
rather than from anything new here, but nothing had ever been able to reach it before.

---

## 6. The redirect's prompt is an addendum, and the Judge is not told about it

`Cause::Edit { of }` names the fork and not the words — an attempt's cause is a fact about lineage,
and the prompt is a fact about the log. So the fleet folds the prompt out of the `ControlApplied` the
landing already wrote, and `Driver::redirect` carries it into `brief::localize` and `brief::change`.

**An addendum, not a replacement.** The task's own prompt still opens both briefs, because a redirect
is the operator turning work that already had a definition — a brief that replaced the task would
leave the model holding one sentence with nothing behind it. The addendum also says *where the tree
is*, which is the half a redirected attempt cannot work out for itself: it opens on the checkpoint the
stopped attempt reached, so work already done is present and re-doing it is the failure mode.

⚠ **`Engineering` is deliberately excluded.** The Judge opens a fresh body from `judge::brief` and is
asked a different question — is this diff what it claims to be — which has no business being told what
the operator typed at the console. The test filters to `recon` and `builders` and says why; asserting
over every call would have quietly required the opposite.

---

## 7. F645 — the tool-call gap was arithmetic, and the old arithmetic composed two things that never co-occur

`tool_call_gap` shipped at 480 s in `9166537`, derived from two SSE captures because one would have
been wrong by 2.6×, and its doc comment ended: *"Tightening it is David's, and the thing to tighten it
against is a re-measured argument rate, not a feeling about eight minutes."*

Re-measured, against **833 `model_call_ended` rows** on this machine's own log rather than two
captures — read 2026-09-07 **before** this session's sortie, so the population is every call the
engine nights produced and nothing this session added. Every row below is the same arithmetic:
`Head::budget()` divided by a decode rate, where the rate is `completion_tokens / (elapsed_ms -
ttfb_ms)`.

| basis | n | slowest decode | whole budget at it |
|---|---|---|---|
| F622's `bigarg` capture — *the old basis* | 1 | **43.1 tok/s** | **380 s** |
| the log, any call size | 833 | 48.5 tok/s | 338 s |
| the log, calls ≥ 8,000 tokens | 15 | 72.2 tok/s | 227 s |
| the log's **longest call ever**, measured | — | — | **138.5 s** |

🚨 **The finding is that decode does not degrade with size — it improves.** Banded:

| completion tokens | n | slowest | p50 | fastest |
|---|---|---|---|---|
| 1–100 | 219 | 55.5 | 86.8 | 361.7 |
| 100–500 | 387 | 52.9 | 81.2 | 130.5 |
| 500–2,000 | 141 | **48.5** | 74.6 | 130.8 |
| 2,000–8,000 | 71 | 55.5 | 74.5 | 132.1 |
| 8,000–17,000 | 15 | **72.2** | 124.8 | 140.0 |

The 48.5 tok/s floor is a **721-token** call. Every call that approaches the budget runs at 72–140
tok/s. So *the whole budget at the slowest rate ever seen* composes the largest size with a rate that
occurs only at small ones, and is pessimistic by construction.

⚠ **The capture still binds, and that is a choice.** At 43.1 tok/s it is 1.7× slower than anything in
the log's own 8,000+ band and its conditions were not recorded — but it is a real observation on this
machine, and a hypothesis worth killing was killed: **`ssecapture.py` is a direct client, not a
proxy**, so it is not an instrument-in-the-path artifact. 400 s covers its 380 s with 5% margin and
buys back 80 s of hang detection. Going lower tightens past a rate this machine has produced.

Two facts the log adds for free: **`completion_tokens` never exceeds 16,384 in any of 833 rows**, so
the budget is confirmed as the hard stop; and `reasoning_tokens ≤ completion_tokens` in all 833, so
these are true whole-call decode rates rather than an accounting artefact.

▶ **The test asserts the arithmetic, not the number.** It recomputes the bound from the capture's own
figures and brackets the shipped gap between it and 125% of it. It fails at **480 s** and at **300 s**.

---

## 8. 🚨🚨 F647 — the redirect survived exactly one attempt, and two of its three mutations survived too

Found by reading the code above before it had been driven, and it is the more useful half of this
write-up.

`Admission::Resume` carried the prompt, because that is where the fold that found it happened to be
standing. **That is one attempt long.** A redirected attempt that ends in an absence lands `Queued`
(F548's landing), is re-admitted through the `Queued` pass — which has no redirect field, and could
not be given one without claiming that a re-route is a property of an *admission* — and the retry
runs on the **original** prompt. The log would then carry two attempts inside one `Cause::Edit` line
of enquiry that were asked different questions, and nothing would say so.

So the words belong to the **task**. `Fleet::redirect_in_force` folds the most recent
`ControlApplied { Redirect }` out of the log; the sortie asks it of *every* admitted task; and
`Admission::Resume` narrows to `{ task, cause }` — it says **why** a task is flying, which is the
log's business, and no longer **what it is being asked**, which is the driver's. The two dispatch
arms then merge into one, and the merge is the point rather than a tidy-up: a resumed attempt and a
fresh one now go down exactly the same code.

**Nothing supersedes a redirect but another redirect.** A pause does not withdraw it — the operator
said what to do instead and *then* stopped the work, which are two statements and not a
contradiction. A retry does not exhaust it. `abcc release` handing a commandeered task back does not
either. What ends it is the task ending.

### 🚨 And two of its three mutations survived the first pass

This is worth more than the fix. The three mutations were *the fold never finds one*, *the **first**
redirect wins*, and *the sortie stops handing it to the driver*. Only the first failed.

* **Nothing asserted that the most recent redirect wins**, because no test had two. The fold would
  have pinned a task to a superseded instruction and looked right until somebody redirected twice.
* **Nothing asserted that the sortie hands the fold to the driver.** `abcc-drive`'s tests prove the
  driver puts a redirect *it is given* into both briefs; replacing `.redirect(redirect)` with
  `.redirect(None)` passed **every test in the fleet crate**.

▶ **That second one is F646's own defect, one layer up, in the code that fixes F646.** A fold that
works, a consumer that does not consume it, and a test suite that covers both ends and not the wire
between them. It took thirty minutes to write a whole section about `resume` being a reader that was
never installed, and then ship the same shape.

Both are covered now — `the_most_recent_redirect_is_the_one_in_force`, and
`a_sortie_hands_the_redirect_in_force_to_the_attempt_it_flies`, which runs a **real sortie** and reads
the brief the provider was actually shown rather than asserting on the admission.

---

## 9. The thirteen mutations, and the test each one broke

| # | mutation | test that failed |
|---|---|---|
| 1 | drop `logged.seq > since` in `held` | `a_resume_from_before_the_hold_belongs_to_a_hold_the_task_has_left` |
| 2 | `Held::Stays` admits anyway | `a_held_task_nobody_asked_for_is_not_admitted` |
| 3 | scan `Holding` before `Queued` | `fresh_work_is_admitted_before_anything_held` |
| 4 | ask the budget before the cause | `a_redirect_resets_the_spent_budget_and_a_resume_does_not` |
| 5 | a redirect dispatches `Retry` | *the same, plus* `a_hold_caused_by_a_redirect_is_admitted_with_the_prompt` |
| 6 | drop the prompt on the way out | *the same two* |
| 7 | the driver always sends `Deploy` | `a_held_task_reaches_the_slot_and_a_queued_one_still_does` |
| 8 | the redirect replaces the task prompt | `a_redirects_prompt_is_an_addendum_to_both_briefs_and_not_a_replacement` |
| 9 | only the first brief gets the addendum | *the same* |
| 10 | the addendum is emitted with no redirect | `an_ordinary_attempt_carries_no_redirect_heading` |
| 11 | the redirect is never in force (the pre-F647 `Queued` path) | `a_redirect_still_applies_to_the_retry_after_the_attempt_it_redirected` |
| 12 | the **first** redirect wins | `the_most_recent_redirect_is_the_one_in_force` — **added after it survived** |
| 13 | the sortie stops handing it to the driver | `a_sortie_hands_the_redirect_in_force_to_the_attempt_it_flies` — **added after it survived** |
| — | `tool_call_gap` at 480 s, and at 300 s | `the_tool_call_gap_covers_the_whole_budget_at_the_slowest_measured_decode` |

⚠ **Mutation 7 is the one that would have shipped.** `Driver::run` sent `Command::Deploy`
unconditionally, and `Deploy` is legal only from `Queued` — so a held task admitted by the new fold
would have been refused at the first line of the attempt, and the fold would have looked like the
thing that was broken.

---

## 10. 🚨 A fixture that refilled the budget it was written to find empty

The budget test walks a task to `Holding` with the chain already spent. The first version of its
helper appended `Cause::Fresh` for the held attempt — which **resets `budget::spent` to 1**. The task
under test arrived at the assertion with a full budget, and the resume arm was admitted.

It failed rather than passing, which is the only reason it is a paragraph and not a defect. But it is
F632's shape exactly, one session later and in the same crate: **the fixture quietly satisfied the
condition the test existed to deny.** The repair is that `held_at` takes the cause as a parameter, so
the line of enquiry a fixture joins is something the test states rather than something the helper
decides.

▶ The rule from F632 still holds and would have caught it earlier: *after a test passes first time,
ask what the fixture would have to look like for the assertion to fail.* Here it did not pass — but
the version that had asserted only the redirect arm would have.

---

## 11. What this deliberately does not do

* **`abcc run` is unchanged, and both verbs are still inert there.** Not an oversight and not fixable
  by wiring: `abcc run` flies one attempt and the process ends, so there is no admission loop for a
  held task to be picked up by. `desk::caveat` now takes a `Behind` and says which command *does* pick
  the row up — because *nothing happened* and *nothing happens until you start a sortie* are different
  things for an operator to do next.
* **No new `Cause`.** A resume is `Retry` and a redirect is `Edit`, both existing vocabulary with
  existing budget semantics. A `Cause::Resumed` would have been a fifth chain rule to keep consistent
  across `spent`, `parent` and `spends_retry_budget`.
* **No auto-resume for `pause` or `halt`.** They are stops. Only a redirect carries its own answer.
* **The `Holding → Deployed` edge stays the fleet's.** `abcc resume <task>` as a CLI verb would have
  to grant a slot with no worker behind it — precisely `RequeueReason::OrphanedByRestart`'s hazard. The
  desk records the request; the fleet, which holds the slot, is what acts on it.

---

## 12. Driving it

```
abcc task "…"                     # something to hold
abcc fleet                        # a desk on stdin for the length of the sortie
  redirect t42 look in src/lib.rs instead
  # → "logged and sent to t42", no caveat any more; the attempt stops,
  #   the task holds, and the NEXT turn of the loop forks an attempt from the prompt
  pause t43
  resume t43                      # → the same loop picks it back up
```

The verb ledger, corrected for the last time: **`pause`, `halt`, `kill`, `redirect` and `resume` are
all wired at a sortie · `take over` / `release` are wired as CLI verbs · `replay` and `retry` are
elsewhere.** ADR-0012 §4's *eight verbs that half-work are worse than three that work* is discharged.

---

## 13. 🚨🚨 F648 — the sortie: `apply_patch` refused **5 of 5**, and the rounds budget is what it burns

David asked for a sortie on **the E0004 subject** — the run in `4735` that got further than `abcc
--version` ever had in 28 attempts, reaching the gate and being refused at the **veto** rung because
the tree did not build (`error[E0004]: non-exhaustive patterns`, one line from fixed). Flown
2026-09-07 on `qwen3.6-35b-a3b-mtp@iq3_s` at ctx 40960, against `D:\dev\abcc` at **`5f6ee08`** —
this session's own code — with the **identical prompt**, so it is a genuine second sample.

**It did not recur. The failure moved *earlier*, and both attempts died the same way.**

| | `a4893` (fresh) | `a5077` (retry) |
|---|---|---|
| ending | `Uncertain { BudgetExhausted { "24 rounds" } }` | the same |
| localize | 10 turns, 15 tools, 85.4 s | 4 turns, 5 tools, 73.0 s |
| change | **24 turns, 27 tools**, 3 m 16 s | **24 turns, 27 tools**, 2 m 3 s |
| model calls | 34, **664,521 in** / 17,369 out | 28, **616,213 in** / 11,738 out |
| `apply_patch` | 2 calls, **2 unmeasured** | 3 calls, **3 unmeasured** |
| gate | *not asked — the attempt produced no artifact* | the same |

🚨 **All five `apply_patch` calls were refused, and all five for the same reason** — F637's
client-side check, firing exactly as designed:

> `apply_patch: the diff argument contains tool-call markup ("<tool_call>" at line 141), so it is a
> transcript and not a diff. Send one call, whose `diff` is only the unified diff text…`

Lines 141, 46, 131, 26, 26. **This is F641's server-side fold, reproducing at 100% on a subject where
the whole-log rate is 77%** — and it is now visible as what it costs rather than as a percentage: two
attempts, 48 rounds, **1,280,734 input tokens**, and **no artifact at all**. The previous run got
*past* this and reached the veto rung; this one never produced a diff to veto.

⚠ **And the shape of the loop is the finding.** The refusal is correct, well-aimed and useless: F641
established the fold happens **in the server's parser, before abcc sees anything**, so the message
asks the model to stop doing something it may not be doing. The model re-reads, re-patches, is
refused identically, and the 24-round budget is the only thing that ends it. *A correct refusal
aimed at an actor who cannot act on it is a loop with a receipt.*

▶ **The cheapest next move, and it is evidence-led rather than a guess: name `write_file` in that
refusal.** The single `Accomplished` in this entire log reached it by *falling back to `write_file`
after `apply_patch` failed twice*, and `write_file` is refused **1 of 17** times against
`apply_patch`'s 51 of 66. The message currently offers the model only a better `apply_patch`. **It is
a one-line change to a string** — and it is deliberately **not shipped here**, because shipping an
unmeasured prompt change is precisely what F625's verdict and F575's floor warn against. It wants an
arm, not a commit.

### What the sortie also settled, for free

* ✅ **The 400 s `tool_call_gap` was never approached.** Worst TTFB **17.5 s**; longest quiet
  **17.4 s**; **zero** timeouts across 62 model calls. F645's arithmetic holds with room to spare.
* ✅ **Every silence over the ten-second bar was marked** — 15 of 15 and 10 of 10.
  ⚠ **This is not evidence that anything improved.** `4735` already carried F592's streaming
  repair and still had one unmarked gap (35.4 s, after `tool_call_started`); that sat in one of the
  **two regions still dark** — a tool child running, and the gate's cold build. Neither was reached
  here: no tool child ran long, and the gate was never asked. **F592's remaining two thirds are
  untested by this run, not vindicated by it.**
* ⚠ **`rounds: 24` is now a live constraint rather than a formality.** It is documented as *a stop,
  not a tier*, and both attempts hit it — the first time on this machine that the round budget, and
  not a timeout or a refused ending, is what ended a phase. Whether 24 is right is a different
  question from whether `apply_patch` works, and it should not be raised until it is.
