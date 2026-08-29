# ABCC 2.0 — architecture decision records

`RESEARCH_BRIEF.md` §13:1039 asks for *"one ADR per architectural decision"*. David ruled on
2026-08-28 that these are **written during Phase 2 and dated when written** — genuine decision
records consumed by `PLAN.md`, never backfilled with dates after the fact (`research/SUMMARY.md`
§ Decisions item 2).

✅ **All fourteen were written 2026-08-28, and ADR-0015 was added 2026-08-29** — the first written
from a running system rather than from a workstream, correcting three things the first two real
runs found. The index is `PLAN.md` §7 and is mirrored below. Each traces to a closed Phase 1
workstream, and **the evidence lives in the workstream doc, not here** — an ADR cites `Wn` and a
finding id, states the ruling, and says what would overturn it. Findings F1–F502 are closed; next
free is **F503**.

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

**Every ADR is `Accepted`** — fourteen as of 2026-08-28, ADR-0015 as of 2026-08-29. Five carry a
David ruling rather than a research conclusion: **ADR-0001** (rewrite, not port), **ADR-0004** (the
lifecycle names, OQ-W3-6), **ADR-0009** (only deterministic rungs may refuse), **ADR-0012** (TUI
primary, 2026-08-19) and **ADR-0015** (three rulings, 2026-08-29). ⚠ ADR-0015 is the only one that
**supersedes another in part** — ADR-0006 § *Timeouts* — leaving the rest of ADR-0006 standing.

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
