# CONSOLE P6 — the battlefield roster, and three layout defects the arithmetic could not see

**Status: `abcc paint` draws the fleet instead of a directory listing — one building per mission,
one unit per live task, positioned by slot, folded out of the event log. The mapping is built and
tested. Three defects in it were found by decoding a painted frame back to pixels, and none of them
was visible in the arithmetic or in the fifteen tests that passed over it.** Findings **F595–F604**;
next free number is **F605**. Built 2026-09-04 against `D:\dev\abcc` at `904fa56`, landed as
**`8148c5e`**. **473 tests passing (up from 451), 15 ignored, clippy clean under `-D warnings`,
`cargo fmt --all --check` clean.** 22 of those tests are new.

▶ This closes item 3 of CONSOLE's non-eyeballing queue: *wire the battlefield roster to the task
projection*. The queue item said it was less work than it looked, because `Battlefield::deploy`
already takes `&mut [Unit]` and only the `--sprites DIR` listing was in the way. **That was right
about the battlefield and wrong about the roster**, which had to answer four questions nobody had
written down: who is on the field, where they stand, which of four pictures they are drawn with,
and what the picture cannot say.

**The session's shape: the mapping took an hour and passed fifteen tests. Then the frame was
decoded, and two of the three things it showed were wrong.**

---

## 1. What shipped

* **`abcc-tui/src/roster.rs`** — the placement. `Post::of` decides a task's rank, `Roster::muster`
  folds a `View` into placed units, and none of it does I/O or knows what a sprite is.
* **`abcc-tui/src/assets.rs`** — `Design`, `Facing`, `Pose` and `Poses`: the corpus, filtered and
  indexed by which picture each file is of. `INTACT` moved here from `abcc/src/paint.rs`, where two
  callers now share it.
* **`abcc-tui/src/view.rs`** — `Card::slot` and `View::card_of`. The slot is the reason (§2).
* **`abcc/src/paint.rs`** — `abcc paint` reads the log, musters, draws, and writes the legend.
  `--corpus` keeps the old view. It opens the log **without booting it**, for the reason `abcc fun`
  and `abcc board` do: boot sweeps orphans and requeues their tasks, and a command that changed
  what it draws by drawing it is not a diagnostic.
* **`abcc-tui/tests/roster.rs`** (15) and seven more in `abcc-tui/tests/assets.rs`.

### The field, in one table

| rank | depth | who stands there | column is |
|---|---|---|---|
| base | **−1** | a mission with at least one live task | its index |
| reserve | 2 | `Queued` | its index |
| line | 4 | `Deployed`, `Engaged` | 🚨 **the slot** |
| waiting | 6 | `AwaitingOrders`, `Holding`, `Commandeered` | its index |
| — | — | `Accomplished`, `Failed`, `Aborted` | off the field |

A mission is a **building** and a task is a **coder**: the one sentence the design axis carries,
and the reason the corpus's second design has a job. Facing is geometry — the formation looks away
from the middle of the field — because the corpus has two facings and nine states, and doubling
state onto facing would be inventing a distinction the art cannot carry.

---

## 2. 🚨 F595 — `Engaged` does not name its slot, so *positioned by slot* is a fold

`TaskState::Deployed { unit, since }` names the runtime slot it holds. **`TaskState::Engaged
{ attempt, since }` does not** — and a task is `Deployed` for the few hundred milliseconds between
the grant and `AttemptStarted`, then `Engaged` for the whole of the work. So for essentially the
entire time a unit is on the line, **its slot is not in its state**.

The slot is in the *log*: `TaskTransitioned { to: Deployed { unit } }` and `AttemptStarted { unit }`
both carry it. `View::project` now folds it into `Card::slot`, and `held_slot` is three cases where
only one is in the state: a grant sets it, any state whose `StateContract::holds_slot` is true keeps
it, and everything else clears it. **The contract decides the third case rather than a second list
that could disagree with it.**

⚠ **A window that opened after the grant honestly does not know.** `Card::slot` is `Option<UnitId>`
and the roster stands such a unit to the **left of slot zero**, at `−1`, `−2`: on the line, because
that is where the log says it is, and off the numbered slots, because `UnitId(0)` would stand it on
top of whatever really is in slot zero — a picture wrong in a way the operator cannot see. The
legend prints `slot ?`.

**Mutation-checked**: deleting the slot line in `View::project` fails
`a_running_task_stands_on_the_slot_the_log_granted_it` and nothing else, because the unit lands at
`−1` instead of on its slot.

---

## 3. 🎉 F596 — the roster's rank agrees with a contract written for the watchdog

`Post::of` is an exhaustive `match` with no wildcard, so a tenth `TaskState` does not compile until
somebody has decided where it stands — the mechanism `theme.rs` uses for labels. **But
exhaustiveness forces an answer, never the right one.** So the answer is checked against
`StateContract`, which was written for reaping and knows nothing about a battlefield:

* `terminal` ⇔ off the field
* `holds_slot` ⇔ the line
* **`Watchdog::WatchNeverReap` ⇔ the operator's rank**

The third is the one worth having. The operator's rank stands **nearest the camera** because those
tasks cannot resolve themselves — and *cannot resolve itself* already has a name in the domain, so
the picture's front row is derivable rather than a matter of taste. Two independent derivations,
checked against each other on all nine states; move a state between ranks for how it looks and the
test names the promise that broke.

---

## 4. 🚨🚨 THE HEADLINE — F597 to F600: the picture was decoded, and it was wrong

The mapping passed fifteen tests. The geometry passed six more, including the one that has guarded
F563 since August. **Then the sixel stream was decoded back to pixels by a second implementation
written for the purpose, and the regions counted.** Two of the three things it showed were defects,
and neither is visible anywhere in the arithmetic.

### F597 — a rank laid out across one `cy` recedes instead of spreading

The obvious layout is *column = index, row = rank*: `cell = (i, rank)`. On the isometric projection
that is not a row at all — `ground` moves **right and down** as `cx` grows, so consecutive units on
a "rank" step diagonally away from the camera, half a tile apart.

A rank laid out along **constant depth** — `cell = (i, depth − i)`, so `cx + cy` is fixed — spreads
by a whole tile per unit, because consecutive cells differ by **two** in `cx − cy` rather than one.

| shape, at `--px 150` on 640x360 | tile | neighbours | of a 100 px figure |
|---|---|---|---|
| this project's own log, as a row | 120 | **60 px apart** | **40% hidden** |
| the same, at constant depth | 135 | **134 px apart** | **0% — clear ground** |
| four full ranks, as rows | 105 | 52 px apart | 48% hidden |
| four full ranks, at constant depth | 67 | 66 px apart | 34% hidden |

**The decode confirms it**: five coders at left edges 6, 140, 274, 404, 538 — pitch 134, 134, 130,
134 — with 96 px of art each.

### F598 — equal depth parity means equal screen columns, and a whole design disappeared

Screen x is `cx − cy`, which on a rank at depth `d` is `2i − d`. **Its parity is the parity of `d`.**
So two ranks at even depths occupy the *same screen columns*, and the rank in front covers the one
behind exactly.

With the ranks at 0, 2, 4 and 6 the single building stood **precisely** behind a queued unit: 100x146
of building art with a 96x129 figure 54 px in front of it, and the decoder returned the two as **one
connected region**. Nothing in the placement arithmetic says so; every test passed; the legend was
correct; the only witness was the pixels.

### F599 — and one step of separation is no separation

Moving the base to depth **1** fixed the parity and did not fix the picture: at one rank-step the
gap is `tile/4` under a figure a whole tile tall, and the decode of a **1280x720** frame still
returned **246x129 of merged art**. The base is now at **−1**: odd, so buildings interleave between
the units ahead of them, and **three steps back**, so there is room to interleave into.

**After the fix, on this project's real log:** six figures, all separate — a building at
(450–549, 45–125) and five coders at 120 px pitch on y 218–346. On 1280x720 with a full reserve:
**seven figures, all separate.**

### 🚨🚨 F600 — the method, and it is the transferable part

**Every check that could have caught these was in place and none of them did.** The unit tests
assert cells; the geometry tests assert that nothing is clipped and that within-rank overlap stays
under half; `battlefield.rs` has asserted the depth sort and the bottom-centre anchor since August.
All of them are about *inputs to* the drawing. **The defect was in the picture.**

This is item 100 of `verify-claims-against-code-not-docs` and it belongs there:
**A TEST THAT ASSERTS THE INPUTS TO A RENDERING CANNOT SEE A DEFECT IN THE RENDERING.** The
instrument is 130 lines of Python that parses our own sixel — palette, bands, run-lengths — floods
the connected regions of non-ground colour and counts them. It cost twenty minutes and it is the
only thing in this session that found anything. ⚠ It is also a **second implementation of the
format**, so it independently exercises the encoder; it lives in the scratchpad rather than the
repository, and if the field is ever animated it should be promoted to an `#[ignore]`d test.

⚠ **Its first answer was wrong and the reason is worth writing down**: the scenery filter took the
*two* most common colours, and the second was the black in the sprites' own outlines, which split
every figure into two regions and reported thirteen. **A threshold picked before looking at the
histogram is a threshold that decides your answer.** The fix is one colour — the ground — and the
tile rule quantises into the same bucket.

---

## 5. F601 — the corpus is admitted by a naming convention *and* a measurement

`Poses::open` keeps a picture only if its filename says which pose it is —
`{design}-{facing}-{action}` — **and** it passes F565's two questions at source resolution. The
convention is the contract, not the four filenames: art that follows it is admitted without a code
change, and a **new design** is a code change, because a design has to be given something to mean on
the field before it can be drawn on one.

**On the shipped corpus, measured:** 4 of 28 files name a pose and all four pass; **24 are
unnamed** — every `cto-*` and `qa-*` — and **0 named files were rejected**. All four poses are
filled. The three ways a pose can be undrawable are counted separately, because *no coder was
drawn* has three causes and they are three different sentences to tell an operator.

⚠ **There is deliberately no substitute.** A missing west-facing coder is not drawn as an
east-facing one; `paint` counts it and names the missing pose. Handing back the mirror would put a
picture on the field saying something the log did not.

⚠ **For David: `--px` normalises heights and throws away the corpus's own proportions.** The
building is 380x568 at source and the coder 300x450; at `--px 150` **both land at exactly
100x150**, so a building is the same size as a person. That is what `--px` has always meant and it
is what he approved in August — but he approved it on a 2x2 of art, not on a field where the two
designs mean different things. **One line to change if he wants the building bigger.**

---

## 6. F602 — inter-rank occlusion is arithmetic, not a bug, and the field height is the bound

Two ranks are `Δdepth × tile/4` apart vertically and a figure is `sprite_h` tall, so nothing behind
is fully clear unless `tile ≥ 4 × sprite_h / Δdepth`. For the base at three steps that is
**tile ≥ 200**, and the clamp caps the tile at `4 × (height − sprite_h) / span`, which at span 7
needs **a field about 500 px tall**. 640x360 cannot do it; **1280x720 can, and the decode confirms
both** — seven merged into five at the default size, seven separate at the larger one.

So the console says so instead of pretending: when the within-rank pitch falls below the art's
width, `abcc paint` prints the percentage and names `--size` and `--px`. ⚠ **Only that one**, which
moves with `--size`. The inter-rank overlap is inherent, is documented on `Post::depth`, and a
warning that fires every time is a warning nobody reads.

**And the rank is bounded at six** — F112's argument one layer up. The queue has no ceiling, and a
rank with no limit shrinks the tile until every unit is a silhouette. What does not fit is
**counted and stated**: *2 more are on the board than a rank of 6 draws*.

---

## 7. F603 — the line rank has never been occupied on this machine, and the legend is why

**Painted against this project's real log: 6 units — one building and five `AwaitingOrders` — and
24 finished tasks off the field.** The reserve is empty and **the line is empty**: of 29 tasks, not
one is `Deployed` or `Engaged`, because nothing was running when the frame was drawn.

🚨 So *positioned by slot* — the queue item's actual sentence — **has no positive control outside
the tests.** This is F594's shape again, and the response is the same: the slot mapping is proved by
`a_running_task_stands_on_the_slot_the_log_granted_it`, `the_line_is_positioned_by_slot_and_not_by_arrival`
and `a_reader_that_arrived_late_stands_the_unit_off_the_numbered_slots` over a real fold, and the
first live sortie after this lands is what confirms it end to end. ▶ **Watch the line rank on the
next `abcc fleet` run.**

### F604 — the field cannot name its units, so the legend does

Two tasks in one rank are the same picture: four pictures, nine states, no text on the canvas. The
field shows the **shape** of the fleet and the legend under it shows which task is which, rank by
rank, left to right, in the order they stand — with the slot for the line and a sentence for every
empty rank. ***No slot is engaged*** is a fact about the fleet; a missing line would be a fact about
the console.

```
the field, from the log — 6 unit(s) on a 640x360 field, 108450 bytes of sixel

  base     m1     abcc
  reserve  nothing standing by
  line     no slot is engaged
  waiting  t1217           INTERVENTION REQUIRED  abcc --version (run 16)
           t1851           INTERVENTION REQUIRED  abcc --version (run 23)
           ...
24 finished task(s) are off the field.
```

⚠ An empty field is an answer, not a failure — and *the board is empty* and *all 24 tasks have
finished* are different sentences, because otherwise **the console being broken and the fleet being
quiet look the same**.

---

## 8. What this does not do

* **It is a still.** Nothing animates, and display FPS is still unmeasured (F562 measured generation
  at 1.91 ms). The roster is a pure function of a `View`, so animating it is a loop and a clock.
* **It is not in `abcc watch`.** The reader is still plain text; `paint` is where the sixels are.
  Putting the field in the reader's viewport is the next milestone-shaped piece of work.
* **`--corpus` still exists and should.** It admits art the field has no job for, which is exactly
  what a person looking at new art needs to see.
* ⏸ **Whether it looks right is David's**, and it is the one question none of this answers. The
  ranks, the facing rule, the building's size relative to a coder, and the ground colour are all
  judgements a decoder cannot make.
