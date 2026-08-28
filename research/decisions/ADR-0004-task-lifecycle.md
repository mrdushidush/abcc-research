# ADR-0004 — Nine-variant Task lifecycle, one write path, attempts immutable

- **Status:** ✅ Accepted — the names are **ratified** (OQ-W3-6 closed, David 2026-08-28)
- **Date:** 2026-08-28
- **Deciders:** David (the words), Claude Code (the mechanism)
- **Sources:** W3 F146, F147, F148, F149, F150, F151 · W5 F103, F105, F130, F132, F138 · W1 F91
- **Depends on:** ADR-0005 (the log the `Seq` indexes into)

## Context

v1's failure here is not a bug, it is a vocabulary. **F146: one enum carried scheduling, pipeline
position and outcome at once**, and the eleven-state count was the damage that conflation did.
Around it, **F148 enumerated four liveness defects that are one missing concept — a per-state
contract**:

1. **The watched set is one state of seven.** `stuckTaskRecovery.ts:194` polls `in_progress` only.
   `assigned` is written by five sites and advanced by none, and **two independent subsystems were
   patched to skip the state** to stay visible (`battleClawService.ts:258`,
   `orchestratorService.ts:417-427`). When services route around a state to stay visible, the state
   machine has stopped describing the system.
2. **The clock never advances with work.** The predicate reads `assignedAt`, written once at
   assignment and refreshed never, so a task running four LLM executions inside one span is **reaped
   at five minutes while healthy**. `grep heartbeat|lastSeen|lastProgress|keepalive`: zero hits.
3. **NULL means invisible, twice.** `assignedAt IS NULL` fails a `<` predicate by SQL three-valued
   logic, so any path that nulls the clock without re-assigning makes the row permanently
   unwatchable — the same shape as F147's `needsHumanAt`.
4. **Recovery is terminal** — the eight-step cleanup is complete, and the task is not re-queued.

And **F150: four retry mechanisms, no lineage — every retry mutates the row it retries**, so the
question *what did the previous attempt do* is unanswerable after the fact.

## Decision

**Five entities, five vocabularies. Never a mega-enum.**

| Entity | Vocabulary | Owner |
|---|---|---|
| **Task** | the nine-variant lifecycle below | W3 |
| **Attempt** (v1's `TaskExecution`, made **immutable**) | `Outcome: Success \| SoftFailure \| HardFailure \| Uncertain` | W3, W6 consumes |
| **Stage** | ADR-0002's phases — *not* folded into `TaskState` | W11 |
| **Agent/Unit** | idle / engaged / draining, derived where possible | W3 |
| **Mission** | its own enum, typed separately | W11 |

### The lifecycle — ratified as sketched

```rust
pub enum TaskState {
    Queued,                                                   // standing-by
    Deployed       { unit: UnitId, since: Seq },              // orders-received
    Engaged        { attempt: AttemptId, since: Seq },        // engaging-target
    AwaitingOrders { attempt: AttemptId, prompt: PromptId,
                     since: Seq },                            // intervention-required
    Holding        { checkpoint: CheckpointId, since: Seq },  // on hold (pause / Esc)
    Commandeered   { operator_since: Seq },                   // human has the keyboard
    Accomplished   { attempt: AttemptId },                    // mission-accomplished
    Failed         { attempt: AttemptId },                    // mission-failed
    Aborted        { reason: AbortReason, since: Seq },       // abort-abort
}
```

🚨 **Every variant carries the evidence its contract needs, so F147's and F148's NULL-clock bugs are
unrepresentable** — the state cannot be constructed without its timestamp. **`since` is a `Seq`**, a
position in the event log, so *when* and *where in the replay* are the same fact (W5's one-integer
ruling, ADR-0012).

**The names are load-bearing, not decoration.** They were chosen against the 96 inherited voice
lines so the speaker already agrees with the screen — `standing-by`, `orders-received`,
`engaging-target`, `intervention-required`, `mission-accomplished`, `mission-failed`, `abort-abort`
— with themes as label-maps over the fixed enum, `classic` mapping to functional names (F130). Two
gaps (`Holding`, `Commandeered`) go on the asset list and block nothing.

### One write path

**Every transition goes through one writer:** `fn apply(task, Command) -> Result<Event, Refused>`.
It appends the event and updates the status row **in the same transaction**; nothing else writes
status, and **no generic set-status endpoint exists**. Foreign processes send *commands that can be
refused*, never column values that cannot.

### Attempts are immutable

Every `Attempt` records `checkpoint_from: Option<CheckpointId>` and
`cause: Fresh | Retry{of} | Rescope{of} | Edit{of} | Replay{of}`. **Retry, edit-prompt, re-route and
replay are all one fork-from-checkpoint operation** (F103, F150), so **lineage exists by
construction**: it cannot be lost, because attempts cannot be mutated.

### The per-state contract table

Each of the nine states declares: slot held · workspace lock · liveness clock · watchdog policy ·
boot reconciliation (W3 item 4 carries the full table). Three rules it encodes that v1 lacked:

- **Every state has a row.** A new variant without one fails the exhaustive `match` in the writer,
  the watchdog **and** the renderer.
- 🚨 **Operator states are watched but never reaped.** The watchdog distinguishes *no human yet* from
  *no progress* — the distinction F91's forty silent minutes taught the harness. `AwaitingOrders`
  has a **human clock and no timeout**, and boot **re-presents the prompt and never auto-answers**;
  arrival time is part of the contract (F132).
- **Terminal ⇒ zero resources**, enforced by the writer.

`Engaged`'s liveness clock is **progress**: the `seq` of the attempt's last event, so every token
batch and tool call is the heartbeat.

## Consequences

- **Three verbs, two target states.** Halt-now → `Holding` (keep the workspace, discard only the
  un-checkpointed generation); kill-now → `Aborted`; pause-at-boundary → `Holding`.
  Stop-but-keep-the-work is a *transition*, not a state (F138). Queue-while-streaming is not a state
  at all — input parks at the broker and applies at the next boundary.
- **Dependency edges are rows** (`depends_on(task, task)`), not a `Blocked` variant: a `Queued` task
  is *eligible* when its edges are satisfied, and "blocked" is derived for display.
- **The RTS vocabulary is now in the domain model**, which W9 says is the only differentiator the
  evidence supports — and Rust enums make domain naming sticky, which is why it was ratified rather
  than defaulted.
- **Two open questions stay open and are cheap:** whether `Deployed` survives as a durable state or
  collapses into an atomic `Queued → Engaged` in a single process (OQ-W3-1), and whether `Blocked`
  becomes stored if the scheduler query cost argues for it (OQ-W3-2).

## Alternatives rejected

- **The mega-enum** — F146: the eleven-state count *was* the conflation's damage. Freezing it into a
  Rust type would make it permanent and exhaustively matched everywhere.
- **Full typestate** — states must round-trip through SQLite and the SSE wire, where typestate
  evaporates; the writer's `match` gives the same safety without the fight.
- **A heartbeat column the worker updates** — the event log already timestamps every event, so
  liveness is a query, not a second clock that can drift from the first.
- **Stored-status-primary with the log as audit** — two sources of truth with the arrow pointing the
  wrong way; F149 shows what the second source does at boot.
- **`Blocked` as a stored variant** — derivable from edges; storing it means reconciling it.

## What would falsify this

**A state turns out to need a contract row that cannot be written** — a real situation where the
same variant legitimately holds a slot sometimes and not others. That is the mega-enum trying to
re-form, and the fix is a new variant with its own row, never a nullable field on an existing one.
