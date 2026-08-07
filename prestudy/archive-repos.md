# Archive Repos — `independencev1` and StealthForge

**Why this document exists.** David pointed at two repos in
`D:\dev\_archive\abcc_projects\abcc_projects\` and asked whether they hold ideas worth carrying
into ABCC 2.0 before Phase 0 closes. They do. One of them settles what the inheritance map calls
the sharpest remaining problem in the design.

**Scope.** This is not a full dossier in the shape of §4.1 — these are not source repos of 2.0 and
they were not in the brief. It is an assessment against the four things ABCC 2.0 has not yet
decided, plus a custody warning. Read `data-assets.md` §6 for the numbers.

**Read at:** working trees as they sit on disk, 2026-08-07. Neither has recoverable git history
(§1.2).

---

## 1. What they are

| | `independencev1` | `stealthsambaV2` |
|---|---|---|
| Real name | independencev1 v1.0.0 | **StealthForge V1.2.2** (crate name `stealthforge`) |
| One line | "Standalone Rust code reviewer — static analysis + LLM critique panel" | "10-Stage Super Pipeline. Independent Review & Spec Fidelity Enforcement." |
| Rust LOC | 6,174 | 10,889 |
| On disk | 1.4 MB | 24 MB (incl. 64 generated missions + 5.3 MB vector store) |
| Last activity | 2026-04-12 20:04 UTC | 2026-04-19 16:00 UTC |
| Async | tokio, full features | tokio, full features |
| Models | Ollama local + optional cloud (Gemini/Grok/OpenAI) | Grok (xAI) primary, Ollama for memory embeddings |
| Declared licence | none in-tree | `MIT OR Apache-2.0` in `Cargo.toml`, no LICENSE file |

The confusing part, stated plainly: **the directory is named `stealthsambaV2` but the code inside
is StealthForge**, the merged successor to StealthSamba V2 *and* BattleCommand Forge. Its own
`BENCHMARK.md` compares all three by name.

### 1.1 Where they sit in the family

Dates, all verified from commits or in-repo records:

| | |
|---|---|
| ABCC v1 active | Jan–Feb 2026 |
| `battleclaw-forge-CLAUDE.md` in the archive root | 2026-03-16 |
| StealthForge V1.1 benchmark + CTO sign-off | **2026-04-06** |
| independencev1 calibration batch 2 / "7.0 floor" found | **2026-04-12** |
| StealthForge v1.2.1 — Stage 8 independence review lands | **2026-04-18** |
| **Claudette, first commit** | **2026-04-18** |
| StealthForge v1.2.2 — veto threshold tuned 2.0 → 4.0 | 2026-04-19 |
| **battle-command-forge, first public commit** | **2026-04-23**, message: *"v0.1.0 — initial public release (port of internal pipeline work)"* |

This reorders the lineage the brief assumes. The public `battle-command-forge` repo is not an
early greenfield POC that predates the serious work — it is a **public port of internal pipeline
work**, published five days *after* Claudette started and four days after StealthForge's last
commit. The internal "BattleCommand Forge (Dream Team)" that StealthForge's benchmark table
measures at 11% gate pass is an earlier, different thing.

None of this contradicts David's own framing (BCF was "something along the way", never a daily
driver). It does mean **the pipeline lessons the brief attributes to BCF were mostly learned in
StealthForge**, and StealthForge wrote them down with numbers attached.

### 1.2 ⚠ Custody — these are history-less copies

Both `.git` directories are **missing `objects/`**. The working trees are intact; the history is
not. `git log` fails in both. Only `logs/HEAD`, `config`, `index` and `COMMIT_EDITMSG` survive,
which is how the dates above were recovered.

Both `config` files point at a **different GitHub account from the rest of the family**:

- `github.com/agentbattlecommand-ops/independencev1`
- `github.com/agentbattlecommand-ops/stealthsambaV2`

versus `mrdushidush/` for ABCC, Claudette and BCF. Commits are authored
`agentbattlecommand-ops <agentbattlecommand@gmail.com>`; `stealthsambaV2/Cargo.toml` names
`Hadar Raz <hadar@agentbattlecommand-ops>`.

**Two things follow, one technical and one for David.**

1. If those GitHub repos are gone or inaccessible, the history of both is unrecoverable. The
   working trees on this one archive path are all that is left. They should be pushed somewhere
   before anything else happens to them.
2. `questions.md` §2 item 2 records "sole authorship is confirmed, so relicensing is available."
   That was established for ABCC, Claudette and BCF. It has **not** been established for these
   two, which carry a second account name and a second person's name in `Cargo.toml`. If any code
   or design from them is carried into 2.0, that needs an answer first. *(New question — added to
   `questions.md` §2.)*

---

## 2. The finding that matters

**StealthForge measured its own quality gate against an independent reviewer and found it
systematically, one-directionally inflated.**

Stage 8 (`src/core/independence.rs`, feature-gated `independence`) shells out to the
`independencev1` binary as a **separate process, with a different model, a different scoring
method and a different methodology**, runs it over the generated project, and computes:

```rust
critic_inflation: internal_avg_score - overall_score
```

Then the orchestrator vetoes (`src/core/orchestrator.rs:876`):

```rust
// Veto logic: if independence FAILS and inflation > 4.0 points, override the internal PASS.
// Hotfix #15: raised from 2.0 → 4.0 based on v1.2.1 regression data showing +3.40 mean
// inflation across ALL missions (including genuine PASSes at +2.6 avg).
// At 2.0 the veto would false-trigger on borderline-good code.
if state.gate_passed && !verdict.passed && verdict.critic_inflation > 4.0 {
    state.gate_passed = false;
    state.independence_vetoed = true;
}
```

Across the **34 missions on disk that carry both scores** (computed independently for this
document, see `data-assets.md` §6):

- median inflation **+3.65**, mean **+5.63**, range +1.08 to +9.84
- inflation > 2.0 on **32 of 34**
- **the independent reviewer scored higher on 0 of 34**

And on the curated M1–M13 regression, the self-scored gate passed **13/13 at mean 9.5/10** while
the independent reviewer graded the same artifacts C+, C−, D and F. M11 scored **9.8 from its own
critics and F (3.3) from the reviewer** — its tests did not compile.

### 2.1 Why the gate missed it

`BENCHMARK.md`'s own post-mortem is more useful than the scores:

> These are **not code generation failures** — they are **verification gaps**.

Four missions passed a gate they should have failed, for two mechanical reasons:

- **`cargo check` without `--all-targets`** checks lib and bin only, not tests. Three missions
  (M7, M11, M12) shipped test files that did not compile against their own library API and were
  scored 9.5–9.8.
- **The pipeline checked the root `Cargo.toml`**, which was an empty workspace, while the code
  lived in `backend/` with 20 compile errors. M13: gate 9.3 PASS, actual compile FAIL.

Security findings — 36 on M3, 32 on M4, 71 on M11 — were **advisory only** and never reached the
gate at all.

### 2.2 What this settles

`inheritance-map.md` §12 lists five genuinely open pieces. Number four:

> **Gate independence in single-player.** ABCC dodged it with different providers, Q56 dodged it
> with hand-written verifiers, BCF's formula reduces but does not remove it. Still the sharpest
> problem in the design.

It is not open any more, at least not in the "does this actually matter" sense. It matters by
about **+3.7 points on a 10-point scale**, in one direction, on 34 out of 34 samples, measured by
the same author on the same class of workload. BCF's threshold formula reduces the bias; the
residual is larger than the gaps the formula is discriminating between.

It also makes the family's trajectory legible. StealthForge measured its gate as inflated in
April; Claudette's Q56, built in July, has **no LLM judge anywhere** and grades only what the model
did to the code. That was not a stylistic preference. It was a conclusion someone reached by
measuring, and it is the single most important inherited decision in the prestudy.

---

## 3. What is worth integrating

Ranked by value, with verdicts in the inheritance-map vocabulary. Rows for these are appended to
`inheritance-map.md` §11.

### 3.1 The independence check as a design pattern — **PORT**

Not the binary. The shape: **a second reviewer, in a separate process, with a different model and
a different method, whose disagreement with the primary gate is itself a recorded metric.**

Why it fits ABCC 2.0 specifically:

- It is the only mechanism in the family that gets gate independence in **single player**, which
  §17 Q6 made the primary mode. It costs a second model pass, not a second machine.
- `critic_inflation` is a **measurable operator-facing number**, which is exactly what W5 and W8
  need and what "fun as a log rather than a vibe" is short of. A console that shows the gate score
  and the independent score side by side, with the delta, tells the operator something no single
  number can.
- The failure mode is already known and priced. The threshold was tuned 2.0 → 4.0 *from regression
  data*, because at 2.0 it false-vetoed good code. 2.0 inherits a calibrated starting point rather
  than a guess.
- Stage 8 is **non-fatal by construction** — errors are logged and swallowed, never crash the
  pipeline. Correct posture for an optional second opinion.

Caveat, and it is real: the reviewer is itself partly an LLM. This reduces correlated failure, it
does not eliminate it. In 2.0 the honest version pairs it with deterministic verification, which
is what §3.2 is for.

### 3.2 Static analysis as a hard clamp on LLM scores — **PORT**

`independencev1/src/critics/scoring.rs:443`, `clamp_score_by_static`. The stated principle:
**static analysis is ground truth; the LLM may only score within bounds it sets.**

Measured rules in the shipped version:

| Condition | Ceiling |
|---|---|
| Code does not compile | Correctness ≤ **4.0** |
| Compiles but tests fail | Correctness clamped into **5.0–7.0** |
| Zero tests | Test Quality ≤ **3.0** |
| Clippy lints | −0.15 each, capped at −3.0 |

And for the cloud phase: **cloud can only lower, never raise.** The system trusts local
deterministic analysis more than a remote opinion.

This is the reconciliation `questions.md` §3.2 item 9 is looking for. It frames
"verifier-as-JSON versus verifier-as-code" as a false choice: the deterministic verifier sets the
ceiling, the LLM ranks underneath it. Both coexist, with a defined precedence.

It also survived contact with its own failure. The repo documents the **7.0 floor**: the LLM
defaults to 7.0 when uncertain — Test Quality scored exactly 7.0 on 8 of 10 calibration projects,
Correctness on 6 of 10 — so the panel *does not meaningfully differentiate in the middle of the
range*. The recorded fix is to make the clamp proportional rather than banded, e.g. Correctness
ceiling `min(7.0, 10.0 × (M−N)/M)` for N of M failing tests. **That is a bug report with a patch,
handed to W6 for free.**

### 3.3 The verification-gap checklist — **REFERENCE**, and act on it immediately

Four cheap rules, each bought with a false PASS:

1. Compile-check with **`--all-targets`**. Tests that do not compile are a failure.
2. **Detect subdirectory manifests.** Do not trust a root workspace file to represent the project.
3. **Route security findings into the gate**, not into an advisory paragraph. 71 medium findings
   scored 9.8.
4. **A gate that reads only its own critics reads its own opinion.** Bind at least one dimension
   to something that executes.

These belong in W6's design as constraints, not discoveries.

### 3.4 The legacy-review path — **REFERENCE**, and it is the family's only one

§17 Q2 answered the target workload as "repository work plus **legacy review** plus
general-purpose coding". StealthForge is the only member of the family with a real legacy mode:
`--path <DIR>` runs `src/analysis/codebase_analyzer.rs` over an existing project and folds the
result into a refined mission before planning. M11 in the benchmark is a legacy mission —
"Add real-time WebSocket task updates" against `./legacy/rust-rest-actix`.

The implementation is thin (204 lines) and M11 is also the benchmark's **worst** divergence, which
is itself the finding: **the legacy mission is where the gate failed hardest.** W8 should treat
repo-work tasks as the place quality measurement is least trustworthy, not most.

### 3.5 The mechanical-failure guards — **REFERENCE**

`src/core/dedup.rs` is 1,646 lines of post-generation repair: merge duplicate `foo_1.rs` /
`foo_2.rs` variants, guarantee `pub mod` declarations exist for every file in `src/`, fix
dependencies, guard derives, warn on missing test infrastructure. The CTO note credits it with
eliminating "almost all mechanical failures".

`src/core/surgical_fixer.rs` sends **only the failing files plus the exact errors** back to the
model and replaces just those files — "~10x faster than full regeneration (1 file vs 10+ files
per round)".

Both are worth reading before W11 designs its fix loop, and both are the kind of thing that looks
like scaffolding and turns out to be most of the pass rate. Claudette's `apply_diff` occupies
similar ground more precisely; the *categories* of mechanical failure are the transferable part.

Relevant cross-check: Q56's tier-2 axis 2 ("agent mechanics") independently found the same class
of failure dominating — four models lost tasks to unparseable output, unterminated strings, and
reaching for unvendored crates, not to bad reasoning.

### 3.6 The RAG + knowledge-graph memory layer — **REFERENCE, do not port**

`src/memory/` is 2,500+ lines: LanceDB vector store (`rag.rs`, 986 lines, Ollama embeddings),
petgraph mission graph with `Mission / Pattern / AntiPattern / Technology` node types
(`graph.rs`, 526 lines), plus conversation and decision memory. On disk: 5.3 MB of vectors,
108 KB of graph, 10 distilled `high_quality_examples`.

It is the only long-term learning system anywhere in the family, and it is genuinely interesting —
the Distiller stage extracts patterns from completed missions and feeds them back.

It is also **unfinished and unmeasured**. The `rag` feature is off by default. The independence
feedback hook is a `TODO(Phase 2.3+)` that prints a line instead of ingesting. No benchmark
isolates its contribution. Nothing in `BENCHMARK.md` or the CTO sign-off attributes any of the
100% gate pass rate to memory.

Verdict: record the design, do not carry the code. If 2.0 wants long-term learning it should be a
deliberate W-item with a measurement attached, not an inherited 2,500-line dependency on LanceDB
and Arrow that nobody has shown pays.

### 3.7 The sandbox QA agent — **REFERENCE**

`independencev1/src/sandbox/` runs a fourth phase nobody else has: copy the project to a tmpdir,
detect its type (Binary / Library / WebServer / TuiApp), build it, then let an LLM agent with four
tools (`run_command`, `read_file`, `list_files`, `write_file`) **use the thing as a user would**
and write a UX review. Path containment by canonicalize-plus-prefix-check, command allowlist, no
container.

Two reasons to note it. First, the UX score is displayed **separately and deliberately does not
affect the technical verdict** — a clean precedent for how 2.0 should treat "fun" and other soft
scores next to hard gates. Second, `questions.md` §3.5 item 17 asks how to measure fun without
asking the user to score it; an agent that tries to *use* the artifact is one concrete answer, and
it already exists in Rust.

The isolation is too weak to inherit as-is (tmpdir plus allowlist, no container), and 2.0's egress
and permission story is stricter.

---

## 4. What to drop

- **Both codebases wholesale.** They are Grok-first and Ollama-first respectively, tokio-heavy,
  and 6k/11k lines with no test suite worth inheriting. Claudette is the better engine on every
  axis the brief cares about.
- **The 9.5-overall / 9.7-critical gate thresholds.** They produced a 100% pass rate on artifacts
  an independent reviewer graded D and F. `inheritance-map.md` §0 already records that BCF's
  9.2/8.5/8.0 ladder is empirically unreachable all-local; this is the same lesson one step
  earlier and one step worse.
- **Grok as the primary model.** Contradicts local-first.
- **The self-scored critic panel as a gate.** Keep the panel as a *signal*; never let it be the
  thing that decides.

---

## 5. New questions for `questions.md`

1. **Authorship and licensing of the archive repos.** Two GitHub accounts and a second name in
   `Cargo.toml`. Gates any code reuse from §3.1–§3.7.
2. **Should the independence check ship in 2.0, and in which mode?** Always on, opt-in per run, or
   only above a complexity threshold? It costs a full second review pass per artifact on a machine
   with one GPU.
3. **What plays the reviewer role in 2.0?** A second local model, the same model with a different
   prompt and no history, or a frontier escalation? The first is cheapest and most correlated; the
   last is least correlated and costs money — which reconnects to §17 Q7, the still-open spend
   ceiling.
4. **Does `critic_inflation` become a first-class console metric?** It is measurable, operator-
   facing, and there is a calibrated threshold to draw on the dashboard.

---

## 6. Confidence

**High** on the inflation finding's direction and on every date and count — computed from files,
not from claims, and 34/34 admits no reading other than systematic.

**High** on the custody findings. Missing `objects/`, the remote URLs and the author identity were
each checked directly.

**Medium** on the exact magnitude (+5.63 mean / +3.65 median). The reviewer has a documented 7.0
floor and clusters in the middle; the internal gate clusters at 9.5. The direction is safe, the
number is an upper bound on a real effect.

**Medium** on the lineage reordering. It rests on commit dates, the BCF release message, and
StealthForge's own comparison table. I did not find a document stating the ordering outright, and
David is the authority on what was actually derived from what.

**Low** on anything about how well any of it runs. I read the code and the recorded results.
Neither binary was built, neither pipeline was executed, no model was loaded.
