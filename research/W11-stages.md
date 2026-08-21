# W11 — Stage pipeline and unit roles

**Status: IN PROGRESS — started 2026-08-21**, the third leg of the W3 + W6 + W11 block (§14 item 4).
Built one item at a time in §13 format. W11 turns §10 into a spec and is the workstream §10 itself
names: *"Phase 0 must surface all three taxonomies side by side, and W11 must produce one. Do not
assume this table wins."* (`RESEARCH_BRIEF.md:529-531`).

Planned items:

1. ✅ **The reconciliation** (F225–F236) — v1's Coder/QA/CTO against BCF's nine stages against §10's
   four, with W6 item 2's four-phase starting taxonomy as the incoming position. Answered: the three
   are not three of the same thing, so the reconciliation separates the axes first and then produces
   **two levels** — Mission (Plan / Integrate / Accept) and Attempt (Localize / Change / Measure /
   Judge, plus Veto). §10's four unit names all survive, as **call-signs on phases that have
   construction sites**, and §10's table turns out to be missing the only stage that ever stopped
   anything in any of the three donors.
2. ☐ **Stage-to-tier mapping** backed by W1 and W2 measurements. Now a *phase*-to-tier mapping
   (item 1's ruling), and one of the phases needs no model at all, which changes the swap arithmetic.
3. ☐ **Handoff artifact schemas as Rust types**, not conventions. Brief, diff, measurement set,
   verdict — each an event on W3's log.
4. ☐ **Gate independence** and how it survives single player mode. Overlaps W6 item 3 directly;
   whichever runs first owns the measurement, the other cites it.
5. ☐ **Loop budgets and circuit breakers per stage**, benchmarked against v1's existing behaviour.
   Inherits W6 F223 (the decline breaker that changed meaning) and W3 F195 (the retry budget).

Scope reference: `RESEARCH_BRIEF.md` §11 lines 949–960, against §10 lines 515–545. Findings continue
the family numbering — one sequence across all workstreams. **Item 1 took F225–F236, so the next
free number is F237.** Check the maximum before adding, not the last number in this file
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
evidence of a mechanism. Four of the twelve findings exist because the declaration and the reader
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

## Options compared

Scored against: does it survive the code evidence (F225–F236), does it fit one GPU (W1 F79's 23.77 s
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
| M1 | **Plan** | model, read-only tools, once per mission | **Engineering** | the task set, each with **one executable acceptance criterion** | §10 Architecture; v1 `decompose_prompt`; BCF ROUTER's complexity tag |
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

High on F225–F236: every one is read at a call site and every one is re-checkable in a line or two,
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
