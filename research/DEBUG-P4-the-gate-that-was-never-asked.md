# DEBUG P4 — the trigger that never fired, and the gate that was never asked

**Status: the F649 arm has now been flown four times and has never once fired, so DEBUG-P3 §8's
stated stopping condition is met and the trigger's width is David's decision on the argument rather
than on data. But the three new sorties bought something much larger than the answer they were flown
for. `a5738` is the closest this project has ever come to landing a change — structural, acceptance
(**544 run, 544 passed, 0 failed**) and veto all green, refused only by clippy — and the reason five
other near-complete trees are not on that list is not that they were bad. It is that `abcc-drive`
asks the gate ONLY when the model declares itself done. Six of ten attempts changed the tree; the
gate was asked about one. I rebuilt the other five out-of-tree and measured what it would have
said.** Findings **F654–F661**; next free number is **F662**. Flown 2026-09-07 against
`D:\dev\abcc` at `e5625a8`, model `qwen3.6-35b-a3b-mtp@iq3_s` at `-c 40960 --parallel 1`,
`abcc check` reporting *matched exactly* before every sortie. **Nothing was changed between runs,
and this session committed nothing to `abcc`.**

▶ Follow-on to `DEBUG-P3-the-other-door.md` §8, which is a recipe and was run as written: the prompt
was **read back from `abcc replay t4886`** rather than retyped, and asserted byte-identical at 329
characters before each of the three new tasks was flown.

**The session's shape: the arm answered *no* a fourth time, and while it was answering, the subject
quietly went from *cannot produce a diff* to *produces a correct one that nobody looks at*.**

---

## 1. What was flown

Three new sorties — `t5430`, `t5683`, `t5871`, arms 3, 4 and 5. With `t4886` (arm 1, on the
**pre-F649** binary) and `t5221` (arm 2, DEBUG-P3's own flight) that is five points on one subject
with one prompt, four of them carrying the F649 message.

| | | |
|---|---|---|
| subject | `abcc --version`, 329 chars, `t4886`'s prompt read back verbatim | |
| assertion | `prompt("t4886") == prompt("tNEW")` before every flight | passed 3 of 3 |
| binary | `e5625a8`, unchanged across arms 2–5 | |
| model | `qwen3.6-35b-a3b-mtp@iq3_s`, `-c 40960`, `--parallel 1` | confirmed exactly, 3 of 3 |
| shape | `abcc fleet`, one slot at exec, 2 attempts per task | as arms 1 and 2 |
| cost | ~8 minutes each; ~25 minutes of GPU for the three | |

The reader is DEBUG-P3's `research/tools/sortieread.py`, plus three new instruments kept beside it.
`armrow.py` classifies every `apply_patch` refusal as **MARKUP** (F637's sentence, the server's
fold) or **NoMatch** (F638's, a real diff that missed) and counts back-to-back pairs; `armtable.py`
does that across all five arms at once; `gatetable.py` joins each attempt's opening and closing
checkpoint to `git diff --shortstat` and to whether any `rung_recorded` row exists. All three read
the log **read-only**. ⚠ `armrow.py` was validated by reproducing DEBUG-P3's published `t5221` row —
1 markup of 2, trigger never fired — before it was pointed at anything new.

---

## 2. The trigger: 0 of 4, and it is now a decision rather than a measurement

F649 offers `write_file` **conditional on a second consecutive markup refusal** — *if the next
`apply_patch` is refused this way too*. Across ten attempts and 27 `apply_patch` calls:

| arm | attempt | `apply_patch` calls in order | ending |
|---|---|---|---|
| 1 (pre-F649) | `a4893` | `mk mk` | BudgetExhausted 24 |
| 1 (pre-F649) | `a5077` | `mk mk mk` | BudgetExhausted 24 |
| 2 | `a5228` | — | TruncatedAtCap 16384 |
| 2 | `a5300` | `mk nm` | SaidNothing (Builders) |
| 3 | `a5437` | `mk` | BudgetExhausted 24 |
| 3 | `a5606` | — | TruncatedAtCap 16384 |
| 4 | `a5690` | — | SaidNothing (Recon) |
| 4 | `a5738` | `mk nm OK OK OK OK` | **Refused by standard** |
| 5 | `a5878` | `nm OK OK OK OK OK OK` | BudgetExhausted 24 |
| 5 | `a6049` | `nm nm nm nm OK OK` | BudgetExhausted 24 |

**Two markup refusals back to back have happened three times in this subject's history, and all
three were in arm 1 — on the binary that did not carry the offer.** On the four flights that do
carry it, it has happened **zero times**, and `write_file` has been called **zero times in ten
attempts**.

That is DEBUG-P3 §8's stopping condition, reached as written: *if the trigger fires in none of them,
that is itself the answer — the condition is too narrow, and the choice between two refusals of any
kind and unconditional has to be made on the argument rather than on data.* ⚠ It should be made
**once, by David, and then flown** — not iterated on quietly between sorties.

🚨 **The argument has moved since DEBUG-P3 wrote it, and it now points away from widening.** F650
worried that a wider trigger might throw away good work, on the strength of one nearly-correct diff.
Arms 4 and 5 turn that worry into a measurement: **12 of 27 `apply_patch` calls now succeed**, and
`a5878` landed six in a row after its first one missed. A *two refusals of any kind* rule would have
fired inside `a6049` — which then landed two patches — and an unconditional one would have fired in
`a5878` before any of its six.

---

## 3. The fold is not a rate, and this is the third time that has had to be said

F651 cautioned that F648's *5 of 5* was a property of one run rather than of the subject. Five arms
on a byte-identical prompt, same model, same settings:

| arm | markup refusals / `apply_patch` calls | succeeded |
|---|---|---|
| 1 (pre-F649) | **5 of 5 — 100%** | 0 |
| 2 | 1 of 2 — 50% | 0 |
| 3 | 1 of 1 — 100% | 0 |
| 4 | 1 of 6 — 17% | 4 |
| 5 | **0 of 13 — 0%** | 8 |

On the F649 binary the fold is **3 of 22 (14%)** against arm 1's 5 of 5, and **12 of 22 calls
succeed** — the first successful `apply_patch` calls this subject has ever recorded.

🚨 **This is not evidence that F649 fixed the fold and must not be written up as though it were.**
F649 changed a refusal string; F641 established that the fold happens in the **server's** tool-call
parser, which never reads that string. What the five arms establish is the negative: **the fold's
rate is not a property of the subject, the model or the settings, because all three were held
byte-identical while it moved from 100% to 0%.** The whole-log 77% remains the only rate with a
population behind it, and it is now visibly an average over something bursty.

⚠ The denominator moves opposite to the rate — 5 calls in arm 1, 13 in arm 5 — which is what you
would expect if a folded turn tends to end an attempt's patching rather than merely cost it a round.
`a5437` is that in its clearest form: one fold, and the model never touched `apply_patch` again in
24 rounds, spending the rest on eleven `bash` calls.

---

## 4. Arm 4 cleared E0004 — the error this subject is named after

`t4735`, the wiretap run, is where the name came from: `a4742` added `CliError::Version` to `cli.rs`
and `main.rs`, never touched the exhaustive match in `tests/cli.rs`, and the acceptance rung came
back `failed_before_running` with `error[E0004]: non-exhaustive patterns: Err(CliError::Version) not
covered`. **`a5738` is the first attempt in this log to clear it**, and it cleared it by doing the
one thing `a4742` missed.

| | `a4742` (wiretap, `t4735`) | `a5738` (arm 4, today) |
|---|---|---|
| structural | exit 0 — 2 files: `cli.rs`, `main.rs` | exit 0 — 3 files, **+ `tests/cli.rs`** |
| acceptance | **`failed_before_running`** — E0004 | **exit 0 — 544 run, 544 passed, 0 failed** |
| veto | exit 1 — the tree does not build | exit 0 — nothing vetoed |
| standard | never reached | exit 101 — `cargo clippy --all-targets -- -D warnings` |
| judge | ran | ran, 2 findings, and it decided nothing |

The gate has been reached on `abcc --version` **twice in the project's entire history** — `a4742`
and `a5738` — out of nine gated attempts in a 6,200-event log.

The two lints are one line each: `write!(out, "{}\n", …)` wants `writeln!`, and the new
`Err(CliError::Version) => String::new()` duplicates the body of the arm above it. 🚨 **The second
lint is caused by the fix for E0004.** Clearing a non-exhaustive match by adding a separate arm
beside one with an identical body is exactly what `clippy::match_same_arms` refuses. **E0004 was
traded for a lint about how E0004 was fixed** — which is the sort of thing only a ladder that runs
every rung can show you, and eight of these ten attempts never got one.

---

## 5. 🚨🚨 The gate is asked only when the model declares itself done

`crates/abcc-drive/src/lib.rs:487`:

```rust
let mut gate = match (kept.as_ref(), last) {
    (Some(closing), PhaseEnded::Answered { .. }) => Some(self.gate(attempt, &opened, closing)?),
    // An attempt that ended in an absence has nothing to measure, and an
    // attempt the operator stopped is not ours to judge.
    _ => None,
};
```

`PhaseEnded::Answered` means *the model stopped talking of its own accord*. An attempt that runs out
of rounds, or is cut at the 16,384-token cap, ends `Stopped` and gets `None` — **whatever is in the
tree**. The console then prints `gate not asked — the attempt produced no artifact`.

That sentence is false five times in this session, and `gatetable.py` measures it:

| arm | attempt | tree change at the closing checkpoint | gate | ending |
|---|---|---|---|---|
| 1* | `a4893` | 1 file, +3 | — | BudgetExhausted |
| 1* | `a5077` | 2 files, +6 | — | BudgetExhausted |
| 2 | `a5228` | (no change) | — | TruncatedAtCap |
| 2 | `a5300` | (no change) | — | SaidNothing |
| 3 | `a5437` | 2 files, +7 | — | BudgetExhausted |
| 3 | `a5606` | (no change) | — | TruncatedAtCap |
| 4 | `a5690` | (no change) | — | SaidNothing |
| 4 | `a5738` | 3 files, +11 | **ASKED** | Refused by standard |
| 5 | `a5878` | **4 files, +13 −1** | — | BudgetExhausted |
| 5 | `a6049` | 3 files, +12 | — | BudgetExhausted |

**Six attempts changed the tree. The gate was asked about one.**

🚨 The rung that would have separated all of them is the **free** one. `Rung::Structural` is *did the
attempt change anything the repository tracks*; it is the diff between two snapshots `abcc` has
**already taken**; `rung.rs` puts it first on `Rung::LADDER`, costs it at **0.024 s**, and records
*0 false positives on 609 correct trees*. It never ran on any of the five.

⚠ **The comment is the bug.** *An attempt that ended in an absence has nothing to measure* conflates
two different absences: **the model said nothing** — `a5228`, `a5300`, `a5690`, where the table
agrees and there genuinely is nothing — and **the model was still working when the budget ran out**
— `a4893`, `a5077`, `a5437`, `a5878`, `a6049`, where there is a changed tree and no measurement.
ADR-0009's own rule is that *a rung that could not run does not disappear*; here four rungs do not
merely fail to run, they are never asked, and the operator is told an artifact does not exist while
it sits in the checkpoint.

⚠ **This is the mechanism under F653, not a contradiction of it.** DEBUG-P3 already recorded that
arm 1's trees changed and that neither was finished work. What it could not say is *why nobody
learned that from `abcc`* — F653 had to be established by reading checkpoints by hand, exactly as
§6 below does, because the ladder built to answer it was never asked.

---

## 6. What the gate would have said — all six trees, measured

Every changed tree was checked out into a worktree outside the repo and put through the two rungs
that matter, byte-for-byte the commands `abcc-gate` runs: `cargo test --workspace` for acceptance
and `cargo clippy --all-targets -- -D warnings` for standard.

| arm | attempt | acceptance | standard | verdict the gate would have given |
|---|---|---|---|---|
| 1* | `a4893` | 101 — `expected ',', found '")}"'` | — | Red at **acceptance** |
| 1* | `a5077` | 101 — **E0004** | `match_same_arms` | Red at **acceptance** |
| 3 | `a5437` | 101 — **E0004** | `match_same_arms` | Red at **acceptance** |
| 4 | `a5738` | **0 — 544 passed** | `write_with_newline` + `match_same_arms` | Red at **standard** ✅ *abcc measured this one* |
| 5 | `a5878` | **0 — 544 passed** | `match_same_arms` (`lib.rs:89`) | Red at **standard** |
| 5 | `a6049` | 101 — `missing #[error("...")] display attribute` | same | Red at **acceptance** |

🚨 **`a5878` is `a5738`'s equal and it was thrown away.** Same 544 tests passing, same veto-clean
tree, one clippy lint instead of two — and because it ended on the round budget rather than on the
model's own full stop, `abcc` filed it as *produced no artifact*. It is, on the evidence, the single
best change this project has ever produced, and nothing in the system knows that.

⚠ **The cross-check matters more than the result.** Running clippy on `a5738` independently
reproduces `abcc`'s standard rung error-for-error — `write_with_newline` then `match_same_arms` —
so the ladder is honest about what it measures. The problem is only ever *what it is asked about*.

🚨 **Every tree that compiles is refused by `clippy::match_same_arms`, and the task is why.** A
`--version` that behaves like `--help` means an arm whose body is identical to `Help`'s — in
`exit_code()`, in `tests/cli.rs`, or both. Four of four compiling trees tripped it; **no attempt in
five arms has ever cleared the standard rung.** The task is landable — merge the patterns rather
than add arms — but the obvious implementation is refused by the repository's own declared standard,
and the fold this session was flown to study never had anything to do with it.

---

## 7. The retry starts from zero, and it is measurably expensive

Every retry opens at a checkpoint byte-identical to the **fresh** attempt's opening snapshot, not to
its closing one — verified on arms 2, 3 and 5, where `git diff` between them is empty. So `a5878`
produced a four-file implementation that passes 544 tests, ended on the round budget, and `a6049`
then began by reading `cli.rs` from scratch, re-derived a worse version of the same change, and
ended on the round budget too. Arm 5 spent **61 model calls, 1,336,659 input tokens and 9 m 45 s**
to produce two independent unmeasured copies of one change, the second worse than the first.

---

## 8. Findings

**F654** — 🚨 **The F649 trigger has been flown four times and has never fired.** Two markup refusals
back to back occurred three times in this subject's history and all three were in arm 1, before the
offer existed; across arms 2–5 it happened zero times and `write_file` was called zero times in ten
attempts. DEBUG-P3 §8's stopping condition is met: **the trigger's width is now a decision on the
argument, and it is David's.** ⚠ The argument has moved — see F656 — and it now points away from
widening rather than toward it.

**F655** — 🚨🚨 **`abcc` asks the gate only when the model declares itself done, so five changed trees
were discarded unmeasured.** `abcc-drive/src/lib.rs:487` matches `(Some(closing),
PhaseEnded::Answered)`; every other ending yields `None`, and the console prints *the attempt
produced no artifact*. **Six of ten attempts changed the tree; the gate was asked about one.** The
rung that would have caught the rest is `Rung::Structural` — free, **0.024 s**, first on the ladder,
*0 false positives on 609 correct trees*. ⚠ The code comment conflates *the model said nothing*
(three attempts, correct) with *the model was still working when the budget ran out* (five attempts,
wrong).

**F656** — 🚨 **`a5878` passes 544 of 544 tests and was filed as producing no artifact.** Rebuilt
out-of-tree, it is `a5738`'s equal on acceptance and veto and **better on standard** — one
`match_same_arms` against `a5738`'s two lints — and the only difference between the two is that
`a5738`'s model stopped talking and `a5878`'s ran out of rounds. ⚠ Independently running clippy on
`a5738` reproduces `abcc`'s standard rung error-for-error, so the ladder is honest; only its
*trigger* is wrong.

**F657** — 🚨 **The fold's rate moved from 100% to 0% with prompt, model, settings and binary held
identical: 5/5, 1/2, 1/1, 1/6, 0/13 across five arms.** On the F649 binary it is 3 of 22 (14%) and
**12 of 22 `apply_patch` calls succeed** — the first successes this subject has recorded. ⚠ **Do not
attribute this to F649**, which changed a refusal string the server's parser never reads (F641).
What is established is the negative: the rate is not a property of the subject. This is the third
time (F648, F651, now) a fold rate has failed to reproduce; it should stop being quoted per-run.

**F658** — 🚨 **Every tree that compiles is refused by `clippy::match_same_arms`, and the task's
shape is why.** A `--version` that behaves like `--help` adds an arm whose body matches `Help`'s, in
`exit_code()` or `tests/cli.rs` or both; four of four compiling trees tripped it and **no attempt in
five arms has ever cleared the standard rung.** ⚠ The blocker on this subject is the repository's
own declared standard, not the fold this session was flown to study. The task is landable by merging
patterns rather than adding arms.

**F659** — **A retry does not inherit the previous attempt's tree.** Verified on arms 2, 3 and 5:
the retry's opening checkpoint is byte-identical to the fresh attempt's opening checkpoint. Arm 5
spent 61 model calls and 1,336,659 input tokens on two independent unmeasured copies of one change.
⚠ Combined with F655 this is the real cost shape — the work is done, discarded unmeasured, then done
again from scratch, and the second copy was the worse of the two.

**F660** — **`write_file` was called zero times in ten attempts and 27 `apply_patch` calls.** The
fallback the model actually reaches for is `bash` (20 calls in arm 1, 9 in arm 2, 11 in arm 3) or
simply more `apply_patch` (arms 4 and 5). F653's observation holds at n=10. ⚠ Not evidence against
the offer, which was never triggered — but the offer has now never been read in the situation it was
written for, in any run, ever.

**F661** — ⚠ **`NoMatch` is now the dominant refusal and its shape is a near-miss that repeats.**
Seven `NoMatch` against three markup on the F649 binary. `a6049` was refused four times running — on
`cli.rs`, then `main.rs` twice, then `lib.rs` — each reported as *6 of 7 context lines match* or
*5 of 6*. The model has read the file and still emits one context line that does not match. This is
the failure F638's sentence exists for, it is where the rounds now go, and it is a different problem
from the fold.

---

## 9. What this leaves

▶ **One decision, and it is David's**, exactly as DEBUG-P3 §8 framed it: F649's trigger fires on a
second *markup* refusal, which has not occurred in four flights. The options are *two refusals of
any kind*, *unconditional*, or *leave it*. ⚠ F657 and F654 argue for **leave it**: `apply_patch` now
works more than half the time on this subject, and both wider rules would have fired inside attempts
that went on to land patches.

▶ **F655 is the one worth fixing, and it is not a prompt.** Asking the gate on a `Stopped` ending
whose closing tree differs from its opening one costs 0.024 s for the structural rung and converts
five discarded attempts in this session alone into five measured ones — one of which is
`a5878`. It is a change to one `match` in `abcc-drive`, it wants tests, and it wants an arm of its
own with the same discipline F649 got. ⚠ **It also opens a design question that is not mechanical**:
a gate-green tree the model never declared finished is not obviously `Accomplished`, and ADR-0009's
*only a measurement says Accomplished* does not settle who is allowed to stop. That part is David's
too, and it should be settled before the code changes rather than discovered after.

▶ **The subject is landable and nobody has landed it.** Five tasks are now in `AwaitingOrders` and
this session accepted and rejected none of them: `t4886`, `t5221`, `t5430`, `t5683`, `t5871`.
`a5738` is two one-line lints from Green; `a5878` is one.

⚠ **Do not raise `rounds`.** It was the binding stop in five of ten attempts here, and in every one
of those five the tree already held a change — two of them passing every test in the workspace. The
constraint is not that the model needs more rounds. It is that nothing looks at what it produced in
the rounds it had.
