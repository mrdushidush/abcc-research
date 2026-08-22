# W3 — Orchestration core in Rust

**Status: COMPLETE — started 2026-08-19, all seven items written 2026-08-20 (F146–F212).** Built one
item at a time in §13 format, same as W5. The language is decided (Rust) and the engine is decided
(copy Claudette's, both stay live — David, 2026-08-07), so this workstream is about **structure**:
the typed lifecycle, durability, the control channel, escalation lineage, and process topology.
The closing summary — one line per item, plus what W3 hands on and still owes — is the last section
of this file.

Planned items, in the order §14 item 4 dictates:

1. ✅ **The typed lifecycle and the Q8 vocabulary** (F146–F152) — §14's named first deliverable,
   written 2026-08-19 from a fresh three-repo extraction. Corrects the record in two places: the
   Task lifecycle has **seven** states, not eleven, and v1 *had* a status type — it was decorative.
2. ✅ **What the family already provides** (F153–F157) — the inheritance walk, verified: the
   engine copy's real shape, the attempt/turn boundary, and the one intrusive change the engine
   needs. "Proved twice" turns out to be "threads proved once, tokio never exercised".
3. ✅ **Durability** (F166–F173) — SQLite event log with `synchronous=FULL`, and the measurement
   that justifies it: full ACID costs 929 µs per transition here, boot-as-replay 94 ms per 100k
   events. The ecosystem, live-verified, offers storage engines or servers — not the middle.
   Answers OQ-W3-2.
4. ✅ **The control channel and the broker** (F174–F184) — control is durable data on item 3's log,
   request identity is a `seq`, and the channel is **two mechanisms**: a boundary select plus a
   cancel flag in the stream loop. Answers OQ-W5-3 and OQ-W3-10; corrects item 2's "exactly one
   intrusive change" to two. The family lost the free-text redirect three separate ways.
5. ✅ **Escalation lineage** (F185–F196) — the mechanism was already ruled (fork-from-checkpoint), so
   this item is the **policy**: classify the failure before escalating, one ladder that is data,
   every fork from the *best* checkpoint, and lineage as the attempt chain answering six queries.
   Two of the brief's four verbs turn out to be inert in the donor, and the engine 2.0 is copying
   already contains the family's only correct escalation. Answers OQ-W3-14 and OQ-W3-17's lineage
   half.
6. ✅ **Rust ecosystem survey, live-verified** (F197–F205) — the tokio question, settled by
   measurement rather than argument: **threads own the work, one runtime owns the console edge, and
   the event log is the only thing that crosses.** Cancellation lands in 4–14 ms on the blocking
   stack, the idle-gap timeout the family lacks turns out to be a *config value* on a semantic the
   docs describe backwards, and the only honest argument for tokio is the one nobody made — every
   maintained Rust HTTP server is async. Answers OQ-W3-13; corrects F154 and F172 in place.
7. ✅ **Process topology** (F206–F212) — **one process now, with the worker seam defined as if it
   were already remote.** The boundary is cheap (10 ms against a 33.9 s TTFB) and buys nothing item 3
   does not already provide — but it would import W10's protocol early, because the log has exactly
   one writer. Blast radius is answered instead by `panic = "unwind"` plus a catch at the attempt
   boundary. And the probe found a live defect in both donors: **the inherited kill orphans the
   work**, which a job object fixes in 1.8 ms.

Scope reference: `RESEARCH_BRIEF.md` §11 lines 708–730, plus §14 item 4's added requirements and
the W5 handoff table (`research/W5-command-center.md`, "What W5 hands to other workstreams").
Findings continue the family numbering from W5's F145.

---

# Item 1 — the typed lifecycle and the Q8 vocabulary

## Question

**What is the task lifecycle, as a Rust type?** Not "which crate", not "what persistence" — those
are items 3 and 6, and §14 item 4 explicitly orders this one first:

> *"W3's first deliverable is the typed lifecycle, before any durability mechanism is chosen.
> ABCC's four services are the right set of concerns and none of them is the hard part — the hard
> part is that the lifecycle exists only as string literals, which is how a task hung in `assigned`
> came to be invisible to both the assigner and the watchdog."*

Three requirements travel with it from §14, and five more from W5's handoff table:

From §14 item 4: every non-terminal state **recoverable**; the liveness clock is **time since last
progress**, not time since assignment, which means the domain model needs a heartbeat ABCC never
had; in-memory admission state **reconciled at startup** against the durable store.

From W5: the enum includes **`Paused` and `Operator`, each with its reconciliation** (F104); it
carries a **checkpoint identity** — retry, edit-prompt, re-route and replay are all
fork-from-checkpoint (F103); the domain model needs **real dependency edges** (F109 — V1 has none);
enum rendering is **exhaustive** (F113); and two verbs arrive from the shipped-agent survey —
**stop-but-keep-the-work** and **queue-while-streaming** (F138).

And the same step settles **Q8's vocabulary** (David, 2026-08-07: the RTS framing goes *into* the
Rust domain model, deliberately reversing Claudette's functional-naming principle), because Rust
enums make the naming sticky and W3, W5 and W11 all inherit it.

## Method

Desk work, no GPU. Sources in order of weight:

1. **Fresh code extraction, this session (2026-08-19)** — three parallel read-only passes over the
   donors as they sit on disk: ABCC v1 at `D:\dev\agent-battle-command-center` (the lifecycle,
   watchdog, admission state, schema), Claudette at `D:\dev\claudette` HEAD `af3f804` (the engine
   being copied), BCF at `D:\dev\battle-command-forge` HEAD `d6c1601` (mission states). Claims
   below carry file:line from this pass, cross-checked against `prestudy/verification.md` §3.4 and
   `prestudy/inheritance-map.md` §2/§7 where those already traced the same code. Where this pass
   and the earlier record disagree, the disagreement is itself a finding (F146).
2. **W5's settled rulings** — F100–F106 (three mechanisms), F130 (the off-switch is a label map
   over a fixed enum), F132/F133/F138 (the shipped-agent corrections).
3. **The inherited audio corpus** — the 96 Bark voice lines under
   `agent-battle-command-center/packages/ui/public/audio/`, read as a vocabulary source, because
   audio is the loudest place the Q8 naming will surface and the names should agree with what the
   speaker already says.

## Inherited

| What | Source | Relevance here |
|---|---|---|
| The seven-state lifecycle, its services, its holes | ABCC `taskAssigner.ts`, `taskExecutor.ts`, `stuckTaskRecovery.ts`, `humanEscalation.ts`, `orchestratorService.ts`, `schema.prisma:47-98` | The concern list and the complete failure catalogue |
| A declared-but-unenforced `TaskStatus` union | ABCC `packages/shared/src/index.ts:54-61` | The cautionary half of "typed" |
| The turn loop, the permission rendezvous and its two invariants | Claudette `runtime/conversation.rs:361-863`, `tui_worker.rs:108-139` | The engine the lifecycle must wrap |
| The append-only action transcript + trash pre-images | Claudette `transcript.rs` | Take-over's undo surface (W5 F102), *not* the lifecycle log |
| Nothing | BCF | Confirmed: no mission state machine exists to port (F152) |
| 96 voice lines, three packs of 32 | ABCC `packages/ui/public/audio/` | The Q8 vocabulary's audio ground truth |

## Findings

### 🚨 F146 — the "eleven states" in the record was four vocabularies wearing one name; the Task lifecycle has seven

The fresh pass enumerated every value ever stored in `tasks.status`: **seven** — `pending`,
`assigned`, `in_progress`, `needs_human`, `completed`, `failed`, `aborted`. That is the whole set:
it matches the only runtime validator in the system (`routes/tasks.ts:33`, a `z.enum` of exactly
those seven) and the `TaskStatus` union in `packages/shared/src/index.ts:54-61`.

The **eleven** recorded in `verification.md` §3.4g — and inherited from there by
`inheritance-map.md` §2 and by W5's F113 — is only reachable by unioning *adjacent entities'*
vocabularies: `decomposing`, `executing`, `reviewing`, `awaiting_approval`, `approved` are
**`Mission.status`** values (`shared/src/index.ts:390-396`), `started` belongs to
**`TaskExecution`** (`:125`), `validating`/`passed`/`retrying` are **UI-only pseudo-states**
(`packages/ui/src/store/uiState.ts:137`, never persisted), and `idle`/`busy`/`stuck`/`offline`
belong to **`Agent`** (`:3`).

Two corrections follow, both filed in the source docs with today's date:

- **`verification.md` §3.4g**: the eleven-state list conflated `Task` with `Mission`. Its substance
  — no enforcement, ≥48 bare literal sites, no state machine — stands untouched.
- **W5 F113**: `STATUS_COLORS` (`shared/src/index.ts:301-309`) is in fact **exhaustive over the
  real seven** — the "four states with no colour" were Mission states that were never Task states
  at all. F113's *requirement* (exhaustive rendering, one owner instead of three duplicated maps)
  survives and is strengthened; its arithmetic falls.

**The design consequence is the finding.** The eleven was not a counting error anyone made
carelessly — it is what an untyped store *does to its readers*: when four entities' states are all
strings in adjacent tables, even a careful verification pass cannot tell whose states are whose.
The typed fix is therefore not one enum but **one vocabulary per entity** — Task, Attempt, Agent,
Mission each typed separately — and the temptation to build a single eleven-variant mega-enum is
exactly the conflation that produced the bad count, promoted into the type system.

### 🚨 F147 — v1 *had* the type; it enforced nothing, because nothing made it the only way to write

The record says the lifecycle "exists only as string literals." Nuance from the fresh pass: a
proper union type **exists and is even exhaustively consumed** — `TaskStatus` at
`shared/src/index.ts:54-61`, `STATUS_COLORS` as `Record<TaskStatus, string>`, `StatusBadge.tsx:4-12`
likewise. What it never does is constrain a write:

- The column is a bare varchar: `status String @default("pending") @db.VarChar(20)`
  (`schema.prisma:53`). Prisma's generated type is `string`, so every write site passes an untyped
  literal and every read casts it back — `taskAssigner.ts:136`:
  `this.emitTaskUpdate(updatedTask as unknown as Task)`.
- `PATCH /api/tasks/:id` (`tasks.ts:135-174`) permits **any of the seven from any current state**,
  no transition validation, with the comment *"Allow updating status and result from diagnostic
  scripts"* (`:32`).
- Three Python CTO tools drive the lifecycle through that PATCH from outside every service
  invariant. `cto_tools.py:150-158` sets `assigned` without `assignedAt`, without marking the agent
  busy, without locks, without a slot. `cto_tools.py:183-188` sets `needs_human` without
  `needsHumanAt` — and the escalation poller filters `needsHumanAt: { lt: … }`
  (`humanEscalation.ts:39-46`), so `NULL < x` is never true and **every live `needs_human` task is
  permanently un-escalatable**. `cto_tools.py:377-390` sets `completed` while bypassing
  `handleTaskCompletion` entirely — locks not released, slot not released, agent left `busy` with
  `currentTaskId` set: **a successful decomposition permanently parks its CTO agent.**
- A fourth door is ajar: the MCP gateway's `update_task_status`
  (`mcp-gateway/src/adapters/postgres.py:204-216`) takes an unvalidated `status: str` into raw SQL
  on a 5-second batch timer whose transaction **swallows per-statement failures** (`:140-145`).
  No in-repo caller today; typed as an invitation.

**The lesson, stated as a requirement:** "typed lifecycle" does not mean *an enum exists* — v1
proves a perfectly good union can sit beside the store it fails to guard. It means **the enum is on
the only write path there is**: one transition module owns every status write, foreign processes
speak to it in commands rather than column values, and no generic status-setting endpoint exists at
all. Parse at the boundary; refuse at the type.

### 🚨 F148 — the liveness holes are one missing concept: a per-state contract

Enumerated precisely, v1's watchdog story is four separate defects that are one design gap:

1. **The found-set is one state of seven.** `stuckTaskRecovery.ts:194` polls
   `status: 'in_progress'` only. `assigned` is written by five sites and advanced by none — the
   author's own comment (`taskExecutor.ts:243-249`) documents the incident, and **two independent
   subsystems were patched to *skip* the state**: `battleClawService.ts:258` (*"C3 fix: use
   in_progress so StuckTaskRecovery monitors it"*) and `orchestratorService.ts:417-427` (goes
   `pending → in_progress` directly). When services route around a state to stay visible, the
   state machine has stopped describing the system.
2. **The clock never advances with work.** The predicate is `assignedAt: { lt: threshold }`
   (`:195`), written once at assignment, refreshed never. `AutoRetryService` can legitimately run
   four LLM executions plus four validations *inside one `in_progress` span*
   (`autoRetryService.ts:107-264`) without touching any timestamp the watchdog reads — so a
   **healthy, progressing task is reaped at five minutes** while a dead task with a recent
   assignment is not. No heartbeat concept exists anywhere in the repo (grep for
   `heartbeat|lastSeen|lastProgress|keepalive`: zero hits).
3. **NULL means invisible, twice.** `assignedAt IS NULL` fails the `<` predicate by SQL
   three-valued logic, so any path that nulls the clock and fails to re-assign
   (`taskQueue.ts:208`, `taskExecutor.ts:261`, `agentManager.ts:145`) produces a permanently
   unwatchable row. Same shape as F147's `needsHumanAt` NULL. The clock's *presence* is optional
   in the schema, and everything downstream silently assumed it was not.
4. **Recovery is terminal.** On timeout the eight-step cleanup is genuinely complete
   (`:228-344` — locks, slot, `aborted` + `errorCategory: 'timeout'`, execution rows, agent, two
   socket events, alert, MCP publish) but the task is **not re-queued**; `aborted` waits for a
   human. And the manual `forceRecoverAll` covers `assigned`+`in_progress` only (`:126-139`), so
   the reset button leaves `needs_human` rows holding their locks.

One concept fixes all four: **every state declares a contract** — what resources it holds, what
clock its liveness runs on, what the watchdog may do to it, and how it reconciles at boot. A state
without a declared contract should not compile, which is precisely what a Rust `match` with no
wildcard arm buys. The recommendation writes this table out.

### F149 — admission state is acquired once, released six times, reconciled never

The resource pool is a process-singleton `Map<ResourceType, Set<taskId>>`
(`resourcePool.ts:83-97`; `ollama: 1`, `claude: 2`). The fresh pass added a fact the record did
not have: **`acquire` has exactly one caller** — `routes/queue.ts:308`, the `parallel-assign`
route — while `release` is called from six places. `OrchestratorService` and `BattleClawService`
execute tasks without ever acquiring, so the pool constrains one route and is decremented by
everyone. And that one route is the recorded incident in miniature: it acquires the slot (`:308`),
calls `assignTask` (`:314`) leaving the task at `assigned`, and returns — slot, agent and locks
held, in the one state nothing polls.

At boot, `index.ts:100-110` shows the pattern was *known* and simply not applied: ten lines apart,
`resourcePool.initialize(io)` (sets a socket handle, reads nothing) and `costAggregator.hydrate()`
(rebuilds an in-memory aggregate from `executionLog.groupBy`). The state that needed rehydration
never got it; seven more in-memory structures share the fate (`inFlightTasks`, review-cadence
counters — with an in-code TODO admitting they reset on restart (`codeReviewService.ts:96-99`) —
the entire `asyncValidationService` retry backlog, rest counters, rate-limiter usage, recovery
history, and Python's `execution_state` abort registry).

**Consequence:** admission must not be state that *could* be reconciled with the store — it must be
a **projection of the store**, recomputed from the same durable facts the lifecycle writes, so that
"reconcile at startup" is not a sweep someone remembers to write but the only way the pool exists.
Slot-holding is derivable: it is exactly the set of tasks in slot-holding states.

### F150 — four retry mechanisms, no lineage: every retry mutates the row it retries

v1 retries in four mutually unaware ways, and **none creates a new record**:

1. **Iteration retry** (`taskExecutor.ts:214-277`): `in_progress → pending`, preserving
   `currentIteration`, nulling `assignedAt` (see F148 §3).
2. **The model-escalation ladder** (`autoRetryService.ts:73-278`: local → remote → Haiku, cap 3)
   runs *invisibly inside* `in_progress` — writes no status, creates no execution row, refreshes no
   clock. The most interesting orchestration behaviour in v1 is unrepresented in its own store.
3. **Review-driven re-scope** (`codeReviewService.ts:383-456`): `completed → pending` with the
   entire escalation history — `previousModel`, `preferredModel`, `reviewScore`, `reviewContext` —
   written into the untyped `result` JSON blob. **`preferredModel` is written and never read**
   (`taskExecutor.ts:700-702` reads the *agent's* config instead), `completedAt` is not cleared
   (the row is simultaneously pending and completed), and the blob is overwritten on the next
   escalation.
4. **Mission retry** (`orchestratorService.ts:682-739`): appends `"\n\nRETRY NOTE: …"` onto
   `description`, destroying the original prompt. Manual retry (`tasks.ts:208-232` →
   `returnToPool`) resets `currentIteration: 0` and `error: null` — full history erasure.

The one durable lineage column, `escalatedToAgentId`, is read only by its own double-escalation
guard. And at the Python boundary the four-valued verdict lattice
`SUCCESS | SOFT_FAILURE | HARD_FAILURE | UNCERTAIN` (`schemas/output.py:11`) collapses to a
boolean, so **`UNCERTAIN` — which sets `requires_human_review=True` — is indistinguishable from a
clean pass** on the TypeScript side (`taskExecutor.ts:513-528` re-derives failure by
string-sniffing).

**Consequence:** attempts must be **immutable rows**, retry must be **fork, not mutation** — which
is the same mechanism W5 F103 already requires for edit-prompt, re-route and replay
(fork-from-checkpoint), so lineage is not a feature to add but a by-product of the only way to
retry. Terminal states stay terminal per attempt; the *task* continues through a new attempt
carrying `cause: Retry{of} | Rescope{of} | …`. And the outcome lattice crosses the boundary intact
— W6 gets `Uncertain` as a first-class verdict, because "the agent isn't sure" routing to the
review queue is precisely the honest-failure-reporting requirement.

### 🚨 F151 — the engine being copied has no task lifecycle to offer, and three of its properties are load-bearing constraints on the design

Claudette is a **single-conversation** agent; its unit of state is the session, not a fleet of
tasks, so the lifecycle is new work sitting *around* the copied engine. The fresh pass verified
what the engine's edges look like from the outside:

- **There is no cancel path.** `UserInput` is consumed at exactly one site (`tui_worker.rs:298`)
  and the `Message` arm calls `run_turn` synchronously — so `Quit` sent mid-turn **queues until the
  turn finishes**. The only mid-turn interaction is the permission rendezvous. W5 F100's
  select-at-every-boundary requirement is confirmed as *new* work, not an adaptation.
- **Persistence is turn-granular and a failed turn leaves a silent stump.** The session file is
  written only after a turn completes or fails (`tui_worker.rs:385`, `repl.rs:279-289`);
  `panic = "abort"` with an explicit no-recovery comment; and on a turn error the partial exchange
  — user message plus whatever tool results landed — **is autosaved with no marker that it was cut
  short**, so the next turn resumes on top of a truncated exchange. For 2.0: *aborted must be a
  recorded event, never an absence*; an attempt that dies leaves a typed tombstone, not a stump.
- **A model-server hang aborts the turn, and no retry covers it.** One flat 300 s cap on the whole
  streamed request (`api.rs:147`); `run_turn_with_retry` is gated on a substring
  (`run.rs:297-299`: `msg.contains("no content")`); the brain-selector fallback has
  `StuckReason::{EmptyResponse, NoTextAtMaxIter, ToolErrorStreak}` and **no timeout/transport
  variant** (`brain_selector.rs:43-55`). §11 W3 asks that a task survive *exactly* a model-server
  hang; the copied engine treats it as turn death. The lifecycle must catch that death and express
  it as an attempt outcome — which is fine, and much better than teaching the engine to hide it.
  *(Sharpened by item 5, 2026-08-20: the missing transport variant is deliberate, not an oversight —
  `diagnose` explicitly declines to escalate on `Err(_)` other than "no content", because a bigger
  model cannot fix a dead socket. F191 keeps the refusal and puts the recovery in the lifecycle,
  exactly as this bullet concludes.)*

Two things **are** worth porting verbatim, both confirmed in code: the per-request rendezvous
channel whose stale answers can never satisfy a later prompt, and fail-closed deny on every
disconnect path (`tui_worker.rs:94-97`, `tui_events.rs:46-49`) — W5 F101's two rules, already
implemented once.

One collision to resolve deliberately in the copy: the tool registry is **mutable mid-session** —
`Arc<Mutex<ToolRegistry>>`, the model itself calls `enable_tools`, and `api.rs:225-232` documents
that the registry is re-read on every request. W2's F81 measured that one changed token at the
front of the prompt annihilates a 79.7% TTFT saving and ruled **freeze the tool set per session**.
Both cannot survive the copy unchanged. (Resolution belongs to item 2 with W2 at the table;
flagged here because the lifecycle's attempt boundary is the natural freeze point.)

Record corrections from this pass: `D:\dev\claudette-forge` is the **same repo one commit behind**
`D:\dev\claudette`, not a sibling; and the test-count claims measure different things — 1,293
`#[test]` attributes in-tree vs the 1,145 executed by the default-feature run of 2026-08-07 (1,274
at `--all-features`). Both real; quote the measure with the number.

### F152 — BCF's third data point is an absence, and it completes the argument

BCF has **no mission state machine at all**: no enum, no status field, no strings — the lifecycle
is implicit in the call stack (`run()` → rounds → `attempt_round()`), the only persisted outcome is
a boolean written *after* the pipeline returns (`mission.rs:382-398`), a crash mid-mission persists
nothing, and each fix round `remove_dir_all`s the output directory before rewriting
(`mission.rs:1271-1274`). The git workspace that could have been the safety net is created and
never committed to (`mission.rs:331`; `Workspace::commit` has no caller). The only lifecycle enum
in the repo, `CtoState` (`cto.rs:33-40`), belongs to the chat agent.

So the family spans the whole failure space: **v1 typed the states and enforced nothing; BCF
enforced nothing by having no states; Claudette scoped the problem away by having one
conversation.** Nothing exists to port. §14 said the lifecycle is the hard part; it is now verified
three ways that it is also *new* work — the one part of the orchestration core with no donor.

## Options compared

Scored against: (A) makes the five recorded bug classes unrepresentable — the `assigned` hole, the
non-advancing/NULLable clock, the decorative type, lineage-by-mutation, admission drift; (B) boot
reconciliation cost; (C) exhaustive rendering and theming per F113/F130; (D) checkpoint/fork
support per F103; (E) implementation weight for Phase 3.

| Option | A | B | C | D | E |
|---|---|---|---|---|---|
| 1. Port v1's shape: one stored-status enum, mutable row, log as audit trail | partial — fixes typos, not the holes: the clock, admission and lineage stay separate concerns | a hand-written sweep, the thing v1 forgot | ✅ enum gives it | ✗ retry still mutates | low |
| 2. Mega-enum: scheduling ∪ stage ∪ outcome in one type | ✗ re-creates F146's conflation *inside* the type system | worse — every reader matches states it doesn't own | nominal | ✗ | low |
| 3. **Split model, log-primary: per-entity vocabularies, data-carrying variants, immutable attempts, status as a projection of the `seq` log** | ✅ each hole closed by construction (shown below) | **the same code as replay** — boot is a projection rebuild, F105's renderer argument applied to the orchestrator | ✅ exhaustive `match` + F130 label maps | ✅ attempts fork from checkpoints natively | medium |
| 4. Full typestate: `Task<Queued>` → `Task<Engaged>` at compile time | ✅ in-process, but states must round-trip through a store and a wire, where typestate evaporates | same as 3 underneath | awkward — generic rendering over typestates needs erasure anyway | ✅ | high, and fights persistence |

## Recommendation

**Option 3.** One vocabulary per entity, a small scheduling/control enum for the task whose
variants carry their own evidence, immutable attempts forked from checkpoints, and the durable
event log as the single source of truth that both the orchestrator and the console project.

### 1. The entity split (F146's fix)

| Entity | Vocabulary | Owner |
|---|---|---|
| **Task** | the scheduling/control enum below — where the work *is* | W3 (here) |
| **Attempt** (v1's `TaskExecution`, made immutable) | `Outcome: Success \| SoftFailure \| HardFailure \| Uncertain` — the Python lattice, kept (F150) | W3 here, W6 consumes |
| **Stage** (where in the pipeline) | W11's reconciled taxonomy — *not* folded into TaskState | W11 |
| **Agent/Unit** | idle/engaged/draining — small, derived where possible | W3 item 7 |
| **Mission** | its own enum, typed separately | W11 |

### 2. The Task lifecycle enum — a sketch to be ratified, not code

```rust
/// Every variant carries the evidence its contract needs, so the NULL-clock
/// and NULL-needsHumanAt bugs (F147/F148) are unrepresentable: you cannot
/// construct the state without its timestamp, and `since` is a `Seq` — a
/// position in the event log — so "when" and "where in the replay" are the
/// same fact (W5 item 6's one-integer ruling).
pub enum TaskState {
    Queued,                                                  // standing-by
    Deployed     { unit: UnitId, since: Seq },               // orders-received
    Engaged      { attempt: AttemptId, since: Seq },         // engaging-target
    AwaitingOrders { attempt: AttemptId, prompt: PromptId,
                     since: Seq },                           // intervention-required
    Holding      { checkpoint: CheckpointId, since: Seq },   // on hold (pause / Esc)
    Commandeered { operator_since: Seq },                    // human has the keyboard
    Accomplished { attempt: AttemptId },                     // mission-accomplished
    Failed       { attempt: AttemptId },                     // mission-failed
    Aborted      { reason: AbortReason, since: Seq },        // abort-abort
}
```

Notes against the requirement list:

- **`Holding` and `Commandeered`** are W5's `Paused` and `Operator`, named per Q8 (§5 below), each
  with a reconciliation row in the contract table.
- **Checkpoint identity** rides in `Holding`, and every `Attempt` records
  `checkpoint_from: Option<CheckpointId>` plus
  `cause: Fresh | Retry{of} | Rescope{of} | Edit{of} | Replay{of}` — retry, edit-prompt, re-route
  and replay are all the same fork operation (F103, F150). Lineage is the attempt chain; it cannot
  be lost because attempts cannot be mutated.
- **Stop-but-keep-the-work** (F138) is a *transition*, not a state: halt-now → `Holding`, keeping
  the workspace and discarding only the un-checkpointed in-flight generation. Kill-now →
  `Aborted`. Pause-at-boundary → `Holding` via the boundary check. Three verbs, two target states.
- **Queue-while-streaming** (F138) is not a state at all — input parked at the broker, applied at
  the next boundary.
- **Dependency edges** (F109) are first-class rows (`depends_on(task, task)`), not a `Blocked`
  variant: a `Queued` task is *eligible* when its edges are satisfied, and "blocked" is derived for
  display. Whether it should be a stored variant instead is OQ-W3-2.
- **`Deployed`** exists because assignment genuinely reserves resources before work starts — but
  unlike v1 it has a contract (below), so it can never again be the state nothing polls. Whether
  it survives as a durable state or collapses into an atomic `Queued → Engaged` transition in a
  single-process 2.0 is OQ-W3-1.

### 3. One write path, and status as a projection (F147/F149's fix)

Every transition goes through **one writer**: `fn apply(task, Command) -> Result<Event, Refused>`.
The writer appends the event to the `seq` log and updates the status row **in the same
transaction**; nothing else writes status, and no generic set-status endpoint exists. Foreign
processes (Python successors, MCP, diagnostic scripts) send *commands* that can be refused, not
column values that can't.

Boot is then **the same code as replay** (W5 F105, applied to the orchestrator): rebuild — or
verify — the projection from the log tail, re-arm per-state watchdogs from each state's `since`,
and *derive* the admission pool as "tasks currently in slot-holding states." The pool stops being
state that could drift; reconciliation stops being a sweep someone must remember.

### 4. The per-state contract table (F148's fix) — the deliverable §14 asked for

| State | Slot | Workspace lock | Liveness clock | Watchdog policy | Boot reconciliation |
|---|---|---|---|---|---|
| `Queued` | – | – | none | none (holds nothing) | re-admit to scheduler |
| `Deployed` | ✅ | ✅ | time since `since` | short spin-up bound (seconds, not minutes) → revert to `Queued`, release all | no live worker → `Queued`, release all |
| `Engaged` | ✅ | ✅ | **progress**: `seq` of the attempt's last event — every token batch / tool call is the heartbeat (OQ-W3-3 sets granularity) | stall on progress clock → attempt `HardFailure(stalled)`, task per retry policy | no live worker → attempt `HardFailure(orphaned)` tombstone (F151), task per retry policy |
| `AwaitingOrders` | released at the boundary | ✅ | human clock — **no timeout** | escalating console visibility (OQ-W5-13), never auto-abort | re-present the prompt; **never auto-answer** — arrival time is part of the contract (F132) |
| `Holding` | released (W5 ruling) | ✅ kept (OQ-W5-6 leaning) | none | visible, never reaped | remains `Holding` |
| `Commandeered` | – | held **by the operator** | none | visible, never reaped | remains `Commandeered` |
| `Accomplished` / `Failed` / `Aborted` | – | – | – | – | **invariant: terminal ⇒ zero resources**, enforced by the writer |

Two rules the table encodes that v1 lacked: **every state has a row** (a new variant without one
fails the exhaustive `match` in the writer, the watchdog *and* the renderer), and **operator states
are watched but never reaped** — the watchdog distinguishes "no human yet" from "no progress",
which is the distinction F91's forty silent minutes taught the harness (silence-vs-unrecorded).

### 5. The Q8 vocabulary — proposed names, grounded in the audio the project already owns

Q8 puts the framing into the domain model; F130 makes themes label-maps over the fixed enum, with
`classic` mapping to functional names. The variant names above were chosen against the 96 inherited
voice lines so the speaker already agrees with the screen:

| Variant | `classic` label | Existing voice line(s) |
|---|---|---|
| `Queued` | queued | `standing-by`, `ready-for-tasking` |
| `Deployed` | assigned | `orders-received`, `assignment-confirmed`, `moving-out` |
| `Engaged` | running | `engaging-target`, `executing-now`, `operation-underway` |
| `AwaitingOrders` | needs input | `intervention-required`, `need-assistance`, `requesting-backup` |
| `Holding` | paused | *(gap — no line; record or remap)* |
| `Commandeered` | operator control | *(gap — `change-of-plan` is the nearest)* |
| `Accomplished` | completed | `mission-accomplished`, `task-complete`, `objective-secured` |
| `Failed` | failed | `mission-failed`, `task-unsuccessful` |
| `Aborted` | aborted | `abort-abort` |

Checkpoint creation already has `checkpoint-reached`. Two gaps (`Holding`, `Commandeered`) go on
the asset list rather than blocking anything. **Entity naming** (task/mission/unit/operation) is
deliberately *not* settled here — W11 owns the taxonomy reconciliation and §10's table; these
variant names are scoped to the Task lifecycle. David ratifies the words (OQ-W3-6): the mechanism
is W3's, the personality is his.

## Rejected alternatives and why

- **The mega-enum** (option 2). F146 is the argument: the eleven-state count was the *damage
  conflation does*, and freezing that conflation into a Rust type would make it permanent and
  exhaustively `match`ed everywhere.
- **Full typestate** (option 4). States here must round-trip through SQLite and the SSE wire;
  typestate evaporates at both edges and would fight generic rendering. Use plain enums in the
  model; the writer's `match` provides the transition safety typestate promises, minus the fight.
- **A heartbeat column the worker updates.** verification.md §3.4e suggested watching
  `max(execution_log.timestamp)` — right instinct, and the event log *is* that, generalized. A
  second clock updated alongside the log would drift from it; the log already timestamps every
  event, so liveness is a query, not a column.
- **Stored-status-primary with the log as audit.** Reintroduces two sources of truth with the
  arrow pointing the wrong way; F149 shows what the second source does at boot. The log is
  primary; the status row is its cache, updated transactionally.
- **`Blocked` as a stored variant.** Derivable from edges; storing it means reconciling it.
  Revisit in OQ-W3-2 if the scheduler query cost argues otherwise.
- **Settling the full RTS taxonomy here.** W11 owns reconciling Coder/QA/CTO × BCF's stages ×
  §10's four; naming task-lifecycle variants is severable and blocking it on the taxonomy would
  serialize the block for no structural reason.

## Effect on fun

- **The battlefield can no longer lie.** Every state a task can occupy has a colour, a label in
  every theme, and (with two recorded gaps) a voice line — by construction, because the exhaustive
  `match` in the renderer fails to compile without them. F113's three duplicated maps become one
  owned mapping.
- **The transition writer is the voice trigger.** One place fires `mission-accomplished` and
  `abort-abort`, so audio is a lifecycle feature rather than a UI afterthought — and the
  busier-the-fleet audio policy (F112) has a single choke point to apply itself at.
- **Replay and boot are the same projection**, so the fun layer's six queries (F129) and the
  orchestrator's own recovery read the same log — the run that crashed is *automatically* the run
  you can re-watch to see why.
- **`Uncertain` becomes visible.** v1 swallowed "the agent isn't sure" into a clean pass; here it
  routes to the review queue and the console shows it — honest failure reporting as a state, which
  is §7's spectator-to-commander requirement applied to doubt.

## Open questions

| # | Question | Waiting on |
|---|---|---|
| OQ-W3-1 | Does `Deployed` survive as a durable state, or collapse into an atomic `Queued → Engaged` in a single-process design? | item 7 (topology) |
| OQ-W3-2 | `Blocked`: derived from edges (leaning) or stored variant? | scheduler design, item 3 |
| OQ-W3-3 | Heartbeat granularity — what counts as progress: token batch, tool call, or coarser? Ties to OQ-W5-22's liveness mark | W8 runs |
| OQ-W3-4 | Does `AwaitingOrders` release its slot immediately at the boundary, or after a grace period to preserve the warm prefix (W2 F81 interaction)? | W2, item 3 |
| OQ-W3-5 | Does the attempt `Outcome` lattice surface in the console, or only in the review queue? | W5/W6 |
| OQ-W3-6 | David ratifies the variant names and the two voice-line gaps | David |
| OQ-W3-7 | The registry-mutability vs F81 freeze collision: is the attempt boundary the freeze point? | item 2, W2 |

## Confidence: high on the split and the contracts, medium on the names

High because every requirement traces to a verified defect with file:line in at least one donor,
extracted fresh this session by three independent passes and cross-checked against the earlier
executed record — including the two places where this pass *corrected* that record (F146). Medium
on the vocabulary because the names await David's ratification (OQ-W3-6), and on `Deployed` and
the slot semantics of `AwaitingOrders` because both interact with items not yet written (OQ-W3-1,
OQ-W3-4). What would raise it: David's ruling on the names, and item 3's durability design
confirming the projection direction holds under SQLite's transaction model.

---

# Item 2 — what the family already provides

## Question

§11 W3's first bullet: *"Start from the inheritance map. What does BattleCommandForge already
provide, and what does Claudette already provide? The default answer to 'what orchestration
framework' should be 'the one we already proved twice', and any deviation needs an argument."*

So, precisely: **what is the thing being copied, what did the family actually prove, and what is
the verified gap list between the copy and an orchestration core?** The answers draw the boundary
between inherited code and new work — which is the boundary every later item builds on.

## Method

Same extraction pass as item 1 (three parallel repo reads, 2026-08-19), cross-checked against
`prestudy/inheritance-map.md` §2 and `prestudy/verification.md` §1. This item spends the Claudette
and BCF halves of the pass that item 1 only sampled.

## Inherited

The inheritance map's §2 rows stand as written — `ConversationRuntime<C,T>` + traits REUSE, the 12
loop breakers REUSE, compaction REUSE, ABCC's four services PORT, tokio REFERENCE. This item
verifies what those rows *mean* structurally rather than re-arguing them.

## Findings

### F153 — the engine copy is 93 modules in one crate, and the seam is the part that matters

What "copy Claudette's engine" actually copies: a **single-crate** workspace — 65,519 lines across
93 files in `crates/claudette/src` — whose former `forge` crate was deliberately folded in at
v0.5.1 because cargo rejects path-only workspace deps at publish (`Cargo.toml:7-10`). **There is no
crate boundary to lift.** The engine is a set of modules (`runtime/`, `tools/`, `api.rs`,
`executor.rs`) inside one `lib.rs`, and 2.0 must draw its own crate lines (item 7, with W12).

The seam the map praises is two one-method traits at `runtime/conversation.rs:141-147`:
`ApiClient` (`stream(&ApiRequest) -> Result<Vec<AssistantEvent>>`) and `ToolExecutor`
(`execute(name, input) -> Result<String, ToolError>`), with exactly three implementors each side.
Everything the family learned the hard way — the 12 loop breakers, empty-turn retry with a
doubling budget, compaction, the duplicate-edit and unchanged-read suppressions — lives *inside*
`run_turn_with_images` (`conversation.rs:361-863`) behind that seam, as per-turn local state.
**The copy's value is the loop's scar tissue plus the seam that makes it testable; the orchestrator
must wrap it without reaching into it.**

### F154 — "proved twice" is actually "threads proved once, tokio never exercised"

The brief's default-answer rule presumes two proofs. The extraction says otherwise:

- **Claudette** has **zero async** — no `async fn`, no `.await`, no tokio in its code (tokio
  appears only transitively in the lockfile via `reqwest`'s blocking backend). Concurrency is OS
  threads and `std::sync::mpsc`, deliberately asymmetric: bounded `sync_channel(512)` toward the
  UI, unbounded toward the worker, rendezvous `sync_channel::<bool>(0)` for permission
  (`tui.rs:721-722`, `tui_worker.rs:114`). This is the configuration with daily-driver mileage.
- **BCF** depends on tokio — and **never exercises it**. Every pipeline stage is a sequential
  `.await`; grep for `tokio::spawn | join_all | Semaphore` over the pipeline returns nothing (hits
  are chat streaming, TTS and the easter-egg games). The 5-member "critique panel" is one LLM call
  (`mission.rs:1624-1625`). It even runs **blocking** `std::process::Command` with a
  `thread::sleep(200ms)` poll loop directly on the runtime (`sandbox.rs:153`), parking a tokio
  worker for up to 120 s — the exact anti-pattern the runtime exists to avoid. And it is
  *deliberately* serial: `offload_model()` (`mission.rs:1749-1762`) evicts the previous model
  between stages because the design assumes one model resident — which W2's F83 (throughput
  saturates at N=2) says was the right instinct on this hardware.

**So the family offers one proof for threads-and-channels and zero evidence for async.** The tokio
question (item 6) therefore starts with the burden of proof on tokio, per the brief's own rule.
The one honest argument on tokio's side, named now so item 6 argues it properly: **cancellation.**
Kill-now must sever an in-flight streamed HTTP read, and a thread parked in
`reader.lines()` (`api.rs:933-941`) cannot be interrupted from outside — whereas dropping an async
future can. Whether a read-timeout-plus-cancel-flag loop closes that gap cheaply is item 6's to
measure, along with whether `llama-server` frees its slot on client disconnect (a live test; the
GPU is available).

> ✅ **Both measured, and the cancellation argument is discharged (2026-08-20).** F162: the slot
> frees in ≤0.25 s on a socket close. F200: the cancel-flag loop lands in **4–14 ms** — the thread
> parked in `reader.lines()` does not need interrupting, because it wakes on every line and the
> `Response` it drops closes the socket. F198: the read timeout the gap needed **already exists**
> as the blocking client's per-read budget. What replaced cancellation as tokio's honest argument
> is **F203 — the console's HTTP server**, since every maintained Rust server crate is async; and
> that argument reaches the edge only, never the core. Item 6's ruling: threads in the core, one
> runtime at the edge.

### F155 — v1's scheduler is a callback chain with six competing assignment paths

The map's row says ABCC's four services are "the right set of concerns." Verified, with two
sharpenings the row lacks:

1. **Nothing loops.** The de facto scheduler is `autoAssignNextTask`
   (`taskExecutor.ts:676-688`), fired only from completion/failure callbacks — **if no task
   completes, the pending queue is never re-scanned.** A fleet that goes idle stays idle until an
   HTTP request happens to poke it. The watchdog (30 s) and escalation poller (60 s) are the only
   timers in the system, and neither assigns work.
2. **Assignment has six independent implementations with different invariants**: `TaskAssigner`
   (locks + pre-check), `TaskExecutor.autoAssignNextTask`, `TaskRouter.autoAssignNext` (smart
   assign — **takes no file locks**), the `queue.ts` routes (one of which acquires the pool slot
   and abandons the task at `assigned`), `task-planning.ts` (commits `assigned`+`busy` then hands
   execution back to the HTTP caller as JSON — a half-transition by design), and
   `OrchestratorService` (skips `assigned` entirely). Each path was added where it was needed;
   collectively they are why item 1's single-writer rule is a structural fix, not a style
   preference.

**The concern list is right — assign, execute, watch, escalate — and 2.0 needs exactly one
implementation of each, plus the one concern v1 lacked: a scheduler that runs because it is a
loop, not because something else succeeded.**

### F156 — the verified gap list: what the copy does not contain

Consolidated from the pass, the orchestration core's new-work list against the copied engine:

| Gap | Evidence | Lands in |
|---|---|---|
| A fleet scheduler loop | F155 | item 3 |
| A control channel readable mid-turn | `UserInput` consumed at one site, `Quit` queues until turn end (F151) | item 4 |
| Cancellation of in-flight inference | F154; F103's "nothing in the family has it" confirmed | items 4, 6 |
| The task store + lifecycle | item 1's enum; Claudette's unit of state is one session | item 3 |
| Dependency edges | F109 confirmed — `parentTaskId` is hierarchy, ordering is prose in `description` (`orchestratorService.ts:217-219`) | item 3 |
| Admission as projection | F149 | item 3 |
| The event log with `seq` | Claudette's `actions.jsonl` is deliberately the wrong shape (mutations only, W5 F102) | item 3 |
| Multi-model slot management | Claudette assumes one brain; BCF evicts between stages | item 3, W2 |
| The broker (two subscribers) | OQ-W5-3 | item 4 |

And the inverse — what the copy contains that the orchestrator must not break: the loop breakers,
compaction, empty-turn recovery, the transcript/undo surface, fail-closed permission. All live
within a turn. **The clean boundary: the attempt is the orchestrator's unit; the turn is the
engine's.** The orchestrator schedules attempts, an attempt runs turns, and the engine's scar
tissue keeps operating unmodified inside each turn.

### F157 — the engine needs exactly one intrusive change, and the hook for it already exists

> ⚠ **Corrected 2026-08-19 by F184 (item 4): it is two.** The gate site is the right door for every
> *resumable* verb, but reaching it costs one generation plus one tool call — minutes on this
> hardware. Mid-stream `Halt`/`Kill` need a second change: a cancel flag read between SSE chunks in
> `api.rs:933`/`:1077`. The rest of this finding stands.

W5 F100 requires the worker to select on a control channel **at every step boundary**. Step
boundaries are *inside* the turn — between tool calls — so the orchestrator's control must reach
into the one place F156 just fenced off. The extraction found the loop already has a door at
exactly the right spot: the permission gate at `conversation.rs:659-664` runs between every tool
dispatch, threaded in as `Option<&mut dyn PermissionPrompter>` on `run_turn`'s own signature
(`conversation.rs:349-355`).

**Generalize that parameter — `PermissionPrompter` becomes a control point that can also answer
`Pause / Halt / Kill / Redirect(String)` — and the existing gate site becomes the select point,
with no restructuring of the loop.** The permission prompt becomes one message type among several,
which is precisely W5 item 2's recommendation restated as a one-trait diff. The rendezvous
invariants (per-request identity, fail-closed disconnect — F151) carry over to every verb.

This also gives OQ-W3-7 a provisional answer: **the attempt boundary is the registry freeze
point.** Fleet attempts run a frozen tool registry derived from their stage (W11's stage-to-tools
mapping), which is what W2 F81's prefix-cache ruling needs; the interactive assistant surface
keeps Claudette's mutable on-demand groups, where a human is present and cache priming matters
less. The collision dissolves into two configurations of one mechanism — pending W2's
confirmation.

## Options compared

| Option | Engine risk | Meets F100/F103 | Divergence cost | Verdict |
|---|---|---|---|---|
| Copy as-is, orchestrate strictly outside the turn | none | ✗ — pause/kill wait for turn end, minutes on a local model | none | fails the requirement |
| **Copy + one intrusive change: generalize the prompter hook into a control point** | one trait, one gate site, both already threaded through | ✅ boundary verbs; kill-now still needs item 6's cancellation answer | small, and mechanical to re-apply when upstream moves | **recommended** |
| Rebuild the loop natively for orchestration | forfeits the scar tissue and its 1,293-attribute test base | ✅ | total — a fork in all but name | rejected |

## Recommendation

1. **Copy the modules, keep the seam, wrap at the attempt.** The orchestrator owns everything
   between turns; the engine owns everything within one; the attempt is the contract between them.
2. **Make the single intrusive change** (F157): the prompter parameter generalizes to a control
   point answering the control-channel verbs at the existing gate site. Everything else about the
   turn loop ships untouched.
3. **One implementation per concern** (F155): one scheduler loop that runs on its own clock, one
   assignment path, one watchdog reading item 1's contract table, one escalation path through
   item 1's attempt forks.
4. **Registries freeze at the attempt boundary** for fleet work, stage-derived; the assistant
   surface keeps on-demand groups (OQ-W3-7 provisional, W2 to confirm).

## Rejected alternatives and why

- **Treating BCF's tokio as prior art for async orchestration.** It is tokio in the dependency
  tree, not in the architecture — sequential awaits, blocking subprocess polls on the runtime, and
  a deliberately serial model policy (F154). Citing it for tokio would repeat the "proved twice"
  error the extraction just corrected.
- **Sharing the engine as a crate with upstream Claudette.** Already ruled out by David
  (2026-08-07): copy, both stay live, fixes stop propagating — and F153 shows there is no crate
  boundary to share anyway.
- **A control sidecar thread that kills the worker thread.** Thread murder leaves locks, the
  registry mutex and the terminal in undefined states; the control point at the gate site gets the
  same latency for boundary verbs without any of that.

## Effect on fun

- The loop breakers become *events*: every nudge, duplicate-suppression and cap-landing the engine
  already performs is worth emitting on the `seq` log, because an operator watching a unit get
  nudged out of a loop is exactly the "failed run as interesting as a successful one" §7 asks for.
- One scheduler loop means the fleet visibly *idles* when it idles — F155's silent stall becomes a
  visible state the console can complain about, with a voice line (`systems-nominal` /
  `ready-for-tasking`) instead of a mystery.

## Open questions

| # | Question | Waiting on |
|---|---|---|
| OQ-W3-8 | ✅ **RESOLVED 2026-08-19** — yes: ≤0.25 s mid-decode, ≤~10 s mid-prefill, proxy transparent (F162/F163, live-probe section below). Kill-now is a socket close | — |
| OQ-W3-9 | Where the crate boundaries fall in the copy (engine / orchestrator / console / shared types) | item 7, W12 |
| ✅ OQ-W3-10 | **ANSWERED in item 4** — a sub-agent gets a *child* control point carrying the parent's grants, refusing to widen them, and naming its lineage through the `attempt_id` chain; fail-closed unchanged | — |

## Confidence: high

The findings are grep-level facts verified this session against both checkouts, and the
recommendation's riskiest element — the intrusive change — modifies a hook that already exists on
the loop's signature. OQ-W3-8's live disconnect test has since run and confirmed the cheap end
(2026-08-19, F162/F163: kill-now is a socket close). Still open: W2 confirming the
attempt-boundary freeze resolves F81's constraint in practice.

---

# Live probe — OQ-W3-8: does the slot free on client disconnect? (resolved 2026-08-19)

## Question

Kill-now's entire cost depends on one server behaviour. When the client vanishes mid-request,
does `llama-server` abort the work and free its only slot (`--parallel 1`), or does the
generation run to completion with the fleet's one slot held by a ghost? The answer decides
whether W5's `Kill` verb needs server-side machinery — a cancel endpoint, slot APIs, a watchdog
restart — or is just a socket close.

## Method

Champion loaded fresh via the canonical command (19.64 s, 12.67 GiB); held constants
re-verified from pid 22696's command line — `-c 65536`, kv q8_0/q8_0, `--flash-attn on`,
`--kv-unified`, `--batch-size 2048`, `--parallel 1`, backend
`llama.cpp-win-x86_64-nvidia-cuda12-avx2-2.27.1` — plus one surprise the command line contained
(F165). Harness: Python stdlib client, three independent witnesses per run — the `/slots`
endpoint polled at 4 Hz (`is_processing`), `nvidia-smi` GPU utilization at 1 Hz, and the latency
of a follow-up request on the same slot. Disconnect = `shutdown(SHUT_RDWR)` + `close`, a plain
FIN — exactly what a killed client process produces; no RST needed. Two paths (direct to
llama-server at `127.0.0.1:62284`, and through the LM Studio proxy at `:1234`) × two phases
(mid-decode: kill 3 s after the first token of a `max_tokens 3000` stream; mid-prefill: a ~35k-token
prompt whose uninterrupted prefill measures 17.36 s ≈ 2,000 tok/s, killed early and late).

## Findings

### F162 — mid-decode, the slot frees in ≤0.25 s, and the LM Studio proxy is transparent

| path | killed at | slot `is_processing`→false | GPU → 0 % | follow-up request |
|---|---|---|---|---|
| direct `:62284` | t=4.50 s | by t=4.70 s poll (**≤0.20 s**) | next 1 Hz sample | **0.37 s**, 200 |
| proxy `:1234` | t=4.25 s | by t=4.50 s poll (**≤0.25 s**) | next 1 Hz sample | **0.36 s**, 200 |

During decode the server writes a chunk per token (~74 data lines/s observed), so a dead socket
is discovered at the very next write. **The proxy propagates the disconnect upstream with no
measurable delay** — timing through `:1234` is identical to direct. Yes: the slot frees itself.

### F163 — mid-prefill, detection is lazy — up to ~8 s observed — but the prefill is always abandoned

Nothing is written to the socket during prompt processing, so the dead connection must be
noticed some other way. Three kills into the ~17.4 s prefill (prompt ≈35k tokens):

| kill (after prefill start) | slot freed | lag | freed at (after prefill start) |
|---|---|---|---|
| +2.6 s | t=11.76 s | **7.76 s** | ~10.3 s |
| +2.7 s (repeat) | t=11.58 s | **7.56 s** | ~10.3 s |
| +11.9 s | t=13.51 s | **0.49 s** | ~12.4 s |

The early-kill lag is deterministic, not noise — both runs freed at the same absolute ~10.3 s
after prefill start. The pattern that fits all three runs: a first connection check ~10 s into
processing, fine-grained (≤0.5 s) checks after it. That mechanism is an inference and is pinned
to this backend build; the operational facts are not: **in every run the prefill was abandoned
before its ~17.4 s completion, generation never started, and the follow-up request ran clean
(0.24 s)**. Worst observed slot-release lag: **7.8 s**; design bound: **~10 s** when a kill lands
early in a large prefill. Mid-decode (F162) remains the common case, at ≤0.25 s.

### F164 — two free instruments fell out of the probe

1. **`/slots` is enabled by default** on LM Studio's llama-server: per-slot `is_processing` and
   `n_ctx`, no flag needed, behind the same API key. That is a real-time occupancy witness the
   orchestrator gets for free — relevant to the liveness clock (OQ-W3-3) and W5's fleet gauges.
2. **An oversized request is rejected instantly and precisely**: a 105,009-token prompt against
   the 65,536 window returned 400 in 0.06 s with
   `{"type":"exceed_context_size_error","n_prompt_tokens":105009,"n_ctx":65536}` — it never
   touched the slot. Admission control can lean on this: the rejection is clean, immediate,
   carries the server's own exact token count, and (used deliberately) is a free tokenizer for
   budget arithmetic.

### F165 — `--spec-type draft-mtp` appears with no flag passed: it is LM Studio's default for this model

Today's load used the canonical command — **no MTP flag** — yet pid 22696's command line carries
`--spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-n-min 0 --spec-draft-p-min 0.75`,
byte-identical to the spec arguments F86 recorded on a *flagged* run. The sticky config
(`…user-concrete-model-default-config…IQ3_S-3.06bpw.gguf.json`) contains **no speculative keys
at all** and its mtime is unchanged (2026-08-08 14:59), so the default is LM Studio's own, for a
GGUF that ships MTP weights.

This breaks F78's premise without touching its rulings. F78 read the flagged command line as
proof "the flag is not silently ignored" — but the same arguments appear unflagged, so the
command line witnessed the *default*, not the flag. Whether F78's no-flag arm ran MTP is
unknowable (the control's command line was never captured); the exact null it measured is
exactly what MTP-vs-MTP would produce. **What survives: do not add the flag (it remains a
no-op), and every champion number stands — all cells ran the same default.** What falls: any
claim that the champion baseline runs *without* MTP. The held-constant rule gains a corollary:
**a command line proves presence, not provenance — capture the control's command line too.**
F78 (W1) and F86 (W2) corrected in place, dated.

## Consequences for the design

- **Kill-now is a socket close.** Drop the in-flight HTTP request, write the attempt's tombstone
  event; the server side cleans itself up with zero machinery. The cancellation problem is
  therefore **100 % client-side** — which sharpens item 6's tokio question: cancellation was
  tokio's one honest argument (F154), and this probe shows that argument is sufficient
  end-to-end, because dropping a future that owns the connection closes the socket and the
  server provably does the rest. Threads must solve "abort a blocking read" to reach the same place.
- **Slot re-availability is eventually-consistent, bounded at ~10 s.** The orchestrator should
  not assume the slot is free the instant it kills; it also need not care — the next request can
  simply be issued and queues server-side (F83), or `/slots` can be consulted (F164).
- No server restart, no slot leak, no ghost generation in any of the five runs.

## Confidence: high

Five kill runs plus one control, two paths, three independent witnesses agreeing in every run,
and the early-prefill lag reproduced to within 0.2 s. The mechanism *explanation* in F163 is
medium — it is a fit, not a source read — and pinned to backend 2.27.1; the bound is what the
design consumes.

---

# Item 3 — durability

## Question

§11's line is *"a task must survive a crash, a reboot and a model server hang. Compare a custom
state machine over a durable queue against anything the ecosystem offers."* Item 1 already chose the
shape of the state — a small enum whose variants carry their evidence, immutable attempts, and
status as a projection of a `seq`-ordered event log written through one `apply()`. This item asks
what actually holds that log, what it costs per transition, whether boot-as-replay is affordable,
and whether the Rust ecosystem already ships the thing rather than the parts.

Three sub-questions, because the brief's three failure modes are not one problem:

- **Crash** (the process dies mid-turn) — a storage-engine question.
- **Reboot** (the machine restarts, the model server is gone too) — a reconciliation question,
  mostly answered by item 1's contract table; what is left is the workspace.
- **Model-server hang** (the socket is open, nothing is coming) — a *detection* question that no
  storage engine can answer, and the one the family gets wrong three times out of three.

## Method

Three passes, 2026-08-19:

1. **Donor extraction**, same style as items 1 and 2: what each of the three repos actually persists,
   at what moment, and through which syscall. Every claim below carries file:line.
2. **A measurement**, because the recommendation turns on a cost nobody in the family ever paid.
   `research/spikes/w3-durability/append_bench.py` (stdlib only, W2 spike house style) times the
   `apply()` write path — event append plus status upsert **in one transaction** — across SQLite's
   two durability knobs, against a control that reproduces the family's current mechanism, plus a
   boot-as-replay run. Two repeats; the table below reports run 1, and run 2 landed within 2% on
   every row.
3. **Live ecosystem verification** against the crates.io API (retrieved 2026-08-19), because §11
   says *check last commit dates* and a durability dependency is the last place to take a README's
   word for liveness.

## Inherited

The inheritance map's durability-adjacent rows: the `file_locks` **table** PORT ("the one durable
piece of ABCC's lifecycle"), the stuck-task watchdog PORT-with-corrections, `ExecutionLog`'s row
shape PORT. W5 item 6 has already ruled the store: **SSE plus SQLite, WAL, single writer**, and one
monotonic `seq` serving as transport cursor, SQL cursor and scrub position (F123–F126). This item
does not reopen that choice — it tests it, tightens one pragma, and supplies the numbers W5 did not
need but W3 does.

## Findings

### 🚨 F166 — ABCC had a real database and never used it as one: `$transaction` appears once in the whole repo, and it is a read

`prisma.$transaction` occurs exactly once in ABCC's source — `packages/api/src/routes/tasks.ts:57`
— where it wraps `[findMany, count]` for a paginated list. A read. Every **write** in the lifecycle
is an independent statement, so every multi-step transition has a crash window in the middle of it.

The clearest case is the watchdog's recovery path (`stuckTaskRecovery.ts:256-334`), the eight-step
cleanup the inheritance map praises as *"better than most"* — and it is, in coverage. In atomicity
it is three unrelated writes and an in-memory call:

| Step | What it does | Durable? |
|---|---|---|
| 1 | `releaseFileLocks(task.id)` | yes, separate |
| 2 | `resourcePool.release(task.id)` | **no — process memory** |
| 3 | `task.update` → `aborted` | yes, separate |
| 4 | `taskExecution.updateMany` → `failed` | yes, separate |
| 5 | `agent.update` → `idle`, stats | yes, separate |

A crash between 3 and 5 leaves the task durably `aborted` while its agent stays durably `busy` with
`currentTaskId` pointing at it — and `getIdleAgents` filters on `status: 'idle'`
(`agentManager.ts:46`), so that agent is permanently out of the fleet.

The repo does contain one genuinely correct idiom, and it deserves to be carried: the claim at
`orchestratorService.ts:395-401` is a compare-and-set — `updateMany({where: {id, status: 'idle'}})`
followed by `if (agentUpdate.count === 0)` — and its own comment calls it *"Atomic agent
assignment"*. It is. Then `:416-417` writes the task to `in_progress` in a **separate** statement, so
the pair is not. The idiom is right; the boundary is drawn in the wrong place.

The one remaining transaction in the family is worth naming because of what it teaches: the MCP
gateway's `conn.transaction()` (`packages/mcp-gateway/src/adapters/postgres.py:136`) is a **batching
optimisation, not a correctness boundary**. It wraps an arbitrary batch drained from an in-memory
`deque`, and inside the transaction each statement is wrapped in its own `try/except` that logs and
continues (`:137-146`) — so a failed write is swallowed and the transaction commits the rest.
A transaction that cannot fail is not providing atomicity; it is providing throughput while looking
like atomicity. Same shape as F161's defect class, one layer down.

### 🚨 F167 — nothing reconciles at boot, and the only full recovery path is a button a human presses

`packages/api/src/index.ts:197-225` is the entire startup sequence: connect Prisma, connect the MCP
bridge, start three timers (`humanEscalation.startChecker`, `scheduler.start`,
`stuckTaskRecovery.start`), listen. No query of in-flight state, no sweep, no reconciliation.

So after a reboot: the in-memory resource pool comes back empty while the database still says agents
are `busy`; `in_progress` tasks sit until the 5-minute watchdog aborts them with
`errorCategory: 'timeout'`, which records a **false cause** (the machine restarted, it did not time
out); and `assigned` and `needs_human` tasks — which the watchdog's found-set never covers — stay
stuck forever. The one routine that would fix all of it, `forceRecoverAll`, has exactly one caller
in the repo: `packages/api/src/routes/agents.ts:389`, an HTTP route. It is the reset button, and it
only runs when a human presses it.

This is the same defect item 1 recorded from the type side (F147/F149), seen from the durability
side: **the state was durable and the recovery was not.** 2.0's boot-as-replay is the fix, and the
per-state contract table's last column is its specification.

### 🚨 F168 — the family's Rust durability is a whole-file rewrite of a mutable document, and a crash *during the save* costs the record

Neither Rust repo has a database in its orchestration path (`rusqlite` is in Claudette's manifest for
one purpose — the recall vector store, `Cargo.toml:97`). Durable state is JSON documents rewritten
in place, in four places, all with the same three properties:

| Site | Write | Cadence | On torn file |
|---|---|---|---|
| Claudette research progress (`run/research.rs:731-735`) | `std::fs::write` | per batch (`:1474`) | `load` (`:721-729`) returns `Err`, and the caller propagates it with `?` (`:1230`) — **the run refuses to resume** |
| Claudette findings store (`run/research.rs:780-784`) | `std::fs::write` | per batch (`:1453`) | same |
| Claudette session autosave (`runtime/session.rs:96` → `secrets.rs:31`) | `truncate(true)` + `write_all` + `flush`, no fsync, no rename (Windows path: plain `std::fs::write`) | **after every turn** (`run.rs:202-203`) | `try_load_session_at` (`run.rs:139-146`) — *"`Err` if it exists but is corrupt"* |
| BCF mission record (`db.rs:30-38`) | `std::fs::write` | **once, after the mission ends** (`mission.rs:382`, and `let _ =` discards the error) | record simply absent |

`std::fs::write` opens with truncate-then-write, so the window between the two syscalls is a window
in which the file on disk is shorter than valid JSON. The consequence is not "lose the last update"
— it is **lose the ability to resume at all**, because in three of the four sites a malformed file
is a hard error rather than a fallback to the last good state. There is no temp-file-plus-rename
anywhere in either repo's persistence path.

Three further properties of the same code:

- **Save errors are discarded.** Every `progress.save(...)` in the research driver ends `.ok()`
  (`:1403`, `:1474`, `:1501`, `:1506`, `:1518`, `:1521`). A full disk produces a run that reports
  success and cannot be resumed.
- **There is no atomicity across files.** A batch writes `FINDINGS.md` (`:1442-1450`, itself a
  read-whole-file-append-write-whole-file), then `findings.json` (`:1453`), then `progress.json`
  (`:1474`). A crash between the second and third re-runs the batch on resume, and `append_batch`
  (`:787`) appends the same findings again under fresh ids. **Duplicate findings are the designed
  behaviour of that crash window.**
- **BCF has no mid-mission durability at all.** The single save is after the last round; a crash at
  round 8 of 9 leaves only whatever the codegen already wrote into the output directory.

None of this is sloppiness — it is the correct amount of machinery for a single-user CLI that
usually finishes. It is the wrong amount for an orchestrator whose whole claim is that a task
survives the machine restarting.

### F169 — measured: full ACID costs 0.93 ms per transition here, and the family's mechanism is the only one that cannot afford the job

`append_bench.py`, this machine, log on the project's NVMe (D:), 2000 transitions per configuration.
"Transition" is the real `apply()` shape: an event row appended and the status projection row
upserted **in the same transaction**.

| Configuration | transitions/s | µs each |
|---|---|---|
| `journal=DELETE`, `synchronous=FULL` — SQLite's default, and what `recall.rs:240` opens with | **293** | 3410 |
| WAL, `synchronous=FULL` | **1076** | 929 |
| WAL, `synchronous=NORMAL` | **11197** | 89 |
| WAL, `NORMAL`, event only (no status upsert) | 14443 | 69 |
| WAL, `NORMAL`, 16 events per transaction | 54637 | 18 |

And the control — the family's mechanism, a mutable status document rewritten whole per update:

| Control: whole-file JSON rewrite | updates/s | µs each |
|---|---|---|
| document holding 10 task rows (1 KiB) | 3224 | 310 |
| document holding 200 task rows (24 KiB) | 597 | 1674 |
| document holding 2000 task rows (247 KiB) | 68 | 14708 |

Two things fall out, and the second is the one that decides the design.

**The rewrite degrades with the run; the append does not.** Ten rows to two thousand costs the
rewrite 47× — because it is O(size of everything) per O(1) change. The append is flat. That is not a
micro-optimisation argument, it is the reason the mechanism cannot be scaled up: 2.0's log is also
the console's replay source (W5 F123), so it is *designed* to grow.

**Full ACID is affordable, so the usual tradeoff does not bind here.** SQLite's docs are explicit
(sqlite.org/pragma.html, retrieved 2026-08-19): `NORMAL` in WAL mode is *"durable across application
crashes"* but *"might roll back following a power loss or system crash"*, while `FULL` *"is atomic,
consistent, isolated, and durable (ACID) in WAL mode"*. The received wisdom is to take `NORMAL` and
accept the power-loss window.

Price it against the work being recorded. One decoded token costs ~13–14 ms (70.12–75.84 tok/s, W1
F80), so a `FULL` transition is ~7% of a *single token* — and W5 F123 already ruled that the log is
written at **action** granularity, not token granularity, where one event covers a tool call's worth
of generation: hundreds of tokens, seconds of wall clock. Against that unit, `FULL` is well under a
tenth of a percent. **Take `FULL`. Nothing on this machine's budget notices it, and it converts
"survives a crash" into "survives the power cut too."**

Caveat, stated plainly: this is CPython's `sqlite3`, not `rusqlite`. Interpreter overhead inflates
the cheap rows and is invisible in the expensive ones, which are fsync-bound. The ratios are disk
behaviour and carry; the absolute rates are a floor.

### F170 — boot-as-replay is free at this scale, and the snapshot threshold is about a million events

Item 1's recommendation makes boot the same code as replay. That is only sound if replay is cheap,
so the spike built a 100,000-event log and folded it into the projection:

- built in 0.66 s (151,556 events/s at 500 per transaction),
- **25.1 MiB on disk, 263 bytes per event**,
- **replayed in 94 ms — 1,059,017 events/s.**

So the projection rebuild at a scale far beyond anything W5 F123 projects (months of real driving is
~16k action-granularity events) costs under a tenth of a second. **No snapshot mechanism is needed
for 2.0.** The crossover where replay reaches one second is ~1M events, ~265 MiB — that is the
number to watch, and it is the same number OQ-W5-9's retention question turns on. Until then, a
snapshot table would be a cache with no cache miss to justify it.

This also settles the strongest objection to log-primary state: "you will need snapshots, and then
you will need to keep them consistent with the log." Not at this scale, and the threshold is
measured rather than assumed.

### F171 — the ecosystem's durable-execution engines all want a server, and its event-sourcing crates are Postgres-shaped

crates.io API, retrieved **2026-08-19**. "Newest" is the most recently published version of any
kind, so a stable line stalled behind a release candidate shows up as such.

| Crate | Latest stable | Newest published | 90-day downloads | Verdict for this design |
|---|---|---|---|---|
| `rusqlite` | 0.40.2 | 0.40.2 @ 2026-08-08 | 29.9M | ✅ **already in the tree** (Claudette `Cargo.toml:97`, `bundled`) |
| `redb` | 4.2.0 | 4.2.0 @ 2026-08-17 | 4.0M | alive, ACID, pure Rust — but a KV store, no SQL |
| `fjall` | 3.1.9 | 3.1.9 @ 2026-08-15 | 417k | alive; LSM, same no-SQL objection |
| `sled` | 0.34.7 | **1.0.0-alpha.124 @ 2024-10-11** | 2.5M | 1.0 stalled ~22 months — not a candidate |
| `persy` / `heed` / `rocksdb` | 1.8.1 / 0.22.1 / 0.25.0 | 2026-06-30 / 2026-04-07 / 2026-08-16 | 137k / 1.3M / 6.2M | alive; KV or a C++ dependency |
| `cqrs-es` + `sqlite-es` | 0.5.0 + 0.5.0 | 2025-12-30 + **2026-04-23** | 27.8k + **621** | a real SQLite event-sourcing path — see below |
| `disintegrate` | 4.0.0 | 4.0.0 @ 2026-02-02 | 2.9k | PostgreSQL only (`disintegrate-postgres`) |
| `esrs` | 0.18.0 | 0.18.0 @ 2024-11-25 | 7.3k | Postgres; ~21 months since a release |
| `eventually` / `thalo` | 0.4.0 / 0.8.0 | 2020-10-04 / 2023-11-21 | 87 / 385 | dead |
| `apalis` (+`apalis-sql`) | 0.7.4 | **1.0.0-rc.9 @ 2026-05-06** | 264k | job queue; `sqlite` feature exists on 0.7.4 but **vanished from the 1.0 rc's feature list** |
| `underway` | 0.2.0 | 0.2.0 @ 2025-07-16 | 5.5k | Postgres only, ~13 months stale |
| `restate-sdk` | 0.11.1 | 0.11.1 @ 2026-08-14 | 390k | healthy — and requires a **separate Restate runtime process** |
| `temporal-sdk-core` | none | **0.1.0-alpha.1 @ 2021-04-22** | 522 | crates.io presence is vestigial; Temporal needs a cluster regardless |
| `dbos` | 0.1.1 | 0.1.1 @ 2026-07-13 | 39 | brand new, Postgres-backed |
| `obeli-sk` | 0.5.0 | 0.5.0 @ 2024-10-11 | 63 | ~22 months, 63 downloads |

Three patterns, and each disqualifies a whole category:

1. **Durable execution as a product means a server.** Restate's own SDK README describes services
   that register with the runtime and are tested against *"a Docker-deployed restate server"*
   (github.com/restatedev/sdk-rust, retrieved 2026-08-19); Temporal needs a cluster; DBOS needs
   Postgres. W5 F95/F125 already established that a container is the thing 2.0 exists to escape.
   This category is out on the install story alone, before any technical comparison.
2. **Event sourcing in Rust is written for Postgres.** The maintained frameworks ship
   `-postgres` crates; SQLite appears once, as `sqlite-es`, a separate single-maintainer repo at
   **621 downloads in 90 days**. That is a real and honest option — it was found by checking rather
   than assumed away — and it is evaluated in the options table below.
3. **Job queues are the wrong layer.** `apalis` durably retries *functions*; it has no opinion about
   a seven-variant lifecycle, per-state watchdog contracts, or an attempt chain. Adopting it would
   leave every W3 problem unsolved and add a dependency whose stable line is nine months old with
   the 1.0 in release candidate since May.

**The ecosystem offers storage engines and it offers servers. What it does not offer, for a
single-binary local-first agent orchestrator, is the middle.**

### 🚨 F172 — three repos, three total-duration timeouts, zero idle-gap timeouts: nothing in the family can tell a hung model from a slow one

The brief's third failure mode is the model server hanging. Every donor bounds the *whole request*
and none bounds *the gap between bytes*:

| Repo | Bound | Where |
|---|---|---|
| Claudette | 300 s total | `api.rs:147` → `.timeout(...)` at `:237` |
| BCF | **1800 s** total | `llm.rs:133` |
| ABCC (Python) | 120 s total | `main.py:19` (`litellm.request_timeout`), `chat.py:75`/`:151` (`httpx`) |

A grep for read/idle timeouts across both Rust repos returns exactly one hit —
`google_auth.rs:548`, the OAuth loopback listener — and nothing in any model path.

The consequence is symmetric and both halves are bad. A **hung** server holds a slot for the full
bound (30 minutes, in BCF's case) because nothing distinguishes silence from work. A **healthy but
long** generation is killed at the bound for the crime of being slow — the same defect ABCC has on
the task clock, where the watchdog measures `assignedAt` instead of last progress.

This is the durability half of item 1's contract table row for `Engaged`, and it confirms that row
from a second direction: **the liveness clock must be time-since-last-progress, at every level of
the stack — the task, and the socket.** It also means the hang is not a storage problem at all.
Recovery is already known to be cheap: F162 measured the slot freeing in ≤0.25 s on a socket close,
so detection is the entire cost.

> ⚠ **Corrected in part by F198 (item 6, 2026-08-20), and only for the Claudette row.** Measured:
> `reqwest`'s blocking `timeout` is a **per-read** budget on a streamed body, so Claudette's 300 s
> is an *inter-chunk gap* on both streaming paths and a total only on the `resp.json()` fallback —
> the same constant meaning two things depending on a response header. The table's *"Bound: total"*
> is therefore wrong for Claudette's normal path. **What survives is the conclusion, restated about
> the value rather than the mechanism:** 300 s of silence between tokens tolerates a hang rather
> than detecting one, and the BCF/Python rows are unaffected. F199 sets the replacement values
> (champion 90 s, R3 180 s, per request).

### F173 — the log and the workspace are two stores with no shared transaction, and nothing in the family bridges them

The event log can restore, exactly, what the operator saw. It cannot restore what the agent touched.
W5 F123 measured the gap and it is three orders of magnitude: a task's narration is ~4 KB, while
this repo's `runs/` directory is 3.1 GB of working directories and fixtures.

So after a crash in `Engaged`, the durable store says "attempt A, progress at `seq` N" while the
files on disk are in whatever half-edited state the tool calls left them. There is no mechanism in
any donor that closes this:

- ABCC serialises access with a `file_locks` table but never snapshots content.
- Claudette's only pre-image mechanism is `transcript::snapshot_to_trash` (`transcript.rs:149`),
  called per mutated path from `tools/file_ops.rs:284` and `tools/fuzzy_apply.rs:116` and unwound by
  `/undo` (`commands.rs:492`) — a per-file, per-turn undo, not a workspace marker.
- Git worktrees appear in the family exactly once, in BCF's SWE-bench harness
  (`swebench.rs:307-317`), never in the orchestration path.

The mechanism is therefore *proved to run on this machine* and *never wired to the lifecycle*. The
requirement this generates is stated in the recommendation and the choice of mechanism belongs to
W6 item 6, which owns per-task isolation and its RAM cost.

## Options compared

Scored against: (A) survives crash, reboot and hang; (B) zero daemons and zero containers (F95/F125);
(C) expresses item 1's write path — one writer, event and projection in one transaction, boot as
replay; (D) serves W5 F126's one-integer contract (SSE cursor, paged read, scrub); (E) dependency
risk, live-verified 2026-08-19; (F) implementation weight.

| Option | A | B | C | D | E | F |
|---|---|---|---|---|---|---|
| 1. Port v1: Postgres, mutable rows, statements not transactions | ✗ — F166/F167 are this option's observed behaviour | ✗ container | ✗ | ✓ | low | medium |
| 2. Keep the family's Rust shape: JSON documents rewritten whole | ✗ — a crash in the save costs the record (F168) | ✅ | ✗ O(n), no transaction | ✗ no paged read | none | low |
| 3. Embedded KV: `redb` or `fjall` | ✅ | ✅ | ✅ | partial — range scans and secondary indexes hand-rolled | low; both fresh | medium-high |
| 4. **SQLite event log + projection, `apply()` hand-written** | ✅ | ✅ | ✅ by construction | ✅ the integer *is* the primary key | **lowest — already in the tree** | **medium-low** |
| 5. `cqrs-es` + `sqlite-es` | ✅ | ✅ | partial — aggregate model, not per-state contracts | ✅ | ⚠ 621 dl/90d, single maintainer, pulls `sqlx` | low |
| 6. `apalis` over SQLite | partial — retries jobs, not lifecycles | ✅ | ✗ | ✗ | ⚠ stable 9 months old, 1.0 in rc | low |
| 7. Restate / Temporal / DBOS | ✅ | ✗ **server process** | ✅ | ✗ | varies | high |

## Recommendation

**Option 4**, which is W5 F125's ruling with one pragma tightened and the write path specified.

### 1. The store, and the two pragmas that are not defaults

SQLite under the 2.0 equivalent of `~/.claudette/`, opened by **one writer process**, with:

```
PRAGMA journal_mode = WAL;          -- not the default; 3.7x on the measured write path
PRAGMA synchronous  = FULL;         -- not the WAL convention; buys power-loss durability for 929 us
PRAGMA foreign_keys = ON;           -- not the default either
PRAGMA busy_timeout = 5000;         -- readers (console) must never see a bare SQLITE_BUSY
```

`FULL` rather than the usual `NORMAL` is the one place this item overrides received practice, and
F169 is the reason: the tradeoff everyone else is making assumes the write rate is the bottleneck,
and here it is three orders of magnitude away from being one. Note also that `recall.sqlite` runs
today on *neither* pragma (`recall.rs:240` opens with SQLite's defaults, so rollback-journal at
293 transitions/s) — 2.0's store is a new file and inherits none of that.

### 2. The schema, which is item 1's model with nothing added

```sql
CREATE TABLE event (                      -- the store of record; append-only, never updated
  seq        INTEGER PRIMARY KEY AUTOINCREMENT,   -- W5 F126's one integer, four roles
  task_id    TEXT NOT NULL,
  attempt_id TEXT,
  kind       TEXT NOT NULL,
  payload    TEXT NOT NULL,
  at_unix_ms INTEGER NOT NULL
);
CREATE TABLE task_status (                -- a projection: derivable, rebuilt at boot, never authoritative
  task_id   TEXT PRIMARY KEY,
  state     TEXT NOT NULL,                -- the seven-variant enum
  since_seq INTEGER NOT NULL,             -- every variant's `since`, as a log position
  evidence  TEXT                          -- the variant's carried data
);
CREATE TABLE attempt (...);               -- immutable rows; cause = Fresh|Retry|Rescope|Edit|Replay
CREATE TABLE depends_on (task, task);     -- first-class edges (F109)
CREATE TABLE checkpoint (...);            -- fork points, incl. the workspace marker (below)
CREATE INDEX event_task ON event(task_id, seq);
```

`task_status` exists for query convenience and for the console's opening screen. It is **not** a
second source of truth: it is written only by `apply()`, in the same transaction as the event that
justifies it, and boot verifies it against the log rather than trusting it.

### 3. `apply()` — the whole durability mechanism, in one sentence

`BEGIN IMMEDIATE` → validate the command against the current state (exhaustive `match`, refusal is a
value) → `INSERT INTO event` → upsert `task_status` → `COMMIT`. That is the 89 µs / 929 µs measured
above. Everything F166 got wrong is unrepresentable here not because anyone was careful but because
there is no other function that writes.

The compare-and-set idiom from `orchestratorService.ts:395-401` survives as the shape of admission:
claims are conditional writes whose zero-row result is a refusal, not an exception. What changes is
that the claim and the state change are now the same transaction.

### 4. The three failure modes, and what each costs

| Failure | What is lost | Recovery |
|---|---|---|
| **Process crash** | the un-checkpointed in-flight generation only | boot replays the log (94 ms/100k, F170); every `Deployed`/`Engaged` task with no live worker gets its contract-table treatment — attempt tombstoned `HardFailure(orphaned)`, task per retry policy |
| **Reboot** | the same, plus the model server | identical path, with one addition: **re-admission must re-check backend health before any task re-enters `Deployed`**, because the reboot invalidated the assumption every `Deployed` row was made under |
| **Model-server hang** | nothing durable | not a storage problem — an **idle-gap timeout on the stream** (the family has none, F172) trips the progress clock; the kill is a socket close and the slot frees in ≤0.25 s (F162) |

**The reboot case needs no mechanism the crash case did not already need.** That is the payoff of
boot-as-replay: there is one recovery path, it runs on every start, and it therefore cannot rot the
way `forceRecoverAll` did — a routine whose only caller was a button.

### 5. Two requirements this item generates for other workstreams

- **W6 item 6 (per-task isolation):** a `checkpoint` is only meaningful if it names a **workspace
  state**, not just a `seq`. F173 shows the family has no such marker and that git worktrees already
  run on this machine in BCF's harness. W6 owns the mechanism and its RAM cost; W3's requirement is
  narrow: *the checkpoint row must carry an identifier that can restore the workspace, and
  `Holding`/fork must refuse to promise resumability without one.*
- **The broker (item 4):** control-channel commands must be durable *before* they are acknowledged
  to the operator, or a crash between "you pressed pause" and the pause costs the operator their
  belief about what the system is doing. Arrival time is already part of the contract (F132); this
  makes durability part of it too.

### 6. What not to build

No job-queue crate, no CQRS framework, no second embedded store, no snapshot table, and no
retry/backoff library. Every one of them is either a layer 2.0 does not need or a dependency at the
exact centre of the system's correctness, and F170 shows the snapshot in particular has no
justification for another two orders of magnitude of growth.

## Rejected alternatives and why

- **`redb` / `fjall` (option 3).** Both are alive and genuinely good, and if the console needed no
  queries this would be closer. But W5 F126's whole argument is that `seq` is simultaneously the SSE
  cursor, the SQL cursor and the scrub position; `SELECT … WHERE seq > ? ORDER BY seq LIMIT n` is
  the paged read the console needs and v1 never built. In a KV store that is a hand-rolled range
  scan, and every secondary access path — by task, by attempt, by state — is a hand-maintained
  index, which is exactly the class of hand-maintained derived state F149 caught drifting. Adding a
  second store beside `recall.sqlite` also doubles the backup and migration story for no gain.
- **`cqrs-es` + `sqlite-es` (option 5).** The honest near-miss. It rejects on three counts: the
  SQLite store is one person's separate repository at 621 downloads per 90 days, which is a
  bus-factor-one dependency holding the system's source of truth; it brings `sqlx` and an async
  executor into a codebase whose HTTP client is deliberately blocking (`reqwest::blocking`,
  `egress.rs:279`); and its aggregate/command/event abstraction does not carry the things this
  design is actually made of — per-state resource contracts, watchdog policy, and the admission pool
  derived from state. We would implement all of that anyway, inside someone else's traits.
- **`apalis` (option 6).** Wrong layer, as F171 argues, and its stable line is 0.7.4 from
  2025-11-18 with 1.0 in release candidate since 2026-05-06 — the `sqlite` feature that makes it
  daemon-free is present on the old line and absent from the rc's feature list. Adopting a
  mid-migration dependency for the wrong abstraction is two risks for no benefit.
- **Restate / Temporal / DBOS (option 7).** These are the right idea at the wrong scale. They solve
  durable execution properly and they all require a process 2.0 has spent its whole design budget
  avoiding. Worth revisiting only if W10's multiplayer work ever makes a coordinator unavoidable —
  and W10 should read Restate's journal-and-replay model before designing its own.
- **Keeping the JSON-document shape (option 2).** Rejected on F168 and F169 together: it is not
  crash-safe in the sense the brief requires, and it is the only measured option that gets slower as
  the thing it records gets bigger.
- **`synchronous = NORMAL`.** Rejected on measurement rather than principle. It is 10× faster and
  the speed is worth nothing here, while the thing it costs — surviving a power cut — is exactly
  what a local-first tool on a desktop machine should not be trading away silently.

## Effect on fun

Three effects, one of them the point of the whole item.

**Replay stops being a feature that rots.** Boot and scrub are the same fold over the same log, so
the code path behind the timeline minimap is exercised on every single start. Compare v1, where the
full-recovery routine was reachable only from a button, and W5 F113's four unstyled states, which
survived because nothing forced them to be handled.

**"Close it and reopen it" becomes true.** The felt property is small and constant: killing the app
mid-run is not a decision. That is a different relationship with a tool than one where you first
think about what you will lose — and it is the honest version of the promise ABCC's console made and
the reset button quietly withdrew.

**No install cost.** SQLite is already in the binary (`bundled`), so the durable store adds a file,
not a service. The comparison that matters to David is the one W5 already made: v1 wanted Postgres
and Redis in containers before it would show you a task list.

The one cost worth naming: `FULL` means every transition touches the disk, so a very chatty
heartbeat granularity (OQ-W3-3) would be felt as disk activity on an idle-looking machine. The
measurement says that is 929 µs a time and W5 F123 says the log is written at action granularity —
but if OQ-W3-3 lands on something finer, this is the row to re-measure.

## Open questions

| # | Question | Waiting on |
|---|---|---|
| OQ-W3-11 | Retention and archival: the log is the console's replay source, so it cannot simply be truncated. Same question as OQ-W5-9 — answer once | W5, W8 volume data |
| OQ-W3-12 | The workspace checkpoint marker: git worktree, git stash-object, or a copied pre-image tree | **W6 item 6** |
| ✅ OQ-W3-13 | The idle-gap timeout value — what inter-token gap actually means "hung" on this hardware | **ANSWERED by W11 item 5, F292**, in two halves: at the socket, set it from the per-round cost (F198 showed the mechanism already exists); at the *task*, do not build it from the outside at all — a working agent is silent for up to 669 s on a cell that passed, so the progress clock is the iteration boundary |
| OQ-W3-14 | Does `attempt` stay a table, or become a second projection of the log? Leaning table: attempts are immutable, so the duplication cannot drift | item 5 (escalation lineage) |
| ✅ OQ-W3-2 | **ANSWERED here** — `Blocked` is derived from `depends_on` edges, not stored. A stored variant is denormalised state with no writer that owns it, which is F149's drift bug re-created on purpose | — |
| OQ-W3-4 | Still open (W2's prefix-cache interaction), but durability narrows it: slot occupancy is *derived* from state, so whichever way it lands it is a scheduler policy change, not a schema migration | W2 |

## Confidence: high

The donor findings are grep-level facts with file:line, verified this session in all three
checkouts. The cost claims are measured on this machine with a script in the repo, repeated twice
within 2%, and the one place a citation carries load — `NORMAL` versus `FULL` under WAL — is quoted
from SQLite's own documentation with a retrieval date. The ecosystem verdicts come from the
crates.io API on 2026-08-19 rather than from reputation, and the check corrected one assumption in
the process: `sqlite-es` exists, so the CQRS option had to be argued rather than dismissed.

What would lower it: OQ-W3-3 landing on a heartbeat granularity far finer than action-level, which
would move F169's affordability argument; and W6 item 6 finding that workspace checkpointing is
expensive enough to change what `Holding` can promise. What would raise it: re-running the spike
through `rusqlite` once the 2.0 crate exists, to replace CPython's floor with the real number.

---

# Item 4 — the control channel and the broker

## Question

§11's line is *"human-in-the-loop pause and resume — the single most important capability in the
list, because it is the one that turns the console from a viewer into a command center."* W5 then
spent an item on the verbs and handed W3 five requirements: the worker selects on a control channel
at **every step boundary** (F100); the permission event carries `Allow | Deny | Redirect(String)`
(F106); an answer must not be accepted if the operator had no chance to read the prompt, so
**arrival time is part of the contract** (F132); grants are scoped `{session, tool, action, path}`
(F133); and two verbs the first pass missed — **stop-but-keep-the-work** and
**queue-while-streaming** (F138). Item 3 added a sixth: a control command must be **durable before
it is acknowledged**, or a crash between "you pressed pause" and the pause costs the operator their
belief about what the system is doing.

So, precisely: **where does the control channel live once there are two subscribers, what does it
carry, and what latency does each verb actually get?** OQ-W5-3 is this item's to answer, and so is
OQ-W3-10 (how the control point composes with spawned sub-agents).

Three sub-questions, because they have different kinds of answer:

- **Identity and transport** — a design question the donors answer by counter-example.
- **Arrival, loss and durability** — a rules question; the rules must live somewhere no surface can
  forget them.
- **Latency per verb** — an arithmetic question, answerable today from numbers already measured
  (F80, F162, F169), and the one that decides how many mechanisms the channel is.

## Method

Fourth donor extraction pass, 2026-08-19, same three checkouts as items 1–3: ABCC v1 at
`D:\dev\agent-battle-command-center` HEAD `d5528ea`, BCF at `D:\dev\battle-command-forge` HEAD
`d6c1601`, Claudette at `D:\dev\claudette` HEAD `af3f804`. This pass follows one thread end to end
in each repo — *an operator forms an intention; what reaches the thing doing the work?* — which
means reading the **callers**, not just the handlers. Every claim carries file:line. No new
measurement was taken: the latency table is arithmetic over W1 F80, W3 F162/F163 and W3 F169, and
it is labelled as such.

## Inherited

| What | Source | Verdict here |
|---|---|---|
| Redirect + undo exist in the family | `prestudy/inheritance-map.md` §12 item 3 | true of the CLI only — and F177/F181 show the redirect has now been lost three separate ways |
| Per-request rendezvous, fail-closed on disconnect | Claudette `tui_worker.rs:88-140` | the **semantics** REUSE; the **mechanism** cannot survive two subscribers (F180) |
| The permission gate as the loop's existing door | F157, `conversation.rs:659-664` | REUSE, and it is necessary but not sufficient (F184) |
| `humanEscalation`'s timeout-then-escalate | ABCC `humanEscalation.ts:36-56` | **REUSE** — the family's one correct answer to operator loss (F178) |
| Kill / abort / recover paths | ABCC `orchestratorService.ts:592`, `taskExecutor.ts:282`, `stuckTaskRecovery.ts:250` | DISCARD — all three are the same database write (F174) |

## Findings

### 🚨 F174 — v1's stop verbs never reach the thing doing the work: four paths, one database write, zero signals

v1 executes a task by POSTing to the Python agent service and awaiting the response
(`executor.ts:71-76`, `taskExecutor.ts:763`), with a 600-second budget (`EXECUTE_TIMEOUT_MS`,
`executor.ts:8`). Four different operator- or system-initiated paths stop a task. Traced to their
ends:

| Path | Entry | What it does |
|---|---|---|
| Kill mission | `orchestratorService.ts:592-653` | releases agents + pool slots, writes `status:'aborted'` on every non-terminal task |
| Abort task / abort agent | `routes/tasks.ts:268`, `routes/agents.ts:320` → `taskQueue.ts:103` → `taskExecutor.ts:282-343` | releases locks + pool slot, writes `status:'aborted'` |
| Watchdog recovery | `stuckTaskRecovery.ts:250-271` | releases locks + pool slot, writes `status:'aborted'` |
| Human reject | `taskQueue.ts:154-156` | calls the same `abortTask` |

**Not one of them calls `ExecutorService`.** `taskExecutor.ts` imports it (`:26`) and constructs it
in exactly one place — the *start* path at `:736`. `abortExecution` exists (`executor.ts:87-102`)
and has **one caller in the repository**: `routes/execute.ts:114`, an endpoint the console does not
use.

And that one caller reaches a no-op. `POST /execute/abort` (`agents/src/main.py:592-601`) reads:

```python
if task_id in execution_state:
    execution_state[task_id]["status"] = "aborted"
    del execution_state[task_id]
return {"aborted": True, "task_id": task_id}
```

`execution_state` is declared at `main.py:36` and — verified by grep over the whole package — is
**written nowhere else**. The membership test is always false, the body is unreachable, and the
endpoint returns `{"aborted": true}` unconditionally. The TypeScript side then treats that `200` as
success (`executor.ts:99`) and reports `{aborted: success}` to its caller.

So the family's most-cited control verb is, end to end, a status column plus a hard-coded `true`.
This is the same disease as F158 and F161 — *a default that pretends to be a measurement* — moved
from the verifier into the control plane, where it is worse: a wrong score misleads, a wrong
`aborted: true` makes the operator stop watching.

### 🚨 F175 — the abort releases the file locks while the worker is still writing

The lie is not confined to the display. All three internal stop paths perform the same three steps
in the same order (`taskExecutor.ts:292-299`, `stuckTaskRecovery.ts:256-262`,
`orchestratorService.ts:604-632`): release file locks, release the resource-pool slot, write
`aborted`. The POST is still open, the agent is still iterating, and the file locks that the
inheritance map calls *"the one durable piece of ABCC's lifecycle"* have just been handed back to
the assigner.

The watchdog case is the sharpest, because it fires **with no operator involved at all**: a task
that looks stalled for `taskTimeoutMs` has its locks released while its worker keeps editing, and
the pool slot it held becomes immediately available to a second task that may now be told to edit
the same files. The concurrency control and the stop verb are wired backwards — locks are released
on *intent to stop* rather than on *confirmation that work has ceased*.

**Requirement this generates:** resources are released by the **worker's own exit**, or by the
broker after the worker's death is *observed* — never by the operator's command. Item 3's `apply()`
already forces the state change and the release into one transaction; F175 says the transaction may
only be written by the party that knows the work has stopped.

### 🚨 F176 — pause is a status rename, and it collides with the state the watchdog acts on

`agentManager.pauseAgent` (`agentManager.ts:82-110`) writes `status: 'stuck'` with the comment
`// Using stuck as "paused"`, emits a socket alert of type `agent_stuck` titled *"Agent Paused"*,
and returns. Nothing is signalled. The agent's task keeps running.

Two consequences the rename creates on its own. First, the agent status `'stuck'` has exactly two
writers (`agentManager.ts:93`, `taskQueue.ts:120`) and **no reader that acts on it** — pausing an
agent changes a colour. Second, the task underneath stays `in_progress`, which *is* the watchdog's
found-set (`stuckTaskRecovery.ts:194`, item 1 F148), so a "paused" agent's task remains on the
timeout clock and is eventually aborted with `errorCategory: 'timeout'` — through the F174 path, so
also without stopping. **Pause does not stop the work, and it does not stop the clock either.**
`resumeAgent` (`agentManager.ts:112`) then restores `busy` on a task that never stopped.

### 🚨 F177 — the operator's instruction is collected, validated, transmitted, and discarded

v1's console renders a human-input panel when a task is `needs_human`
(`ui/src/components/main-view/TaskDetail.tsx:239-270`): a textarea placeheld *"Enter your input or
instructions…"* and three buttons — Approve, **Modify**, Reject — where Modify is
`disabled={loading || !humanInput}`, i.e. **the UI enforces that the operator has typed something
before it will let them send it**. `handleSubmitInput` (`:55-58`) posts the text. The route accepts
it, and a second field besides:

```ts
input: z.string(), action: z.enum(['approve','reject','modify']), modifiedContent: z.string().optional()
```

(`routes/tasks.ts:238-241`), then calls `taskQueue.provideHumanInput(id, data.input, data.action)`
— dropping `modifiedContent` at the call site. And the service (`taskQueue.ts:147-186`) **never
reads `input` at all**: `reject` aborts, while `approve` and `modify` fall through to the identical
branch that sets the task back to `assigned`.

So the operator types an instruction, the interface validates that they typed it, the wire carries
it, and the handler resumes the task exactly as if they had clicked Approve. That is the third
distinct way this family has lost the same verb:

1. **Claudette CLI** — has it, smuggled inside a deny reason (`cli_prompter.rs:127-134`).
2. **Claudette TUI** — dropped it at the channel type, `SyncSender<bool>` (F106).
3. **ABCC v1** — renders it, validates it, transmits it, discards it.

Three surfaces, three losses, zero compiler errors. **The redirect is not a feature that keeps
getting deprioritised; it is a feature that keeps getting *deleted in transit*, because it has never
once been a variant of a type that something exhaustively matches on.**

### F178 — v1's one real gate is agent-initiated, and its loss rule is the family's only correct one

Worth stating plainly, because items 1–3 have been unkind to this donor and this part is right.

The only producer of `needs_human` in the entire repository is a **tool the model can call**:
`escalate_task(task_id, reason, urgency)` (`agents/src/tools/cto_tools.py:180-197`) PATCHes the
task. `taskQueue.requestHumanInput` (`:107`) exists for the same purpose and has no caller. There is
**no operator-initiated gate and no per-tool-call gate anywhere in v1** — which is the structural
reason its console is a viewer: the operator can only answer questions the model chose to ask.

But the *loss* rule is written down and it runs. `HumanEscalationService` (`humanEscalation.ts`)
polls every 60 s for tasks that have been `needs_human` longer than `config.humanTimeoutMinutes` and
**escalates them to another agent** (`:36-56`). That is F101's requirement — a defined behaviour for
"the operator never answered" — implemented, in the family, once. It is the shape 2.0 should keep:
an unanswered control request is not a hang and not a silent default; it is a transition to a
written state, on a clock, visible.

### F179 — BCF's only gate is at a round boundary on blocking stdin, and its TUI switches it off

BCF has exactly one human-in-the-loop decision point (`mission.rs:517-583`), and it is well shaped
for what it is: after each fix round it prints the gate score and offers `[a]` accept, `[f]` another
fix round, `[q]` abort mission, then reads a line. On `q` it writes the report and returns cleanly
(`:585-597`) — the only place in the family where a stop verb produces a durable artefact.

Three defects, each of which becomes a rule for 2.0:

- **The granularity is a whole round.** Architect → tester → coder → verify runs to completion
  before the operator is asked anything. There is no mid-round control of any kind: BCF contains no
  `AtomicBool` and no cancellation token, verified by grep over `src/`.
- **It reads stdin, blockingly, from inside an `async fn`** (`:573`), parking a tokio worker —
  F154's "tokio in the dependency tree, not in the architecture", in the one place it is
  load-bearing.
- **The TUI hard-codes `runner.auto_mode = true`** (`tui.rs:739-741`), and `auto_mode` replaces the
  whole gate with a printed `[AUTO]` decision (`mission.rs:519-538`). So from the surface with the
  display, the gate never appears — **and neither does `[q]`.** The only way to stop a running
  mission from BCF's TUI is `q`/`Esc` → `should_quit` → exit the process (`tui.rs:1257`).

That is F106's asymmetry a second time, in the other donor, on a different verb: **the surface with
the better display has the worse control.** Two donors, two independent occurrences, is not an
accident — it is what happens when control is a property of a surface instead of a property of the
core.

### 🚨 F180 — Claudette's request identity is a channel, not data — which is exactly why it cannot serve two subscribers

Claudette's mechanism is the good one in the family, and reading it closely shows why it has to be
replaced rather than extended. `TuiPrompter::decide` (`tui_worker.rs:108-139`) creates a **fresh
rendezvous channel per request** and ships the sender inside the event; the doc comment above it
(`:88-97`) states the two properties this buys: a stale answer from an earlier prompt *"can never
satisfy a later one, by construction"*, and every render-loop exit path drops the sender, so
`recv()` returns `Disconnected` and the tool is denied rather than hung.

Both properties are real. Both are properties **of the channel object**, not of any data. Look at
what the request itself carries (`permissions.rs:70-75`):

```rust
pub struct PermissionRequest { tool_name: String, input: String,
                               current_mode: PermissionMode, required_mode: PermissionMode }
```

No request id, no timestamp, no task or attempt identity, no operator. The *only* thing that
distinguishes this request from the next identical one is which `SyncSender` it arrived with.

A `SyncSender` cannot be written to SQLite, cannot be delivered to two subscribers, cannot be
acknowledged durably, and cannot be re-offered after a crash. **So the two-subscriber case is not a
refactor of this mechanism; it is a replacement of it — and item 4's job is to re-create both of its
safety properties in data.** That is OQ-W5-3's answer, and it is mechanical rather than a matter of
taste: *the channel must become a row, and the identity must become a `seq`.*

### F181 — the third branch is not in the type, which is why it was droppable

`PermissionPromptDecision` has two variants (`permissions.rs:77-81`):

```rust
pub enum PermissionPromptDecision { Allow, Deny { reason: String } }
```

The redirect that F106 calls the family's richest control verb is not one of them. It is a
*formatting convention inside `Deny.reason`* — `gate_line_decision` (`cli_prompter.rs:118-135`)
builds the string *"The user declined to run this tool and gave this instruction instead — follow it
before continuing: {trimmed}"*, and the model recovers the operator's intent by reading English out
of an error `tool_result`.

This is the mechanical explanation for F106's port defect. The TUI's `SyncSender<bool>` loses the
third branch **without a single compiler error**, because at the type level there were only ever two
branches to lose. It is the same class of defect item 1 found in v1's status field (F147: the type
existed and enforced nothing) — a distinction that lives in a string is a distinction nothing checks.

### F182 — the structured operation that grants need already exists, and is wired to nothing

F133 requires grants scoped `{session, tool, action, path}` — *"don't ask again for this"*, between
prompt-every-time and a global yolo toggle. That scope needs a structured description of what a tool
call is about to do. The family has the type. `permissions.rs:16-32` defines

```rust
pub enum Operation { ReadFile(PathBuf), WriteFile(PathBuf), Execute(Vec<String>), Network(String), Other(String) }
```

lifted from the `claudettes-forge` scaffold, with `describe()` and a doc comment stating *"Today
only the prompter consumes it; the policy still keys off the tool name."*

**The prompter does not consume it.** `PermissionRequest` has no `Operation` field, and grep across
`crates/claudette/src` finds `Operation::` referenced **only inside `permissions.rs`'s own test
module** (`:530-566`). It is dead code carrying a doc comment that describes a consumer which does
not exist — F147's pattern once more, this time in the repo 2.0 is copying from.

What survives is the *shape*: those five variants are close to the grant key F133 asks for, and
building the request around `Operation` rather than around `(tool_name, input_json)` is what makes a
grant expressible at all. Today the policy keys off tool name only (`permissions.rs:158-164`), so
the finest grant the family could express is "always allow bash".

### F183 — nothing in the family timestamps a prompt, and the two-surface case makes the naive arrival rule wrong

F132 requires that a control answer be refused if the operator had no chance to read the prompt.
Searched for across all three repos, the implementation is absent everywhere — and in Claudette's
gate the *hazard shape* is present: `read_single_key` (`cli_prompter.rs:146-197`) calls
`enable_raw_mode()` and then `event::read()`, which returns the **oldest keypress the console has
buffered**. The only thing run beforehand is `status::global().on_prompt()` (`:51`), which
transitions the spinner phase and drains nothing. A `y` typed ahead while the model was working is
therefore a candidate to be consumed as `Allow` with zero display time; any other printable
character is a candidate to open the free-text redirect and swallow the rest of the line.

**Marked derived, not measured.** Whether the console input buffer actually survives the raw-mode
transition on Windows Terminal is settleable — a ten-line crossterm probe with pre-filled console
input would do it — and the design does not depend on the answer, because the *mechanism* that would
enforce the rule is missing regardless. (The TUI narrows the window differently: typing is disabled
while `app.working` (`tui.rs:1186`), so keystrokes are swallowed by the `_ => {}` arm rather than
queued in the app — but the modal branch (`tui.rs:812-865`) still reads whatever the terminal has
buffered, and has no debounce, no timestamp, and no drain.)

The two-surface case then corrects F132's rule. Codex's fix is a one-second delay *while the
composer is active* — a single-surface rule, because there is one composer. With a console and a
terminal both subscribed there is no single moment of display: the console may have been closed and
reopened, the terminal may have been scrolled away. **So arrival must be measured from display, per
answer, not from request** — every answer carries the `displayed_at` of the surface that produced
it, and the broker checks that answer against that surface's own display time. A surface that cannot
honestly report when it displayed a prompt is a surface that may not answer.

### 🚨 F184 — the arithmetic that splits the verb set: boundary-select buys minutes, and kill-now is a socket close

F157 concluded the engine needs *exactly one* intrusive change — generalise the prompter hook at
`conversation.rs:659-664` into a control point, so the existing gate site becomes the select point.
That is correct and it is not enough, and the numbers say so without any new measurement.

The gate site sits **between tool calls**. To reach it, the loop must first finish streaming a model
response. On this hardware the champion decodes **54–76 tok/s** (W1 F80) and the fleet's
`num_predict` is **8192** (W8 `runmeta.json`), so a maximal generation is **~108–152 s**. Then the
tool runs: W8's own verify budget is **300 s** (`verify_timeout_s`). And the HTTP client is blocking
with a **300 s whole-request timeout** and no read timeout (`api.rs:147`, `:237`), reading the
stream with `for line in reader.lines()` (`api.rs:933`, `:1077`).

| Verb | Where it can land | Latency, this hardware |
|---|---|---|
| Allow / Deny / Redirect | the gate itself | operator-bound; the loop is already stopped there |
| Pause (clean, resumable) | next boundary | up to ~2.5 min of generation **plus** the running tool — minutes |
| Enqueue (queue-while-streaming) | next model call | same bound, and that is fine — it is a message, not a stop |
| **Halt (keep the work)** | mid-stream | **≤0.25 s** — abandon the read, drop the response, socket closes (F162) |
| **Kill (destructive)** | mid-stream | ≤0.25 s mid-decode, ≤~10 s mid-prefill (F162/F163) |

**An operator who presses stop and waits three minutes has not been given a stop button.** So the
control channel is *two* mechanisms, not one — the same shape W5 found for the eight verbs:

1. **A boundary select** at the generalised gate site, for everything resumable. F157's change.
2. **A cancel flag read between stream chunks** — one `AtomicBool::load(Relaxed)` per line in the
   two `reader.lines()` loops — whose only job is to break the loop early. Dropping the blocking
   `Response` closes the socket, and OQ-W3-8 measured what happens next: the slot frees in ≤0.25 s.

That is a **second** intrusive change to the copied engine, and item 2's "exactly one" is corrected
here. It is a small one — two call sites, one atomic load at F123's ~150 events/sec — but it is on
the hot path and must be named now, not discovered later.

One consequence follows immediately, and it is the same gap F172 recorded from the other side: with
a whole-request timeout and no read timeout, **a hung server parks the worker inside `read`, where
no flag is checked.** The idle-gap timeout F172 says the family lacks is not a separate feature from
the abort path — it is what makes the abort path reachable when the model stops talking.

## Options compared

Scored against: (A) two subscribers, neither privileged (F98, OQ-W5-3); (B) stale-answer
impossibility, preserving F180's property; (C) durable before acknowledged (item 3 §5); (D) carries
`Redirect(String)` in the type (F181); (E) mid-stream verbs in ≤1 s (F184); (F) survives a crash
with the operator's answer intact; (G) implementation weight.

| Option | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|
| 1. Port Claudette's per-request rendezvous as-is | ✗ one receiver | ✅ by construction | ✗ nothing durable | ✗ needs a new type anyway | ✗ | ✗ | lowest |
| 2. Rendezvous + a second channel per surface | ⚠ two channels that must agree | ✗ two senders, one slot | ✗ | partial | ✗ | ✗ | low |
| 3. v1's shape: broadcast events out, HTTP answers in | ✅ | ✗ nothing binds an answer to a request | ✗ | ✗ (F177) | ✗ | ✗ | medium |
| 4. **Control as events on item 3's log; broker owns delivery; in-memory notify + cancel flag** | ✅ | ✅ conditional write on `in_reply_to` | ✅ 929 µs (F169) | ✅ | ✅ ≤0.25 s (F162) | ✅ replay re-offers | medium |
| 5. Option 4 + a message-bus crate between broker and worker | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | medium-high, and a dependency at the centre of correctness |

## Recommendation

**Option 4.** The control channel is not a channel — it is **two rows in the log item 3 already
builds, plus two in-memory wake paths that carry no truth of their own.**

### 1. Control is durable data, and identity is a `seq`

Two event kinds on the one log:

```
ControlRequest  { seq, task_id, attempt_id, kind, operation, at_unix_ms }   -- the worker asks
ControlAnswer   { seq, in_reply_to: seq, verb, by: OperatorId, displayed_at, at_unix_ms }
```

The request's identity **is its own `seq`** — W5 F126's one integer, in a fifth role. F180's
anti-stale property is preserved exactly, but as a conditional write instead of a consumed channel:
`apply()` refuses a `ControlAnswer` whose `in_reply_to` is already answered, superseded, or belongs
to a dead attempt. Refusal is a value, the same compare-and-set shape admission already uses (item 3
§3). **The channel became a row; the guarantee did not change.**

Fail-closed survives too, and improves: F180's "dropped sender ⇒ deny" becomes "no answer by the
deadline ⇒ the written loss rule for that verb" — v1's escalation shape (F178), generalised.

### 2. The broker: durable first, notify second, replay as the backstop

One process owns the writer (item 3's single-writer rule). On an operator command it writes the
`ControlAnswer` through `apply()`, **then** pokes the in-memory `Sender` for that attempt, **then**
acknowledges to the surface. 929 µs (F169) buys the ordering, which is three orders of magnitude
below the operator's own reaction time — durability here is free in the only sense that matters.

The in-memory notify is an optimisation, never a source of truth: if it is lost, boot replay
re-delivers the answer, because the answer is in the log. Workers never poll SQLite.

### 3. The control point: one trait, one method, two boundaries

F157's generalisation, with the verb set the acceptance list demands:

```rust
enum Control {
    Proceed,
    Allow, Deny(String), Redirect(String),   // three variants, in the type (F181's fix)
    Pause,                                    // boundary; releases the model slot, keeps the workspace lock
    Halt,                                     // mid-stream; abandon generation, KEEP artefacts (F138)
    Kill,                                     // mid-stream; destructive, releases everything
    Enqueue(String),                          // queue-while-streaming; lands at the next model call
}
trait ControlPoint { fn check(&mut self, at: Boundary) -> Control; }
```

`Boundary::BeforeTool { name, operation, input }` is the generalised permission gate — and it
carries `Operation` (F182's fix), because grants are unexpressible without it.
`Boundary::BeforeModelCall` is where `Enqueue` lands. `Halt` and `Kill` do **not** arrive through
this trait: they are the `Arc<AtomicBool>` read in `api.rs:933`/`:1077`, per F184.

### 4. The rules that live in `apply()`, not in a surface

Three, and the placement is the whole point — F106, F177 and F179 are all cases of a surface
silently declining to implement a rule:

- **Arrival (F132/F183).** An answer carries the `displayed_at` of the surface that produced it, and
  `apply()` refuses answers where `at_unix_ms - displayed_at < min_read_ms`. A surface that cannot
  report display time honestly may not answer.
- **Attribution.** `by: OperatorId` is required, so *"who answered"* is in the record. With two
  subscribers this stops being a nicety: two operators can answer the same prompt, and the loser
  must be told they lost.
- **Loss (F101).** Per verb, written, in a table the watchdog reads — item 1's contract table gains a
  column rather than the system growing a mechanism.

| Request kind | No answer by deadline | Rationale |
|---|---|---|
| Tool permission | `Deny`, reason `operator absent` | matches Claudette's disconnect behaviour; fail closed |
| Escalation / review | task → the operator-blocked state, then **escalate on a clock** | F178, the family's one correct rule |
| Pause acknowledgement | none — pause is not a request | the operator does not wait on the fleet |

### 5. Grants (F133), as events

A grant is a `ControlAnswer` variant carrying a scope key `{session, tool, action, path}` derived
from `Operation`, written to the log like everything else. That makes it durable, listable ("what
have I allowed this session?"), and **revocable by another event** rather than by a mutable flag —
the single-writer discipline F149's drift bug argues for. Default scope is the session; a grant
never outlives the process unless the operator says so.

### 6. Sub-agents (OQ-W3-10, answered)

Today `AgentToolExecutor::stateless()` runs sub-agents with no prompter, so dangerous tools are
auto-denied (`conversation.rs:659-664` with `prompter == None`). The answer: **a sub-agent gets a
child control point, not no control point.** It carries the parent's grants, may not widen them, and
every request it raises names its lineage through the `attempt_id` chain, so the console can show
*which* unit is asking. The fail-closed default is preserved — a sub-agent whose broker link is gone
denies, exactly as today — but "the model spawned a helper and the helper went silent" stops being
invisible.

### 7. What not to build

No second control transport; no per-surface answer channel (option 2 is F180's bug re-created with
two senders); no message-bus crate; no polling of the log by workers; and **no `Pause` implemented
as kill-and-restart** — the point of the boundary select is that pause is cheap and resumable, and
item 3's checkpoint is what makes the promise honest.

## Rejected alternatives and why

- **Porting the rendezvous unchanged (option 1).** Its two safety properties are properties of a
  channel object (F180), and neither survives a second subscriber, a durable ack, or a crash. Kept as
  the *specification* of what the row-based mechanism must reproduce.
- **A channel per surface (option 2).** Two senders into one logical answer slot is precisely the
  stale-answer hazard the rendezvous was built to make impossible, re-introduced for convenience. It
  also has nowhere to put "who answered".
- **v1's shape — broadcast out, HTTP in (option 3).** Worth naming because the *transport* is right:
  socket.io fan-out plus a point request is a reasonable two-subscriber arrangement, and 2.0's SSE +
  POST is its descendant. What v1 lacks is any binding between an answer and the request it answers,
  which is why `provideHumanInput` can accept an instruction for a task and apply nothing (F177).
  **v1 had the transport and no semantics; Claudette has the semantics and no transport. Item 4 is
  the join, and neither donor's code carries over — only their lessons.**
- **A message-bus or actor crate (option 5).** The same argument item 3 made against `cqrs-es`: this
  is the centre of the system's correctness, the mechanism is a few hundred lines of conditional
  writes over a table that already exists, and a dependency here buys an abstraction we would have to
  bend anyway.
- **Thread-kill for `Kill`.** Already rejected in item 2 for leaving locks and the terminal in
  undefined states; F184 removes the last reason to want it, since the socket close achieves the same
  latency (≤0.25 s) with a clean unwind.
- **Making `Halt` a special case of `Kill` with a flag.** F138's lesson is that *"keeps the work done
  so far"* is what the operator wants most of the time; a flag on the destructive verb makes the safe
  path the one you have to remember. Two verbs, two entries in the contract table.

## Effect on fun

**The console gets to be wrong out loud.** Every request, every answer and every refusal is an event
with an author and a time, so replay shows not just what the fleet did but *what it asked and how
long you left it waiting*. W5 F129's fun table wanted "how long the operator watched dead air" to be
measurable; a control request with a `displayed_at` and an answer with an `at_unix_ms` measures it
exactly, per prompt.

**Steering becomes ordinary.** `Redirect(String)` and `Enqueue(String)` in the type mean the cheap
version of take-over — type at the fleet while it works, land at the next boundary — is available on
day one rather than waiting for fork-from-checkpoint. F138 found this is what the most-used agent in
the world actually ships, and F177 is what it looks like to *promise* it and not have it.

**Stop feels like stop.** The difference between a three-minute pause and a quarter-second halt is
not a performance number, it is whether the operator believes the button. This is the item where the
console stops being a viewer, and the felt version is small: you press a key, the unit stops
mid-sentence, and the work it had already done is still there.

The cost worth naming: three surfaces must each implement `displayed_at` honestly, and a surface that
fakes it defeats the rule for everyone. That is a code-review item forever, and it is the price of
the rule living in `apply()` instead of in one screen.

## Open questions

| # | Question | Waiting on |
|---|---|---|
| OQ-W3-15 | `min_read_ms` — Codex chose 1 s for a single composer; the right value for a console that may have been closed is unknown, and F183's probe would inform it | W5 console build; a ten-line crossterm probe would settle the type-ahead half now |
| OQ-W3-16 | Two operators, one prompt: first-answer-wins with the loser notified, or an explicit claim? Only matters once W10 exists, but the `by:` field must be in the schema before then | W10 |
| OQ-W3-17 | Does `Enqueue` land at the next model call or the next tool boundary when a tool is mid-flight? Codex retries rejected steers on the next turn; the cheapest correct rule is unproven here | item 5, W5 console |
| ✅ OQ-W5-3 | **ANSWERED here** — the permission channel lives in the log; identity is the request's `seq`, delivery is the broker's in-memory notify, and "who answered" is a required field (F180) | — |
| ✅ OQ-W3-10 | **ANSWERED here** — sub-agents get a child control point carrying the parent's grants and their own lineage; fail-closed unchanged | — |
| ✅ OQ-W3-13 | Unchanged from item 3, and F184 sharpens it: the idle-gap timeout is what makes the cancel flag reachable when the server stops talking, so it is the same mechanism, not a separate feature | **ANSWERED by W11 item 5, F292** — see item 3's row |

## Confidence: high on the diagnosis and the mechanism, medium on the arrival rule

The donor findings are grep-level facts with file:line, verified this session in all three checkouts,
and the four stop paths in F174 were traced from route to handler to the far side of the HTTP call
rather than inferred from names — which is what turned "kill releases resources" into "kill releases
resources *while the worker keeps writing*". F184's latency table is arithmetic over numbers already
measured on this machine (F80, F162/F163, F169) and is labelled as arithmetic; no new measurement was
taken and none is needed to choose between the options.

What is weaker: **F183 is derived, not measured** — the claim that a type-ahead keystroke reaches
`event::read()` through the raw-mode transition is consistent with how the code is written and is not
something this pass ran. The design does not turn on it (the enforcement mechanism is absent either
way), but the `min_read_ms` value in OQ-W3-15 does. And the arrival-from-display rule is this item's
one genuine invention rather than a port: it is the right generalisation of F132 for two subscribers
as far as the argument goes, and nobody we have read has shipped it.

What would raise it: the crossterm probe; and W5's console reaching the point where a real
`displayed_at` can be produced and checked against a real answer.

---

# Item 5 — escalation lineage

## Question

§11's line is a single sentence with four verbs in it: *"worker fails, verification fails, task gets
re-scoped by a stronger model, retried, and the whole lineage stays traceable."*

Three of those four are already answered. Item 1 ruled attempts **immutable** and made every retry,
re-scope, edit and replay the same **fork-from-checkpoint carrying `cause`**, so lineage is the
attempt chain *by construction* and cannot be lost. Item 3 made the chain durable. Item 4 gave the
operator half — `Redirect(String)` and re-route are control events with `by:` and `displayed_at`.

What is left is the part no previous item touched, and it is the harder half: **the policy.** Who
decides to escalate, on what evidence, to what, at what price, and what does the record have to
carry so the decision can be second-guessed later? Precisely:

- **The predicate** — what distinguishes a failure that escalating can fix from one it cannot.
- **The ladder** — what the rungs are on *this* hardware, and what each costs.
- **The record** — what an escalation edge carries so that "traceable" means a query, not a story.

OQ-W3-14 is this item's to close (does `attempt` stay a table or become a second projection?), and
OQ-W3-17's lineage half — when does an operator's steer *land* in the running attempt and when does
it *fork* a new one — belongs here too.

## Method

Fifth donor pass, 2026-08-20, same three checkouts and same HEADs as items 1–4: ABCC v1 `d5528ea`,
BCF `d6c1601`, Claudette `af3f804`. Deliberately **not** a re-extraction — items 1–4 and W6 item 1
already read the lifecycle, the store, the control paths and the verifier, and this pass does not
re-walk them. It reads one thing they did not: the **decision sites**. Every `if` that chooses to try
again, every place a rung is selected, every place a failure is classified — and then, the part that
turns a design into a finding, a grep for the **readers** of each field those decisions write. Every
claim carries file:line.

No new measurement. The prices in the rung table are arithmetic over numbers already measured on this
machine (W1 F79 swap, W1 F88 wall-clock ratios, W2 F81 prefix cache, W2 F83 concurrency), and they
are labelled as arithmetic where they are composed.

## Inherited

| What | Source | Verdict here |
|---|---|---|
| `humanEscalation`'s timeout-then-escalate | ABCC `humanEscalation.ts:37-57` | **shape REUSE** (F178) with all three of its defects fixed (F196) |
| Surgical fix loop, best-round restore, 0.1 decline breaker, capped rounds | BCF `mission.rs:698-741` | **REUSE** — and F190 promotes best-round restore from nicety to invariant |
| Feedback that names issues persisting across rounds | BCF `mission.rs:1575-1584` | **REUSE** — the family's best evidence-carrying, and the input to "is this failure stuck or improving" |
| The four-valued outcome lattice | ABCC `schemas/output.py:11`, kept by item 1 | REUSE as the **verdict**; item 5 adds the failure **class**, which is what decides whether escalating can help at all |
| Tiered brain fallback | Claudette `brain_selector.rs` | **REUSE the mechanism** — typed trigger, fork-from-checkpoint, append-only lineage (F191). **DISCARD its cost assumption** (F193) |
| Three ladders + the `preferredModel` blob | ABCC `autoRetryService.ts`, `asyncValidationService.ts`, `codeReviewService.ts` | DISCARD (F185, F186) |
| The 9.2/8.5/8.0 gate ladder as an escalation trigger | BCF `mission.rs:57-67` | DISCARD — W6 F160 voided the numbers, and F189/F191 show a scalar is the wrong shape anyway |

## Findings

### F185 — v1 escalates four ways down three different ladders, and which one runs is a property of the code path, not of the task

Item 1's F150 counted four retry mechanisms with no lineage. Reading them for their *rungs* rather
than their writes shows something worse: they do not agree about what the ladder is.

| Mechanism | Rungs | Selected by |
|---|---|---|
| `AsyncValidationService.processRetryQueue` (`:206-311`) | local Ollama → **Haiku** | default-on (`ASYNC_VALIDATION_ENABLED !== 'false'`, `index.ts:119`) |
| `AutoRetryService.validateAndRetry` (`:82-278`) | local Ollama → **remote Ollama** → Haiku | constructed only when async is *absent* (`taskExecutor.ts:55`) |
| `CodeReviewService.getEscalationTier` (`:461-467`) | `'ollama'` → `'haiku'`; everything else → **`'human'`** | a `switch` on the model **name string** |
| Iteration retry (`taskExecutor.ts:243-277`) | **none** — same model, same prompt | `currentIteration < maxIterations` |

The exclusivity at `taskExecutor.ts:55` looks like a migration in progress — until you find that
`orchestratorService.ts:458` and `battleClawService.ts:284` each construct `AutoRetryService`
directly and unconditionally. **Both ladders are live in one process**, and a task's escalation
policy is decided by which entry point created it: a mission task gets three rungs and a durable
`completed`/`failed` write (`orchestratorService.ts:461-470`), an ordinary queued task gets two rungs
and a verdict that never leaves memory (F187).

For 2.0 this is the argument that **the ladder must be one piece of data read by one policy
function.** Three hard-coded ladders did not diverge because anyone chose three policies; they
diverged because each was written at its own call site, where nothing could compare them.

### 🚨 F186 — the brief's "re-scoped by a stronger model" is, in the donor, a JSON blob with no reader

`handleReviewFailure` (`codeReviewService.ts:383-455`) is the one path that looks like §11's
sentence. On a failed review it sets `status: 'pending'`, clears `assignedAgentId`, increments
`currentIteration`, and writes into `task.result`: `reviewFailed`, `reviewScore`, `previousModel`,
**`preferredModel: nextTier`**, and a full `reviewContext { qualityScore, findings, summary,
hasSyntaxErrors }`.

Grepping the readers across `packages/*/src`:

- **`reviewContext` — zero reads.** Written at `:434` and `:449`, read nowhere.
- **`previousModel` — zero reads.** Written at `:432`, read nowhere.
- **`preferredModel` — zero reads of *this* one.** The name is live, but every reader is the
  *agent's* config: `taskExecutor.ts:701` reads `agentConfig?.preferredModel` and hands it to
  `resolveModelOverride` (`modelResolver.ts:35`); the agents route validates it
  (`agents.ts:161-229`); the UI renders it (`AgentCard.tsx:62`). The task's `result.preferredModel`
  is a different object that nothing consults.

So when the re-scoped task is picked up again, `TaskRouter.routeTask` re-routes it on **complexity**
(`taskExecutor.ts:697`) — the same rule that chose the model that just failed — and it is executed
with `taskDescription: pendingTask.description || pendingTask.title` (`:766`): **the identical
prompt, none of the findings, and no memory that a review rejected it.** The review's whole payload
is overwritten by the next escalation (F150).

Two of the sentence's four verbs are inert. Stated as a rule, because this is the third time the
family has done it (F177/F181's redirect, F174's stop paths): **an escalation that is recorded but
not applied is indistinguishable from one that was applied, from every surface except the model's
input.** In 2.0 the re-scope *is* the new attempt's prompt — there is nowhere to write it that is not
the thing that runs.

### 🚨 F187 — the default ladder is unreachable from the console, and its queue does not survive a restart

`AsyncValidationService` is the default (`index.ts:119`). Its escalation ladder is drained by
`startRetryQueue()` (`:168`), whose **only** caller is `POST /validation/retry`
(`routes/validation.ts:66`). The UI defines the call — `validationApi.triggerRetry`
(`ui/src/api/client.ts:658`) — and **never invokes it**: grep over `packages/ui/src` finds
`validationApi` imported once, in `TaskDetail.tsx:7`, using only `getResult`. Nothing on a timer,
nothing on mission completion, no other service. **The default escalation ladder in v1 runs only if a
human sends an HTTP request by hand.** That is F174's shape a third time — the capability exists and
the console cannot reach it.

Underneath, the state is entirely in memory: `validationResults: Map` and
`retryQueue: RetryQueueEntry[]` (`:96-97`), with the file's only Prisma call a `findUnique` (`:372`).
So a restart erases both the verdicts and every pending escalation — and `TaskDetail.tsx:38` renders
the verdict *from that Map*, which is empty after a reboot. The declared cap
`MAX_RETRY_QUEUE_SIZE = 100` (`:91`) is never referenced; only `MAX_VALIDATION_RESULTS` is enforced
(`:127-130`).

This is item 3's ruling arriving in the escalation path: **the queue of things still to be tried is
exactly as load-bearing as the status of things already done, and it belongs on the same log.** In
2.0 there is no retry queue — a task whose attempt failed is a task in a state, and the scheduler is
a projection of the log.

### 🚨 F188 — the trigger fails open where the instrument is absent, and invents a number where it is unparseable

Both ladders open the same way:

```ts
if (!task || !task.validationCommand) {
  return { validated: true, phase: 'skipped', attempts: 0 };   // autoRetryService.ts:82-84
}
```

and the async twin sets `passed: true` with the comment *"No validation command — auto-pass"*
(`asyncValidationService.ts:372-380`). `validationCommand` is nullable (`schema.prisma:70`) and has
exactly one automatic producer — the decomposition tool `cto_tools.py:338`. **A task nobody wrote a
check for is reported as validated**, and the ladder above it never runs.

The review trigger has the other half of the disease. `checkReviewFailed` (`:360-378`) fires on
`qualityScore < 6` (`REVIEW_QUALITY_THRESHOLD`, `:60`), any `critical` finding, or `hasSyntaxErrors`
— reasonable predicates over a number produced like this:

```ts
qualityScore: Math.min(10, Math.max(0, result.qualityScore || 5)),   // codeReviewService.ts:578
```

An unparseable or absent score becomes a **measured-looking 5.0**, which is then written onto the
task as `reviewScore` (`:402`, `:415`, `:431`) and shown in the console. The escalation direction
happens to be the safe one (5 < 6, so it escalates); the *record* is the casualty — the task now
carries a review score nobody produced.

This is W6 F161 one layer earlier than W6 found it. F161 fixed the gate; F188 says the same rule
binds the **trigger**: *absence of measurement is `Uncertain`, and `Uncertain` routes to the operator
— it is never `Success` and never a midpoint.* A 2.0 task with no verifier does not pass; it finishes
`Uncertain(no verifier configured)` and says so.

### F189 — v1 classifies its failures at the exact moment it stops caring, and its main classifier always writes `null`

`errorCategory` (`schema.prisma`, *"Error categorization for failures"*) has three writers:
`orchestratorService.ts:628` (`'killed'`), `stuckTaskRecovery.ts:269` (`'timeout'`), and
`taskExecutor.ts:308-318`, the general path, via `categorizeError`.

Two facts, both from this pass:

1. **Zero readers.** Grep across `packages/api/src/routes` and all of `packages/ui/src`: nothing
   reads the column. No policy, no query, no display. The one place v1 tries to learn from failure is
   `captureTrainingData`, and it fires only when the budget is already spent
   (`taskExecutor.ts:237-241`).
2. **The general writer cannot produce a value.** `categorizeError` returns `null` unless the task's
   status is already `'failed'` or `'aborted'` (`complexityCalculator.ts:75-77`). It is called from
   `abortTask` (`:308`) against the row read at `:283` — *before* the same function writes
   `status: 'aborted'` at `:312-320`. Every caller of `abortTask` (`taskExecutor.ts:275`,
   `taskQueue.ts:103`/`:155`, three routes) passes a task that is `in_progress`, `assigned` or
   `needs_human`. **So the general path always stores `errorCategory: null`**, and the only non-null
   values in the whole system are the two hard-coded string literals.

The design consequence is the important one, and it is the centre of this item: **the retry ladder
cannot tell a model that produced wrong code from a sandbox that never ran** — and the field that
would have told it exists, is populated by a function that returns null, and would have had no
readers if it hadn't been. Escalating a `HardFailure` caused by a missing interpreter to a bigger
model buys nothing but 24 seconds and a larger bill for the same error.

### F190 — one donor assumes retries improve the work; the other measured that they do not

v1's ladder re-reads the file from disk at the head of every phase (`autoRetryService.ts:101`,
`:159`, `:210`) and the executor writes in place. There is no snapshot, no restore, no comparison:
**the Haiku rung's starting point is whatever the two Ollama rungs left behind**, and if a rung made
things worse the next rung inherits the damage.

BCF does the opposite, deliberately. `best_result` / `best_round` track the highest-scoring round;
the decline breaker stops the loop when `result.final_score < prev_best - 0.1` from round 2 on
(`mission.rs:698-707`); and after the loop it restores — `codegen::write_files(output_dir,
&best.files)` under the comment **"Restore best round's files to disk (fix rounds may have
degraded)"** (`:735-741`). That comment is the finding: someone watched fix rounds make the artefact
worse and built the machinery to undo it.

For 2.0, with item 1's checkpoints already in the design, this costs nothing to get right and is an
invariant rather than a feature: **every fork starts from the best checkpoint on the chain, never
from the last one.** "Last" is only correct when the last attempt is also the best, and the donor
that measured it says that is not reliably true.

### 🚨 F191 — the engine 2.0 is copying already contains the family's only correct escalation, and it is fork-from-checkpoint with a typed trigger and an append-only lineage log

`crates/claudette/src/brain_selector.rs` — which items 1–4 walked past with a single clause (F151) —
is a working tiered-model escalation:

- **Typed triggers, chosen from data.** `StuckReason::{EmptyResponse, NoTextAtMaxIter,
  ToolErrorStreak}` (`:41-56`), each documented with why it fires and what it costs to be wrong:
  *"False positives waste swap time; false negatives leak bad output. The three signals above are the
  ones the brain200 transcripts showed produce true-positive escalation candidates."* (`:21-26`)
- **A pre-turn checkpoint.** `let pre_turn_session: Session = runtime.session().clone();` is taken
  **before** the primary runs (`:231`), *"so the fallback doesn't see a duplicated user message or a
  stuck assistant turn"*. The escalation then replays the same input against a runtime built on that
  snapshot (`:236-256`). That is item 1's fork-from-checkpoint, already implemented, in the engine
  being copied.
- **A scoped revert.** After the fallback turn the runtime is rebuilt on the primary and the fallback
  model is unloaded (`:262-268`) — escalation is per-turn, not sticky, and it pays back the VRAM it
  borrowed.
- **An append-only lineage record.** `append_fallback_event` writes one JSON line per escalation to
  `~/.claudette/fallback.jsonl` — `{ts, prompt_hash, trigger, fallback_succeeded, primary_model,
  fallback_model}` (`:383-410`) — and the type's doc says why it exists: *"Logged to fallback.jsonl
  so we can tune the thresholds against real data."* **It is the only append-only durable artefact in
  the entire family** (F171: everything else rewrites a whole document), and the only place any donor
  records *why* it escalated and *whether that worked*.
- **A refusal to escalate on the wrong evidence.** `diagnose` (`:302-326`) returns `None` for
  `Err(_)` that is not "no content" — *"Transport errors, permission denials — don't escalate"* — and
  `None` when the turn landed gracefully on the iteration cap, *"don't burn the fallback brain
  re-running a 40-iteration turn whose tool-error streak is incidental to the cap"*.

Two limits keep it from being 2.0's answer as-is. It is **one rung, one turn**. And **all three
signals are liveness-shaped**: empty output, no text near the cap, a streak of tool errors. None of
them means *the code was wrong*. Claudette escalates when the model stops producing usable output;
v1 escalates when a validation command exits non-zero; BCF does not escalate at all — grep for
`escalat` over `battle-command-forge/src/` returns **nothing**. Three donors, three disjoint trigger
classes, and 2.0 needs the union: stuck, wrong, and — per F188 — unmeasured.

### F192 — the escalation threshold that rotted, and the rule it teaches

`brain_selector.rs:70-88` carries its own post-mortem. The `NoTextAtMaxIter` signal was originally an
absolute count, `11`, written against `max_iterations = 15` — a 73 %-of-budget tripwire. When the cap
moved to 40 the constant did not, and it silently became a 27 % tripwire *"diagnosing ordinary long
tool chains as stalls and replaying them wholesale on the bigger brain."* The fix expresses it as a
margin below the cap actually in force (`MAX_ITER_STUCK_MARGIN: usize = 4`) with an absolute floor
(`MAX_ITER_STUCK_FLOOR: usize = 11`) so a small cap cannot drive it down to "escalate on the second
tool call".

The rule, and it is not specific to this constant: **an escalation threshold stated as an absolute
count of a budgeted quantity decays silently when the budget moves — and it decays in the expensive
direction**, because a threshold that fires too often still *looks* like a working feature. Every
threshold in 2.0's ladder is expressed against the budget it measures (a fraction of the attempt's
iteration budget, a fraction of the idle-gap timeout, a count of *consecutive* failures rather than
total), or it carries the floor and the margin that make the intent survive a config change.

### 🚨 F193 — Claudette's own skip rule says the tiered fallback is unusable on 2.0's hardware, and it says why in the source

`FallbackSkip` (`brain_selector.rs:95-128`) refuses to escalate in two cases, and the doc comment on
the enum is written against *this* configuration:

> *"The tiered-brain design assumes Ollama on a small card: escalating pulls a second model into
> memory for one turn, then evicts it. That assumption breaks badly on the setup the README now
> recommends for 16 GB — LM Studio with one large model resident — because escalating asks the server
> to JIT-load a second model, which evicts the brain the user deliberately loaded."*

`SameAsPrimary` skips when the fallback resolves to the primary (*"replay the whole turn against an
identical brain for an identical result, at double the latency"*); `NotServed` skips when the backend
is not already serving the fallback. Note the direction of the defaults: a *failed* probe fails
**open** (`served == None` ⇒ escalate anyway, `:155-160`, argued as *"an unreachable probe must not
silently disable a working fallback"*) while a *stale cache* can only produce a skipped escalation,
*"never a surprise model load — the safe direction"*. This is the family's one place where a default
is chosen by naming the consequence in both directions, and it is the model for how 2.0 argues its
own defaults.

The consequence for 2.0's ladder is arithmetic:

- The cheap mid-turn escalation the donor implements **only exists where a second model is already
  served.** On one 5090 with the champion resident it is not; the 27B alone occupies 94.4 % of the
  card at `-c 40960` (W1).
- So a model rung costs a **23.77 s round-trip swap** (W1 F79, n=3 each direction, load-dominated and
  not bandwidth-bound), before the stronger model reads a token.
- And the stronger model then runs **1.3× to 9.5×** longer per task, 5.2× over the whole K-series
  campaign (W1 F88) — while fixing better, not scoring better (F87: verdicts tie 8/9).
- The rung above that — v1's Haiku, priced in dollars by `calculateCost`
  (`codeReviewService.ts:593-600`) — **does not exist for 2.0 at all** (W5 F114: the spend ceiling is
  zero by decision).

**2.0's ladder is shorter than every donor's and its one model rung is the most expensive act in the
system.** That is not a reason to drop it; it is the reason it must be priced, shown and budgeted
rather than fired automatically the way all three donors fire theirs.

### F194 — escalating one task stops the other one: the model rung is a fleet-wide event (derived, not measured)

Composed from measured numbers, and labelled as composition:

- The 27B at `-c 40960` occupies 94.4 % of the card (W1), so it and the champion **cannot be
  co-resident**. A model rung is an unload plus a load, not an addition.
- Useful concurrency is **N=2** (W2 F83: 1→2 buys +69 % prefill / +68 % decode; beyond that nothing,
  and TTFT degrades from 3.67 s to 10.54 s).
- Therefore escalating attempt A evicts the model attempt B is mid-turn on. Every other in-flight
  attempt loses its server for the duration: 23.77 s of swap, plus A's inflated wall clock, plus
  23.77 s back.

So on this hardware **escalation is a scheduling decision over the whole fleet, not a property of one
task's ladder** — and with a fleet of two, escalating one task halves the fleet for minutes. The
mechanism it needs already exists: item 4's `Pause` at a boundary, applied to every other attempt,
then resume. The rung is implemented as *pause the fleet at boundaries → swap → run the escalated
attempt → swap back → resume*, which is also why it must be a decision the operator can see coming
(W5 F104's rule that the price is shown before the verb commits).

One corollary worth stating because it is cheap and non-obvious: a **re-scope** rung — same model,
restated prompt — is a *cold* prompt by construction. W2 F81 measured that changing one token at the
front annihilates 79.7 % of the prefix-cache TTFT saving. Re-scoping is therefore never free even
when the model does not change, and the ladder should prefer *appending* evidence to *rewriting* the
prompt whenever both would do.

### F195 — the retry budget: one number, read by one of four mechanisms, with a global cap bolted on after an incident

`maxIterations` (default 3, `schema.prisma`; `1..10` at the route, `tasks.ts:16`) is read at exactly
two sites, both in the iteration-retry path (`taskExecutor.ts:237`, `:243`). Neither validation ladder
consults or decrements it; neither does the review re-scope, which increments `currentIteration`
itself (`codeReviewService.ts:429`) — the same counter, from outside the mechanism that owns it.

Inside the sync ladder, a second budget: `MAX_TOTAL_RETRIES = 3` with the comment *"Hard limit:
prevent infinite retry loops (Mar 2, 2026 fix)"* (`autoRetryService.ts:50-51`), checked four separate
times (`:108`, `:165`, `:213`, `:225`). It exists because three independent per-phase caps
(`MAX_OLLAMA_RETRIES`, `MAX_REMOTE_RETRIES`, `MAX_HAIKU_RETRIES`, each defaulting to 1 and each
independently configurable by env) **cannot bound the total** — a fact discovered in production and
patched with a fourth counter rather than a single budget.

2.0's rule follows directly, and it is one line in the writer: **one attempt budget per task,
decremented by every mechanism that consumes an attempt, refused by `apply()` when exhausted.** A
ladder cannot outlive the budget because a rung *is* an attempt, and attempts are what the budget
counts. This also makes the budget a thing the operator can *raise* — `+2 attempts` is a control
event with an author, the same shape as every other control verb (item 4).

### F196 — the family's one correct loss rule has three defects, and each is a one-line rule for 2.0

F178 credited `HumanEscalationService` as the family's only implemented answer to *"the operator
never answered"*. Read for its policy rather than its existence, it has three defects:

1. **Two clocks for one deadline.** `checkTimeouts` selects on `config.humanTimeoutMinutes`
   (`humanEscalation.ts:41-43`) — a global env, default 30 (`config.ts:12`) — while
   `getRemainingTime`, which is what a surface would render as a countdown, computes from
   **`task.humanTimeoutMinutes`**, a per-task column with its own default of 30 (`:146-149`,
   `schema.prisma`). They agree only because both defaults are 30; set the per-task column and the
   displayed deadline stops being the deadline. → *2.0: the clock the watchdog reads and the clock
   the console renders are the same field, and it is on the event that started it.*
2. **Escalation happens at most once per task, ever.** The polling query filters
   `escalatedToAgentId: null` (`:45`). It is a double-escalation guard, and its consequence is that a
   second timeout — the new agent also stalls, the operator still absent — matches nothing, and the
   task waits forever holding its slot and its locks. → *2.0: the loss rule is a policy on the state,
   not a one-shot flag; re-entering the state re-arms it, and the chain records how many times.*
3. **The target is arbitrary.** `prisma.agent.findFirst({ where: { id: { not: … }, status: 'idle' } })`
   under the comment *"Find a more capable agent (for now, just find another idle agent)"*
   (`:71-77`). The one correct loss rule in the family escalates to **someone else, not someone
   better** — and when no agent is idle it emits an alert and returns `false` (`:79-90`), leaving the
   task in `needs_human` with the guard still unset, so the same non-escalation is attempted again
   every minute. → *2.0: the escalation target comes from the same ladder as every other rung, and
   "no rung available" is a written state, not an alert.*

The shape still stands: an unanswered request is not a hang and not a silent default; it is a
transition to a written state, on a clock, visible. All three defects are in the *policy*, which is
this item's subject and exactly why the policy belongs in one place that can be read.

## Options compared

| Option | Trigger | Where policy lives | Verdict |
|---|---|---|---|
| 1. Port v1's ladders | validation exit code | hard-coded at each call site | **rejected** — F185: three ladders that disagree, because nothing could compare them |
| 2. Escalate on the gate score | one scalar crossing a threshold | the gate formula | **rejected** — W6 F160 voided the numbers, and F189/F191 show a scalar cannot separate *wrong* from *stuck* from *never measured*, which is the only distinction that matters |
| 3. Port `brain_selector` as-is | three liveness signals | the engine, per turn | **rejected as the whole answer, adopted as the core** — right mechanism (F191), wrong scope: one rung, one turn, no correctness trigger, and its cost assumption is false here (F193) |
| 4. **Classified outcome → a ladder that is data → fork from the best checkpoint → lineage as the attempt chain** | the failure **class**, from the Attempt lattice plus the cause | one policy function over the log | **recommended** |
| 5. Operator escalates everything | none — every failure asks | the human | **rejected as policy, kept as the floor** — exactly right for `Uncertain` and for an exhausted ladder, wrong as a default: F129's bar wants intervention to be *meaningful*, and a fleet that asks on every failure is a treadmill |

## Recommendation

**Option 4.** Escalation is a **policy function over a classified outcome**, the ladder is **data**,
every rung is a **fork from the best checkpoint**, and lineage is the **attempt chain** the fork
already creates. Nothing here is a new mechanism; it is items 1–4's mechanisms with a policy on top.

### 1. Classify before you escalate — the predicate is a class, not a number

The Attempt's `Outcome` (item 1) says *what happened*. Escalation needs a second, orthogonal fact —
*what kind of failure it was* — because that is what decides whether a different model could help:

```rust
enum FailureClass {
    Wrong { evidence: Seq },       // the verifier ran and the work is wrong → a better brain may help
    Stuck { signal: StuckSignal }, // no usable output: empty, no-text-near-cap, tool-error streak
    Budget { which: BudgetKind },  // iterations / idle-gap / context exhausted → not a stuck signal
    Environment { detail: Seq },   // sandbox, transport, missing tool, server down → NEVER escalate
    Unmeasured { why: String },    // the instrument did not run → operator, per F188 / W6 F161
}
```

The mapping to policy is the whole point, and every row of it is a donor's mistake or a donor's
lesson:

| Class | What the ladder does | Grounded in |
|---|---|---|
| `Environment` | **never a model rung.** Retry the same rung if the cause is transient, else fail the task with the cause attached | Claudette's `Err(_) => None` (F191); v1 cannot do this because `errorCategory` has no readers *and* writes null (F189) |
| `Budget` | not a failure of the model. Escalate only when the budget itself is the binding constraint, and say which | `hit_iteration_cap ⇒ None` (F191); F192's rotted threshold is what happens when this is confused with `Stuck` |
| `Stuck` | fix-in-place is pointless — the model produced nothing to fix. Go straight to the re-scope or model rung | the three signals, F191 |
| `Wrong` | fix-in-place **first**, carrying the evidence; escalate the model only when the same defect survives a fix | BCF's persistent-issue tracking (`mission.rs:1575-1584`); F190's best-round restore |
| `Unmeasured` | **stop and ask.** Never a rung, never a pass | F188, W6 F161 |

`StuckSignal` carries Claudette's three verbatim, because they were selected against real transcripts
and their false-positive cost is written down.

### 2. The ladder is data, and there is one of it

```rust
struct Rung {
    role: RungRole,           // FixInPlace | Rescope | StrongerModel | Operator
    model: Option<ModelId>,   // None = "whatever the task is already using"
    budget: AttemptBudget,    // iterations, idle-gap, context — the rung's own limits
    price: PriceEstimate,     // filled from measurement, shown before the rung is taken
}
```

One ordered `Vec<Rung>` in config, one `fn next_rung(chain: &[Attempt], class: FailureClass) ->
Option<Rung>`, one caller. F185 is the argument: three hard-coded ladders diverged because each was
written where nothing could compare it. A `Vec` can be printed, diffed, overridden per task, and
tested without a model in the loop — which is what `diagnose` being a pure function already buys
Claudette (`brain_selector.rs:302`, *"can be unit-tested without a real Ollama in the loop"*).

### 3. The rungs for this machine, with their prices

| # | Rung | What changes | Price on this box | Enter when |
|---|---|---|---|---|
| R0 | first attempt | — | the task's own wall clock (K-series medians 100–190 s/cell, W1 F88) | — |
| R1 | **fix-in-place** | same model, same chain; feedback carries test errors, verifier issues and **issues that persisted** | one attempt; the prompt grows, the prefix cache mostly survives | `Wrong`, and the defect set is shrinking |
| R2 | **re-scope** | same model, restated goal, fresh context | one attempt **plus** a cold prompt — W2 F81: one token at the front costs 79.7 % of the TTFT saving | `Stuck`, or `Wrong` with the same defect surviving R1 twice |
| R3 | **stronger model** | the 27B replaces the champion | **23.77 s swap each way** (W1 F79) + **1.3–9.5×** wall clock (W1 F88) + **the rest of the fleet pauses** (F194) | `Wrong` after R2, and the operator has the budget for it |
| R4 | **operator** | a human has the keyboard | unbounded; the clock is the loss rule | ladder exhausted, `Unmeasured`, or an explicit gate |

Notes that keep this honest:

- **R3 is a fleet operation, not a task operation** (F194). It pauses every other attempt at a
  boundary (item 4's `Pause`), swaps, runs, swaps back, resumes. It is the one rung that must be
  *scheduled*, and W5 F104's rule applies: the console shows the price before the verb commits.
- **Nothing above R3 exists.** No cloud rung (W5 F114). R4 is the top, which is a much stronger
  reason to make R4 pleasant than any donor had.
- **A bare retry — same rung, same prompt, no new evidence — is not in the ladder.** It is v1's
  mechanism 1 (F185) and it carries no hypothesis about why this time differs. Whether it
  nevertheless converts failures to passes at a useful rate is unknown and cheaply measurable on W8's
  harness (OQ-W3-19); until then the ladder always changes *something*, and the thing it changed is
  on the edge.

### 4. Every fork starts from the best checkpoint on the chain

F190's invariant, and it is one line at the fork site because item 1 already put
`checkpoint_from: Option<CheckpointId>` on `Attempt`. The chain records each attempt's outcome, so
"best" is a query over data the log already holds; best is chosen by the outcome lattice first (a
`Success` beats any `SoftFailure`) and by the verifier's measurement second — never by an LLM judge
alone (W6 F159).

BCF's decline breaker survives with it: **a rung that produces a worse result than the best on the
chain ends the ladder and restores**, rather than spending the next rung on a degraded base. What
does *not* survive is BCF's threshold arithmetic (W6 F160), so the 0.1 is inherited as a *shape* —
"backwards ends it" — with the number recalibrated on W8's harness.

### 5. The lineage record, and OQ-W3-14 closed

**`attempt` stays a table** — a materialised projection maintained by the same `apply()` writer that
appends the event, in the same transaction (item 3 §3). The duplication cannot drift, because
attempts are immutable: a row is written once, at fork time, and never updated except by the terminal
outcome write. F149's drift bug needs a *mutable* denormalisation to bite; this is not one. The
alternative — deriving the chain by replaying the log on every query — makes the console's most-used
view the most expensive one, and boot-as-replay (94 ms per 100k events, F170) already rebuilds it for
free.

Each attempt row carries what an escalation decision needs to be second-guessed:

```
Attempt { id, task, parent: Option<AttemptId>, cause, rung, model, checkpoint_from,
          budget_granted, started: Seq, outcome: Option<Outcome>, class: Option<FailureClass>,
          evidence: Seq,           -- the verifier event that justified the fork
          decided_by: Actor,       -- Policy | Operator(OperatorId)   (item 4's `by:`)
          price_estimated, price_actual }
```

`cause` is item 1's enum — `Fresh | Retry{of} | Rescope{of} | Edit{of} | Replay{of}` — and an
operator-initiated re-scope is the *same edge* as an automatic one, differing only in `decided_by`.
That is item 4's ruling arriving here: `Redirect(String)` is a control event whose effect is a fork,
so the operator's steering and the policy's escalation share one lineage and one set of queries.

`price_estimated` next to `price_actual` is what makes the ladder self-correcting: the estimate is
shown before the rung commits (W5 F104), and the gap between the two is the number that recalibrates
it. Claudette's `fallback.jsonl` exists for exactly this purpose ("tune the thresholds against real
data", F191) and is a file *next to* the session rather than part of it — F173's two-stores problem
in miniature. In 2.0 it is a column on the chain.

### 6. "Traceable" means these six queries answer without a story

F129 made *fun* six queries over the event log. Lineage gets the same treatment and the same
discipline: if a question needs a human to reconstruct it, the record is wrong.

| Question | Query | Why it must be one query |
|---|---|---|
| Why did this task take four attempts? | the chain: `parent` walk with `cause`, `class`, `rung`, `evidence` | the answer *is* the chain; nothing to reconstruct |
| Did escalating help? | per rung: attempts entered ÷ attempts that reached `Success` | the only honest way to defend a ladder — and the number no donor can produce |
| What did it cost? | `sum(price_actual)` over the chain against R0's wall clock, plus the swap events | R3's price is fleet-wide (F194); the query must include what the *other* tasks lost |
| Which defect survived? | issue keys present in attempt *n* and *n+1* | BCF computes this in memory per mission (`mission.rs:1575-1584`) and throws it away; durable, it is the R1→R2 predicate |
| Who re-scoped it, and what did they type? | control events with `by:` and `displayed_at`, joined to the fork edge they caused | F186: the redirect text *is* the new attempt's prompt, so the join is by construction |
| Should the router have started higher? | for chains ending `Success` at rung *k*, the wall clock spent at rungs < *k* | the counterfactual that prices the routing model |

The last row is worth its own sentence. **W4's data well is dry** — the brief's §11 strikes through
"start with data you already own" — and the lineage chain is the well refilling itself: every
escalation is a labelled example of *"the router chose rung 0 and the task needed rung 2"*. v1 knew
it wanted this and captured only the final frame (`captureTrainingData`, fired once, at max
iterations, `taskExecutor.ts:237-241`). W4 should be told the data arrives as a by-product, not as a
collection project.

### 7. Budgets and thresholds

- **One budget per task** (F195), decremented by every mechanism that consumes an attempt, enforced
  in `apply()`. `+N attempts` is a control event with an author, not a config edit.
- **Thresholds are expressed against the budget they measure** (F192): a margin below the iteration
  cap with a floor, a fraction of the idle-gap timeout, a count of *consecutive* failures. Any
  absolute count of a budgeted quantity is a bug waiting for someone to change the budget.
- **The idle-gap timeout (F172 / OQ-W3-13) is what makes `Stuck` detectable at all.** Three donors
  have total-duration timeouts and none has an idle-gap timeout; without one, "the model went quiet"
  arrives as `Budget`, minutes late, indistinguishable from slow work.

### 8. The operator half, and OQ-W3-17's lineage rule

F196's three fixes: one clock (on the event), a loss rule that re-arms every time the state is
re-entered, and a target that comes from the ladder rather than from `findFirst`.

And the rule that decides whether an operator's mid-flight instruction *lands* or *forks*:

> **If the instruction changes what "done" means, it forks a new attempt (`cause: Rescope`,
> `decided_by: Operator`). If it only adds information the current attempt can use, it lands as
> `Enqueue` at the next model call.**

The test is the acceptance criteria, not the length of the text or where the worker happens to be.
This answers OQ-W3-17's lineage half — *what an enqueued steer does to the record* — and leaves its
timing half (does `Enqueue` land at the next model call or the next tool boundary when a tool is
mid-flight?) to the W5 console, where it is observable. The reason the distinction matters is F186: a
re-scope that lands as a note on a running attempt is a re-scope the model may never read, and that
is precisely how the donor lost it.

### 9. What not to build

- **No retry queue.** F187: a task with a failed attempt is a task in a state, and the scheduler is a
  projection (item 3).
- **No score-triggered escalation.** A scalar cannot express F189's distinction, and W6 F160 voided
  the only scalars we have.
- **No second lineage store.** No `fallback.jsonl`, no training-data table, no per-service log: one
  chain, one log, six queries.
- **No automatic model rung.** R3 pauses the fleet (F194); it is scheduled and priced, not fired.
- **No "escalate on any failure".** `Environment` and `Unmeasured` must not consume the budget that
  `Wrong` needs.

## Rejected alternatives and why

- **A separate `escalations` table.** It is the attempt chain with extra steps: every row would carry
  a `from_attempt` and a `to_attempt`, which is the edge the fork already writes. A second table with
  the same content is F149's drift hazard for no gain.
- **Escalating by re-writing the task description** (v1's mission retry,
  `orchestratorService.ts:682-739`, which appends `"\n\nRETRY NOTE: …"` and destroys the original
  prompt). The prompt of attempt *n* is evidence about attempt *n*; a chain whose earlier prompts
  have been overwritten cannot answer any of the six queries.
- **Keeping `brain_selector`'s per-turn scope.** It is right for a single-conversation agent, where
  the unit of work is a turn. 2.0's unit of control is the **task** (W5 F104), the thing that holds
  the slot and the locks, so the escalation edge is an attempt, not a turn — and the swap cost (F193)
  makes per-turn escalation unaffordable here anyway.
- **A judge deciding when to escalate.** The trigger would then have the same failure mode as the
  gate it is judging (W6 F159's critique term), and F188 shows what an unparseable judge produces: a
  measured-looking midpoint. The trigger is a classification over facts the system already has — exit
  codes, empty output, error streaks, timeouts — and none of them needs a model.
- **Escalating to a second *instance* of the same model** (N attempts in parallel, majority vote).
  Tempting on a machine where concurrency is 2 — and W2 F83 is exactly why it fails: two concurrent
  streams already saturate, so N parallel attempts cost N× wall clock with no throughput gain, and
  W1 F87 found the two models tie on verdicts, so variance is not obviously the binding constraint.
  Revisit if OQ-W3-19's measurement says bare retries convert well.

## Effect on fun

**Escalation is the story beat the console has been missing.** Everything before this item is a
system defending itself: states with contracts, writes that cannot drift, a stop that stops. This is
the one place the fleet *does something dramatic on purpose* — the champion fails twice, the console
says "calling in the heavy: 24 seconds to swap, the other unit holds", both units visibly pause, and
the big model takes the field. That is a set-piece falling out of the scheduler, not a cutscene
someone wrote.

**It is also where the honest-failure bar (F129) gets its best case.** A failed run worth replaying
is one where you can watch the fleet *trying different things* — R1's fix, R2's restatement, R3's
heavy — rather than the same attempt three times. The attempt chain is a replay timeline with
branches, and "why did this take four attempts" is answerable by scrubbing rather than by reading
logs.

**And the price tag is the drama.** 23.77 s is long enough to feel and short enough to watch. A verb
that costs nothing generates no tension; a verb that costs the *other unit's* time is a decision. The
console showing `R3: ~24 s swap · ~5× wall clock · fleet holds` before the operator commits is
simultaneously the honest disclosure W5 F104 requires and the most game-like moment in the design.

The cost worth naming: a ladder with real prices will sometimes be *declined*, and the fleet will
finish a task at `Failed` with three attempts on the chain and a rung it did not take. That is the
correct outcome and it will feel like a loss. It should — F129's honest-failure clause is that
failures are worth re-watching, not that they are rare.

## Open questions

| # | Question | Waiting on |
|---|---|---|
| ✅ OQ-W3-14 | **ANSWERED here** — `attempt` stays a **table**, written by `apply()` in the same transaction as the event. Immutability makes the denormalisation undriftable, and the console's most-used view stays cheap | — |
| OQ-W3-18 | What identifies "the same defect" across attempts? BCF normalises issue strings by substring (`mission.rs:1594-1620`), which is the fragile matching W6 F158 condemns elsewhere. The R1→R2 predicate depends on it | W6 item 2 (verifier output schema) |
| OQ-W3-19 | How often does a bare retry — same rung, same prompt — convert a failure into a pass? The ladder currently assumes "rarely enough not to bother". Cheap to measure: re-run the K-series failures n times | W8 harness, GPU |
| OQ-W3-20 | Does R3 pause the fleet automatically or ask? F194 makes it fleet-wide either way; the question is whether consent is per-escalation or a standing policy | W5 console, David |
| OQ-W3-17 | **Lineage half answered here** (changes the acceptance criteria ⇒ fork; adds information ⇒ lands). Timing half — where `Enqueue` lands when a tool is mid-flight — still open | W5 console |
| OQ-W3-6 | Unchanged, and item 5 adds the rung names to the list if the ladder is themed (R3 is *"calling in the heavy"* in every voice line the project owns) | David |

## Confidence: high on the diagnosis and the record, medium on the rung ordering

The donor findings are file:line facts from this pass, and the three that matter most were each
verified by grepping for *readers* rather than by reading the writer — which is what turned "v1
re-scopes to a stronger model" into F186, "v1 categorises its errors" into F189, and "the ladder
runs" into F187. F189 in particular was found by tracing the call order inside `abortTask`, not by
reading `categorizeError`, which looks correct in isolation. That is
[[verify-claims-against-code-not-docs]] item 18's lesson applied deliberately: a feature can be
present at every layer but the last.

The record design — attempt chain as a table, edges carrying cause, evidence, actor and price — is a
direct application of items 1, 3 and 4 and inherits their confidence.

What is weaker: **the rung ordering and the entry conditions are argued, not measured.** That R1
before R2 before R3 is the right order follows from the prices, which are measured, plus an
assumption about how often each rung succeeds, which is not. OQ-W3-19 is the cheap experiment that
would firm it up and W8's harness is the instrument. F194 is explicitly labelled derived — the swap
cost and the wall-clock ratios are measured, their composition into a fleet-pause is arithmetic that
has never been run end to end.

What would raise it: OQ-W3-19's measurement; and the first real chain — three attempts, one
escalation, one operator re-scope — rendered in W5's console, which is where a lineage design either
answers its six queries or does not.

---

# Item 6 — the Rust ecosystem survey, live-verified

## Question

The brief asks for a *"Rust ecosystem survey with live verification: async runtime, HTTP and
WebSocket layer, persistence, serialization, job and queue crates, and whatever agent-specific
crates are actually maintained today. Check last commit dates."* (§11:713-715)

Persistence was answered in item 3 and is not reopened here (F171, crates.io API, 2026-08-19). Of
what remains, one question is not a shopping list: **does ABCC 2.0's core run on `tokio`?** Every
other line on the list follows from it — an async runtime is not a dependency you add beside the
others, it is a colour that spreads through every function signature that touches it. F154 left the
burden of proof on tokio and named its one honest argument as **cancellation**. This item either
discharges that argument or concedes it.

The subordinate questions, in the order they turn out to matter: what serves the console W5 chose;
what the timeout story actually is on the stack the engine already ships; and which of today's
agent-specific crates are alive enough to matter.

## Method

1. **Read the manifests and the lockfiles of both Rust donors, then count the async surface** rather
   than trust the feature list. A `tokio` feature list is a claim; `grep -c "\.await"` is a fact,
   and the two disagreed in one repo.
2. **Read the vendored dependency source** for the semantics the design leans on —
   `~/.cargo/registry/.../reqwest-0.12.28/src/blocking/*` — and then re-read the same files on
   `master` to check the semantics are not a point-version accident.
3. **Measure rather than infer.** The claims that decide the item — "you cannot cancel", "you cannot
   detect a hang" — are cheap to test, so they were tested, against the exact dependency line the
   engine ships. Spike: `research/spikes/w3-runtime/` (a stdlib Python chunked server, a 200-line
   Rust probe, two repeats agreeing within milliseconds). Raw output in
   `w3-runtime-probe-results.txt`.
4. **crates.io API, live, 2026-08-20** for every crate named here, plus the **GitHub API for last
   commit dates** on anything whose crates.io row looked stale — the brief asks for commit dates,
   and a crate can publish rarely while being maintained, or the reverse.
5. Persistence deliberately **not** re-verified: item 3 did it one day earlier.

## Inherited

- **F154** — "proved twice" is threads proved once; tokio was never exercised. Burden of proof on
  tokio; its one honest argument is cancellation.
- **F162–F165** (OQ-W3-8's live probe) — cancellation against `llama-server` is 100% client-side: a
  socket close frees the slot in ≤0.25 s mid-decode.
- **F172** — three repos, three total-duration timeouts, zero idle-gap timeouts. Nothing in the
  family can distinguish a hung model from a slow one.
- **F184** — the control channel needs two engine changes: a boundary select, and an `AtomicBool`
  read between SSE lines at `api.rs:933`/`:1077`.
- **F194** — the expensive stop is a *scheduled fleet pause*, not a race.
- **W5 Option D** — the isometric web console served by the **same single binary** is the primary
  view, over **SSE plus `POST /control`** (F124). This is the fact that turns out to decide the item.
- **W2 F83** — aggregate throughput saturates at **N=2**. The fleet is two workers, not two thousand.
- **W1 F80** — measured TTFT: 2.2 s at 2.4k tokens, **33.9 s at 55k**; prefill plateaus ~1,600 tok/s;
  decode 54–76 tok/s.
- **Item 3 F171** — the persistence ruling and its live table. Not reopened.

## Findings

### 🚨 F197 — the engine being copied contains no async at all, and is already running a tokio runtime

Two facts that sound contradictory and are both true.

**There is no async in the source.** Across 93 modules and 65,519 lines of
`crates/claudette/src`, the count of `async fn` is **0**, `.await` is **0**, and `tokio::` is **0**.
The string "tokio" appears exactly once in the entire tree, as an example crate name in a tool's
JSON schema (`tools/registry.rs:32`). Concurrency is `std::thread` — 11 spawn sites — plus 58 uses
of `mpsc`/`SyncSender`/`Arc<Mutex>`/`AtomicBool`.

**And tokio 1.52.1 is in its `Cargo.lock`.** It arrives under `reqwest`'s `blocking` feature
(`crates/claudette/Cargo.toml:57`), and it is not vestigial: `blocking::ClientHandle::new` spawns a
thread named `reqwest-internal-sync-runtime` running a **current-thread tokio runtime**, then
forwards every request to it over an unbounded mpsc channel and blocks the caller on a oneshot
(`blocking/client.rs:1359-1420`). The lock holds 306 crates; `hyper`, `tower`, `mio` and
`futures-util` are all already there.

Measured cost of that arrangement, from the probe (test D): **exactly one extra OS thread per
`blocking::Client`, released on drop** — 5 → 6 → 7 → 8 → 9 threads for four clients, back to 5
after dropping them.

Two consequences, and they point in opposite directions from the usual argument:

- **"Adopt tokio" is not a dependency decision.** The dependency is paid, compiled and shipping in
  every Claudette binary today. Binary size, compile time and audit surface are already spent.
  Whatever tokio costs here, it is not that.
- **It is a code-shape decision**, and the shape it would change is 93 modules that currently have
  no colour at all. Adding `async` to the engine's call graph is not a `Cargo.toml` line; it is a
  rewrite of every function between `main` and the HTTP call — which is most of them.

And the shape 2.0 needs is already running: `tui_worker::spawn_worker`
(`tui_worker.rs:274-282`) spawns a thread whose doc comment reads *"The thread owns the runtime for
its entire lifetime, processing `UserInput` commands one at a time and firing `TuiEvent`s for every
interesting state change."* That is one agent, one OS thread, commands in over a channel, events out
over a channel — the fleet worker, minus the fleet. Going from one to N=2 is arithmetic.

### 🚨 F198 — measured: the blocking timeout is a *per-read* budget, not a total-duration one — so F172's missing idle-gap timeout is a config value, not a mechanism

The probe's first question was whether a streamed body under `reqwest::blocking` shares one budget
or renews it per chunk. Six lines 1000 ms apart — about five seconds of body — read under a **2 s**
client timeout:

| test | server | client timeout | result (run 1 / run 2) |
|---|---|---|---|
| A | 6 lines, 1000 ms apart | 2 s | **7 lines, completes in 5.003 s / 5.002 s** |
| A2 | 3 lines, 3000 ms apart | 2 s | **fails at 2.004 s / 2.015 s**, on the first over-budget gap |
| B | one line, then silence | 3 s | **fails at 3.005 s / 3.013 s** |

The budget restarts on every chunk. The mechanism is in the source: `impl Read for Response` calls
`wait::timeout(self.body_mut().read(buf), self.timeout)` (`blocking/response.rs:435-441`), and
`wait::timeout` computes `deadline = Instant::now() + d` **inside the call** (`blocking/wait.rs`),
parking the thread until the waker fires. A fresh deadline per `read()` is the definition of an
idle-gap timeout. Verified byte-identical on reqwest `master` (2026-08-20), and the changelog dates
the behaviour to **v0.11.7** ("Fix `blocking` request-scoped timeout applying to bodies") — it is
not a 0.12 accident.

**This corrects F172 for the Claudette half of the family, and sharpens it.** Claudette's
`REQUEST_TIMEOUT_SECS = 300` (`api.rs:147`, applied at `:237`) is not one thing. It is:

- an **inter-chunk gap** budget of 300 s on the streaming path — both of them, Ollama NDJSON via
  `consume_stream_lines(BufReader::new(resp))` and OpenAI-compat SSE via `consume_sse_lines(...)`
  (`api.rs:611-638`); and
- a **total** budget of 300 s on the non-streaming fallback path, `resp.json()` at `api.rs:628`,
  taken when the server answers a `stream: true` request without an SSE content type.

**The same constant means two different things, and which one you get is decided by a response
header.** F172's generalisation — *nothing in the family distinguishes a hung model from a slow one*
— survives as a statement about **the value**, not the mechanism: 300 s of silence between tokens is
not a hang detector, it is a hang tolerator. But the mechanism 2.0 needs is already under it.

⚠ **One trap to carry forward: the documentation says the opposite.** `RequestBuilder::timeout`'s
doc comment claims the timeout *"is applied from when the request starts connecting until the
response body has finished"* (`blocking/request.rs:356-359`) — a total-duration description of a
per-read implementation. `ClientBuilder::timeout` says *"connect, read and write operations"*, which
matches the code. A design that leans on the measured behaviour must own a test that pins it, or a
future release could "fix" the code toward the doc and turn 2.0's hang detector into a wall clock.

### F199 — the same knob also bounds time-to-first-byte, and the measured prefill table sets its floor

Test E, both directions:

- headers delayed **3 s** under a 2 s budget → `send()` fails at **2.006 s / 2.012 s**;
- headers delayed **1.5 s** under the same 2 s budget → succeeds, and the body then gets its own
  fresh budget (total 1.516 s / 1.502 s).

So one number bounds *the wait for the first byte* and *each subsequent read* — separately, not
cumulatively. There is no second knob on the blocking API: `ClientBuilder::read_timeout` was added
in reqwest **0.12.4** to the **async** builder and is still absent from the blocking one on
`master`; the blocking builder offers `timeout`, `connect_timeout`, `pool_idle_timeout`,
`http2_keep_alive_timeout`, `http3_max_idle_timeout` and a Linux-only `tcp_user_timeout`.

For a token stream that is the right shape anyway, and W1 F80 supplies the arithmetic:

| phase | measured | what the budget must clear |
|---|---|---|
| TTFB, champion, 2.4k prompt | 2.2 s | — |
| TTFB, champion, **55k prompt** | **33.9 s** | the daily driver's worst case |
| TTFB, the 27B rung (R3) | ~76 s derived (33.9 s × the 2.25× prefill ratio, W1 F88) | the escalation rung |
| inter-token gap, steady decode | 13–18 ms (54–76 tok/s) | three orders of magnitude below |

A single global constant that clears the 27B's cold prefill cannot detect a champion hang in under
about 90 seconds of waiting — which is why **the budget belongs to the rung, not to the client**.
`RequestBuilder::timeout` overrides per request on the blocking client
(`blocking/client.rs:1438`: `req.timeout().copied().or(self.timeout.0)`), so this costs one argument
at the call site: **champion 90 s, R3 180 s**, both roughly 2.4× their measured worst-case TTFB and
both an order of magnitude tighter than today's 300 s. That is OQ-W3-13's answer, derived from
measurement rather than taste; what it still wants is a run of real traffic to confirm nothing
legitimate sits between 34 s and 90 s.

### 🚨 F200 — measured: stopping a stream from another thread is an `AtomicBool` and a `drop`, and it lands in 3–14 ms

This is the argument F154 left standing, tested end to end on the blocking stack with no runtime in
the caller. A watchdog thread flips an `AtomicBool` at 1.000 s; the reading thread checks it between
lines and returns, dropping the `Response`:

- stopped at **1.014 s / 1.004 s** — 14 ms and 4 ms after the flag;
- the server observed the dead socket at **1.205 s / 1.215 s**, one write cadence later (it was
  writing every 100 ms), because the first write into a just-closed socket succeeds locally and the
  second one fails;
- where the server *polls* its socket instead of writing (test B), it sees the close in **19 ms** —
  3.024 s against the client's 3.005 s.

That is precisely F184's design — a flag read between SSE lines at `api.rs:933`/`:1077` — working, on
the stack already in the tree, at a latency three orders of magnitude below the thing being stopped.
Combined with F162's ≤0.25 s slot release measured against `llama-server` itself, **the cancellation
argument for adopting tokio in the core is discharged.** It was never a runtime capability; it was a
socket close, and a socket closes when its owner drops it regardless of who is polling what.

The honest residue: `tokio::select!` would let a worker wait on *the stream and the control channel
simultaneously*, where the thread design waits on the stream and samples the channel between lines.
The sampling interval is one SSE line — 13–18 ms at measured decode rates. Against an operator's
reaction time and a 23.77 s model swap, that difference does not exist.

### F201 — BCF's async is a calling convention, not concurrency, and it blocks the runtime it declares

The other donor is the one that "proved" tokio. What it actually contains, over 33 files and 17,481
lines:

| | count |
|---|---|
| `async fn` | 69 |
| `.await` | 206 |
| `tokio::spawn` | **6** |
| `tokio::select!` / `join!` / `try_join` / `JoinSet` | **0 / 0 / 0 / 0** |
| `Arc<` | **0** |
| `spawn_blocking` | **0** |
| `std::process::Command` vs `tokio::process` | **17 vs 15** |
| `std::fs::` vs `tokio::fs` | **50 vs 25** |

Zero `Arc<` in seventeen thousand lines is the whole story: **nothing is shared between tasks,
because there are no concurrent tasks.** Of the six spawns, four are UI or voice; one hands the
chat call a task so the caller can print tool events beside it (`main.rs:927-932`); and one
(`cto.rs:249`) launches an entire mission **detached** — no handle, no join, no cancellation, its
only channel to the world an optional `event_tx`. That last one is what "run a mission from the
chat agent" means in the donor, and it is exactly the uncancellable background work item 4 rules
out.

And the pipeline blocks its own runtime. `MissionRunner::attempt_round` is an `async fn`
(`mission.rs:933`) that calls `verifier::verify_project` — a **synchronous** function
(`verifier.rs:67`) — at `mission.rs:1006`. That function runs `cargo test`/`go test`/`pytest`
through `sandbox::run_tool_sandboxed`, whose wait loop is `try_wait()` plus
`std::thread::sleep(Duration::from_millis(200))` with a **120 s** cap (`sandbox.rs:142-153`). With
`#[tokio::main]` defaulting to the multi-thread runtime (`main.rs:252`) and `rt-multi-thread` in the
feature list, **a tokio worker thread is parked in a sleep-poll for up to two minutes per verify,
and `spawn_blocking` appears nowhere in the repo.** The manifest's own comment says the features
were narrowed to *"what `grep tokio:: src/` actually exercises"* — `process`, `fs` and `time` are on
the list while `std::process` and `std::fs` outnumber their tokio equivalents at every call site.

F154's "tokio never exercised" is confirmed and can be stated more strongly: **the async in the
family's async repo buys nothing that a thread would not, and costs a runtime it then blocks.**

### 🚨 F202 — the family's two child-process runners differ by one detail, and the one inside the async repo can deadlock

Both Rust donors run tools by spawning a child with piped stdout/stderr and polling `try_wait` with
a sleep. They diverge on what happens to the pipes while they poll:

- **Claudette drains them on background threads** the moment the child starts, with the reason in a
  comment — *"Drain pipes on background threads so the child can't block writing"*
  (`test_runner.rs:63`, reader at `:124-134`). On timeout it kills, then joins the readers, so a
  killed child still returns its partial output.
- **BCF does not.** `run_tool_with_timeout` pipes both streams, polls `try_wait()` every 200 ms, and
  calls `read_to_string` **only after the child has exited** (`sandbox.rs:126-134`). A child that
  writes more than the OS pipe buffer — 64 KiB, routinely exceeded by `cargo test` or
  `go test ./...` on a real project — blocks on `write`, never exits, and is killed at the 120 s
  deadline. The verifier then records a **timeout** for a tool that finished its work and was
  strangled by its own output.

This is a defect in the instrument W6 item 1 already voided on other grounds (F158), so it is
recorded here and handed on: **W6 item 2 inherits it.** For this item it makes a narrower point.
The two runners have the same architecture and one is correct; the difference is a design detail
about pipes, not a runtime capability. Nothing about `tokio::process` would have prevented it
either — `tokio::process::Child` has the same pipe semantics — and the repo that had the async
runtime available is the one that got it wrong.

### 🚨 F203 — the console decides the runtime, and it decides it for the edge only

Here is the argument that survives, and it is not the one that was expected.

W5 chose Option D: the isometric web console is the **primary view**, served by the **same single
binary**, over **SSE plus `POST /control`**. That is an HTTP *server*, and this is where the Rust
ecosystem genuinely constrains the choice. crates.io + GitHub, both 2026-08-20:

| Server crate | Latest stable | Last commit | 90-day downloads | Model |
|---|---|---|---|---|
| `axum` | 0.8.9 @ 2026-04-14 | **2026-08-20** | 107.1M | async (tokio) |
| `actix-web` | 4.14.1 @ 2026-08-09 | — | 9.6M | async (actix-rt/tokio) |
| `salvo` | 0.95.2 @ 2026-08-06 | — | 1.1M | async (tokio) |
| `poem` | 3.1.12 @ 2025-07-28 | — | 688k | async (tokio) |
| `tiny_http` | 0.12.0 @ **2022-10-06** | **2023-05-16** | 13.4M | blocking, thread-per-connection |
| `rouille` | 3.6.2 @ **2023-04-24** | 2025-06-17 | 2.9M | blocking |
| `astra` | 0.4.0 @ 2024-11-07 | — | **989** | blocking, on hyper |
| `may_minihttp` | 0.1.11 @ 2024-09-22 | — | 1,607 | coroutines (`may`) |
| `iron` / `nickel` / `simple-server` | 2019 / 2019 / **2018** | — | 187k / 96k / 2k | blocking, abandoned |

**Every maintained Rust HTTP server is async; every blocking one is stale.** `tiny_http`'s 13.4M
downloads are transitive weight behind a crate whose last commit is three years old, and `astra` —
the one modern blocking server, by a good author — has 989 downloads in ninety days. Serving a
long-lived SSE stream plus a control endpoint on `tiny_http` in 2026 means owning that layer.

So tokio enters ABCC 2.0. **At the edge, for the console, and nowhere else** — because the boundary
it needs to cross is already a *data* boundary, not a call boundary. Items 3 and 4 put the entire
contract between core and console in the SQLite event log: the console's SSE feed is a **reader of
the log** positioned by `seq`, and operator control is a **row written to the log**, not a call into
a worker. Neither direction needs a future to touch a worker's stack frame.

And the pattern for confining a runtime to a thread is already in the binary, written by someone
else: reqwest's blocking client is a current-thread tokio runtime on a dedicated thread, reached
only by channel (F197). 2.0's console server is the same trick with the polarity flipped — a
runtime on its own thread(s), reached only through the log.

### F204 — the survey table, for the layers item 3 did not cover

crates.io API, **2026-08-20**; commit dates from the GitHub API the same day. "Newest" is the most
recent publication of any kind, so a stable line stalled behind a release candidate shows as such.

| Layer | Crate | Latest stable | 90-day dl | Verdict |
|---|---|---|---|---|
| runtime | `tokio` | 1.53.1 @ 2026-07-20 | 205.5M | ✅ **edge only** — already in the lock at 1.52.1 (F197) |
| runtime | `async-std` | 1.13.2 @ 2025-08-15 | 9.4M | **self-deprecated** — its own description reads *"Deprecated in favor of `smol`"* |
| runtime | `smol` | 2.0.2 @ **2024-09-07** | 3.8M | alive upstream (commit 2026-08-03), but no server ecosystem to speak of |
| HTTP client | `reqwest` | **0.13.4** @ 2026-05-25 | 164.1M | ✅ **keep**, on the `blocking` feature; the tree pins `"0.12"` (0.12.28) |
| HTTP client | `ureq` | 3.4.0 @ 2026-08-08 | 51.5M | real alternative, rejected below |
| HTTP client | `attohttpc` | 0.31.0 @ 2026-05-25 | 5.9M | smaller, no streaming story worth the switch |
| HTTP server | `axum` | 0.8.9 @ 2026-04-14 | 107.1M | ✅ **the console**, with `tower-http` 0.7.0 for static assets |
| SSE, server | `axum::response::sse` | in-tree | — | ✅ event `id:` = `seq`, `Last-Event-ID` is a request header (F124/F126) |
| SSE, client | `eventsource-client` | 0.18.0 @ 2026-08-10 | 1.4M | alive (commit 2026-08-10) — **not needed**: the engine parses `data:` lines itself (`api.rs:1051-1120`) |
| SSE, client | `reqwest-eventsource` / `eventsource-stream` | 0.6.0 @ 2024-03-29 / 0.2.3 @ **2022-02-17** | 2.5M / 7.3M | stale; async-only; same conclusion |
| WebSocket | `tokio-tungstenite` / `tungstenite` | 0.30.0 @ 2026-07-11 | 63.7M / 71.0M | healthy — **kept as W5's documented fallback, not a plan** |
| serialization | `serde` + `serde_json` | 1.0.229 / 1.0.151 @ 2026-07 | 271M / 276M | ✅ **already in the tree**; the store is JSON columns at 263 B/event (F170) |
| serialization | `simd-json` / `sonic-rs` | 0.18.0 @ 2026-08-16 / 0.5.8 @ 2026-03-25 | 5.4M / 1.9M | alive, and pointless here — item 3 replays 1.06M events/s already |
| serialization | `bincode` / `rmp-serde` / `postcard` | 3.0.0 / 1.3.1 / 1.1.3 | 56.4M / 23.8M / 20.2M | binary formats buy nothing a human-readable log wants |
| config | `toml` | 1.1.4 @ 2026-07-28 | 193.2M | ✅ already in the tree — item 5's ladder is a TOML `Vec<Rung>` |
| process | `shared_child` | 1.1.1 @ 2025-07-04 | 10.2M | 🚨 **add** — kill a running tool child from the control thread; commit 2026-01-22 |
| process | `command-group` | 5.0.1 @ **2023-11-18** | 870k | process-group kill; stale (commit 2024-04-21); revisit only if orphans appear |
| process | `duct` / `subprocess` | 1.1.1 / 1.2.1 | 6.7M / 1.8M | alive; more than a `Command` plus two reader threads needs |
| assets | `rust-embed` | 8.12.0 @ 2026-07-08 | 13.2M | ✅ **add** — 44 MB of art and 96 voice lines inside one binary |
| assets | `include_dir` | 0.7.4 @ **2024-06-17** | 14.6M | same job, two years since a release |
| git | `gix` / `git2` | 0.86.0 @ 2026-07-23 / 0.21.0 @ 2026-05-18 | 9.3M / 15.4M | both alive — **W6 item 6's** call (worktrees, OQ-W3-12), not W3's |
| observability | `tracing` (+`-subscriber`) | 0.1.44 @ 2025-12-18 | 173.7M | **not** for the run record — that is the event log (item 3). Process diagnostics only |
| errors | `anyhow` + `thiserror` | 1.0 / 2.0.20 | — / 325.2M | ✅ `anyhow` already in the tree; `thiserror` for the typed domain errors item 1 introduces |
| job queue | `apalis`, `underway` | see F171 | | ❌ wrong layer, ruled in item 3 |
| persistence | `rusqlite` `bundled` | 0.40.2 @ 2026-08-08 | 29.9M | ✅ **already in the tree** at 0.39 — ruled in item 3, not reopened |

Two notes the table cannot carry. `notify` (filesystem watching) has been in a **9.0.0-rc since
2026-05-02** with 8.2.0 stable from 2025-08-03 — relevant to W6/W7, not here. And `rusqlite`'s
`Connection` is `Send` but not `Sync`: with the thread design it lives behind one `Mutex` and one
writer, which is item 3's `apply()` verbatim. Under an async core it would have needed
`tokio-rusqlite` (0.7.0, 518k) or `deadpool-sqlite` (0.13.0, 179k) — an extra crate and an extra
failure mode to buy back what the thread design has for free.

### F205 — the agent-framework layer exists now, and the one that matters is W10's business

The brief asks what agent-specific crates are *actually maintained*. As of 2026-08-20, unlike the
last time anyone looked, several are:

| Crate | Latest stable | Last commit | 90-day dl | What it is |
|---|---|---|---|---|
| `rmcp` | **3.1.4 @ 2026-08-20** | **2026-08-20** | **10.7M** | the **official** Model Context Protocol Rust SDK |
| `rig-core` | 0.42.0 @ 2026-08-17 | 2026-08-20 | 1.4M | opinionated LLM-app framework, provider-agnostic |
| `async-openai` | 0.41.3 @ 2026-07-31 | — | 2.3M | OpenAI-shaped client, alive |
| `genai` | 0.6.5 @ 2026-06-06 (0.7.0-beta.19 @ 2026-08-18) | — | 114k | multi-provider client |
| `ollama-rs` | 0.3.6 @ 2026-07-24 | — | 144k | Ollama client |
| `llm` | 1.3.8 @ 2026-04-19 | — | 30k | multi-backend unifier |
| `swiftide` | 0.32.1 @ 2025-11-15 | — | **2.1k** | agentic/RAG pipelines |
| `langchain-rust` | 4.6.0 @ **2024-10-06** | — | 12k | stale |
| `llm-chain` | 0.13.0 @ **2023-11-15** | — | 6.5k | dead |
| `kalosm` | 0.4.0 @ 2025-02-09 | — | 1.9k | local-model interface, quiet |
| `anthropic-sdk` | 0.1.5 @ **2024-07-23** | — | 9.7k | dead |
| `mcp-core` / `mcp-sdk` | 0.1.50 @ 2025-05-01 / 0.0.3 @ 2025-01-20 | — | 5.5k / 1.2k | superseded by `rmcp` |

The client crates are all solving the problem the engine solved in `api.rs`, against providers 2.0
does not use, and none of them knows about tool-registry freezing (W2 F81), the reload-retry window
(`api.rs:675-730`) or a `num_ctx` this project measures in gigabytes. Adopting one would trade a
measured file for an unmeasured dependency. The framework crates (`rig`, `swiftide`) go further and
want to own the agent loop — the exact asset §14 says to copy.

**`rmcp` is the exception worth flagging, and it is not W3's decision.** An official SDK, published
the day of this survey, at 10.7M downloads in ninety days, is the strongest signal in this table
about where tool interop is going; and MCP is the interop surface **W10** owns. Two facts to hand
over: it is tokio-based, and by F203 that is affordable — an MCP surface is an edge, and edges get
runtimes. Recorded, not adopted.

## Options compared

| | Core code shape | Console server | Cancellation | Idle-gap timeout | Cost to the inherited engine |
|---|---|---|---|---|---|
| **A. All-tokio core** — rewrite the engine async | every fn between `main` and the socket recoloured | native (axum) | `select!` | `read_timeout` on the async client | 🚨 93 modules, 65.5k lines, and the copy stops tracking upstream |
| **B. Threads everywhere** — blocking server too | unchanged | `tiny_http` (2023) / `astra` (989 dl) | measured, 3–14 ms (F200) | measured, per-read (F198) | owning an HTTP/SSE server layer nobody maintains |
| **C. Threads in the core, tokio at the edge** ✅ | unchanged | axum on its own runtime | measured (F200) | measured (F198) | zero — the seam is already the log (items 3, 4) |
| **D. Threads, no server** — TUI only | unchanged | none | measured | measured | contradicts W5 Option D; deletes the identity (W5's rejected option C) |

## Recommendation

### 1. The rule, in one sentence

**Threads own the work; a runtime owns the edge; the event log is the only thing that crosses.**
The fleet is OS threads — one per attempt, each owning its state, taking commands from a channel and
writing events through item 3's single `apply()` — and `tokio` exists in exactly one place: the
thread that runs the console's HTTP server.

### 2. The thread inventory, counted rather than hand-waved

At W2 F83's measured fleet size of **N=2**:

| Thread | Count | Why |
|---|---|---|
| main / supervisor | 1 | admission, watchdog sweep, `apply()` ownership |
| attempt workers | 2 | one per concurrent attempt (F83's ceiling) |
| `reqwest-internal-sync-runtime` | 2 | one per `blocking::Client`, measured (F197) |
| tool child pipe drainers | ≤4 | 2 per running tool, and only while one runs (F202) |
| console runtime workers | 2–4 | axum's runtime, or `new_current_thread` for one |
| **total, steady state** | **~8–11** | on a box whose GPU is the scarce resource |

Nothing here is close to the scale at which async's advantage — cheap tasks in the tens of thousands
— exists. The workload is two GPU-bound conversations and one operator.

### 3. The seam, which items 3 and 4 already built

The console never calls into a worker and a worker never calls into the console:

- **Downstream:** the SSE handler is a **reader** of the event log, positioned by `Last-Event-ID` →
  `seq`, tailing new rows. Two readers or ten make no difference to a worker.
- **Upstream:** `POST /control` **writes a `ControlRequest` row** and pokes an in-memory `Sender`
  (item 4). The poke is a latency optimisation and never the truth; boot replay is the backstop.
- Therefore the runtime boundary and the data boundary are the same line, and neither side's futures
  or threads are visible to the other. This is what makes option C cost nothing.

### 4. Timeouts, with the numbers on them

- Per-request, not per-client: `RequestBuilder::timeout`, set from the rung. **Champion 90 s, R3
  180 s** (F199) — roughly 2.4× each one's measured worst-case TTFB, and 1.7–3.3× tighter than the
  300 s inherited.
- Because the budget is per-read on a streamed body (F198), that same number is the **idle-gap**
  timeout F172 says the whole family lacks. A stream that stalls for 90 s is a hang; the worker
  records `Stuck{signal: IdleGap}` — item 5's class, not a generic failure — and item 4's recovery
  applies at F162's ≤0.25 s.
- The non-streaming fallback path (`api.rs:628`) keeps total-duration semantics. That is correct and
  should be **commented**, because the constant looks identical at both call sites.

### 5. The dependency list

Everything marked ✅ is already in `crates/claudette/Cargo.toml` and arrives with the copy:

✅ `reqwest` (blocking, rustls-tls, json) · `serde` · `serde_json` · `toml` · `anyhow` · `chrono` ·
`regex` · `ignore` · `glob` · `rusqlite` (bundled) · `ratatui` + `crossterm` (the deferred TUI) ·
`scopeguard`

➕ New, and each with one reason: **`axum` + `tower-http`** (the console and its static assets, F203)
· **`tokio`** (already in the lock; now a direct dependency, features `rt-multi-thread`, `net`,
`sync` — *not* `full`) · **`rust-embed`** (44 MB of identity inside one binary) ·
**`shared_child`** (kill a tool child from the control thread) · **`thiserror`** (item 1's typed
domain errors).

Sixteen direct dependencies against Claudette's nineteen. The bet is that 2.0's core is *smaller* in
dependencies than the engine it copies, because everything W3 adds is structure, not machinery.

### 6. What not to build, and what not to add

- **No async in the core.** Not "not yet" — the measurements say it buys nothing here.
- **No agent framework** (F205). The agent loop is the inherited asset.
- **No LLM client crate.** `api.rs` is measured, retry-hardened and already OpenAI-compatible.
- **No `tracing` for the run record.** The event log is the record (item 3); `tracing` is for
  diagnosing the binary, and mixing the two produces two logs that disagree.
- **No WebSocket** until something needs bidirectional streaming (W5, unchanged).

### 7. Two tests this design owes itself

1. **Pin the per-read semantic.** A test that streams a body with gaps under a short timeout and
   asserts it completes — because the documentation describes the opposite behaviour (F198) and a
   future release could align the code to the doc.
2. **Pin the cancel latency.** A test that sets the flag mid-stream and asserts the reader returns
   within one line — because F200's 3–14 ms is the number the operator's abort button inherits.

Both are cheap, both run offline, and the spike in `research/spikes/w3-runtime/` is their prototype.

## Rejected alternatives and why

- **An all-tokio core (option A).** Rejected on F197 + F200 + F201: it would recolour 93 modules and
  65.5k lines to buy `select!` over a 13–18 ms sampling interval, and the family's own async repo
  demonstrates the failure mode — 69 `async fn`, zero `select!`, zero `Arc<`, and a runtime worker
  parked in a 200 ms sleep-poll for up to two minutes (F201). It also permanently ends the option of
  tracking Claudette upstream, which §14's "both stay live" assumes.
- **A blocking HTTP server (option B),** keeping tokio out entirely. Rejected on F203's dates:
  `tiny_http`'s last commit is 2023-05-16, `rouille`'s release is from 2023, `astra` has 989
  downloads in ninety days, `iron`/`nickel` are 2019. A long-lived SSE stream is exactly where an
  unmaintained server layer becomes the project's problem.
- **`ureq` instead of `reqwest`,** which would remove tokio from the process entirely — a real
  option, alive (3.4.0 @ 2026-08-08, 51.5M/90d), with **nine named timeout knobs** where reqwest has
  one. Rejected on the shape of those knobs: they are phase deadlines (`timeout_recv_response`,
  `timeout_recv_body`, `timeout_global`), and **none of them is an inter-chunk gap**. For a stream
  where the body legitimately takes minutes and silence is the failure signal, reqwest's per-read
  budget is the better instrument — and it is measured (F198), in the tree, and behind the one file
  that is the engine's contract with the model.
- **`smol`/`async-std` as a lighter runtime.** `async-std`'s own crates.io description reads
  *"Deprecated in favor of `smol`"*; `smol` is alive but its last release is 2024-09-07 and no
  maintained HTTP-server ecosystem sits on it. Choosing it would mean owning the server layer anyway,
  which is option B with extra steps.
- **`sqlite-es` / an event-sourcing framework.** Ruled in item 3 (F171); not reopened.
- **`tokio-rusqlite` / `deadpool-sqlite`.** Only needed by the core shape this item rejects.

## Effect on fun

Three of the project's promises turn out to be latency claims, and this item is where they get their
numbers.

**The abort button is honest.** F200 measures the whole path an operator's *stop* travels: flag set,
read between lines, socket dropped, slot free — 4–14 ms of software over a ≤0.25 s server-side
release (F162). "Stop" that visibly stops is the difference between a command center and a progress
bar, and it now has a measurement instead of an intention.

**A hung model looks different from a thinking one.** Today, 300 s of silence and 300 s of work are
the same picture. With a per-rung 90 s idle-gap budget (F199) the console can say *the champion has
been silent for 41 s* — which is the honest-failure-reporting requirement W6 item 8 will ask for,
delivered by a config value rather than a subsystem.

**The console is one binary, and the art is inside it.** `rust-embed` and a single `axum` thread mean
`abcc` with no arguments opens the isometric console with its 44 MB of sprites and 96 voice lines,
with no second process, no container and no asset directory to lose (W5 F95/F125).

And a quieter one: the core stays **debuggable by reading it**. A stack trace through nine OS
threads names the function that is stuck. That matters more on a solo project at this cadence than
any throughput number tokio could offer at a scale of two.

## Open questions

| # | Question | Waiting on |
|---|---|---|
| ✅ OQ-W3-13 | **ANSWERED here** — the idle-gap value is per-rung, from measured TTFB: champion **90 s**, R3 **180 s**, set with `RequestBuilder::timeout`. Confirmation that nothing legitimate sits between 34 s and 90 s is a by-product of the first real runs | — (confirm on W8 traffic) |
| OQ-W3-21 | Does the console runtime get `new_current_thread` or `rt-multi-thread`? One operator and an SSE tail argue for the former; W10's multiplayer would argue the latter. Deferrable — it is one builder call | W10 |
| OQ-W3-22 | `reqwest` is pinned `"0.12"` in the copy and 0.13.4 is current. The per-read semantic is unchanged on master (F198), so this is a routine upgrade — but it should be done **with the pinning test in place**, not before | — (do it with test 7.1) |
| OQ-W3-23 | Does the sampling design need a second control check *inside* a long tool call, or is the tool's own child-kill (F202, `shared_child`) sufficient? Item 4's boundary select covers between-tool; a 10-minute `cargo test` is the gap | W7 (sandboxing), W6 item 6 |

## Confidence: high

The runtime ruling rests on five measurements taken twice, agreeing within milliseconds, against the
exact dependency line the engine ships — not on a reading of the documentation, which in the decisive
case (F198) says the opposite of what the code does. The donor counts are `grep` over checked-out
trees, and the ecosystem rows are the crates.io and GitHub APIs on the day of writing, with last
commit dates checked wherever a release date looked stale — which is how `tiny_http` (13.4M
downloads, last commit 2023) and `astra` (maintained, 989 downloads) both got read correctly.

What is weaker: **F199's 90 s and 180 s are derived, not observed in production.** They come from
W1's measured TTFT table times a margin, and the margin is a judgement. If a legitimate champion
turn ever takes 91 s to first token, the number is wrong and the run that discovers it will look
like a hang — which is why the answer is a config value per rung rather than a constant in the
source. F203's server conclusion also depends on W5's Option D holding; if the console were ever
descoped to a TUI, tokio would leave the design entirely, and nothing in the core would change.

What would raise it: the two pinning tests in recommendation 7, and the first fleet run where an
operator presses stop on a real 55k-token turn.

---

# Item 7 — process topology

## Question

The brief's last W3 line: *"Process topology: one binary, or a supervisor plus workers? What does
that mean for sandboxing in W7 and for the multiplayer protocol in W10?"* (§11:727-729)

Item 6 settled the *runtime* shape — threads own the work, one runtime owns the console edge. This
item settles the *process* shape, which is a different question with different arguments: a thread
boundary is a compiler construct, a process boundary is an OS construct, and only the second one
survives a panic, enforces a memory limit, or can be killed unconditionally.

Three sub-questions, in the order the evidence orders them:

1. What did the family's process boundary actually buy? (One donor is eight containers.)
2. What does a boundary cost here, measured — and what does the *absence* of one cost?
3. Which of the three things a process boundary is for — blast radius, kill semantics, isolation —
   can be had without one?

## Method

- **Read v1's topology from its compose file and its service entry points**, then check whether the
  concurrency the design implies is the concurrency the code can deliver. It is not, and the gap is
  one line of `uvicorn`.
- **Measure**, again, rather than argue: spawn cost, and the kill semantics of the mechanism both
  Rust donors already use. Spike: `research/spikes/w3-topology/orphan_probe.py` (stdlib, ctypes for
  the Windows half), two runs agreeing exactly. Raw output in `topology-probe-results.txt`.
- **Read the donors' panic policy as written**, including the lints and the CI that enforces them —
  because "one panic kills the fleet" is only an argument if panics are actually reachable.
- Cross-check the two workstreams this item feeds: W7's isolation requirements and W10's remote-rig
  protocol.

## Inherited

- **Item 6's ruling** — threads in the core, one runtime at the edge, ~8–11 threads at N=2.
- **Item 3** — one SQLite writer, one `apply()`, boot = replay at 94 ms per 100k events (F170).
- **Item 4** — control is a row on the log; the stop verbs are a boundary select plus a cancel flag.
- **F200** — the cancel flag lands in 4–14 ms, *when the worker is somewhere that checks it*.
- **F151** — the engine's release profile is `panic = "abort"`.
- **W5 F95/F125** — a container is the thing 2.0 exists to escape; the install story is one binary.
- **W2 F83** — the fleet is two concurrent attempts.
- **W1 F80** — a turn begins with 33.9 s of prefill at the daily driver's context.

## Findings

### 🚨 F206 — v1 has eight containers and one event loop: the process boundary bought a network hop, not concurrency

`docker-compose.yml` defines **eight services** — postgres, redis, ollama, api, agents,
mcp-gateway (profile-gated), ui, backup. That is the shape of a supervisor-plus-workers design.
Then:

- The `agents` container starts `uvicorn src.main:app --host 0.0.0.0 --port 8000`
  (`packages/agents/Dockerfile:41`) — **no `--workers`**, so one process, one event loop.
- `/execute` is declared `async def` (`main.py:236`), so it runs *on* that loop rather than in
  FastAPI's threadpool.
- Inside it, `result = crew.kickoff()` (`main.py:381`) — a fully synchronous CrewAI run that takes
  minutes. There is no `run_in_executor`, no `to_thread`, no `asyncio` anywhere in the file.

**So the entire agent fleet is serialised on one Python event loop, and while a task runs the
service cannot answer anything at all** — not a second `/execute`, not `/health`.

Now the admission side. `ResourcePoolService` grants `ollama: 1` and `claude: 2` slots, plus
`grok: 2` and a configurable `remote_ollama: N` when those are enabled
(`resourcePool.ts:88-118`) — **three to five concurrent tasks admitted** against an executor that
can run one. The queued ones are not queued anywhere visible: the API has already written
`status:'in_progress'`, the watchdog clock is running, and the Node side is blocked in
`fetchWithTimeout(..., EXECUTE_TIMEOUT_MS)` where `EXECUTE_TIMEOUT_MS = 600_000`
(`executor.ts:8`) — **a fourth total-duration timeout, and the largest of v1's, which F172's
three-row table missed.** Ten minutes later the task fails with `Execution failed`, attributing to
the agent a delay that was entirely queueing.

One more detail in the same family as item 5's zero-reader fields: `maxConcurrentTasks` is a
validated field on the agent PATCH route (`routes/agents.ts:162`) that lands in the Agent's `config`
JSON — and **grep finds no reader anywhere in `packages/`.** The fleet's size is a setting nobody
consults, sitting above an executor whose real capacity is one.

**The lesson for 2.0 is not "avoid processes". It is that a process boundary buys nothing unless
something inside it is concurrent.** v1 paid the boundary's full price — a network hop, a second
language, a container, serialisation at the edge, and a 600 s timeout to paper over the queue — for
a fleet of one.

### F207 — measured: a process boundary is nearly free at this workload, so the decision cannot be made on cost

From the probe, two runs agreeing:

| | run 1 | run 2 |
|---|---|---|
| spawn only, no wait (`Popen`) | 2.5 ms | 2.4 ms |
| native binary spawn + exit + reap (`cmd /c exit`) | 10.5 ms | — |
| interpreted child spawn + exit + reap | 27.8 ms | 26.5 ms |

Against W1's measured **33.9 s** time-to-first-token at the daily driver's context, a 10 ms process
spawn is **0.03% of one turn** — and an attempt is many turns. Even the most pessimistic reading
(27.8 ms, which is mostly Python interpreter startup a Rust worker would not pay) does not register.

This cuts both ways and is worth stating plainly: **there is no performance argument for one process
and no performance argument against workers.** Anyone who reaches for either is arguing from
something else. The something else is the next three findings.

### 🚨 F208 — measured: the family's kill orphans the work it was told to stop

Both Rust donors stop a tool the same way: `child.kill()` on the handle they hold
(`test_runner.rs:82`, `sandbox.rs:145`). The probe reproduces exactly that shape — a wrapper process
that launches the real worker and waits on it — and kills the wrapper:

- **plain `child.kill()`: the grandchild kept running.** Ticking 5 times at the moment of the kill,
  13 two seconds later, still alive. Identical in both runs.
- **a Windows Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`: the tree died in 1.8–1.9 ms**,
  and creating the job cost **0.04 ms**.

That wrapper shape is not hypothetical, it is the normal path. Claudette's `bash` tool executes
`powershell -NoProfile -NonInteractive -Command <command>` on Windows and `sh -c <command>`
elsewhere, through `run_command_with_timeout(program, &args, 30, …)` (`tools/shell.rs:207-221`) —
**a 30-second timeout**, so any build, test run or install that takes longer than half a minute ends
with the shell killed and the actual work detached, still writing to the workspace the orchestrator
believes it has reclaimed. BCF's verifier is the same story one level down: it kills `cargo`, and
`cargo test`'s test binary is a grandchild.

Two consequences:

- **This is a defect in the inherited tool runner, and it is independent of the topology choice.**
  In-process workers or worker processes, the tool's own children need a job object (Windows) or a
  process group (Unix), or "stop" is a lie at the only level where the user can see it.
- It also **bounds what F200's cancel flag is worth.** The flag stops the model stream in 4–14 ms.
  It does nothing about a detached `npm install`. Item 4's kill verb is only as good as the tree
  kill underneath it.

### 🚨 F209 — the engine can start work it has no verb to stop

The shell tool surface is four verbs: `bash`, `bash_background`, `bash_status`, `bash_tail`
(`tools/shell.rs:75-157`). There is **no `bash_kill`**. `bash_background` writes the child's pid to
an owner-only meta file, spawns a reaper thread that waits for exit and stamps a `.done` file
(`shell.rs:589-595`), and returns the job id. From that moment the job is observable — status,
tail — and unstoppable: nothing in the tool surface, the REPL, or the TUI terminates it.

Combined with F208, **the family's complete answer to "stop that" is "wait for it"**, and the
operator control bar W5 designed has nothing underneath it at the tool level. 2.0's `Kill` verb
therefore needs three things, not one: the cancel flag (F200), the tree kill (F208), and a verb that
reaches background jobs (this).

### F210 — the blast radius of one process is smaller than the profile suggests, because the donor already worked the problem

`panic = "abort"` is in both Rust donors' release profiles, and under `abort` a panic on *any*
thread takes the process down — no `catch_unwind`, and even `scopeguard::defer!` is skipped. On its
face that is the strongest argument for worker processes: one bad `unwrap` in attempt A kills
attempt B.

Except the donor has spent effort making panics unreachable, and it is visible in the source:

- `#![cfg_attr(not(test), deny(clippy::unwrap_used))]` at the top of **both** `lib.rs:22` and
  `main.rs:22`, annotated *"Production code must not panic via `.unwrap()` … a stray unwrap is a
  hard process crash, not a catchable error. (Wave F.1 — production unwrap audit.)"*
- CI enforces it: `cargo clippy --all-targets --no-deps -- -D warnings`, twice (default features and
  `--all-features`), on an OS matrix (`.github/workflows/ci.yml:56-57`). The 768 `.unwrap()` calls
  in the tree are therefore, by construction, inside `#[cfg(test)]` — 85 of 93 modules carry inline
  tests.
- `unsafe_code = "forbid"` at the crate level.
- And where an abort would do damage the user could not undo, there is a hook: `run_tui` installs a
  panic hook that leaves raw mode and the alternate screen *before* the process dies, with a comment
  explaining that `defer!` does not run under `abort` (`tui.rs:686-709`).

What remains is real but named: **`.expect(` is not linted** (388 occurrences, some of them
production — `api.rs:239` builds the HTTP client with one), plus slice indexing, arithmetic, and
panics inside dependencies.

And the cost of an abort is now bounded by item 3. The durable state is the log; a crash loses the
in-flight turn of each running attempt and nothing else, and boot is replay at 94 ms per 100k
events. At N=2 that is two turns — expensive in GPU seconds, invisible in correctness.

**Which reframes the question. Blast radius is not "process or no process". It is "does a panic in
attempt A end attempt B", and there is a third answer.** See recommendation 2.

### F211 — the fleet is new construction either way, so nothing inherited constrains the boundary

The engine builds exactly one conversation: `runtime_build.rs:155` is the only
`ConversationRuntime::new` outside tests, used by both the REPL and the TUI worker. The
`OllamaApiClient::new` constructor whose doc comment says *"Used by spawned agents (who have a hard
tool allowlist) and by tests"* (`api.rs:211-213`) has, on grep, **only test callers** — the spawned
agents it describes are not in the tree.

And the multi-agent plumbing that does exist is deliberately hollow. `forge/mod.rs:1-20` describes
itself as *"dormant plumbing for forge-mode"* and lists what survived the fold: a persona loader, a
role→model map, and three types. *"The standalone crate's `pipeline` module (`pub mod` stubs only)
did not carry over — it was 36 LoC of empty placeholders"*, and the pipeline vocabulary was
*"dropped 2026-05-15 after the multi-agent audit."*

So the process-topology decision is genuinely free: there is no inherited fleet whose shape has to be
respected, in either donor, and W11's stage pipeline will be new code too.

### 🚨 F212 — worker processes force W10's protocol early, because the log has exactly one writer

This is the finding that decides the item, and it comes from item 3 rather than from the OS.

The durability ruling is **one writer**: a single `apply()` that appends the event and updates the
projection in one transaction (F169). A worker in the same process calls it behind a mutex — the
cost is a function call. A worker in a *different* process cannot: SQLite would need multi-process
WAL writers (possible, but it discards the single-writer invariant that makes the design provable),
or the worker sends its events to the supervisor to write — which is an **IPC protocol carrying
every state transition, every token-level progress marker and every control answer**.

That protocol is not a small thing bolted on. It is, feature for feature, **W10's remote-rig
protocol**: a worker that talks to the supervisor over a wire is a remote worker whose wire happens
to be local. Choosing worker processes today therefore does not add a process boundary; it adds
W10's design, before W10 has run, to buy isolation that recommendation 2 gets for free.

The inverse is the useful half: **the seam is worth defining now even though the boundary is not
worth building now.** A worker's entire interface with the rest of the system is two operations —
read control decisions addressed to me, append events about what I did. Keep it to those two, behind
a trait, and the local implementation is a function call while the remote implementation is W10's
protocol, with no third design in between.

## Options compared

| | Concurrency | Blast radius | Kill semantics | Isolation | Install story | Cost now |
|---|---|---|---|---|---|---|
| **A. One process, threads** | N=2, real | one panic ends the fleet (F210) | cooperative flag + tree kill | none between attempts | one binary ✓ | zero |
| **B. Supervisor + worker processes** (same binary, `abcc worker`) | N=2, real | contained per attempt | preemptive, per worker | memory + handles | still one binary ✓ | 🚨 W10's protocol, early (F212) |
| **C. Supervisor + containers** (v1) | **one**, in practice (F206) | contained | preemptive | strong | ✗ docker-compose (W5 F95) | very high |
| **D. One process, threads, `panic = "unwind"` + `catch_unwind` per attempt, seam defined** ✅ | N=2, real | **contained per attempt** | cooperative flag + tree kill | none between attempts | one binary ✓ | one profile line |

## Recommendation

### 1. One binary, one process, threads — and the fleet lives inside it

`abcc` is a single process: supervisor, workers, tool children, console runtime. This follows item 6
and W5 F95, and F207 confirms nothing is being paid for it. Worker *processes* are not rejected
forever; they are rejected **now**, on F212 — they would import W10's protocol into W3.

### 2. Build with `panic = "unwind"` and catch the panic at the attempt boundary

This is the one place 2.0 should **deviate from the inherited release profile**, and the reason is
that the inheritance changed shape. Claudette runs one conversation, so `abort` costs exactly the
thing that panicked, and its arguments — a smaller binary and no unwind tables across an FFI
boundary — are unopposed. 2.0 runs a fleet, and under `abort` a panic in attempt A ends attempt B,
the console, and the supervisor.

With unwinding, a panicking worker thread simply ends; `JoinHandle::join()` returns `Err`, the
supervisor records the attempt as `Failed` with item 5's `FailureClass::Environment{panic}` — a class
that explicitly never climbs the model ladder, which is right, because a bigger brain does not fix a
slice index — and the other attempt never notices. The pattern for the one hazard, a poisoned mutex,
is already in the donor: `Err(poisoned) => poisoned.into_inner()` (`api.rs:182-183`).

Carry the donor's discipline unchanged: `deny(clippy::unwrap_used)` outside tests, enforced by CI
with `-D warnings`; `unsafe_code = "forbid"`; a panic hook where terminal state is at stake. Consider
extending the lint to `expect_used` in the worker modules only — F210 names it as the residual.

### 3. Every tool child is born into a job object or a process group

Non-negotiable, and independent of everything above (F208). Measured cost: 0.04 ms to create the
job, 1.8 ms to kill the tree. Without it, `Kill` stops the shell and not the build, and the
workspace keeps changing under a task the console shows as stopped.

⚠ **This collides with `unsafe_code = "forbid"`** — `CreateJobObject` via `windows-sys` and `killpg`
via `libc` are both `unsafe`. Three ways out, and the choice is W7's: a single narrow module with
`#[allow(unsafe_code)]` and a comment; `command-group` (5.0.1, but last commit 2024-04-21);
or `process_control` (5.2.0 @ 2025-09-06, 417k dl/90d). On Unix, `Command::process_group(0)` is safe
std since 1.64 and gets half the job done — the group kill is the part that needs help.

### 4. The missing verb

Add the kill (F209). Every started process — foreground tool, background job, model request — is
addressable and stoppable, or the operator control bar is decoration. Background jobs already write
a pid file; that is the registry, it just has no consumer.

### 5. Define the worker seam now, build the boundary later

A worker's interface is exactly two operations:

```
trait Worker {              // the shape, not the signature
    fn poll_control(&self, attempt: AttemptId) -> Option<ControlDecision>;  // read the log
    fn append(&self, event: Event) -> Seq;                                  // one apply(), one writer
}
```

Local workers get a direct implementation over item 3's `apply()`. When W10 wants a rig over
Tailscale, it implements the same two operations over HTTP and nothing else in the system learns
about it. **The rule that keeps this true: no worker ever touches the store, the console, or another
worker directly.** That rule costs nothing today and is unrecoverable if broken.

### 6. What this hands to W7 and W10

- **W7 (sandboxing):** the isolation boundary in 2.0 is the **tool child**, not the worker — a worker
  is trusted code, the tool runs whatever the model wrote. That is where the sandbox belongs, and
  recommendation 3's job object is also the natural attachment point for a memory cap and a
  descendant limit. W7 also inherits the unsafe-code question from 3, and F208 as a live defect.
- **W10 (fleet):** the seam in 5 is the protocol's first draft, and F212 is the reason to design it
  as if it were remote from the beginning. Also: v1's failure (F206) is the cautionary case — a
  remote rig that serialises internally is a rig with one slot, whatever its pool advertises.

## Rejected alternatives and why

- **v1's container-per-concern (option C).** Rejected on F206 and W5 F95: eight services whose fleet
  is one event loop, plus the install story 2.0 exists to escape. The design's own admission control
  over-promises its executor by 3–5×, and it needed a 600 s timeout to hide the queue.
- **Worker processes now (option B).** Rejected on F212, not on cost — F207 says the cost is 10 ms.
  It buys per-attempt blast-radius containment that recommendation 2 provides for one line in
  `Cargo.toml`, and it charges W10's protocol for it. Revisit exactly when a worker needs to be
  remote, an OS-enforced memory cap, or a preemptive kill that survives wedged native code.
- **Keeping `panic = "abort"` because the engine has it.** Rejected on F210's own reasoning: the
  security argument is about panics crossing an FFI boundary, and 2.0's own code forbids `unsafe`;
  what changed is that the process now holds more than one attempt.
- **A thread per tool call with in-process sandboxing.** Rejected as out of scope and probably
  incoherent — a thread shares the address space with the orchestrator, so it is not a boundary
  against anything the model writes. That is W7's problem and the child process is its unit.
- **`spawn_blocking`-style worker pools, work stealing, or any scheduler cleverness.** At N=2 there
  is nothing to schedule. Item 6's thread inventory is the whole design.

## Effect on fun

**Stop means stop, all the way down.** The measurement that matters here is not the 1.8 ms tree
kill; it is the 13 ticks the orphan kept writing after being killed. An operator who presses stop and
watches the file tree keep changing stops trusting the console, and no amount of isometric sprite
work buys that back. Recommendation 3 is the least glamorous line in this workstream and probably
the most load-bearing for the feeling of command.

**One attempt can fail without taking the room with it.** Under the inherited profile a stray slice
index in a tool ends the whole session — every attempt, the console, the operator's place in the
run. Recommendation 2 turns that into one card going red while the other keeps working, which is
what a command center looks like when something goes wrong, and it costs a profile line.

**And the install is still one file.** Every argument in this item that pointed at processes pointed
at more infrastructure, and each one was answered without it. `abcc` stays a binary you can copy to
a machine and run — which is the property W5 F95 identified as the difference between the thing
people try and the thing people read about.

## Open questions

| # | Question | Waiting on |
|---|---|---|
| OQ-W3-24 | How does the tree kill get built without breaking `forbid(unsafe_code)` — narrow `#[allow]` module, `command-group` (stale), or `process_control`? And what is the Unix half, given `Command::process_group(0)` is safe but `killpg` is not? | W7 |
| OQ-W3-25 | Does `panic = "unwind"` cost anything measurable here — binary size and the release profile's `opt-level="z"`/`lto` interaction? Cheap to measure once 2.0 has a binary | — (build it and check) |
| OQ-W3-26 | At what point does a worker actually need to be a process — the first remote rig, an OS memory cap, or a wedged tool that ignores the flag? The trigger should be written down before the temptation arrives | W10, W7 |
| OQ-W3-27 | Background jobs (F209) outlive the attempt that started them by design. Does a job survive its attempt's completion, or is "kill my orphans" part of attempt teardown? | W5 console, W7 |

## Confidence: high on the diagnosis, high on the ruling, medium on recommendation 2's details

F206 and F208–F211 are file:line facts and two agreeing measurements. The orphan result in
particular is the kind of finding that only appears when you run it: both donors' code reads
correctly, and the mechanism they share does not do what its call site assumes.

The ruling — one process now, seam defined, boundary deferred — rests on F212, which is an argument
from item 3's single-writer invariant rather than a measurement. It is a strong argument, but it is
an argument: if the store ever grew a second writer for another reason, the case against worker
processes would weaken considerably.

Recommendation 2 is the piece most likely to need adjustment in contact with real code. Unwinding
across a thread that holds a `MutexGuard` on the SQLite connection is the hazard, and while the
donor's poisoning idiom handles it, "handles it" here means the next writer sees a poisoned lock and
must decide whether the projection is intact. That decision has not been designed yet, and it should
be, before the first panic finds it.

---

# W3 — what the seven items decided

Written 2026-08-20, at the close of the workstream. One line per item, so the next workstream can
read the rulings without re-reading the arguments.

| # | Item | The ruling | Confidence |
|---|---|---|---|
| 1 | Typed lifecycle | One vocabulary per entity, **seven** Task states as data-carrying variants, one write path, attempts immutable, status a projection | high on structure, medium on names (OQ-W3-6) |
| 2 | Inheritance | 93 modules, one crate; the attempt/turn line is the engine contract; **two** intrusive engine changes | high |
| 3 | Durability | SQLite event log, WAL + `synchronous=FULL` (929 µs measured), one `apply()`, boot = replay (94 ms/100k) | high |
| 4 | Control channel | Control is **durable data on that log**; identity is a `seq`; broker writes then pokes; `Redirect(String)` is in the type | high |
| 5 | Escalation | **Classify before escalating**; one ladder that is data; fork from the *best* checkpoint; R3 pauses the fleet | high on record, medium on rung order |
| 6 | Ecosystem | **Threads own the work, one runtime owns the edge, the log is the only thing that crosses**; timeouts per rung | high |
| 7 | Topology | **One process now**, `panic = "unwind"` for per-attempt containment, tree kill for every tool child, worker seam defined as if remote | high |

**The one sentence the workstream reduces to:** *a fleet of OS threads writing an append-only SQLite
log through a single writer, controlled by rows on that same log, observed through an SSE tail of
it, escalating by forking immutable attempts, and served to a browser by one runtime confined to the
edge — in one binary.*

**What W3 still owes, all tracked as open questions:** the variant names (OQ-W3-6, David), retention
(OQ-W3-11 = OQ-W5-9), the workspace checkpoint marker (OQ-W3-12 → W6 item 6), two-operator arrival
semantics (OQ-W3-15/16), where `Enqueue` lands mid-tool (OQ-W3-17), defect identity across attempts
(OQ-W3-18 → W6 item 2), the bare-retry conversion rate (OQ-W3-19 → W8), fleet-pause consent
(OQ-W3-20, David), the console runtime flavour (OQ-W3-21 → W10), the reqwest upgrade (OQ-W3-22),
control inside a long tool call (OQ-W3-23 → W7), and item 7's four (OQ-W3-24 through 27).

**What it hands other workstreams, beyond the open questions:** W4 learns that its training data is
a by-product of escalation, not a project. W6 inherits F202's pipe-buffer deadlock and F161's
`Uncertain` rule. W7 inherits the tool child as *the* isolation boundary, plus the unsafe-code
question. W10 inherits the worker seam and v1's cautionary tale about rigs that serialise. W11
inherits an empty field: no fleet exists in either donor to constrain the stage design.

---
