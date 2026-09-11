# RULINGS P1 — the two unshipped rulings, and the subject's first landing

**Status: both of David's unshipped rulings of 2026-09-10 are SHIPPED, the eleven E0004 arms are
CLOSED, and a five-sortie arm was flown on the byte-identical subject.** 🎉 **Ruling 1 fired on its
first live outing and produced the first `MISSION ACCOMPLISHED` this subject has ever had** —
`a8327` ended `Why::SaidNothing` with four green rungs and was promoted; yesterday's code would have
handed that tree to an operator with the sentence *the attempt produced no artifact*. 🚨 **Ruling 2
is UNSCORED and must not be reported as working or as not working**: `diagnostics` was called **0
times in 7 attempts**, while **5 of the 7 compiled by hand through `bash`** — the repaired
instrument is one the model does not pick up, which is F650's shape exactly. 🚨 **And the landing
exposed a defect ruling 1 created**: the promoted attempt is the one path to `Accomplished` with **no
review attached**, on a task going terminal — shipped the same day (`ad64194`). ⚠ **`Accomplished`
is not *what was asked***: `a8327`'s diff put the flag in `main.rs` ahead of the parser and never
touched `cli.rs`, which the task named, and 580 of 580 tests pass because no test covers a flag
nobody had added yet. Findings **F693–F700**, next free **F701**. `abcc` `a6bb2ad` → **`ad64194`**,
three commits, **581 tests** (was 575), fmt and `clippy --all-targets -D warnings` clean. Flown
against `qwen3.6-35b-a3b-mtp@iq3_s` at `-c 40960 --parallel 1`, prompt sha **`6917f0ccaf0f83c3`**
(329 chars), asserted identical to all eleven prior arms.

---

## 1. Ruling 1 — the `Accomplished` bar, and the check that must not be written

**His words:** *"model is allowed to accomplish only if gate tree is green — and updated."*

The ruling reads as two conditions and is one. `rung::structural` returns **`exit: 1`** on
`touched.is_empty()` — *"the attempt changed no file the repository tracks"* — it is the **first**
rung, and a refusal breaks the walk. `Headline::Green` is every declared rung measured and none red.
**So a green ladder already asserts the tree moved**, and the second limb has nothing left to
enforce.

🚨 **Writing it anyway would have been the defect**, and the test that says so was written before the
ruling existed:

> the objection the widened arm has to answer … is answered by `Rung::Structural` rather than by a
> check in the driver … **a driver that re-derived *did anything change* for itself would be a
> second copy of that rule.**

That test — `an_unchanged_tree_stops_at_the_free_rung_however_the_phase_ended` — is **untouched** and
is now the proof standing up: the same truncated ending over a tree nobody wrote to still stops at
the free rung and is still not promoted.

### What changed

`ending()` read the gate **only** under `PhaseEnded::Answered`. F655 had already made the gate get
*asked* for an ending the model never chose and deliberately stopped there. The edit is one guarded
arm beside the other three:

```rust
PhaseEnded::Unmeasured { .. }
    if matches!(gate.map(|g| &g.headline), Some(Headline::Green { .. })) => accomplished(),
```

⚠ **It reads the headline and not the `why`**, because `why` says why the *conversation* stopped and
the ladder is about the *tree*. Both arms of that were checked rather than assumed: **`Why::Denied`
cannot reach here at all** (a refused tool call is a `ToolCallEnded` and the loop carries on — only
`turn.uncertain()`, `said_nothing`, the round budget, a provider error and `Disposition::Carry` end a
phase `Unmeasured`), so a denial cannot be silently promoted to `Success`. `Why::EngineError` **can**
and is: the tree passed every rung the repository declared and the fault is on the log as itself.

### 🚨 F693 — it fired, and it is the subject's first landing

`a8327`, arm 15, verified at the event level rather than from the headline:

| seq | | |
|---|---|---|
| 8406, 8413 | `phase_nudged` ×2, `left: 1` then `left: 0` | the nudge budget spent |
| 8419 | `model_call_ended`, `stop`, 391 completion of which **389 reasoning** | F503's empty payload |
| — | **no Builders `claim_recorded`** | the phase did not end `Answered` |
| 8422–8425 | structural 0 · acceptance **580/580** · veto 0 · **standard 0** | four green rungs |
| 8426 | *"the Judge was not asked: the model never said the change was finished"* | the ending was `Unmeasured` |
| 8428–8429 | `outcome: success` → `Accomplish  Engaged → Accomplished` | **the promotion** |

▶ **Under the code of the morning, that attempt ends `Uncertain { SaidNothing }` in
`AwaitingOrders`.** The tree passes every declared rung including the one that has refused this
subject six times, and the console tells the operator it produced nothing to measure. This is F503
and F655 meeting: the champion reasons to the end and emits five to nine tokens that trim to an empty
string in **8 of 10 phases**, F655 made the gate get asked about the tree anyway, and the ruling made
the answer count.

### 🚨 F694 — and it opened the one path to `Accomplished` with no review on it

Seq 8426 is the defect in its own words. The Judge is asked under `Answered` and was not widened with
the gate, on an argument that was right at the time: *a model call spent on an attempt that already
ran out of room buys prose at the price of the thing it was short of.* **That argument holds for an
attempt going back to a person and stops holding for one going terminal.** `a8327` went terminal with
nothing having read its diff against its task.

⚠ **It costs the Judge nothing it needed**, which is what makes the repair cheap rather than a
compromise: `judge::Dossier` holds the task, the diff and the rungs and deliberately holds **no
completion report** (F280–F282 — the author's prose measured *subtractive*, **0 of 3**). The dossier
for a silent ending is the same dossier. Shipped in `ad64194`: asked when the ladder is green under
`Unmeasured`, still not asked when it is not — that attempt is going back to an operator who is owed
the rungs rather than a paragraph about a tree already refused.

### 🚨 F695 — `Accomplished` means measured, and measured is not *what was asked*

The whole of `a8327`'s diff:

```rust
 fn main() -> ExitCode {
     let stdout = std::io::stdout();
     let mut out = stdout.lock();
+    if std::env::args().any(|a| a == "--version") {
+        writeln!(out, "abcc {}", env!("CARGO_PKG_VERSION")).unwrap();
+        return ExitCode::SUCCESS;
+    }
     match abcc::main_with(std::env::args().skip(1), &mut out) {
```

It works. It also ignores the sentence it was given — *"the argument surface lives in
`crates/abcc/src/cli.rs` … follow the conventions already in those files"* — by short-circuiting
ahead of the parser, and it adds an `.unwrap()` panic path into a file whose whole job is turning
errors into exit codes. **All four rungs are green and none of them could have noticed:** structural
sees a tracked file changed, acceptance runs the suite and **no test covers a flag nobody had added
yet**, veto sees a tree that builds, and the standard sees formatting and lints it has no complaint
about.

▶ **This is the strongest argument for F694's repair that exists**, and it is why the repair shipped
the same day rather than being written down as a risk: the only thing in the system that reads a diff
*against its task* is the Judge, and it was the one thing not asked.

### The test that was replaced, and the guard it broke

`a_green_ladder_under_an_unchosen_ending_is_still_uncertain` asserted the boundary F655 did not
cross. Its assertions were superseded and **so was its sentence** — *"it is nobody's to answer by
widening a `match` arm"* — so it was rewritten rather than re-pointed.

🚨 **F696 — repairing it broke the guard in the test above it, and that is the transferable lesson.**
The fixture guard in `an_ending_the_model_did_not_choose_is_measured_when_the_tree_changed` read *the
change phase really did end in an absence* **off `landed.outcome`** — and the ruling promotes exactly
that outcome to `Success`. The guard was reading the thing under test. It now reads the last
`ModelCallEnded`'s `Finish::Length { content_empty: true }`, one level below where the promotion can
reach. ▶ **A guard that shares a witness with its subject stops guarding the moment the subject
changes**, and nothing warns you: the test just starts failing for the right reason in the wrong
place.

---

## 2. Ruling 2 — F673, shipped and UNSCORED

**The defect:** the model is graded by the standard rung, is never told so, and the tool it is handed
to check its own work runs neither of the commands that grade it.

| | command |
|---|---|
| what the model was handed | `cargo check --all-targets` |
| what the gate grades with | `cargo fmt --check -- --color=never` **then** `cargo clippy --all-targets -- -D warnings` |

🚨 **It is the tool and not the prompt because W7 already measured the prompt**: the best-written
wrapper in the donor family bound its model **39 of 50**, a better-written one **0 of 50**. A tool
result is a fact; a prompt is a request. F673 is a case where the model complied with everything it
was told, iterated to **550 of 550** on its own instruments, and stopped — the criterion it was
failing was on none of them.

**Settled: APPEND, never substitute.** `Standard::declared_at` is the whole of it — a repository with
no `clippy.toml` declares no standard, **an undeclared rung is absent rather than missing**, and a
workspace without a witness gets exactly what it got before (pinned by a test). ▶ **And the compiler
still runs first**, the one ordering question: the standard's own order is cheapest-first, but
`diagnostics` exists to report compile errors and a tree with a type error would otherwise be handed
a formatting refusal instead of its error. **A red that names the wrong program is F555 read
backwards.** The list is a conjunction and the first refusal ends it, the same shape as
`rung::standard`. ⚠ The selector narrows the profile's own command and nothing else: a standard is a
claim about the tree, and appending `-p x` to a command with a `--` in it hands the argument to
rustc.

The tool's `summary` changed with the behaviour — *"return the compiler's own output"* stopped being
true, and **a summary that undersells what a tool measures is how a model comes to believe it has
checked its work**.

### 🚨 F697 — the instrument has a pickup rate of zero

Over the five sorties, seven attempts:

| tool | calls | attempts using it |
|---|---|---|
| `bash` | 28 | **7 of 7** — and **5 of 7 spent 36–81 s in it**, which is a compile |
| `apply_patch` | 26 | 6 of 7 |
| `read_file` | 103 | 7 of 7 |
| `run_tests` | 2 | 1 of 7 |
| **`diagnostics`** | **0** | **0 of 7** |

And over the eleven prior arms it was **5 calls in 2 phases against `bash`'s 95 in 13**. ▶ **So the
arm cannot score ruling 2 at all**, and saying otherwise would be F650 repeated: the change was flown
and the trigger never fired. What is now known is sharper than *the tool was wrong* — **the tool is
not the instrument the model uses.** `bash` is, it is an arbitrary shell, and nothing can make it
report the standard.

⚠ **The lever that remains is the `summary` line**, which is the only sentence in the system that
tells the model this tool is worth reaching for, and one arm of five cannot tell whether it moved
anything.

### F698 — what it costs when it is reached for

Measured cold in a worktree that has never been built, which is the case the exec budget must fit:

| command | cold, fresh worktree | warm, second call |
|---|---|---|
| `cargo check --all-targets` | **25.9 s** | 0.50 s |
| `cargo fmt --check -- --color=never` | 0.60 s | 0.61 s |
| `cargo clippy --all-targets -- -D warnings` | **8.1 s** | 0.54 s |
| **the conjunction** | **34.6 s** | **1.6 s** |

🎉 **The standard adds 8.7 s to a cold `diagnostics`, not a second compile** — which is what it
looked like it would cost and is the reason the cost question was asked at all. Clippy is cheap
*because the compiler ran first*: measured separately in its own fresh worktree, **`cargo clippy`
alone, cold, is 25.1 s** against **8.1 s** when `cargo check` has already run. They share the
check-profile artifacts.

⚠ **So the ordering decision has a price and it is now a number rather than an argument.** On a tree
that compiles, running the compiler first costs **+8.9 s (35%)** over substituting the standard for
it — 34.6 s against 25.7 s. On a tree that does not, the two are level: the conjunction stops at the
first refusal, so a broken tree pays the 25.9 s check and never reaches clippy, where the substitute
would pay 0.6 s of fmt and 25.1 s of clippy to report the same error. **8.9 s on the passing case is
what it costs to have compile errors reported by the program whose job is compile errors**, and it is
9 seconds against a model turn measured in minutes.

⚠ And it is far cheaper than the other exec tool: `target/` after the conjunction is **622 MB**
against the gate's **2.3 GB**, because nothing here links a binary.

---

## 3. The arm, sortie by sortie

| arm | task | attempts | ending | standard rung | `diagnostics` |
|---|---|---|---|---|---|
| 12 | `t7655` | 2 | `Uncertain` — 24 rounds, both | not reached (veto red, E0004) | 0 |
| 13 | `t7999` | 1 | **`Refused by standard`** | reached, **refused** — `match_same_arms` | 0 |
| 14 | `t8149` | 1 | `Refused by veto` — E0004 | not reached | 0 |
| 15 | `t8319` | 1 | 🎉 **`Success` → `Accomplished`** | reached, **passed** | 0 |
| 16 | `t8430` | 2 | `Uncertain` — 24 rounds, both | not reached | 0 |

**Against the eleven-arm baseline, re-derived from the log rather than quoted:**

| | baseline (11 arms) | this arm (5 sorties) |
|---|---|---|
| attempts | 20 | 7 |
| reached the standard rung | 4 | **2** |
| passed it | **0** | **1** |
| `diagnostics` calls | 5 | **0** |

⚠ **One pass in seven attempts is inside F575's floor** — *asking the identical question twice moved
totals 41 → 50, and turning the switch on moved them 41 → 51* — and F657 is the same warning on this
exact subject: `a6865` 4 of 5 and `a7085` 1 of 5 on a byte-identical prompt an hour apart. **Quote
the aggregate, never a run.** What is attributable is not the rate: it is that **ruling 1's promotion
fired, and the mechanism is on the log event by event.**

### 🚨 F699 — the lint refuses the design the task asks for

Every refusal of the standard rung this subject has ever produced, over sixteen arms:

| attempt | refused by |
|---|---|
| `a5738` | `cargo clippy` — `match_same_arms` |
| `a6689` | **`cargo fmt --check`** |
| `a6865` | **`cargo fmt --check`** |
| `a7085` | `cargo clippy` — `match_same_arms` |
| `a8007` | `cargo clippy` — `match_same_arms` |

▶ **Half the baseline's refusals were rustfmt and every summary had said clippy.** And the clippy half
is the sharper fact: following the repository's own convention — a `CliError::Version` beside
`CliError::Help`, which is what the task asks for — produces two match arms with identical bodies,
and `clippy::match_same_arms` refuses it:

```
96 ~ AppError::Cli(cli::CliError::Usage(_)) => 2,
97 ~ AppError::Cli(cli::CliError::Help) | AppError::Cli(cli::CliError::Version(_)) => 0,
```

The lint is right and the merge is one line. **But the only attempt that ever passed this rung is the
one that did not follow the convention** — `a8327` never opened `cli.rs`. ⚠ *A gate that refuses the
instructed design and accepts the shortcut is selecting for the shortcut*, and nothing in the system
says so out loud except a review nobody was asking for until `ad64194`.

### 🚨 F700 — a gate refusal reaches a person and never a model

Read in code rather than inferred. `brief::refused` writes the rung and its detail into
`Event::OperatorPrompted`; the only readers of `OperatorPrompted` and `OperatorAnswered` anywhere in
the workspace are `abcc-tui`, `replay` and `fun`. `brief::change` is `row.title` + `row.prompt` +
Recon's report + an optional redirect, and `Driver::land` builds it identically for a fresh attempt
and for a `Cause::Retry`.

▶ **So the standard rung's verdict cannot reach a model on any path except an operator retyping it as
a `redirect`.** That is F673 one level up and a larger lever than the tool: even when the criterion
fires, the information dies at the desk. ⏸ **Not shipped** — it is a change to what a retry is told,
which is a prompt-surface change and wants its own arm.

---

## 4. The eleven arms — closed

David ruled on 2026-09-11 after three agents recommended it across two sessions: **reject all
eleven.** Done — `t4886`, `t5221`, `t5430`, `t5683`, `t5871`, `t6207`, `t6530`, `t6858`, `t6985`,
`t6986`, `t6987`, each carrying the ruling as its note. All eleven were in `AwaitingOrders`; the
brief said seven because the last four were flown after it was written. `reject` is
`Aborted { Operator }`, it hands the workspace back through `takeover::hand_back`, and **the
checkpoints are still on refs**.

---

## 5. What is owed next

1. 🚩 **F700 — tell a retry what refused it.** The largest lever found this session and the only one
   still untouched. A prompt-surface change: it wants an arm.
2. ⏸ **The `summary` lever is unmeasured.** F697 says the model does not reach for `diagnostics`; one
   arm cannot say whether the new sentence moves that. A second arm on the same subject would.
3. ⏸ **The four `paint` changes** — `--px` 150→120, `--cell` 20→a value that over-reserves, the
   inverted comment at `paint.rs:307`, a test pinning `rows × cell ≥ height`.
4. ⏸ **Row 8's other half** — `--offline` for unattended roles, and `leaves_the_machine` acquiring a
   caller or an explanation of why it has none.
5. ⏸ **The 96 voice lines**, unblocked now the dependency gate exists.
6. 🚨 **SELF-HOST still opens on a broken instrument**: `review_recorded` is 0 and always has been.
