# LINEAGE P2 — the two arms, and the half of the change that shipped broken

**Status: F701 is CONFIRMED LIVE. F700 shipped broken, the arm proved it, it is REPAIRED and
RE-FLOWN.** Two five-sortie arms on the byte-identical subject (prompt sha `6917f0ccaf0f83c3`, 329
chars, asserted before either was seeded), `qwen3.6-35b-a3b-mtp@iq3_s` at `-c 40960 --parallel 1`.
**9 attempts each, 35 and 43 minutes.** `abcc` `acde6fa` → **`082567b`**, **593 tests** (was 590),
fmt and `clippy --all-targets -D warnings` clean. Findings **F707–F710, next free F711.**

🎉 **F701 works: 7 of 7 retries across both arms opened on their parent's closing checkpoint**, and
4 of those inherited a tree with real work in it. 🚨 **F700 did not fire once in arm 1 — and could
not.** It keyed on `AttemptOutcome::Refused`, which says how the *conversation* ended, while the
thing that matters is the rung recorded against the *tree*. Two attempts left trees the veto rung
had refused with *the tree does not build*; both **ended `Uncertain/BudgetExhausted`**, because what
ran out was the model's rounds. Their retries inherited the wreckage, were told nothing, read a few
files and stopped (F707). 🎉 **Repaired, arm 2 told 3 of 3**, and one of them — `a10364` — **fixed
the exact defect it was named and advanced the failure to the next error**, which this subject has
never done before (F710). ⚠ **n = 5 inheriting retries over both arms. That is not a rate and must
not be quoted as one** (F575, F657). 🚨 **And the load-bearing instrument gap: the brief is on no
event.** 23 event kinds and not one carries what the model was shown, so *was it told* is derived
from a precondition and never observed — for this arm and for every prompt arm this project has
flown (F708).

---

## 1. F701, confirmed as data

| | arm 1 (17–21) | arm 2 (22–26) |
|---|---|---|
| attempts | 9 | 9 |
| retries | 4 | 3 |
| retries that reused the parent's closing checkpoint | **4 of 4** | **3 of 3** |
| …of those, inherited a tree with work in it | 2 | 3 |

Arm 1's row for `a9443` is the one to read: *reused `c9433`, and its parent left work in it* — opened
on tree `a860cfce1966` while every fresh attempt in both arms opened on the checkout. Under
`ad64194` that tree was discarded on every retry this project ever ran.

⚠ **Two witnesses were needed and the first sortie proved it.** `a8808` reused its parent's
checkpoint and opened on a tree byte-identical to the checkout — because its parent had changed
nothing. The **checkpoint id** shows the mechanism; the **tree object** shows the consequence.
Item 139 said compare trees not commits, and that is right for the bug and insufficient here: on
exactly the attempts that did no work, the tree cannot tell inheritance from a fresh snapshot.

## 2. 🚨 F707 — F700 asked the conversation how it ended

`refusal_under` shipped reading `AttemptOutcome::Refused` off `Event::AttemptEnded` — already in
`task_history`, no new read path, and the obvious choice. **It fired zero times in nine attempts.**

Arm 1, `a9292` and `a9480`, identically:

```
structural  measured  exit 0   2 file(s) changed: crates/abcc/src/cli.rs, crates/abcc/src/main.rs
acceptance  unmeasured  failed_before_running
veto        measured  exit 1   the tree does not build — error[E0004]: non-exhaustive patterns …
ENDING      {"outcome":"uncertain","why":{"why":"budget_exhausted","which":"24 rounds"}}
```

**A rung refused the tree. The attempt ended `Uncertain`, because the model ran out of rounds.**
Their retries — `a9443`, `a9649` — inherited those trees, were told nothing, made **no edits at
all**, and were refused by the structural rung for it.

▶ **The rule was already written in this crate, one function over.** `ending`'s comment: *it reads
the headline and not `why`, because `why` says why the **conversation** stopped and the ladder is
about the **tree***. I quoted that line in a comment two commits before keying a sentence about a
tree to how a conversation ended.

**The repair** pages `Store::read_from` across the parent's own span for the first red
`RungRecorded`. No new event; `RungRecorded` carries no `task`, which is why it was never in
`task_history` to be read the easy way.

⚠ **`Rung::Structural` is excluded, and that is the same distinction pointed the other way.** *The
attempt changed no file the repository tracks* is a fact about an **attempt**, not a defect in a
**tree**; every other rung runs a checker on the tree. Two of arm 1's four refusals were exactly
that, and passing one on would be true of the predecessor and useless to its successor.

⚠ **And the split recurs one level up:** an attempt that inherits a tree and does nothing ends
`Refused{structural}` only if it *answered*. `a10131` and `a10851` did nothing and ended
`Uncertain/TruncatedAtCap` and `Uncertain/SaidNothing` — same tree fact, different ending, because
the ending is about the conversation.

## 3. 🚨 F709 — and it was unreachable as well as mis-keyed

A refusal lands `AwaitingOrders`, which the fleet never admits (F703). **Arm 1 produced four
refusals and not one had an attempt behind it.** So `abcc take` + `abcc release` is the only route a
refused task has back onto the board — and `hand_back` *always* writes a checkpoint.

The shipped rule was *`continues` survives only if the latest checkpoint **is** the one that attempt
closed on*. An operator who opened the tree, read it and changed nothing still moved the id. So the
suppression fired on exactly the path that reaches the feature, and F700 had **no reachable
production path at all** — a control whose only evidence was a test, which is the shape this
archive names about other people's code.

▶ **The question is about the tree, so it now asks git**, through `changed_between` — the structural
rung's own primitive, so *did anything the repository tracks move* does not get two answers in one
workspace. **An identity is not content**, for the third time on this feature (F704, F705).

## 4. 🎉 F710 — repaired, and what arm 2 measured

Every retry that inherited real work, both arms:

| attempt | arm | told about a red rung? | did it edit? | ending |
|---|---|---|---|---|
| `a9443` | 1 | no — old keying | no | `refused{structural}` |
| `a9649` | 1 | no — old keying | no | `refused{structural}` |
| `a10131` | 2 | **yes, `veto`** | no | `uncertain/truncated_at_cap` |
| `a10364` | 2 | **yes, `veto`** | **yes** | `uncertain/budget_exhausted` |
| `a10851` | 2 | **yes, `veto`** | no | `uncertain/said_nothing` |

**Told: 0 of 2 → 3 of 3.** That half is mechanical and the repair is what does it.

🎉 **And `a10364` did the thing the paragraph exists for.** It was told its inherited tree failed
with *missing `#[error("...")]` display attribute* at `cli.rs:191`. It edited `cli.rs` and
`main.rs` — the files the task names — **fixed that error**, and its tree then failed on a
*different, later* one (`E0004`, the non-exhaustive match in the test). **It repaired the named
defect and moved the failure forward**, which is the first time a retry on this subject has built on
a predecessor's work at all.

🚨 **Do not turn this into a rate.** Five inheriting retries exist in the world, two under the old
code and three under the new. F575's floor and F657 — `a6865` 4 of 5 against `a7085` 1 of 5 on a
byte-identical prompt an hour apart, on *this* subject — both apply. What is attributable is the
**mechanism**: the paragraph is written, and one attempt acted on it in a way the log shows
step by step.

## 5. 🚨 F708 — the one thing this log cannot tell you is what the model was shown

The log has **23 event kinds** and none of them carries a prompt body. `ModelCallStarted` records
the provider, model, head, ceiling and budget; the brief is not on it, and there is no other
candidate.

So the *told?* column above is **derived, not observed**: it is (the parent has a red non-structural
rung) ∧ (`Opened::continues` is set), which is precisely `refusal_under`'s own precondition. The
unit test is what proves the paragraph is emitted for that precondition; the arm proves the
precondition held.

⚠ **This applies to every prompt-surface arm this project has flown** — F649's `write_file` sentence,
F655's rescue prose, ruling 2's `summary` line, and both halves of this session. In each case the
evidence that the model *saw* the change is a code path plus a test, never a record. That is a
larger gap than any of the individual changes, and it is cheap to close: the opening body of each
phase is already built in one place.

## 6. Both arms, for the record

| | arm 1 (17–21) | arm 2 (22–26) | baseline (12–16) |
|---|---|---|---|
| attempts | 9 | 9 | 7 |
| `refused{veto}` | 2 | 1 | — |
| `refused{structural}` | 2 | 0 | — |
| `uncertain` | 5 | 8 | 4 |
| reached the standard rung | **0** | **0** | 2 |
| passed it | 0 | 0 | 1 |
| `Accomplished` | 0 | 0 | 1 |
| `apply_patch` refused | 13 of 19 (68%) | 14 of 18 (78%) | — |
| `diagnostics` calls | **0** | **0** | 0 |

🚨 **Nothing reached the standard rung in either arm, because the veto refused first — 11 of 11
trees that got that far do not build.** E0004 on the non-exhaustive match, or the missing
`#[error]` attribute, every time. That is the same wall the eleven E0004 arms were named for and it
has not moved.

⚠ **Do not read 0 `Accomplished` against the baseline's 1 as a regression.** F575's floor, F657's
variance on this exact subject, and the subject is **not** byte-identical across the three arms: it
is `abcc` itself, and it carried three commits and nine more tests by arm 1, four and twelve by arm
2. The prompt is identical; the repository under test is not, and it cannot be while the subject is
the project.

🚨 **`diagnostics` is now 0 calls in 18 attempts across two arms**, on top of 0 in 7 last session.
Ruling 2 remains **unscored** and the ceiling is the pickup rate, not the fix (item 137).

---

## Findings

### F707 — F700 keyed on how the conversation ended, and the ladder is about the tree

`refusal_under` shipped reading `AttemptOutcome::Refused` off `AttemptEnded` and **fired 0 times in
9 live attempts**. `a9292` and `a9480` each left a tree the veto rung refused with *the tree does
not build* (E0004, the compiler printing the missing arm) and each **ended
`Uncertain/BudgetExhausted`**, because what ran out was the model's rounds. Their retries inherited
the wreckage, were told nothing, made no edits and were refused for it. The rule was already in this
crate, one function over: *`why` says why the conversation stopped and the ladder is about the
tree*. ⚠ `Rung::Structural` is excluded from what is passed on for the same reason in reverse — *the
attempt changed no file* is a fact about an attempt, not a defect in a tree. ⚠ And the split recurs:
an attempt that does nothing ends `Refused{structural}` only if it *answered*; `a10131` and `a10851`
did nothing and ended `Uncertain`.

### F708 — the log cannot say what the model was shown, and never could

**23 event kinds and not one carries a prompt body.** `ModelCallStarted` records provider, model,
head, ceiling and budget. So *was the model told* is always derived from a code path and a
precondition, never read back — in this arm, and in **every prompt-surface arm this project has
flown** (F649's `write_file` sentence, F655's prose, ruling 2's `summary` line, F700). The evidence
that a change reached the model is a test, not a record. Cheap to close: each phase's opening body
is built in one place.

### F709 — take-and-hand-back always moves the checkpoint, so an identity test suppressed the feature on its only path

A refusal lands `AwaitingOrders`, which the fleet never admits (F703) — **arm 1 produced four
refusals and none had an attempt behind it** — so `abcc take` + `abcc release` is the only route back
onto the board, and `hand_back` always writes a checkpoint. The shipped rule (*`continues` survives
only if the latest checkpoint **is** the parent's closing one*) therefore went `None` on exactly that
path, because an operator who read the tree and changed nothing still moved the id. **F700 had no
reachable production path.** The question is about the tree, so it now asks git through
`changed_between`. **An identity is not content** — third time on this feature.

### F710 — repaired: 3 of 3 told, and one retry repaired the named defect and advanced the failure

Arm 2's three inheriting retries were all told which rung had refused the tree under them (arm 1:
0 of 2). **`a10364` was told its tree failed with *missing `#[error("...")]` display attribute* at
`cli.rs:191`, edited `cli.rs` and `main.rs`, fixed that error, and produced a tree that fails on a
different later one** — the first time a retry on this subject has built on a predecessor's work.
🚨 **Five inheriting retries exist in total and this is not a rate** (F575, F657). What is
attributable is the mechanism, which the log shows step by step.
