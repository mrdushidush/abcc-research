# CONSOLE P4 — the fleet control desk, and two verbs that were never wired

**Status: `abcc fleet` has an operator surface, and the thing that made one unsafe was one layer
below where any desk could see it.** Findings **F582–F586**; next free number is **F587**. Built
2026-09-04 against `D:\dev\abcc` at `90c1273`. **428 tests passing, 14 ignored, 61 targets, clippy
clean under `-D warnings`, `cargo fmt --check` clean.** 17 of those tests are new, and 🎉 **the whole surface was driven end to end against the champion** — see §7b.

▶ This closes item 1 of CONSOLE's non-eyeballing queue. `abcc fleet` had no `pause`, `halt`, `kill`
or `redirect`, and `Ctrl-C` was the only stop; `fleet.rs`'s own doc comment said so and named the
trap — *a desk bound to whichever task happened to be in flight would send a verb to a task the
operator was not looking at.* The trap is real, and it turned out to have a second half nobody had
written down.

**The session's shape: the design question was answered in ten minutes and the next two hours were
spent on the two races underneath it, one of which no desk can see.**

---

## 1. The design: the operator names the task

A `Desk` is opened with one `TaskId` and one `ControlHandle`, which is right for `abcc run` — one
attempt, one channel, the task named once. A sortie moves between tasks, so a desk that spans one
has two ways to be wrong and, on the face of it, no way to be right:

* **Bound to the task it opened on**, it sends verbs to something that landed several attempts ago.
* **Bound to whatever is in flight**, it sends them to a task the operator was never looking at. The
  window is the length of a keystroke: the operator reads `t42 flying`, types `kill`, and t42 lands
  while their hand is moving.

The third answer is that **the operator names the task on every line** — `halt t42`, not `halt` —
and the name is checked against what the slot is actually on. A name that no longer matches is
**refused, never redirected**. That is the whole trade, and it is worth stating as a rule:

> 🚨 **A verb that misses is recoverable. A verb that lands somewhere else is not.**

Two orders are the sortie's rather than a task's, and they are what makes the surface complete
rather than merely safe:

| order | scope | what it does |
|---|---|---|
| `pause/halt/kill/redirect/resume <task>` | the task | ADR-0012 §4's five, addressed |
| `ground` | the sortie | admit nothing more; what is in flight is flown out and lands normally |
| `slot` | — | what is the slot on? reads, changes nothing, writes nothing |

`ground` is the stop that did not exist. Before it, ending a sortie early meant killing an attempt
nobody objected to, or `Ctrl-C` — and `Ctrl-C` takes the process with it. ⚠ It is sampled **once per
loop, before admission**, so it is not a stop and does not pretend to be one; an operator who also
wants the attempt in flight stopped types `halt t42` as well, and the two compose.

`slot` earns its place because the refusal above is only actionable if the operator can find out
what moved. It is the one order that answers the question the race steals from them.

---

## 2. 🚨 F582 — a control channel that outlives its attempt is a queue the next attempt drains

**This is the finding, and it is not a desk problem at all.**

`Fleet::sortie` took **one `ControlPoint` for the whole sortie** and handed the same `&mut` to every
attempt. `ControlPoint::check` drains everything waiting and latches the first stop it finds. So:

1. The operator sends a verb for `t42`.
2. `t42`'s attempt has already passed its last step boundary. The verb sits in the queue unread.
3. `t42` lands normally — `next` is `Some`, so the sortie does not come down.
4. `t43` is admitted, and **its first `check()` drains the queue and latches `t42`'s stop.**

A task the operator never named is halted, by a verb they sent minutes earlier, and **nothing in any
desk can detect it.** The desk did its part correctly: it checked the name, the name matched, it
poked the channel. The mis-delivery happens after the poke, in a queue whose lifetime is wrong.

▶ **Fixed where it lives: the sortie makes a fresh `ControlPoint` per attempt** and publishes its
handle. The previous point is dropped with the attempt that owned it, so a verb physically cannot
outlive its target. `Fleet::sortie` therefore takes **no** `ControlPoint` argument any more — the
one it was given was the bug's whole shape.

⚠ This was latent, not live: `abcc fleet` had no desk, so nothing ever poked. It became reachable
the moment a desk existed, which is the useful thing about it — **the defect was created by the
feature that made it observable, and it was in the code before the feature was written.**

> ▶ **The general shape, for `verify-claims-against-code-not-docs`: a channel whose lifetime is
> longer than its addressee is a mis-delivery that the addressing layer cannot see.** Checking the
> name is necessary and it is not sufficient; the queue has to be scoped to the thing being named.

---

## 3. 🚨 F583 — check-then-poke is the same mis-delivery in slow motion

The obvious desk implementation is *ask which task is flying, then poke the handle*. Those are two
operations, and between them the attempt can land and the next one start. The verb then arrives at a
task the operator did not name — the same failure, through a narrower window.

▶ **The check and the send are one critical section.** `InFlight::deliver(task, control)` takes the
lock, compares the name, sends under it, and returns one of three answers:

| answer | means |
|---|---|
| `Sent` | the slot was on that task and its worker took the poke |
| `Gone` | the slot was on that task and the worker had already finished — the ordinary race |
| `NotFlying { flying }` | the slot was **not** on that task; nothing was poked, and `flying` says what it was on |

⚠ `Gone` and `NotFlying` are held apart deliberately. *Your verb was too late* and *the slot moved,
and here is where it moved to* are two different things for an operator to do next, and one enum
variant answering both would make them guess which.

**And the row is written against the task the operator named, matched or not.** A desk that logged
only what it managed to deliver would lose the verb that arrived one moment too late — which is
precisely the verb an operator most wants to find afterwards.

---

## 4. 🚨🚨 F585 — two of the five verbs have no mechanism behind them

ADR-0012 §4 states the risk in one sentence: **eight verbs that half-work are worse than three that
work.** Wiring the fleet desk meant reading what each verb actually reaches, and two of them reach
nothing. Checked against the code, not the ADR:

* ✅ **`pause`, `halt`, `kill`** — `Keep::AtCheckpoint` / `Keep::Nothing`, honoured at both sampling
  points, landing to `Holding` or `Aborted`. These work.
* ⚠ **`redirect` does not redirect.** It reaches `Keep::AndFork`, and the landing turns that into
  `NextAction::Attempt { cause: Cause::Edit }` — **a recommendation nothing acts on.** `Fleet::sortie`
  reads only `next.is_none()`, and `Fleet::admit` admits `Queued` tasks while a redirect leaves this
  one `Holding`. So the attempt stops, the prompt is written to the log, and **no attempt is ever
  forked from it.** It is a `halt` that also records a sentence.
* 🚨 **Nothing acts on `resume` anywhere.** `disposition()` returns `None` for it, so the control
  point ignores it by design — and `Command::Resume`, the lifecycle's only edge out of `Holding`,
  has **no caller in the binary**: `grep` finds one lifecycle test and one TUI label, and nothing
  else in `crates/`.

⚠ The consequence, stated plainly: `pause`, `halt` and `redirect` all park a task in `Holding`, and
**the binary has no command that puts a `Holding` task back to work.** `abcc accept` and
`abcc reject` do reach it — `Abort` and `Commandeer` are both handled **ahead of the per-state
table** and so are legal from any non-terminal state — so the task is not stuck, but the only ways
out are *finish it by hand* and *stop it*.

▶ **Not faked, and not hidden.** The two verbs still parse, still reach the log, and are still
spelled the same at both desks — the gap is in the mechanism, not in the word, and deleting the word
would only move the surprise to `abcc run`. What changed is that **both desks now say so on the line
the operator gets back**, at the moment it matters:

```
> logged and sent to t42
  ⚠ nothing acts on resume yet — `abcc accept <task>` and `abcc reject <task>` are the ways out of Holding
```

`caveat()` is a public function with a test asserting exactly which three verbs owe nothing and
which two owe a sentence. **The day `resume` is wired, that test fails** — which is the point: the
line telling operators it is not wired has to be removed by the change that makes it false.

▶ **This is a decision for David, not a defect to fix quietly.** Wiring `redirect` is mechanism 2's
work (a typed lifecycle with checkpoints), not mechanism 1's, and it needs the fleet to receive
`Cause::Edit` — which is `abcc-fleet`'s stated job and currently a `next.is_none()` check.

---

## 5. ⚠ F584 — the desks fold case on the verb and not on the task id

`HALT t3` parses; `HALT T3` is refused with *"T3" is not a task id — they look like `t42`*. That
asymmetry is deliberate — the id has to be the spelling `abcc accept t3` already takes, and a desk
that quietly accepted a second spelling would be teaching the operator the wrong one — but it is a
seam, and it was found by a test asserting the wrong thing rather than by reading the code.

The test now states the seam instead of hiding it, which is the only reason it is worth a number: a
reader who meets it at a terminal has one line to find.

---

## 6. ⚠ F586 — the fleet-desk test that would have passed having measured nothing

The test that matters most here is *a verb for a landed task is refused rather than delivered to the
next one*: it sends a `Kill` for the **first** task during the **second** task's attempt and asserts
`NotFlying { flying: Some(second) }`.

🚨 **Every other assertion in it is also true of a run where the verb was never sent** — four
attempts flown, a quiet ending, both tasks in front of a person. The delivery happens inside a
provider wrapper on a chosen call index, and if that index were ever wrong the assertion would
simply never execute and the test would pass green forever.

▶ The refusal is **counted**, and the count is asserted afterwards with the number of calls seen in
the failure message. This is the standing rule — *a zero from an unvalidated instrument is not a
measurement* — in its cheapest form: one `AtomicUsize`.

⚠ The other two operator tests are self-validating and do not need one: if their hook never fired,
`grounded` would come back `Quiet` and they would fail on the next line.

---

## 7. How the operator's surface is tested at all

**The verbs are delivered the way a console delivers them** — named, through `InFlight`, while the
attempt is running — rather than by pre-loading a channel before the sortie starts. That is not
tidiness. A test holding one channel across a whole sortie **could not tell F582's design from the
one that replaced it**, because the thing under test is the channel's lifetime.

A synchronous test has exactly one place it can act while an attempt runs: inside the provider, on
the way to a turn. `OnFirstCall` and `OnEveryCall` wrap `Scripted` and run a closure there. They are
the operator standing in for themselves, and they are deterministic — no thread races the thing it
is measuring.

**The five claims now held by tests:**

| claim | test |
|---|---|
| a named verb reaches the log and the task it names | `a_fleet_verb_reaches_the_log_and_the_task_it_names` |
| 🚨 a verb for a task the slot is not on is logged and sent **nowhere** | `a_verb_for_a_task_the_slot_is_not_on_is_logged_and_sent_nowhere` |
| 🚨 a verb cannot reach the attempt that followed its target | `a_verb_for_a_landed_task_is_refused_rather_than_delivered_to_the_next_one` |
| a stand-down lets what is flying land, and admits nothing after | `a_stand_down_lets_the_attempt_in_flight_land_and_admits_nothing_after_it` |
| the two desks agree about what a word means | `the_two_desks_agree_about_what_a_word_means` |

⚠ The last one exists because the verb table is now shared by two parsers. `parse_verb` is the run's
and takes no task; `parse_order` is the fleet's and requires one; both call one `control()`, and a
word that means `kill` at one has to mean `kill` at the other.

---

## 7b. 🎉 It was run against the real model, and the log agrees with the screen

⚠ Unit tests prove the mechanism; they do not prove the **thread wiring** — the desk reads the
process's stdin, and nothing in a test harness does. So it was driven for real: the champion loaded
in 20.99 s, two tasks on the board, `abcc fleet --rounds 12`, and the orders fed from a timed pipe
while the first attempt was running.

**Every order behaved as designed, on the first run:**

```
  > the slot is flying t2
  > logged against t3, and sent nowhere: the slot is on t2 now. Nothing was done to t2.
  ? pause needs a task. The slot moves between tasks here, so a verb with no name would go to
    whatever is flying when you press enter — which may not be what you were looking at.
    Type `pause t42`, or `slot` to see.
  > standing down after t2 lands. It is still running; `halt t2` stops it too.
  > the slot is flying t2
```

```
sortie  1 attempt(s) flown, and you stood the sortie down — anything still standing by was not admitted
```

🚨 **And the durable log is the proof, not the screen.** Three rows, and the one that is missing
matters most:

| `seq` | row |
|---|---|
| 10 | `attempt_started { task: 2 }` — the slot was on **t2** |
| 26 | `control_requested { task: 3, control: halt }` — written against the task the operator **named** |
| 31 | `note` — the stand-down |

**There is no `control_requested` for task 2, and t2 ran to a normal landing** (`HandToOperator`,
`INTERVENTION REQUIRED`). The verb aimed at a task the slot was not on was recorded and delivered
nowhere; it was not re-aimed at the task that happened to be flying. ⚠ And `t3` is still
`STANDING BY` — the stand-down took effect at admission and reached into nothing.

▶ **One wording fix came out of reading that transcript**, and only from reading it: *"Nothing was
done to t2"* is true and states the safety property, but a reader meets it wondering about t3. It
now reads *"the slot moved to t2, and t2 was left alone."* **A message that is correct and reads
wrong is a message that gets misread once, at the moment it matters.**

⚠ **What this did not exercise:** the first run had `--rounds 2`, the whole sortie of four attempts
finished in under 25 s, and every order arrived after the process had exited — the desk's stderr was
**empty**, and an unread transcript would have been recorded as a pass. The verbs only landed
because the attempts were lengthened and the cadence tightened. *An instrument without a warm-up can
complete having measured nothing*, in its cheapest form.

---

## 8. What this leaves for the next CONSOLE session

The queue as it stood, with item 1 struck:

1. ~~the fleet-level control desk~~ ✅
2. **The six fun queries (ADR-0012 §5).** Still nothing implemented — only the bars are written
   down, in three doc comments. 🚨 The 10-second bar is the most actionable line in W5. ⚠ *Control
   events per run > 0* is now a query that can return something other than zero, which it could not
   before this session: `abcc fleet` had no way to produce a control event at all.
3. Wire the battlefield roster to the task projection. `Battlefield::deploy` already takes units.
4. Replay and the after-action views, over a paged log read that is still a doc comment.
5. **The `take over` verb still does not exist**, and F585 changes what that means: the eight-verb
   acceptance list now stands at *three wired, two logged-and-inert, one absent*, plus replay and
   retry which are elsewhere.
6. Decode the four GIFs.
7. `rust-embed` the 16 distinct images.

▶ **The one question for David**: whether `redirect` and `resume` get wired, or whether the honest
line stays. Wiring them is mechanism 2 and it is a real piece of work — the fleet has to receive
`Cause::Edit`, and something has to own the `Holding -> Deployed` edge that nothing calls today.

---

## Appendix — what changed

| file | what |
|---|---|
| `abcc-engine/src/control.rs` | `InFlight` — the slot's task and channel, and `deliver` under one lock |
| `abcc-fleet/src/lib.rs` | `StandDown`, `Grounded::StoodDown`, per-attempt `ControlPoint`, `sortie()` takes none |
| `abcc/src/desk.rs` | `FleetDesk`, `Order`, `Misread`, `parse_order`, `caveat`, shared `control()` table |
| `abcc/src/fleet.rs` | the desk wired, the banner, and the doc comment that said there was none |
| `abcc/src/cli.rs` | both desks' verbs in `USAGE`, with F585 said out loud |

1,348 insertions, 55 deletions across 7 files.
