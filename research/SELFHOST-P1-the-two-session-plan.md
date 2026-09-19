# SELF-HOST P1 — the two-session plan, and the one arm that does not fit in it

**Status: a plan, not a result. Written 2026-09-18 against the live log
(`abcc-1ae35b6091a63e2c/log.sqlite`, 108 attempts) and `D:\dev\abcc` at `71f6aa8`, both read
rather than remembered. The headline is that every milestone is built — `land` and `review` both
shipped — and the distance to daily driving is two numbers: `change_landed` is **0** and
`review_recorded` is **0**, so W13's ladder has never had a single row. The second headline is
arithmetic David should see before he spends a session on it: the discriminating arm, designed as
the memory specifies it, needs ~100 attempts for 0.79 power and cannot exceed ~0.55 at any n
against its frozen reference. It does not fit beside daily driving, and this file costs it rather
than assuming it.** Candidate findings **F771–F772**; next free number is **F771**.

---

## 1. What was measured today, before any plan was written

Nothing here is inherited. Each row is a query against the live log, run 2026-09-18.

| question | answer | how |
|---|---|---|
| attempts ever | **108** — 5 `success`, 79 `uncertain`, 19 `refused` | `attempt.outcome` |
| last 30 endings | `budget_exhausted` **14** · `truncated_at_cap` **6** · `said_nothing` **4** | ditto |
| changes landed | **0** | `change_landed` absent from the log's 22 kinds |
| review minutes | **0** | `review_recorded` absent from the same 22 |
| prompt at phase end | 9.8k–**37.9k** against a **40,960** window | `model_call_ended.usage` |
| attempt wall clock | p50 **4.3 min**, p90 **7.1 min** (n = 107 under 1 h) | event span per attempt |
| GPU | **empty** | `lms ps` |

🚨 **80% of the last thirty endings are budget or output *shape*, not work quality.** That is the
whole distance to daily driving, and it is one class rather than four.

---

## 2. ⚠ SUPERSEDED BY SELFHOST-P2 — the chain below is wrong, and Block A is what found it

🚨 **Read `SELFHOST-P2-the-rounds-went-on-reading.md` instead of this section.** Block A ran on
2026-09-18 and refuted its central claim: **tool refusals cost 8.8% of the rounds in a
`budget_exhausted` attempt** (F773), median 2 of 30, so the *refusal → round → budget* chain below
is real and is not the mechanism. What spends the budget is **reading** — 50.5% of the Change
phase's tool calls, and **65% of the readable reads are re-reads** (F774). The window binds **9 of
36** rather than none or all (F775). ✅ F771 and F776 settled the two instrument questions.
**The section is kept as written because Block C's proposals were argued from it, and a plan whose
wrong turn is deleted teaches nobody which turn it was.**

## 2. The diagnosis the numbers already support, and the one they do not

**94% of `budget_exhausted` attempts reached at least one `apply_patch` call** — 34 of 36. So they
are not thrashing without editing: they get to the edit and then run out. And the round loop is
`for round in 0..self.limits.rounds` (`turn.rs:487`), one model call per round, **so a refused tool
call costs a full round of the 24.** The chain is therefore readable end to end:

> the model writes a patch → `apply_patch` refuses it → a round is gone → 24 rounds run out →
> `Uncertain { BudgetExhausted }` → the gate has nothing to measure → nothing lands.

**What `apply_patch` actually does, by day, read from `unmeasured` rather than `output`:**

| day | applied | refused | no result recorded |
|---|---|---|---|
| 08-29 → 09-12 | **0** | 147 | 86 |
| 09-13 | 1 | 0 | 0 |
| **09-14** (the newest flight) | **8** | **16** | 0 |

🚨 **F771 (candidate) — the success path wrote no result text until 09-13, so `applied` is 0 for
every earlier day and the 86 "no result" rows are almost certainly successes.** Any `apply_patch`
rate computed across that date from this field is an instrument artifact rather than a change in
the tool. ⚠ **Almost certainly is not measured** — §3's A1 settles it by reading the code at that
commit, and until it does, **no apply_patch rate spanning 09-13 may be quoted**, including the
`31 ok / 35 refused of 66` this project's memory currently carries.

**What refuses, over the 163 refusals whose detail the log kept:** **42** tool-call markup in the
diff argument (F637's class, F641's server-side fold), **~56** *hunk does not match*, **12** a
malformed diff, **~10** *claims line N and finds another*. ▶ The first is a serving-layer defect;
the rest are the model mis-citing a tree it read in 18-line slices.

⚠ **And one detector has never fired.** `Event::PromptCut` — F748's, the one that exists because
*the server cut the prompt and nothing could say so* — is **not among the log's 22 kinds**. Either
no attempt has crossed the server's cut, or the detector does not catch it. **Nobody knows which**,
and A3 below is that question rather than a fix for it.

---

## 3. SESSION 1 — why attempts do not finish

**Shape: three desk blocks that need no GPU, and one GPU block that needs a decision first.** Desk
work is always available; the GPU is the scarce half, so the desk blocks are sized to run while a
flight is in the air if one is.

### ✅ Block A — DONE 2026-09-18, and it changed the diagnosis (see SELFHOST-P2, F771–F776)

All four items are closed: **A1** settled the apply_patch instrument (36.9% pre / 36.0% post — the
instrument changed, the tool did not), **A2** killed the refusal chain at 8.8% of rounds, **A3**
split the window question three-to-one, and **A4** bounded `promptcuts.py --check` at
`AS_OF = 11726`. ▶ **Block C's proposal list is rewritten at SELFHOST-P2 §7.** The original block
is kept below as written.

### ▶ Block A — the instruments, before any conclusion rests on them (desk, ~90 min)

* **A1 — settle F771.** Read `apply_patch`'s result path at the 09-13 commit and prove whether the
  86 no-result rows are successes. One finding either way; it decides whether this project's
  standing apply_patch number survives. 🚨 **This runs first**, because §2's whole table depends on
  it and a rate quoted across a schema change is the class of error this corpus keeps finding.
* **A2 — round accounting.** For every attempt: how many of its 24 rounds ended in a *refused* tool
  call. That single number says whether the binding constraint is the budget or the model, and it
  is the evidence every proposal in Block C is argued from. **Pre-specify the cut** — all attempts,
  not a chosen cohort — before looking at it.
* **A3 — window accounting.** Does `prompt_tokens` ever exceed the load's window? Did `PromptCut`
  have anything to fire on? Answers whether LM Studio's `truncateMiddle` is in this story at all,
  which three sessions have assumed and none has measured on this log.
* **A4 — the owed bound.** `promptcuts.py --check` gets `AS_OF` the way `toolreach.py:47,:130`
  already has it. 🚨 **`PUBLISHED` is not moved to 123/90/109** — F764 repairs by adding.

### ▶ Block B — the discriminating arm, costed honestly (GPU, and David's call first)

**The design the memory specifies** — build `941add1` + `7fe980f` with the **OLD** `diagnostics`
summary, fly the anchored prompt, and ask whether checker use returns to the pre-pivot rate — was
costed today by simulation against the fixed post-pivot reference (**1 of 24**):

| n, new arm only | power at α = .05 |
|---|---|
| 20 | 0.36 |
| 40 | 0.53 |
| 60 | **0.53** |

| balanced, both arms fresh | attempts | power | GPU hours at p50–p90 |
|---|---|---|---|
| 20 / arm | 40 | 0.32 | 2.9–4.8 |
| 40 / arm | 80 | 0.68 | 5.7–9.5 |
| **50 / arm** | **100** | **0.79** | **7.2–11.9** |

🚨🚨 **F772 (candidate) — against a reference frozen at 1/24, power saturates near 0.55, and n
cannot buy what the reference's precision does not have.** The affordable version of this arm is
not underpowered by a little: it is **structurally incapable** of clearing 0.05 more than half the
time even if the effect is exactly as large as the pre/post split suggests. ▶ This is the same
overestimate that made A4 project p ≈ 0.03 and deliver 0.091 — stated in advance this time.

✅ **DAVID RULED 2026-09-18: option 2.** The deterministic discriminator is what runs, followed by
a small pre-registered descriptive arm. 🚨 **The word is *descriptive*** — n = 10/arm cannot clear
0.05 and is not asked to, so no p-value from that arm may be published as a result. **Do not
re-argue the design**; what reopens it is the same thing that reopens the slot count, which is a
subject cheap enough to repeat, and this one is not.

**So Block B opens with a decision, not a build.** Three designs, David picks one:

1. **As specified, balanced, n = 50/arm.** 100 attempts, **7.2–11.9 GPU hours**. It is both
   sessions. Daily driving does not happen in this plan if this is chosen, and that is a trade
   rather than a risk.
2. **▶ Recommended — a deterministic discriminator, pre-registered.** The two commits differ in
   *what the model is shown*; build both binaries and capture the exact bytes each puts in the
   transcript for one fixed tree. **~30 min, no GPU, and the answer is certain.** It answers *what
   differs* rather than *which caused the behaviour* — a smaller question, answered, in place of a
   larger one this box cannot afford. Then fly a **small pre-registered descriptive arm**
   (n = 10/arm, ~1.5–2.5 h), reported as descriptive and never as significant.
3. **Defer the arm.** Both sessions go to daily driving. `4687405` and `941add1` stay confounded,
   which is exactly where P12 left them, and nothing regresses.

🚨 **Whichever is chosen:** the discriminator, the n and the stopping rule are written to the
ledger **before the first attempt**; the build happens **before** anything flies, because it edits
`D:\dev\abcc` and `git add -A` over the live root is what a checkpoint stages; and the tree is
restored afterwards. ⚠ **A desk edit during a flight changes the subject.**

### ▶ Block C — the proposal pack (desk, ~45 min, ends the session)

David ruled *measure and propose, you rule*, so this block **proposes and ships nothing**. Each
candidate arrives with its evidence, its cost, and what it would move:

* **The round budget (24).** A2 says how many rounds went to refusals. If the answer is *most*,
  the honest fix is not more rounds — it is fewer refusals.
* **`apply_patch`'s markup fold** (42 of 163 refusals). A serving-layer defect with a known shape;
  the question is whether the tool layer should strip what the server folds in, and that changes
  what the model is allowed to send.
* **A context guard ahead of the server's own.** Only if A3 says the window is actually in play.
* **The 16,384 completion cap**, against `truncated_at_cap` at 24 of 108.

🚨 **Nothing in Block C is applied in session 1.** Each one moves a measured number, and every rate
on this project's log would then straddle the change.

---

## 4. SESSION 2 — the first landing, which has never happened

### ▶ D1 — David rules; the ruled changes ship (~1 h)

Tests, `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, one commit per change, and
**the commit message names which measurement it moves**, so the straddle is readable later.

### ▶ D2/D3 — the re-measure, pre-registered (GPU, ~2 h)

**The n and the ending distribution to beat are written down first.** The bar is the honest one:
`budget_exhausted` 14 of 30 and `truncated_at_cap` 6 of 30 are what the change has to move, and a
small arm that moves neither is a result. ⚠ **Seeded** (`223ae3a`), and the word is *attributable*,
never *reproducible*.

### ▶ D4 — **the act the whole ladder is defined in, performed once** (~1 h)

One real task on `D:\dev\abcc`, run to `Headline::Green`, then:

1. **David reads the diff.** Not the agent — `land.rs`'s own header says the fleet must never call
   it, and OQ-W13-4 (*does the agent get commit rights, ever?*) is open.
2. **`abcc land <task>`** → the first `change_landed` row this project has ever written.
3. **`abcc review <change> <minutes>`**, typed by David with his own minutes → the first
   `review_recorded` row, and **W13's ladder has a baseline for the first time.**

🚨 **An agent may never type either verb.** `by` defaults to `operator()`, so an agent running
`review` fabricates the exact measurement SELF-HOST is judged on. What an agent can do is make it
cheap: hand David the sha, the diff, and an honest estimate of what reading it costs.

### ▶ D5 — repeat until the ladder has a shape (GPU, ~2 h)

Two or three more, so the baseline is a small population rather than one point. **M1 is *the
human's only act is merge*** — reached the moment D4 completes. **M2 and M3 are counted, not
built**, and this is where the counting starts.

### ▶ D6 — the board, the runbook, the memory (~45 min)

**Seven tasks sit `awaiting_orders`** (`11312`, `11726`–`11731`) and they are research arms, not
work. Each needs `accept` / `reject` / `abort` — David's words, from the board — or a daily driver
opens on a screen of other people's leftovers. Then the runbook: load, check, task, run, board,
land, review, in the order a person types them.

---

## 5. What this plan will not deliver, said now rather than at the end

* ⏸ **Unattended running.** F592's hang detector is one third built; the hung tool child and the
  gate's cold build still have no detector. Daily driving here means **David is at the keyboard**.
* ⏸ **The three parked decisions** — restate F765, whether a pooled seeded/unseeded rate may be
  published at all, and the arm's design — are David's, and are put to him rather than taken.
* ⏸ **Any repository but this one.** Every rate this project owns was measured on one Rust
  workspace, and the toolchain table has a Python row nothing has ever driven.
* 🚨 **`abcc review` is never typed by an agent**, and no green attempt is landed by one.
