# Claudette - Repo Dossier

**Repo:** `D:\dev\claudette` (public, MIT OR Apache-2.0, `github.com/mrdushidush/claudette`, published on crates.io)
**Pinned at:** `fc1ea22`, 2026-08-04, branch `main`, 470 commits, version **0.17.0**
**Read method:** static read **plus** `cargo test --lib`, which was run and passed. No model was loaded and no eval was re-run; the Q56 numbers below are read from committed results, not reproduced.
**Author of this dossier:** Claude Code, Phase 0

---

## 0. One-paragraph summary

Claudette is a single-binary Rust coding agent, roughly 60k lines in one crate, that drives one
local model over HTTP and enforces its air-gap claim structurally rather than by policy. It uses
native tool calling with a 20-group on-demand tool registry that keeps the base schema at about
200 tokens, a generic `ConversationRuntime` parameterized over an API client and a tool executor,
and a loop-control layer that responds to each failure mode with a differentiated nudge instead
of an exception. Its 1,145 unit tests pass in under 15 seconds. Attached to it is Q56, a 56-task
evaluation battery with per-task shell verifiers, no LLM judge anywhere, run across 131 model
configurations. Q56 is the most valuable single asset in the three repos, and it contains
measured findings that contradict the research brief's hardware framing.

The brief calls Claudette "the harness". That undersells it. It is the reference implementation
of nearly every mechanism 2.0 needs, and the parts it is missing are precisely the parts ABCC v1
already has.

---

## 1. Module map

### 1.1 Workspace and checkouts

Single-crate workspace. `Cargo.toml` members = `["crates/claudette"]`. The comment records why:

> `claudette` is the only crate. The dormant `forge` plumbing was folded into
> `crates/claudette/src/forge/` in v0.5.1 so the published manifest no longer carries a
> path-only workspace dependency (cargo rejects those at `cargo publish` time).

Three checkouts exist on disk, all pointing at `mrdushidush/claudette`. They are working roles,
not stale copies:

| Path | HEAD | Role |
|---|---|---|
| `D:\dev\claudette` | `fc1ea22` (470) | **canonical** |
| `D:\dev\claudette-forge` | `fc1ea22` (470) | the clone Claudette edits when working on her own code, so she cannot break the real repo |
| `D:\dev\claudette-research-control` | detached, 442 | the harness checkout used to run Q56 |

### 1.2 Crate layout

93 `.rs` files, **59,938 lines** under `crates/claudette/src`. The load-bearing modules:

| Module | Lines | Owns |
|---|---:|---|
| `runtime/conversation.rs` | 3,611 | **the agent loop.** `ConversationRuntime`, turn execution, iteration budget, loop breakers |
| `api.rs` | 3,168 | **the model boundary.** Ollama-native `/api/chat` and OpenAI-compat, streaming, tool-call parsing, context budgeting |
| `run/research.rs` | 2,535 | batched whole-repo research mode |
| `tools.rs` | 2,271 | tool schema assembly, dispatch, path resolution, workspace roots |
| `commands.rs` | 2,195 | slash commands |
| `run/forge_run.rs` | 1,687 | the forge pipeline driver (fix rounds, scoring, security stage) |
| `tools/quality.rs` | 1,464 | `run_tests`, `diagnostics`, `apply_patch` |
| `tools/repomap.rs` | 1,424 | concept-level code localization |
| `tools/search.rs` | 1,410 | grep / glob / web, workspace-rooted |
| `main.rs` | 1,391 | CLI |
| `tools/github.rs` | 1,331 | GitHub + brownfield missions |
| `telegram_mode.rs` | 1,234 | Telegram bot (feature-gated) |
| `tools/shell.rs` | 1,173 | `bash`, background bash |
| `scheduler.rs` | 1,148 | proactive reminders |
| `security_review.rs` | 1,140 | security review stage |
| `recall.rs` | 1,132 | cross-session semantic recall over SQLite |
| `tui.rs` + `tui/render.rs` + `tui_worker.rs` | 2,487 | Ratatui TUI |
| `transcript.rs` | 932 | action journal, undo, secret redaction |
| `tool_groups.rs` | 864 | **the on-demand tool registry** |
| `runtime/compact.rs` + `run/compaction_policy.rs` + `runtime/context_evict.rs` | 1,498 | context management |
| `egress.rs` | 569 | **air-gap enforcement** |
| `runtime/permissions.rs` | 620 | permission tiers and operations |
| `brain_selector.rs` | 716 | model selection |
| `secrets.rs` | 420 | secret detection and redaction |

`src/tools/` holds 28 tool modules. `src/runtime/` holds 10. `src/forge/` holds 4.

### 1.3 Non-source assets

| Dir | Files | What |
|---|---:|---|
| `runs/` | 11,873 | **19 dated campaigns of real run data.** The data asset. |
| `editor/` | 12,706 | VS Code extension (mostly `node_modules`) |
| `plans/` | 119 | per-sprint task specs, written before the work |
| `docs/` | 29 | including `docs/archive/mtp_benchmark.md` |
| `tests/` | 69 | benchmark harness data, no `.rs` targets; excluded from the published crate |
| `launch-drafts/` | 56 | release write-ups, including two full benchmark write-ups |

---

## 2. The agent loop

The loop lives in `ConversationRuntime<C, T>` (`runtime/conversation.rs:237`), generic over two
traits declared in the same file:

```rust
trait ApiClient  { fn stream(&mut self, request: &ApiRequest<'_>) -> Result<Vec<AssistantEvent>, RuntimeError>; }
trait ToolExecutor { fn execute(&mut self, tool_name: &str, input: &str) -> Result<String, ToolError>; }
```

That is the whole seam. The model and the tools are both injected, which is why the crate is so
testable and why 1,145 unit tests can cover the loop without a running model.

**Entry point:** `run_turn` / `run_turn_with_images` (`conversation.rs:349-879`). One turn is:
build the system prompt, call `stream`, classify the returned `AssistantEvent`s, dispatch any
tool calls, append results, repeat until the model stops calling tools or the iteration budget
runs out, then return a `TurnSummary`.

**Builder configuration:** `with_max_iterations`, `with_graceful_iteration_cap`,
`with_auto_compaction_input_tokens_threshold`, `with_unknown_tool_hinter`.

### What makes this loop different from ABCC's

ABCC's loop control raises an exception and hands the model a generic "you are stuck" string.
Claudette's loop has a **separate, purpose-written response for each failure mode**, all in
`conversation.rs`:

| Situation | Response | Line |
|---|---|---|
| Iterations running low | `iteration_budget_nudge(remaining)` tells the model its remaining budget | 57 |
| Unknown tool called | `build_unknown_tool_body(tool, suggestions)` returns near-miss suggestions | 1210 |
| Too many searches | `search_budget_nudge(n)` | 1237 |
| Same call repeated | `duplicate_call_body(tool)` | 1278 |
| Same *edit* repeated | `duplicate_edit_body(tool)` - different text for block-edit tools | 1303 |
| Repeat of a denied call | `duplicate_denied_body(tool)` | 1319 |
| Re-reading an unchanged file | `unchanged_read_notice(path, reads)`, keyed on `content_hash` | 1443 |
| Iteration cap reached | `iteration_cap_landing` + `iteration_cap_fallback_reply(last_error)` - a graceful landing that reports the last real error rather than a bare timeout | 879, 1377 |
| Model returned nothing | `turn_produced_no_content` → `empty_turn_retry_ceiling(attempt, num_ctx)` → `empty_turn_error` | 1033-1123 |

The empty-turn path has its own campaign in `runs/empty-stream-flake-2026-07-17`, so it was
found in the wild and fixed with evidence.

**Context management is automatic and layered:** `maybe_auto_compact` (`conversation.rs:983`)
fires on an input-token threshold, `apply_context_eviction` drops tool output,
`runtime/compact.rs` does the summarization, and `run/compaction_policy.rs` decides between soft
and hard compaction. Thresholds are `CLAUDETTE_COMPACT_THRESHOLD` and
`CLAUDETTE_SOFT_COMPACT_THRESHOLD`.

---

## 3. Tool calling

The brief calls this the highest-value thing in Claudette and the biggest gap in ABCC v1. It is,
and the gap is wider than the brief suggests.

### 3.1 Mechanism

**Native tool calling.** From `api.rs`'s own header:

> Uses native tool calling: passes a `tools` array on every request and parses
> `message.tool_calls` from the response.

Also `think: false` on the request so reasoning models skip chain-of-thought.

This is a categorical difference from ABCC, which relies on CrewAI's ReAct-style text protocol
and recovers its logs by scraping stdout. Claudette asks the server for structured tool calls and
reads them out of the response object.

### 3.2 The on-demand tool registry - the single best idea in the repo

`tool_groups.rs`. Twenty groups: Notes, Todos, Files, Meta, Git, Ide, Search, Advanced, Facts,
Registry, Github, Telegram, Calendar, Schedule, Gmail, Recall, Quality, Semantic, Vision,
Clipboard.

Only **three** tools ship on every request: the synthesized `enable_tools` meta-tool,
`get_current_time`, and `load_workspace_rules`. Everything else is gated behind
`enable_tools(group)` and appears on the *next* turn.

The rationale is measured and stated in the module header:

> Pre-rewrite the baseline was ~2,500 tokens (43 tools shipped per turn in TUI/Telegram). Now
> it's ~200 tokens, with each group adding only the tools it owns when the model asks for it.

The registry is `Arc<Mutex<_>>`-shared between `OllamaApiClient` (reads it to build the `tools`
field) and `AgentToolExecutor` (writes it when the model calls `enable_tools`).

### 3.3 The `enable_tools` spiral, and the fix

This is the most transferable finding in the repo, and it is a **failure** of the idea above.

From `runs/eval-2026-05-29/battery/REPORT.md`, root-caused from `lms log stream`:

> q3 routinely emits the call with the required `group` arg **dropped entirely** -
> `<function=enable_tools></function>` - **415 such errors** in the baseline capture. With no
> tools enabled it either gave up and explained (A1) or retried the empty call until the 150s
> timeout (B1, B2, B5).

The fix was two-part and is the pattern 2.0 should inherit whole:

1. **Workspace-gated pre-enable.** When `CLAUDETTE_WORKSPACE` is set, pre-enable a lean **coding
   core** = Files + Search + Advanced + Quality, about 2.2k tokens
   (`ToolGroup::coding_core()`, `tool_groups.rs:183`). The long-tail integration groups stay
   lazy.
2. **A forgiving `enable_tools`.** An empty or missing `group` enables the coding core instead of
   erroring (`executor::run_enable_tools`).

Result: `enable_tools: missing` errors went to **zero**, and tasks got *faster* because the
wasted round-trips disappeared. B1 went from a 150s timeout to 42s; B2 from 160s to 31s.

The lesson generalizes past this one bug: **a token-saving indirection that a small model cannot
reliably operate costs more than it saves.** Claudette kept the mechanism and removed the
requirement to use it.

### 3.4 Schema economy, enforced by tests

The token budget is defended by unit tests, which is unusual and worth copying:

- `enable_tools_group_param_has_no_redundant_description` - the per-property description would
  duplicate the function description.
- `enable_tools_schema_has_no_enum` - the `enum` on `group` was removed to save about 37 tokens
  per turn; server-side validation plus a clear error message is enough for the model to recover.
  The test exists so nobody silently re-adds it.
- `coding_core_schema_stays_lean` - asserts the pre-enabled core stays under 16,000 chars.
- `every_advertised_tool_is_classified` - catches the class of bug where a new tool is added to
  the schema but not to a group, so the registry silently drops it. The comment names the
  incident: `note_update` shipped invisibly until v0.2.3.

There is also a `schema_size_report` test that exists purely to print the numbers so they can be
cited without re-deriving them.

### 3.5 Small-model findings recorded in the code

Two comments in `tool_groups.rs` are worth quoting into W1 and W11 verbatim:

- On group summaries: "Brain100 on 4b regressed from 94% to 84% when we tried a terser variant -
  the verb decomposition is load-bearing on small models."
- On a `describe_group` tool that was tried and removed: "qwen3.5-4b couldn't figure out how to
  call it and the manifest already carries the verb hints."

### 3.6 Path resolution and containment

`tools.rs` does this properly, and the contrast with ABCC's `startswith` prefix test is stark.

- `WorkspaceRoots` (`tools.rs:571`) is a value type resolving three allowed roots: process cwd,
  `CLAUDETTE_WORKSPACE` entries, and `$HOME`. It has a `startup_diagnostics` that warns loudly
  when the resolution would deny most reads.
- `CLAUDETTE_WORKSPACE` is `PATH`-style multi-root, `;` on Windows and `:` on Unix.
- `validate_read_path` is the shared envelope. `grep_search` got workspace rooting in v0.8.0 and
  `glob_search` was missed - which is Gap 2 in the Q56 report, where the model globbed
  `**/stats.py`, searched `C:\Users\david\**`, matched 13 decoy files from old scikit-learn
  checkouts and read the wrong file. Fixed by giving glob the same root priority.
- The **F5 fallback** (`tools.rs:505-521`) closes what the comment calls "the silent-
  hallucination footgun": launched from `$HOME`, asked to read `crates/foo/bar.rs`, the path
  joined to cwd, the file was not there, and the brain papered over the missing-file error with a
  hallucinated answer. Now unresolvable relative paths are probed against each workspace root.

### 3.7 Post-edit verification

`tools/post_edit_check.rs` (572 lines) plus `CLAUDETTE_POST_EDIT_CHECK`, `CLAUDETTE_CHECK_CMD`,
`CLAUDETTE_CHECK_MAX_ROUNDS`, `CLAUDETTE_CHECK_TIMEOUT_SECS`. Edits are checked after
application rather than trusted. `tools/near_miss.rs` powers the unknown-tool suggestions and
`tools/fuzzy_apply.rs` (840 lines) does tolerant before/after patching, which is what makes
`apply_diff` survive a model that gets whitespace slightly wrong.

---

## 4. State and persistence

No database server. Everything is files under `~/.claudette/`, which is a large part of why the
install story is one binary.

| Store | Backing | Contents |
|---|---|---|
| Session | `runtime/session.rs`, `CLAUDETTE_SESSION` | conversation history, resumable |
| Transcript | `transcript.rs` (932 lines) | **action journal with undo** |
| Recall | `~/.claudette/recall.sqlite` via `rusqlite` bundled | cross-session semantic memory, one `recall(query, k)` tool |
| Schedule | `~/.claudette/schedule.jsonl` | proactive reminders |
| Notes / todos | files under the claudette data home | |
| Files | `~/.claudette/files/` | screenshots and scratch |

**The transcript is the standout.** Its tests describe the guarantees better than prose can:

- `record_redacts_secrets_before_writing_to_disk`
- `undo_last_turn_restores_every_action_of_the_turn`
- `undo_never_destroys_newer_content_at_the_original_path`
- `undo_refuses_restore_target_outside_allowed_roots`
- `undo_refuses_trash_source_outside_trash_dir`
- `undo_twice_restores_both_entries_of_a_same_millisecond_batch`
- `move_to_trash_relocates_and_survives_name_collision`

Deletes go to a trash directory rather than being destroyed, undo is per-turn or per-action, and
the restore path is itself bounded. This is a real answer to the brief's "human in the loop"
requirement and it already exists.

**Crash survival:** sessions and transcripts are on disk per turn, so a crash loses the in-flight
turn and nothing else. Note the deliberate `panic = "abort"` in the release profile, with a
comment spelling out the consequence: any panic kills the process and the agent loop does **not**
survive a panicked turn, so fallible parsing must be panic-free rather than relying on unwind
recovery.

---

## 5. Quality gates and verification

Four layers, and unlike ABCC they compose.

1. **The `Quality` tool group**: `run_tests`, `diagnostics` (cargo check / clippy / tsc / mypy /
   ruff), `apply_patch` (atomic multi-file unified diff). These are tools the model calls, and
   they are in the pre-enabled coding core, so a coding session always has them.
2. **Post-edit check** - see 3.7. Runs after an edit, bounded by `CLAUDETTE_CHECK_MAX_ROUNDS`.
3. **The forge fix loop** - `run/forge_run.rs`. `DEFAULT_MAX_FIX_ROUNDS = 3`
   (`CLAUDETTE_MAX_FIX_ROUNDS`), with round scoring and a `best_round` selector. The code
   explicitly prevents restoring a high-scoring round that the security stage rejected.
4. **Security review stage** - `security_review.rs` (1,140 lines), opt-in via
   `CLAUDETTE_FORGE_SECURITY_REVIEW`, with `CLAUDETTE_FORGE_SECURITY_OVERRIDE` as the escape
   hatch.

**Permissions** (`runtime/permissions.rs`): five modes - `ReadOnly`, `WorkspaceWrite`,
`DangerFullAccess`, `Prompt`, `Allow` - plus a structured `Operation` enum (`ReadFile`,
`WriteFile`, `Execute(argv)`, `Network(url)`, `Other{reason}`) so the prompter can say
`read /etc/passwd` instead of showing a JSON blob. The header is honest that policy still keys
off the tool name and that operation-level inference is future work.

Guarded by dedicated env flags: `CLAUDETTE_ALLOW_DESTRUCTIVE_GIT`, `CLAUDETTE_ALLOW_SECRET_READS`,
`CLAUDETTE_ALLOW_REMOTE_OLLAMA`, `CLAUDETTE_WEB_FETCH_ALLOW_PRIVATE`.

### The air gap is structural, not configured

Two independent mechanisms, and this is the part a public 2.0 should study closely.

**Compile-time.** `default = []` in `Cargo.toml`. The comment:

> Claudette ships as a lean, air-gapped *coding agent*. The default `cargo install claudette` /
> release binary contains NO cloud code - no Google/Telegram, no voice/tts/briefing - so it
> cannot reach those services even by misconfiguration; the air-gap guarantee is structural, not
> a setting.

`integrations` opts back in and pulls exactly one real dependency (`getrandom`, for OAuth state).

**Runtime.** `egress.rs`. `--offline` or `CLAUDETTE_OFFLINE=1` checks every outbound destination
against an allow-list of the resolved local backend host plus loopback. Two enforcement layers,
because not all egress is in-process:

1. HTTP layer - `guard()` on the resolved host inside the reqwest path of every network tool.
2. Dispatch/subprocess layer - `guard_subprocess()` for things reqwest cannot see: `git_push`,
   `git_clone`, the brownfield mission clone and submit, and the edge-tts subprocess.

Both refuse with the same uniform message so the refusal reads identically regardless of which
path tripped it. The allow/deny decision is a pure function and is unit-tested.

This is a far better answer to the brief's "data sovereignty, honestly stated" requirement than
anything the brief proposes, and it is already built.

---

## 6. Evaluation: Q56

The brief's W8 does not know this exists. It should be the starting point of W8, and much of W1
and W2 is already answered by it.

### 6.1 Structure

Location: `runs/eval-2026-05-29/battery/`.

- **Q50 core**, defined by `manifest.tsv`: 50 tasks, one row per task, columns
  `id, surface, task_type, fixture, timeout_secs`.
- **K1-K8 extension**: 8 further tasks with their own prompts and verifiers. Q50 + K = **Q56**.
- **Coverage**: 11 languages and surfaces (Rust, Python, JS, TypeScript, Go, shell, HTML, CSS,
  SQL, a large real repo, and a git repo), 12 task types (bugfix, add-feature, multi-file edit,
  refactor, create-file, explain, locate-symbol, enumerate, run-tests, debug-from-error,
  git-workflow, answer-from-codebase).
- Per-task timeouts range 120-240 seconds, set per task in the manifest.

### 6.2 How it verifies - this is the important part

Each task has `prompts/<id>.txt` and `verify/<id>.sh`. The contract in `verify/_lib.sh`:

```
verify/<id>.sh <WORKDIR> <TRANSCRIPT>
print exactly one "RESULT: PASS — ..." or "RESULT: FAIL — ..." line; always exit 0
```

Helpers: `pass`, `fail`, `tc` (transcript contains literal), `tcre` (transcript matches regex),
`tcount` (count of ground-truth tokens present).

Three verification modes, chosen per task:

1. **Real execution.** A1 runs `cargo test --quiet` in the workdir and greps for
   `test result: ok`.
2. **File state.** K2 checks the fixed C++ source contains `+ 32` and no longer contains `- 32`,
   with a comment explaining the choice: no C++ toolchain on the box, and `32` appears nowhere
   else in the fixture so the check is unambiguous.
3. **Transcript ground truth.** For explain and locate tasks, regex over the transcript.

**There is no LLM judge anywhere in the loop.** That is a design commitment, and combined with a
frozen core-50 it is what makes 14 months of score rows comparable.

### 6.3 The traps

David described Q56 as having traps in each task. The clearest is **I3**:

```
prompt: What is the default maximum number of forge fix-loop rounds, and where is that value
        set? Answer from the actual source code.

verify: # GT: source const DEFAULT_MAX_FIX_ROUNDS = 3 (run.rs). Stale docs say 2 — the trap.
```

The repo genuinely contains four doc files saying 2 and one source constant saying 3. The task
measures whether the model resists stale documentation. That is a real agentic failure mode and
almost nothing in the public benchmark landscape tests it.

The verifiers are also written defensively against their own brittleness. C6 checks three
independent signals so an explanation saying "buckets" instead of "arrays" still passes, with a
comment saying exactly that. The report also records a **verifier false-negative** on C6 that was
found, corrected, and re-verified against the unchanged transcript rather than quietly rescored.

### 6.4 Scale of what has been run

- **131** `logs-<config>` directories, one per model configuration.
- Roughly **90** `SCORES-*.tsv` result tables.
- Harness scripts: `run_battery.sh`, `run_model_eval.sh`, `run_screener.sh`, `analyze.sh`,
  `probe_speed.sh`. A screener tier (SCREEN-10) and a smoke tier exist for cheap triage before
  committing to a full battery.
- Analysis documents: `REPORT.md`, `CHAMPION-DOSSIER.md` (22 KB), `MODEL-COMPARISON.md` (24 KB),
  `CANDIDATES.md`, `SCREENER.md`, `champion-launch.md`.
- Failed and aborted runs are kept and labelled in the filename, for example
  `SCORES-q50-coder30b-PARTIAL-KILLED-thermal-2026-07-25.tsv` and
  `SCORES-coder30b-BROKEN-template-32k.tsv`. Negative results were not deleted.

Models evaluated include the Qwen 3.5 and 3.6 families at several sizes, Qwen3-Coder-30B,
gpt-oss-20b, GLM 4.7 Flash, Granite 4.1 8B, Devstral, Gemma variants, and Nemotron variants.

### 6.5 The champion

`CHAMPION-DOSSIER.md`, campaign 2026-07-11. Decision matrix:

| config | PASS/50 | K/8 | wall | gen tok/s | spill |
|---|---:|---:|---:|---:|---|
| `champ-q3kxl-lms` (incumbent) | 47 | 8 | 32.2 m | 33.8 | ~5 GB experts to RAM |
| `champ-iq4xs-lms` | 50 | 8 | 32.2 m | 27.8 | ~6 GB experts to RAM |
| `champ-q4kxl-lms` | 48 | 8 | 28.7 m | 36.0 | ~9 GB experts to RAM |
| `champ-mtp-q4kxl-llsrv` | screen 10/10 | 7 | - | 43.1 | fit-target 2304 |
| **`champ-bs-mtpgpu2-lms`** | **50** | **8** | **10.1 m** | **76.3** | **zero, fully resident** |
| same, at 64k ctx | 49 | 8 | 14.6 m | 69.8 | zero (15.4 of 16.3 GiB) |

**Crowned:** byteshape `Qwen3.6-35B-A3B-MTP-GGUF` MTP-GPU-2, 3.06 bpw, 13.6 GB, in LM Studio, ctx
65536, KV q8_0, no-mmap, parallel 1, MTP draft-max 2. Runner-up and same-lineage fallback:
unsloth UD-IQ4_XS.

---

## 7. Configuration surface

**65 `CLAUDETTE_*` environment variables.** Grouped by what actually matters for 2.0:

**Model boundary:** `CLAUDETTE_MODEL`, `CLAUDETTE_NUM_CTX`, `CLAUDETTE_NUM_PREDICT`,
`CLAUDETTE_OPENAI_COMPAT`, `CLAUDETTE_FALLBACK_BRAIN_MODEL`, `CLAUDETTE_VISION_MODEL`,
`CLAUDETTE_VRAM_GB`, `CLAUDETTE_MODEL_RELOAD_RETRY_MS`, `CLAUDETTE_DISABLE_MODEL_RELOAD_RETRY`,
`CLAUDETTE_SKIP_LM_STUDIO_PROBE`, `CLAUDETTE_SKIP_OLLAMA_PROBE`. Plus `OLLAMA_HOST` for the URL.

**Loop and context:** `CLAUDETTE_MAX_ITERATIONS`, `CLAUDETTE_COMPACT_THRESHOLD`,
`CLAUDETTE_SOFT_COMPACT_THRESHOLD`, `CLAUDETTE_EVICT_TOOL_OUTPUT`, `CLAUDETTE_READ_LOOP_LIMIT`,
`CLAUDETTE_NO_READ_LOOP_BREAKER`, `CLAUDETTE_READ_DEFAULT_LINES`, `CLAUDETTE_MAX_TOOLS`.

**Safety:** `CLAUDETTE_OFFLINE`, `CLAUDETTE_AUTO_APPROVE`, `CLAUDETTE_ALLOW_DESTRUCTIVE_GIT`,
`CLAUDETTE_ALLOW_SECRET_READS`, `CLAUDETTE_ALLOW_REMOTE_OLLAMA`,
`CLAUDETTE_WEB_FETCH_ALLOW_PRIVATE`.

**Forge:** 11 `CLAUDETTE_FORGE_*` plus `CLAUDETTE_MAX_FIX_ROUNDS`, `CLAUDETTE_CHECK_*`,
`CLAUDETTE_POST_EDIT_CHECK`.

**Workspace:** `CLAUDETTE_WORKSPACE` (multi-root), `CLAUDETTE_SESSION`, `CLAUDETTE_MEMORY`,
`CLAUDETTE_RECALL_*`.

Defaults worth carrying: `DEFAULT_NUM_CTX = 16384`, `DEFAULT_NUM_PREDICT = 6144`,
`REQUEST_TIMEOUT_SECS = 300`, `CHARS_PER_TOKEN = 4`, `SAFETY_CHARS = 1024`.

---

## 8. The forge module and the role taxonomy

`src/forge/` is what survived the fold-in from `claudettes-forge`: `types.rs`, `personas.rs`,
`models_toml.rs`, `mod.rs`. `types.rs` is candid about what was dropped:

> The pipeline-vocabulary types (`Mission`, `Subtask`, `MissionId`, `Complexity`, `ToolCall`,
> `ToolResult`) were duplicates of types claudette's runtime owns elsewhere and never reached the
> live orchestrator in `run.rs`; they were dropped 2026-05-15 after the multi-agent audit.

**`Role` - the eight roles that survived:**

| Role | Job, per the doc comment |
|---|---|
| `Assistant` | conversational loop, default no-subcommand mode |
| `Planner` | mission decomposition, **Campbell-complexity tagging** |
| `Router` | complexity router and model selector |
| `Coder` | code generation |
| `TestCoder` | test generation |
| `Verifier` | correctness grading |
| `SurgicalCoder` | surgical fix pass, patches specific compile/test failures |
| `Cto` | strategic review at Gate, ship / no-ship call |

Two things matter here for W11.

First, **Campbell complexity travelled from ABCC into Claudette**. The brief treats the
complexity model as an ABCC-only asset to be ported; it has already made one jump, into a Rust
type, and the `Planner` role owns it. That is a live precedent, not a hypothesis.

Second, the type comment states the naming principle explicitly: "A single model can fill
multiple roles simultaneously - role naming is about *what the model is doing*, not about which
weights are loaded." That is the direct answer to the tension the brief poses in section 10 about
gate independence in single-player mode, and it disagrees with ABCC v1, where "agent types" were
model-tier bindings wearing role names.

`ProviderKind` has exactly two variants: `Ollama` and `AnthropicClaude` (feature-gated, v0.2).
That is the whole provider abstraction today, and W10 should treat it as a starting point rather
than a finished design.

**Personas** (`personas.rs`) are markdown files with YAML frontmatter carrying `name`, `role` and
`status`, a body, and an optional `## Example moments` section parsed into structured examples.
There is a bundled directory and a user directory that overrides it. This is the CodeX-7 idea
from ABCC, rebuilt as data with a loader, a parser, an override path, and 12 unit tests. The
persona A/B campaigns are in `runs/persona-2026-06-21` and `runs/persona-ab-2026-06-22`.

---

## 9. What works well

- **The `ApiClient` / `ToolExecutor` trait seam.** Two small traits and the entire loop becomes
  unit-testable without a model. This is why the test suite is both large and fast.
- **The on-demand tool registry**, with the caveat in 3.3 that its gating had to be relaxed.
- **Differentiated loop breakers.** Nine distinct situations, nine purpose-written messages back
  to the model.
- **The transcript and undo system.** Trash rather than delete, per-turn and per-action undo,
  bounded restore targets, secret redaction before write.
- **Structural air-gapping.** Compile-time feature default plus a two-layer runtime guard.
- **Q56.** Objective verifiers, no LLM judge, frozen core, negative results retained.
- **Tests as executable design documentation.** `enable_tools_schema_has_no_enum` and
  `coding_core_schema_stays_lean` encode *why* the code is shaped the way it is, so the reason
  survives refactoring.
- **Comment discipline.** Nearly every non-obvious decision carries the measurement and the
  regression that motivated it. This dossier was fast to write because the code explains itself.
- **`unsafe_code = "forbid"`**, clippy `all` + `pedantic` at warn with each allow individually
  justified.
- **Dependency restraint.** No tokio, no async runtime at all - `reqwest` blocking. No openssl,
  rustls only. `image` restricted to PNG. `getrandom` instead of all of `rand`. For a
  RAM-constrained single-binary tool this is exactly right.

---

## 10. What is broken, half-finished or a known workaround

Much shorter than ABCC's equivalent section, and most items are self-declared in the code.

1. **Permissions are tool-name-keyed, not operation-keyed.** The `Operation` enum exists and is
   consumed only by the prompter. The header says operation-level tier inference is the intended
   replacement. So the richer model is built but not yet load-bearing.
2. **`panic = "abort"` means no turn-level recovery.** Documented deliberately, but it does mean
   a single panic on malformed input kills a session. For a long-running 2.0 orchestrator this is
   a design decision to revisit rather than inherit.
3. **`ProviderKind` has two variants and one of them is feature-gated.** There is no real
   multi-provider abstraction yet. W10 starts near zero here.
4. **Create-file routes through a second model pass.** From the Q56 report: "create a new file"
   goes through `generate_code`, a second coder-model pass, and q3 over-thought a trivial
   function past the 150s cap on C4 and F2. The recommended fix - route simple signature-known
   creation to a direct `write_file` - was written down and deliberately **not** applied
   unsupervised. Still open as of that report.
5. **B4's clean-exit wart.** A task that accomplished its work but did not terminate before the
   cap. Called "a real UX wart worth a follow-up (clean-exit-on-done)".
6. **Known model-bound failures, honestly triaged.** I1 under-enumerates in a large repo; I3
   trusts stale docs. The report calls these "genuine model limits, not harness bugs" and the
   4-bit jump later bought both back.
7. **`forge` is a partial fold.** Four files remain of a seven-crate project; most of the
   pipeline vocabulary was dropped as duplicative. What is left is roles, personas and a model
   map, not a pipeline.
8. **Amputations are visible in the tests.** `group_of("tv_get_quote") == None` with the comment
   "a web scraper has no place in an air-gapped coding agent". Healthy, but it means the tool
   surface has churned and some group boundaries are historical.
9. **`CLAUDETTE_ZZZ_TEST_NONEXISTENT_ABC_TOKEN`** is a test sentinel living in the production env
   surface. Cosmetic.

---

## 11. Dependencies

Nineteen direct dependencies, every one justified by a comment. Notable:

```
reqwest 0.12  (blocking, rustls-tls, json, multipart — no openssl)
serde 1 / serde_json 1 / toml 1 / chrono 0.4 / cron 0.17
anyhow 1.0 / dotenvy 0.15 / colored 3 / glob 0.3 / scopeguard 1
regex 1          — coding models write ripgrep-style regex; literal substring matched none
ignore 0.4       — ripgrep's walker; respects .gitignore, skips target/ and node_modules
ratatui 0.30 (default-features off, crossterm) / crossterm 0.29
arboard 3 / image 0.25 (png only)
rusqlite 0.39 (bundled)   — single-binary install, no system sqlite
getrandom 0.4 (optional, `integrations` only)
```

`rust-version = "1.88"`, edition 2021. **No async runtime.** Nothing here looks stale or
unmaintained; `ratatui 0.30` and `crossterm 0.29` are current majors.

---

## 12. Size and test coverage

| Metric | Value |
|---|---|
| Source | 93 files, 59,938 lines |
| `#[test]` functions | 1,274 in source |
| **`cargo test --lib` result** | **1,145 passed, 0 failed, 6 ignored, 14.76 s** |
| Version | 0.17.0 |
| Commits | 470 |

**The 14.76 second full-suite run is a finding in its own right.** W13 asks how long a full test
run takes because agent loop latency is bounded by it. For a 60k-line crate this is close to
ideal, and it is a direct consequence of the trait seam in section 2 - almost nothing needs a
running model to be tested.

---

## 13. Corrections to the brief

Section 3.2 is short, so most of these are additions. Two of them reach outside section 3.

### 13.1 Section 3.2

| # | Brief says | Reality |
|---|---|---|
| 1 | "currently running Qwen 3.6 35B-A3B as its daily driver **under llama.cpp**" | **LM Studio** is the daily driver, confirmed by David and by every crowned config. llama.cpp `llama-server` was benchmarked as an alternative and is *not* the production path. Claudette reaches it over HTTP either way. |
| 2 | "with `--n-cpu-moe` expert offload" | See 13.2. Expert offload was **abandoned** on 2026-07-11. |
| 3 | "mmap disabled deliberately" | Correct, and measured: `--no-mmap` is worth +9.4% tok/s and +10.2 GB free RAM. |
| 4 | "the tool-calling implementation" as the thing inherited | Correct but far too narrow. See sections 2-5: the loop, the transcript and undo, the permission model, the egress guard and the compaction stack are all equally portable and equally absent from ABCC. |
| 5 | "the eval loop" | It is Q56, a 56-task battery with objective per-task verifiers run across 131 configurations. Section 6. |
| 6 | "Real harness data from actual daily use" | 19 dated campaigns and 11,873 files under `runs/`. |
| 7 | (not mentioned) | Claudette **already ships a Ratatui TUI**, a VS Code extension, a Telegram bot, a scheduler, Gmail and Calendar tools, and cross-session semantic recall. It is a personal assistant that is also a coding agent. |
| 8 | (not mentioned) | The `forge` fold-in carries **Campbell complexity into Rust** via the `Planner` role. The complexity model has already made the jump the brief proposes. |

### 13.2 Section 5 - the hardware constraint framing is out of date

This is the most consequential correction in this dossier.

The brief's section 5 states: "**32GB system RAM is the ceiling, not 16GB VRAM.** MoE under
llama.cpp with `--n-cpu-moe`, mmap off." Every concurrency and residency question in W1, W2 and
W11 is framed on that basis.

That describes the **incumbent** configuration - `champ-q3kxl-lms`, which spilled about 5 GB of
experts to RAM. It was superseded on 2026-07-11 by a config that **spills nothing**. From
`CHAMPION-DOSSIER.md`:

- `--cpu-moe` was measured at **1.16x only - "worse than fit-target packing"**, with the verdict
  "don't use".
- The crowned config runs **0 CPU experts, fully VRAM-resident**, at 15.4 GiB of 16.3 GiB.
- The speed decomposition is explicit: at 24k, NTP 67.34 vs MTP-d2 76.31; at 64k, 68.71 vs 69.77.
  Conclusion in the document: **"Residency is ~90% of the win; MTP in LMS is a small bonus."**
- And the general statement: "**VRAM residency** ... is the biggest single lever on this card".

The lever was quantization lineage, not offload. byteshape's ShapeLearn per-tensor learned
datatypes fit 35B-A3B into 13.6 GB at 3.06 bpw and **tied the best quality score on the battery**
(50/50 + K 8/8), with 4.1 GB less than the unsloth 4-bit that also scored 50/50. The document
records that this defeated the project's own prior: "The '3-bit damage' precedent does NOT apply
to ShapeLearn's learned per-tensor datatypes."

So the binding constraint is not 32 GB of system RAM. On the crowned configuration system RAM is
barely involved. **W1 and W2 should be reframed around staying resident in 16 GB rather than
around surviving expert offload into 32 GB.** That is a different research question with
different answers, and it makes 32 GB versus 64 GB much less decisive than open question 9
assumes.

### 13.3 Section 6 and W2 - the central question is already answered

The brief lists "llama.cpp as the inference engine" as a settled decision and makes "how does the
Rust orchestrator talk to llama.cpp" the central question of W2, offering an OpenAI-compatible
HTTP server, in-process bindings such as `llama-cpp-2`, or something else.

Claudette answered this. `api.rs` speaks HTTP in two dialects: Ollama-native `/api/chat`, and
OpenAI-compatible when `CLAUDETTE_OPENAI_COMPAT=1`. There are no in-process bindings and no FFI.
Pointing it at LM Studio is `OLLAMA_HOST=http://localhost:<port>` plus the compat flag
(`api.rs:204-296`, cited in the champion dossier and used verbatim by the battery harness).

The same surface reached LM Studio, `llama-server`, and Ollama across the campaign, and
template and tool-call parity through `llama-server --jinja` was explicitly proven. W2 should
start from "keep the HTTP surface, here is the measured evidence" and spend its effort on
concurrency, prefix caching and grammar-constrained decoding, which are genuinely open.

The engine decision is also worth restating in the brief: the settled choice is **LM Studio, which
runs llama.cpp underneath**, and the value of the OpenAI-compatible surface is that it makes that
choice reversible.

### 13.4 W1's NVFP4 note

The brief says not to re-litigate NVFP4, already assessed as prefill-only. Consistent: MXFP4_MOE
was measured null-to-negative on both backends, attributed to Blackwell FP4 not paying on a
bandwidth-bound workload. Recorded as a closed question with data behind it.

---

## 14. Observations logged for Phase 1

Inputs, not proposals, per hard rule 1.

1. **The three taxonomies are now four.** V1's Coder/QA/CTO, the forge's eight roles, the brief's
   four stages - and the forge roles come with a stated principle ("role naming is about what the
   model is doing, not which weights are loaded") that resolves the gate-independence tension
   section 10 flags as unresolved. W11 should start from the forge roles.
2. **A token-saving indirection a small model cannot operate is a net loss.** The `enable_tools`
   spiral cost 415 errors and several timeouts before the pre-enable fix. Any 2.0 mechanism that
   requires a meta-call before real work needs the same forgiving fallback.
3. **The eval already measures time-to-completion per task.** The brief's W8 wants
   time-to-first-visible-output as a first-class metric. Q56 records wall clock per task and per
   battery but not TTFT; adding it is cheap and would make the fun criterion measurable.
4. **Q56 has no fun dimension and no interactive dimension.** Every task is a one-shot
   `claudette "<prompt>"` invocation. Nothing in it measures pause, redirect, take-over, or
   anything an operator does. That is exactly the axis 2.0 adds, and it means Q56 is a floor for
   the 2.0 harness rather than a ceiling.
5. **Frozen-core discipline versus corpus expansion.** The LoRA report names this directly:
   the frozen core-50 is what makes 14 months of rows comparable, and expanding or training on it
   destroys that. Folding ABCC's C8/C9 tasks in must therefore be an *extension* like K1-K8, not
   an edit of the core.
6. **The LoRA question is already researched and answered NO**, on four structural grounds -
   eval integrity, a 2048 sequence ceiling versus 8k-32k agentic transcripts, MTP head drift, and
   thin MoE tooling - with trigger conditions written for reopening it. W4's "assess whether a
   fine-tuned router or worker is worth it. Expect no" is already done to a higher standard than
   the brief asks for.
7. **No async runtime anywhere.** Claudette is blocking `reqwest` throughout. 2.0 wants parallel
   builders, a WebSocket console and a fleet protocol, all of which push toward tokio. That is a
   real architectural divergence from the donor and W3 should cost it explicitly.
8. **`~/.claudette/` files versus Postgres.** Claudette proves a serious agent needs no database
   server. W5's SQLite-versus-Postgres question has a working precedent: SQLite for recall,
   plain files for everything else.
9. **The reviewer-independence problem is untouched.** Q56 has no LLM judge because every task
   has an objective verifier. That works for a benchmark and does not generalize to the Gate
   stage on arbitrary user tasks. Still open, and the sharpest problem in the design.

---

## 15. Confidence

**High** on module map, agent loop, tool calling, state, permissions, egress, dependencies,
configuration surface, and test results. Read from source at a pinned commit, and the test suite
was executed here: 1,145 passed, 0 failed, 14.76 s.

**High** on Q56's structure and verification method, read directly from `manifest.tsv`,
`_lib.sh`, and four sampled prompt/verifier pairs.

**Medium** on the champion campaign's numbers. They are read from `CHAMPION-DOSSIER.md` and
`REPORT.md`, which are internal documents by a single author, not independently reproduced. They
are detailed, self-consistent, dated, and retain their own negative results, which is about as
good as internal evidence gets - but the residency finding in 13.2 is load-bearing enough for
Phase 1 that it deserves one confirming re-run before W1 and W2 are built on it. That re-run is
cheap: the harness, the fixtures and the crowned config are all committed.

**Not attempted:** no model was loaded, no battery was re-run, no throughput was measured, and
`runs/` was characterized by directory structure rather than by reading the 11,873 files. Full
data-asset characterization is the separate deliverable.
