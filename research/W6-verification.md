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
3. ✅ **Who plays the reviewer** — **answered and measured in W11 item 4 (F270–F284), which owns
   the measurement; this item cites it rather than repeating it.** Of the three candidates:
   **same-model-no-history wins**, and the reason is that the deciding axis is not the weights but
   what the reviewer is shown — the same model in a fresh call is 11/12 reading the diff and 5/12
   reading the author's completion report (F280), 0/3 on the shipped sham when the report is added
   *alongside* the diff (F281), and 4/12 with five empty payloads when it continues the author's own
   conversation (F282). **Co-residency is arithmetically impossible on this card** — 1,210 MiB free
   against a 4.41 GB smallest model (F275). **The second-model swap is priced and measured** at
   26.3 s round trip plus 4.6× the decode, and the second model returned no verdict at all on the
   correct answer 3/3 (F284). `critic_inflation` **does not ship**: item 3's verdict has no score, so
   the quantity does not exist — its successor is the veto yield, the contradiction count, the
   criterion-coverage fraction and the `Uncertain` count (W11 item 4 recommendation 4, closing
   OQ-W6-2). W8's +3.65 median inflation over 34 missions stands as the motivation and not as a
   number 2.0 can reproduce.
4. ✅ **Verification headroom** (F297–F310) — quantified over **431 real agent attempts** and 9
   constructed artifacts. **v1's baseline does not fire**: its syntax check is on the wrong agent's
   tool list, its validation channel scores a green test suite as a failure, and on default settings
   the live path auto-passes a task with no validation command and drains its retry queue only when a
   benchmark script asks it to. Against the suite verifier instead: **a type check caught 0 of 114
   real failures in two languages, a syntax check 0 of 114, and a linter is strictly dominated by
   the test suite in both**. What fires is the free structural check — *did the change touch any source
   file* — at 9 of 12 on repository work with no false positives, and the acceptance test, which
   costs less than the ladder that decides nothing. Generated tests discriminate 4/9 written before
   the change and **ratify a wrong change 6/9 written after it**.
5. ☐ **Language generality** — what in the pipeline is language-specific (item 1 shows: almost
   everything that works) and what generalizes.
6. ☐ **Worktrees / per-task isolation** — overhead and RAM cost against the 32 GB ceiling.
7. ☐ **Verifying the unrunnable** — docs and review output; LLM-as-judge failure modes.
8. ☐ **Honest failure reporting** — the design against v1's zero-tests-claimed-passing defect;
   item 1's no-silent-midpoints rule is its first half.

Scope reference: `RESEARCH_BRIEF.md` §11 lines 808–827. Findings continue the family numbering.
Item 1 took F158–F161; W3 then ran to F212 (complete, 2026-08-20); item 2 took F213–F224; W11
then ran to F296 (complete, 2026-08-22), and **item 3 was answered inside W11 item 4 (F270–F284)**;
item 4 took **F297–F310**, so the next free number is **F311**. W11 item 5 (F285–F296) handed item 4
a second headroom result and item 8 its anti-pattern. The numbering is one sequence across all
workstreams — check the maximum before adding, not the last number in this file
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
| OQ-W6-2 | Does `critic_inflation` ship as a console metric now that the check is always on? | **answered** in W11 item 4 recommendation 4: no — the quantity does not exist once the verdict has no score. Four replacements, all computable from the log |
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

---

# Item 4 — verification headroom

## Question

§11's scope: *"Automated verification is the biggest lever on cheap-model output quality: type
checks, linters, unit test generation, property-based testing, static analysis, sandboxed
execution. **Quantify the headroom over V1's syntax-error auto-retry** plus periodic frontier
review."*

Two halves, and the second is worthless without the first. **What is v1's baseline, on the path it
actually runs?** And then: **for each instrument, does its verdict move between work the suite's own
verifier accepts and work it rejects, and what does it cost?**

The frontier-review half of the baseline is already answered and is not repeated here: v1's
periodic reviewer reads the model's narration rather than the file (W11 item 1, F232), scores a
zero as a five (`result.score || 5`, F233), and W11 item 4 measured what a reviewer is worth as a
function of what it is shown (F280–F282). This item is about the deterministic half.

## Method

Two populations, both already in this repository, and ground truth that is a program rather than an
opinion.

- **Constructed** — for each of the three K tasks, the unfixed fixture, the reference solution and
  the shipped sham. 9 trees, truth by construction and re-measured.
- **Real** — every preserved agent workdir under `runs/`: **54 K cells** (repository bugfixes,
  16–20 files, from the K model comparison and the W11 budget sweeps) and the Rust and Python half
  of the **Q56** cells (small single-function tasks — v1's own workload shape). These are the
  mistakes a local model actually made, not mistakes chosen to be interesting.

Each rung runs on a fresh copy of the tree and returns `green | red | error` plus its wall clock.
The oracle is `verify.sh`, re-run here rather than read off the record. Spike:
`research/spikes/w6-headroom/`.

The v1 baseline was read from `agent-battle-command-center` HEAD `d5528ea`, 2026-08-22, with
[[verify-claims-against-code-not-docs]] 19 applied throughout — **grep the readers**. Three of this
item's five baseline findings are about who calls something, not about what it does. Its
`/run-validation` rule is six lines long, so it was reimplemented and run rather than reasoned
about.

## Inherited

| What | Source | Verdict here |
|---|---|---|
| `validate_syntax` as the pre-write check | v1 `tools/code_validation.py` | **DISCARD** — it is on the wrong agent's tool list (F297) |
| `validationCommand` + the `"PASS" in stdout` rule | v1 `main.py:571` | **DISCARD** — no real instrument can satisfy it (F298) |
| The four-phase auto-retry ladder | v1 `autoRetryService.ts` | **DISCARD as a baseline** — the live path is the async one, and its retry queue's only caller is a benchmark script (F299) |
| Linters and type checkers as gate inputs | §11's own list | **DO NOT GATE** — zero yield here, and their delta form is anti-correlated with correctness (F300, F301) |
| Sandboxed execution | §11's own list | **KEEP, and read the output** — the exit code alone catches only the crash (F303) |
| The repository's own test suite | Claudette `tools/quality.rs:344` | **KEEP as a regression guard, not as an acceptance test** — green on every tree here (F300), and the inherited detector does not even fire (F304) |
| Generated tests | BCF's TESTER stage (item 2, F216) | **KEEP, before the change only, and never as a veto** (F305) |
| Property-based tests | §11's own list | **KEEP where an invariant is written down** — the ceiling is 2 of 3 (F306) |

## Findings

### 🚨 F297 — v1's syntax pre-check is given to the agent that does not write code, and prescribed to the agent that cannot call it

`ValidateSyntaxTool` is real, it works, and it does what it says: it writes the candidate to a temp
file and runs `python3 -m py_compile` on it (`tools/code_validation.py:16-93`, the validator table
at `:28`). Then:

- **`CODER_TOOLS_HTTP` does not contain it** (`agents/base.py:58`). `QA_TOOLS_HTTP` does, with the
  comment `# QA gets validation tool` (`:59`).
- **The coder's persona instructs it to use it anyway.** `coder.py:42-46` carries a block headed
  `**Workflow with validation:**` whose step 2 is `validate_syntax(code, language) → Check result`
  and whose step 4 is *"If error → Fix syntax → Repeat step 2"*. The tool is not in its list.
- The same persona's own worked examples skip the step: all three `MISSION SUCCESS EXAMPLES` go
  `file_write` → `shell_run` → done (`coder.py:60-75`).

So the check exists, is advisory where it exists, and is on the wrong agent. This is the
[[verify-claims-against-code-not-docs]] 18 shape — a feature present at every layer but the last —
with the twist that the layer it is missing from is the *tool list*, while the prompt telling the
model to call it is intact.

### 🚨 F298 — v1's validation channel cannot carry a linter, a type checker or a test run: 16 replays, 2 passes, and both of them are blind

`POST /run-validation` (`agents/src/main.py:513-589`) does two things to a `validationCommand`:

1. **Dispatch.** `first_word in ("go","php","python","python3","node","tsx")` → `shlex.split`;
   otherwise, for `language == "python"`, the whole string is wrapped as `python3 -c "<command>"`
   (`:534-541`). There is no shell.
2. **Success.** `success = result.returncode == 0 and "PASS" in result.stdout` (`:571`).

Reimplemented verbatim (`v1_channel.py`) and run against the K task's reference solution and its
shipped sham:

| candidate | v1 says | exit | what actually happened |
|---|---|---|---|
| `python3 -c "import run; print('PASS')"` | **PASS** | 0 | `PASS` — on **both** artifacts |
| `ruff check .` | FAIL | 1 | `SyntaxError: invalid syntax` — wrapped into `python3 -c` |
| `mypy .` | FAIL | 1 | `SyntaxError: invalid syntax` |
| `pytest -q` | FAIL | 1 | `Traceback ... NameError` |
| `python3 -m ruff check .` | FAIL | 1 | the linter ran and reported findings |
| `python3 -m mypy .` | **FAIL** | **0** | `Success: no issues found in 13 source files` |
| `python3 -m pytest -q` | **FAIL** | **0** | `24 passed in 0.26s` |
| `python3 run.py data/jobs.json` | **FAIL** | **0** | the correct report, in full |

**A clean type check, a green test suite and a correct program run are all scored as validation
failures**, because none of them prints the word PASS. In v1 that verdict is not inert: it is what
feeds the retry ladder, so the model is handed its own correct output as an error and told to
*"Fix the error shown above. Rewrite the ENTIRE file"* (`autoRetryService.ts:362-364`).

The two passes are the same command, and it passes the sham as readily as the reference solution —
it imports the module and prints a constant. That is not an accident of this probe: **all 40 of
v1's benchmark validation commands have that shape**, bare Python snippets ending in
`print('PASS')`, none of them starting with a language binary
(`scripts/ollama-stress-test-40.js`, 40/40 counted). The rule and the corpus were built for each
other.

Two consequences for 2.0, and they are cheap: **a verifier's contract is an exit code, not a magic
word on stdout**, and **the thing that decides pass/fail must be able to express "run the project's
own suite"** without the operator wrapping it in `&& echo PASS`.

### 🚨 F299 — on default settings the ladder does not run: validation is fire-and-forget after the task is already done, absence of a command is scored a pass, and the retry queue's only caller is a benchmark script

`taskExecutor.ts:54-57` constructs the sync `AutoRetryService` **only if async validation is
absent**, and `index.ts:119-121` enables async validation unless `ASYNC_VALIDATION_ENABLED` is
explicitly `'false'`. So the default live path is `AsyncValidationService`, and the four-phase
ladder in `autoRetryService.ts` — the one `CLAUDE.md` documents and the brief names — is the dead
one.

On that live path:

- `validateInBackground()` is **fire-and-forget** and is called *after* the agent is released
  (`asyncValidationService.ts:145-166`, `taskExecutor.ts:207`). The task is recorded complete
  before anything is checked.
- **No `validationCommand` → `passed: true`**, under the comment `// No validation command —
  auto-pass` (`:371-381`). The sync path does the same thing with `validated: true, phase:
  'skipped'` (`autoRetryService.ts:80-83`), and its caller treats that as success
  (`taskExecutor.ts:119-131`). This is F161's disease — parse-failure-defaults-to-success — in its
  third donor location.
- A failed validation goes into an in-memory `retryQueue` that is drained only by
  `startRetryQueue()`, whose **single caller in the entire product is an HTTP route**
  (`routes/validation.ts:66`). The UI's API client defines `validationApi.startRetry`
  (`client.ts:659`) and **nothing in the UI calls it**. The one caller that does is
  `scripts/ultimate-100-task-test.js:2864`.

And when the ladder does run, the code it shows the model is located by regexing the task
*description* for `tasks/<name>.<ext>` and reading that one file out of a hardcoded `tasks/`
directory (`autoRetryService.ts:320-331`). On any repository task the regex misses, `failedCode` is
`''`, and the retry prompt says *"rewrite the ENTIRE file"* without naming one.

So the honest baseline for 2.0's target workload — repository work, no operator-authored validation
command — is **nothing at all**: the task completes, is auto-passed, and no instrument runs. §11's
"quantify the headroom over v1's syntax-error auto-retry" has the answer that the thing to beat does
not fire. That is the same shape as W11 item 5's baseline finding (F285), and it is why the rest of
this item measures instruments against a verifier rather than against v1.

### 🚨 F300 — the deterministic ladder above the syntax check is silent: six rungs, 63 trees, not one verdict that moves with the truth

Every rung on both populations, `green`/`red` against what `verify.sh` says:

| rung | constructed (6 FAIL / 3 PASS) | real K (12 FAIL / 42 PASS) | median ms | reads? |
|---|---|---|---|---|
| `syntax` (v1's rung) | green on all 9 | green on all 54 | 135 | **identical** |
| `ruff` | red on all 9 | red on all 54 | 78 | **identical** |
| `ruff --select ALL` | red on all 9 | red on all 54 | 80 | **identical** |
| `mypy` | green on all 9 | green on all 54 | 1,519 | **identical** |
| `mypy --strict` | red on all 9 | red on all 54 | 1,534 | **identical** |
| `pytest` (the repo's own suite) | green on all 9 | green on all 54 | 692 | **identical** |
| `entrypoint` (run the ticket's command) | 1 of 6 wrong | **4 of 12 wrong, 0 of 42 right** | 93 | differs |
| *the acceptance test* | 6/6, 3/3 | 12/12, 42/42 | **1,081** | — |

Six rungs × 63 trees = 378 runs in which **the instrument's verdict is a constant**. The linter and
strict typing are red on the reference solutions and on the fixtures themselves; `mypy` and the
existing suite are green on the shipped shams. The six rungs together cost **4.0 s** per tree and
decide nothing; the acceptance test decides the question in **1.1 s**. The instrument that reads is
cheaper than the ladder that does not.

This is not a claim that linters and type checkers are worthless. It is a measurement of **which
failure class this workload produces**: every K fixture ships a green test suite over a wrong
program (the T1 fixture's 24 tests assert that `cancelled` is in `ALL`, is terminal and is reachable
in `TRANSITIONS`, and assert its dashboard label and its notification text — and not one asserts
what the four consumers that make *decisions* do with it), and every wrong answer is syntactically valid,
type-clean code that does the wrong thing. A rung that cannot see behaviour cannot see these
defects — and the local model's real mistakes, measured below, are not the kind a linter catches
either.

### 🚨 F301 — the delta form is worse than useless: it fires on correct work and never on wrong work

An absolute lint gate is meaningless on a repository that is already red — all three K fixtures are.
The standard fix is to gate on the *delta*: findings the change added. Measured, against the
unfixed fixture's finding multiset:

| rung | added findings & the verifier FAILED | added findings & the verifier PASSED |
|---|---|---|
| `ruff` | **0 / 12** | 7 / 42 |
| `ruff --select ALL` | 1 / 12 | 11 / 42 |
| `mypy --strict` | **0 / 12** | **32 / 42** |

A strict-typing delta gate on this population blocks **76% of the correct changes and 0% of the
wrong ones**. The mechanism is legible in the data: the added findings are
`tests/test_jobs.py::no-untyped-def` ×7, `tests/test_jobs.py::no-untyped-call` ×16 — the agents that
passed **wrote tests**, and every new test function is a new strict-mode finding. One passing cell
added 18 findings by leaving a scratch file, `_analyze_tmp.py`, in the tree.

The delta is measuring how much work was done, and doing the job properly is what trips it.

### 🚨 F302 — what the failures actually are: of 54 real attempts, exactly one was a substantive change that was substantively wrong

The instrument that fires is the cheapest one available, and it is not on §11's list. `residue.py`
walks the tree and compares it to the fixture:

| deterministic check | fires on FAIL | fires on PASS |
|---|---|---|
| the change touched **no source file at all** | **9 / 12** | **0 / 42** |
| the change touched fewer source files than the reference solution does | 10 / 12 | 0 / 42 |
| the change left a new source file behind (`_analyze_tmp.py`) | 1 / 12 | 10 / 42 |
| the change edited an existing test | 0 / 12 | 5 / 42 |
| no test was added or changed at all | 12 / 12 | 37 / 42 |

The specificity of the first row is partly tautological — an empty change cannot pass a behaviour
verifier — and that is exactly why it is worth stating: **the veto is free, it cannot be wrong, and
it catches most of this population.** The informative number is the recall. Taxonomising the 12
failures by hand:

- **2** are not behavioural failures at all (F308).
- **9** of the remaining 10 changed **no source file**: 4 left the tree byte-identical to the
  crashing fixture, 5 left it identical to a fixture that runs and lies.
- **1** is a partial change: `w11-b12-r2` fixed `jobs/charges.py` and `jobs/sla.py` and left
  `summary.py` and `retry.py` alone — two of the four sites.

So on 54 real attempts by two local models, **one** produced code that was substantively wrong in a
way any of §11's instruments would need to reason about. Everything else either did the work, or did
not do it. That reframes the headroom question: the thing a gate on this workload must catch is
mostly **work that did not happen**, and the check for that is a directory walk. It also names the
one that is left — a change that lands at some of the sites and not all of them — which is precisely
the regime W11 item 4 measured a Judge in (11/12 reading the diff, F280) and precisely what F290
asked item 4 for: a coverage fraction. The site list that fraction needs is what the Plan phase
produces.

### F303 — sandboxed execution buys one failure class if you read the exit code, and a different one if you read the output

`entrypoint` runs the command the ticket itself names (`python3 run.py data/jobs.json`) and believes
the exit code. It is the only §11 rung with any yield: **4 of 12** real failures, **0 of 42** false
fails, 93 ms. All four are `trace_dropped_samples` trees left at the crashing fixture — the rung
catches the crash and nothing else.

What it misses is more interesting than what it catches. On `round_at_the_line_not_the_total` the
unfixed program **prints its own defect** — eight `linesum_mismatch` lines naming the invoices, then
eight `export_mismatch` lines — and **exits 0**. The reference solution prints `AUDIT clean`. The
information needed to fail that tree is on stdout, free, with no test written and no model called;
the exit code discards it.

So "sandboxed execution" is two instruments wearing one name. Running the program is nearly free and
catches crashes. *Reading what it printed* is the acceptance test, and it is the one that decides.

### F304 — the inherited build+test gate does not fire on 3 of 3 of this project's own repository tasks

Claudette's `run_build_and_tests` — the deterministic gate item 2 said to inherit — starts with
`detect_framework(dir)`, and returns `ran: false, build_ok: None, tests_ok: None` with the summary
*"no test framework detected (no Cargo.toml / package.json / pyproject.toml / go.mod)"*
(`tools/quality.rs:344-373`).

None of the three K fixtures carries any of those four marker files. All three carry a `tests/`
directory with a pytest suite that runs green in 0.3 s. So on 100% of 2.0's own repository corpus
the inherited gate reports `Uncertain`, correctly and uselessly.

Item 2's rule holds up — `Uncertain` loses every comparison it enters, so nothing is silently
passed — but the detector is wrong: **the marker file is a proxy for a test suite, and the test
suite is right there.** 2.0's Measure phase should detect by looking for what it intends to run
(a `tests/` directory, a `test_*.py`, a `#[cfg(test)]`), and fall back to the marker file, not the
other way round. Note also that this gate is skipped outright under `--offline`
(`quality.rs:352-362`) — deliberately, and advisory, but it means an air-gapped run has no
deterministic half at all.

### 🚨 F305 — a generated test is worth something, and *when* it is written decides what it is worth: 4/9, 9/9, and 6/9 in the wrong direction

The champion writing a pytest file, three tasks × three reps per arm, scored red-red-green against
the unfixed tree, the sham and the reference solution (`gentests.py`):

| arm | what it was shown | discriminates | false-fails the reference solution | passes the sham | empty payload | median wall |
|---|---|---|---|---|---|---|
| **tdd** | the ticket and the repository, no change yet | **4/9** | **4/9** | 0/9 | 1/9 | 84 s |
| **posthoc** | the same, plus the diff of the **correct** change | **9/9** | 0/9 | 0/9 | 0/9 | 58 s |
| **posthoc_sham** | the same, plus the diff of the **wrong** change | 2/9 | **3/9** | **6/9** | 1/9 | 56 s |

Read from the top:

1. **Generated tests are a much stronger instrument than generated acceptance criteria.** W11 item 3
   found 5 of 35 generated *criteria* discriminated (F279) and all 5 fell to a comment. Here the
   worst arm is 4 of 9 and the best is 9 of 9. A test executes; a criterion greps.
2. **🚨 As a veto, a TDD-time generated test blocks correct work 4 times in 9.** Both mechanisms are
   the same: the test over-specifies past the stated invariant. On `finish_the_cancelled_status` it
   asserted a cancelled job may *never* breach its SLA, where the specification says only that its
   clock stops — so a job that was already late when it was cancelled is a breach, the reference
   solution keeps it as one, and the test fails it. On `trace_dropped_samples`, 3 reps out of 3
   demanded that `stats.summarise` survive an empty window, which is the *symptom*; the reference
   solution fixes the cause four modules upstream so that the empty window never occurs, and
   `config.STRICT_EMPTY_WINDOWS = True` says an empty window is an error rather than a hole. The
   generated test encodes the crash site as a requirement — which is the wrong answer this task was
   built to punish.
3. **The post-hoc arm's 9/9 is not a better instrument; it is a different one.** It was shown the
   correct diff. A test written from a diff measures the diff — which is why the third arm exists.
4. **🚨 Shown a wrong diff and asked for tests, the same model ratifies the wrong answer 6 times in
   9 and rejects the right one 3 times in 9.** On `trace_dropped_samples` all three reps do both at
   once: green on the sham, red on the reference solution. This is the shape of "have the coder add
   tests for its change", and it is a gate that certifies whatever it was shown.
   The exception is instructive. On `round_at_the_line_not_the_total` the sham is a change that
   *misdescribes itself* — it rounds the invoice total up and its own docstring claims the total is
   *"never below the sum of the printed lines"*, which is false for some invoices under it. The
   generated test asserted the claim and failed the sham 2 of 2. So a post-hoc test catches a change
   that lies about itself and ratifies one that is honestly partial — the same asymmetry W11 item 4
   found in the Judge's inputs, where the dangerous completion report was the *true* one (F281).
5. Two of the 27 generated files were output-budget stops rather than verdicts: one
   `finish_reason: length` with `completion_tokens: 8192` and an **empty** payload, and one
   truncated mid-file that pytest could not collect. That is W11 item 4's
   `Uncertain(OutputBudgetOverrun)` (F282) on the generating side, and the empty one happened on a
   prompt that had produced a working test file on the previous rep at temperature 0.

### F306 — the property-test rung's ceiling is 2 of 3, and the miss is a property that quotes the module's own docstring

Priced at the ceiling rather than the average: the invariants a competent engineer writes with the
repository's documentation open and no sight of the reference solution, each quoted in its own
docstring from a sentence already in the fixture (`properties.py`).

| task | invariant | verdict |
|---|---|---|
| `finish_the_cancelled_status` | *"Nothing should be waiting on it, charging for it as if it were still going, or retrying it"* (`status.py`) + *"a status that lands in `other` is a status nobody looks at"* (`summary.py`) | **discriminates** — unfixed 4 failed, sham 3 failed, refsol 4 passed |
| `round_at_the_line_not_the_total` | *"it must hold for every invoice we issue"* (`invoice.reconciles`) | **discriminates** — 1 failed on unfixed and on the sham, 2 passed on the refsol |
| `trace_dropped_samples` | *"A silent drop here is the worst failure mode this pipeline has"* (`ingest.py`) → every record is kept or counted | **green on all three** |

The third is the interesting one. The property is correct, it states the exact failure mode the
module's own docstring names, and it holds before and after the fix — because the lost data was
**not silently dropped**. Rev B firmware emits `OK`/`WARN` upper-case, the flag comparison is
case-sensitive, and half the fleet is discarded into `drops["bad_flag"]`, counted, printed, and
reconciled. The accounting is right and the data is gone.

So the rung is worth building where an invariant is written down — two of three tasks here, at a
cost of one file each and 1.4 s to run — and the limit is not rigour. It is that a property catches
the invariant you thought to state, at the stage you thought to state it, and a defect that hides
inside a legitimate category satisfies every one of them.

### 🚨 F307 — on 377 small-task attempts in two languages the type checker catches nothing, the repository's own tests catch 11 of 102 with no false positives, and the linter fires on correct work more often than on wrong

The K population is repository work. The Q56 population is the other shape — 56 single-function
tasks, which is v1's own workload — and it is big enough to stratify. The Rust and Python halves
(29 tasks, **377 preserved attempts**, 102 of them failures) through the same ladder:

| language | rung | red on FAIL | red on PASS | median |
|---|---|---|---|---|
| Rust (182 cells) | `cargo check` — the type check *is* the build | **0 / 59** | 0 / 123 | 193 ms |
| | `cargo clippy -D warnings` | 8 / 59 | **7 / 123** | 236 ms |
| | `cargo test --lib` — the crate's own visible tests | **8 / 59** | **0 / 123** | 487 ms |
| Python (195 cells) | `py_compile` — v1's rung | **0 / 43** | 0 / 151 | 90 ms |
| | `ruff` | 8 / 43 | **29 / 151** | 73 ms |
| | `mypy` | **0 / 43** | 0 / 151 | 991 ms |
| | the fixture's own test file | **3 / 43** | **0 / 151** | 645 ms |

Read across both populations — **431 real agent attempts, 114 real failures**:

- **A type check caught 0 of 114**, in a dynamically typed language and in a statically typed one.
  `cargo check` is green on all 182 Rust attempts including all 59 wrong ones. The most likely
  reason is that a compile error is visible to the agent *inside its own loop* and is fixed there,
  so nothing is left for a gate — the rung is consumed before the gate sees the tree. The
  transcripts cannot confirm that directly (Claudette narrates file mutations only, W1 F91), but
  whatever the mechanism, the measurement stands: **by the time work reaches a gate, it compiles.**
  The same argument covers v1's syntax rung, which caught 0 of 114.
- **The repository's own tests caught 11 of 114, and false-failed 0 of 316 correct trees.** They are
  worth running and cannot be the acceptance test: 8 of 59 in Rust, 3 of 43 in Python, 0 of 12 on
  repository work.
- **A linter carries no information about correctness in either language.** `ruff` is 8 of 43 wrong
  against **29 of 151 right** — on the Python half a lint gate blocks nearly a fifth of the correct
  answers to catch a fifth of the wrong ones. `clippy -D warnings` looks better on the raw split
  (8 of 59 against 7 of 123) and is not: its reds are concentrated in three tasks, they are style
  complaints — *"this `if` statement can be collapsed"*, *"manual implementation of an assign
  operation"* — and **the identical lint fires on the passing and the failing version of the same
  line**. `Q08` passing is `result = result + terms[k + 1]`; `Q08` failing is
  `result = terms[k] + result`; clippy flags both, at `src/eval.rs:61:28`, with the same message.
  What it is measuring is which cells used a particular idiom. Its 8 reds are also **disjoint** from
  the 8 `cargo test` finds, which is what a coincidence looks like.
- Ground truth reproduced on **376 of 377** cells, which is also a re-validation of the Q56 corpus.

The 377th is the best single illustration in this item. `Q13/deny-first-edit` is a Python attempt
whose solution **loops forever** on an input the fixture's own test never supplies. Every cheap
rung is green on it — `py_compile`, `ruff`, `mypy`, and the shipped test file all pass — and the
acceptance test never returns: 300,137 ms, killed by the bound, no `RESULT:` line. One tree in 431
hangs the only instrument that can see it, and it is green on every instrument that cannot. That is
the case F220's plumbing exists for, and it is why a timeout has to be a classified outcome rather
than an absent one.

### 🚨 F308 — two of the twelve K "failures" are the verifier asserting a print format the ticket never mentioned, and one of them is the champion's only loss in the K comparison

`k-champ-r1` and `w11-b40-r2` on `finish_the_cancelled_status` are recorded FAIL. Re-run here, both
produce:

```
COUNTS queued=2 running=2 done=11 failed=5 cancelled=4
SLA breaches 2          CHARGES total 37615.00p across 13 job(s)          RETRY candidates 7
```

Every one of the four consumer decisions is correct, and identical to the reference solution's.
Both agents replaced `"other"` with `"cancelled"` in `summary.BUCKETS`; the verifier requires the
literal `other=0` to still be printed, and the ticket says nothing about the output format (unlike
the other two K tickets, which both say *"do not change the output format"*).

Two consequences, and they point in different directions.

- **For W1.** `research/W1-models.md:722` reads the K comparison as showing *"the champion's own
  verdicts are unstable (`finish_the_cancelled_status` failed once and passed twice on identical
  inputs)"*. The verdicts were unstable; the **behaviour was not**. All three cells fixed all four
  consumers; one of the three also tidied the bucket list, and that is what the verdict recorded.
  The conclusion (keep the champion) is unaffected and if anything strengthened — but "unstable
  verdicts" should be read as instability in an unstated format detail, not in the fix.
- **For W6.** This is the acceptance test's own failure mode, and it is the mirror of F305's: an
  acceptance test that asserts on output detail the ticket never fixed **manufactures failures**,
  exactly as a generated test that over-specifies does. The only instrument that reads behaviour is
  also the only one that can be wrong in a way that costs a correct answer, and the discipline that
  keeps it honest is the corpus's own rule — assert what the ticket asked for, and add positive
  controls for what must *remain* true.

### F309 — three of five timed-out K attempts had already produced a tree that passes

The five K cells recorded `status: timeout` carry no verdict at all — a timeout records no metrics
(`corpus/suites/k/tasks/finish_the_cancelled_status/task.toml`, the 900 → 2400 note). Running the
verifier over the workdirs as they were left: **three PASS, two FAIL**.

The split is exactly along W1's F91. The two that fail are the `trace_dropped_samples` cells F91
already dissected — untouched workdirs, forty minutes in a read-only tool loop, no bytes on either
pipe. The other three (`k-27b-r1` on both of the other tasks, `k-27b-r2` on `trace`) had **finished
the work**: the tree on disk passes the four-consumer verifier, and the deadline threw the result
away.

So a wall-clock deadline does not merely mismeasure, it **discards finished work** — 3 of 5 here.
That is W11 item 5's F290 from the other side, and it makes F91's fix only half a fix: sealing the
transcript records that the subject was silent, and the thing worth recording is that the *tree was
correct*. The cheap version is one line of policy — **on a kill, run the gate on the workdir before
discarding the cell** — and it would have shipped three of these five.

### F310 — corpus hygiene, found by reusing the corpus: the verifier leaves its answer key in the workdir

Every preserved Q56 workdir contains the hidden tests the verifier wrote into it during the original
run (`tests/hidden_gate.rs`, `hidden_gate_test.py`). Any post-hoc instrument that runs "the
project's tests" over those workdirs is running the oracle and will report a perfect gate. The probe
here measures the residue instead of guessing it — it runs the verifier against a pristine fixture
and diffs the tree (`instruments.verifier_residue`) — and deletes exactly those paths before any
rung runs.

Two smaller ones from the same pass: the K `refsol`/`sham` overlays are CRLF where the fixtures are
LF, so any byte-level diff of an overlay reports every line of every touched file as changed; and
the Q56 verifiers take the transcript as a **required** second argument, so calling one with `""`
produces no `RESULT:` line at all — which is indistinguishable, at the call site, from a verifier
that ran and could not decide.

## Options compared

Every instrument this item ran, priced on the same two axes — what it catches on real agent output,
and what it costs to be wrong.

| instrument | cost | catches, on 54 real K attempts | false-fails correct work | verdict |
|---|---|---|---|---|
| `py_compile` (v1's rung) | 135 ms | 0 / 12 | 0 / 42 | keep, it is free; expect nothing |
| `ruff` | 78 ms | 0 (red on everything) | **42 / 42** | **not a gate** |
| `ruff --select ALL` | 80 ms | 0 (red on everything) | **42 / 42** | **not a gate** |
| `mypy` | 1.5 s | 0 / 12 | 0 / 42 | not a gate here; language-dependent |
| `mypy --strict` | 1.5 s | 0 (red on everything) | **42 / 42** | **not a gate** |
| lint / type **delta** | +1 walk | 0–1 / 12 | 7–32 / 42 | **worse than useless** (F301) |
| the repository's own suite | 692 ms | 0 / 12 | 0 / 42 | **regression guard, not acceptance** |
| run the ticket's command, read the exit code | 93 ms | 4 / 12 | 0 / 42 | keep — it catches crashes |
| **the structural check** (no source file touched) | one walk | **9 / 12** | **0 / 42** | **keep, first, free** |
| the acceptance test | 1.1 s | 12 / 12 | 2 / 42 by over-assertion (F308) | **the gate** |
| a generated test, written before the change | 84 s GPU | discriminates 4/9 | **4/9** | advisory only |
| a generated test, written after the change | 56 s GPU | ratifies the change 6/9 | 3/9 | **never** |
| a property test, at the ceiling | 1.4 s | 2 of 3 tasks | 0 | keep where an invariant is written |

## Recommendation

**1 — Order the Measure phase cheapest-first, and make the first rung structural.** Before any
toolchain runs: is the diff empty? did it touch any source file? did it touch the sites the Plan
phase named? On this corpus that single walk accounts for **9 of the 10 behavioural failures**, at
no cost and with no possibility of a false positive — an empty change cannot pass a behaviour
verifier. This is item 2's recommendation 1 (empty diff is a veto) with a number attached, and it is
the coverage fraction F290 asked this item for. Its denominator is the site list, which means
**Localize has to emit one** — a requirement on item 2's phase 1, not a new phase.

**2 — The acceptance test is the only `Measured` input; everything else is advisory or a veto.**
Nothing in the deterministic ladder above `py_compile` moved with the truth on 63 trees. The
instrument that decides is the one that executes the program and asserts on the behaviour the ticket
asked about — and it costs less than the ladder that decides nothing (1.1 s against 4.0 s).

**3 — Run the repository's own suite, and call it what it is.** It was green on all 63 trees here,
including every wrong one, so it cannot *accept*. It can still veto: a change that breaks a test
that passed before is a regression, which is a different question from whether the ticket is
done. Detect the suite by **looking for tests** (`tests/`, `test_*.py`, `#[cfg(test)]`) rather than
for a marker file — the inherited detector finds no marker in 3 of 3 of this project's own fixtures
and reports `Uncertain` where a runnable suite is sitting in plain sight (F304).

**4 — Do not gate on a linter or a type checker, in either form.** Absolute: red on the fixtures
themselves. Delta: fires on 32 of 42 correct changes and 0 of 12 wrong ones, because writing tests
is what adds findings (F301). Keep them exactly where the successor already keeps them — as tools
the model may call (`tool_groups.rs:135`) — and off the gate.

**5 — Generated tests are advisory, are generated before the change, and never bind.** 4 of 9 TDD-time
files discriminated and 4 of 9 would have blocked the reference solution; a file generated *after* a
change ratifies that change 6 times in 9. So: generate at Localize time, show the result to the
Judge and to the human, and let a human promote one into the acceptance set. Never let one veto, and
never generate one from the diff. **This answers OQ-W6-6**: a returning TESTER artifact must be
immutable to the Change phase *and* non-binding on the gate, because at 4/9 false-fails an immutable
binding artifact is a machine for rejecting correct work.

**6 — Property tests where the repository states an invariant.** Two of three K tasks have an
invariant written in a module docstring or in `docs/`, and in both cases a property over it
separates the reference solution from the sham for 1.4 s. The third shows the limit and it is not
laziness: the drop accounting was *correct* while the data was gone (F306). So the rung is worth its
cost, and it is not a substitute for an acceptance test.

**7 — A verifier's contract is an exit code and a stream, never a magic word.** v1's channel scores a
clean type check, a green suite and a correct program run as failures because none of them prints
`PASS` (F298). 2.0's measurement interface takes `Measured(exit_code, stdout, stderr)` and lets the
task's own criterion decide.

**8 — Kill the tree, bound the wait, classify the timeout.** This item's own harness reproduced F220
in the wild: a Q56 verifier's `pytest`, running an agent solution that spins, was orphaned by a
`subprocess.run` timeout, held the stdout pipe open, and stalled the run for 22 minutes with no
output. `common.kill_tree` is the two-line version of W3 item 7's job-object seam. Anything 2.0
executes on behalf of a model needs it, and a timeout has to come back as
`Uncertain(timeout, partial_output)` rather than as an exception or a zero.

## Rejected alternatives and why

- **"Add a linter to the gate; cheap insurance."** Measured: it is not insurance, it is a tax on
  correct work. Every K fixture is already red under `ruff` and under `mypy --strict`, and the delta
  form fires on the changes that *did the job*. The only version that would work is a baseline-diffed
  gate scoped to the touched hunks, which is a lot of machinery to catch a failure class this corpus
  does not contain.
- **Treating "the repository's tests pass" as acceptance.** The T1 fixture ships 24 tests that assert
  `cancelled` is in `ALL`, is terminal, is reachable in `TRANSITIONS`, and has a dashboard label —
  and not one that asserts what the four consumers that make decisions do with it. Green suite,
  wrong program, and the sham passes too.
- **Having the coder write tests for its own change.** This is the shape most agent frameworks reach
  for, and it is the worst arm measured here: 6 of 9 ratify a wrong change, 3 of 9 reject the right
  one. It is F281's asymmetry in test form — the tests catch a change that misdescribes itself and
  bless the one that is honestly partial.
- **A second model as the deterministic half.** Priced in W11 item 4 (F284): 26.3 s round trip, 4.6×
  the decode, and no verdict at all on the correct answer 3 of 3. Nothing in this item changes that.
- **Quantifying headroom "over v1's auto-retry" as a rate.** There is no rate to beat. On defaults
  the ladder does not run, absence of a validation command is scored a pass, and the retry queue's
  only caller is a benchmark script (F299). The honest baseline is zero, so the numbers here are
  reported against the suite verifier instead.

## Effect on fun

The measurement that matters is also the one that looks like something. A **structural veto fires in
milliseconds** — before any toolchain, before any model — and it has a line to say: *"nothing was
touched"*, or *"one of four sites"*. That is a unit reporting a fact about the battlefield, and it
is the single most common outcome on real runs, which means the console's most frequent event is an
honest one rather than a spinner.

The coverage fraction is the console object F290 asked for and this item can now size: `1/4 sites`
is a progress bar that means something, unlike a percentage derived from a weighted average. And the
acceptance test's output is *already* dramatic in this corpus — the unfixed billing run prints eight
`linesum_mismatch` lines naming the invoices it got wrong and then exits 0. A console that shows
what the program said beats one that shows `verifier_score: 7.5`, and it costs nothing because the
program printed it anyway.

The rejected half matters for fun too. A linter gate would mean the most common console event is a
red bar over correct work — 42 of 42 here. Nothing kills a command centre faster than an alarm that
is always on.

## Open questions

| # | Question | Waiting on |
|---|---|---|
| OQ-W6-6 | *(from item 2)* Does a generated-test artifact return, and what makes it immutable? | **answered here**: yes, TDD-time, advisory, never binding — 4/9 discriminate and 4/9 false-fail (F305) |
| OQ-W6-8 | Does the coverage fraction bind as a veto, or only as a report? It needs Localize to emit a site list, and the one failure it misses here is a 2-of-4 change | item 5 / W11's Plan phase |
| OQ-W6-9 | Does the picture change in a language whose type checker is the build? Q56's Rust half is the first evidence (F307); node, typescript and shell are unmeasured | item 5 (language generality) |
| OQ-W6-10 | Should the K verifier's `other=0` assertion be relaxed, and what does that do to the recorded K comparison? A corpus change invalidates prior cells, so it is a W8 decision, not a W6 one | W8 |
| OQ-W6-7 | *(from item 2)* Rules-only router, or rules plus a recorded model reading? Does 2.0 scale the bar by complexity? | still open — nothing here bears on it |

## Confidence: high on the negative result, high on the baseline, medium on generality

The negative result is the strongest thing in this item: six instruments over 63 trees produced a
constant, which is not a subtle statistical claim and does not depend on how the population was
sampled. The v1 baseline is line-level and re-checkable, and its most load-bearing part — the
validation channel — was reimplemented and executed rather than read. The failure taxonomy was
hand-checked cell by cell, which is how the two format-only failures were found.

**Medium on generality**, for three reasons, and each has a named next step. The corpus is three
tasks and two model families, so "the local model's mistakes are mostly work that did not happen" is
a claim about *this* subject and *these* fixtures. The languages are Python and Rust; a project in
TypeScript, where the type checker is the build, may well find `tsc` doing real work (OQ-W6-9). And
the generated-test arms are n=3 per task per arm, which is enough to show that TDD-time generation
false-fails often and post-hoc generation ratifies, and not enough to put a confidence interval on
either rate.

One thing this item does **not** show: that verification is a weak lever. It shows that the *cheap
deterministic* rungs above a syntax check are a weak lever **on this failure distribution**, and
that the levers which do move — a structural check on the change, and an acceptance test that
executes the program — are the two the donors both skipped.
