# ADR-0019 — The Judge keeps the rungs' counts and output, because withholding them was measured and lost

- **Status:** ✅ **Accepted** — decided by a probe rather than by argument
- **Date:** 2026-08-29
- **Deciders:** **David's ruling of 2026-08-29** on F531's open question — *probe the three shams
  first* — and this file records what the probe said. The alternative was a one-line change to
  `judge::rungs`; it is not being made.
- **Sources:** **F531** (the Judge is 0 for 3 on the shams and cites the rungs while doing it) ·
  **F534** (two of the three shams' defects are not in the dossier at all, and one hunk is
  byte-identical to the answer key) · **F535** (the counter reads `findings.len()`) · **F536** (the
  probe, 15 calls) · **F522** (the completion is 93–96% reasoning trace) · ADR-0008's four rules ·
  ADR-0009 (`Measured | Unmeasured(Why)`) · artifacts `research/corpus-run/reviews-{full,named}-{a,b}/`
- **Extends:** ADR-0018 (this is a decision about the brief that ADR-0018 built)
- **Depends on:** ADR-0008 (rule 1, *show it the artifact and not the verdict on it*), ADR-0009

## Context

ADR-0018 built the Judge's brief under a rule it held on purpose: **the reviewer is shown every
rung and not the conjunction they add up to**, because *a reviewer shown the decision is a reviewer
asked to agree with it*. The rungs it is shown carry their exit status, their `counts` where they
have them, and the output they captured.

**F531 found that the withheld headline arrived anyway.** On the three sham trees — the corpus's own
tempting local fix, which repairs the symptom the ticket named and leaves the defect — the reviewer
reported *"Defects: None found"* on 3 of 3 **while citing the rungs as the proof**, and on one of
them turned the acceptance rung's `18 run / 18 passed` into *"the host's acceptance suite confirms
all eighteen discrepancies are resolved"* about a tree where **7 of 18 invoices are still wrong**.
Eighteen tests and eighteen invoices are not the same quantity: F517's defect class, in the model's
voice.

The obvious inference is that the rung output is doing the headline's job and should be withheld.
**David declined to rule on the inference and asked for the measurement**, which is the standing
*probe rather than assume*. This file is that measurement.

## Decision

🚨 **`judge::RungView::Full` stays the shipped view. The Judge continues to see each rung's exit
status, `counts` and captured output.**

`RungView::Named` — which renders each rung as `- acceptance — measured` and nothing else — **is
kept in the tree as the instrument that produced this decision**, not as a switch anybody is meant
to flip. It is reachable only by `ABCC_JUDGE_RUNGS=named` from `tests/corpus_review.rs`; `brief`
calls `Full`; no production caller passes a view at all, and `abcc-drive` is unchanged.

⚠ **The probe changed exactly one thing.** The task, the diff and every sentence of instruction are
byte-identical across the two views, asserted by
`the_view_moves_the_rungs_and_nothing_else_in_the_brief`.

### The three reasons, in the order they matter (F536)

**15 calls: 3 shams × 2 views × 2 fresh samples, plus the original run's 3.** Nothing here is
sampled at temperature zero — the engine sends no `temperature`, no `top_p`, no `seed` — so the
control was run first: **9 of 9 `Full` calls returned 0 findings.** F531 is behaviour, not a sample.

| view | calls | findings | cites the rungs as proof | says it cannot verify | median s |
|---|---|---|---|---|---|
| `Full` | 9 | **0** | **7 of 9** | 1 of 9 | 60.5 |
| `Named` | 6 | **5** | **1 of 6** | 2 of 6 | 96.6 |

1. 🚨 **Four of the five findings are wrong, and one of them is wrong *because* of the change.**
   `round_at_the_line (named-b)` returned three: an `import math` "overhead" defect that Python's
   module cache makes false; a speculative float-drift claim that is not the defect; and
   *"`money.EPSILON` ... `NameError` if absent"* — **on a tree that runs and whose suite passes.**
   Under `Full` the reviewer could see that and never made the claim. **Withholding the measurement
   did not make it humble; it made it invent a runtime crash.** The fourth flags `st.is_terminal`,
   which F534 shows is the one hunk **byte-identical to the answer key**.
2. 🚨 **The failure mode returned in the new wording.** `trace_dropped_samples (named-b)`, with no
   counts and no output anywhere in its brief, wrote *"the host measurements already confirm
   structural, acceptance, and veto checks pass."* **Nothing in that brief says any rung passed** —
   it read `measured` as *passed* and supplied the verdict itself. That is the hazard
   `abcc_core::outcome` exists to remove, arriving from the model's side of the prompt. Removing the
   evidence removed the citation, not the conclusion.
3. **It costs 1.6× the median wall clock and up to 3×** — `round_at_the_line (named-a)` spent
   **191.9 s and 11,990 completion tokens** against 60.5 s and 4,036 for the same tree under `Full`,
   and returned nothing. F522 says the completion is 93–96% reasoning trace, so that is the trace
   growing with less to work from.

✅ **One of the five is correct**, and it is worth naming: `trace_dropped_samples (named-a)` — *"the
fix suppresses symptoms rather than resolving why sample volumes are lower than expected."* That is
the sham's real defect, on the tree F534 shows the defect is not in the diff for. **It is the only
correct sham finding in all 15 calls, under either view.** One is not a rate, and it was bought with
four wrong ones.

## Consequences

* **The Judge's brief is unchanged, so every number in `ACCEPTANCE-C-corpora.md` still describes the
  shipped system.** Recall 44 of 46, 0 confirmed false positives on 59 correct trees, 87 findings at
  a median of 1 per tree — all of them measured under `Full`, which is what ships.
* 🚨 **F531 is not retracted and it is not fixed.** Under `Full` the reviewer cited the rungs as
  proof in **7 of 9** calls on the shams and manufactured a count on one of them. That is a real
  cost and it is now a *known* cost with a measured alternative that is worse. **A reassuring report
  about a change that leaves seven bad invoices still spends trust**, and nothing here changes that.
* **The sham tier stays the falsifier's sharpest instrument** and it is 3 trees. Anything that claims
  to fix F531 has to beat `Full` on those three *and* not lose precision on the correct trees, which
  this probe did not measure at all — 6 calls, all on shams.
* `RungView` costs one enum, one `brief_with`, and two tests. It is the cheapest way to re-ask this
  question when the population grows.

## Alternatives rejected

* **Withhold `counts` and stdout, keep the exit status.** Not probed separately. The probe tested the
  strict end deliberately: if the strict end had won, the middle would be worth measuring, and it
  did not.
* **Withhold everything but which rungs ran** — this is `Named`, and it is what lost. See above.
* **Show the headline as well, since the rung output leaks it anyway.** Rejected: F536 point 2 shows
  the model will supply a verdict from thin material, so handing it a real one makes the agreement
  problem worse, not honest. ADR-0008 rule 1 stands.
* **Let the Judge refuse on a sham.** Not available and not wanted: *only deterministic rungs may
  refuse* (David, 2026-08-28), and F536's four wrong findings are the argument for why.

## What would falsify this

🎉 **The probe found the better lead by accident, and it is the falsifier.** The best answer in all
15 calls came from **`Full`** — `finish_the_cancelled_status (full-b)`, with the counts and stdout
in front of it:

> *"the task explicitly requires treating cancelled jobs correctly **everywhere** it makes a decision
> based on status ... this diff only modifies one file and **I do not have visibility into the other
> five consumers** ... I cannot verify full spec compliance."*

That is F534's *correct-but-incomplete* read, reached **with** the rung output visible and not used
as a warrant. So the discriminating variable is not what the reviewer was shown; it is **whether it
checked the change against the scope the ticket states** — and two of the three shams state their
scope in the ticket in so many words.

▶ **So this ADR is falsified by a brief change beating `Full` on the shams without losing precision
on the correct trees:** one sentence asking whether the change covers the scope the task states, and
whether anything it depends on lies outside the diff. **It is deliberately not written here.** It has
a population of one call, and an ADR for a decision nobody has made is a name standing in for a
specification. The experiment is cheap and already built: three shams, two samples, one switch.

⚠ **A second falsifier, from F535.** That best answer was scored **`0 findings, silent`** by the
instrument, because the counter reads `findings.len()`. Any conclusion in this file drawn from a
findings count is drawn from a counter that has now been wrong twice — `q56-Q05` and
`finish_the_cancelled_status (full-b)`. The prose flag added this session catches the first shape
and **not** the second: a correct refusal to endorse is a third thing `findings[]`/`silent` cannot
express, and nothing here measures how often it happens.
