# ABCC v1 - Repo Dossier

**Repo:** `D:\dev\agent-battle-command-center` (public, MIT, `github.com/mrdushidush/agent-battle-command-center`)
**Pinned at:** `d5528ea`, 2026-08-06, branch `main`, 318 commits
**Read method:** static read plus metadata. Nothing was built or executed for this pass. Docker daemon is stopped, so no runtime behaviour was observed.
**Author of this dossier:** Claude Code, Phase 0
**Status:** complete for 4.1. Data extraction (4.2) is deferred per David's instruction and is covered separately.

---

## 0. One-paragraph summary

ABCC v1 is a three-service, three-language Docker Compose application that routes coding
tasks to a local 7B model and escalates to Claude only for decomposition and review. A React
console renders the whole thing as a Command and Conquer style battle map with voice lines. The
orchestration lives in TypeScript, the agent execution lives in Python behind CrewAI, and the
state lives in PostgreSQL behind Prisma. The routing intelligence and the presentation layer are
genuinely good and are the reason 2.0 exists. The execution layer underneath them is held
together by stdout scraping and has a defect that makes an agent report success when its own
output parser fails.

---

## 1. Module map

### 1.1 Top-level

```
agent-battle-command-center/
├── packages/
│   ├── api/          TypeScript, Express + Prisma + socket.io. The orchestrator.
│   ├── agents/       Python, FastAPI + CrewAI + litellm. The executor.
│   ├── ui/           React 19 + Vite 7 + Three.js. The console.
│   ├── mcp-gateway/  MCP server. Disabled by default (USE_MCP=false).
│   ├── shared/       One file of shared types.
│   └── backup/       PG dump + workspace snapshot on a 30 min timer.
├── workspace/        Agent-writable scratch. tasks/, tests/, and their _archive/ twins.
├── scripts/          68 files. Benchmarks, stress tests, one-off ops scripts.
├── modelfiles/       Ollama Modelfiles: qwen2.5-coder at 8k, 16k, 32k, 64k.
├── docs/             API.md, DEVELOPMENT.md and friends.
└── codev-specs/, roast-2026-08-04/, archive/, backups/
```

Measured size, excluding `node_modules`, `.git`, `dist`, caches:

| Area | Files | Lines |
|---|---|---|
| `scripts/` | 68 | 24,261 |
| `packages/api` | 79 | 15,703 |
| `packages/ui` | 84 | 13,453 |
| `workspace/` (agent output, not source) | 436 | 11,904 |
| `packages/agents` | 38 | 5,500 |
| `packages/mcp-gateway` | 19 | 1,973 |
| root + archive + shared | 16 | 1,514 |

Real source is roughly 38k lines across three languages. `scripts/` being the single largest
directory is itself a finding: the benchmark and ops tooling outgrew the application.

### 1.2 Dependency graph

```
ui (5173) ──HTTP──> api (3001) ──HTTP──> agents (8000) ──litellm──> Ollama (11434)
   │                   │                     │                    └─> Anthropic API
   └──socket.io────────┘                     │                    └─> xAI (Grok, undocumented)
                       │                     │
                       └──> PostgreSQL 5432  └──HTTP back──> api:3001 (execution log writeback)
```

The back-edge matters: `agents` calls `api` to persist execution logs while `api` is
synchronously waiting on `agents`. The two services are mutually dependent at runtime, not
layered.

### 1.3 `packages/api` internals

22 route modules and 30 services. The load-bearing ones:

| File | Role |
|---|---|
| `services/taskRouter.ts` | Rule-based complexity scoring plus tier selection. The IP. |
| `services/complexityAssessor.ts` | Haiku semantic pass plus the dual-assessment weighting. |
| `services/complexityCalculator.ts` | Post-execution "actual complexity" plus error categorization. |
| `services/taskExecutor.ts` | Execution lifecycle, calls the agents service. |
| `services/taskQueue.ts` | Lifecycle, rest delays between tasks. |
| `services/autoRetryService.ts` | Validate then retry ladder. |
| `services/resourcePool.ts` | Parallel slots, remote model map. |
| `services/orchestratorService.ts` | Mission lifecycle (decompose, execute, review, approve). |
| `services/stuckTaskRecovery.ts` | Watchdog. |
| `services/budgetService.ts` | Daily ceiling, can force everything to local. |
| `services/fileLock.ts` | Per-path locks for parallel work. |
| `services/humanEscalation.ts` | Terminal state for failed escalation. |
| `websocket/handler.ts` | socket.io event fan-out to the console. |

### 1.4 `packages/agents` internals

```
src/
├── main.py                  FastAPI app. /execute is the whole product.
├── orchestrator.py          decompose_prompt, review_results, clarify_intent (Anthropic SDK direct)
├── chat.py                  Streaming chat endpoint
├── agents/{coder,qa,cto,base}.py    CrewAI Agent factories, personas live here
├── tools/{file_ops,shell,search,code_validation,cto_tools,mcp_*}.py
├── monitoring/{action_history,execution_logger,token_tracker,rate_limiter}.py
├── models/{ollama,claude}.py
├── schemas/output.py        AgentOutput pydantic model + parse_agent_output
└── validators/test_validator.py
```

---

## 2. The agent loop, traced end to end

One task, from queue to persisted result.

1. **Route.** `TaskRouter.routeTask(taskId)` loads the task, lists idle agents, computes
   `calculateComplexity(task)` (rules), and if that score is `<= 8` calls
   `getDualComplexityAssessment()` which hits Haiku. The final score is written back to
   `tasks.complexity` / `complexity_source` / `complexity_reasoning`. A tier and an agent are
   selected. (`taskRouter.ts:244-452`)

2. **Assign.** `autoAssignNext()` flips the task to `assigned`, sets `assigned_agent_id`, and
   flips the agent to `busy`. (`taskRouter.ts:511-550`)

3. **Dispatch.** `taskExecutor.ts` POSTs `agents:8000/execute` with
   `{task_id, agent_id, task_description, expected_output, use_claude, model, allow_fallback, env}`.
   `env` is how remote Ollama is injected, by overriding `OLLAMA_API_BASE` for that one call.

4. **Execute.** `main.py:execute_task()`:
   - `ActionHistory.reset()` clears the global loop-detection state (`main.py:243`).
   - `get_llm()` returns a **model string** for litellm, not an object. `anthropic/...`,
     `ollama/...` or `xai/...`. (`main.py:142-178`)
   - Agent type is inferred by substring match on `agent_id`:
     `if "coder" in request.agent_id.lower()`. (`main.py:280-291`)
   - An `ExecutionLogger` is constructed pointing back at `http://api:3001`.
   - Each tool is wrapped: `agent.tools = [create_tool_wrapper(tool, execution_logger) for tool in agent.tools]`. (`main.py:318`)
   - A CrewAI `Task` and a one-agent `Crew(memory=False)` are built. `output_pydantic` is
     deliberately not used, with the comment that it "doesn't work well with Ollama models"
     (`main.py:337-338`). Structure is requested in the backstory prose instead.
   - **`sys.stdout` is redirected into a `StringIO`**, `crew.kickoff()` runs, stdout is restored
     in a `finally`. (`main.py:367-385`)
   - `execution_logger.parse_and_log_output(full_execution_log)` regex-parses that captured
     console text to recover any steps the tool wrappers missed. (`main.py:396`)
   - `parse_agent_output(raw_output=full_execution_log, ...)` builds the structured result.
   - Response returns `success`, `output`, and a `metrics` dict.

5. **Persist.** Execution logs were written by the wrapper during the run, over HTTP, to
   `api:3001`. The API writes the task result, cost and timing, then emits socket.io events.

6. **Post-process.** Depending on config: auto-retry if a `validationCommand` exists, Haiku
   review on every 5th Ollama task, Opus review on every 10th task above complexity 5.

### The critical observation

Steps 4 and 5 mean **the execution log, which the brief treats as a prize data asset, is
recovered by scraping CrewAI's verbose console output.** Fidelity is coupled to CrewAI's print
formatting. `requirements.txt` pins `crewai==0.203.2` while `CLAUDE.md` still documents
`0.86.0+`, so that formatting has moved a long way underneath the parser during the project's
life. Any retrospective analysis of the logs in W4 has to establish which log rows came from the
tool wrapper (reliable) and which from `parse_and_log_output` (format-dependent).

---

## 3. Tool calling

**Mechanism:** CrewAI `BaseTool` subclasses, dispatched by CrewAI's ReAct-style text protocol
through litellm. There is no native structured tool-calling API in the loop, and no JSON schema
constraining the model. Temperature is pinned to 0 because, per `CLAUDE.md:45-47`, anything
higher makes the 7B emit code instead of calling a tool.

**Tool surface** (`tools/file_ops.py`, `tools/shell.py`, `tools/search.py`, `tools/code_validation.py`):

| Tool | Signature | Notes |
|---|---|---|
| `file_read` | `(path)` | Workspace-relative |
| `file_write` | `(path, content)` | Rejects test files written into `tasks/` |
| `file_edit` | `(path, old_text, new_text)` | Exact match, replaces first occurrence only |
| `file_list` | `(path="")` | |
| `shell_run` | `(command)` | Per-language denylist of dangerous imports and functions |
| `code_search` | `(pattern, path)` | |
| `validate_syntax` | `(code, language)` | Pre-write syntax check |

**Containment:** every file tool does
`str(full_path.resolve()).startswith(str(Path(settings.WORKSPACE_PATH).resolve()))`.
This is a string prefix test, not a path-boundary test. It is adequate in practice because the
container's workspace has no sibling directory sharing its prefix, but it is the wrong primitive
and should not be ported as-is.

**On malformed output:** nothing structured. If the model does not emit a parseable action,
CrewAI iterates until `max_iter=25` (`coder.py:248`) or `ActionHistory` raises. There is no
grammar, no retry-on-parse-failure, no repair pass.

**Loop and runaway control** (`monitoring/action_history.py`) is the most thought-through part
of the tool layer:

- Hard cap of 50 tool calls per task.
- Per-path caps: `file_write` 3 to the same path, `file_edit` 5, `shell_run` 10 for the same command.
- Exact-duplicate detection over the last 3 actions raises immediately.
- 80 percent similarity detection over the last 5 actions warns to stdout but does not block.
- Same tool 5 or more times in the last 5 actions raises.
- On raise, the exception is caught inside each tool and returned to the model **as tool output
  text**, so the model gets told it is looping and is instructed to change approach. That is a
  good design and worth keeping.

**But:** `ActionHistory` stores `_history`, `_tool_path_counts` and `_total_calls` as **class
attributes on a singleton** (`action_history.py:31-33`). The state is process-global. `/execute`
calls `ActionHistory.reset()` at the top of every request (`main.py:243`). The agents service is
a single FastAPI process, and ABCC advertises parallel execution with two Claude slots plus one
or two Ollama slots. **Two concurrent `/execute` calls therefore share and reset each other's
loop-detection state.** Loop detection and parallel execution, both listed as V1 features, are
mutually exclusive as implemented.

---

## 4. State and persistence

PostgreSQL via Prisma. 13 models in `packages/api/prisma/schema.prisma`.

| Model | Carries |
|---|---|
| `AgentType` | coder / qa / cto, with display metadata (icon, colour) |
| `Agent` | instance, status, `current_task_id`, config JSON, stats JSON |
| `Task` | the core record. Status, priority, iterations, parent/child, mission FK, `locked_files[]`, `acceptance_criteria`, `validation_command`, cost, timing |
| `TaskExecution` | per-iteration attempt record with input/output JSON |
| `ExecutionLog` | **per tool call**: thought, action, actionInput, observation, durationMs, isLoop, input/output tokens, modelUsed |
| `CodeReview` | reviewer model, initial vs Opus complexity, findings JSON, quality score, fix attempts, token cost |
| `TrainingDataset` | paired Claude vs local execution of the same task, with quality flags |
| `Mission` | prompt, plan JSON, subtask counts, review result and score, total cost |
| `TaskMemory` | cross-task learnings with a human approval workflow |
| `FileLock` | path-unique lock rows for parallel safety |
| `Event`, `Conversation`, `ChatMessage` | event log and chat history |

**What survives a crash:** everything that reached Postgres. Tasks stuck `in_progress` are
recovered by `stuckTaskRecovery.ts`, which aborts the task, releases the agent, locks and
resource slots, and emits WebSocket events. Default timeout is **5 minutes**, with the source
comment `// 5 minutes (was 10 - tightened for faster recovery)`. Check interval 30 seconds.

**What does not survive:** anything in `ActionHistory` (process memory), and the in-flight
CrewAI run itself. There is no checkpoint mid-task. A crash at tool call 20 of 30 loses the
reasoning and restarts the task.

**Schema correction with real consequences for W4.** Migration
`20260201_simplify_complexity_model` consolidated five complexity fields into three. The schema
comment reads `// Migration note: finalComplexity → complexity, tracks source for audit`. The
current `Task` carries `complexity`, `complexitySource`, `complexityReasoning`. It does **not**
carry `routerComplexity` and `haikuComplexity` as separate columns. `CLAUDE.md:259` still
documents the old four-field layout, and the brief inherited that error.

Consequence: for any task created after 2026-02-01, the database **cannot** tell you what the
rule-based score was versus what Haiku said, except by string-parsing `complexity_reasoning`,
which happens to embed both (`Router: 3, Haiku: 7 (using Haiku - semantic complexity). ...`,
`complexityAssessor.ts:145`). That parse is recoverable but it is a text parse, not a query. W4's
plan to "judge the rule-based plus Haiku weighting retrospectively" is still possible, just more
expensive than the brief assumes.

---

## 5. Quality gates and verification

Four independent mechanisms, none of which gate the others:

1. **Syntax pre-check.** `validate_syntax(code, language)` is offered to the model as a tool and
   recommended in the persona workflow. It is advisory. Nothing forces its use.

2. **Validation command.** If a task carries `validationCommand`, `autoRetryService.ts` runs it
   via `POST agents:8000/run-validation`. Success is
   `result.returncode == 0 and "PASS" in result.stdout` (`main.py:571`). Note both conditions:
   a script that exits 0 but prints `ok` is scored a failure.

3. **Auto-retry ladder.** Phase 0 validate, Phase 1 local Ollama retry with error context,
   Phase 2 remote Ollama, Phase 3 Haiku escalation. One retry per phase by default.
   `CLAUDE.md:94` carries an honest warning that the ladder's effect on pass rate is
   **unmeasured**, because the 40-task benchmark runs each task once with no retries.

4. **Tiered LLM review.** Haiku on every 5th Ollama task, Opus on every 10th task with
   complexity above 5. Fail is `score < 6` or any critical finding, which escalates
   Ollama to Haiku to human. Results land in `CodeReview`.

**Gate independence, since W11 asks:** V1 sidesteps the problem entirely by using different
providers for building and reviewing. The builder is a local 7B, the reviewers are Haiku and
Opus. V1 therefore has no answer to the single-player question, exactly as the brief suspects.

---

## 6. Evaluation

**The 40-task corpus.** `scripts/ollama-stress-test-40.js`, results in
`scripts/ollama-stress-results-40.json`.

Distribution: C1 x3, C2 x3, C3 x4, C4 x5, C5 x5, C6 x5, C7 x5, C8 x5, C9 x5 = 40.

Each entry is:

```js
{
  complexity: 1,
  name: "double",
  description: "Create tasks/c1_double.py with: def double(n): return n * 2",
  code: "def double(n):\n    return n * 2",
  validation: "from tasks.c1_double import double; assert double(5)==10; print('PASS')"
}
```

Two things to note before anyone re-runs this. First, the low-complexity entries **embed the
reference implementation in the task description**. C1 is a transcription exercise, not a coding
exercise. Second, every task carries a real executable assertion, which is the good part, and is
why the C8 and C9 entries are worth triaging into the 2.0 eval even though the bottom of the
scale is not.

Results JSON keys: `byComplexity`, `details`, `errors`, `failed`, `model`, `passed`,
`recommendedThreshold`, `successRate`, `timestamp`, `total`, `totalDuration`.

**Other harnesses in `scripts/`:** `ollama-stress-test.js` (20 tasks C1-C8),
`ollama-stress-test-apps.js` (20 multi-file apps C6-C8), per-language variants for JS, Go and
PHP, `run-full-tier-test.js` (10 tasks across all tiers, about $1.50), `test-mission.js`,
`context-size-benchmark.js`. Archived report sets under `scripts/results-archive/` and
`scripts/json_logs_archive/`.

**Unit tests:** 17 test files in `packages/api`, 4 in `packages/agents`, 5 in `packages/ui`.
26 files total. The API service is the only one with meaningful coverage, and it covers exactly
the services you would want covered: router, complexity calculator, cost calculator, budget,
resource pool, file lock, task queue, task assigner, task executor, stuck task recovery,
scheduler, rate limiter, ollama optimizer, code review, agent manager. Coverage percentage was
not measured for this pass.

---

## 7. Configuration surface

Roughly 45 environment variables. Grouped by whether they matter.

**Load-bearing:**

| Variable | Default | Why it matters |
|---|---|---|
| `OLLAMA_API_BASE` | - | litellm will not reach Ollama without it. Also the injection point for remote execution. |
| `REMOTE_OLLAMA_URL` | empty | Presence flips the entire C7-C9 routing branch |
| `REMOTE_OLLAMA_MODEL_MAP` | empty | Per-complexity model map, e.g. `7-8:qwen2.5-coder:32k,9:qwen2.5-coder:70b` |
| `USE_MCP` | false | Disabling it moved Haiku success from 60 to 100 percent |
| `ANTHROPIC_API_KEY` | - | Absent, `get_llm` silently falls through to Ollama. See section 9. |
| `STUCK_TASK_TIMEOUT_MS` | 300000 | Watchdog |
| `AUTO_RETRY_ENABLED` and 4 siblings | - | The retry ladder |
| `OLLAMA_REST_DELAY_MS` / `OLLAMA_EXTENDED_REST_MS` / `OLLAMA_RESET_EVERY_N_TASKS` | 3000 / 8000 / 5 | Context pollution mitigation |
| `REVIEW_QUALITY_THRESHOLD` | 6 | Review pass/fail line |
| `OLLAMA_REVIEW_INTERVAL` / `OPUS_REVIEW_INTERVAL` | 5 / 10 | Review cadence |

**Tuning noise:** rate limit buffers, retry counts, timeouts, cost-per-task in cents, slot
counts, debug flags.

---

## 8. What works well

Specific, with files.

- **`taskRouter.ts:105-239`, the rule-based scorer.** Four scoring sections mapped onto
  Campbell's factors, each contributing bounded points to a 1-10 scale. Readable, debuggable,
  free, and fast. Whatever replaces it should keep the shape.
- **`complexityAssessor.ts:117-161`, the dual-assessment weighting.** The asymmetry is the
  clever part: when Haiku scores 2 or more points **higher**, take Haiku outright; when Haiku
  scores 2 or more points lower, blend 60/40 toward the router. It trusts the semantic pass to
  catch under-scoring but not to argue a task down. That asymmetry is a real insight and it
  should survive.
- **`action_history.py`, loop control.** Multi-signal, tuned thresholds, and it reports the loop
  to the model as tool output rather than just killing the run.
- **`coder.py`, the CodeX-7 persona.** Whatever its defects (section 9), the pattern of an
  in-character operator identity plus worked three-step examples plus an explicit
  write-verify-report loop is the single most transferable prompting artifact in the repo.
- **`stuckTaskRecovery.ts`.** Releases agent, locks and resource slots, not just the task. The
  cleanup is complete, which is the part people usually get wrong.
- **The console.** See section 11. It is the reason the project has users.
- **`CLAUDE.md` itself.** It flags its own unverified claims, for example the auto-retry warning
  at line 94 and the 88 versus 98 percent distinction. That is unusually honest project
  documentation and it made this dossier much faster to write.

---

## 9. What is broken, half-finished or a workaround

Ordered by how much it should influence 2.0.

### 9.1 A parse failure is reported as success

`main.py:436-447`. When `parse_agent_output()` throws, the handler builds:

```python
structured_output = AgentOutput(
    status="UNCERTAIN",
    confidence=0.5,
    summary=...,
    success=True,  # Assume success unless proven otherwise
    ...
    requires_human_review=True,
)
```

and `ExecuteResponse.success` is then set from `structured_output.success` (`main.py:479`).

**This is the failure mode the brief describes in section 7 and W6.** The brief says "V1 hit
exactly this" and treats it as a known incident. It is not an incident, it is a default, written
into the error path on purpose with a comment justifying it. Any run whose output could not be
parsed is recorded as a success with a human-review flag that nothing blocks on. This single
line is the strongest available argument for W6's "honest failure reporting" workstream, and it
should be quoted in it.

### 9.2 Abort is a no-op

`main.py:36` declares `execution_state: dict = {}`. `/execute/abort` (`main.py:592-601`) checks
`if task_id in execution_state` and deletes the entry. **`execute_task` never writes to
`execution_state`.** The dict is always empty, so the branch never fires and the endpoint
returns `{"aborted": True, "task_id": ...}` unconditionally, having aborted nothing.

There is no cancellation token threaded into `crew.kickoff()` either, so even a correct
bookkeeping fix would not stop a running task. This is worth dwelling on, because the brief's
section 7 names agency as the single biggest gap in V1 and section 8 lists pause, kill and take
over as core 2.0 features. V1 does not merely lack them. It ships an endpoint that claims to
have them.

### 9.3 The CodeX-7 backstory is textually corrupted

`coder.py:19-23`:

```
CONTEXT CAPACITY: 8K-16K tokens dynamically allocated by complexity.
For complex tasks, use file_read to gather context from related files before writing code.
This lets you understand cross-file dependencies and write consistent code.

2. **Edge Cases to Check**
```

A numbered list begins at item 2. There is no item 1 and no heading for the section it belongs
to. Something was deleted from the prompt and never repaired. The `8K-16K` figure is also stale:
8K was deprecated in March 2026 and live routing uses 16K and 32K.

So the most valuable prompting artifact in the repo has been running with a hole in it and a
wrong context figure. This is good news, not bad: it means the measured results were achieved by
a **damaged** version of the prompt, and repairing it is free upside for the 2.0 port.

### 9.4 Loop detection and parallel execution are mutually exclusive

Covered in section 3. Class-level singleton state, reset per request, in a single process that
is documented as running up to 3 or 4 tasks concurrently.

### 9.5 Silent provider fallback

`get_llm()` (`main.py:163-178`): if `use_claude` is true but `ANTHROPIC_API_KEY` is unset, the
`elif check_ollama_available()` branch takes over and the task runs on the local 7B. A task the
router deliberately escalated to Sonnet executes on the model it was escalated away from, and no
error is raised. The tier is later recomputed from `str(llm)`, so cost accounting stays
self-consistent while the routing decision is silently discarded.

### 9.6 `metrics.iterations` is hardcoded

`main.py:487`: `"iterations": 1`. Every execution reports one iteration regardless of what
happened inside CrewAI. Any analysis keying on iteration counts from this field is analysing a
constant.

### 9.7 Agent type by substring on an ID

`main.py:280-291` derives agent type from `"coder" in request.agent_id.lower()`. `Agent.id` is a
UUID in the schema. The test scripts pass friendly names like `coder-01`, so this works in
practice, but it means the API and the agents service disagree about what an agent ID is, and a
UUID containing `qa` as a substring would misroute.

### 9.8 Security items for W7

- `main.py:64-70`: CORS `allow_origins=["*"]` together with `allow_credentials=True` on the
  agents service.
- `run_validation` (`main.py:524-589`) executes a command string with `subprocess.run` in the
  workspace with no sandbox beyond the container.
- `shell.py` blocks dangerous imports by string matching per language. That is a speed bump, not
  a boundary.
- Path containment is a `startswith` prefix test.
- A populated `.env` is committed at the repo root.

None of these are surprising for a local dev tool. All of them need an answer in a public 2.0
that people point at their own repos.

### 9.9 Documentation drift

`CLAUDE.md` documents `crewai 0.86.0+`; `requirements.txt` pins `0.203.2`. `CLAUDE.md` documents
four complexity task fields; the schema has three. `CLAUDE.md` references backups at
`C:\dev\abcc-backups\daily\`; the repo's own `backups/daily/` stops on 2026-02-13 and `C:\dev`
does not exist on this machine.

### 9.10 Half-finished

- **MCP gateway**: 1,973 lines, disabled by default because it hurt success rates.
- **Grok / xAI support**: fully wired in `get_llm` and `get_model_tier` with pricing in
  `COST_RATES`, mentioned nowhere in `CLAUDE.md`.
- **`TaskMemory`**: schema, tools and an approval UI exist, but the tools ship through MCP,
  which is off. The feature is built and unreachable in the default configuration.
- **`complexityCalculator.ts`**: computes a post-execution "actual complexity" and an error
  category, which is exactly the feedback signal you would want for recalibrating the scale.
  Nothing feeds it back into routing. It writes to `complexity_source = "actual"` and stops.

---

## 10. Dependencies

**API (Node):** Express, Prisma, socket.io, `@anthropic-ai/sdk`, vitest. Not individually
version-audited this pass.

**Agents (Python):** `requirements.txt`, all pinned or floored:

```
fastapi==0.136.3          uvicorn[standard]==0.48.0
crewai==0.203.2           crewai-tools==0.76.0
langchain>=0.3.30,<0.4.0  langchain-anthropic>=0.3.22
langchain-community>=0.3.1,<0.4.0
anthropic>=0.102.0        pydantic>=2.13.4
python-dotenv==1.2.2      httpx>=0.28.1
aiofiles==23.2.1
```

`crewai` plus `crewai-tools` plus three `langchain` packages is the heaviest thing in the repo
and the part 2.0 explicitly discards. `aiofiles==23.2.1` is the one clearly old pin.

**UI:** React 19.2, `three` 0.185, `@react-three/fiber` 9.6, `@react-three/drei` 10.7,
zustand 5.0, Vite 7.3, Tailwind 4.3, vitest 4.1, socket.io-client 4.7,
react-syntax-highlighter, react-markdown, lucide-react. Current across the board. The UI stack
is in better shape than the rest of the repo.

---

## 11. Presentation layer inventory

This is the material 2.0 is explicitly extending, so it gets its own section.

**Audio:** 96 `.wav` files, 6.4 MB total, in `packages/ui/public/audio/`. Three packs (Tactical
Ops, Mission Control, Field Command), Bark TTS with radio post-processing. Driven by
`audio/audioManager.ts` (playback singleton with a queue) and `audio/voicePacks.ts`.
Regeneration script is `scripts/bark-generate-all.py`, which needs Bark plus CUDA and requires
stopping Ollama first to free VRAM. The brief's count of 96 is exactly right.

**3D battlefield**, `components/battlefield/`, 11 files: `BattlefieldCanvas`, `BattlefieldView`,
`BattlefieldCamera`, `BattlefieldLabels`, `AgentSquad`, `TaskBuilding`, `BuildingGeometries`,
`BuildingExplosion`, `ProjectileSystem`, `HolographicTable`, `ScanLine`. React Three Fiber.

**2D isometric renderer**, `components/isometric/`, 8 files: `IsometricBattlefield`,
`IsometricGrid`, `IsometricTank`, `IsometricTarget`, `IsometricProjectile`, `IsometricExplosion`,
`IsometricLabel`, and `isoProjection.ts`.

**The brief does not mention this second renderer, and it matters.** Section 3.1 lists only the
React Three Fiber battlefield. There is a complete, separate, non-3D isometric layer with its own
projection maths, tank sprites, grid and projectile system. Given that David has now specified a
full isometric C&C-style web console as the 2.0 target, this is the closest existing asset to
that target, and W5 should start from it rather than from the R3F work.

**Other console surfaces:** three minimaps (`Minimap`, `FlowMinimap`, `TimelineMinimap`),
`ToolLog` (terminal-style action feed), `TokenBurnLog`, `CodeWindow`, `CodeReviewPanel`,
`ResourceBar`, `AlertPanel`, `ComplexityDistribution`, `CostDashboard`, `SuccessRateChart`,
`AgentComparison`, `MemoryApproval`, a chat panel with `CTOWelcome` and `MissionProgressTracker`,
`ShortcutsHelp` plus `useKeyboardShortcuts`, and a theme system with two themes
(`themes/classic.ts`, `themes/battleclaw.ts`).

**Not found:** the "bounty board" named in the brief. No component, hook or route by that name.
Either it was renamed, removed, or the brief is remembering something else.

---

## 12. Corrections to brief section 3.1

| # | Brief says | Code says |
|---|---|---|
| 1 | "Routing ladder: C1-6 to local Ollama, C7-8 to Haiku, C9-10 to Sonnet" | C1-C6 local Ollama 16K; C7-C9 remote Ollama if configured, else local Ollama 32K; C10 Sonnet. **Haiku is not an execution tier at all.** It does complexity assessment, periodic review, auto-retry phase 3 and fix attempt 1. (`taskRouter.ts:356-401`) |
| 2 | "roughly 88 percent of tasks routed to the free local model" | 88 percent is a **pass rate**, 35/40 on 2026-02-05. A later run scored 98 percent, 39/40, on 2026-02-20. (`CLAUDE.md:94,368`) On a C1-C9 corpus the local routing rate would be ~100 percent by construction, since only C10 leaves. The routing-rate claim is unverified and needs the database. |
| 3 | "a Haiku semantic pass at roughly $0.001 per call" | Plausible but not asserted anywhere in code. `estimatedCost` for a haiku tier task is hardcoded `0.001` in the router; the assessor call itself is capped at `max_tokens: 300`. Treat as an estimate, not a measurement. |
| 4 | "Stuck-task detection at 10 minutes" | 5 minutes. Source comment: `// 5 minutes (was 10 - tightened for faster recovery)`. |
| 5 | "three worked examples of ideal three-step execution" | Seven: 3 Python, 1 JS, 1 TS, 1 Go, 1 PHP. (`coder.py:51-107`) And the surrounding prompt is corrupted, see 9.3. |
| 6 | "Three agent types: Coder, QA, CTO, all visible and controllable" | The three types exist, but they are **model-tier bindings wearing role names**. Routing to Sonnet selects the agent whose `agentType.name === 'qa'` (`taskRouter.ts:394`); CTO is forced onto Claude regardless of request (`main.py:286-289`). Directly relevant to W11's taxonomy reconciliation: V1's "roles" are not roles. |
| 7 | "React Three Fiber 3D battlefield" | True, and there is also a separate 2D isometric renderer the brief omits. See section 11. |
| 8 | "Auto-retry pipeline catching syntax errors and re-running with error context" | Exists, and `CLAUDE.md:94` states its effect on pass rate is **unmeasured**. No benchmark exercises it. |
| 9 | "Parallel execution ... claimed 40 to 60 percent speedup" | Claim reproduced verbatim in `CLAUDE.md:163` with no cited measurement. Also see 9.4: parallel execution corrupts loop detection. |
| 10 | "bounty board" | Not found. |
| 11 | "Target languages: Python, JS, TS, Go, PHP" | Confirmed, with per-language validation commands, test templates and denylists. |
| 12 | (not mentioned) | Undocumented xAI / Grok provider support, a full Mission orchestrator, a Battle Claw external API, a cross-task memory system, and a training-data export pipeline. V1 is substantially larger than section 3.1 describes. |

Hardware footnote: `CLAUDE.md:71` tunes everything for an **RTX 3060 Ti 8GB**. Every V1 model
choice, context size and pass rate is an 8GB result. The 2.0 box is a 5060 Ti 16GB. None of V1's
model-sizing conclusions transfer without re-measurement.

---

## 13. Observations logged for Phase 1

Recorded here as inputs, not proposals, per hard rule 1.

1. The two routing dimensions the brief wants separated in W4 are **already** conflated in code:
   `complexity >= 7` picks both the tier and the 32K context variant in one expression
   (`taskRouter.ts:382`). The separation W4 proposes is a real change, not a clarification.
2. `complexityCalculator.ts` already computes post-hoc actual complexity and an error category.
   If the database holds these, W4 gets predicted-versus-actual correlation for free.
3. `complexity_reasoning` embeds both sub-scores as text. Recovering router-versus-Haiku pairs
   post-2026-02-01 needs a string parse. Worth confirming the format is stable before W4 plans
   around it.
4. Keyword matching in `calculateComplexity` uses `text.includes(k)` with no word boundaries.
   `'api'` matches inside `rapid`, `'tree'` inside `street`, `'stack'` inside `haystack`. Cheap
   to fix, and it means the published scores carry an unmeasured false-positive rate.
5. The Haiku pass is skipped entirely when the rule-based score is already above 8
   (`taskRouter.ts:297`), so the two assessments were never compared on the hardest tasks.
6. V1 resolves gate independence by using different providers for build and review. That answer
   is unavailable in single-player mode. Confirmed as an open problem, not a solved one.
7. `Crew(memory=False)` plus rest delays plus periodic context reset means V1's answer to context
   pollution was to throw all context away between tasks. With a 35B-A3B this is worth revisiting.

---

## 14. Confidence

**High** on structure, schema, routing, complexity model, tool layer, presentation inventory and
the defects in section 9. All read directly from source at a pinned commit.

**Medium** on the evaluation history, since the results JSON was read only at the key level and
the per-task detail was not analysed. That is the data-assets deliverable's job.

**Low, and deliberately not attempted:** anything requiring a running system. No service was
started, no test suite was run, no database was opened. The claim "what works well" in section 8
means "is well-constructed in source", not "was observed working". Building and running is
authorized and is the obvious next increment if you want section 8 upgraded from a reading to a
measurement.
