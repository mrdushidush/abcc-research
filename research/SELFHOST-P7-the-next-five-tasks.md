# SELF-HOST P7 — the next five tasks, and why each one is wanted

**Status: a work queue, not a study.** The first landing happened 2026-09-18 23:09 — `a0054e7`,
`Seq::is_origin`, 4 rungs, **120 seconds of human review**. W13's ladder has one row. These five are
chosen to give it four or five more, and every premise below was checked against the tree at
`a0054e7` rather than assumed.

🚨 **Three of the four remaining green attempts now CONFLICT.** Landing `a0054e7` moved `seq.rs`, and
`t2598` / `t2691` / `t2692` were already three weeks stale. Only **`t8319`** (`--version`) still
applies, and its diff is the weak one. **So there are no free ladder rows left; these need runs.**

---

## The shape that works, read off the log

The engine has gone green **6 times in 126 attempts**. Every one of the six was: **one file, one
function or method, purely additive, with a test.** The one prompt that named a neighbour which did
not exist (`t2598`, *"beside `available`"* — `available` was deliberately deleted at F646) produced a
change whose premise was already false. So each task below **names the file, the exact signature, and
a real neighbour to copy**, which is also what F774 asks for: 50.5% of the Change phase's tool calls
are `read_file` and 65% of those are re-reads, so anything the prompt can settle is a round saved.

---

## 1. `Seq::back` — the strongest of the five

**`crates/abcc-core/src/seq.rs`.** Three independent reasons, all verified:

* 🎉 **It is already open-coded in the TUI.** `crates/abcc-tui/src/reader.rs:172`:
  `Intent::Rewind(Seq::new((self.view.cursor().get() - back).max(0)))` — that *is* `back`, saturating
  at the origin, written out by hand.
* 🚨 **A shipped doc comment already discusses it.** `crates/abcc-gate/src/judge.rs:379` describes a
  model's attempt at `Seq::new(-1).back(5)` and the defect in it. The archive's own prose names a
  method the crate does not have.
* ✅ **The engine has already done it once** (`t2692`, 4 rungs, 510/510 tests) and that diff now
  conflicts.

⚠ **And judge.rs records exactly how a model got it wrong before:** *"an `as u64` cast that turns a
negative into a large positive and walks straight past the saturation the task asked for."* The
prompt says so, because a criterion the model cannot see is F673 and this one can simply be stated.

## 2. `Outcome::is_unmeasured`

**`crates/abcc-core/src/outcome.rs`.** `impl Outcome` has `is_green`, `is_red` and `rung` — and the
doc comments on the first two both go out of their way to say the third state is neither: *"An absent
measurement is not red either — that is the whole point of the type."* **There is no way to ask for
it.** Callers pattern-match instead: `abcc/src/land.rs:192`, `abcc-gate/src/rung.rs:247`, and tests
in `abcc-drive` and `abcc-gate`. Completing the triple is the module's own doctrine.

## 3. `Cause::name`

**`crates/abcc-core/src/attempt.rs`.** `AttemptOutcome::name(&self) -> &'static str` is 50 lines
below `Cause` in the same file. `Cause` has no equivalent, and **two files map it to strings by hand
— and they already disagree**: `abcc/src/replay.rs:726` says `"edit"`, `abcc-tui/src/line.rs:414`
says `"edited {of}"`. One fact, two renderings, one word apart, which is F392's shape in miniature.

⚠ The task is **additive only**. Rewiring `replay.rs::cause()` to call it is a second change and a
second review; it is not bundled here.

## 4. `abcc --version`, done the way the file already does `--help`

**`crates/abcc/src/cli.rs`** and **`crates/abcc/src/main.rs`.** The flag genuinely does not exist —
`abcc --version` prints *"is not a command"* today. ⚠ **This is the one task with two files**, and it
is here anyway because `t8319`'s green diff is the *wrong* implementation: it bypasses `cli::parse`
with a manual `std::env::args()` scan and an `.unwrap()` in `main.rs`, when Recon had correctly
pointed at the `CliError` enum. **The prompt names the right seam** — a `Version` variant beside
`Help`, which is already *"not a failure"* in the same match.

## 5. `Seq::forward` — run this one LAST

**`crates/abcc-core/src/seq.rs`**, the symmetric partner of `back`. `abcc-tui/src/feed.rs` computes
it by hand twice — `Seq::new(self.head().get() + 1)` at line 110 and the same `+ 1` at line 78.

🚨 **Two constraints on this one.** It touches the same `impl Seq` block as task 1, so **land task 1
before running it** or the second diff conflicts. And it **must not be called `next`**:
`clippy::should_implement_trait` fires on a method named `next`, and the standard rung is
`clippy --all-targets -- -D warnings`, so the name alone would fail the gate.

---

## What was considered and REJECTED, so nobody re-proposes it

| candidate | why not |
|---|---|
| `budget::retries()` (`t2598`) | Names `available`, deleted at F646; `ATTEMPTS - 1` is computed nowhere, so it would be dead code — and `budget.rs` says *"there is deliberately no cause-blind version of this."* |
| `Counts::all_passed()` | Against ADR-0009 §5 — `exit` decides the verdict, and `Measurement.exit`'s own doc says counts are *"never parsed for a verdict."* |
| The 20 broken intra-doc links `cargo doc` reports | **The gate cannot check them.** Its rungs are structural, `cargo test`, veto, and fmt+clippy — `cargo doc` is none of them, so a wrong answer still goes green and the cost lands on the operator's review minutes, which is the metric M1 *is*. |
| `name()` on `AttemptPhase`, `Mode`, `TaskState` | `abcc-tui/src/theme.rs` maps these per theme on purpose (`Localize` → `RECON`). Not a gap; the theme doing its job. |
| `Display for Outcome`, `name()` on `Why` | The two existing renderings are wire-token vs operator prose and one impl cannot serve both; `Why` already has `Display`, and a `name()` would duplicate serde. |
| A parser for `checkpoint_ref` | Nothing reads a seq back out of a ref — the sha comes from the event. It would be dead code. |

---

## Running them

`research/tools/selfhost-queue.ps1` creates all five with `abcc task`. Nothing in it runs an attempt,
lands anything, or touches the GPU.

```
cd D:\dev\abcc
powershell -File ..\ABCC_20_powerd_by_claudette\research\tools\selfhost-queue.ps1
```

Then, per task — and **the champion has to be loaded first, the GPU is empty**:

```
lms load qwen3.6-35b-a3b-mtp@iq3_s -c 40960 --parallel 1
.\target\release\abcc.exe run --task t<id>
.\target\release\abcc.exe board
```

🚨 **`land` and `review` stay David's.** An agent running `review` writes `by: operator()` and
fabricates the one measurement SELF-HOST is judged on.

⚠ **Expect to lose some.** 6 of 126 attempts have gone green — but 5 of those 6 are this exact shape,
and the two attempts that did `is_origin` both passed. 🚨 **And do NOT expect budget 2 to buy a second
try here:** a gate *refusal* is a measured answer, not a failure, so `AttemptOutcome::is_retryable` is
false for it, the task goes straight to **INTERVENTION REQUIRED**, and neither `run` nor `fleet` will
attempt it again. **One attempt is what a refused task gets.** (An earlier draft of this line said
`fleet` would retry once. It will not, and the distinction is ADR-0009's whole point.)

---

## What the first run showed, 23:25–23:31 — and it is one decision, not a mystery

**`t13051` `Seq::back`, first attempt `a13063`, 6 minutes.** It produced a **correct** implementation
with three tests, and it **anticipated the exact trap `judge.rs:379` documents** — `back(u64::MAX)`
returns `ORIGIN` instead of casting a negative into a large positive:

| rung | |
|---|---|
| structural | **exit 0** — 1 file changed |
| acceptance | **exit 0** — **681 / 681 tests passed** |
| veto | **exit 0** — nothing vetoed |
| **standard** | **exit 101** |

🚨 **And what refused it was a style lint.** `cargo fmt --check` passed. Clippy said *"this could be
rewritten as `let...else`"* and printed its own one-line fix. The change is three lines from landing:

```rust
let n = match i64::try_from(n) { Ok(n) => n, Err(_) => return Self::ORIGIN };
// clippy wants: let Ok(n) = i64::try_from(n) else { return Self::ORIGIN };
```

🚨🚨 **THE LINT WAS NOT IN THE DENIED SET, AND THE LOG SAYS SO ITSELF.** The note reads
**`-D clippy::manual-let-else` implied by `-D warnings`**. `Cargo.toml` declares
`clippy::all = deny` and **`clippy::pedantic = warn`**; `manual_let_else` is pedantic, so it is a
*warning* by the workspace's own configuration — and the **gate's command line**,
`cargo clippy --all-targets -- -D warnings`, is what promotes it to a blocker.

⚠⚠ **AND THE OBVIOUS CONCLUSION FROM THAT IS WRONG, WHICH IS WHY THE CLASS WAS COUNTED.** The first
draft of this section called the `-D warnings` promotion *the* blocker and a one-flag decision. Over
the whole log it is **2 cases in 10**:

| of the 10 near-misses, what refused it | n |
|---|---|
| **`cargo fmt --check`** — formatting, not clippy at all | **4** |
| a lint the workspace **denies** (`clippy::all` in `Cargo.toml`) | **4** |
| a lint only **promoted** by the gate's `-D warnings` (pedantic) | **2** |

▶ **So dropping `-D warnings` would have unblocked two of ten.** ⚠ And even that split is soft: the
rung `detail` is truncated on the log, so the *"implied by `-D warnings`"* note can be cut — **4 is an
upper bound on the denied group and 2 is a lower bound on the promoted one.** Both readings are
reported rather than the convenient one.

⚠ **A refusal is not a failure and the engine is right about that.** `Refused { rung: "standard" }`
sends the task to **INTERVENTION REQUIRED** and **never retries** — a deterministic rung produced a
measurement, and ADR-0009's whole point is that a measurement is information rather than an error.
**So budget 2 does not apply here: one attempt is what a refused task gets.**

✅ **`research/tools/reviewpack.py --near` exists for exactly this** — it lists every green *and* every
one-rung-refused attempt with its diff, its rung output, and whether it still applies to `HEAD`.
`t13051`'s diff **applies cleanly to `a0054e7`**.


---

## The five ran 23:25–23:48. One landed, and the losses name one rung

| task | attempt | min | outcome | change-phase reads | edits |
|---|---|---|---|---|---|
| `Seq::back` | `a13063` | 6.0 | **refused / standard** — the change was *correct*, 681/681 | 4 | 1 |
| `Outcome::is_unmeasured` | `a13164` | 3.7 | `uncertain` / **truncated_at_cap** | 3 | **0** |
| `Cause::name` | `a13241` | 3.6 | `uncertain` / **truncated_at_cap** | 2 | **0** |
| `abcc --version` | `a13308` | 3.3 | `uncertain` / **context_overflow** (40,828 of 40,960) | 14 | 4 |
| **`Seq::forward`** | **`a13436`** | **6.8** | 🎉 **success — 4 rungs, 680/680** | 3 | 1 |

**Five walls, four of them different, and not one of them is the model failing at the work.**

* 🚨 **Two attempts never attempted an edit.** `a13164` and `a13241` spent the whole Change phase on
  `read_file`/`search`, then hit the **16,384-token completion cap** while writing. Both had a Recon
  brief that named the file *and quoted the lines*. **This is F774 at full strength** — reading was
  not 50.5% of the Change phase, it was **100%** of it. ⚠ And the budget's own doc forecloses the easy
  fix: *"raising this budget alone does not raise the ceiling; the ceiling is the gap"* (F625).
* 🚨 **`context_overflow` fired for the first time on this log** — window 40,960, prompt 40,828, **132
  tokens of headroom**. ⚠ **That one is my fault, not the engine's:** I wrote a four-seam, three-file
  prompt, said in this very file that it broke the one-file envelope, and shipped it anyway. **The
  prompt was the defect.**
* ✅ **`Seq::forward` is landable now** and applies cleanly to `a0054e7`.

### 🚨 What the whole log says, which is bigger than tonight

113 attempts: **6 success, 20 refused, 82 uncertain.** Of the 20 refusals, **10 are one rung from
landing** — every other rung measured green — and **all ten refused at `standard`. Not one at
structural, acceptance or veto.**

▶ **And a third of them are pure formatting**, which `cargo fmt` fixes mechanically. **F673's repair
put `fmt` and `clippy` inside the `diagnostics` tool for exactly this reason — and F786 measured that
`diagnostics` has never been called once under that summary.** The instrument built for this failure
class has never been picked up. **That is the finding, and it is not a new one — it is F786 with a
cost attached.**

⚠ **`reviewpack.py --near` also surfaced `t11727` from 09-14**: `--version` implemented properly
across `cli.rs`, `main.rs` and `tests/cli.rs`, 657/657 tests, refused at `standard` on two clippy
lints — **and it still applies cleanly to `a0054e7`.** The near-miss pile is older than tonight.

---

## 🚨🚨 F791 — the tool F673 shipped is hostile to its own first use

**Wave 2's prompts told the model to check its work with `diagnostics`. It did — and that is the
first `diagnostics` call on this project since 2026-09-08, and the first *ever* under the summary
`4687405` shipped (F786: 0 of 39 anchored Change attempts).** This is what came back:

```
$ cargo check --all-targets crates/abcc-core
exit 1 in 49 ms
error: unexpected argument 'crates/abcc-core' found
Usage: cargo.exe check [OPTIONS]
```

▶ **The model passed `selector: "crates/abcc-core"`, which is the only thing the schema invites, and
the tool spliced it onto the command line as a positional argument.** `workspace.rs:763`:

```rust
let mut argv: Vec<String> = command[1..].iter().map(|a| (*a).to_owned()).collect();
argv.extend(asked.selector.iter().flat_map(|s| s.split_whitespace()).map(ToOwned::to_owned));
```

🚨 **The selector is appended RAW, and `cargo check` takes no positionals at all** — cargo's own
error says so: *"Usage: cargo.exe check [OPTIONS]"*. Narrowing it requires **`-p abcc-core`**, and
**nothing tells the model that**: the schema is `{"selector": {"type": "string"}}` with no
description, and the summary — the sentence F673 rewrote precisely so it would stop under-selling the
tool — does not mention the selector at all.

🚨 **And the trap is that the SAME SCHEMA is right for the other tool.** `tools.rs:268` (`run_tests`)
and `tools.rs:287` (`diagnostics`) are **byte-identical** in their schema, and for
`cargo test <filter>` a bare string *is* correct. So a model that has learned `selector` from
`run_tests` will use it the same way on `diagnostics` and get a usage error back.

⚠ **What this is and is not.** It is a **code defect, read from the source and from cargo's own
refusal** — not a rate, not an inference, n = 1 call and it does not need more than one, because the
argv construction is deterministic. It is **not** a claim that this is why F786's count is zero:
F786 measured **zero calls**, so nobody had reached this. What it does mean is sharper than a rate:

▶ **The instrument F673 built to show the model the criterion it cannot see fails on the first
plausible argument anybody gives it.** The repair has been in the tree since 2026-09-11, unused, and
the first time a model was told to pick it up, it got a usage error instead of a measurement.

▶ **The fix is small and it is David's to rule on** — translate the selector per profile (`-p` for
cargo's `check`, bare for `test`), or reject a selector `diagnostics` cannot honour, or say the form
in the schema. **The one thing not to do is leave a tool whose documented argument breaks it.**

---

## 🚨 The green change that was not what was asked — and the contradiction was MINE

**`t13604` `Cause::name` passed all four rungs** and returns:

```rust
Cause::Fresh => "Fresh",  Cause::Retry { .. } => "Retry",  ...
```

The prompt said *"it returns the bare variant name: `"fresh"`, `"retry"`, `"rescope"`, `"edit"`,
`"replay"`"* — **lowercase**, which is what `replay.rs::cause()` returns and what serde's
`rename_all = "snake_case"` tag emits, and therefore the only casing that would let the method unify
the two hand-rolled mappings this task existed to unify.

⚠ **But the same prompt also said *"`AttemptOutcome::name` … does exactly this job for the other
enum; match its shape"* — and `AttemptOutcome::name` returns `"Success"`, `"SoftFailure"`,
`"HardFailure"`. Capitalised.** So the prompt gave two instructions that cannot both be obeyed, and
**the model followed the code over the prose.** That is the defensible resolution of a contradiction
it did not create.

▶ **So this is a defect in the task, not in the attempt**, and the casing is now a design question for
the operator: lowercase to match `replay.rs` and the wire tag, or capitalised to match the sibling
method in the same file. **Either is a coherent answer; the prompt should have picked one.**

🚨 **THE LESSON IS ABOUT AUTHORING, AND IT IS THE SECOND PROMPT DEFECT OF THE NIGHT** (the first put
four seams in three files and overflowed the window at 40,828 of 40,960). **A prompt that names both
a literal specification and a neighbour to imitate has to check that the two agree** — and when they
do not, the gate cannot tell: all four rungs measured green, because the model wrote a test that
asserts its own strings. ▶ **A green gate is compliance with the compiler, the tests, the formatter
and the linter. It is not compliance with the request, and nothing in the ladder claims it is.** That
cost is paid in exactly the currency M1 measures: the operator's review minutes.

---

## ⚠ THE TWO `seq.rs` CHANGES CANNOT BOTH LAND — land one, re-run the other

`t13055` (`Seq::forward`) and `t13606` (`Seq::back`) are both green, both apply cleanly to `a0054e7`
**on their own**, and both:

* insert into `impl Seq` at the **same** point — each patch opens `@@ -43,6 @@`, after `is_origin`;
* add a **`#[cfg(test)] mod tests`** to `crates/abcc-core/src/seq.rs`, **which has none today**.

🚨 **So landing both gives that file two modules named `tests`, which is `E0428` — a compile error,
not a merge conflict.** That is certain by reading the two patches; it needs no experiment.

Measured, with `t13606` applied first: plain `git apply --check` of `t13055` then **conflicts** at
`seq.rs:43`. ⚠ **And what that test could NOT answer:** `land` uses `git apply --3way`, which needs
the pre-image in the *index*; I applied to the working tree without committing, so the `--3way` run
returned *"does not match index"* — **an artifact of the test setup, not a verdict on `land`.**
Answering it properly requires committing the first change, which is `land`, which is the operator's.
**So this is reported as unknown rather than guessed.**

▶ **The order that works regardless:** land one, then **re-run the other task** against the landed
tree. `Seq::back` (`t13606`) is the better of the two to land first — it has five tests to `forward`'s
two, and `reader.rs:172` open-codes exactly it today.

---

## ✅ THE COMBINATION IS VERIFIED GREEN — four changes, landable together

Each attempt's gate measured **its own change alone** against `a0054e7`, so the tree with all of them
on it had never been measured by anything. **It is now.** Applied in this order and then run through
the gate's own four commands:

| applied | file |
|---|---|
| `t14016` `Outcome::is_unmeasured` | `abcc-core/src/outcome.rs` |
| `t13604` `Cause::name` | `abcc-core/src/attempt.rs` |
| `t13606` `Seq::back` | `abcc-core/src/seq.rs` |
| `t8319` `abcc --version` | `abcc/src/main.rs` |

| command | exit |
|---|---|
| `cargo check --all-targets` | **0** |
| `cargo fmt --check -- --color=never` | **0** |
| `cargo clippy --all-targets -- -D warnings` | **0** |
| `cargo test --workspace` | **0** |

▶ **All four can be landed.** ⚠ `t13055` `Seq::forward` is **excluded** — it is the one that collides
with `t13606`. Land `t13606`, then re-run `Seq::forward` against the landed tree.

## ⏹ `--version` has now failed five times, on five different walls — it needs a ruling, not another attempt

| attempt | wall |
|---|---|
| `t8319` | **green**, but bypasses `cli::parse` with `env::args()` and `.unwrap()` |
| `t11726` | veto |
| `t11727` | `standard` — two clippy lints; **its diff still applies cleanly** |
| `t13054` | `context_overflow`, 40,828 of 40,960 — **my four-seam prompt** |
| `t14017` | veto — `#[error(env!(…))]`; thiserror needs a literal. **My prompt invited it** |
| `t14411` | `standard` — `clippy::match_same_arms`, then out of rounds at 24 |

🎉 **`t14411` is the informative one.** The attribute form I compile-tested first
(`#[error("abcc {}", env!("CARGO_PKG_VERSION"))]`) **worked** — no veto failure. What refused it was
somewhere the prompt could not have pointed: **`tests/cli.rs:287` already merges
`Ok(_) | Err(CliError::Help)`**, so a third variant makes three arms with identical bodies and
`clippy::match_same_arms` demands they be merged. ▶ **So adding a `CliError` variant is not confinable
to `cli.rs`** — it forces an edit to an existing test helper, and the linter dictates its shape. **My
"cli.rs only" decomposition was wrong about the blast radius.**

🚨 **And three attempts tonight ended `budget_exhausted / 24 rounds` *after* being told to run
`diagnostics` and fix what it reports** (`t13603`, `t14017`, `t14411`). **The lever works and it costs
rounds:** the model edits, checks, finds a lint, repairs, re-checks — and 24 rounds does not cover it.
`--rounds` is a flag on `abcc run`, so this is testable without touching a default. ▶ **That is the
next thing worth trying on this task, and it is a proposal, not a move.**
