# W3 — Orchestration core in Rust

**Status: IN PROGRESS — started 2026-08-19.** Built one item at a time in §13 format, same as W5.
The language is decided (Rust) and the engine is decided (copy Claudette's, both stay live — David,
2026-08-07), so this workstream is about **structure**: the typed lifecycle, durability, the control
channel, escalation lineage, and process topology.

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
| OQ-W3-13 | The idle-gap timeout value — what inter-token gap actually means "hung" on this hardware | W8 runs; F172 says the *mechanism* is missing regardless |
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
| OQ-W3-13 | Unchanged from item 3, and F184 sharpens it: the idle-gap timeout is what makes the cancel flag reachable when the server stops talking, so it is the same mechanism, not a separate feature | W8 runs |

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
