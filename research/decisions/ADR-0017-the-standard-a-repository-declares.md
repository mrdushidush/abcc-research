# ADR-0017 — The rung a repository declares for itself, and the veto's one rule

- **Status:** ⏳ **Proposed — one question is David's** (§ *What is David's*, below). Everything
  else here is built and measured; the open question is what *correct tree* means for the Gate's
  own exit criterion.
- **Date:** 2026-08-30
- **Deciders:** written by Claude Code from a running gate; the refusal clause it rests on is
  David's ruling of 2026-08-28 (ADR-0009 §4)
- **Sources:** **F512** (six working implementations, clippy refuses six), **F516** (a tree changed
  by a cut run does not compile), **F517** (a green run's last line says zero passed), **F518**
  (the gate's first full population, 25 of 25) · F356 (the shared build cache) · F357, F350
  (the donors' vocabulary) · the population is attempts `a8`–`a2086` on
  `%LOCALAPPDATA%\abcc\abcc-1ae35b6091a63e2c\log.sqlite`, 2,130 events
- **Extends:** ADR-0008 (the conjunction; this adds a fourth rung it argued against, on evidence
  it did not have), ADR-0009 (`Measured | Unmeasured(Why)`; this adds the one outcome that is
  neither)
- **Depends on:** ADR-0007 (the snapshot pair the free rung diffs)

## Context

ADR-0008 rejected the linter as a rung, and it was right to, on the evidence it had: over **728
real agent attempts in five languages** the linter was *strictly dominated by the test suite in
both languages*. It caught nothing the tests did not.

**F512 is a counter-example from this repository, and it is not a small one.** Twenty-five real
attempts by the champion on one task — *add a `--version` flag to the abcc binary* — are on this
project's own event log. Nine changed the tree. Six of those nine build the binary and print
`abcc 0.1.0`. **`cargo clippy --all-targets -- -D warnings` refuses all six**, on genuine
violations of rules this repository declares in its own `clippy.toml` and `Cargo.toml`; five of
them for the same one (`parse` lands at exactly **101 lines against a limit of 100**,
independently, four times) and one for a different real rule. **On two of the six every test
passes**, so the linter is the only rung that refuses them.

The two results are not in conflict, because they answer different questions:

| | ADR-0008's linter | this rung |
|---|---|---|
| question | does it catch a **wrong** answer? | can this tree **land**? |
| measured | 728 attempts, five languages | 25 attempts, one repository |
| answer | no — dominated by the tests | yes — 2 of 25 are refused by nothing else |

A tree that fails the repository's own declared standard cannot be merged into it, whether or not
it is correct. For a project whose last milestone is **self-hosting**, and whose success measure
is *human review minutes per merged change* (W13), a gate that accepts un-mergeable work is a
gate that spends the reviewer's minutes on the thing CI was going to say anyway.

### The other two things the population made necessary

🚨 **F516: a tree changed by a cut run does not compile.** Raising the completion budget to 16,384
bought three tree-changing runs out of five and cost two trees that end mid-edit. Run against the
whole 25, **7 of the 9 tree-changing attempts leave a tree whose build fails** — and `cargo test`
exits **101** both for a red suite and for a test target that does not compile, so the exit status
alone cannot separate them. `classify_cargo_tests` separates them by whether a `test result:` line
was printed at all, and answers `Unmeasured { FailedBeforeRunning }`. Left there, the console says
*nothing measured it* about a tree that definitively does not build.

🚨 **F517: the sentence beside a correct measurement was the most misleading line in the output.**
`cargo test --workspace` on this repository prints **44** `test result:` lines and the last belongs
to an empty doc-test target, so `last_nonempty` gives `test result: ok. 0 passed` for a run of
**281 passing tests at exit 0**. The counts were never wrong — `counts_from` sums all 44 — but the
`detail` stored next to them was F357's donor defect (*"tests: 0 passed"* on a crate that has
them) arriving as the human-readable half of a **correct** measurement.

## Decision

### 1. The ladder is `structural → acceptance → veto → standard`, and the conjunction is the type

**Nothing implements `∧`.** `Report::headline` already returns `Green` only when every declared
rung produced a measurement and none is red, and `Headline::is_pass` is the one function in the
workspace that produces a `bool`. The gate's job is to produce the right outcomes in the right
order.

Two ADR clauses then hold **by construction rather than by discipline**:

- **The Judge cannot vote.** Its verdict is a `Claim`, which attaches through `Report::note`, and
  there is no function anywhere converting a `Claim` into an `Outcome`. When the Judge is built
  there will be nothing to wire it into.
- **A rung that could not run does not disappear.** It is `Unmeasured(Why)`, the headline is
  `Unverified`, and it lists what was missing.

🚨 **The veto is third rather than last.** It reads the acceptance rung's *absence* and turns the
determinate half of it into a refusal. Placing it after the standard rung would make a tree that
does not build report a *lint* failure — one failure wearing five hats, which is the defect
`Report::headline`'s own doc names.

🚨 **The ladder stops at the first refusal and never at an absence.** A red is a decision and
there is nothing after it worth a cold build; an absence is not, so the rungs after it still run.
This cannot produce a wrong `Green`, because `Green` means nothing refused, which is the case
where every rung ran. On the 25-attempt population it saves a cold build **16 times**.

### 2. The standard rung is declared by the repository, never by us

`Toolchain` gains `standard: Option<Standard>`, and `Standard` carries **witnesses** as well as a
command. For cargo the witness is `clippy.toml` / `.clippy.toml`; for pytest the standard is
`None`, because Python has no single declared standard and picking between ruff, flake8, pylint and
mypy would be this tool choosing a linter for somebody else's repository.

🚨 **An undeclared rung is absent, not missing.** It contributes no `Unmeasured` and does not make
the headline `Unverified`. A workspace with no witness has three rungs and a `Green` that means
what it says.

⚠ **Stated gap:** a project declaring clippy only through `[lints.clippy]` in its `Cargo.toml` is
not detected, because detecting it needs a TOML parser this crate does not have and grepping a
manifest for a section header is a keyword count rather than a declaration. An operator sets the
profile explicitly.

### 3. The veto has exactly one rule, and the other three are named absences

**A tree whose checker could not get as far as running is broken, not unmeasured.** ADR-0008 lists
four veto clauses; three are deliberately not here:

- **empty diff** — the structural rung owns it. A second copy of a rule is a second thing that can
  drift.
- **a required measurement that came back `Uncertain`** — already `Headline::Unverified`, by
  `Green`'s coverage promise, and `Unverified` is the *better* sentence because it lists what was
  missing. Vetoing on it would collapse *we could not tell* into *it is broken*.
- **security HIGH** — there is no scanner until Posture. **A veto that cannot fire is a veto an
  operator will trust for the wrong reason.**

⚠ The acceptance rung's own outcome is **not rewritten**. It stays `Unmeasured { FailedBeforeRunning }`
on the log; the veto is a second rung with a second outcome. Nothing is collapsed — something is
added, and a reader sees both.

### 4. `AttemptOutcome::Refused { rung, detail }`, carrying no `Why`

A red rung is a **measurement**, not an absence: the host watched a checker run and watched it say
no. `Why` is the vocabulary for a rung that produced *no* measurement, and putting a refusal in
there would put a failure into the enum whose whole job is keeping failures and absences apart. So
the refusal carries what `Headline::Red` carries — the rung and the evidence — and `Success` is
the precedent: **the two definite endings are the two that need no `Why`.**

🚨 **`Accomplished` becomes reachable, said by `Headline::Green` and by nothing else.** It was
absent for the whole of Skeleton because nothing was entitled to say it.

### 5. A task may not go terminal while something is owed to a person

A refused attempt lands `AwaitingOrders` and **recommends a retry**. Those do not disagree: an
operator prompt is exactly *here is what I would do, say the word*. Landing a refusal on `Failed`
would make the recommendation unreachable — there is no fleet to act on it — and throw away work
that F512 shows is routinely **one line** from landing.

### 6. A rung's detail is the evidence, not the last line

`outcome::evidence` takes the `error`-prefixed lines from the top **and** the tail, deduplicated
and capped, because the runners disagree about where the fault goes: rustc and clippy put it at
the top and end with `could not compile … due to 1 previous error`, which names neither the lint
nor the function; pytest and `cargo test` put it at the bottom.

⚠ **This is presentation and never a verdict.** The exit status decides (ADR-0009 §5), no count is
derived from any line chosen here, and **no line is selected for what it claims about counts** —
which is the mistake that made a green run say zero.

### 7. The gate may not share a build cache, and that costs real money

F356 qualifies ADR-0007: two trees with one package name and one `CARGO_TARGET_DIR` make cargo
print `Fresh`, run *the other tree's* binary and report `ok. 0 passed` at exit 0. Nothing had to be
done to get this right — `CARGO_TARGET_DIR` is not on `ENV_ALLOWLIST`, so a rung child never
inherits one. **The isolation is a consequence of the allowlist rather than a second rule that
could be forgotten.**

Measured on this workspace: **`cargo test --workspace` 55 s cold, then clippy 13 s, for a
`target/` of 2.3 GB.** ⚠ Fleet has to plan for two of those.

## Consequences

🎉 **F518 — the gate's first full population, and it is the acceptance test ADR-0008 asked for.**
All 25 attempts on this project's log, 373 s end to end:

| refused by | n | mean cost | what it is |
|---|---|---|---|
| **structural** | **16** | 0.0 s | the tree is byte-identical to the one the attempt started from |
| **veto** | **7** | 31 s | the tree does not build |
| **standard** | **2** | 68 s | every test passes; clippy refuses at 101/100 |
| **acceptance** | **0** | — | 🚨 the rung with the best donor yield never fired once |

**25 of 25 refused, every one by a deterministic rung on a real fact, and zero accepted.** The two
`standard` refusals measured **281 and 288 passing tests, 0 failed** on their way to being
refused — the situation F512 predicted, executed.

- 🚨 **The acceptance rung's silence is the finding.** It never refused because **nothing in this
  population ever got far enough to fail a test**: 16 trees did not change, 7 did not compile, and
  the 2 that did compile passed everything. The rung ADR-0008 ranks highest is the rung this
  population never reached — which is an argument for the free rung and the veto, not against the
  tests.
- 🚨 **F512 restated precisely.** *"The tests fail"* was, for 4 of the 6, *"the test target does
  not compile"* — `error[E0004]: non-exhaustive patterns` in `tests/cli.rs`, while the library and
  binary build fine. `cargo test` exits 101 for both, so only the missing `test result:` line
  separates them, and only the veto turns that into a refusal.
- **`AttemptOutcome` grew a variant, and that is safe for the log where a field would not be**
  (F514): a `#[serde(tag)]` enum reads every existing row unchanged. A required field on an
  existing struct is what broke every log that already existed.
- **The reader's exhaustive match did its job**: `Refused` did not compile until somebody decided
  what an operator sees when it happens.
- **The Judge, pairwise comparison against the pre-image, and the report-volume falsifier are
  still unbuilt.** `Measured::changed` keeps the change list for exactly that, so the Judge does
  not pay for a second `git diff`.

## What is David's

🚨 **One question, and the Gate's own exit criterion turns on it.** `PLAN.md` §3 says the
milestone closes on *"zero false fails on the correct-tree population, any one of them fixed as a
rung defect before the milestone closes"*, and ADR-0009 §4 says *a false fail is a bug in a rung*.

So: are F512's runs 10 and 23 — which compile, print `abcc 0.1.0`, pass **281** and **288** tests,
and are refused for a function one line over this repository's own limit — **correct trees**?

- **If the bar is correctness**, they are, and the standard rung false-fails 2 of 2. The rung is a
  defect and comes out, or its limit does.
- **If the bar is mergeability**, they are not: the repository's CI would refuse them, and a gate
  that accepts them hands the operator work that cannot land. Then the standard rung has **zero**
  false fails and the population contains no correct trees at all.

The rung is built either way and one entry in a `const` decides it. **Nothing else in this ADR
depends on the answer** — it decides what the exit criterion is measuring, not what the gate does.

## What would falsify this

- **ADR-0008's original falsifier still stands**: the conjunction's report volume on wrong trees is
  high enough that unattended `Accept` is not worth having.
- **This ADR's own**: 🚨 **the standard rung refuses correct work often enough that an operator
  starts accepting past it without reading.** A rung an operator routinely overrides is a rung
  that has stopped being a gate and started being a speed bump, and the instrument for it already
  exists — `abcc accept` after a `Refused` ending is one query over the log. **If that fraction is
  high, the rung's limit is wrong, not the operator.**
- **The veto's**: a `FailedBeforeRunning` that is *not* a build break — a harness that cannot start
  for an environmental reason — would make its one rule refuse something it should have called an
  absence. Nothing in 25 attempts produced one; the population is small.
