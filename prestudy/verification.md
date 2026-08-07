# Verification Pass

**Why this exists.** Phase 0's dossiers and the inheritance map were written by reading. David's
instruction before Phase 1 starts: *"read the code to get source of truth."* The one confirmed
error found during his review had been sourced from a repo's **own documentation** rather than its
source, and Claudette's `docs/decisions.md` opens by declaring itself *"fiction relative to the
shipped product"*. Repo documentation in this family is a known contamination vector.

**Scope, as agreed.** Not a re-read of everything. Four targets:

1. Claims sourced from a repo's own docs rather than its source.
2. Every **PORT / REWRITE / REUSE** row a build decision rests on.
3. Everything the map already self-flags Medium or Low confidence (§13).
4. Anything involving **ordering, comparison or control flow** — those get *executed*, not read.
   That rule is why the `PermissionMode::Prompt` trap was found at all.

Descriptive "what it is" rows and **DROP** rows are skipped: nothing is being built on them.

**Method.** Per repo, at the pinned commit, working tree confirmed clean. Static citations checked
by opening the cited line. Countable claims counted. Numeric claims re-measured. Where a claim
could be executed, it was.

**Environment.** David confirmed LM Studio and Docker were up for this pass, so the model-boundary
and hardware rows were exercised live rather than read. That is new evidence Phase 0 did not have.

---

## 1. Claudette — pin `fc1ea22` (v0.17.0), tree clean

66,619 lines of Rust across 101 files in one crate. Carries the most REUSE rows in the map, so it
was done first.

### 1.1 Executed, not read

| Check | Result |
|---|---|
| Full test suite, default features | **1,145 pass, 0 fail, 6 ignored** in the lib binary; 1,186 across all 6 binaries |
| Full test suite, `--all-features` | **1,232 pass, 0 fail**; 1,274 across all binaries |
| `claudette --doctor` against live LM Studio | **all probes passed** |
| Tool-schema payload sizes | measured with a throwaway integration test, since removed |
| `best_round` restore ordering | comparator read in full against its doc comment |

### 1.2 The tool-schema numbers — a doc-sourced claim that survives

The map's §4 figure "~210 tokens core versus ~34 KB fully loaded" came from
`docs/architecture.md:97`. It is **correct**. Measured directly off `ToolRegistry`:

| Payload | Chars | Tokens (at Claudette's own `CHARS_PER_TOKEN = 4`) |
|---|---|---|
| Base (`enable_tools` + `get_current_time`) | **827** | ~207 |
| Coding core (Files, Search, Advanced, Quality) | **12,161** | **~3,040** |
| All 20 groups loaded at once | **33,251** | ~8,310 (~33 KB) |

`ToolGroup::all()` returns exactly 20. The base and full-load figures check out.

**The middle row does not.** `tool_groups.rs:175` says the coding core "Costs ~2.2k tokens of
schema". Measured, it is **~3,040** — about 38% more. `questions.md` §3.3 item 10 asks whether the
`enable_tools` indirection still earns its keep now that a coding session pre-ships the core; it
inherits the understated number. The question is sharper than it reads.

### 1.3 The `14.76 s` is measuring something else

The map justifies the `ConversationRuntime` REUSE row with "1,145 tests run in 14.76 s without a
model". The **1,145** is exactly right — it is the default-feature lib binary, to the test.

The timing is not. Measured on David's machine at the pinned commit:

| What | Wall clock |
|---|---|
| The 1,145 tests themselves | **3.76 s** |
| `cargo test`, warm, nothing to rebuild | 4 s |
| `cargo test` after touching one source file (incremental build + test) | **17 s** |
| `cargo check` after touching one source file | **6 s** |

So 14.76 s is the **edit-to-green cycle**, not test execution. Both numbers are real and they mean
different things. This matters twice:

- `questions.md` §4 item 6 says *"Claudette's 14.76 s is the bar and agent loop latency is bounded
  by it."* The bar for a test *run* is 3.8 s and the bar for an *edit-to-green loop* is ~17 s.
- `questions.md` §3.1 item 3 asks whether `cargo check` latency drives 2.0 toward a workspace.
  The number it needs is **6 s at 66.6k lines in one crate**, now measured.

### 1.4 The `hw.rs` row was wrong twice — and it costs W1/W2 real work

The map read: *"`hw.rs` GPU/VRAM/**temperature** probes — W1 and W2 need this to report peak
**RAM** per configuration."*

`hw.rs` is 208 lines with four public functions: `parse_nvidia_smi_mib`, `detect_vram_gb`,
`resolve_vram_gb`, `recommend_brain`. There is **no temperature probe**. There is **no system-RAM
probe** — its own module doc says "no NVML/sysinfo bindings", and `sysinfo` appears nowhere in the
crate. It reads *installed* VRAM off `nvidia-smi`; it never reads *peak* anything.

`questions.md` §4 item 1 wants "peak system RAM and VRAM for N concurrent builders … a hard limit
reported, not a tuning suggestion." **Nothing in the family implements that.** The map recorded it
as an existing asset to REUSE. It is new work, and it is now a REWRITE row.

What `hw.rs` *does* do was verified live: `detect_vram_gb` reported **15.9 GiB** correctly.

### 1.5 The residency reframing is now code-sourced

`questions.md` §1 — the one settled decision Phase 0 reopened, and the correction the most
workstreams inherit — rested entirely on `CHAMPION-DOSSIER.md`. A document.

It does not have to. `hw.rs:103-109` ships the VRAM→brain recommendation as code, and the string it
prints to every user is:

> 50/50 + K 8/8 on the 50-task battery (49/50 at 64k ctx) at ~70-76 tok/s — **fully VRAM-resident
> in 13.6 GB, zero RAM spill**. Load with the README's champion command (ctx 65536 + MTP flags)

Claudette's installer tells its users the crowned configuration does not spill. W1 and W2 can be
reframed from "survive expert offload into 32 GB" to "stay resident in 16 GB" **now**, without
waiting on the reproduction run.

Two riders from the same live `--doctor`:

- `hw.rs:108` cites the **50-task + K1-K8** battery, not Q56 — a third independent confirmation of
  §0 item 5. The instrument Claudette ships against is on `main`; Q56 is a different battery on an
  unmerged branch. The §9 row that names them as one thing is confirmed wrong.
- David's live environment: `CLAUDETTE_MODEL=qwen3.6-35b-a3b-mtp@iq3_s`,
  **`CLAUDETTE_NUM_CTX=61440`**, `CLAUDETTE_NUM_PREDICT=16384`. `T2.md` axis 4 says Q56 never
  stresses ctx 32768 — meanwhile the daily driver runs at **60k**. The evaluation gap W8 has to
  close is wider than the map records.

### 1.6 Ordering and control flow — executed, per the standing rule

**`best_round` (`forge_run.rs:269`) is correct.** This is the same shape as the
`PermissionMode::Prompt` trap — a comparator whose doc comment and behaviour could silently
disagree — so it was read in full rather than trusted. `min_by` maps "better" to "smaller":
`(!a.pass).cmp(&!b.pass)` → `security_high` → `b.score.cmp(&a.score)` → `a.round.cmp(&b.round)`.
Doc matches code. No inversion. The apparent conflict (a *passing* round with a HIGH finding
outranking a *failing* clean one) cannot occur: a HIGH finding flips the round to not-passing
upstream, so the two keys never disagree.

**But the stage it defends is off by default.** `security_review::enabled()` (`:67`) reads
`CLAUDETTE_FORGE_SECURITY_REVIEW`, and the module doc calls itself *"a high-signal heuristic, **not**
a full SAST"* over a curated pattern set, added lines only. The map presents
"refusing to restore a round the security stage rejected" as a shipped improvement over BCF. It is
— but only when a user opts in. **2.0 has to decide whether it runs by default**, and that decision
belongs to W6, not to a footnote.

### 1.7 Loop breakers: 12, not 9

The map says "9 situations, 9 purpose-written nudges" at `conversation.rs:1210-1443`. That range
holds seven of them. Counting the whole file, there are **twelve** distinct purpose-written
interventions, spanning `:57` to `:1470`:

iteration-budget warning (`:57`) · graceful cap landing prompt (`:69`) · tool-refusal during
landing (`:78`) · empty-turn continuation nudge (`:1063`) · unknown-tool near-miss body (`:1210`) ·
over-search budget nudge (`:1237`) · duplicate navigation suppression (`:1278`) · duplicate block
edit suppression (`:1303`) · duplicate *denied* call suppression (`:1319`) · empty cap-landing
fallback reply (`:1377`) · unchanged re-read pointer-up (`:1443`) · no-progress nudge (`:1459`).

The verdict does not change. The asset is bigger than recorded, and each nudge carries the dated
incident that motivated it — which is the practice §11 says W13 should mandate.

### 1.8 Citations checked, claims confirmed

| Claim | Verdict |
|---|---|
| Empty-turn detection at `conversation.rs:1033-1123` | ✅ exact |
| Model-reload transient retry at `api.rs:647-668` | ✅ exact |
| `truncate_to_budget` at `api.rs:1554` | ✅ — but `CHARS_PER_TOKEN` / `SAFETY_CHARS` are at `:151` / `:154`, not in the cited range |
| `WorkspaceRoots` at `tools.rs:571-646` | ⚠ struct is at `:589`, F5 fallback at `:646`; `validate_read_path` is at `:733`, outside the range |
| Five-phase forge pipeline | ✅ `forge_run.rs:592` / `:621` / `:943` |
| `forge_run.rs` is 1,687 lines | ❌ **1,803** at the pinned commit |
| `MAX_FIX_ROUNDS = 3` | ⚠ it is `DEFAULT_MAX_FIX_ROUNDS`, env-overridable, hard cap 10 — **Claudette already separates algorithm from policy**, which is what §6 recommends BCF's gate threshold should do |
| `doctor.rs` ten probes | ✅ exactly ten — **nine in the default air-gapped build** (`probe_google_oauth` is `#[cfg(feature = "integrations")]`) |
| `setup.rs` five-step wizard | ✅ `[1/5]`…`[5/5]` |
| `plans/` 119 files | ✅ 119 — but `/plans/` is in `.git/info/exclude`, so it is **local-only and untracked**, same hazard class as `/runs/` |
| `recall.sqlite` 50k-row FIFO | ✅ `RECALL_ROW_CAP = 50_000` (`recall.rs:130`) |
| `default = []` structural air-gap | ✅ `Cargo.toml:42`, with the reasoning inline |
| `opt-level = "z"` + LTO + strip + `panic = "abort"` | ✅ |
| `egress.rs` two enforcement layers | ✅ `guard` (HTTP) + `guard_subprocess`, uniform refusal |
| `secrets.rs` `0600` / Windows ACL | ✅ `mode(0o600)` on Unix, `icacls` tighten on Windows |
| `transcript.rs` per-turn **and** per-action undo, trash-backed | ✅ `begin_turn` / turn-tagged lines / `undo_last`; ReadOnly never logged |
| `ProviderKind` two variants, one feature-gated | ✅ `Ollama` + `AnthropicClaude` (v0.2 feature-gated) — REWRITE stands |
| `brain_selector.rs` tiered fallback + stuck diagnostics | ✅ three strict stuck signals — note it is **single-fallback with per-turn revert**, built for 4b→9b swaps, not an N-tier cloud ladder |
| Live OpenAI-compat dialect reaches LM Studio | ✅ `/v1/models` HTTP 200, 24 models, brain loaded |

### 1.9 A hazard worth naming once

Three of Claudette's most valuable assets are invisible to `git status` and to a clone:
`/runs/` (the 131-config evidence base), `/plans/` (119 sprint specs, the W13 precedent), and the
Q56 corpus on an unmerged branch. All three are cited in the map as things 2.0 inherits. Two are
untracked via a local-only `.git/info/exclude`; the third needs a branch name nobody would guess.
**A clone of `main` gets none of them and reports no error.** §0 item 5 flagged this for Q56 alone;
it is a pattern, not an incident.

---

## 2. battle-command-forge — pin `d6c1601` (v0.2.0), tree clean

Fewer rows, but one of them is `§13`'s standing Medium-confidence admission: *"I read the dispatch
branches for Python, Rust, Go and TS/JS but did not execute any of them."* So they were executed.

### 2.1 The headline rows are exact

| Claim | Verdict |
|---|---|
| Gate formula `critique*0.4 + verifier*0.6` at `mission.rs:1139` | ✅ **exact** — `critique_avg * 0.4 + verifier_score * 0.6`, with the reasoning inline: *"Verifier (tests + linting) is the real quality signal — weight it higher"* |
| Thresholds 9.2 / 8.5 / 8.0 at `mission.rs:61` | ✅ **exact** — `quality_gate()`, `0..=6 => 9.2`, `7..=8 => 8.5`, `_ => 8.0` |
| `RoutingResult` keeps `rule_score` **and** `ai_score` as typed fields | ✅ `router.rs:60` — `rule_score: f32`, `ai_score: Option<f32>`, plus `ComplexitySource {Rules, Ai, Dual}` |
| `model_config.rs` 8 roles, fast/balanced/premium | ✅ architect, tester, coder, fix_coder, security, critique, cto, complexity; 3 presets |
| A tiny dedicated model scores complexity (§1 convergence) | ✅ `complexity: RoleConfig::local("qwen3.5:4b-q8_0")` in every preset |
| Subprocess env **allowlist** | ✅ `ALLOWED_ENV_NAMES` + `LC_` prefix; the doc comment names the exact leaks that motivated it |
| `validate_path_within` traversal / absolute / NUL / backslash | ✅ with the `..`-in-filename regression test |
| BCF test suite "96 pass, 2 fail" (§13) | ⚠ now **98 pass, 0 fail** — see 2.4 |

BCF's own fix cap is `MAX_FIX_ROUNDS = 5` (`mission.rs:52`), against Claudette's default of 3.

### 2.2 The deterministic verifier does not survive execution

The map's PORT row reads *"Python deep, Rust/Go/TS-JS shallow, six static-check categories. The
scoring model generalizes."* Executed against fixtures on David's machine:

| Fixture | Language | Score | `syntax_valid` | `has_tests` | `has_docstring` | `has_error_handling` |
|---|---|---|---|---|---|---|
| Valid, tested, documented Python | python | **5.80** | false | false | false | false |
| **Syntactically broken** Python | python | **5.80** | false | false | false | false |
| Good Rust | rust | 10.00 | true | true | true | true |
| **`"this is not rust but it says fn  here"`** | rust | **7.50** | **true** | false | false | false |
| Good Go | go | 10.00 | true | true | true | true |
| Good TypeScript | typescript | 10.00 | true | true | true | true |

Three separate defects, and the row is wrong in both halves.

**(a) The non-Python branches are not "shallow", they are substring presence.** `verify_rust` sets
`syntax_valid = content.contains("fn ") || contains("struct ") || contains("impl ")`. A line of
English prose containing `fn ` scores 7.5. `verify_go` needs `package ` and `func `; `verify_js_ts`
needs any of `function `/`const `/`export `/`class `. Nothing is parsed. A model that emits
plausible-looking non-code passes.

**(b) `verify_python` returns early and discards three of its four signals.** This is
platform-independent. `verifier.rs:678-697`: when the `python3` spawn *succeeds*, the function sets
`syntax_valid` and then `return`s — before the `has_tests` / `has_docstring` /
`has_error_handling` assignments, which sit **after** the block and are only reached when the spawn
*fails*. So on a working Linux box a good Python file gets `syntax_valid` (+1.5) but can never earn
the +1.0 tests, +0.5 docstring or +1.0 error-handling credit that an equivalent Rust file collects
for free. **Python is structurally penalised ~2.5 points against every other language**, in the
component that carries 60% of the gate.

**(c) On Windows it is worse: every Python file is reported as a syntax error.** `verify_python`
hardcodes `Command::new("python3")` with no fallback — even though `run_project_tests`
(`verifier.rs:160`) gets this right with `if cfg!(windows) { "python" } else { "python3" }`, which
is what makes it an oversight rather than a decision. On Windows `python3` resolves to the
Microsoft Store App Execution Alias, which **spawns successfully and exits 49**. So
`status.success()` is false, `syntax_valid` is set false, and a bogus *"Python syntax error in
generated code"* lint issue is appended — for correct code. Measured above: a good Python file and
a broken one are indistinguishable at 5.80.

**Why this matters beyond a bug report.** §0 item 2 records that BCF's 10-mission all-local stress
test averaged **7.5**, and the map and `questions.md` §3.2 item 6 both build on that number to
argue the *thresholds* need recalibrating for local-first. That average was produced by this
verifier. If those missions were Python — BCF's deepest-supported language — the 60%-weighted
deterministic component was pinned near 5.8 regardless of output quality. **The instrument was
miscalibrated before the thresholds were.** W6 cannot recalibrate against BCF's numbers without
first deciding whether to trust the measurement that produced them.

The verdict stays **PORT** and the reason gets stronger, not weaker: the *scoring model*
(weighted static categories feeding a gate) is worth keeping; the *implementation* is not a
starting point for any language, and "Python deep" should be struck.

### 2.3 The `aspirational` preset does not exist

§6 has a **PORT** row: *"Config-driven threshold, default 8.0, `aspirational` preset |
`decisions.md` AD-7 | The right resolution of the row above."* Checked against both codebases:

- Not in BCF. `grep -i aspirational src/` is empty; BCF ships the hardcoded 9.2/8.5/8.0 ladder.
- Not in Claudette. No `gate_threshold`, no `--gate-threshold`, no `models.toml::pipeline` key.
  Claudette's forge gate is **`VERIFIER_PASS_SCORE: u8 = 8`**, hardcoded (`forge_run.rs:1310`),
  applied as `pass = model_pass && score >= VERIFIER_PASS_SCORE`, fail-closed (a degenerate
  Verifier response abstains as `pass=false, score=0` so it can never win best-round restore).

So AD-7's config-driven threshold is a design that was written down and never built, in the
document that opens by declaring itself *"fiction relative to the shipped product"*. The row is
still worth doing — but it is **new work**, not an inheritance, and W6 must budget it as such.

The precedent to copy is in the same repo, one file over: `max_fix_rounds()`
(`forge_run.rs:41-61`) is exactly the algorithm/policy separation AD-7 describes — env override,
clamped to a hard cap, warns on an unparseable value, falls back to a documented default. Port
*that shape* and apply it to the gate threshold.

### 2.4 The two failing tests now pass, for an uncomfortable reason

§13 records BCF at "96 pass, 2 fail". It now runs **98 pass, 0 fail** — same total, so two tests
changed verdict without the code changing.

The likely pair is the Unix-binary tests: `test_env_var_stripping` (`sandbox.rs:472`) runs
`run_tool("env", …)` and `test_timeout_kills_process` runs `sleep 30`. Neither binary exists on a
stock Windows box. This pass ran from Git Bash, so both resolved off `PATH` and genuinely executed.

That confirms the map's **REWRITE** verdict on `test_env_var_stripping` and sharpens it. The map
says *"passes vacuously on Windows … the control is real; the evidence is not."* More precisely:
**the test silently changes meaning with the shell it is invoked from.** From Git Bash it really
runs `env`, really greps the child environment, and really passes — so the allowlist control is now
positively verified, which it never was before. From PowerShell the spawn fails, stdout is empty,
and `!stdout.contains("secret123")` is vacuously true. Same test, same machine, opposite epistemic
value, no signal telling you which one you got. That is the defect to fix in 2.0, and it is a
sharper lesson than "it doesn't work on Windows".

## 3. ABCC v1 — pin `d5528ea`, tree clean

### 3.1 Confirmed

| Claim | Verdict |
|---|---|
| Campbell rule-based scorer at `taskRouter.ts:105-239` | ✅ `calculateComplexity` starts at `:105`; base score 1, structural group (step count, unique file extensions, def/class count) then semantic keyword tiers |
| **The substring-matching defect** ("`'api'` matches inside `rapid`") | ✅ **confirmed** — `'api'` is a keyword at `:156` and matching is `complexityIndicators.<tier>.filter(k => text.includes(k))` at `:175`, `:180`, `:185`, `:190`. Unanchored substring containment on every tier. `'add'` (low tier) also fires on "address"; `'api'` fires on "rapid"/"therapy". Port the structure, fix the matcher — the map is right. |
| Complexity → context-size coupling at `taskRouter.ts:382` | ✅ `const ctxSize = complexity >= 7 ? '32K' : '16K'` — a bare ternary. REWRITE stands. |
| The real escalation ladder is C1-C6 → 16K, C7+ → 32K (`questions.md` §5 item 2) | ✅ corroborated by the same line. Confirms "Haiku was never an execution tier". |
| **96 Bark TTS voice lines, 3 packs** | ✅ `field-command` 32 + `mission-control` 32 + `tactical` 32 = **96**, plus a README. **6.7 MB** measured (map says 6.4). Path is `packages/ui/public/audio/`, not `public/audio/`. |
| 2D isometric renderer, 8 components | ✅ `IsometricBattlefield`, `Grid`, `Tank`, `Target`, `Projectile`, `Explosion`, `Label` + `isoProjection.ts` |

### 3.2 The isometric renderer: upgraded from "exists" to "good", with one caveat

§13's standing admission was *"I inventoried ABCC's components by file and read their names and
imports, not their rendering logic. Whether `isoProjection.ts` is a good foundation or merely an
existing one is a W5 judgment."* Read properly, it is **a good foundation**:

- 181 lines, **zero dependencies**. Classic 2:1 diamond grid: `sx = (x-z)·64 + originX`,
  `sy = (x+z)·32 + originY`. Pure screen-space math, explicitly "no CSS 3D transforms needed".
- Ships the parts people get wrong: `isoZIndex` depth sorting (south-east renders on top), a
  `Z_LAYER` table (building / agent / projectile / explosion / label), and `isoCubeFaces`, which
  returns SVG polygon point strings for the three visible faces of a block.
- It is the *math*, cleanly separated from the components that consume it. That is exactly what
  makes it portable — 2.0 can keep the projection and replace the renderer.

**The caveat W5 needs.** It renders through **SVG polygons with DOM `z-index`**, and `GRID_RANGE`
is 8 (a 17×17 board). `questions.md` §4 item 7 asks about the console's frame budget "with a live
task graph at 2.0's event volume" and notes ABCC's React Three Fiber battlefield was built for
three agents. **The same question applies to the isometric path and is not answered by it** — one
DOM node per sprite is a different scaling curve from canvas or WebGL. Also note `isoZIndex` mixes
the spatial key and the layer key on one scale (`(x+z)·10 + layerOffset`, layers spaced 100 apart),
so layer priority only dominates within ~10 world units of separation. Fine on a 17×17 board;
something to re-derive if 2.0's board grows.

So: **REUSE the projection module, treat the renderer as an open W5 question.** That is a narrower
and more useful verdict than "W5 starts here".

### 3.3 Not verified in the first pass

Stated plainly rather than left to look checked:

- The remaining §8 presentation rows (ToolLog, TokenBurnLog, CodeWindow, the three minimaps, the
  four dashboards, `useSocket.ts`, the theme system). Component inventory only, as before.
  **TokenBurnLog is now partly covered — see §3.4(i).**
- `audioManager.ts` queueing behaviour — the map calls the queueing "the non-obvious part" and it
  was not executed. **Still not executed.**
- ~~§2's PORT rows (task lifecycle, queue, resource pool, stuck-task watchdog) and §7's
  `ExecutionLog` shape / `FileLock`.~~ → **done, see §3.4.**
- The UI has still never been run. The frame-budget question (§4 item 7) needs it. §3.4 ran
  ABCC's API test suites, which is the first time anything in ABCC was executed for this study,
  but that is Node and mocked Prisma — not the stack, and not the browser.

### 3.4 The §2 and §7 PORT rows — executed, second pass (2026-08-07, evening)

These four concerns — task lifecycle, queue, resource pool, file locks — plus the watchdog and
`ExecutionLog` carry build decisions, so they get the full treatment: the suites were **run**, and
the token path was **traced end to end** rather than read at one site.

**Headline: no verdict flips.** All six rows stay where they were. But one row's stated *reason*
reverses outright, one citation has gone stale, and the trace found the mechanism behind a hole the
data-assets pass could only observe.

#### (a) The citation has moved out from under §2

`taskQueue.ts` is no longer the queue. It is a **275-line facade**: eleven methods, most marked
`@deprecated`, each a one-line delegation. The lifecycle now lives in **`taskExecutor.ts` (700
lines)** and **`taskAssigner.ts` (233)**, both split out of it. §2 cites `taskQueue.ts` for "rest
delays / periodic context reset"; those moved to **`ollamaOptimizer.ts`** and are not in
`taskQueue.ts` at all. Only `requestHumanInput` / `provideHumanInput` / `returnToPool` still have
bodies there.

#### (b) Executed: 81 tests pass in 32.4 s

First execution of anything in ABCC for this study. `jest` with `jest-mock-extended` mocking
Prisma; no Postgres, no Docker.

| Suite | Tests |
|---|---|
| `resourcePool.test.ts` | 19 |
| `taskAssigner.test.ts` | 19 |
| `taskQueue.test.ts` | 18 |
| `fileLock.test.ts` | 16 |
| `stuckTaskRecovery.test.ts` | 8 |
| `taskExecutor.test.ts` | **1** |
| **Total** | **81 passed / 0 failed, 32.359 s** |

**0.40 s per test, against Claudette's 0.0033 s (1,145 in 3.76 s) — a ~120× gap**, and the reason
is visible in the run log: the suite sleeps through the **real** rest delays. Timestamps from the
run: `20:19:56.416` "resting, restSeconds: 3" → next line `20:19:59.431`; then "restSeconds: 8" at
`20:19:59.437` → `20:20:07.449`. `OllamaOptimizer.applyRestDelay` awaits a bare
`setTimeout` (`ollamaOptimizer.ts:25`, `:105`) with no injected clock, so ~14 s of the 32 is the
test suite waiting in wall-clock time. **This is the §2 `ConversationRuntime` REUSE row's argument,
measured on both sides of the family** — and a concrete instruction for the port: the delay must be
injectable.

#### (c) The coverage is inverted relative to the risk

- **`taskExecutor.test.ts` has one test, and it is `'should exist and be importable'`.** The
  700-line lifecycle core — completion, failure, retry, abort, resource release, rest delay,
  training capture, auto-assign — has **no behavioural coverage**. It is also the file that took
  the pin's HEAD commit (#229, a retry bug, 2026-08-06).
- **`stuckTaskRecovery.test.ts`'s 8 tests never reach `recoverStuckTask`.** They cover the
  constructor, start/stop, `getStatus`, `updateConfig`, and one `checkAndRecoverStuckTasks` case:
  *"should return empty array when no stuck tasks"*. The recovery path the map calls "the part
  usually done wrong" is **untested**, and so is `forceRecoverAll`.
- **`fileLock.test.ts`'s 16 tests cover a class nothing calls** — see (d).

Not an indictment: this is the natural coverage pattern of a project where the easy-to-test parts
got tested. It is the strongest possible argument for Claudette's two-trait seam, which is what
makes the *hard* path testable without a model or a database.

#### (d) `FileLockService` is dead code, and the live lock path ignores ownership

`FileLockService` (`fileLock.ts`, 144 lines) is the careful implementation: it respects ownership,
takes over only expired locks, emits a `file_conflict` alert and returns `null` on a real conflict,
and offers `isFileLocked` / `cleanupExpiredLocks`. **Its only references in the repo are its own
definition and its own test file.** Nothing in production constructs it.

What actually runs is `TaskAssigner`:

- `lockFiles()` (`taskAssigner.ts:164-184`) — a bare `prisma.fileLock.upsert` per path with **no
  ownership check at all**. It overwrites a live lock held by another agent, unconditionally and
  silently.
- `getLockedFiles()` (`:148`) — its own duplicate of the query, not the service's.
- `releaseFileLocks()` (`:189`) — `deleteMany` by `lockedByTask`.

The only guard is a **pre-check in `assignNextTask`** (`:45`, `:68`): read the locked-file list,
then assign. Classic TOCTOU, and it is bypassed entirely on the two routes that call `assignTask`
directly — `routes/queue.ts:111` (manual assign) and `:314`. And **`cleanupExpiredLocks` is never
called from anywhere**, so expired rows are never collected; they are merely filtered out by the
`expiresAt > now()` predicate and sit in the table until the task is deleted (the `FileLock.task`
relation is `onDelete: Cascade`, so that is the actual GC).

One interaction worth carrying: the lock TTL is **30 minutes** (`taskAssigner.ts:165`,
`fileLock.ts:15`) while the watchdog fires at **5**. The watchdog is what keeps the 30-minute TTL
from mattering — which means the TTL is not the safety net it looks like.

#### (e) The watchdog: complete cleanup of an incomplete found-set

**What the map says — "cleanup is complete, which is the part usually done wrong" — is true of what
it finds, and the finding is the part done wrong.** Both halves matter, so both go in the row.

Cleanup, confirmed complete (`stuckTaskRecovery.ts:256-334`): locks released, resource slot
released, task → `aborted` with `errorCategory: 'timeout'`, the open `TaskExecution` row → `failed`
with `completedAt`, agent → `idle` + `currentTaskId: null` + failure stats, WebSocket task and
agent updates, an operator-visible `alert`, and an MCP publish. Eight steps, nothing left dangling.
That is genuinely better than most.

The found-set (`:192-202`):

```
status: 'in_progress',  assignedAt: { lt: timeoutThreshold }
```

- **A task stuck in `assigned` is invisible to it, forever.** It holds the agent (`busy`), the
  resource slot and its file locks until a human presses reset (`forceRecoverAll`, the only path
  that covers `assigned`). This is not inference — the author documents the same class of bug in
  the commit at the pin's HEAD, `taskExecutor.ts:244-249`: *"Nothing polls 'assigned' —
  autoAssignNextTask selects on status 'pending' — so leaving the task assigned held the agent, the
  resource-pool slot and the file locks until a human hit reset, and the retry never actually
  happened."* He fixed the retry path. The watchdog still cannot see the state.
- **`needs_human` is invisible too**, and so is the `stuck` agent status that
  `requestHumanInput` sets (`taskQueue.ts:111-121`). `forceRecoverAll`'s orphan sweep only resets
  agents whose status is `busy` (`:158-160`), so the reset button leaves a `needs_human` task
  holding its locks and slot. Defensible by design — a human *is* the recovery path — but it means
  "reset" does not reset everything.
- **The clock is `assignedAt`, not last progress.** There is no heartbeat: `Task` has
  `assignedAt` / `needsHumanAt` / `completedAt` / `createdAt` / `updatedAt` and no started-at or
  liveness field. So the 5 minutes is *total elapsed since assignment*, and a healthy long task is
  aborted for being slow. The signal it needs already exists — `ExecutionLog.timestamp`, written
  per step — and is not used. **For 2.0 this is the cheap fix: watchdog on
  `max(execution_log.timestamp)`, not on assignment time.** A local 35B doing multi-file work will
  exceed 5 minutes of wall clock routinely.
- Doc drift, minor but worth not inheriting: the module header and the config comment both say
  *"default: 10 minutes"* (`:5`, `:31`); the constant is **5** (`:40`), check interval **30 s**
  (`:41`), both env-overridable.

#### (f) "No crash durability" — precisely which half

The map's blanket phrase is right in effect and imprecise in mechanism. The locks *are* durable.

| State | Where it lives | Survives restart |
|---|---|---|
| Task status, assignment, iteration, error | Postgres `tasks` | ✅ |
| **File locks** | Postgres `file_locks` (`filePath` unique) | ✅ |
| Execution logs, task executions | Postgres | ✅ |
| **Resource-pool slots** | `Map<ResourceType, Set<string>>`, process singleton (`resourcePool.ts:88`) | ❌ |
| Ollama rest counters | module-level `Map`, process-global (`ollamaOptimizer.ts:22`) | ❌ |
| Watchdog recovery history, `lastCheckTime` | in-memory, capped at 100 | ❌ |

**And nothing reconciles at boot.** `index.ts` constructs an empty pool (`:101-102`) and starts the
watchdog (`:214`); no sweep rebuilds slot state from the tasks table. The *one* piece of in-memory
state that is rehydrated at boot is `costAggregator.hydrate()` (`:108`) — which rebuilds from the
three columns nothing writes (see (h)). The state that needs rehydration does not get it; the state
that gets it has no source.

Two restart branches, both worth stating because they are different bugs:

- **One coder agent** (the shipped default): the agent is left `busy` in Postgres. Recovered ≤5 min
  later *if* the task was `in_progress`; **never** if it was `assigned`.
- **Two or more coder agents:** the empty pool admits a second task to the 1-slot `ollama`
  resource while the first is still believed in progress. Over-admission on a single GPU, for up to
  the watchdog interval.

#### (g) The lifecycle has no type

`Task.status` is `String @db.VarChar(20) @default("pending")` — no enum, no check constraint, and
**no status union type anywhere in `packages/api`** (`grep` for `TaskStatus` or any `'pending' | …`
union returns nothing). Counted across `services/` + `routes/`, excluding tests: **143 bare
status-literal comparison and assignment sites** for all entities, of which **at least 48 are
unambiguously `Task`** — a floor, because `'completed'` and `'failed'` are shared with
`TaskExecution` and were excluded from that count. The eleven `Task` states in use: `pending`,
`assigned`, `in_progress`, `completed`, `failed`, `aborted`, `needs_human`, `decomposing`,
`awaiting_approval`, `reviewing`, `approved`.

There is no state machine — only conventions, which is exactly how (e)'s "nothing polls
`assigned`" survived. **This is the concrete first job for Q8's "RTS framing into the Rust domain
model" ruling**: the vocabulary decision and the durability fix are the same piece of work, and a
Rust enum with typed transitions makes the entire class of bug in (e) unrepresentable.

#### (h) `ExecutionLog`: the shape is as good as claimed, and three of its fields were never writable

The map calls it "the best-designed table in the family" and lists
`thought/action/input/observation/timing/**tokens**/isLoop`. Six of those seven are real. The
tokens are not, and this pass found why. Traced in order:

1. **Schema has them.** `input_tokens Int?`, `output_tokens Int?`, `model_used VarChar(50)`.
2. **The producer sends them.** `packages/agents/src/monitoring/execution_logger.py:136-138` puts
   `inputTokens` / `outputTokens` / `modelUsed` in the POST body.
3. **The route accepts them.** `createLogSchema` validates all three
   (`routes/execution-logs.ts:25-27`).
4. **The route forwards them.** `logService.createLog({ ...input, actionInput })` (`:48-51`).
5. **The service drops them.** `CreateExecutionLogInput` (`executionLogService.ts:3-14`) has no
   token fields, and `createLog` writes an **explicit `data` list** (`:24-34`) that omits all
   three. TypeScript cannot catch this: excess-property checking does not apply to **spread**
   properties, only to written ones. The one blind spot in the type system, landed on exactly.

The downstream damage is larger than three null columns, because two consumers are gated on them:

```ts
if (log.inputTokens || log.outputTokens) {   // always false
  budgetService.recordUsage(...)             // :55
  costAggregator.addLog(log);                // :70
  emitCostUpdate(io, costAggregator.snapshot());
}
```

`budgetService.recordUsage` has **exactly one production caller** — that line — and **14 call sites
in its own test file**. It is thoroughly tested and has never once run on real data. Same for
`costAggregator`.

Two more independent drop points confirm there is no way in:

- **`captureTrainingData` drops them twice** (`taskExecutor.ts:637-647`): its log mapping omits the
  three fields, and it passes `tokens: undefined` with the comment *"Could be tracked in future"*.
  So the `TrainingDataset` rows have no token data either.
- **The second write path never sends them.** `packages/mcp-gateway/src/adapters/postgres.py:239-249`
  is a raw `INSERT INTO execution_logs` listing `id, task_id, agent_id, step, action, "actionInput",
  observation, model_used` — `model_used` yes, the two token columns no.

**Net: no write path in the system can populate `input_tokens` or `output_tokens`.**
`data-assets.md`'s "0% populated" was an accurate observation of an unreachable column, not of
neglect.

One detail for whoever ports the shape: the table **mixes naming conventions**. `task_id`,
`duration_ms`, `is_loop`, `input_tokens` are `@map`ped to snake_case; `step`, `timestamp`,
`thought`, `action`, `actionInput`, `observation` are not, so `actionInput` is a camelCase column
in a snake_case table — which is why the raw SQL above has to quote `"actionInput"`.

#### (i) The console consequence: TokenBurnLog has never rendered a real number

`packages/ui/src/components/main-view/TokenBurnLog.tsx` (322 lines) filters the live log store on
the same dead predicate — `.filter((log) => log.inputTokens || log.outputTokens)` (`:93`) — so
`realEntries` is **always empty**. The only way the panel shows anything is `useMockData`, which
generates 25 entries from `Math.random()` and appends another every 8 s (`:63-75`, `:121-134`).

To be fair to the code: mock mode defaults to **off** (`:85`), auto-disables the moment real data
arrives (`:107-111`), and carries the comment *"this is a demo cosmetic, not a polling fallback"*
(`:113-114`). Someone was careful here. The emptiness is entirely upstream in (h).

**So: the layout is proven and the data path never was.** §8's `TokenBurnLog` **PORT** stands on
the design; nothing about its behaviour under real volume has been observed, by anyone, ever.

#### (j) The rest delay runs after the slot is freed

`handleTaskCompletion` releases the resource slot at `taskExecutor.ts:141`, then reaches the rest
delay at `:171` → `updateAgentOnCompletion` → `:408`. So the shared 1-slot `ollama` resource is
**available for the whole 3-8 s "rest"**. The delay protects the agent's turnaround, not the model
context it was built to protect — the Feb 2026 stress-test finding in `ollamaOptimizer.ts:4-7`.
It only bites with two or more coder agents, since `isOllamaTask` requires
`agentTypeName === 'coder'` (`:85`), which is likely why it was never noticed. Constants:
**3 s** normal, **8 s** every **5th** task, per agent.

---

## 4. Where this leaves the map

Corrections applied to `inheritance-map.md` in the same pass:

### 4.1 First pass (morning)

| § | Row | Change |
|---|---|---|
| §0.1 | Forge pipeline | `forge_run.rs` 1,687 → **1,803** lines; `MAX_FIX_ROUNDS` is a *default* with an env override and a hard cap |
| §0 | **new item 9** | The residency reframing is now code-sourced (`hw.rs:103-109`), not dossier-sourced |
| §2 | `ConversationRuntime` | 14.76 s → **3.8 s** for the tests; 14.76 s relabelled as the edit-to-green cycle |
| §2 | Loop breakers | 9 → **12**, line range corrected |
| §3 | `hw.rs` | **Split.** VRAM probe stays REUSE; "temperature" struck; **peak-RAM reporting becomes a REWRITE row** |
| §3 | HTTP client | Live-verified against LM Studio |
| §4 | `ToolRegistry` | Token figures re-measured and confirmed; coding-core cost corrected 2.2k → **~3.0k tokens** |
| §6 | BCF verifier | "Python deep" **struck**; substring-spoofing and the early-`return` bug recorded |
| §6 | `aspirational` preset | **PORT → REWRITE** — it exists in no codebase |
| §6 | `security_review.rs` | Flagged **opt-in / off by default** |
| §11 | `doctor.rs`, `setup.rs` | Counts confirmed; nine probes in the default build |

**Net effect on the verdict counts:** two rows moved out of the "already exists, just carry it"
column into "nobody built this" — peak-RAM/VRAM reporting, and the config-driven gate threshold.
§12's headline ("only five REWRITE rows") is now **seven**, and both additions land in W1/W2 and
W6 respectively. The overall shape — integration project, not research project — still holds.

### 4.2 Second pass (evening) — ABCC's §2 and §7 rows

| § | Row | Change |
|---|---|---|
| §0 | **new item 10** | The token columns are unreachable by every write path in ABCC. The mechanism, and what it kills downstream |
| §2 | Task lifecycle / queue / pool / locks | Citation moved to `taskExecutor.ts` + `taskAssigner.ts` (`taskQueue.ts` is now a facade). Durability split: **locks are durable, slots are not, nothing reconciles at boot**. `status` is an untyped string across 72 sites |
| §2 | **Stuck-task watchdog** | **"Cleanup is complete" reversed in half.** Cleanup of what it finds *is* complete (8 steps); the found-set is `in_progress` only — `assigned` and `needs_human` are invisible — and the clock is `assignedAt`, not last progress. Recovery path untested |
| §2 | Rest delays | Citation corrected `taskQueue.ts` → **`ollamaOptimizer.ts`**; constants recorded; applied *after* the slot is released; unmockable `setTimeout` |
| §2 | `ConversationRuntime` (Claudette) | Strengthened with the other side of the comparison: ABCC is **81 tests / 32.4 s**, ~120× slower per test, because it sleeps for real |
| §3 | `resourcePool.ts` | Four resource types including **`grok`**; env-gated pools; C10→claude / C7-9→remote confirmed a second time; in-memory semaphore, no waiters, no durability |
| §5 | `budgetService.ts` | **Never called in production.** Its one live call site is gated on the dead token fields; 14 of its 15 call sites are its own tests |
| §7 | `ExecutionLog` | Shape confirmed good on six of seven fields; **"tokens" struck** — three independent drop points, no write path can populate them. Column-naming inconsistency flagged for the port |
| §7 | `FileLock` | `FileLockService` is **dead code**; the live path is an ownership-blind `upsert` reachable from `routes/queue.ts:111`; `cleanupExpiredLocks` never called; 30-min TTL vs 5-min watchdog |
| §8 | ToolLog / **TokenBurnLog** / CodeWindow | TokenBurnLog's real-data path is structurally empty; its only non-empty state is an opt-in `Math.random()` demo. Layout proven, behaviour never observed |
| §13 | Confidence | The "still Medium, first thing to verify next" paragraph is now resolved |

**Net effect on the verdict counts: none. No row moved.** All six targeted rows stay PORT or
REFERENCE, and the counts in §12 are unchanged. What changed is six *reasons* — and one of them,
"cleanup is complete", was half wrong in the direction that matters, because it was the sentence
telling 2.0 it could carry the watchdog design across as-is.

**The pattern across both passes.** The first pass found things recorded as existing that do not
exist. The second found things that exist, are well built, and **are not connected to anything** —
a lock service nothing constructs, a budget service nothing calls, three columns nothing writes, a
console panel with no reachable data. Neither failure mode is visible from reading a file; both are
visible from tracing a path or running the thing. Same lesson as
`verify-claims-against-code-not-docs`, one level up: **a component being good is not evidence that
it ran.**
