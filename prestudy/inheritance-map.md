# Inheritance Map

**Purpose:** one row per meaningful component across the three source repos, with a verdict and a
reason. Per brief 4.3, this is the bridge from Phase 0 to Phase 1.

**Sources pinned at:** ABCC v1 `d5528ea` · Claudette `fc1ea22` (v0.17.0) · battle-command-forge
`d6c1601` (v0.2.0)

**Verdicts:**

| Verdict | Meaning |
|---|---|
| **PORT** | Reimplement in Rust. The idea is proven, the implementation is in the wrong language. |
| **REUSE** | Take as-is. Already Rust, or a non-code asset that transfers unchanged. |
| **REWRITE** | 2.0 needs this, but no existing implementation is a good starting point. |
| **REFERENCE** | Do not carry the code. Read it, learn the lesson, record it. |
| **DROP** | Not part of 2.0. |

**Reading note.** Per David: ABCC was a learning project where fun was the only goal and
architecture deliberately was not; Claudette is where the same person, having accumulated the
expertise, built for correctness and omitted fun. The verdicts below reflect that. Where the two
disagree on a mechanism, Claudette wins on correctness and ABCC wins on experience, and that is
the intended shape of 2.0 rather than a criticism of either.

---

## 0. Corrections to the three dossiers

Found while reading `docs/architecture.md` and `docs/decisions.md`, after those dossiers were
written. All three are now stated correctly here.

1. **Claudette's forge is a working five-phase pipeline, not just types and personas.** The
   Claudette dossier said `forge/` is "roles, personas and a model map, not a pipeline". The
   `forge/` *directory* is, but `run_forge_mission` in `run.rs` (driven by
   `run/forge_run.rs`, 1,687 lines) orchestrates: **Planner → Coder round 0 → Verifier →
   Fix-loop → Submitter**, with `MAX_FIX_ROUNDS = 3` and a Verifier that emits one-line JSON
   `{"score": 1-10, "pass": bool, "feedback": string}`. That materially raises what Claudette
   contributes to W6 and W11.
2. **BCF's 9.2 / 8.5 / 8.0 gate thresholds are empirically unreachable with all-local models.**
   The BCF dossier praised them without this context. `decisions.md` AD-7 records the measurement:
   BCF's own 10-mission stress test averaged **7.5** all-local, and the design that followed made
   the threshold **config-driven with a default of 8.0**, keeping the BCF ladder as an
   `aspirational` preset. BCF's demo run hitting 9.4 used the `premium` preset, where Opus writes
   the tests and Sonnet does the surgical fixes. The **formula** survives; the **numbers** are
   cloud-assisted calibration and must not be inherited as-is by a local-first tool.
3. **Claudette's permission model is documented as three-tier, not five.** The `PermissionMode`
   enum does carry five variants (`ReadOnly`, `WorkspaceWrite`, `DangerFullAccess`, `Prompt`,
   `Allow`), which is what the dossier reported, but both `architecture.md` and `decisions.md`
   describe the shipped policy as three-tier, and AD-5's five-tier design is explicitly flagged as
   not-built. Treat the enum as wider than the policy.

Also worth flagging: `docs/decisions.md` opens with a warning that AD-1 through AD-7 describe
`claudettes-forge` and are "fiction relative to the shipped product". It is still valuable, but
only as a record of *measurements and reasoning*, never as a description of Claudette.

---

## 1. What the three repos already agree on

The most useful output of Phase 0 is not a list of parts, it is the set of conclusions the same
person reached independently three times. These should be treated as settled going into Phase 1.

| Convergence | ABCC v1 | BCF | Claudette | Status |
|---|---|---|---|---|
| **Campbell dual complexity, 1-10, rules + AI, with a source label** | `taskRouter.ts` + `complexityAssessor.ts` | `router.rs`, `ComplexitySource::{Rules,Ai,Dual}` | `Role::Planner` "Campbell-complexity tagging" | Implemented three times. Settled. |
| **Surgical fix beats full regeneration** | auto-retry with error context | fix loop, best-round restore, "fix bugs only, never add features" | fix-loop with `MAX_FIX_ROUNDS=3` | AD-4 calls it "the strongest convergent learning in the family". Settled. |
| **An in-character operator persona with worked examples improves completion** | CodeX-7 in `coder.py` | `personas.rs` loader | `personas/codex7.md` baked in via `include_str!` | **The same persona survived into two Rust codebases.** Settled. |
| **A tiny dedicated model should score complexity** | Haiku | `qwen3.5:4b-q8_0` in every preset | `Role::Router` | Settled in principle; the model choice is W1's. |
| **The deterministic signal must outweigh the LLM judge** | reviews advisory, tests authoritative | `critique*0.4 + verifier*0.6` | Q56 has no judge at all | Settled. |
| **Single binary, no database server** | (failed at this: 5 containers + Postgres) | JSON files under `.battlecommand/` | files + one SQLite under `~/.claudette/` | Two out of three, and the two that succeeded agree. |
| **rustls, no OpenSSL; `panic = "abort"`; `opt-level = "z"` + LTO + strip** | n/a | yes | yes | Settled. |

**And one thing they disagree on:** BCF is tokio-first; Claudette is deliberately sync
(`std::thread` + `mpsc`, blocking `reqwest`) and AD-7 decision 3 rejects tokio explicitly, with
reasons. 2.0 wants parallel builders, a live WebSocket console and a fleet protocol, none of which
existed when that decision was made. **This is the single largest unforced architectural choice
facing W3, and it must be made deliberately rather than inherited from whichever file is ported
first.**

---

## 2. Orchestration and the agent loop

| Component | Source | Verdict | Reason |
|---|---|---|---|
| `ConversationRuntime<C,T>` + `ApiClient` / `ToolExecutor` traits | Claudette `runtime/conversation.rs` | **REUSE** | The two-trait seam is why 1,145 tests run in 14.76 s without a model. Best structural idea in the family. |
| Differentiated loop breakers (9 situations, 9 purpose-written nudges) | Claudette `conversation.rs:1210-1443` | **REUSE** | Strictly better than ABCC's single exception. Includes unknown-tool near-miss, duplicate-edit, unchanged-read, and graceful iteration-cap landing. |
| Auto-compaction + context eviction | Claudette `runtime/compact.rs`, `context_evict.rs`, `run/compaction_policy.rs` | **REUSE** | Solves the handoff-bloat problem W11 raises, already tuned. |
| Empty-turn detection and retry ceiling | Claudette `conversation.rs:1033-1123` | **REUSE** | Found in the wild (`runs/empty-stream-flake-2026-07-17`) and fixed with evidence. |
| CrewAI agent construction | ABCC `packages/agents` | **DROP** | The dependency 2.0 exists to remove. |
| stdout redirection to recover execution logs | ABCC `main.py:367-396` | **DROP** | Log fidelity coupled to a third party's print formatting. The anti-pattern. |
| `execution_state` / `/execute/abort` | ABCC `main.py:36,592` | **DROP** | Never populated; the endpoint aborts nothing. See W3's pause/resume requirement. |
| Parse-failure-defaults-to-success | ABCC `main.py:436-447` | **DROP** | Cite in W6 as the thing being designed against. |
| Task lifecycle, queue, resource pool, file locks | ABCC `packages/api/src/services/*` | **PORT** | The right set of concerns; wrong language and no crash durability. |
| Stuck-task watchdog (5 min, releases agent + locks + slots) | ABCC `stuckTaskRecovery.ts` | **PORT** | Cleanup is complete, which is the part usually done wrong. |
| Rest delays / periodic context reset between tasks | ABCC `taskQueue.ts` | **REFERENCE** | A 7B-era workaround for context pollution. Re-test before assuming a 35B-A3B needs it. |
| tokio async runtime | BCF | **REFERENCE** | See section 1. A decision for W3, not an inheritance. |
| `swarm.rs` | BCF | **DROP** | Aspirational; the pipeline runs single-task. |

---

## 3. Model boundary and serving

| Component | Source | Verdict | Reason |
|---|---|---|---|
| HTTP client with Ollama-native + OpenAI-compat dialects | Claudette `api.rs` | **REUSE** | Answers W2's central question. Reached LM Studio, `llama-server` and Ollama across 131 configs; `--jinja` parity proven. |
| Context budgeting (`truncate_to_budget`, `CHARS_PER_TOKEN`, `SAFETY_CHARS`) | Claudette `api.rs:1554-1671` | **REUSE** | Unglamorous and load-bearing. |
| Model-reload transient retry | Claudette `api.rs:647-668` | **REUSE** | Handles LM Studio JIT loads. Needed the moment model swapping enters the design. |
| `brain_selector.rs` tiered fallback + stuck diagnostics | Claudette | **REUSE** | Direct input to W4's escalation ladder. |
| Per-role model config with presets | BCF `model_config.rs` (8 roles, fast/balanced/premium) + Claudette `models.toml` | **PORT** | BCF's shape is right; merge with Claudette's TOML overlay and role-map. |
| `hw.rs` GPU/VRAM/temperature probes | Claudette | **REUSE** | W1 and W2 need this to report peak RAM per configuration. |
| `hardware.rs` | BCF | **DROP** | Duplicate of the above; Claudette's is live. |
| litellm provider strings | ABCC | **DROP** | Replaced by the HTTP surface. |
| Silent Claude-to-Ollama fallback on missing key | ABCC `main.py:163-178` | **DROP** | Discards the routing decision without an error. |
| `ProviderKind { Ollama, AnthropicClaude }` | Claudette `forge/types.rs` | **REWRITE** | Two variants, one feature-gated. W10 needs local + cloud + remote rig behind one trait; nothing here is a real starting point. |
| Remote Ollama routing + per-complexity model map | ABCC `resourcePool.ts` | **REFERENCE** | The only multiplayer precedent in the family. Read it in W10; do not port a `REMOTE_OLLAMA_MODEL_MAP` string format. |

---

## 4. Tool calling

| Component | Source | Verdict | Reason |
|---|---|---|---|
| Native tool calling (`tools` array out, `message.tool_calls` in) | Claudette `api.rs` | **REUSE** | Categorically better than ReAct text parsing. The single biggest gap in ABCC. |
| `ToolRegistry` + 20 on-demand groups | Claudette `tool_groups.rs` | **REUSE** | ~210 tokens core versus ~34 KB fully loaded. |
| Workspace-gated pre-enable of the lean coding core | Claudette `ToolGroup::coding_core()` | **REUSE** | The fix for the 415-error `enable_tools` spiral. Carry the fix with the mechanism, never the mechanism alone. |
| Forgiving `enable_tools` (empty group → coding core) | Claudette `executor::run_enable_tools` | **REUSE** | Same. |
| Schema-economy tests (`..._has_no_enum`, `coding_core_schema_stays_lean`) | Claudette `tool_groups.rs` tests | **REUSE** | Encodes *why* the schema is shaped this way so the reason survives refactoring. Copy the practice, not just the tests. |
| `every_advertised_tool_is_classified` regression test | Claudette | **REUSE** | Catches silently-dropped tools. Cheap, high value. |
| `WorkspaceRoots` + `validate_read_path` + F5 fallback | Claudette `tools.rs:571-646` | **REUSE** | Multi-root, `PATH`-style, with the anti-hallucination probe. |
| `startswith` prefix containment | ABCC `file_ops.py` | **DROP** | Wrong primitive. |
| `fuzzy_apply.rs` tolerant patching | Claudette | **REUSE** | What makes `apply_diff` survive whitespace drift from a local model. |
| `post_edit_check.rs` | Claudette | **REUSE** | Verify after edit rather than trust. |
| `near_miss.rs` unknown-tool suggestions | Claudette | **REUSE** | Recovery instead of an error. |
| `repo_map` concept-level localization | Claudette `tools/repomap.rs` | **REUSE** | The Recon stage's primary tool. |
| Loop control (50-call cap, per-path limits, similarity detection) | ABCC `action_history.py` | **REFERENCE** | Good multi-signal design and the thresholds are worth reading, but Claudette's per-situation nudges supersede it and the process-global singleton is unshippable. |
| ABCC file/shell tools | ABCC `tools/` | **DROP** | Superseded feature-for-feature. |

---

## 5. Complexity, routing and escalation

| Component | Source | Verdict | Reason |
|---|---|---|---|
| Campbell rule-based scorer (4 factor groups → 1-10) | ABCC `taskRouter.ts:105-239` | **PORT** | The IP. Port the structure; fix the substring matching (`'api'` matches inside `rapid`). |
| Dual-assessment asymmetric weighting | ABCC `complexityAssessor.ts:117-161` | **PORT** | Trust the semantic pass to raise a score, not to lower one. Real insight. |
| `RoutingResult` keeping `rule_score` **and** `ai_score` as typed fields | BCF `router.rs` | **REUSE** | Already Rust, and structurally fixes the data loss ABCC's Feb 2026 migration caused. Start here. |
| Complexity → context-size coupling in one expression | ABCC `taskRouter.ts:382` | **REWRITE** | W4 wants difficulty and required-context separated. They are fused in the source. |
| Post-hoc "actual complexity" + error categorization | ABCC `complexityCalculator.ts` | **PORT** | Computed but never fed back. Closing that loop is free calibration data. |
| Skipping the AI pass when rules score > 8 | ABCC `taskRouter.ts:297` | **DROP** | Means the two assessments were never compared on the hardest tasks. |
| Agent-type-as-model-tier binding (`qa` = the Claude agent) | ABCC | **DROP** | Roles wearing model names. Claudette's forge states the correct principle. |
| Budget service, daily ceiling, force-to-local | ABCC `budgetService.ts` | **PORT** | Co-op mode needs exactly this. |
| Cost calculator + per-tier rates | ABCC `costCalculator.ts`, `main.py:218` | **PORT** | Rates are stale; the structure is right. |
| Fine-tuning / LoRA | Claudette `CHAMPION-DOSSIER.md` §8 | **REFERENCE** | Already researched to a NO with four structural reasons and written trigger conditions. W4 should cite it, not redo it. |

---

## 6. Verification, gates and the stage pipeline

| Component | Source | Verdict | Reason |
|---|---|---|---|
| **Gate formula `critique*0.4 + verifier*0.6`** | BCF `mission.rs:1139` | **REUSE** | The most portable artifact in the three repos. Outvotes the judge instead of trusting it, and generalizes to arbitrary tasks in a way Q56's per-task verifiers cannot. |
| Complexity-scaled thresholds 9.2 / 8.5 / 8.0 | BCF `mission.rs:61` | **REFERENCE** | Inverted scaling is a real insight; the numbers are cloud-assisted calibration (all-local average was 7.5). Recalibrate, do not inherit. |
| Config-driven threshold, default 8.0, `aspirational` preset | `decisions.md` AD-7 | **PORT** | Separates algorithm from policy. The right resolution of the row above. |
| Surgical fix loop with best-round restore + decline detection | BCF `mission.rs` | **REUSE** | Family-wide convergent learning. |
| Refusing to restore a round the security stage rejected | Claudette `run/forge_run.rs` | **REUSE** | The improvement BCF's version lacks. |
| Five-phase forge pipeline (Planner → Coder → Verifier → Fix → Submit) | Claudette `run_forge_mission` | **REUSE** | The only stage pipeline in the family that runs daily against real repos. |
| Verifier JSON contract `{score, pass, feedback}`, fence-tolerant | Claudette | **REUSE** | Small, typed, already survives real model output. |
| Deterministic project verifier (lint + tests, per language) | BCF `verifier.rs` | **PORT** | Python deep, Rust/Go/TS-JS shallow, six static-check categories. The scoring model generalizes; env construction is Python-specific. |
| `check_secrets` + `check_todos` in scoring | BCF `verifier.rs:633-673` | **REUSE** | Cheap, language-independent, connects to W7. |
| `security_review.rs` deterministic added-lines scan | Claudette | **REUSE** | Deterministic, not an LLM. Correct shape for a gate input. |
| Tiered LLM review every 5th / 10th task | ABCC | **REFERENCE** | Cadence-based review is a cost hack for a co-op-only world. The gate formula replaces it. |
| Validation-command + `"PASS" in stdout` | ABCC `main.py:571` | **REFERENCE** | Magic-string contract. Q56's per-task verifiers are the better pattern. |
| BCF 9-stage sequence (Router…Gate) | BCF | **REFERENCE** | Nine stages collapsed to five in the successor and stayed there. W11 should reconcile toward the five, not away from it. |
| SWE-bench harness | BCF `swebench*.rs` | **DROP** | Prototyped, never run, out of scope per David. |
| Decomposition into subtasks | BCF (`mission.rs:361`) and ABCC (`orchestrator.py`) | **REFERENCE** | BCF tried and reverted: "caused duplicate projects". ABCC shipped it for missions. Contradictory evidence, different regimes. W11 must test, not assume. |

---

## 7. State and persistence

| Component | Source | Verdict | Reason |
|---|---|---|---|
| Transcript / action journal with trash-backed undo | Claudette `transcript.rs` | **REUSE** | Per-turn and per-action undo, bounded restore targets, deletes to trash, secrets redacted before write. Directly serves the operator-control pillar. |
| Only mutating calls logged; ReadOnly never logged | Claudette | **REUSE** | Keeps the journal meaningful and small. |
| `redact.rs` secret redaction for logs and traces | Claudette | **REUSE** | W7 requires this because the console renders traces. |
| Session autosave + `--resume` | Claudette `runtime/session.rs` | **REUSE** | |
| `recall.sqlite` cross-session memory, 50k-row FIFO, tool calls not indexed | Claudette `recall.rs` | **REUSE** | Also the SQLite precedent W5 needs. |
| Files-under-`~/.claudette/` storage model | Claudette | **REUSE** | Proof that a serious agent needs no database server. Answers W5's Postgres question by example. |
| Prisma schema (13 models: Task, ExecutionLog, CodeReview, Mission, TrainingDataset, TaskMemory…) | ABCC | **REFERENCE** | The right *entities* for a console, discovered over months. Read as a domain model; do not carry Postgres. |
| `ExecutionLog` per-tool-call shape (thought/action/input/observation/timing/tokens/isLoop) | ABCC | **PORT** | This is the console's data. Best-designed table in the family. |
| The Feb 2026 complexity-field collapse | ABCC migration | **REFERENCE** | Cautionary. BCF's typed `RoutingResult` is the fix. |
| JSON mission records | BCF `db.rs` | **DROP** | Superseded by Claudette's storage model. |
| `FileLock` per-path locks | ABCC | **PORT** | Parallel builders need this; W6's worktree question may replace it. |

---

## 8. Console, presentation and the fun layer

Everything here is the pillar Claudette deliberately omitted, so ABCC dominates.

| Component | Source | Verdict | Reason |
|---|---|---|---|
| **2D isometric renderer** (`isoProjection.ts`, grid, tank, target, projectile, explosion, label) | ABCC `components/isometric/` | **REUSE** | Closest existing asset to the stated C&C isometric target. W5 starts here. |
| React Three Fiber 3D battlefield (11 components) | ABCC `components/battlefield/` | **REFERENCE** | Real work, but the decision is isometric. Keep as a source of motifs. |
| **96 Bark TTS voice lines** (6.4 MB, 3 packs) | ABCC `public/audio/` | **REUSE** | Irreplaceable and expensive to regenerate. Copy the files. |
| `audioManager.ts` playback queue + `voicePacks.ts` | ABCC | **PORT** | Small, and the queueing behaviour is the non-obvious part. |
| `bark-generate-all.py` regeneration script | ABCC `scripts/` | **REUSE** | Needed to extend the voice set. |
| ToolLog terminal feed, TokenBurnLog, CodeWindow | ABCC | **PORT** | The no-dead-air surfaces. |
| Three minimaps (Minimap, FlowMinimap, TimelineMinimap) | ABCC | **REFERENCE** | Three attempts at one problem. Pick one deliberately in W5. |
| Dashboards (CostDashboard, SuccessRateChart, ComplexityDistribution, AgentComparison) | ABCC | **PORT** | Legibility over completeness: port selectively, not all four. |
| Theme system (`classic.ts`, `battleclaw.ts`) | ABCC | **REUSE** | Personality-with-an-off-switch already has a mechanism. |
| `useSocket.ts` WebSocket event plumbing | ABCC | **PORT** | Event taxonomy is reusable; transport is W5's call. |
| Chat panel, CTOWelcome, MissionProgressTracker | ABCC | **REFERENCE** | Overlaps the conversational surface Claudette already owns. |
| Ratatui TUI | Claudette `tui.rs` (5 tabs) and BCF `tui.rs` | **REFERENCE** | Decision is isometric web. Keep as the headless/SSH fallback question for W5, not the primary. |
| `snake.rs` / `space.rs` minigames | BCF | **REFERENCE** | Correct instinct about dead air, wrong answer. Make the work watchable instead. |
| macOS `say` voice announcements | BCF `voice.rs` | **DROP** | macOS-only; dead on the target hardware. |
| Bounty board | brief section 3.1 | **DROP** | Does not exist in any repo. |

---

## 9. Evaluation

| Component | Source | Verdict | Reason |
|---|---|---|---|
| **Q56 core-50 tasks + K1-K8 extension** | Claudette `runs/eval-2026-05-29/battery/` | **REUSE** | The project's evaluation baseline per David. Frozen core is what makes 14 months of rows comparable. |
| Per-task shell verifiers + `_lib.sh` contract | Claudette `battery/verify/` | **REUSE** | Objective, no LLM judge, three verification modes (execution / file state / transcript ground truth). |
| Trap tasks (I3 stale-docs-versus-source) | Claudette | **REUSE** | Tests a real agentic failure mode almost nothing public covers. |
| Harness scripts + screener/smoke tiers | Claudette `run_battery.sh`, `run_screener.sh`, `analyze.sh`, `probe_speed.sh` | **REUSE** | Cheap triage before committing to a full battery. |
| 131 model-run result set | Claudette `battery/logs-*`, `SCORES-*.tsv` | **REUSE** | W1's evidence base, already collected. |
| `CHAMPION-DOSSIER.md` methodology | Claudette | **REUSE** | Decision-matrix-with-rejected-rows is exactly the brief's "no recommendation without a rejected alternative". |
| ABCC 40-task corpus, C1-C4 | ABCC `ollama-stress-test-40.js` | **DROP** | Descriptions embed the reference implementation. Transcription, not coding. |
| ABCC 40-task corpus, C8-C9 (10 tasks) | ABCC | **PORT** | Per David, triage the hardest ones in. Must land as a **K-series-style extension**, never as an edit to the frozen core. |
| ABCC per-language stress suites (JS, Go, PHP) | ABCC `scripts/` | **REFERENCE** | Q56 already covers 11 surfaces. Mine for PHP, which Q56 lacks. |
| Time-to-first-visible-output metric | nowhere | **REWRITE** | Q56 measures wall clock per task, not TTFT. The brief makes it a first-class metric. New work. |
| Operator-interaction metrics (pause, redirect, take-over) | nowhere | **REWRITE** | Every Q56 task is a one-shot invocation. The axis 2.0 adds is unmeasured by anything that exists. |

---

## 10. Security and sandboxing

| Component | Source | Verdict | Reason |
|---|---|---|---|
| **`egress.rs` two-layer offline guard** (HTTP + subprocess, uniform refusal) | Claudette | **REUSE** | The best answer in the family to the brief's "code leaves only through a deliberate, logged path". |
| Structural air-gap via `default = []` feature set | Claudette `Cargo.toml` | **REUSE** | No cloud code compiled into the default binary at all. Guarantee, not a setting. 2.0 must adapt this, since co-op mode needs cloud on purpose. |
| **Subprocess env allowlist** | BCF `sandbox.rs` | **REUSE** | Arrived at after a blocklist missed `OLLAMA_HOST`, `DATABASE_URL`, `AWS_ACCESS_KEY_ID`, `SSH_AUTH_SOCK`. Allowlist semantics close the class. |
| `validate_path_within` (traversal, absolute, NUL, backslash) | BCF `sandbox.rs` | **REUSE** | With the regression test for the over-eager `..` substring check. |
| Subprocess timeouts | BCF `sandbox.rs`, Claudette `test_runner.rs` | **REUSE** | |
| `secrets.rs` token storage (`0600` / Windows ACL) | Claudette | **REUSE** | |
| Permission tiers + `Operation` enum | Claudette `runtime/permissions.rs` | **PORT** | Policy still keys off tool name; the operation-level model is built but not load-bearing. 2.0 should finish it. |
| `[y/N]` gate + `diff_preview.rs` | Claudette | **REUSE** | Human-in-the-loop, already shipped. |
| Docker as the isolation boundary | ABCC | **DROP** | Not a boundary against hostile code, and 2.0 ships one binary. |
| Per-language dangerous-import string denylist | ABCC `shell.py` | **DROP** | Speed bump, not a boundary. |
| CORS `*` + `allow_credentials` | ABCC `main.py:64` | **DROP** | |
| `test_env_var_stripping` | BCF `sandbox.rs:472` | **REWRITE** | Passes vacuously on Windows (asserts a negative over output from a Unix-only binary). The control is real; the evidence is not. |
| Platform sandboxing (`sandbox-exec` / `bwrap`) | Claudette, removed 2026-06 | **REFERENCE** | Was designed, then deleted as dead code. W7 should know it was tried. |

---

## 11. Operations, onboarding and process

| Component | Source | Verdict | Reason |
|---|---|---|---|
| `doctor.rs` — ten diagnostic probes with copy-paste fixes | Claudette | **REUSE** | "It has to run on other people's machines" is a stated constraint; this is the mechanism. |
| `setup.rs` five-step wizard + `firstrun.rs` failure classifier | Claudette | **REUSE** | Same. |
| Comment discipline (measurement + regression that motivated it) | Claudette | **REUSE** | A practice, not code. It is why the Claudette dossier was fast to write, and W13 should mandate it. |
| ADR practice | Claudette `docs/decisions.md`, BCF | **PORT** | Both wrote ADRs. Claudette's went stale and needed a warning banner. W13 should require a supersession marker, not just a file. |
| `plans/` per-sprint task specs written before the work | Claudette (119 files) | **REUSE** | Direct precedent for W13's co-development conventions. |
| Retained negative results (`SCORES-*-BROKEN-*`, `*-PARTIAL-KILLED-thermal-*`) | Claudette | **REUSE** | Practice worth mandating. |
| `.gitattributes` LF enforcement | `decisions.md` AD-6 | **REUSE** | CRLF silently broke the persona frontmatter parser once already. |
| `enterprise.rs` paid-tier scaffolding | BCF | **DROP** | 2.0 is a community project, confirmed. |
| `BMORE.md` | BCF | **DROP** | Unrelated commercial spec. See questions.md. |
| Docker Compose 5-container stack | ABCC | **DROP** | The thing being replaced. |
| MCP gateway (1,973 lines, disabled) | ABCC | **DROP** | Disabled because it hurt success rates. |
| Battle Claw external API | ABCC | **REFERENCE** | Precedent for exposing 2.0 to other tools; not Phase 1. |
| xAI / Grok support | ABCC | **DROP** | Undocumented, unused. |
| `TrainingDataset` Claude-versus-local pairing | ABCC | **REFERENCE** | Only relevant if fine-tuning reopens, which is a documented NO. |

---

## 12. Summary by verdict

| Verdict | Count | Where it concentrates |
|---|---|---|
| **REUSE** | 48 | Overwhelmingly Claudette. The harness, the tools, the safety layer, the eval. |
| **PORT** | 18 | Overwhelmingly ABCC. The complexity model, the console surfaces, the console's data model. |
| **REFERENCE** | 22 | Spread evenly. Mostly negative results and superseded attempts. |
| **DROP** | 21 | Mostly ABCC infrastructure and BCF's commercial scaffolding. |
| **REWRITE** | 5 | The genuinely new work: provider abstraction, difficulty/context separation, TTFT, operator metrics, one security test. |

**The shape this implies:** 2.0 is Claudette's engine with ABCC's console bolted onto it, BCF's
gate arithmetic inserted at the verification boundary, and about five things that nobody has built
yet. Only five REWRITE rows is the headline: the brief expected a research project and Phase 0
found mostly an integration project with a hard UI problem attached.

**The five genuinely open pieces**, which is where Phase 1 effort should concentrate:

1. **The provider abstraction** (W10) — local, cloud and remote rig behind one trait. Nothing
   existing is a starting point.
2. **Difficulty separated from required context** (W4) — fused in every existing implementation.
3. **Operator control as a measurable property** (W5, W8) — pause, redirect, take-over, replay.
   No repo has it and no eval measures it.
4. **Gate independence in single-player** (W6, W11) — ABCC dodged it with different providers,
   Q56 dodged it with hand-written verifiers, BCF's formula reduces but does not remove it. Still
   the sharpest problem in the design.
5. **Async or not** (W3) — the donors disagree and 2.0's requirements postdate the decision.

---

## 13. Confidence

**High** on every verdict sourced from code read at a pinned commit, which is most of the table.

**Medium** on the presentation-layer rows. I inventoried ABCC's components by file and read their
names and imports, not their rendering logic. Whether `isoProjection.ts` is a good foundation or
merely an existing one is a W5 judgment that needs someone to actually run it.

**Medium** on the BCF verifier's language-generality claim. I read the dispatch branches for
Python, Rust, Go and TS/JS but did not execute any of them.

**Low, and marked as such in the rows:** anything about how well a component *works* as opposed to
what it *is*. Only Claudette's test suite (1145 pass) and BCF's (96 pass, 2 fail) were executed.
No model was loaded, no mission was run, no battery was reproduced.
