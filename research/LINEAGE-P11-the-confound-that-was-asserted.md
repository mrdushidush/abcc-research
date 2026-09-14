# LINEAGE P11 — the confound that was asserted, and the control that ate itself

Session 13, 2026-09-14. `abcc` `71f6aa8`, unchanged and clean; `abcc-research` `3fbfb29` → this
commit. Findings **F763–F766**. ▶ The queue's first item was *fly the A4 arm*, and David authorized
the GPU for it. **The arm flew and it answered the question it was given** — §5 — but the
sharper result came from folding what the archive already had.

🚨 **Three of these four findings are corrections to things this archive already believed**, and each
was believed because a sentence was read where a fold was available. The A4 brief carried an
explanation for the checker fall — *the task-size confound* — that had never been measured. It is
measurable: **the same 329-character prompt has 49 Change-phase attempts before the pivot and 20
after**, so task size can be held exactly fixed. Held fixed, the fall is still there, it is
**significant as a class**, and it takes down a tool `4687405` never touched.

⚠ **None of this rescues the zero, and the arm did not either.** `diagnostics` alone is p = 0.171 on
the fixed-subject cohort (§3) and **p = 0.091** over the whole post-fix cohort once the arm had flown
(§5) — the plan projected ≈ 0.03, the attempts arrived and the p did not. **Do not quote the zero
against F673.** What falls is the *reason* the archive was giving for setting it aside.

---

## 1. 🚨 F763 — `Store::boot` repairs the **log** and leaves the **worktree** standing, and the retry it schedules lands on the byte-identical path

The first `abcc fleet` of the session booted, did the right thing, and died:

```
boot  12118 events replayed, 76 task(s)
      requeued t11728 — a slot-holding state with no worker behind it
abcc: git: `git worktree add --detach ...\worktrees\t11728-12040 b4f0ce9` failed with 128:
      fatal: '.../worktrees/t11728-12040' already exists
```

Exit code 1 — **the whole fleet, not just that task.** Every link read in the code:

1. `Store::boot`'s `BootAction::Requeue` (`abcc-store/src/lib.rs:505–527`) does exactly two things:
   tombstone the in-flight attempt (`AttemptEnded`/`HardFailure`, *"orphaned by restart"*) and
   `Command::Requeue { OrphanedByRestart }`. **It never touches the filesystem.**
2. The removal that *does* exist is `Driver::close_worktree` (`abcc-drive/src/lib.rs:970`) →
   `Worktree::close` (`abcc-vcs/src/lib.rs:572`, `worktree remove --force` **and** `prune`). It runs
   **in-process at the end of an attempt**, so a killed process skips it entirely.
3. The requeue dispatches as `Cause::Retry`, and `fork_point` maps `Retry` to
   `last_checkpoint(&history)` (`abcc-drive/src/lib.rs:458–459`) — **the same checkpoint the killed
   attempt opened on**, deliberately, so a retry continues the operator's tree.
4. The worktree path is `{task}-{checkpoint.id.born()}` (`abcc-drive/src/lib.rs:632–634`). Same
   checkpoint, same path, and git refuses.

🚨 **So boot's tombstone-and-requeue promises self-healing after a crash and cannot deliver it.** One
attempt killed mid-flight grounds the entire fleet until a person types `git worktree remove`, and
nothing in the product says so. The failure is not even attributed to the right place: the message
names git.

▶ **The log says it too, and nobody was reading it.** `worktree_opened` **104**, `worktree_closed`
**102**, with one worktree legitimately open at the time. The gap *is* the leak, and it is one line
of SQL.

✅ **The repair is safe by construction, and the repository already proves it.** `takeover.rs:355–360`
names the operator's tree `{task}-take-{seq}` *deliberately* so the namespaces cannot collide —
*"an attempt's tree is `{task}-{seq}` and this is `{task}-take-{seq}`, so the two cannot collide and
an operator can tell whose is whose."* ▶ **A directory at `{task}-{seq}` can only ever be an
attempt's tree, never a person's work**, so `open_workspace` may close a tree standing at the path it
is about to cut without risking the F701-class loss of throwing away someone's edits. The leaked tree
was clean at `b4f0ce9 abcc t11728 before 12039` — nothing to lose.

⏸ **Not repaired this session, and the reason is F763's companion fact.** `Repo::checkpoint`
(`abcc-vcs/src/lib.rs:241–265`) does `read-tree HEAD` then **`git add -A` over the live repo root**,
so a fresh attempt snapshots whatever uncommitted work is sitting in `D:\dev\abcc` into its own
worktree. `t11729`–`t11731` are fresh. ▶ **A desk edit during a flight is not neutral: it changes the
subject under the measurement.** The arm's whole premise is a byte-identical subject, so `abcc` was
left untouched and all of this session's work went into the research tree.

## 2. 🚨 F764 — one kept control is bounded, its sibling is not, and the unbounded one had been crying wolf since before this session booted

Two instruments were kept out of `scratch/` in the last two sessions for the same stated reason
(F758): a kept control makes drift visible *before* a new figure is quoted. Run this session:

```
promptcuts.py --check  →  3 FIGURE(S) DRIFTED
    attempt_keyed_falls  117 → 123    attempt_keyed_attempts  86 → 90
    boundary_falls       103 → 109
toolreach.py  --check  →  OK: all 7 published numbers reproduce.
```

▶ **The published numbers are correct and the instrument's arithmetic is correct.** Bounding the
same fold below the arm restores all nine exactly:

| fold | `attempt_keyed_falls` | attempts | `boundary_falls` |
|---|---|---|---|
| unbounded, the whole log | 117 → **123** | 86 → **90** | 103 → **109** |
| `seq < 12119` — this session excluded | 117 → **122** | 86 → **89** | 103 → **108** |
| `seq < 11726` — the whole SELFHOST arm excluded | **all nine reproduce** | ✓ | ✓ |

🚨 **So the drift was already on the log before this session started**; today contributed one attempt
and one fall of it. The memory's line *"`--check` reproduces all nine of P9's published numbers"* has
been stale since the arm first flew, and **nobody re-ran it** — a kept control is only a control on
the days somebody runs it.

**The cause is an asymmetry between two siblings 200 lines apart.** `toolreach.py:47` carries
`AS_OF = 11726` and folds `below=AS_OF` for `--check` (`:130`). `promptcuts.py` has no bound, no
`AS_OF`, no argparse at all. And `toolreach.py`'s own comment explains exactly why it needs one:

> *WITHOUT THIS THE CONTROL EATS ITSELF. The first run of `--check` was made while an arm was flying
> and it reported DRIFT on two numbers — correctly … A control that fails whenever anybody flies a
> sortie gets switched off within a week, and the drift it was built to catch goes with it.*

🚨 **The lesson was learned, written down, and never carried across to the file next to it.** That is
the finding: not that a bound was missing, but that the remedy was already in the repository, with
its own justification attached, and the sibling never got it.

🚨 **And the obvious repair is the wrong one.** Updating `PUBLISHED` to 123/90/109 would silently
re-publish figures contaminated by arm attempts LINEAGE-P9 never measured. The right repair is the
sibling's bound.

⚠ **"Only three drifted" understates the exposure.** All nine figures are unbounded. The other six
(`within_phase` 14/6, `cut_calls` 74, `cut_attempts` 12, `falls_any_size` 23, `deepest_cut` 27041)
are stable *because the arm happened not to produce those phenomena yet* — undisturbed, not
protected. The first prompt cut in any future arm moves `cut_calls`.

✅ **One thing that buys, free:** `cut_calls` 74 and `cut_attempts` 12 unchanged over the whole log,
and bare `abcc replay` printing no cut line, is the brief's own end-of-arm check answered early —
**zero new prompt cuts in the arm**, so none of it is a truncation artefact (F744).

## 3. 🚨🚨 F765 — the task-size confound was asserted, not measured; measured, it is eliminated, and the checker fall is significant **as a class**

The A4 brief carried this, from session 11, as the reason not to read anything into the zero:

> *In the cohort so far **both checkers fell** — `run_tests` 17.5 → 7.4%, `diagnostics` 9.5 → 0% —
> while **both manipulation tools held**. That is the **task-size confound**, not a failed summary
> rewrite.*

▶ **It was never necessary to reason about task size, because the log can hold it fixed.** The
anchored subject `6917f0ccaf0f83c3` — the identical 329-character prompt the whole arm is built on —
has **49 Change-phase attempts before `4687405` and 20 after** (and 9 in the arm). The comparison can
be made on one subject.

**Three variables held constant across the comparison**, each checked rather than assumed:

* **subject** — identical 329-char prompt, `sha256[:16] = 6917f0ccaf0f83c3`.
* **head** — `builders` for all 74 anchor Change attempts. The head *does* vary elsewhere on this log
  (`commandos` appears on no-tools ceiling calls), so this was worth checking: **zero attempts use
  more than one head inside Change**, so it is exact and not modal.
* **sampler** — **both cohorts are entirely unseeded.** Only the arm's attempts are seeded.

### On that fixed subject

| tool | before `4687405` | after | Fisher p |
|---|---|---|---|
| `diagnostics` | 6/49 **12.2%** | 0/20 **0.0%** | 0.171 |
| `run_tests` | 8/49 **16.3%** | 0/20 **0.0%** | 0.094 |
| `apply_patch` | 37/49 75.5% | 15/20 75.0% | 1.000 |
| `bash` | 27/49 55.1% | 14/20 70.0% | 0.291 |
| **any checker** (`diagnostics` ∨ `run_tests`) | 12/49 **24.5%** | 0/20 **0.0%** | **0.0139** |
| **any manipulation tool** — the mirror | 37/49 75.5% | 16/20 80.0% | 0.764 |

🚨 **Verification behaviour collapsed as a class, on a fixed subject, while manipulation behaviour was
unchanged.** And it **cannot be attributed to F673's summary rewrite**: `run_tests` was never touched
by `4687405` and fell at least as hard as the tool that was.

### What this licenses, and what it does not

✅ **The brief's warning stands.** `diagnostics` alone is p = 0.171. **Do not quote the zero against
F673.** Nothing here makes that zero significant.

🚨 **What falls is the brief's named cause.** *Task-size confound* was an explanation offered in place
of a fold. The fold exists, it is four lines, and it eliminates task size, the head and the sampler
together.

⚠ **The `∨` test was chosen after seeing both checkers move. It is post-hoc**, and must be quoted as
a hypothesis with its p beside it, never as a pre-registered result.

⚠ **No ledger edge is owed for this, and that is deliberate.** The corrected sentence is **editorial prose** — `LINEAGE-P10:203` and the gitignored run report — and was never a numbered finding. `findings-authored.tsv` records finding-to-finding corrections, and inventing a `dst` so this one had somewhere to point would be exactly the fabricated fact its own header warns against. ▶ Stored here instead, so the next heuristic does not go looking.

⚠ **`seq 8319` is a time boundary as well as a code boundary.** Everything else that shipped around
then — F649's refusal wording, F700/F701's repairs, engine changes — is confounded with `4687405`.
▶ The honest statement is **the fall is real and unexplained**, which is neither *"`4687405` caused
it"* nor *"it is an artefact"*.

### 🚨 And a problem with the arm's own design, found by the same fold

The arm's attempts are **seeded**; both historical cohorts are **entirely unseeded**. The plan —
*"~7 more Change-phase attempts take the cumulative post-fix to 0 of ~34 against 9.5%, p ≈ 0.03"* —
pools seeded with unseeded across the exact variable F715/F716 measured as influential. **And the
already-published figures do it too:** the brief's "after" cohort of 27 is the 24 unseeded
post-pivot attempts *plus* the arm's seeded ones, which is why `run_tests` reads 7.4% there (2 of 27)
and 0.0% on the unseeded anchor cohort. ▶ **A pooled rate over this boundary is David's call**, and
the unseeded before/after above is the comparison that needs no ruling.

### ▶ Where the silence starts, which is the shape a cause has to fit

The anchor subject's Change attempts in seq order, `C` = reached a checker:

```
BEFORE  n=49  ....CC........C...CC...C.........C....CC.C..C..C.    12 reaches, unseeded
AFTER   n=20  ....................                                 0 reaches, unseeded
ARM     n=9   .C......C                                            2 reaches, SEEDED
```

**The last reach before the pivot is `a8007`, with exactly one no-checker attempt between it and
`4687405`.** Checker use was ongoing right up to the boundary and then stopped dead for **twenty
consecutive attempts** — a run that a 12-in-49 rate produces about 0.4% of the time, which is the
same story the Fisher p = 0.0139 tells and not an independent one.

🚨 **The twelve reaches are spread across the whole before-cohort** — `a479` to `a8007`, seven of them
`run_tests`, three `diagnostics`, two both. This is not a rate that was already decaying; it is a
behaviour that was present throughout and then absent.

⚠ **The arm's one reach is `a11909`** — `run_tests` — **and `a11909` is the attempt that got furthest**,
the sixth tree ever to reach the standard rung. One attempt is an anecdote and it is recorded as one:
it is consistent with *the attempts that verify are the ones that get somewhere*, and it is equally
consistent with chance. ▶ It is the recovery signal the brief asked for; §5 shows the arm
finished with **two** such reaches and the signal is still far too small to bank.

### 🚨 The control F765 most needed: was the tool even **offered**?

A zero is worthless if the tool stopped being on the menu, and this repository has a mechanism that
would do exactly that — `ac02ff5`, *a tool policy per slot: the ceiling is a Tier, and it narrows the
head*. `model_call_started` records the effective `ceiling`, so it can be checked rather than assumed:

| | before `4687405` | after | arm |
|---|---|---|---|
| Change-phase ceiling (anchor subject) | `exec` (492 calls) + `None` (217, the field predates `ac02ff5`) | **`exec`, 306 calls** | **`exec`, 94 calls** |

* `Tier` is ordered `NoTools < Read < Write < Exec` and **`Exec` is the top** (`tools.rs:52–62`).
* `diagnostics` is `Reach::SpawnsChild` (`tools.rs:273`) — **the same reach class as `bash` and
  `run_tests`**.
* And the after-cohort **actually called `bash` 84 times** in Change on the anchor subject, alongside
  `apply_patch` 46, `read_file` 199, `search` 12, `write_file` 7.

▶ **So a `SpawnsChild` tool at the `exec` ceiling was being called freely in the very cohort where
both checkers read zero.** The ceiling did not narrow, the tool did not leave the roster, and the
reach class was demonstrably live. **The zero is a choice, not an availability artefact.**

⚠ This is the control that could have killed F765 outright, and it is the one the *task-size*
explanation never had to survive — which is the point of the finding.

## 4. ⚠ F766 — *"the sixth tree ever to reach the standard rung"* is true under two restrictions, neither of them written down

`a11909` is recorded in the A4 brief as **the sixth tree ever** to reach the gate's standard rung.
Folded over the log:

| reading | where `a11909` lands |
|---|---|
| distinct attempts that reached the standard rung, **all subjects** | **14th** |
| distinct attempts, **anchor subject only** | **7th** |
| anchor subject, **and excluding the one attempt that passed** (`a8327`, `end=success`) | **6th** ✓ |

So the sentence is arithmetically correct and it needs **both** unstated filters to be: the subject
restriction, and the exclusion of the single attempt that got through. Seven of the fourteen
standard-rung attempts are on other subjects entirely, `a2137` through `a4374`.

▶ **Nothing was measured wrongly; a count was quoted without its denominator's shape.** It is the
same class as F485 — *the same ceiling reads as 88% or 44% depending on the denominator* — and the
repair is the archive's own rule: **say what the population is in the sentence that says the number.**
`a11909` is the **sixth anchor-subject tree to be refused at the standard rung**, which is both true
and self-describing.

## 5. ▶ The arm itself — it flew, and **the mirror recovered**

**Seven attempts flown this session**, `a12133` through `a12881`, plus `a12042` tombstoned at boot
(F763). The arm now stands at **10 attempts, 9 of them with a Change phase.** All six tasks are
`AwaitingOrders` and none was landed — that is David's.

| attempt | task | Change calls | furthest rung | ending | checker |
|---|---|---|---|---|---|
| `a11739` | t11726 | 10 | veto | refused @veto | — |
| `a11909` | t11727 | 19 | **standard** | refused @standard | **`run_tests`** |
| `a12042` | t11728 | 6 | — | hard_failure/engine_error | — |
| `a12133` | t11728 | 2 | structural | uncertain/truncated_at_cap | — |
| `a12224` | t11729 | 24 | veto | uncertain/budget_exhausted | — |
| `a12423` | t11729 | 24 | structural | uncertain/budget_exhausted | — |
| `a12585` | t11730 | 9 | structural | uncertain/truncated_at_cap | — |
| `a12691` | t11730 | 24 | veto | uncertain/budget_exhausted | — |
| `a12845` | t11731 | 0 | structural | uncertain/said_nothing | — |
| `a12881` | t11731 | 24 | veto | uncertain/budget_exhausted | **`run_tests`** |

### 🚨 The pre-specified condition was met

The brief set the discriminator in advance: *"the story is only about `diagnostics` if `run_tests`
recovers in the same cohort."* Folded over the arm:

| cohort | `diagnostics` | `run_tests` — the mirror |
|---|---|---|
| before `4687405` | 6/63 = **9.5%** | 11/63 = **17.5%** |
| from `4687405` | 0/33 = **0.0%** | 3/33 = 9.1% |
| **the arm** | **0/9 = 0.0%** | **2/9 = 22.2%** |

▶ **`run_tests` came back to 22.2%, above its own pre-fix baseline, on the same nine attempts where
`diagnostics` stayed at zero.** The joint fall that carried the whole task-size story is gone: the
two checkers have separated, and §3 had already shown the story was not task size to begin with.

### ⚠ And the arm still did not reach significance — the plan's power was overestimated

🚨 **`diagnostics` is 0 of 33 post-fix against 6 of 63, Fisher p = 0.091.** The plan projected
*"0 of ~34 … p ≈ 0.03"*. The attempts arrived — 33 of the ~34 — and **the p did not**. ▶ **Do not
quote the zero against F673**; the brief's warning outlives the arm that was meant to settle it.

⚠ **The separation is not significant either.** Within the arm it is a *paired* comparison over the
same nine attempts: two discordant pairs, **McNemar exact two-sided p = 0.500**. ▶ So *the mirror
recovered* is a **descriptive** fact about rates, offered as the pre-specified condition being met,
and it is **not** a demonstration that `diagnostics` is being avoided.

### What else the arm shows

* **No third tree at the standard rung.** `a11909` remains the arm's only one; this session's seven
  reached veto three times and structural otherwise. **The find worth stopping for did not appear.**
* 🚨 **The dominant ending is `budget_exhausted` at the full 24 Change calls** — four of seven — with
  two `truncated_at_cap` and one `said_nothing`. Opportunity was not the limit (§3), and `a12881`
  used all 24 calls, reached `run_tests` *and* reached veto.
* ✅ **Zero `prompt_cut` events on the whole log**, so none of the arm is a truncation artefact
  (F744), and `toolreach.py --check` still reproduced all seven published numbers afterwards.

## 6. What is owed next

**David's calls, and only his:**

1. 🚨 **Whether a pooled seeded/unseeded rate may be published at all.** The arm's attempts are
   seeded and both historical cohorts are not. The A4 plan's *"0 of ~34 against 9.5%"* crosses that
   boundary, and so does the already-quoted *"0 of 27"*. ▶ The unseeded before/after comparison in §3
   needs no ruling and is the one to quote until this is settled.
2. ⏸ **A2 and B1** remain one command and one sentence, and remain his. 🚨 **An agent still may not
   type `abcc review`** — `by` defaults to `operator()`, and an agent running it fabricates the exact
   measurement Self-Host is judged on.
3. ⏸ **A5, A6, F721, F723, F727, F733** are parked. Launch is parked. The sprite corpus is deferred
   (F714). **None of the green attempts were landed** — that is still his call.

**Work that needs no ruling:**

4. ✅ **F763's repair**, deferred here only because the arm was flying and `Repo::checkpoint` stages
   the live tree. `open_workspace` should close a worktree standing at the path it is about to cut;
   `takeover.rs`'s naming rule already proves that path can only hold an attempt's tree. Until then
   **a killed attempt grounds the next fleet**, and the manual clear is `git worktree remove`.
5. ✅ **F764's bound** — give `promptcuts.py` the `AS_OF` its sibling already has. 🚨 **Do not**
   "repair" it by moving `PUBLISHED` to 123/90/109.
6. ▶ **The open question F765 leaves.** Something at `seq 8319` took checker use from 12-in-49 to
   twenty consecutive zeros on a fixed subject, and it is **not** the `diagnostics` summary rewrite,
   because `run_tests` fell with it. `4687405` is confounded with everything else that shipped
   around then. The next fold is the commits in that window, not more attempts.
7. ⚠ **Re-run both `--check`s before quoting anything.** That is the whole lesson of §2, and it cost
   nothing this session only because it was the first thing run.
