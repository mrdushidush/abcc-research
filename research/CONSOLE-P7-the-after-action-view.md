# CONSOLE P7 — the after-action view, and an instrument that reads zero on the case it was built for

**Status: `abcc replay` ships. The durable log now folds back into what happened — with no task,
every final state against the endings of the attempts underneath it; with one, that task's
transitions and per attempt its phases, spend, tools, rungs, longest silence and ending. Building it
was three hours. Pointing it at this project's own log was twenty minutes, and it produced the two
findings below that no amount of further building would have.** Findings **F605–F612**; next free
number is **F613**. Built 2026-09-05 against `D:\dev\abcc` at `8148c5e`, landed as **`4a3f9c2`**.
**493 tests passing (up from 473), 15 ignored, clippy clean under `-D warnings`,
`cargo fmt --all --check` clean.** 20 of those tests are new, in two files.

▶ This closes item 4 of CONSOLE's non-eyeballing queue: *replay and the after-action views*.

**The session's shape: the queue item was written as plumbing — "the durable log exists, the paged
read cursor is a doc comment." Both halves were wrong. The cursor was already built and already had
three consumers, and the thing that was missing was not a read path but a QUESTION: the board says
what state a task is in, and nothing said how it got there.**

---

## 1. What shipped

* **`abcc-core/src/replay.rs`** (844 lines) — the fold. `Replay::over(&[Logged])` produces one
  `TaskTrace` per task, each holding its transitions, its attempts and the questions still owed to a
  person. Per attempt: `PhaseTrace` (paired to its entry, §5), `Spend`, `Made` (F511's composition),
  the discarded calls, the rungs, and `Quiet`. No I/O, no `&mut`, nothing but the words.
* **`abcc/src/replay.rs`** (514 lines) — the report. Only the two things that are true of a process:
  reading the whole log, and putting a `TaskState` through the console's label map so the page names
  a state with the word the operator saw. **It opens the log without booting it**, for the reason
  `abcc fun` and `abcc board` do — boot sweeps orphans and requeues their tasks, and this command is
  meant to be usable *while* the next sortie is flying.
* **`abcc-core/tests/replay.rs`** (15) and **`abcc/tests/replay.rs`** (5).

### 🚨 It is not `Cause::Replay`, and the module says so in its first screen

`Cause::Replay` **forks an attempt** — it re-runs work and writes new events, and `abcc-fleet`'s
budget carries a comment about it. `abcc replay` **writes nothing**. The word is right for both
because ADR-0005 already uses it in this sense (*boot is the same code as replay*) and ADR-0012 §4
pairs it with the screen (*replay-as-primary makes the after-action screen nearly free*) — but the
two live one crate apart and would have been confused within a month.

---

## 2. F605 — the board's one word is standing over five endings, and sixteen of twenty are not failures

`abcc replay` over this repository's log, 2,689 events, 29 tasks, 30 ended attempts:

| the board says | tasks | attempts | and underneath it |
|---|---|---|---|
| **MISSION FAILED** | 20 | 20 | 8 `Uncertain/TruncatedAtCap` · 5 `Uncertain/SaidNothing` · 3 `Uncertain/BudgetExhausted` · 2 `HardFailure/EngineError` · 2 `SoftFailure/Timeout` |
| **INTERVENTION REQUIRED** | 5 | 6 | 2 `Uncertain/NoCheckerForArtifact` · 1 `Refused/standard` · 1 `Uncertain/BudgetExhausted` · 1 `Uncertain/ContextOverflow` · 1 `Uncertain/SaidNothing` |
| **ABORT** | 2 | 2 | 2 `Uncertain/NoCheckerForArtifact` |
| **MISSION ACCOMPLISHED** | 2 | 2 | 2 `Success` |

🚨 **Sixteen of the twenty `MISSION FAILED` are `Uncertain`** — the system reporting that it could
not tell, which is a different fact from the work being wrong. Only **two** of the twenty are
`HardFailure`, and both are the same HTTP 500.

**This is not a bug in the board.** A projection of a lifecycle is a lifecycle, and `Failed` is
exactly where `abcc-drive` puts those tasks. The ending lives on the *attempt*, `AttemptOutcome`
already keeps failures and absences apart — that is `abcc-core`'s rule 3 and the reason the type has
`Uncertain` at all — and the projection is simply not where that survives. **The honesty was in the
record the whole time and nothing was reading it back.** That is the entire product case for this
command, and it took one run to find because the board had been read forty times and the log never.

⚠ The transferable half: **a state and an ending are different facts, and a status column is the
place they get conflated.** v1's eleven-state enum is the same defect one level up (W3 F146) — it
carried scheduling, pipeline position and outcome in one word, and ABCC 2.0 split them into four
types. Splitting the types is not sufficient if the only screen re-merges them.

---

## 3. F606 — the composition accounts for 1.4–1.9% of what was billed, and the field that should say where it went reads ZERO

`Event::ModelCallEnded.composition` is F511: *what a completion was made OF, as opposed to how big
it was*. Its doc comment is unambiguous about why it exists — five live turns spent 94–98% of their
budget assembling one enormous tool call and were cut mid-argument, and from the usage block alone
that is indistinguishable from a model writing an essay.

**Every `Finish::Length` call on this log that spent the full cap:**

| # | completion tokens billed | text chars | trace chars | **argument chars** | accounted ≈ tokens | share |
|---|---|---|---|---|---|---|
| 1 | 8,192 | 160 | 393 | **0** | ~138 | **1.7%** |
| 2 | 8,192 | 144 | 468 | **0** | ~153 | **1.9%** |
| 3 | 8,192 | 123 | 344 | **0** | ~117 | **1.4%** |

The one call in each is an **`apply_patch` whose `argument_chars` is zero**, and whose kept
`arguments` string is empty — F506's own case, *a tool call cut mid-argument is not a request*.

🚨 **So the instrument built to answer *where did the completion go* reads nothing on precisely the
case it was written for.** 98% of the budget is unaccounted, and the field that would name it is 0.

### F607 — and the separation is clean, which is what makes it a defect rather than noise

Per attempt, accounted characters ÷ 4 against completion tokens billed:

| ending | n | min | median | max |
|---|---|---|---|---|
| **`uncertain/truncated_at_cap`** | **3** | **35.9%** | **39.2%** | **40.1%** |
| `uncertain/said_nothing` | 2 | 69.0% | 82.2% | 82.2% |
| `success` | 2 | 81.2% | 87.0% | 87.0% |
| `uncertain/budget_exhausted` | 2 | 84.1% | 84.7% | 84.7% |
| `refused` | 1 | 86.0% | 86.0% | 86.0% |
| `uncertain/no_checker_for_artifact` | 2 | 82.3% | 86.4% | 86.4% |
| `soft_failure/timeout` | 2 | 88.3% | 89.9% | 89.9% |
| `uncertain/context_overflow` | 1 | 88.9% | 88.9% | 88.9% |

**No overlap.** The truncated attempts top out at 40.1% and the lowest of everything else is 69.0%.
The attempt-level numbers are higher than the call-level 1.4–1.9% because a truncated attempt's
*other* calls account normally — which is itself the control: the counter works, and stops working
on one call shape.

⚠ **n = 3, not 8.** Five of the eight `TruncatedAtCap` attempts predate the `composition` field
entirely, and `Made::counted` is 0 for them — *nobody counted*, which the report prints as an
absence rather than as a zero. Quoting 8 here would be quoting a denominator that does not exist.

### What this is NOT yet

⚠ **This does not say the model streamed 8,000 tokens that nothing counted.** Two candidates
survive and a fold cannot separate them:

1. The argument deltas were streamed and the in-flight counter never accumulated them for a call
   that never completes.
2. The tokens were never streamed, and the server's `completion_tokens` is not describing bytes that
   crossed the socket.

**They have opposite fixes**, and one live run distinguishes them: point the champion at a task that
will truncate and read the raw SSE alongside the log. That is the morning's cheapest experiment and
it needs the GPU, which is why it is not in this document.

---

## 4. F608 — the gate's cold build is a 78.9-second UNMARKED silence, and now you can see it

`Quiet` reports the largest gap inside an attempt's span **and names the event that broke it**,
which is the field that matters. From `abcc replay t2598`, the `budget::retries()` success:

```
quiet    worst 78.9 s at seq 2675, after checkpoint_taken — broken by rung_recorded (UNMARKED)
         15 silence(s) over the 10 s bar, 13 liveness mark(s) in the attempt
```

versus `abcc replay t1594`, a truncation:

```
quiet    worst 67.6 s at seq 1628, after ModelCallStarted — broken by LivenessMark (the run marked it)
         7 silence(s) over the 10 s bar, 7 liveness mark(s) in the attempt
```

🚨 **Both are over a minute and only one of them was watched.** The 67.6 s is the model thinking, and
a `LivenessMark` closed it because the mark is emitted from inside the stream's read loop — the run
knew. The 78.9 s is the gate's cold build between `checkpoint_taken` and `rung_recorded`, where no
stream is being read, **so nothing marked it and nothing could have.** That is F592 exactly, and
until now it was inferred from a stopwatch rather than read off the record.

⚠ **The limit is asserted as a test rather than left to be rediscovered.** A gap needs an event on
both sides, so an attempt that hangs and is never written to again produces **no** `Quiet` at all —
`a_hang_after_the_last_event_produces_no_gap` says so and would fail if the fold ever pretended
otherwise. Seeing that half needs the wall clock, which is not on the log. **F592 is still not
fixed. It is now legible after the fact, which is a different thing and a smaller one.**

---

## 5. Four smaller things, three of them about documents rather than code

**F609 — a rationale written in the present tense expires the moment the fix lands.**
`event.rs` says of `TraceSignal`: *"two `OpenAt200` observations exist in this project's whole
history and both survive only because a person read them off stdout before the scrollback went."*
The log holds **32 `PhaseEnded` events, 30 `closed` and 2 `open_at200`** — both are durable, because
F513 added the field that made them so. The sentence is the *justification* for the field, written
in the present, and it now reads as a false statement about the record. ▶ The general form: **when a
comment explains why something was added, it is describing a world that no longer exists by the time
anybody reads it.**

**F610 — "a doc comment and nothing more" was about the use, not the function.** The queue item said
the paged read cursor was a doc comment at `abcc-store/src/lib.rs:299`. `Store::read_from` is fully
implemented at line 305 and already has **three consumers** — `feed.rs` (the SSE resume path),
`fun.rs` and `ops.rs`. What was only a doc comment is the *scrub/replay* use named in the same
sentence. ⚠ Checking took one grep and would have been skipped by anyone who trusted the note; it is
the same shape as every other entry in *verify claims against code, not docs*.

**F611 — a second exhaustive match over the same enum is a second thing to keep in step.** The fold
first carried a private `name_of(&Event) -> &'static str`, 29 arms. `Event::kind()` already exists,
is already exhaustive, and returns the log's own serde tag. The private copy was deleted and
`Quiet` now names events as `liveness_mark` rather than `LivenessMark` — the on-disk spelling, which
is also the one a person greps for. ⚠ `attempt_of` stays a match, because it reads a *field* and
`kind()` cannot give it one.

**F612 — two tasks in the same state are not equal, so a histogram keyed by the value is one row per
task.** Every `TaskState` variant but `Queued` carries a `since`, and `Failed`/`Accomplished` name
their attempt. `Replay::endings` groups on `TaskState::name()` and keeps the first whole value only
so a caller can label it. **Mutation-checked**: switching the key to `r.state == *state` fails
`two_tasks_in_one_state_are_one_row` and two others. ▶ It would have looked correct on any log with
one task per state, which is what a fixture usually has.

---

## 6. The tests, and why there are two files

🚨 **`abcc/tests/replay.rs` asserts on the rendered text, not on the fold's output.** That is F600
applied on purpose: *a test that asserts the inputs to a rendering cannot see a defect in the
rendering* — fifteen tests passed over the roster's placement and decoding the drawn frame found two
defects in it. So the report gets its own file over a real `Store`, and it asserts the strings a
person reads: `1 of 2 are Uncertain`, `8192 completion token(s)`, `accounts for ~116 (1%)`,
`cut before a single argument character arrived`.

What that catches which the fold's tests cannot: a number computed and never printed, a unit
converted twice, an absence rendered as a zero, and two states collapsing into one row *on the page*
rather than in the `Vec`. One of these fired during the session — the composition line printed a
complete-looking account of a completion with no denominator beside it, which is F511's own mistake
one level up; `accounting()` and the `billed` line exist because of it.

**Mutation checks run:** grouping by value (3 tests fail), pairing every `PhaseEnded` with the first
phase rather than the last open one (`a_phase_ending_takes_the_name_of_the_entry_before_it` fails).

---

## 7. What is open, and what the morning should point at

▶ **F606 is the one to spend the GPU on**, and it is one run: make the champion truncate, read the
raw SSE beside the log, and see whether the argument deltas cross the socket. Both candidates are
live and they have opposite fixes.

▶ **The 20 `MISSION FAILED` are now five separate investigations rather than one**, and they are not
equally interesting. `TruncatedAtCap` (8) is F606's. `SaidNothing` (5) has ADR-0016's nudge
mechanism already aimed at it and `Limits::nudges` is 2. `EngineError` (2) is the contentless HTTP
500 that F506 says comes from appending a turn cut at the cap — **so it is probably the same root as
the truncations**, which would make ten of the twenty one bug.

⏸ **Still David's, unchanged by this session:** F592 (a silence detector on the data path cannot
observe silence — now *legible* after the fact, still not fixed), the three console instruments
(F587), whether `redirect`/`resume` get wired (F585), the eyeballing review, `--px`, animation
smoothness, sixel inline, the 96 voice lines.

**Remaining non-eyeballing queue:** the *take over* verb, the four GIFs, `rust-embed` the 16 images.

---

## Findings index

| # | what |
|---|---|
| **F605** | 🚨 The board's `MISSION FAILED` stands over **five** endings, and **16 of 20 are `Uncertain`** — the system could not tell, not the work was wrong. The attempt-level honesty existed all along; the projection discards it. |
| **F606** | 🚨🚨 On **every** full-cap truncation the composition accounts for **1.4–1.9%** of the tokens billed, and the single `apply_patch` call's `argument_chars` is **0**. F511's instrument reads nothing on the case it was written for. Two candidate causes, opposite fixes, one live run separates them. |
| **F607** | Per attempt the truncations run **35.9–40.1%** against **69.0–90.0%** for every other ending — **no overlap**. ⚠ n=3 of 8; the other five predate the field and report an absence, not a zero. |
| **F608** | The gate's cold build is a **78.9 s UNMARKED** gap (`checkpoint_taken` → `rung_recorded`); a 67.6 s model gap in the same log *was* marked. F592 made readable after the fact, not fixed. A hang with no second event still produces no gap at all, and a test says so. |
| **F609** | ⚠ A rationale written in the present tense expires when the fix lands: `event.rs` says both `OpenAt200` survive only from stdout, and the log holds both (2 of 32 `PhaseEnded`). |
| **F610** | ⚠ *"The paged read cursor is a doc comment and nothing more"* was wrong about the function and right about the use: `read_from` is implemented with three consumers. |
| **F611** | A private `name_of(&Event)` was a **second exhaustive match** over an enum `Event::kind()` already names. Deleted; `Quiet` uses the on-disk spelling. |
| **F612** | 🚨 Two tasks in one state are **not equal** (each names its attempt), so a histogram keyed by the value is one row per task — and looks correct on any fixture with one task per state. Mutation-checked. |
