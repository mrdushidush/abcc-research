# CONSOLE P5 — the six fun queries, and the silence detector that rides the data path

**Status: ADR-0012 §5's six queries are built, and running them on this project's own log broke
the bar they were written to check — 251 times, four fifths of them by the instrument that
exists to satisfy it.** Findings **F587–F594**; next free number is **F595**. Built 2026-09-04
against `D:\dev\abcc` at `900efe8`. **451 tests passing (up from 428), 14 ignored, clippy clean under
`-D warnings`, `cargo fmt --all --check` clean.** 23 of those tests are new.

▶ This closes item 2 of CONSOLE's non-eyeballing queue. §5 writes six product constraints down as
observables with bars, on the argument that *a feeling nobody can query is a feeling nobody can
hold a milestone to*. The queue item called them "pure folds over the durable log". **Two thirds
of that sentence turned out to be wrong**, and the two ways it is wrong are the two most useful
things this session produced.

**The session's shape: the arithmetic took twenty minutes, and the rest was finding out that
three of the six cannot be measured at all, and that the one everybody cares about has been
failing on our own log since Skeleton.**

---

## 1. What shipped

* **`abcc-core/src/fun.rs`** — the six, as folds over `&[Logged]`. No I/O, no clock, no model.
* **`abcc/src/fun.rs`** — `abcc fun`, which pages the whole log, folds it, and prints the six with
  their bars. 🚨 It opens the log **without booting it**, for the reason `abcc board` does: boot
  sweeps orphans and requeues their tasks, and this command is meant to be run *while* a sortie is
  flying. A reporting command that changed what it reports on is not a reporting command.
* **`abcc-core/tests/fun.rs`** (19) and **`abcc/tests/fun.rs`** (4).
* One deletion: `abcc-tui::view::SILENCE_BAR_MS` was a **second** definition of the ten-second bar.
  It is now a re-export of `abcc_core::fun::SILENCE_BAR_MS`. The reader and the query that grades
  the reader must not be able to disagree about where the bar is.

| §5 constraint | shipped as | state |
|---|---|---|
| No dead air | `DeadAir` + `Fun::open_silence` | measured, with two limits — §3 |
| Speed where it is felt | `Speed` | measured to the log's edge |
| Legibility | `Fun::legibility` | 🚨 **no instrument** |
| Agency | `Agency` | measured; reads zero — §5 |
| Personality with an off switch | `Fun::personality` | 🚨 **no instrument** |
| Honest failure | `HonestFailure` | denominator only |

## 2. F587 — three of the six have nothing to fold, and the reason is architectural

🚨 **Legibility, personality and the numerator of honest failure have no instrument.** Nothing
writes a screen switch, a theme change or a replay-cursor movement. There is no `Event::Screen…`
of any kind: the grep returns zero across the workspace.

This is not an oversight to be repaired with a `match` arm. **All three ask what the operator did
at the console, and `abcc-tui` does not depend on `abcc-store`** — the console is a reader by
construction, which is ADR-0012's design and `CLAUDE.md`'s standing rule that the reader reads the
log and never the projection. Installing these three means **making the reader a writer**. That is
an ADR-level decision and it is David's, not something to do quietly on the way past.

▶ So they return **`Answer::NoInstrument(Missing)`** and never `0`, and the type exists for exactly
that. *Screen switches before the first operator command: 0* reads as **perfect legibility** and
means **nothing is counting** — the shape this project has been bitten by often enough to give it
a type. Each absence names the event that would fix it (`Event::ScreenSwitched`,
`Event::SettingChanged`, `Event::ReplayCursorMoved`) and the sentence saying why it is not small.

`HonestFailure` is the honest half-and-half: **the denominator is measured and the numerator is
not**, so the ratio §5 asks for is not reported at all. Two halves beat an invented quotient.

## 3. The two limits on dead air, neither of which is a bug

**F588 — 🚨 a fold over the log can only see silences that *ended*.** A gap needs an event on both
sides, and **the forty-minute hang the bar exists for writes no second event.** The headline case
of the most actionable line in W5 is the one case a pure fold cannot see. Seeing it needs the wall
clock, which is not on the log — so `Fun::open_silence` takes `now`, and it is the half of the
query that is deliberately not a fold. On the live log it reports **7,574 minutes**, correctly: the
last event is 2026-08-30 and nothing is running.

**F589 — ⚠ `Event::RunStarted` has no counterpart, so a run's span is open at the tail.** There is
no `RunEnded`. The events after a run exits and before the next one starts are, on the log,
indistinguishable from events inside it — **an `abcc accept` typed an hour later reads as an hour
of dead air.** So a span is closed here at its **last in-flight event**: the class of events only a
running process writes, as an exhaustive `match` over `Event` with no wildcard arm, for the same
reason `line::describe` is exhaustive. Where a variant is written from both sides — `Event::Note`
is written by `abcc::desk` inside a run *and* by `abcc check` outside one — the answer is *not in
flight*. **A span that is short by one event under-reports; a span that runs on invents a silence.**

▶ The test for this is mutation-checked: reverting the span to *ends at the next `RunStarted`*
fails exactly two tests and no others.

## 4. 🚨 What it measured: the bar has been broken since Skeleton, and mostly by its own timer

`abcc fun` over this repository's log — **2,689 events, 30 runs, 64 belonging to no run**:

```
1. no dead air              BROKEN
     p50 2 ms · p95 10.0 s · max 1 m 37 s over 2595 sample(s)
     251 of 2595 gap(s) over the 10 s bar
     worst 1 m 37 s between seq 1699 and seq 1700
```

**F590 — the dead-air bar fails on our own log, 251 times in 2,595 in-run gaps.** p50 is 2 ms and
p95 is *exactly* 10.0 s, which is the shape of a cluster sitting on the threshold rather than a
tail.

**F591 — 🚨 four fifths of the breaches are the instrument, not the model.** Of the 251:

| gap | count | share |
|---|---|---|
| 10.0–10.5 s | **202** | **80.5%** |
| 10.5–12 s | 4 | 1.6% |
| 12–20 s | 12 | 4.8% |
| 20–60 s | 21 | 8.4% |
| > 60 s | 12 | 4.8% |

**237 of the 251 are *ended* by a `liveness_mark`.** And `Limits::liveness_gap` defaults to
**`Duration::from_secs(10)`** against a bar of *no gap **over** ten seconds* — **the period is set
exactly equal to the threshold, so the mark emitted to satisfy the bar arrives just the wrong side
of it.** Zero margin, by construction. Its own doc comment cites §5's bar, which is how the two
came to be the same number.

**F592 — 🚨🚨 the root cause, and it is worse than an off-by-one: the liveness mark is emitted from
inside the read loop, so it only fires when the stream is *not* silent.** `TurnLoop::drain` checks
`last_mark.elapsed() >= liveness_gap` at the top of its loop, and the next statement is
`stream.next_delta()`, which on the real provider is **`recv_timeout(self.idle_gap)` — a block of
up to 90 seconds**. During a silence the loop does not come round, so no mark is written. The
check runs only *after* a delta arrives.

> **A silence detector that rides the data path cannot observe silence.** It reports liveness
> exactly when liveness was never in doubt.

The log carries the signature plainly: **25 gaps of `model_call_started → liveness_mark`, up to
73 s** — the model's TTFB, entirely unmarked, with the first mark arriving on the first token.

**F593 — the unmarked regions are three, not one.** Of the 45 gaps over 12 s:

| shape | count | what it is |
|---|---|---|
| `model_call_started → liveness_mark` | 25 | waiting for the first token |
| `tool_call_started → tool_call_ended` | 9 | a tool child running |
| `liveness_mark → liveness_mark` | 6 | the stream stalling mid-answer |
| `checkpoint_taken → rung_recorded` | 3 | **the gate's cold build** — 78.9 s twice |
| `model_call_started → phase_ended` | 2 | a call that produced nothing: **97.1 s, 95.7 s** |

The gate rows matter because **the turn loop is not even in the picture there**: `abcc-gate` runs
a cold build per attempt, measured at 55 s and 2.3 GB in `CLAUDE.md`, and **nothing marks liveness
during it at all**. Any fix aimed only at the streaming path leaves that region dark.

▶ **Not fixed here, deliberately.** The repair is on the hang-detector path that `CLAUDE.md` guards
with three findings and a dedicated test file (F198, F199, F493, `tests/http.rs`), and the choice
between *shorten the `recv_timeout` to the liveness period and loop* and *a timer that does not ride
the stream* interacts with `idle_gap`. **It is its own change with its own tests, and the number
trades log volume against margin, which is David's call.** The query that found it is now standing.

## 5. F594 — agency reads zero, and the positive control had to be built

```
4. agency                   BROKEN
     0 control event(s) across 0 of 30 run(s)
     the control bar is decoration on this log
```

The queue item said this query *could finally return non-zero*, because the fleet control desk
landed on 2026-09-04 and was driven end to end. **It returns zero.** There is exactly one `abcc`
log on this machine and it holds **no `ControlRequested` at all**; its last event is 2026-08-30.
🚨 **The live sortie that produced one ran against a scratch `--home` that no longer exists.**

⚠ **A zero from an instrument nobody has validated is not a measurement**, so the positive control
is now a test rather than a memory: `abcc/tests/fun.rs` puts a real `ControlRequested` on a real
on-disk store, reads it back through `read_from`, and requires the query to find it — with the
same log minus the verb as the negative side, so the pass is the verb and not the fixture. The
reading stands: **on every run that survives, the control bar has never been touched.**

## 6. What this does not do

* **It does not install the three missing instruments.** §2 — that is a question for David.
* **It does not fix F592.** §4 — that is its own change.
* `Speed` is measured **to the log's edge**: every event has a line, so the next event after a
  command is the next thing the console draws, but the transport and the paint are a second hop
  nothing records. On the live log it reads `unknown`, there being no operator command on it.
* §5's *meaningful share of runs* for agency is not a number anyone has set, so the query answers
  the falsifiable half — whether the bar has been touched at all.
* The §16 additions §5 also names — unprompted opens per week, idle-open time, abandonment split
  by intervention — are not here. They need the console to be a writer, same as §2.

## 7. Verification

* **451 tests passing** (428 before), 14 ignored, **0 failing**; clippy clean under `-D warnings`; `cargo fmt
  --all --check` clean.
* **The span rule is mutation-checked.** Reverting `spans` to end at the next `RunStarted` fails
  `an_operator_command_an_hour_later_is_not_dead_air` and
  `every_event_is_either_in_a_run_or_loose`, and nothing else.
* **The log analysis is replication-checked.** The distribution tables in §4 were computed by an
  independent Python pass over `log.sqlite`, and it reproduces the Rust output exactly — 2,595
  gaps, 251 over the bar, max 97,074 ms — before any of its own numbers were read.
* Tests assert counts and not just verdicts (F586's lesson): the span test asserts the worst gap is
  **1,000 ms** rather than merely that the verdict held, so a fold that quietly swallowed the hour
  would fail even if the bar moved.

---

## Findings

**F587** — Three of ADR-0012 §5's six queries have no instrument, and the reason is architectural
rather than clerical: all three ask what the operator did at the console, and `abcc-tui` does not
depend on `abcc-store`. Installing them makes the reader a writer. They return `NoInstrument`,
never `0`, because *nothing is counting* reported as a count reads as a perfect score.

**F588** — 🚨 A fold over an event log can only see silences that **ended**; a gap needs an event on
both sides. The forty-minute hang the ten-second bar exists for writes no second event, so the
bar's headline case is precisely the case a pure fold cannot see. It needs `now`, which is not on
the log.

**F589** — ⚠ `Event::RunStarted` has no counterpart, so a run's span is open at the tail and an
operator command typed an hour later reads as an hour of dead air. A span must be closed at the
last event only a running process writes — decided by an exhaustive `match` with no wildcard arm,
answering *not in flight* for any variant written from both sides.

**F590** — The dead-air bar fails on this project's own log: **251 of 2,595 in-run gaps exceed ten
seconds**, p50 2 ms, p95 exactly 10.0 s, max 97.1 s, across 30 runs and 2,689 events.

**F591** — 🚨 **202 of those 251 breaches (80.5%) fall between 10.0 and 10.5 s, and 237 are ended by
a `liveness_mark`.** `Limits::liveness_gap` is `from_secs(10)` against a bar of *no gap over ten
seconds*: **the period equals the threshold, so the mark that exists to satisfy the bar lands just
outside it.** A period set to its own bar has no margin by construction.

**F592** — 🚨🚨 **A liveness mark emitted from inside the read loop is a silence detector that only
runs when there is no silence.** `TurnLoop::drain` checks the liveness gap at the top of a loop
whose next statement blocks in `recv_timeout(idle_gap)` for up to 90 s, so no mark is written while
the stream is quiet. The log shows 25 `model_call_started → liveness_mark` gaps of up to **73 s** —
the model's whole TTFB, unmarked, with the first mark arriving on the first token.

**F593** — The unmarked regions are three, not one: waiting for the first token, a tool child
running, and **the gate's cold build** (`checkpoint_taken → rung_recorded`, 78.9 s twice), where
the turn loop is not involved at all. A repair confined to the streaming path leaves the gate dark.

**F594** — ⚠ The agency query reads **0 control events across 30 runs**. The live sortie of
2026-09-04 that first produced one ran against a scratch `--home` that no longer exists, so the
claim *this can now return non-zero* had no surviving evidence. A zero from an unvalidated
instrument is not a measurement, so the positive control is now a test over a real on-disk store,
with the verb-free log as its negative side.
