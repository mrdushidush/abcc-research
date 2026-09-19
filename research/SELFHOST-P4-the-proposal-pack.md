# SELF-HOST P4 — the proposal pack, for David to rule on

**Status: proposals, not changes. David ruled *measure and propose, you rule*, so nothing here is
applied and nothing in `D:\dev\abcc` has moved — it is at `71f6aa8` apart from the arm's detached
checkout, which is restored. Block A rewrote this pack: the chain SELFHOST-P1 argued from
(`apply_patch` refuses → the round budget dies) is false, because refusals cost 8.8% of the rounds
(F773). What spends the budget is reading, half of it re-reading (F774). So the pack has one
proposal the evidence actually points at, two that are real but small, and one that is now measured
to be a quarter of the population rather than all of it. Each carries what it would move, what it
would cost, and what would have to be measured to know whether it worked.** Written 2026-09-18
while the REDACT arm flew. Findings **F781–F782**; next free is **F783**.

---

## Proposal 1 — carry Recon's reads into the Change phase, under a cap ▶ **the one to take**

**The evidence.** The Change phase spends **50.5%** of its tool calls on `read_file`, and **47.1%**
of the reads whose path is recoverable re-read a file **Recon already read in the same attempt**
(F774). `a12881` made 5 first reads and **24 re-reads**, then died `BudgetExhausted`.

**The mechanism is in the brief, not the model.** `brief::change` says *"Recon's report is a claim
about the tree rather than a measurement of it, so check the part you are about to rely on before
you rely on it."* That sentence is right — it is ADR-0009's honesty rule — and the brief hands over
Recon's **sentence** while dropping the **bytes**. Obeying it therefore costs a round per file.

🚨 **And a tool result is a fact while a prompt is a request.** `workspace.rs:673` already argues
this for F673: W7 measured the best prompt in its family at 39 of 50 and a better-written one at
0 of 50. **Rewriting the sentence is the weak lever; handing over the bytes is the strong one.**

### 🚨 F781 — the cap is the design, because the naive version does not fit

Measured over the F713-era attempts, the **unique** `read_file` output Recon produced per attempt:

| | bytes | ≈ tokens at 4 B |
|---|---|---|
| p50 | 39,757 | **9,939** |
| p90 | 75,829 | **18,957** |
| max | 191,687 | **47,922** |

▶ **Against the measured median headroom of 16,057 tokens (F775), carrying everything fits at the
median and blows the window at p90.** So *carry Recon's reads* is not implementable as stated, and
the honest form is **carry the most recent N tokens of them, oldest dropped first, N a constant
with a name**. ⚠ A cap that truncates in the middle of a file hands the model a lie of exactly the
kind F529 is about — a rendering that is wrong about a thing that is right — so the unit dropped
must be **a whole file**, never a slice of one.

**What it would move:** the Change phase's 24 rounds stop being spent re-fetching. **It should show
up as fewer `read_file` calls per Change phase and more attempts reaching a gate verdict** — and if
it does not, the hypothesis was wrong and the cost has been paid for nothing.

**What it costs:** ~10k tokens of context at the *start* of the Change phase instead of accumulating
at the end, and the 9-of-36 cut cohort (F775) gets worse before it gets better. **This is why it
ships with the cap or not at all.**

**How to know it worked — pre-specify before flying:** `read_file` calls per Change phase
(now: 50.5% of 927 calls over 36 attempts) and the ending distribution (now `budget_exhausted` 14
of 30). ⚠ **The 47% re-read figure is only recoverable from `read_file`'s output text and only for
the F713 era** (F771), so the after-measurement must use the same instrument or it is not a
comparison.

---

## Proposal 2 — the round budget ⏸ **propose, but not on its own**

`Limits::rounds` is **24** per phase (`turn.rs:228`), and `for round in 0..self.limits.rounds` is
one model call per round whatever the tool did.

🚨 **F773 says refusals are not why it runs out.** So raising the budget buys *more reading*, which
is the thing Proposal 1 exists to stop. ▶ **Raising rounds before Proposal 1 is measured would
confound the only clean comparison available**, and if Proposal 1 works the budget may not need
touching at all.

⚠ **The memory already carries a standing instruction on this — *do not raise rounds*** — written
when the endings were `BudgetExhausted` twice, `TruncatedAtCap` and `SaidNothing` across four
attempts. Nothing measured since contradicts it. **Recommendation: hold, and revisit only with
Proposal 1's after-measurement in hand.**

---

## Proposal 3 — `apply_patch`'s markup fold ⏸ **real, and smaller than its reputation**

**42 of 163 recorded refusals** are the model's own tool-call markup arriving inside the diff
argument — F637's class, which F641 put in the **server's** parser, before `abcc` sees anything.

🚨 **F771 resized the whole question.** `apply_patch` applies **~36% of what it is handed and always
has** — 36.9% pre-`F713`, 36.0% after, 95 of 258 calls. The *"77% refused"* and *"31 ok / 35 refused
of 66"* figures in this project's memory are narrower windows, and one of them straddles an
instrument change. **The tool did not get worse and it did not get better.**

**What it would move:** at F773's exchange rate, about **two rounds in thirty**. Worth having,
**not** worth calling the blocker.

### ✅ F782 — F649 IS NO LONGER UNSCORED. The trigger fires perfectly and the repair does not work.

F649 shipped in `e5625a8` at **2026-09-07 19:40:59**: the markup refusal names `write_file` as the
way out. F650 recorded it as *flown, and the trigger never fired*. **The query was run
2026-09-18 and the trigger has fired 33 times.**

| day | markup refusals | name `write_file` |
|---|---|---|
| 09-06 | 3 | **0** — before the fix |
| 09-07 | 13 | 7 — the fix lands at 19:40:59 |
| 09-08 · 09-11 · 09-14 | 4 · 17 · 5 | **4 · 17 · 5 — every one** |

🚨 **And the model takes the offered exit once in thirty-three — 3%.** What the very next tool call
actually was, in the same attempt:

**`read_file` 18 (55%) · `bash` 7 · `apply_patch` again 7 (21%) · `write_file` 1 (3%).**

▶ **So F650's *never fired* is superseded, and the repair it was waiting to score has been scored:
the sentence is delivered 33 of 33 times and complied with once.** ⚠ This is W7's result again, at
this project's own expense — a prompt binds only as far as the model complies, measured at 39 of 50
for the best in its family and 0 of 50 for a better-written one. **Here it is 1 of 33.**

🎉 **It is also the strongest available argument for Proposal 1.** F649 is a *sentence* and it
bought 3%. Proposal 1 is a *tool result*. `workspace.rs:673` makes exactly this distinction for
F673, and F782 is the first time this repository has measured its own sentence and watched it fail.

▶ **Recommendation: do not iterate on the wording.** The next thing worth trying for markup is on
the server side of F641's fold, or nothing.

---

## Proposal 4 — the window, for the cut quarter only ⏸ **not a general guard**

**27 of 36 `budget_exhausted` attempts were never cut and die with ~16k to spare; 9 were cut**, the
deepest by 27,041 tokens (F775). ▶ **So a global context guard would be built for a quarter of the
population and would cost the other three quarters the headroom Proposal 1 needs.**

✅ **`Event::PromptCut` is young, not blind** — all twelve cut attempts predate it by hours. **Ten
attempts have run since and none was cut**, so the detector is untested rather than vindicated.
▶ **The right next step is not a guard. It is to let `PromptCut` accumulate a population** — and
Proposal 1, which pushes context earlier in the phase, is exactly the change most likely to give it
one. 🚨 **Ship Proposal 1 with the detector watched, and the guard becomes a decision with data
behind it instead of a precaution.**

---

## What I am NOT proposing, and why

* 🚨 **Nothing about the gate's rungs.** `standard` is `cargo fmt --check` then
  `clippy -D warnings`, and ADR-0017's criterion is *a correct tree is one that could land*. That
  bar is the repository's own and moving it moves what the product accepts.
* 🚨 **Nothing about the brief's honesty sentence.** Proposal 1 makes obeying it cheap; it does not
  weaken it. Deleting *check before you rely* would buy rounds by making the model more credulous,
  which is the trade ADR-0009 exists to refuse.
* ⏸ **Nothing about `said_nothing`** (14 of 108, 4 of the last 30). It is a real class and I have
  no mechanism for it — 995 completion tokens of which 990 were reasoning, on the last one. **An
  unexplained class is not a proposal.**

---

## The order, if David takes any of it

1. **Proposal 1**, with the cap, with its after-measurement pre-specified, and with `PromptCut`
   watched. It is the only one the evidence points at.
2. **Proposal 3's query** — has F649's trigger fired since? Free, and it closes an unscored repair.
3. **Hold 2 and 4** until 1 has an after-measurement. 🚨 Shipping them together makes the result
   unreadable, which is the mistake the seq-8319 pivot cost two sessions to undo.
