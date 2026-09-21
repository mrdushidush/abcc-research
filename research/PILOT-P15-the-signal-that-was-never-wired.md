# PILOT P15 — the one in-flight signal was never wired, and it is watching the wrong quantity

**Status: `SHELL-04` was driven as a real card, twice. Both attempts died in Localize without
producing anything to measure, the same way. Diagnosing them found that ADR-0010 §7's one
in-flight signal — `TraceSignal::OpenAt200` — is computed, logged, displayed, and acted on by
nothing; that the population F532 asked for now says wiring it would be wrong; and that the
failure which actually killed both attempts is detectable in flight by a different rule, which is
3 for 3 with zero false positives over 2,536 turns.**

David's instruction for this session was a card driven end to end, not more research on
`RUNTIME-11`. `SHELL-04` was verified solvable by hand first, the way the standing discipline
requires, then queued and flown.

Every number below is read from `abcc-1ae35b6091a63e2c/log.sqlite` and
`claudette-92490a1b1de94eca/log.sqlite`, or from the source at `b09bcdf`.

---

## 0. The card, and the reference solution that proved it solvable

`SHELL-04` [C] HIGH — *the 30 s timeout does not kill the process tree*.
`crates/claudette/src/test_runner.rs`, 180 lines. `child.kill()` is `TerminateProcess` on the
direct child alone; a grandchild survives holding the inherited stdout/stderr write ends, the pipe
never reaches EOF, and `join_reader`'s unbounded `handle.join()` blocks for the grandchild's whole
lifetime. The roast measured 45.4 s and 25.4 s returns on a 5 s budget.

✅ **Reproduced by hand before any GPU was spent: a 3 s budget returned after 60.07 s**, the exact
lifetime of the surviving grandchild. The reference solution — `taskkill /T /F /PID` on Windows,
`process_group(0)` plus a negated-PID `kill` on Unix, and a `recv_timeout` deadline on
`join_reader` — brings the same call to **3.26 s**, leaves **zero** leaked grandchildren, and
passes all three gate rungs: `cargo test` **1163 + 41 pass, 0 fail**, `cargo fmt --check` exit 0,
`cargo clippy --all-targets -- -D warnings` exit 0. 171 insertions, 22 deletions, one file.

🚨 **The constraint that decides the prompt: claudette has no `windows`, `winapi` or `libc`
dependency, and sets `unsafe_code = "forbid"`.** The card's own suggested fix — a Windows Job
Object — needs both. The dependency-free shape above is what the prompt named.

⚠ **A control worth recording, because a green would otherwise have meant nothing.** Both the old
and the new test reach a subprocess through `python` and **skip silently** if it is absent. abcc's
gate runs children under `env_clear()` plus `ENV_ALLOWLIST`. Under exactly that environment — the
20 names, nothing else — `python` resolves and reports `3.14.5` at exit 0. The skip guard cannot
fire inside the gate, so a green on this card would have been a real green.

## 1. The two attempts, turn by turn

**`t1339` / `a1347`** — one Localize phase, 5 turns, 356,974 ms:

| turn | prompt | completion | reasoning | r% | **text chars** | calls | finish | s |
|---|---|---|---|---|---|---|---|---|
| 1 | 2,119 | 183 | 148 | 81 | **0** | `read_file` | tool_calls | 3.8 |
| 2 | 3,886 | 2,945 | 2,933 | 100 | **0** | — | stop | 49.9 |
| 3 | 3,939 | 2,641 | 2,602 | 99 | **0** | `read_file` *(same file)* | tool_calls | 41.4 |
| 4 | 5,706 | 1,113 | 1,070 | 96 | **0** | `list_files` | tool_calls | 18.9 |
| 5 | 6,615 | **16,384** | **16,334** | **100** | **0** | — | **length** | **243.0** |

**`t1409` / `a1417`** — the same card, same gate, prompt re-queued as pure ASCII (§7), different
seeds. 4 turns, 517,796 ms:

| turn | prompt | completion | reasoning | r% | **text chars** | calls | finish | s |
|---|---|---|---|---|---|---|---|---|
| 1 | 2,100 | 165 | 130 | 79 | **0** | `read_file` | tool_calls | 3.3 |
| 2 | 3,867 | 1,390 | 1,325 | 95 | **0** | `read_file`, `list_files` | tool_calls | 23.1 |
| 3 | 6,782 | **16,328** | **16,296** | **100** | **0** | — | **stop** | **252.0** |
| 4 | 6,831 | **16,384** | **16,364** | **100** | **0** | — | **length** | **239.4** |

**`text_chars` is 0 on every one of the nine turns.** Across both attempts the model emitted
**57,533 completion tokens, 57,202 of them reasoning (99.4%)**, and not one character of the
artifact either phase existed to collect. Both ended
`Uncertain { why: TruncatedAtCap { budget: 16384 } }`, `change did not run — Localize produced no
artifact`, and the structural rung then refused honestly: *the attempt changed no file the
repository tracks*.

⚠ **Neither is a false red** — unlike the three manufactured reds of P13, the gate here reported
exactly what was true. ⚠ And the prompt was never large: the biggest in either attempt is 6,831
tokens against a 40,960 context, so `truncateMiddle` is not implicated. The cap that bit is the
**output** cap.

## 2. F811 — ADR-0010 §7's one in-flight signal feeds nothing

ADR-0010 §7 is one paragraph and makes three claims:

> **At token 200, has the reasoning trace closed?** If not, this turn is far likelier to end at the
> ceiling with nothing. 🚨 **It is a stop, not a score** — it feeds `Uncertain(OutputBudgetOverrun)`
> and `NextAction`, and it never becomes a number displayed next to an answer.

Read against the source, the last clause is the only one that holds.

* **`concern()` has exactly one caller**, `turn.rs:314`, and it is a max-reducer:
  `if concern(turn.trace) > concern(self.trace) { self.trace = turn.trace }`. It picks which signal
  the phase *reports*. It gates nothing.
* **`TruncatedAtCap` does not consult it.** `provider.rs:599` derives it from the finish reason
  alone: `if self.finish.is_uncertain() || matches!(self.finish, Finish::Length { .. })`. Delete
  `TraceSignal` entirely and both attempts end with the identical `Why`.
* **`NextAction` does not consult it either.** `NextAction` lives in `abcc-drive`, and
  `grep -rn "trace" crates/abcc-drive/src/` returns **nothing**. `TraceSignal` appears in
  `abcc-core` (the type and its replay label), `abcc-engine` (compute), `abcc-tui` and
  `abcc/src/replay.rs` (display). Compute, log, display. No decision anywhere.

▶ **The signal is an instrument that was built, read, and never connected.** Which is defensible —
ADR-0010 said so itself at Skeleton: *"it is recorded and not acted on ... stopping a generation on
this signal is a behavioural change that needs a population to justify it."* What is not
defensible is the ADR's own present-tense sentence *it feeds `Uncertain(OutputBudgetOverrun)` and
`NextAction`*, which describes code that has never existed.

## 3. F812 — and as written it could not be a stop, because it is computed after the turn is over

`fn trace(&self, completion_tokens: u32)` (`turn.rs:905`) reads `self.reasoning_open`, accumulator
state mutated as deltas arrive, and compares `completion_tokens >= 200`. It is called once, at
`turn.rs:780` — **after the drain loop has broken and the whole turn has streamed**:

```rust
let turn = Turn { trace: acc.trace(usage.completion_tokens), /* ... */ };
```

So the question the ADR poses *at token 200* is in fact asked **at end of turn**, and what it
actually measures is *was the last delta of this turn a reasoning delta, and did the turn exceed
200 completion tokens*. By the time the value exists, `a1417` turn 4's 239.4 seconds and 16,384
tokens are already spent.

⚠ **This is a fixable shape, not a deep one** — `reasoning_open` and a running completion count are
both live inside the drain loop, so the check could be evaluated per delta. §4 and §5 are why doing
so on *this* predicate would still be the wrong change; §8 is the predicate that works.

## 4. 🚨🚨 F813 — the population F532 asked for has arrived, and it points the other way

F532 is the finding that discharged ADR-0010's justification clause, on one event:

> **The population is 121 calls. `TraceSignal::OpenAt200` fired on exactly one of them, and that one
> is the only call of the 121 that did not answer.** ... At this sample the signal has **0 false
> positives in 120 good calls** and caught **1 of 1** failures. Acting on it would have saved 209 s
> and 16,384 tokens and cost nothing.

F532 wrote its own caveat — *"one event is one event"* — and it was right to. Both logs now hold
**272 phases** carrying a recorded trace signal. Asking of each phase *did **this** phase's last
model call finish at the ceiling*:

| trace at phase end | phases | ended at the ceiling | rate |
|---|---|---|---|
| `closed` | 211 | 23 | **10.9%** |
| `open_at200` | 61 | 4 | **6.6%** |

**Fisher exact two-sided p = 0.4657, and the direction is inverted**: phases the signal flags end
at the ceiling at *under two-thirds* the rate of phases it clears. A turn-level proxy over all
logged model calls points the other way — 4.2% vs 1.8% — but at **p = 0.0743** it is not
significant either, and it would stop 168 turns to catch 7.

🚨 **Had the stop been wired, it would have killed 57 healthy phases to catch 4.** F532's *0 false
positives in 120* is **57 false positives in 61** on this population. The recommendation that
follows is *do not wire this predicate*, and **F813 supersedes F532's policy conclusion**; F532's
raw observation of its own 121 calls stands.

⚠ **The populations are different workloads and that is part of the answer, not an excuse.** F532
counted Judge/review calls in the q56 corpus run; these 272 phases are agentic coding phases from
the two repositories abcc actually drives. The signal is now being asked to earn its place in the
workload abcc is judged on, and in that workload it does not separate.

## 5. F814 — why it cannot work: it is watching the wrong quantity

27 turns that ended `length` carry the `composition` field F511 added and can be decomposed. What
filled the budget:

| what consumed the cut turn | turns |
|---|---|
| **one tool call's arguments** (reasoning tiny and closed, `calls = 1`, 0 chars captured) | **23** |
| reasoning, at 100% | 4 |

**23 of 27 cap deaths are argument overruns with a small, closed trace** — F511's finding,
confirmed at the raised budget, with F515's signature on every one of them: `arg_c = 0`, because a
call cut mid-argument delivers no characters at all. Eighteen sit at exactly 16,384.

▶ **So `OpenAt200` is watching the reasoning trace while the budget is usually being eaten by
tool-call arguments.** That is the mechanism behind §4's null result: the predicate and the
dominant failure are about different quantities.

## 6. 🚨 F815 — the failure that killed both attempts, and the reason a `length` filter misses half of it

The right unit is a **barren turn**: a turn that spent real budget and emitted **no text and no
tool call at all**. Over 2,536 decomposable turns in both logs, at a ≥ 8,192-token floor, there are
**four**:

| log | seq | attempt | completion | reasoning | r% | finish |
|---|---|---|---|---|---|---|
| claudette | 230 | `a209` | 8,559 | 8,531 | 100% | **stop** |
| claudette | 1400 | `a1347` | 16,384 | 16,334 | 100% | length |
| claudette | 1459 | `a1417` | 16,328 | 16,296 | 100% | **stop** |
| claudette | 1485 | `a1417` | 16,384 | 16,364 | 100% | length |

Three things this says, none of which a `finish == length` filter can see:

1. 🚨 **Two of the four end `stop`, not `length`.** `a1417`'s turn 3 reasoned to **16,328 tokens,
   56 short of the cap, and ended cleanly having said nothing.** It is not a cap death by any
   counter abcc keeps, and it cost 252.0 seconds. **Any measurement of this failure mode keyed on
   `length` undercounts it by half.**
2. 🚨 **All four are in the claudette log. Zero in abcc's own ~2,300 turns.** The spiral appears on
   real coding cards from an external repository and not on abcc's own self-host tasks. ⚠ The
   occasion is *proved for this corpus and unmeasured for any other* — same discipline as the
   ENV_ALLOWLIST mechanism in P13.
3. ⚠ **It is rare overall and concentrated where it bites**: 4 turns in 2,536 is **0.16%**, but
   three of them are the two attempts on this one card, and together they are **734 seconds** of
   pure waste.

⚠ **This corrects the first draft of this section, which said "one turn in 2,735" from `a1347`
alone.** `a1417` had not run yet; it produced two more and the claim did not survive its own next
data point. The standing rule applied to itself.

## 7. F816 and F817 — two smaller things, both verified

* **F816 — the operator question counts wrong.** `t1339`'s `operator_prompted` reads *"This task
  has had **1** attempts, which is the whole budget"* and then offers *"A **third** attempt is
  worth buying only where..."*. The count and the ordinal disagree; the sentence was written for a
  two-attempt budget and is emitted after one.
* **F817 — a brief is recorded verbatim with no integrity check, and a damaged one left no
  witness.** `t1339`'s prompt reached the log with **9 mojibake sequences**: every `—` in it had
  become `â€"`. The cause was mine and is an operator trap, not an abcc defect — PowerShell 5.1's
  `Get-Content -Raw` reads a BOM-less UTF-8 file as the ANSI codepage. But **nothing anywhere in
  abcc noticed**, and the brief is the one input that decides everything downstream.
  ✅ **The control ran.** `t1409` re-queued the identical text as pure ASCII — 9 mojibake sequences
  to 0, verified in the log *before* the GPU was spent — and **died the same way, with two barren
  turns instead of one.** 🚨 **So the mojibake is not the cause, and was never claimed to be.** It
  was fixed because it is a defect, and the retry is what proves it was not the explanation.

## 8. ▶ What to do

1. 🚨 **Do not wire `OpenAt200` to a stop.** §4 and §5 are the population ADR-0010 asked for and
   they say no. Correct ADR-0010 §7's present tense — it feeds nothing — and note in `turn.rs`
   that the value is an end-of-turn measurement, not the in-flight question its name implies.
2. 🎉 **The predicate that IS supported, measured over the same 2,536 turns.** *At N reasoning
   tokens with no text delta and no tool-call delta yet seen, stop the turn:*

   | N | turns reaching N | barren (caught) | productive (killed) | precision |
   |---|---|---|---|---|
   | 8,192 | 9 | 4 | 5 | 44.4% |
   | **12,288** | **3** | **3** | **0** | **100%** |

   At **12,288** it is **3 for 3 with zero false positives in 2,536 turns**, and would have saved
   **734 seconds** across the two `SHELL-04` attempts. ⚠ **State the margin honestly: the nearest
   productive turn reached 10,486 reasoning tokens**, so the gap is 1,802 tokens — clean on this
   population, but thin, and n = 3 on the catch side. It is also the shape ADR-0010 §7 always
   wanted, keyed on the quantity that is actually running away.
   ⚠ It would NOT have caught `a209`'s barren turn at 8,531, and it does nothing about the 23
   argument overruns of §5, which remain the larger population.
3. ⏸ **Leave the 16,384 budget alone.** The reasoning overrun is 0.16% of turns; F511's argument
   overrun is 23 of 27 cap deaths. Raising the cap feeds the spiral and does not touch the
   dominant failure.
4. ⏸ **`SHELL-04` itself is unresolved after two attempts** and its disposition is David's. The
   card is real, the defect is real, and the reference solution in §0 is proof it is solvable —
   what has not been shown is that this model can localize it. ▶ **A smaller card is the better
   next measurement**, since both attempts died before writing a line: the three-part fix may
   simply be too much to hold. `SHELL-06` (`tools/semantic.rs`, 427 lines, `ignore` already a
   dependency) is one change, not three.

## 9. Housekeeping

* `abcc` unchanged at `b09bcdf` throughout. `claudette` at `007b84f`, clean; the reference solution
  was reverted with `git checkout --` after the gate ran over it and is saved outside the repo.
* Model `qwen3.6-35b-a3b-mtp@iq3_s`, `-c 40960`, `--parallel 1`, `max_tokens 16384`, seeds recorded
  per call (F715's fix is live: `a1347`'s five calls carry five distinct seeds).
* 🚨 **The six P14 measurement rows are untouched and must stay that way** — `t839 t840 t988 t1068
  t1069 t1070` still read `abcc land` and must never be landed (F810).
* `t1339` and `t1409` are both `INTERVENTION REQUIRED`; disposition is David's, and `reject` has no
  `--by` (F795). Neither wrote a file, so neither has anything to land.

Findings **F811–F817**; next free is **F818**.
