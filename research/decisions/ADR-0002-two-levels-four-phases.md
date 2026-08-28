# ADR-0002 — Two levels, four phases each; Router, Tester and CTO are not phases

- **Status:** ✅ Accepted
- **Date:** 2026-08-28
- **Deciders:** Claude Code (W11 reconciliation), ratified by David with `research/SUMMARY.md`
- **Sources:** W11 F225, F226, F231, F232, F234, F235, F237 · W11 § Recommendation 1, 3, 4 ·
  W6 F213, F214, F216, F217, F221, F222

## Context

Three pipelines had to be reconciled: v1's Coder/QA/CTO, BCF's nine stages, and the brief's §10
stage table. **F225 found that §10 is the conflation rather than the reconciliation** — its one
table carries four different axes at once (when a thing runs, who runs it, what comes out, and what
may stop it), and v1 built exactly that conflation with measurable results: the capability model
went unread, the tier collapsed into a ternary on a name, two of three unit types never received
work, and the unit type became a scheduling token carrying resource exhaustion in a complexity
field (F228, F229).

**F226 then found that the pipeline is two-level and §10's Architecture row is at the wrong one.**
v1's own header comment documents six steps of which **2 and 5 are mission-level — called exactly
twice per mission, once to decompose and once to review** (`orchestrator.py:9`) — while step 4 is a
loop over tasks. Decomposition does not hand an artifact to the next stage of the same task; **it
produces the tasks**. A flat list that puts Architecture between Research and Coding implies all
three operate on one entity, and no donor does that.

Two more facts constrain the shape. **BCF's nine stages do not transfer**: F213 found a repository
asymmetry behind six of them — they exist to compensate for having no repository to read, and 2.0's
workload is an existing tree. And **F235 found §10's table is missing the only stage that ever
stopped anything**: the no-model measurement step. v1 has no mission-level build at all.

## Decision

**Seven phases across two levels. Three of the seven run no model.**

**Mission level** — the operator's unit of intent:

| # | Phase | Kind | Call-sign | Output |
|---|---|---|---|---|
| M1 | **Plan** | model, read-only tools, once per mission | **Engineering** | the task set, each with one *executable* acceptance criterion |
| — | *(the task set runs — the attempt level, below)* | | | |
| M2 | **Integrate** | **no model** — build + test the assembled workspace | *(instrument)* | `Measured \| Uncertain` per check |
| M3 | **Accept** | human by default; a W3 ladder rung when unattended | the operator | ship / don't, with reasons |

**Attempt level** — one pass at one task:

| # | Phase | Kind | Call-sign | Output |
|---|---|---|---|---|
| A1 | **Localize** | model, read-only tools | **Recon** | a grounded brief |
| A2 | **Change** | model, full tools, commits; *the fix round is this phase with different feedback* | **Builders** | diff |
| A3 | **Measure** | **no model** — build, typecheck, the real suite, the acceptance criterion, the diff scanner | *(instrument)* | `Measured(x) \| Uncertain(why)` per input |
| A4 | **Judge** | **one** model call, no tools, sees the brief, the diff **and A3's measurements** | **Commandos** | verdict + defect list |

Plus one thing that is **not a phase at either level**: **Veto** — deterministic, non-scoring
refusals evaluated after Judge, at whichever level they arise (security HIGH, empty diff, build
break, a required measurement that came back `Uncertain`).

🚨 **Measure precedes Judge, and Judge sees its output** (F235). This is the ordering, not an
implementation detail: the family's judges read the model's own narration rather than the artifact
(F232), and W6 measured that the axis deciding a reviewer's quality is *what it reads*.

### What is deliberately not a phase

**Measure has no call-sign because it has no model** — it is the instrument, not a unit; staffing it
with a fifth unit type would be F230's inflation committed on purpose. And four names from the
donors stay out of the domain model: **`Router`** is a routing decision, which is data on the event
log (F221) · **`Tester`** is an artifact, and only if it is immutable to A2 (F216) · **`QA`** is
A4's prompt — v1's Sentinel-9 protocol, the best reviewer in the family and a prompt with no caller
(F234) · **`CTO`** is a person, or a rung on W3's ladder (F217). Each becomes a name again only when
someone builds its construction site, named in the plan with its cost, not added to an enum first.

▶ **§10's four unit names all survive as call-signs on phases** — Engineering → M1, Recon → A1,
Builders → A2, Commandos → A4. The table's *names* were good; its *columns* were the defect.

## Consequences

- **Seven phases, one entity each level, and the console can draw the level boundary** — which is
  the thing a flat list makes impossible.
- **Three of seven phases are free of the model and of tier arithmetic.** A3 and M2 have no tier at
  all, and they are the two most decisive phases in the pipeline.
- **The retry story is representable:** a failed attempt re-enters A1 or A2 and never re-runs Plan.
- **The fix round is not a phase.** It is A2 with different feedback, which is why the phase list
  does not grow when retry does.
- **Acceptance criteria must be executable or they do not exist** (F236: v1 carries them twice, one
  prose with no reader and one executable that is the gate). This binds M1's output schema.
- **Hands onward:** the phase set is the vocabulary ADR-0004's lifecycle transitions over, and A3/A4
  are the two rungs ADR-0008 and ADR-0009 are about.

## Alternatives rejected

- **Keeping §10's per-stage unit types** — F229's empty-pool path. This is the single substantive
  change the reconciliation makes to §10. See ADR-0003.
- **A flat seven-phase list** — the retry story kills it: in a flat list, re-entering A1 reads as
  re-running Plan.
- **Dropping the mission level so tasks are the only entity** (BCF's and Claudette's shape) — it
  would simplify the build and throw away the one thing v1 got structurally right (F226). The front
  line is a mission with N tasks on it, not one task.
- **Following BCF and deleting decomposition** — the strongest inherited argument against M1, and it
  is greenfield-specific: BCF's stated cause is *"duplicate project structures"*
  (`mission.rs:361-362`), a failure that needs the project structure to be generated output. On
  2.0's workload it is input, so the failure cannot occur (F237). The revert constrains what M1
  emits; it does not remove the phase.
- **Adopting BCF's nine stages** — already rejected in W6 for independent reasons (F214, F222), and
  six of the nine exist only to compensate for having no repository (F213).
- **Naming the measurement phase "Verifier"** for continuity with both Rust donors — F235: the word
  means opposite things in the two of them.

## What would falsify this

**M1 inflates a one-task mission into a task set on the real workload.** F250 measured that Plan
does not inflate when told not to, which is why skipping M1 is an optimisation rather than a
correctness fix — if that inverts in practice, the mission level earns a fast path, not a deletion.
