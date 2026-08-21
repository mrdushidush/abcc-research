# W6 — Verification, gates and the TDD pipeline

**Status: IN PROGRESS — started 2026-08-19**, as part of the W3 + W6 + W11 block (§14 item 4).
Built one item at a time in §13 format. W6 **grew** on 2026-08-07: the independence check ships
always-on (David, Q-independence), which with zero cloud spend and one GPU makes "who plays the
reviewer" a hard design constraint that interacts with W2's residency work.

Planned items:

1. ✅ **The instrument, fixed on paper** (F158–F161) — §14's entry condition: *"W6 must fix BCF's
   verifier before recalibrating any threshold."* The defect is now mechanically diagnosed; every
   number the verifier produced is reclassified; the 2.0 verifier's requirements follow from the
   diagnosis.
2. ✅ **The pipeline inheritance** (F213–F224) — BCF's nine stages against Claudette's five-phase
   forge. Answered: nine is a display convention over **three** phases, seven LLM stages collapsed
   to **three** constructed roles, and six of BCF's nine exist to compensate for having no
   repository. Hands W11 a four-phase starting taxonomy (Localize / Change / Measure / Judge, plus
   Veto and Decide). **F202 is now measured, and it grew**: the probe reproduces BCF's pipe-buffer
   deadlock *and* finds that the successor's fix hangs on its own timeout path when the killed
   child left a grandchild holding the pipe (F220, `research/spikes/w6-pipeline/`).
3. ☐ **Who plays the reviewer** — always-on independence on one GPU: same-model-no-history vs
   second-model-swap (23.77 s, W1 F79) vs co-residency; `critic_inflation` as a console metric.
   Gate independence is measured at +3.65 median inflation over 34 missions (W8).
4. ☐ **Verification headroom** — quantify what type checks, linters, generated tests, property
   tests and sandboxed execution buy over v1's syntax-error auto-retry. Needs GPU runs.
5. ☐ **Language generality** — what in the pipeline is language-specific (item 1 shows: almost
   everything that works) and what generalizes.
6. ☐ **Worktrees / per-task isolation** — overhead and RAM cost against the 32 GB ceiling.
7. ☐ **Verifying the unrunnable** — docs and review output; LLM-as-judge failure modes.
8. ☐ **Honest failure reporting** — the design against v1's zero-tests-claimed-passing defect;
   item 1's no-silent-midpoints rule is its first half.

Scope reference: `RESEARCH_BRIEF.md` §11 lines 808–827. Findings continue the family numbering.
Item 1 took F158–F161; W3 then ran to F212 (complete, 2026-08-20); **item 2 took F213–F224, so the
next free number is F225.** The numbering is one sequence across all workstreams — check the
maximum before adding, not the last number in this file
(`grep -rho "F[0-9]\{2,3\}" research/*.md | sort -u | sed 's/F//' | sort -n | tail -3`).

---

# Item 1 — the instrument, fixed on paper

## Question

§14 item 4's entry condition: *"W6 must fix BCF's verifier before recalibrating any threshold,
because the all-local 7.5 average it would calibrate against was produced by an instrument that
scores a correct and a broken Python file identically."*

So: **what exactly is broken, what do the inherited numbers still mean, and what must 2.0's
verifier do differently?** In a research phase the fix is a diagnosis plus a requirements list —
the instrument that gets fixed is 2.0's, not the archived donor's.

## Method

Fresh code extraction from `D:\dev\battle-command-forge` HEAD `d6c1601`, 2026-08-19 (same
three-repo pass as W3 items 1–2), cross-checked against `prestudy/verification.md` §2.2, which
first executed the defect on 2026-08-07. File:line cites are from this pass.

## Inherited

| What | Source | Verdict here |
|---|---|---|
| Gate formula `critique*0.4 + verifier*0.6` | BCF `mission.rs:1137-1139` | shape REUSE, per the map — confirmed below with one large caveat (F159) |
| Complexity-scaled thresholds 9.2 / 8.5 / 8.0 | BCF `mission.rs:57-67` | numbers DISCARD (F160) |
| Per-file scoring model | BCF `verifier.rs:741-765` | the additive shape survives; every current input is compromised (F158) |
| Surgical fix loop, best-round restore, decline breaker | BCF `mission.rs:699-707` + Claudette's security-refusal improvement | REUSE, unchanged from the map |
| "Parse-failure-defaults-to-success" | ABCC `main.py:436-447` | the same disease in the other donor — see F161 |

## Findings

### 🚨 F158 — the verifier never measures behaviour, and its three content signals are dead code

Two causes stack, both in `verify_python` (`verifier.rs:675-704`):

1. **It only parses.** The entire per-file correctness verdict is the exit status of
   `python3 -c "import ast, sys; ast.parse(sys.stdin.read())"` (`verifier.rs:678-679`). A wrong
   comparison operator, an undefined name, an off-by-one — all parse cleanly. Nothing is ever
   executed at the per-file level.
2. **An early `return` kills the heuristics.** The success branch returns at `verifier.rs:695`,
   *before* the `has_tests` / `has_docstring` / `has_error_handling` assignments at `:701-703` —
   so whenever `python3` is on PATH (the intended case), those three fields keep their
   initialized `false`. No compiler warning fires because the tail is reachable via the
   spawn-failed path. The bug is Python-only; the other languages set all four fields — but their
   "syntax checks" are **substring searches** (`content.contains("fn ")` for Rust,
   `verifier.rs:718`), and `verify_generic` scores syntax by **length** (`content.len() > 50`,
   `:735`).

The arithmetic consequence (`calculate_score`, `verifier.rs:741-765`): base 5.0 + 1.5
(`syntax_valid`) + 1.0 (`lint_passed`, which **defaults true**, `:41`) + 0 + 0 + 0 = **every
syntactically valid Python file scores exactly 7.5**, regardless of content. A file with a syntax
error scores 5.8. On Windows there is a second identical-scores mechanism, already executed in
`verification.md` §2.2: `python3` hardcoded resolves to the Store alias, exits 49, and a correct
and a broken file both score 5.80. Either way the claim under §14's entry condition is confirmed
with the mechanism attached: **there is no input to the score that depends on what the code
does.**

Supporting decay, same file: `check_todos` pushes issues but never clears `lint_passed`
(`:653-673`), so the +1.0 survives; `check_secrets` substring-matches `"sk-"` anywhere in a word
(`:633-651`); and the module doc claims mypy, eslint and cargo clippy run (`verifier.rs:3-4`) —
**none of the three appears anywhere else in the codebase.** `ruff` is the only linter wired
(`:124-140`).

### 🚨 F159 — the gate number's only behaviour-sensitive input is the test run, and two of the four stages feeding it weigh zero

The gate (`mission.rs:1137-1139`) is `critique_avg * 0.4 + verifier_score * 0.6`. Traced:

- The **security** (stage 6) and **CTO** (stage 8) verdicts contribute **nothing** to the number —
  they are parsed to booleans for the report (`mission.rs:873-874`) and pasted into retry feedback
  text. A FAIL from either does not move the score.
- The **critique** half is one LLM call role-playing five reviewers; a parse failure on any
  dimension **silently defaults it to 5.0** (`mission.rs:1647-1656`).
- The **verifier** half is the mean of F158's per-file constants, adjusted ±2.0 by the pytest pass
  rate (`verifier.rs:95-110`) — and if no files are found it **defaults to 5.0** (`:96`).
- On the final fix round, `--auto` mode **accepts regardless of score** (`mission.rs:519-537`).
- The persisted report **hardcodes `quality_gate_threshold: 9.2`** whatever the complexity
  (`report.rs:388`) — a C8 mission that passed at 8.6 is recorded as having passed a 9.2 gate.

So the only path by which reality enters the gate is the test run — and BCF's own benchmark notes
(`CLAUDE.md:84`) say tests ran in **5 of 10** missions. In the other five, the verifier term was
pinned at F158's constant.

### F160 — what the inherited numbers still mean: nothing, and saying so unblocks the block

- **The 7.5 all-local average** is numerically identical to the degenerate per-file constant. The
  causal link is not provable from static reading (the critique term adds variance), but it does
  not matter: an average dominated 60% by an input that cannot see behaviour carries no
  information about quality. It is not a baseline to beat; it is a reading from a disconnected
  gauge.
- **The thresholds 9.2 / 8.5 / 8.0** were calibrated against that gauge. The inheritance map said
  "recalibrate, do not inherit"; this item hardens that: **there is nothing to recalibrate
  *from*.** The inverted-scaling idea (harder task, lower bar) survives as a hypothesis worth
  re-testing on a working instrument — W8's harness, whose Q56 cells carry real per-task
  verifiers, is that instrument.
- **What genuinely survives** (all confirmed live in the same files): the *shape* of the gate —
  a deterministic verifier outweighing an LLM judge; the surgical fix loop with best-round restore
  and the 0.1 decline breaker (`mission.rs:699-707`); the three fix-round guards (too-short fix,
  reasoning-leak markers); and `MAX_FIX_ROUNDS` with its compile-time floor assert
  (`mission.rs:52-55`).

### 🚨 F161 — the family's verification failures are all the same bug: a default that pretends to be a measurement

Put side by side, the donors' verification defects are one disease:

- ABCC defaults a **parse failure to success** (`main.py:436-447`) — the agent that claimed two
  passing tests on a run that executed zero.
- BCF defaults an **unparseable critique to 5.0 per dimension**, a **file-less project to 5.0**,
  and a **lint that found problems to lint_passed=true** — midpoints and passes invented where no
  measurement happened.
- v1 collapses `UNCERTAIN` to a clean pass at the Python/TS boundary (W3 F150).

**The 2.0 rule, stated once for every gate input: absence of measurement is `Uncertain`, and
`Uncertain` is a rendered, routed state — never a midpoint, never a pass.** This is the first half
of §11's honest-failure-reporting requirement, and it is why W3 item 1 kept the four-valued
outcome lattice in the `Attempt` type: the lifecycle now has somewhere for "the instrument could
not run" to go that is not a lie in either direction.

## Options compared

| Option | What the gate scores mean | Cost | Verdict |
|---|---|---|---|
| Inherit the thresholds as defaults, tune later | readings from a disconnected gauge anchor every early decision | none now, compounding later | rejected |
| Fix BCF's verifier and re-run its 10-mission benchmark to recalibrate | numbers from a dead donor's corpus, on missions 2.0 will never run | days of work in an archive | rejected |
| **Discard the numbers; inherit the shape; calibrate on W8's harness with 2.0's verifier** | every threshold traceable to a measurement made by a working instrument on 2.0's own tasks | calibration waits for Phase 3's verifier — which §14 already sequences after the research | **recommended** |

## Recommendation

1. **Declare the inherited numbers void** — the 7.5 average and the 9.2/8.5/8.0 ladder never
   enter 2.0's config, docs or defaults, so they cannot anchor anything.
2. **Inherit the shape**: deterministic-verifier-over-judge weighting, surgical fix loop,
   best-round restore, decline breaker, capped rounds with the compile-time floor — plus
   Claudette's refusal to restore a security-rejected round.
3. **2.0's verifier requirements, from the diagnosis**: behaviour first (execute tests; the pass
   rate is the core signal, not an adjustment), real parsers per language (never substrings, never
   length), every scoring input reachable (a heuristic that cannot fire is a lie in the weights),
   lint findings that affect the lint verdict, and **no silent midpoints** — every input is
   `Measured(x) | Uncertain(why)`, per F161.
4. **The stage-verdict wiring is a design decision, not an accident**: if security and CTO
   verdicts gate, they enter the formula or hard-veto explicitly; weight-zero inputs that look
   load-bearing are F159's reporting drift waiting to recur.
5. **Recalibrate thresholds only on W8's harness**, where the inverted-scaling hypothesis can be
   tested against per-task verifiers that actually run.

## Rejected alternatives and why

- **Patching the archived BCF.** The donor is a closed POC (David, 2026-08-07: "something along
  the way"); fixing its instrument would produce numbers about its corpus, not about 2.0.
- **Treating the 60/40 weights as calibrated.** They were chosen, not fitted — and fitted against
  F158's gauge they could not have been. Carry them as a starting shape with the same skepticism
  as any other uncalibrated constant.

## Effect on fun

The gate is where the game earns its stakes: a commando stage that passes everything is not
drama, it is decoration — v1's parse-failure-defaults-to-success made every battle a scripted
win, which is §7's definition of boring. An `Uncertain` that renders honestly (a unit radioing
`something-wrong` instead of `all-clear`) is both the honest instrument and the better show.

## Open questions

| # | Question | Waiting on |
|---|---|---|
| OQ-W6-1 | Do security/CTO verdicts enter the formula, hard-veto, or advisory-only? | item 2 (pipeline), W11 |
| OQ-W6-2 | Does `critic_inflation` ship as a console metric now that the check is always on? | item 3 |
| OQ-W6-3 | The first threshold set for 2.0's verifier — chosen how, before W8 data exists? | item 4, W8 |

## Confidence: high on the diagnosis, high on voiding the numbers

The defect mechanism is line-level and was independently confirmed by execution in
`verification.md` §2.2 before this pass read the code. Voiding the numbers follows arithmetically.
Medium only on the requirements list's completeness — items 4 and 7 (headroom measurement,
judge reliability) may add rows.

---

# Item 2 — the pipeline inheritance

## Question

§11's scope for this item: *"Start from BattleCommandForge's 9-stage pipeline. Document what it
actually does, how the complexity-scaled quality gates score, and what carries over. This is the
single most reusable asset across the three repos."*

Item 1 answered the scoring half and voided the numbers. This item answers the structural half:
**which of BCF's nine stages are stages, which were always one model call wearing another hat, and
what did Claudette's successor learn by collapsing to five?** The deliverable is not a preference.
It is a starting taxonomy W11 can reconcile against, derived from what both pipelines run.

## Method

Fresh extraction from both Rust donors at their pinned commits — BCF `d6c1601`
(`src/mission.rs`, 2,449 lines; `src/router.rs`; `src/model_config.rs`; `src/sandbox.rs`) and
Claudette `af3f804` (`crates/claudette/src/run/forge_run.rs`, 1,803 lines; `prompt.rs`;
`run/runtime_build.rs`; `tools/quality.rs`; `security_review.rs`; `test_runner.rs`), plus a
confirming pass over ABCC v1 (`packages/agents/src/`). All file:line cites are from this pass,
2026-08-21.

Two methods from this block were applied deliberately:

- **Grep the readers, not the writers** ([[verify-claims-against-code-not-docs]] 19). Claudette
  declares eight forge roles; the running pipeline constructs three. No amount of reading the
  role definitions would have shown that (F215).
- **When the claim is about the OS rather than the codebase, stop reading and run it** (item 20).
  The reading said Claudette's subprocess runner was correct and BCF's was broken. Ten minutes of
  probing confirmed the first half and found that the successor's *timeout* path hangs outright
  (F220). Spike: `research/spikes/w6-pipeline/`.

## Inherited

| What | Source | Verdict here |
|---|---|---|
| The nine-stage pipeline as a structure | BCF `mission.rs:262`–`:1141` | **DISCARD as a structure** — it is three phases and a display convention (F214) |
| ARCHITECT → a design document | BCF `:416-421` | **REPLACE** with the successor's read-only localizing Planner (F213) |
| TESTER, tests-before-code | BCF `:442-443` | **DROP as written** — defeated by its own merge rule (F216); revivable only as an immutable artifact |
| CODER, one call emitting every file | BCF `:1171-1217` | **REPLACE** with an agentic, tool-using, committing Coder (F213) |
| SECURITY as a scored stage | BCF `:1056-1070` | **REPLACE** — survives as a deterministic veto, not a score (F217) |
| CRITIQUE, "5 specialist reviews" | BCF `:1100` / `:1624-1640` | **COLLAPSE** — it was always one call, and it is blind to the tests (F217) |
| CTO review | BCF `:1112-1133` | **REPLACE** with the human review gate, or with a rung on W3's ladder (F217) |
| Weighted gate number | BCF `:1137-1139` | **DISCARD** (item 1, F159/F160) — the gate stops being a number |
| Deterministic build+test gate | Claudette `tools/quality.rs:344` | **INHERIT — with the timeout fixed** (F218, F220) |
| Fix loop, best-round restore, decline breaker | both | REUSE the first two; the third needs a round budget stated with it (F223) |

## Findings

### F213 — the two pipelines are not the same kind of object, and that is what collapsed seven LLM stages into three

BCF is a **greenfield generator**: the CODER emits every file as fenced markdown in one call, and
`codegen::extract_files` writes them to an output directory (`mission.rs:1216-1226`). There is no
repository, no VCS, and nothing on disk to read. Claudette's forge is a **brownfield editor**: the
Coder is a full agentic turn with Files / Search / Git / Advanced / Github tool groups
(`runtime_build.rs:222-235`), it commits to a mission branch, and every downstream phase grades a
`git diff` (`forge_run.rs:666-667`).

That difference explains most of the collapse. BCF *must* have an ARCHITECT, because there is no
code to localize into — the spec is the only context that exists. It *must* have a TESTER, because
no suite exists to run. Claudette needs neither: its Planner **reads the repository** rather than
designing a system (`prompt.rs:240-266`), and the project's own test suite replaces the generated
one (`quality.rs:344`). **Six of BCF's nine stages exist to compensate for not having a
repository.**

2.0 is not a greenfield generator. David's answered question 2 in `RESEARCH_BRIEF.md:1264-1270`:
*"Target workload: repository work plus legacy review plus general-purpose coding"*, with the same
paragraph noting that **"BCF's missions are greenfield generation"** and calling that a gap W8 must
close. So the inheritance runs through the successor, not the donor: **2.0 inherits BCF's
vocabulary and Claudette's shape.** Where the map said "BCF's pipeline is the single most reusable
asset", this item narrows it: the reusable asset is the *gate discipline* and the *stage names*,
not the stage list.

### F214 — the nine stages are three phases; "9" is a display convention, and there is no path back to the plan

The structure, read off `mission.rs`:

- Stages **1–3** (ROUTER `:262`, ARCHITECT `:416`, TESTER `:442`) run **once**, before the loop.
- Stages **4–8** are the loop body (`attempt_round_with_report`, entered at `:482-491`), repeated
  up to `MAX_FIX_ROUNDS = 5` (`:52`). After round 0 the banners **relabel to `[FIX]`** while the
  numbers stay (`:995`, `:1055`, `:1075`, `:1112`) — same code, different caption.
- Stage **9** is one line of arithmetic and a log line (`:1137-1141`).

There is no `Vec<Stage>`, no stage trait, no table: the pipeline is straight-line calls in one
2,449-line file. Nothing enumerates the stages, so nothing can skip, reorder, retry or *report* one
generically — which is why the persisted report hardcodes its threshold (item 1, F159).

The consequence that matters is not the count. **Stages 1–3 never re-run.** A wrong complexity
assessment, a wrong architecture or a wrong test plan is frozen for all five fix rounds; the loop
can only re-write code against a brief it cannot question. Claudette inherited exactly this
property and its own comment says so — the Planner runs once at `forge_run.rs:592-593`, and
`:607-609` notes the brief *"is trusted blindly downstream and never re-planned"*. The successor's
answer was not to add a re-plan path but to add an **advisory** check that the brief's file paths
exist (`warn_if_brief_paths_missing`, `:1073-1121`), explicitly *"never blocks"*.

**For 2.0:** whether localization is revisable is a live design decision, not an oversight to
inherit. W3's lattice already has the shape for it — an attempt that fails classification `Wrong`
can fork a *new attempt with a new brief* rather than another fix round against the old one. State
it, or 2.0 will re-derive the same frozen-plan pipeline by accident.

### F215 — the role vocabulary outlived the roles: eight declared, three constructed

Claudette's `forge::types::Role` declares eight variants — `Assistant`, `Planner`, `Router`,
`Coder`, `TestCoder`, `Verifier`, `SurgicalCoder`, `Cto` (`forge/types.rs:18-35`). Each has a model
in the default map (`forge/models_toml.rs:101-108`), a TOML override key (`:160-169`) and a persona
parser entry (`forge/personas.rs:193-200`).

Grepping the **construction sites** in the running pipeline finds three:

| Role | Constructed at | |
|---|---|---|
| `Planner` | `forge_run.rs:1260` | read-only tools (Files, Search) |
| `Verifier` | `forge_run.rs:1285` | **no** tool groups |
| `Coder` | `runtime_build.rs:225` | full toolset |
| `Router`, `TestCoder`, `SurgicalCoder`, `Cto` | — | model map, persona parser, and `examples/forge_e2e.rs:71-78` only |

And the fifth phase is not a fourth role: the Submitter calls `build_forge_runtime(session,
&mission, true)` (`forge_run.rs:1027`), which is the **same `Role::Coder` runtime with the same
full toolset**, differing only in one closing sentence of the system prompt
(`prompt.rs:186-190`) — the code comment at `runtime_build.rs:219-222` says restricting it was
"tempting" and rejected.

So the honest count is: BCF **seven** LLM stages (1, 2, 3, 4, 6, 7, 8) + one deterministic (5) +
one arithmetic (9) → Claudette **three** model roles + one re-prompt + two deterministic gates.
"Nine collapsed to five" understates it; seven collapsed to three.

**For 2.0, and for W11 directly:** four role names survive in the vocabulary with no mechanism
behind them. Q8 already ruled that role naming goes *into the Rust domain model*
(`RESEARCH_BRIEF.md:1255`), which makes this exactly the trap W3 item 5 documented — a name that
exists in three places and runs in none. Declare a role only where a construction site exists.

### F216 — the TDD stage is defeated by its own merge rule, which is why the successor dropped it

BCF stage 3 writes tests before any code exists (`mission.rs:442-443`, *"TESTER: Writing tests
first (TDD)"*), using a dedicated model — under the default preset, **Claude Opus**
(`model_config.rs:175`). Then stage 4 happens:

1. The CODER's prompt orders it to write the tests too: *"Generate ALL files: production code,
   tests (conftest.py + test files), and pyproject.toml"* (`mission.rs:1209-1211`).
2. The tester's output reaches the coder **truncated to 4,000 characters**
   (`truncate_str(tests_raw, 4000)`, `:1199`).
3. The merge rule keeps the coder's version on any path collision — *"Merge tester-generated test
   files (don't overwrite coder's)"* — pushing a tester file only `if !all_files.iter().any(|f|
   f.path == tf.path)` (`:1221-1227`).

For a Python project with conventional layout (`tests/test_*.py`, `conftest.py`) collision is the
normal case, not the exception. **The implementer overwrites the specification it was supposed to
be graded against**, and the stage that cost a cloud model call survives only in whatever files the
coder happened not to name. Tests-before-code is present as a stage and absent as a mechanism.

Claudette dropped it outright: `Role::TestCoder` has no construction site (F215), no prompt
mentions writing tests, and the Coder's instruction is *"Make the smallest change that satisfies
the request"* (`prompt.rs:198-200`). Verification runs the **project's existing** suite instead.

**For 2.0:** TDD is in this workstream's title, so this is a decision, not a deletion. The rule the
donor teaches is precise — *a generated test is only a gate if the implementer cannot edit it.*
Any revival must make the test artifact immutable to the Change phase (separate commit, separate
path space, or a diff-level refusal), and must show the implementer all of it, not the first 4 KB.
Otherwise it is a model call that buys a banner.

### F217 — the successor replaced LLM stages with deterministic gates, and the gate stopped being a number

This is the inheritance, stage by stage:

| BCF | What it contributed to the verdict | Claudette's replacement | Kind |
|---|---|---|---|
| 5 VERIFIER `:996` | mean of per-file constants ±2.0 by pytest rate (item 1, F158) | `run_build_and_tests` — real build/typecheck + the project's real suite, four frameworks (`quality.rs:344-404`) | deterministic, **the whole signal** |
| 6 SECURITY `:1056` | **zero** (F159) | `security_review::scan_diff` — 29 deterministic rule sites over added diff lines only, string literals blanked (`security_review.rs:299-311`) | deterministic **veto**: HIGH fails the round (`forge_run.rs:773-783`) *and* blocks the PR after the loop (`:911-943`) |
| 7 CRITIQUE `:1076` | 40% of the gate, from one call role-playing five reviewers | the Verifier's own `{"score","pass","feedback"}` judgement | one model call, honestly labelled as one |
| 8 CTO `:1114` | **zero** | the human review gate — plan + full diff + explicit `y` before any push (`forge_run.rs:993-1020`), **on by default** | a person |
| 9 GATE `:1137-1141` | `critique*0.4 + verifier*0.6 ≥ quality_gate(complexity)` | `pass = model_pass && score >= 8` (`forge_run.rs:1310`, `:1367-1371`), then hard overrides | a boolean with vetoes |

Two structural readings follow.

**The weighted average is gone, and what replaced it is a conjunction.** In Claudette a round
passes only if the judge says pass *and* the score clears a constant *and* the diff is non-empty
(`forge_run.rs:686-707`) *and* the build+test gate did not hard-fail (`:719-746`) *and* no HIGH
security finding stands (`:754-783`). Every one of those is a refusal, not a term. A refusal cannot
be outvoted by a generous number elsewhere, which is exactly how BCF's weight-zero security stage
became decoration.

**🚨 In both donors the model judgement is computed blind to the strongest measurement available.**
BCF's `run_critique_panel(&all_code, spec)` receives code and spec only (`mission.rs:1082`,
`:1624-1640`) — never the verifier report, never the pass/fail counts, though stage 5 has already run.
Its CTO prompt gets request + code + security verdict (`:1124-1130`) — also no test results.
Claudette runs the Verifier turn **before** the build+test gate (`:666` then `:719`), so its judge
grades a diff without knowing whether it compiles. In both, the cheapest and most reliable evidence
in the system is withheld from the most expensive and least reliable component. Ordering the phases
**measure → judge**, and putting the measurements in the judge's prompt, costs nothing and is
strictly more informed. See OQ-W6-4.

### F218 — F161's rule already has a working implementation in the family, and its type is `Option<bool>`

Item 1 ended on the family's unifying defect and the rule that answers it: *absence of measurement
is `Uncertain`, never a midpoint, never a pass.* The successor already implements it, in the exact
place BCF defaults to 5.0:

```rust
pub(crate) struct BuildTestOutcome {
    pub ran: bool,                 // false = no recognised framework
    pub build_ok: Option<bool>,    // None = no compile step, or the tool would not run
    pub tests_ok: Option<bool>,    // None = tool missing / timed out / nothing collected
    pub summary: String,           // the human- and Coder-readable why
    pub framework: &'static str,
}
impl BuildTestOutcome {
    pub fn is_hard_fail(&self) -> bool { self.build_ok == Some(false) || self.tests_ok == Some(false) }
}
```

(`quality.rs:317-340`.) `None` is produced deliberately at every non-measurement: build timeout
(`:427`), build tool absent (`:433`), test timeout (`:467`), test tool absent (`:472`), pytest
exit 5 = no tests collected (`:490`), and air-gapped mode, where the whole gate abstains with a
sentence explaining that the toolchain is not run offline (`:351-365`). Only
`Some(false)` gates. The `summary` carries the reason to both the operator and the next Coder
round.

The same discipline appears at the judge: `parse_verifier_response` **abstains as a fail with score
0** on unparseable, fence-only, or missing-field output (`forge_run.rs:1325-1348`), and a verifier
*turn* error (timeout, OOM, provider 5xx) is caught and converted to `score 0 / pass false` rather
than an endorsement (`:660-670`). Score 0 rather than a midpoint is load-bearing: it stops an
abstention from winning best-round restore.

**For 2.0:** `Measured(x) | Uncertain(why)` is not an aspiration, it is a port. Take the tri-state
*and* its two companions — the `why` string travels with the abstention, and the abstention's
numeric value must lose every comparison it enters.

### F219 — 🚨 the cure is in the code and the disease is still in the documentation

Two doc comments in Claudette describe the **pre-fix** behaviour, and both say the opposite of what
the code does:

- `forge_run.rs:1269-1273`, on `run_verifier`: *"Unparseable responses fall through to a permissive
  default (pass=true, score=10) so a poorly-behaved Verifier model can't deadlock a working
  Coder."*
- `prompt.rs:268-272`, on `forge_verifier_system_prompt`: *"an unparseable response is treated as a
  pass (advisory mode, never blocks the pipeline)."*

The code twelve lines below the first one fails closed and says so at length (`:1315-1324`). The
only correct specification of this behaviour is the test module —
`verifier_unparseable_fails_closed` (`:1510`), `verifier_missing_fields_fail_closed` (`:1539`),
`verifier_pass_requires_score_threshold` (`:1498`).

This is not pedantry about comments. It is the same lesson as item 1's F161 arriving from the other
direction: **the most convincing statement of a gate's policy is the one nobody executes.** A
reader porting this pipeline from its documentation would port the bug — and the documentation is
where a porting reader starts. ([[verify-claims-against-code-not-docs]]: this is item 18's shape,
found inside a donor rather than in our own reading.)

**For 2.0:** the abstention policy is asserted in a test or it does not exist. Prose about a gate
is a comment on a test at best.

### F220 — 🚨 measured: the inherited build/test gate hangs *after* it announces the timeout

This item recommends inheriting Claudette's deterministic gate. Before inheriting a mechanism, run
it. Probe and raw output: `research/spikes/w6-pipeline/`, two runs agreeing exactly, Windows 11.

**Cell 1 — F202 reproduces by execution.** BCF's shape (`sandbox.rs:126-134`: pipe both streams,
`try_wait` to completion, *then* `read_to_string`) deadlocks on a child that writes 512 KiB, a
small `cargo test` run. `wait()` consumed the entire 8 s budget; the child only finished once the
parent drained. F202 was a reading; it is now a measurement. Worse than recorded: BCF's timeout arm
returns `stdout: String::new()` (`sandbox.rs:146-150`), so the mission logs a timeout with **no
output at all** — neither pass counts nor failure text reach the fix round.

**Cell 2 — the successor's fix holds on the normal path.** The same child, drained on two reader
threads (`test_runner.rs:64-65`), completes in **0.03 s** with all 512 KiB captured. The module doc
at `test_runner.rs:33-38` names the bug and explains it — the family contains its own fix, in the
other repo.

**Cell 3 — 🚨 and the timeout path hangs.** Claudette's timeout arm kills the direct child
(`test_runner.rs:82`) and then **joins the reader threads** (`:87-88`), under a comment stating the
assumption: *"Reader threads exit cleanly once the kill closes the pipe ends."* They do not, when
the child had a child of its own. W3 item 7 (F206–F212) measured that `child.kill()` orphans
grandchildren; the orphan also inherited the pipe's **write end**, so the reader never sees EOF:

```
[3/plain] kill at timeout, grandchild pid 16220 STILL RUNNING: reader join STILL BLOCKED
          after 11.01 s (budget 10 s)
```

The wrapper shape is the normal one, not a contrivance: `cargo test` compiles and then spawns the
test binaries as separate processes, and Claudette's own `bash` tool runs `powershell -NoProfile
-NonInteractive -Command <cmd>` with a 30 s timeout (`tools/shell.rs:209-212`, `:222`). So a suite that overruns
`forge_test_timeout_secs()` (default **180 s**, `forge_run.rs:119-125`) does not fail the round —
it stops the pipeline, with the timeout message already composed and never returned.

**Cell 4 — W3 item 7's fix closes this one too.** With the child in a Windows Job Object carrying
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, closing the handle kills the tree, the last write end
closes, and the join returns in **0.00 s**. The job object was already costed at **0.04 ms** by the
topology spike. One mechanism fixes an orphaned workspace and a hung verification gate, which is
the argument for putting it in the worker seam rather than at either call site.

**For 2.0, four rules:** drain concurrently, never after wait · a timeout kills the **tree**, not
the handle you happen to hold · never join a reader you have not closed, and bound the join anyway
· and a gate's failure modes are its interface — `Uncertain(timeout)` is a legitimate verdict
(F218), *no verdict ever* is not.

Honest scope: measured on Windows only, with Python subprocesses reproducing the shape and the OS
semantics rather than the donors' binaries. The Unix equivalent of cell 4 (process groups +
`killpg`) is **not measured here**; the line-level match to `test_runner.rs:82-88` and
`sandbox.rs:126-150` is from reading.

### F221 — the complexity router is a one-way ratchet toward a lower bar

Stage 1 is "dual": a rule score and an LLM score, combined in `assess_complexity_dual`
(`router.rs:78-140`). The combination rule is asymmetric:

| Case | Result | Direction |
|---|---|---|
| AI ≥ rules + 2 | take the AI score outright | **up** |
| \|AI − rules\| < 2 | `((rules + ai) / 2).max(rules)` — averaged, then **floored at the rule score** | never down |
| AI ≤ rules − 2 | `0.6·rules + 0.4·ai` | down, damped to 40% |

So the model's opinion is free to raise complexity and is either ignored or heavily damped when it
lowers it. Then complexity **lowers the bar**: `quality_gate` returns 9.2 for C1–C6, 8.5 for C7–C8,
8.0 for C9+ (`mission.rs:57-67`). Net: the one LLM input to routing can almost only make the gate
easier to pass, and the tier it picks also selects bigger, slower models.

Item 1 voided the ladder's numbers and kept the inverted-scaling *idea* as a hypothesis worth
re-testing. This finding adds the precondition: **an estimator that scales the bar must be able to
move the bar in both directions.** Re-testing inverted scaling on a ratcheting estimator measures
the ratchet, not the hypothesis.

Also worth carrying: the rule half is a keyword-and-length heuristic (`router.rs:147-311`) with a
real test suite (`:363-492`) — it is the cheapest complexity signal in the family and it costs no
tokens. If 2.0 wants a router at all, the honest starting position is *rules by default, model
opinion as a recorded second reading*, which is also what W3's escalation ladder wants: a routing
decision is **data on the event log**, not a phase.

### F222 — the stage boundary is a VRAM boundary, and the nine-stage pipeline's default was never all-local

Five `offload_model` calls punctuate the pipeline (`mission.rs:438`, `:462`, `:988`, `:991`,
`:1108`), each POSTing `keep_alive: 0` to Ollama (`:1750-1762`). Three of them are **inside** the
fix-round loop, so every round can pay them again. The one at `:988` is **unconditional** —
*"Unload coder/fix_coder model to free VRAM for reviewer"* — which under the `Fast` preset, where
seven of the eight roles are the same `qwen2.5-coder:7b` (`model_config.rs:150-160`), unloads a
model and immediately reloads the identical weights for the next stage.

W1 F79 measured a champion-class swap at **23.77 s round trip** (n=3 per direction). A 7B swap is
cheaper and is *not* measured here — the point stands regardless: **on one GPU, a stage boundary
between two different models is a stall, and none of BCF's reported per-mission timings include
it** as anything but wall clock nobody attributed.

And the configuration those stages were designed for is not local at all. `ModelConfig::default()`
returns `Preset::Premium` (`model_config.rs:437-439`), whose **tester is `claude-opus-4-6`,
fix_coder and cto are `claude-sonnet-4-6`** (`:172-182`) — three cloud roles. The all-local run
that produced the 7.5 average (item 1, F160) was the *exception* configuration, not the default.
For a project whose stated design point is zero cloud spend on one 16 GB card, this reframes the
donor: **the nine-stage pipeline as shipped is a cloud-assisted design, and its stage count is a
cost 2.0 pays in full.** W6 item 3 (who plays the reviewer) inherits the number; W2's residency
work is where it gets attacked.

### F223 — the decline breaker changed meaning when it was inherited, and is inert at the default budget

Both donors have a "score declining → stop early" breaker. They are not the same rule:

- **BCF** (`mission.rs:697-706`): from round ≥ 2, break if `result.final_score < prev_best - 0.1` —
  a **single** drop more than 0.1 below the running best. The comment above it says *"Stop early if
  score hasn't improved for 2 consecutive rounds"*, which is not what the code checks.
- **Claudette** (`forge_run.rs:297-308`): break if the last **three** history entries are strictly
  declining. Its own doc note (`:290-296`) records the consequence honestly: with
  `DEFAULT_MAX_FIX_ROUNDS = 3` it *"can only fire on the same final pass the round cap would break
  on anyway — it changes the exit message, not the pass count"*, and only earns its keep when
  `CLAUDETTE_MAX_FIX_ROUNDS` is raised to ≥ 4.

So an inherited mechanism kept its name, changed its trigger, and landed in a loop too short to
contain it. Note the asymmetry in how each donor handled being wrong: BCF's comment misdescribes
its code; Claudette measured the interaction and **wrote it down instead of deleting the code** —
which is the behaviour to inherit.

**For 2.0:** a stopping rule and the round budget are one decision. State them together (`k`
declines within `n` rounds, `n > k`) or neither means anything. This is the same class as W3 item
5's three divergent ladders, caught before it ships.

### F224 — v1 has no pipeline, and its two defaults point in opposite directions

For W11's taxonomy: ABCC v1's "three agents" are not three stages.

- The **role is chosen by substring match on an agent id**, with a silent fallback:
  `if "coder" in request.agent_id.lower() … elif "qa" … elif "cto" … else agent_type = "coder"`
  (`packages/agents/src/main.py:279-291`). The three factories build CrewAI `Agent` objects —
  persona, goal, tools, `max_iter` (`agents/cto.py:5-19`, `agents/qa.py`, `agents/coder.py`) —
  with no ordering between them. Whether a QA agent ever runs is a property of how the fleet was
  named, not of any code path.
- The actual orchestration is two calls, and the module says so: *"Called exactly twice per
  mission: once to decompose, once to review"* (`packages/agents/src/orchestrator.py:9`).
  Decompose fans out one-file/one-function subtasks; review scores the collected results.

And the defaults: `review_results` fills missing fields **fail-closed** — `approved: False`,
`score: 0` (`orchestrator.py:361-364`) — while the verification path in the same repo defaults a
**parse failure to success** (`main.py:436-447`, item 1's F161). Same codebase, same author, two
opposite policies a few files apart. That sharpens F161's diagnosis: the family's verification
disease is not a competence gap, it is the absence of **one stated rule applied at every gate
input**. Which is precisely what F161 supplies and F218 shows can be typed.

## Options compared

| Option | What 2.0's pipeline becomes | Cost | Verdict |
|---|---|---|---|
| Port BCF's nine stages and fix the verifier | seven model calls per round on one GPU, six of them shaped by greenfield generation, with stages 1–3 frozen | swap stalls (F222), a TDD stage that cannot bind (F216), a gate that averages away its own vetoes | rejected |
| Port Claudette's five phases as-is | three model roles + two deterministic gates, brownfield-shaped and already debugged | inherits the hung timeout (F220) and the blind judge (F217) verbatim | rejected as-is |
| **Take the successor's shape, fix what the probe found, and re-derive the phase list from what each stage contributes to the verdict** | four phases and two gate kinds (below), each with a construction site | one design decision now (re-plan path, F214); the job-object seam is already W3's | **recommended** |

## Recommendation

**1 — The starting taxonomy handed to W11.** Derived from what both pipelines run, not from a
preference. Four phases and two gate kinds:

| # | Phase | Kind | Absorbs |
|---|---|---|---|
| 1 | **Localize** | model, read-only tools, once per attempt, output is a grounded brief | BCF ARCHITECT + Claudette Planner |
| 2 | **Change** | model, full tools, commits; the fix round is *this phase with different feedback*, not another phase | BCF CODER + SurgicalCoder + Claudette Coder |
| 3 | **Measure** | **no model** — build, typecheck, the project's real suite, the diff scanner; tri-state per input | BCF VERIFIER + SECURITY (as measurement) |
| 4 | **Judge** | **one** model call, no tools, sees the diff, the brief **and the measurements** | BCF CRITIQUE + CTO + Claudette Verifier |

plus two things that are not phases:

- **Veto** — deterministic, non-scoring refusals evaluated after Judge: security HIGH, empty diff,
  build break, `Uncertain` where a measurement was required. A veto is never a weight.
- **Decide** — the ship call: the human review gate by default (Claudette's, on by default), or a
  rung on W3's escalation ladder when unattended.

Names that do **not** become phases, with the reason: **Router** — a routing decision is data on
the event log (F221); **Tester** — an artifact, and only if immutable to phase 2 (F216);
**SurgicalCoder** — a prompt variant of phase 2; **CTO** — a person, or an escalation rung (F217).
Entity naming (task / mission / unit / operation) remains W11's, per W3 item 1.

**2 — Order the loop `Change → Measure → Judge`,** and put the measurements in the Judge's prompt.
Both donors judge blind to their own tests (F217); fixing it costs one prompt field.

**3 — Every gate input is `Measured(x) | Uncertain(why)`,** ported from `BuildTestOutcome`'s
`Option<bool>` + `summary` (F218), with `Uncertain` losing every comparison it enters.

**4 — Fix the plumbing before inheriting it** (F220): drain concurrently, kill the process **tree**
via W3 item 7's job-object seam, bound the reader join, and render a timeout as
`Uncertain(timeout)` carrying whatever partial output was captured.

**5 — Decide the re-plan path explicitly** (F214). Both donors freeze the brief for the whole fix
loop. 2.0 should either state that as a rule with the failure mode named, or let a `Wrong`
classification fork an attempt with a fresh Localize — W3's lattice already supports the second.

**6 — Declare a role only where a construction site exists** (F215), and state the round budget
together with any stopping rule (F223).

## Rejected alternatives and why

- **Keeping "nine stages" as the console's vocabulary while running four phases.** Tempting for
  the RTS framing — nine unit types is a better-looking sidebar. It is also exactly the drift that
  produced a report claiming a 9.2 gate on a mission that passed at 8.6 (item 1, F159). The
  console renders phases that exist.
- **Reviving TESTER now.** It is a genuinely good idea that the donor never made binding (F216),
  and reviving it properly means an immutable-artifact design plus a measurement of whether
  generated tests beat existing ones on the real workload. That is W6 item 4's headroom question
  with a GPU attached, not a structural ruling to make here.
- **Rebuilding BCF's greenfield path for parity.** 2.0's answered target workload is repository
  work (`RESEARCH_BRIEF.md:1264-1270`). A greenfield generator is a later feature, not the shape
  of the pipeline.

## Effect on fun

The stage list is the console's cast. Nine stages that are really three phases would put seven
marching units on the battlefield where three do the work — and W5's finding was that the agency
has to be *in* the terminal, which means what animates has to be what happens (F98/F106). A
`[FIX]` banner that relabels the same code is the visual equivalent of BCF's 9.2-on-an-8.6 report.

The upside is that the honest structure is the more dramatic one. **Measure** is the only phase
whose outcome is not a model's opinion — it is the phase where the battle is actually won or lost,
it produces real numbers (tests passed, tests failed, build broken), and it is fast enough to
watch. A veto is better theatre than a weighted average: a security scanner refusing to let a PR
out is a gate slamming, where `critique*0.4 + verifier*0.6 = 8.61` is a spreadsheet. And
`Uncertain` is the most interesting state on the field — a unit radioing *"could not reach the
objective"* is a story; a unit reporting 5.0 because nobody looked is the scripted win §7 calls
boring.

## Open questions

| # | Question | Waiting on |
|---|---|---|
| OQ-W6-4 | Does the Judge see the Measure phase's output before scoring? (Recommended: yes. Neither donor does it.) | design, W11 |
| OQ-W6-5 | Is Localize re-runnable — can a failed attempt fork a new brief, or is the brief frozen per task? | W11, W3's lattice |
| OQ-W6-6 | Does a generated-test artifact return, and if so what makes it immutable to the Change phase? | item 4 (GPU headroom) |
| OQ-W6-7 | Rules-only router, or rules plus a recorded model reading? Does 2.0 scale the bar by complexity at all, now that the ratchet is known? | item 4, W8 |
| OQ-W6-1 | *(from item 1)* Security/CTO verdicts: formula, hard-veto, or advisory? | **answered here**: deterministic veto, never a weight (F217) |

## Confidence: high on the structure, high on the probe, medium on the taxonomy's boundaries

The stage-by-stage extraction is line-level and re-checkable; the collapse from seven LLM stages to
three came from grepping construction sites, not from reading intent. F220 is measured twice with
identical verdicts, with its platform scope stated. Medium on the four-phase taxonomy's edges —
specifically whether **Localize** and **Judge** stay separate calls once 2.0's own verifier exists
(a judge that reads the repo is a different, more expensive animal), and whether the fix round
stays a variant of **Change** or earns its own phase when the surgical-patch idea is re-tested.
Those are W11's to settle with this as the starting position.
