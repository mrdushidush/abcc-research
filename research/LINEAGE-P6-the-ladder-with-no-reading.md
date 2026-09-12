# LINEAGE P6 — the measurement the milestone is judged on, and the archive that could not state it

**Status: queue item 1's agent half is done and its human half is David's.** `abcc` `f3ce25c` →
**`1f2d5ff`**, one commit, **627 tests** (was 621), 19 ignored, `cargo fmt --all --check` clean and
`clippy --workspace --all-targets -D warnings` at **0 diagnostics**. No GPU, no sortie. Findings
**F724–F727, next free F728** — ask `fledger.py next`, never this line.

🚨 **W13's ladder had a writer, a feed line, a status total, and no reading.** `abcc review` has
appended `ReviewRecorded` since Skeleton. `abcc-tui` renders one as a line and keeps a running
total. `abcc replay` — the instrument this project reaches for when it wants a number about its own
history, the one that produced the funnel five days ago — folded every review to `None`. The
archive could not say what the ladder was at.

🚨 **And the unit was wrong, in the flattering direction.** The live screen counted `reviews += 1`
per **event** while the call site that printed the number called it `changes`. Two recordings of one
change — a second pass, or a second reviewer, which is what `--by` is for — would have read as two
changes at half the minutes each: **the review burden falling as a reward for reviewing more.**

⚠ **Every reading of this measurement was correct only because the measurement was empty.** 0 of
**11,391** events is a `review_recorded`. A zero passes through a wrong denominator, a wrong unit
and a mislabelled unit without changing, which is why three defects sat in one small measurement
with a passing test suite over all of it.

▶ **Nothing here is a re-measurement.** `review_recorded` is still 0, and it is still 0 **honestly**
— `abcc review` records how many minutes a *person* spent, so an agent running it on its own commits
fabricates exactly the number SELF-HOST is judged on. §6 sizes the five unreviewed merges for David
and stops there.

---

## 1. F724 — the archive folded the milestone's own measurement to nothing

**F724 — `abcc replay` read 11,391 events and said nothing about the ladder.** The fold's
`attempt_of` returns `None` for `ReviewRecorded`, correctly — a review names a *change*, which lives
in the version control and not in the lifecycle, so it belongs to no attempt and no task. But
*belongs to no task* was implemented as *belongs to nothing*, and the event fell out of the report
entirely.

The two things that did read it are both a **live run's screen**: a feed line as the event scrolls
past, and a status-bar total that resets with the process. Neither answers the question W13 actually
poses, which is a question about *months* — is the human review burden per merged change falling?
That question is only ever asked of the archive.

▶ **This is F718's shape one layer up.** F718 was a field written onto the log with no screen
reading it. This is an event written onto the log with no archive reading it. Both were invisible
for the same reason: **nobody had ever written a row**, so every reader was trivially right.

▶ Fixed at `1f2d5ff`: `abcc_core::replay::Ladder` folds beside the tasks, and `abcc replay` prints
it. On this project's own log, today:

```
W13's ladder — human review minutes per merged change
  nothing recorded: none of these 11391 event(s) is a review, so the ladder has no
  baseline — and a ladder whose baseline starts at Self-Host is unfalsifiable.
  `abcc review <change> <minutes>` writes one. The minutes it records are a person's.
```

⚠ **An absence, not a zero.** `0.0 min over 0 changes` is a sentence a person quotes; *nothing
recorded* is the true one. The status bar keeps `review 0.0 min / 0` and that stays honest for a
different reason — it prints the count beside the total, so the zero cannot be read as *a change
reviewed in no time*.

## 2. F725 — the ladder's two readers disagreed about its unit, and neither had ever seen a row

**F725 — the live screen counted recordings and called them changes.** `abcc-tui`'s view kept
`review_seconds` and `reviews`, incremented once per event; `render.rs` destructured the accessor
into `let (seconds, changes)` and printed `review {minutes} / {changes}`. **The variable name was
right and the number under it was not.**

The scenario is not exotic — it is the one the command was built for:

```
abcc review 223ae3a 10 --by david --boundary     the author's own pass
abcc review 223ae3a  5 --boundary                a second reader, or a second sitting
```

Two changes at 7.5 minutes each, says the old count. **One change at 15 minutes** is the truth, and
the difference is the whole measurement: W13's claim is that a self-hosting project fails on review
burden before it fails on anything else, so a ladder that *improves* when a change is read twice is
pointed the wrong way.

▶ **The fix is one type, not two tallies.** `Ladder::record` is public precisely so both readers
call the same function; the unit is decided once, in the crate that owns the events. A screen that
keeps its own tally of a shared measurement is free to drift from the archive's, and for the whole
life of this project neither could have been shown to be wrong.

▶ **`recordings` is kept beside `changes`** for the same reason F722 keeps `seeds.len()` apart from
`seeded_calls`: the gap between the two *is* the second pass. A reading that kept only one of them
could report either *two changes* or *one change* and never *one change, read twice*.

⚠ **What the fold deliberately does not do: resolve a name.** The operator types the string — a
short sha, a long sha, a task id, a tag. Nothing in the fold can ask git whether `f3ce25c` and
`f3ce25c0d9f2` are one commit, so they are two rows, and a ladder that silently merged them would be
claiming a resolution it never performed. Pinned by its own test.

## 3. F726 — seconds printed as minutes, in the one diagnostic that reads a real log

**F726 — `tests/feed.rs` bound the accessor's first element to `minutes` and printed `{minutes}
min`.** The accessor returned **seconds**. Sixty times too high, in the direction that flatters, in
the one test in this workspace whose whole job is to open a *real* log and print what the reader
makes of it (`#[ignore]`, `ABCC_LOG=…`).

It has never printed a wrong number, because `0` is the same in both units. ▶ **It would have
printed one the first time anybody recorded a review** — which is to say, on the very run it exists
to be trusted on. This is F723's shape (a length in bytes reported as characters) in a test rather
than in a field, and it is the third member of the same family in one measurement.

## 4. F727 — the ladder has no denominator, and never will

**F727 — *minutes per merged change* is measurable; *what fraction of merged changes were reviewed*
is not.** A change that was merged and never reviewed **writes no event at all**. The log holds
reviews, so a fold over it can only ever report the changes somebody reviewed, and `reviewed 5 of 5`
would be true of the fold and false of the repository.

▶ This is the same class as the fold's existing limit — *a gap needs an event on both sides*, so the
hang the silence bar exists for writes no second event — and it is written into the report rather
than left to be discovered:

```
  ⚠ changes somebody recorded a review of — never changes that were merged.
    A merge nobody reviewed writes no event, so this fold has no denominator.
```

▶ **Printed every time the number is**, because the reading it invites is precisely the one it
cannot support. If coverage is ever wanted it needs a second source — the version control — and a
decision about what counts as a merged change; that is a design question and not a reader.

## 5. What shipped, and the two negative controls

`abcc-core` gains `Ladder` and `Reviewed` and folds `ReviewRecorded` into them. `abcc` prints the
ladder on the board, per change, with the passes and the reviewers beside it. `abcc-tui` drops its
private tally and reads the shared one; `minutes()` widens to `u64`, because one review fits a `u32`
and a **sum over months** is the thing being summed.

Six new tests, and the controls are what make them worth anything:

| control | what it breaks | result |
|---|---|---|
| key the rows on the event, not the change | F725's fix | **exactly 3 fail**, one per crate |
| let the boundary flag overwrite, not stick | the sticky rule | **exactly 3 fail**, one per crate |

🚨 **Under both controls all 621 pre-existing tests pass.** That is the finding restated as a
measurement: nothing in the suite could see either defect, because the measurement had never had a
row in it.

## 6. ⏸ The five unreviewed merges — sized, and David's to record

`abcc review <change> <minutes>` writes `by` from `$ABCC_OPERATOR`, defaulting to `operator`. **It
records how many minutes a person spent.** An agent that runs it on its own commits fabricates the
one measurement W13 says SELF-HOST is judged on, so the agent's job ends at making it cheap.

| change | source | non-comment | tests | docs | crates |
|---|---|---|---|---|---|
| `3e5a04b` | 18 | **2** | 123 | 0 | core |
| `1cfe1ac` | 61 | **10** | 240 | 0 | core · engine · tui |
| `d6c60e0` | 0 | **0** | 0 | 30 | docs only |
| `223ae3a` | 109 | **37** | 204 | 0 | core · engine · tui · abcc |
| `f3ce25c` | 158 | **58** | 311 | 0 | core · tui · abcc |
| **total** | **346** | **107** | **878** | **30** | |

▶ **107 lines of the 346 are not comment**, and `scratch/review-packet-session7.md` reproduces every
one of them, comment-stripped, in order, with the recording commands underneath. Sizes are lines
*touched* (insertions + deletions), which is the method the earlier per-session figures used.

⏸ Two decisions ride in those merges and are recorded, not taken: **F721's `Option<u32>` for the
seed** — `0` is both *no seed recorded* and a legal draw, and 1,910 calls predate the field — and
**F723's `len` on `BriefRecorded`**, one word on an already-shipped line that means bytes and says
neither. Both are schema edits to events already on disk.
