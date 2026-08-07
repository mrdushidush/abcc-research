# Inheritance Map

**Purpose:** one row per meaningful component across the three source repos, with a verdict and a
reason. Per brief 4.3, this is the bridge from Phase 0 to Phase 1.

**Sources pinned at:** ABCC v1 `d5528ea` · Claudette `fc1ea22` (v0.17.0) · battle-command-forge
`d6c1601` (v0.2.0)

**Extended 2026-08-07** with §11a, covering two archived repos the brief did not know about
(`independencev1`, StealthForge/`stealthsambaV2`). See `archive-repos.md`. §0 items 5–8 were added
at the same time and change rows in §6 and §9.

**Verified 2026-08-07 in two passes** (`verification.md`). The first pass moved two rows into
REWRITE — things recorded as existing that do not exist. The second pass covered ABCC's §2 and §7
PORT rows and moved nothing, but rewrote six reasons and added §0 item 10; it also ran ABCC's
lifecycle test suites, the first time anything in ABCC was executed for this study. Rows carrying a
⚠ have been corrected against executed or traced code and the original text is struck rather than
deleted.

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
   `run/forge_run.rs`, **1,803 lines**) orchestrates: **Planner → Coder round 0 → Verifier →
   Fix-loop → Submitter**, and a Verifier that emits one-line JSON
   `{"score": 1-10, "pass": bool, "feedback": string}`. That materially raises what Claudette
   contributes to W6 and W11.

   *Verified 2026-08-07 (see `verification.md` §1).* The phase banners are at `forge_run.rs:592`
   (Planner), `:621` (Coder ↔ Verifier fix-loop, phases 2-4) and `:943` (Submitter). Two
   corrections: the file is 1,803 lines at the pinned commit, not 1,687; and the fix-round cap is
   **`DEFAULT_MAX_FIX_ROUNDS = 3`** (`:29`), overridable by `CLAUDETTE_MAX_FIX_ROUNDS` and clamped
   to `FIX_ROUNDS_HARD_CAP = 10` (`:35`). **Claudette already separates algorithm from policy the
   way §6 recommends BCF's threshold should** — 2.0 inherits the pattern, not just the number.
2. **BCF's 9.2 / 8.5 / 8.0 gate thresholds are empirically unreachable with all-local models.**
   The BCF dossier praised them without this context. `decisions.md` AD-7 records the measurement:
   BCF's own 10-mission stress test averaged **7.5** all-local, and the design that followed made
   the threshold **config-driven with a default of 8.0**, keeping the BCF ladder as an
   `aspirational` preset. BCF's demo run hitting 9.4 used the `premium` preset, where Opus writes
   the tests and Sonnet does the surgical fixes. The **formula** survives; the **numbers** are
   cloud-assisted calibration and must not be inherited as-is by a local-first tool.
3. ~~**Claudette's permission model is documented as three-tier, not five.**~~ **Corrected
   2026-08-07 against the code, at David's instruction. He was right; the earlier reading was
   wrong, and checking it found a latent trap.**

   `crates/claudette/src/runtime/permissions.rs:5` — the enum has **five variants and four are
   load-bearing**. They are two different kinds of thing, which is what the "three-tier" docs are
   describing without saying so:

   - **Capability tiers**, ordered, and the only ones a tool is ever registered against:
     `ReadOnly`, `WorkspaceWrite`, `DangerFullAccess`. Verified across `crates/`: 8 tools at
     `ReadOnly`, 4 at `WorkspaceWrite`, 6 at `DangerFullAccess`, and **zero** at anything else.
   - **Session-control modes**, which only ever appear as `active_mode`: `Prompt` and `Allow`. The
     code says so itself at `permissions.rs:267` — *"`Prompt` / `Allow` modes are session-control
     tiers (not 'higher privilege') so they bypass this cap."* `Allow` is live, set by
     `with_active_mode` for unattended forge runs (`runtime_build.rs:146`, `:296`).

   **⚠ `PermissionMode::Prompt` is dead, and if 2.0 revives it as-is it will do the opposite of
   its name.** It appears nowhere outside `permissions.rs`. And the derived `Ord` places it
   *above* `DangerFullAccess`, so in `authorize` the line-283 guard
   `current_mode >= required_mode` is true for **every** tier a tool can require — the
   `current_mode == PermissionMode::Prompt` branch at line 294 is unreachable. A session in
   `Prompt` mode would auto-approve everything silently. Verified by reproducing the enum
   ordering and both branches standalone; nothing is broken today because nothing sets it.

   What *is* narrower than the design is the **dimension**, not the tier count.
   `required_mode_for` keys off the **tool name**; the `Operation` enum
   (`ReadFile`/`WriteFile`/`Execute`/`Network`/`Other`) that would let policy key off the actual
   operation is built, but per its own doc comment at `permissions.rs:13-18` *"Today only the
   prompter consumes it; the policy still keys off the tool name."* That is what the §10 row
   means by "built but not load-bearing", and it stands.

Added 2026-08-07, from the data-asset extraction and the archive repos:

4. **The Q56 crown moved to gemma — and ABCC 2.0 is building on qwen anyway. Both are true.**

   Q56 crowned **`google/gemma-4-26b-a4b-qat`** at `2a6acea` (2026-07-25/26), Q4_0, 13.45 GiB,
   median **55/56** over three runs. `qwen3.6-35b-a3b-mtp@iq3_s` scores 48–52/56.

   **David's ruling, 2026-08-07: gemma wins single-shot; in agentic coding over large multi-file
   context it falls apart, and qwen remains the champion. `qwen3.6-35b-a3b-mtp` is 2.0's
   foundation primary brain.** This is a decision, and it is also the better reading of the
   evidence, for two reasons the corpus states about itself:

   - **Q56 structurally cannot see the thing that decides it.** `T2.md`'s own axis 4: *"Every Q56
     fixture is small; ctx 32768 is never stressed and we never test whether a model can **find**
     the relevant code before changing it."* Every task is one `claudette "<prompt>"` invocation
     against a small buildable fixture. The crown is a **single-shot crown on small inputs**, and
     `questions.md` §3.5 item 19 already flags that nothing in Q56 measures interactive operation.
   - **The crown rule discarded a 3.4x speed difference by design.** Median wall clock for the
     full 56: gemma-qat **4,535 s** versus qwen-mtp **1,338 s** (`prestudy/data/q56-results.csv`).
     `Q50.md`'s crown rule says speed *"is recorded but breaks no ties; the speed champion keeps
     the daily-driver role regardless."* For a tool whose success test is David reaching for it
     instead of Claude Code, 3.4x on every turn is not a tiebreak.

   **So:** "35B-A3B" references below are **not** stale — they name the intended base agent.
   What is stale is treating Q56's score column as the whole ranking. Two consequences carry
   into Phase 1: W1 evaluates candidates on **agentic multi-file work at context pressure**, not
   Q56 alone, and W8's first job is a corpus that can see that axis (tier 2 was started for
   exactly this and is 4 tasks in).
5. **The Q56 corpus is not on Claudette's `main`.** It lives only on the unmerged branch
   `battery/q50-quality-corpus`. `main` carries a different, older A–K battery, and a local-only
   `.git/info/exclude` hides the artifacts from `git status`. Row "Q56 core-50 tasks + K1-K8
   extension" in §9 conflates the two batteries; they are separate instruments.
6. **ABCC's 40-task corpus ships deterministic per-task verifiers.** Each task carries a Python
   assertion one-liner. ABCC never used an LLM judge either. The §9 rows treating the ABCC corpus
   as unverified transcription are right about C1–C4's *prompts* and wrong about its *grading*.
7. **ABCC has a 100-task suite with 7 recorded runs** (`ultimate-100-task-test.js`) that neither
   the brief nor this map mentions, covering React, landing pages, Python/Node APIs, security and
   bug-fixing across 10 categories. It is closer to 2.0's stated target workload than the 40.
   See `data-assets.md` §4.2.
8. **§12's open piece 4, "gate independence in single player", has been measured.** StealthForge
   ran a separate reviewer process over its own output on 34 missions: median **+3.65** points of
   inflation, **0 of 34** where the independent reviewer scored higher. See §11a and
   `archive-repos.md` §2.

Added 2026-08-07 by the verification pass (`verification.md`):

9. **The residency reframing is now sourced from shipped code, not from a dossier.**
   `questions.md` §1 — the single most load-bearing correction Phase 0 made — rested on
   `CHAMPION-DOSSIER.md`, a document, which is exactly the contamination vector David warned
   about. It no longer has to. `hw.rs:103-109` ships the VRAM→brain recommendation as *code*, and
   the recommendation string reads: *"50/50 + K 8/8 on the 50-task battery (49/50 at 64k ctx) at
   ~70-76 tok/s — **fully VRAM-resident in 13.6 GB, zero RAM spill**."* Claudette's own installer
   tells every user the crowned config does not spill. **W1 and W2 should be reframed to
   "stay resident in 16 GB" without waiting for a reproduction run.**

   Two riders, both from the same live probe (`claudette --doctor`, 2026-08-07):

   - `hw.rs:108` cites the **50-task + K1-K8** battery, not Q56. That is a third independent
     source for §0 item 5: the instrument Claudette ships against lives on `main`, and Q56 is a
     different battery on an unmerged branch. The §9 row conflating them is confirmed wrong.
   - David's live daily-driver environment runs **`CLAUDETTE_NUM_CTX=61440`** on
     `qwen3.6-35b-a3b-mtp@iq3_s`. So `T2.md` axis 4's "ctx 32768 is never stressed" understates
     the gap: the *evaluation* never exceeds 32k while the *daily driver* runs at 60k. W8's corpus
     problem is bigger than the map records.

Added 2026-08-07 by the second verification pass (`verification.md` §3.4):

10. **ABCC's per-step token columns are unreachable by every write path it has, and that kills
    three things downstream.** `execution_logs.input_tokens` / `.output_tokens` /
    `.model_used` exist in the schema. The Python producer sends all three
    (`execution_logger.py:136-138`), the API route validates them
    (`routes/execution-logs.ts:25-27`) and spreads them onward — and
    `ExecutionLogService.createLog` writes an explicit `data` list that omits them
    (`executionLogService.ts:24-34`). TypeScript misses it because excess-property checking does
    not apply to spread properties. The only other writer, a raw `INSERT` in
    `mcp-gateway/adapters/postgres.py:239-249`, never sends them either, and
    `captureTrainingData` drops them a third time (`taskExecutor.ts:637-647`).

    What that takes with it:

    - **`budgetService`** — its one production call site is gated on those fields, so
      `recordUsage` has never fired. Same for `costAggregator`, whose `hydrate()` at boot rebuilds
      totals from the null columns. §5's row is annotated.
    - **`TokenBurnLog`** — filters on the same predicate, so the panel is structurally empty and
      its only non-empty state is an opt-in `Math.random()` demo. §8's row is annotated.
    - **`data-assets.md`'s "0% populated"** — now explained. An unreachable column, not neglect.
      This is the mechanism behind brief §11.0's W4 row, and it means no amount of running ABCC
      longer would have produced the data.

    **The generalisable lesson, which is why this is an item and not just a row edit:** every
    component in this chain is individually well built. The schema is right, the producer is right,
    the validation is right, the consumers are right, the UI guards its demo mode carefully. The
    system still cannot record a token. Reading any one file would have found nothing wrong.

    **Extent, once the UI was run (`verification.md` §3.5h):** `emitCostUpdate`'s only caller is
    inside the dead gate, so **`cost_updated` can never fire**; `budget_updated` fires only from
    `setConfig` / `resetDaily`, so it only ever reports zero spend. **3 columns → 2 services →
    2 socket events → 2 store slices → the budget HUD and the burn-rate panel.** Eleven components.
    Visible in one screenshot: `$0.00 / $5.00`, `$0.0000` all-time, `BURN RATE 0/min`,
    `No token usage yet`.

11. **The isometric renderer is raster sprites over painted backdrops, not an SVG tile engine — and
    the wrong version of this was written into this map earlier the same day, by me.** §8's row and
    `verification.md` §3.2 both said "one SVG node per sprite … on a `GRID_RANGE = 8` (17×17)
    board". Both were **inferred from `isoProjection.ts`'s exports without opening the components
    that consume them.** What ships: `IsometricGrid` is a single full-bleed background `<img>` (the
    17×17 board is never drawn), `IsometricTank` is two divs plus a 280 px raster `<img>`, SVG
    appears only in the projectile tracer and one arc on the target, and `isoCubeFaces` — cited as
    the module's best evidence of quality — **has zero call sites**.

    Running it settled the question the wrong reading had opened: **idle sprites are free to ~100
    entities, the cliff is between 100 and 400, and the technique needs no canvas or WebGL at 2.0's
    scale.** The renderer moves REFERENCE → PORT. Full numbers in `verification.md` §3.5(c).

    **Why this is an item.** Items 1-10 are corrections to other people's code. This one is a
    correction to a claim of mine that read as a code citation and was an inference. The fix was one
    screenshot and four greps. **Open the consumer, not just the module.**

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
| `ConversationRuntime<C,T>` + `ApiClient` / `ToolExecutor` traits (`conversation.rs:141`, `:145`, `:237`) | Claudette `runtime/conversation.rs` | **REUSE** | The two-trait seam is why **1,145 tests run in 3.8 s** without a model. Best structural idea in the family. (Executed 2026-08-07: 1,145 pass / 0 fail in the default-feature lib binary, 3.76 s; 1,274 across all binaries at `--all-features`. The brief's 14.76 s is the *edit-to-green* cycle, not test execution — see `verification.md` §1.3.) **Now measured on both sides:** ABCC's six lifecycle suites are **81 tests in 32.4 s** — 0.40 s per test against Claudette's 0.0033 s, a **~120× gap** — because the suite sleeps through real rest delays. The seam is not a style preference; it is the difference between a suite you run on every keystroke and one you avoid. |
| Differentiated loop breakers (**12 purpose-written interventions**) | Claudette `conversation.rs:57-1470` | **REUSE** | Strictly better than ABCC's single exception. Iteration-budget warning, graceful cap landing + its tool refusal + its empty-reply fallback, empty-turn continuation, unknown-tool near-miss, over-search nudge, duplicate nav / duplicate edit / duplicate-denied suppression, unchanged-read pointer-up, no-progress nudge. |
| Auto-compaction + context eviction | Claudette `runtime/compact.rs`, `context_evict.rs`, `run/compaction_policy.rs` | **REUSE** | Solves the handoff-bloat problem W11 raises, already tuned. |
| Empty-turn detection and retry ceiling | Claudette `conversation.rs:1033-1123` | **REUSE** | Found in the wild (`runs/empty-stream-flake-2026-07-17`) and fixed with evidence. |
| CrewAI agent construction | ABCC `packages/agents` | **DROP** | The dependency 2.0 exists to remove. |
| stdout redirection to recover execution logs | ABCC `main.py:367-396` | **DROP** | Log fidelity coupled to a third party's print formatting. The anti-pattern. |
| `execution_state` / `/execute/abort` | ABCC `main.py:36,592` | **DROP** | Never populated; the endpoint aborts nothing. See W3's pause/resume requirement. |
| Parse-failure-defaults-to-success | ABCC `main.py:436-447` | **DROP** | Cite in W6 as the thing being designed against. |
| Task lifecycle, queue, resource pool, file locks | ABCC `taskExecutor.ts` (700 lines) + `taskAssigner.ts` (233) | **PORT** | The right set of concerns; wrong language and no crash durability. ⚠ **Executed and traced 2026-08-07** (`verification.md` §3.4). **Citation moved:** `taskQueue.ts` is now a 275-line facade of `@deprecated` one-line delegations — the lifecycle left it. **Durability splits three ways:** file locks *are* durable (Postgres, `filePath` unique); resource-pool slots are a **process-singleton `Map`** (`resourcePool.ts:88`) and rest counters a module-level `Map` (`ollamaOptimizer.ts:22`); and **nothing reconciles at boot** — `index.ts:101` builds an empty pool, `:214` starts the watchdog, and the only state rehydrated from the DB is `costAggregator.hydrate()` (`:108`), which reads the three columns nothing writes. Restart with one coder agent leaves it `busy`; with two, the empty pool over-admits to a 1-slot GPU. **And the lifecycle has no type:** `Task.status` is `String @db.VarChar(20)`, 11 states, **no status union type anywhere in the package** and **≥48 bare `Task`-status literal sites** (143 across all entities in `services/` + `routes/`), so no state machine — only conventions. That is Q8's "RTS framing into the domain model" and the durability fix being the same job — a Rust enum with typed transitions makes the watchdog hole below unrepresentable. |
| Stuck-task watchdog (5 min, releases agent + locks + slots) | ABCC `stuckTaskRecovery.ts` | **PORT** | ⚠ **Half of this row's reason reversed 2026-08-07.** *Cleanup of what it finds is complete* and that part is real — eight steps at `:256-334`: locks, slot, task→`aborted` with `errorCategory: 'timeout'`, open `TaskExecution`→`failed`, agent→`idle` + stats, two socket events, an operator alert, an MCP publish. Better than most. **But the found-set is `status: 'in_progress'` only** (`:192-202`). A task stuck in **`assigned`** is invisible forever — it holds the agent, the slot and its locks until a human presses reset. Not inference: the author's own comment at `taskExecutor.ts:244-249` (the pin's HEAD commit) says *"Nothing polls 'assigned'… held the agent, the resource-pool slot and the file locks until a human hit reset"*. `needs_human` is invisible too, and `forceRecoverAll`'s orphan sweep only catches `busy` agents, not the `stuck` status `requestHumanInput` sets. **And the clock is `assignedAt`, not last progress** — no heartbeat field exists, so a healthy long task is aborted for being slow; `ExecutionLog.timestamp` is written per step and would serve. **For 2.0: watch `max(execution_log.timestamp)`, cover every non-terminal state.** The recovery path has **no test** (8 tests, none reach `recoverStuckTask`). Doc drift: header says 10 minutes, constant is 5. |
| Rest delays / periodic context reset between tasks | ABCC **`ollamaOptimizer.ts`** | **REFERENCE** | A 7B-era workaround for context pollution. Re-test before assuming a 35B-A3B needs it. ⚠ **Citation corrected 2026-08-07** — this is not in `taskQueue.ts`. Measured: **3 s** after each task, **8 s** every **5th**, per agent, coder-agents-only (`:16-18`, `:85`). Two defects to not inherit: it runs *after* the shared 1-slot resource is released (`taskExecutor.ts:141` vs `:408`), so it protects the agent's turnaround and not the model context it exists for; and it awaits a bare `setTimeout` with no injectable clock, which is why ABCC's 81 lifecycle tests take 32.4 s. |
| tokio async runtime | BCF | **REFERENCE** | See section 1. A decision for W3, not an inheritance. |
| `swarm.rs` | BCF | **DROP** | Aspirational; the pipeline runs single-task. |

---

## 3. Model boundary and serving

| Component | Source | Verdict | Reason |
|---|---|---|---|
| HTTP client with Ollama-native + OpenAI-compat dialects | Claudette `api.rs` | **REUSE** | Answers W2's central question. Reached LM Studio, `llama-server` and Ollama across 131 configs; `--jinja` parity proven. **Exercised live 2026-08-07** against David's running LM Studio: `--doctor` reports `backend: openai-compat` → `/v1/models` HTTP 200, 24 models, brain loaded. Dialect selection is `CLAUDETTE_OPENAI_COMPAT` (`api.rs:368`) over `OLLAMA_HOST` (`:296`). |
| Context budgeting (`truncate_to_budget` `api.rs:1554`; `CHARS_PER_TOKEN = 4` `:151`; `SAFETY_CHARS = 1024` `:154`) | Claudette `api.rs` | **REUSE** | Unglamorous and load-bearing. (The constants live at the top of the file, not inside the earlier-cited `1554-1671` range.) |
| Model-reload transient retry | Claudette `api.rs:647-668` | **REUSE** | Handles LM Studio JIT loads. Needed the moment model swapping enters the design. |
| `brain_selector.rs` tiered fallback + stuck diagnostics | Claudette | **REUSE** | Direct input to W4's escalation ladder. |
| Per-role model config with presets | BCF `model_config.rs` (8 roles, fast/balanced/premium) + Claudette `models.toml` | **PORT** | BCF's shape is right; merge with Claudette's TOML overlay and role-map. |
| `hw.rs` GPU **VRAM** probe + VRAM→brain recommendation | Claudette `hw.rs` (208 lines, 4 public fns) | **REUSE** | Live-verified 2026-08-07: `detect_vram_gb` shells out to `nvidia-smi` and reported 15.9 GiB correctly. `recommend_brain` (`:103`) is the VRAM→certified-model table. |
| **Peak RAM / VRAM reporting per configuration** (W1, W2) | nowhere | **REWRITE** | ⚠ **Correction 2026-08-07.** This row previously read "GPU/VRAM/**temperature** probes … W1 and W2 need this to report peak **RAM** per configuration" and was wrong twice. `hw.rs` has **no temperature probe and no system-RAM probe at all** — it is `nvidia-smi` VRAM only, and its own module doc says "no NVML/sysinfo bindings". It reads *installed* VRAM, never *peak* anything. W1/W2's "report a hard limit, not a tuning suggestion" (`questions.md` §4 item 1) has **no existing implementation**. Budget for it. |
| `hardware.rs` | BCF | **DROP** | Duplicate of the above; Claudette's is live. |
| litellm provider strings | ABCC | **DROP** | Replaced by the HTTP surface. |
| Silent Claude-to-Ollama fallback on missing key | ABCC `main.py:163-178` | **DROP** | Discards the routing decision without an error. |
| `ProviderKind { Ollama, AnthropicClaude }` | Claudette `forge/types.rs` | **REWRITE** | Two variants, one feature-gated. W10 needs local + cloud + remote rig behind one trait; nothing here is a real starting point. |
| Remote Ollama routing + per-complexity model map | ABCC `resourcePool.ts` | **REFERENCE** | The only multiplayer precedent in the family. Read it in W10; do not port a `REMOTE_OLLAMA_MODEL_MAP` string format. **Read properly 2026-08-07:** four resource types — `ollama` (1 slot), `remote_ollama` (env-gated, N slots), `claude` (2), and **`grok`** (2, gated on `XAI_API_KEY`) — so ABCC had *four* provider paths, not two, which is worth knowing when W10 designs the one trait. `getResourceForComplexity` (`:240`) is an independent second confirmation of the real ladder: C10→claude, C7-9→remote if enabled, else local. It also validates remote model availability at startup, non-blocking, with a `ollama pull` hint (`:124-152`) — good operator manners worth keeping. What not to keep: a counting semaphore with **no queue and no waiters** (`acquire` just returns `false`), a process-global singleton, and no durability. |

---

## 4. Tool calling

| Component | Source | Verdict | Reason |
|---|---|---|---|
| Native tool calling (`tools` array out, `message.tool_calls` in) | Claudette `api.rs` | **REUSE** | Categorically better than ReAct text parsing. The single biggest gap in ABCC. |
| `ToolRegistry` + 20 on-demand groups | Claudette `tool_groups.rs` (`all() -> [ToolGroup; 20]` at `:144`) | **REUSE** | **Measured 2026-08-07, not read off a doc:** base schema **827 chars**, all 20 groups loaded **33,251 chars**. At Claudette's own `CHARS_PER_TOKEN = 4` that is **~207 tokens core versus ~33 KB fully loaded** — `docs/architecture.md:97`'s "~210 tokens / ~34 KB" checks out. Exactly 20 groups. |
| Workspace-gated pre-enable of the lean coding core | Claudette `ToolGroup::coding_core()` `tool_groups.rs:183` | **REUSE** | The fix for the 415-error `enable_tools` spiral. Carry the fix with the mechanism, never the mechanism alone. Four groups: Files, Search, Advanced, Quality. ⚠ **Measured at 12,161 chars ≈ 3,040 tokens, not the "~2.2k tokens" its own doc comment (`:175`) claims.** `questions.md` §3.3 item 10 inherits that understatement — the indirection's remaining payer is being asked to justify ~38% more schema than the number in the question suggests. |
| Forgiving `enable_tools` (empty group → coding core) | Claudette `executor::run_enable_tools` | **REUSE** | Same. |
| Schema-economy tests (`..._has_no_enum`, `coding_core_schema_stays_lean`) | Claudette `tool_groups.rs` tests | **REUSE** | Encodes *why* the schema is shaped this way so the reason survives refactoring. Copy the practice, not just the tests. |
| `every_advertised_tool_is_classified` regression test | Claudette | **REUSE** | Catches silently-dropped tools. Cheap, high value. |
| `WorkspaceRoots` (`tools.rs:589`) + `validate_read_path` (`:733`) + F5 fallback (`:646`) | Claudette `tools.rs` | **REUSE** | Multi-root, `PATH`-style, with the anti-hallucination probe. Also carries `startup_diagnostics` — the wrapper-forgot-`CLAUDETTE_WORKSPACE` warning, which fired for real during this verification pass. |
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
| Budget service, daily ceiling, force-to-local | ABCC `budgetService.ts` | **PORT** | Co-op mode needs exactly this. ⚠ **But it has never run.** Traced 2026-08-07: `recordUsage` has **exactly one production caller**, `routes/execution-logs.ts:55`, gated on `if (log.inputTokens || log.outputTokens)` — and those are always null, because the write path drops them (§0 item 10). Its other 14 call sites are its own test file. So the logic is well tested in isolation and has **never seen a real token**; read the row as "a design worth porting", not "a mechanism proven in use". Same applies to `costAggregator`. Q7's zero-spend ruling makes this small either way. |
| Cost calculator + per-tier rates | ABCC `costCalculator.ts`, `main.py:218` | **PORT** | Rates are stale; the structure is right. |
| Fine-tuning / LoRA | Claudette `CHAMPION-DOSSIER.md` §8 | **REFERENCE** | Already researched to a NO with four structural reasons and written trigger conditions. W4 should cite it, not redo it. |

---

## 6. Verification, gates and the stage pipeline

| Component | Source | Verdict | Reason |
|---|---|---|---|
| **Gate formula `critique*0.4 + verifier*0.6`** | BCF `mission.rs:1139` | **REUSE** | The most portable artifact in the three repos. Outvotes the judge instead of trusting it, and generalizes to arbitrary tasks in a way Q56's per-task verifiers cannot. |
| Complexity-scaled thresholds 9.2 / 8.5 / 8.0 | BCF `mission.rs:61` | **REFERENCE** | Inverted scaling is a real insight; the numbers are cloud-assisted calibration (all-local average was 7.5). Recalibrate, do not inherit. |
| Config-driven threshold, default 8.0, `aspirational` preset | `decisions.md` AD-7 — **and nowhere else** | **REWRITE** | ⚠ **Reclassified 2026-08-07.** Separating algorithm from policy is still the right resolution of the row above, but **this was never built.** Not in BCF (`grep -i aspirational src/` is empty; it ships the hardcoded ladder). Not in Claudette (no `gate_threshold`, no `--gate-threshold`, no `models.toml::pipeline` key — its forge gate is `VERIFIER_PASS_SCORE: u8 = 8`, hardcoded at `forge_run.rs:1310`, fail-closed). AD-7 is in the document that declares itself *"fiction relative to the shipped product"*. **The shape to copy is `max_fix_rounds()` (`forge_run.rs:41-61`)** — env override, clamped to a hard cap, warns on garbage, documented default — applied to the gate threshold. New work; budget it. |
| Surgical fix loop with best-round restore + decline detection | BCF `mission.rs` | **REUSE** | Family-wide convergent learning. |
| Refusing to restore a round the security stage rejected | Claudette `run/forge_run.rs` | **REUSE** | The improvement BCF's version lacks. |
| Five-phase forge pipeline (Planner → Coder → Verifier → Fix → Submit) | Claudette `run_forge_mission` | **REUSE** | The only stage pipeline in the family that runs daily against real repos. |
| Verifier JSON contract `{score, pass, feedback}`, fence-tolerant | Claudette | **REUSE** | Small, typed, already survives real model output. |
| Deterministic project verifier (lint + tests, per language) | BCF `verifier.rs` | **PORT** | ⚠ **Executed 2026-08-07 — "Python deep" is struck.** The *scoring model* (weighted static categories feeding the gate) generalizes and is worth porting. **No language branch is.** Rust/Go/TS-JS `syntax_valid` is substring presence, not parsing: the string `"this is not rust but it says fn  here"` scores **7.5**. `verify_python` `return`s early on a successful spawn, before its `has_tests` / `has_docstring` / `has_error_handling` assignments — so on *every* platform Python is docked ~2.5 points against other languages. On Windows it hardcodes `python3`, which resolves to the Store alias, spawns fine and exits 49 — **a correct Python file and a syntactically broken one both score 5.80**. See `verification.md` §2.2; this contaminates BCF's own all-local 7.5 average. |
| `check_secrets` + `check_todos` in scoring | BCF `verifier.rs:633-673` | **REUSE** | Cheap, language-independent, connects to W7. |
| `security_review.rs` deterministic added-lines scan | Claudette | **REUSE** | Deterministic, not an LLM. Correct shape for a gate input. ⚠ **But it is opt-in and off by default** — `enabled()` reads `CLAUDETTE_FORGE_SECURITY_REVIEW` (`:67`), and the module doc calls itself "a high-signal heuristic, **not** a full SAST" over a curated pattern set, added lines only. HIGH flips the round to not-passing; MEDIUM/LOW are advisory. **2.0 must decide whether this runs by default** — the row below only has teeth when it does. |
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
| `ExecutionLog` per-tool-call shape (thought/action/input/observation/timing/~~tokens~~/isLoop) | ABCC | **PORT** | This is the console's data. Best-designed table in the family — **on six of its seven fields.** ⚠ **Traced 2026-08-07: `tokens` is struck.** `input_tokens` / `output_tokens` / `model_used` exist in the schema, the Python producer sends them (`execution_logger.py:136-138`), the route's zod schema validates them (`routes/execution-logs.ts:25-27`) and forwards them — and then `ExecutionLogService.createLog` drops all three, because `CreateExecutionLogInput` (`executionLogService.ts:3-14`) has no such fields and `createLog` writes an explicit `data` list (`:24-34`) that omits them. TypeScript cannot see it: excess-property checking does not apply to **spread** properties. Two further drop points confirm there is no way in — `captureTrainingData` omits them from its log mapping and passes `tokens: undefined` (`taskExecutor.ts:637-647`), and the second write path, a raw `INSERT` in `mcp-gateway/adapters/postgres.py:239-249`, sends `model_used` but neither token column. **`data-assets.md`'s "0% populated" was an unreachable column, not neglect.** Port the shape; wire the fields; and note the table mixes conventions (`task_id` and `actionInput` side by side) — pick one in 2.0. |
| The Feb 2026 complexity-field collapse | ABCC migration | **REFERENCE** | Cautionary. BCF's typed `RoutingResult` is the fix. |
| JSON mission records | BCF `db.rs` | **DROP** | Superseded by Claudette's storage model. |
| `FileLock` per-path locks | ABCC `file_locks` table + `taskAssigner.ts` | **PORT** | Parallel builders need this; W6's worktree question may replace it. ⚠ **Read properly 2026-08-07 — port the table, not the code path.** The **table** is sound: `filePath` unique, `lockedByAgent` / `lockedByTask`, `expiresAt`, `onDelete: Cascade` from the task. It is also the one durable piece of ABCC's lifecycle. **The careful service is dead code:** `FileLockService` (`fileLock.ts`, 144 lines) respects ownership, takes over only expired locks, alerts on conflict and offers `cleanupExpiredLocks` — and its only references in the repo are its own definition and its own 16 tests. **What actually runs** is `TaskAssigner.lockFiles` (`:164-184`): a bare `upsert` per path with **no ownership check**, which silently overwrites another agent's live lock. The only guard is a read-then-assign pre-check in `assignNextTask` (`:45`, `:68`) — TOCTOU, and bypassed entirely by `routes/queue.ts:111` and `:314`, which call `assignTask` directly. `cleanupExpiredLocks` is never called from anywhere, so the effective GC is the task cascade. And the 30-minute lock TTL is only survivable because the 5-minute watchdog fires first — the TTL is not the safety net it looks like. |

---

## 8. Console, presentation and the fun layer

Everything here is the pillar Claudette deliberately omitted, so ABCC dominates.

| Component | Source | Verdict | Reason |
|---|---|---|---|
| **2D isometric projection math** (`isoProjection.ts`, 181 lines, zero deps) | ABCC `packages/ui/src/components/isometric/` | **REUSE** | ✅ **Read properly 2026-08-07 — upgraded from "exists" to "good".** Classic 2:1 diamond grid in pure screen-space math (`sx=(x−z)·64`, `sy=(x+z)·32`), explicitly no CSS 3D transforms. Ships `isoZIndex` depth sorting and a `Z_LAYER` table. Cleanly separated from the components that consume it, which is what makes it portable. ⚠ **Reason corrected 2026-08-07 (late), after running the UI:** this is sprite **placement** math over painted backdrops, **not a tile engine** — nothing draws a diamond grid. And `isoCubeFaces` / `isoHexFaces`, which the earlier note singled out as "the parts people get wrong", have **zero call sites**; only `getDiamondDimensions` is imported. REUSE stands on `worldToScreen` + `isoZIndex` + `Z_LAYER`; budget for the rest as unproven. |
| The isometric **renderer** (7 components: grid, tank, target, projectile, explosion, label, battlefield) | ABCC `components/isometric/` | ~~REFERENCE~~ → **PORT** | ⚠ **Re-verified by execution 2026-08-07 (late) — and it was wrong twice, in my own earlier note.** It does **not** render SVG-per-sprite: `IsometricTank` is an absolutely-positioned `div` + a radial-gradient glow `div` + one 280 px raster `<img>` (PNG, or GIF for coders), three DOM nodes per agent, and SVG appears only for the projectile tracer and one arc on the target. And **the 17×17 board is never drawn** — `IsometricGrid` is a single full-bleed background `<img>`, one of six pre-rendered battlefield JPEGs rotated every 10 tasks. **The look is art-driven, not engine-driven.** The frame-budget question that held this at REFERENCE is now **answered and favourable** (`verification.md` §3.5c): idle sprites are **free to ~100 entities** (pegged at the harness ceiling, 6.9 ms), the cliff is between 100 and 400 (20.8 ms) and 1,000 costs 48.6 ms. At any plausible 2.0 fleet size this technique needs **no canvas and no WebGL**. Two things to fix in the port: `iso-hex-glow` animates `filter: blur()` on every firing agent and **doubles** frame cost at N=100, so pre-blur and animate opacity instead; and four animated GIFs are **34.3 MB of the 35 MB** sprite budget (12.9 MB / 242 frames for the building) — no frame cost measured, memory under load **not** measured and still open. |
| React Three Fiber 3D battlefield (11 components) | ABCC `components/battlefield/` | **REFERENCE** | Real work, but the decision is isometric. Keep as a source of motifs. **Confirmed by the source itself 2026-08-07:** `BattlefieldView.tsx:13` calls it *"legacy Three.js canvas (lazy-loaded)"* and the running page has **zero `<canvas>` elements**. ABCC deprecated this path on its own; the REFERENCE verdict is not an outside judgment. All three views (`cards` / `isometric` / `3d`) are runtime-switchable from the top bar. |
| **96 Bark TTS voice lines** (6.7 MB, 3 packs) | ABCC `packages/ui/public/audio/` | **REUSE** | Irreplaceable and expensive to regenerate. Copy the files. Verified: `field-command` 32 + `mission-control` 32 + `tactical` 32. (Path corrected — it is under `packages/ui/`, and `packages/ui/dist/audio/` is a build-artifact duplicate, not a fourth pack.) |
| `audioManager.ts` playback queue + `voicePacks.ts` | ABCC | **PORT** | Small, and the queueing behaviour is the non-obvious part. |
| `bark-generate-all.py` regeneration script | ABCC `scripts/` | **REUSE** | Needed to extend the voice set. |
| ToolLog terminal feed, TokenBurnLog, CodeWindow | ABCC | **PORT** | The no-dead-air surfaces. ⚠ **TokenBurnLog read 2026-08-07: the layout is proven and the data path never was.** 322 lines, and it filters the live store on the same dead predicate as the API — `.filter(log => log.inputTokens \|\| log.outputTokens)` (`:93`) — so its real-data list is **always empty** (§0 item 10). Its only non-empty state is an opt-in demo that generates entries from `Math.random()` (`:63-75`, `:121-134`). The component is *not* the problem: mock mode defaults off, auto-disables when real data arrives, and is labelled *"a demo cosmetic, not a polling fallback"*. **But no human has ever seen this panel render a real number**, so W5 inherits a design with zero observed behaviour under real volume, and W8 inherits the reason cost was never measurable. **Seen running 2026-08-07** — it renders `BURN RATE 0/min · $0.0000 · In: 0 Out: 0 Total: 0 · No token usage yet`, with the `Demo` toggle visible in the panel header. ⚠ **And one structural fact for all three, found the same pass: the console is a live view, not a record.** The store is a **500-row ring buffer** (`store/uiState.ts:10`, enforced on both append and replace), `ToolLog` renders `slice(-50)`, and reconnect recovers `listRecent(200)` — while Postgres holds every row. Sound against unbounded growth; **a direct problem for 2.0's replay requirement**, which needs a paged read path against the store of record that ABCC never wired up. |
| Three minimaps (Minimap, FlowMinimap, TimelineMinimap) | ABCC | **REFERENCE** | Three attempts at one problem. Pick one deliberately in W5. (190 / 129 / 297 lines. Seen running 2026-08-07: `Minimap` is the circular radar sweep and it occupies the entire left column — a real estate decision W5 should make on purpose, not inherit.) |
| Dashboards (CostDashboard, SuccessRateChart, ComplexityDistribution, AgentComparison) | ABCC | **PORT** | Legibility over completeness: port selectively, not all four. ⚠ **Split 2026-08-07:** `SuccessRateChart`, `ComplexityDistribution` and `AgentComparison` read REST endpoints backed by columns that *are* populated, and draw **hand-rolled `<svg>` with no charting library** — the same zero-dependency instinct as `isoProjection.ts`, and worth keeping. `CostDashboard` is starved by §0 item 10 and renders zeros; it degrades rather than breaking, because it has a REST fallback alongside the live store. |
| Theme system (`classic.ts`, `battleclaw.ts`) | ABCC | **REUSE** | Personality-with-an-off-switch already has a mechanism. ✅ **Stronger than this row said, and now in tension with Q8.** Each theme is **~28 lines** and maps **domain vocabulary**, not colours: `taskQueue: 'Bounty Board'`, `agents: 'Strike Team'`, `dashboard: 'Intel Dashboard'`, plus a logo and an `agentIcons` map (coder→Sword, qa→Shield, cto→Crown). `classic.ts` is the off-switch. ⚠ **But Q8 puts the RTS framing into the Rust domain model**, where an enum variant named `Squad` cannot be renamed by a theme file. **W5 inherits an off-switch that the chosen depth partly disables and must decide what "off" means** — labels-only translation over fixed enums, or a neutral theme that is merely cosmetic. Not a reason to reopen Q8; a thing to design for. |
| `useSocket.ts` WebSocket event plumbing | ABCC | **PORT** | Event taxonomy is reusable; transport is W5's call. ⚠ **Read properly 2026-08-07 — 456 lines and 26 domain event handlers** (tasks, agents, execution logs and steps, alerts, cost, budget, chat streaming, validation pipeline, auto-retry, code review, five mission lifecycle events, clarification). **The no-dead-air logic lives inside the transport:** sound on status transition, a 3 s anti-overlap window, a milestone sound every 2 iterations, a failure sound when `currentIteration` *decreases*. **Port the taxonomy and break that coupling**, or 2.0 inherits it. Three scars to not repeat: `window.__ABCC_SOCKET__` and `window.chatHandlers` globals (HMR / StrictMode workarounds), and `MAX_PENDING_TIMEOUTS = 5` labelled "(OOM fix)". One pattern to keep: rehydrate the log buffer from REST on reconnect. |
| Chat panel, CTOWelcome, MissionProgressTracker | ABCC | **REFERENCE** | Overlaps the conversational surface Claudette already owns. |
| Ratatui TUI | Claudette `tui.rs` (5 tabs) and BCF `tui.rs` | **REFERENCE** | Decision is isometric web. Keep as the headless/SSH fallback question for W5, not the primary. |
| `snake.rs` / `space.rs` minigames | BCF | **REFERENCE** | Correct instinct about dead air, wrong answer. Make the work watchable instead. |
| macOS `say` voice announcements | BCF `voice.rs` | **DROP** | macOS-only; dead on the target hardware. |
| Bounty board | brief section 3.1 | **DROP** | Does not exist in any repo. **Confirmed 2026-08-07 with the UI running, and the phrase's origin found:** "BOUNTY BOARD" appears in the console because it is BattleClaw's *theme label for the task queue* (`themes/battleclaw.ts`). There is no bounty mechanic, no rewards, no claiming. DROP stands. |

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
| Permission tiers + `Operation` enum | Claudette `runtime/permissions.rs` | **PORT** | Three capability tiers plus two session-control modes; policy still keys off **tool name**, and the `Operation` enum that would let it key off the operation is built but only the prompter reads it. 2.0 should finish it. **Carry over §0 item 3's landmine: `PermissionMode::Prompt` is unused and, under the derived `Ord`, unreachable — a `Prompt` session auto-approves everything. Fix the ordering before reviving the mode.** |
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
| `doctor.rs` — ten diagnostic probes with copy-paste fixes | Claudette `doctor.rs` (1,045 lines) | **REUSE** | "It has to run on other people's machines" is a stated constraint; this is the mechanism. Verified: exactly ten — env, safety-overrides, brain, pick-brain, toolchains, recall, egress, google-oauth, voice, secrets. `probe_google_oauth` is `#[cfg(feature = "integrations")]`, so **the default air-gapped build ships nine**. Ran green end-to-end against live LM Studio 2026-08-07. |
| `setup.rs` five-step wizard + `firstrun.rs` failure classifier | Claudette `setup.rs` (233 lines) | **REUSE** | Same. Verified: `[1/5]` backend → `[2/5]` hardware → `[3/5]` brain + pull offer → `[4/5]` integrations → `[5/5]` doctor pass. Adds no probe logic of its own; it sequences `firstrun`, `hw` and `doctor` interactively — which is why it is cheap to carry. |
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

## 11a. Archive repos — `independencev1` and StealthForge

Added 2026-08-07. Two Rust repos in `D:\dev\_archive\abcc_projects\abcc_projects\`, active
April 2026, sitting in the family timeline between BCF's internal work and Claudette. Full
assessment in `archive-repos.md`; the paired-score dataset is in `data-assets.md` §6.

**Authorship, resolved by David 2026-08-07:** both were built in collaboration with **Hadar Raz**,
who was the projects' tech lead. David wrote all the code. They are still friends and there is no
dispute.

**The constraint that follows, and it applies to every row below: take the ideas and concepts,
never copy the code verbatim.** In this table that makes **PORT** mean *reimplement from the
concept* — which is what the verdict has always meant here (see the legend: "the idea is proven,
the implementation is in the wrong language"), except that here the implementation is already
Rust, so the reason is provenance rather than language. Read these repos for what they learned,
then write 2.0's version from the design. No file from either is copied into 2.0.

| Component | Source | Verdict | Reason |
|---|---|---|---|
| **Independence check as a pipeline stage** (separate process, different model, different method; `critic_inflation` recorded as a metric) | StealthForge `core/independence.rs`, `orchestrator.rs:876` | **PORT** | The only mechanism in the family that achieves gate independence in **single player**, which §17 Q6 made primary. Costs a second model pass, not a second machine. Veto threshold already calibrated 2.0 → 4.0 from regression data. Non-fatal by construction. |
| **Static analysis as a hard clamp on LLM scores** (no-compile → Correctness ≤ 4.0; tests fail → 5.0–7.0; zero tests → TestQuality ≤ 3.0; cloud may lower, never raise) | `independencev1/critics/scoring.rs:443` | **PORT** | Resolves `questions.md` §3.2 item 9 as a false choice: the deterministic verifier sets the ceiling, the LLM ranks underneath. Both coexist with a defined precedence. |
| The **7.0 floor** failure mode + its proposed fix (proportional clamp `min(7.0, 10·(M−N)/M)`) | `independencev1/CLAUDE.md` calibration | **REFERENCE** | Measured: TestQuality scored exactly 7.0 on 8 of 10 projects. An LLM panel does not discriminate in the middle of its range. A bug report with a patch, free to W6. |
| **Verification-gap checklist** — `--all-targets`, subdirectory manifest detection, security findings must reach the gate | StealthForge `BENCHMARK.md` post-mortem | **REFERENCE** | Four false PASSes bought these four rules. W6 constraints, not discoveries. |
| Legacy-review path (`--path` → `codebase_analyzer.rs` → refined mission) | StealthForge | **REFERENCE** | The family's only real legacy mode, and §17 Q2 named legacy review a target workload. Thin (204 lines), and its benchmark mission M11 was the worst gate divergence — which is itself the finding for W8. |
| Mechanical-failure guards (`dedup.rs` 1,646 lines: duplicate-file merge, `pub mod` guard, dependency fixer, derive guard) | StealthForge | **REFERENCE** | Credited with eliminating "almost all mechanical failures". Q56's tier-2 axis 2 independently found the same class dominating. Read the *categories* before W11 designs its fix loop. |
| Surgical fixer (only failing files + exact errors resent; ~10× faster than regeneration) | StealthForge `core/surgical_fixer.rs` | **REFERENCE** | Claudette's `apply_diff` occupies the ground more precisely. The economics argument transfers. |
| Sandbox QA agent — build in tmpdir, detect project type, LLM agent *uses* it, UX score reported **separately from the technical verdict** | `independencev1/sandbox/` | **REFERENCE** | A concrete answer to `questions.md` §3.5 item 17 (measure fun without asking). The separation of soft score from hard gate is the precedent worth keeping. Isolation (tmpdir + allowlist, no container) is too weak to inherit. |
| RAG + knowledge-graph memory (LanceDB 986 lines, petgraph 526 lines, 5.3 MB vectors, Distiller feedback loop) | StealthForge `memory/` | **REFERENCE** | Family's only long-term learning system, and genuinely interesting — but off by default, the feedback hook is a `TODO` that prints instead of ingesting, and no benchmark attributes anything to it. If 2.0 wants this it is a W-item with a measurement, not a 2,500-line inherited dependency. |
| **34-mission paired score dataset** (internal gate vs independent review) | StealthForge `generated/` | **REUSE** | A measurement, not code — the "no verbatim copying" constraint does not bind it. Extracted to `prestudy/data/stealthforge-mission-reports.tsv`. The evidence base for W6's gate design. |
| The 9.5-overall / 9.7-critical gate thresholds | StealthForge | **DROP** | Produced a 100% pass rate on artifacts an independent reviewer graded D and F. Same lesson as §0 item 2, one step earlier and one step worse. |
| The self-scored critic panel *as the deciding gate* | StealthForge | **DROP** | Keep the panel as a signal. Never let it be the thing that decides. |
| Grok as primary model | StealthForge | **DROP** | Contradicts local-first. |
| Both codebases wholesale | both | **DROP** | 6k and 11k lines, tokio-heavy, Grok-first / Ollama-first, no inheritable test suite. Claudette is the better engine on every axis the brief cares about. |

---

## 12. Summary by verdict

Counts updated 2026-08-07 to include §11a (14 rows: +2 PORT, +6 REFERENCE, +1 REUSE, +5 DROP).
**The second verification pass (evening) changed no counts** — all six ABCC rows it examined stayed
PORT or REFERENCE. Six reasons were rewritten; see `verification.md` §4.2.

| Verdict | Count | Where it concentrates |
|---|---|---|
| **REUSE** | 49 | Overwhelmingly Claudette. The harness, the tools, the safety layer, the eval. |
| **PORT** | **21** | Mostly ABCC — the complexity model and the console surfaces — plus the two gate-independence mechanisms from the archive repos. **+1 on 2026-08-07 (late): the isometric renderer, promoted from REFERENCE once the frame-budget question was measured and came back favourable.** |
| **REFERENCE** | **27** | Spread evenly. Mostly negative results and superseded attempts. (−1: the isometric renderer left for PORT.) |
| **DROP** | 26 | Mostly ABCC infrastructure, BCF's commercial scaffolding, and StealthForge's self-scored gate. |
| **REWRITE** | **7** | The genuinely new work: provider abstraction, difficulty/context separation, TTFT, operator metrics, one security test — **plus two added by the 2026-08-07 verification pass: peak VRAM/RAM reporting (W1, W2) and the config-driven gate threshold (W6)**, both of which the map had recorded as existing assets and neither of which is implemented anywhere. |

**The shape this implies:** 2.0 is Claudette's engine with ABCC's console bolted onto it, BCF's
gate arithmetic inserted at the verification boundary, and about five things that nobody has built
yet. Only seven REWRITE rows is the headline: the brief expected a research project and Phase 0
found mostly an integration project with a hard UI problem attached. Verification moved two rows
*into* that column rather than out of it — a reminder that the risk in this map is rows recorded as
"already exists, carry it" that turn out not to exist.

**The five genuinely open pieces**, which is where Phase 1 effort should concentrate:

1. **The provider abstraction** (W10) — local, cloud and remote rig behind one trait. Nothing
   existing is a starting point.
2. **Difficulty separated from required context** (W4) — fused in every existing implementation.
3. **Operator control as a measurable property** (W5, W8) — pause, redirect, take-over, replay.
   No repo has it and no eval measures it.
4. ~~**Gate independence in single-player**~~ (W6, W11) — **no longer open in the "does it matter"
   sense, as of 2026-08-07.** StealthForge measured it: median **+3.65** points of self-scoring
   inflation across 34 missions, **0 of 34** where the independent reviewer scored higher. BCF's
   formula reduces the bias; the residual is larger than the gaps it discriminates between. What
   remains open is *implementation*: who plays the reviewer in 2.0, whether it always runs, and
   whether `critic_inflation` becomes a console metric. See §11a and `archive-repos.md` §5.
5. **Async or not** (W3) — the donors disagree and 2.0's requirements postdate the decision.

---

## 13. Confidence

**High** on every verdict sourced from code read at a pinned commit, which is most of the table.

**Updated 2026-08-07 by the verification pass.** See `verification.md` for the full ledger.

**~~Medium~~ → resolved on the BCF verifier's language-generality claim.** It was executed against
fixtures per language. The claim did not survive: no language branch parses anything, Python is
docked ~2.5 points on every platform by an early `return`, and on Windows a correct and a broken
Python file both score 5.80. §6's row is rewritten and `verification.md` §2.2 has the table.

**~~Medium~~ → ~~partly resolved~~ → resolved on the presentation layer, 2026-08-07 (late), by
running the UI.** `isoProjection.ts` is a good foundation — 181 lines of dependency-free 2:1
projection math — though it is placement math, not a tile engine, and two of its exports are unused.
~~The *renderer* around it was narrowed to REFERENCE: SVG-per-sprite on a 17×17 board, with the
frame-budget question still open.~~ **That reading was wrong** (§0 item 11): raster sprites, no
drawn board, and the frame-budget question is now **measured and favourable**, which promoted the
renderer to PORT. ToolLog, TokenBurnLog, CodeWindow, the dashboards, `useSocket.ts` and the theme
system were all read properly and their rows rewritten.

**Still Medium in §8, and now a short list:** `audioManager.ts`'s queueing behaviour, which the map
calls "the non-obvious part" and which still has not been executed; the three minimaps, read only far
enough to confirm what each one shows; and **memory under real event volume** — the one half of the
frame-budget question that survives, since 34.3 MB of animated GIF cost no measurable *frame* time
and this harness could not see decode memory. That needs the UI against a live backend.

**~~Still Medium, and now explicit~~ → resolved 2026-08-07 (second pass).** ABCC's §2 PORT rows
(task lifecycle, queue, resource pool, stuck-task watchdog) and §7's `ExecutionLog` / `FileLock`
were traced and their test suites **run** — 81 tests, 32.4 s, all passing. **No verdict changed.**
Six *reasons* did, and one of them reversed: "cleanup is complete" was the sentence telling 2.0 it
could carry the watchdog across as-is, and the cleanup is complete only of a found-set that omits
two of the states a task can hang in. Full ledger in `verification.md` §3.4 and §4.2.

**Still Medium:** the rest of §8 — ToolLog, CodeWindow, the three minimaps, the four dashboards,
`useSocket.ts`, the theme system, and `audioManager.ts`'s queueing. Inventory-only, and the UI has
still never been run, so the frame-budget question stays open for W5.

**High** on every verdict sourced from code read at a pinned commit, which is most of the table,
and now higher on the rows that were re-measured or executed rather than read.

**One caveat that applies to the whole table, learned from the second pass.** A row saying a
component is well built is not a claim that it ever ran. Four things this pass looked at are
well built and connected to nothing: `FileLockService`, `budgetService`, the three token columns,
and `TokenBurnLog`'s real-data path. Where a row's value depends on the component having been
*exercised*, that is now said explicitly in the row. Where it is not said, assume it was read.

**Low, and marked as such in the rows:** anything about how well a component *works* as opposed to
what it *is*. Executed this pass: Claudette's suite (**1,145 pass / 0 fail**, 3.8 s), BCF's
(**98 pass / 0 fail** — the two previously-failing tests are shell-dependent, see
`verification.md` §2.4), BCF's per-language verifier against fixtures, Claudette's tool-schema
sizes, and `claudette --doctor` end-to-end against live LM Studio. **Still true: no model was
prompted, no mission was run, no battery was reproduced, and ABCC's UI was never started.**
