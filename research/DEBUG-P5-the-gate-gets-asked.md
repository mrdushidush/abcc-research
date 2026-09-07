# DEBUG P5 — the gate gets asked, and the arm is only half scored

**Status: F655 is shipped and flown. `abcc` `38763a6` asks the gate about an `Unmeasured` ending as
well as an `Answered` one, so an attempt that ran out of rounds is measured instead of being told it
produced nothing. Two sorties, four attempts: the new path fired twice and cost **44 ms** each time,
measured on the log, with the acceptance command never reached — which is the objection the change
had to answer, answered in the field rather than in a test. ⚠ But both times the tree was empty. The
case the change exists for — a budget-exhausted attempt whose tree holds work — occurred **0 of 4
attempts here against 5 of 10 in arms 1–5**, so F655 is proven wired and proven cheap and its value
case is still only retrospective. Meanwhile the subject produced its best tree yet: `a6689` passes
structural, acceptance (**550 run, 550 passed, 0 failed**) and veto, and is refused by
`cargo fmt --check` over **one stray blank line**.** Findings **F662–F667**; next free number is
**F668**. Built and flown 2026-09-07 against `D:\dev\abcc`, model `qwen3.6-35b-a3b-mtp@iq3_s` at
`-c 40960 --parallel 1`, `abcc check` matched exactly before each sortie. **550 tests (was 544), 19
ignored, clippy clean under `-D warnings`, `cargo fmt --all --check` clean. Five mutations, one at a
time, none survived.**

▶ Follow-on to `DEBUG-P4-the-gate-that-was-never-asked.md` §9, which named F655 as *the one worth
fixing* and said it wanted an arm of its own. This is that arm.

⚠ **A correction to DEBUG-P4 before anything else.** §5 said a round-budget or token-cap ending
lands in `PhaseEnded::Stopped`. It does not — those are `PhaseEnded::Unmeasured { why }`, and
`Stopped` is the **operator's** halt. Same code line, same mechanism, wrong label; DEBUG-P4 is
corrected in place. It mattered, because it is the difference between widening the arm that holds
*the operator stopped this and it is not ours to judge* — which is a rule worth keeping — and the
arm that holds *the model was still working*.

---

## 1. What shipped: one `match` arm, and two things deliberately left alone

`crates/abcc-drive/src/lib.rs` gated the ladder on `PhaseEnded::Answered` alone, and the comment
beside it folded two absences into one word:

```rust
// An attempt that ended in an absence has nothing to measure, and an
// attempt the operator stopped is not ours to judge.
```

`SaidNothing` really is nothing to measure. `BudgetExhausted` and `TruncatedAtCap` are *the model was
still working when the clock ran out*. The arm now reads:

```rust
(Some(closing), PhaseEnded::Answered { .. } | PhaseEnded::Unmeasured { .. }) => {
    Some(self.gate(attempt, &opened, closing)?)
}
```

**Three things about that are decisions rather than mechanics.**

▶ **The driver does not check whether the tree changed, and must not.** The objection to the widened
arm is *this now pays for a cold `cargo test` on attempts that wrote nothing*. It does not, and the
reason is already in the gate: `Gate::measure` runs `Rung::Structural` first, that rung **owns** the
empty diff, and a refusal breaks the walk. Re-deriving *did anything change* in the driver would have
been a second copy of a rule `rung.rs` is explicit about owning once — §4 measures what it costs
instead of asserting it.

▶ **It measures; it does not promote.** `ending` reads the gate **only** under `Answered`, so a
budget-exhausted attempt still ends `Uncertain { BudgetExhausted }` with its rungs now on the log.
🚨 Whether a gate-green tree the model never declared finished may be `Accomplished` is a question
about **who is allowed to stop**, ADR-0009's *only a measurement says Accomplished* does not settle
it, and it is not a `match` arm's to answer. **It is David's, and a test holds the boundary shut
until he answers it.**

▶ **The Judge was not widened with the gate.** It is a model call that decides nothing by
construction; spending ~40–55 s of it on an attempt that just ran out of room buys prose at the price
of the thing it was short of. ⚠ The absence is a `Note` rather than a gap, like every other absence
here — the log now carries *the Judge was not asked: the model never said the change was finished, so
there is a measurement to read but no completed change to review*.

**And the sentence that reported all of this was false.** `run.rs` printed *gate not asked — the
attempt produced no artifact*, which described the branch it was printed from and not the tree. It
now names the operator, which after this change is the only way to reach it at all.

---

## 2. Six tests, and the one that is about my own boundary

Five in `abcc-drive/tests/attempt.rs`, over a real git repository and a real log, and one in
`run.rs` over the rendered line.

| test | the claim |
|---|---|
| `an_ending_the_model_did_not_choose_is_measured_when_the_tree_changed` | the arm itself: cut at the cap mid-change, three rungs green |
| `a_green_ladder_under_an_unchosen_ending_is_still_uncertain` | 🚨 **the boundary** — green ladder, still `Uncertain`, not `Accomplished` |
| `an_unchanged_tree_stops_at_the_free_rung_however_the_phase_ended` | one rung on the log, `exit 1`, acceptance never reached |
| `the_judge_is_not_asked_for_an_ending_the_model_did_not_choose` | the review head unused, and the `Note` says why |
| `an_attempt_the_operator_halted_asks_no_rung` | `Stopped` still is not ours to judge |
| `run::tests::an_unasked_gate_names_the_operator_…` | the string, where the operator reads it |

⚠ **The last one exists because of F649's rule and DEBUG-P4's F656.** The driver arm and the sentence
that reports it are two places and only one of them is what anybody sees; a false sentence was
inherited as a fact by four sessions of write-ups. Asserting the rendered line is what makes the
correction stick.

### Five mutations, one at a time

| mutation | caught by |
|---|---|
| revert the gate arm to `Answered` only | `an_ending_the_model_did_not_choose_is_measured…` |
| promote a green ladder under an unchosen ending to `Success` | `a_green_ladder_under_an_unchosen_ending_is_still_uncertain` |
| widen the Judge with the gate | `the_judge_is_not_asked_for_an_ending…` |
| gate the operator's stop too | `an_attempt_the_operator_halted_asks_no_rung` |
| restore *the attempt produced no artifact* | `run::tests::an_unasked_gate_names_the_operator_…` |

🚨 **The harness was wrong before the code was, and said so on the first run.** It reported the fifth
mutation as *surviving*. It had not: `cargo test <name> -- --exact` matches the **full** test path,
so the bare name filtered to **zero tests**, exited 0, and read as a pass. The harness now requires
the named test to have **run** — `running 1 test` — rather than inferring it from an exit code. ▶ It
is the same shape as item 122 in `verify-claims-against-code-not-docs`: *a summary statistic over
filtered data is a claim about the filter first.*

---

## 3. The arm: two sorties, four attempts

Same subject, same 329-character prompt read back from `abcc replay t4886` and asserted byte-identical
before each flight, same model confirmed exactly. `t6207` and `t6530`.

| arm | attempt | tree at the closing checkpoint | gate | rungs | ending |
|---|---|---|---|---|---|
| 6 | `a6214` | (no change) | **ASKED — new** | structural `exit 1` | BudgetExhausted 24 |
| 6 | `a6385` | 3 files, +11 | ASKED | structural 0 · acceptance **E0004** · veto 1 | Refused by **veto** |
| 7 | `a6537` | (no change) | **ASKED — new** | structural `exit 1` | BudgetExhausted 24 |
| 7 | `a6689` | 4 files, +13 | ASKED | structural 0 · acceptance **550/550** · veto 0 · standard 1 | Refused by **standard** |

**The gate was asked about 1 of 10 attempts across arms 1–5. It was asked about 4 of 4 here.** ⚠ Two
of those four are F655's doing; the other two ended `Answered` and would have been gated anyway.

### What the new path cost, measured on the log

`a6214`, from the log's own millisecond stamps:

```
+62840  phase_ended            the change phase gives up at 24 rounds
+63055  checkpoint_taken       the closing snapshot — 215 ms, and taken before F655 too
+63099  rung_recorded          structural, exit 1 — 44 ms, and this is the whole addition
+63100  note                   "the Judge was not asked: the model never said …"
+63175  attempt_ended
```

🎉 **44 milliseconds**, against the 0.024 s `rung.rs` predicts for the rung itself, and the
acceptance command was never reached. `a6537` is the same shape. **The objection is answered with a
number rather than an argument**, and the sentence the operator now reads is *the attempt changed no
file the repository tracks* — which is true — instead of *the attempt produced no artifact*, which
was not.

---

## 4. 🚨 The honest score: the half that fired is the cheap half

F655 exists for the attempt that **ran out of rounds with work in the tree**. Across arms 1–5 that
happened **5 times in 10 attempts**. Across arms 6–7 it happened **0 times in 4**: both
budget-exhausted attempts wrote nothing at all, and both retries answered.

So what this arm establishes is real but narrower than the change it scores:

* ✅ the wiring works — an `Unmeasured` ending reaches the ladder, twice;
* ✅ the cost objection is dead — 44 ms, measured, twice, with `cargo test` never reached;
* ✅ the false sentence is gone and the true one is in its place;
* ⚠ **the rescue has not been observed live.** Every tree F655 would have saved is one it saved
  *retrospectively*, by hand, in DEBUG-P4 §6.

⚠ **Do not read the 0-of-4 as evidence against the change.** F655 acts *after* a phase ends and
cannot influence what the model does; the two budget-exhausted attempts here wrote nothing because
`apply_patch` was refused 4 of 4 and 2 of 2 in them, which is the fold and the near-miss, not the
gate. n = 4 against a base rate near a half is a handful of coin tosses.

---

## 5. The best tree this subject has produced, and it is two mechanical edits from Green

`a6689` changed four files — the variant in `cli.rs`, the exit code in `lib.rs`, **the printing arm
in `main.rs`**, and the exhaustive match in `tests/cli.rs` — and the ladder measured it:

```
rung  structural  exit 0  4 file(s) changed
rung  acceptance  exit 0 — 550 run, 550 passed, 0 failed
rung  veto        exit 0  nothing vetoed
rung  standard    exit 1  `cargo fmt --check -- --color=never` refused
```

Rebuilt out-of-tree, **the entire fmt refusal is one stray blank line** at `cli.rs:284`:

```diff
     }
 
-
     // The two global flags are pulled out first so they can appear anywhere,
```

Apply `cargo fmt` and clippy then refuses `match_same_arms` — the same lint that has refused every
compiling tree this subject has produced. So: **delete one blank line, merge one match arm, and it
lands.**

🚨 **Which blocker gets *reported* depends on which runs first, and the standard rung is a
conjunction.** `Standard::commands` runs `cargo fmt --check` then `cargo clippy --all-targets -- -D
warnings`, cheapest first, and the first refusal ends the rung. Arm 4 reported clippy; arm 7 reported
fmt. **Both trees have both faults.** Anyone reading a single run's headline as *the* blocker will
name the wrong one — which is exactly what F657 warned about for the fold's rate, one layer up.

---

## 6. Findings

**F662** — 🚨 **F655 shipped and the gate is now asked about an `Unmeasured` ending.** `abcc`
`38763a6`: one `match` arm in `abcc-drive`, the Judge deliberately not widened with it, and the
console's *the attempt produced no artifact* replaced by a sentence about the operator. Six tests,
five mutations, none survived; 550 tests, clippy and fmt clean. ⚠ It **measures and does not
promote** — `ending` still reads the gate only under `Answered`, and a test holds that shut, because
whether a gate-green tree the model never declared finished may be `Accomplished` is David's
question and not a `match` arm's.

**F663** — 🎉 **The cost objection is dead, and the number is 44 ms.** The whole addition on an
unchanged tree, twice, measured between `checkpoint_taken` and `rung_recorded` on the log, with the
acceptance command never reached. It comes for free from the ladder's own shape — `Rung::Structural`
runs first, owns the empty diff, and a refusal breaks the walk — rather than from a tree check in
the driver, which would have been a second copy of that rule.

**F664** — 🚨 **The arm is only half scored, and the half that fired is the cheap half.** F655 exists
for the attempt that ran out of rounds *with work in the tree*; that happened 5 of 10 times in arms
1–5 and **0 of 4 here**, because both budget-exhausted attempts wrote nothing. The wiring is proven,
the cost is proven, **the rescue has still only ever been demonstrated retrospectively and by hand.**
⚠ Not evidence against the change: F655 acts after a phase ends and cannot influence what the model
does, and n = 4 against a base rate near a half is a handful of coin tosses.

**F665** — 🎉 **`a6689` is the best tree this subject has produced and it is two mechanical edits from
Green**: structural ✓, acceptance **550 of 550** ✓, veto ✓, refused by `cargo fmt --check` over **one
stray blank line** at `cli.rs:284`. Applying fmt exposes `clippy::match_same_arms` underneath. It is
also the third tree in a row to touch `main.rs`, so the version now reaches **stdout** as asked.

**F666** — 🚨 **The standard rung is a conjunction, so the *reported* blocker depends on which command
fails first.** `cargo fmt --check` then `cargo clippy --all-targets -- -D warnings`, cheapest first,
first refusal ends the rung. Arm 4 reported clippy, arm 7 reported fmt, **and both trees have both
faults.** ⚠ Quoting one run's headline as *the* blocker names the wrong one — the same error F657
caught a layer up. F658 now holds at **5 of 5 compiling trees tripping `match_same_arms`**, and no
attempt in seven arms has cleared the standard rung.

**F667** — ⚠ **The mutation harness was wrong before the code was, and reported a false survivor.**
`cargo test <name> -- --exact` matches the **full** test path, so a bare name filtered to zero tests,
exited 0, and read as a surviving mutation. The harness now requires `running 1 test` rather than
inferring from an exit code. ▶ Same shape as item 122: *a result over filtered data is a claim about
the filter first* — and a mutation harness that cannot tell *nothing ran* from *nothing failed* is
worth less than no harness, because it produces confident green.

---

## 7. What this leaves

▶ **Two decisions, both still David's, and neither moved by this session.** (1) Whether a gate-green
tree the model never declared finished may be `Accomplished` — F655 deliberately did not answer it
and a test holds the boundary. (2) The F649 trigger's width, where DEBUG-P4's F654 and F657 argue for
leaving it alone.

▶ **Seven tasks are in `AwaitingOrders` and this session accepted and rejected none**: `t4886`,
`t5221`, `t5430`, `t5683`, `t5871`, `t6207`, `t6530`. `a6689` (`t6530`) is the one to look at first —
one blank line and one match arm from Green, over 550 passing tests.

▶ **The next arm for F655, if it is flown, is a re-fly and nothing else** — the change needs an
attempt that exhausts its rounds with a changed tree, which the log says happens about half the time
and did not happen in four. ⚠ **Change nothing to chase it.** The same discipline that made arms 1–7
comparable is the only reason any of these numbers can be put beside each other.

⚠ **Still do not raise `rounds`.** It was the binding stop in 2 of 4 attempts here, and in both of
those the model had produced no tree at all — more rounds would have bought more refused
`apply_patch` calls, which is what F654 already measured.
