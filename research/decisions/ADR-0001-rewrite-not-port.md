# ADR-0001 — Rewrite rather than port; the donors are a specification and a test corpus

- **Status:** ✅ Accepted
- **Date:** 2026-08-28
- **Deciders:** David (ruling, 2026-08-28), Claude Code (research)
- **Sources:** `PLAN.md` §1 · W12 F440, F442 · W3 F148, F153, F155, F166, F202 · W6 F218, F350 ·
  W7 F422 · W5 (`W5-command-center.md:80`)
- **Supersedes:** David 2026-08-07 — *"2.0 copies the engine and both stay live. No shared crate"*
  (`RESEARCH_BRIEF.md` §17 item 4)

## Context

Phase 0 mapped three donors: ABCC v1 (TypeScript, the data assets and the design language),
Claudette (Rust, the turn engine — 93 modules in one crate, F153) and BattleCommandForge (Rust, the
vocabulary). The 2026-08-07 ruling was to **copy** Claudette's engine into 2.0 and let both stay
live, with the cost accepted in writing: *fixes stop propagating and the 1,145-test suite splits in
two.*

Phase 1 then spent thirteen workstreams reading those donors, and what it produced is mostly a
catalogue of **design** defects rather than bugs:

- **Six competing assignment paths** in one scheduler, with no single writer (F155).
- **A watchdog that cannot see a NULL clock** — `assignedAt IS NULL` fails a `<` predicate by SQL
  three-valued logic, so a nulled clock makes a row permanently unwatchable; and the clock is
  written once at assignment and refreshed never, so a healthy task that runs four LLM executions
  inside one span is reaped at five minutes (F148).
- **`$transaction` appears once in the whole repository and it is a read** (F166) — in a system
  whose eight-step recovery path mutates locks, slot, status, execution rows and agent.
- **A dispatcher gated on the word `passed`**, which an all-red pytest run does not contain, so
  **eight real run-endings collapse into three records** (F350).
- **A destructive-git guard implemented twice, neither copy covering the other**, and the careful
  copy fails open (F422).

None of these is a line-level bug that a port would carry as a line. They are *shapes*, and a port
inherits shape. That is the expensive kind of inheritance, because it is the kind that survives
review.

Two independent Phase 1 conclusions point the same way. **W12 already ruled this way at smaller
scope** — reimplement what the four outside contributors added, so 2.0 ships MIT OR Apache-2.0 with
no inherited-code caveat, after a blame sweep over all 395 tracked files found **944 outside-authored
lines in 20 files** (F442). And the repository **thanks five upstream projects and zero humans**
(F440, `README.md:759`), which is a debt paid by writing the replacement, not by copying it.

## Decision

🚨 **Rewrite everything. Do not port.** David, 2026-08-28:

> *"i prefer we rewrite everything rather than porting. The donors were written by opus 4.5 and opus
> 4.6 — you are much better — so i prefer you read the donor files, then rewrite instead of
> importing verbatim."*

**The rule in one line: the donors become a SPECIFICATION and a TEST CORPUS, never a source tree.**
Every `file:line` citation in `research/` is a citation of *reference behaviour and its known
defects*, not an import instruction. Read the donor, understand what it got right, write the
replacement, and **use its catalogued defect as a test case** — Phase 1 handed over hundreds of them
already localised.

### Scope, stated precisely

Most of the build was already new code: the event log, the two-level phase model, the slot, the
conjunction gate and its Outcome type, and the whole routing position were specified as new in
Phase 1. The ruling therefore bites in exactly three places, and is explicitly carved away from a
fourth:

| | Was going to be | Now |
|---|---|---|
| Claudette's turn engine + tool layer (93 modules, one crate — F153) | copied | **rewritten to the contracts in W3/W6/W10** |
| The 3,011 inherited Ratatui lines (`W5-command-center.md:80`) | ported | **rewritten**; they stay as reference for what worked |
| v1's 44 MB of art + audio, the 96 voice lines, ~1,903 lines of identity | copied | **still copied — these are assets and they are David's** |
| `harness/crates/` — `hw-probe`, `w8-run`, `w8-corpus`, the three importers | ours already | **UNCHANGED — it is the instrument, not the product** |

⚠ **The harness carve-out is load-bearing** (`PLAN.md` §9.4). Every rate in the corpus — the 1,369
preserved cells, Q56, K, the 40-task floor check — came out of `harness/crates/`, and **changing the
instrument changes what those numbers mean**; F59 already showed this box drifts between sessions.
2.0 *consumes* the harness's output and does not reimplement it.

## Consequences

- **The cost of the 2026-08-07 ruling is paid up front rather than gradually.** The suite was going
  to split in two the first time either side diverged; it now splits on day one, deliberately, with
  the donor suite retained as a corpus to test against rather than a suite to keep green.
- **The licensing claim becomes true by construction.** *No inherited code* stops being the output
  of a blame sweep and becomes a property of how the code was written (W12, F442).
- 🚨 **The donors' working parts must be re-earned, and they are real.** Three named ones, because
  they are the ones a rewrite is most likely to lose: **the drain-on-threads fix** — Claudette
  drains child pipes on background threads so a child writing past the 64 KiB pipe buffer cannot
  deadlock, where BCF's runner strangles a finished tool and records a timeout (F202); **the
  exit-code rungs Claudette alone reads**, including pytest exit 5 = no tests collected; and
  **`Option<bool>` in `BuildTestOutcome`** (F218), which is `Measured | Unmeasured(Why)` already
  working in the family, at the exact site where BCF defaults to 5.0.
- **It retires a falsifier and creates one.** SUMMARY.md's *"`Provider` cannot be made `&self` +
  stream without forking the engine past a maintainable delta"* cannot fire — there is no fork. See
  below for its replacement.
- **`research/SUMMARY.md` gets a dated amendment, not a silent edit** — it is signed off and
  committed (`67cd3e3`). Done: two struck lines pointing at `PLAN.md` §1.

## Alternatives rejected

- **Port the engine and correct as we go** — the 2026-08-07 position. Rejected because the
  corrections Phase 1 identified are structural: one write path instead of six (F155), a per-state
  contract instead of a nulled clock (F148), a transaction around the recovery path (F166), an
  outcome type instead of a substring test (F350). Applying all of those to a port is a rewrite
  performed in the worst order — with the old shape still holding the pen.
- **Share a crate with Claudette** — rejected 2026-08-07 and not reopened; the donors stay live and
  independent.
- **Fork Claudette and track upstream** — the maintainable-delta option. It is what the retired
  falsifier was about, and the rewrite removes both the delta and the tracking cost.

## What would falsify this

⚠ **NEW FALSIFIER — the rewrite does not re-earn the engine's working behaviour inside the Skeleton
and Gate milestones.** This is a *schedule* risk, not an architecture one. The donors' working parts
are real and debugged; if re-earning them is still open when Gate should be closing, the ruling was
too broad and **the turn loop goes back on the table as a port** — that one component, named, rather
than the ruling as a whole.
