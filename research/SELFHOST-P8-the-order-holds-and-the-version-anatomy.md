# SELF-HOST P8 — the landing order is proven, and `--version` gets its autopsy

**Status: desk only. No GPU, no attempt flown, nothing landed — `land` and `review` are David's.**
🎉 **THE OPEN UNKNOWN IS CLOSED.** P7 could not say whether the second landing still applies once the
first one commits, because answering it needs commits and commits on `main` are `abcc land`. It is
answered now, in a detached worktree that `main` never saw: **all four apply CLEANLY, in order, with
a real commit between each — the `--3way` fallback was never reached — and the gate's own four
commands all exit 0 over the tree they make.** Instrument `research/tools/landsim.py`.
🚨🚨 **F793 — AND `--version` HAS AN ANATOMY, NOT A CURSE.** Adding a `CliError::Version` variant
forces **two** `clippy::match_same_arms` merges, not one: `tests/cli.rs:287` (which three attempts
found, the hard way) and `lib.rs:102` (**which none of five ever reached, because not one of them
opened `lib.rs`**). The second is the dangerous one: `exit_code` ends in `_ => 1`, so the variant
compiles, passes 679 tests and reports a **failing status for something `main` exits 0 on** — and
**no rung can see it.** The repaired change is **30 lines across 4 files**, desk-verified green on
all four gate commands, and `abcc --version` prints `abcc 0.1.0` and exits 0.
🚨🚨 **F794 — AND I ALMOST PUBLISHED A HEADLINE ITS OWN CONTROL REFUTES.** *One file lands, many
files do not* reads 33.3% against 2.3%, **p = 0.00068**, over 68 attempts. Stratify by subject and it
**dissolves in both strata** — p = 0.18 inside `--version`, **p = 1.00** outside it. The file count
was the subject wearing a costume. Findings **F793–F795**; next free is **F796**.

---

## 1. ✅ THE ORDER HOLDS — four landings, in sequence, with commits in between

P7 left this as `UNKNOWN` **and said why**: the order was tested by applying patches to the working
tree without committing, so git's `does not match index` was an artifact of the rig rather than a
verdict on `land`. The fix is not a cleverer test, it is a place where committing is free.

`research/tools/landsim.py` adds a **detached `git worktree` at HEAD**, which has the whole object
store and its own index, and performs the four applies for real. `main` is never touched; the
worktree is removed at the end.

It reproduces `land`'s mechanism rather than approximating it — the pair is the attempt's own
`checkpoint_taken` shas (`land.rs::landing`, newest green attempt first), the patch is
`Repo::patch_between`'s exact `git diff --no-ext-diff --no-color --find-renames --unified=3`, and the
apply is `Repo::apply`'s `git apply --index --3way`.

| # | task | attempt | change | files | applied |
|---|---|---|---|---|---|
| 1 | `t14016` | `a14025` | `Outcome::is_unmeasured` | `outcome.rs` +60 | **cleanly** |
| 2 | `t13604` | `a13805` | `Cause::name` | `attempt.rs` +27 | **cleanly** |
| 3 | `t13606` | `a13921` | `Seq::back` | `seq.rs` +46 | **cleanly** |
| 4 | `t8319` | `a8327` | `abcc --version` | `main.rs` +4 | **cleanly** — ⏸ **but ruled OUT of the sequence, §5(2)** |

🎉 **The `--3way` fallback was never needed** — the plain applier took all four. And over the tree
they make:

| the gate's own command | exit |
|---|---|
| `cargo check --all-targets` | **0** |
| `cargo test` | **0** |
| `cargo fmt --check -- --color=never` | **0** |
| `cargo clippy --all-targets -- -D warnings` | **0** |

⚠ **What this is not.** A pass here is not a promise that `abcc land` succeeds: `land` also rebuilds
the report and asks `Report::headline_at`, and refuses a dirty checkout. It is a proof about **the
one step a preceding landing can break**, which is the step nobody could test before.

✅ **And landing 1 cannot stale the rungs of 2, 3 and 4.** `land.rs::green` asks
`headline_at(&sha)` where `sha` is *the attempt's own* first measured rung — not `HEAD`. A landing
moves `HEAD` and leaves every other attempt's entitlement exactly where it was.

⚠ **`t13055` `Seq::forward` is still excluded and still for the reason P7 gave** — it and `t13606`
both open `@@ -43,6 @@` in `impl Seq` and both add a `#[cfg(test)] mod tests` to a `seq.rs` that has
none, so landing both is `E0428`, a compile error rather than a conflict. Land `t13606`, then re-run
`Seq::forward` against the landed tree.

---

## 2. 🚨🚨 F793 — `--version` forces TWO `match_same_arms` merges, and the gate can only see one

Five attempts have hit five walls. Put the walls beside each other and **three of the five are one
line of test code** — the `match` at `crates/abcc/tests/cli.rs:287` — hit from two directions, and
the other two failed on `thiserror`'s attribute and on the context window.

| task | attempt | rung | what refused, from the log | files it opened |
|---|---|---|---|---|
| `t11726` | `a11739` | **veto** | `E0004` non-exhaustive: `Err(CliError::Version(_))` not covered, **same `match`** | 2 |
| `t11727` | `a11909` | **standard** | `match_same_arms` at `cli.rs:287` **+** `uninlined-format-args` | 3 |
| `t13054` | `a13308` | **structural** | changed no file — `context_overflow`, window 40,960, prompt **40,828** | 0 |
| `t14017` | `a14162` | **veto** | `#[error(env!("CARGO_PKG_VERSION"))]` — `thiserror` needs a **literal** | 1 |
| `t14411` | `a14419` | **standard** | `match_same_arms` at `cli.rs:287` | 2 |
| `t8319` | `a8327` | — **green** — | 4 lines in `main.rs`; **never enters `cli::parse`** | 1 |

▶ **Why that one line is lethal.** It already merges two patterns into one body:

```rust
Ok(_) | Err(CliError::Help) => String::new(),
```

So a third variant with the same body has exactly one legal shape. **Not covering it is `E0004`**
(`t11726`). **Covering it in its own arm is `clippy::match_same_arms`**, which `-D warnings`
promotes from a pedantic warning to a refusal (`t11727`, `t14411`). The only way through is to merge
the *pattern*: `Ok(_) | Err(CliError::Help | CliError::Version(_)) => String::new(),`.

### 🚨🚨 And there is a second one, in a file no attempt ever opened

`crates/abcc/src/lib.rs:102`:

```rust
AppError::Cli(cli::CliError::Help) => 0,
AppError::Cli(cli::CliError::Usage(_)) => 2,
_ => 1,
```

**`CliError::Version` matches neither arm, so it falls to `_ => 1`.** The binary is still correct —
`main` intercepts `Version` before the generic `Err(e)` arm and returns `SUCCESS` — but the function
the project keeps *precisely so every caller spells the exit status the same way* now disagrees with
`main` about it. That is **F392's class exactly**: two functions answering one question is two
answers waiting to disagree, and `land.rs` cites F392 as the reason it re-asks `headline_at` instead
of counting rungs locally.

🚨 **No rung can see it.** The catch-all means it compiles; `tests/cli.rs:32` asserts the exit code
for `Help` and `:38` for `Usage` and `Refused`, and nothing asserts it for a variant that did not
exist. **679 tests pass over the defect.** This is the class the P7 rejected-table already named
about the broken intra-doc links: *the gate cannot check them, so a wrong answer goes green and the
cost lands on the operator's review minutes, which is the metric M1 is.*

🚨 **And fixing it correctly hits `match_same_arms` a second time** — measured, not predicted. Adding
`AppError::Cli(cli::CliError::Version(_)) => 0,` beside the `Help` arm was refused at
`lib.rs:102`, same lint, same `-D warnings` promotion. The merge is the fix:
`AppError::Cli(cli::CliError::Help | cli::CliError::Version(_)) => 0,`.

### ✅ The repaired change, verified at the desk

`research/patches/version-verified-green.patch` — **4 files, +30 / −2**, built on `t11727`'s own
diff so that what is verified is the design the engine produced, not one I invented:

| | |
|---|---|
| `cargo check --all-targets` · `cargo test` · `cargo fmt --check` · `cargo clippy -D warnings` | **all exit 0** |
| tests | **679 passed** |
| the new test | `the_version_flag_prints_and_exits_zero ... ok` |
| `abcc --version` | `abcc 0.1.0`, **exit 0** |
| `abcc board --version` | `abcc 0.1.0`, exit 0 — the house convention, same as `--repo` |

⚠ **Two of those 30 lines are mine, not the engine's, and they are the two that matter**: the
`exit_code` arm and the test that asserts it. `t11727` did not write them, and nothing in the gate
would have asked.

---

## 3. 🚨🚨 F794 — the "one file lands" headline is refuted by its own control

Over the 68 attempts that edited at least one file, the pooled table is as clean as this project
ever gets:

| files touched | success | other | green rate |
|---|---|---|---|
| **1 file** | 8 | 16 | **33.3%** |
| **2+ files** | 1 | 43 | **2.3%** |

**Fisher two-sided p = 0.00068.** It is the obvious operational lesson — *feed the engine one file* —
and it is wrong.

🚨 **`--version` is inherently multi-file and it is 50 of the 68 attempts.** So the control is
forced: hold the subject fixed and ask again.

| stratified by SUBJECT | 1 file | 2+ files | p |
|---|---|---|---|
| `--version` only | 1 / 9 — 11.1% | 0 / 41 — 0.0% | **0.18** |
| every other subject | 7 / 15 — 46.7% | 1 / 3 — 33.3% | **1.00** |

▶ **It dissolves in both strata.** 41 of the 44 multi-file attempts are one subject, and the file
count was carrying its name.

Run the mirror — hold the file count fixed and vary the subject — and the asymmetry identifies which
variable is doing the work:

| stratified by FILE COUNT | other subjects | `--version` | p |
|---|---|---|---|
| 1 file | 7 / 15 | 1 / 9 | 0.178 |
| 2+ files | 1 / 3 | 0 / 41 | 0.068 |
| **pooled** | **8 / 18 — 44.4%** | **1 / 50 — 2.0%** | **4.5e-05** |

**The subject survives in direction in both strata; the file count reverses in one and vanishes in
the other.** That is the signature of the subject being the real variable.

⚠⚠ **What may NOT be claimed, and it is most of it.** Neither stratum of the surviving variable
clears 0.05 on its own (0.178 and 0.068) — only the pooled table does, and the two variables are
**near-collinear on this log**, so it cannot fully separate them. The grouping is **post-hoc**: I
computed the file table first and went looking for the control afterwards. "Every other subject" is
**18 attempts over ten subjects**, nearly all one-method additions to `abcc-core`, so it is closer to
*one-method additions* than to *everything that is not `--version`*. And every cell is **unseeded**
(F715), which makes it a population and never a run.

✅ **What may be said.** **`--version` is 1 green in 50 edited attempts, and that one green bypasses
`cli::parse`. Every other subject the board has carried is 8 of 18.** Whatever the mechanism, the
board's own history says this subject does not yield.

---

## 4. ⚠ F795 — `--by` exists on one operator verb of three

`abcc review` takes `--by` (`cli.rs:370`) so a person can record who read the diff. `accept` and
`reject` take **only `--note`** (`cli.rs:421`), and both write `by: operator()` into the durable log
— `AbortReason::CompletedByOperator` and `AbortReason::Operator` (`ops.rs:450`).

`operator()` reads `ABCC_OPERATOR` (`lib.rs:59`, `:186`) and falls back to the literal `"operator"`.
So the only lever that makes `accept`/`reject` honest about who did it is **an environment
variable** — invisible in the command line, and therefore invisible in the shell history that is the
only other record of what a person typed.

▶ **Small, and David's.** Either give `accept` and `reject` the same `--by` that `review` has, or
decide that they are operator-only by construction and say so where the log is read.

---

## 5. ✅ THE RULINGS — ASKED, AND ANSWERED THE SAME DAY

### (1) The three landings — nothing is blocked but the keyboard

Verified in order, gate green over the tree they make. In David's own hand, one at a time:

```
.\target\release\abcc.exe land 14016     # then: review <sha> <minutes>
.\target\release\abcc.exe land 13604
.\target\release\abcc.exe land 13606
```

🚨 **`t8319` is NOT in this list** — ruling (2) retired it. The sequence above is
re-verified as a three-change run in its own right, not merely as a prefix of the four.

✅ **The binary is current.** `target/release/abcc.exe` on disk was built 2026-09-18 **22:52**,
seventeen minutes *before* `a0054e7` landed at 23:09 — a binary from the tree before the first
landing. **Rebuilt from `main` 2026-09-19 in 27 s** and re-checked against the log. P7's own
lesson was *check a binary's provenance before believing a verb is broken*.

### (2) `--version` — the ruling, not another attempt

✅🚨 **RULED BY DAVID, 2026-09-19: DOOR C. `--version` IS RETIRED AS A WORK TASK.**
`t8319` is **not** landed; the verified patch is applied by hand and takes **no ladder row**.

⚠⚠ **SEQUENCING, AND IT IS NOT OPTIONAL: the patch goes on AFTER the landings.**
`land` refuses a dirty checkout, so applying `--version` first would block every landing behind
it. Order: land the three → re-run `Seq::forward` → *then* `--version`.

▶ **The recipe, once the tree is clean again.** It is an ordinary commit — no green attempt
backs it, so `land` cannot take it and the ladder does not get a row:

```
git apply --index research/patches/version-verified-green.patch   # run from D:/dev/abcc
git commit -m "feat(abcc): --version, through cli::parse rather than around it"
```

⚠ **The patch lives in the *research* repo and applies to the *product* repo**, so the path above
is relative to wherever `abcc-research` is checked out. It was verified against `a0054e7`; after
three landings the tree has moved, and none of the three touches `cli.rs`, `lib.rs`, `main.rs` or
`tests/cli.rs`, so it should still apply — **should**, which `git apply --3way` will settle.

🚨 **The reasoning behind the ruling: do not land `t8319`, retire `--version` as a work
task.**

* `t8319` is green and applies cleanly, but it intercepts `--version` in `main` **before
  `cli::parse`**, so the flag is unknown to the parser, absent from `USAGE`, and absent from
  `exit_code`. It is the change a 120-second review should reject — and **merging a change you would
  reject makes M1's ladder measure the wrong thing**, because the metric is review minutes per
  *merged* change.
* `--version` has been this project's **experimental anchor** for 25+ arm runs. Its job was to be a
  fixed subject, not a feature. F794 says it is now the worst-yielding subject on the board.
* The feature itself is **30 verified lines** sitting in
  `research/patches/version-verified-green.patch`.

▶ **The three doors, priced:**

| | cost | what it buys | what it costs |
|---|---|---|---|
| **A. land `t8319`** | 0 | a ladder row today | a design David would reject, merged |
| **B. one more attempt, wave 4** | ~1 GPU hour | a ladder row for the *right* design | the prompt would have to **be** the patch — all four seams, both merges, both verbatim — so it measures transcription, not the work |
| **C. retire it; apply the verified patch by hand** | 0 | the feature, correct | **no ladder row** — a hand-applied change has no green attempt, so `land` cannot take it |

🚨 **B's honest label:** F792 shows the `diagnostics` lever works (5 of 6 when told), and the two
merges are now compile-tested, so wave 4 has the best odds any `--version` attempt has ever had. But
three attempts already ended `budget_exhausted` at **24 rounds** *after* being told to run
diagnostics, and `--rounds` is a flag on `abcc run` rather than a default — **so B should be flown
at a raised `--rounds`, which is testable without moving a default.** Nothing here moves one:
ruling (3) of 2026-09-18 is *measure and propose, David rules*.

### (3) The board — five tasks are safe to clear, and none of them is mine to clear

`reject` writes `by: operator()` (F795), so the same argument that keeps an agent off `review` keeps
it off `reject`. ✅ **RULED 2026-09-19: David clears them himself.** The five commands:

```
.\target\release\abcc.exe reject 13051 --note "superseded by t13606"
.\target\release\abcc.exe reject 13052 --note "superseded by t14016"
.\target\release\abcc.exe reject 13053 --note "superseded by t13604"
.\target\release\abcc.exe reject 13603 --note "superseded by t14016"
.\target\release\abcc.exe reject 13605 --note "junk probe, never a task"
```

✅ **The quotes are load-bearing, and the binary says so itself.** `take_flag` (`cli.rs:497`)
removes exactly **one** token after the flag and `one_positional` then wants exactly one argument
left — so an unquoted multi-word note is a refusal, not a note. Tested against a throwaway
`--home`: quoted it parses and gets as far as *there is no t13051 on this board*; unquoted it
answers **`reject takes a task and nothing else — quote it if it has spaces in it`**.

| task | why it can go |
|---|---|
| `t13051` `Seq::back` | superseded by `t13606`, green and landable |
| `t13052` `Outcome::is_unmeasured` | superseded by `t14016`, green and landable |
| `t13053` `Cause::name` | superseded by `t13604`, green and landable |
| `t13603` `Outcome::is_unmeasured` (wave 2) | superseded by `t14016` |
| `t13605` `probe` | **a junk task I created while diagnosing an argument failure** |

⏸ Seven more sit at `INTERVENTION REQUIRED` and are **research arms rather than work** — `t11312`
and `t11726`–`t11731`. ✅ **Three more are now closable too** — `t13054`, `t14017` and
`t14411` were all `--version`, which ruling (2) retired; they are listed separately only because
their work was real and their walls are what F793 is made of.

---

## 6. What this session did not do

* **Did not land, review, accept or reject anything.** `main` is at `a0054e7`, clean.
* **Did not touch the GPU.** `lms ps` reported no model loaded at the start and none was asked for.
* **Did not fly wave 4.** The prompt is ruling (2)'s to authorize, and its honest label is in the
  table above.
* **Did not move a default.** `--rounds` is named as a proposal and nothing else.
