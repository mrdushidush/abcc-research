# PILOT P14 — the paragraph was not the lever, and the control says so

**Status: the headline this session inherited — *the lever is ONE PARAGRAPH: order `write_file`, not
`apply_patch`* — does NOT survive its own control. The baseline prompt, re-run byte-identical with no
paragraph at all, landed 4 of 5.**

P13 closed on one pair: `t649` (no paragraph) died at the 16,384-token cap with an `apply_patch`
argument that delivered **0** characters, and `t720` (one paragraph added, every other byte
identical) went green. That pair was read as *the paragraph is the lever*, with two caveats written
down and not yet paid: the paragraph makes two claims at once — it names `write_file` **and** says
the file is 112 lines — so *"separating those needs a third cell"*, and *"one attempt is not a
landing rate."*

This session flew the third cell, the fourth, and the control P13 never ran. Eight attempts on one
card, `RUNTIME-11` in `crates/claudette/src/runtime/usage.rs`, at `3fdfefe` — the sha before the fix
landed, so the defect is genuinely present in every cell.

| cell | names `write_file` | states "112 lines" | first editing call | outcome |
|---|---|---|---|---|
| `t649` a657 | no | no | `apply_patch`, **0** chars / 16,384 tok / `length` | ❌ Uncertain / TruncatedAtCap |
| `t720` a728 | **yes** | **yes** | `write_file`, 4,297 chars / 1,185 tok | 🎉 green 4/4 |
| `t839` a848 | no | **yes** | `write_file`, 4,647 chars / 1,283 tok | 🎉 green 4/4 |
| `t840` a918 | **yes** | no | `write_file`, 4,689 chars / 1,263 tok | 🎉 green 4/4 |
| `t988` a996 | no | no | `apply_patch`, 53,401 chars / 15,115 tok | 🎉 green 4/4 |
| `t1068` a1078 | no | no | `apply_patch`, 2,696 chars / 806 tok | 🎉 green 4/4 |
| `t1069` a1156 | no | no | `apply_patch`, 2,678 chars / 813 tok | 🎉 green 4/4 |
| `t1070` a1257 | no | no | `apply_patch`, 2,920 chars / 900 tok | 🎉 green 4/4 |

Every prompt is `t720`'s text with exactly one paragraph substituted or removed. The four baseline
prompts were read back out of the log and compared to `t649`'s **byte for byte** before being run.
Every figure below is read from `claudette-92490a1b1de94eca/log.sqlite`, not from a doc.

---

## 1. F806 — either half of the paragraph works, and it does not buy what we credited it with

The paragraph makes two independent claims. Split into one cell each, **both halves work, and they
work equally well**:

* **`t839`, the size claim with no tool named.** The prompt says only *"This file is only 112
  lines… send ONE editing call whose content carries the COMPLETE change… an editing call here has
  twice run past the output ceiling and been discarded whole."* The strings `write_file` and
  `apply_patch` appear **nowhere** in it — checked programmatically against the stored prompt, not
  by eye. The model reached for **`write_file`** unprompted, first try, 4,647 chars in 1,283 tokens.
* **`t840`, the tool named with no size claim.** Every mention of 112 lines removed. Same result:
  `write_file`, 4,689 chars in 1,263 tokens.

Both went green on all four rungs with the Judge reporting no findings, and **their diffs are nearly
identical** — same two call sites, `self.turns` included, one new test, even the same test name
`saturating_counters_do_not_wrap`.

▶ **What is statistically real here is the tool choice, and only that.** All three paragraph cells
opened with `write_file`; all five baseline cells opened with `apply_patch`. **3 of 3 against 0 of
5, Fisher two-sided p = 0.0179.** The paragraph reliably changes which editor the model reaches for.

## 2. 🚨🚨 F807 — and changing the editor did not change the outcome: the baseline lands 4 of 5

`t988`, `t1068`, `t1069` and `t1070` are `t649`'s prompt, verbatim, re-run at the same sha with no
paragraph. **Four of the five baseline attempts went green on all four rungs**, and their diffs are
the same correct fix — both call sites, `turns` included, a real test that panics on the unfixed
tree. `t1070` did it with `apply_patch` alone, applying 3 hunks and then 1, with no refusal at all.

| contrast | paragraph | baseline | test | p |
|---|---|---|---|---|
| first editing call is `write_file` | 3 of 3 | 0 of 5 | Fisher | **0.0179** |
| attempt went green | 3 of 3 | **4 of 5** | Fisher | **1.0000** |
| change-phase completion tokens (median) | 1,991 | 4,946 | Mann-Whitney exact | 0.3929 |

🚨 **So the sentence *"the lever is one paragraph"* is retracted.** The paragraph moves the tool
choice, and nothing that has been measured follows from it. `t649`'s death was **the outlier of
five, not the rule** — and the single pair P13 reasoned from was the one comparison in which that
outlier sat on the control side.

⚠ **This is the fifth time this project has published a cause before running the control** (F769,
F777, F789, F794, F797), and the first time the control was run in the same week as the claim. The
cheapest control remains what it has always been: **re-run the same input.** Four re-runs of one
unchanged prompt cost about twenty minutes of GPU and overturned the session's headline.

## 3. F808 — what actually saves a baseline attempt is a refusal message abcc already ships

The baseline is not landing *despite* reaching for `apply_patch`. It lands because abcc tells it what
to do when the patch fails. Every baseline attempt's editing history:

| attempt | first `apply_patch` | how abcc answered | what followed | end |
|---|---|---|---|---|
| a657 | 16,384 tok, **0 chars** | *(never became a call — cut at the cap)* | nothing | ❌ dead |
| a996 | 53,401 chars | refused: **tool-call markup**, `<tool_call>` at line 1262 | `write_file`, 4,615 chars | 🎉 |
| a1078 | 2,696 chars | refused: **hunk 3 does not match**, closest line 54, 2 of 4 context lines | `write_file`, 4,446 chars | 🎉 |
| a1156 | 2,678 chars | refused: **tool-call markup**, `</tool_call>` at line 63 | `write_file`, then `apply_patch` applied 1 hunk | 🎉 |
| a1257 | 2,920 chars | **applied, 3 hunks** | `apply_patch` again, 1 hunk | 🎉 |

🚨 **The markup guard is F637's, and its refusal text already contains the paragraph:**

> *"If the next `apply_patch` is refused this way too, stop patching and use `write_file` instead:
> one call, `path`, and the file's whole new text in `content`."*

▶ **The instruction P13 credited to the task prompt is already in the product** — it arrives on the
failure path instead of up front, and the model takes it: **3 of 3 refusals recovered to green.** The
repair loop works. `t649` never reached it, because a call cut mid-argument never becomes a call
(F515) — so it is never refused, never advised, and the attempt dies with the model still believing
it patched.

⚠ **Two of the five baselines emitted `<tool_call>` markup INTO the diff argument** — the model
serialising its own transcript into a tool argument, at 53,401 and 2,678 characters. That is a
model-side pathology this guard exists for, and it fired correctly both times. **Three guards of one
shape manufactured red last session; this one is the counter-example — a guard that reported a real
defect and told the model how to recover.**

## 4. F809 — the size rule is too tight, because it sizes the cap with the wrong end of the distribution

P13 §16 sized the ceiling as *"the measured median 2.54 argument characters per completion token, so
16,384 tokens is roughly 41,600 characters — about 1,000–1,100 lines of Rust."* Re-measured over
**303** single-call events carrying ≥ 500 argument characters across all three logs, the median holds
at **2.55** — and is the wrong statistic for the job.

| | chars/token |
|---|---|
| median, all 303 | **2.55** |
| p10 / p90 | 1.56 / 3.22 |
| min / max | 0.26 / 3.94 |
| **the eight largest arguments ever delivered** | **2.77 – 3.82** — every one above the median |

🚨 **Long arguments are denser than the median call**, which is the opposite of what a conservative
estimate needs: a short call is prose and schema punctuation, a 50,000-character diff is mostly
source text. Sizing the cap by the overall median therefore **understates** it. At the rate large
calls actually achieve, 16,384 tokens buys roughly **46,000–62,000 characters**, not 41,600.

✅ **The record moved this session: the largest argument this stack has ever delivered intact is now
53,401 characters** (`t988`'s `apply_patch`), past the 51,401 P13 recorded. `write_file`'s own
maximum is unchanged at 33,020 — a fact about what it has been *asked* for, not a ceiling it hit.

Against this repository's Rust (**38.0 chars per line**, median over 99 files of ≥ 50 lines):

| budget | lines of Rust |
|---|---|
| 41,600 chars (P13's rule) | 1,094 |
| 46,000 | 1,210 |
| 55,000 | 1,446 |

⚠ So *"the lever only exists under ~1,100 lines"* is **too tight by roughly a third**, and the
worklist it produced — *17 of 41 located cards fit* — is a floor, not the count. `api.rs` (3,548
lines) and `conversation.rs` (3,899) stay far out of reach; the cards near 1,400 do not.

⚠ **None of this is a licence to aim at the ceiling.** The three paragraph cells each delivered a
whole file in **1,185–1,283 tokens**, about 8% of the budget.

## 5. ▶ What to do with P13 §17, whose recommendation this unmakes

P13 §17 recommended **(b) rewrite `apply_patch`'s `summary` in `tools.rs`** as a size rule, on the
strength of the paragraph's 1-of-1. That evidence is gone: the paragraph does not change the landing
rate, and the same advice already reaches the model through F637's refusal text and works there.

▶ **The honest options now:**

1. **Do nothing to `tools.rs`.** The repair loop lands 4 of 5 unaided. This is the default, and the
   burden has shifted onto anyone who wants a change.
2. **Fix the thing that actually killed the one dead attempt: the cut.** `t649` is the only failure
   in eight, and its cause is F511/F515 — one argument overran the cap, delivered nothing, and the
   attempt had no way to learn that. A model told *"your last call was cut before it arrived"* could
   retry; today it is told nothing at all. **That is a real, unbuilt mechanism**, and unlike the
   paragraph it addresses the observed failure rather than the observed tool preference.
3. ⏸ **Do not remove `apply_patch`** — unchanged from P13 §17(c), and `t1070` strengthens it: the
   tool applied 4 hunks cleanly with no refusal, and it is the only editor that can touch a file
   over ~1,500 lines.

⚠ **And do not spend more GPU on this card.** Eight attempts on one 112-line file is enough; the n
that matters now is **different cards**, which is what David asked for — *"drive the tool for at
least 100 tasks."*

## 6. Housekeeping

* The two arms and the four baseline replicas ran on a temporary `pilot-arms` branch in
  `D:/dev/claudette` at `3fdfefe`, **nothing was landed**, and the branch is deleted — `007b84f`
  already carries this fix on `main`.
* 🚨 **F810 — a green attempt cannot be marked "measured, do not land", and the board now shows six
  that must never be landed.** `abcc reject` refuses every one of them: *"Accomplished is terminal;
  Abort would resurrect a finished task"* — which is the right guard on the wrong question. The
  state machine has one word for *this work is good* and no word for *this run was an instrument*.
  Six rows now read `MISSION ACCOMPLISHED … abcc land t1070`, and landing any of them would re-apply
  a fix `main` already carries. Same shape as F802: **the log is honest about what happened and has
  no verb for what the operator knows.** ⚠ Until it has one, the warning lives here and in memory,
  which is exactly the fragility F802 described.
* `abcc` unchanged at `b09bcdf` throughout; model `qwen3.6-35b-a3b-mtp@iq3_s`, `-c 40960`,
  `max_tokens 16384`, default `--rounds 24`. All eight cells share one prefix except the substituted
  paragraph.
* ⚠ **`CHECK-01` is already fixed in the tree** — `outcome_from_run` and `CheckOutcome::TimedOut`
  exist, and the doc comment names the roast card. Another stale card, found the way the standing
  rule says to find them: grep the tree, never read the title.
* ✅ Still open by grep, for the next real tasks: `SHELL-04` (`test_runner.rs`, 180 lines — no job
  object, no `taskkill`, no `killpg`), `SHELL-06` (`tools/semantic.rs`, 427 — still the hand-rolled
  `is_dir()` walker), `UX-04` (`status.rs`, 326), `RUNTIME-08` (`runtime/context_evict.rs`, 542 —
  `messages.to_vec()` still unconditional at line 141).

Findings **F806–F810**; next free is **F811**.
