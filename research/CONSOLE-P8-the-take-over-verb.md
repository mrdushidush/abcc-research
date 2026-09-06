# CONSOLE P8 — the *take over* verb, and a destructive step that ran before the check that would have stopped it

**Status: `abcc take` and `abcc release` ship, and ADR-0012 §4's eighth verb has a mechanism all the
way down for the first time. `abcc take t42` moves the task to `UNDER MANUAL CONTROL` and hands the
operator a git worktree cut at its last checkpoint — the work as the fleet left it; `abcc release
t42` snapshots what they did in it, takes the tree down and puts the task back on the board. `accept`
and `reject` close the workspace on the way out.** Findings **F627–F632**; next free number is
**F633**. Built 2026-09-06 against `D:\dev\abcc` at `00dc18a`. **504 tests passing (up from 493), 15
ignored, clippy clean under `-D warnings`, `cargo fmt --all --check` clean.** Eleven of those tests
are new, in three files, and **six of them were mutation-checked one at a time**.

▶ This closes item 5 of CONSOLE's non-eyeballing queue: *the verb ledger*. What is left there is the
four GIFs and `rust-embed`.

**The session's shape: the queue item said `take over` was "the one verb of the eight with no
mechanism", and the lifecycle half of it had in fact been shipped since Skeleton. What was missing
was not a state — `Commandeered` has been in the enum, in the theme map and on the roster all along
— but a DIRECTORY. And the moment a person can hold one, an invariant the whole workspace had been
relying on stops being true by accident and has to be enforced on purpose.**

---

## 1. What shipped

* **`crates/abcc/src/takeover.rs`** (386 lines) — the verb. `take`, `release`, the fold that says
  which worktree a task has open, and `hand_back`, the snapshot-then-close the two endings share.
* **`abcc_drive::snapshot`** — the checkpoint recipe, promoted from a `Driver` method to a free
  function taking `&mut Store`. `Driver::snapshot` now delegates to it and `Kept` is public.
* **`abcc_vcs::Repo::adopt_worktree`** — a `Worktree` value for a directory this process did not
  create, so a second process can close what the log told it about.
* **`abcc::ops::finish`** — `accept` and `reject` now go through `hand_back` before the abort.
* **The desk's `resume` caveat** names `abcc take` as the third way out of `Holding`, and says
  plainly that take-over is *not* the `Holding -> Deployed` edge F585 found missing.
* Tests: **9** in `abcc/tests/operator.rs` (real git, real log), **1** in `abcc/tests/cli.rs`,
  **1** in `abcc-vcs/tests/isolation.rs`. No new test target, so `CLAUDE.md`'s process bucket is
  unchanged at nine.

**Driven end to end as an operator, on a scratch repository**: `task` → `take` → edit a file and
add a new one by hand → `release` → the work is at `4dac0d6` on `refs/abcc/checkpoints/m1/6`,
`git show 4dac0d6:NOTES.md` prints a file that has never existed in the repository, and the
operator's own checkout is byte-identical and `git status` clean.

---

## 2. F627 — `holds_workspace: false` on the terminal states was true by an accident of statement order, and this verb is what makes it breakable

`StateContract` gives every one of the nine states a `holds_workspace` flag, and all three terminal
states say `false`. **Nothing enforced it.** The reason it had never been violated is one ordering
inside one function: `abcc-drive`'s `land` closes the attempt's worktree at `lib.rs:478` and sends
the landing command at `lib.rs:500`, so a task could not reach `Accomplished`, `Failed` or `Aborted`
with a directory still open — not because anything checked, but because the close happened first.

**Measured on this project's own log**, 2,689 events over 29 tasks:

| | count |
|---|---|
| `worktree_opened` | **30** |
| `worktree_closed` | **30** |
| `Note` matching *"would not close"* | **0** |
| tasks holding a worktree at the end of the log | **0** |
| leftover directories under `worktrees/`, and stale `git worktree list` entries | **0** and **0** |

So the claim held perfectly for the whole history of the project, and held for a reason that has
nothing to do with the type saying so. 🚨 **A verb that hands a directory to a person breaks that
accident**: an operator can `take` a task and then `accept` it, and there is no `land` in that path
at all. `accept`, `reject` and `release` therefore all call one function, `takeover::hand_back`,
which snapshots the tree and then removes it — and the test is written against the contract
(`assert!(!state.contract().holds_workspace)`) rather than against a list of states, so a tenth
state inherits it.

⚠ The transferable half: **a contract field that has never been violated is not the same as a
contract field that is enforced**, and the way to tell them apart is to ask *what would have to
happen for this to be false* rather than to grep for violations. Here the answer was *one feature we
were about to build.*

---

## 3. F628 — the operator's verb is legal in a strictly smaller set of states than the lifecycle command behind it, and that gap is the feature

`Command::Commandeer` is legal from **every non-terminal state** — six of the nine — and the
transition function early-returns it before the per-state table, deliberately, so that "the
operator's two escape hatches never depend on where the fleet happened to be."

**`abcc take` is legal from four.** It refuses the two where `holds_slot` is true, `Deployed` and
`Engaged`, and the refusal names the desk verb that frees them.

| | `Queued` | `Deployed` | `Engaged` | `AwaitingOrders` | `Holding` | `Commandeered` | terminal |
|---|---|---|---|---|---|---|---|
| `Command::Commandeer` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | refused |
| **`abcc take`** | ✓ | **refused** | **refused** | ✓ | ✓ | ✓ | refused |

🚨 **The one-line reason: the transition moves a state and the verb has to move a directory.** While
a task holds a slot, a live `Driver` in another process owns that worktree and will remove it when
the attempt lands. Two things go wrong if the verb mirrors the command:

* The operator gets a **second tree beside a live one**, cut at the last checkpoint, which is a stale
  copy of work still being written.
* The running attempt **dies**. Every landing command — `Accomplish`, `Fail`, `Requeue`, `Hold`,
  `RequestOrders` — falls through `TaskState::apply`'s table to `NotLegalHere` from `Commandeered`,
  and `Driver::command` turns a refusal into `DriveError::Refused`. Only `Abort` survives, because
  it is the other early return.

⚠ So the test is `StateContract::holds_slot` and not a hand-written list of state names. That is the
same move as F596's rank-from-the-watchdog-contract on the roster, and it is becoming the house
style: **when a display or a verb needs to know something about a state, ask the contract, because a
list of names does not fail when a tenth state arrives — it just stops covering it.**

---

## 4. 🚨🚨 F629 — a destructive step placed before its legality check destroys and *then* refuses, and the log shows it doing both

This is the finding with teeth, and it was found by mutation rather than by reading.

`abcc release` has two jobs: hand the workspace back, and hand the task back. The obvious order is
the useful one — snapshot and close the tree, *then* send `Command::Release` — because `Release`
lands the task in `Queued`, which is the one state a sortie admits, and releasing the task first
would let an attempt cut its own worktree from a checkpoint the operator had not written yet.

**But `Release` is only legal from `Commandeered`, and the refusal comes from `TaskState::apply` —
which is the last thing that runs.** So with the natural ordering, `abcc release t42` typed against a
*flying* task does the whole destructive half first and discovers the illegality afterwards.

Mutation, on a task walked to `Engaged` with a real worktree on the log the way the driver would
leave one. The guard was moved from before `hand_back` to after it, nothing else changed:

```
left:  [... "attempt_started", "task_transitioned", "worktree_opened",
        "checkpoint_taken", "worktree_closed"]        <- what a REFUSED release wrote
right: [... "attempt_started", "task_transitioned", "worktree_opened"]
```

🚨 **A command that exits non-zero saying `Release is not legal in Engaged` had already snapshotted
and removed the running attempt's worktree.** The exit status is honest and the damage is done. The
repair is four lines and no I/O: a **dry run** of the transition — `row.state.apply(&Command::Release,
store.head()?)` is pure — before anything is touched, which keeps `TaskState::apply` the one
authority on legality rather than adding a second `match` that can drift from it.

⚠ **The near-miss on the test is worth as much as the finding.** The first version of the test walked
the task to `Engaged` and asserted *a refused release writes nothing* — and it **passed with the
guard removed**, because an `Engaged` task in that fixture had no worktree on the log and there was
nothing for an unguarded `hand_back` to destroy. F586's shape exactly: the key test would have passed
having measured nothing. It now cuts the driver a real tree first, and asserts the directory is still
standing afterwards.

### The six mutations, and the test each one broke

| mutation | test that failed |
|---|---|
| `cut` always takes a fresh snapshot instead of using the last checkpoint | `a_take_over_cuts_the_tree_at_the_last_checkpoint_and_not_at_head` |
| the `holds_slot` refusal removed | `taking_over_is_refused_while_the_fleet_holds_the_slot` |
| the `release` dry run removed | `releasing_a_task_nobody_took_over_is_refused_before_anything_is_touched` |
| the dry run moved *after* `hand_back` | the same test, with the log above |
| `hand_back` removed from `finish` | `a_task_may_not_go_terminal_still_holding_a_workspace` |
| the adopt-a-standing-tree branch removed | `taking_over_twice_adopts_the_tree_that_is_already_standing` |
| the worktree cut *before* the `Commandeer` | `taking_over_hands_the_operator_the_state_and_a_tree_to_work_in` |

Seven rows, six mutations — the dry run earns two, because its presence and its position are
different claims and the second is the one that matters.

---

## 5. F630 — a worktree could only be closed by the process that opened it, and F631 — there was one caller of the checkpoint recipe and therefore no seam

Two small structural findings that the verb could not be written without, and both have the same
shape: **the driver does a thing from beginning to end inside one function, so the API grew only the
half that one function needed.**

* 🚨 **F630.** `abcc_vcs::Worktree` has private fields and was constructible only by
  `Repo::open_worktree`. The driver opens and closes inside `attempt`, so it never noticed. But the
  durable record of a worktree is `WorktreeOpened { path, sha }` **on the log**, and `abcc release`
  is a second process an hour later holding exactly that and no `Worktree`. `Repo::adopt_worktree`
  is now the constructor for it — no git, no checking, deliberately: the check that matters is *will
  git remove this*, which is `close`'s, at the moment of use. A second check here reading
  `git worktree list` and comparing paths would be a reimplementation that can disagree with the one
  that acts, on a platform where `D:\dev\x`, `D:/dev/x` and `\\?\D:\dev\x` are one directory.
* 🚨 **F631.** The checkpoint recipe — *ask the log for its head, name a ref from it, snapshot, write
  `CheckpointTaken`* — was `Driver::snapshot`, a private method on a struct the operator's verbs do
  not have. It is now the free function `abcc_drive::snapshot`. **The argument for one copy is not
  tidiness**: the `update-ref` in that recipe is what stops `git gc --prune=now` collecting the
  snapshot (F330), so two places that name checkpoint refs is *work quietly lost*, which nobody
  reads a message about.

---

## 6. F632 — three assertions in this session's own tests passed while measuring nothing, and the fixture is why

The tests write `pub fn one() -> u32 { 2 }` into a tree and then assert the change survived. The
first draft asserted `content.contains('2')`.

🚨 **The fixture's unmodified content is `pub fn one() -> u32 { 1 }`, which contains a `2` — in
`u32`.** All three assertions were tautologies. They passed on the first run, on correct code, and
they would have passed on code that cut every tree at `HEAD` and threw the operator's work away.
Caught by reading the fixture back rather than by any failure; fixed to `contains("{ 2 }")`, and the
`cut`-at-HEAD mutation above then failed as it should.

⚠ This is the same family as F594's *a zero from an unvalidated instrument is not a measurement* and
F586's *the key test would have passed having measured nothing*, and it is the cheapest one to fall
into: **a substring assertion over a short needle is a tautology waiting for the right haystack.**
The habit that catches it is the one that caught it here — after a test passes first time, ask what
the fixture would have to look like for the assertion to fail, and check that it does not already
look like that.

---

## 7. The verb ledger, and what it says now

F585 corrected this list once, and it moves again:

| verb | mechanism | state |
|---|---|---|
| `pause` · `halt` · `kill` | control channel | wired, driven live |
| `redirect` | control channel | **logged and inert** — reaches `Keep::AndFork`, nothing forks |
| `resume` | typed lifecycle | **logged and inert** — `Command::Resume` still has no caller |
| **`take over`** | typed lifecycle | 🎉 **wired** — state, directory, and both ways out |
| `retry` | typed lifecycle | the fleet's budget, ADR-0022 |
| `replay` | durable log | `abcc replay`, CONSOLE P7 |

⚠ **`abcc take` does not close F585's gap and the desk now says so at the moment `resume` is
typed.** The missing edge is `Holding -> Deployed`, *the fleet picking the work back up*;
take-over is `-> Commandeered`, *a person taking the work off the fleet*. They are opposite
directions through the same wall. Wiring `resume` is still mechanism 2's work and still David's
question, and `caveat()` is still public and still tested, so **the day it is wired the test fails.**

---

## 8. What this deliberately does not do

* **It is not a desk verb.** `pause`/`halt`/`kill`/`redirect`/`resume` are typed at a run or a sortie
  and addressed to an attempt that is flying; take-over is only legal when nothing is. A sixth word
  on that prompt would be refused every time it was reachable.
* **It does not stop a flying attempt for you.** It refuses and names `halt`. Chaining the two —
  `halt t42` then `take t42` when it lands — is two deliberate acts, and the alternative is a verb
  that kills a run as a side effect of asking for a directory.
* **It does not resolve what the operator did.** `release` puts the task back `Queued` with the
  operator's snapshot as its most recent checkpoint, so the *next* attempt starts from their work.
  Nothing diffs it, nothing gates it, and `accept` is still `Aborted { CompletedByOperator }` rather
  than `Accomplished`, because nothing measured it.
* ⏸ **The take-over is not on the battlefield.** `Commandeered` already draws — F596 put it in the
  operator's rank, nearest the camera, because it is a state nothing but a person can move — but the
  roster has never had a live one on this machine to look at. **Watch it on the next real sortie**;
  this is F602's shape again, one rank further forward.

---

## 9. Driving it

```
abcc take t42        # -> UNDER MANUAL CONTROL, and prints the worktree path
cd <that path>       # ordinary git. It is a detached worktree at the last checkpoint.
abcc release t42     # snapshot, tree down, task back on the board Queued
abcc accept t42      # or: end it by hand. Also closes the workspace.
```

⚠ Three things worth knowing before the first one:

* **The tree is cut at the task's last checkpoint**, which is the closing snapshot of its last
  attempt. A task that has never run has none, so one is taken from the operator's checkout — the
  same recipe `Driver::open_workspace` uses, uncommitted work included.
* **`take` twice adopts the tree that is standing** rather than cutting a second. That is idempotence,
  and it is also the recovery path for the driver's one worktree-leak case: a `close` git refuses is
  recorded as a `Note` and leaves the directory there, so the standing tree is sometimes fresher than
  the last checkpoint.
* **Delete the directory by hand and `release` still works.** It says so on the log — a `Note` and a
  `WorktreeClosed`, so the record and the disk agree again — and takes no snapshot it cannot take.
