# SELF-HOST P6 — the desk test, and the tool that was fixed and never called again

**Status: the F785 desk test ran, and it settled the mechanism in both directions at once.
✅ The premise is TRUE: on a tree the compiler is silent about, the OLD `diagnostics` command puts
**zero** redactable lines into its own result and the NEW one puts **three** — and what the buggy
redactor does to a `cargo fmt --check` diff is worse than garbage, because the `-` and the `+` line
redact to the *same* text, so the tool tells the model to replace a line with itself.
🚨🚨 **And the cause is REFUTED, because the NEW command has never run.** `diagnostics` has been
called **13 times in this project's history and every one was on a tree with the OLD summary** — the
last at `seq 7210`, **2026-09-08 00:05:11**, three days before `4687405` landed. There was never a
result to mangle. 🚨 **The same log kills two more of P5's claims:** the buggy redactor never
touched an exec-tier tool result *once* (20 notes: 17 `read_file`, 2 `search`, **1 a brief**), the
arm's cell recorded **zero** redactions in 18 attempts so **its treatment was never administered**,
and F784's interaction **dissolves on decomposition** — `diagnostics` is 0.0% in *both* NEW cells,
so the tool the two commits actually changed shows no interaction at all.**
🎉🎉 **AND §7 CLOSES THE QUESTION THE REST OF THIS FILE LEFT OPEN, for the price of eleven sorties
rather than the 120–160-attempt arm §6 priced: F792 — the zero was never unreachability. The tool had
never been ASKED for.** Told to call it, 5 of 6 attempts did (83%) against **0 of 44** untold,
p = 0.0152 — and the first call in the project's history to F673's repaired tool returned a **usage
error** (F791). Findings **F786–F790** and **F792**; next free is **F793**. Instrument
`research/tools/diagreach.py`, **34 figures under `--check`**, bounded at `AS_OF = 13049` with
`--since` for the sorties above it.

---

## 1. F786 — `diagnostics` has never been called under the summary `4687405` shipped

`4687405` is F673's fix: the tool that a model checks its own work with stopped running
`cargo check --all-targets` alone and began running the standard the repository grades by. It landed
**2026-09-11 15:26:19**. The log says what happened next.

| | |
|---|---|
| `diagnostics` calls, whole primary log | **13** |
| the last one | `seq 7210`, attempt `a7085`, **09-08 00:05:11** |
| `diagnostics` calls after `4687405` | **0** |
| `bash` calls after `4687405` | **151** |
| `run_tests` calls after `4687405` | **6** |

🚨 **THE CONTROL IS WHY THIS ZERO IS WORTH READING.** A tool-reach zero is worthless if the tool
left the menu, and that is the trap this archive has already fallen into once. `bash`, `run_tests`,
`git` and `diagnostics` are **one class** — `Reach::SpawnsChild`, so `required_tier()` is
`Tier::Exec` for all four (`tools.rs:177`) — and every `model_call_started` in the Change phase
carries `ceiling: "exec"`. **151 `bash` calls in the same attempts prove the exec class was on the
menu.** The zero is a choice.

Per attempt, which is the unit of decision (F749), on **F784's own anchored cohort**:

| summary | cohort | Change attempts | reached `diagnostics` | |
|---|---|---|---|---|
| OLD | `none/OLD` | 45 | 6 | 13.3% |
| OLD | `buggy/OLD` — the arm | 15 | 1 | 6.7% |
| **OLD** | **pooled** | **60** | **7** | **11.7%** |
| NEW | `buggy/NEW` | 24 | **0** | **0.0%** |
| NEW | `fixed/NEW` | 8 | **0** | **0.0%** |
| **NEW** | **pooled** | **32** | **0** | **0.0%** |

**Fisher exact, two-sided: p = 0.0914.** ⚠ **That is not significant and may not be quoted as
though it were.** The count of *calls* (16 against 0) is more dramatic and is the wrong unit. ⚠ And
the reach is **clumpy**: six attempts carry all thirteen calls, in three clusters.

🚨 **HOW WEAK THE ZERO IS AS A RATE, stated because it is easy to over-read.** *0 of 32* bounds the
NEW-summary rate at **≤ 8.9%** (one-sided 95%, `0.911^32 = 0.05`) — which is **barely below the OLD
11.7% and does not exclude it.** So the two defensible readings are very different sizes:

* ✅ **As a count about the record: exact and total.** The command `4687405` shipped has produced
  **zero tool results, ever.** No inference is involved and no n is needed.
* ⚠ **As an estimate of a behavioural rate: weak.** A true NEW rate of 8% would produce 0 of 32
  about one time in twelve. **The zero is compatible with almost no change in behaviour.**

▶ **Everything downstream in this file rests on the first reading, not the second.**

### ✅ The control that could have killed it, run before the number was written down

The last `diagnostics` call is **09-08** and `4687405` is **09-11** — three days apart. **If the
zero began before the commit, the summary is not even a candidate.** It did not:

| | |
|---|---|
| last OLD-summary attempt | `a7484`, **09-08 00:17** |
| `4687405` lands | **09-11 15:26** |
| first NEW-summary attempt | `a7663`, **09-11 15:45** — 19 minutes later |
| attempts in between | **none** |

▶ **The three days are a gap in *activity*, not a window of OLD attempts declining to call the
tool**, and the two cohorts are adjacent in the log — which independently reproduces F767's
`a7663`. Three OLD attempts do follow the last *call* (`a7247`, `a7402`, `a7484`, all within 15
minutes) without reaching it; against a 6/56 base rate, 0 of 3 is what you would expect seven times
in ten. **The boundary is tight.**

✅ **And `941add1` is cleared off this particular zero by the arm.** Its cell is redaction **present**
with the **OLD** summary, and it reached `diagnostics` in 1 of 15 — **6.7%, not zero.** Only the NEW
summary gives zero.

⚠ **It is still observational, not an arm.** Seven commits landed in the quiet; **three of them are
model-visible and they are the three already in the frame** (`941add1`, `7fe980f`, `4687405` — the
other four are docs, CI and the weights digest). The residual confounds are the subject (SELF-HOST
made this repository its own subject), the task family and the seeding. What is *not* statistical is
the plain fact underneath: **F673's repair has never once been exercised by a model.** The fix
shipped and the tool it fixed stopped being reached for.

---

## 2. F787 — the desk test: the premise is confirmed, the cause is refuted

Run on `D:\dev\abcc` at `71f6aa8`, warm target dir, tree verified clean before and after.
**Deliberately broken means compiling but wrong**, because that is the only case where the two
commands differ: the conjunction's first refusal ends it, so a tree with a *type error* gets
`cargo check`'s output under both and the two are indistinguishable. Two breakages, both inside
`TurnLoop::secrets` — chosen because that function is one of F712's own witnesses.

| capture | chars | markers, **fixed** regex | markers, **buggy** regex |
|---|---|---|---|
| clean tree, NEW command | 888 | 0 | 0 |
| misformatted, **OLD** command | 412 | 0 | **0** |
| misformatted, **NEW** command | 451 | 0 | **3** |
| unused parameter, **OLD** command | 943 | 0 | **1** |
| unused parameter, **NEW** command | 2,075 | 0 | **4** |

🎉 **The middle pair is the test and it passes.** `cargo check --all-targets` exits **0** on the
misformatted tree and prints no source at all; `cargo fmt --check` exits **1** and prints a diff of
it. What the model would have been handed:

```
Diff in D:\dev\abcc\crates\abcc-engine\src\turn.rs:409:
     pub fn secrets(mut self, secrets: [redacted] -> Self {
-      self.secrets = [redacted]
+        self.secrets = [redacted]
     }
```

🚨 **Worse than garbage: the `-` line and the `+` line are now the same string.** The tool's result
is a diff with no visible difference, instructing the model to replace a line with itself — and the
signature above it has lost its type and its closing paren, exactly as F712 described.

⚠ **The honest qualification the desk test added.** The `warn` row shows the OLD command is not
source-free in general: a rustc *warning* prints the offending line under `cargo check` too, which
is why `warn-old` scores 1. What `4687405` distinctively adds is (a) source on a tree rustc is
**silent** about, and (b) `-D warnings`, which turns that warning into a refusal. The clean claim is
the middle pair, not a blanket one.

✅ **The instrument is the shipped code, not a transcription of it.** A throwaway example was built
against `abcc_core::redact::Secrets` and run twice — at HEAD, and with `(?i)` put back on the
Assignment shape exactly as `3e5a04b` took it off. F779 is what happens when this particular probe
is written by hand.

🚨🚨 **AND NONE OF IT CAUSED ANYTHING.** F785's mechanism runs through a mangled tool **result**.
F786 says the NEW command produced **no results at all**, in 32 anchored Change attempts. **A cause
needs an occasion and this one never had one.** The mechanism is real, reproducible, and was never
instantiated. ✅ It is also **already closed**: the fixed regex scores **0 in all five captures**.

---

## 3. F788 — where the buggy redactor actually reached the model: not a tool result, a **brief**

Every tool result crosses `Secrets::scrub` at one place, and a scrub that removed something appends
`Event::Note { "redacted: Nx <kind>" }` *before* the `ToolCallEnded` it belongs to — so the note is
attributable to the call in progress, and unlike `output` it has been logged since redaction
shipped (F771). **20 redaction notes exist on the primary log. This is all of them.**

| attributed to | notes |
|---|---|
| `read_file` | **17** |
| `search` | 2 |
| **a brief** | **1** |
| `bash` / `run_tests` / `diagnostics` / `git` | **0** |

▶ **Zero on the exec class, ever.** The tool-result seam that P5 §4 built its mechanism on has
never once carried a redaction.

🚨 **The one corrupted *instruction* on the record is a brief.** `a11138`'s Change brief, `seq
11277`, **09-12 00:45:10**, 3,438 chars, **2 markers** — and the brief is scrubbed on the same seam
(`abcc-drive/src/lib.rs:698`), which is why its note is on the log at all:

````text
**The smallest change:** Replace line 149 in `crates/abcc-tui/tests/lines.rs` with …
```rust
        text: Secrets:[redacted]0".repeat(12)).text,
```
````

**The model was handed, as the instruction it was told to implement, a line of Rust whose content
had been destroyed** — inside a fenced `rust` block captioned *the smallest change*. That is F712's
failure mode at the seam that matters most, and it is the seam nobody was looking at.

⚠ **Denominator, stated because it is small.** `BriefRecorded` only exists from **09-12 00:32**, so
there are **30 briefs** on the log and only **4** of them fall inside the buggy era (`a10967` and
`a11138`, two each). **1 of 4 is not a rate.** The claim is existence, not frequency.

---

## 4. 🚨 F789 — F784's `buggy/OLD` cell had no treatment in it

The arm flew a tree carrying `941add1`, so its cell is labelled **buggy**. What the redactor
actually did there:

| arm log, `4687405^` | |
|---|---|
| attempts | **18** |
| tool calls | **512** |
| **redaction notes** | **0** |
| briefs carrying a marker | 0 — ⚠ **vacuous**, that binary predates `BriefRecorded` entirely |

🚨 **The buggy redactor was installed and never fired once.** And F712 said why, in advance:
*"every arm flown so far worked on `cli.rs` and `main.rs`, which carry none of these shapes."* The
anchored task is `--version`; the fifteen attempts had no reason to read a file the Assignment shape
matches.

▶ **So P5's "redaction alone does nothing — 24.4% → 26.7%, p = 1.0000" is a statement about a cell
where the treatment was never administered.** The 2×2 varied *the presence of the code*, not *the
occurrence of the corruption*. **The pre-registered rule could not have detected
redaction-as-mechanism even if redaction were the whole story** — which is a limit the registration
did not state, and the honest postscript in P5 §6 asked for exactly this kind of third outcome.

🎉 **The lesson is sharper than the correction.** The anchor is what makes the cells comparable —
`sha1[:8] = 552a8db2`, the same 329-char prompt everywhere, checked before any task was made. **The
same anchor is what made one cell's treatment inert.** A fixed subject buys comparability and
spends the ability of a treatment to reach the subject at all; the next registration on a
context-corruption hypothesis has to check that the corruption *can occur* in the cohort it is
about to fly, and say so before it flies.

---

## 5. 🚨🚨 F790 — F784's interaction dissolves when the two checkers are separated

F784 measured **any checker** — `diagnostics` or `run_tests` — which is F765's metric, kept for
continuity and reasonably so. Decomposed on F784's own anchored cohort:

| cell | n | `diagnostics` | `run_tests` | **either** (F784's number) |
|---|---|---|---|---|
| `none/OLD` | 45 | 6 — 13.3% | 7 — 15.6% | 11 — **24.4%** |
| `buggy/OLD` (arm) | 15 | 1 — 6.7% | 3 — 20.0% | 4 — **26.7%** |
| `buggy/NEW` | 24 | **0 — 0.0%** | 1 — 4.2% | 1 — **4.2%** |
| `fixed/NEW` | 8 | **0 — 0.0%** | 2 — 25.0% | 2 — **25.0%** |

▶ **`diagnostics` is zero in BOTH `NEW` cells.** There is no fall-and-recovery to explain and no
interaction: it is a **monotone step on the summary axis alone**, 7/60 → 0/32, p = 0.0914, and the
redaction axis does nothing to it (6/45 → 1/15, both OLD).

🚨 **F784's collapse-and-recovery lives entirely in `run_tests`, and it is one event against two.**
The 4.2% vs 25.0% at p = 0.1468 is `1/24` against `2/8` in a single tool. **The tool the two
commits actually changed is not the tool that moved.**

* 🚨 **May not:** quote F784's *"neither commit alone moves checker use and only the combination
  collapses it"* as a property of `diagnostics`. On `diagnostics` the combination is not needed —
  and the cell that was supposed to isolate redaction had no redaction in it (F789).
* ✅ **May:** say that `diagnostics` reach falls from 11.7% to 0.0% across the summary change, at
  p = 0.0914, **observationally and not significantly.**
* 🚨 **May not:** restate **F765**, **F673** or **F784** from any of this. F764's rule is unchanged:
  repair by adding what is missing, never by moving a published number under a reader who will quote
  it. **Restating them is David's call.**

---

## 6. What this leaves open, and what it costs to close

⏸ **The open question is now singular and much cheaper than it was.** Everything about the redaction
axis is either refuted (F787, F789) or bounded to a single brief (F788). What is left is: **does the
NEW summary's *sentence* stop the model reaching for the tool?** The two candidate texts are the
whole of it —

> **OLD** — *"Build or typecheck the workspace and return the compiler's own output."*
>
> **NEW** — *"Typecheck the workspace and run the standard it declares for itself (formatting,
> lints), and return their own output. The gate's standard rung runs the same commands over the
> same tree."*

⚠ **That is a prompt question, and W7 has already priced prompt questions twice** — 39/50 and 0/50
(F404–F406), and F782 is the third at 1/33. **A sentence binds only as far as the model complies.**
So the arm worth flying is not *which commit*, it is **two summaries over one tree, everything else
held**, and the outcome is a tool-reach rate with a pre-specified third outcome for *neither*.

🚨 **And it must be costed before it is proposed, because the base rate is 11.7% — which is tiny.**
⚠ **My first draft of this paragraph guessed "25–30 attempts per arm" and was wrong by more than a
factor of two.** Simulated, 20,000 trials per point, seed 11726, two-sided Fisher at 0.05, OLD 11.7%
against NEW 0%:

| attempts per arm | 25 | 30 | 40 | 50 | **60** | **80** |
|---|---|---|---|---|---|---|
| power, anchored cohort (OLD 7/60) | 0.06 | 0.13 | 0.32 | 0.54 | **0.71** | **0.92** |
| power, all attempts (OLD 7/86) | 0.01 | 0.03 | 0.10 | 0.22 | 0.37 | 0.64 |

▶ **120–160 attempts in total on the *favourable* cohort — MORE than F772 priced the commit arm
at**, because an 11.7% base rate is a worse discrimination target than the one that already cost
7.2–11.9 GPU hours; on the broader cohort it is worse still. **This is F772's arithmetic a second
time and it says the same thing louder.**

▶ **The recommendation is therefore NOT to fly it.** Make the tool's reach an ordinary observable
instead — **one column per attempt, folded by the board** — so the next twenty sorties answer it for
free and the estimate improves without a single dedicated GPU hour. **That is a proposal for the
pack, not a flight.** 🚨 And it is *measure and propose*: nothing here ships without David's word.

▶ **What this session did not cost:** no GPU, no flight, no build of the subject beyond a warm
`cargo check` and one `clippy`, and `D:\dev\abcc` is back at `71f6aa8` clean. **Five findings, three
retractions and the control that could have killed the headline all came off a log and a git history
that were already on disk** — which is P2's lesson landing for the fourth time: *the control was one
directory away.*

---

## 🎉🎉 F792 — the zero was not unreachability. The tool had never been ASKED for.

**This file's §1 reported `diagnostics` at 0 of 39 NEW-summary attempts and called the residual
question *"does the NEW summary's sentence stop the model reaching for the tool?"*, priced an arm to
answer it at 120–160 attempts, and recommended NOT flying it — make tool reach an ordinary observable
instead and let the next sorties answer it for free.** Eleven sorties answered it, and the answer is
neither of the two hypotheses on the table.

| cohort | attempts | reached `diagnostics` | calls |
|---|---|---|---|
| every NEW-summary attempt before 2026-09-18 (F786) | 39 | **0** | 0 |
| **wave 1** — prompts do not mention the tool | **5** | **0** | **0** |
| **waves 2 + 3** — prompts say to call it | **6** | **5 — 83%** | **10** |

**Fisher exact, two-sided: 0/5 against 5/6 is p = 0.0152.** Against the pooled untold population
(0 of 44) it is p = 0.000003. ✅ **And the control is mechanical rather than remembered:** the string
`diagnostics` appears in **0 of 5** wave-1 task prompts and **6 of 6** wave-2/3 prompts, checked
against the `task` table rather than against my memory of what I wrote.

▶ **So the instrument was never unreachable and the summary was never the binding constraint. Nobody
had asked for it.** A tool that a model is told to use gets used; ADR-0009's own doctrine is that a
tool result is a fact and a prompt is a request, and this is the cheap case where the request suffices.

⚠ **What may NOT be claimed.** Waves 2 and 3 pulled a second lever — the surrounding source is in the
prompt — so this is **not an isolated manipulation**, even though carrying source is not a plausible
cause of *which tool* gets called. **n = 11.** And the grouping was **not pre-registered**: the
instruction was added after wave 1 lost, so the only thing protecting this from being a post-hoc cut
is that wave 1 ran *before the decision existed*, which makes it a genuine before-and-after rather
than a slice of one population. 🚨 **It says nothing about the summary text**, which remains the
open question §6 named — it says that the summary does not have to be fixed for the tool to be used.

🚨 **And F791 is what reaching it found.** The first call in the project's history to the repaired tool
returned a usage error, because the selector its schema invites is appended raw to a command that
takes no positionals. ▶ **The two findings are one sentence: the tool is reachable by asking, and
asking exposed a defect that had been sitting in the tree unexercised since 2026-09-11.**

⚠ **`diagreach.py --check` reports nine figures moved, and that is this finding, not a fault.** The
tool was written unbounded and said so in its header — *"unbounded is right here because the claim is
about the LAST call, which a bound would hide"* — and eleven sorties then moved the population it
described. F764's rule applies: **`PUBLISHED` is not edited.** `AS_OF = 13049` bounds `--check` to the
population the figures were measured over, the seq of the first landing, and `--since` reads the
sorties after it.
