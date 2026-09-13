# LINEAGE P7 — the default that failed invisibly, and the edge nobody has ever taken

**Status: queue item 3's first two entries are closed, and a short probe flew.** `abcc`
`1f2d5ff` → **`6e1cbaa`**, two commits, **629 tests** (was 627), 19 ignored, `cargo fmt --all
--check` clean and `clippy --workspace --all-targets -D warnings` at **0 diagnostics**. Findings
**F730–F735, next free F736** — ask `fledger.py next`, never this line. ▶ **The funnel moved to
5 of 97 = 5.15%.**

🚨 **Both halves of this session are the same shape: a thing that was written down, never read
back, and wrong in the direction nobody would notice.** `paint`'s comment named two failure modes
for a wrong cell height and **both were inverted** — and neither was the mode that actually
happens, which is the terminal silently cutting the bottom off every frame. The lifecycle's
transition table declared an edge out of `AwaitingOrders` that **nothing in the workspace sends and
no transition on the archive has ever taken**, and a research document had already used that edge
as the reason a *different* defect was not a defect.

⚠ **The instrument that settled the second half is the log itself**, folded for the first time over
`task_transitioned`: **333 transitions, 9 of the 12 commands ever sent, 7 of the table's 12
per-state arms ever fired.** A transition table is a claim about what *may* happen; this is the
first time this project has measured what *has*.

---

## 1. F730 — the assumed cell height failed the one way an operator cannot see

`abcc paint --play` reserves rows for the picture by writing newlines and walking back up into
them. How many rows is `field height ÷ cell height`, and **`cell` is told, never measured** — F644
settled that: `crossterm::terminal::window_size()` is `Unsupported` on Windows, and the alternative
is a probe that can hang. F644 also wrote down what happens when the told value is wrong:

> too small and the picture overwrites the report under it, too large and there is a gap. Both are
> visible to the operator, which is what makes a guess allowable where a hang is not.

**Both halves are backwards, and neither is what happens.**

* Told **shorter** than the terminal's real rows: `ceil(H/cell)` is **larger** than the rows the
  picture fills, so more rows are reserved than used and a **gap** opens under it.
* Told **taller**: fewer rows are reserved than the picture fills — and Windows Terminal does not
  overwrite anything. It **clips the image and says nothing**. Measured on David's screen, whose
  rows are 19 px: the shipped default of **20** reserved `ceil(360/20)` = **18** rows for a picture
  that needs 19, and the sixel drew **342 px of the 360 it encoded**, identically at six columns.
  The bottom of every frame never appeared.

🚨 **And the report under the picture survives either way, which is exactly what makes the clipping
the dangerous one.** The caller writes `rows` newlines *and* the `writeln!` it already owed, so the
text below is never overdrawn. Nothing else on the screen looks wrong. A gap is a shrug; a clip is
a picture that is quietly 5% shorter than the one the encoder produced, and there is nothing on the
screen to notice.

▶ **So the default errs short.** `paint::CELL` is **16** and owns both the number and the argument;
`cli.rs` reads it rather than keeping a second copy of it (F725's rule, one owner per unit). At
David's 19 px rows that reserves 23 rows for the 19 the picture fills — **four blank rows, which is
the price of never clipping**, and the price is now asserted rather than discovered.

⚠ **16 rather than 19 is a judgement and nothing pins it.** 19 is one screen, not a floor. What is
pinned is the *direction*: never above the one pitch anybody has measured.

---

## 2. F731 — two assertions about the reservation that cannot fail, and one of them looks exactly like the test

The change David specified was *a test pinning `rows × cell ≥ height`, which nothing asserts*. It
is worth writing out why that test, written as specified, would have passed at the broken default.

**`rows × cell ≥ height` is `u32::div_ceil`'s own postcondition.** It holds for every `cell`,
including the 20 that clipped 18 px off every frame. It is not a statement about the default at
all.

🚨 **The second one is the one that nearly shipped.** Having seen that, the obvious repair is to
sweep the *real* pitches a terminal might have and assert the reservation covers them:

```rust
let given = rows_for(height, CELL);
for real in CELL..=64 {
    assert!(given >= rows_for(height, real));   // passes at 16, at 20, at 200
}
```

**That is `div_ceil`'s monotonicity.** The sweep's floor is derived from the very number under
test, so `rows_for(h, CELL) >= rows_for(h, real)` for every `real ≥ CELL` is true by construction —
at every default there has ever been. It reads as a property and it is a tautology, and it took a
negative control to see it: setting `CELL` back to 20 left it green.

▶ **The floor has to come from the world.** The sweep starts at **19**, the only terminal row pitch
this project has ever measured, and that number is written down as its own constant with the
measurement beside it. Both tautologies are kept in the test, labelled as tautologies, because a
reader who deletes them writes one of them back as the test.

⚠ **It is deliberately not `assert!(CELL <= MEASURED)`.** Clippy refuses that as an assertion with a
constant value, and it is the wrong statement anyway: what has to hold is that the reservation
covers the rows the picture *fills*, and two pitches a pixel apart often round to the same row
count. **The rows are the unit; the pixels are not.**

**The controls.** At `CELL = 20`, exactly **3** tests fail — two in `abcc`'s lib, one in
`tests/cli.rs` — and **both tautologies still pass**, which is the finding restated as a
measurement. At `--px 150`, exactly **1** fails.

---

## 3. F732 — 333 transitions, and five of the table's twelve arms have never fired

F703 left a question: `Command::OrdersGiven` acquires a sender or it leaves the table. The archive
answers it. Folding every `task_transitioned` event on the log:

| command | sent |
|---|---|
| `deploy` | 96 |
| `engage` | 96 |
| `request_orders` | 44 |
| `abort` | 42 |
| `requeue` | 27 |
| `fail` | 20 |
| `accomplish` | 5 |
| `commandeer` | 2 |
| `release` | 1 |
| **`orders_given`** | **0** |
| **`hold`** | **0** |
| **`resume`** | **0** |

**333 transitions, 9 of 12 commands.** By arm: `Abort` and `Commandeer` are legal from any
non-terminal state and are checked before the per-state table, so they account for 44; the other
289 fall through **7** of the table's **12** arms. The five that have never fired are
`(Deployed, Requeue)`, `(Engaged, Hold)`, `(AwaitingOrders, OrdersGiven)`, `(AwaitingOrders, Hold)`
and `(Holding, Resume)` — **`Holding` has never been entered at all.**

🚨 **Of those five, exactly two have no sender in the source, and they are the same state's two
edges back into the fleet's world.** `(Deployed, Requeue)`, `(Engaged, Hold)` and
`(Holding, Resume)` all have callers — F646 wired the last two — and have simply never fired here.
`AwaitingOrders`'s do not exist: `Landing::Hold` only fires from `Engaged`, and `OrdersGiven`'s only
caller anywhere in the workspace was the lifecycle test that asserted it.

▶ **So `OrdersGiven` leaves the table**, and nothing is lost. 44 tasks have arrived in
`AwaitingOrders`; **41 left by `Abort`, 2 by `Commandeer`** (of which 1 was released back to
`Queued`), and 1 is standing there now. That route — `abcc take`, `abcc release`, `Queued` — is the
same shape as every other return to work in the system: through the state whose contract is
*eligible for admission*, with the pool handing out the slot rather than a desk command naming one.
`OrdersGiven` would have had a desk command name a slot it has no way to reserve.

⚠ **And the removal touches nothing on disk.** `Command` is serialised inside
`Event::TaskTransitioned`, so removing a variant is a schema edit over data already written — F721's
class. It is safe here for a reason that had to be checked rather than assumed: **zero
`task_transitioned` rows carry it**, because nothing ever sent it.

🚨 **The consequence nobody drew.** `FLEET-P2` excused the refusal path from F548's contradiction in
these words: *"A deterministic rung refusing already lands `AwaitingOrders` and recommends
`Attempt`, and those two do not disagree: `AwaitingOrders` is non-terminal and **`OrdersGiven`
re-opens it**."* It does not re-open it and never did. **17 of the 96 ended attempts ended
`Refused`** — 8 standard, 7 veto, 2 structural — each returning `NextAction::Attempt` beside a state
that no verb can dispatch an attempt from, while `Fleet::admit` scans `Queued` then `Holding` and
never `AwaitingOrders`. The path is still defensible, because a refusal one line from landing is
something a person should see (F512) and the operator *can* act on the recommendation by hand. But
**the reassurance named a mechanism that does not exist**, which is the same defect as the one it
was excusing, in prose instead of in code.

---

## 4. ⏸ F733 — the other arm with no sender, recorded and deliberately not taken

`(AwaitingOrders, Hold)` is undriven for exactly the reason `OrdersGiven` was: `Command::Hold` is
sent only from `Landing::Hold`, which needs a live attempt, and a task in `AwaitingOrders` has
none. **It is not the same decision.** `OrdersGiven` was a variant that existed for one arm, so
deleting it forecloses nothing any verb can do. `Hold` is a live command, and its arm here becomes
reachable the day `pause` learns to address a task that is waiting on a person — which is a
question about whether an operator may park an `INTERVENTION REQUIRED` row, and therefore a
decision rather than a clean-up.

▶ **Left standing, flagged in the state's own doc comment, and put to David.** It joins F721
(`Option<u32>` for the seed), F723 (`BriefRecorded`'s `len`) and F727 (the ladder's coverage).

---

## 5. F734 — grepping the event log for an identifier now hits the model's reading

The first query run against the log for `OrdersGiven` returned **2 rows**, which reads exactly like
*something sent it twice*. Both are `tool_call_ended`: attempt `a11320` called `read_file` on
`crates/abcc-tui/src/line.rs` — **twice, 18,324 bytes each, byte-identical** — and F713's `output`
field now carries the file's text onto the log, identifier and all.

▶ **A search over the log's bodies stopped being a search over the system's own vocabulary the
moment tool output landed on it.** The fix is to key the query on `kind` (`task_transitioned`,
here) rather than on the body, and it is the same lesson as *reach for the repo's own instrument
before writing a query* arriving from the other side: F713 made the log richer and made one class
of query less reliable in the same commit.

---

## 6. F735 — the probe: an attempt that wrote the test and not the feature, and passed the structural rung

▶ **A short GPU probe, David's call, one attempt.** The task was deliberately the change this
session would otherwise have made by hand: *`abcc replay` bare says nothing about the transition
table — add one line reporting how many arms have ever been taken and how many transitions there
were, and a unit test for it.* Champion loaded in 15.5 s, `abcc check` matched exactly, pulse
1 token in 503 ms.

`a11400` ended **`Uncertain { BudgetExhausted { 24 rounds } }`** in the Change phase, after
**37 model calls, 528,163 in / 23,630 out**, 13 turns of Localize and 24 of Change,
**0 denials**, 2 nudges, worst TTFB 10.9 s.

🚨 **It wrote 106 lines and none of them were the feature.** The whole diff is a new
`#[cfg(test)] mod tests` appended to `crates/abcc/src/replay.rs`, testing a line that was never
added. **The structural rung passed it — `exit 0`, *1 file(s) changed*** — because structural
measures that the tree changed, not that it changed *toward the task*. The veto rung then refused:
the tree does not build.

⚠ **The three build errors are worth keeping, because two of them are about this codebase and
only one is about the model.**

* `E0433: cannot find module or crate atomics`, three times — the model wrote
  `UnitId(atomics::AtomicU64::new(1))`. A slot id is a `u8`. That one is a hallucination.
* `E0603: tuple struct constructor UnitId is private` — it reached for
  `abcc_core::task::UnitId`, which is a private `use` inside `task.rs`; the public path is
  `abcc_core::seq::UnitId`, whose field is `pub u8`. **A re-export that is private is a name that
  resolves and then refuses**, which reads as a visibility bug rather than a wrong path.
* `(TaskState, Command)` does not implement `Ord`, so the `BTreeSet` it reached for cannot hold
  one. Neither type derives `Ord` **or `Hash`**, so no standard set will. ▶ **And that is the
  finding, not the error.** An arm's identity is a pair of *discriminants*, and both types already
  carry `name() -> &'static str` for exactly that; the census in §3 was keyed on those names.
  The model keyed on the **values**, which are the one thing here that does not compare.

⚠ **What the run says about itself, printed on its own last line:**
`next Attempt { cause: Retry { of: a11400 } }  (a recommendation; nothing acted on it)`. That is
§3's finding stated by the program during a live run — the parenthetical is honest and the prose
in `FLEET-P2` was not.

🎉 **And two readers were confirmed live on a real log for the first time since they
shipped.** `sampler 37 of 37 call(s) seeded, 37 distinct` (F715/F719's seed, read back off the
archive) and a per-tool byte tally on every tool — `read_file 16 call(s) [116,600 bytes back]`,
`bash 12 call(s) at exec [2 non-zero, 5,516 bytes back]` (F713/F718). ⚠ **12 `bash` calls at the
exec tier, where the previous sortie had zero**, and the one `apply_patch` call was **not** refused
— n = 1 against a 77% refusal rate, so it is an observation and not a rate.

▶ **The funnel: 5 of 97 = 5.15%** (was 5 of 96 = 5.2%). The row was closed with
`abcc reject t11392 --note` naming the agent as the closer, because the veto's verdict is measured
rather than judged and the note keeps a human's words off the log. **0 worktrees standing.**

---

## 7. What shipped

**`fix(paint,cli)` `9767688`** — `paint::CELL` = 16 owning the number and the argument, `rows_for`
carrying the three real modes where the inverted comment was, `--px` 150 → 120, the usage text and
both struct docs, the two pins in `tests/cli.rs` (and the test's own *hundred and fifty* in its
name), and `roster.rs`'s *"at the default `--px 150`"*, which was measured at 150 and would have
gone stale the moment the default moved. Two new tests.

**`refactor(core,tui)` `6e1cbaa`** — `Command::OrdersGiven` removed from the enum, `name()`, the
transition table, `names_attempt` and `abcc-tui`'s label; `CLAUDE.md` and two `abcc-drive` test doc
comments rewritten off the census; and the lifecycle test that was the variant's only caller
rewritten to assert its **absence** — four commands that could reach a slot refused with
`NotLegalHere` *specifically*, `Engage` naming the in-flight attempt on purpose so it is the table
refusing and not the wrong-attempt guard, then take-and-release walked. Control: expecting
`Refused::Terminal` fails it.

---

## 8. ⏸ Still owed

1. 🚨 **The five unreviewed merges are now seven**, and `review_recorded` is still 0 and still
   honest — confirmed on the live fold at 11,586 events. `abcc review` records what a *person* spent. Sizes for the first five are in LINEAGE-P6
   §6; this session adds `9767688` and `6e1cbaa`.
2. ▶ **K-series arms B and C** — `n ≥ 3` repeats, **no seed** (F728: the subject is greedy and a
   seed is inert). Hours of GPU; ask first.
3. ⏸ A second arm for the `summary` lever · row 8's other half · the 96 voice lines.
4. ⏸ **Four decisions parked for David**: F721, F723, F727, and now **F733**.
