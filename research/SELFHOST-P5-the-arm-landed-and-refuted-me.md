# SELF-HOST P5 — the arm landed, refuted the file that designed it, and found an interaction

**Status: flown, scored against a rule fixed before the model was loaded, and the result is the
opposite of what SELFHOST-P3 §4 predicted. The arm is 15 valid attempts on `4687405^` = `7fe980f`
(buggy redaction, OLD `diagnostics` summary), 68 minutes, 15 clean exits, zero timeout kills, and
the cell control passed on every checkpoint. 🚨 **It reached a checker 4 times in 15 — 26.7% —
against a registered prediction of 0–1 under REDACTION and ~3–4 under DIAGNOSTICS.** So the
pre-registered rule returns **DIAGNOSTICS**, and P3 §4's "941add1 goes in front of 4687405" is
**wrong**. ▶ But the completed 2×2 says the registered dichotomy was itself too simple:
**neither commit alone moves checker use at all — both isolated comparisons land at p = 1.0000 —
and only their COMBINATION collapses it.** F712's corruption is reproduced at the desk on the
current tree (15 of 117 files), which gives the interaction a mechanism worth one more desk test
before anybody flies again.** Findings **F783–F785**; next free is **F786**.

---

## 1. What flew, and the controls that ran before the count was read

| | |
|---|---|
| tree / binary | `4687405^` = **`7fe980f`**, built from a detached checkout of `D:\dev\abcc` |
| cell, verified on every checkpoint | redaction **buggy**, `diagnostics` **OLD** — `armscore.py` refuses to score otherwise |
| task | the anchored prompt, 329 chars, `sha1[:8] = 552a8db2`, verified before any task was made |
| flight | 15:45:36 → 16:53:43, **68 min**, 15 exits all **0**, **zero** timeout kills |
| valid observations | **15 with a Change phase**, after replacing 3 that never reached it |
| seeding | **unseeded** — `223ae3a` postdates this tree |

⚠ **Three of the original fifteen (`t9`, `t14`, `t16`) died in Localize with `said_nothing`** and
were replaced under the rule written at 16:07, before any kill or count had been seen. **That rule
is what keeps this honest**: an attempt with no Change phase has no *opportunity* to call a checker,
so scoring it as a miss would have inflated the REDACTION side — the side this project predicted.

---

## 2. 🚨 F783 — the registered rule returns DIAGNOSTICS, and the prediction was wrong

**4 checker hits in 15 — 26.7%.** Registered expectations: **REDACTION ~4.2% → 0–1 hits**;
**DIAGNOSTICS ~24.4% → ~3–4 hits**. The rule (`≤1` vs `≥2`) returns **DIAGNOSTICS (`4687405`)**.

The four: `a200` (`diagnostics` ×3), `a1400` (`run_tests`, and it ended **`success`**), `a1693`
(`run_tests`), `a1970` (`run_tests`). ⚠ One attempt in this arm reached a **green ending** on a tree
five days older than `main` — the only `success` in any anchored cohort.

🚨 **SELFHOST-P3 §4 said "941add1 goes in front of 4687405" and this refutes it.** That paragraph
was hypothesis-generating, found after looking, at p = 0.1468 and n = 8 — and it said so at the
time. **The pre-registration is what made this falsifiable, and it is the only reason the refutation
is worth anything.** ▶ *An inference found after looking survived exactly as long as it took to
pre-register it and fly.*

---

## 3. 🚨🚨 F784 — the completed 2×2 is an INTERACTION: neither commit alone does anything

With the arm's cell filled, all four exist for the first time:

| | `diagnostics` **OLD** | `diagnostics` **NEW** |
|---|---|---|
| redaction **none / fixed** | **24.4%** (11/45) | **25.0%** (2/8) |
| redaction **buggy** | **26.7%** (4/15) ◀ the arm | **4.2%** (1/24) |

**Three cells sit between 24.4% and 26.7%. One collapses to 4.2%.** The isolated effects:

| what is varied, holding the other fixed | comparison | p |
|---|---|---|
| **redaction alone**, both OLD | 24.4% → 26.7% | **1.0000** |
| **`diagnostics` alone**, redaction not buggy | 24.4% → 25.0% | **1.0000** |
| `diagnostics` within buggy redaction | 26.7% → 4.2% | 0.0621 |
| redaction within NEW `diagnostics` | 25.0% → 4.2% | 0.1468 |

▶ **Neither commit moves checker use on its own, and both nulls are exact.** Pooling the three
unaffected cells against the collapsed one: **17/68 25.0% vs 1/24 4.2%, p = 0.034.**

🚨 **This is why P11 and P12 could not pin it.** Both were looking for *which single commit* was
the lever, and on this evidence **neither is** — the question had no answer in the form it was
asked. ⚠ **The pooling and the interaction reading are POST-HOC.** What is pre-registered is F783
alone. The interaction is the best available reading of four cells, not a tested hypothesis.

⚠ **And the cells are not matched on everything.** The arm flew 09-18 unseeded; `buggy/NEW` flew
09-11 unseeded; `none/OLD` is older and unseeded; **`fixed/NEW` is seeded and n = 8**. Date, seeding
and sample size all vary across the table, and only the two commits were deliberately varied.

---

## 4. ⚠ F785 — a mechanism for the interaction, reproduced at the desk, and NOT yet tested

**Why would the two together do what neither does alone?** The buggy Assignment shape is
case-insensitive, so it matches ordinary Rust identifiers. Reproduced on `main` today:

> **15 of 117 `crates/**/*.rs` files are rewritten by the buggy regex; 2 by the fixed one.**
> `pub fn served(base_url: &str, api_key: Option<&str>) -> Result<Listing,`
> — `api_key:` matches `API[_-]?KEY`, and the value half `[^\s"'#]{8,}` eats `Option<&str>`.
> **The type is destroyed and the signature is left malformed.**

▶ **The hypothesis: `4687405` is what puts redactable SOURCE into the `diagnostics` result.** The
OLD summary ran `cargo check --all-targets` and returns compiler errors; the NEW one appends
`cargo fmt --check` — **whose output is a diff of the source** — and `cargo clippy`, which prints
source context. So with the new summary the tool's own result is full of lines like the one above,
**the buggy redactor mangles them, and `diagnostics` starts returning corrupted text.** A model that
calls a tool twice and gets garbage back stops calling it — which is what 1 of 24 looks like.

🚨 **This is NOT tested and must not be reported as the cause.** The test is deterministic, costs no
GPU, and is the obvious next desk task: **run the NEW `diagnostics` command on a deliberately broken
tree, pass its output through both regexes, and count what changes.** If the buggy one mangles the
tool result and the fixed one does not, the interaction has its mechanism.

---

## 5. What may and may not be said from this

* ✅ **May:** the pre-registered discrimination came out **DIAGNOSTICS**, and **P3 §4's reading is
  retracted by its own arm.**
* ✅ **May:** on the evidence in §3, **neither commit alone changes checker use**, both at p = 1.0000.
* 🚨 **May not:** *`4687405` suppresses checker use.* The registered rule names it, but the 2×2 says
  it does nothing on a tree whose redactor is sound (24.4% → 25.0%). **The rule was a forced choice
  between two hypotheses and the truth was a third.**
* 🚨 **May not:** restate **F765** or **F673** from any of this. F764's rule stands — repair by
  adding, never by moving a published number.
* 🚨 **May not:** quote the 0.0621 or the 0.1468 as significance. They are not.
* ⏸ **Open:** the mechanism (§4), and whether the interaction survives a seeded, date-matched
  replication. **Nothing here is worth another 100-attempt arm; the desk test comes first.**

---

## 6. What this cost, and what the design bought

**68 minutes and 15 attempts**, against SELFHOST-P1's original design of **100 attempts and
7.2–11.9 GPU hours** for less information. The saving came from estimating both rates off the log
first and asking a two-hypothesis question (F780) — and the *result* came from pre-registering a
prediction the evidence was then free to destroy.

⚠ **The honest postscript: the registered rule returned an answer that the fuller table then
qualified.** A two-hypothesis rule cannot report *neither*, and this one could not have. **That is a
limit of the design, not a failure of it** — but the next pre-registration on this subject should
carry a third outcome, and say in advance what *no effect from either* would look like.
