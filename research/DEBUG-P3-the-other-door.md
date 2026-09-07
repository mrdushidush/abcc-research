# DEBUG P3 — the other door, and a trigger narrower than the failure it exists for

**Status: the change is shipped and the arm was flown, and the arm DID NOT FIRE. `write_file` is
named in `apply_patch`'s markup refusal (`abcc` `e5625a8`), and a sortie on the same subject with a
byte-identical prompt never satisfied the condition that offers it — because the offer is gated on a
*second consecutive markup refusal*, and the model's second edit call was a clean diff refused for a
different reason. So this run does not score the change. What it does settle is that F648's 100%
was a property of that run and not of the subject: markup went 5 of 5 to 1 of 2.** Findings
**F649–F653**; next free number is **F654**. Built 2026-09-07 against `D:\dev\abcc` at `f2434d5`,
shipped as **`e5625a8`**. **544 tests passing (up from 541), 19 ignored, clippy clean under
`-D warnings`, `cargo fmt --all --check` clean.** Three tests are new and **five mutations were run
against them one at a time**.

▶ Follow-on to `CONSOLE-P10-the-way-back-out-of-holding.md` §13, which flew F637's refusal on a real
subject, watched it fail five times out of five, and named the next move without taking it: *name
`write_file` in that refusal — a one-line change to a string, and it wants an arm, not a commit.*
This is that arm, and the arm came back **unscored**, which is a different answer from *no effect*
and has to be reported as one.

**The session's shape: the cheap change was cheap and correct, and flying it cost eight minutes and
answered a question nobody had asked. The question it answered — does the fold reproduce? — is
worth more than the one it was built for.**

---

## 1. What shipped: 155 characters

`PatchError::NotADiff` is the refusal F637 added — the one that fires when an `apply_patch`
argument carries the model's own tool-call markup, which F641 established is the **server's** parser
folding a multi-call turn into one call's arguments. It said this, and only this:

> `apply_patch:` the diff argument contains tool-call markup (`"<tool_call>"` at line 141), so it is
> a transcript and not a diff. Send one call, whose `diff` is only the unified diff text: no
> `<tool_call>` wrappers, no commentary, and nothing after the last hunk.

It now ends with one more sentence:

> …and nothing after the last hunk. **If the next `apply_patch` is refused this way too, stop
> patching and use `write_file` instead: one call, `path`, and the file's whole new text in
> `content`.**

414 characters where there were 259 — about 100 tokens in the transcript, once per refusal. That is
the entire change to the running system. Everything else here is either the evidence that picked
those words or the measurement of what they did.

---

## 2. Why `write_file`, and why on the second refusal

**The tool was chosen from the log, not from taste.** Two numbers, both from the census in
`abcc-2-apply-patch-is-the-bottleneck` over the whole event log:

| | refused | of | rate |
|---|---|---|---|
| `apply_patch` | 51 | 66 | **77%** |
| `write_file` | 1 | 17 | **6%** |

And one case that matters more than either rate: **the single `Accomplished` in this project's
entire history reached it by falling back to `write_file` after `apply_patch` had failed twice.**
That is not a large sample. It is, however, the only path to a finished task this system has ever
walked, and the message as shipped offered the model no way onto it — every sentence in it was
advice about writing a better diff.

**The refusal was never wrong. It was correctly aimed at the wrong actor.** F641 put the fold in the
server's parser, before abcc sees anything, so *send one clean call* asks the model to stop doing
something it may not be doing. F648 measured the price: five refusals, two attempts, 48 rounds,
1,280,734 input tokens, no artifact. **A correct refusal aimed at an actor who cannot act on it is a
loop with a receipt.**

### Why the second refusal and not the first — and this is the decision the sortie went after

* **It is the shape the one success actually had.** It fell back after *two* failures.
* **A first refusal can be an honest mistake.** This repository's own notes quote `<tool_call>` in
  prose; a payload that genuinely is a transcript over a diff is the model's error, and the advice
  already there fixes it.
* **`apply_patch` is the better tool when it arrives intact** — bounded by the hunk rather than the
  file, and 15 of 66 calls did work.

⚠ **This is a prompt, and the `tools` module's own docs say what a prompt is worth: it binds only as
far as the model complies** — 39 of 50 for the shipped wrapper, 0 of 50 for the best re-aimed one.
Which is why it was flown rather than merely shipped. **§5 is what happened to that reasoning.**

---

## 3. Three tests, and F647's rule one layer down

F647's rule, from the session before this one: **when you add a fold, mutate the wire, not just the
fold and its consumer.** Here there is no fold — there is a *sentence*, and a sentence has a wire
too. It has to arrive in the body the next round is sent, or it is a string that changes nothing.

**`tests/patch.rs` — `the_refusal_the_model_reads_offers_write_file_as_the_way_out`.**
It asserts `result.text`. The F637 test beside it asserts `unmeasured.detail` — which is what the
**log** keeps. `Message::tool_result` is built from `text`. A sentence that reached the record and
not the transcript would pass the older test and change nothing about the run, so this one also
asserts the two are the same string, which is `refused`'s deliberate clone. ⚠ The fixture contains
neither `write_file` nor `content`, asserted before the call, because F632's three tautologies came
from a fixture that already carried what the test looked for.

**`tests/policy.rs` — `every_ceiling_that_admits_apply_patch_admits_the_tool_its_refusal_names`.**
The offer's precondition. A refusal that recommends a tool the role cannot call is *worse* than the
one it replaces: the model spends a round being denied, and the denial is the engine's fault rather
than its own. Nothing in the message can know which ceiling it will be read under, so the registry
has to make it true everywhere — which it does structurally, because both entries are `Reach::Edits`
and a tier comparison cannot separate them. The test renders the real `PatchError` and asserts the
recommendation is still in it, so the two halves cannot drift apart; and it asserts that *some*
ceiling admits `apply_patch`, because a loop over an empty set proves nothing.

**`tests/turn_loop.rs` — `a_folded_apply_patch_puts_write_file_in_the_model_s_own_transcript`.**
The wire. A scripted `apply_patch` carrying a folded payload, run through the **real** `Workspace`
rather than the `Recorder` every other test in that file uses, with the assertion in `body`.

⚠ **The first version of that test's comment was wrong, and the correction is the useful part.** It
claimed the last hop was uncovered. Blanking the tool result at `turn.rs` and running the *whole*
suite fails **two** tests: this one and `http.rs`'s
`the_second_request_carries_the_assistant_turn_that_asked_for_the_tool`. So the hop had a test. What
had no test was the **join**: that hop carries a stub's fixed string across the HTTP seam and never
enters `patch.rs`, and `patch.rs`'s own tests stop at the `ToolResult`. Nothing ran a folded payload
through the real tool layer and looked in the body.

🚨 **A small finding with wide reach: `cargo test --workspace` stops after the first failing test
binary.** The first run of that check reported one catching test and hid the other. **`--no-fail-fast`
is mandatory for any claim of the form *what else covers this?*** — and this project makes that kind
of claim often.

---

## 4. Five mutations, one at a time

| # | mutation | caught by |
|---|---|---|
| 1 | drop `write_file` from the message | all three new tests |
| 2 | offer it on the *first* refusal instead of the second | `patch.rs` |
| 3 | lift `write_file` out of `Reach::Edits` | `policy.rs` (+ the pre-existing donor-defect test) |
| 4 | let the refusal reach the log but not the transcript | `patch.rs`, `turn_loop.rs` |
| 5 | blank the tool result at `turn.rs` | `turn_loop.rs` (+ `http.rs`'s seam test) |

None survived. ⚠ **Mutations 4 and 5 are the point** — they are the wire, and under mutation 5 the
old F637 test passes happily while the model reads nothing at all.

⚠ **The mutation harness itself had to be corrected mid-run.** It classified a run as *did not
compile* whenever the output contained `error: `, and `cargo test`'s own failure line is `error: test
failed`. The first pass therefore reported five compile failures and zero caught mutations. **A
guard written against one failure reported another, and its own output was plausible** — the same
shape as every instrument in this project.

---

## 5. The sortie: `t5221` against `t4886`

Flown 2026-09-07 on `qwen3.6-35b-a3b-mtp@iq3_s` at ctx 40960, `--parallel 1`, model confirmed
exactly, pulse 130 ms before the attempt. Two attempts, one slot at exec, the fleet's own retry —
the same shape as F648. **The prompt was asserted byte-identical to `t4886`'s before flying: 329
characters, compared programmatically rather than by eye.** The only deliberate difference between
the two runs is the 155 characters of §1; the incidental one is that the tree carries this session's
own commit.

### What the two arms did

| | arm 1 `t4886` (`5f6ee08`) | arm 2 `t5221` (`e5625a8`) |
|---|---|---|
| `apply_patch` calls that ran | **5** | **2** |
| …refused for tool-call markup | **5 (100%)** | **1 (50%)** |
| …refused for a genuine `NoMatch` | 0 | **1** |
| …discarded at the 16 384 cap, never run | 0 | **1** |
| **`write_file` calls** | **0** | **0** |
| `bash` calls | 20 | 9 |
| tree changed by the attempt | **+3 lines / +6 lines** | **nothing, either attempt** |
| endings | `BudgetExhausted{24 rounds}` ×2 | `TruncatedAtCap{16384}`, `SaidNothing{Builders}` |
| change-phase turns (of 24) | 24, 24 | **2, 14** |
| input tokens | 1,280,734 | **326,007** |
| gate asked | no | no |
| wall clock | 8.0 min | 7.8 min |

### The sequence that decides it

`a5300`'s change phase, in order — four reads, then:

| # | seq | tool | outcome |
|---|---|---|---|
| 5 | 5366 | `apply_patch` | **refused: tool-call markup at line 64** — the new sentence is shown |
| 6–7 | | `read_file` ×2 | |
| 8 | 5378 | `apply_patch` | **refused: `NoMatch`** — *3 of its 4 context lines match* |
| 9 | | `read_file` | |
| 10–18 | | `bash` ×9 | 4 non-zero |
| 19 | | `read_file` | then nudged twice, and the phase ended saying nothing |

**The condition was never met.** The message offers `write_file` *if the next `apply_patch` is
refused this way too*. The next one was refused a different way — it was a clean, well-formed
unified diff whose context was one line stale — so by the message's own terms the offer did not
apply, and the model never had a qualifying moment.

The first payload is F641's signature exactly, and worth seeing whole: 67 lines, of which 1–63 are a
real four-file diff and 64–67 are the literal opening of a **second call**:

```
    62| -        }
    63|
    64| <tool_call>
    65| <function=read_file>
    66| <parameter=path>
    67| crates/abcc/src/cli.rs
```

### ⚠ Instruments, and two readings that were wrong before they were right

Both were caught by the standing rule — **validate a new instrument on a solved case first** — and
both would have produced a confident, plausible, wrong sentence in this document.

* The log reader reported **zero tool calls** for `t4886`, an attempt that made 42. `tool_call_ended`
  carries `attempt` and a **NULL `task`**, so a query keyed on the task returns the lifecycle and
  none of the work. Fixed, it reproduces F648's table to the digit.
* Attempt durations came out at **0.2 s**. `attempt.started` / `attempt.ended` are **seq numbers,
  not milliseconds**. Recomputed from `event.at_ms`, `a4893` is 282.0 s against the replay view's
  *4 m 42 s* — agreement, and only then quotable.

---

## 6. Findings

**F649** — The `apply_patch` markup refusal now names `write_file` as the way out, conditional on a
second refusal of the same kind. Chosen from the log rather than from taste: `write_file` is refused
1 of 17 against `apply_patch`'s 51 of 66, and the only `Accomplished` this project has ever recorded
reached it by falling back to `write_file` after `apply_patch` failed twice. Three tests, five
mutations, none survived; `tests/policy.rs` holds the precondition that no ceiling may admit
`apply_patch` and deny `write_file`.

**F650** — 🚨🚨 **The arm did not fire, so it is unscored, and the reason is the trigger I chose.**
The offer is gated on *the next `apply_patch` refused this way too* — the same fold twice running.
Across two attempts the model made two edit calls that reached the tool layer, and they failed
**differently**: one folded payload, one genuine `NoMatch` three context lines of four from
matching. A trigger that requires a repeat of one failure cannot fire in a run that produces two
different ones. **The failure this exists for is *the model cannot land an edit*; the condition
written into the string is *the server folded twice in a row*, which is narrower.** ⚠ The evidence
does not say the wider trigger is better — the second refusal was aimed at a nearly-correct diff,
which is exactly where F638's message earns its keep and where abandoning to `write_file` would
throw away good work.

**F651** — 🚨 **F648's 100% did not reproduce: markup went 5 of 5 to 1 of 2 on a byte-identical
prompt.** Same subject, same model, same settings, one commit apart. So *the fold reproduces at 100%
on the E0004 subject* described **that run**, not the subject — and the whole-log 77% remains the
only rate with a population behind it. ⚠ Both arms are n=1; this is a caution against the earlier
number, not a new one.

**F652** — **Four attempts across the two arms produced four endings and only two of them are the
same.** `BudgetExhausted{24 rounds}` twice in arm 1; `TruncatedAtCap{16384}` and
`SaidNothing{Builders, 2538 out, 2528 of it reasoning}` in arm 2. **`rounds: 24` was not the
constraint this time** — `a5300` ended at turn 14 of 24 — so CONSOLE-P10's *rounds is now a live
constraint* was one run old when it was written. ⚠ `a5228` lost its change phase to F515's total
loss: an `apply_patch` **discarded at 0 argument characters**, cut before a single character
arrived, with 85% of the turn's output being reasoning trace.

**F653** — ⚠ **Neither arm ever called `write_file`, and the only fallback either model reached for
was `bash`** — 20 calls in arm 1, 9 in arm 2. In arm 1 that fallback moved the tree (`+3` and `+6`
lines): `a5077` landed the `CliError::Version` variant, the `parse` branch and the `lib.rs` exit
code. ⚠ **Neither arm-1 tree is finished work, and reading the checkpoints says why**: `a4893`'s
variant carries `#[error("abcc {env!("CARGO_PKG_VERSION")}")]`, whose unescaped quotes end the
string literal, so that tree does not compile; and `a5077` never touched `main.rs`, whose match ends
in a catch-all `Err(e)` arm — so it compiles, and `--version` would print to **stderr** down the
error path rather than to stdout as asked. ⚠ **This is not E0004**, which came from the earlier
`4735` run; nothing here reproduced it. **In arm 2 the tree was byte-identical at both checkpoints:
nine `bash` calls and nothing written.** So on the one axis
where arm 1 produced something, arm 2 produced less. ⚠ **This is not evidence against the message.**
The attempts died of different causes and the offer was never triggered; a run that ends at the
token cap in its second change turn cannot be compared to one that spends 24.

---

## 7. What this leaves

▶ **The change stays.** It is correct, it is tested at the wire, its precondition is guarded, and it
costs ~100 tokens per refusal. Nothing measured argues for reverting it.

▶ **It has not been shown to work, and one more sortie will not settle it either.** Firing the
trigger needs a run where the server folds twice in a row. That happened in both of F648's attempts
and in neither of these — a base rate somewhere around half, so a single extra sortie is a coin
toss. **Three or four runs of the same subject would give the offer a real chance to fire**, at ~8
minutes each.

▶ **The trigger's width is a decision, not a measurement, and it is David's.** Three shapes:

1. **As shipped** — two consecutive markup refusals. Truest to the one success; fires rarely.
2. **Two refusals of any kind** — would have fired at seq 5378 in this run. ⚠ But it would have
   pointed the model away from a diff that was three context lines of four from applying.
3. **Unconditional** — name `write_file` on every markup refusal. Fires always; abandons
   `apply_patch` on a first offence that may be the model's own and is fixable.

⚠ **Whichever is chosen, it is another unmeasured prompt change, and F625's verdict applies: shipping
one is what this project keeps deciding not to do.** The honest cost of settling it is GPU time, not
thought.

▶ **And a bigger thing this run says out loud: `apply_patch` is not the only lossy path.** Arm 2
lost one edit to the fold, one to a stale context line, and a whole change phase to the token cap
before a single argument character arrived. **Three different failures, three different mechanisms,
one shared outcome — no artifact, gate never asked.** The bottleneck memo's headline (*every tool
works except the one by which work lands*) is still true, but the tail is longer than one tool.
