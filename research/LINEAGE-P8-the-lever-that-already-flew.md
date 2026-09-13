# LINEAGE P8 — the lever that had already been pulled, and the denominator that flattered it

Session 9, 2026-09-13. `abcc` at `6e1cbaa`, `abcc-research` at `67fa204`, both trees clean.
Findings **F736–F746**. ▶ The queue's first open item was *a second arm for the `summary` lever*,
budgeted as a GPU session. **It did not need one: the arm had already flown, twice, and nobody had
counted it.** The counting cost nothing and the answer is not the one the queue expected.

🚨 **And the first number the count produced was wrong in the flattering direction** — by a factor
of a hundred — which is the finding worth keeping.

---

## 1. F736 — the `summary` lever's second arm flew two sessions ago and was never read

F697 left this open: `diagnostics` was called **0 times in 7 attempts** on the arm flown just after
F673 rewrote its `summary`, against **5 calls in 20 attempts** on the eleven-arm baseline, and *one
arm of five cannot tell whether the new sentence moved anything.* The queue has carried *a second
arm* ever since, priced in GPU hours.

▶ **The board already holds three more groups flown on that same summary.** Arms 17–21
(`t8729`–`t8733`, the F701/F700 LINEAGE arms), arms 22–26 (`t9694`–`t9698`, F700 repaired), and the
three later rows (`t10959` smoke, `t11312` the F715 read-back, `t11392` last session's probe). Every
one of them ran with F673's sentence in force, because it shipped at `4687405` and has not been
touched since.

The whole post-change window, folded out of the log for the first time:

| group | tasks | attempts | tool calls | exec-tier | `diagnostics` |
|---|---|---|---|---|---|
| arms 12–16 — the F673 arm | 5 | 7 | 212 | 30 | **0** |
| arms 17–21 — F701/F700 | 5 | 9 | 177 | 28 | **0** |
| arms 22–26 — F700 repaired | 5 | 9 | 240 | 40 | **0** |
| smoke · seed read-back · probe | 3 | 4 | 98 | 13 | **0** |
| **total after F673** | **18** | **29** | **727** | **111** | **0** |
| **total before F673** | **51** | **68** | **1,463** | **229** | **13** |

⚠ **The four groups are not four replicates of one condition.** Arms 17–26 carried their own prompt
changes — that is what they were flown for — so they vary the brief while holding the summary fixed.
For *does the model reach for this tool* that is a wider sample, not a cleaner one, and it is stated
that way rather than as an arm.

---

## 2. 🚨 F737 — the denominator that overstates the result by a hundredfold

The obvious reading is the call-level one, and it is the wrong one:

| unit | before | after | p |
|---|---|---|---|
| **tool calls** | 13 of 1,463 (0.89%) | 0 of 727 | **0.0015** — binomial |
| **attempts** | 6 of 68 (8.8%) | 0 of 29 | **0.174** — Fisher, 2-sided |

🚨 **A hundredfold apart, and the small one is the lie.** `diagnostics` does not arrive as
independent draws: the six attempts that ever reached for it called it **1, 2, 2, 2, 3, 3** times.
An attempt decides *once* whether this tool is worth reaching for and then uses it two or three
times in a row. So 727 calls are not 727 opportunities — they are **29** opportunities, and treating
them as 727 is counting the same decision over and over and calling the repeats evidence.

▶ **THE DENOMINATOR MUST BE THE UNIT OF DECISION, NOT THE UNIT OF RECORD.** The log records calls
because calls are what happen; the model chooses per attempt. Whenever those differ, the record's
unit is the larger one and therefore the flattering one.

⚠ **So the honest verdict is that the lever is *unmoved*, not that it is *disproved*.** `p = 0.174`
is not a result. What is established is narrower and still worth having: **the new sentence did not
produce a single reach in 29 attempts**, where the old one produced six in 68 — and if the sentence
had worked loudly, 29 attempts would have been enough to see it.

This is F731's lesson in a second costume. There, a test's floor came from the number under test;
here, a rate's denominator comes from the instrument rather than from the thing being measured.
Both give a clean, plausible, confident number, and both are arithmetic about themselves.

---

## 3. F738 — the confound that would have made the zero meaningless, checked and dead

**A tool that is never offered is called zero times, and it looks identical on the log to a tool
that is offered and refused.** `diagnostics` is `Reach::SpawnsChild`, so
`ToolSpec::required_tier` puts it at `Tier::Exec` alongside `bash`, `run_tests` and `git`, and
`Policy::admitted` filters *by tier*, not by name — the four are offered or withheld as one set.

▶ So the check is whether any exec-tier tool was called after the change. **111 were**: `bash` 108,
`run_tests` 3, `git` 0. And it holds inside each group separately — 30, 28, 40, 13 — so no single
window carries it.

| tool | before | after | tier |
|---|---|---|---|
| `read_file` | 800 | 432 | read |
| `bash` | 200 | **108** | **exec** |
| `apply_patch` | 160 | 74 | write |
| `search` | 137 | 86 | read |
| `list_files` | 115 | 17 | read |
| `write_file` | 22 | 7 | write |
| `run_tests` | 13 | **3** | **exec** |
| **`diagnostics`** | **13** | **0** | **exec** |
| `git` | 3 | 0 | **exec** |

🚨 **`diagnostics` was on the menu every one of those 29 times and was not chosen once.** The zero
is a choice. ▶ And the shape of the table is the older finding restated: **`bash` is the instrument
this model reaches for** (F697), and the summary sentence was never competing with silence — it was
competing with an arbitrary shell that can run the same commands and much else besides.

---

## 4. 🚨 F739 — the query that returned all zeros, and read like an answer

The first census returned one row per task with `tools = 0` for every task and a first-attempt date
of **1970-01-01**. Against 2,190 recorded tool calls that is visibly broken. It is worth writing
down because the *shape* of the mistake is the reusable part, and a slightly luckier version of it
would have been quoted.

Two causes, both of them a column that exists and is empty rather than a column that is missing:

1. **`event.task` is NULL on all 2,190 `tool_call_started` rows.** Tool events carry `attempt` and
   nothing else; the task is reachable only through `attempt.task`. A join on `event.task` is
   therefore well-formed, runs without error, and matches nothing.
2. **`attempt.started` is a `seq`, not a timestamp.** The values are `8`, `107`, `162` — event
   sequence numbers. Read as Unix milliseconds they render as the epoch, which is exactly what a
   date column looks like when it was never populated.

▶ **F734 said *key a log query on `kind`, never on the body*. This is its other half: key it on the
column the event actually carries.** The schema comment says the discriminant is in a column *"so
the common filters are index scans rather than JSON extraction"* — `task` and `attempt` are there
for the same reason, and neither is on every row.

⚠ The tell was a control that cost nothing: **a total that must be non-zero.** 2,190 tool calls are
known to exist, so any per-task fold that sums to zero is wrong before its content is read at all.
That check is cheaper than the query it validates.

---

## 5. F740 — row 8's missing leg is mostly built, and its own write-up says otherwise

POSTURE-P1 records ADR-0014 §5's `--offline` as *"the leg that would close row 8, and it is not
built."* Read against the code, the **mechanism** is built and shipped:

* `abcc run` and `abcc fleet` both accept **`--ceiling <tier>`** (`cli.rs:235`), which caps every
  head in the slot.
* `Posting` takes `Tier::narrower` of the role's own ceiling and the slot's (`head.rs:291`), so a
  slot ceiling cannot be widened by a role.
* `Policy::admitted` is the single list that is both advertised to the model and enforced against
  it, so **`--ceiling write` already denies the entire exec class today.**

▶ So what is actually missing from row 8 is not the denial. It is **the name** (nothing in the CLI
says *offline*, and an operator who wants egress closed has to know that `write` is the word for
it), **the binding** (nothing makes it automatic for unattended roles, which is what ADR-0014 §4
asks for), and **the record** (no event says a run was flown with the class denied, so the log
cannot answer *was this one closed?* after the fact).

⚠ And the correction cuts the other way too: **`ProviderClass::leaves_the_machine` should not
acquire a caller from this work.** It is a predicate about where the *model* runs; egress from a
tool child is a different question with a different mechanism, and POSTURE-P1 is right that reading
one as the other is an error. The queue item's *"or an explanation of why it has none"* is the half
that applies.

---

## 6. F741 — what closing the lever would cost, computed rather than guessed

Holding the before-arm at 6 of 68 and assuming every further attempt also reaches zero:

| attempts after the change | Fisher p |
|---|---|
| 29 — **where it stands today** | 0.174 |
| 35 | 0.093 |
| 40 | 0.083 |
| 45 | 0.079 |
| **48** | **0.041** — crosses |
| 60 | 0.029 |
| 80 | 0.008 |

▶ **19 more attempts at zero**, and only if they *are* zero. ⚠ A single reach anywhere in those 19
pushes the requirement well past 48, because the comparison is against a baseline of 8.8% and one
success at n≈48 is close to the baseline rate itself. This is a real GPU cost on a question whose
answer is already *no visible movement*, and it is David's to spend or decline — recorded here so
the decision is priced rather than open-ended.

---

## 7. F742 — the sortie: 24 rounds in Localize, no artifact, and structural refused this time

Row 8's naming half was put up as `t11590` — *add `--offline` beside `--ceiling`, capping the slot
at `Tier::Write`*. `a11598` ended **`Uncertain { BudgetExhausted { 24 rounds } }`**: 24 turns, 28
tool calls, **0 denials**, 403,505 in / 4,495 out, 171,758 ms. `change` never ran — *Localize
produced no artifact* — and the tree was untouched.

🎉 **The structural rung refused it**, `exit 1`, *"the attempt changed no file the repository
tracks"*. ▶ **That is the exact complement of F735 and worth putting beside it.** Last session an
attempt wrote 106 lines that were all test and no feature and **structural passed it**. This session
an attempt wrote nothing and **structural caught it**. So the rung's reach is now bracketed from
both sides by evidence: **it detects *changed nothing*; it cannot detect *changed the wrong
thing*.** F735's reading stands and is now bounded rather than open.

⚠ And the attempt is a 30th sample for §1: `read_file` 18, `search` 6, `list_files` 4, and
**`diagnostics` 0** — Recon is capped at `Tier::Read`, so this one could not have reached for it and
is excluded from F736's denominator rather than quietly added to it.

## 8. F743 — 47.2% of everything the attempt read, it had already read

The 18 `read_file` calls returned **369,451 bytes**, and **7 of them were byte-identical repeats of
a read the same attempt had already made — 174,221 bytes, 47.2% of the total.**

| file | reads | bytes returned |
|---|---|---|
| `crates/abcc/src/cli.rs` (652 lines) | **4×** | 112,444 |
| `crates/abcc-engine/src/tools.rs` (640 lines) | **3×** | 73,095 |
| `crates/abcc/src/run.rs` (512 lines) | **3×** | 61,737 |

This is only visible because F713 put the tool's own output on the log. Before that field existed
the log said *18 read_file calls* and nothing else, and this attempt would have read as thorough.

## 9. 🚨 F744 — THE SERVER IS SILENTLY TRUNCATING THE PROMPT, AND NOTHING ON THIS SIDE KNOWS

`turn.rs:11` states the design: the loop *"appends to a [`Body`] — the same body, growing"*. Every
path is `body.append`; nothing in the workspace shrinks it. **So the body abcc sends is monotone by
construction.** And `prompt_tokens` is the server's own measurement of exactly that object.

🚨 **It is not monotone.** Across `a11598`'s 24 calls it climbs to **36,737**, drops to **19,181**,
climbs, drops to **9,965**, and ends at **15,132** — while abcc's body has grown past **90,000
tokens**. ▶ **A non-monotone measurement of a monotone object means the object is being cut before
it is measured.** No byte estimate is needed for that step; it follows from the append-only proof
and the server's own number.

▶ **At the final call abcc was sending roughly 94,000 tokens of body and the model was shown
15,132 — about 16% of it.** The other 84% was discarded by the server in silence. Nothing is logged,
no event is emitted, no warning is printed, and `abcc replay` cannot say it happened.

🚨 **And it is not this attempt.** Over the whole archive:

| | |
|---|---|
| attempts with ≥ 2 model calls | **98** |
| attempts whose prompt shrank by > 1,000 tokens | **86 — 88%** |
| such drops in total | **117** |
| largest single drop | **38,006 tokens** (`a8007`: peak 40,087, last call 2,081) |

before F673: **57 of 68** · after F673: **29 of 30**. ▶ **This has been happening to nearly every
long attempt this project has ever flown**, and the context is `-c 40960`, which is the number the
drops sit against.

### F745 — the control that makes it a finding and not an accounting artifact

**There is an innocent explanation and it had to be killed first.** If this server reported only
*newly processed* tokens — cache misses, with the prefix cache doing the rest (W1/W2 measured it
saving 79.7% of TTFT) — then a falling `prompt_tokens` would mean a cache **hit** and nothing would
be wrong at all.

▶ **Ruled out by the ratio of reported tokens to the body abcc had actually sent:**

| call | 2 | 3 | 4 | 5 | 6 | 7 | **8** | 13 | 24 |
|---|---|---|---|---|---|---|---|---|---|
| reported ÷ body | 2.27 | 2.22 | 1.24 | 1.13 | 1.11 | **1.10** | **0.37** | **0.17** | **0.16** |

**Calls 4–7 converge on ~1.10 and hold there** — the server is reporting the *whole* prompt, the
residual being JSON scaffolding and the head prefix that the byte estimate does not count. Cache-miss
accounting cannot produce four stable consecutive readings at ~1.1 and then collapse to 0.37 in one
step. ⚠ The early ratios (2.27, 2.22) are high because the head prefix dominates a small body; they
are the estimate warming up, not evidence either way.

### F746 — what it costs, and which earlier numbers it touches

1. 🚨 **The round budget is not what binds a long attempt — the window is.** `a11598` and F735's
   `a11400` both ended `BudgetExhausted { 24 rounds }`, and **that name attributes the ending to the
   wrong resource.** An attempt that re-reads because its evidence was discarded spends rounds
   re-acquiring what it already had; raising the round budget would buy more re-reads.
2. 🚨 **F743 is a symptom of F744, not a separate defect.** The model is not being wasteful. It
   re-read `cli.rs` a fourth time because the first three reads were no longer in what it was shown,
   and **nothing in the loop can tell it that.**
3. ⚠ **F717's estimate was taken from prompt-token deltas** and therefore from a quantity that is
   truncated 88% of the time. ▶ **F720's byte-based measurement is the one that survives**, which
   is the reason F720 was run on a second instrument at all. *Roughly quadruples* still stands;
   the **method** behind it now matters more than it did.
4. ⏸ **Not diagnosed here:** whether this is llama.cpp's context shift, an LM Studio policy, or a
   server setting this project can turn off — and what it discards. That is the next probe, and it
   is cheap. **What is measured is that it happens, how often, and how much.**

---

## 10. What is owed next

1. ▶ **The `summary` lever is answered as far as counting can answer it** (F736/F737), and F741
   prices the rest. Queue item 3's first entry is closed.
2. ⏸ **Row 8** — F740 narrows it from *build the leg* to *name it, bind it, record it*. The sortie
   on the naming half produced no artifact (§7), for a reason that is now measured (F744), so the
   feature itself is still owed.
3. 🚨 **F744 is the largest thing found this session and it is entirely undiagnosed.** One cheap
   probe — does this server shift context, and can it be told not to — decides whether every long
   attempt this project flies is working from a truncated view on purpose or by accident.
4. ⏸ **The 96 voice lines**, still unblocked and still untouched.
5. 🚨 **`review_recorded` is still 0**, and there are now **seven** unreviewed merges. The packet is
   built and waiting at `scratch/review-packet-session9.md` — **546 source lines touched, of which
   140 are feature and 30 are in-module test**, every one reproduced comment-stripped. David asked
   for it this session and will type `abcc review` himself.
6. ⏸ **Four decisions still parked**: F721, F723, F727, F733.
