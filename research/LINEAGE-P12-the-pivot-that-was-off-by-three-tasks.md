# LINEAGE P12 — the pivot that was off by three tasks

Session 14, 2026-09-15. `abcc` `71f6aa8`, unchanged and clean; `abcc-research` `8b47290` → this
commit. Findings **F767–F770**. ▶ P11 closed with one item at the front of the queue and it was not
a sortie: *something at seq 8319 took checker use from 12-in-49 to twenty consecutive zeros on a
fixed subject, and it is NOT the `diagnostics` rewrite — fold the COMMITS in that window.* This is
that fold.

🚨 **The window turned out to be the wrong question, because the boundary was in the wrong place.**
`toolreach.py` splits at seq 8319 and states its reason in a comment: *"`t8319` at seq 8319 is the
first task created after it."* **It is not.** `4687405` landed 15:26:19; `t8319` was created at
16:13:02; three tasks were created in between. The pivot names a task 28 minutes and four attempts
late, and one of the four attempts it misfiles **called a checker**.

⚠ **This is a correction to an instrument, not a drift in it.** `toolreach.py --check` is green —
all seven published numbers reproduce, before this session and after it. The arithmetic was right.
What was wrong is what the boundary *meant*, and no control that checks numbers against themselves
can see that.

▶ **What survives:** F765's class result, weaker — any checker **24.4% → 4.2%, p = 0.0457**.
▶ **What dies:** *twenty consecutive zeros*, and with it the premise that sent P11 looking for a
commit other than `4687405`.

---

## 1. 🚨 F767 — the pivot is off by three tasks and four attempts, and the log says so in one query

`toolreach.py:31-36`, the comment that defines the constant:

```
# `4687405` shipped F673's fix; `t8319` at seq 8319 is the first task created
# after it. Attempts at or above this seq saw the tool that measures the
# standard; attempts below it saw `cargo check` and the old summary.
F673_PIVOT = 8319
```

The first sentence is true. The second is false, and it is the one the cohort split rests on:

| | when | |
|---|---|---|
| `4687405` | **2026-09-11 15:26:19** | `feat(engine): F673 — diagnostics runs the standard` |
| `t7655` created | 15:45:14 | *"E0004 arm 12, F673"* — **the first task created after the fix** |
| `t7999` created | 15:55:49 | *"E0004 arm 13, F673"* |
| `t8149` created | 16:05:09 | *"E0004 arm 14, F673"* |
| `t8319` created | **16:13:02** | *"E0004 arm 15, F673"* — what the constant names |

Each of those four is its own `run_started` with its own pid — 14652, 14932, 14788, 7676 — so they
are four separate `abcc run` launches, every one of them after the commit. There is no moment in
this sequence at which 8319 is distinguished. **By the rule the comment states, the pivot should be
7655.**

**The second reading agrees, and it does not go through a clock at all.** Every attempt takes a
`checkpoint_taken`, and `Repo::checkpoint` (`abcc-vcs/src/lib.rs:241-265`) does `read-tree HEAD`
then `git add -A` over the live repo root — so the checkpoint sha *is* the source state that attempt
was handed, uncommitted work included. 214 of them are still on the repo under
`refs/abcc/checkpoints/m1/`, every one a readable commit. Ask each one whether it carries the fix:

```
  a7484  09-08 00:17  PRE   run_tests    OLD diagnostics
  a7663  09-11 15:45  PRE   -            NEW diagnostics   <- the boundary
  a7830  09-11 15:49  PRE   -            NEW diagnostics
  a8007  09-11 15:55  PRE   run_tests    NEW diagnostics
  a8157  09-11 16:05  PRE   -            NEW diagnostics
  a8327  09-11 16:13  POST  -            NEW diagnostics   <- where the pivot is
```

**PRE-pivot: NEW 4 / OLD 45. POST-pivot: NEW 28 / OLD 0.** The four attempts on the wrong side of
the line are exactly the four the task-creation times predict, derived a different way.

⚠ **The detector is controlled before it is used.** `tools.rs` contains the word `standard` zero
times at `4687405^` and three times at `4687405`; `subjectfold.py` classifies those two trees first
and refuses if they do not separate. An instrument that cannot tell apart the two commits it was
built from is not an instrument — F740's rule, one level over.

⚠ **What this reading cannot see.** The summary the model *reads* is compiled into the **binary**;
the checkpoint records the **source**. They are inferred to agree because a run is launched from a
build, and the log carries only `version: "0.1.0"` — there is no build identity on it. **The
correction does not rest on that inference**, because the pivot already fails its own stated rule on
task-creation time alone. But any claim about what a *specific* attempt was shown does, and should
be written that way.

## 2. 🚨 F768 — corrected, F765's class result survives and weakens, and the twenty zeros are an artifact

The same events, the same fold, the same Fisher, only the boundary moving. Bounded below
`AS_OF = 11726`, as F765 was:

| | as published, split at seq 8319 | corrected, split by the tree |
|---|---|---|
| **any checker** | 12/49 24.5% → 0/20 **0.0%**, p = **0.0139** | 11/45 24.4% → 1/24 **4.2%**, p = **0.0457** |
| `diagnostics` | 6/49 12.2% → 0/20 0.0%, p = 0.171 | 6/45 13.3% → 0/24 0.0%, p = 0.085 |
| `run_tests` | 8/49 16.3% → 0/20 0.0%, p = 0.094 | 7/45 15.6% → 1/24 4.2%, p = 0.246 |

**The class result holds.** Checker use on a subject held exactly fixed still falls, and it is still
under 0.05. It is no longer comfortable there: **p = 0.0139 → 0.0457**, a result that would not
survive any correction for the six cells in the table above, let alone the twelve this fold
computed.

🚨 **`a8007` is the whole difference and it is worth naming.** One attempt, 09-11 15:55, called
`run_tests` on a tree that carried the fix. The seq pivot holds it in the *before* numerator; the
subject boundary moves it to *after*. It is the single worst direction a misfiling can take — it
inflates the before-rate and empties the after-rate at once — and it is why the corrected p is 3.3×
the published one.

▶ **Retire the phrase "twenty consecutive zeros."** The corrected after-cohort is twenty-four
attempts with one checker call in it. The zero was a property of where the line was drawn.

## 3. 🚨🚨 F769 — the premise that sent P11 hunting for another commit was itself the artifact

P11 set `4687405` aside for a stated reason, and the reason is in its own words:

> something at **seq 8319** took checker use from 12-in-49 to twenty consecutive zeros on a fixed
> subject, and it is **NOT** the `diagnostics` summary rewrite — **`run_tests` fell with it and
> `4687405` never touched `run_tests`.**

The argument is sound and the fact it rests on does not survive the boundary correction. `run_tests`
falls with `diagnostics` **only at the seq pivot**:

| `run_tests` | before | after | p |
|---|---|---|---|
| seq pivot, bounded | 8/49 16.3% | 0/20 **0.0%** | 0.094 |
| **subject, bounded** | 7/45 15.6% | 1/24 **4.2%** | **0.246** |
| **subject, unbounded (arm in)** | 7/45 15.6% | 3/32 **9.4%** | **0.509** |

**The mirror does not fall on the subject boundary.** p = 0.25 bounded, p = 0.51 with the arm in —
nowhere near a signal. The fall that made `4687405` look innocent was carried by `a8007`, the one
misfiled attempt that called it.

⚠ **This does not convict `4687405`, and the temptation to say it does should be named.** In the
same table, unbounded, `diagnostics` reads **6/45 13.3% → 0/32 0.0%, p = 0.0382** — the only cell in
this entire fold that clears 0.05 for `diagnostics` alone. **It is one cell of twelve, it was chosen
after seeing the numbers, and it must not be quoted as a result.** What is honest is narrower and
still useful:

▶ **The open question is not answered; its premise is withdrawn.** There is no longer a measured
reason to believe the fall reaches a tool `4687405` never touched, so there is no longer a reason to
go looking for a *different* commit to explain it. `4687405` is back in the frame — along with
whatever else shipped beside it.

## 4. ⚠ F770 — seven commits in the real window, three the model can see, one killed by measurement

The window is no longer 16:05→16:13. It runs from the last OLD tree, `a7484` on **09-08 00:17**, to
the first NEW tree, `a7663` on **09-11 15:45** — three days, and `git diff` across the two
checkpoints is **42 files, 3,021 insertions**. Seven commits landed:

| commit | what it touches | model-visible? |
|---|---|---|
| `941add1` | redaction at `TurnLoop::tool_round` | 🚨 **yes** — a tool's output reaches the model through that seam |
| `126f03b` | CI, `deny.toml` | no |
| `eca9c39` | `abcc/src/weights.rs`, the weights digest | no |
| `a91dd3b`, `a6bb2ad` | `SECURITY.md` | no |
| `7fe980f` | `ending` lands Accomplished on a green ladder | 🚨 **yes** — it decides when an attempt stops |
| `4687405` | the `diagnostics` summary | 🚨 **yes** — it is what the model reads about the tool |

**`7fe980f` is the one that could have killed the result, so it was measured first.** If a green
ladder now stops attempts early, a checker that goes unreached was never declined — the attempt
ended before the question came up, and *the zero is a choice* is false. It did not happen:

| Change phase | OLD tree (45 attempts) | NEW tree (32 attempts) |
|---|---|---|
| turns | median **18.5**, mean 15.0 | median **19.0**, mean 16.2 |
| tool calls | median **19.0**, mean 17.1 | median **20.0**, mean 18.5 |
| ended `success` on a green ladder | — | **1** |

**The phase got slightly longer, not shorter, and the new ending fired exactly once in 32 attempts**
— on `t8319` itself, which is why that task is the only `accomplished` one in its range. The model
had at least as many turns and at least as many calls in which to reach for a checker, and reached
less. ▶ `7fe980f` is controlled out.

🚨 **`941add1` is not, and the log cannot separate it from `4687405`.** It applies the scrub at one
seam and names the model's own context as one of the three sinks that read from it, so it changes
what comes back from every tool call in the window. Both commits are model-visible, both landed
inside the same boundary, and every attempt after it has both. **Only an experiment separates them:**
a tree carrying `941add1` and `7fe980f` with the OLD `diagnostics` summary, flown on the anchored
prompt. That is a sortie, it needs a power calculation the last one did not get, and it is not an
agent's to launch.

## 5. What is owed next

* ▶ **F765's published figures need restating** — `research/LINEAGE-P11-the-confound-that-was-asserted.md:122`
  and the memory block both carry `24.5% → 0%, p = 0.0139`. The corrected pair is
  **24.4% → 4.2%, p = 0.0457**. 🚨 `F673_PIVOT` was **left at 8319 on purpose**: `PUBLISHED` was
  measured with it and `--check` reproduces all seven, so the numbers are correctly *computed*.
  F764's rule holds unchanged — repair by adding what is missing, never by moving a published number
  under a reader who will quote it. **Restating is David's call, not a `sed`.**
* ▶ **The discriminating arm**, if David wants it: `4687405` vs `941add1`, held apart by build.
  Pre-specify the discriminator and the n *before* flying, and note that the last arm's power was
  overestimated by 3×.
* ⏸ **Still David's, unchanged:** whether a pooled seeded/unseeded rate may be published at all; no
  green attempt may be landed; an agent may never type `abcc review`.

▶ **Instrument:** `research/tools/subjectfold.py` — `--stats` prints both boundaries over the same
events, and refuses to run if its detector cannot separate `4687405^` from `4687405`.
