# ADR-0018 — The Judge reports, in both directions: it cannot refuse an attempt, and it cannot fail one

- **Status:** ✅ **Accepted** — written from a running Judge, after two live reviews on the champion
- **Date:** 2026-08-29
- **Deciders:** Claude Code, building A4 under ADR-0008's four rules; the refusal clause it rests on
  is **David's ruling of 2026-08-28** (ADR-0009 §4, *only deterministic rungs may refuse*)
- **Sources:** ADR-0008's residue measurements — **F275–F284** (pairwise 14/14 against pointwise
  0/8; the runnable triple 10/23 against 1/34; the author's report 0/3 *alongside* the diff) ·
  **F81** (the frozen head) · **F86** (schema-constrained decoding, used nowhere by the donor) ·
  **F498** (the window is observed, not assumed) · **F518** (16 of 25 attempts change nothing) ·
  **F521**, **F522** (both new, below) · the live population is attempts `a2137` and `a2260` on
  `%LOCALAPPDATA%\abcc\abcc-1ae35b6091a63e2c\log.sqlite`
- **Extends:** ADR-0008 (this is its second line, built), ADR-0009 (the `Claim`/`Outcome` boundary),
  ADR-0011 §3 (the schema seam, used here for the first time)
- **Depends on:** ADR-0007 (the snapshot pair the pre-image comes from), ADR-0017 (the rungs the
  Judge is shown)

## Context

ADR-0008 is two lines and only the first was built:

```text
Accept  ⇔  structural ∧ acceptance ∧ ¬Veto        (and every one of them Measured)
Judge   →  a report attached to the attempt, never a term in the conjunction
```

The first line shipped as `abcc-gate` and refused **25 of 25** real attempts on this project's own
log (F518). The second line is the residue: **on the 280 cells where the agent was left alone, no
deterministic rung in any language fired on any of the 29 real failures.** The rungs are cheap and
sound and they do not catch what is left, which is what the second line is for.

**The obvious way to build it is the one every donor took, and it is measurably wrong.** A model
verdict as a gate is 3 of 23 wrong trees at 1 false fail in 34, and *two of the three catches do
not survive a change to the output schema* — so `call` is not measuring a property of the tree.
Worse, the verdict contradicts itself: on **14 of 16** trees the same call names the failing input
and answers `pass`, and on documents it names the planted falsehood at `high` severity and approves
the artifact anyway on **every one of the seven that answered**.

So the question was never *how good is the model's verdict*. It was *what is a model call worth
when it is not allowed to decide anything*, and ADR-0008 answered that with four numbers.

## Decision

**The Judge is one model call, no tools, over a fresh body holding the task, the diff and the
measurements — and it is wired so that it can move nothing.** The rule is symmetric and the second
half is the one that is easy to miss.

### 1. It cannot refuse, and not by discipline

Its answer is an `outcome::Claim`. A `Claim` attaches through `Report::note`, which touches no
`Outcome` and therefore no `Headline`; `Headline::is_pass` is `Green` and nothing else; and **no
function in the workspace converts a `Claim` into an `Outcome`.** `AttemptPhase::may_refuse` is
`!uses_model()`. There is nothing to wire a vote into, which is what David's ruling of 2026-08-28
asked for — a visible edit rather than a quiet one.

### 2. 🚨 It cannot fail an attempt either

**A gate whose *reporter* can fail an attempt is a gate with a fifth rung nobody declared.** The
attempt's ending is computed from the phase and the ladder *before* the review is asked for, so a
review that times out, fills the window, says nothing or comes back malformed leaves the attempt
exactly where the measurements put it. This is not a property the code merely has; it is asserted
by `a_review_that_never_arrives_changes_nothing_about_the_ending`, which runs the same tree twice
and compares the outcome, the headline and the recommendation.

### 3. What it reads is a struct with four fields and no fifth

`judge::Dossier` is the task, the diff, and the rungs. **Nothing either model wrote in prose is in
it.** Same model, fresh call: **11/12** reading the diff, **5/12** reading the author's completion
report (F280), **0/3** when the report is added *alongside* the diff (F281 — the report is
*subtractive*), 4/12 with five empty payloads when it continues the author's own conversation
(F282). Three things are left out, and each absence is a decision:

- **Builders' claim** — F281. The measured worst input available.
- **Recon's brief.** `Head::Commandos`' charter promised it, and **the charter was corrected rather
  than the evidence assumed to match it.** The only measurement this project has about adding prose
  beside a diff is 0 of 3; a localizer's brief is a different unit's prose than the one F281 tested,
  which makes it *untested* rather than *safe*.
- **The headline.** It sees every rung and not the conjunction. A reviewer shown the decision is a
  reviewer asked to agree with it, and the rungs carry strictly more information anyway.

### 4. The pre-image is a diff, and the finding is a triple

Pointwise scoring is **0 of 8** — the model has no absolute scale. Pairwise against the pre-image is
**14 of 14** on the same defects and order-stable on **7 of 7** pairs. A unified diff is the
cheapest honest form of *show it the other artifact*: `Repo::patch_between` pins `--no-ext-diff`,
`--no-color`, `--find-renames` and `--unified=3`, because the artifact a reviewer reads must not
depend on whose git configuration produced it.

`judge::REVIEW` is the first use of the `Schema` seam (ADR-0011 §3, `strict: true`, never
`json_object`). Under `strict` every property is required, so **a finding without
`call → expected → actual` is unrepresentable** — which is what takes 3 of 23 to **10 of 23** out of
the same call. ⚠ The findings array is **bounded**: an unbounded array is the shape that lost
**17 of 57** calls to the token cap, and a sixth finding that does not fit costs one line of a
report where a lost call costs everything. Bounding the artifact is not bounding the verdict,
because there is no verdict here to bound.

### 5. It is not asked when there is nothing to review

Two refusals, both written to the log as a `Note` rather than passed over: an **empty diff** — the
structural rung has already refused, and this is **16 of 25** attempts (F518), so it is the common
case and a model call not made — and a diff over `judge::MAX_PATCH_CHARS`. ⚠ The second **does not
truncate**: a review of part of a change is a review of a different change and would arrive
indistinguishable from a review of the whole one.

## Consequences

- **`Accomplished` still means exactly what it meant.** Live run `a2137`: four rungs green,
  `Headline::Green { rungs: 4 }`, the task terminal — and the review attached to the report changed
  nothing about any of it.
- 🚨 **The residue is real, and it showed up on the first wrong tree.** Live run `a2260`: the
  standard rung refused an `as u64` cast on clippy's `cast_possible_wrap`, the attempt landed
  `Refused { rung: "standard" }` and `AwaitingOrders` **on the ladder's word**, and the review ran
  anyway and reported the defect no rung saw — `Seq::new(-1).back(5)`, where the cast turns a
  negative into a large positive and walks past the saturation the task asked for. It arrived with
  something runnable attached, which is the whole of rule 2.
- 🚨 **F521 — the first live review of a refused tree spent finding 1 of 2 restating the rung it had
  just been shown** (`run: cargo clippy`, `expected: exit 0`, `actual: exit 101`). That is report
  volume with no information in it, and **report volume on wrong trees is ADR-0008's own falsifier**
  — so the brief now says the measurements already ran and a finding that repeats one is a line the
  operator reads twice. ⚠ Unmeasured whether the sentence works; it is one call of evidence and the
  corpora are where it gets a population.
- 🚨 **F522 — the completion is almost entirely trace, and the schema does not touch it.** Two
  calls: 1,708 completion tokens of which **1,589 reasoning** (25.5 s), and 7,808 of which **7,474
  reasoning** (122 s). The constrained artifact is 120–330 tokens; the trace is **93–96% of the
  spend**. ⚠ So the wall-clock cost of A4 is the trace's, not the artifact's, and a bound on the
  artifact — `maxItems`, a shorter brief — buys nothing on time. It is the same shape as F511 one
  level up: the budget goes where nobody was looking.
- **The prompt is small and `MAX_PATCH_CHARS` is untested in anger** — 1,752 and 1,622 tokens on two
  real reviews against a 16,384-token share. The constant is derived from the 32,768-token window
  and `Head::budget`, and it is falsifiable in flight: when it is wrong the call returns
  `Why::ContextOverflow` with the window *observed* (F498), and that is a number to correct it with.
- **A third model call per attempt that changes a tree.** 25 s and 122 s on the two measured; on
  F518's population 16 of 25 would be skipped for an empty diff.

## Alternatives rejected

- **A judge that votes** — the donors' design, and ADR-0009 §4 is David's ruling against it. The
  measurement behind the ruling: 3 of 23, with two of three catches not surviving a schema change,
  and a verdict that names the failing input and answers `pass` on 14 of 16 trees.
- **A pointwise score against a threshold** — 0 of 8. There is no absolute scale to score on.
- **Showing it the author's report** — F280/F281. Not insufficient: *subtractive*, 0 of 3.
- **Continuing the author's conversation** — F282: 4/12, with five empty payloads.
- **A second model as the independent reviewer** — F275, F284, ADR-0003: co-residency is
  arithmetically impossible on this card, the swap is 26.3 s plus 4.6× the decode, and the second
  model returned no verdict at all on the correct answer 3 of 3.
- **Truncating an oversized diff to fit** — it would produce a review of a different change wearing
  a review of this one's clothes, which is the shape of every defect ADR-0009 exists to prevent.
- **Skipping the review when a rung refused** — rejected because that is where the operator most
  needs it: F512's refusals are routinely one line from landing, and `a2260` is the case where the
  rung found the lint and the review found the bug.
- **Putting the call in `abcc-gate`** — the crate that measures does not need a provider seam. The
  pure half (schema, brief, parse, render) lives there and is testable without a server; the call is
  `abcc-drive`'s, where the store, the repository and the provider already meet.

## What would falsify this

**ADR-0008's own falsifier, unchanged and now measurable:** the conjunction's report volume on wrong
trees is high enough that unattended `Accept` is not worth having. F521 is the first evidence in
that direction — one finding of two was noise — and the population that settles it is the corpora:
**56 Q56 fixtures are wrong trees with a known-right refsol beside each**, so the report volume on
wrong trees and the false-report rate on correct ones can both be counted rather than argued. If the
stream is too noisy to read, the Judge earns a refusal on a **named, closed class** of defects —
never a global threshold, and never by adding a function that turns a `Claim` into an `Outcome`.

⚠ A second, narrower falsifier arrived with the build: **if the operator routinely acts on the
review rather than on the rungs**, the claim that a report cannot function as a gate is wrong in
practice even though it is true in the type. The log carries both halves — `ClaimRecorded` and the
`Aborted { CompletedByOperator }` that `abcc accept` writes.
