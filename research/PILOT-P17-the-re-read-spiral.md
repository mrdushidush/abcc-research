# PILOT P17 — the re-read spiral, and the paragraph that could not stop it

**Session of 2026-09-22.** `SHELL-10` landed first try and the standing next step was *another
one-change card on a different file*. `SEC-06` was chosen, verified by hand, driven twice, and
**did not land either time**. This is what the two attempts measured.

**Verdict up front: the prompt is not the lever for the re-read spiral, and now there are two arms
that say so.** A paragraph written against the exact measured behaviour, quoting its own numbers at
the model, moved the re-read rate **89.9% → 88.0%**. ▶ **The tool layer has to stop it, because the
brief demonstrably cannot.**

---

## 1. What ran

| | `a1711` (v1) | `a1866` (v2, + one paragraph) |
|---|---|---|
| task | `t1703` | `t1858` |
| prompt | 3,828 B | 4,573 B — **v1 plus one paragraph, nothing else moved** |
| ending | `Uncertain { TruncatedAtCap { budget: 16384 } }` | `Uncertain { BudgetExhausted { which: "24 rounds" } }` |
| turns | 22 | 24 |
| tool calls | 20 (**19 `read_file`, 1 `search`**) | 22 (**21 `read_file`, 1 `search`**) |
| **editing calls** | **0** | **0** |
| tokens | 368,523 + 31,301 (29,232 reasoning) | 444,736 + 16,403 (14,145 reasoning) |
| trace | `OpenAt200` | `Closed` |
| wall clock | 531,401 ms | 305,393 ms |
| gate | REFUSED structural — *changed no file the repository tracks* | same |

Both refusals are correct and neither is a false red: **no file was written, by either attempt.**

## 2. 🚨 F827 — the no-re-read paragraph does not work

The paragraph was written against the measurement, not against a hunch. It told the model the file
had been read whole **thirteen times, byte for byte the same 14,017 bytes**, that this was 89.9% of
everything the tools returned, that the attempt died having changed nothing, that **a file does not
change between your reads because you are the only thing editing it**, and that it should scroll
back in the conversation or ask for a narrow range instead.

| | v1 | v2 | change |
|---|---:|---:|---|
| `read_file` calls | 19 | 21 | **+2** |
| bytes served | 187,018 | 175,167 | −6.3% |
| **byte-identical repeats** | **89.9%** | **88.0%** | **−1.9 points** |
| whole-file reads (`lines 1-427 of 427`) | 13 | 12 | −1 |
| ranged reads | 6 | 9 | +3 |

**Nothing here clears a noise floor, and no floor was measured, so the honest reading is that the
paragraph did nothing detectable at n = 1 a side.**

⚠ **What it DID change is the class of death**, and that is not an improvement: v1 spent its token
budget (`TruncatedAtCap`), v2 spent its round budget (`BudgetExhausted`, 24 rounds). Reasoning
halved, 29,232 → 14,145, so the model floundered less — and still never called an editor. **A
cheaper way to reach the same nothing.**

### 2.1 Why this is not `t1494`'s result, though it was modelled on it

`SHELL-06`'s `t1494` died of context overflow and a one-line control — *do not open the sibling
files* — cut its read output **75%** and removed the overflow entirely. That worked because
compliance was **subtractive**: the model could obey by not touching files it did not need.

Here the instruction is *do not re-read the file you do need*, and compliance requires the model to
trust its own conversation instead of re-fetching ground truth. ▶ **The distinction to carry
forward: a prompt can remove a read the model does not need, and cannot remove one it believes it
needs.**

### 2.2 It is the same shape as P14, one layer down

`PILOT-P14` found the *order `write_file`* paragraph had **no effect on the outcome** (3 of 3 against
a baseline 4 of 5, Fisher p = 1.0) while strongly moving **which tool was called first** (p = 0.0179).
The pattern repeats: **a paragraph can move what the model reaches for; it does not move whether the
attempt lands.**

## 3. 🚨 F828 — the spiral, and where a stop would have to fire

`a1711`'s prompt trace, in tokens:

    seq 1716   2,209  ─┐
    seq 1779  37,165  ─┴  thirteen whole-file reads fill a 40,960 window
    seq 1784  18,649      prompt_cut fires and halves the conversation
    seq 1848  19,306      16,384 completion / 16,384 reasoning / 0 text / no call / finish=length

⚠ **The barren-turn stop WOULD have fired on `a1711`** — turn `1848` is 16,384 reasoning tokens with
no text delta and no tool-call delta, past the 12,288 threshold. **That makes it 5 for 5.** ✅ This
corrects a claim made mid-session that it would not fire because every turn produced a tool call;
the *final* turn did not.

🚨 **But it fires at the END, and by then the window is already spent.** It would have saved the
decode of one turn. The re-read stop would fire at **seq 1746 — the second byte-identical whole-file
read** — and would have saved roughly 150,000 bytes ≈ 37,000 tokens, which is the attempt itself.

▶ **F822's objection does not reach a stop.** F822 parked the re-read back-reference because a
back-reference is only sound if the earlier copy survives in the conversation the server sees. That
is an argument about **rewriting** the conversation. Refusing, or ending the turn on, the Nth
byte-identical whole-file read inside one attempt **rewrites nothing**, needs no truncation policy,
and is the same kind of signal as a barren turn: not work, a loop.

⚠ **n = 2 attempts on one card.** This is a ranking argument, not a measured rate, and the catch
side has no false-positive population behind it yet. The barren-turn stop has 2,536 turns of that;
this has none. **Say both halves.**

## 4. ⚠ What this does to the one-change ladder

| shape | cards | attempts | landed |
|---|---|---:|---:|
| one change | `RUNTIME-11` 4/5, `SHELL-10` 1/1, **`SEC-06` 0/2** | 8 | **5** |
| multi-part | `SHELL-04` 0/2, `SHELL-06` 0/2 | 4 | 0 |

**Fisher two-tailed p: 0.0476 → 0.0606 → 0.0808.**

🚨 **The claim is weaker than it was at the start of this session, and it is recorded that way on
purpose.** Both attempts are counted. Excluding an inconvenient attempt after seeing its result is
the failure this project's standing rule exists to prevent.

⚠ **And the data point is confounded.** `SEC-06` died of a mechanism that has nothing to do with how
many parts the card asks for: `semantic.rs` is **427 lines** against `SHELL-10`'s **180**, and the
spiral's cost is proportional to file size. So this varied **size and shape together**, which is
exactly the thing `ScopeNote`'s doc comment warns about. ▶ **The same-file control remains the
strongest half of the ladder**, and it is untouched: `SHELL-04` and `SHELL-10` are both
`test_runner.rs` at 180 lines, 3 parts vs 1, **0 of 2 against 1 of 1**.

## 5. ✅ The card is sound — that is not what failed

`SEC-06` was verified by hand before it was ever queued, which is the standing pre-queue rule:

* the defect is live at `crates/claudette/src/tools/semantic.rs:179-184` — `if name != ".env"
  { continue; }` inside the dotfile skip, so `.env` is the one dotfile walked into model context;
* the candidate test goes **RED on the unfixed tree** — `.env was walked into model context:
  [".env", "ok.rs"]` — with **no** privilege, platform or stdin caveat, unlike `SHELL-06`'s symlink
  and `SHELL-10`'s EOF;
* the fix is **one deletion**, and afterwards the suite is **1,164 passed, 0 failed**;
* no new dependencies — `std::env::temp_dir()` is the crate's own idiom.

Reference solution `research/patches/SEC-06-reference-solution.patch`; prompts
`SEC-06-task-prompt.txt` and `-v2.txt`. **Nothing about the defect defeated the model. It never
reached an editor.**

## 6. Findings

* **F827** — the no-re-read paragraph does not work: byte-identical re-read rate **89.9% → 88.0%**,
  whole-file reads 13 → 12, bytes 187,018 → 175,167, across two attempts on one card whose prompts
  differ by **one paragraph and nothing else**. Both died without an editing call. The class of
  death changed (`TruncatedAtCap` → `BudgetExhausted`) and the outcome did not. ▶ A prompt can
  remove a read the model does not need (`t1494`, −75%) and cannot remove one it believes it needs.
* **F828** — on `a1711` the barren-turn stop would have fired at turn `1848` (16,384 reasoning, no
  text, no call), making it **5 for 5**, but it fires after the window is spent; a stop on the
  **second byte-identical whole-file read** would have fired at `seq 1746` and saved ~37,000 tokens.
  F822's soundness objection is about rewriting the conversation and does not reach a stop.

## 7. 🎉 F829 — the barren-turn stop is wireable after all, and here is the number

**Added 2026-09-22, after a five-agent review.** §3 called the barren-turn stop "the top remaining
change" and every reviewer agreed. **One of them found that it cannot be wired as published, and
that was correct.** This section runs the control that unblocks it.

### 7.1 🚨 The blocker: 12,288 is measured in a quantity the engine cannot see live

`usage.reasoning_tokens` is the server's own count and arrives **in the closing usage block**. The
only quantity the engine tracks **per delta, live**, is `reasoning_chars` — `turn.rs:841`,
`self.reasoning_chars += chunk.len()` inside `Accumulator::take`. ✅ Verified: `reasoning_tokens`
appears in `abcc-engine` only in `openai.rs` (parsing the API's usage), `provider.rs:623`,
`turn.rs:255` (the `PhaseReport` field) and the scripted test helpers. **There is no chars-to-tokens
constant anywhere in `abcc-engine`** — the only one in the tree is `abcc/src/replay.rs:583`, whose
own comment calls it *an estimate*, and it is a reporting helper.

▶ **So a live stop needs the threshold re-derived in `reasoning_chars` against the same population.**
That is desk work on the log, not a code change, and it had not been done.

### 7.2 The ratio, measured rather than assumed

**2,778 `model_call_ended` rows carry BOTH `reasoning_chars` and `reasoning_tokens`.**

| | chars per reasoning token |
|---|---|
| pooled (5,118,603 chars / 1,383,089 tokens) | **3.701** |
| mean / median | 3.885 / 3.803 |
| p10 / p90 | 3.332 / 4.609 |

⚠ **The spread is why a single multiplication is not the answer** — p10 to p90 is 3.33 to 4.61, so
12,288 tokens is anywhere from 40,943 to 56,635 chars depending on the turn. The threshold has to be
chosen against the **population**, not converted.

### 7.3 🎉 The control, run in chars over 3,048 turns

**Population: 3,048 turns carrying a live `reasoning_chars` figure** — 2,830 productive (emitted text
or a tool call), 218 that emitted nothing.

🚨 **The most-reasoning PRODUCTIVE turn is 40,628 chars** (`abcc-1ae35b6091a63e2c` seq 8312), and its
`reasoning_tokens` is **10,486** — which is exactly the figure P15 quoted as the nearest productive
turn in token space. ✅ **The two analyses cross-check each other.**

| threshold (chars) | ≈ tokens | CATCH (emitted nothing) | FALSE POSITIVE (productive) |
|---:|---:|---:|---:|
| 30,000 | 8,106 | 6 | **4** |
| 40,000 | 10,808 | 5 | **1** |
| **45,478** | **12,288** | **5** | **0** |
| **50,000** | 13,510 | **5** | **0** |
| **56,635** | 15,303 | **5** | **0** |
| 60,000 | 16,212 | 5 | 0 |
| 70,000 | 18,914 | **0** | 0 |

✅ **Anything from ~41,000 to ~60,000 chars gives 5 catches and 0 false positives.** The rule is a
plateau, not a knife edge — which is the property that makes it safe to ship.

▶ **RECOMMENDED: 50,000 chars.** It sits **9,372 chars above** the most-reasoning productive turn and
**10,760 below** the least-reasoning barren turn (60,760), which is the most margin available on both
sides at once. It is a round number chosen from a plateau, not a fitted one.

### 7.4 The five turns it catches, and what they confirm

| log | seq | reasoning chars | reasoning tokens | finish |
|---|---:|---:|---:|---|
| claudette | 1400 | 64,732 | 16,334 | `length` |
| claudette | 1595 | 63,923 | 16,380 | `length` |
| claudette | 1459 | 63,703 | 16,296 | **`stop`** |
| claudette | 1485 | 62,344 | 16,364 | `length` |
| claudette | 1848 | 60,760 | 16,384 | `length` |

✅ **All five are in the claudette log and none in abcc's own ~2,300 turns** — F815 said exactly this.
🚨 **One of the five ends `stop`, not `length`** — F815's point that a `length` filter misses them,
reproduced independently in chars.

### 7.5 ⚠ The limitation nobody had stated: it catches ONE shape, and a1866 is the other

🚨 **The barren-turn stop would NOT have fired on `a1866` at all.** No turn in that attempt reached
the barren shape — its largest reasoning turn was ~1,800 chars. It died at **round 24,
`BudgetExhausted`**, through many small unproductive turns rather than one enormous one.

▶ So the rule is **5 for 5 on the turns it is about** and **0 for 1 on attempts**: it catches
*context exhaustion inside a single turn* and does not catch *a round budget spent on many small
turns*. Both `SEC-06` attempts died of the same re-read spiral; only one of them died in a shape this
rule can see. **That is the argument for ranking the re-read guard above it**, and it is now measured
rather than asserted.

### 7.6 ⚠ And the re-read guard has a risk the morning's write-up understated

§3 argued F822's objection does not reach a stop, because a stop rewrites nothing. That is true about
**safety** — a stop cannot fabricate content. But a reviewer found the residual, and it is real:
**`body` is abcc's local record and is not guaranteed to equal what the server retained.**
`prompt_cut` fired inside *both* of these attempts, and LM Studio truncates the middle at HTTP 200.
So a guard that refuses a re-read because *you already have this* can strand a model whose visible
copy the server has since dropped.

▶ **Mitigation to measure, not to assume**: refuse the 2nd occurrence and let the 4th through, rather
than refusing permanently. ⚠ **No false-positive population exists for this** — zero instances are
wired — so that escape valve is a design choice with no rate behind it yet, and it must be written
down as such.

### 7.7 F829

* **F829** — the barren-turn stop's 12,288 threshold is measured in `usage.reasoning_tokens`, which
  arrives only in the closing usage block; the engine's one live counter is `reasoning_chars`
  (`turn.rs:841`) and no chars-to-tokens constant exists in `abcc-engine`. Re-derived over **3,048
  turns**: the pooled ratio is **3.701 chars/token** (p10 3.33, p90 4.61), the most-reasoning
  productive turn is **40,628 chars / 10,486 tokens**, and **every threshold from ~41,000 to ~60,000
  chars catches 5 and costs 0 false positives**. ▶ **Ship 50,000.** ⚠ And the rule catches one
  failure shape only: it would not have fired on `a1866`, which died at the round budget.

---

## 8. ✅ BOTH STOPS ARE WIRED — and the class the guard must not touch

**Added 2026-09-22, the same day.** Work-order items ① and ② are in the tree, with tests, and
every claim below is either a measurement over the log or a test that kills its own mutation.
🚨 **The falsifier has NOT been run** — see §8.5 — so nothing here says the guard works on a live
attempt, only that it does what it says to a body.

### 8.1 Item ① — the re-read guard, `crates/abcc-engine/src/turn.rs`

`TurnLoop::already_have` runs inside `tool_round`, **upstream of `Event::ToolCallEnded`**, and
returns a back-reference to send instead of a result the body already carries byte for byte.

| | |
|---|---|
| state | the **`Body`**, scanned per call. No new field, no new state, no cross-crate change |
| key | full content equality, plus a 64-bit FNV-1a fingerprint in the substituted header so repeats are countable |
| scope | **`Reach::Inspects` only** — see §8.2 |
| floor | **arithmetic**: substitute only when the note is smaller than what it stands in for |
| escape valve | every **4th** occurrence is served whole |
| record | `ToolCallEnded.output` carries the note, so F713 still holds; an `Event::Note` says how much was withheld |

🚨 **Scoped to `Body` and not `Workspace`, and the reason is structural rather than stylistic.**
`Workspace` is one `&self`-shared instance across both phases (`abcc-drive/src/lib.rs:368` and
`:381`); `Body` is fresh per phase. Dedup state on the workspace would substitute in a Change
phase whose body never saw the original — a back-reference to nothing.

### 8.2 🚨 F830 — the class that must be excluded, and it was measured rather than reasoned

The morning's plan said *scan for a prior `Role::Tool` message with identical content*. Run over
the **855 `tool_call_ended` rows that carry an `output`** across all four logs (abcc, claudette,
arm-redact, ABCC-20 — the success path logged nothing before `1cfe1ac`, F771), there are **150
byte-identical repeats within one attempt**, worth **1,791,455 bytes**:

| tool | repeats | duplicate bytes |
|---|---:|---:|
| `read_file` | 135 | 1,788,309 |
| **`apply_patch`** | **12** | **2,466** |
| `search` | 2 | 377 |
| `list_files` | 1 | 303 |

🚨 **All twelve `apply_patch` repeats are results a back-reference would lie about.** Ten are
failure messages — eight *hunk 1 does not match* and two *the diff is malformed* — and **two are
`applied 1 hunk to 1 file`**, at 52 and 57 bytes. An inspecting tool answers *what is in the
workspace*, so an identical answer is the same fact restated; an editing tool reports **what just
happened**, so two identical reports are two distinct events. Telling a model *you already have
this* in answer to its second successful patch would say the patch had not landed.

✅ **Excluding the whole class costs 2,466 bytes of 1,791,455 — 0.14%** — and it is a property
every tool already declares (`ToolSpec::reach`), not a name list, which is W7's ruling.

⚠ **The floor is arithmetic, not a constant.** Substituting pays only when the note is smaller
than what it stands in for. Inventing a size threshold would be a number with nothing behind it;
the arithmetic excludes exactly one repeat in the log, a **78-byte `search`** result the note
would have made *bigger*. Everything else clears it: the smallest surviving `read_file` repeat is
380 bytes.

⚠ **The escape valve costs 13% of the saving**: every 4th occurrence served whole re-admits **16
of 131** substitutions and **233,283 of 1,785,975** bytes. The remaining 87% is what the guard is
worth on this population. 🚨 **There is still no rate behind the valve** — zero instances of the
failure it guards against have been observed, because zero were possible before it existed.

### 8.3 Item ② — the reasoning ceiling, shipped at 50,000 chars

`Limits::reasoning_ceiling`, sampled in `TurnLoop::drain` between deltas beside
`control.interrupted()`. Crossing it returns `Drained::Runaway`, which drops the stream — F200's
3–14 ms socket close — and ends the phase `Why::ReasoningRunaway { chars, ceiling }`, a **new**
variant because nothing in that enum meant *abcc itself gave up on a turn*.

`classify` calls it **`Uncertain`** — an absence, like the eleven above it — and `next_after`
recommends **another attempt**, on `SaidNothing`'s argument: F246 measured the trace at
9,942–16,564 characters on *identical* input, so a runaway is a sample and not a property of the
task.

### 8.4 The tests, and the mutation matrix that makes them load-bearing

Nine tests across `abcc-engine/tests/turn_loop.rs` and `abcc-drive/tests/attempt.rs`. Every one
was driven RED by a mutation of the thing it asserts, **one mutation killing exactly one test**:

| mutation | test that died |
|---|---|
| the guard never fires | `an_identical_second_read_is_answered_with_a_back_reference` |
| the guard applies to every tool | `an_editing_tool_is_never_answered_with_a_back_reference` |
| no arithmetic floor | `a_result_smaller_than_the_back_reference_is_served_whole` |
| no escape valve | `the_fourth_identical_read_is_served_whole` |
| dedup on size rather than content | `a_result_that_changed_between_reads_is_never_a_duplicate` |
| `drain` never checks the ceiling | `a_turn_that_reasons_past_the_ceiling_is_ended_by_abcc` |
| ceiling dropped to 40,000 | `the_most_reasoning_productive_turn_ever_logged_still_answers` |

✅ **714 tests pass, 0 fail**; `cargo fmt --check` and `cargo clippy --all-targets -- -D warnings`
are both clean. 🧹 `$D` deleted.

### 8.5 🚨 WHAT HAS NOT BEEN DONE, stated plainly

* **The falsifier has not run.** `SEC-06` must be re-driven with the **v1 prompt unmodified**, and
  the dup-byte share must collapse from ~88–90% toward 0 with `prompt_cut` no longer firing. If
  dup% and `prompt_cut` are unchanged, **revert**. Until that runs, the measured saving —
  ≈29,000 tokens on `a1711`, ≈36,000 on `a1866` — is arithmetic over a log, not an observation.
* **No live attempt has ever seen either stop.** Both are measured against bodies and populations.
* **The escape valve has no rate**, restated because it is the one number in §8.1 that is a guess.
* Item ③'s card is **verified but not driven**: `RUNTIME-10`'s red test goes RED on the unfixed
  tree with no stack overflow, the reference fix turns it green, **1,205 claudette tests pass**,
  and `research/patches/RUNTIME-10-task-prompt.txt` is **4,949 bytes of pure ASCII** — 0 non-ASCII
  bytes, no `U+FFFD` — which is the whole point, since `t201`'s stored prompt carries mojibake.
* Item ④ has not started: it needs the QUALITY tier resident, and **no model is loaded**.

### 8.6 F830

* **F830** — the re-read guard must be scoped to `Reach::Inspects`, and the reason is measured
  rather than tidy. Of the **150** byte-identical tool-result repeats in this project's whole log
  (855 rows carrying an output, four logs), **12 are `apply_patch`**: ten failure messages and
  **two `applied 1 hunk to 1 file` lines**. An editing tool's result reports *what just happened*,
  so a back-reference to it is a false statement about an event — on the two applied-ok lines it
  would tell a model its second patch had not landed. Excluding the class costs **2,466 of
  1,791,455 duplicate bytes, 0.14%**. ⚠ A second exclusion is arithmetic and not a threshold:
  substituting pays only when the note is smaller than the result, which drops exactly one repeat,
  a 78-byte `search`. ⚠ And the escape valve — every 4th occurrence served whole — costs **16 of
  131** substitutions and **233,283 of 1,785,975** bytes, 13%.

---

## 9. THE GPU SESSION — the falsifier ran, and it found more than it was pointed at

**Session of 2026-09-22/23.** Both stops were driven live: six attempts on the speed tier and two
on the quality tier. The falsifier passed. Two of the things it turned up were not what it was
looking for.

### 9.1 ✅ Item ① — the falsifier, on its second sample

▶ **The first re-run was a null result and is recorded as one.** `a2009` ran the v1 prompt
unmodified on the new engine and died `Uncertain { SaidNothing }` after **7 turns and 4 tool
calls** — F503's shape, both nudges spent. It never repeated a read, so the guard never fired:
0 back-references, 0 `prompt_cut`, largest reasoning turn 7,510 chars. ⚠ **Neither new stop is
implicated and that was checked rather than assumed.** `seed_for` hashes the attempt, so a new
attempt is a new sample on a byte-identical prompt.

`a2065` is the measurement:

| | `a1711` | `a1866` | **`a2065`** |
|---|---:|---:|---:|
| `read_file` calls | 19 | 21 | 22 |
| **bytes served to the model** | 187,187 | 175,339 | **41,291** — **−78%** |
| duplicate-content share | 89.9% | 87.9% | **38.9%** |
| back-references sent | 0 | 0 | **7** |
| bytes withheld | 0 | 0 | **58,573** |
| **`prompt_cut`** | **8** | **5** | **0** |
| ending | `TruncatedAtCap` | `BudgetExhausted` | `BudgetExhausted` |

🚨 **The residual 38.9% is not a miss — it is the escape valve, to the byte.** Per fingerprint:

    130146e5…  the 14,017-byte whole-file read   occ 1 FULL · 2 ref · 3 ref · 4 FULL · 5 ref · 6 ref
    5ab3f68a…  an 826-byte read                  occ 1 FULL · 2 ref · 3 ref · 4 FULL
    ac755f80…  a 789-byte read                   occ 1 FULL · 2 ref

14,017 + 826 = **14,843**, which is the measured duplicate total exactly. With the valve removed it
would be 0. ▶ **Do not revert**: `prompt_cut` stopped firing outright, which was the second
condition, and the first collapsed as far as the valve permits.

⚠ **It did not make the card land, and that is the more useful half.** 22 `read_file` calls,
**zero editing calls**, dead at the round budget. The model still re-read the whole file **six
times** — it just paid for two of them. ▶ **F827 one layer down: the tool layer can remove the
*cost* of a read the model believes it needs; it cannot remove the read.**

### 9.2 🚨 F831 — the ceiling fired twice in the wild, and its own field data corrects it

✅ **Both live firings are true positives.** `a2229` (speed tier) and `a2468` (quality tier) each
ended `ReasoningRunaway { chars: 50003, ceiling: 50000 }`. The witness for the first is the
liveness mark at the cut — *`recon streaming: 0 chars of answer, 49622 of trace, 0 of tool-call
arguments`*. The second is true **by construction**: `produced_nothing()` is a precondition of the
cut, so a turn that had produced anything could not have reached it.

🚨 **But `a2065` breaks the plateau's premise.** It contains, **in one attempt**:

| turn | reasoning chars | produced |
|---|---:|---|
| seq 2163 | **26,275** | nothing — 0 text, 0 calls, `stop` |
| seq 2207 | 17,008 | nothing |
| seq 2151 | **34,760** | 1,037 chars of text **and** a `read_file` |

▶ **The two populations F829 fitted the plateau against are not separable by a threshold.** No
ceiling catches the 26,275-char barren turn without discarding the 34,760-char productive one.
F829's *5 catches, 0 false positives* was a property of that 3,048-turn sample, not of the
quantity. **The rule is 5 of 6 on turns, not 5 of 5.**

✅ **The engine answers the half that can be answered.** The stop now also requires
`Accumulator::produced_nothing()` — no text, no assembled call, no argument bytes, no
`ToolCallOpened`. This can only *prevent* firings, so catches stay 5 and false positives can only
fall. ⚠ **It does not make the rule complete**: LM Studio buffers a tool call's arguments to the
end (F624), so a turn whose only output is a large call looks barren for almost all of its trace.
**The threshold is still doing the real work.**

✅ **Two more live productive turns above 30,000 chars** — 30,660 in `a2229` and 34,760 in `a2065`
— independently confirm that F829's 30,000 row (4 false positives) was rightly rejected. ⚠ And with
the ceiling **off**, `a2603` produced a turn at **64,572** reasoning chars, a new maximum above the
historical 60,760.

🚨 **`--reasoning-ceiling <n>`, where `0` is OFF, and it exists because of `a2468`.** The ceiling
ended the first Change phase the quality tier ever reached, correctly by every signal the loop had
— and *whether that turn would have produced anything* then became **unobservable, because the
observation is the thing the stop prevents**. ▶ **A stop that cannot be taken out of the path
cannot be measured.** `0` maps to `usize::MAX` rather than to a ceiling of zero, which would end
every turn before its first delta.

### 9.3 🚨🚨 F832 — TWO OF THREE LANDED CARDS CARRY A TEST THAT PASSES UNFIXED

`RUNTIME-10b` landed — MISSION ACCOMPLISHED, four green rungs — and **the Judge reported that its
test does not exercise the change**. The Judge was right. Each landed test was then extracted
**verbatim** and injected into the tree it was written against:

| landed card | its own test, run on the pre-fix tree | verdict |
|---|---|---|
| `RUNTIME-11b` (`a728`) | `test result: FAILED` | ✅ **real** |
| **`SHELL-10`** (`a1612`) | `test result: ok` | 🚨 **SHAM** |
| **`RUNTIME-10b`** (`a2322`) | `test result: ok` | 🚨 **SHAM** |

* `RUNTIME-10b` wrote `format!("{}{}", "[", "]").repeat(300)` — that is `"[][][]…"`, **flat**. It
  errors on *unexpected trailing content* and never reaches the depth check.
* `SHELL-10` asserts a child reads **0 bytes** of stdin. Under `cargo test` the parent's stdin is
  already at EOF, so an **inherited** stdin reads 0 too. Verified: the pre-fix tree has
  `cmd.args(args).stdout(Stdio::piped()).stderr(Stdio::piped())` and **no `.stdin(...)` at all**,
  and the test still passes there.

⚠ **Both production fixes are correct.** The defect is in the tests. Three consequences:

1. 🚨 **The gate cannot see this.** It runs `cargo test` and gets green either way. A red test is
   the one thing the card design rests on and the one thing nothing verifies.
2. 🚨 **The same-file control is gone.** §4 called it *"the strongest half of the ladder —
   `SHELL-04` and `SHELL-10`, both `test_runner.rs` at 180 lines, 3 parts vs 1, 0 of 2 against
   1 of 1."* **That 1 of 1 is a sham-test landing.**
3. 🎉 **The Judge caught what the deterministic rungs could not, and decided nothing** — which is
   ADR-0009's ruling working exactly as written. This is the first time in the project's history
   the judge has produced a finding the gate could not, and it argues the report is worth more
   than the ladder has credited.

▶ **`abcc land t2018` was NOT run.** The change is fine; its test should be replaced first.

### 9.4 F833 — item ④: the QUALITY tier does not land the multi-part card either

`unsloth/qwen3.8-27b`, 4.9× cost, `-c 40960 --parallel 1` — **the same window as the speed tier, so
the window is not a confound.** The card is `SHELL-04b` (`t1409`), the ASCII multi-part prompt that
already failed on the speed tier.

| | `a1417` speed tier | `a2468` 27B, ceiling on | **`a2603` 27B, ceiling off** |
|---|---|---|---|
| Localize | 4 turns / 3 calls | 7 / 11 | **8 / 10, artifact produced** |
| Change | **never ran** | 1 / 1 | **12 turns / 13 calls** |
| **editing calls** | — | — | **0** |
| ending | `TruncatedAtCap` | `ReasoningRunaway` (**void**) | `TruncatedAtCap` |
| wall clock | — | — | **38.3 min** |

▶ **The bigger model gets much further and still never calls an editor.** On the speed tier Change
never ran at all; on the 27B it ran twelve turns and spent them on **11 `bash` calls and 2
`read_file`**. ⚠ `a2468` is **void for this question** — abcc's own stop ended it, which is what
§9.2's flag exists to prevent.

▶ **So the one-change law is not refuted by a bigger model**, and that is the weaker of the two
readings available: *this quant cannot hold multi-part instructions* is no longer the explanation,
but n = 1 attempt on one card at the quality tier is not a rate.

### 9.5 ✅ F834 — `Body` scoping, confirmed in the wild on the first attempt that could test it

`a2603` served **two byte-identical `read_file` results whole** — 7,914 B and 6,165 B — with the
guard silent. That is correct, and it is the design decision being exercised:

    occ 1 seq 2612 in LOCALIZE  ->  occ 2 seq 2721 in CHANGE   (7,914 B)
    occ 1 seq 2637 in LOCALIZE  ->  occ 2 seq 2749 in CHANGE   (6,165 B)

🚨 **Both crossed the phase boundary.** Had the dedup state been on `Workspace` — one instance
shared across both phases — the Change phase would have been handed *you already have this,
earlier in this conversation* pointing at a message its own `Body` never contained: **a
back-reference to nothing**. The work order predicted this failure; it occurred on the first
attempt that read substantially in both phases, and the guard was silent exactly as designed.

⚠ Also confirmed live: the `Reach::Inspects` filter. `a2603`'s Change phase made **11 `bash`
calls** and none was considered for substitution.

### 9.6 ⚠ The ladder, recomputed from the log — and it does not match §4

🚨 **Every attempt in the claudette log, counted by `outcome = success`:**

| card | shape | landed / attempts |
|---|---|---:|
| `RUNTIME-11` | one change | 7 / 8 |
| `SHELL-10` | one change | 1 / 1 |
| `SEC-06` | one change | 0 / 4 |
| `RUNTIME-10b` | one change | 1 / 2 |
| `SHELL-04` | multi-part | 0 / 4 |
| `SHELL-06` | multi-part | 0 / 2 |
| **one change** | | **9 / 15** |
| **multi-part** | | **0 / 6** |

**Fisher two-tailed p = 0.0186.** ⚠ **With the two sham-tested landings not counted as landings
(§9.3), it is 7 / 15 and p = 0.0609.**

🚨 **This table does not match §4's**, which published *one change 5 of 8, multi-part 0 of 4,
p = 0.0808*. The log says 15 and 6 attempts where §4 says 8 and 4. ▶ **Which accounting is the
intended one is David's to settle** — §4 may have been counting cards, or excluding the
`RUNTIME-11e` control re-runs, and inventing a reconciliation here would be exactly the kind of
after-the-fact adjustment this project's standing rule exists to prevent. **Both numbers are on the
record; neither is quietly replaced.**

### 9.7 Findings

* **F831** — the reasoning ceiling's two populations are **not separable by a threshold**. `a2065`
  holds a barren turn at **26,275** reasoning chars and a productive one at **34,760** in the same
  attempt, so F829's *5 catches, 0 false positives over 41,000–60,000 chars* is a property of that
  sample and not of the quantity; the rule is **5 of 6 on turns**. The stop therefore also requires
  the turn to have produced nothing — no text, no assembled call, no argument bytes, no
  `ToolCallOpened` — which can only prevent firings, and **does not make the rule complete**
  because F624 buffers a tool call's arguments to the end. ✅ Two live firings, `a2229` and
  `a2468`, both true positives. ▶ And a stop that cannot be taken out of the path cannot be
  measured: `--reasoning-ceiling 0` exists because the ceiling ended `a2468`, making the very
  observation that would validate it impossible.
* **F832** — **two of three landed cards carry a test that passes on the unfixed tree.** Verified
  by extracting each landed test verbatim and injecting it into the tree it was written against:
  `RUNTIME-11b` goes RED (real), **`SHELL-10` passes (sham)**, **`RUNTIME-10b` passes (sham)**. The
  gate cannot detect this — it runs `cargo test` and sees green either way — and the judge can, did,
  and correctly decided nothing. 🚨 §4's *strongest half of the ladder*, the same-file
  `test_runner.rs` control at 1 of 1, **is a sham-test landing**.
* **F833** — the QUALITY tier does not land the multi-part card either. `unsloth/qwen3.8-27b` at
  the same 40,960 window reached Change and spent **12 turns and 13 tool calls** there — 11 of them
  `bash` — with **zero editing calls**, ending `TruncatedAtCap` after 38.3 minutes, where the speed
  tier's Change phase never ran at all. ▶ *This quant cannot hold multi-part instructions* is no
  longer the explanation. ⚠ n = 1 attempt; a first run was voided by abcc's own ceiling.
* **F834** — the re-read guard's `Body` scoping is confirmed in the wild. `a2603` served two
  byte-identical `read_file` results whole, 7,914 B and 6,165 B, **both crossing the
  Localize→Change boundary**; dedup state on the shared `Workspace` would have answered the Change
  phase with a back-reference to a message its own `Body` never held. ✅ The `Reach::Inspects`
  filter is confirmed too: the same phase made 11 `bash` calls and none was considered.
