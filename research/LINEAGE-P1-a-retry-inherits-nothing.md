# LINEAGE P1 — a retry inherits nothing, and seven places said it did

**Status: F701, F702 and F700 are SHIPPED.** `abcc` `ad64194` → **`acde6fa`**, three commits,
**590 tests** (was 581), 19 ignored, `cargo fmt` and `cargo clippy --all-targets -D warnings` clean.
🚨 **The defect was not one false sentence, it was seven true-looking ones**: the claim *a forked
attempt opens on the checkpoint its parent left* was written in **seven places across three crates
and `CLAUDE.md`**, every one agreeing with the others, and **none of them agreeing with
`Driver::open_workspace`** — which snapshotted the operator's checkout and never read `Cause` at all
(F706). ✅ David's ruling: **both `Edit` and `Retry` inherit**, which is what all seven already
promised. 🎉 **F700 then became possible in the same session** — a retry that stands on the refused
tree is a retry that can be told what refused it, and that paragraph was previously written only into
`Event::OperatorPrompted`, which nothing that builds a model body has ever read. 🚨 **Three new
findings came out of building it, and all three are about instruments rather than about the fix**:
the test that would have caught F701 had to compare **trees, not commits** (F704); the precise
lineage read is the one that **throws a person's edits away** (F705); and `Command::OrdersGiven`
**has no sender outside a lifecycle test**, so the retry this ending recommends is reachable only
through `abcc take` + `abcc release` (F703). Findings **F703–F706, next free F707.**
⚠ **Nothing here has been flown.** Both changes are prompt-surface, so F625's verdict and F575's
floor apply: **they want an arm**, and none has been run.

---

## 1. What F701 actually was

`Driver::open_workspace` opened every attempt the same way:

```rust
let taken = self.checkpoint(row, "before")?;   // Driver::checkpoint -> self.repo
```

`Driver::checkpoint` snapshots **`self.repo`** — the operator's checkout. `Cause` is a parameter of
`Driver::run`, it is written to `Event::AttemptStarted`, and **`open_workspace` never saw it.** There
was no branch for `Cause::Retry` and none for `Cause::Edit`. `abcc-fleet` hands the cause to
`driver.run` and builds the `Driver` over the same `self.repo` either way. Exactly two places in the
workspace open a worktree, and only the operator's own `abcc take` opened at a task's last
checkpoint.

The consequence is one sentence: **every retry, every redirect and every resumed hold in this
project's history threw its parent's work away and started again from the same untouched tree.**

🎉 **It was proved as data rather than by reading** — the previous session's five-sortie arm produced
seven attempts with seven *distinct* opening checkpoints, all pointing at one tree object
`9088b222dcbbb8e242c97dfe4aacf8232ebe650c`, with `a7830` — a retry of `a7654`, which had left three
changed files — among them.

---

## 2. 🚨 F706 — seven witnesses, and all of them were prose

The previous session's brief recorded **two** places making the false claim: the sentence in
`brief::redirected` and the doc comment beside it. Reading for the fix found **seven**, at `ad64194`:

| # | where | what it said |
|---|---|---|
| 1 | `abcc-drive/src/brief.rs:40` | *"it opens on the checkpoint the stopped attempt reached"* |
| 2 | `abcc-drive/src/brief.rs:52` | *"the tree you are looking at is the one that attempt left behind"* |
| 3 | `abcc-fleet/src/lib.rs:389` | *"The same question, **from the checkpoint**"* |
| 4 | `abcc-core/src/event.rs:559` | `Control::Redirect` — *"fork a new attempt **from the checkpoint**"* |
| 5 | `abcc-core/src/task.rs:341` | `Command::Resume` — *"the caller forks a new attempt **from the checkpoint**"* |
| 6 | `abcc-core/src/seq.rs:91` | `AttemptId` — *"retry, edit, re-route and replay all fork a new attempt from a checkpoint"* |
| 7 | `CLAUDE.md:240` | *"Retry, edit, re-route and replay are all one operation — fork from a checkpoint with a `Cause`"* |

🚨 **Rows 3, 5 and 6 are about `Retry`, not `Edit`** — which settled the one question the previous
session left open. *Should a `Cause::Retry` inherit too?* was posed as an open design choice; the
design had in fact been written down three times, in three crates, by three different authors of
three different doc comments. David's ruling confirmed it: **both**.

⚠ **The lesson is the count, not the content.** Seven agreeing statements read as overwhelming
corroboration and were worth exactly nothing, because **not one of them was derived from the code** —
each was written from the intended design, and the intended design was never built. This is the same
shape as the memory file's *a comment and a prompt that agree with each other are ONE witness, not
two*, at scale: **seven copies of one unverified belief is still one unverified belief.** What was
missing was a single test that asked git.

---

## 3. What shipped — `Driver::fork_point`

Exhaustive on `Cause`, because the four parented causes do not want the same tree:

| cause | opens on | `continues` |
|---|---|---|
| `Fresh` | the operator's checkout, freshly snapshotted | `None` |
| `Retry` / `Edit` / `Rescope` | **the task's latest checkpoint** | `Some(parent)` — but see §5 |
| `Replay` | the checkpoint its parent *opened* on | `None` |

`Replay` is the arm that would have been wrong by default. It is the console's after-action re-run
and produces no new work; **a replay that starts from the finished tree replays nothing.**

### The opening checkpoint is the parent's own, reused rather than re-taken

So `checkpoint_from` on `AttemptStarted` names a real ancestor instead of a fresh snapshot that
happens to hold the same tree — lineage becomes a fact on the log rather than a coincidence.

🚨 **And that moves what the gate's diff is about: *what this attempt changed*, not what the chain
changed. That is the control, not a side effect.** Without it, a retry could open on a green tree its
parent produced, do nothing whatsoever, and still pass `Rung::Structural` — whose entire job is
refusing an unchanged tree — because the tree differs from the operator's checkout. Since the
operator's ruling of 2026-09-10 a green ladder is promoted to `Accomplished`, so that is **a terminal
success reached by an attempt that did no work.** The test is
`a_retry_that_adds_nothing_to_the_tree_it_inherited_is_refused_by_the_free_rung`.

### A checkpoint the log records and cannot produce is an error

`DriveError::Lineage`, not a quiet fall back to the checkout — because a silent fallback to the
checkout **is F701**, and the model would be told its parent's work was there while standing on a
clean tree.

---

## 4. 🚨 F704 — the instrument that cannot see this bug compares commits

The first version of the control test — *a fresh attempt still opens on the operator's checkout* —
**failed**, and it was right to. Two snapshots of one unchanged checkout are **two different
commits**: `abcc_drive::snapshot` puts the log head in the commit message so the ref name says where
in the replay it was taken, so the commit sha moves even when nothing in the working tree has.

```
2d6975a87e73239a87b7f1cbe8d66959a30464be   |  one checkout,
3d2d7e56a2418b3ee868cc73ef029b3617605f38   |  no edits between them
```

⚠ **This is exactly why F701 survived three milestones.** Any instrument that compared opening
*checkpoint ids*, or their commit shas, would have reported seven attempts opening on seven different
things and found nothing to report. The live-log evidence was a **tree** hash for this reason, and
the test now has `tree_of` for it. **An identity that is stamped with when it was taken cannot answer
whether two things are the same.**

---

## 5. 🚨 F705 — the precise lineage read is the one that loses a person's work

The obvious implementation of *inherit the parent's tree* is **the last checkpoint inside the parent
attempt's span** — bounded by its `AttemptStarted` and its `AttemptEnded`, because `CheckpointTaken`
carries a `task` and no `attempt`. That is the precise answer to *what did that attempt leave*, and
it is **wrong**.

`abcc release` calls `hand_back`, which snapshots the taken-over worktree as `when = "operator"` —
and that event lands **after** the attempt's `AttemptEnded`, inside no attempt's span at all. So the
span-bounded read steps over it and hands the retry the attempt's tree, discarding whatever the
operator did by hand.

🚨 **That is F701's class of loss and a worse instance of it**, because the work thrown away is a
person's rather than a model's. `fork_point` therefore takes the task's **latest** checkpoint, which
is `abcc take`'s own rule (`last_checkpoint`) — so the operator's verb and the fleet's next attempt
continue one tree instead of two.

⚠ **And the attribution narrows when the tree does not.** Once the operator has edited it, *a check
refused the tree you are looking at* is no longer something anyone can say, so `Opened::continues`
goes to `None` and F700's paragraph disappears. **The tree and the sentence about it move together or
they drift** — which is the whole of F702, applied to the fix for F702.

---

## 6. F700 — the refusal that now reaches a model

`brief::refused` writes the rung and the check's own output into `Event::OperatorPrompted`. The only
readers of that event anywhere in the workspace are `abcc-tui`, `replay` and `fun` — **none of which
builds a model body.** So the retry the same ending *recommends* opened with a brief byte-identical
to the fresh attempt's: told the task, and never told that a deterministic check had already refused
this exact work, which one, or what it said.

▶ **Nothing new is written for it.** `AttemptOutcome::Refused { rung, detail }` is already on
`AttemptEnded`, which `Store::task_history` already returns. ⚠ `RungRecorded` carries the same detail,
has **no `task`**, and is therefore not in that history — so the read that exists is the one used.

The paragraph the model now gets:

> ## A check has already refused this tree
>
> The attempt whose work you are looking at was stopped by the `acceptance` rung. It is one of the
> checks this repository asks of every change, it runs again on whatever you leave behind, and until
> it passes the change cannot land however good it is. This is what it said:
>
> *…the check's own output…*
>
> Fix what it names. It is a statement about the tree, not about whether the task was understood.

⚠ It says **cannot land** and not **is wrong** — `brief::refused`'s distinction, and real rather than
diplomatic: on F512's runs the champion's work compiles, prints and passes every test, and is refused
for a function one line over this repository's own limit.

🚨 **It could not have shipped before F701.** *A check refused the tree you are looking at* is only
true if the retry is looking at that tree. The two changes are one change in two commits.

⚠ **It is read from `Opened::continues` and never from the task's last attempt.** Those two answers
differ in two real cases — a replay, and a task the operator has taken over — and the easy one
describes a tree the model is not looking at in both.

### Why this matters on the live subject

Four attempts have reached the standard rung on this subject and **none has passed.** Every refusal
over sixteen arms: `a5738` clippy, `a6689` **fmt**, `a6865` **fmt**, `a7085` clippy, `a8007` clippy —
**half were rustfmt and every summary of them had said clippy.** A model told *the `standard` rung
refused this, and here is what it said* is told which of the two it was. ⚠ Whether it acts on that is
unmeasured; see §8.

---

## 7. 🚨 F703 — `Command::OrdersGiven` has no sender

`AwaitingOrders` is where a refused attempt lands, and it is where fifteen of this project's arm rows
are sitting. Its transition table gives it one edge back to a slot:

```rust
(TaskState::AwaitingOrders { .. }, Command::OrdersGiven { unit, .. }) => Deployed
```

**Nothing in the workspace sends it.** The only occurrences are `abcc-core/tests/lifecycle.rs:352`
and a label in `abcc-tui`'s `line.rs`. `Command::Hold` from `AwaitingOrders` has no production sender
either — the driver's `Landing::Hold` only fires from `Engaged`.

So a refused task's *reachable* exits are: `abcc take` (→ `Commandeered` → `release` → `Queued`),
`accept`, and `reject`. **The retry that `ending()` recommends for a refusal is reachable only by
taking the task over and handing it back** — which is what made §5 load-bearing rather than
theoretical.

⚠ **The transition table is not evidence that a transition happens.** This is the same class as the
archive's *a control whose evidence is a test, with nothing that runs the test*: an edge exists, it
is exercised by a lifecycle test, and no product code drives it.

---

## 8. ⏸ What is owed

1. 🚩 **An arm.** Both changes are prompt-surface, so F625's verdict and F575's floor apply. Same
   subject, same prompt sha `6917f0ccaf0f83c3`. **Nothing in this document is a claim about
   outcomes** — F700's paragraph is *available* to the model and has not been measured, which is
   F650's shape and must not be reported as working or as not working.
2. ⏸ The `summary` lever's second arm (ruling 2, still unscored — `diagnostics` was called **0 times
   in 7 attempts**).
3. ⏸ Decide whether `Command::OrdersGiven` acquires a sender or is removed. An edge nothing drives is
   either a missing verb or a lie in the table.
4. ⏸ The four `paint` changes · row 8's other half · the 96 voice lines.
5. 🚨 **`review_recorded` is still 0 and SELF-HOST still opens on a broken instrument.** Untouched.

---

## Findings

### F703 — `Command::OrdersGiven` has no sender outside a lifecycle test

`AwaitingOrders`'s only named edge back to a slot is driven by nothing in the workspace: the
occurrences are `abcc-core/tests/lifecycle.rs:352` and a TUI label. `Command::Hold` from that state
has no production sender either. A refused task returns to the board only through `abcc take` +
`abcc release`, so the retry `ending()` recommends for a refusal cannot be dispatched any other way.
**A transition table is not evidence that a transition happens.**

### F704 — an identity stamped with when it was taken cannot answer whether two things are the same

Two `abcc_drive::snapshot` calls over one unchanged checkout produce **two different commits**,
because the log head goes in the commit message. Any instrument comparing opening checkpoint ids or
commit shas reports seven attempts opening on seven different things; the live-log evidence for F701
was a **tree** hash, and the control test failed until it compared trees. **This is why F701 survived
three milestones with no test contradicting it.**

### F705 — the precise lineage read is the one that throws a person's edits away

*The last checkpoint inside the parent attempt's span* is the exact answer to *what did that attempt
leave*, and it is wrong: `abcc release`'s `hand_back` snapshots the operator's own work as
`when = "operator"`, **after** `AttemptEnded` and inside no attempt's span — and take-then-hand-back
is the only route a refused task has back onto the board (F703). `fork_point` takes the task's latest
checkpoint, `abcc take`'s own rule. ⚠ The attribution narrows with it: once the operator has edited
the tree, `Opened::continues` is `None` and F700's paragraph is not written, because the tree and the
sentence about it must move together.

### F706 — seven copies of one unverified belief is still one unverified belief

The claim *a forked attempt opens on the checkpoint its parent left* was written in seven places
across three crates and `CLAUDE.md` at `ad64194` — `brief.rs:40` and `:52`, `abcc-fleet/lib.rs:389`,
`event.rs:559`, `task.rs:341`, `seq.rs:91`, `CLAUDE.md:240` — all agreeing with each other and none
with `Driver::open_workspace`. The previous session's brief recorded two of them. 🚨 **Three of the
seven are about `Retry` rather than `Edit`, which answered as already-decided a question that had
been carried forward as open.** Every one was written from the intended design; not one was derived
from the code. **Agreement among prose is not corroboration** — what was missing was a single test
that asked git.
