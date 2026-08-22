# W11 — Stage pipeline and unit roles

**Status: IN PROGRESS — started 2026-08-21**, the third leg of the W3 + W6 + W11 block (§14 item 4).
Built one item at a time in §13 format. W11 turns §10 into a spec and is the workstream §10 itself
names: *"Phase 0 must surface all three taxonomies side by side, and W11 must produce one. Do not
assume this table wins."* (`RESEARCH_BRIEF.md:529-531`).

Planned items:

1. ✅ **The reconciliation** (F225–F237) — v1's Coder/QA/CTO against BCF's nine stages against §10's
   four, with W6 item 2's four-phase starting taxonomy as the incoming position. Answered: the three
   are not three of the same thing, so the reconciliation separates the axes first and then produces
   **two levels** — Mission (Plan / Integrate / Accept) and Attempt (Localize / Change / Measure /
   Judge, plus Veto). §10's four unit names all survive, as **call-signs on phases that have
   construction sites**, and §10's table turns out to be missing the only stage that ever stopped
   anything in any of the three donors.
2. ✅ **The phase-to-tier mapping** (F238–F251) — backed by W1/W2's existing numbers and five probes
   run for it. Answered: the mapping is **four phases → one tier, three phases → no model**, and
   "tier" is the wrong axis. What varies per phase is a four-knob runtime profile, sorted by what a
   change costs: weights and window are frozen, and the head, the tool policy and the output budget
   are where a phase gets to differ. F79's swap cost turns out to be a floor — a swap also wipes the
   prompt cache — and the reasoning trace turns out to be an unbounded input to a bounded output
   budget, which is how a shipping donor's Judge returns an empty string with HTTP 200.
3. ☐ **Handoff artifact schemas as Rust types**, not conventions. Brief, diff, measurement set,
   verdict — each an event on W3's log.
4. ☐ **Gate independence** and how it survives single player mode. Overlaps W6 item 3 directly;
   whichever runs first owns the measurement, the other cites it.
5. ☐ **Loop budgets and circuit breakers per stage**, benchmarked against v1's existing behaviour.
   Inherits W6 F223 (the decline breaker that changed meaning) and W3 F195 (the retry budget).

Scope reference: `RESEARCH_BRIEF.md` §11 lines 949–960, against §10 lines 515–545. Findings continue
the family numbering — one sequence across all workstreams. **Item 1 took F225–F237 and item 2 took
F238–F251, so the next free number is F252.** Check the maximum before adding, not the last number
in this file
(`grep -rho "F[0-9]\{2,3\}" research/*.md | sort -u | sed 's/F//' | sort -n | tail -3`).

---

# Item 1 — the reconciliation

## Question

§10 ships a table of four stages and says, in the same breath, that it may not survive: *"V1 ships
three unit types (Coder, QA, CTO). BattleCommandForge reportedly runs nine pipeline stages. This
table has four. Phase 0 must surface all three taxonomies side by side, and W11 must produce one.
Do not assume this table wins."*

So: **what is the one taxonomy, and what does the evidence say about which of the three deserves to
be it?**

W6 item 2 already did half the job from the verification side and handed over a four-phase starting
position (Localize / Change / Measure / Judge, plus Veto and Decide). What it did *not* do is look
at v1's unit taxonomy in the code, or ask whether the three candidate taxonomies are even the same
kind of object. Both turn out to matter.

## Method

Fresh code extraction, 2026-08-21, from all three donors at their current HEADs:

- **ABCC v1** — `D:\dev\agent-battle-command-center` HEAD `d5528ea`. Primary pass; this is the donor
  whose taxonomy had never been read at the level of its call sites.
- **Claudette** — `D:\dev\claudette` HEAD `af3f804`, re-checked rather than cited from W6.
- **BattleCommandForge** — `D:\dev\battle-command-forge` HEAD `d6c1601`, one targeted check (stage 5).

Method note, per the standing rule (memory: *grep the readers, not the writers*): every taxonomy
claim below is checked at its **consumption** site, not its declaration. A role that is declared, a
column that is written, and an event that is emitted are all evidence of intent; only a reader is
evidence of a mechanism. Five of the thirteen findings exist because the declaration and the reader
disagreed. File:line cites are from this pass.

## Inherited

| What | Source | Verdict here |
|---|---|---|
| §10's four stages + four unit types + per-stage tier | `RESEARCH_BRIEF.md:517-524` | rows mostly survive, **columns do not** — the per-stage unit type is the defect (F225, F230) |
| W6 item 2's four phases (Localize / Change / Measure / Judge) + Veto + Decide | `research/W6-verification.md:618-658` | **adopted at the attempt level**, with Measure before Judge confirmed from the donor's own ordering (F235) |
| W3 item 1's entity split — Stage is W11's, Mission is W11's, not folded into `TaskState` | `research/W3-orchestration.md:346-354` | ratified, and now discharged: the Mission level is real, and its enum falls out (recommendation 7) |
| F215's rule — declare a role only where a construction site exists | W6 item 2 | ratified, and now quantified across all three donors (F230) |
| F218 — every gate input is `Measured(x) \| Uncertain(why)` | W6 item 2 | ratified, with one amendment: `Uncertain` must be *constructed*, never coalesced (F233) |
| Q8 — role naming goes into the Rust domain model, overriding Claudette's own principle | `RESEARCH_BRIEF.md:1255` | binding, and it is why this item is worth its length: enums make the answer sticky |
| v1's `validation_command` per subtask | `orchestrator.py:172-285` | **REUSE, promoted** — the family's only per-unit-of-work acceptance criterion that binds (F231, F236) |
| v1's "QA Engineer / Sentinel-9" review protocol | `agents/qa.py:7-30` | REUSE as a **prompt**, discard as a unit (F234) |

## Findings

### 🚨 F225 — the three taxonomies are three different axes, and §10 is the conflation rather than the reconciliation

This is the finding the rest of the item rests on, and it is visible the moment the three are put
side by side *as data structures* rather than as lists of names.

- **v1's taxonomy is a taxonomy of units.** `AgentType` is a database table (`schema.prisma:11`)
  seeded with exactly three rows — `coder`, `qa`, `cto` (`seed.ts:7,20,33`) — and exactly one agent
  instance per row: `coder-01`, `qa-01`, `cto-01` (`seed.ts:47,72,95`). It says *who exists*. It says
  nothing about ordering; no code path sequences a coder before a qa.
- **BCF's taxonomy is a taxonomy of stages.** W6 F214 established there is no `Vec<Stage>`, no stage
  trait and no table — nine straight-line calls in one 2,449-line file. It says *what happens when*.
  There is no unit concept at all: nothing in BCF has an identity, a status or a queue.
- **§10's table is both at once, per row.** Each row carries a stage, a unit type, a model tier, an
  output artifact and an exit gate. Four rows × five axes. That is not one taxonomy; it is five
  taxonomies indexed by a shared row number, which is exactly the failure mode W3 F146 named for the
  Task lifecycle ("eleven states was four vocabularies wearing one name") reappearing one level up.

The cost of the conflation is measurable in v1, which built it. The unit type is the routing key:
`taskRouter.ts:336` selects the agent whose `agentType.name` matches `task.requiredAgent`, and the
very next line pins the model tier off the same string —

```ts
modelTier = requiredAgentName === 'cto' ? 'opus' : requiredAgentName === 'qa' ? 'haiku' : 'ollama';
```

— `taskRouter.ts:340`. Unit type *is* model tier, resolved by a ternary on a name. Meanwhile the
field that was supposed to carry capability, `AgentType.capabilities` (`seed.ts:14,27,40`, e.g. the
CTO's `['review_code','assign_task','query_logs','escalate_task','make_decision']`), has **no
functional reader anywhere in the repo** — it appears in the seed, in the shared TypeScript
interface (`packages/shared/src/index.ts:34`), in three test fixtures as `[]`, and in one route that
builds its own unrelated object. No scheduler ever matches a task against it. The declared capability
model is inert; the operative one is a string comparison on a name.

**For 2.0:** the reconciliation cannot be "pick one of the three", because they answer different
questions. It has to name the axes and answer each separately. Four are needed: **when** (phase),
**who** (unit), **what came out** (artifact), **what may stop it** (gate). §10's table conflates the
first two, and F230 shows what that costs.

### 🚨 F226 — the pipeline is two-level, and §10's Architecture row is at the wrong level

v1 documents its own pipeline at the top of the service that runs it (`orchestratorService.ts:1-13`):

```
 *   1. Create Mission record
 *   2. POST agents:8000/orchestrate/decompose (Sonnet)
 *   3. Create Task records per subtask (linked via missionId)
 *   4. Sequential execution: route → assign → execute → auto-retry per subtask
 *   5. POST agents:8000/orchestrate/review (Sonnet)
 *   6. Status → awaiting_approval (or auto-approve)
```

Steps 2 and 5 are **mission**-level: one call each, for the whole mission. Step 4 is a loop over
**tasks**. The Python side says the same thing in one line — *"Called exactly twice per mission: once
to decompose, once to review"* (`orchestrator.py:9`).

That structural fact settles where §10's second row belongs. **Decomposition does not hand an
artifact to the next stage of the same task; it produces the tasks.** Its output is `Task` rows
(`orchestratorService.ts:160-175`), not a context pack for a downstream stage. A stage list that puts
"Architecture" between "Research" and "Coding" implies all three operate on one entity, and none of
the three donors does that.

The other two donors confirm it by absence: BCF and Claudette have **no mission level at all**. One
invocation, one unit of work, one pipeline — which is precisely why W6 item 2's four phases are all
attempt-level and why nothing in them corresponds to §10's Architecture row. The gap was not an
oversight in W6; it is a level boundary.

Two details worth carrying, both from v1's decomposer:

- **It is capped twice, and the second cap is silent.** The prompt says "Maximum 5 subtasks"
  (`orchestrator.py:43`); the code truncates at 7 with a `print` and no error
  (`orchestrator.py:218-221`). A mission that genuinely needed nine units of work silently becomes a
  mission of seven, and the review at step 5 grades the seven against the original request.
- **It is greenfield-shaped, and says so.** Every subtask must be "ONE file with ONE function, ONE
  class, or ONE complete page/component", paths must be flat under `tasks/`, and the reason given is
  *"The coder agent cannot create nested directories"* (`orchestrator.py:43-50`). W6 F214 found six
  of BCF's nine stages exist to compensate for having no repository; v1's decomposer goes further and
  *forbids* repository structure. 2.0's answered target workload is repository work
  (`RESEARCH_BRIEF.md:1264-1270`), so the mission-level Plan phase is a **new** construction, not a
  port — only its two-level shape is inherited.

### F227 — v1's mission stages are hiding inside its mission status column, and a failure erases which one

`Mission.status` is a `VarChar(30)` (`schema.prisma:294`) and takes seven values across the service:
`decomposing` (`:96`), `executing` (`:138`), `reviewing` (`:295`), `awaiting_approval` (`:345`),
`approved` (`:564`), `failed` (`:362`), `aborted` (`:626`).

The first four are not states in W3's sense — they are **stages**. They say where in the pipeline the
mission is, not what it is waiting on or what resources it holds. The last three are states. One
column, two vocabularies: W3 F146's exact diagnosis, found one level above the entity F146 was about.

The concrete cost: when a mission fails, `status` becomes `failed` and `error` gets a string
(`orchestratorService.ts:359-365`). There is no `failedStage` column and no per-stage record, so
**which stage failed is unrecoverable from the row**. Whether the decomposer returned prose instead
of JSON, whether a subtask exhausted its retries, or whether the reviewer timed out — all three land
as the same terminal value, distinguishable only by parsing free text.

**For 2.0:** the fix is already built. With W3's event log, the stage is a *projection* — the last
stage event before the terminal one — and needs no column at all. `MissionState` stays small and
lifecycle-shaped; the stage is derived. This is the same "status as a projection" ruling W3 item 1
made for tasks (`W3-orchestration.md:400-411`), applied to the entity W3 explicitly deferred to W11.

### 🚨 F228 — three unit types, one that ever receives work

On every automated path in v1, `requiredAgent` is null.

- Mission tasks are created with `taskType: 'code'` and `validationCommand`, and **no
  `requiredAgent`** (`orchestratorService.ts:160-175`).
- The only sites that set it are the manual "Create Task" modal in the UI
  (`CreateTaskModal.tsx:29`) and the task-planning route (`task-planning.ts:219`).
- With `requiredAgent` null, `taskRouter` skips the override branch (`:334`) and falls through the
  complexity ladder, whose every rung selects `agentType.name === 'coder'` (`:360`, `:376`, `:421`).

So the coder unit does all the work, and the two other units' *functions* are performed by code that
never touches the agent table at all:

| Named unit | What its name promises | Who actually does it | Touches `Agent`? |
|---|---|---|---|
| `cto-01` (Opus) | decompose, review | `orchestrator.py` — a stateless `anthropic.Anthropic` client at Sonnet (`:19-21`), called over HTTP by `orchestratorService` | no |
| `qa-01` (Haiku) | review, verdict | `codeReviewService.triggerSentinelReview` — a direct `this.anthropic.messages.create` at Haiku (`:293-303`) | no |
| `coder-01` (Ollama) | write code | itself | yes |

And the CTO's one real construction site is unreachable from the product. `/api/task-planning` is
mounted (`packages/api/src/index.ts:170`) and fully built — decompose via the CrewAI CTO agent with
`create_subtask` / `complete_decomposition` tools (`agents/base.py:60-64`), list subtasks, execute
subtasks — but grepping the whole repo for callers finds only `docs/API.md`, `CHANGELOG.md`,
`CLAUDE.md`, and four `scripts/*-test.js` stress-test scripts. No UI, no service. v1 has **two
complete decomposition mechanisms**, and the one built out of its unit taxonomy is the one nothing
calls.

**For 2.0:** "reconcile v1's Coder/QA/CTO" has a shorter answer than expected — there is one working
unit type and two names. Any reconciliation that treats the three as three peers is reconciling
against a fiction.

### 🚨 F229 — the unit type is a scheduling token, not a role, and the empty-pool path proves it

Two paths in `taskRouter.routeTask` use a unit type for something that has nothing to do with what
that unit is:

1. **The QA slot runs Sonnet decomposition.** At `complexity >= 10` the router selects
   `agentType.name === 'qa'` and sets `modelTier = 'sonnet'` (`:392-400`, and again in the fallback
   at `:406-418`, which throws rather than substitute another unit). The qa agent's seeded
   `preferredModel` is `claude-haiku-4-5-20251001` (`seed.ts:81`) and its persona is a QA reviewer.
   Neither is used. The unit is being used as a **slot**, and the slot's declared identity is
   overridden by the caller.
2. **An empty pool becomes a hard task.** If no agent is idle, the router returns the CTO with
   `modelTier: 'opus'`, `estimatedCost: 0.04`, and — literally — `complexity: 10, // High complexity
   if no agents available` (`:262-284`). Resource exhaustion is written into the field that means
   task difficulty, and then billed at the most expensive tier available. The CTO is fetched with
   `findFirst` and **no idle filter** (`:263-271`), so the "no agent is free" path routes to a unit it
   never checks is free; the caller then blocks on `waitForAgent(agentId, 120_000)`
   (`orchestratorService.ts:402-407`).

So one number carries three meanings — task difficulty, "this needs decomposing", and "the pool is
empty" — and the routing decision reads it as the first. This is the cousin of W6 F221 (the
complexity router as a one-way ratchet) with the ratchet pointing the other way: toward the *most*
expensive tier, on the least informative signal.

**For 2.0:** this is the argument for the axis split in F225, in its most concrete form. If unit and
role are the same thing, then "no free unit" and "hard problem" become the same event, because both
are answered by picking a different unit. Separate them and the empty-pool case has an obvious
honest answer — the task stays `Queued`, which W3's lifecycle already provides for free.

### F230 — the declared-to-constructed inflation is about 3× in every donor, and §10 proposes a fourth

Counted the same way in each donor: a role/unit/stage name is **declared** if it exists in a type, a
table, a config map or a spec table, and **constructed** if a running product path builds something
that behaves differently because of it.

| Donor | Declared | Constructed on the product path | Ratio | Evidence |
|---|---|---|---|---|
| ABCC v1 | 3 unit types (`seed.ts:7,20,33`; zod enum `tasks.ts:14`) | **1** (`coder`) | 3.0× | F228 |
| Claudette | 8 `forge::types::Role` variants (`forge/types.rs:18-35`) | **3** (`Planner` `forge_run.rs:1260`, `Verifier` `:1285`, `Coder` `runtime_build.rs:225`) | 2.7× | re-verified this pass; `Router`, `TestCoder`, `SurgicalCoder`, `Cto` appear only in the model map, the persona parser and an example |
| BattleCommandForge | 9 stages (banners `mission.rs:262-1141`) | **3** phases | 3.0× | W6 F214 |
| §10 as written | 4 unit types | 0 (it is a spec) | — | `RESEARCH_BRIEF.md:517-524` |

Re-checkable in one line each; the Claudette count is the sharpest because the enum is exhaustive:

```sh
rg -n "Role::(Router|TestCoder|SurgicalCoder|Cto)\b" --type rust \
  | rg -v "personas.rs|models_toml.rs|types.rs|examples/"     # → no hits
```

The consistency is the finding. Three independent codebases, three different languages, three
different authors' intentions, and each ends up with roughly a third of its declared vocabulary
actually built. The mechanism is the same each time and it is cheap to see: **declaring a role costs
one line in an enum or one row in a table; constructing one costs a prompt, a tool policy, a model
choice, a call site, and a reason for the call site to exist.** Vocabularies grow at the cost of the
first and are paid for at the cost of the second.

Claudette's own `Role` doc comment states the principle that makes this safe — *"role naming is about
what the model is doing, not about which weights are loaded"* (`forge/types.rs:14-16`) — and Q8
**deliberately overrides it** for 2.0 (`RESEARCH_BRIEF.md:1255`): the RTS framing goes into the Rust
domain model. That override is why this finding is load-bearing rather than a style note. In
Claudette an over-declared role is a dead enum variant; in 2.0 it is a unit type on the battlefield,
a sidebar entry, a voice line and an exhaustive `match` arm in the renderer, the scheduler and the
event log.

**For 2.0:** F215's rule stands and gets a second clause. Declare a role only where a construction
site exists — and where the spec proposes a role that does not exist yet, it is a **construction
site to be built**, named in the plan with its cost, not a name to be shipped in an enum first.

### 🚨 F231 — v1's only binding gate is a shell command, and it reports pass when it is absent

Three things in v1 produce a verdict on work. Exactly one of them can change an outcome.

**Binding: `validationCommand`.** `AutoRetryService.validateAndRetry` runs the task's command and
sets `status: validated ? 'completed' : 'failed'` (`orchestratorService.ts:453-470`). It is
deterministic, it is per-task, and it is the only thing in v1 that can fail a unit of work.

**Not binding, by explicit design: the sentinel review.** After validation passes, a Haiku review
runs, and the code says what happens with the result (`orchestratorService.ts:483-503`):

```ts
// Note: we don't fail the subtask — Sentinel failure is informational
// The CTO review at the end will catch critical issues
```

Both halves are worth checking, and the second is false:

- The event it emits, `mission_sentinel_failed`, occurs **exactly once in the repo** — at the emit
  (`orchestratorService.ts:491`). No UI subscriber, no service, no handler.
- The CTO review it defers to never receives its findings. `SubtaskResult` carries `title`,
  `file_name`, `validation_passed`, `code`, `error` (`orchestratorService.ts:47-53`), and
  `reviewMission` posts exactly that array (`:838-842`). The sentinel's score, verdict and findings
  are written to the `CodeReview` table (`codeReviewService.ts:314-328`) and read by nothing on this
  path.

**Not binding, by configuration: the mission review.** `review.approved` and `review.score` are
computed and stored; a repo-wide grep for `.approved` finds one write and no gate. And on the
programmatic path the comment is explicit (`orchestratorService.ts:337-339`): *"autoApprove=true
means API/programmatic callers — approve regardless of review score (no chat to manually approve
in). Review is informational."* `approveMission` runs no check of any kind (`:558-586`).

And then the sting, in the one gate that binds (`autoRetryService.ts:81-84`):

```ts
if (!task || !task.validationCommand) {
  return { validated: true, phase: 'skipped', attempts: 0 };
}
```

**No acceptance criterion means validated.** `validationCommand` is `String?` in the schema
(`schema.prisma:70`) and `.optional()` in the create route (`tasks.ts:22`), so this is reachable from
every path except the decomposer, which requires the field (`orchestrator.py:224-228`). The same
early return fires when `AUTO_RETRY_ENABLED` is false (`:77-79`).

**For 2.0:** this is convergent evidence for W6's Measure/Judge split, arrived at independently by a
third codebase — the thing that can stop work is deterministic, and every model verdict in the same
system drifted to advisory. It also supplies the rule F218 was missing: **absent is not pass.** A
missing measurement is `Uncertain`, and `Uncertain` loses every comparison it enters.

### 🚨 F232 — the judge reads the model's narration, not the artifact

What the mission reviewer grades as "the code" is assembled by `readGeneratedCode`
(`orchestratorService.ts:865-883`):

```ts
const logs = await this.prisma.executionLog.findMany({
  where: { taskId, action: { in: ['file_write', 'write_file'] } },
  orderBy: { timestamp: 'desc' },
  take: 1,
});
...
return (actionInput.content || actionInput.code) as string | null;
```

Nothing here touches the filesystem. Three consequences, in increasing order of severity:

1. **`take: 1`.** A subtask that wrote two files is reviewed on one of them.
2. **`file_edit` never matches.** The coder's tool set is
   `[file_read, file_write, file_edit, file_list, shell_run, code_search, find_file]`
   (`agents/base.py:58`), and `FileEditTool.name` is `"file_edit"` (`tools/file_ops.py:93`) — not in
   the filter. A task completed by editing returns `code: null`, and the reviewer scores a subtask
   whose code it never saw. The review prompt is even written to accommodate it: *"code (if
   available)"* (`orchestrator.py:294`).
3. **Some `ExecutionLog` rows are scraped from the model's own prose.** Besides the accurate
   tool-wrapper path (`main.py:318`), `parse_and_log_output` regex-matches
   `Thought:/Action:/Action Input:/Observation:` out of captured CrewAI stdout and writes rows with
   `action` and `actionInput` taken from that text (`execution_logger.py:42-103`, called at
   `main.py:396`). When the narration parses as JSON, `actionInput.content` is **what the model said
   it wrote**.

So the family's most expensive verdict is rendered over a projection of a transcript, one write deep,
blind to edits, and reachable by narration. W6 F217 found both donors judge blind to their own tests;
this is the same failure one step earlier — a judge blind to the artifact itself.

**For 2.0:** the Judge phase reads the **artifact**, from the workspace, at the `seq` it is judging —
the diff from git at the attempt level, the tree at the mission level. Never a log projection. W3
item 3's log already makes "at which `seq`" expressible, and item 3 also flagged the log and the
workspace as two stores with no shared transaction (F173); this is what that gap costs when a gate
tries to bridge it by reading the wrong one.

### 🚨 F233 — `result.score || 5`: the sentinel scores a zero as a five

`triggerSentinelReview` persists its result like this (`codeReviewService.ts:319-322`):

```ts
initialComplexity: task.complexity || 5,
findings: (result.findings || []) as unknown as undefined,
summary: result.summary || '',
codeQualityScore: result.score || 5,
```

`||` in JavaScript coalesces on falsiness, not on absence. A model that returns `"score": 0` — the
strongest signal a reviewer can send — has it rewritten to **5**, the midpoint, before it reaches the
database. Same for `complexity: 0`.

This is F161's disease in its third and worst form. F161 (v1's parse-failure-defaults-to-success) and
F158 (BCF's verifier scoring a correct and a broken file identically) both *invent* a measurement
where none was taken. This one **destroys a measurement that was taken** and replaces it with the
number that looks most like an ordinary result. W6's "Effect on fun" section wrote that "a unit
reporting 5.0 because nobody looked is the scripted win §7 calls boring" — that sentence was written
about a hypothetical, and here is the line that does it.

**For 2.0:** F218's `Measured(x) | Uncertain(why)` needs one more clause to be safe in Rust, because
Rust has the same trap in politer clothing. `unwrap_or(5)`, `unwrap_or_default()` and
`.unwrap_or_else(|| mid)` on a gate input are this bug. **`Uncertain` must be constructed
explicitly, at the site that knows why**, and a gate input type must have no `Default` impl. A
missing value is a branch, never a fallback.

### F234 — the best reviewer in the family is a prompt with no caller

v1's QA agent persona (`agents/qa.py:7-30`) is "Sentinel-9", callsign "Watchdog", and its review
protocol is this, verbatim:

> 1. **READ REQUIREMENTS** — Understand what was asked (task title + description)
> 2. **READ CODE** — Use file_read to inspect the generated file(s) in tasks/
> 3. **RUN VALIDATION** — Use shell_run to execute the validation command
> 4. **CHECK EDGE CASES** — Verify: empty inputs, boundaries, type mismatches, off-by-one
> 5. **ISSUE VERDICT** — Structured JSON with PASS or FAIL + defects + confidence
>
> Never skip steps. Never guess what the code does — always read it. Never assume validation passes —
> always run it.

That is **Measure-before-Judge**, written out in full, with the two failure modes of F232 and F231
named as prohibitions, in the donor that predates both other repos. Its tool set includes
`validate_syntax` and `shell_run` (`agents/base.py:59`), so it can actually do steps 2 and 3.

It is unreachable from the mission pipeline. `create_qa_agent` is called only from `get_agent`
(`main.py:192`), which is called only by `/execute` with an `agent_id` matching `qa`, which requires
a task assigned to `qa-01`, which requires `requiredAgent: 'qa'`, which no automated path sets
(F228). What ships in its place is a 500-token Haiku call with no tools, over the log-scraped blob of
F232, that cannot read the file and cannot run the validation — and whose zero becomes a five (F233).

**For 2.0:** carry the protocol into the Judge phase's prompt and let the unit go. This is the
cleanest possible illustration of the axis split in F225: the *role* was right, the *unit* was the
thing that made it unreachable, and separating them recovers the good half.

### 🚨 F235 — §10's table is missing the only stage that ever stopped anything

Put the three donors' deterministic measurement side by side:

| Donor | Where measurement runs | What it produces | Can it stop the work? |
|---|---|---|---|
| ABCC v1 | per task, after execution — `runValidation(validationCmd)` (`autoRetryService.ts:92`) | pass/fail of one shell command | **yes** — sets `completed`/`failed` (F231) |
| BCF | stage 5 of 9, per round — `verifier::verify_project` = ruff + pytest over the output dir (`mission.rs:994-1006`) | **a score out of 10** (`avg_score`) | only by moving an average, which the 0.4/0.6 formula can dilute (W6 F159) |
| Claudette | per round, after the LLM Verifier — `run_build_and_tests` on the mission tree (`forge_run.rs:719-724`) | tri-state `build_ok`/`tests_ok: Option<bool>` + summary (`tools/quality.rs:317-332`) | **yes** — `is_hard_fail()` forces `pass=false, score=0` (`forge_run.rs:731-736`) |
| **§10 as written** | — | — | — |

§10's four rows are Research, Architecture, Coding, Gate. Its Gate row is *"Adversarial verification:
break it, review it, probe it"* staffed by Commandos — a model. There is no row for running the
project's build and tests. The one stage that binds in two of three donors, and that the third at
least runs, is absent from the table that is supposed to be the organizing principle for the console.

Two details fall out of the same comparison:

- **The measurement runs after the judge, in the donor 2.0 is built on.** In Claudette the LLM
  Verifier is called at `forge_run.rs:666-668`, and `run_build_and_tests` at `:719-724` — *after* —
  and its only effect is to overwrite `verifier.pass` and `verifier.score`
  (`:731-736`). Same for the security scan at `:755-780`. So the judge writes an opinion, and the
  facts arrive afterwards and cross it out. W6 recommendation 2 said to reorder this; the ordering is
  now confirmed from the code rather than inferred, and the fix is still one prompt field.
- **"Verifier" means opposite things in the two Rust donors.** In BCF, VERIFIER is the deterministic
  stage — ruff and pytest, no model (`mission.rs:996` emits the stage label `"ruff+pytest"`). In
  Claudette, `Role::Verifier` is the LLM judge, constructed with **no tool groups**
  (`forge_run.rs:1285`), whose doc comment reads "Correctness grading". The successor kept the word
  and swapped its referent, which is how the same name ends up meaning both "the only thing here that
  is not an opinion" and "the opinion". Any reconciliation that inherits the word inherits the
  ambiguity.

**For 2.0:** Measure is a phase, it is named, it has no model, and it is not called Verifier.

### F236 — acceptance criteria exist twice in v1: one prose with no reader, one executable that is the gate

§10's Architecture row promises "Task DAG with per-task acceptance criteria". v1 built that column
twice.

- `Task.acceptanceCriteria` — `String? @db.Text` (`schema.prisma:68`), accepted by the create route
  (`tasks.ts:20`) and written (`tasks.ts:117`). A repo-wide grep finds **no reader**: it is in no
  prompt, no gate, no report. Three test fixtures set it to `null`.
- `Task.validationCommand` — `String? @db.Text` (`schema.prisma:70`), generated per subtask by the
  decomposer with a whole page of prompt rules and four auto-repair passes to keep it pointing at the
  right file (`orchestrator.py:223-284`), and executed by the one binding gate (F231).

The prose field is what a human would write; the executable field is what ever mattered. And the
decomposer's auto-repairs are worth noting for what they imply — the model gets the file/command
correspondence wrong often enough that v1 wrote regex fixers for Python imports, JS requires and
`os.path.exists` paths, each with a `print` announcing the correction. That is a real, load-bearing
piece of engineering hiding in a donor otherwise short of them.

The same disease is visible in the type field. `taskType` exists as three separate `VarChar(50)`
columns in one schema — `Task` (`:51`), `TrainingDataset` (`:249`), `TaskMemory` (`:321`) — with two
different value vocabularies: the zod enum `['code','test','review','debug','refactor',
'decomposition']` (`tasks.ts:13`) and the schema comment's `// file_creation, bug_fix, refactor,
test, etc.` (`:321`). No shared enum, no foreign key. Its only functional reader is a **cost report**
that groups spend by type (`cost-metrics.ts:132-163`). Nothing routes on it, nothing selects a prompt
with it — and mission tasks hardcode it to `'code'` anyway (`orchestratorService.ts:166`).

**For 2.0:** one acceptance criterion per unit of work, and it is **executable or it does not exist**.
Prose belongs in the brief, where the Change phase will actually read it. A criterion that no gate
can run is a comment with a database column.

### F237 — BCF's one piece of evidence against a Plan phase is greenfield-specific, and it left a voice line behind

This is the finding that had to be checked before recommending a mission-level Plan phase, because it
is the only thing in the family that argues the other way: BCF **built decomposition and removed it**.
The reason is in the code, at the site where the call used to be (`mission.rs:361-362`):

```rust
// Run as single task — multi-file extraction handles project structure.
// Decomposition caused duplicate projects; single-task + good prompts is better.
```

and twice in its own docs — *"No subtask decomposition — removed because it caused duplicate project
structures"* (`CLAUDE.md:231`), listed as design decision 3 of 6 (`CLAUDE.md:353`).

**The failure mode does not transfer.** "Duplicate project structures" is what happens when N
subtasks each generate a project from scratch: every one scaffolds its own `src/`, its own config,
its own entry point, and the union is a project three times over. That failure requires the project
structure to be an *output*. In repository work it is an *input* — it already exists, no phase
generates it, and two tasks editing two files cannot duplicate it. This is the same greenfield/
repository asymmetry F213 found behind six of BCF's nine stages and F226 found in v1's decomposer
(flat files under `tasks/`, no nested directories), pointing the same way for the third time.

So the evidence against decomposition is evidence against **greenfield** decomposition, and v1 —
the only donor whose decomposition survived — is also the only donor that ran the mission level at
all. BCF's revert is not a counter-example to M1 Plan; it is a constraint on what M1 may emit: **task
sets over an existing tree, never task sets that each construct a tree.**

The residue is worth one line, because W5's console inherits it. `voice::decomposed(count)` — *"Mission
decomposed into {} subtasks."* — is still in `voice.rs:68-71` with **zero callers**, an audio asset
announcing a feature that was deleted. F230's inflation, in the one medium where an unbuilt name is
still audible.

## Options compared

Scored against: does it survive the code evidence (F225–F237), does it fit one GPU (W1 F79's 23.77 s
swap, W2 F83's N=2), does every name have a construction site (F230), and does the console get an
honest cast (W5 F98/F106).

| Option | What the taxonomy becomes | Cost | Verdict |
|---|---|---|---|
| **A.** Adopt §10's table as written — four stages, each with its own unit type and tier | 4 unit types, 4 tiers, 4 exit gates | rebuilds F225's conflation and F229's consequence; 4 units on a box that saturates at 2 (W2 F83); no Measure row (F235); 4 declared / 0 constructed (F230) | rejected |
| **B.** Adopt v1's unit taxonomy (Coder / QA / CTO) as the organizing principle | 3 units, no stage list | it is a fiction — 1 constructed of 3 (F228), and it has no ordering to offer at all (F225) | rejected |
| **C.** Adopt BCF's nine stages | 9 stages | already rejected in W6 item 2 for independent reasons (F214, F222) | rejected |
| **D.** One flat list across both levels — Plan, Localize, Change, Measure, Judge, Integrate, Accept | 7 phases, one sequence | reproduces §10's error in a longer form: Plan operates on the *mission* and Localize on a *task*, so a flat list makes a level boundary look like a stage boundary, and every per-attempt retry appears to re-run Plan | rejected |
| **E. Separate the four axes, then two levels: Mission (Plan / Integrate / Accept) and Attempt (Localize / Change / Measure / Judge, plus Veto)** — §10's four unit names kept as call-signs on phases that have construction sites | 3 + 4 phases, 2 gate kinds, units as runtime slots | one new construction (mission-level Integrate, F226); one measurement owed (its cost on this box) | **recommended** |

## Recommendation

### 1. The one taxonomy

Four axes, named separately, per F225. Two of them are the taxonomy proper; the other two are what
§10 was carrying in the same table.

**Axis 1 — Phase: when, at which level.** Seven phases across two levels. Three run no model.

**Mission level** — the operator's unit of intent, and the level §10's Architecture row belongs to:

| # | Phase | Kind | Call-sign | Output artifact | Absorbs |
|---|---|---|---|---|---|
| M1 | **Plan** | model, read-only tools, once per mission | **Engineering** | the task set, each with **one executable acceptance criterion**, over an existing tree (F237) | §10 Architecture; v1 `decompose_prompt`; BCF ROUTER's complexity tag |
| — | *(the task set runs — axis 1, attempt level)* | | | | |
| M2 | **Integrate** | **no model** — build + test the assembled workspace | *(instrument — no unit)* | `Measured \| Uncertain` per check | BCF `verify_project` over the whole output dir; Claudette `run_build_and_tests` over the mission tree; **absent in v1** (F235) |
| M3 | **Accept** | human by default; a rung on W3's ladder when unattended | the operator | ship / don't, with reasons | v1 `awaiting_approval` + `approveMission`; W6's Decide |

**Attempt level** — one pass at one task. W6 item 2's four, with Measure moved ahead of Judge (F235):

| # | Phase | Kind | Call-sign | Output artifact | Absorbs |
|---|---|---|---|---|---|
| A1 | **Localize** | model, read-only tools, output is a grounded brief | **Recon** | brief | §10 Research; BCF ARCHITECT; Claudette Planner |
| A2 | **Change** | model, full tools, commits; the fix round is *this phase with different feedback* | **Builders** | diff | §10 Coding; BCF CODER + SurgicalCoder; Claudette Coder |
| A3 | **Measure** | **no model** — build, typecheck, the project's real suite, the acceptance criterion, the diff scanner | *(instrument — no unit)* | `Measured(x) \| Uncertain(why)` per input | v1 `validationCommand`; BCF stage 5; Claudette's build/test gate + security scan |
| A4 | **Judge** | **one** model call, no tools, sees the brief, the diff **and A3's measurements** | **Commandos** | verdict + defect list | §10 Gate; BCF CRITIQUE + CTO; Claudette Verifier; **v1's Sentinel-9 protocol as the prompt** (F234) |

plus one thing that is not a phase at either level:

- **Veto** — deterministic, non-scoring refusals evaluated after Judge, at whichever level they arise:
  security HIGH, empty diff, build break, a required measurement that came back `Uncertain`. A veto is
  never a weight (W6 F217).

**Axis 2 — Unit: who.** A unit is a **runtime slot with a resident model and a tool policy**. It is
not a stage and it is not a role. The number of units is set by VRAM and measured concurrency
(W2 F83: saturation at N=2), never by the length of the phase list. A phase is the role a slot plays
for one call; one slot plays every phase in turn on this hardware.

**Axis 3 — Artifact: what came out.** Brief, task set, diff, measurement set, verdict. Each is an
event on W3's log, addressed by `seq`, and each is read from its source of truth: the Judge reads the
diff from git and the tree from the workspace, never a projection of a transcript (F232). Schemas are
item 3.

**Axis 4 — Gate: what may stop it.** Two kinds only, matching W6's ruling: a **measurement** (A3, M2)
which is tri-state and can force a fail, and a **veto** which is boolean and non-scoring. A model
verdict is an input to a decision, never a gate by itself — which is what all three donors converged
on in practice even where their docs said otherwise (F231).

### 2. Units are slots, not stages — and that is the whole of §10's correction

§10's per-stage unit type is the one thing in the table that the evidence refuses. v1 built it, and
the result was: the capability model went unread (F225), the tier collapsed into a ternary on a name
(F225), two of three units never received work (F228), and the unit type became a scheduling token
carrying resource exhaustion in a complexity field (F229). On a box that saturates at N=2, four unit
types means the console shows four portraits of which at most two can ever be lit.

Slots also make the swap cost visible where it actually lands. A phase transition that changes tier
costs a model swap (W1 F79: 23.77 s round trip); a phase transition that does not, costs nothing.
**A3 and M2 have no tier at all**, which means the pipeline's two most decisive phases are free of
the arithmetic that shapes everything else. Item 2 inherits that as its starting condition.

### 3. §10's four names all survive — as call-signs on phases

Not one of §10's unit names is discarded, which is the part worth noticing: the table's *names* were
good and its *columns* were the problem.

- **Engineering** → M1 Plan (decompose and sequence — which is what §10 said Engineering does)
- **Recon** → A1 Localize
- **Builders** → A2 Change
- **Commandos** → A4 Judge

**Measure has no call-sign because it has no model.** It is the instrument, not a unit — and W6
already argued it is the most watchable thing on the field precisely because its outcome is not
anyone's opinion. Declaring a fifth unit type to staff it would be F230's mistake committed on
purpose.

No other role name enters the domain model. `Router` is a routing decision, which is data on the
event log (W6 F221). `Tester` is an artifact, and only if it is immutable to A2 (W6 F216). `QA` is
A4's prompt (F234). `CTO` is a person, or a rung on W3's ladder (W6 F217). `SurgicalCoder` is a
prompt variant of A2. Each of these becomes a name again only when someone builds its construction
site — and when they do, F230's second clause applies: it is named in the plan with its cost, not
added to an enum first.

David ratifies the words (OQ-W3-6, still open): the mechanism is W11's, the personality is his.

### 4. Where the mission-level judgement went

v1 has a mission-level model review; W6's four phases have nothing at that level. The reconciliation
does not simply delete it, because the *function* is real and neither Rust donor has it: per-task
judges cannot see whether five separately-validated files work together.

The ruling is that the function survives and the implementation does not. **M2 Integrate is a
measurement, not an opinion** — build and test the assembled workspace, exactly as both Rust donors
already do per round, which v1 never did at all (it validated each file's own command and shipped on
a model's summary, `approveMission` running no check whatsoever, `orchestratorService.ts:558-586`).
If a mission-level model opinion is wanted later, it is an input to M3 Accept, it reads artifacts,
and it is optional. The evidence pack M3 decides on is assembled from what is already on the log —
W3 item 5's six queries answer it without a fresh call.

### 5. Acceptance criteria are executable, or they do not exist

One criterion per task, produced by M1, carried on the task, executed in A3 (F236). Prose belongs in
the brief, where A2 will read it. Every criterion returns `Measured(x) | Uncertain(why)` (F218),
`Uncertain` loses every comparison it enters, and — the clause F231 forces — **absent is not pass**.
A task with no runnable criterion is `Uncertain`, and a mission of `Uncertain` tasks does not reach
M3 clean.

Two things to port rather than reinvent when item 3 writes the schemas: v1's per-language criterion
templates and its four auto-repair passes that keep the command pointing at the file it is supposed
to test (`orchestrator.py:223-284`). Those exist because the model gets it wrong often enough to
warrant them.

### 6. `Uncertain` is constructed, never coalesced

F233's rule, stated so it survives the port to Rust: a gate-input type has **no `Default` impl**, and
`unwrap_or`, `unwrap_or_default` and `unwrap_or_else` on one are the same bug as `result.score || 5`.
Every `Uncertain` is built at the site that knows why, and carries the why. A missing value is a
branch, never a fallback.

### 7. What this hands to W3, and to the rest of W11

**To W3 item 1**, whose entity table left two rows to W11:

- **Stage** is now defined, at two levels, and stays out of `TaskState` as W3 required.
- **Mission** gets its enum, and F227 says what shape it is: lifecycle only, stage derived from the
  log. Proposed for ratification alongside `TaskState`:

  ```rust
  pub enum MissionState {
      Planning      { since: Seq },
      Executing     { since: Seq },                 // stage = projection of the log, not a column
      Integrating   { since: Seq },
      AwaitingDecision { prompt: PromptId, since: Seq },
      Accepted      { at: Seq },
      Rejected      { at: Seq },
      Aborted       { reason: AbortReason, since: Seq },
  }
  ```

  Same three rules as `TaskState`: every variant carries its evidence, every variant gets a row in a
  per-state contract table, and terminal ⇒ zero resources.

**To W11 item 2:** the mapping is phase→tier, not unit→tier, and two of the seven phases need no
tier. The swap arithmetic only binds on M1→A1→A2→A4.

**To W11 item 3:** five artifacts to type — brief, task set (with criteria), diff, measurement set,
verdict — each as a log event.

**To W11 item 4 / W6 item 3:** the independence question is now precisely stated. A4 is one model
call with no tools that reads A3's output; the open question is whether the same weights that ran A2
can fill that slot, and W8 already measures the inflation at +3.65 median over 34 missions.

## Rejected alternatives and why

- **Keeping §10's per-stage unit types.** Covered above and in F229; the empty-pool path is the
  short version of the argument. It is worth saying plainly that this is the single substantive
  change the reconciliation makes to §10 — the rows are largely right, one row is missing, and the
  unit column is the defect.
- **A flat seven-phase list (option D).** The retry story kills it: at the attempt level a failed
  attempt re-enters A1 or A2, and in a flat list that reads as re-running Plan. Level boundaries and
  stage boundaries are different kinds of edge and the console has to draw them differently.
- **Dropping the mission level and letting tasks be the only entity** (BCF's and Claudette's shape).
  It would simplify the port, and it would throw away the one thing v1 got structurally right
  (F226). §10's own justification for the stage list is that "the operator should see where the front
  line is" — the front line is a mission with N tasks on it, not one task.
- **Following BCF and deleting decomposition**, which is the strongest inherited argument against M1
  and the reason F237 exists. Checked rather than assumed: BCF's stated cause is *"duplicate project
  structures"* (`mission.rs:361-362`, `CLAUDE.md:231`), a failure that requires the project structure
  to be generated output. On 2.0's answered workload it is input, and the failure cannot occur. The
  revert constrains what M1 emits; it does not remove the phase.
- **Reviving QA as a unit type** because its persona is the best in the family. F234 is the argument
  for carrying the *prompt*; making it a unit again is what made it unreachable.
- **Naming the measurement phase "Verifier"** for continuity with both Rust donors. F235: the word
  means opposite things in the two of them, and 2.0 would inherit the ambiguity along with the
  familiarity.

## Effect on fun

Four call-signs, and every one of them exists. That is the difference between this table and §10's,
and between this table and the nine-unit sidebar W6 rejected: **Recon, Builders, Commandos and
Engineering each have a construction site**, so when the console lights one up, something is actually
happening behind it. F230's 3× inflation is what a battlefield of ghosts looks like from the inside —
eight roles declared and three doing anything, a QA unit with a callsign and a motto that no code
path can reach.

The unit-as-slot ruling changes what the screen shows and improves it. Four stage-shaped portraits on
a two-slot machine means two of them are permanently greyed out — a roster, not a battle. Two slots
rotating through phases means both are always doing something, and the interesting question becomes
*which phase* each is in, which is the question §10 actually wanted the console to answer.

And the missing stage is the dramatic one. A3 and M2 are where the outcome stops being anyone's
opinion: tests passed, tests failed, build broken, criterion met. They are fast, they produce real
numbers, and they are the only phases that can contradict a model that just said it was finished.
§10's table had Commandos probing and breaking and no row for the moment the project's own test suite
returns a verdict — which is the moment the operator is actually waiting for. Giving that moment its
own phase, with no unit and no opinion attached, is both the honest structure and the better theatre.

The other half of the fun is negative and worth stating: `result.score || 5` (F233) is what a boring
console is made of. Every unit reporting a five, forever, because the number that means "nobody
looked" and the number that means "middling" are the same number.

## Open questions

| # | Question | Waiting on |
|---|---|---|
| OQ-W11-1 | What does M2 Integrate cost on this box — a full build + test of the assembled workspace, per mission? If it is minutes, does it run once at the end or after each task? | measurement, W6 item 4's GPU block |
| OQ-W11-2 | Is M1 Plan skippable for a single-task mission? v1 always decomposes, paying a model call to produce a list of one. | item 2, cheap to measure |
| OQ-W11-3 | Does a task set need real dependency edges, or is v1's ordered list enough? W3 F109 already made `depends_on(task, task)` first-class rows; M1 has to emit them or it does not. | item 3, W3 item 1's OQ-W3-2 |
| OQ-W11-4 | Is A1 Localize re-runnable — can a failed attempt fork a fresh brief? | inherits OQ-W6-5; W3's lattice supports it |
| OQ-W11-5 | Does M3 Accept get a model-authored evidence summary, or only the six queries? | item 4, W5 |
| OQ-W11-6 | Ratify the call-signs and the entity words (mission / task / attempt / unit / slot). | David, OQ-W3-6 |
| OQ-W6-4 | *(from W6 item 2)* Does the Judge see the Measure phase's output before scoring? | **answered here**: yes — A3 precedes A4 and its output is in A4's prompt (F235) |

## Confidence: high on the axis split and the two levels, medium on the call-sign assignment

High on F225–F237: every one is read at a call site and every one is re-checkable in a line or two,
and the four that matter most (F228, F229, F231, F232) are absence claims verified by grepping for
readers rather than by reading intent. The two-level structure is not inferred — v1 documents it in
its own header comment and its module docstring, and the other two donors confirm it by having no
mission level at all.

Medium on the call-sign assignment, which is a naming judgement David ratifies, and on whether
**Localize** and **Judge** stay separate model calls once 2.0's own verifier exists — W6 flagged the
same edge and nothing here settles it. Medium on M2 Integrate's affordability: the phase is the right
shape and both Rust donors already run something like it, but on a repository-sized workload with one
GPU its cost is unmeasured (OQ-W11-1), and F220's hung timeout is a warning about what running a
project's real suite can do to a pipeline that has not planned for it.

---

# Item 2 — the phase-to-tier mapping

## Question

§10 asks it as five words and one demand: *"Tier mapping. Which tier fits each stage, given a
decided base agent? Recon wants cheap plus long context. Architecture wants the strongest
reasoning available in the current mode. Building wants parallel throughput. Gate wants
adversarial capability. **Justify with measurements.**"* (`RESEARCH_BRIEF.md:534-538`).

Item 1 changed the shape of the question twice. The mapping is **phase→tier, not unit→tier**,
because units turned out to be runtime slots rather than stage types; and **two of the seven
phases run no model at all**, so the swap arithmetic only binds across M1 Plan → A1 Localize →
A2 Change → A4 Judge.

The measurements the brief demands mostly exist already — W1 F77–F80 and W2 F81–F86, all taken
2026-08-16 on this box. What they do not cover is the thing a *pipeline* does that a single agent
does not: change the prompt, repeatedly, in the same session. That gap is what this item measured.

## Method

Desk work over W1/W2's existing numbers, plus five probes run 2026-08-22
(`research/spikes/w11-tier/`, README there, raw output committed):

- `phases.py` — what a phase transition costs when the phase brings its own system prompt and
  tool array, against the same transition with the head frozen and the phase at the tail.
- `heads.py` — how many distinct prompt heads the server holds warm at once, and whether a model
  load survives it. Run once at 6 heads, once at 12 after a reload.
- `verdict.py` + `repeat.py` — what output budget one Judge call needs, against the donor's actual
  number, with and without BCF's own `/no_think` workaround; then five identical calls for
  reproducibility, and a fair prompt-and-pray arm.
- `plan.py` + `criteria.py` — what one Plan call costs, whether it inflates a single-task mission,
  and whether the acceptance criteria it emits fail on the unfixed tree.
- `integrate.py` — M2 Integrate's cost on two real projects, cold, warm and incremental (CPU only,
  no model call in flight).

Held constants per Q56's rule: champion at `-c 65536 --parallel 1`, nothing else resident, and the
`llama-server` command line captured per F86 — byte-identical to W2's, which is itself a finding
(F240). Donor claims are read at their **consumption** sites, per the standing rule.

## Inherited

| What | Source | Verdict here |
|---|---|---|
| §10's per-stage model tier column | `RESEARCH_BRIEF.md:517-524` | **collapses to one value** on this box, and is replaced by a four-knob per-phase profile (F238) |
| F79 — a model swap costs 23.77 s round trip | W1 | **it is a floor, not the price** — the swap also destroys the prompt cache (F241) |
| F81 — one token at the front annihilates the prefix cache | W2 | ratified and generalised: a whole head does the same, and the fix is a prompt *layout* rule (F239) |
| F81's consequence, "freeze the tool set per session" | `abcc-2-w1-w2-state` | **sharpened**: freeze is the wrong word. Enumerate. A finite set of heads is affordable; an unbounded one is not (F240) |
| F83 — concurrency saturates at N=2, KV is a sum not a division | W2 | binding, and now compatible with per-phase heads: two slots do not evict each other (F240) |
| F87–F88 — the 27B ties on verdicts at 5.2× the wall clock | W1 | binding: "escalate to a bigger local model" has no measurement behind it on this box |
| F82 — constrained decoding is enforced; the trace is spent first | W2 | ratified, and the trap is worse than F82 could see: the overflow is non-deterministic (F246) |
| §14 item 0 — C10 stays manual and rare, no routing tier | brief | binding, and item 2 finds the one phase where "manual and rare" is structurally possible (M1) |
| F218 / F233 — every gate input is `Measured \| Uncertain`, constructed never coalesced | W6, W11 item 1 | ratified, and an empty payload from a length-capped call is now a named instance (F246) |
| OQ-W11-1, OQ-W11-2 | item 1 | **both answered** (F249, F250) |

## Findings

### 🚨 F238 — the tier axis on this box has one rung, and F79's 23.77 s was the floor of the second rung's price, not its price

The candidates are fixed by arithmetic that is already done. F68: nothing co-resides with the
champion — the card is 16,311 MiB, the champion holds 14,362–14,820 at ctx 32768 and 15,772 at
65536, and the smallest model on this disk is 3,759 MiB. So every "second tier" is a **swap**, and
F79 priced the swap at 23.77 s round trip.

What F79 did not measure is what the swap does to everything the server had learned. It destroys
it. Measured this session: a prompt head warm at **2.626 s** came back at **10.584 s** after an
unload and load of the *same* model — a full cold prefill, because LM Studio spawns a fresh
`llama-server` per load (F75) and the cache lives in that process (F241).

So the price of a tier change is three things, not one:

| component | at ~17k tokens | at the daily driver's ~55k |
|---|---|---|
| the swap itself (F79) | 23.77 s | 23.77 s |
| the arriving model's prefill is cold, not warm | +8.5 s | +26 s (extrapolated) |
| every head the champion had warm is cold on return | +8.5 s each | +26 s each |

**A per-gate second-opinion reviewer therefore costs ~32–41 s per gate at 17k and ~50–76 s at the
daily driver's window**, against **zero** for same-model-no-history. The 17k figures are measured;
the 55k figures extrapolate F80's 33.9 s cold prefill at 54,930 tokens against this session's
measured restore rate of ~6,500 tok/s. Either way the number W6 item 3 and W11 item 4 have to weigh
against W8's +3.65 median critic inflation is **roughly double F79's**, and it recurs per attempt
rather than per mission.

The same arithmetic kills the other direction. §10 wants Recon "cheap plus long context", and W1's
recommendation 4 nominates `qwen3.5-4b` from the champion's own family for triage. Priced here:
a 4 B model decodes perhaps 2–3× faster, so a 1,000-token brief saves ~10 s of decode — against
~12–18 s of swap and at least 8.5 s of destroyed cache, each way. **A cheaper tier costs more than
it saves for any single call.** It only pays for a long batch of calls at that tier with nothing
else needing the champion in between, and the retry loop (a failed A3 sends the task back to A2)
forbids exactly that batching. W1's recommendation stands as written — as advice for the hardware
variants in its own table, not as an operating point for this box.

### 🚨 F239 — a phase transition costs a full cold prefill if and only if the phase rewrites the prompt head

W2 F81 measured that one token changed at the front of an 18,470-token prompt costs 11.399 s
against a cold 11.549 s — annihilation, not degradation. The pipeline question is bigger than one
token: §10 gives every stage its own unit, and the natural implementation gives every phase its own
system prompt and its own tool array, both of which the chat template renders **ahead of** the
messages.

Measured at ~16.9k prompt tokens, champion, `--parallel 1`:

| | TTFT | vs cold |
|---|---|---|
| A1 head *Recon*, first sight | 10.944 s | 1.00× |
| A2 same head, different question | 2.398 s | 0.22× |
| **B1 head *Builders* — a phase transition** | **10.857 s** | **0.99×** |
| A3 back to head *Recon* | 2.770 s | 0.25× |
| S1 frozen head, phase at the tail, first sight | 10.878 s | 1.00× |
| **S2 → Change, frozen head** | **2.362 s** | **0.22×** |
| **S3 → Judge, frozen head** | **2.377 s** | 0.22× |
| **S4 → Localize, frozen head** | **2.364 s** | 0.22× |

**A phase transition that rewrites the head costs +8.5 s, 4.60× the frozen-head transition.** Over
one attempt's three transitions (A1→A2→A3→A4, of which three are model calls) that is 32.6 s of
prefill against 7.1 s — and at the daily driver's window it is roughly triple that, which starts to
rival the task itself (F88: 100–190 s median per K-suite task on the champion).

The fix is not a tier and not a model. It is a **prompt layout rule**, and it is stated in
recommendation 3.

### 🚨 F240 — the server holds at least twelve distinct heads warm, and that is a backend default nobody configured

Step A3 above should not have been warm. With `--parallel 1` there is one slot, head *Builders* had
just displaced head *Recon* in it, and the two share no prefix beyond a few tokens. Returning to
*Recon* was warm anyway, at 2.770 s.

Pushed further — twelve distinct heads over the same body, each ~16.9k tokens:

| | pass 1 (first sight) | pass 2 (same twelve, same order) |
|---|---|---|
| every head | 10.58 – 10.83 s | **2.53 – 2.60 s** |

No eviction at twelve, and the restore is indistinguishable from a same-prefix hit. Re-prefilling
16,865 tokens in 2.6 s would be 6,500 tok/s against a measured prefill plateau of ~1,600 (F80), so
the server is restoring state, not recomputing it.

**It costs host RAM, and the amount is measurable.** `llama-server`'s working set went **988 MiB
after load, cache empty → 2,879 MiB with four cached states**: **473 MiB per state of ~16.9k
tokens, ≈ 28.7 KiB per token.** At the daily driver's 61,440 that is ~1.7 GiB for one warm head.

And per F86's rule — the command line is the only complete witness — the flags that would configure
this are **not on it**: no `--cache-ram`, no `--slot-save-path`. This is llama.cpp b2.27.1's default
RAM prompt cache, arriving through LM Studio unasked. That is the mirror image of F165's lesson: a
command line proves presence, not provenance, and an **absent flag does not prove an absent
feature**.

⚠ **What this does and does not buy, because the tempting reading is wrong.** It does not make
per-phase heads free. In production the body under the head is *task-specific*, so each
(phase head, task context) pair is a first sight and pays F239's 8.5 s regardless of how many
states are held. What the store actually buys is two things, both real:

- **retries are warm.** A failed A3 sends the task back to A2 with the same head and the same
  context — which is a prompt the server has already seen. The loop that costs the most re-prefills
  is the one the cache covers.
- **concurrent attempts do not evict each other.** F83 put the concurrency ceiling at N=2; two slots
  working on different tasks would thrash a single-prefix cache and do not thrash this one.

So the ruling F81 handed to memory — *"freeze the tool set per session"* — was right, and **freeze
is the wrong verb**. The correct rule is **enumerate**: a finite, compile-time set of heads is
affordable in both time (one cold prefill each, once per body) and RAM (473 MiB each at 17k). An
*unbounded* set — a tool registry that grows on demand, a system prompt carrying a task id or a
timestamp — is unaffordable twice over, a cold prefill per variant and 473 MiB per variant.

### F241 — the cache is process-local, so a model load is a cache wipe

The evidence is in F238's table and worth isolating because it is the mechanism: head H0, warm at
**2.626 s**, measured at **10.584 s** immediately after an `lms unload` + `lms load` of the same
model. Nothing else changed.

The round trip for that same-model reload was **9.20 s** (unload 0.87 s, load 8.33 s) — *faster*
than any figure in F79's table, which measured 11.42–12.35 s per direction. The difference is the
OS page cache: F79 alternated two models of 12.67 and 12.4 GiB on a machine whose file cache could
not hold both, while this reload had just released the weights it then re-read. **F79's 23.77 s
remains the number for a real tier change**; 9.20 s is the number for "restart the server", which is
a different operation and worth knowing separately — it is what a 2.0 that needs to clear state
would pay.

### 🚨 F242 — BCF has two per-role model tables, the live one is not the one you find first, and the dead one is uniform

BCF is the donor that actually built §10's tier column, which makes it the best available evidence
about whether the column works. It built it twice.

- **`src/models.rs::PresetConfig`** — five roles (architect, tester, coder, reviewer, security) ×
  three presets. **In all three presets, all five fields hold the same model string**
  (`models.rs:29-59`): `qwen3-coder-next:q8_0` for premium, `qwen2.5-coder:32b` for balanced,
  `qwen2.5-coder:7b` for fast. Its module docstring says *"Reads presets from
  .battlecommand/models.toml"* (`models.rs:3`) and `get_preset` is a hardcoded `match` that reads no
  file (`models.rs:91-97`). Its only reader in the whole repo is `main.rs:419`, inside a display
  loop for `models list`.
- **`src/model_config.rs::ModelConfig`** — eight roles (architect, tester, coder, fix_coder,
  security, critique, cto, complexity) × four fields each (`model`, `provider`, `context_size`,
  `max_predict`), with a real resolution order — preset → env → TOML → CLI (`model_config.rs:333-345`).
  This is the one `mission.rs` reads (`:124-146`, `:214-218`) and the one `main.rs:297-307`
  constructs.

So the first tier table a reader meets is inert, and it is the uniform one; the live one is
genuinely heterogeneous. Two consequences. First, **the grep-the-readers rule earns its keep again**
— a whole preset system, tested (`models.rs:225-232`) and documented, with one reader that prints
it. Second, the honest reading of the donor evidence is *not* "BCF tried per-stage tiers and made
them all the same"; it is **F243**.

### 🚨 F243 — the live tier table costs about four model loads per mission, and one of them is the same weights at a different window

`ModelConfig::from_preset(Premium)` (`model_config.rs:169-180`) assigns:

| role | model | window | output cap |
|---|---|---|---|
| complexity (router) | `qwen3-coder:30b-a3b-q8_0` | 32768 | 1024 |
| architect | `qwen2.5-coder:32b` | 32768 | 4096 |
| tester | **cloud** `claude-opus-4-6` | 200000 | 8192 |
| coder | `qwen3-coder-next:q8_0` | 65536 | 32768 |
| security | `qwen3-coder:30b-a3b-q8_0` | 65536 | 1024 |
| critique | `qwen3-coder:30b-a3b-q8_0` | 65536 | 1024 |
| cto | **cloud** `claude-sonnet-4-6` | 200000 | 1024 |
| fix_coder | **cloud** `claude-sonnet-4-6` | 200000 | 16384 |

Four **distinct local (model, window) pairs**, and the nine stages walk them in an order that
touches each at least once. On this hardware that is four loads per mission at F79's ~12 s each,
before a single fix round repeats any of them — **~48 s of pure loading per mission**, plus a cold
prefill after each.

The detail worth the finding number is the last pair. `security`/`critique` and `complexity` are the
**same weights at two different windows**, and BCF sends the window per request —
`"options": {"num_ctx": self.context_size, "num_predict": self.max_predict}` (`llm.rs:309, 440,
581, 979, 1087`). W1 F77 established that the KV cache is allocated **in full at load time**, and
W2 F84 that the window cannot be changed on the wire at all on the OpenAI-compat path. So a role
table that varies `context_size` on one model is asking for a reload it does not know it is asking
for. **A tier is not a model; it is a (model, window) pair**, and 2.0's profile table has to say so
or it will inherit this.

### 🚨 F244 — every donor's tier ladder is biased upward, and two of them escalate on an infrastructure failure rather than on difficulty

- **v1** (F229, item 1): no idle agent in the pool → return the CTO with `modelTier: 'opus'` and
  literally `complexity: 10, // High complexity if no agents available`.
- **BCF**: `if ollama_result.is_err()` → *"Ollama unavailable, falling back to Claude Opus"*
  (`llm.rs:168-176`, and again at `:262-271` and `:419-428`). The predicate is **any** error from
  the local call — and `call_ollama` bails on model-not-found as well as on connection failure
  (`llm.rs:997-1001`). **A mistyped model name in a preset routes the whole mission to a frontier
  model**, with a 1,800 s client timeout (`llm.rs:132-135`) and no cap.
- **BCF again, twice more, in defaults**: `preset.parse().unwrap_or(Preset::Premium)`
  (`main.rs:297-299`) and `get_preset`'s `_ => default_premium()` (`models.rs:92-96`). An
  unrecognised preset name selects the most expensive one.
- **BCF's router**, which is otherwise the best-engineered tier decision in the family: when rules
  and AI agree it takes `((rules + ai) / 2).max(rules)` — a **floor at the rule score**
  (`router.rs:108-112`); when the AI scores higher by ≥2 it takes the AI's number outright
  (`:85-94`); only when the rules score higher by ≥2 can the result fall below them, and then only
  40% of the way (`:95-106`). Every branch rounds toward complexity, and complexity ≥ 7 upgrades the
  coder to a cloud model (`mission.rs:307-328`).

The one thing in this list to **port rather than avoid** is the router's shape:
`ai_complexity_score` returns `Option<u32>` and a `None` degrades to the deterministic rule score
with `ComplexitySource::Rules` recorded (`router.rs:117-121`), and the result carries `source`,
`rule_score` and `ai_score` alongside the number. That is F218's `Measured | Uncertain` discipline
arrived at independently. What must not be ported is the direction of every default around it.

**The rule for 2.0:** a tier decision records its source, can go **down**, and treats an unavailable
tier as `Uncertain` — never as an upgrade. Resource exhaustion is not difficulty (F229), and an
error from a local server is not a licence to spend.

### 🚨 F245 — the donor's output cap for a judging role returns an empty verdict on this model, and the donor's own workaround for that does not work here

BCF caps `security`, `critique` and `cto` at `max_predict` 1024 (`model_config.rs:174-179`). That
number was chosen for `qwen2.5-coder`, which does not emit a reasoning trace. Measured on the
champion with a realistic Judge prompt (745 tokens: brief + diff + measurement set) and a strict
verdict schema:

| `max_tokens` | finish | completion tokens | reasoning chars | **payload chars** | JSON |
|---|---|---|---|---|---|
| 256 | length | 256 | 938 | **0** | — |
| 512 | length | 512 | 1,990 | **0** | — |
| **1024 — the donor's number** | **length** | 1,024 | 4,107 | **0** | — |
| 2048 | length | 2,048 | 8,599 | **0** | — |
| 4096 | stop | 2,718 | 9,640 | 1,300 | ok |
| 8192 | stop | 2,284 | 8,104 | 1,148 | ok |

At the donor's production number the endpoint returns **HTTP 200 with an empty string**. W2 F82 saw
this at 300 tokens and called it a silent failure; here it is a silent failure at the number a
shipping donor actually uses, on the phase where it matters most.

BCF knows about the trace and works around it: its router prompt begins with `/no_think`
(`router.rs:327`), a Qwen-family control token. On this model it does nothing measurable — 1,035 /
2,041 / 3,979 chars of reasoning at 256 / 512 / 1024 against 938 / 1,990 / 4,107 without it, and the
payload still empty at 1024. **A control token from one Qwen generation is not a mechanism on
another**, and it should be treated as a measurement per model, never as a portable trick.

### 🚨 F246 — the trace is an unbounded input to a bounded output budget, and the overflow is silent, non-deterministic, and 20% at four times the donor's cap

Five identical calls, identical prompt, `max_tokens: 4096`, `temperature: 0`:

| run | finish | completion tokens | reasoning chars | payload |
|---|---|---|---|---|
| r1 | stop | 2,780 | 9,942 | verdict |
| r2 | stop | 3,872 | 14,257 | verdict |
| r3 | stop | 2,860 | 10,200 | verdict |
| r4 | stop | 4,006 | 14,916 | verdict |
| **r5** | **length** | **4,096** | **16,564** | **empty** |

The trace varies **9,942–16,564 characters on identical input** — a 1.67× spread — and one call in
five hit the ceiling and returned nothing at a budget four times the donor's. There is no
`max_tokens` that is safe by construction, because the quantity being bounded is not the answer.

Two consequences, both mandatory rather than advisory:

1. **8192 is the defensible budget for a judging phase on this model** — twice the largest observed
   successful completion (4,006) — and it costs nothing when unused, since billing here is wall
   clock and the model stops when it stops.
2. **`finish_reason == "length"` with an empty payload is `Uncertain(TraceOverran)`, constructed at
   the site that knows why.** It is not a verdict, it is not a zero, and it is exactly the shape
   F233's `result.score || 5` destroys. The instrument is free: `usage.completion_tokens_details.
   reasoning_tokens` is on the wire from this endpoint, so the trace can be logged as a measurement
   rather than inferred.

### F247 — the verdict's binary is reproducible and its number is not

Across the seven successful Judge calls on identical input (four schema-constrained, three
prompt-constrained), the verdict was **`fail` 7/7**. The score was **0, 2, 0, 2** in the schema arm
(stdev 1.15 on a 0–10 scale) and 2, 2, 2 in the other. Defect counts were 3 or 4, and 2.

Temperature was 0.0 in every call; the variation is the model, not the sampler — MoE expert routing
and speculative decoding are not bit-reproducible. **A gate threshold on the number would flip on
re-running the same input**; the binary would not. This is item 1's ruling — a model verdict is an
input to a decision, never a gate — arriving as a measurement rather than an argument, and it is the
same conclusion W6 F217 reached from the veto side.

### F248 — asked for JSON in the prompt, the unconstrained arm parsed 3/3, so the schema's case is the guarantee and not the hit rate

`verdict.py`'s first no-schema arm had not been told to emit JSON, which measured nothing useful.
Re-run with the format spelled out in the prompt — which is what v1 and BCF actually do — the
unconstrained arm returned **valid JSON 3 times out of 3**, at 1,764–2,891 completion tokens, and
never hit the ceiling.

That refutes the strong version of the argument for `response_format`, and the honest statement of
the weak version is the one that survives: a schema makes malformation **unrepresentable** rather
than **unlikely**, which matters because the family's one hard number about output reliability is
ABCC's 10.5% tool-call malformation rate — a rate, not an impossibility, and one that shows up in
the tail rather than in a probe of three. Worth recording alongside: the constrained arm produced
3–4 defects and 1,148–1,838 payload characters against the prompt arm's flat 2 defects and ~420, on
n=4 and n=3 — suggestive that the schema changed the *content* and not only the shape, and far too
small to rule on.

### 🚨 F249 — Integrate's cost is the target project's cost, and the workspace-isolation choice multiplies it ~5× (OQ-W11-1)

Item 1 owed one measurement: what M2 Integrate costs on this box. It is not one number, because M2
runs the *target project's* build and suite, and 2.0 does not choose that project.

| | K-suite Python fixture (15 files) | Claudette (real Rust workspace, ~300 deps) |
|---|---|---|
| acceptance criterion alone | 0.17 s cold, 0.06 s warm | — |
| **fresh workspace** (no build cache) | 1.17 s | **104.2 s** (clone-fetch 17.5 + build 57.1 + test compile 19.7 + run 9.8) |
| **persistent workspace, nothing changed** | 0.48 s | **6.1 s** |
| **persistent workspace, one source file touched** | 0.47 s | **22.3 s** (build 5.1 + test 17.1) |

The third row is the one M2 actually faces after a task lands. **22 s on a real Rust repository
means Integrate after every task is affordable** — against F88's 100–190 s per task, it is 12–22%.
The first row is the price of workspace isolation: **~4.7× the incremental cost**, per attempt, and
that is the number W6 item 6 needs for OQ-W3-12 (git worktree vs stash-object vs copied pre-image) —
a fresh worktree does not share `target/`, so every isolated attempt pays a cold build.

So the policy question item 1 could not settle does not have a fixed answer, and should not be given
one: **measure the first Integrate, record it on the log, and let the policy follow the number.**
Cheap project, run it after every task; expensive project, run it at the mission boundary and let
A3's per-task criterion carry the load in between. The mechanism this needs from W3 item 7 is
already built — the job object, because a build that hangs is the failure mode Claudette's own gate
demonstrates (F220: killed the child, joined the reader threads, still blocked at 11 s).

### F250 — Plan does not inflate a one-task mission when it is told not to, so skipping M1 is an optimisation and not a correctness fix (OQ-W11-2)

v1 always decomposes, paying a model call to produce a list of one. The open question was whether
that is the model's behaviour or v1's. Measured: one Engineering head over a real 112-file Rust
tree, schema-constrained task set, n=3 per mission, with *"a mission that is one change is one
task"* in the system prompt.

| mission | tasks emitted | wall clock | prompt / completion tokens |
|---|---|---|---|
| plainly one task (`UsageTracker` double-counts on resume) | **1, 1, 1** | 36.4 / 37.6 / 40.8 s | 1,534 / 2,442–2,676 |
| plainly several (`--json` mode across the CLI) | **3, 2, 3** | 39.1 / 53.0 / 61.7 s | 1,534 / 2,679–4,301 |

So M1 costs **36–62 s per mission**, TTFT 2.3–3.0 s, and it does not manufacture work. Skipping it
for a single-task mission saves ~40 s against a mission that will run 100–190 s per task — real, but
an optimisation. And it cannot be skipped outright, because M1 is what emits the executable
acceptance criterion, which is the only thing in the family that ever bound (F231, F236). **The fast
path §10 asks for is "one task, one criterion, no decomposition", not "no Plan".**

Two operational notes. The completion sizes (2,442–4,301) put Plan in the same budget class as
Judge, so **8192 is the output budget for M1 as well** (F246). And the model chose `cargo` commands
for a Rust tree without being told the language, which is the cheap end of what §10's "fast path"
triage would otherwise need a router for.

### 🚨 F251 — six of eleven acceptance criteria pass on the unfixed tree, and the one that failed for the right reason tested the wrong binary

The task sets from F250 were the right *size*. Their criteria were run against the unmodified clone
they were planned over — the tree where every task is by construction **not yet done**, so a real
criterion must fail:

| | count | examples |
|---|---|---|
| **passes today** — exit 0 on the unfixed tree | **6 / 11** | `cargo check -p claudette`; `cargo test -p claudette`; `cargo test --lib usage_tracker_resets_on_resume` |
| **could not run** | 3 / 11 | `./target/debug/claudette …` (not a command under `cmd.exe`); two needing `jq`, which is not installed |
| **failed for the right reason** | 2 / 11 | `claudette --help \| grep -q -- --json` |

The middle column is the mechanism worth naming. `cargo test --lib <name>` with a filter that
matches **nothing** prints `running 0 tests` and **exits 0** — so "write a test called X and make it
pass" is satisfied by the test's absence. That is F231's defect one level up: not an *absent* gate
reporting pass, but a *present* gate that never had an opinion. And the two that did fail ran a bare
`claudette`, which resolves to `C:\Users\david\.cargo\bin\claudette.exe` — the installed daily
driver, not the tree under test. A criterion that names a bare binary measures whatever is on
`PATH`, which is F232's disease (grade the artifact, not a proxy for it) in the gate rather than in
the judge.

None of this is fixed by a tier. It is fixed by a mechanism, and the mechanism is cheap:
**run the criterion before the change.** If it passes on the unfixed tree it is not a criterion;
if it cannot run it is `Uncertain`. Recommendation 6.

## Options compared

Scored against: does the mapping survive the measurements (F238–F251), does it fit one GPU and one
resident model, does every per-phase difference cost something the project can afford, and does the
console get something honest to show.

| Option | The mapping | Cost | Verdict |
|---|---|---|---|
| **A.** §10 as written — a model tier per stage | 4 tiers | 3 swaps per attempt minimum, 23.77 s each plus a wiped cache (F238, F241); on a card that holds one model (F68) | rejected |
| **B.** BCF's live table — per-role (model, provider, window, cap) | 8 roles, 4 local pairs | ~48 s of loading per mission (F243), an upward-biased ladder (F244), and a cap that returns nothing (F245) | rejected, one part ported |
| **C.** One tier, one prompt, no per-phase difference at all | 1 profile | throws away the only per-phase knobs that are *free* — tool policy and output budget — and gives A4 the same 32k output budget as A2 | rejected |
| **D. One tier; per-phase differences confined to the free knobs — head (enumerated), tool policy, output budget, context budget — with three phases running no model** | 1 model, 7 profiles | one cold prefill per (head, body); 473 MiB of host RAM per warm head; nothing else | **recommended** |
| **E.** D, plus a swapped second model for A4 Judge | 2 models | +32–41 s per gate at 17k, +50–76 s at 61k (F238), recurring per attempt | **deferred to item 4 / W6 item 3** — priced here, not decided here |

## Recommendation

### 1. There is one tier, and "tier" is the wrong axis

The phase→tier mapping on this box is **four phases → one tier, three phases → no model**:

| | phases | tier |
|---|---|---|
| model phases | M1 Plan, A1 Localize, A2 Change, A4 Judge | the champion, resident, `-c 61440` under a 65536 load |
| **no model at all** | **M2 Integrate, A3 Measure, M3 Accept** | — |

Item 1 handed over "two of the seven need no tier". It is **three**: M3 Accept is a human by
default, and when unattended it is a rung on W3's ladder, which is data on the event log and not a
model call. Item 1's own text says so; its handoff undercounted.

What replaces §10's tier column is a **per-phase runtime profile of four knobs**, sorted by what it
costs to change them — which is the only sort order that matters on hardware this tight:

| knob | cost to vary per phase | vary it? |
|---|---|---|
| **weights** | 23.77 s + the whole prompt cache (F238, F241) | **no** |
| **window** (`-c`) | a model load, and VRAM spent at load whether used or not (F77, F243) | **no** — one window for the session |
| **prompt head** (system prompt + tool array) | one cold prefill per (head, body), +8.5 s at 17k; 473 MiB RAM per warm head (F239, F240) | **yes, from a closed set** |
| **output budget** (`max_tokens`) | nothing | **yes** |
| **tool policy** | nothing, if enforced at the executor rather than by editing the head | **yes** |

### 2. The phase profile table — the deliverable

One resident model. Everything below the first column is per phase.

| # | phase | model | head | tools in the head | output budget | measured cost on this box |
|---|---|---|---|---|---|---|
| M1 | **Plan** | champion | `Plan` | read-only | **8192** | 36–62 s, 2.4–4.3k completion (F250) |
| M2 | **Integrate** | **none** | — | — | — | 0.5 s … 22 s incremental; 104 s from a fresh workspace (F249) |
| M3 | **Accept** | **none** (human, or a W3 ladder rung) | — | — | — | 0 |
| A1 | **Localize** | champion | `Localize` | read-only | 8192 | not separately measured — same class as M1 |
| A2 | **Change** | champion | `Change` | full, gated | large; bounded by the loop budget (item 5) | dominates: 100–190 s per task (F88) |
| A3 | **Measure** | **none** | — | — | — | the project's suite: 0.5 s … 22 s (F249) |
| A4 | **Judge** | champion | `Judge` | **none** | **8192**, and empty ⇒ `Uncertain` | 25–64 s at a 745-token prompt (F246) |

Concurrency: **two slots** (F83), and F240 says they will not evict each other's context. The KV
bound is a sum, not a division — Σ(active sequence lengths) ≤ the loaded window — so two attempts in
flight are budgeted at ~30k each, not 61k each.

### 3. Within an attempt the prompt is append-only

This is F239's ruling and it is the one design rule in this item that will be violated by accident
if it is not written down.

**Layout:** `[phase head][task context][accumulated artifacts][phase instruction]`, and each phase
**appends**. Localize appends nothing and asks for a brief; Change reads the brief that Localize
appended; Judge reads the brief, the diff and A3's measurements, all appended behind it. Nothing
before the tail is ever rewritten. That is F81's benign case D — measured at 1.30× — rather than its
case C, measured at 4.85×, and over one attempt it is 7.1 s of prefill instead of 32.6 s.

**Corollary, and it is the awkward one:** if the head must be constant across the phases of one
attempt, then **per-phase tool arrays cannot live in the head**. Declare the union once and enforce
the policy at the executor: Localize's `write_file` call is refused by the runtime, not hidden from
the model, and the refusal is an event on the log like every other. The model sees tools it may not
use, which costs some prompt discipline and buys 8.5 s per transition at 17k and ~26 s at 61k.

Where per-phase heads *are* wanted — and they may be, since a Judge with no tools in its head is a
better Judge — the cost is now known rather than guessed, and it is paid per (head, task), not per
transition. **Enumerate them**: a `PhaseHead` enum resolving to `&'static str`, no interpolation, no
task id, no timestamp, no registry that grows. F240's 473 MiB per warm head is the budget line.

### 4. When a second tier is worth buying — amortise it, and the answer is M1 or nothing

A tier change is affordable exactly where it is paid **once per mission at a boundary where nothing
is warm**. There is one such place.

- **M1 Plan qualifies.** It runs once, at mission start, before any head has been prefilled, so the
  cache-wipe term is zero and the price is F79's 23.77 s against a mission of several tasks at
  100–190 s each — **4–8% of a three-task mission**. This is also the only phase where §14 item 0's
  "C10 stays manual and rare" is structurally compatible with the pipeline: one call, at a boundary,
  that a human can choose to make.
- **A4 Judge does not qualify.** Once per attempt, mid-context, with heads warm: **32–41 s per gate
  at 17k, 50–76 s at 61k** (F238). Item 4 and W6 item 3 own that trade against W8's +3.65 median
  critic inflation; item 2's contribution is the price and the correction that F79 alone understates
  it by roughly half.
- **A cheap triage tier does not qualify at all** (F238): it costs more than it saves for any single
  call, and the retry loop forbids the batching that would amortise it.

And **"up a tier" is not a rung on the failure ladder.** §10 asks "on gate failure, back to build,
back to architecture, or up a tier?" On this box the only bigger local model is the 27B, which W1
measured as **level on verdicts at 5.2× the wall clock** (F87, F88) — no measurement supports
escalating to it, and F244 shows what happens to a ladder whose defaults all point upward. The
failure ladder is W3's classified-failure ladder over data: retry, re-localize, ask the human.

### 5. Output budgets are per phase, and an empty payload is a measurement of nothing

Set **8192** for every model phase that emits a structured artifact (M1, A4, and A1 by inheritance),
which is twice the largest completion observed. Then, because F246 shows no budget is safe by
construction:

```rust
match (finish_reason, payload.is_empty()) {
    (FinishReason::Length, true) => GateInput::Uncertain(Why::TraceOverran { reasoning_tokens }),
    (FinishReason::Length, false) => GateInput::Uncertain(Why::Truncated { reasoning_tokens }),
    (FinishReason::Stop, false)   => GateInput::Measured(parse(payload)?),
    (FinishReason::Stop, true)    => GateInput::Uncertain(Why::EmptyPayload),
}
```

No `Default`, no `unwrap_or`, no `unwrap_or_default` on that type (F233's rule). Log
`usage.completion_tokens_details.reasoning_tokens` on every call: it is already on the wire, it is
the quantity that overran, and without it the failure is invisible in the record.

Use `response_format: json_schema, strict: true` for every structured artifact — but for the reason
F248 leaves standing, which is that it makes malformation unrepresentable, not that this probe
caught the unconstrained arm failing. It did not.

### 6. A criterion is validated by running it before the change

F251's mechanism, and it belongs to A3 Measure rather than to M1 Plan, because M1 cannot check its
own work and A3 already has the runner.

**When a task set arrives, run every criterion once against the unchanged tree.**

- exits non-zero for a reason that is not "cannot run" → the criterion **binds**; record the
  baseline on the log.
- exits zero → **not a criterion**. The task is `Uncertain(CriterionDoesNotDiscriminate)` and goes
  back to M1 with the evidence, which is the command and its exit code.
- cannot run — binary absent, tool missing, wrong shell → `Uncertain(CriterionUnrunnable)`, never a
  fail.

Three specifics the measurement produced, each worth encoding: a `cargo test` filter matching
nothing **exits 0**, so "make this new test pass" is satisfied by the test's absence; a bare binary
name resolves against `PATH` and not against the workspace, so criteria must name the artifact the
task builds; and the shell is part of the criterion, so it is recorded with it. v1's four auto-repair
passes over generated validation commands (`orchestrator.py:223-284`) exist for exactly this reason
and item 1 already flagged them for porting — F251 is the measurement that says why they are not
optional.

### 7. What this hands onward

- **To W11 item 3 (artifact schemas):** the task set carries `acceptance: Criterion { command,
  shell, cwd, baseline: Option<ExitCode> }` — the baseline is F251's red-first check, and its absence
  is a state, not a default. The verdict artifact carries `reasoning_tokens` and a `finish_reason`,
  because F246 makes them part of the measurement.
- **To W11 item 4 / W6 item 3:** the decorrelation price, per gate, on this box: **32–41 s at 17k,
  50–76 s at 61k**, recurring per attempt, against zero for same-model-no-history — and F247's
  finding that the binary is reproducible while the score is not, which narrows what a second
  opinion could even be asked for.
- **To W11 item 5 (loop budgets):** the per-phase output budget is 8192 and the overrun is a
  classified failure, not a retry. A retry of A2 is **warm** (F240), which is what makes the loop
  affordable at all.
- **To W6 item 6 (OQ-W3-12, workspace checkpoints):** isolation costs **4.7×** on a real Rust
  project — 104.2 s from a fresh clone against 22.3 s incremental. That is the number the worktree
  question turns on.
- **To W5:** the console's per-unit line is *(phase, head, tokens in flight, output budget used)*,
  and the honest thing to show during a swap — if one is ever bought — is the cache going cold,
  because that is what the operator is waiting for.
- **To W2's open question 3** (slot save/restore as an answer to F79): partly answered without
  running it. The RAM prompt cache is already doing what `--slot-save-path` would do *within* a
  process (F240); what it cannot do is survive the process (F241). If a swap-per-gate design is ever
  wanted, `--slot-save-path` is the only thing that would make it affordable, and F241 is the
  measurement that says why.

## Rejected alternatives and why

- **A tier per stage (§10 as written).** F238 and F241: three swaps per attempt, each 23.77 s plus a
  wiped cache, on a card that holds one model. The column is not expensive, it is unaffordable.
- **A cheap triage tier for Recon.** F238's arithmetic: the swap and the destroyed cache cost more
  than the decode saved, for any single call. Kept in W1's table as advice for other hardware.
- **Per-phase windows** (BCF's `context_size` per role). F77: the window is VRAM spent at load, and
  F243 shows a role table that varies it is asking for a reload it did not budget. One window per
  session.
- **Per-phase tool arrays in the head, unconditionally.** Not rejected outright — priced (F239) and
  made a deliberate purchase at 8.5 s per (head, task) at 17k, with the default being the union set
  and executor-side enforcement.
- **BCF's `/no_think` as a way to cut the Judge's cost.** F245: no measurable effect on this model.
  A control token is a per-model measurement, not a portable technique.
- **A score threshold as a gate.** F247: 0, 2, 0, 2 on identical input at temperature 0. The binary
  survives re-running; the number does not.
- **Escalating a failed attempt to a bigger local model.** F87/F88 measured the only candidate as
  level on verdicts at 5.2× the wall clock, and F244 shows every donor's ladder already leans that
  way for reasons that are not difficulty.

## Effect on fun

The best thing item 2 found for the console is that **the expensive thing is visible and the cheap
thing is instant**. A phase transition under recommendation 3 costs 2.4 s; a phase transition that
rewrites the head costs 10.9 s. That is the difference between a unit that turns to face a new job
and a unit that has to be re-briefed from scratch, and the operator can feel it. Building the
pipeline the cheap way is also building the responsive way, which is not usually how those two line
up.

The unit-as-slot ruling from item 1 gets its counterpart here: **a slot's phase changes for free,
its weights do not.** That is a game mechanic and it is honest — the map is the card, the resident
model is the garrison, and swapping it is a costed, visible, 24-second action that also throws away
everything the unit had learned about the current fight. If a swap is ever bought, the console
should show the cache going cold, because that is the real price and it is the part a status
spinner would hide.

And F251 is the one that would have made the game a lie. A mission where every task ships with a
criterion that passes before the work starts is a mission where the green ticks mean nothing — eleven
criteria, six of which were satisfied by the tree as it stood. Running them red first is one extra
second on a Python project and 22 on a Rust one, and it converts the tick from decoration into the
only thing on the screen that cannot be argued with. §10 wanted the operator to see where the front
line is; the front line is wherever a measurement last changed its mind.

## Open questions

| # | Question | Waiting on |
|---|---|---|
| OQ-W11-7 | Does a **bigger model for M1 Plan only** produce a better task set? F250 measured cost and inflation, not quality; F87 says the 27B ties on *fixes* and nothing measures it on *plans*. | one K-series-shaped run over plan quality |
| OQ-W11-8 | What is the RAM prompt cache's actual capacity and eviction policy? Twelve heads at 16.9k did not evict; the budget is a llama.cpp default this project has not read from source. | cheap: keep adding heads until one comes back cold |
| OQ-W11-9 | Does the restore rate hold at the daily driver's window? All of F239/F240 is at ~17k; the 55k figures in F238 are extrapolated from F80 and a measured ~6,500 tok/s restore. | one probe at 55k, ~10 minutes |
| OQ-W11-10 | Is A1 Localize's output budget really 8192? It is assigned by inheritance from M1, not measured. | item 3 or the first real pipeline run |
| OQ-W11-11 | Does the executor-side tool policy of recommendation 3 cost quality — does a model that can see `write_file` during Localize behave worse than one that cannot? | a comparison run; W6 item 3's harness |
| OQ-W11-2 | *(from item 1)* Is M1 Plan skippable for a single-task mission? | **answered here** (F250): it does not inflate, so skipping is a ~40 s optimisation, and it cannot be skipped outright because it emits the criterion |
| OQ-W11-1 | *(from item 1)* What does M2 Integrate cost on this box? | **answered here** (F249): 0.5 s to 22 s incremental, 104 s from a fresh workspace |

## Confidence: high on the arithmetic, medium on what it implies for the head

**High** on everything measured this session, all of it repeatable in minutes from
`research/spikes/w11-tier/`: the transition cost (F239), the multi-head store and its RAM price
(F240), the cache wipe (F241), the empty verdict at the donor's cap (F245), the non-deterministic
overrun (F246), Integrate's cost (F249) and the criteria tally (F251). The donor readings (F242,
F243, F244) are read at their consumption sites and each is re-checkable with one grep.

**Medium** on three things. F238's 55k figures are extrapolated, not measured (OQ-W11-9). The
recommendation to enforce tool policy at the executor rather than in the head trades a measured 8.5 s
against an unmeasured quality effect (OQ-W11-11) — the arithmetic is certain and the trade is not.
And F251's rate is n=11 from one prompt over one repository: the direction is not in doubt, since the
system prompt explicitly demanded a criterion that fails today and six still did not, but the number
is a sample, not a rate.
