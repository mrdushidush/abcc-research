# battle-command-forge - Repo Dossier

**Repo:** `D:\dev\battle-command-forge` (public, **Apache-2.0**, `github.com/mrdushidush/battle-command-forge`, published on crates.io as `battlecommand-forge`)
**Pinned at:** `d6c1601`, 2026-04-30, branch `main`, **7 commits**, version **0.2.0**, tags `v0.1.0` / `v0.2.0`
**Read method:** static read plus `cargo test`, which was run. **96 passed, 2 failed, 0.45 s.** No model was loaded and no mission was run.
**Author of this dossier:** Claude Code, Phase 0
**Scope note:** deliberately lighter than the Claudette dossier. Per David, BCF was a greenfield POC that generated nice-looking landing pages and never became a daily driver. It is judged here as a source of *mechanisms*, not as a product.

---

## 0. One-paragraph summary

BCF is a 16k-line single-crate Rust binary that takes one prompt and emits a whole tested
project, by pushing it through nine named stages ending at a numeric quality gate. It is the only
one of the three repos that treats "is this good enough to ship" as an arithmetic question with a
threshold, and its answer to that question - weight the deterministic verifier at 60 percent and
the LLM critique at 40 percent, and scale the threshold *down* as complexity rises - is the best
single idea in the repo and the thing 2.0 should take. It also contains a working Rust port of
ABCC's dual complexity assessment that fixes a data problem ABCC still has. Structurally it is
33 flat modules in one `src/` with no crate boundaries, its git history is a squashed snapshot,
and its fun layer is macOS-only and therefore dead on the target machine.

---

## 1. Module map

**No workspace, no crates.** One package, `src/` flat, 33 files, **15,992 lines**.

| Module | Lines | Owns |
|---|---:|---|
| `mission.rs` | 2,262 | **the pipeline driver.** All nine stages, the fix loop, the gate |
| `tui.rs` | 1,803 | Ratatui TUI |
| `llm.rs` | 1,213 | provider client |
| `swebench.rs` + `_tools` + `_eval` | 1,732 | SWE-bench harness (prototyped, never run) |
| `main.rs` | 940 | CLI |
| `verifier.rs` | 800 | **quality scoring**: lint, tests, secrets, TODOs |
| `cto.rs` | 778 | stage 8, mission coherence |
| `report.rs` | 595 | run reports to `.battlecommand/reports/` |
| `sandbox.rs` | 526 | **sandboxed subprocess execution** |
| `model_config.rs` | 525 | per-role model assignment, presets |
| `router.rs` | 439 | **stage 1, Campbell dual complexity** |
| `space.rs` / `snake.rs` | 706 | in-TUI minigames |
| `model_picker.rs` | 407 | interactive model selection |
| `memory.rs` | 380 | run memory |
| `hardware.rs` | 306 | hardware detection |
| `codegen.rs` | 398 | multi-file extraction from model output |
| `swarm.rs` | 297 | parallel work |
| `editor.rs` | 282 | project context reading |
| `enterprise.rs` | 176 | paid-tier scaffolding |
| `secrets.rs` / `github.rs` / `db.rs` / `context.rs` / `benchmark.rs` / `stress.rs` / `voice.rs` / `workspace.rs` / `custom_commands.rs` / `snake`-adjacent | ~1,100 | supporting |

The brief expects to inherit "the Rust project structure and module boundaries". There are no
module boundaries to inherit: it is a flat file list in one crate with no visibility discipline.
The *pipeline* is worth taking. The *structure* is not.

---

## 2. The nine stages

Confirmed from `README.md` and from `mission.rs`.

| # | Stage | What it does | Model in `premium` preset |
|---|---|---|---|
| 1 | **Router** | Scores complexity C1-C10, rules plus AI | `qwen3.5:4b-q8_0` (always, all presets) |
| 2 | **Architect** | ADR, file manifest, TDD test plan | `qwen2.5-coder:32b` local |
| 3 | **Tester** | Writes the complete test suite **before** any code | `claude-opus-4-6` cloud |
| 4 | **Coder** | Generates every file in a single shot | `qwen3-coder-next:q8_0` local, 64k ctx |
| 5 | **Verifier** | venv, pip install, lint, run tests. **No model.** | - |
| 6 | **Security** | OWASP Top 10 review | local or Sonnet |
| 7 | **Critique** | 5-in-1 scoring: DEV / ARCH / TEST / SEC / DOCS | local or Sonnet |
| 8 | **CTO** | Mission-level coherence, ship or no-ship | Sonnet |
| 9 | **Gate** | Arithmetic. Ship or enter the fix loop. **No model.** | - |

Note that stages 5 and 9 - the two that actually decide anything - involve no model at all.

**Presets** (`model_config.rs`): `fast` (everything on `qwen2.5-coder:7b`), `balanced` (32b for
architect/tester/coder/fix_coder, 7b for the review roles), `premium` (Opus writes the tests,
Sonnet does the surgical fixes, local models do the bulk coding). Eight named roles:
`architect, tester, coder, fix_coder, security, critique, cto, complexity`.

The router model is a dedicated small model in every preset. That is the "small fast model for
triage" W1 goes looking for, already chosen and in production use.

---

## 3. The quality gate - the most reusable thing in the repo

### 3.1 The formula

`mission.rs:1139`, with its own comment:

```rust
// Calculate final score: critique 40% + verifier 60%
// Verifier (tests + linting) is the real quality signal — weight it higher
let final_score = critique_avg * 0.4 + verifier_score * 0.6;
```

`verifier_score` comes from `verifier.rs` and is fully deterministic: lint results, test
pass/fail counts, secret scanning, TODO detection. `critique_avg` is the mean of five LLM scores.

**This is a direct, working answer to W6's LLM-as-judge problem.** The judge is not removed, it is
*outvoted*. A model that loves its own output cannot push a project through the gate if the tests
fail, because the deterministic component carries 60 percent of the weight. Claudette solves the
same problem by having no judge at all and writing an objective verifier per task, which works
for a fixed benchmark. BCF's answer is the one that generalizes to arbitrary user tasks, and 2.0
needs that one.

### 3.2 The thresholds are inverted, deliberately

`mission.rs:61`:

```rust
fn quality_gate(complexity: u32) -> f32 {
    match complexity {
        0..=6 => 9.2,   // simple tasks should be near-perfect
        7..=8 => 8.5,   // complex but achievable with fix rounds
        _     => 8.0,   // very complex — reward functional code
    }
}
```

The bar *drops* as tasks get harder. The reasoning in the README is that a trivial task producing
a 8.5 is a bad sign, while a C9 project that merely works is a win. This is a genuine insight and
it is the opposite of what most quality systems do. It also means the gate is not comparable
across complexity bands, which is a caveat worth carrying: a 9.4 at C3 and an 8.1 at C9 are both
passes and are not the same thing.

### 3.3 The surgical fix loop

`MAX_FIX_ROUNDS = 5` (`mission.rs:52`), backed by a compile-time
`const _: () = assert!(MAX_FIX_ROUNDS >= 1)`.

On gate failure the pipeline does not regenerate. Per the README and the code:

1. **Traces imports** - `identify_broken_files(feedback, files)` (`mission.rs:2031`) parses test
   and lint output, and `extract_failed_module` pulls the module name out of an error line, to
   work out exactly which files are broken.
2. **Fixes surgically** - each broken file gets its own LLM call with its own error context.
3. **Preserves clean code** - files that passed are untouched.
4. **Detects decline** - if the score falls two rounds in a row it restores the best round's
   files. `best_score` / `last_best_score` track this.
5. **Bounds scope** - fix rounds fix bugs only, never add features, to prevent regression.

Claudette's `run/forge_run.rs` carries the same `best_round` idea with
`DEFAULT_MAX_FIX_ROUNDS = 3`, and explicitly refuses to restore a high-scoring round that the
security stage rejected. So this mechanism has already survived one port and been improved in
transit.

---

## 4. Router: ABCC's complexity model, in Rust, with the bug fixed

`router.rs:1`:

```rust
/// Campbell's Complexity Theory — Dual Assessment Router.
/// 1. Fast rule-based scoring
/// 2. AI-assisted scoring via configured complexity model (nuanced)
```

The types:

```rust
pub enum ComplexitySource { Rules, Ai, Dual }

pub struct RoutingResult {
    pub complexity: u32,
    pub source: ComplexitySource,
    pub rule_score: f32,
    pub ai_score: Option<f32>,
    pub reasoning: String,
}
```

`Tier::from_score` bands at 9.0, 7.0 and 4.0. `assess_complexity(prompt)` is the rules-only fast
path; `assess_complexity_dual(prompt, llm)` runs both and reconciles.

Two things matter here.

**First, this is a faithful port of ABCC's design.** `ComplexitySource::{Rules, Ai, Dual}` is
exactly ABCC's `complexitySource: 'router' | 'haiku' | 'dual'`. The brief wonders whether the
complexity model survives into 2.0. It has already survived one migration into Rust, and a second
into Claudette's `Planner` role. It is the most-travelled idea in the family.

**Second, it structurally fixes the problem ABCC created.** ABCC's
`20260201_simplify_complexity_model` migration collapsed `routerComplexity` and
`haikuComplexity` into a single `complexity` column plus a prose `complexity_reasoning` string,
which is why W4's retrospective comparison now needs a text parse. BCF's `RoutingResult` keeps
`rule_score: f32` and `ai_score: Option<f32>` as separate typed fields alongside the final score.

That is the concrete demonstration of the brief's claim that "Rust's type system should make
these contracts enforceable rather than hopeful". It already happened, in this file, to this
exact data.

---

## 5. Verifier and sandbox

### 5.1 The verifier is not Python-only

The brief says BCF has "Python-only code output". That is wrong.

`verifier.rs` runs **project tests** for four language families:

| Language | Line | How |
|---|---:|---|
| Python | 147 | creates a venv, pip installs, runs pytest; extracts deps from `pyproject.toml`; recovers from missing-module errors |
| Rust | 431 | cargo |
| Go | 468 | `sandbox::run_tool_sandboxed("go", ["test", "./...", "-count=1"], 120s)`, guarded by `tool_exists("go")` |
| TypeScript / JavaScript | 490 | node toolchain |

And **static checks** for python, javascript, typescript, rust, go and a `verify_generic`
fallback, dispatched on file extension (`py`, `ts`, `tsx`, `js`, `jsx`, `rs`, `go`).

Plus two language-independent checks that are worth stealing outright: `check_secrets` scans
generated code for credentials, and `check_todos` flags TODO markers, both feeding the score.

Python is genuinely the deepest path - it is the only one with environment construction and
dependency recovery. So the accurate statement for W6 is: **the scoring model and the static
checks generalize; the environment-construction step is Python-deep and everything else is
shallow.** That is a much better starting position than "Python only" implies.

### 5.2 The sandbox

`sandbox.rs`, 526 lines. Three mechanisms:

1. **Environment allowlist.** Subprocesses receive only names on `ALLOWED_ENV_NAMES` (PATH, HOME,
   USER, SHELL, LANG, TZ, TERM, TMPDIR, the venv vars, and the Windows essentials). The header
   explains the change of approach:

   > The previous substring blocklist missed several real leak surfaces (`OLLAMA_HOST`,
   > `DATABASE_URL`, `KUBECONFIG`, `AWS_ACCESS_KEY_ID`, `SSH_AUTH_SOCK`, ...); allowlist
   > semantics close the class.

   This is exactly the finding W7 needs about secrets and traces, arrived at the hard way.

2. **Path validation.** `validate_path_within(root, rel)` rejects `../etc/passwd`,
   `app/../../etc/shadow`, absolute paths, `\windows\system32`, and embedded NUL. A regression
   test records that an earlier validator rejected `..` as a bare substring and false-positived
   on legitimate filenames.

3. **Timeouts.** `DEFAULT_TIMEOUT_SECS = 30`, with per-call overrides.

Compared with ABCC (a `startswith` prefix check and a per-language string denylist), this is a
serious improvement and the best security work in the three repos.

---

## 6. Test results, and one that passes for the wrong reason

`cargo test` on `rustc 1.95.0`, matching the declared MSRV:

```
test result: FAILED. 96 passed; 2 failed; 0 ignored; finished in 0.45s
```

Both failures are in `sandbox::tests` and both are Unix assumptions running on Windows:

- `test_tool_exists` asserts `tool_exists("ls")`, above the comment "These should exist on any
  unix system".
- `test_timeout_kills_process` runs `run_tool_with_timeout("sleep", ["30"], "/tmp", 2)` and
  asserts `timed_out`. There is no `sleep` binary on Windows, so the spawn fails and the process
  never times out because it never started.

Neither is a product defect. The README's "86/86 unit tests" is now 98 tests, and the suite does
not pass clean on the machine it was written on.

**But there is a third test worth flagging.** `test_env_var_stripping` (`sandbox.rs:472`) sets
`TEST_API_KEY=secret123`, runs `run_tool("env", ...)`, and asserts
`!result.stdout.contains("secret123")`. It **passed**. `env` is also a Unix binary that does not
exist on Windows, and the assertion is a negative over that command's stdout. A test that only
asserts the absence of a string in output from a binary that is not present cannot be evidence
that stripping works, whatever the mechanism. So on the platform BCF was developed on, the one
test guarding the "API keys do not leak into model-driven subprocesses" property provides no
assurance. The allowlist code itself looks correct on reading; it is the *evidence* that is
missing, and that distinction matters for a W7 threat model.

---

## 7. What is broken, half-finished, or superseded

1. **The git history is gone.** Seven commits on `main`, tagged v0.1.0 and v0.2.0, with real work
   ending 2026-04-30 and the later push being dependabot. David confirms it is a snapshot. There
   is no development history to mine, so "how did this evolve" questions cannot be answered from
   this repo.
2. **Decomposition was tried and abandoned.** `mission.rs:361`:
   > Run as single task - multi-file extraction handles project structure. Decomposition caused
   > duplicate projects; single-task plus good prompts is better.

   This is a significant negative result and it is directly relevant to the brief's Architecture
   stage, which assumes decomposition into a task DAG. See section 9.
3. **SWE-bench is a prototype that never ran.** 1,732 lines across three modules. David confirms
   it was never executed and is out of scope.
4. **The voice layer is macOS-only.** `voice.rs`: "Voice TTS announcements using macOS `say`
   command." It cannot run on the target Windows box. BCF's fun layer is dead on this hardware.
5. **`enterprise.rs`** is scaffolding for a paid tier that the 2.0 project has ruled out.
6. **Persistence is JSON files** in `.battlecommand/missions/`, with the comment "Can be upgraded
   to PostgreSQL later (Phase 12 evolution)". There is no Phase 12.
7. **`swarm.rs`** (297 lines) exists but the pipeline runs a single task. Parallelism is
   aspirational here.
8. **`BMORE.md`** is a full product specification for an unrelated commercial SaaS platform
   (product data management for SMB computing retailers, with revenue targets and business
   goals). It is excluded from the published crate tarball but it **is in the public GitHub
   repo**. If it is a demo mission input, fine. If it is a real client or business document, it
   is public and probably should not be. Flagging it rather than assuming. See open questions.

---

## 8. Corrections to brief section 3.3

The brief marks this section "low confidence". It holds up better than expected.

| # | Brief says | Reality |
|---|---|---|
| 1 | "Believed to implement a 9-stage TDD pipeline with complexity-scaled quality gates" | **Correct on both counts.** Nine named stages, thresholds scaled by complexity band. |
| 2 | "roughly along the lines of architect, TDD, code, verify, security, critique, quality gate" | Seven of nine. Missing **Router** (stage 1) and **CTO** (stage 8). |
| 3 | "to have reached a shippable state with a real test suite" | Shipped: crates.io, v0.2.0, ~3.7 MB binary, CI. Test suite is real (98 tests) but **2 fail on Windows** and one passes vacuously. |
| 4 | "and Python-only code output" | **Wrong.** Project tests run for Python, Rust, Go and TS/JS; static checks cover six categories. Python is the deepest path, not the only one. |
| 5 | "2.0 probably inherits the Rust project structure and module boundaries" | **Nothing to inherit.** 33 flat modules, one crate, no workspace, no visibility discipline. Take the pipeline, not the structure. |
| 6 | "the quality gate scoring mechanism" | Confirmed and it is the best thing here. `critique*0.4 + verifier*0.6`, thresholds 9.2 / 8.5 / 8.0. |
| 7 | (not mentioned) | **Uses tokio.** Claudette has no async runtime at all. The two donors disagree on this, and W3 has to pick. |
| 8 | (not mentioned) | Contains a working Rust port of ABCC's Campbell dual complexity assessment that keeps both sub-scores as typed fields. |
| 9 | (not mentioned) | Has its own Ratatui TUI, a sandbox, a model-per-role config with three presets, hardware detection, and two in-TUI minigames. |
| 10 | (not mentioned) | Backend is **Ollama**, not LM Studio. The README's quick start is `ollama serve` plus `ollama pull qwen2.5-coder:7b`. |
| 11 | W12: "whether any inherited BCF code has different terms" | **Apache-2.0**, against ABCC's MIT and Claudette's MIT-OR-Apache dual. David confirms sole authorship and no outside contributors, so relicensing is his call to make and is not blocked. |

---

## 9. Observations logged for Phase 1

Inputs, not proposals.

1. **The gate formula is the single most portable artifact in the three repos.** Weighting a
   deterministic verifier above an LLM critique is a general answer to judge unreliability that
   works on arbitrary tasks, which is what 2.0 needs and what Q56's per-task verifiers cannot
   provide outside a fixed benchmark.
2. **Inverted thresholds deserve a decision, not an inheritance.** They encode a real insight and
   they make scores incomparable across complexity bands. W6 and W11 should decide explicitly
   whether 2.0 wants one comparable scale or one calibrated bar.
3. **Decomposition has a recorded negative result.** BCF tried it, got duplicate projects, and
   reverted to single-task plus multi-file extraction. The brief's Architecture stage assumes a
   task DAG is the right shape. That assumption now has evidence against it from a sibling
   project - at greenfield scale with a 7b-to-32b model, which is a materially different regime
   from repo work with a 35B-A3B. Worth testing rather than assuming in either direction.
4. **Three of the family's four complexity implementations agree.** ABCC (TypeScript), BCF (Rust)
   and Claudette's `Planner` role all carry Campbell dual assessment. The disagreement is only in
   how the two sub-scores are reconciled and whether they are retained.
5. **The two donors disagree on async.** BCF is tokio; Claudette is blocking `reqwest` with no
   runtime. 2.0 wants parallel builders, a live console and a fleet protocol. W3 should cost this
   explicitly rather than inheriting by accident from whichever file gets ported first.
6. **A dedicated tiny router model is already the pattern.** `qwen3.5:4b-q8_0` scores complexity
   in every preset, including the one where Opus writes the tests. W1's "small fast model for
   triage" question has a working incumbent.
7. **`check_secrets` and `check_todos` in the verifier are cheap and general.** Scanning generated
   code for credentials before it is scored is a control 2.0 wants regardless of language, and it
   connects directly to W7's secrets-in-traces concern.
8. **The minigames are the wrong answer to the right question.** `snake.rs` and `space.rs` exist
   so the operator has something to do while the pipeline runs. That is BCF noticing the dead-air
   problem from section 7 of the brief. The 2.0 answer is to make the *work* watchable, not to
   supply a distraction from it, but the instinct was correct and is worth recording.

---

## 10. Open questions raised by this repo

For `prestudy/questions.md` and for David directly:

1. **`BMORE.md`** - is it a demo mission input, or a real business specification? It is in the
   public repo. If the latter, it should probably come out.
2. **Apache-2.0 to MIT.** Sole authorship confirmed, so relicensing is available. Does 2.0 go MIT
   like ABCC, MIT-OR-Apache like Claudette, or keep Apache-2.0 for anything derived from BCF?
3. **`enterprise.rs`** - 2.0 is a community project with no enterprise tier. Confirming this is
   drop-not-port.
4. Do the two Windows test failures matter enough to fix in the donor, or does BCF stay frozen
   and only its ideas travel?

---

## 11. Dependencies

```
clap 4.5 · tokio 1 (rt-multi-thread, macros, sync, process, fs, time — narrowed from "full")
anyhow 1.0 · tracing 0.1 + tracing-subscriber 0.3
reqwest 0.12 (json, stream, rustls-tls — no openssl)
serde 1.0 · serde_json 1.0 · chrono 0.4 · toml 0.8 · dotenvy 0.15
ratatui 0.29 · crossterm 0.28 · futures-util 0.3 · shell-words 1
```

MSRV 1.95, edition 2021. Release profile matches Claudette's (`opt-level = "z"`, LTO, strip,
`panic = "abort"`) plus `codegen-units = 1`. Binary is about 3.7 MB.

`ratatui 0.29` / `crossterm 0.28` are one major behind Claudette's `0.30` / `0.29`. Nothing here
is unmaintained; the tree is just four months colder.

---

## 12. Size and test coverage

| Metric | Value |
|---|---|
| Source | 33 files, 15,992 lines, one flat crate |
| Tests | 98 total: **96 passed, 2 failed**, 0.45 s |
| Version | 0.2.0, tags v0.1.0 and v0.2.0 |
| Commits | 7 (squashed snapshot, history lost) |
| Binary | ~3.7 MB |

---

## 13. Confidence

**High** on the pipeline, the gate arithmetic, the thresholds, the fix loop, the router types,
the verifier's language coverage, the sandbox mechanisms, dependencies and test results. All read
from source at a pinned commit, and the suite was executed here.

**High** on the two test failures being environmental rather than product defects, since both
name Unix binaries explicitly.

**Medium** on the vacuous-pass reasoning for `test_env_var_stripping`. The conclusion that the
test cannot evidence stripping on Windows is sound from the assertion's shape alone, but I did
not read `run_tool`'s spawn-failure path to confirm the exact mechanism.

**Not attempted:** no mission was run, no model was loaded, no generated project was inspected,
and the claimed 10-mission stress suite was not reproduced. So this dossier describes what the
pipeline *is*, not how well it works. Given BCF's status as a superseded POC, I did not think
that was worth the hardware time - say if you disagree.
