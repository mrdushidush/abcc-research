# W3 — Orchestration core in Rust

**Status: IN PROGRESS — started 2026-08-19.** Built one item at a time in §13 format, same as W5.
The language is decided (Rust) and the engine is decided (copy Claudette's, both stay live — David,
2026-08-07), so this workstream is about **structure**: the typed lifecycle, durability, the control
channel, escalation lineage, and process topology.

Planned items, in the order §14 item 4 dictates:

1. ✅ **The typed lifecycle and the Q8 vocabulary** (F146–F152) — §14's named first deliverable,
   written 2026-08-19 from a fresh three-repo extraction. Corrects the record in two places: the
   Task lifecycle has **seven** states, not eleven, and v1 *had* a status type — it was decorative.
2. ☐ **What the family already provides** — the inheritance-map walk: Claudette's engine as the
   default answer, ABCC's four services as the concern list, BCF as reference.
3. ☐ **Durability** — a task must survive a crash, a reboot and a model-server hang. Custom state
   machine over a durable store versus what the ecosystem offers.
4. ☐ **The control channel and the broker** — where W5's `Allow | Deny | Redirect(String)` event
   lives with two subscribers (OQ-W5-3), select-at-every-boundary, arrival-time contract.
5. ☐ **Escalation lineage** — worker fails → verification fails → re-scoped by a stronger model →
   retried, with the whole lineage traceable.
6. ☐ **Rust ecosystem survey, live-verified** — async runtime (the tokio question), HTTP/SSE,
   persistence, serialization, queue crates; last-commit dates checked, not assumed.
7. ☐ **Process topology** — one binary or supervisor plus workers, and what that means for W7
   sandboxing and W10's protocol.

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
