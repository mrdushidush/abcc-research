# SELF-HOST P3 — the arm that turned out to be a query, and the suspect that changed

**Status: Block B is done, at the desk, with no GPU and nothing flown. David ruled option 2 —
*the deterministic discriminator first* — and the discriminator did more than it was asked to.
`4687405` (the diagnostics summary) and `941add1` (redaction at the tool-result seam) were
confounded because *every attempt after the boundary has both*. They are not simultaneous:
`941add1` landed at **11:30:10** and `4687405` at **15:26:19** on 2026-09-11, so a tree in the
3h56m between them carries the redaction with the OLD summary — the exact cell the arm was going
to buy. 🚨 **On the bounded cohort that cell is EMPTY**, which is a negative result and is
reported as one. ▶ **But unbounded there is a third cell, and it reverses the suspicion:** checker
use falls to 4.2% while F712's redaction bug is live and returns to **25.0% — baseline, p = 1.00 —
once it is fixed, with the diagnostics summary NEW in both. The summary cannot explain a fall and
a recovery it was present for.** ⚠ **p = 0.1468, n = 8, and I found it after looking.** What it
buys is a properly pre-specified arm: **the tree is `4687405^`, the rule is written below, and
n = 15 gives worst-case 0.87 against the original design's 100 attempts for 0.79.** Findings
**F777–F780**; next free is **F781**. Instrument `research/tools/redactfold.py`, read-only.

---

## 1. The four commits, and why the confound was never quite airtight

| commit | landed | what it does to the bytes the model sees |
|---|---|---|
| `941add1` | 09-11 **11:30:10** | redaction at `TurnLoop::tool_round` — **with F712's `(?i)` bug** |
| `7fe980f` | 09-11 15:18:51 | the green ladder ending (controlled out by P12) |
| `4687405` | 09-11 **15:26:19** | `diagnostics` runs the standard (F673's fix) |
| `3e5a04b` | 09-12 **11:32:33** | **F712 — the `(?i)` comes off the Assignment shape** |

▶ **The confound rested on *every attempt after the boundary has both*, and that is a claim about
which trees exist rather than about the commits.** The commits are **3h56m apart**, and a fourth
commit removes half of one of them a day later. So the log has more structure than the confound
assumed, and `redactfold.py` asks it for that structure instead of flying for it.

🚨 **And F712 is a mechanism, not a detail.** With `(?i)` the Assignment shape matched the English
word `secrets`, so `pub fn secrets(mut self, secrets: Secrets) ->` reached the model as
`secrets: [redacted] ->` — **the type gone and the closing paren with it. Fourteen of this
workspace's 132 files were rewritten before a model saw them.** A model shown corrupted source is
a plausible cause of almost any behaviour change, which is exactly why it may not stay confounded
with the other candidate.

---

## 2. The detector failed its own control twice before it passed

🚨 **F779 — two obvious probes for *is the redaction bug present in this tree* are both wrong, and
one of them is wrong in the reassuring direction.**

* **Counting `(?i)` in `redact.rs` INVERTS across the fix: 2 before, 3 after.** F712 removes one
  `(?i)` from the regex and adds two to the comments explaining why. A count would have classified
  every fixed tree as buggy and every buggy tree as fixed.
* **Grepping `(?i)(?P<keep>` matches at HEAD**, because the AuthHeader shape begins with the same
  eight characters. It reports the bug as present in every tree ever.

✅ **The probe that works is anchored on the Assignment shape alone** — `(?i)(?P<keep>\b[A-Z0-9_]*`
— and `control()` refuses to classify any unknown tree until it has separated all three known
pairs, which it prints:

```
control: redaction   941add1^ 'none'  -> 941add1 'buggy'
control: redaction   3e5a04b^ 'buggy' -> 3e5a04b 'fixed'
control: diagnostics 4687405^ False   -> 4687405 True
```

⚠ **This is F740's rule paying for itself twice in one sitting.** An instrument that cannot
separate the commits it was built from is not an instrument, and neither failure would have
announced itself — both produce a clean-looking table of the wrong numbers.

---

## 3. The separating cell is empty, and that is the honest answer to what was asked

🚨 **F777 — over the 69 anchored Change attempts below `AS_OF = 11726`, the trees occupy exactly
two of the four cells.** No attempt was handed the redaction with the old summary.

| redaction | `diagnostics` | n | reached a checker | rate |
|---|---|---|---|---|
| none | OLD | 45 | 11 | **24.4%** |
| buggy | NEW | 24 | 1 | **4.2%** |
| **buggy** | **OLD** | **0** | — | **the cell the arm would buy** |
| fixed | OLD | 0 | — | — |

▶ **So the bounded log cannot separate `941add1` from `4687405` on its own.** That is a negative
result and not a missing number: the 3h56m window exists, and no anchored attempt was launched
inside it. **This is what Block B was asked and this is the answer.**

---

## 4. Unbounded, a third cell exists — and it moves the suspect

⚠ **Declared: this crosses `AS_OF`.** The A4 arm of 2026-09-14 flew after the redaction fix, so
unbounded there is a third populated cell.

| redaction | `diagnostics` | n | checker | rate | |
|---|---|---|---|---|---|
| none | OLD | 45 | 11 | **24.4%** | the pre-fix baseline |
| buggy | NEW | 24 | 1 | **4.2%** | **while F712's bug is live** |
| **fixed** | **NEW** | **8** | **2** | **25.0%** | **after F712 is fixed** |

🚨🚨 **F778 — `diagnostics` is NEW in both of the last two cells, so the summary cannot explain the
difference between them.** Checker use falls to 4.2% and returns to **25.0%**, which is the
pre-fix baseline to within a rounding error — **`fixed/NEW` against `none/OLD` is p = 1.0000.**
The only one of the two candidates that changes across the fall and the recovery is **the
redaction**. ▶ **P12 put `4687405` back in the frame; this puts `941add1` in front of it.**

🚨 **And here is everything wrong with that paragraph, stated at the same volume:**

* **`buggy/NEW` against `fixed/NEW` is p = 0.1468.** Not significant. **n = 8.**
* **It was not pre-specified.** I read the two-cell table, saw the gap, and went looking for a
  third cell. That is the procedure this archive condemns four findings running, and naming it
  does not launder it. ▶ **It is hypothesis-generating and it is not a result.**
* **`fixed/NEW` is confounded with three days of commits** — `223ae3a`'s seeding, `c366440`,
  `83a93fe` and the rest. *Redaction fixed* and *everything else that landed 09-12 to 09-14* are
  the same column. **The confound is narrower than it was; it is not gone.**
* ⚠ The recovery cell is the A4 arm, whose attempts were **seeded**, while the two older cells
  were not (F715). Nothing here controls for that.

---

## 5. What this does to the arm — the one thing Block B was meant to buy

🎉 **F780 — the arm is now a two-hypothesis discrimination with both rates estimated from the log,
and it costs 15 attempts instead of 100.**

**The tree is a name, not a build script: `4687405^` is `941add1` + `7fe980f` with the OLD
`diagnostics` summary** — precisely the binary the memory specified, and it is the empty cell.

**Pre-specified, before anything flies:**

* **Hypothesis R** (redaction is the cause): checker use on this tree ≈ **4.2%**.
* **Hypothesis D** (the summary is the cause): checker use on this tree ≈ **24.4%**.
* **Decision rule: `≤1` hit in n Change attempts favours R; `≥2` favours D.**
* **n = 15.** Worst-case probability of the rule pointing the right way: **0.87**
  (0.87 under R, 0.91 under D). n = 12 gives 0.83; n = 20 gives 0.80 because the rule's
  threshold stops matching the rates.

| design | attempts | what it delivers | GPU hours at p50–p90 |
|---|---|---|---|
| SELFHOST-P1's, balanced | 100 | 0.79 power against a null | 7.2–11.9 |
| **this one** | **15** | **0.87 worst-case, two hypotheses** | **1.1–1.8** |

▶ **The saving is not cleverness about statistics; it is that the log already estimated both
rates.** A null-hypothesis test against a reference frozen at 1/24 spends its n fighting that
reference's noise (F772). Two point hypotheses with a 6× gap between them do not.

🚨 **What must be written to the ledger before the first attempt flies:** the tree (`4687405^`),
the rule (`≤1` vs `≥2`), **n = 15**, the stopping rule (no early look), and the seed. ⚠ **And the
prediction is now directional, which makes pre-registration matter more rather than less** —
§4 already says which way this file expects it to go.

---

## 6. What is still owed

* ⏸ **The arm itself.** ~1.1–1.8 GPU hours, David's word, and the build edits `D:\dev\abcc` — so
  it happens while nothing flies and the tree is restored after.
* ⏸ **Whether the 14 corrupted files were ever actually read** by an attempt in the `buggy` cell.
  That is a stronger link than the timing and it is checkable from `read_file` output — but only
  for the F713 era (F771), and the `buggy` cell mostly predates it. **Check before relying on it.**
* 🚨 **Do not restate F765 or F673 from this file.** §4 is not significant and was not
  pre-specified, and F764's rule stands: repair by adding, never by moving a published number.

---

## 7. 🔒 PRE-REGISTRATION — written before the first attempt flew

**Everything below was fixed before the model was loaded. Nothing in it may be revised after
seeing a result; a revised pre-registration is not one.**

| | |
|---|---|
| **Subject tree / binary** | **`4687405^`** = `941add1` + `7fe980f`, **buggy** redaction, **OLD** `diagnostics` summary. `D:\dev\abcc` is checked out detached at it and the binary is built from it, so the tree the checkpoint records and the summary the binary carries are the same commit. |
| **Task** | the anchored 329-char prompt, `sha1[:8] = 552a8db2`, unchanged. `--version` is absent at `4687405^` and at `main`, so the task is real. |
| **n** | **15 attempts with a Change phase.** Attempts that never reach Change are replaced, not counted. |
| **Outcome** | **reached a checker** — `diagnostics` or `run_tests` appears in `tool_call_started` for the attempt. Identical to `redactfold.py`'s `CHECKERS`. |
| **Decision rule** | **`≤1` hit of 15 favours REDACTION (`941add1`). `≥2` favours DIAGNOSTICS (`4687405`).** |
| **Expected under each** | R: 4.2% → 0–1 hits. D: 24.4% → ~3–4 hits. Worst-case accuracy **0.87**. |
| **Stopping rule** | **No early look.** All 15 fly before the count is read. No extension, whatever the count is. |
| **Seed** | **UNSEEDED** — `223ae3a` postdates `4687405^`, so the binary cannot seed. ⚠ This matches the two cells it is compared against (`none/OLD` and `buggy/NEW`, both unseeded) and does **not** match `fixed/NEW`, which was seeded. |
| **Log** | ~~the primary log. Schema version is **1** at both commits and the DDL is `CREATE TABLE IF NOT EXISTS`, so the old binary is compatible.~~ **FALSIFIED AT 15:51, BEFORE ANY ATTEMPT FLEW — see the amendment below. A separate `--home` is used.** |

### ⚠ AMENDMENT, 2026-09-18 15:51 — the log clause only, before any attempt flew

🚨 **The compatibility claim was wrong and the arm binary proved it in one command.** `abcc task`
on the primary log fails fifteen times out of fifteen with

```
the log: serializing an event: unknown variant `brief_recorded`, expected one of
`run_started`, ... `weights_checked`, `note`
```

**I checked `SCHEMA_VERSION` and the DDL and neither is the thing that binds.** The binding
compatibility is the **`Event` enum**: booting replays the log, and `7fe980f` cannot deserialise
`brief_recorded`, `change_landed` or `prompt_cut`, all of which postdate it. **A version constant
and a table shape say nothing about a tagged union that grew.**

✅ **It refused rather than corrupting, and the refusal was total** — the primary log is byte-identical
afterwards: 13,048 events, 76 tasks, file mtime unchanged.

### ⚠ CLARIFICATION, 2026-09-18 16:07 — the orphan rule, declared before it can be a choice

The flight script caps each attempt at `timeout 1200`. **A killed attempt would leave an orphan
with a Change phase and a truncated tool set** — and since the outcome measure is *did a checker
appear*, truncation can only ever push an attempt toward **no hit**, which is the direction the
file's own prediction wants. That is exactly the shape of bias that must be ruled on before it
occurs rather than after.

🚨 **Rule: an attempt killed by the timeout is not a completed observation. It is replaced, not
counted** — the same treatment as one that never reached Change.

✅ **Declared while this was still hypothetical: no attempt had been killed** (`t2` exited **0** at
15:50:26, the only open attempt was the one in flight) **and no checker count had been read.**

▶ **What changes: the arm writes to a fresh `--home`.** ▶ **What does not change: the tree, the
task, n = 15, the outcome measure, the decision rule, the stopping rule, and the unseeded status.**
The hypothesis and the rule were fixed before this and are untouched by it. 🚨 **No attempt had
flown and no count had been seen when this was written** — which is the only condition under which
a pre-registration may be amended at all.

🚨 **Declared in advance: SELFHOST-P3 §4 expects R.** The prediction is directional and this file
wrote it down before flying, which is the only thing that makes the result worth anything.

⚠ **What a `≤1` result will NOT license.** It says the old summary did not restore checker use on
this tree. It does not restore F765, does not restate F673, and does not by itself convict
`941add1` — `4687405^` carries the buggy redaction *and* every other pre-09-11 difference. The
claim it supports is narrow: **the diagnostics summary is not the lever.**
