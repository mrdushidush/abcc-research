# W6 — Verification, gates and the TDD pipeline

**Status: COMPLETE — started 2026-08-19, closed 2026-08-25**, as part of the W3 + W6 + W11 block
(§14 item 4). All eight items answered; F158–F161 and F213–F224 and F297–F359 are this document's.
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
5. ✅ **Language generality** (F311–F324) — measured over the donors' own code, one controlled
   experiment, and **728 real agent attempts in five languages** (item 4's 377, plus the 351 node,
   typescript and shell cells it deliberately skipped). **The scoping question has a smaller answer than it looks:** what is language-specific
   is a *toolchain profile* — extensions, a build command, a test command, a binary path — and the
   expensive part of the donors' abstraction (387 of 1,068 lines in Claudette's `quality.rs`) is
   output parsers keyed to a **tool**, not a language, which item 4's `Measured(exit_code, stdout,
   stderr)` contract deletes. **OQ-W6-9 is answered and its premise was wrong**: a type check catches
   1 of 6 wrong answers where the subject code has a catch-all arm and 4 of 6 where it does not —
   *identically* in Python, TypeScript and Rust — and neither real corpus has a single site where the
   rule could fire (0 of 30 Rust fixtures, 0 `match` statements in the Python ones), which is the
   mechanical explanation for F307. The acceptance test is 5 of 6 in every cell of the grid. Donor
   facts, all executed: v1's five-language syntax table discriminates in **0 of 6** languages on this
   host and its validation channel runs **1 of 13** real commands; BCF scores a perfect Python file
   **5.80** and a language it has never heard of **8.00**, and cannot pass its own gate on a project
   whose extensions it does not know at any complexity; Claudette's npm arm **cannot spawn `npm` from
   a Rust process on Windows at all**, while its health check probes `node`. On the real population:
   a type check caught **0 of 160** failures in five languages, `tsc` false-failed 5 correct answers,
   and on the 280 cells where the agent was left alone **no rung in any language fired on any of the
   29 real failures**. The free structural check has now produced **0 false positives on 609 correct
   trees**, and its yield is a property of the task's shape — 9/12 on repository work against 0/29 on
   clean single-function work — so it goes first because it is free, never because of a rate.
6. ✅ **Worktrees and per-task isolation** (F325–F335) — measured on the four real repositories on
   this machine. **The marker is free and the working directory is not**: a worktree costs
   0.08–0.66 s and 0.8–63.7 MB against 6–136 s and 1.7–25.5 GB to copy the same tree, because the
   difference is not the mechanism but what git ignores. **OQ-W3-12 is answered as a composition** —
   the checkpoint identifier is a commit sha from a temp-index snapshot (`read-tree` / `add -A` /
   `write-tree` / `commit-tree`, 0.16 s, and it captures the files the agent created, which
   `git stash create` **cannot**), isolation is a worktree at that sha (0.25 s), the change list is
   the diff between two snapshots (0.024 s, exactly the six paths), restore is `read-tree -u --reset`
   plus `clean -fd` (0.06 s, byte-exact) — and the sha **must be written to a ref**, because an
   unreferenced snapshot does not survive `git gc --prune=now`. **W11 F249's clause is corrected**: a
   worktree created *after* the build cache is warm compiles one crate in **24.7 s**, not 204 in 57,
   when `CARGO_TARGET_DIR` is shared, and a copied tree with no `.git` gets the same. **The 32 GB
   answer is a policy rather than a number**: two cold builds at once take the box to **2.3 GB free**
   and finish in 110.8 s against 113–135 s in sequence, so *isolate the workspaces and serialize the
   gate*. Donor facts: **no donor ever
   runs two agents against one tree**, and v1's parallel endpoint has no caller; v1's three
   file-locking surfaces all exclude the one agent that writes code; **241 of 539 tracked files in
   the v1 donor differ from their blobs while `git status` reports the tree clean**; and **0 of this
   project's 1,383 measured cells is a git repository**, so the mechanism degrades to `workdir.rs`'s
   copied file plan. OQ-W6-11 answered (F335).
7. ✅ **Verifying the unrunnable** (F336–F348) — measured on two populations that both have an
   answer key: **57 agent trees** on which no deterministic rung in five languages fires (the 29
   real clean-arm failures plus their 34 matched passes, deduplicated by tree content), and **ten
   documents** against the code they describe. **OQ-W6-13 is answered**: the 29 are boundary cases,
   and the axis is not the language but whether the ticket's own words decide the failing input —
   8 of 29 they do, 12 of 29 nothing decides it but the domain, and 2 are not reasoning failures at
   all. **A model verdict is not a gate**: 3 of 23 wrong trees, 1 false fail in 34, and **two of the
   three catches do not survive a change to the output schema**, so `call` is not measuring a
   property of the tree. **What it is, is a report that contradicts itself** — on 14 of 16 trees it
   names the failing input and answers `pass`, and on documents it names the planted falsehood at
   `high` severity and approves the artifact anyway on **every one of the seven that answered**. **The instrument that works is
   execution**: run the reviewer's own `call → expected → actual` and 13 of 15 claims on wrong trees
   really discriminate, catching **10 of 23** against 1 of 34 false — three times the recall of the
   same model's own verdict, from the same call. Demanding that schema is **not** free: 2.8× the
   decode, 2.7× the wall clock and 17 of 57 calls lost to the token cap, every one legibly
   `finish_reason: length`. **The judge has no absolute scale** — 0 of 8 pointwise against **14 of 14
   pairwise** on the same defects, order-stable on 7 of 7 pairs, so the thing to show a judge is the
   *other artifact*, which item 6 produces in 0.16 s. Position bias did not reproduce at all;
   verbosity bias did, weakly, and only on a genuine tie. The free rung for prose checks **addresses
   and nothing else**: 1,873 unique addresses across four corpora, one provably stale citation, 0
   false positives — and **1 of 7 planted document defects**, the one that is an address rather than
   an assertion. It also found that **F22–F29 are cited 23 times in six documents and defined in
   none**. Donor facts, all executed: **BCF cannot pass a documentation project at any complexity**
   (5.00 → 7.00 against a gate of 8.00, and it builds a virtualenv to run pytest over markdown);
   **v1 has no documentation task type** and puts its only prose type, `review`, on
   `SKIP_REVIEW_TYPES`, whose two unit tests both pass for the wrong reason; **v1's frontier review
   tier fires 0 times in 30 all-local tasks** because every multiple of 10 is a multiple of 5; and
   Claudette's `CheckOutcome` refuses to fold a timeout into "clean" and folds *"there is no checker
   for this artifact"* into it three lines later.
8. ✅ **Honest failure reporting** (F349–F359) — measured on the donor chain, on this project's own
   corpus, and on a compiled type. **§11's reading of its own incident is wrong, and that decides the
   design.** On 98 unimpeded Q56 Rust attempts the champion asserted the tests pass 81 times, a test
   really ran **81 of 81**, and re-running the suite on the delivered tree makes **81 of 81 of those
   sentences true** — the seven unbacked claims in the corpus are **7 of 7** in the arms built to block
   the edit, where they are predictions about a patch that was never applied. *And it does not help*:
   **14 of the 81** true, measured, green claims sit on trees the hidden gate fails, **6 of 81**
   measured a tree that no longer existed (the edit lands 1.7–3.0 s after the test binary), and one
   subject wrote seven tests, ran them, **deleted them**, and reported *"all the smoke tests I ran
   earlier passed (7/7)"* with seven ticks over a tree with no tests in it. What prose cannot carry is
   **scope and time**, not truth. Donor facts, all executed rather than read: v1's chain marks **15 of
   16** records *completed* — including the all-red run its own documented fix was written for — and
   the one it stops reports **2 run / 0 passed** on a run of three with one passing; the reason is a
   dispatcher gated on the word `passed`, which an all-red pytest run does not contain, so **eight real
   run-endings become three records** and *every test failed* is indistinguishable from *there were no
   tests*; **the exit status separates all of them** (pytest and unittest both use **5** for "no tests
   collected") and no donor reads one. v1's `UNCERTAIN` exists, is constructed **once**, and sets
   `success=True` in the same literal, and `ExecuteResponse` has no status field at all. The successor
   is the best of the three — `Option<bool>`, order-free parsers, and the only exit-code rung in the
   family — and still returns **`Some(true)` with the line "tests: 0 passed"** for a cargo crate with
   no tests. Found on the way: **a green test run that measured nothing, produced by cargo** — two
   trees holding one package name and one shared `CARGO_TARGET_DIR` make cargo print `Fresh`, run the
   other tree's binary and report `ok. 0 passed` at exit 0, which **qualifies item 6's F331**: share
   the cache for building, never for the gate. The answer is a type, compiled and asserted (17 tests):
   `Measured | Unmeasured(Why)` with eight named reasons, a `Green` that requires **every** declared
   rung to have been measured, and a `Claim` that no function converts into an `Outcome` — and the
   shape already ships here, at **17,648 metric slots, 1,426 of them carrying a sentence instead of a
   number**.

Scope reference: `RESEARCH_BRIEF.md` §11 lines 808–827. Findings continue the family numbering.
Item 1 took F158–F161; W3 then ran to F212 (complete, 2026-08-20); item 2 took F213–F224; W11
then ran to F296 (complete, 2026-08-22), and **item 3 was answered inside W11 item 4 (F270–F284)**;
item 4 took **F297–F310**, item 5 took **F311–F324**, item 6 took **F325–F335** and item 7 took
**F336–F348** and item 8 took **F349–F359**, so the next free number is **F360**. W11 item 5
(F285–F296) handed item 4 a second headroom result and item 8 its anti-pattern (`Ok(())` on
exhaustion, F296, now encoded as `Why::BudgetExhausted`); item 5 handed item 6 the toolchain-profile
question (OQ-W6-11, answered in F335) and item 8 the loud-`Uncertain` requirement (delivered in
F358); item 6 handed item 8 the honest-restore contract (F330) and W3 the checkpoint identifier it
asked for (OQ-W3-12), and item 8 hands item 6's shared build cache back a qualification (F356). The numbering is one sequence across all
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

---

# Item 5 — language generality

## Question

§11's scope: *"BCF reportedly outputs Python only. 2.0 targets more languages. **What in the
pipeline is language-specific and what generalizes?** This is a real scoping question."*

Item 1 gave the short answer — *almost everything that works is language-specific* — and item 4
made it urgent, because the two instruments it kept are the two whose language dependence is least
obvious. A structural check has to know what a source file is. An acceptance test has to know how
to run the program. So the question splits in three:

1. **Where does language enter?** Every site in the three donors where a language name, an
   extension, a marker file or a tool binary is hard-coded, and which layer it sits in.
2. **What does a new language cost?** Given the best abstraction in the family — Claudette's
   four-framework `quality.rs` — what has to be written per language, and what has to be written
   per *tool*, which is not the same number.
3. **OQ-W6-9, the one item 4 left open:** does the picture change in a language whose type checker
   is the build? Q56's Rust half said no (F307, 0 of 59). This item asks it as a controlled
   experiment instead, with the language as the only variable.

## Method

Four probes in `research/spikes/w6-language/`, three of which execute donor code rather than
paraphrase it.

- **BCF's scorer, through BCF's own crate.** `bcf-probe/` takes a path dependency on the pinned
  donor checkout (`d6c1601`) and calls `verifier::verify_file` / `verify_project` on one
  best-possible file per language — nine files, nine languages, every quality signal the scorer
  looks for present in each. BCF's gate is a constant threshold over an average of these numbers,
  so a per-language ceiling is a per-language handicap.
- **v1's two language surfaces, ported verbatim and run.** `v1_channel.py` carries
  `ValidateSyntaxTool._run` (`packages/agents/src/tools/code_validation.py:16-89`, minus the
  `ActionHistory` loop hook) and the `/run-validation` dispatch
  (`packages/agents/src/main.py:524-576`) as byte-for-byte copies, and runs them over valid and
  invalid samples in six languages and thirteen realistic validation commands.
- **Claudette's gate, vendored with citations.** The parts under test are `pub(crate)`, so
  `claudette-probe/` copies `detect_framework`, `run_build_step`, the four count parsers,
  `classify_tests` and `is_hard_fail` verbatim with their line numbers, and drives them with real
  subprocesses over twelve trees — four frameworks × {no tests, green suite, failing suite} — plus
  a polyglot tree. The subprocesses are spawned from a Rust process, which is part of the question.
- **The three languages item 4 skipped, on real cells.** Item 4 ran Q56's rust and python halves
  and left 351 preserved workdirs unmeasured because its ladder had no rungs for node, typescript or
  shell. Those rungs are now written (`../w6-headroom/instruments.py`, and the harness change is part
  of this item), the resumable ladder re-run, and two further passes added: `structural.py`, which
  runs item 4's free structural rung over all 728 Q56 cells and re-runs it over K stratified by arm,
  and `baseline.py`, which runs every rung over the pristine fixture and the reference solution so a
  rung that is red before the change is caught being one (F323).
- **One ticket, three languages, two styles.** `mutants.py` writes the same task — *a fourth
  status exists in the type; make the four consumers agree about what it means*, the K corpus's
  shape — in Python, TypeScript and Rust, in seven candidate answers from "did nothing" to
  "correct", under two styles of subject code: every consumer ending in a catch-all arm, or none.
  42 trees, five instruments each, ground truth by construction.

Toolchain as measured: python 3.14.5 / mypy 2.3.1 / ruff 0.16.4 / pytest 9.1.1, node 24.15.0 with
typescript 5.9.3, cargo 1.95.0. `go` and `php` are **not installed on this host**, which is data
rather than a gap.

## Inherited

| What | Source | Verdict here |
|---|---|---|
| The five-language syntax table | v1 `tools/code_validation.py:27-33` | **DISCARD** — 0 of 6 languages separate valid from invalid code on this host (F311) |
| `LANG=xxx` on the validation command | v1 `asyncValidationService.ts:476-483` | **DISCARD** — the language decides how the command is *mangled*, and 1 of 13 real commands survives (F312) |
| Per-language quality scoring | BCF `verifier.rs:54-60`, `741-765` | **DISCARD the number** — the ceiling is 5.80 for Python and 8.00 for a language BCF has never heard of (F313) |
| Test counts as a pass rate | BCF `verifier.rs:431-510` | **DISCARD** — a Boolean in three of five languages, weighted ±2.0 (F314) |
| Language from the prompt | BCF `mission.rs:343` + `detect_language` | **DISCARD** — a keyword scan with a Python default; a C++ mission writes `main.py` (F315) |
| Marker → command → parser | Claudette `tools/quality.rs` | **PORT the shape, not the parsers** — 387 of 1068 non-test lines are output parsers, and they are per *tool*, not per language (F316) |
| `Option<bool>` for "could not run" | Claudette `quality.rs:317-339` | **KEEP** — it is what makes a missing toolchain survivable, and it is the only reason the npm arm's death on Windows is not a false failure (F317) |
| A type check as a gate rung | item 4's F300 / F307 (0 of 114) | **KEEP the verdict, correct the reason** — the yield is set by the subject code's style, not by the language (F318, F319) |

## Findings

### 🚨 F311 — v1's syntax rung is a five-language table, and on this host it separates valid from invalid code in none of them

`ValidateSyntaxTool` maps a **model-supplied** language string (the tool's own description says
`language (str: python|javascript|typescript|go|php)`, `code_validation.py:13`) to an extension and
a checker. Ported verbatim and run over a valid and an invalid sample in six languages:

| language | valid sample | invalid sample | discriminates? |
|---|---|---|---|
| python | `Syntax error` | `Syntax error` | **no** |
| javascript | `OK` | **`OK`** | **no** |
| typescript | `Syntax error` | `Syntax error` | **no** |
| go | `Validation failed: [WinError 2]` | `Validation failed: [WinError 2]` | no — `gofmt` absent |
| php | `Validation failed: [WinError 2]` | `Validation failed: [WinError 2]` | no — `php` absent |
| rust | `Unsupported language: rust` | `Unsupported language: rust` | n/a — 2.0's own language is not in the table |

Four different mechanisms, and each one is a lesson about what a language binding actually binds to.

- **Python — the binary name is a claim about the machine.** The table's checker is `python3`. On
  Windows 11 `python3` resolves to `WindowsApps\python3.exe`, the Microsoft Store *app execution
  alias*, which spawns successfully, prints *"Python was not found; run without arguments to install
  from the Microsoft Store"* and exits 9009. The tool's own fallback — *"If python3 not available,
  skip syntax check"* — never fires, because the process **did** start. This is **F27**, already on
  the family's record: the Q56 import rewrote all 56 donor verifiers to probe an interpreter *by
  executing it* for exactly this reason (`W8-q56-import.md:186-188`), and every Q56 verifier still
  carries the comment. What is new here is that it also defeats v1's own guard, and BCF's (F313).
  v1 ships in Docker where `python3` is real, so this is not a defect in v1's container; it is what
  the same table does on 2.0's target machine.
- **JavaScript — the extension decides the parser.** The table writes the model's code to a `.js`
  temp file and runs `node --check`. On node 24.15.0, `node --check` **exits 0 on a file that
  contains ESM syntax and a syntax error**, and exits 1 on the identical bytes in a `.mjs` file:

  | content | `.js` | `.mjs` |
  |---|---|---|
  | `function add(a, b) {` … unclosed | exit 1 | — |
  | `export function add(a, b) {` … unclosed | **exit 0** | exit 1 |
  | `import x from "y"; const q = ;;;` | **exit 0** | exit 1 |

  Every modern model writes `import`/`export`, so the rung passes broken JavaScript for the code a
  model actually produces. (Measured on one node version on one platform; not checked elsewhere.)
- **TypeScript — the checker is a JavaScript parser, so valid TypeScript is a syntax error.** The
  table entry is `['npx', '-y', 'tsx', '--help']`, which validates nothing, and a special case at
  `code_validation.py:47-55` replaces it with `node --input-type=module --check`. Fed
  `export function add(a: number, b: number): number`, that returns
  `SyntaxError: Unexpected token ':'`. The rung rejects correct work 100% of the time, and the
  false-fail is indistinguishable from a real one.
- **Go and PHP — an absent toolchain is returned as a string.** `subprocess.run` raises
  `FileNotFoundError`, the blanket `except Exception` at `:76` turns it into
  `"Validation failed: [WinError 2] The system cannot find the file specified"`, and that string is
  the tool's return value. There is no channel for *"I could not measure this"*; the model is handed
  a sentence that reads like a defect in its own code. Claudette's `Option<bool>` (F218, F317) is
  the fix, and it is the whole difference.

Read with F297 — the tool is on the QA agent's list and not the coder's — this is a table nobody
calls, whose one entry that could have worked is broken by the host and whose second is broken by a
file extension.

### 🚨 F312 — the validation channel is not Python-shaped, it is `python3 -c`-shaped: 1 of 13 real commands survives

Item 4 (F298) found that `/run-validation` scores anything that does not print `PASS` as a failure.
Reading the same handler for the *language* question finds an earlier defect: the command is
**rewritten before it runs**. `main.py:534` holds six binaries —
`("go", "php", "python", "python3", "node", "tsx")` — and a command whose first word is not one of
them is wrapped in the language's inline-source flag: `python3 -c`, `node -e`, `tsx -e`, `php -r`,
or, for Go, `go run <the whole command as a filename>`. Ported verbatim and run against thirteen
validation commands a real ticket would carry:

| the ticket's `validationCommand` | what actually executes | verdict |
|---|---|---|
| `pytest -q` | `python3 -c "pytest -q"` | fail |
| `ruff check .` | `python3 -c "ruff check ."` | fail |
| `mypy .` | `python3 -c "mypy ."` | fail |
| `cargo test` (no `LANG=`) | `python3 -c "cargo test"` | fail |
| `cargo test` (`LANG=rust`) | nothing — `Unsupported language: rust` | fail |
| `npm test` (`LANG=javascript`) | `node -e "npm test"` | fail |
| `tsc --noEmit` (`LANG=typescript`) | `tsx -e "tsc --noEmit"` | fail — `tsx` absent |
| `go test ./...` | `go test ./...`, correctly split | fail — `go` absent |
| `node --test` | `node --test`, correctly split | **fail — exit 0, "tests 0", no `PASS`** |
| `python3 -m pytest -q` | itself, correctly split | fail — the Store alias |
| `python -c "… print('PASS')"` | itself | **pass** |
| `python -c "… assert add(2,3)==5"` | itself | fail — correct, silent, no `PASS` |

The one command that works is the shape v1's own QA persona teaches — `python -c "…; print('PASS')"`
in two of its four worked examples (`qa.py:37`, `:55`), which is also the only agent given the syntax
tool (F297). The coder's examples run `python -c` too and print the *result* rather than the word
(`coder.py:57`), so a coder that copies its own persona fails the channel. On a host
where `python3` is real the wrapper's output is worth quoting, because it is what
`buildRetryDescription` (`asyncValidationService.ts:484-500`) pastes into the retry prompt under
*"The validation failed with this error"*:

```
$ python -c "pytest -q"      NameError: name 'pytest' is not defined. Did you mean: 'bytes'?
$ python -c "cargo test"     SyntaxError: invalid syntax
$ python -c "npm test"       SyntaxError: invalid syntax
```

So a Rust task carrying `validationCommand = "cargo test"` sends the model a Python `SyntaxError`
and asks it to *"rewrite the ENTIRE file with the corrected implementation"*. The channel does not
merely prefer Python; **it is an `eval` port, and the only artifact it can carry is an expression in
one of five interpreters.** A verifier's interface has to be a *process* — argv, cwd, exit code, two
streams — and v1's is a string plus a language label.

### 🚨 F313 — BCF's quality number is a per-language handicap: a perfect Python file scores 5.80 and a language BCF has never heard of scores 8.00

Phase 0 already measured this scorer on Python and found a valid and a broken file scoring the same
5.80 (`prestudy/verification.md` §2.2), and item 1 built F158 on it. The question here is the one
nobody asked: **what does the same scorer do to the other four languages, and to a fifth it has
never heard of?**

`calculate_score` (`verifier.rs:741-765`) starts every file at 5.0 and adds fixed amounts for six
Boolean signals — syntax valid +1.5, lint passed +1.0, has tests +1.0, has a docstring +0.5, has
error handling +1.0, hard-coded secrets −2.0. The signals are set by a per-language function
(`verifier.rs:54-60`), and **the languages do not have the same number of signals available**. Run
through BCF's own crate, on one best-possible file per language — every signal present, no secrets,
no TODOs:

| fixture | language arm | score | syntax_valid | has_tests | docstring | error handling |
|---|---|---:|---|---|---|---|
| `best.py` | `verify_python` | **5.80** | **false** | false | false | false |
| `best.ts` | `verify_js_ts` | 10.00 | true | true | true | true |
| `best.js` | `verify_js_ts` | 10.00 | true | true | true | true |
| `best.rs` | `verify_rust` | 10.00 | true | true | true | true |
| `best.go` | `verify_go` | 10.00 | true | true | true | true |
| `best.cpp` / `best.c` | `verify_generic` | 8.00 | true | false | true | false |
| `best.java` / `best.rb` | `verify_generic` | 8.00 | true | false | true | false |

Three things are wrong at once, and they compound.

- **Python's three content signals are dead, and only Python's.** F158 recorded them as dead code;
  the language question shows *why*. `verify_python` spawns a real syntax check and then `return`s
  inside the `if let Ok(output)` (`verifier.rs:675-695`); the three `report.has_*` assignments sit
  **after** that return and run only when the spawn fails. Every other arm sets all four by
  substring poll — `verify_rust` (`:718`) calls a file syntactically valid if it contains `fn `, `struct ` or
  `impl `; `verify_generic` (`:735`) calls it valid if `content.len() > 50`.
- **The one language with a real check is the one the check is broken for.** The checker is
  `python3` (F311's Store alias, F27), so `syntax_valid` is false and a lint issue is pushed for
  *every* Python file, valid or not: 5.0 + 1.0 (lint_passed is still `true`, the issue only costs
  −0.2) = **5.80, invariant over the content**. That number is **not new** — Phase 0 executed it
  (`prestudy/verification.md` §2.2:218-219, a valid and a broken Python file both at 5.80) and item 1
  restated it (`:126-128`). It is reproduced here through the donor's own crate as the control for
  the row that is new: **every other language in the table**.
- **The extension list decides whether a file is looked at at all.** `verify_project` (`verifier.rs:74-80`) maps
  `py ts tsx js jsx rs go cpp cc cxx hpp h` and `continue`s on anything else — `.c` is **not in the
  list while `.h` is**. Measured on a directory of nine files: six scored, and `best.c`,
  `best.java`, `best.rb` skipped in silence.

Then the arithmetic. `verify_project` averages the scored files, adjusts by the test pass rate
(`pass_rate * 4.0 - 2.0`, so +2.0 for a perfect suite), and `mission.rs:1139` mixes it with the LLM
critique at `critique * 0.4 + verifier * 0.6` against a threshold of 9.2 (C1–C6), 8.5 (C7–C8) or 8.0
(C9–C10). Best case for each language on this host, with a **perfect 10.0 critique and a 100% green
suite**:

| project | verifier score | final | 9.2 | 8.5 | 8.0 |
|---|---:|---:|---|---|---|
| Python | 5.80 → 7.80 | **8.68** | fail | fail | pass |
| Python, no suite to run | 5.80 | **7.48** | fail | fail | **fail** |
| TS / JS / Rust / Go | 10.00 | 10.00 | pass | pass | pass |
| a language not in the extension list | **5.00** (the empty-average default) | **7.00** | fail | fail | **fail** |

The bottom row is measured, not derived: a directory containing only `.rb` and `.java` returns
`file_reports: []` and `avg_score: 5.0` — F161's default-pretending-to-be-a-measurement — and 7.00
is the *ceiling* with a perfect critique. **BCF cannot pass its own gate on a project in a language
it does not know, at any complexity, however good the code is.** And on this host it cannot pass
9.2 or 8.5 on a Python project either — the language BCF was built for and whose tools name its
stage (`emit_stage("5/9", "VERIFIER", "ruff+pytest")`, `mission.rs:996`).

This retires the last reason to port BCF's score. Item 1 voided the *numbers*; this voids the
*shape*, because a constant threshold over a per-language average compares quantities that were
never on the same scale.

### F314 — three of BCF's five test arms return an invented count, and the pass rate is the biggest single term

`run_project_tests` (`verifier.rs:145-510`) is where the "60% deterministic" half of the gate gets
its strongest input, and it is a Boolean dressed as a rate outside Python:

| arm | how the count is produced |
|---|---|
| python (`:147`) | venv, pip install, `pytest -q`, real counts parsed from the summary |
| rust (`:431`) | look for a `test result:` line; if absent, `if result.success { (1, 0) } else { (0, 1) }` |
| go (`:468`) | `if combined.contains("PASS")` then `passed.max(1)`, else `(0, 1)` |
| ts / js (`:490`) | `npm install --silent`, then `npm test -- --passWithNoTests`; `success ? (1,0) : (0,1)` |

`passed.max(1)` is the sharpest of the three: any output containing the substring `PASS` anywhere
reports at least one passing test, and anything that does not contain it — including every way a
`go test` invocation can decline to run — reports exactly one failure. Which of those two branches a
real Go project lands in depends on whether `go test ./... -count=1` prints the word, and the code
pins no flag that would guarantee it. **Not measured here: `go` is not installed on this host**, so
the Go arm is read rather than run. The adjustment those counts feed is `pass_rate * 4.0 - 2.0`, a
±2.0 swing on a 10-point scale — larger than any content signal and larger than the gap between two
of the three gate thresholds.

Measured, by accident, in this item's own probe: `verify_project` on the fixtures directory with
`language = "rust"` printed `cargo test: failed` and returned `tests_passed: 0, tests_failed: 1`.
There is no `Cargo.toml` in that directory. The average went from 8.97 to **6.97** because a build
tool declined to run in a directory that was not a crate, and the gate cannot tell that apart from a
test that failed. Claudette's `Option<bool>` exists precisely for this cell (F317).

The `--passWithNoTests` flag in the ts/js arm is worth one more line: it is a **jest** flag. Passed
to a project whose `test` script is `vitest` or `node --test` it is an unknown argument, and the run
fails for a reason that has nothing to do with the code. Both donors assume jest for Node
(Claudette's `--testNamePattern` at `quality.rs:237` is the same assumption) — which is the first
sign that the unit 2.0 has to model is not the language.

### F315 — the language of a BCF mission is a keyword scan of the user's prompt, with a Python default

`Mission::new` calls `detect_language(prompt)` (`mission.rs:343`), which lowercases the prompt and
returns on the first substring hit: `python|fastapi|django|flask` → python, `typescript|next.js|react`
→ typescript, `javascript|node|express` → javascript, `rust|cargo` → rust, `go |golang` → go,
`c++|cpp|cmake` → c++, **else python**. That one string then selects the coder's system prompt, the
file-extension defaults, the verifier arm, the linter, the test runner and the boilerplate.

Three consequences, all in the code:

- **`"go "` needs a trailing space**, so *"Write a Go service"* is Go and *"Write a service in Go."*
  is Python. The default is not "unknown", it is a language.
- **C++ is detectable and unrepresented downstream.** `default_code_path("c++")` falls to
  `_ => "main.py"` and `default_test_path` to `_ => "test_main.py"` (`mission.rs`), so a C++ mission
  whose model emits a bare fence with no path header has its C++ written to `main.py`, which the
  extension list then reads as Python.
- **The prompt layer leaks a web framework into every language.** `known_bad_patterns(language)`
  prepends a `common` block to every coder prompt whose bullets are *"Service/repository methods
  must return ORM/database models, NOT request schemas"*, *"register()/create() MUST call
  repository.create()"*, *"Do NOT return password hashes in response schemas"*. A Rust CLI mission is
  told about password hashes and repositories. Below it, `write_boilerplate` (`codegen.rs:302`)
  writes — for Python only — a `requirements.txt` pinned to FastAPI/SQLAlchemy/PyJWT, a
  `Dockerfile` with `FROM python:3.12-slim` and `CMD ["uvicorn", "app.main:app", …]`, and an
  `__init__.py` in every directory.

So BCF is not "Python-only" in the sense the brief guessed. It is **one-stack-only**: a FastAPI
service generator with five other languages wired far enough in to reach the scorer. That is the
honest answer to §11's *"BCF reportedly outputs Python only"* — the reusable asset is the pipeline's
*shape* (item 2's three phases), and none of the language plumbing under it.

### F316 — the family's one real multi-language abstraction names the seam, and the expensive third of it is per *tool*, not per language

Claudette's `tools/quality.rs` is the only place in the three donors where "run this project's
checks" is written once and specialised. Its module doc states the contract (`quality.rs:5-10`):
walk up from the cwd, find a canonical config file, and dispatch. The shape it factors into is
exactly three things, and they do not cost the same:

| the seam | what it is | lines |
|---|---|---:|
| **marker** | `Cargo.toml` → Rust, `package.json` → Node, `pytest.ini`/`pyproject.toml` → Python, `go.mod` → Go (`:136-152`), plus a second table for the diagnostics side (`:585-602`) | 35 |
| **command** | `cargo test`, `npm test [-- --testNamePattern=…]`, `pytest [-k …]`, `go test ./... [-run …]` (`:222-263`), plus the build step (`:410-453`) | 42 |
| **parser** | thirteen functions that read a tool's human-readable output back into structure — counts, failures, diagnostics (`:663-1068`) | **387** |

387 of the module's 1,068 non-test lines are output parsers, a further 80 turn parsed output back
into text for the model, and detection plus invocation together are 77. **Adding a language is
about ten lines; adding a language you want structured results from is about fifty; and the fifty
are keyed to a tool's stdout format, not to the language.** `parse_jest_counts` reads
`Tests: 2 failed, 10 passed` — jest's format, not Node's — so a project on vitest or `node --test`
parses to `(0, 0)` from the same `npm test` command. The unit is the **toolchain**, and a language
has several.

Two structural consequences fall out of the same file, and both matter for 2.0.

- **The two marker tables disagree.** `detect_framework` looks for `package.json`; `detect_diag_tool`
  looks for `tsconfig.json`. A TypeScript repository is therefore `npm` to the test side and `tsc` to
  the diagnostics side; a Python repository carrying only `pytest.ini` is `pytest` to one and
  *nothing* to the other. Two answers to "what is this project" in one module is one too many — 2.0
  needs a single resolved profile that every rung reads.
- **The gate has no compile step for two of its four frameworks by construction.**
  `run_build_step` returns `None` for `Pytest | Npm` (`:416-421`), with the honest comment that
  neither has a generic language-level compile step. The consequence is that **the forge gate never
  type-checks a TypeScript project**, even though `parse_tsc_lines` sits 300 lines away and
  `detect_diag_tool` knows how to find `tsconfig.json`: `tsc` is reachable only as a tool the *model*
  may call (`tool_groups.rs:135`), never as a gate input. That is OQ-W6-9's question answered inside
  the donor before it is asked of the language: in the one ecosystem where the type checker is not
  the build command, the inherited gate does not run it.

### 🚨 F317 — the same tree state gets four different verdicts from the four frameworks, and on Windows the npm arm cannot spawn at all

`run_build_and_tests` is the successor's deterministic gate and its outcome type is the right one:
`ran`, `build_ok: Option<bool>`, `tests_ok: Option<bool>`, and `is_hard_fail` = *either* half is
`Some(false)` (`quality.rs:317-339`). F218 already recorded that as the fix for F161. Vendored
verbatim and driven over twelve trees that differ only in language and in whether tests exist:

| framework | no tests in the tree | green suite | failing suite |
|---|---|---|---|
| cargo | `build ok` + `tests: 0 passed` → **`Some(true)`, a pass** | `Some(true)` | `Some(false)`, hard fail |
| pytest | exit 5 → `None`, *"no tests collected"* — advisory | `Some(true)` | `Some(false)`, hard fail |
| npm | **spawn fails** → `None` | **`None`** | **`None` — the failing suite is invisible** |
| go | `go` absent → `None` on both halves | `None` | `None` |

Three separate results, in increasing order of importance.

- **"There are no tests here" is a pass in Rust and a non-answer in Python.** `cargo test` on a
  crate with no `#[test]` exits 0 and prints `test result: ok. 0 passed`, which `classify_tests`
  reads as `Some(true)`; pytest exits 5, which has an explicit arm (`:488-491`) returning `None`.
  Same tree state, same gate, opposite verdicts — and the Rust one is the dangerous direction,
  because `tests_ok = Some(true)` is what the fix-loop reads as verified.
- **On Windows the npm arm is dead, in all three states.** `npm` ships as `npm.cmd` / `npm.ps1`;
  Rust's `std::process::Command` resolves a bare program name through `CreateProcess`, which does
  not consult `PATHEXT`, so `Command::new("npm")` returns `program not found` — measured, 0 ms,
  every time. `cargo`, `pytest`, `node` and `python` all spawn; `npm` and `go` do not; `python3`
  spawns and exits 9009 (F311). The gate degrades honestly — `None`, advisory, no false failure —
  which is exactly what the `Option<bool>` is for and is the difference between this and v1's
  `"Validation failed: [WinError 2]"` string. But the measured consequence stands: **on 2.0's target
  machine the inherited gate gives a Node or TypeScript project no deterministic verification at
  all, including when its suite is red.**
- **And the health check cannot warn about it, because it probes a different binary.** `doctor.rs`
  opens its toolchain section with *"Missing a toolchain is the #1 silent reason 'forge says it
  passed but nothing actually compiled'"* (`doctor.rs:513-516`) and then probes `node` — with
  `why: "the npm forge gate"` (`:560-567`) — while the gate runs `npm`. There is no `npm` entry in
  `TOOLCHAINS`. Both use the same spawn mechanism (`Command::new(bin).arg(arg).output()`, `:609`),
  so the probe passes and the gate fails, on the same machine, for the same reason the section
  comment was written. The `python` entry shows the author knew the shape — `bins: &["python",
  "python3"]`, *"a platform that ships `python3` but not `python` still resolves"* — and the fix was
  applied to one row of one table.

The polyglot case is the fourth result and it needs no toolchain to be missing. A tree with
`Cargo.toml` at the root and a Python package in `pysrc/` containing a **failing** test: the
detector returns `cargo` (the closest marker to the probe point, which is the mission's root),
`cargo check` and `cargo test` both pass, and the gate returns `tests_ok: Some(true)`,
`hard_fail: false`. The failing test is never run. `detect_framework(pysrc)` would have said
`pytest` — the information is there, and nothing asks for it, because the framework is resolved from
the *repository root* and never from **what the change touched**. That is the same missing input
item 4's recommendation 1 needs: a site list.

### 🚨 F318 — OQ-W6-9 answered: the language is not the variable, the subject code's style is. A type check catches 1 of 6 wrong answers under a catch-all arm and 4 of 6 without one — the same split in Python, TypeScript and Rust

The experiment holds the ticket, the defects and the instruments fixed and varies two things: the
language, and whether the four consumers end in a catch-all arm. Seven candidate answers, ground
truth by construction, 42 trees. Red counts are over the **six wrong answers**; the last column is
the false-fail on the one correct answer.

**`wildcard` — every consumer ends in `case _:` / `default:` / `_ =>`:**

| instrument | python | typescript | rust | false-fails the correct answer | median |
|---|---|---|---|---|---|
| syntax | 0/6 | 0/6 | 1/6 | 0 | 80 / 87 / 187 ms |
| **type check** | **1/6** | **1/6** | **1/6** | 0 | 1081 / 686 / 48 ms |
| linter | 0/6 | — | **5/6** | **1/1 in rust** (F320) | 75 / — / 225 ms |
| the repo's own suite | 1/6 | 1/6 | 2/6 | 0 | 679 / 177 / 449 ms |
| **the acceptance test** | **5/6** | **5/6** | **5/6** | 0 | 719 / 169 / 476 ms |

**`exhaustive` — no catch-all; `assert_never` in Python, `const x: never` in TypeScript, nothing at
all in Rust, which is how Rust spells it:**

| instrument | python | typescript | rust | false-fails the correct answer | median |
|---|---|---|---|---|---|
| syntax | 0/6 | 0/6 | 4/6 | 0 | 80 / 85 / 179 ms |
| **type check** | **4/6** | **4/6** | **4/6** | 0 | 1087 / 698 / 110 ms |
| linter | 0/6 | — | 4/6 | 0 | 76 / — / 230 ms |
| the repo's own suite | 1/6 | 1/6 | 5/6 | 0 | 674 / 180 / 195 ms |
| **the acceptance test** | **5/6** | **5/6** | **5/6** | 0 | 723 / 170 / 117 ms |

Five things, and the first is the answer to the open question.

- **The picture does not change with the language. It changes with the style.** mypy on annotated
  Python with `assert_never`, `tsc` on a string-literal union with a `never` guard, and `rustc` on
  an enum behave *identically*: 1 of 6 with a catch-all, 4 of 6 without. Python with `assert_never`
  is Rust; Rust with `_ =>` is untyped Python. Item 4's F307 (`cargo check` 0 of 59, `mypy` 0 of 43)
  is not a fact about statically typed languages, and OQ-W6-9's premise — that a language whose type
  checker is the build might be different — is **false as stated**. What it should have asked about
  is the code.
- **What the type check adds under `exhaustive` is exactly the failure class item 4 found dominant.**
  The three extra catches are `m0_empty`, `m1_one_site` and `m2_three_sites` — nothing was done, or
  part of it was. F302 measured that as almost the whole real distribution ("work that did not
  happen"), and F290's coverage fraction is the same quantity. So in a repository written without
  catch-alls, **the compiler is the coverage check**, and it names the missing sites for free.
- **What no type check ever catches, in any language or style, is `m3_wrong_semantics`** — all four
  consumers handled, one of them backwards — **and `m6_regression`**. Those are 2 of the 6, they are
  the two that require executing the program, and they are caught by the acceptance test and the
  pre-existing suite respectively. The division of labour item 4 recommended survives the language
  change unaltered.
- **The acceptance test is 5 of 6 in every cell of the grid**, and the sixth is the regression it is
  not asked about. It is also *cheaper* than the type check in two of three languages — 169 ms
  against 686 in TypeScript, 719 against 1081 in Python — and dearer only in Rust, where
  `cargo check` is 48 ms because it is the same compiler doing less work.
- **Rust couples the rungs, and that is a design constraint, not a defect.** In the `exhaustive`
  arm Rust's repo suite is red on 5 of 6 rather than 1 of 6, because a tree that does not compile
  cannot run its tests either: the type error takes the regression check down with it. Python and
  TypeScript keep running the wrong program. So in 2.0's own language the gate has to be **ordered
  and short-circuiting** — report the first rung that fired, and say the later ones did not run —
  rather than a set of parallel verdicts to be summarised. `Uncertain` is the right word for the
  rungs behind a compile error, and `Some(false)` for the compile error itself.

### F319 — the exhaustiveness rule has no site in either real corpus: 0 of 30 Rust fixtures and 0 match statements in the Python ones

F318's `exhaustive` arm is worth 3 extra catches out of 6, which is the largest effect this item
measured. It is also the arm the real corpora cannot reach:

- **Q56's Rust half.** 30 `.rs` fixture files; 6 contain a `match`; 4 of those 6 have a literal
  `_ =>` arm. The remaining two are matches over `Option` and over a tuple, closed by a *binding*
  catch-all — `(x, y) =>` in `Q56/refsol/src/lib.rs:15`, `other =>` at `:20` — which is a wildcard
  with a name. **Zero of thirty have a closed enum match**, which is the mechanical explanation for
  F307's `cargo check` catching 0 of 59 Rust failures: the instrument had no site to fire at.
- **K's Python fixtures.** Zero `match` statements. Status branching is 14 `if`/`elif` comparisons
  and 10 set-membership tests, and the vocabulary module's own API is membership —
  `TERMINAL = frozenset({DONE, FAILED, CANCELLED})`, `def is_terminal(status): return status in
  TERMINAL` (`finish_the_cancelled_status/fixture/jobs/status.py`). A membership test over a set has
  **no exhaustive form at all**; adding a member cannot make any caller fail to compile, in any
  language.

The K fixture's own docstring is the point: *"Adding the constant and the transition was the easy
half; every place that BRANCHES on status has to agree about what it means."* The task was written
around exactly the failure exhaustiveness prevents, in the idiom where the compiler cannot see it —
which is what real code looks like, because the idiom was chosen for other reasons years earlier.

So the rule 2.0 can state is narrow and honest: **exhaustiveness is a property of the subject
repository, not a capability of the pipeline.** 2.0 cannot assume it, cannot create it, and should
detect it rather than hope for it — the cheap detector is that the type check is red on the *unfixed*
tree, which is a fact the Localize phase already has to establish for its own reasons.

### F320 — the linter counts the work done: `-D warnings` is green on the answer that did nothing and red on the correct one

Unplanned, and the cleanest replication of item 4's F301 in a second language. In the `wildcard`
arm, `cargo clippy -- -D warnings` is:

| tree | clippy | errors |
|---|---|---|
| `m0_empty` — did nothing | **green** | 0 |
| `m1_one_site` | red | 1 |
| `m2_three_sites` | red | 3 |
| `m5_reference` — **correct** | **red** | **4** |

The lint is `unreachable_patterns`, and it is not a clippy opinion — it is a rustc lint that
`-D warnings` promotes to an error, so `RUSTFLAGS="-D warnings" cargo check` does the same thing.
The mechanism is visible in the diagnostic: once all four variants have an explicit arm, the
pre-existing `_ =>` **becomes unreachable**, and each completed consumer contributes one error.
The lint's error count is the coverage fraction, inverted — a gate on it would reject the correct
answer with four errors and accept the empty one with none.

F301 measured the same anti-correlation on the K corpus through a delta (32 of 42 correct changes,
0 of 12 wrong) and could only say *why* by hand. Here the cause is a single named lint and it
generalises: **a linter's reds move with the code that was touched, and "the code that was touched"
is the one thing the free structural check already measures for nothing.** Item 4's recommendation 4
— do not gate on a linter, in either form — now has a mechanism as well as a rate, in a second
language, at the absolute level rather than the delta.

### 🚨 F321 — the ladder in three more languages: 351 more real cells, and on the arms where the agent was left alone every rung in every language is green on every failure

Item 4 measured the Rust and Python halves of Q56 and skipped the other three languages because
`instruments.q56_ladder` had no rungs for them (F307). Item 5 wrote the rungs — `node --check` and
the fixture's own test for node, `tsc --noEmit` (plain and `--strict`) plus the fixture's test for
TypeScript, `bash -n` for shell — and re-ran the ladder, which is resumable and therefore measured
only the 351 new cells. **The Q56 population is now 728 preserved agent workdirs in five languages,
160 of them real failures**, ground truth re-run rather than read.

Pooled over all 728 cells:

| language | cells | FAIL | rung | red on FAIL | red on PASS | median |
|---|---:|---:|---|---|---|---:|
| node | 130 | 14 | `node --check` | 0 / 14 | 0 / 116 | 48 ms |
| | | | the fixture's own test | 1 / 14 | 0 / 116 | 53 ms |
| typescript | 117 | 11 | `tsc --noEmit` | **0 / 11** | **5 / 106** | 606 ms |
| | | | `tsc --noEmit --strict` | **0 / 11** | **5 / 106** | 609 ms |
| | | | the fixture's own test | 1 / 11 | 0 / 106 | 88 ms |
| shell | 104 | 33 | `bash -n` | 1 / 33 | 0 / 71 | 36 ms |

**OQ-W6-9's named unmeasured language behaves exactly like the two item 4 measured.** `tsc` is the
build in TypeScript and it caught **none** of the eleven real failures, while going red on **five
correct answers**. Across all five languages and 160 real failures, a type or syntax check caught
**one** — and that one is `bash -n` on a file the harness had truncated mid-write.

Then the stratification, which changes the reading and is the reason this finding is not the one it
first appeared to be. The Q56 cells come from W8's gate campaign, which has four arms: `control` and
`gated` leave the agent alone, while `redirect-first-edit` and `deny-first-edit` **interfere with the
agent's first attempt to write a file**. Split on that:

| stratum | cells | failures | any rung red on a failure |
|---|---:|---:|---|
| `control` + `gated` | 280 | 29 | **0 of 29, in all five languages** |
| `redirect-first-edit` + `deny-first-edit` | 448 | 131 | structural 90, the repo's own tests 13, `bash -n` 1, type checks 0 |

**On the 280 cells where the agent was left alone, not one deterministic rung in five languages went
red on a single one of the 29 real failures** — while `ruff` went red on 12 of 68 correct Python
answers, `tsc` on 4 of 44 correct TypeScript ones and `clippy` on 2 of 56 correct Rust ones. The
ladder is not a weak instrument here. It is a **constant**, and the only thing it varies with is
whether it is wrong.

The five `tsc` false-fails have one mechanism and it is worth quoting, because it is F320's in
another language. All five are `Q35`, whose declared return type is
`Record<string, string | string[]>` and whose ticket asks for a repeated key to collect its values
into an array. The fixture stub is type-clean; a correct answer assigns a `string` into the slot and
later `.push`es to it, and gets `TS2322: Type 'string | string[]' is not assignable to type 'string'`
and `TS2339: Property 'push' does not exist`. **The type checker is red because the work was done**,
on the one task in the language whose ticket creates a union type — the same direction as
`unreachable_patterns` in Rust, by a completely different route.

### 🚨 F322 — the free structural check is a measurement of the task's *shape*, not of the language: 9 of 12 on repository work, 0 of 29 on clean single-function work, 90 of 131 when the harness itself blocked the edit — and 0 false positives on 609 correct trees

Item 4's cheapest and best rung is *did the change touch any source file?* — 9 of 12 behavioural
failures on the K population, no toolchain, no parser, no language table (F302, recommendation 1).
It is therefore the rung whose generality matters most, and it was run here over every preserved
Q56 workdir in five languages, plus re-run over K stratified by arm.

| population | cells | failures | untouched trees among the failures | false positives |
|---|---:|---:|---|---|
| Q56, `control` + `gated` | 280 | 29 | **0** | 0 / 251 |
| Q56, edit-interference arms | 448 | 131 | **90** (69%) | 0 / 316 |
| K (repository bugfixes) | 54 | 12 | **9** | 0 / 42 |

Pooled over Q56 that is 90 of 160, which is the number this item nearly recorded, and it would have
been an artefact: **every one of the 90 is in an arm built to stop the agent editing.** The rung is
measuring the interference. On the arms where nothing was interfered with, a single-function task
either got written or the cell did not exist — and 29 real failures produced 29 modified files.

The K population says the opposite, and that is the interesting half. Nine of its twelve failures
are untouched trees — item 4's number, reproduced here with item 4's exact rule (CRLF-normalised,
`tests/` excluded) so the two populations are comparable — and they are **not** concentrated where a
sceptic would look:

| K arm | failures | untouched |
|---|---:|---:|
| `k-champ`, the champion unconstrained | 1 | **0** |
| `k-27b`, both of them timeouts (W1 F91) | 2 | 2 |
| `w11-b12`, budget 12, deliberately tight | 3 | 2 |
| `w11-b20` | 1 | 1 |
| **`w11-b40`, the most generous arm W11 item 5 ran** | 5 | **4** |

Four of the nine are at the budget where F294 found the model stopping 25 rounds *short* of
exhausting it, so this is not starvation. On repository work the empty tree is a real and common
failure, and the reason is the one F302 named: on a 16–20 file repository an agent can spend its
whole budget navigating and never edit; on a one-file exercise it cannot.

**The ruling that survives is item 4's, with its scope stated: the structural check goes first
because it is free and because it has now produced zero false positives on 609 correct trees in five
languages — but its yield is a property of the task shape.** Expect it to fire on repository work
(the shape 2.0 targets) and to stay silent on single-file work, and never quote the pooled rate,
because the pooled rate is a fact about which arms were in the sample.

### F323 — an instrument that is red on the unfixed tree is not an instrument, and this item shipped one for an hour

The first `tsc` run over the TypeScript cells returned **red on 10 of 10 failures and 80 of 80
passes**. A rate like that is either a perfect instrument or a broken one, and the control that
settles it costs nothing: run the rung on the **pristine fixture** and on the **reference solution**,
where truth is by construction. Both were red, with `TS2307: Cannot find module 'node:assert/strict'`
— the fixtures import node's own types and the probe had not pointed `tsc` at `@types/node`. With
`--typeRoots` added, the fixture and the refsol are green for all nine TypeScript tasks and the
population numbers become F321's.

The same pass is worth running for what else it says. Over all 56 Q56 tasks, fixture and reference
solution:

| rung | red on the unfixed fixture | red on the reference solution |
|---|---|---|
| `tsc` / `tsc --strict` | 0 / 9 | 0 / 9 |
| `cargo check`, `py_compile`, `node --check`, `bash -n`, `mypy` | 0 | 0 |
| `cargo clippy -D warnings` | 2 / 14 | 0 / 14 |
| `ruff` | 3 / 15 | **1 / 15** |
| the fixture's own test | **13 / 56** (6 rust, 3 python, 2 node, 2 ts) | **0 / 56** |

Two readings. The linter is red on a **reference solution**, which is the whole argument against
gating on it in one cell. And the tests a repository already ships are red-before and green-after in
**13 of the 56 tasks** — by construction they discriminate on nearly a quarter of this corpus — yet
on the real cells they caught only 13 of 160 failures (F321). The gap is the point: a shipped test
encodes the part of the requirement someone thought to write down, and the failures are in the part
nobody did. That is item 4's recommendation 3 with a mechanism, and it is the same asymmetry F305
found in generated tests.

This is not only a note about the probe. **It is the requirement.** 2.0 will run rungs inside
repositories it has never configured — that is what item 5's whole profile machinery is for — and a
misconfigured rung is red on everything, which is indistinguishable at the call site from a
repository full of defects. So: **every rung is calibrated against the pre-change tree, and a rung
that is red before the change contributes `Uncertain`, never a veto.** The pre-change tree is
already available at Localize time (F318's exhaustiveness detector wants the same run), so the
calibration is free. F300 found the same thing from the other end — `ruff` and `mypy --strict` red
on the K fixtures themselves — and [[verify-claims-against-code-not-docs]] 23 recorded it as a method
rule after item 4; here it is a product rule.

### F324 — F220 again, in a third language, in this item's own run: `taskkill /T` is not a job object

While the ladder was running, a `bash solution.sh` from a Q56 **shell** cell was found alive with 202
seconds of CPU and **its parent gone** — a spinning agent solution, orphaned by the verifier's
timeout, burning a core after the cell it belonged to had been recorded. `common.kill_tree` does the
right thing on Windows (`taskkill /PID <pid> /T /F`), and `/T` walks the *live* parent-child links:
the intermediate `bash` had already exited, so the grandchild was reparented and the sweep missed it.

That is F220's mechanism exactly, now reproduced in a third language and in a harness that already
carries the fix. Item 4 hit it in Python (a `pytest` orphan holding a pipe for 22 minutes); item 2
measured it in the donor's own pipeline. The conclusion is the one W3 item 7 already specified and
this is the third piece of evidence for it: **process-tree killing by parent links is not a
containment primitive.** On Windows the containment primitive is a **job object** with
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`; on Linux it is a process group or a cgroup. Anything 2.0
executes on behalf of a model is created inside one, and the kill closes the job rather than walking
a tree that has already been rearranged.

## Options compared

The scoping question is really one design question — **how does 2.0 learn what to run?** — and the
three donors between them have already tried four of the five answers.

| how the language is decided | who does it | works for a language nobody anticipated | fails how | evidence |
|---|---|---|---|---|
| a compiled-in table of languages | v1 `validators`, BCF `verify_file` | no — `Unsupported language: rust`, or worse, `verify_generic` scoring it 8.00 | silently, and the default *is* a language | F311, F313 |
| the model names it | v1's `language` tool argument | no | the model can name one that is not in the table | F311 |
| a keyword scan of the prompt | BCF `detect_language` | no | *"a service in Go."* is Python; C++ writes `main.py` | F315 |
| marker files in the tree | Claudette `detect_framework` | no, but it degrades honestly | two tables disagree; the root wins over the change | F316, F317 |
| **the task carries its own command** | this repository's corpus (`task.toml` `[verify] script = "verify.sh"`) | **yes** | only if the task is wrong, which is visible | item 4 rec 2 |

And within a chosen language, the per-rung cost of being general, measured:

| rung | what generalises | what does not | on 728 real attempts in five languages |
|---|---|---|---|
| **structural check** | **the whole thing** — no toolchain, no parser, no table | "what is a source file", as an extension list | 0 false positives on 609 correct trees; 9/12 on repository work, 0/29 on clean single-function work (F322) |
| syntax check | nothing — a different binary, extension and module system per language | all of it | 1 of 160 failures, and that one is `bash -n` on a truncated file (F321); v1's table discriminates in 0 of 6 languages (F311) |
| type check | the verdict, exactly | whether the subject code has a catch-all arm | **0 of 160**, in all five; 1/6 vs 4/6 on the constructed grid depending on style (F318, F321) |
| linter | nothing worth having | — | red on 12 of 68 correct python and 4 of 44 correct typescript answers, 0 of 29 wrong ones on clean arms (F321); green on the empty answer and red on the correct one in rust (F320) |
| the repo's own suite | the *role* — regression guard | the runner, and the runner is not the language | 13 of 127, no false positives — and 0 on the clean arms (F321); jest vs vitest from one `npm test` (F316) |
| **acceptance test** | **the whole thing** | one command string, which the task already carries | it is the ground truth here; 5/6 in every cell of the constructed grid (F318) |

## Recommendation

**1 — One resolved toolchain profile per mission, with the task's own command outranking it.**
Three sources in priority order: the **task's** declared command, the **repository's** declared
profile if it has one, then **detection** from markers. This is not a new mechanism — the corpus in
this repository already works this way (`[verify] kind = "script"`), and item 4's recommendation 2
already made the acceptance test the only `Measured` input. What is new is that detection must
resolve **one** profile that every rung reads, rather than the donor's two marker tables that
disagree about the same repository (F316).

**2 — The profile is a data record, not a match arm.** Source extensions, build command, test
command, acceptance command, formatter and linter (advisory), and the resolved absolute path of
each binary. Adding a language is adding a row in a TOML table that ships with 2.0 and is
overridable per repository — not a new `match` arm and a rebuild. The reason this is affordable is
item 4's recommendation 7: the measurement interface is `Measured(exit_code, stdout, stderr)`, so a
row needs no parser.

**3 — Never parse a tool's human-readable output to decide a verdict; parse only to display one.**
387 of the 1,068 non-test lines in the donor's best module are output parsers (F316), they are keyed
to a *tool* rather than a language, and the tool changes underneath them — `parse_jest_counts`
returns `(0, 0)` for the same `npm test` on a vitest project. Counts are worth showing a human and
worth nothing to a gate that has an exit code.

**4 — Resolve every binary once, at startup, with the same spawn mechanism the gate uses.** Three
absences measured here look like three different things: `python3` **spawns and exits 9009**
(F311, F313), `npm` **cannot be spawned from a Rust process on Windows at all** (F317), and `go` is
honestly missing. The donor's own health check misses the middle one because it probes `node` and
the gate runs `npm` (F317). So: probe the binary the rung will actually invoke, by name, through
`std::process::Command`, and store the resolved path — a version string is not proof, and a
successful spawn is not proof either.

**5 — An absent toolchain is `Uncertain`, and `Uncertain` is loud.** Claudette's `Option<bool>` is
the right type and 2.0 keeps it (F218, F317). The gap is that advisory currently means *silent*: on
this machine a Node project passes the inherited gate with a red suite and nothing says so. Every
rung that did not run must appear in the outcome and on the console, with the reason. This is item
8's first requirement and it arrives here from the language direction.

**6 — Run the structural check first everywhere, quote its yield nowhere.** It is the one rung that
needed no rungs written for it: the same walk ran unchanged over five languages and produced **zero
false positives on 609 correct trees** (F322). Its *yield*, though, is a property of the task shape
and of the arm — 9 of 12 on repository work, 0 of 29 on clean single-function work, 90 of 131 when
the harness itself blocked the edit — so it goes first because it is free and cannot be wrong, not
because of a rate. Two details it needs: a definition of "source file" that is a **deny-list**
(BCF's twelve-extension allow-list drops `.c` while keeping `.h` and scores a project it cannot read
as exactly 5.0, F313), and CRLF normalisation, without which a file rewritten with different line
endings reads as work (F310, and item 4's `residue.py:37` already does it). The real answer is still
the Plan's site list, which is language-free.

**7 — Do not require exhaustiveness; detect it, and take the site list for free where it exists.**
Under the `exhaustive` style the compiler catches the whole dominant failure class — nothing done,
or part of it done — in all three languages, and its error list *is* the coverage fraction (F318).
Under the style both real corpora actually use, it catches none of it (F319), which is what 728 real
attempts show from the other side: **a type check caught 0 of 160 real failures in five languages**
(F321). The detector is cheap and Localize needs it anyway: **run the type check on the unfixed
tree**. Red with file names means the compiler will do the coverage check; green means the site list
has to come from the Plan (OQ-W6-8); and red *without* the change having happened is F323's
calibration signal, not a verdict.

**8 — The gate is ordered and short-circuits, because Rust makes that mandatory.** In Rust a type
error takes the test suite down with it — the repo suite goes from 1/6 to 5/6 red in the
`exhaustive` arm not because it found five regressions but because five trees did not compile
(F318). A gate that reports parallel verdicts would report five regressions. Order the rungs, report
the first that fired, and mark everything behind it `Uncertain` rather than green *or* red.

## Rejected alternatives and why

- **"Support the top N languages at launch."** The donors priced it: N is not the number.
  Claudette's four frameworks cost 387 lines of parser, and the parsers are per *toolchain* — jest
  and vitest are two, `pytest` and `unittest` are two, and every row is also a claim about which
  binaries exist on the machine. Ship one row that is correct (Rust), one that is nearly free
  (Python), and a way to add rows without a rebuild.
- **"Ask the model which language this is."** v1 takes it as a tool argument and BCF scans the
  prompt. Both are guesses with a Python default, and BCF's writes C++ into `main.py` (F315). The
  tree knows, the task knows, and neither has to be asked.
- **"Score files per language and gate on the average."** F313: a perfect Python file scores 5.80
  and a language BCF has never heard of scores 8.00, so the constant threshold compares quantities
  that were never on the same scale — and a project BCF cannot read is unpassable at 7.00 with a
  perfect critique. Item 1 voided the numbers; this voids the shape.
- **"Add a linter to the gate for languages where it is idiomatic."** Rust is the case for it and
  Rust is the counter-example: `-D warnings` is green on the answer that did nothing and red on the
  correct one, with an error count equal to the work completed (F320). On the real population the
  same instruments cost 12 of 68 correct Python answers and 4 of 44 correct TypeScript ones while
  catching nothing on the clean arms (F321).
- **"Require the subject repository to be written with exhaustive matches."** Zero sites in either
  corpus (F319), and 2.0 does not own the code it is asked to change. Detect, do not demand.
- **"Treat Windows as the problem and require WSL."** Tempting after F317, and it moves the failure
  rather than removing it: the same class — a binary name that resolves to something that is not the
  tool — produced `python3` exiting 9009 *and* the Store alias defeating v1's own fallback. Resolve
  binaries explicitly and the platform stops mattering. (What WSL would change is left as
  OQ-W6-12.)

## Effect on fun

The console gets a roster it can actually show. A resolved profile is a small, concrete,
per-repository fact — `cargo · pytest · no runner for web/` — and it belongs on screen at mission
start, the way a strategy game shows which units are available before the first order. It is also
the honest version of a loading screen: the profile resolves in milliseconds and it is the first
thing 2.0 can say about a repository it has never seen.

The bigger win is that **an absent rung becomes an event instead of a silence**. The inherited gate's
worst moment on this machine is invisible: a Node project's red suite produces no verdict, no line,
no colour. A unit that reports *"npm: not on this machine — tests not run"* is both more honest and
more interesting than a green tick, and it is the same shape as W3's classified failures. Nothing
about a command centre is fun if the most common outcome is a tick that means "I did not look".

And the linter result has a fun consequence worth keeping: the reds a linter produces are a map of
**where the work happened**, which is a genuinely useful thing to draw and a terrible thing to gate
on. Show them on the diff; never let them stop a unit.

## Open questions

| # | Question | Waiting on |
|---|---|---|
| OQ-W6-9 | Does the picture change in a language whose type checker is the build? | **answered twice here**: on the constructed grid the variable is the subject code's catch-all arm, not the language — 1/6 vs 4/6 identically in Python, TypeScript and Rust (F318); and on **728 real attempts in five languages** a type check caught **0 of 160** failures while false-failing 5 correct TypeScript answers (F321) |
| OQ-W6-8 | Does the coverage fraction bind as a veto, or only as a report? | still open, with a second source named: where the subject code is exhaustive the *compiler* emits the site list (F318), and neither corpus is (F319), so Plan still has to |
| OQ-W6-11 | Where does the toolchain profile live — a table shipped with 2.0, a file in the repository, or both — and who writes it for a repository 2.0 has never seen? | item 6 (isolation) and W12 (repo strategy) |
| OQ-W6-12 | Does 2.0 ship a PATHEXT-aware spawn for Windows, or declare Node work out of scope until WSL? `Command::new("npm")` is `program not found` today (F317) | W7 (sandboxing) — it is the same seam as the job object, which F324 says is not `taskkill /T` |
| OQ-W6-13 | The Q56 clean arms hold 29 real failures and no rung fires on any of them (F321). What *are* they? K's taxonomy (F302) does not transfer — these are one-file tasks where the file was always written | item 7, and a candidate for the first thing an LLM judge is asked to do |
| OQ-W6-7 | *(from item 2)* Rules-only router, or rules plus a recorded model reading? | still open — nothing here bears on it |

## Confidence: high on the donor facts, high on the experiment's internal validity, medium on how far it travels

Every donor claim in this item was **executed**, not read: BCF's scores come from BCF's own crate
through a path dependency, v1's two surfaces were ported byte-for-byte and run, and Claudette's
detector, build step, parsers and classifier were vendored with line citations and driven with real
subprocesses. Where something could not be run it is marked — the Go arm of BCF's test dispatch, and
PHP anywhere, because neither toolchain is installed here.

The controlled experiment is strong internally: 42 trees, ground truth by construction, and the
three languages agree cell for cell within a style, which is not a subtle statistical claim. Its
**defect set is chosen rather than sampled** — six candidate answers around one ticket — so the 1/6
and 4/6 are ratios over a constructed population. That is why the real half matters: **728 preserved
agent workdirs in five languages, 160 real failures, ground truth re-run rather than read**, and it
agrees (F321). Between them the two halves are the strongest generality evidence this workstream
has.

Two limits remain, and one of them nearly became a finding. The **Q56 population is arm-heavy**: 448
of its 728 cells come from arms that deny or redirect the agent's first edit, and pooling them
produced a structural-check rate of 90/160 that stratification cut to 0/29 on the clean arms (F322).
Every rate in this item is therefore reported per stratum, and the pooled numbers are labelled as
pooled. ([[verify-claims-against-code-not-docs]] 26 is exactly this, and it fired again.) And the
**task shape is one shape in each population** — a new case in an existing vocabulary for the
constructed grid, one-function exercises for Q56. A task that changes a signature is the case where
a type checker should earn its place in any style, and it is untested here.

Two narrower caveats. The `node --check` result (F311) is one node version on one platform and
reads like a bug rather than a design; it was not checked against another version, and the finding
that matters — v1 chooses the extension, and the extension chooses the parser — does not depend on
it. And every "this binary is missing" result is a fact about this machine, which is the point
rather than a limitation: the machine is the one 2.0 runs on.

---

# Item 6 — worktrees and per-task isolation

## Question

§11's scope: *"Git worktrees or per-task isolation for parallel work. Compare overhead, and check
RAM cost against the 32GB ceiling."*

Two other workstreams have already aimed a narrower question at this item.

- **OQ-W3-12**, which arrives as W3 item 4's fifth recommendation: *"the checkpoint row must carry
  an identifier that can restore the workspace, and `Holding`/fork must refuse to promise
  resumability without one."* F173 measured the hole — the event log restores exactly what the
  operator saw and nothing about what the agent touched — and named three candidate mechanisms: a
  git worktree, a git stash object, or a copied pre-image tree.
- **OQ-W6-11**, from item 5: where the toolchain profile lives, and who writes it for a repository
  2.0 has never seen. It lands here because a worktree is precisely the case where a profile
  resolved in one directory is asked about another.

W11 F249 also left a number to check rather than to inherit. It priced isolation at **~4.7×** the
incremental cost on a real Rust project — 104.2 s from a fresh clone against 22.3 s incremental —
and explained it in a clause: *"a fresh worktree does not share `target/`, so every isolated attempt
pays a cold build."* That clause is an assumption about a tool, and it is testable.

So the item is three questions, and only the first is the brief's:

1. **What does isolation cost** — wall clock, disk, and RAM against a 32 GB box that is already
   holding a model.
2. **What identifies a workspace state** well enough that a checkpoint row can restore it.
3. **Does the toolchain survive the move**, given that everything it needs is what git ignores.

## Method

Six probes in `research/spikes/w6-isolation/`, run against the four real repositories on this
machine — the three donors and this one — rather than against a synthetic tree, because the numbers
that decide the question are the sizes of the directories git ignores.

| probe | what it does | output |
|---|---|---|
| `stale.py` | hashes every tracked file in every repo the way git would, and compares with the index | `stale-results.json` |
| `mechanisms.py` | prices `git worktree add`/`remove`, `git checkout-index`, `git stash create`, the temp-index snapshot, and a full `robocopy` of the working directory, per repo, n=3 | `mechanisms-results.json` |
| `checkpoint.py` | the whole cycle in a throwaway clone: snapshot → an agent's edits → snapshot → change list → a worktree **at** the snapshot → restore → `git gc --prune=now` | `checkpoint-results.json` |
| `buildcache.py` | seven cargo phases on the real Rust workspace: private against shared `CARGO_TARGET_DIR`, cold against warm against cross-worktree, and two attempts at once on one build directory and on two, with RAM sampled throughout | `buildcache-results.json` |
| `freshwt.py` | the case `buildcache.py` could not see — a worktree created *after* the cache is warm, a copied tree with no `.git` at all, and two cold builds at once | `freshwt-results.json` |
| `toolchain.py` | what a fresh worktree does not contain: the ignored entries and their size, the profile resolved in both trees, and one executed command per repo | `toolchain-results.json` |

Host as measured: git 2.54.0.windows.1, cargo 1.95.0, node 24.15.0, 12 logical cores (i5-10500),
31.9 GB RAM, and every repository on the same SATA SSD (Samsung 870 EVO) as the scratch space.
`pnpm` — the package manager v1's own lockfile names — is **not installed on this host**, which is
data rather than a gap, and no model was resident during the RAM measurements, which is the
optimistic case.

Because the probes run against David's working repositories, the safety rule is stated once: they
add a worktree and remove it, and they write objects with `git stash create` and `commit-tree`,
which touch neither the index, the working tree, nor any ref. Every repo's `git status` and
`git worktree list` are asserted clean before and after, and the one file each probe edits is
restored byte for byte.

That rule is where the first finding came from. It fired on the second repository, and what it
caught was not the probe.

## Inherited

| What | Source | Verdict here |
|---|---|---|
| Git worktrees, the family's one use | BCF `swebench.rs:260-330` | **KEEP the mechanism, not the wiring** — a sequential bench harness, never pruned, and it falls back to a full clone (F325) |
| A clone per mission | Claudette `tools/mission.rs`, `tools/git.rs:538-555` | **CANNOT TRANSFER** — `validate_clone_url` refuses `file://` and local paths by design, so a repository on this disk cannot be isolated by that path at all (F325) |
| One shared workspace directory | v1 `docker-compose.yml:110,144,170`, `tools/file_ops.py:53-89` | **DISCARD** — one host directory mounted read-write into three services, and the tool that writes takes no lock (F326) |
| A `file_locks` table | v1 `schema.prisma:121-133`, `taskAssigner.ts:100-120`, `fileLock.ts` | **DISCARD** — the lock names files a *planner* declared, is taken at assignment, and has a second implementation with no production caller (F326) |
| MCP distributed file locks | v1 `mcp/client.py:168-229`, `agents/base.py:66-67,119-121`, `config.py:36` | **DEAD IN EVERY CONFIGURATION** — off by default, explicitly bypassed for the only agent that writes code, and the gateway is not deployed (F326) |
| A copied file plan per cell | this repo `w8-corpus/src/workdir.rs` | **KEEP** — 952 cells, median 8 KB and 10 files each, and it is what runs when the subject has no git (F327) |
| Per-file undo into a trash directory | Claudette `transcript.rs:132-154`, `commands.rs:492` | **KEEP, as a different thing** — a per-turn undo, not a workspace marker (F173) |
| *"A fresh worktree does not share `target/`, so every isolated attempt pays a cold build"* | W11 F249 | **CORRECTED** — 56.6 s cold, **24.7 s** for a worktree created after the cache is warm, 0.4 s for one that is warm (F331) |
| Cap concurrent builders at 2 | W2 F83 and its recommendation 5 | **BINDING, and it is about the model** — two *builds* at once save 2–18% and take the box to 2.3 GB free (F333) |

## Findings

### F325 — nothing in the family ever runs two agents against one tree, and the one path that could has no caller

The brief's phrase is *"per-task isolation for parallel work"*. The work is the part the family
does not have.

**BCF** owns the only worktree in the three donors, and it is in the bench harness.
`prepare_workspace` (`src/swebench.rs:260-334`) caches one clone per repository, creates
`git worktree add --detach <workspace> <base_commit>` per instance (`:307-322`), reuses an existing
workspace with `git reset --hard <base_commit>` plus `git clean -fd` (`:265-283`), and falls back to
a direct clone when `worktree add` fails (`:327-334`). Two things it never does: `git worktree
remove` and `git worktree prune` appear **nowhere in the repository**, so the metadata accumulates
for as long as the harness runs; and it never runs two of them at once — the driver is
`for (i, instance) in instances.iter().enumerate()` (`:884`), and `src/mission.rs` contains no
`spawn`, no `join_all` and no `JoinSet`.

**Claudette** is one session in one working directory. Its only isolation is `git_clone` into
`~/.claudette/missions/<slug>/`, and `validate_clone_url` (`tools/git.rs:538-555`) rejects anything
that is not `https://`, `http://`, `git@` or `ssh://` — the comment is explicit: *"Don't let the
model talk us into `file:///` or other surprise schemes."* That is a defensible security decision
and it means **a repository on this disk cannot be isolated by that path at all**. The one place
Claudette anticipates a worktree is `missions.rs:428-441`: if `.git` is a pointer file rather than a
directory, `add_marker_to_git_exclude` returns `Ok` without doing anything, and — by its own comment
— *"the worst case is the pre-fix behaviour of the marker landing in the PR"*. The family's single
acknowledgement of a worktree is a graceful leak.

**v1** has the apparatus and no caller. `/queue/parallel-assign` (`routes/queue.ts:237-320`) is
documented as the endpoint that *"does NOT check if agent is idle (allows parallel execution)"*, and
it is the only caller of `ResourcePoolService.canAcquire` / `acquire` (`:283`, `:308`) in the whole
of `packages/api/src`. Nothing calls the endpoint: the UI client posts `/queue/assign`
(`packages/ui/src/api/client.ts:132`), `schedulerService.ts` contains no assignment call at all, and
the only other match for the string in the repository is v1's own compiled `dist/`. This is the
third instance of the same shape in this workstream — the retry queue whose only caller is a
benchmark script (F299), the re-scoped-by-a-stronger-model blob with no reader (F186) — and it is worth stating as a
rule: **in this family, the parallel path is the one that was never wired.**

So there is no inherited *wiring* to port, only a mechanism that has been shown to run on this
machine. And the parallelism 2.0 can actually use is two: W2 F83 measured aggregate throughput
saturating at N=2 (1,541 tok/s prefill at two sequences, 1,511 at four), and W2's recommendation 5
already caps concurrent builders there. Every cost in this item should therefore be read as "×2",
never "×8".

### F326 — v1's isolation is a scheduler's promise, and the tool that writes code is party to none of it

v1 is the donor that ran multi-agent, so its answer is the one worth reading closely. There are
three mechanisms, in three layers, and the agent that mutates the tree is excluded from all three.

1. **The workspace is one directory.** `docker-compose.yml` bind-mounts `./workspace` into `api`
   (`:110`), `agents` (`:144`) and `mcp-gateway` (`:170`) read-write, and into `backup` (`:215`)
   read-only. The agents' file tools resolve every path against it: `FileWriteTool._run`
   (`packages/agents/src/tools/file_ops.py:53-89`) joins `settings.WORKSPACE_PATH / path`, checks
   only that the result does not escape the workspace, creates parents, and writes. There is no
   task subdirectory, no lock check, and no record of which task wrote the bytes.
2. **The `file_locks` table locks names a planner chose.** `orchestratorService.ts:170` fills a
   task's `lockedFiles` from the decomposition (`[st.file_name]`, one declared file per subtask);
   `taskAssigner.ts:100-120` acquires those locks at *assignment* time and skips a task whose
   declared files collide. So the lock is a **scheduling filter over declarations**, taken before
   the work starts, by a component that never sees a write. An agent that edits a file nobody
   declared — the normal case, since the coder gets `file_write` with a free-text path — collides
   with nothing.
3. **The distributed lock is dead in every configuration.** `mcp/client.py:168-229` implements
   `claim_file` / `release_file` against the MCP gateway, and `tools/mcp_file_ops.py` documents
   *"distributed file locking to prevent conflicts when multiple agents"* work at once. `USE_MCP`
   defaults to **false** (`config.py:36`); when it is true, `get_tools_for_agent` returns
   `CODER_TOOLS_HTTP` for the coder anyway — *"Coder always uses HTTP tools, never MCP (even if
   USE_MCP is enabled)"* (`agents/base.py:119-121`) — and the module's own comment says why the
   question is moot: *"MCP file ops are NOT used because MCP Gateway isn't deployed"*
   (`base.py:66-67`). A fourth surface, `FileLockService` (`services/fileLock.ts`), is a complete
   second implementation of the same table whose only callers are its unit test and a manual
   release button in the UI.

The lesson 2.0 should take is not "add a lock". It is that **isolation has to be enforced where the
bytes are written**, and the only place that is true of is the path the tool resolves. v1's tool
resolves every path against one shared root, so no amount of table-keeping upstream can make two
tasks safe. Item 4's `Measured(exit_code, stdout, stderr)` contract has the same shape: the fact has
to be produced where it is true.

### 🚨 F327 — the marker is free and the tree is not: 0.08–0.66 s against 6–136 s, and 0.8–64 MB against 1.7–25.5 GB

OQ-W3-12's three candidates priced on the four real repositories, n=3, medians:

| repo | tracked | worktree add | the worktree | worktree remove | `checkout-index` | `stash create` | temp-index snapshot | full copy | what the copy copies |
|---|---|---|---|---|---|---|---|---|---|
| bcf | 61 | **0.08 s** | 0.8 MB / 62 | 0.03 s | 0.05 s | 0.047 s | 0.085 s | 6 s | 1.7 GB / 2,342 files |
| claudette | 494 | **0.30 s** | 4.7 MB / 495 | 0.11 s | 0.24 s | 0.064 s | 0.148 s | **136 s** | **25.5 GB** / 55,831 files |
| v1 | 539 | **0.66 s** | 63.7 MB / 540 | 0.12 s | 0.50 s | 0.055 s | 0.385 s | 58 s † | 1.3 GB / 72,463 files † |
| abcc20 | 1,079 | **0.63 s** | 9.4 MB / 1,080 | 0.28 s | 0.53 s | 0.070 s | 0.311 s | 62 s | 5.7 GB / 57,111 files |

† the only bounded number available for v1 — see below. Multi-threaded copies (`/MT:8`) are 0.8 s /
102 s / 21 s / 30 s on the same rows, and deleting the copy afterwards costs another 0.6–8.5 s.

**The isolation marker is free at every size in this family.** A worktree of the largest repository
here costs two thirds of a second and 9.4 MB, and `git checkout-index` — the same tree with no
`.git` at all — is within a factor of 1.3 of it. The three-orders-of-magnitude difference is not
between the mechanisms; it is between *tracked content* and *the working directory*, and the whole
of it lives in what git ignores: claudette's tree is 4.7 MB of tracked files sitting under 25.5 GB
of `target/`.

The copy also has two failure modes that a worktree does not have, and both fired here:

- **It follows the platform's reparse points.** v1's tree is a pnpm install: **2,859 junctions** and
  **53,455 hard links**. `robocopy /E` follows them, so the copy expands rather than reproduces —
  it was killed at **190 s having written 247,869 files**, more than the source contains, and still
  climbing. With `/XJ` it finishes in 58 s and produces a `node_modules` with 2,859 missing links,
  which is a tree the toolchain cannot use. The platform's own copy tool cannot faithfully copy the
  platform's own package manager's output.
- **It copies its own destination.** The first attempt at this repository put the copy in
  `scratch/`, which is inside the repository: 453,507 files and 43.7 GB in ten minutes before it was
  killed, from a 5.7 GB source. Obvious in hindsight, invisible in a design document, and the reason
  the recommendation says the pre-image must live outside the tree it copies.

And one Windows tail case worth recording because it cost ten minutes: the v1 copy contained a file
named `nul`, which is a reserved device name, so `rmdir /s /q` could not delete the copy at all. It
took `Remove-Item -LiteralPath '\?\D:\…'` to get rid of it. A mechanism that leaves a directory
behind on this platform needs the extended-length path form in its cleanup, or it accumulates.

### 🚨 F328 — `git status` clean is not a claim about content: 241 of 539 tracked files in the v1 donor differ from their blobs, and the tree reports clean

This one caught the probe before the probe caught anything. `mechanisms.py` dirties one tracked
file, measures, writes the original bytes back, and asserts the repository is clean again. On v1 the
assert fired: a 500-line file reported as 500 insertions and 500 deletions, after a byte-for-byte
restore.

The bytes were never the problem. `git ls-files --debug .claude.md` records **size 19,754** against
a blob of **19,254 bytes** and an mtime from February; the file on disk has been CRLF, and the blob
LF, for months. Git's index caches `(size, mtime)` per entry and skips re-hashing when both match,
so `git status` had never looked. Touching the file — writing back the identical bytes it already
held — invalidated the stat entry, git re-hashed, and the difference that was always there became a
modification attributed to whoever ran last.

Scanned properly (`stale.py`: hash every tracked file the way git would, compare with the index):

| repo | tracked | content differs from index | `git status` reports | hidden |
|---|---|---|---|---|
| bcf | 61 | 0 | 0 | 0 |
| claudette | 494 | 0 | 0 | 0 |
| **v1** | 539 | **241** | **0** | **241** |
| abcc20 | 1,079 | 0 | 0 (1 untracked) | 0 |

All 241 are end-of-line only, all in the same direction (CRLF on disk, LF in the blob), 56,754 CRs
in total, and the distribution names the cause: `.ts` 74, `.tsx` 53, `.js` 52, `.md` 24, `.yml` 8,
`.json` 6, `Modelfile` 5, `.ps1` 3 — and **zero `.py`, `.sh` or Dockerfiles**, which are exactly the
three patterns v1's `.gitattributes` covers. The repository has an EOL policy for three globs and
241 files fell outside it.

Three consequences, and none of them is about v1:

1. **A checkpoint that asks git "what changed" gets an answer conditioned on stat state.** On this
   tree the honest answer is "241 files", the answer git gives is "nothing", and which one you get
   depends on whether something touched an mtime since the last checkout — a formatter, an editor,
   an agent reading and rewriting identical content.
2. **The instrument must be content, not status.** `git hash-object` over the tracked set costs
   under a second per repository here and cannot be fooled by a stat cache.
3. **It is F310 again, one layer up.** Item 4 already had to normalise CRLF before comparing trees;
   the same normalisation decides what a workspace checkpoint even means. EOL policy is not a
   cosmetic detail of the isolation design — it is part of its semantics.

### 🚨 F329 — `git stash create` cannot see the files the agent created, and the snapshot that can sweeps in everything else

The pre-image candidates, on the same dirtied tree — one tracked file edited, one new file created:

| repo | `git stash create` | what it captured | temp-index snapshot | what it captured |
|---|---|---|---|---|
| bcf | 0.047 s | 1 path: the edit | 0.085 s | 2 paths: the edit **and** the new file |
| claudette | 0.064 s | 1 path | 0.148 s | 2 paths |
| v1 | 0.055 s | 1 path | 0.385 s | **243 paths** |
| abcc20 | 0.070 s | 1 path | 0.311 s | 6 paths |

`git stash create` has no `--include-untracked`; the porcelain `git stash push -u` does, and it
mutates the working tree, which is the one thing a checkpoint must not do. So the stash object
records the modifications and **drops every file the agent created** — which, for a coding agent, is
most of the work. That alone eliminates OQ-W3-12's second candidate.

The mechanism that does capture them is plumbing: point `GIT_INDEX_FILE` at a scratch file,
`read-tree HEAD`, `add -A`, `write-tree`, `commit-tree`. It touches neither the real index nor the
working tree, it costs 0.085–0.385 s on trees of 61 to 1,079 files, and it produces **a commit sha —
exactly the identifier W3 item 4 asked the checkpoint row to carry**.

The v1 row is the warning that comes with it. `add -A` re-hashes everything, so the snapshot of that
tree contains 242 modifications and one addition: the agent's two files, plus F328's 241. A
snapshot's *contents* are therefore not a change list. **The change list is the diff between two
snapshots taken with the same instrument** — pre-image and post-image — and never a diff against
`HEAD`, which imports every difference that predates the task.

### F330 — the whole checkpoint cycle, measured: 0.16 s to take, 0.02 s to diff, 0.25 s to hand to an isolated attempt, 0.06 s to undo — and the identifier is collectable

`checkpoint.py` runs the cycle W3 asked for, in a throwaway clone of claudette (495 files) carrying
a 4 MB ignored build artifact, with an agent that edits two tracked files, creates three, deletes
one, and rewrites the build output:

| step | mechanism | cost | result |
|---|---|---|---|
| snapshot the pre-image | temp index → `write-tree` → `commit-tree` | **0.157 s** | one sha |
| snapshot the post-image | the same | **0.171 s** | one sha |
| the change list | `git diff --name-status S0 S1` | **0.024 s** | **exactly the 6 paths, and no ignored file** |
| isolate at a state | `git worktree add --detach <dir> S1` | **0.251 s** | 497 files: the created files present, the deleted one gone, no build cache |
| restore the pre-image | `read-tree -u --reset S0` + `clean -fd` | **0.058 s** | byte-exact against the pre-attempt fingerprint; the build cache untouched |

Four things this settles.

**The identifier exists and it is a commit sha.** `git worktree add` takes any commit, and a
snapshot *is* a commit, so the operator's uncommitted work — including files git has never tracked —
can be handed to an isolated attempt without committing anything to a branch, polluting the reflog,
or touching the operator's index.

**The change list is free and it is the structural check.** Item 4's one instrument that fires
(*did the change touch any source file*) is a diff between two snapshots, at 0.024 s, with the
ignored build output excluded by construction. No directory walk, no CRLF normalisation, no
deny-list of extensions: `.gitignore` already answers "is this a source file" for the repository it
belongs to.

**The restore is exact and it leaves the build cache alone.** `clean -fd` without `-x` removes what
the agent created and keeps `target/`, which is what makes the next attempt cheap (F331).

**And the identifier is collectable.** An unreferenced snapshot commit did **not** survive
`git gc --prune=now` — neither did S0 or S1 — while the one written to `refs/abcc/checkpoints/probe`
did. Git ran gc in 0.47 s here, and `gc --auto` runs on its own schedule inside ordinary commands.
So the checkpoint row may carry the sha, but the *mechanism* must write a ref: **an identifier with
no reference is a promise of resumability that the storage layer is entitled to break.**

One caveat, and it is the same axis as F328. The snapshot goes through git's own filters, so what it
captures is the repository's *normalised* content. Claudette's `.gitattributes` says `* text=auto
eol=lf`; the probe's agent wrote CRLF; the working file held **219 CRLF**, the snapshot blob **0**,
and the worktree materialised from it **0**. The trees are identical ignoring CR and not identical
byte for byte. For a checkpoint whose contract is *restore the workspace*, the honest statement is
**restore up to the repository's own text attributes** — which is what its own tools would do to
those bytes at the next `git add` anyway, and is not what a `robocopy` pre-image would have done.

### 🚨 F331 — the cold build is not the price of isolation: 56.6 s cold, 24.7 s for a worktree created after the cache is warm, 0.4 s for one that is

W11 F249 measured isolation at ~4.7× on this Rust workspace and explained it in a clause: *"a fresh
worktree does not share `target/`, so every isolated attempt pays a cold build."* The clause is an
assumption about cargo, and `CARGO_TARGET_DIR` is a documented environment variable, so it is
testable. `cargo test --workspace --no-run --offline`, on worktrees of `claudette`:

| phase | build directory | wall | crates compiled |
|---|---|---|---|
| cold, private `target/` inside the worktree | its own | **67.7 s** | 204 |
| cold, shared `CARGO_TARGET_DIR`, empty | shared | 62.4 s | 204 |
| a *second* worktree onto that warm shared directory | shared | **0.46 s** | **0** |
| the same worktree again, nothing changed | shared | 0.47 s | 0 |
| one source file edited | shared | 3.7 s | 1 |
| **a worktree created *after* the cache was warm** | shared | **24.7 s** | **1** |
| that worktree, second run | shared | 0.43 s | 0 |
| back to the first worktree | shared | 0.41 s | 0 |
| **a copied tree with no `.git` at all** (`checkout-index`) | shared | **25.0 s** | **1** |

The third row is the one that looks too good, and the sixth is why it is reported separately. Cargo
decides freshness by mtime, and in the third row both worktrees predated every artifact, which is
the favourable case. `freshwt.py` runs the realistic one — cold-fill the shared directory from one
worktree, *then* create the second, so every source file is newer than every artifact (asserted:
`src_newer_than_cache: true`). That worktree recompiles the workspace crate and relinks the test
binaries — **one crate, 24.7 s** — and does not touch the 204 dependencies. Its second run is 0.43 s,
and the first worktree is still 0.41 s, so the two do not thrash each other.

The last row matters for the subjects that have no git at all: a tree materialised by
`git checkout-index`, with no `.git`, gets the same 25.0 s. **The build cache does not care how the
tree was made; it cares where the artifacts live.**

So the price of isolating an attempt on a real Rust project is **24.7 s once, then 0.4 s**, plus
0.30 s for the worktree — not a 104 s cold build. The 4.7× F249 measured is real and it is the price
of a *fresh clone with its own build directory*, which is one implementation of isolation and the
most expensive one. Disk follows the same split: a private `target/` is **2.90 GB per attempt**; one
shared directory is 2.93 GB total.

The tested condition is two worktrees at the same commit, which is the shape of two attempts at one
task. Two attempts at *different* commits share the 204 dependency units (same versions, same
features) and differ in the workspace crate, so the shape should hold; that case is not measured.

### F332 — what serializes two isolated attempts is cargo's package-cache lock, and a private build directory does not remove it

Both concurrency phases print the same line, three times each, in both configurations:

```
    Blocking waiting for file lock on package cache
```

| phase | build directories | wall | per-attempt |
|---|---|---|---|
| two attempts, one shared `CARGO_TARGET_DIR` | shared | 4.06 s | 4.06 s / 3.93 s, blocked |
| two attempts, one private target each | separate | 4.78 s | 4.78 s / 4.77 s, blocked |

The lock named is not the build directory — it is `CARGO_HOME`'s package cache, which both processes
share because they share `~/.cargo`. **Isolating the workspace does not isolate the toolchain's
global state**, and the contention survives every workspace-level mechanism in this item. At this
size it costs well under a second and the honest reading is "free"; the reason to record it is that
the *shape* is the one that bites later — the same shared-state seam covers a package manager's
global cache, a language server, a docker daemon, and a `~/.npm` or `~/.cache/uv`. If it ever
matters, the fix is a per-attempt `CARGO_HOME`, which costs a registry copy; that is not measured
here and should not be built before something needs it.

### 🚨 F333 — the 32 GB answer: one cold build takes the box from 17.6 GB free to 9.6, two at once take it to 2.3, and the second one saves at best a sixth of the wall clock

RAM sampled every 400 ms across every phase, with **no model resident** — the optimistic case, since
the champion is 13.6 GB of VRAM and a live `llama-server` also holds host memory:

| phase | processes | peak toolchain working set | free RAM |
|---|---|---|---|
| one cold build | 21 | 11.6 GB | 17.6 → **9.6 GB** |
| one incremental build (1 crate) | 6 | 2.5 GB | 15.0 GB |
| two incremental builds at once | 12 | 5.3 GB | 12.6 GB |
| **two cold builds at once** | **42** | **23.3 GB** | 17.5 → **2.3 GB** |

An independent sampler run from a separate shell agreed within noise on the last row (21.6 GB peak,
2.2 GB free). Summed working sets double-count shared pages, so the free-RAM column is the honest
one; both agree on the shape.

And the second build buys little: **110.8 s for two at once, against 113–135 s for the same two in
sequence** — the four cold builds measured in this item span 56.6 s to 67.7 s, so the saving is
somewhere between 2% and 18%, on six physical cores that one cargo build already saturates. So the answer to
the brief's question is not a per-worktree RAM figure at all:

> **Isolate the workspaces; serialize the gate.** Two isolated attempts are cheap to *hold* — 0.30 s
> and 9.4 MB each, plus one shared build cache — and expensive to *build* at the same time. W2's cap
> of two concurrent builders (F83) is a statement about the model server, where the second sequence
> buys +69% throughput. At the build, the second concurrent job saves at best a sixth of the wall
> clock and costs 87% of the box's free memory.

That is a one-line rule for the runtime W3 designed: the build/test rung is a single-flight
resource, like the model swap, and it belongs behind the same kind of permit.

### 🚨 F334 — a worktree contains the repository and none of the toolchain: 0.8–64 MB of tracked tree against 1.7–25.5 GB of ignored environment

`toolchain.py` creates a fresh worktree of each repository, resolves item 5's profile in both trees,
and runs one command in each:

| repo | the worktree | what git ignores | markers, main → worktree | executed check, main → worktree |
|---|---|---|---|---|
| bcf | 0.8 MB / 62 files | 1.7 GB / 2,244 (`target/`) | Cargo.toml ×1 → ×1 | `cargo metadata --offline` **101 → 101** |
| claudette | 4.7 MB / 495 | 25.5 GB / 55,135 (`target/` 25.2 GB; battery `work/`; the vscode extension's `node_modules`) | Cargo.toml ×2, package.json ×1 → same | `cargo metadata --offline` **0 → 0** |
| v1 | 63.7 MB / 540 | 3.9 GB / 230,652 (`node_modules/` ×4, `workspace/`, `dist/`) | package.json ×6 → **×5** | `require.resolve('typescript')` **0 → 1** |
| abcc20 | 9.4 MB / 1,080 | 5.7 GB / 56,388 (`runs/` 3.2 GB, four `target/`s) | 4 toolchains, 17 sites → **2 toolchains, 7 sites** | `require.resolve('typescript')` **0 → 1** |

The profile's *markers* are tracked, so where a marker is tracked it resolves identically in the
worktree — item 5's detector needs no isolation-specific work. Everything the marker *names* is
ignored by design, which is the whole point of ignoring it, and so the isolated tree cannot run the
command the profile chose. In v1's main tree `require.resolve('typescript')` answers with a path
inside `node_modules/.pnpm/`; in the worktree it throws `MODULE_NOT_FOUND`.

Three specifics worth keeping:

- **v1's own agent workspace is gitignored.** The package.json that exists in the main tree and not
  in the worktree is `workspace/package.json` — the directory every agent container mounts (F326).
  The tree v1's agents actually work in is invisible to any git-based isolation, in v1's own layout.
- **The markers can be mostly ignored files.** This repository declares cargo, npm, python and go
  across 17 sites; 10 of them are spike output under `.gitignore`, so the worktree sees 7. A
  detector that runs in the operator's tree and a detector that runs in the attempt's tree do not
  agree, and the one that matters is the second.
- **Detection is not resolution.** `go` is declared by three marker files here and **is not on this
  machine**; `pnpm` — the package manager v1's own lockfile names — is not installed either; and
  BCF cannot resolve its own dependency graph offline in *either* tree (`failed to download js-sys
  v0.3.91`, rc=101 both). Only the last of those is a fact about isolation, and it is a fact about
  isolation only in the sense that isolation did not cause it.

And the population this project has actually measured has no git at all: **0 `.git` directories in
the entire corpus** — every one of the 952 Q56 cells and 431 K attempts ran in a plain directory
built by `w8-corpus`'s file plan (`workdir.rs`), median 8 KB and 10 files, 2.78 GB for the whole
campaign. Whatever 2.0 ships must degrade to that copy, and the copy is cheap exactly when the
subject is a fixture rather than a working repository.

### F335 — OQ-W6-11 answered: the tree decides, the repository may override, the log records, and the attempt re-resolves

Item 5 left the question of where the toolchain profile lives — a table shipped with 2.0, a file in
the repository, or both — and who writes it for a repository 2.0 has never seen. The four
repositories answer it between them.

**A table shipped with 2.0 cannot be right**, because the profile is not one row. `claudette`
declares cargo twice and npm once; this repository declares four toolchains at seventeen sites, of
which one is the real project and the rest are fixtures and spikes. The unit is a **directory**, not
a repository, and item 5's console line already had the right shape: `cargo · pytest · no runner for
web/`.

**Detection is the default and it travels for free** (F334): markers are tracked, so a checkout, a
worktree and a `checkout-index` copy all resolve the same profile. Nothing has to be written for a
repository nobody has seen — the tree is asked, not the model (F315's lesson) and not the operator.

**A file in the repository is the override, and it must be a tracked file** — precisely so that it
travels to the isolated tree the way the markers do. The precedent is this project's own corpus:
`corpus/subjects/<id>.toml` carries markers, capabilities and a `[quirks]` block written by hand
after something surprised the harness, and it lives *with the harness*, not inside the subject. The
difference for 2.0 is the direction of ownership — 2.0 does not own the repositories it is asked to
change, so its override belongs in the repository as an opt-in file, and its fallback belongs in the
mission record.

**The resolved profile is data on the event log**, not a computation repeated per rung. W3's log
already carries what the operator saw; the profile is the same kind of fact — resolved once at
mission start, replayable, and diffable when a run behaves differently on Tuesday because someone
installed `go`.

**And the attempt re-resolves.** F334's abcc20 row is the reason: the profile resolved in the
operator's tree names ten sites that do not exist in the attempt's tree. A profile is a fact about a
*directory at a time*, and an isolated attempt is a different directory.

## Options compared

Scored against what W3 actually asked for — an identifier that restores a workspace — plus what item
4 needs from the same mechanism (a change list) and what this box can afford:

| | captures created files | restores exactly | works with no git | leaves the build cache | to take | to isolate at it |
|---|---|---|---|---|---|---|
| **worktree at a snapshot commit** | ✅ (F330) | ✅ byte-exact up to text attributes | ❌ | ✅ | 0.16 s | 0.25 s |
| worktree at `HEAD` | ❌ — the operator's uncommitted work is invisible | n/a | ❌ | ✅ | — | 0.08–0.66 s |
| `git stash create` object | ❌ **no `--include-untracked`** (F329) | partial | ❌ | ✅ | 0.05–0.07 s | via `stash apply` |
| `git stash push -u` | ✅ | ✅ | ❌ | ✅ | mutates the working tree | — |
| copied pre-image (`robocopy /E`) | ✅ | ✅ bytes | ✅ | ❌ it copies that too | 6–136 s, 1.7–25.5 GB | free (it *is* the tree) |
| copied file plan (`workdir.rs`) | ✅ | ✅ | ✅ | n/a — fixtures have none | ~8 KB median | free |
| no isolation (v1) | n/a | ❌ | ✅ | ✅ | 0 | 0 |

The first row wins on every column that is not "works with no git", and the last two rows are the
answer to that column: when the subject is a fixture rather than a repository, the copy is 8 KB and
the question does not arise.

## Recommendation

**1 — The checkpoint identifier is a commit sha, produced by a temp-index snapshot, and written to a
ref.** The recipe, measured at 0.16 s on a 495-file tree and 0.31 s on a 1,079-file one (0.39 s
on v1's, where `add -A` re-hashes the 241 files that were already divergent):

```
GIT_INDEX_FILE=<scratch>  git read-tree HEAD
GIT_INDEX_FILE=<scratch>  git add -A
GIT_INDEX_FILE=<scratch>  git write-tree                          -> tree
GIT_INDEX_FILE=<scratch>  git commit-tree <tree> -p HEAD -m "..."  -> the identifier
                          git update-ref refs/abcc/checkpoints/<mission>/<seq> <sha>
```

It touches neither the index nor the working tree, it captures the files the agent created, and the
last line is not optional: an unreferenced snapshot does not survive `git gc --prune=now` (F330).
This is what W3 item 4's checkpoint row carries, and `Holding`/fork may promise resumability exactly
when it is present.

**2 — Isolation is a worktree at that sha, with one shared build directory.** 0.25 s to create,
2.90 GB *not* spent per attempt, and the first build in a tree created after the cache is warm costs
**24.7 s rather than 57** (F331). `CARGO_TARGET_DIR` is the Rust instance of a general rule: the
toolchain profile (item 5) gains one field — *where this toolchain's build cache lives* — and 2.0
sets it per repository, not per attempt.

**3 — When the subject has no git, copy the file plan, never the directory.** 0 of this project's
corpus is a git repository (F334); `workdir.rs` already copies an explicit, load-time resolved file
list at a median 8 KB per cell. Two rules the probes bought the hard way (F327): the destination
lives **outside** the tree being copied, and the cleanup uses the `\\?\` extended-length form,
because a copy can contain a name Windows will not delete.

**4 — The change list is the diff between two snapshots, and it is item 4's structural rung.**
0.024 s, exactly the six paths the agent touched, ignored build output excluded by construction
(F330). It replaces the directory walk *for a git subject*, and it answers the deny-list question
item 5 left open — `.gitignore` is the repository's own answer to "is this a source file". Two
warnings attached: never diff a snapshot against `HEAD` (F329 — v1's tree would report 241 phantom
files), and never ask `git status` what changed (F328 — it answers from a stat cache).

**5 — Isolate the workspaces; serialize the gate.** Holding N isolated attempts is cheap; building
two at once is not — 110.8 s against 113–135 s in sequence, and 2.3 GB of free RAM left on a
31.9 GB box with no model loaded (F333). The build/test rung is a **single-flight resource**, behind the
same kind of permit W2 gave the model swap. W2's cap of two concurrent builders is about the model
server, where the second sequence is worth +69%; at the build the second job is worth at best a
sixth of the wall clock.

**6 — State the restore contract as *up to the repository's text attributes*, and mean it.** The
snapshot round trip normalises line endings the way the repository's own `.gitattributes` says
(219 CRLF in, 0 out, F330), and the repository with no such rule accumulated 241 divergent files
without noticing (F328). Both are the same requirement: 2.0 must never claim a byte-exactness it
does not have, and the honest claim is the one git itself makes.

**7 — Any 2.0 code that writes inside `.git` must handle the pointer file.** In a worktree `.git` is
a file, not a directory. Claudette already met this and chose to degrade silently — its mission
marker lands in the PR rather than in `.git/info/exclude` (`missions.rs:428-441`). 2.0 should ask
`git rev-parse --git-common-dir` and treat "this is a worktree" as the normal case, because under
this recommendation it *is* the normal case.

## Rejected alternatives and why

- **"Copy the working directory per attempt."** 6–136 s and 1.7–25.5 GB on the four repositories
  here, against 0.08–0.66 s and 0.8–63.7 MB for a worktree. It also follows pnpm's 2,859 junctions
  until it is killed, copies its own destination when the scratch directory is inside the tree, and
  can leave behind a directory Windows refuses to delete by name (F327). The copy survives in
  exactly one role: a subject with no git, where the file plan is 8 KB.
- **"Give each attempt its own `target/`."** 2.90 GB and 57–68 s per attempt, and running two of
  them at once takes the box to 2.3 GB free for at best a sixth of the wall clock (F331, F333). A shared build directory costs one lock message.
- **"Use `git stash` for the pre-image."** `create` cannot see the files the agent wrote (F329), and
  `push -u` gets them by mutating the working tree — the one thing a checkpoint must not do.
- **"Run more attempts in parallel; the box is idle."** It is not. The model saturates at two
  sequences (W2 F83), and one cargo build already saturates six physical cores.
- **"Lock files, like v1."** Three surfaces, none of them reachable from the agent that writes
  (F326). Isolation has to be enforced where the path is resolved, and a worktree does exactly that.
- **"Require the subject to be a git repository."** 0 of the 1,383 measured cells in this project's
  own corpus is one (F334).
- **"A container per attempt."** F95/F125 already ruled out daemons for 2.0's runtime, W3 put the
  isolation boundary at the tool child, and nothing measured here needs more: the expensive part of
  an attempt is the build cache, which a container would have to share anyway.

## Effect on fun

A checkpoint sha is a save game, and it costs 0.16 s. That is the difference between a command
centre that can offer *"roll this attempt back"* as a button and one that can only offer an apology:
the restore is 0.06 s and exact, and the operator can be shown, before pressing it, precisely which
six paths will change. W5's verb set asked for undo as a first-class thing; this is the mechanism
that makes it honest rather than aspirational.

The change list is the other half, and it is free. A unit that reports *"3 files, +41 −6, `target/`
untouched"* the moment it finishes has said something true and checkable, and the same diff drives
the map view: which files the fleet has touched this mission, drawn from data that already exists.

The single-flight build is the one that will *look* best. A queue where one unit is at the forge and
the others are visibly holding is a strategy game's natural shape, it is honest about the hardware,
and it turns the box's real constraint into something to watch rather than something to explain. The
alternative — two builds squeezing a 31.9 GB box down to 2.3 GB free for a fraction of the wall
clock — is both riskier and duller.

## Open questions

| # | Question | Waiting on |
|---|---|---|
| OQ-W3-12 | The workspace checkpoint marker: worktree, stash object, or copied pre-image | **answered here**: a temp-index snapshot commit *plus* a worktree at it (F329, F330), degrading to the copied file plan when the subject has no git (F334) |
| OQ-W6-11 | Where the toolchain profile lives, and who writes it for an unseen repository | **answered here** (F335): the tree decides, a tracked file may override, the log records, and the attempt re-resolves |
| OQ-W6-14 | Two attempts at **different commits** sharing one build directory — the 204 dependency units should still be shared, but this was measured at the same commit only (F331) | a second measurement, cheap, once 2.0 has two real attempts |
| OQ-W6-15 | Does package-cache contention (F332) ever cost enough to justify a per-attempt `CARGO_HOME`, and what does a registry copy cost? | nothing yet — do not build it before something needs it |
| OQ-W6-16 | The no-git subject with a large tree: at what size does the copied pre-image stop being affordable, and what does `Holding` say when it refuses? | W3's contract table, when the first non-fixture subject appears |
| OQ-W6-8 | Does the coverage fraction bind as a veto, or only as a report? | still open (item 5) |
| OQ-W6-7 | *(item 2)* Rules-only router, or rules plus a recorded model reading? | still open |

## Confidence: high on the mechanism costs and the checkpoint cycle, medium on the build-cache generality

Everything in this item was executed on this machine, against the repositories 2.0 will actually be
pointed at, and the two headline corrections are both cases where reading would have got it wrong:
`git stash create` looks like the obvious pre-image until it is run against an untracked file, and
W11's *"a fresh worktree does not share `target/`"* survives three careful readings and dies to one
environment variable.

The checkpoint cycle is the strongest part: snapshot, change list, isolate, restore and gc, each
measured, with the restore verified by hashing every file rather than by reading git's opinion of
it. The mechanism costs are n=3 on four real repositories spanning 61 to 1,079 tracked files and
0.8 MB to 25.5 GB of ignored environment.

Three limits. **The build-cache result is one project, one toolchain, and two worktrees at the same
commit** — the shape should hold for any content-addressed dependency cache, and the two cases that
would test it (different commits, a second language) are OQ-W6-14. **The RAM numbers are this box
with no model resident**, which is the optimistic case and still lands at 2.3 GB free; with the
champion loaded the honest figure is worse by whatever `llama-server` holds in host memory, which
was not measured here. And **the copy row for v1 is a bound, not a time**: a faithful copy of a pnpm
tree was not achievable with the platform's own tool, so 58 s buys a tree whose `node_modules` is
missing 2,859 links, and the naive copy was killed at 190 s rather than finished.

One measurement here is about the machine rather than about any mechanism, and it is worth saying
plainly: **the v1 donor's working tree holds 241 tracked files that differ from what git recorded**,
and nothing in this item put them there. `stale.py` reports them, and the probe restored the mtime
it found, so that repository is exactly as it was.

---

# Item 7 — verifying the unrunnable

## Question

§11's line is *"Verifying documentation and review output where there is no test to run.
LLM-as-judge reliability and its known failure modes."* It carries a trap that has to be
disarmed before any number is quoted: **a population with no test also has no ground truth**,
so a reliability figure measured on one is an opinion about an opinion. Every donor number in
this family has that shape — BCF's 7.5 average, v1's graduated review, the +3.65 critic
inflation — and item 1 voided them for exactly this reason.

So the question is asked in three parts, each with an answer key:

1. **OQ-W6-13, inherited from item 5.** The Q56 `control` and `gated` arms hold 29 real
   failures on which no deterministic rung in five languages fires (F321, F322). What *are*
   they? They are also the closest thing this project has to the unrunnable case with an
   answer key: the visible suite is green on every one, so at the moment the agent stopped
   there was no test it could have run that would have told it the truth — and the hidden
   reviewer tests are a key nobody in the loop can see.
2. **What does a model reviewer buy on exactly that population**, shown exactly what the agent
   could see? And does *demanding a concrete input* — a review finding shaped `call → expected
   → actual` rather than a paragraph — change the answer, and can the finding then be run?
3. **What holds for documentation**, which is the artifact the brief actually names: what can a
   free mechanical rung check, what needs a reader, and which of the LLM-as-judge failure modes
   in the literature reproduce on this model on this box?

## Method

Eight probes in `research/spikes/w6-judge/`. Two populations, both with ground truth that was
re-measured rather than read; three of the eight execute donor code rather than paraphrase it.

- **The 29, assembled and classified.** `common.py` joins item 4's re-run verdicts
  (`../w6-headroom/results-q56.json`, the suite verifier re-executed rather than the campaign's
  recorded verdict) to the preserved workdirs, strips the verifier's own residue — showing a
  judge the hidden tests is showing it the answer key — and deduplicates by the content of the
  tree the agent left: **29 failure cells are 23 distinct trees, and the 36 clean-arm passes on
  those same tasks are 34** (12 of the 13 tasks have one; Q03 has none), so 57 trees over 65
  cells. `census.py` dumps ticket, diff, reference
  solution and hidden assertions for every failing tree; `taxonomy.py` carries the hand
  classification and **asserts every quoted ticket clause is a substring of the ticket the agent
  was actually given**, because a classification whose evidence is a quotation is worth nothing
  until the quotation is checked.
- **The champion as reviewer, two arms, same 57 trees.** `judge.py` shows the ticket, the files
  the agent left and the fact that the project's own tests are green — and nothing else. The
  `verdict` arm returns the VerdictWire schema W11 item 3 shipped (rationale, defects, then
  `call` last, which F263 says is not a style choice). The `edge` arm returns the same context
  under a schema that demands concrete cases: `why`, `call`, `expected`, `actual`.
- **Running the reviewer's own findings.** `check.py` takes every case the `edge` arm named,
  wraps it in a per-language driver (a Rust `examples/` binary under `catch_unwind`, a Python
  driver, a node/TypeScript dynamic import, a bash command line), and runs it twice — against
  the tree the agent left and against the suite's reference solution. A case where the two
  disagree is a finding that is *true*; a case where they agree is a finding that is *false*,
  however well argued; a case that will not run is not a finding. The reference solution is an
  oracle that would not exist in a real run: what the number is for is the precision of a model
  reviewer's concrete claims, which is a property of the reviewer.
- **The free rung for prose, on a real corpus.** `citations.py` runs an address-level check over
  **44 authored documents, 1.75 MB** — this repository's research documents, the harness
  crates' READMEs, the prestudy dossiers, the corpus SPEC and the brief — resolving finding
  numbers, open-question ids and `file:line` citations against this repository and the three
  donor checkouts, and checking fenced code quotations line for line against the file they cite.
- **A real document with planted defects.** `docgate.py` takes `docs/status_lifecycle.md` from
  the K suite's `finish_the_cancelled_status` and the reference solution it describes — a
  document that is true of its code sentence by sentence — and builds seven variants, each with
  exactly one planted defect applied as an anchored substitution. Six are false statements about
  the code; the seventh states nothing false and drops three of the five rules, which is F281's
  shape. Three arms: the pointwise gate, position bias (every pair in both slots) and verbosity
  bias (the faithful document against itself padded, and the padded *defective* document against
  the terse faithful one).
- **The donors, executed rather than read.** `v1_review.mjs` ports v1's `getReviewDecision`
  (`codeReviewService.ts:110-160`) and the router's type switch (`taskRouter.ts:200-213`)
  byte-for-byte from `d5528ea` and runs them over the donor's own unit-test inputs and over four
  synthetic task streams. `bcf-doc/` takes a path dependency on the pinned BCF checkout and calls
  `verifier::verify_project` on a three-file documentation project, which is the artifact the
  brief names arriving at the donor's own gate.

Held constants: champion `qwen3.6-35b-a3b-mtp@iq3_s` at `-c 65536 --gpu max --parallel 1`,
temperature 0, `max_tokens` 8192, schema-constrained; the server's command line records
`--cache-type-k/v q8_0 --flash-attn on --kv-unified --batch-size 2048 --spec-type draft-mtp`.
Donor commits v1 `d5528ea`, BCF `d6c1601`, Claudette `af3f804`.

## Inherited

| What | Source | Verdict here |
|---|---|---|
| "No rung fires on any of the 29" | item 5, F321/F322 | **CORRECTED** — one does, and it is noise: `ruff` TRY004 on one Q51 tree, the same lint firing on two *correct* answers to the same task (F336) |
| The verdict has no score | W11 item 3, F247 | **KEEP** — the binary is what a gate consumes, and this item measures the binary and the case list separately |
| Reasoning first, decidable field last | W11 item 3, F263 | **KEEP, and it is not enough** — the ordering survives, and the field still contradicts the reasoning above it (F339) |
| A reviewer is decided by what it is shown | W11 item 4, F280–F282 | **EXTENDED** — the *schema* is the other half: the same model, same context, changes verdict when the output shape demands a concrete input (F339) |
| Generated criteria carry no positive control | W11 item 4, F277 | **ANSWERED for review output** — a case shaped `call → expected → actual` has one for free: run it on the pre-image (F340) |
| Generated tests ratify a wrong change | item 4, F305 | **CONFIRMED on real agent behaviour** — three of the 23 wrong trees ship the agent's own green tests, one of which asserts the opposite of the hidden test (F337) |
| A project BCF cannot read scores 5.0 | item 5, F313 | **KEEP, and it settles the doc case** — a documentation deliverable is that case exactly: 7.00 with a perfect critique against a lowest gate of 8.00 |
| `Option<bool>` for "could not run" | item 5, F317 | **KEEP, and it is incomplete** — the successor's own check folds "no checker for this artifact" into the same variant as "the feature is off" (F348) |

## Findings

### 🚨 F336 — OQ-W6-13 answered: the 29 are one class of mistake, and the axis that matters is not the language but whether the ticket's own words decide the case — 8 of 29 they do, 12 of 29 nothing does but the domain, and 2 are not reasoning failures at all

Item 5 left the question as an open row: *"The Q56 clean arms hold 29 real failures and no rung
fires on any of them. What are they? K's taxonomy (F302) does not transfer — these are one-file
tasks where the file was always written."*

They are, without exception, **the same mistake**: the code does the stated main case and gets a
boundary wrong. Every one of the 23 distinct trees compiles, lints, type-checks and passes the
visible suite; every one is a plausible answer a competent reader would sign off; and every one
dies on exactly one input. That is why no rung fires — there is nothing malformed to find.

What separates them is **what decides the failing input**, and that axis is the one that sets
whether a reviewer with no tools could possibly catch it:

| class | what decides the case | trees | cells | languages |
|---|---|---:|---:|---|
| `stated` | the ticket's own words fix the expected value | 8 | 8 | rust 7, shell 1 |
| `signalled` | the ticket has a generality clause pointing at edges and does not say what the answer is | 6 | 6 | python 3, rust 3 |
| `implied` | the ticket does not mention the case; the domain decides it | 6 | 12 | python 4, rust 4, shell 3, typescript 1 |
| `undecided` | neither the ticket nor the domain decides it | 1 | 1 | node 1 |
| `mechanical` | not a reasoning failure: the artifact was mangled, or it does not terminate | 2 | 2 | shell 2 |
| | | **23** | **29** | |

`taxonomy.py` carries the classification with the ticket clause quoted verbatim for every
`stated` and `signalled` row, and asserts each quote is a substring of the prompt the agent was
given. The clauses are things like *"while keeping the split as even as possible"* (Q03),
*"breaking ties alphabetically"* (Q07), *"if END is past the end of input, print through the last
line"* (Q46), *"and for any capacity"* (Q52) and *"Versions with different numbers of components
compare as if the shorter one is padded with trailing zeros"* (Q56) — five sentences that fully
determine the answer, in tickets whose author never wrote a test for them.

Four things in the table are worth pulling out.

**The `implied` class is the biggest by cells and the hardest by construction.** `split_bill(7, 0)`
panics; `total_cents(["5"])` throws because the agent split on `"."`; an `EventEmitter` holding its
listeners in a `Set` fires a twice-registered listener once; `sed -n "5,3p"` prints line 5 for the
range 5..3. Nothing in any of those tickets names the case. The reference solution for Q46
*comments* the trap — "*a start past the end is a degenerate (empty) range. Guard it, because
`sed -n "5,3p"` would otherwise print the single line at the start address*" — which is a task
author writing down the domain knowledge the ticket deliberately withheld.

**The one `undecided` case is the most interesting artifact in the corpus.** Q53's ticket says a
trailing newline must not produce an extra empty row and says nothing at all about empty input.
The agent wrote its own probe file, `_quick_test.mjs`, containing the line
`// Empty input → one empty row (standard CSV behavior)`. It saw the ambiguity, decided it,
recorded its decision in a comment, and decided against the hidden test. There is no reviewer,
model or human, that could have called that wrong from the ticket; what a reviewer could have done
is *notice that a decision was made*.

**Two of the 29 are not model failures.** Q45's whole file is one line —
`` #!/usr/bin/env bash`n# Strip comment and blank lines from stdin.`ngrep -v "^\s*#" ... `` — a
PowerShell backtick-n escape written literally into a bash script, which as bash is a single
comment producing no output at all. `bash -n` is green on it because it is valid; the free
structural check is green on it because the file was modified. Q49's `normalize()` misspells the
character class (`[[:space]]`, not `[[:space:]]`), so `${s#[[:space]]}` strips nothing while the
`[[ =~ ]]` guard keeps matching — measured directly: the regex matches a leading space and the
expansion returns the string unchanged, so the `while` loop never ends.

**And that last one carries a correction to the corpus's own ground truth.** Its recorded verdict
is `FAIL` at **228,287 ms**, against a 130–302 ms median for the same task's other cells. Re-run
here under a 300 s cap it does not terminate and returns **no verdict at all**. So one of the 29
"failures" is a hang whose recorded classification depends on who killed it and when — which is
item 2's `Uncertain(timeout)` rule arriving as data rather than as a design preference.

**One further correction, to item 5's own headline.** F321 and F322 say no rung goes red on any of
the 29. Re-reading the same cells rung by rung, **one does**: `ruff` reports `TRY004` on the Q51
tree that raises `ValueError` for a non-`str` argument. It is not a detection. The same lint fires
on **two of the correct answers to the same task** and on none of the others, and the line it
flags has nothing to do with the whitespace handling that fails. The honest statement is *one of the
twelve rungs goes red on one of the 29 failures, and that specific lint goes red on BOTH of the two
correct answers to the same task and on one of its three wrong ones* — while `ruff` across the clean arms is red on 12 of 251 correct
trees against 1 of 29 wrong ones. That is the shape item 5 already found in Rust (F320) and item
4's own lesson restated: a linter's reds are a property of the code's style, not of its
correctness.

### 🚨 F337 — the agents wrote 22 tests of their own, all green, on trees that are wrong — and writing tests is not a signal of correctness at all

Item 4 measured generated tests on constructed artifacts and found them ratifying a wrong change
6 of 9 times when written after it (F305). Here the same thing happens unprompted, in the real
population, and it can be counted because the agent's tests are in the tree it left.

| | rust/python trees | trees that added `#[test]` / `def test_` | assertions added |
|---|---:|---:|---:|
| wrong (`FAIL`) | 16 | **3** | **22** |
| right (`PASS`) | 18 | 2 | 15 |

Every one of those 22 assertions passes: `cargo test` is green on all 14 Rust failure cells.

The Q52 tree is the clearest. The agent implemented a ring buffer and wrote **eleven** tests of
its own — under capacity, exactly full, overwrite, multiple wraps, capacity 1, order preservation
after two overwrites, `to_vec` on empty, cloning a `String` — and not one of them is
`RingBuffer::new(0)`, which is the case the ticket's *"and for any capacity"* names and the hidden
test checks. The agent's tests cover the shape of the problem it was thinking about. Q01 is the
same: five new tests for punctuation, repeated spaces, leading and trailing space, unicode and
empty input, and none for feeding a slug back in, which is the one that fails.

And the node tree is worse than uninformative. Q53's agent added `_quick_test.mjs` and used it to
**record the wrong convention as a comment** rather than to test anything —
`// Empty input → one empty row (standard CSV behavior)`, with a `console.log` and no assertion.

The rate is the finding: **3 of 16 wrong trees wrote tests against 2 of 18 right ones.** A tree
carrying the author's own green tests is not more likely to be correct, and a gate that counted
"the agent wrote tests" as evidence would be reading noise. This is the mechanical reason item 4's
recommendation — generated tests are advisory, never binding — survives contact with real agent
behaviour.

### 🚨 F338 — a model judge shown a green measurement approves 19 of 22 wrong answers, and the three it catches are all cases the ticket's own words decide

The `verdict` arm shows the champion the ticket, the files the agent left, and one measurement —
*the project's own test suite is green* — and asks for the VerdictWire schema W11 item 3 shipped.
That is the entire information set the agent itself had. 57 trees, temperature 0, one call each.

| truth | call | trees | cells |
|---|---|---:|---:|
| FAIL | `fail` | **3** | 3 |
| FAIL | `pass` | 19 | 25 |
| FAIL | *(empty payload)* | 1 | 1 |
| PASS | `pass` | 32 | 34 |
| PASS | `fail` | 1 | 1 |
| PASS | *(empty payload)* | 1 | 1 |

**3 of the 22 wrong trees that got an answer are caught. 1 of 33 correct trees is failed.** Split
by F336's axis, the three catches are not distributed at random:

| class | wrong trees | caught |
|---|---:|---:|
| `stated` | 8 | **2** |
| `signalled` | 6 | **1** |
| `implied` | 6 | 0 |
| `undecided` | 1 | 0 |
| `mechanical` | 2 | 0 |

All three are real and correctly diagnosed. On Q56 the rationale is *"the current logic immediately
returns `Ordering::Greater` … without checking if the remaining components in the longer version"*
are zero; on Q46 it identifies the `head | tail` pipeline and the edge the ticket names; on Q51 it
quotes the regex and explains that it permits a space between a number and its unit but not
between units. **A reviewer with no tools, reading the ticket carefully, catches the cases the
ticket decides and nothing else.** That is a completely reasonable thing for a reader to be, and it
is not a gate: an instrument that a wrong answer walks past 86% of the time is a report.

Three things about the misses matter more than the rate.

**The model is not blind to the edge; it argues the edge away.** On the Q03 tree whose remainder
distribution is correct and which panics at `people == 0`, the rationale says so explicitly and
then dismisses it: *"The only edge case is `people == 0`, which causes a division-by-zero panic.
However, this is standard Rust behavior for invalid input and falls outside the scope of the
ticket's requirements."* The hidden test disagrees. Nothing about that reasoning is careless — it
is a scope judgement, made in the absence of anyone to ask, and it is the `implied` class's whole
difficulty in one sentence.

**Two calls of 56 spent the entire 8,192-token budget on reasoning and returned an empty string.**
`finish_reason: length`, `completion_tokens: 8192`, `reasoning_tokens: 8192`, content `""`. That is
F282's and F284's failure mode reproduced on the champion in the Judge role, at **3.6%** — low, and
not zero, and a gate that treats a missing payload as anything but `Uncertain` is deciding by
coin-flip 1 time in 28.

**And the single false-fail is the most instructive row in the table.** On a *correct* Q45 tree the
model produced a well-formed verdict whose rationale argues, correctly and in detail, that the
solution is right — and then stops mid-sentence at *"ignoring inline hashes (e.g., `` `code =  ``"*,
emits `"defects": []`, and emits `"call": "fail"`. `finish_reason` is **`stop`**; 992 completion
tokens; the JSON parses; the schema is satisfied. **A gate reading `call` gets a red with no defect
attached and a rationale that says the code is fine.** No schema catches this, because the schema
is not violated. The cheap defence is a consistency rule the type system can carry — a `fail` with
an empty defect list is not a verdict — and it is the same shape as item 1's diagnosis: the family's
verification failures are defaults that pretend to be measurements.

### 🚨 F339 — the same model, the same trees, one field changed in the schema: 2.8× the decode, 30% of the calls destroyed, and a binary that catches three either way but not the same three

The `edge` arm is the `verdict` arm with exactly one thing different — the output schema. Same 57
trees, same model, same context, same temperature, same 8,192-token budget. Where `verdict` asks
for a rationale, a defect list and a `call`, `edge` asks for a rationale, a list of cases shaped
`{why, call, expected, actual}`, and the same `call`.

| arm | median completion tokens | median reasoning tokens | median wall | hit the 8,192 cap | empty payload |
|---|---:|---:|---:|---:|---:|
| `verdict` | 2,472 | 2,267 | 38.3 s | 2 | 2 |
| `edge` | **6,870** | **6,729** | **104.1 s** | **17** | **17** |

**Asking for a concrete input costs 2.8× the decode and 2.7× the wall clock, and it destroys 17 of
57 calls outright.** Every empty payload in both arms is `finish_reason: length` at the cap — the
model spent the whole budget reasoning and emitted nothing. W11 item 4 called the schema the cheap
intervention next to swapping the model (F280, F284). On this population it is not cheap: per
answered call it costs 2.8× where swapping to the 27B costs 4.6× (F284), and it fails 30% of the
time rather than 3.6%.

The one thing that redeems it is that this failure is *legible*. `finish_reason: length` with an
empty string is a fact the caller can read, and 17 of 17 have it. That is the opposite of F338's
false-fail, where the schema was satisfied, the JSON parsed, and the rationale contradicted the
field. **A budget that runs out is a better failure than a verdict that is wrong**, and a gate that
maps it to `Uncertain` is correct by construction.

The binary is no better under the new schema, and the interesting part is *how* it is no better:

| arm | caught | which trees |
|---|---:|---|
| `verdict` `call == fail` | 3/23 | Q46, Q51, Q56 |
| `edge` `call == fail` | 3/23 | Q07, Q40, Q56 |
| both | **1** | Q56 |
| either | 5 | |

**Two of the three catches do not survive a change to the output schema, in either direction.** The
same model, reading the same tree, at temperature 0, says `fail` under one schema and `pass` under
the other — and Q46 is the instructive one, because under the schema where it said `pass` it also
produced the correct failing input. `call` is not measuring a property of the tree.

And that is the general case, not the exception. Of the 16 trees where the model named at least one
concrete case, **its own `call` agrees with its own cases twice.** Fourteen times it names the
input, states what the code should return, states what it does return — and answers `pass`.

On Q46 the rationale quotes the ticket's own words, *"if START is past the end, print nothing"*,
explains that `head -n "$end"` still reads the whole input, and offers
`printf 'l1\nl2\nl3\n' | bash solution.sh 4 4`, expected empty, actual `l3`. That case is correct:
run it, and the agent's script prints `l3` where the reference prints nothing. The `call` field on
that verdict is `pass`.

Where the cases are, and are not:

| | wrong trees (23) | correct trees (34) |
|---|---:|---:|
| named at least one case | **11** | 5 |
| answered, named none | 6 | 18 |
| empty payload | 6 | 11 |

Twenty cases in total, 15 of them on wrong trees. Of the six wrong trees that answered and named
nothing, five say `pass` — a reviewer that has decided the code is fine is not withholding a case
it has, it does not have one.

### 🚨 F340 — a review finding you can execute is worth three times its author's own verdict: 13 of 15 cases named on wrong trees really discriminate, 10 of 23 wrong trees caught against 1 of 34 false, and that one belongs to the oracle

`check.py` takes every one of the 20 cases the `edge` arm produced, wraps it in a per-language
driver, and runs it twice — against the tree the agent left and against the suite's reference
solution. This is the positive control F277 said the donors' generated criteria never carry, and it
is the only measurement in this item that does not ask anyone's opinion about anything.

| | cases |
|---|---:|
| **discriminates** — the two trees disagree; the finding is true | **14** |
| **agrees** — both trees produce the same value; the finding is false | 5 |
| **unrunnable** — the call does not execute at all | 1 |

Split by whether the tree was really wrong:

| truth | discriminates | agrees | unrunnable |
|---|---:|---:|---:|
| FAIL | **13** | 2 | 0 |
| PASS | 1 | 3 | 1 |

**On the trees that are wrong, 13 of 15 concrete claims are true** — the model that names an input
is usually right about it, which is a different and much better instrument than the model that
names a verdict. By F336's axis: `stated` 7/8, `signalled` 5/5, `mechanical` 1/1, `implied` 0/1.
The class the ticket's words decide is the class whose cases run.

The three gates, all scored over all 57 trees rather than over the 16 that produced a case — the
same three trees F338 reported as 3 of 22, rebased onto the whole population so the four rows are
comparable:

| gate | catches wrong | fires on correct |
|---|---:|---:|
| `verdict` `call == fail` | 3/23 | 1/34 |
| `edge` `call == fail` | 3/23 | 0/34 |
| the reviewer named any case at all | 11/23 | 5/34 |
| **the reviewer named a case that discriminates** | **10/23** | **1/34** |

**Executing the reviewer's own findings triples the recall of the reviewer's own verdict at the
same false-positive rate** — and it does it by throwing away the field the model is most confident
about and keeping the one it can be checked on.

The single false positive is worth more than the ten catches. On a *correct* Q05 tree the reviewer
offered `parse_kv("key=value\n# this is a comment")`, expecting `Ok({"key": "value"})`. Run it: the
agent's tree returns `Err("line 2: missing '=' in '# this is a comment'")` and the reference returns
`Err("malformed line (no '='): \"# this is a comment\"")`. **Both refuse the input. They word the
refusal differently, and a string comparison calls that a difference.** The reviewer was right that
the tree does not accept comments; it was wrong that this distinguishes the tree from the
reference; and the harness was wrong to score two `Err` values as disagreement. **The instrument's
one false positive is the instrument's own equality rule, not the model's claim** — and in 2.0 the
comparison is against the pre-image of the same tree, where a changed error message is a real
change that a reviewer *should* surface.

The unrunnable case is the honest bound. On a correct Q40 tree the reviewer offered three lines of
JavaScript registering two listeners and emitting, with an expectation written as a sentence
(*"Both listeners execute, printing `1` then `2` ... All registered listeners for the event are
invoked exactly once"*). It is a good description of a test and it is not a call. **1 of 20 findings
is prose wearing a schema's clothes**, and the check that catches it is trying to run it.

Two costs to state plainly. Every case is a process — a Rust `examples/` binary under
`catch_unwind`, a `node --input-type=module`, a `bash -c` — and on this box those ran in seconds
against the 104 s median the reviewer took to produce them; **the execution is free next to the call
that generated it.** And `check.py` used the reference solution as an oracle, which does not exist
in a real run. What survives that is the number this finding is for: the precision of a model
reviewer's concrete claims, **13 of 15** on the population where nothing else fires.

### 🚨 F341 — on a document the model names the planted falsehood, marks it `high`, and approves the document anyway: 5 of 8 found, 0 of 8 gated

`docgate.py`'s pointwise arm shows the champion the five modules of the K suite's
`finish_the_cancelled_status` reference solution and one document, and asks whether every claim in
the document is true of the code. Ten documents: the real `docs/status_lifecycle.md`, seven variants
each carrying one planted defect applied as an anchored substitution, and two padded controls — so
**eight defective documents carrying seven distinct defects**, the eighth being `wrong_constant`
again with 350 words appended.

| document | planted defect | defects named | `call` |
|---|---|---:|---|
| `faithful` | — | 0 | `pass` |
| `faithful_padded` | — (plus 350 words) | 0 | `pass` |
| `wrong_constant` | `MAX_ATTEMPTS` is 5; the code says 3 | 2 | `pass` |
| `wrong_constant_padded` | the same, plus 350 words | 2 | `pass` |
| `phantom_symbol` | cites `status.is_retryable`, which does not exist | 1 | `pass` |
| `wrong_type` | `summary.counts()` returns pairs; the code returns a dict | 2 | `pass` |
| `reversed_semantics` | cancelled work IS chargeable; the code says it is not | 1 | `pass` |
| `stale_transition` | a transition table that is wrong | 0 | `pass` |
| `wrong_default` | a default that is wrong | — | *(empty payload)* |
| `true_but_incomplete` | nothing false; three of five rules deleted | 1 | `pass` |

**The defect list names the plant in 5 of the 8 defective documents. The `call` field says `fail` on
none of them.** Not once. And the descriptions are not hedged:

> `severity: high` — *"Document claims `MAX_ATTEMPTS` allows up to 5 attempts, but `jobs/retry.py`
> sets it to 3."*

> `severity: high` — *"The document references a non-existent function `status.is_retryable(job)`.
> This function does not exist in `jobs/status.py` or any other provided module."*

> `severity: high` — *"The document falsely claims that cancelled work IS chargeable ... The code
> explicitly excludes CANCELLED status from being chargeable, returning False immediately."*

Each of those is correct, specific, cites the file, and sits under `"call": "pass"`. This is F338's
contradiction on the other population and in a sharper form: on code the model argues the edge away
before deciding (*"this is standard Rust behavior ... falls outside the scope"*); here it does not
argue anything away — it states the falsehood and approves the artifact in the same object.

**So the gate is 0 of 8 and the report is 5 of 8, and the difference between them is one line of
consuming code.** A `pass` carrying a `high` defect is not a verdict. Reading the defect list and
ignoring `call` turns this arm from a broken gate into a working one, on this population, for free.

Two more things the arm produced that were not planted.

**The base document is not perfectly faithful, and the model found what the probe did not know was
there.** Rule 2 of the real document says a cancelled job *"is NOT an SLA breach ... the deadline no
longer applies to it."* The reference solution stops the clock — `finished_at` returns `ended_at`
for any terminal status — but `is_breached` still compares that against the deadline. Measured
directly against the refsol: a CANCELLED job with `queued_at=0`, `sla_seconds=100`, `ended_at=5000`
gives `is_breached == True`. The model raised exactly this, on three of the ten documents, at
`high`: *"`sla.py` does not explicitly exempt CANCELLED status from breach evaluation."* It is
right. **A control built by hand from a real document and its real reference solution held a defect
its author did not see, and the model under test found it** — which is the population 2.0 will
actually be pointed at, and the reason the `faithful` row is a lower bound on the false-positive
rate rather than a measurement of it.

**And it found it on three documents of ten, not on ten of ten.** The same true-but-unimplemented
claim is present in every one of the ten, including `faithful`, where the model reported nothing. A
reviewer that surfaces a real defect 30% of the times it is shown it is a sampler, not a check —
the same instability F339 measured on the code population, in the report rather than the verdict.

### 🚨 F342 — the judge has no absolute scale: 0 of 8 as a gate on one document, 14 of 14 as a choice between two, and the only textbook bias that reproduces is a preference for the longer document when nothing else separates them

The brief asks for LLM-as-judge's *known failure modes*. Two of the canonical ones are position bias
and verbosity bias, and both were run here as designed — every defective document against the
faithful one in both slot orders, and the faithful document against itself padded with 350 words.

**Position bias does not reproduce.** Seven pairs, fourteen orderings, and the model is right in
every one of them:

| defect | defective document shown first | shown second | order-stable |
|---|---|---|---|
| `wrong_constant` | correct | correct | yes |
| `phantom_symbol` | correct | correct | yes |
| `wrong_type` | correct | correct | yes |
| `wrong_default` | correct | correct | yes |
| `reversed_semantics` | correct | correct | yes |
| `stale_transition` | correct | correct | yes |
| `true_but_incomplete` | correct | correct | yes |

**14 of 14 orderings correct, 7 of 7 pairs order-stable, slot preference A 7 / B 7.** Every planted
defect is caught — including `stale_transition` and `wrong_default`, on which the pointwise arm
produced nothing at all, and `true_but_incomplete`, which contains no false statement and is F281's
shape.

That is the finding, and it is not about position. **The same model, the same defects, the same
code, the same temperature: shown one document it approves it, shown two it picks the right one
every time.** 0 of 8 against 14 of 14. Pointwise judgement asks for a threshold the model does not
have; pairwise asks for a comparison, which is a question it can answer. This is F280's axis — what
the reviewer is *shown* — in the strongest form it has taken in this project: **the thing to show a
judge is the other artifact.**

**Verbosity bias does reproduce, weakly, and it is dominated.** The padding is 350 words of true
design rationale that makes no new claim about behaviour, and the system prompt says in as many
words that *"length, tone and polish are not"* criteria:

| A | B | chose | correct answer |
|---|---|---|---|
| `faithful_padded` | `faithful` | **A** | equal |
| `faithful` | `faithful_padded` | **B** | equal |
| `faithful` | `wrong_constant_padded` | A | A |
| `wrong_constant_padded` | `faithful` | B | B |

**On the tie it picks the longer document both times, in both slot orders — and it converts length
into accuracy to justify it**: *"Document A provides a more complete description ... Since accuracy
is the only criterion."* More complete is not more accurate, and the `equal` option was in the
schema and was never used. But one factual difference beats 350 words of padding, in both orderings,
and the rationale names the difference: *"Document A incorrectly states MAX_ATTEMPTS is 5; the code
sets it to 3."*

So the ranking on which the pairwise arm scores 14 of 14 is not fragile to the two biases the
literature warns about — it is fragile to a *tie*, and a tie is exactly where a gate should abstain
rather than choose. **`equal` must be in the schema, and a judge that never returns it on a pair
that is genuinely equal is a judge whose comparisons are worth reading and whose ties are not.**

### F343 — the free rung on a document reaches the one defect that is an address, and only that one: 1 of 7

Before any model, the same question item 4 asked of code: what can a machine check on this document
without reading it? The prose analogue of the structural rung is symbol existence — every backticked
`module.name` or `name()` the document mentions must exist in the code it describes.

| document | call-shaped references | unresolved | verdict |
|---|---:|---|---|
| `phantom_symbol` | 1 | `status.is_retryable` | **fail** |
| `wrong_type` | 1 | — | pass |
| `reversed_semantics` | 1 | — | pass |
| the other seven | 0 | — | pass |

**1 of 7 planted defects, 0 false positives on the two faithful documents.** The one it reaches is
the one that is an address rather than an assertion, and it reaches it for nothing — no model, no
toolchain, milliseconds. The other six cite symbols that all resolve perfectly: `MAX_ATTEMPTS`
exists and is 3, `summary.counts()` exists and returns a dict, `charges.is_chargeable` exists and
returns False for cancelled work. **Every one of the six is a true sentence about a symbol that
exists, saying the wrong thing about it.**

The coverage number matters as much as the yield. This document — a real one, written by a task
author about real code — contains **at most one call-shaped reference per variant.** It is prose
about behaviour, not an API reference, and the rung has almost nothing to bite on. That is the
honest shape of the free rung for documentation: worth running because it costs nothing and never
lies, and silent about substantially everything a document says.

### 🚨 F344 — the free rung for prose checks addresses and nothing else: 1,873 of them across four documentation corpora, and exactly one points past the end of the file it names

`citations.py` is the documentation analogue of item 4's structural check — the thing a machine can
own without reading. Three kinds of claim in a research document are addresses rather than
assertions: a finding number must be defined somewhere, an open-question id must be defined
somewhere, and a `file:line` citation must name a file that exists and is at least that long. A
fenced block introduced by a citation is a fourth and stronger kind — a *quotation*, which can be
compared with the file line for line.

Run over this repository's **44 authored documents, 1.75 MB** — the workstream documents, the harness crates' READMEs, the prestudy dossiers, the corpus SPEC and the brief —
resolving against this repository and the three donor checkouts — the corpus includes this
document, so the counts are of the corpus at the commit that closes this item:

| | count |
|---|---:|
| findings defined | 338, by 342 headings |
| finding references | **2,553**, over 347 distinct numbers |
| dangling finding references | **9 numbers** — eight are one story (F345), cited **23 times across six documents** once this finding's own naming of the range is excluded; the ninth is this document's *"the next free number is F349"* note, a forward reference the convention creates once per item |
| open questions defined / referenced | 96 / 96, over 271 references |
| dangling open questions | **0** |
| `file:line` citations, unique | **752** |
| — resolve, and in range | 397 (53%) |
| — ambiguous under any mechanical rule | 343 (46%) |
| — name no file in the resolution set | 11 (1%) |
| — **point past the end of the file** | **1** |
| citations that quote the code they cite | 30 |
| — quotation matches the file line for line | 7 |
| — differs | 7, and all of them are paraphrase or an introducing citation that is not the block's source |

And the same address check on each donor's own documentation, resolved against its own tree:

| corpus | head | docs | citations | ok | no such file | ambiguous | past EOF |
|---|---|---:|---:|---:|---:|---:|---:|
| v1 | `d5528ea` | 65 | 752 | 636 | 24 | 92 | **0** |
| BCF | `d6c1601` | 12 | **0** | — | — | — | — |
| Claudette | `af3f804` | 163 | 369 | 51 | 39 | 279 | **0** |
| this repo | `582660a` | 44 | 752 | 397 | 11 | 343 | **1** |

**1,873 unique addresses across four corpora and one provable stale citation** — W5's F100
cites `crates/claudette/src/tui_events.rs:75-88` and the file ends at line 87. (The quoted enum is
really at 73–87, so even that one is an address off by one around content that is right.) BCF's
twelve documents cite their own code by line **zero** times, which is its own kind of answer.

Three things this measurement is worth more for than its yield.

**The checker's number is a measurement of the checker.** It reported **40** dangling finding
references, then 21, then 12, then 9, as it learned that this corpus defines a finding in **five**
different ways — `### F158 —`, `### 🚨 F158 —`, `### F35.`, `## 4. F54 —`, and a bold paragraph
`**F41.**`. Open questions have two conventions and a status marker. Every one of the first 31
"errors" was the rule, not the corpus. The same happened twice more: attributing a fenced block to
"the citation within three lines above" produced 12 documentation errors of which all 12 were the
rule, and resolving a bare `Cargo.toml:57` to a workspace's 23-line root manifest produced five
"past EOF" citations in the successor's documentation that were the rule again. **Every loosening of
the attribution manufactured defects, and no tightening ever cost a real one.**

**What is checkable is about half of what is written, at best.** A bare basename —
`orchestrator.py:43`, which is how most of this corpus cites — is not an address until a resolution
rule is fixed, and 46% of the citations here have no unambiguous target across four
trees. The convention that would make the rung meaningful is one line long (*cite a
repository-relative path*), and its value is prospective: it does not find today's errors, it makes
tomorrow's findable.

**And the rung is silent about every claim.** The documentation errors this project has actually
found, it found by hand, and the two that were cross-reference errors — F193 and F88, each cited as
saying something it does not say — pointed at findings that **exist**. Existence-checking would have
passed both. That is the honest bound on this instrument, and F343 is the same bound measured
against planted defects: it verifies that an address resolves, never that the sentence around it is
true.

### 🚨 F345 — eight finding numbers are cited 23 times across six documents in this repository and defined in none of them

The one residue the corrected checker leaves is a real defect and it is a single story. **F22
through F29** are referenced **21 times in five documents**, plus twice in this one before item 7 —
`harness/crates/w8-run/README.md`, `harness/crates/w8-corpus/README.md`,
`harness/crates/w8-import-q56/README.md`, `harness/crates/hw-probe/README.md`,
`research/W8-q56-import.md` and, as of item 5, `research/W6-verification.md` itself — in
load-bearing sentences: *"third time CRLF has produced a difference that looks like a finding and is
not (cf. F21, F22)"*, *"76 of the 90 tasks ship an empty fixture (F29)"*, *"it prints an advert
instead of running code (F27)"*. **None of the eight is defined anywhere in the repository**, under
any of the five conventions, and `git log --diff-filter=D -- '*.md'` shows no document was ever
deleted.

They exist in the private memory directory. `memory/abcc-2-w8-state.md` says of
`harness/crates/w8-import/`: *"Its README is the design record; findings F22-F27 below"* — and
`harness/crates/w8-import/README.md` contains **six headings and no finding numbers at all**. The
memory file then defines F28 and F29 itself, under a heading that names two findings at once
(`### F28-F29, both found by building the loader`), which is a sixth convention and outside the
repository.

This is worth a finding of its own because of what it is evidence for. **The repository's
cross-reference integrity had never been checked**, in 91 commits and 1.7 MB of prose, by anyone;
the check costs milliseconds; and it found a defect that only a mechanical pass would ever find,
because a human reading any one of those documents sees a citation that looks exactly like the
2,500-odd that resolve. One caveat the checker itself cannot resolve: **this finding is now the
largest single citer of the eight numbers it is about**, so the raw dangling count at head is
higher than the defect. The defect is the 23 load-bearing references; the rest is this document
discussing them. It is the documentation-shaped version of item 4's cheapest rung — free,
narrow, and worth running because it is free.

### 🚨 F346 — the family has no word for a documentation deliverable, and the one artifact type that is pure prose is the one type its reviewer is told to skip

Executed, not read. `bcf-doc/` takes a path dependency on the pinned BCF checkout and calls
`verifier::verify_project` on a three-file documentation project — the K suite's real status
lifecycle spec, a README and a CHANGELOG.

BCF's per-file mapping (`verifier.rs:73-81`) is `py | ts | js | rs | go | cpp` and `_ => continue`,
so no file is scored, `file_reports` is empty, and `avg_score` falls to the `5.0` literal at
`verifier.rs:96` — which W11 item 3 identified as the family's `Uncertain` spelled as a passing-ish
number (F258). Measured:

| | files scored | avg | final with a **perfect** critique | lowest gate |
|---|---:|---:|---:|---:|
| `language = "markdown"` | 0 | 5.00 | **7.00** | 8.00 |
| `language = "python"` (BCF's default, F315) | 0 | 5.00 | **7.00** | 8.00 |

**A documentation deliverable cannot pass BCF's gate at any complexity, however good it is**, and it
cannot fail it for any reason to do with its content. This is F313's mechanism arriving at the
artifact the brief names. One incidental measurement is worth recording: under the default `python`
language the run printed `Creating venv... Installing dependencies in venv... pytest: no tests
found` — **BCF builds a Python virtualenv and runs pytest against a directory of markdown.**

v1 is more explicit about it. Its task vocabulary is
`TaskType = 'code' | 'test' | 'review' | 'debug' | 'refactor'`
(`packages/shared/src/index.ts:53`), and the route accepts a sixth, `'decomposition'`, that the type
does not contain (`packages/api/src/routes/tasks.ts:13`). **There is no documentation task type**, so
a documentation deliverable is a `code` task and goes to the same validation command item 5 measured
running 1 of 13 real commands (F312).

And the one type in the vocabulary that is unambiguously prose with no test — `review` — is on
`SKIP_REVIEW_TYPES` (`codeReviewService.ts:54`), alongside `decomposition` and `debug`. **The
family's only reviewer is explicitly told not to look at review output.**

Two more facts fell out of running the donor's own decision function over the donor's own test
inputs (`v1_review.mjs`, ported byte-for-byte from `d5528ea`):

- **Both unit tests for the skip list pass for the wrong reason.**
  `codeReviewService.test.ts:34-48` builds `{ type: 'decomposition', status: 'completed' }` and
  asserts `shouldReview === false`. `getReviewDecision` reads `task.taskType`, which is `undefined`,
  so the skip never fires; the returned reason is `"No review needed (Ollama: 1/5, All: 1/10)"` —
  the *scheduler* declining, not the skip list. Run with the field the code actually reads, the
  reason becomes `"Skipping decomposition task type"`. **The skip list has never been exercised by
  its own tests.**
- **`refactor` and `debug` score 0 in the router's complexity switch** (`taskRouter.ts:200-213`,
  which has cases for `code`, `test`, `review` and `decomposition` only), so the two task types most
  likely to be a rewrite with no new behaviour are the two the router treats as the simplest.

### 🚨 F347 — v1's frontier review tier fires zero times in thirty tasks in exactly the regime the project was built for, because the cheaper tier's schedule divides the expensive one's

v1's graduated review is two schedules over two counters (`codeReviewService.ts:139-155`): Haiku when
`isOllamaTask && ollamaTaskCounter % 5 == 0`, Opus when `complexity > 5 && allTaskCounter % 10 == 0`.
The Haiku branch returns first. When every task is executed locally the two counters are equal — and
**every multiple of 10 is a multiple of 5**, so the Opus branch is unreachable.

Run over four task streams, complexity 9 throughout, one service instance each:

| stream | haiku | opus | unreviewed |
|---|---:|---:|---:|
| 30 tasks, all `ollama` | 6 | **0** | 24 |
| 30 tasks, alternating sonnet / ollama | 3 | **0** | 27 |
| 30 tasks, alternating ollama / sonnet — *the same stream, other phase* | 3 | 3 | 24 |
| 30 tasks, all sonnet | 0 | 3 | 27 |

**All-local is the premise of the entire project**, and it is the row where the expensive reviewer
never runs. Whether it runs at all is decided by the *phase* of the model stream, which is not a
property anyone chose. This is F270 and F271 with a mechanism attached: the tier table is not a
policy, it is an interference pattern between two counters.

`isOllamaTask` is `executedByModel === 'ollama' || !executedByModel`, so a task with no recorded
model counts as local — the provenance F271 called invented. And the complexity default is a falsy
coalesce, `task.complexity || 5`, against a strict `complexity > 5`: measured on the Opus tick with a
non-local model, complexity `undefined`, `0` and `5` all decline, and `5.5` and `9` review. **A task
whose complexity was never recorded, or was honestly recorded as zero, can never receive the frontier
review** — the same `||` defect W11 item 2 found destroying a reviewer's zero, in the other
direction.

### 🚨 F348 — the successor refuses to fold a timeout into "clean" and folds "there is no checker for this artifact" into it three lines later

Claudette's post-edit check is the most careful gate in the family, and its enum says so:

```rust
/// A timeout is deliberately NOT folded into "clean". A check that never
/// finished has verified nothing, and reporting silence there is exactly how a
/// corrupt file slips through unnoticed (roast CHECK-01).
pub(crate) enum CheckOutcome { Skipped, Passed, Failed(String), TimedOut(u64) }
```

`Skipped` covers three different situations (`post_edit_check.rs:289-299`): the feature is off, the
process is offline, and **no check command matched this file type**. `builtin_cmd` maps `.rs`, `.py`,
`.go`, `.js`, `.mjs` and `.cjs`; everything else returns `None`, and the donor's own test asserts it
for `["ts", "tsx", "md", "toml"]` and for an extensionless path (`post_edit_check.rs:483-491`).

The single call site (`runtime/conversation.rs:753-754`) then writes
`CheckOutcome::Skipped | CheckOutcome::Passed => None`.

So **editing a document produces exactly the observable result of editing a Rust file that
compiles**: nothing is appended, and the model that just wrote the document is told the same thing
either way. The type carries the distinction the design argued for and the consumer discards it —
which is item 1's diagnosis restated for the unrunnable artifact, and the reason item 5's
`Option<bool>` ruling (F317) is necessary and not sufficient. What 2.0 needs is not a third Boolean
but a *reason*: `Uncertain(NoCheckerFor(".md"))` is a different fact from `Uncertain(FeatureOff)`,
and only one of them should ever reach an operator.

## Options compared

Every row is scored on this item's own populations: 57 agent trees on which no deterministic rung
fires, and ten documents against the code they describe.

| For an artifact with no test | What it costs | What it buys |
|---|---|---|
| **Nothing** — accept the artifact | free | v1's answer for documentation (no task type) and for review output (`SKIP_REVIEW_TYPES`); Claudette's answer for every file its table does not map; BCF's 5.00 → 7.00 against a gate of 8.00 (F346, F348) |
| **An address rung** — do the citations resolve, do the symbols exist | milliseconds, no toolchain, no model | 1 of 7 planted document defects, 1 stale citation in 1,873, 8 dangling finding numbers. **Zero false positives once the attribution rule is tight**, and silent about every claim (F343, F344, F345) |
| **A model verdict** — the shipped `pass`/`fail` field | one call, 38 s median | **3 of 23** wrong trees, 1 false fail in 34, 2 empty payloads in 57 — and 2 of the 3 catches do not survive a change to the output schema. On documents, **0 of 8** (F338, F339, F341) |
| **A model report, verdict discarded** — read the defect list, not the call | the same call | **5 of 8** planted document defects, named at `high` under `call: pass`. On code the two agree, so this buys nothing there (F338, F341) |
| **A model report shaped as concrete cases** — `call → expected → actual` | **2.8× the decode, 2.7× the wall clock, 17 of 57 calls lost to the token cap** | 11 of 23 wrong trees produce a runnable case; the model's own verdict contradicts its own cases 14 times in 16 (F339) |
| **Running the reviewer's cases** — execute each named case | one process per case, seconds — free next to the 104 s call that produced it | **10 of 23** wrong trees, 1 of 34 false, and that one is the harness's string equality, not the model's claim. 13 of 15 concrete claims on wrong trees are true (F340) |
| **A pairwise comparison** — this artifact against another | one call, and you must have the other artifact | **14 of 14** orderings correct, order-stable on 7 of 7 pairs, including two defects the pointwise arm missed entirely. Fails only on a genuine tie, where it prefers the longer document (F342) |
| **A second model** | a 26.3 s swap plus 4.6× decode | measured in W11 item 4 and rejected: a better reader, an unusable component (F284) |

## Recommendation

**1 — A model verdict is a report, never a gate.** On the population where nothing else fires, the
shipped binary catches 3 of 23 wrong answers and false-fails 1 of 34 right ones; on documents it
catches 0 of 8. That is not a weak gate, it is not a gate. And it is worse than weak, it is
*unstable*: change nothing but the output schema and it catches a different three, overlapping the
first three in one tree (F339). 2.0's `Verdict::call` stays advisory and never binds a merge.

**2 — A verdict that contradicts its own report is `Uncertain`, in both directions.** On
documentation the same call *finds the defect and then approves the artifact* — the wrong constant,
the non-existent function and the reversed billing rule are all named at `high` severity under
`call: "pass"`. On code, the model that names the failing input answers `pass` 14 times in 16. The
rule that is right on both populations is a consistency check the type system can carry: **a `fail`
with an empty defect list is not a verdict, and a `pass` carrying a `high` defect or a concrete
failing case is not a verdict either.** Both are `Uncertain`, both stop the gate rather than
deciding it, and both are free. The single false-fail in the whole code arm and five of the eight
document defects are caught by that one rule and by nothing else.

**3 — Demand a concrete case, and budget for it, because it is not free.** W11 item 4 found the
deciding axis is what the reviewer is *shown* (F280); this item adds the other half — what it is
*asked to emit*. Same model, same context, same temperature: a schema whose leaf is
`{why, call, expected, actual}` produces a runnable falsification on 11 of 23 wrong trees where the
paragraph produced 3. It also costs 2.8× the decode and loses 17 of 57 calls to the token cap
(F339). So: ask for the case, give it a budget that reflects the ask, and treat
`finish_reason: length` as `Uncertain` rather than as silence. **An empty payload with a legible
reason is a better failure than a well-formed verdict that is wrong.**

**4 — A review finding is verified by running it, and item 6 already built the machine.** A finding
that names an input is falsifiable: run it on the snapshot commit (item 6's
`read-tree` / `write-tree` / `commit-tree` pre-image, 0.16 s) and on the tree as it stands. Differ →
the finding is real and the reviewer earned its keep. Same → the reviewer is wrong, and the operator
should never see it. Will not run → it was never a finding. Measured: **10 of 23 wrong trees caught
against 1 of 34 false**, three times the recall of the same model's own verdict at the same
false-positive rate, and 13 of 15 concrete claims on wrong trees are true (F340). **This is the
answer to "verifying review output": you do not verify the prose, you require the prose to carry
something you can execute.** It closes F277's gap — a generated criterion with no positive control —
for free, because the pre-image *is* the control.

One implementation note that the one false positive pays for: **compare the way the suite compares,
not the way a string does.** The single false fire in 34 was two `Err` values with different
wording. Against a pre-image that difference is a real change and should be surfaced; against a
reference it is noise. Say which comparison is being made, in the finding.

**5 — If a model must judge, give it the other artifact, not a threshold.** The strongest single
result in this item: the same model, the same defects, the same code, the same temperature scores
**0 of 8 pointwise and 14 of 14 pairwise** (F341, F342). Absolute judgement asks for a scale the
model does not have; comparison asks a question it can answer, and it answered every one — including
the two defects the pointwise arm missed completely and the one that contains no false statement at
all. Item 6 hands 2.0 the second artifact for 0.16 s: **the pre-image is the other document.** Where
there is genuinely nothing to compare against, that is exactly the case where the verdict is a report
and rule 1 applies.

**6 — `equal` must be in the schema, and a tie must be allowed to be a tie.** The pairwise arm's only
error is on a pair that is genuinely equal, where it prefers the longer document in both slot orders
and converts length into accuracy to justify it (F342). Position bias did not reproduce at all —
14 of 14, order-stable on 7 of 7 — so the failure mode to design against here is not the one the
literature names first. A comparison whose `equal` branch is never taken is a comparison that will
manufacture a preference when there is none.

**7 — Run the address rung on documentation because it is free, and never call it verification.** It
found 1 stale citation in 1,873 addresses and 8 dangling finding numbers in 2,553
references, at zero false positives (F344, F345), and it reaches 1 of 7 planted document defects —
the one that is an address rather than an assertion (F343). Six of seven planted defects cite symbols
that resolve perfectly, including a reversed billing rule and a wrong return type.

**8 — Ship one citation convention, and its value is prospective.** 46% of this corpus's
citations are a bare basename with no unambiguous target. `path/relative/to/repo.rs:12-18` is one
line of convention and it turns 343 unresolvable addresses into checkable ones. Do the same
for finding ids: one definition form, checked in CI. And **quote what you cite** — 30 of
752 citations here are followed by the code they name, and a quotation can be checked
against the file line for line while an address cannot.

**9 — `Uncertain` needs a reason, not a Boolean.** Claudette's `CheckOutcome::Skipped` folds "the
feature is off", "we are offline" and "there is no checker for a `.md` file" into one variant, and
its single call site then folds that into `Passed` (F348). 2.0's `Uncertain(why)` carries the why,
and the console shows *no checker for this artifact* as a different line from *check disabled*.

**10 — Review output is reviewed.** v1 puts `review` on `SKIP_REVIEW_TYPES` (F346). In 2.0 the
artifact with no test is exactly the artifact that most needs a second reading, and the second
reading is cheap because it is the same model in a fresh call reading the diff (W11 F280).

## Rejected alternatives and why

- **"Score the artifact 1–10 and threshold it."** BCF's shape, and item 1 voided the ladder. This
  item adds the mechanism: the model has no absolute scale to threshold. 0 of 8 pointwise against
  14 of 14 pairwise on the same defects (F342), and a documentation project scores exactly 5.00
  because nothing was read at all (F346).
- **"Trust the defect list on code the way it works on documents."** On documents, reading the
  defects and ignoring `call` turns 0 of 8 into 5 of 8. On code it buys nothing — the defect list
  and the binary agree, and the derived gate is the same 3 of 23 (F338). The rule that transfers is
  the *contradiction* check, not "prefer the report".
- **"Have the reviewer write a test."** F337 measured what agents' own tests are worth on this
  population: 22 green tests on trees that are wrong, one asserting the opposite of the hidden test.
  A test written by the same reasoning that produced the artifact ratifies it. The case in F340 is
  different in one specific way: it is run against a tree the reviewer did not write — the pre-image
  — so agreement is evidence rather than tautology.
- **"Swap in a bigger model for the judge."** W11 item 4 measured it (F284): a better reader, and an
  unusable component — it burned the whole budget and returned nothing 3 of 3 on a correct answer, at
  4.6× the decode plus a 26.3 s swap. This item reproduced that failure mode on the champion at 30%
  under a demanding schema (F339); a larger model would make it worse, not better.
- **"Check documentation by regenerating it and diffing."** Not measured, and it is the wrong shape:
  it makes the model's own output the standard, which is F280's failure with an extra step. The
  comparison that works is against something with independent provenance — the pre-image, or the code
  itself.
- **"Grade prose with an embedding or a similarity score."** Nothing in this corpus needs it. Every
  defect that mattered here was a specific false sentence about a specific symbol, and both
  instruments that reached them — the address rung and the pairwise comparison — are exact.

## Effect on fun

The unit that finishes a documentation task and says *"clean"* is lying, and the console has no way
to know. That is the state today in all three donors. The change that matters for the operator is
small and entirely mechanical: **a fourth outcome with a reason in it.** *No checker for this
artifact* is a legitimate thing for a unit to report, it is honest, and it is a different colour on
the map from *checks passed* — which means the operator can see, at a glance, which of the fleet's
finished work has actually been measured and which has only been asserted.

The reviewer's concrete case is the part that will read best. A finding that says *"this is fragile"*
is an opinion an operator has to arbitrate; a finding that says `split_bill(10, 4)` → expected
`[3,3,2,2]`, got `[4,2,2,2]`, **and carries a green tick because the harness ran it against the
pre-image**, is a fact. That is a genuinely different feel: the review panel stops being a wall of
advice and becomes a short list of things that were tried and did happen, with the ones that did not
reproduce already filtered out before anyone read them.

And the pairwise result gives the console a verb it did not have. *Compare* — this attempt against
the checkpoint, this document against the one it replaces — is a question the model answers 14 times
out of 14, on the same material where *approve* answers 0 of 8. A command centre that asks its
analysts to rank rather than to certify is asking them something they are good at, and the operator
keeps the decision, which is where W5 put it.

## Open questions

| # | Question | Waiting on |
|---|---|---|
| OQ-W6-13 | What the 29 clean-arm failures are, and whether anything can reach them | **answered here** (F336): they are boundary cases, the axis is whether the ticket's own words decide the failing input, and 8 of 29 they do |
| OQ-W6-17 | The pairwise gate against a **pre-image** rather than against a hand-built rival: does 14 of 14 survive when the second artifact is the previous version of the same file? | item 6's snapshot plus one real edit; cheap, and it is the form 2.0 would actually ship |
| OQ-W6-18 | What token budget makes the `edge` schema stop failing? 8,192 lost 30% of the calls; the model's median was 6,870 | one re-run at 16,384, one arm, ~2 hours of GPU |
| OQ-W6-19 | Does running the reviewer's case against the **pre-image** rather than a reference solution hold the 13-of-15 precision? The oracle used here does not exist in production | 2.0's first real attempt, or a re-run of `check.py` against item 6's snapshot commits |
| OQ-W6-20 | Is the `pass`-with-a-`high`-defect contradiction a property of this model or of the schema? W11 F263 fixed the field order; the contradiction survives it | one arm at a different temperature, and one on a different model, when there is a reason to load one |
| OQ-W6-8 | Does the coverage fraction bind as a veto, or only as a report? | still open (item 5) |
| OQ-W6-7 | *(item 2)* Rules-only router, or rules plus a recorded model reading? | still open |

## Confidence: high on the donor facts and on the code population, medium on how far the document numbers travel

The donor half is executed rather than read — `v1_review.mjs` runs v1's own decision function over
v1's own test inputs, `bcf-doc/` calls BCF's verifier on a real documentation project, and the
Claudette finding is a call site read against the enum three files away. The interference pattern in
F347 is not an inference from the source; it is four task streams run through the ported function.

The code population is the strongest measurement here. 57 trees with a hidden answer key that no
participant could see, deduplicated by content, with the verifier's residue stripped before anything
was shown to a model, and every classification's quoted ticket clause asserted as a substring of the
ticket the agent actually received. The judge arms are n=1 per tree at temperature 0, which is the
right shape for a gate but means the 3-of-23 and 10-of-23 rates carry the sampling noise of 23
trees — the interval on 3/23 is wide, and the finding that survives it is not the rate but the
*direction*: the executable claim beats the binary by a factor, on the same calls.

Three limits worth stating. **The document arm is one document, one code base, seven planted
defects** — 0 of 8 pointwise and 14 of 14 pairwise are a large gap on a small n, and the mechanism
(no absolute scale, a working relative one) is the part to carry forward, not the fractions.
**`check.py` used the reference solution as an oracle**, which is exactly what production does not
have; OQ-W6-19 is the honest version of that measurement. And **the base document was not perfectly
faithful** — the model found a real defect its author had not seen (F341), so the `faithful` row is a
lower bound on the false-positive rate and not a measurement of it. That is the third time in this
workstream that a constructed clean baseline turned out to be an untested claim.

One thing this item did *not* find, and it is worth recording as an absence: **no LLM-as-judge
failure mode from the literature reproduced as the dominant problem.** Position bias: absent, 14 of
14. Verbosity bias: present, weak, dominated by one fact. Self-preference: not testable here, one
model. What actually failed was simpler and is not in the usual list — **the model reliably finds the
defect and then approves the artifact**, in one object, in the same call, on both populations.

---

# Item 8 — honest failure reporting

## Question

§11's line is the only one in the whole brief that names a specific incident: *"**Honest
failure reporting**, which V1 got badly wrong when an agent claimed two passing tests on a run
that executed zero. Rust's error handling makes it possible to do this properly. Design for it
explicitly."*

It reads as a question about models lying, and that reading has to be tested before anything is
designed, because it decides what gets built. If the failure is *the model asserts things that
are not so*, the answer is a reviewer, and item 7 just measured what those are worth. If the
failure is *the system cannot tell an assertion from a measurement*, the answer is a type, and
no reviewer is needed at all.

So three parts.

1. **What actually happened in v1** — not what its documentation says happened, and not what
   its fix says it fixed. v1 has a written, dated, "IMPLEMENTED" fix for this class of defect
   and a module whose docstring is *"Prevents agents from hallucinating test success."* The
   question is what that code returns when it is called.
2. **How often the model does it here.** This project has 1,369 preserved cells, and 266 of
   them are Rust work dirs still on disk with an answer key attached. Does the champion claim
   test results it did not produce, and if it does not, does that make the record honest?
3. **The type.** The brief says Rust makes it possible to do this properly, which is a design
   claim, and a design claim in this workstream gets compiled and run rather than described.

## Method

Nine probes in `research/spikes/w6-honesty/`, four of which execute donor code rather than
paraphrase it, and one of which is a Rust crate.

- **The donor chain, imported and called.** `v1_parser.py` executes pytest and
  `python -m unittest` in a scratch tree in the states a test run can end in, saves what each
  printed **with the exit status the OS returned**, and feeds those bytes to v1's own
  `parse_test_output` (`validators/test_validator.py` at `d5528ea`). `v1_output.py` imports v1's
  `_parse_from_execution_logs` and `parse_agent_output` and reads back the `status` and
  `confidence` the task record would have carried. `v1_safety_net.mjs` ports
  `taskExecutor.ts`'s `handleTaskCompletion` guard and its `detectTestFailures` predicate
  byte-for-byte and runs them over the records those two produced. Nothing in the chain is a
  hand-written string: the observations come from `captured/`, and `cargo_endings.py` adds the
  five cargo endings the same way.
- **The forensic discriminator, established by executing it.** A Q56 Rust verifier runs exactly
  one cargo command — `cargo test --test hidden_gate --quiet` — so a test executable in
  `target/*/deps` under the *crate's* name can only have been produced by the subject.
  `control.py` runs all four candidate commands on a fresh fixture and asserts which of them
  leaves one: the verifier's does not, `cargo test` does, `cargo build` and `cargo check` do
  not. It is the first thing to run and the numbers below are void without it.
- **The census.** `ran.py` walks every preserved Q56 **Rust** cell — 266 of them, 14 tasks, 9
  runs — and takes two independent readings: the physical one above, and a rule-based
  classification of the subject's own prose that keeps the sentence every rule fired on. It
  also compares the test binary's mtime to the newest source file's, because a binary older
  than the tree is a measurement of something that no longer exists.
- **Was the claim true?** `visible.py` copies each clean-arm work dir to a scratch tree, drops
  `target/` and deletes the verifier's `tests/hidden_gate.rs`, and re-runs `cargo test` — the
  suite the subject could actually see, including any tests it wrote itself. Nothing is written
  inside `runs/`.
- **The type.** `report/` is a small Rust crate: `Outcome::{Measured, Unmeasured(Why)}`,
  `Headline::{Green, Red, Unverified}`, a `Claim` that no function converts into an `Outcome`,
  and two classifiers. Its tests read the same `captured/` bytes, and one of them —
  `donor_gate.rs` — is Claudette's `classify_tests` copied verbatim and run beside them.
  17 tests, `cargo test`.

Donor commits v1 `d5528ea`, BCF `d6c1601`, Claudette `af3f804`. No GPU: nothing in this item
asks a model anything.

## Inherited

| What | Source | Verdict here |
|---|---|---|
| No silent midpoints; a default that pretends to be a measurement is the family's signature bug | item 1, F161 | **CONFIRMED and localised** — the default here is a *branch*, and its comment says so: `# No tests ran or all tests passed = SUCCESS` (F351) |
| `Option<bool>` is the right type for "could not run" | item 5, F317/F218 | **KEEP, and it is not sufficient** — Claudette has it, reads pytest's exit 5 with it, and still returns `Some(true)` for a crate with no tests (F357) |
| Every rung that did not run must appear in the outcome with its reason | item 5, recommendation 5 | **BUILT** — `Unmeasured(Why)` with eight variants, and a headline that cannot be green while one is present (F358) |
| `Uncertain` needs a reason, not a Boolean | item 7, recommendation 9 | **EXTENDED** — v1 has the fourth outcome, constructs it once, and sets `success=True` in the same literal (F352) |
| `Ok(())` on budget exhaustion is the anti-pattern | W11 item 5, F296 | **ENCODED** — `Why::BudgetExhausted` is neither pass nor fail, asserted (F358) |
| An empty payload with a legible reason beats a well-formed wrong verdict | W11 item 4, F282; item 7 recommendation 3 | **KEEP** — the same rule one layer down: a green with nothing behind it is worse than a legible "nothing ran" |
| Share `CARGO_TARGET_DIR` across attempt worktrees | item 6, F331 | **QUALIFIED** — safe for building, unsafe for testing: two trees holding one package name make cargo run the wrong binary and report `ok. 0 passed` (F356) |
| A pooled rate can invent a finding that stratification denies | item 4/5, F321; memory item 26 | **BIT AGAIN** — the 7 unbacked claims are 7 of 7 in the arms built to block the edit (F353) |

## Findings

### 🚨 F349 — the brief's charge, executed end to end: v1's chain marks 15 of 16 records "completed", and the single one it stops reports two tests where three ran

`v1_output.py` builds the execution logs v1's own tool layer produces — one `file_write` with
the observation the tool really prints, then one `shell_run` whose observation is the bytes a
real runner really emitted — and calls v1's two completion parsers. `v1_safety_net.mjs` then
runs the ported `handleTaskCompletion` guard over the resulting records. Eight run-endings ×
two entry points:

| what really happened | `_parse_from_execution_logs` | `parse_agent_output` | the TS safety net |
|---|---|---|---|
| pytest discovered zero tests | SUCCESS, conf 0.7 | SUCCESS, conf 1.0 | marked completed |
| pytest ran 3 and all 3 failed | SUCCESS, conf 0.7 | SUCCESS, conf 1.0 | marked completed |
| pytest ran 3, one passed | **SOFT_FAILURE, conf 0.0** | SUCCESS, conf 1.0 | **redirected** (log path only) |
| pytest ran 2 and both passed | SUCCESS, conf 1.0 | SUCCESS, conf 1.0 | marked completed |
| pytest failed to collect | SUCCESS, conf 0.7 | SUCCESS, conf 1.0 | marked completed |
| the test command could not spawn | SUCCESS, conf 0.7 | SUCCESS, conf 1.0 | marked completed |
| no test command was issued at all | SUCCESS, conf 1.0 | SUCCESS, conf 1.0 | marked completed |
| the model reported its own result | SUCCESS, conf 1.0 | SUCCESS, conf 1.0 | marked completed |

**15 of the 16 records are marked completed, and one is redirected.** The row that fires is the
one the documented fix was written for — and among the endings that really went red it is the
only one whose output contains the word `passed`, which F350 explains. It is also wrong about what it measured: the run was three
tests with one passing, and v1 records **2 run, 0 passed, 2 failed**, so
`confidence = success_rate = 0.0` on a suite that was a third green.

Two further facts fall out of the table's shape.

**The same run gets two different verdicts depending on an HTTP call.** `parse_agent_output`
fetches the execution logs from `http://api:3001/api/execution-logs/task/<id>` with a 5 s
timeout inside a bare `except Exception` that prints a warning and falls through
(`output.py:368-383`). Above the fold that fall-through path never sees the logs at all, and the
one ending v1 can catch becomes SUCCESS at confidence 1.0. A gate whose verdict depends on
whether a container's DNS resolved is not a gate.

**The fall-through has a shortcut in it.** Before parsing anything, `parse_agent_output` looks
for a JSON object in the raw output and returns it whole:
`if data.get('files_created') or data.get('commands_executed'): return AgentOutput(**data)`
(`output.py:385-394`). The last row of the table is that path: a model that emits
`{"status": "SUCCESS", "confidence": 1.0, "summary": "…2 tests passed.", "files_created": [...]}`
has its own self-report adopted verbatim as the task record, while the execution logs beside it
show one file written and no command run. **That is the literal mechanism §11 describes**, and
it is the first branch in the function.

### 🚨 F350 — the reason the fix cannot fire: v1's parser is gated on the word `passed`, and eight real run-endings become three records

`parse_test_output` (`test_validator.py:181-242`) chooses its pytest parser with one condition:

```python
if '===' in output and 'passed' in output.lower():
```

A pytest run in which every test failed prints no `passed` anywhere — this is not an inference,
`v1_parser.py` executes pytest and saves the bytes:
`============================== 3 failed in 0.30s ==============================`. So the pytest
branch is skipped, the unittest branch needs `Ran`, the generic patterns all require `passed`,
and the `FAIL:`/`ERROR:` fallback is unittest-shaped. The function returns
`TestResult(raw_output=output)` — `tests_run=0`, `tests_failed=0` — whose summary is
**`NO TESTS RAN - Test discovery failed or no tests found`**.

Fed the eight endings a real runner produced, v1's parser returns **three distinct records**:

| record | endings that land in it |
|---|---|
| 2 run, 2 passed, 0 failed, valid | pytest 2 of 2 pass · unittest 2 of 2 pass |
| 2 run, 0 passed, 2 failed, invalid | pytest 1 passes 2 fail · unittest 2 of 2 fail |
| **0 run, 0 passed, 0 failed** | **pytest 3 of 3 fail** · pytest nothing to collect · pytest collection error · unittest nothing to collect |

The third row is the finding. *Every test failed*, *there were no tests*, and *the suite did not
load* produce one identical object, and it is the object that says nothing ran. The status
determination downstream then keys on `parsed_test_result.tests_run > 0`
(`output.py:294`, `:530`), so on the all-red run — the incident that motivated the whole fix —
the guard is skipped by construction and control falls to the `else` branch.

**And the fact v1 needed was already in the exit status.** The same captures, with the number
the OS returned:

| ending | exit | what the integer means |
|---|---|---|
| pytest, 2 of 2 pass | 0 | all tests passed |
| pytest, 1 passes 2 fail | 1 | tests ran and something failed |
| pytest, 3 of 3 fail | 1 | tests ran and something failed |
| pytest, collection error | 2 | interrupted before running |
| pytest, nothing to collect | **5** | **no tests collected** |
| unittest, nothing to collect | **5** | **no tests collected** |

pytest and `python -m unittest` both reserve **5** for *no tests collected*. The question v1's
242-line module tries to recover from prose — *did anything actually run?* — is a
single integer that the process already handed it, and no line in `test_validator.py`,
`output.py` or `taskExecutor.ts` reads an exit code at all.

### F351 — the defect is documented as intended behaviour, at four independent sites

This is not a bug hiding in a corner. Four places in v1 state it, in writing:

1. **The fix's own behaviour matrix.** `docs/FIX_FALSE_POSITIVE_COMPLETIONS.md:93`, in the table
   headed *"Behavior matrix after fix"*: `| Files created + no tests ran | SUCCESS | SUCCESS
   (unchanged) |`. It is the first row.
2. **The status branch's comment.** `output.py:304` and `:540`, identically in both parsers:
   `# No tests ran or all tests passed = SUCCESS`. Two different states, one branch, and the
   comment names both.
3. **The safety net's doc comment.** `taskExecutor.ts:509-512`: *"Returns true if tests were run
   and failed. **Returns false if no tests ran** or all tests passed."*
4. **The module docstring above all of it.** `test_validator.py:4`: *"Prevents agents from
   hallucinating test success."*

The gap between 4 and 1–3 is the whole item. The fix was written for a real, correctly
diagnosed incident — a File Upload Handler with 3 of 3 tests failing, reported SUCCESS at
confidence 1.0 — and it fixed the case where the parser produces a failure count. The case where
the parser produces *nothing* was recorded as out of scope in the same document, and the case
where the parser produces nothing **because everything failed** was not distinguished from it.

### F352 — v1 has the fourth outcome, constructs it once, and shadows it with a Boolean in the same literal

`AgentOutput.status` is
`Literal["SUCCESS", "SOFT_FAILURE", "HARD_FAILURE", "UNCERTAIN"]` (`output.py:11-14`), described
in its own field as *"UNCERTAIN (unverified)"*. Item 7 recommendation 9 asks for exactly this
value. Three facts about it:

- **It is written at exactly one site**, `main.py:436-447`, when parsing the structured output
  raised. Three lines below the `status="UNCERTAIN"` is `success=True,  # Assume success unless
  proven otherwise`.
- **It never crosses the process boundary as a status.** `ExecuteResponse` (`main.py:107-113`) is
  `{success: bool, execution_id, output, error, metrics}` — there is no status field. `status`
  is printed to the console (`main.py:450`) and returned nowhere.
- **What does cross is the Boolean**, `success=structured_output.success` (`main.py:479`) — and
  the TS safety net's first check is `if (agentOutput.success === false)`, which an `UNCERTAIN`
  record whose `success` is `True` can never satisfy.

So the type has four values, the wire has two, and the one construction of the fourth pre-empts
the ambiguity it exists to express. This is F218's shape one layer up: the right type, present,
with a call site that flattens it.

### 🚨 F353 — on this project's own corpus the model is not the liar: 81 of 81 clean-arm claims that the tests pass are backed by a real test run and true of the tree that was delivered

266 preserved Q56 Rust cells, 14 tasks, 9 runs. Two independent readings per cell — what the
subject said, and whether a test binary the verifier never builds is sitting in the work dir.
Split by arm, because the arms are not the same experiment:

| arm | cells | asserts the tests pass | a test really ran | says nothing about tests |
|---|---|---|---|---|
| `control` + `gated` (the subject worked freely) | 98 | 81 | **81 of 81** | 15 |
| `deny-first-edit` + `redirect-first-edit` (the harness blocked the edit) | 168 | 112 | 105 of 112 | 43 |

**In the clean arms the rate of unbacked test claims is zero.** And `visible.py` re-ran the
suite on every delivered tree: **81 of 81 of those assertions are true** — the visible suite,
including any tests the subject wrote itself, is green on the tree it left behind.

The seven cells where a subject asserts a pass with no test run are **7 of 7 in the interrupted
arms**, 6 of the 7 wrote no file at all, and reading them explains why: they are predictions
about a patch the harness would not let them apply — *"The existing test (`"1,2,3" → [1, 2, 3]`)
passes unchanged. Want me to apply this?"*, *"The test `finds_a_nearby_duplicate` will still
pass. Shall I go ahead?"* Three are in the future tense. A pooled rate over all 266 cells would
have produced "2.6% of test claims are fabricated" and it would have been a fact about the
harness's own interventions — the same trap as F321 and memory item 26, one item later, on a
corpus half of which exists to interrupt the agent.

**This kills the reading the brief invites.** The champion, on 98 unimpeded attempts, did not
once report a test result it had not produced. Whatever went wrong in v1, a lying model is not
the necessary ingredient.

### 🚨 F354 — and it does not matter: 14 of those 81 true, measured, green claims sit on trees that fail, 6 measured a tree that no longer existed, and one reported 7 of 7 after deleting the tests

Same 81 cells, joined to the verdict the hidden reviewer tests recorded at grade time:

- **14 of 81** are green on the visible suite, honestly reported, and **FAIL** the hidden gate.
  The sentence *"Done — both existing tests pass"* is true, was measured, and is not a claim
  about whether the work is right. Q56 is built so that the visible tests are green on the
  fixture before anyone touches it, which is exactly the situation the operator is in: **the
  scope of the measurement is the whole content of the claim, and prose does not carry it.**
- **6 of 81 measured a tree that no longer existed.** The subject's test binary is older than
  its newest source file — it ran the tests, then edited, then reported. The gaps are 1.7, 1.7,
  1.8, 1.8, 2.7 and 3.0 seconds. Q10/`control` is the clean specimen and the timings line up to
  the millisecond: `apply_diff` at 7,530 ms, the subject's `q10-*.exe` built at **8,619 ms**,
  `edit_file` at 10,291 ms (1,165 → 1,161 bytes), and at 13,764 ms *"Test passes clean, no
  warnings."* Four bytes changed after the last measurement, and nothing in the record says so.
- **One case does all of it at once,** and narrates itself while doing it. Q52/`gated`: the
  subject writes the implementation, adds a test module (1,148 → 2,829 bytes), and reports
  *"All 7 tests pass. Now let me strip back to just the production code (the test module wasn't
  in the original stub):"* — then writes the file back to 1,148 bytes, which the harness's own
  diff preview flags as **"LOST MORE THAN HALF THE FILE"**. The final message is *"Done —
  `RingBuffer<T>` is implemented … It compiles clean and all the smoke tests I ran earlier
  passed (7/7)"* followed by seven ticked bullets. `cargo test` on the delivered tree runs
  **zero tests**, and the hidden gate fails it.

That last message is *scrupulously* accurate. "The smoke tests I ran **earlier**" is the correct
tense, the count is right, and the tests really did pass. What the operator sees is seven green
ticks. **The model's honesty was never the binding constraint; the record's inability to carry
*when* and *over what* is.**

### F355 — the record of a run does not say whether a test ran, and recovering it took build artifacts and file timestamps

The instrument F353 and F354 depend on is a measurement of the corpus, so it gets its own
finding and its own controls. Q56's Rust verifiers all run exactly `cargo test --test
hidden_gate --quiet` (Q12 adds `--release`), which builds the library and one integration
target. A subject that runs the crate's own tests builds the library's *unit-test* binary as
well. `control.py` executes all four arms on a fresh Q01 fixture and asserts the discriminator
rather than reasoning about it:

| command | leaves a crate-named test binary |
|---|---|
| `cargo test --test hidden_gate --quiet` (the verifier's) | no — only `hidden_gate-*.exe` |
| `cargo test --quiet` (a subject running the suite) | **yes** — `q01-601bc0322f0a2ab5.exe` |
| `cargo build --quiet` | no |
| `cargo check --quiet` | no |

The hash matches the one in the preserved Q01/`control` work dir exactly, and the mtime
alignment in F354 puts the binary between two narrated tool calls, so the discriminator is
checked twice against two independent clocks.

What it cost is the point. **Claudette narrates file mutations and nothing else** — 333 `▸`
lines across these cells are `apply_diff`, `write_file`, `edit_file` and one `apply_patch`, and
not one of them is a shell command or a test run. So the transcript, which is the complete record of the session as the
operator saw it, contains a sentence saying the tests pass and contains no way to check it. The
answer had to be excavated months later from build artifacts and file timestamps in a directory
that survived only because this project keeps its work dirs. **A record that cannot answer "did
you run it?" is the defect**, independently of who said what.

### 🚨 F356 — a green test run that measured nothing, produced by cargo and not by a model: one shared build directory silently runs the other tree's binary

Found by walking into it. The first draft of `visible.py` shared one `CARGO_TARGET_DIR` across
all 98 cells to get item 6 F331's warm-cache saving, and reported `ok. 0 passed` on trees that
have eleven tests. `shared_target.py` is the minimal reproduction and it asserts every arm:

| arm | exit | tests run |
|---|---|---|
| tree A (`collide v0.1.0`, no tests), shared build dir | 0 | 0 |
| tree B (`collide v0.1.0`, three tests), **same shared build dir** | **0** | **0** |
| tree B, its own build dir | 0 | 3 |
| tree B, cargo's default `target/` | 0 | 3 |

`cargo test -v` in the second arm prints **`Fresh collide v0.1.0 (…/B)`** and then
`Running …/_target/debug/deps/collide-c1866d723b8f419c.exe` — one executable, built from A,
run for B. The `-C metadata` hash does not separate two directories holding the same package
name and version, so the second tree is declared up to date and its tests are never compiled.
The process exits 0. The summary line says `test result: ok`. Nothing anywhere says that the
binary and the source came from different trees.

This is the item's own thesis arriving from the build system rather than from a model, and it
**qualifies item 6's recommendation**: sharing `CARGO_TARGET_DIR` across per-attempt worktrees
is safe for *building* — that is where the 24.7 s came from — and unsafe for *testing*, because
the collision is silent and it is green. It answers half of OQ-W6-14: two attempts can share a
build cache, and each attempt's gate must run in a build directory nothing else writes to.

### F357 — the successor already implements most of the cure, and still passes a crate with no tests

Claudette is the best of the three donors here by a distance, and `donor_gate.rs` ports its
`classify_tests` (`quality.rs:458-502`) verbatim and runs it over the same captures. What it
gets right, executed:

- The return type is `Option<bool>`, and `None` is reachable from three distinct causes:
  `result.timed_out`, `result.exit_code.is_none()` (the process never started), and
  **pytest's exit 5**, which it reads by number with the comment *"pytest exit 5 = 'no tests
  collected' — advisory, not a failure"*. Run on the real capture it returns `None` and the line
  *"tests: no tests collected (nothing to verify)"*. **It is the only place in any of the three
  donors where an exit code decides anything.**
- Its count parsers are order-free — each integer is paired with the word after it — so on the
  real `2 failed, 1 passed` line it returns `(1, 2)` where v1's regex returns `(0, 2)`.
- The layer beneath it, `CommandResult` (`test_runner.rs:11-20`), is item 5's
  `Measured(exit_code, stdout, stderr)` contract already built: `success`, `stdout`, `stderr`,
  `timed_out`, `exit_code: Option<i32>`.

And what it still does, executed on `cargo test` in a crate with no tests at all:

```
cargo, no tests at all -> Some(true)  ["tests: 0 passed"]
```

`cargo test` has no exit code for *nothing to run*: a crate with no tests exits **0**, so
`result.success` is true, the branch above the exit-5 check fires, and the zero never reaches a
decision. The line it writes is honest — *"tests: 0 passed"* — and the value the gate consumes
is a pass. Two further limits from the same run: cargo exits **101** for both a red suite and a
test target that does not compile, so those are separated only by whether a `test result:` line
was printed at all; and the exit-5 rung is written `framework == Framework::Pytest`, so npm and
go have no equivalent. The generalisation 2.0 needs is one sentence: **ask the process what
happened, and treat "ran nothing" as an outcome in its own right in every profile, not as a
special case for the one runner that gives it a number.**

### F358 — the type, compiled: 17 tests, 8 endings into 6 outcomes where v1 gets 3, and a first draft that invented a count on its first run

`report/` is 441 lines of Rust with no dependencies. `Outcome` is `Measured(Measurement)` or
`Unmeasured { rung, why }`; `Why` has eight variants — no checker for this artifact, checker not
on this host, spawn failed, nothing to run, failed before running, timeout, budget exhausted,
cancelled — and `Headline` is `Green { rungs }`, `Red { rung, detail }` or
`Unverified { missing: Vec<(rung, Why)> }`. There is no `bool` in the data and exactly one
function that produces one, `Headline::is_pass`, deliberately not named `is_ok`.

The properties are assertions, one per donor defect:

| test | the defect it forbids |
|---|---|
| `a_report_with_nothing_measured_is_not_a_pass` | v1's `elif has_meaningful_output:` → SUCCESS at 1.0 |
| `the_reasons_for_not_measuring_are_distinguishable_and_none_is_green` | Claudette's `Skipped` carrying three meanings, folded into `Passed` (F348) |
| `what_the_model_said_never_becomes_what_the_host_saw` | `AgentOutput(**data)` from the model's own JSON (F349) |
| `exhaustion_is_classified_and_is_neither_pass_nor_fail` | W11 F296's `Ok(())` |
| `the_first_red_is_the_headline_and_it_names_itself` | item 5 §8: one type error reported as five regressions |
| `a_cargo_crate_with_no_tests_is_unmeasured_where_the_donor_says_pass` | F357, side by side on the same bytes |

Over the eight pytest/unittest captures the type produces **six classes** where v1's parser
produces three, and the only two endings that share a class are the two that are the same fact.
Over the five cargo captures it produces four outcomes and exactly one pass — the one where two
tests really ran and really passed.

**And its own first draft invented a count.** `counts_from` read unittest's
`FAILED (failures=2)` as *no failures* — the number lives inside a `key=value` token, not a
`<n> <word>` pair — so it reported **2 of 2 passed on a run where both tests failed**. That is
the defect this item is about, in the code written to prevent it, caught by running it against
a real capture rather than by reading it. The rule that came out of the fix is the one worth
carrying: **never derive a number that was not printed.** Where the breakdown is unreadable,
`counts` is `None`, which is a measurement without counts and not a green one.

### F359 — the shape already ships in this repository, at 17,648 metric slots

The last thing this item needs is a demonstration that the contract survives contact with real
work, and it has one that predates the item. W8's harness writes every metric as a tagged
envelope rather than a number:

- **1,369 cells** across every run in `runs/`, carrying **17,648 metric slots**.
- **16,222** are `{"measured": n}`. **1,426** are `{"not_applicable": "<why>"}`. There are no
  bare zeros and no nulls.
- The reasons are sentences, and there are **11 distinct ones**: *"no probe exists yet; W1/W2
  owns building it"* (1,328), *"no turn-end marker, so the session-cumulative counts were never
  printed"* (65 across six metrics), *"no verifier ran for this cell"* (7), *"the subject wrote
  nothing to stdout"* (4), *"the subject produced no output for this turn"* (2), and so on.
- **62 cells have no verifier verdict at all** (`"verifier": null`) and not one of them is
  scored; the cell status vocabulary is five words — `pass` 1,039, `fail` 266, `error` 41,
  `timeout` 15, `invalid` 8 — and not a Boolean.

Q07/`gated` is the whole contract in one cell: the subject looped writing the same broken
514-byte stub ten times, said *"I keep writing the same broken stub"*, and hit the wall.
`status: "timeout"`, `verifier: null`, `iterations: {"not_applicable": "no turn-end marker, so
the session-cumulative counts were never printed"}`, and the delivered tree does not compile.
Every one of those is a fact, none of them is a zero, and the record is legible three months
later — which is how this item read it.

## Options compared

| | v1's shape (Boolean + prose) | BCF's shape (a score) | Claudette's shape (`Option<bool>` per rung) | `Outcome`/`Headline` (this item) |
|---|---|---|---|---|
| "nothing ran" is representable | no — folded into SUCCESS (F349) | no — an unreadable project scores 5.00 (F313) | partly — pytest exit 5 only (F357) | yes, with a reason |
| the reason is carried | no | no | three causes, one `None` | eight named variants |
| a green needs coverage | no | no — the gate is a threshold | no — `ran=false` leaves the LLM verdict standing | yes: `Green` requires every rung measured |
| model prose can become a verdict | **yes** (`AgentOutput(**data)`) | yes (the critique is scored) | no | no — no conversion exists |
| the exit status is read | never | never | pytest only | always, per profile |
| what the console can say | "completed" | "7.5 / 10" | "tests: 0 passed" | "unverified — tests: ran and found nothing to run" |

## Recommendation

**1 — The unit of a report is a rung, and a rung either measured something or says why not.**
`Outcome::Measured(Measurement)` carries the rung name, the exit status the OS returned, the
counts *if the runner printed them*, and the output tail. `Outcome::Unmeasured { rung, why }`
carries a `Why` with eight variants. There is no third variant meaning "fine", and there is no
`bool` in the data. This is item 5's `Measured(exit_code, stdout, stderr)` and item 7's
`Uncertain(why)` composed into one value, and it is 441 lines.

**2 — A pass is a claim about coverage, so `Green` requires every declared rung to have been
measured.** One rung that could not run turns the headline into `Unverified` and lists what was
missing — it does not turn it into a failure, and it does not quietly disappear. `Green` becomes
rarer and it starts meaning something. The console line for the common awkward case is
*"unverified — tests: ran and found nothing to run"*, and item 5 already asked for exactly this
from the language direction.

**3 — Ask the process, never the prose.** Every donor tries to recover *did anything run?* by
pattern-matching the output, and v1 spends 242 lines failing at it because an all-red pytest run
does not contain the word `passed`. pytest and unittest both hand back **5** for "no tests
collected"; cargo hands back 0 and needs the `test result:` line's totals instead; the toolchain
profile from item 5 (F335) is where each runner's exit-code table lives, alongside its marker
file and its command. **The profile owns the exit-code reading, and every profile must answer
"ran nothing" — not only the one runner that gives it a number.**

**4 — Never derive a count that was not printed.** `passed = total - failed` is how this item's
own first draft reported two passes on an all-red run, and `2 run / 0 passed` on a run of three
is how v1 reports the only ending it catches. Parse order-free, sum what is named, and where the
breakdown is unreadable return no counts rather than a plausible pair. A measurement with no
counts is honest; a wrong count is worse than silence because it is actionable.

**5 — What the model said is a different type from what the host saw, and there is no function
between them.** `Claim { by, text }` attaches to a report, is shown to the operator, and cannot
become an `Outcome`. This is the single structural difference from v1, whose
`test_results: str` is a field a model writes and a gate reads, and whose fall-through path
returns the model's own JSON as the record. The claims are worth keeping — F354's *"all the
smoke tests I ran earlier passed (7/7)"* is useful, interesting and true — they are simply not
evidence.

**6 — A measurement is stamped, because scope and time are what prose cannot carry.** F354's two
failure modes are both invisible in a truthful sentence: the tree moved after the measurement (6
of 81) and the measurement was of the wrong thing (14 of 81). Item 6 already produces the
identifier that fixes the first — the snapshot commit sha, 0.16 s — so a `Measurement` names the
sha it was taken at, and a headline computed against a newer sha is `Unverified`, not green.
The second is not fixable by honesty at all; it is the coverage fraction (item 4) and the
pre-image comparison (item 7), and the report's job is only to stop *implying* a scope it does
not have.

**7 — The metric envelope generalises, and this repository has already run it 17,648 times.**
`{"measured": n}` versus `{"not_applicable": "<why>"}` is the same distinction one level down,
with 1,426 live instances, 11 distinct reasons and zero bare zeros (F359). 2.0 emits metrics
the same way, which means the console never has to decide whether a `0` means *none* or *not
looked at*, and a metric with no probe behind it is a visible, sentence-shaped absence instead
of a plausible number.

**8 — Isolate the build directory per attempt, and share the cache only for building.** F356 is
a silent green produced by the toolchain: two work trees holding one package name and one
`CARGO_TARGET_DIR` make cargo declare the second `Fresh` and run the first's test binary. Item
6's warm-cache saving survives — sharing is what makes a fresh worktree compile in 24.7 s — but
**the gate runs in a build directory nothing else writes to.** This costs a rebuild of the
subject crate and it is the difference between a verdict and a coincidence.

**9 — Every rung, measured or not, is an event on the log with a name.** W11 item 5's handoff
(F296) and W3's classified failures are the same object as `Why`: `BudgetExhausted { which }`,
`Timeout { after_ms }` and `Cancelled { by }` are already `FailureClass` members, and
`NoCheckerForArtifact`, `CheckerNotOnHost` and `NothingToRun` join them. The report is then a
projection of the log rather than a second source of truth, which is W3's rule (durability is
the event log) applied to the thing operators actually read.

**10 — Say the honest thing in the unit's own voice.** *"No checker for this artifact"* is a
legitimate report. So is *"ran and found nothing to run"*. The design failure in all three
donors is not that they lie, it is that their vocabulary for *"I did not measure that"* is the
same word as *"I measured it and it was fine"*. Four outcomes, eight reasons, one sentence each.

## Rejected alternatives and why

- **"Add a reviewer that checks the completion report."** This is the answer if the model is the
  problem, and F353 says it is not: 81 of 81 clean-arm claims were true. W11 F281 already
  measured the cost of the opposite direction — the author's *true* completion report pasted in
  front of a diff took a judge from 3/3 to 0/3. A reviewer added here would be reviewing honest
  sentences.
- **"Require the model to emit structured test results."** v1 does, and `AgentOutput(**data)`
  is the result: the model's own JSON becomes the task record whenever it carries a
  `files_created` key (F349). Structure does not change who is speaking.
- **"Score confidence and threshold it."** v1's confidences on the eight endings are 0.7 and 1.0,
  and the 0.7 is `max(0.7, success_ratio)` — a floor, not a measurement, and item 1's exact
  diagnosis. The 0.0 it produces on the one ending it catches is computed from counts that are
  wrong.
- **"Parse the test output properly and the problem goes away."** Claudette parses properly —
  order-free, per framework, 387 lines — and still returns `Some(true)` for a crate with no tests
  (F357), because the defect is not in the parser. It is in a type that has no way to say
  *nothing ran*.
- **"Treat any absent measurement as a failure."** Tempting, and it breaks the honest cases:
  documentation has no test suite (item 7), a Node project may have no `npm` on this host
  (F317), and an operator's cancel is not a failure of the work. `Unverified` is a third
  outcome for a reason — it stops the gate without accusing the unit.
- **"Have the harness re-run the tests after the unit finishes."** It is not wrong and it is not
  the same thing: it produces a *new* measurement rather than making the unit's own report
  honest, and F354's stale-tree cases show why both are needed — the question *"is this report
  about the tree in front of me?"* has to be answerable from the report.

## Effect on fun

The console gets a fourth colour, and it is the one that makes the other three trustworthy.
Today every donor's map is green-or-red, which means green is doing double duty as *"I checked
and it is fine"* and *"I did not check"*. Separating them is worth more to an operator than any
new instrument: at a glance, the fleet splits into work that was measured and work that was
merely finished, and the second group is where attention belongs.

The lines themselves are the fun part, because they are the unit talking about its own
limitations in a specific voice. *"ran and found nothing to run"*, *"ruff is not on this
machine"*, *"still running after 600,000 ms"*, *"rounds budget exhausted"* — each is a different
sentence, each suggests a different next action, and none of them is a tick. A command centre
whose units report *"I could not verify that"* is dramatically more interesting than one whose
units all report success, and it is also the only version where the operator's judgement has
anything to do.

And it turns the most annoying moment in agent work — reading a confident completion message and
not knowing whether to believe it — into a two-line answer. The claim stays, in the unit's own
words, because F354's *"all the smoke tests I ran earlier passed (7/7)"* is worth reading. Under
it sits what the host watched: `tests · 0 measured · nothing to run`. The operator is not being
asked to arbitrate a personality; they are being shown a sentence and a measurement, and told
which is which.

## Open questions

| # | Question | Waiting on |
|---|---|---|
| OQ-W6-21 | The exit-code table for the profiles this item did not capture — npm/jest, go, tsc, shell. pytest and unittest use 5 for "nothing collected", cargo uses none; what do the others do, and is there a profile where no integer answers the question? | item 5's profile table, when the second toolchain row is written |
| OQ-W6-22 | Does a stamped `Measurement` (recommendation 6) need the snapshot sha of the *tree* or of the *changed files*? The 6 stale cases moved one file; a whole-tree sha would also invalidate on an unrelated write | item 6's snapshot, and 2.0's first real attempt |
| OQ-W6-23 | F356 in the other direction: does sharing a build cache across attempts at **different commits** produce a wrong *build* as well as a wrong test binary, or only a stale test target? OQ-W6-14's other half | one probe, cheap, before 2.0 shares a cache for real |
| OQ-W6-24 | 14 of 81 honest green claims sit on failing trees. What fraction of *that* gap the coverage fraction closes is unmeasured here — it needs Localize's site list, which does not exist yet | OQ-W6-8, and W11's Plan phase |
| OQ-W6-8 | Does the coverage fraction bind as a veto, or only as a report? | still open (item 5) |
| OQ-W6-7 | *(item 2)* Rules-only router, or rules plus a recorded model reading? | still open |

## Confidence: high on the donor chain and on the type, high on the corpus result, medium on how far the zero-fabrication rate travels

The donor half is the strongest evidence in the item because none of it is a reading. v1's
parser, both of its status determinations and its TypeScript safety net were imported or ported
and called, on bytes that pytest and unittest really printed, with the exit statuses the OS
really returned; the 15-of-16 table is what those functions returned. Claudette's
`classify_tests` was ported verbatim and produced `Some(true)` with the line *"tests: 0 passed"*
on a real cargo capture. The four documentation sites in F351 are quotations with line numbers.

The corpus half rests on one instrument and the instrument has three controls plus an
independent clock: `control.py` asserts that the verifier's own cargo invocation cannot produce
the artifact the census counts, `cargo build` and `cargo check` cannot either, the hash in the
control matches the hash in the preserved work dir, and the mtime alignment places the subject's
test binary between two narrated tool calls to within a second. Its known weakness is
asymmetric: **presence proves a test run, absence does not disprove one.** A subject whose crate
did not compile leaves no binary and would read as "did not test" — which is why the 7 unbacked
cells were read individually rather than counted, and why the clean-arm number is quoted as
81 of 81 present rather than as a rate over failures.

Three limits worth stating plainly. **The zero-fabrication result is one model on one task
shape**: 14 Q56 Rust tasks, single-file, small, with visible tests already in the fixture, and one of the
fourteen prompts even says *"Run `cargo test` to check your work."* It does not license
"local models do not fabricate test results"; it licenses "on this population the fabrication
rate was zero, so the defect §11 names does not require one." **`visible.py` re-runs the suite
today, not at grade time** — the toolchain has moved since these cells were recorded, and a
tree that is green now was assumed green then; nothing in the 81-of-81 result depends on a
version-sensitive behaviour, but the measurement is a re-execution and not a recording.
And **the type is a design, not a deployment**: 17 tests over 13 captured endings say the
distinctions are makeable and cost nothing, and they say nothing about what happens when a
profile for a runner nobody here has tried meets a run-ending nobody here has captured. That is
OQ-W6-21, and it is the first thing the second toolchain row will find out.

One absence worth recording, because it is the mirror of item 7's. **No probe in this item
needed a model.** The whole of §11's honest-reporting problem — the incident, the fix that could
not fire, the four documented sites, the fourth outcome shadowed by a Boolean, the successor's
surviving green, the build system's own silent pass, and the type that makes all of it
unrepresentable — is decided by exit codes, types and call sites. The one place a model appears
is as the *control*: 98 attempts, 81 claims, and not one of them false.

---
