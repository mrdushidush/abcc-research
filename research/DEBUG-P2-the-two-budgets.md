# DEBUG P2 — the two budgets, and the tool that fails three times in four

**Status: three fixes shipped and two sorties measured them. F625 is repaired and F592's streaming
third with it (`abcc` `9166537`); then the re-baseline found something larger and F637/F638 repaired
that (`abcc` `95f466a`). The headline: with the timeout out of the way, the binding constraint on
this system is one tool — `apply_patch`, refused 82% of the time in August and 47% by the end of
the night, while every other tool runs at 0–6%.** Findings **F633–F640**; next free is **F641**. Built 2026-09-06 against `D:\dev\abcc` at `a03bdcd`. **513 tests
passing (up from 504), 16 ignored, clippy clean under `-D warnings`, `cargo fmt --all --check`
clean.** Nine tests are new and **seven mutations were run against them one at a time**.

▶ Follow-on to `DEBUG-P1-the-buffered-argument.md`, which found the mechanism and left the repair to
David as three shapes. **Shape 1 shipped** — the narrow one, which uses a signal already on the wire.

**The session's shape, and it is the same shape three times: every number here was wrong on its
first derivation, and each was corrected by a second measurement rather than by more thinking.** The
gap's bound was wrong until a second wire capture contradicted the first by 2.6×. The near-miss rate
was wrong because the parser counted a phantom line. And the whole *story* was wrong — "the model is
one character out" — until one failing payload was read whole and turned out not to be a diff at
all. **The finding that survives is that `apply_patch` has been refused 77% of the time for the life
of this project, and 70% of those refusals are payloads carrying the model's own `<tool_call>`
markup.**

---

## 1. What was wrong, in one paragraph

LM Studio buffers a tool call's arguments whole and delivers them in a single delta at the end
(F622). Between the announcement and the call, a **perfectly healthy stream carries nothing**. The
per-read budget — 90 s, `Limits::idle_gap` — was spent against that silence, so it was not detecting
a hang. **It was capping how large a patch abcc could write**, which is why the largest patch ever
seen intact, 17,157 characters, sat inside the band 90 s buys at the measured argument rate.

## 2. What shipped

* **`Delta::ToolCallOpened { tool }`** — the announcement, carried on the wire all along and
  discarded by `openai.rs`. It is a `tool_calls` fragment with an `id`, a `type`, the function's
  **name**, and `arguments: ""`.
* **`Limits::tool_call_gap`, 480 s** — the per-read budget while a call is announced and has
  produced no bytes. §4 derives it.
* **`Delta::Waiting { silent_ms }`** and the sliced wait — F592's streaming third, which had to come
  in the same change: a wider gap with no marks inside it is worse than what we had.
* Five tests in `crates/abcc-engine/tests/http.rs`, one `#[ignore]`d and live.

### 🚨 The state is *announced and not one byte since*, and the first version got it wrong

The first implementation counted `ToolCallOpened` against `Delta::ToolCall`. That is wrong in a way
**no test written first could see**: `Delta::ToolCall` is emitted by `flush_calls` at
`finish_reason`, not when the arguments land — so the wide budget stayed open **from the first
announcement to the end of the turn**. On this stack the two are 4 ms apart and nothing would ever
have shown it; on a stream that did anything after a call, a dead socket would have waited eight
minutes instead of ninety seconds.

▶ **Found by writing the mutation test and watching it fail on unmutated code.** The state that
matters is *announced, and not one byte since*: set by the announcement, cleared by the first
`ToolCallProgress`, and a `bool`, because a server announces and writes one call at a time.

---

## 3. 🚨 F633 — the announcement is on the wire, carries the tool's name, and the gap it opens is *true* silence

Read out of `research/spikes/f606-sse/` and `research/spikes/f625-gap/` at no GPU cost:

| capture | announced | delivered | chars |
|---|---|---|---|
| `complete_small` | 5,546 ms | 6,243 ms | 231 |
| `bigarg` (F622) | 15,171 ms | 226,377 ms | 33,962 |
| `cap8192` (F623) | 54,743 ms | **never** | — |
| `fullbudget` (tonight) | 39,338 ms | 89,257 ms | 21,112 |

Every announcement carries `name` with a zero-length argument string; every delivery carries the
whole argument with **no** `name` and **no** `id`.

🚨 **The gap is TRUE silence, and that had to be checked rather than assumed.** An
announcement-to-call gap would mean nothing if the reasoning trace were still streaming inside it —
the socket would be busy and the idle gap would never fire.

| capture | the gap | next largest gap in the whole stream |
|---|---|---|
| `bigarg` | **211,206 ms** | 80 ms |
| `fullbudget` | **49,919 ms** | 109 ms |

The trace has finished by the time the call opens. The socket really does go silent, and the number
the budget is spent against really is the whole of it.

---

## 4. 🚨 F634 — the bound is derived from two captures, and one capture would have got it wrong by 2.6×

The bound answers *how long can a tool call legitimately take?* — `budget ÷ argument rate`, and the
rate is the part that must be measured.

| capture | chars | true silence | **chars/s** |
|---|---|---|---|
| `bigarg` | 33,962 | 211.2 s | **160.8** |
| `fullbudget` | 21,112 | 49.9 s | **422.9** |

**A 2.6× spread between two runs of the same prompt, same model, same box.** Derived from tonight's
capture alone the bound would have been 149 s for a full-budget call — a number that kills a
`bigarg`-rate call at half its length, which is the same defect one layer up.

The bound takes the **slower** rate. `Head::budget` is 16,384 tokens and the measured argument
density is **3.84 chars/token**, so a full-budget call is ~62,900 characters; at 160.8 chars/s that
is **391 s**. **480 s** covers it with 23% margin.

### ⚠ Why it must cover the whole budget, and what that costs

An earlier draft used 300 s, justified as *clearing the working range*. **That is the defect
restated, not repaired**: any value below the full-budget time leaves a second, tighter stop hidden
inside the transport and merely moves the ceiling. The budget is already the stop.

**The price: a server that dies *during* a tool call now takes eight minutes to detect instead of
ninety seconds.** Survivable only because the silence is no longer unobserved (§5). ▶ **Tightening
it is David's, against a re-measured argument rate rather than a feeling about eight minutes.**

---

## 5. 🚨 F635 — F592's streaming third had to be fixed in the same change, or the fix makes things worse

`TurnLoop::drain` checks its liveness clock at the top of a loop whose next statement blocked in
`recv_timeout` for the whole budget. **A silence detector that rides the data path cannot observe
silence.** At 90 s that already cost 25 unmarked `model_call_started → liveness_mark` gaps of up to
73 s. At 480 s it would be eight minutes of a screen saying nothing.

The repair touches neither budget: the wait is taken in `liveness_gap` slices, and an expired slice
returns `Delta::Waiting` rather than an error. **The clock the budget is spent against lives on the
stream and survives the slices**, which is the whole correctness of it.

> ⚠ **The near-miss.** The first version restarted that clock on every `next_delta` call, so every
> `Waiting` return would have reset it and the gap would silently have become the *slice* — no
> stream would ever have timed out again. Caught by reading; the mutation now pins it, and with the
> clock restarted **six tests fail**, including all three inherited idle-gap tests.

In the field on the first attempt of the sortie, marks that could not previously exist:

```
recon    writing a tool call: read_file
builders writing a tool call: apply_patch
```

**Two sentences instead of one, because a mark that says *0 chars of everything* during a buffered
tool call is indistinguishable from a dead socket.**

### The four mutations

| mutation | tests that failed |
|---|---|
| the second budget removed (revert F625) | `the_silence_while_a_tool_call_is_written_is_not_a_hang`, `a_tool_call_that_outlasts_its_own_budget_is_still_a_hang` |
| the announcement never emitted | the same two |
| the silence clock restarted every slice | **six**, including all three inherited idle-gap tests |
| `awaiting_call` never cleared | `the_wider_budget_stops_applying_once_the_call_has_arrived` |

⚠ The fourth test did not exist until the fourth mutation went uncaught, and writing it exposed the
`flush_calls` defect in §2. **A mutation nothing catches is a test you have not written yet.**

---

## 6. 🎉 Live against the champion: the old record was a measurement of the timeout

`a_live_turn_writing_a_large_tool_call_survives_its_own_silence`, `#[ignore]`d, driving the real
server through the fixed code with `ssecapture.py`'s big-argument prompt:

| run | announced | arrived | chars | silence | `Waiting` deltas |
|---|---|---|---|---|---|
| 1 | 41.7 s | 106.5 s | **23,497** | 64.8 s | 6 |
| 2 | 72.9 s | 139.6 s | **24,831** | 66.6 s | 6 |

**24,831 characters is 45% past the 17,157-char "largest this stack has delivered intact"** that
`Head::budget` reasons from — exactly as F625 predicted, because 17,157 sat inside the band a 90 s
gap buys.

⚠ **Two honest caveats.** Neither run's silence exceeded 90 s, so neither *proves* a call the old
code would have killed; that proof is `bigarg`'s 211.2 s, measured before the fix existed. And the
model chose **`write_file`**, not `apply_patch` — correctly, since the task creates a file and the
Builders head offers both. `ssecapture.py` only ever offered `apply_patch`, so this is the first time
the real tool set has faced that prompt. **That choice turns out to matter enormously — see §8.**

---

## 7. 🚨🚨 F636 — every tool in this system works except the one by which work lands

With the timeout out of the way, the first re-baseline attempt ended
`Uncertain { BudgetExhausted { "24 rounds" } }` after 7 minutes, having made **10 `apply_patch`
calls of which 7 were refused**. **Not one round was lost to a timeout.**

Every `tool_call_ended` on this log — all 29 tasks, both populations, five weeks apart:

| tool | applied | refused | **fail rate** |
|---|---|---|---|
| **`apply_patch`** | 15 | **51** | **77%** |
| `write_file` | 16 | 1 | 6% |
| `read_file` | 330 | 1 | 0% |
| `bash` | 69 | 0 | 0% |
| `list_files` · `search` | 74 | 2 | 2–3% |
| `diagnostics` · `run_tests` · `git` | 13 | 0 | 0% |

In the August population alone, 41 of 50 `apply_patch` calls were refused, every one
`FailedBeforeRunning`. **This is the binding constraint on the whole system, and it was invisible
behind a headline about truncation.**

---

## 8. 🚨🚨 F637 — 70% of the refused payloads are not diffs at all: they carry the model's own tool-call markup

F505 keeps a refused call's arguments on the log, so all 46 recoverable payloads can be read back.
Classified by whether the `diff` string contains `<tool_call>`, `<function=` or `<parameter=`:

| what the `diff` argument actually contained | payloads |
|---|---|
| **literal tool-call markup** | **32 (70%)** |
| a clean diff that genuinely mismatched | 14 (30%) |

One payload, abridged — this is a single `diff` argument:

```
@@ -16,6 +16,9 @@ fn main() -> ExitCode {
     match abcc::main_with(std::env::args().skip(1), &mut out) {
+        Err(AppError::Cli(cli::CliError::Version(ref v))) => {
...
"
Wait, that last patch block is broken. Let me redo this properly with three clean patches.

<tool_call>
<function=apply_patch>
<parameter=diff>
--- a/crates/abcc/src/cli.rs
...
That's still garbled from my thinking. Let me just do clean patches one at a time.

<tool_call>
<function=apply_patch>
...
I apologize for the confusion in my tool calls.
```

**Four attempted calls and the prose between them, concatenated into one argument.**

### 🚨 It is not degradation after a failure. It is there from the first call.

| | attempts |
|---|---|
| attempts that called `apply_patch` | 20 |
| attempts where markup appeared at all | 14 |
| **markup on the very first `apply_patch` call** | **14** |
| first call clean, markup only later | **0** |

**Fourteen of fourteen.** So this is not the model falling apart after being refused — it arrives
broken, and the refusals that follow are the consequence rather than the cause.

### ▶ What follows, and what does not

* **abcc can refuse this immediately and say what is wrong.** A `diff` containing `<tool_call>` is
  not a diff. Today `Patch::parse` accepts it — it finds real headers and hunks near the top — and
  fails several hunks later with a message about line numbers, which is the worst of both.
* ⚠ **The cause is not established and must not be written down as if it were.** The payload has the
  shape of *several tool calls concatenated*, which is consistent with the model emitting several
  `<tool_call>` blocks in one turn and the server's parser taking the first function name and
  everything after it as the argument. **That is a hypothesis about LM Studio's tool-call parser, and
  it is testable exactly the way F622 was** — a raw SSE capture of a turn that emits more than one
  call. It costs minutes and it has not been done.
* ⚠ **`write_file` fails 6% on comparably large string arguments**, so "the argument is big" does not
  explain it.

---

## 9. 🚨 F638 — the clean 30%, where the model is one character out

The 14 payloads that *are* diffs fail a different way. `research/tools/patchmiss.py` replays each
against the file and finds where the context comes closest:

```
crates/abcc/src/cli.rs, hunk 1: 5 of 6 context lines match at line 186
  model: ' everywhere:'
  file : ' Everywhere:'
```

Another, from August: the model wrote `return Err(CliError::Help");` where the file has
`return Err(CliError::Help);` — one stray quote.

🚨 **And the message sends the model to fix the wrong thing.** `PatchError::NoMatch` reads *"hunk 1
claims line 187 and its context is nowhere in the file"*. The observed response, three times in one
attempt: **the model changed the line number — 195, then 196, then 187.** But `patch.rs` treats the
hunk header as a **hint**; `locate` searches the whole file. **The claimed line is the one part of a
hunk that cannot cause this failure**, and the message names it first.

▶ **The repair is to say what the file actually has** — the position where the context came closest,
how much of it matched, and the file's own text at the first line that differs. ⚠ **A change to the
diagnosis, not to the matching**: application stays exact, because the module's refusal to match
loosely is right and *what it hides is a patch applied in the wrong place*.

---

## 10. ⚠ F639 — the instrument produced a confident wrong finding twice, and both times the fix was to look at one case whole

This section is here because the numbers above were nearly published in a different and wrong form.

1. **First pass.** `patchmiss.py` reported *"the model wrote a blank line"* as **64% of all
   single-line misses**, 85 hunks. That was the tool: `split("\n")` on a diff ending in a newline
   yields a trailing empty string, which was collected as a context line, so **the last hunk of every
   diff carried a phantom blank line**. The tell was in the data — **82 of the 85 sat at the last
   line of their hunk.** Fixed by honouring the `@@` header's old-file count, which is authoritative,
   and validated on three hand-written diffs including one with a genuine blank context line.
2. **Second pass.** With the parser fixed, the answer became *54% of failing hunks are one line
   wrong* — a clean, quotable, **still misleading** number, because it was computed over payloads
   that were never diffs. Only reading one failing hunk *and the raw argument around it* showed the
   `<tool_call>` markup. **The aggregate was consistent, reproducible, and about the wrong
   population.**

▶ **Both times the aggregate looked fine and the single case did not.** The rule this pays for
again: *a summary statistic over parsed data is a claim about the parser first and the world second.*

---

## 11. 🚨 The re-baseline: F625 removed a whole failure class and did not raise the success rate

Five prompts, run verbatim against the real log. **All five were the August population's own tasks
and all five were still undone**, so this is like-for-like rather than a new experiment.

| | August (2026-08-29/30) | tonight (2026-09-06) |
|---|---|---|
| attempts ended | 30 | 7 |
| `success` | 2 (6.7%) | 2 (28.6%) |
| `truncated_at_cap` | 8 | 2 |
| `budget_exhausted` | 4 | 2 |
| `said_nothing` | 6 | 0 |
| `no_checker_for_artifact` | 4 | 0 |
| `engine_error` (HTTP 500) | 2 | 0 |
| **`timeout`** | **2** | **0** |
| `context_overflow` | 1 | 0 |
| `refused` | 1 | 1 |
| p50 attempt wall clock | 175 s | **340 s** |
| `rung_recorded` (the gate ran) | 12 | 12 |
| marks naming a tool call (F625) | **0** | **58** |
| marks reporting quiet (F592) | **0** | **46** |

⚠ **The two success rates are not comparable and must not be quoted against each other.** The
August population is **one task repeated 25 times** plus four others; tonight's is five distinct
tasks with retries. The honest comparison is per task:

| task | August | tonight |
|---|---|---|
| `Seq::back saturating` | 0/1 | **1/1** |
| `Seq::is_origin` | 1/1 | 1/1 |
| `abcc --version` | **0/25** | 0/2 |
| `abcc breaker --depth` | 0/2 | 0/2 |
| `budget::retries()` | **1/1** | 0/1 |

### What actually moved

* 🎉 **The timeout class is gone: 2 → 0**, and `said_nothing`, `engine_error` and `context_overflow`
  did not recur. F625 and the raised budget did what they were built to do.
* 🎉 **F592's marks exist for the first time: 0 → 58 and 0 → 46.** They could not have existed
  before — the mark was written from inside a loop that blocked for the whole gap — so this is a
  *by construction* zero turning into a measurement, not a rate improving.
* 🚨 **The success rate did not clearly move**, and `budget::retries()` — which August passed —
  failed tonight. **At n=1 per cell, that is variance, and F575's caution applies to every row of
  that table.**

### 🚨 And that is the finding, not a disappointment

**Removing the timeout did not raise the success rate because the timeout was never the binding
constraint.** The tool table in §7 says what is: three quarters of every attempt to land work is
refused before it runs. The failures simply moved along the list — from `timeout` and
`truncated_at_cap` to `budget_exhausted`, which is what *twenty-four rounds of a tool that refuses
three times in four* looks like from the outside.

⚠ **`abcc --version` has now failed 27 consecutive attempts across five weeks and two builds.** It
is the smallest task in the set by any reading, and it is the one this system cannot do. Whatever is
wrong is reproducible on demand, which makes it the cheapest possible subject for the next probe.

⚠ **p50 wall clock doubled, 175 s → 340 s.** Two reasons and both are expected: the gate now
actually runs, and nothing is killed early any more. It is the price of the attempt being real.

---

## 12. Pass 2: the tool's refusal rate fell by half, and the task success rate did not follow

Same five prompts again, with F637 and F638 in (`abcc` `95f466a`). 30 minutes, 10 attempts.

### What moved, and it has an n worth quoting

| population | `apply_patch` applied | refused | **fail rate** |
|---|---|---|---|
| August | 9 | 41 | **82%** (n=50) |
| pass 1 — F625 only | 6 | 17 | **74%** (n=23) |
| **pass 2 — + F637/F638** | **10** | **9** | **47%** (n=19) |

Both new messages fired in the field: **3 markup refusals and 6 nearest-miss refusals.** One of the
latter, verbatim, and it is the case for the whole change:

```
apply_patch: crates/abcc/src/cli.rs: hunk 1 does not match. The closest place is
line 154, where 11 of its 12 context lines match. The first difference is line 9
of the hunk:
  you wrote:    "    #[error(\"{USAGE}\")]"
  the file has: "    #[error(\"abcc {}\", env!(\"CARGO_PKG_VERSION\"))]"
```

🚨 **Eleven of twelve lines matched, and the one that differed is the model's own earlier edit,
already in the file.** It was patching against a stale view of a file it had already changed. The old
message — *"its context is nowhere in the file"* — could not have said that, and the observed
response to the old message was to go hunting for a different line number.

### What did not move

| task | August | pass 1 | pass 2 |
|---|---|---|---|
| `Seq::back saturating` | 0/1 | **1/1** | 0/2 · budget_exhausted, **standard** |
| `Seq::is_origin` | **1/1** | **1/1** | 0/2 · budget_exhausted, truncated_at_cap |
| `abcc --version` | 0/25 | 0/2 | 0/2 · budget_exhausted ×2 |
| `abcc breaker --depth` | 0/2 | 0/2 | 0/2 · said_nothing ×2 |
| `budget::retries()` | **1/1** | 0/1 · **standard** | 0/2 · truncated_at_cap ×2 |
| **total** | **2/30** | **2/7** | **0/10** |

⚠ **I cannot claim the change helped or hurt the success rate, and neither should anyone reading
this.** One arm per condition over five tasks is exactly the design F575 warns about — *the floor is
as large as the effect* — and `Seq::is_origin` passing twice and then failing twice, with nothing
between the runs that touches it, is that floor being visible.

**What can be claimed** is the narrower thing, and it has the larger n: **the refusal rate of the
one tool that lands work fell from 82% to 47% across three populations.**

### 🚨 Where the failures went instead

Pass 2's ten endings: **5 `budget_exhausted`, 3 `truncated_at_cap`, 2 `said_nothing`**, and one
`refused` at the **`standard`** rung. The model is now landing patches and still not converging —
which is the same shape as §11's result one level down. *Removing a constraint reveals the next one.*

🎉 **And one attempt got further than anything else this project has recorded**: `Seq::back` reached
the gate's `standard` rung and was refused for a **formatting diff** in `seq.rs`. Working code that
`cargo fmt --check` would not pass. ▶ **That is a new failure mode and a cheap one** — the head has
`bash` at the exec tier and used it 17 times this pass, so it *can* run `cargo fmt`; it simply does
not. Whether telling it to helps is a prompt question, and W7's ruling applies: a sentence binds only
as far as the model complies.

### ⚠ The regression I checked for and did not find

Refusing markup payloads outright could in principle throw away a patch that would have applied. It
does not: **all three markup payloads pass 2 refused carry duplicated file headers** — the same file
twice, from the repeated attempts, one of them literally headed
`--- a/crates/abcc-core/src/seq.rs\t(rejected patch)`. Two blocks for one file cannot express one
coherent edit, so nothing correct was lost.

---

## 13. ⚠ F640 — the probe that would have settled the cause came back negative

`research/tools/multicall.py` asks the champion for three small edits across three files — the shape
that invited more than one call in the field — and captures the raw SSE. **It did not reproduce.**
One clean `apply_patch`, 292 argument characters, one `index`, no markup anywhere.

So the cause of the markup is still open, but four explanations are now eliminated:

| hypothesis | evidence against |
|---|---|
| the turn was truncated and left a mess | **all 60 payloads finished `tool_calls`**, none `length` |
| the model degrades after being refused | markup is on the **first** call in 14 of 14 attempts |
| Recon's brief carries an example it copies | **0 of 57 claims** contain any markup |
| asking for several edits at once triggers it | the probe above, negative |

▶ **What is left to try** is the thing the probe could not stage: the field cases all carry a real
transcript — a brief, twenty-odd `read_file` results, 6,700–20,600 prompt tokens — and the probe had
none of that. **Replaying one failing turn's exact body through the same capture is the next step**,
and the log has the body.
