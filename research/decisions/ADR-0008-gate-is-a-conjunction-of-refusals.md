# ADR-0008 — The gate is a conjunction of refusals, never a weighted average

- **Status:** ✅ Accepted
- **Date:** 2026-08-28
- **Deciders:** Claude Code (W6 items 1–7), ratified with `research/SUMMARY.md`
- **Sources:** W6 F158–F161, F213–F224, F297–F310, F311–F324, F336–F348 · W11 F231, F233, F254,
  F258, F266, F272, F276–F284
- **Depends on:** ADR-0007 (the change list and the pre-image both come from the snapshot pair)
- **See also:** ADR-0009, which owns the *outcome type* and the rule that only deterministic rungs
  may refuse

## Context

**Every donor gate is a number, and every one of those numbers is a lie in a measurable way.**

- **BCF scores a perfect Python file 5.80 and a language it has never heard of 8.00**, against a
  gate of 8.00 — so it cannot pass a documentation project at any complexity (5.00 → 7.00), and it
  builds a virtualenv to run pytest over markdown.
- **`result.score || 5` — the sentinel scores a zero as a five** (F233), and **`5.0` is the family's
  `Uncertain` spelled as a passing-ish score** (F258).
- **The measurement set is collapsed into one float, and the float adds an opinion to a
  measurement** (F254).
- **v1's only binding gate is a shell command, and it reports pass when the command is absent**
  (F231). Its validation channel scores a green test suite as a failure, and its five-language
  syntax table discriminates in **0 of 6** languages on this host while its validation channel runs
  **1 of 13** real commands.

Then the rungs themselves were measured on real populations rather than argued about. Over **728
real agent attempts in five languages**:

| Rung | Result |
|---|---|
| **Type check** | **0 of 160** real failures caught; `tsc` **false-failed 5 correct answers** |
| **Syntax check** | 0 of 114 |
| **Linter** | strictly dominated by the test suite in both languages |
| **Free structural check** — *did the change touch any source file* | **9 of 12** on repository work, **0 false positives on 609 correct trees** |
| **Acceptance test** | **5 of 6 in every cell of the language grid** |
| **Generated tests** | 4/9 written *before* the change — and **ratify a wrong change 6/9** written after it |

🚨 **And on the 280 cells where the agent was left alone, no rung in any language fired on any of the
29 real failures.** That is the honest starting position: the deterministic rungs are cheap, sound,
and they do not catch the residue.

The residue was then measured on the 57 trees that survive every rung. **A model verdict is not a
gate**: 3 of 23 wrong trees, 1 false fail in 34, and **two of the three catches do not survive a
change to the output schema** — so `call` is not measuring a property of the tree. **What it is, is a
report that contradicts itself**: on 14 of 16 trees it names the failing input and answers `pass`,
and on documents it names the planted falsehood at `high` severity and approves the artifact anyway
on **every one of the seven that answered**.

## Decision

**The gate is a conjunction of refusals. Every rung may refuse; nothing may compensate.** There is
no weighted average, no threshold, and no score anywhere in the type (ADR-0009).

```
Accept  ⇔  structural rung ∧ acceptance test ∧ ¬Veto        (and every one of them Measured)
Judge   →  a report attached to the attempt, never a term in the conjunction
```

### Rung order and why it is that order

1. **The free structural rung first — because it is free, never because of a rate.** Its yield is a
   property of the task's shape: 9/12 on repository work against 0/29 on clean single-function work.
   It is the diff between two snapshots (ADR-0007, 0.024 s), so it costs nothing to run first.
2. **The acceptance test** — one executable criterion per task (ADR-0002's M1 output), and it
   **costs less than the ladder that decides nothing**.
3. **Veto** — deterministic, non-scoring, boolean: security HIGH, empty diff, build break, a required
   measurement that came back `Uncertain`. **A veto is never a weight** (F217).
4. **Judge** — one model call, no tools, after Measure, **seeing the measurements**.

### Four rules the Judge is built under

- 🚨 **Show it the other artifact, not a threshold.** Pointwise scoring is **0 of 8**; pairwise
  against the pre-image is **14 of 14** on the same defects, **order-stable on 7 of 7 pairs**.
  Position bias did not reproduce at all; verbosity bias did, weakly, and only on a genuine tie. The
  pre-image is free — ADR-0007 produces it in 0.16 s.
- 🚨 **A review finding must carry something runnable, or it is not a finding.** Running the
  reviewer's own `call → expected → actual` makes 13 of 15 claims on wrong trees really discriminate
  — **10 of 23 caught against 1 of 34 false, three times the recall of the same model's own verdict,
  out of the same call.** ⚠ **The schema is not free:** 2.8× the decode, 2.7× the wall clock, and
  **17 of 57 calls lost to the token cap** — every one legibly `finish_reason: length`, which is a
  measurement, not a score (ADR-0009).
- **What it reads decides its quality, not whose weights it is.** Same model, fresh call: **11/12
  reading the diff, 5/12 reading the author's completion report** (F280), **0/3** when the report is
  added *alongside* the diff (F281 — the report is subtractive), 4/12 with five empty payloads when
  it continues the author's own conversation (F282). **Nothing the author wrote in prose reaches the
  gate.**
- **A second model is not the answer here.** Co-residency is arithmetically impossible on this card
  (ADR-0003), the swap is 26.3 s round trip plus 4.6× the decode, and the second model **returned no
  verdict at all on the correct answer 3/3** (F284).

### The free rung for prose

**Addresses and nothing else.** 1,873 unique addresses across four corpora, one provably stale
citation, **0 false positives — and 1 of 7 planted document defects**, the one that is an address
rather than an assertion. It is worth having because it is free and never wrong, not because it
covers the class. (It also found that **F22–F29 are cited 23 times in six documents and defined in
none**.)

## Consequences

- **`critic_inflation` does not ship** — item 3's verdict has no score, so the quantity does not
  exist. Its successors are the **veto yield, the contradiction count, the criterion-coverage
  fraction and the `Uncertain` count** (OQ-W6-2 closed). W8's +3.65 median inflation over 34
  missions stands as motivation, not as a number 2.0 reproduces.
- **Acceptance criteria are executable or they do not exist** — and **red-before-green is
  necessary**: of 35 model-generated criteria, **zero are red before the change and green after it**
  (F266), 5 of 35 discriminate against three wrong answers, and **0 survive a comment written to
  defeat them** (F279). A criterion is validated by running it *before* the change.
- 🚨 **Share the build cache for building, never for the gate** (F356). Two trees holding one package
  name and one shared `CARGO_TARGET_DIR` make cargo print `Fresh`, run *the other tree's* binary and
  report `ok. 0 passed` at exit 0 — **a green test run that measured nothing.** This qualifies
  ADR-0007's shared-`CARGO_TARGET_DIR` ruling.
- **The gate is the product, and it is where the schedule risk concentrates** — SUMMARY.md's risk 3.
  The GATE milestone exists to make right-vs-wrong separable before anything is parallelised.

## Alternatives rejected

- **A weighted average or a score against a threshold** — every donor's version, and F254 is the
  general statement: collapsing a measurement set into one float adds an opinion to a measurement.
- **A pointwise judge score** — 0 of 8. The model has no absolute scale.
- **Type and syntax checking as the verification workhorse** — 1 of 160 across 728 real attempts,
  and `tsc` false-fails correct answers.
- **Generated tests as a gate** — they ratify a wrong change 6 times in 9 when written after it.
- **A second model as the independent reviewer** — F275, F284; see ADR-0003.
- **A reviewer that reads the author's report** — F280/F281: it is not merely insufficient, it is
  *subtractive*.
- **A per-language rung ladder** — F311–F324: what is language-specific is a **toolchain profile**
  (extensions, build command, test command, binary path), and the expensive part of the donors'
  abstraction is output parsers keyed to a *tool*, not a language.

## What would falsify this

**The conjunction's report volume on wrong trees is high enough that unattended `Accept` is not
worth having** — the falsifier that replaced the old false-fail one when David ruled that only
deterministic rungs may refuse (ADR-0009). The measured base for the exposure is *10 of 23 wrong
trees caught by execution*; the rest arrive as reports. If that stream is too noisy to read, the
Judge earns a refusal on a **named, closed class** of defects — never a global threshold.
