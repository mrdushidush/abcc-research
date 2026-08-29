# ABCC 2.0 — Phase 2: the build plan

**Phase 1 closed 2026-08-28** (`67cd3e3`): 13 workstream docs, 2 acceptance sweeps, `research/SUMMARY.md`
approved, all eight §16 criteria met, findings F1–F488. **This document is the Phase 2 deliverable**
— §1:47 *"turn the research into a sequenced build plan with milestones"*. ✅ **APPROVED by David
2026-08-28, so the Phase 2 gate is met**, with one clarification folded into ground rule 6 below.
Phase 3 is co-development: the first line of ABCC 2.0 is written there, not here.

▶ **This plan does not restate the architecture.** `research/SUMMARY.md` is the architecture, it is
signed off, and it is two pages. This document answers *in what order, against which risk, and who
writes it.* Where the two disagree, SUMMARY.md wins and this file is wrong.

⚠ **Naming, so nobody collides them again:** W13 owns **M0–M3**, the *self-hosting* ladder measured
in human review minutes, whose **M0 is already taken by v1**. The build milestones below are
**named, never numbered**, for exactly that reason. The two ladders are orthogonal and run
concurrently.

---

## 1. What changed after SUMMARY.md was signed — David, 2026-08-28

🚨 **REWRITE, DO NOT PORT. This supersedes the ruling of 2026-08-07.**

David: *"i prefer we rewrite everything rather than porting. The donors were written by opus 4.5 and
opus 4.6 — you are much better — so i prefer you read the donor files, then rewrite instead of
importing verbatim."*

The 2026-08-07 decision was *"2.0 copies the engine and both stay live. No shared crate"*, with the
accepted cost that *"fixes stop propagating and the 1,145-test suite splits in two"*
(`RESEARCH_BRIEF.md` §17 item 4). **That cost is now paid up front instead of gradually**, and the
new position is stronger for three reasons the research already established:

- **Phase 1 is mostly a catalogue of donor *design* defects, not bugs.** Six assignment paths with
  differing invariants; a watchdog that cannot see a NULL clock; `$transaction` used once in the
  whole repo and it is a read; a dispatcher gated on the word `passed` that turns eight run-endings
  into three records; a destructive-git guard that exists twice with neither copy covering the
  other. **A port inherits those as shape**, which is the expensive kind of inheritance.
- **W12 already ruled this way at smaller scope** — reimplement what the four outside contributors
  added, so 2.0 ships MIT OR Apache-2.0 with no inherited-code caveat. This generalises that
  instinct rather than reversing anything.
- **The licensing story gets simpler, not harder.** A clean-room rewrite makes the *no inherited
  code* claim true by construction instead of by a blame sweep.

### What the ruling actually costs, scoped precisely

**Most of the build was already new code.** The event log, the two-level phase model, the slot, the
conjunction gate and its Outcome type, and the whole routing position (*ship none of what they
have*) were specified as new in Phase 1. The ruling therefore bites in exactly three places:

| | Was going to be | Now |
|---|---|---|
| Claudette's turn engine + tool layer (93 modules, one crate) | copied | **rewritten to the contracts in W3/W6/W10** |
| The 3,011 inherited Ratatui lines | ported | **rewritten**; they stay as reference for what worked |
| v1's 44 MB of art + audio, the 96 voice lines, ~1,903 lines of identity | copied | **still copied — these are assets and they are David's** |
| `harness/crates/` — hw-probe, w8-run, w8-corpus and the three importers | ours already | **UNCHANGED — it is the instrument, not the product** (§9.4) |

▶ **The rule in one line: the donors become a SPECIFICATION and a TEST CORPUS, never a source
tree.** Every `file:line` citation in `research/` is now a citation of *reference behaviour and its
known defects*, not an import instruction. Read the donor, understand what it got right, write the
replacement, and **use its catalogued defect as a test case** — Phase 1 handed us hundreds of them
already localised.

### It retires one falsifier and creates another

SUMMARY.md's falsifier *"`Provider` cannot be made `&self` + stream without forking the engine past
a maintainable delta"* **cannot fire** — there is no fork. It is replaced by a **schedule** risk,
not an architecture one:

> ⚠ **NEW FALSIFIER: the rewrite does not re-earn the engine's working behaviour inside the
> Skeleton and Gate milestones.** The donors' *working* parts are real and debugged — the
> drain-on-threads fix, the exit-code rungs Claudette alone reads, `Option<bool>` in
> `BuildTestOutcome`. If re-earning them is still open when Gate should be closing, the ruling was
> too broad and the engine's turn loop goes back on the table as a port.

**Action this creates:** `research/SUMMARY.md` is signed off and committed, so it gets a **dated
amendment**, not a silent edit — one line under *What would falsify*, pointing here.

---

## 2. Ground rules for the build

1. **Rewrite, do not port.** §1 above. Assets are copied; code is written.
2. **A model verdict is a report and never a gate** — the corpus's most reused ruling, and as of
   2026-08-28 held **strictly**: 🚨 **only deterministic rungs may refuse. The Judge never blocks.**
3. **Every gate is a conjunction of refusals**, never a weighted average, never a threshold.
4. **`Measured | Unmeasured(Why)` from the first commit that runs anything.** A `Claim` must have no
   function that converts it into an `Outcome`. This is the one type that must not be added later.
5. **Verify against code, not docs** — 51 items in the standing memory, and item 50 was earned this
   week. When a number gates a decision, re-derive it.
6. 🚨 **Probe rather than assume — David, 2026-08-28: *"better check stuff then assume. The box and
   gpu are available to probe and use."*** A question a load or a probe can settle gets settled that
   way, in the same session, rather than reasoned around. This **supersedes** the Phase 1 rule that
   no probe ran without asking — that rule was written when the GPU was the scarce half of a
   research budget, and Phase 3 writes code against a live box. ⚠ **The one check that remains: ask
   before a HEAVY GPU session**, so David can confirm the card is free and ambient temperature is
   not too high — he has killed a running campaign for heat. *A single load, a probe or a 40-task
   run needs no permission; a multi-hour campaign does.* Pre-flight the spill fix either way: a
   spilled load still answers every request and still reports a plausible number.
7. **One vocabulary per entity.** Never a mega-enum; the nine-variant lifecycle is ratified.
8. **The RTS vocabulary is load-bearing, not decoration** — W9 found it is the *only* differentiator
   the evidence supports (zero game/RTS/sprite vocabulary across 340 comparable projects). It is the
   last thing to cut, not the first.

---

## 3. The milestone spine

Six milestones. Each states what exists at the end, **which falsifier it retires**, and an exit
criterion that is checkable rather than felt.

### ▶ SKELETON — one attempt, end to end, on a real repository task

**Goal:** the thinnest possible vertical slice that is architecturally honest. No gate, no fleet, no
sprites.

**Exists at the end:** the SQLite event log with `WAL` + `synchronous=FULL` and the single
transition writer · the nine-variant lifecycle as data-carrying variants over `since: Seq` · status
as a projection and boot as replay (same code path) · one slot running one attempt through
Localize → Change on a real repo · the git-worktree checkpoint composition, with the snapshot sha
**written to a ref** · the rewritten turn loop and tool layer with the control point answering
`Pause/Halt/Kill/Redirect` · **review-minute instrumentation** (see §5) · 🚨 **a plain-text Ratatui
reader over the event log — no sprites, no battlefield** (David, 2026-08-28).

**Why the reader is here and not at Console:** the event log is Console's only input, so *"every
milestone emits events in the shape Console reads"* is otherwise a **written rule nothing checks**.
A real reader turns it into a compile-and-run failure the day it is violated. It is cheap, it is
thrown away by nothing — Console extends it — and it retires the rework risk with code instead of
discipline. **The sixel battlefield still lands at Console**, on a read path already proven.

**Retires:** the new schedule falsifier from §1 — this is where "can we re-earn the engine" is
answered, first and cheaply — **and the Console-rewrite risk from §4**.

**Exit:** one real task on this repository runs to a durable terminal state; killing the process
mid-attempt and restarting reconstructs identical status from the log alone, **and the reader shows
that run without reading anything but the log.**

✅ **CLOSED 2026-08-29.** Every clause is met by something that was run rather than argued: ten real
attempts on this repository's own code, two named durability tests for the kill-and-restart half,
and `abcc watch` driven by David in a real terminal — which is what found F501. 🎉 **Run 10 went
further than the criterion asks**: it implemented `--version` completely, fixed the exhaustive-match
test its own change broke, and compiles and passes all 64 `abcc` tests — while failing
`clippy -D warnings` by one line, which is the Gate demonstrated before the Gate exists. The code is
`D:/dev/abcc`; see ADR-0015 and ADR-0016 for what the runs corrected.

### ▶ GATE — the part that is actually the product

**Goal:** make right-vs-wrong separable. SUMMARY.md's risk 3 says this is where the product lives
and that the best instrument found catches under half.

**Exists at the end:** Measure as a no-model phase returning tri-state · the free structural rung ·
the acceptance test rung · Judge as one model call that **sees the measurements**, with pairwise
comparison against the pre-image rather than a pointwise score · Veto as deterministic
non-scoring refusal · the full `Measured | Unmeasured(Why)` outcome type with a `Green` that
requires every declared rung to have been measured · **a review finding carries something
runnable** or it is not a finding.

#### 🚨 The Judge never refuses — David, 2026-08-28

**Only deterministic rungs may refuse.** Unattended `Accept` is gated on the structural rung, the
acceptance test and Veto — nothing else. **The Judge reports, and its report is never a vote.**

This is the corpus's most reused ruling held *strictly* rather than nearly, and it removes a tuning
knob instead of setting one: **there is no false-fail rate to pick, because a false fail is a bug in
a rung.** The measured base is 0 false positives on 609 correct trees. The earlier draft's "a few
percent" quietly assumed the Judge could block, which contradicted the ruling it was written under.

**The accepted cost, stated plainly:** the wrong trees only a model would catch — Phase 1 measured
10 of 23 — now reach David as **reports rather than blocks**. That is the trade, and it is the right
way round, because a report costs attention while a false block costs trust.

⚠ **This replaces the falsifier too.** False-fails are ~0 by construction, so the exposure moves:
> **NEW FALSIFIER: the wrong trees reaching David as reports are frequent enough that unattended
> `Accept` is not worth having.** Then the Judge earns a refusal on a named, closed class of defects
> — never a global threshold.

**Retires:** *the conjunction gate false-fails more than a few percent of correct trees* — by
construction rather than by measurement.

**Exit:** run against the Q56 and K corpora, whose answer keys already exist. **Zero false fails on
the correct-tree population**, any one of them fixed as a rung defect before the milestone closes;
and the report volume on wrong trees measured, so the new falsifier above has a number.

⏳ **HALF BUILT, 2026-08-30 (`a3ca3fa`, ADR-0017).** The deterministic half is running: `abcc-gate`
is the eighth crate, the ladder is `structural → acceptance → veto → standard`, and **the
conjunction is `Report::headline` rather than code** — so the Judge, when it arrives, has nothing
to wire a vote into. 🎉 **F518: it was run against all 25 real attempts on this project's own log
and refused 25 of 25** — 16 structural at 0.0 s, 7 veto (*the tree does not build*), 2 standard
(*every test passes; clippy refuses at 101/100*), and **0 by the acceptance rung, which never once
fired.** `Accomplished` is reachable for the first time, said by `Headline::Green` and by nothing
else.

▶ **What is left:** the Judge as one model call seeing the measurements, pairwise against the
pre-image · schema-constrained decoding, which arrives with it · the Q56 and K corpora run · the
report-volume number. 🚨 **And one question that is David's** — ADR-0017 § *What is David's*:
whether *correct tree* in the criterion above means **correct** or means **mergeable**. F512's runs
10 and 23 compile, pass 281 and 288 tests, and are refused for a function one line over this
repository's own limit. Under the first reading the standard rung false-fails 2 of 2 and is a rung
defect; under the second it has zero false fails and this population contains no correct trees at
all. One entry in a `const` decides it.

### ▶ FLEET — two slots on one box

**Goal:** answer SUMMARY.md's risk 2 with the real workload rather than an idle probe.

**Exists at the end:** admission as a projection of the store · two slots with a resident model and
a tool policy each · workspaces isolated and **the gate serialized** · the tool-head set enumerated
and frozen per attempt · `NextAction { Attempt | Stop | HandToOperator }` with retry budget 2 and no
pre-dispatch estimate · the breaker that reports and never gates.

**Retires:** *two slots plus a worktree plus a real build cannot hold inside 31.92 GiB.*

**Exit:** two concurrent attempts, each with a worktree and a real build, measured with `hw-probe`
against a **same-session baseline** (F488 — a `peak_committed_b` quoted across sessions is
meaningless). Peak must stay under the 28.03 GiB ceiling of record with the box still responsive.

### ▶ CONSOLE — the reason to use it

**Goal:** the flagship. Ratatui primary, SSE + SQLite, one `seq` as event id / `Last-Event-ID` /
paged-read cursor / scrub position, and the C&C-1995 isometric sixel battlefield.

**Exists at the end:** the battle screen answering its six questions · the after-action screen that
replay-as-primary makes nearly free · eight operator verbs over three mechanisms · the 96 voice
lines · **fun as six queries over the event log**, with the 10-second attention bar honoured.

**Retires:** *the sixel battlefield does not survive a real workday.*

**Exit:** David runs a real task through it, on purpose, twice, without turning the sprites off.

### ▶ POSTURE — modes, and telling the truth about Windows

**Goal:** ship the security position Phase 1 actually supports, and no more.

**Exists at the end:** two modes, `SinglePlayer` and `CoOp`, mode as a one-way sticky ratchet whose
downgrade is an event · `Provider` taking `&self` and returning a stream · a remote rig as a
**device on the local provider**, never a peer · **`max_tier` per role — denying the class** ·
redaction mandatory at `Provider::start` · the dependency gate copied verbatim from Claudette,
**plus the digest pin on model weights that no donor has**.

**Retires:** nothing — risk 1 is a *platform fact*, not a hypothesis. This milestone makes the
stated posture honest: **blast radius, not a sandbox**, written in the README in those words.

**Exit:** the threat model table's 11 rows each have a shipped answer or a written, dated admission
that they do not.

### ▶ SELF-HOST — W13's ladder, which starts measuring at Skeleton

**Goal:** the project's own definition of done — *ABCC 2.0 takes a task on its own repository and
completes it through its own pipeline.*

**Exit:** W13's **M3** — ten consecutive boundary-crossing, gate-accepted tasks with **review
minutes flat or falling**. ⚠ **2.0 may not claim M0; v1 already occupies it** (15 of 471 commits,
one week, none crossing a module boundary).

---

## 4. Why this order, and not a layered one

**The spine is ordered by which falsifier would force the most rework, not by what sits underneath
what.** Two consequences that a layer-first plan would get wrong:

- **The engine rewrite is answered in Skeleton, first.** It is the premise the whole plan rests on
  after §1's ruling, and it is the cheapest thing to be wrong about early. A layered plan would
  reach it late, with the gate and fleet already built on top of it.
- **Gate precedes Fleet.** Parallelism is more fun to build and it is the wrong thing to build
  second: two slots producing output nothing can grade is a faster way to be wrong. Risk 3 says the
  gate *is* the product.

**The one deliberate compromise: Console sits fourth**, which means the flagship — and the only
differentiator W9 found evidence for — is the fourth thing David sees. That is a real cost and it is
taken with open eyes, because a battlefield rendering a fleet whose results nobody can trust is a
demo, not a tool. ✅ **Its mitigation is now code, not a rule** (David, 2026-08-28): a plain-text
Ratatui reader over the event log ships in **Skeleton**, so *"every milestone emits events in the
shape Console reads"* is enforced by something that breaks when it is violated. **Console extends
that reader; it does not replace it.**

---

## 5. Instrumentation that must exist from the first milestone

🚨 **Review minutes per merged change must be recorded from Skeleton onward.** W13's ladder is
measured in human review minutes, never in agent-authored commits, because *every long-term failure
mode in the literature is a review-burden failure*. **Starting the measurement at Self-Host leaves
no baseline and the ladder becomes unfalsifiable.** It is one W8 column and one W3 event type —
trivial at Skeleton, unrecoverable later.

Also from day one: `usage.completion_tokens_details.reasoning_tokens` logged on every call · the
run's mode as its first event · `finish_reason == length && content.is_empty()` recorded as
`Uncertain` and never as a score · every gate rung's `Unmeasured(Why)` reason, since Phase 1 found
**11 distinct reasons** already occurring in practice.

---

## 6. The co-development split — §12's Phase 2 requirement

§12:1007 says *"define the split in the Phase 2 plan"*. The shape it proposes, made concrete:

| Who | Owns | Explicitly does not own |
|---|---|---|
| **Claude Code** | Architecture, the contracts and type design, the gate's logic, security posture, review of everything Claudette writes, live research | Bulk mechanical edits; anything better measured than reasoned |
| **Claudette** | Local execution, high-volume mechanical work, the running dogfood. **Every task it handles well or badly is W8 harness data** | Architectural decisions; the gate's own logic; anything crossing a module boundary unreviewed |
| **David** | The gate. Direction, taste, and the final word on whether it is fun | — |
| **ABCC 2.0 itself** | Progressively its own construction, tracked explicitly on W13's ladder | Anything above the rung it has actually reached |

**This is a research input, not just process** (§12): a tool built by the workflow it supports gets
its ergonomics tested continuously. ⚠ **The transition is the measurement** — the point where 2.0
takes over its own construction is the point it is real, so the handover of each milestone's work
from Claudette to 2.0 is itself a logged event, not an impression.

---

## 7. The ADRs — David's ruling, written as the plan consumes each ruling

`research/decisions/`, one per architectural decision, **written during Phase 2 and dated when
written** — not backfilled with dates after the decisions they describe. Fourteen, each tracing to a
closed workstream. ✅ **ALL FOURTEEN ARE WRITTEN, 2026-08-28** — filenames below, index and house
template at `research/decisions/README.md`:

| # | Decision | Source |
|---|---|---|
| 1 | [Rewrite rather than port; donors are specification and test corpus](research/decisions/ADR-0001-rewrite-not-port.md) | §1 above, W12, W3 |
| 2 | [Two levels, four phases each; Router/Tester/CTO are not phases](research/decisions/ADR-0002-two-levels-four-phases.md) | W11, W6 |
| 3 | [The unit is a runtime slot, N=2, set by VRAM](research/decisions/ADR-0003-slot-is-the-unit.md) | W11, W2, W1 |
| 4 | [Nine-variant lifecycle, one write path, attempts immutable](research/decisions/ADR-0004-task-lifecycle.md) | W3, W5 |
| 5 | [SQLite event log, WAL + FULL, status a projection, boot = replay](research/decisions/ADR-0005-sqlite-event-log.md) | W3, W5 |
| 6 | [Threads own the work; one runtime at the console edge](research/decisions/ADR-0006-threads-own-the-work.md) | W3, W2 |
| 7 | [Worktree isolation at a temp-index snapshot sha](research/decisions/ADR-0007-worktree-isolation.md) | W6, W11 |
| 8 | [The gate is a conjunction of refusals](research/decisions/ADR-0008-gate-is-a-conjunction-of-refusals.md) | W6, W11 |
| 9 | [`Measured \| Unmeasured(Why)`; **only deterministic rungs refuse — the Judge never blocks**](research/decisions/ADR-0009-measured-or-unmeasured.md) | W6, David 08-28 |
| 10 | [No pre-dispatch estimate; one tier; retry budget 2](research/decisions/ADR-0010-no-estimate-one-tier-retry-2.md) | W4, W1, W2 |
| 11 | [Model roster; enumerate and freeze the tool-head set](research/decisions/ADR-0011-model-roster-and-frozen-heads.md) | W1, W2, W11 |
| 12 | [Ratatui + sixel primary; SSE + SQLite; one `seq`](research/decisions/ADR-0012-ratatui-sixel-console.md) | W5 |
| 13 | [Two modes; rig as device; `Provider` `&self` + stream](research/decisions/ADR-0013-two-modes-rig-as-device.md) | W10, W9 |
| 14 | [Deny the class via `max_tier`; blast radius, not a sandbox](research/decisions/ADR-0014-deny-the-class-blast-radius.md) | W7, W8 |
| 15 | [The idle gap is ours; a full window is not a fault; silence is not an artifact](research/decisions/ADR-0015-what-the-first-real-runs-corrected.md) | F493, F496–F502 |
| 16 | [A phase asks again when the model says nothing; a cut turn's tool calls never run](research/decisions/ADR-0016-a-phase-repairs-a-missing-answer.md) | F503–F508 |

`research/benchmarks/` — §12 also lists this. It is **satisfied in substance already**:
`research/spikes/` holds the reproducible drivers and `runs/hw-probe/` plus the 62 manifests are now
committed. **Recommend recording that rather than creating a third location for the same artifacts.**

▶ **What writing them changed, recorded here because it is a plan-level fact.** Nothing in the
architecture moved — every ADR states a ruling this document already carried — but three things
surfaced. **(a)** Two of W3's and W2's rulings were written assuming a port and are now kept as
*specification*: the dependency list (ADR-0006) and `post_with_model_reload_retry`'s six matched
surface forms (ADR-0011). The all-tokio rejection also loses its fourth argument — *it ends the
option of tracking Claudette upstream* — and survives on the three measurements. **(b)**
`research/W4-routing.md`'s status header was **stale** — *OPEN, items 1, 2 and 3 of 6 closed* over a
body carrying all six items to F399 — and is corrected in place with a dated note. **(c)** **F59 is
cited in three research documents and defined in none**, the same shape W6 found for F22–F29.

---

## 8. Budget

**Phase 1 landed in 13 of 14 sessions.** Phase 2 is a plan and fourteen ADRs, not a research phase:
**3–4 sessions** — this document, two of ADRs written as each ruling is consumed, one buffer for
David's review. **Phase 3 is where the code is written**, and it is not budgeted here; the milestone
spine above is its shape, not its schedule.

**Standing:** exceeding a budget by up to 10% is a non-issue, generally, for every doc. Do not split
or strip a document to protect a number.

---

## 9. Decisions — David, 2026-08-28

The four questions this plan was written to raise are answered, and three of them changed it.

1. ✅ **`PLAN.md` lives at the repo root**, parallel to `RESEARCH_BRIEF.md`: the brief governs
   Phases 0–1, this governs Phase 3. §13's layout names nothing for Phase 2 and that gap stands —
   `research/decisions/` still holds the ADRs, per §12.
2. ✅ **A plain-text Ratatui reader moves into Skeleton; the sixel battlefield stays at Console.**
   The reader proves the event-shape contract with code rather than a written rule, and Console then
   lands on a read path already known to work. **Fun is deferred; the rework risk is retired.**
3. 🚨 ✅ **Only deterministic rungs may refuse — the Judge reports and never gates.** There is no
   false-fail rate to tune; a false fail is a rung bug. See the Gate milestone: this removed a knob
   rather than setting one, and it **replaced** the gate falsifier with a report-volume one.
4. ✅ **The rewrite ruling does NOT extend to `harness/crates/`.** It is the measurement instrument,
   not the product: every rate in the corpus — 1,369 preserved cells, Q56, K, the 40-task floor
   check — came out of it, and **changing the instrument changes what those numbers mean**. F59
   already showed this box drifts. **2.0 consumes the harness's output and does not reimplement it.**
   Accepted cost: harness and product carry two different outcome types until a successor is built
   inside 2.0 and compared against the old one before retirement.

## 10. Open questions

**None blocking.** The plan's gate is David's sign-off on this document.
