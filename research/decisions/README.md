# ABCC 2.0 — architecture decision records

`RESEARCH_BRIEF.md` §13:1039 asks for *"one ADR per architectural decision"*. David ruled on
2026-08-28 that these are **written during Phase 2 and dated when written** — genuine decision
records consumed by `PLAN.md`, never backfilled with dates after the fact (`research/SUMMARY.md`
§ Decisions item 2).

✅ **All fourteen were written 2026-08-28, and ADR-0015 was added 2026-08-29** — the first written
from a running system rather than from a workstream, correcting three things the first two real
runs found, and **ADR-0016** the same day from ten of them. The index is `PLAN.md` §7 and is mirrored below. Each traces to a closed Phase 1
workstream, and **the evidence lives in the workstream doc, not here** — an ADR cites `Wn` and a
finding id, states the ruling, and says what would overturn it. Findings F1–F562 are closed; next
free is **F563**.

## The template

```markdown
# ADR-NNNN — <the decision, as a sentence>

- **Status:** Accepted | Superseded by ADR-NNNN | Proposed
- **Date:** YYYY-MM-DD (when written, not when decided)
- **Deciders:** who ruled
- **Sources:** the workstream doc and the finding ids that carry the evidence

## Context          — the question, and what the donors actually do
## Decision         — the ruling, stated not re-argued
## Consequences     — what this costs, what it makes unrepresentable, what it hands onward
## Alternatives rejected — each with the measurement that rejected it
## What would falsify this — the observation that would reopen it
```

▶ **Two conventions that are not optional.** (1) **A number in an ADR is quoted from a named
finding** — the standing rule is verify against code, not docs, and an ADR is a doc. (2) **An ADR
records a decision, it does not restate the architecture.** Where an ADR and `research/SUMMARY.md`
disagree, SUMMARY.md wins and the ADR is wrong.

## Index

| # | File | Decision | Source |
|---|---|---|---|
| 1 | [ADR-0001](ADR-0001-rewrite-not-port.md) | Rewrite rather than port; donors are specification and test corpus | `PLAN.md` §1, W12, W3 |
| 2 | [ADR-0002](ADR-0002-two-levels-four-phases.md) | Two levels, four phases each; Router/Tester/CTO are not phases | W11, W6 |
| 3 | [ADR-0003](ADR-0003-slot-is-the-unit.md) | The unit is a runtime slot, N=2, set by VRAM | W11, W2, W1 |
| 4 | [ADR-0004](ADR-0004-task-lifecycle.md) | Nine-variant lifecycle, one write path, attempts immutable | W3, W5 |
| 5 | [ADR-0005](ADR-0005-sqlite-event-log.md) | SQLite event log, WAL + FULL, status a projection, boot = replay | W3, W5 |
| 6 | [ADR-0006](ADR-0006-threads-own-the-work.md) | Threads own the work; one runtime at the console edge | W3, W2 |
| 7 | [ADR-0007](ADR-0007-worktree-isolation.md) | Worktree isolation at a temp-index snapshot sha | W6, W11 |
| 8 | [ADR-0008](ADR-0008-gate-is-a-conjunction-of-refusals.md) | The gate is a conjunction of refusals | W6, W11 |
| 9 | [ADR-0009](ADR-0009-measured-or-unmeasured.md) | `Measured \| Unmeasured(Why)`; **only deterministic rungs refuse** | W6, David 08-28 |
| 10 | [ADR-0010](ADR-0010-no-estimate-one-tier-retry-2.md) | No pre-dispatch estimate; one tier; retry budget 2 | W4, W1, W2 |
| 11 | [ADR-0011](ADR-0011-model-roster-and-frozen-heads.md) | Model roster; enumerate and freeze the tool-head set | W1, W2, W11 |
| 12 | [ADR-0012](ADR-0012-ratatui-sixel-console.md) | Ratatui + sixel primary; SSE + SQLite; one `seq` | W5 |
| 13 | [ADR-0013](ADR-0013-two-modes-rig-as-device.md) | Two modes; rig as device; `Provider` `&self` + stream | W10, W9 |
| 14 | [ADR-0014](ADR-0014-deny-the-class-blast-radius.md) | Deny the class via `max_tier`; blast radius, not a sandbox | W7, W8 |
| 15 | [ADR-0015](ADR-0015-what-the-first-real-runs-corrected.md) | The idle gap is ours; a full window is not a fault; silence is not an artifact | F493, F496–F502 |
| 16 | [ADR-0016](ADR-0016-a-phase-repairs-a-missing-answer.md) | A phase asks again when the model says nothing; a cut turn's tool calls never run | F503–F508 |
| 17 | [ADR-0017](ADR-0017-the-standard-a-repository-declares.md) | The rung a repository declares for itself; the veto's one rule; `Refused` | F512, F516–F518 |
| 18 | [ADR-0018](ADR-0018-the-judge-reports-and-cannot-refuse.md) | The Judge reports: it cannot refuse an attempt **and cannot fail one** | ADR-0008, F275–F284, F521–F522 |
| 19 | [ADR-0019](ADR-0019-the-judge-keeps-the-rung-output.md) | The Judge keeps the rungs' counts and output — withholding them was probed and lost | F531, F534–F536 |
| **20** | [ADR-0020](ADR-0020-one-slot-for-now-and-a-delta-not-a-ceiling.md) | **One slot (N=1) for now**; the memory clause is a **delta + `min_avail_mib` + the blind window** | F539–F547 |
| **21** | [ADR-0021](ADR-0021-the-idle-gap-watches-delivery-not-content.md) | The idle gap watches whether the stream is **delivering**, not whether the model is **saying** anything | F537, F538 |
| **22** | [ADR-0022](ADR-0022-the-budget-is-two-attempts-and-a-landing-may-not-foreclose-it.md) | **Budget 2 = two attempts, one retry**; and a landing may not foreclose the recommendation beside it | F548, F549 |
| **23** | [ADR-0023](ADR-0023-a-slot-narrows-the-head-not-just-the-check.md) | A slot's ceiling **narrows the head itself**, not just the check under it — the advertised and enforced surfaces are one list | F404–F422, F551, F552 |
| **24** | [ADR-0024](ADR-0024-the-standard-is-a-conjunction.md) | A declared standard is a **conjunction of commands**, and `cargo fmt --check` is in the cargo one, first | F555, F557 |
| **25** | [ADR-0025](ADR-0025-a-pulse-is-a-measurement-and-may-refuse.md) | A **pulse may stop a preflight** because it is a measurement; the rate may not because it is a verdict; `NotTaken` never refuses | F539, F550 |

**Every ADR is `Accepted`** — fourteen as of 2026-08-28, ADR-0015 through ADR-0019 as of
2026-08-29, and ADR-0020 through ADR-0025 as of 2026-08-30. ⚠ **ADR-0017 and ADR-0018 carried
2026-08-30 and 2026-08-31 until 2026-08-30 (F556)**, and both were corrected against the commit
that added the file — `df6c55c` and `4f65779`, both 2026-08-29. The other twenty agree exactly.
The opening of this file is why it matters: a record *"never backfilled with dates after the fact"*
is a claim about its dates being true. ⚠ ADR-0017 is the first written **from a
running system rather than before one**: the gate was built and put to all 25 real attempts on the
log, and only then was its one open question put to David. ADR-0018 is written the same way, from
two live reviews — and it is the one that **corrected a prompt this project had already
shipped**: `Head::Commandos`' charter promised the reviewer Recon's brief, and the only measurement
about prose beside a diff is 0 of 3, so the charter was changed to match the evidence rather than
the evidence assumed to match the charter. 🚨 **ADR-0019 is the first decided by a PROBE rather than by an argument or a
ruling**: F531 left an open question about the brief, David's answer was *measure it before you
change it*, and the measurement — 15 calls over 3 shams under both views — says the change loses.
The rejected alternative is kept in the tree as the instrument that rejected it. **Eleven** carry a
David ruling rather than a research conclusion: **ADR-0001** (rewrite, not port), **ADR-0004** (the
lifecycle names, OQ-W3-6), **ADR-0009** (only deterministic rungs may refuse), **ADR-0012** (TUI
primary, 2026-08-19), **ADR-0015** (three rulings, 2026-08-29), **ADR-0017** (a correct tree is
one that could land, 2026-08-30), **ADR-0019** (probe the shams before changing the brief,
2026-08-29), **ADR-0020** (one slot, and a delta rather than a ceiling, 2026-08-30) **ADR-0022** (two attempts, and lands `Queued` rather than `Failed`, 2026-08-30), **ADR-0024**
(add `cargo fmt --check` unconditionally, 2026-08-30) and **ADR-0025** (a silent pulse refuses a
preflight, 2026-08-30). 🚨 **Six supersede another in part, and none supersedes one whole.** ADR-0015 takes ADR-0006 § *Timeouts*; **ADR-0020** takes **ADR-0003's *count* only** — N=2 – 1, with the slot abstraction and every other consequence intact, and revises ADR-0006's thread-inventory row *attempt workers = 2* to **1**; **ADR-0021** amends **ADR-0015 §1**, which established that the gap is ours but left *what a gap is* implicit — and it was implemented as *no delta arrived*, which is a content detector; **ADR-0022** amends **ADR-0010 §2 and §3**, which set the budget and stated it in two ways the shipped `Cause` enum reads differently — the stopping rule stands and *what the number counts* is fixed; **ADR-0024** amends **ADR-0017**, whose rung keeps its purpose and changes its shape from one command to a list; and **ADR-0025** **scopes ADR-0010 §4** rather than weakening it — *reports and never gates* is about the **rate**, which cannot tell a hard task from a dead server, and a pulse is a measurement that can.

🚨 **ADR-0022 is the first found by BUILDING the receiver rather than by measuring or arguing.** `abcc-drive` had returned a `NextAction` since Skeleton and its own doc said nothing was built to receive it; the moment something did, two values that were each correct in isolation turned out to contradict each other — `next: Attempt` beside a terminal landing, both asserted in a passing test since Skeleton. ⚠ **A recommendation nothing receives is a recommendation nothing checks.**

🚨 **ADR-0020 and ADR-0021 are the first pair where the probe overturned the premise it was written to test.** `PLAN.md`'s FLEET milestone existed because *two turns in flight push each other past the 90 s idle gap*; that had never been measured, is false (F545), and the thing actually killing turns was the detector itself (F537) — caught only because `hw-probe` was sampling the GPU at 75% utilisation through a 90-second *"silence"*. ⚠ **ADR-0020's N=1 is NOT ADR-0003's own falsifier firing**: two slots plus two worktrees plus real builds *held* inside 31.92 GiB. The count drops because the second slot bought nothing measurable (F546), which is the opposite reason.

## What the ADRs changed while being written

- ⚠ **Two ADRs record a ruling that the rewrite decision partly voided, and say so rather than
  quietly dropping it.** ADR-0006 keeps W3's dependency list as a *specification* — the crates are
  still right, but *"arrives with the copy"* is void, and so is the fourth argument against an
  all-tokio core (*it ends the option of tracking Claudette upstream*); the other three are
  measurements and stand alone. ADR-0011 does the same for `post_with_model_reload_retry`: **the six
  matched surface forms are the specification; the code is written fresh.**
- ⚠ **`W4-routing.md`'s status header was stale and is corrected, dated, in place** — it read *OPEN,
  items 1, 2 and 3 of 6 closed* over a body that carries all six items and runs to F399.
- ⚠ **F59 is cited in three research documents and defined in none of them** — the same shape W6
  found for F22–F29 (*"cited 23 times in six documents and defined in none"*). ADR-0001 and ADR-0011
  cite it as the corpus does, for the fact that the token baseline steps ~10% between sessions.
  Nothing depends on it that a same-session baseline does not already enforce (F488).

⚠ **`research/benchmarks/` is deliberately not created.** §13 lists it, and it is satisfied in
substance: `research/spikes/` holds the reproducible drivers, and `runs/hw-probe/` plus the 62
`runmeta.json` manifests are tracked as of `67cd3e3`. A third location for the same artifacts would
be a place for them to disagree (`PLAN.md` §7).
