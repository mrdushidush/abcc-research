# ADR-0009 — `Measured | Unmeasured(Why)`, and only deterministic rungs may refuse

- **Status:** ✅ Accepted — the refusal clause is **David's ruling of 2026-08-28**, held strictly
- **Date:** 2026-08-28
- **Deciders:** David (only deterministic rungs refuse), Claude Code (the type, W6 item 8)
- **Sources:** W6 F349–F359, esp. **F358** (the type, compiled, 17 tests) and F359 · W6 F336–F348 ·
  W11 F296 · W3 F189 · `PLAN.md` § Gate
- **Depends on:** ADR-0008 (the conjunction this type is the value of)

## Context

**The family's vocabulary for *"I did not measure that"* is the same word as *"I measured it and it
was fine"*.** That is the design failure, and it is not that the donors lie:

- **v1's dispatcher is gated on the word `passed`**, which an all-red pytest run does not contain,
  so **eight real run-endings become three records** and *every test failed* is indistinguishable
  from *there were no tests*. **The exit status separates all of them** — pytest and unittest both
  use **5** for "no tests collected" — **and no donor reads one** (F350).
- **v1's chain marks 15 of 16 records *completed*, including the all-red run its own documented fix
  was written for**, and the one it stops reports **2 run / 0 passed** on a run of three with one
  passing.
- **v1's `UNCERTAIN` exists, is constructed once, and sets `success=True` in the same literal**;
  `ExecuteResponse` has no status field at all. And v1's main failure classifier always writes
  `null` (F189).
- **The successor is the best of the three** — `Option<bool>`, order-free parsers, the only exit-code
  rung in the family — **and still returns `Some(true)` with the line "tests: 0 passed"** for a cargo
  crate with no tests (F357).

The honesty question was also measured from the model's side, and **§11's reading of its own incident
turned out to be wrong**. On 98 unimpeded Q56 Rust attempts the champion asserted the tests pass 81
times, a test really ran **81 of 81**, and re-running the suite on the delivered tree makes **81 of
81 of those sentences true**. *And it does not help*: **14 of the 81** true, measured, green claims
sit on trees the hidden gate fails, and **6 of 81** measured a tree that no longer existed — the edit
lands 1.7–3.0 s after the test binary. One subject wrote seven tests, ran them, **deleted them**, and
truthfully reported *"all the smoke tests I ran earlier passed (7/7)"* over a tree with no tests in
it. 🚨 **What prose cannot carry is scope and time, not truth.**

## Decision

### 1. The type

**`Outcome::Measured(Measurement) | Outcome::Unmeasured { rung, why }`. There is no third variant
meaning "fine", and there is no `bool` in the data.** `Why` has **eight variants** — no checker for
this artifact · checker not on this host · spawn failed · nothing to run · failed before running ·
timeout · budget exhausted · cancelled. `Headline` is `Green { rungs }`, `Red { rung, detail }` or
`Unverified { missing: Vec<(rung, Why)> }`, and exactly one function produces a `bool`:
`Headline::is_pass`, deliberately not named `is_ok`. **441 lines, no dependencies, 17 tests, one per
donor defect** (F358).

### 2. `Green` is a claim about coverage

**`Green` requires every declared rung to have been measured.** One rung that could not run turns the
headline into `Unverified` and lists what was missing — it does not become a failure and it does not
quietly disappear. **`Green` becomes rarer and it starts meaning something.** The console line for
the common awkward case is *"unverified — tests: ran and found nothing to run"*.

### 3. A `Claim` never becomes an `Outcome`

**`Claim { by, text }` attaches to a report, is shown to the operator, and there is no function that
converts it into an `Outcome`.** This is the single structural difference from v1, whose
`test_results: str` is a field a model writes and a gate reads. The claims are worth keeping — they
are useful, interesting and often true — **they are simply not evidence.**

### 4. 🚨 Only deterministic rungs may refuse — the Judge never blocks

**David, 2026-08-28, holding the corpus's most reused ruling strictly rather than nearly.**
Unattended `Accept` is gated on the structural rung, the acceptance test and Veto — **nothing else.
The Judge reports, and its report is never a vote.**

**This removes a tuning knob instead of setting one: there is no false-fail rate to pick, because a
false fail is a bug in a rung.** The measured base is **0 false positives on 609 correct trees**.

**The accepted cost, stated plainly:** the wrong trees only a model would catch — Phase 1 measured
**10 of 23** — now reach David as **reports rather than blocks**. That is the trade, and it is the
right way round, because **a report costs attention while a false block costs trust.**

### 5. Ask the process, never the prose — and never derive a count that was not printed

**The toolchain profile owns the exit-code reading**, and **every profile must answer "ran nothing"**,
not only the one runner that gives it a number. `passed = total - failed` is how this item's own
first draft reported two passes on an all-red run — and how v1 reports `2 run / 0 passed` on a run of
three. **Parse order-free, sum what is named, and where the breakdown is unreadable return no counts
rather than a plausible pair.** A measurement with no counts is honest; **a wrong count is worse than
silence because it is actionable.**

⚠ **The type's own first draft invented a count.** `counts_from` read unittest's
`FAILED (failures=2)` as *no failures*, because the number lives inside a `key=value` token rather
than a `<n> <word>` pair, and reported **2 of 2 passed on a run where both tests failed** — caught by
running it against a real capture, not by reading it.

### 6. A measurement is stamped with the sha it was taken at

Both of F354's failure modes are invisible in a truthful sentence: **the tree moved after the
measurement** (6 of 81) and **the measurement was of the wrong thing** (14 of 81). ADR-0007 already
produces the fix for the first — the snapshot commit sha, 0.16 s — so a `Measurement` names its sha,
and **a headline computed against a newer sha is `Unverified`, not green**. The second is not fixable
by honesty at all; it is the coverage fraction and the pre-image comparison, and the report's job is
only to stop *implying* a scope it does not have.

### 7. Every rung, measured or not, is an event on the log

`Why` and W3's `FailureClass` are the same object: `BudgetExhausted { which }`, `Timeout { after_ms }`
and `Cancelled { by }` are already members, and `NoCheckerForArtifact`, `CheckerNotOnHost` and
`NothingToRun` join them. **The report is then a projection of the log rather than a second source of
truth** — ADR-0005's rule applied to the thing operators actually read.

## Consequences

- **Eight endings become six outcomes where v1 gets three**, over the same eight pytest/unittest
  captures; and over five cargo captures, four outcomes with **exactly one pass** — the one where two
  tests really ran and really passed.
- **`Ok(())` on budget exhaustion is forbidden by the type** (W11 F296): exhaustion is classified and
  is **neither pass nor fail**.
- **The metric envelope generalises, and this repository has already run it 17,648 times.**
  `{"measured": n}` versus `{"not_applicable": "<why>"}` is the same distinction one level down, with
  **1,426 live instances, 11 distinct reasons and zero bare zeros** (F359). 2.0 emits metrics the same
  way, so **the console never has to decide whether a `0` means *none* or *not looked at***.
- 🚨 **This is the one type that must not be added later** (`PLAN.md` ground rule 4): it ships in the
  first commit that runs anything. Retrofitting it means rewriting every call site that returned a
  `bool`.
- **`finish_reason == length` with an empty payload is `Uncertain`, never a score** — the 17 of 57
  judge calls lost to the token cap are legible, and they are absences, not failures.
- **The instrumentation is not optional** (`PLAN.md` §5): every rung's `Unmeasured(Why)` reason is
  logged from the first milestone.

## Alternatives rejected

- **A tri-state that folds "skipped" into "passed"** — Claudette's `Skipped` carries three meanings
  and folds into `Passed` (F348); the type forbids it by assertion.
- **`5.0`, or any midpoint, as the absence value** — F258: the family's `Uncertain` spelled as a
  passing-ish score, and `result.score || 5` scores a zero as a five (F233).
- **Recovering *did anything run?* by pattern-matching the output** — v1 spends 242 lines failing at
  it. The exit status already separates every ending.
- **Letting the Judge block on a tuned false-fail rate** — David's ruling; and the earlier draft's
  "a few percent" quietly assumed a Judge that could block, contradicting the ruling it was written
  under.
- **A `bool` anywhere in the data** — one function produces one, at the edge, by name.

## What would falsify this

**The report stream on wrong trees is frequent or noisy enough that unattended `Accept` is not worth
having.** Then the Judge earns a refusal on a **named, closed class** of defects — never a global
threshold, and never a rate to tune. This is the same falsifier ADR-0008 carries, because it is the
same trade seen from the type's side.
