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
2. ☐ **The pipeline inheritance** — BCF's nine stages against Claudette's five-phase forge; what
   carries, what the successor already collapsed. Feeds W11's reconciliation.
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

Scope reference: `RESEARCH_BRIEF.md` §11 lines 808–827. Findings continue the family numbering
(W3 item 2 ended at F157).

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
