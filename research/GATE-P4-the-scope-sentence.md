# GATE P4 — the scope sentence, measured against its own noise floor

**Session of 2026-09-03/04.** David postponed the Console eyeballing review and asked for a GPU
session instead; the work he chose was **F536's better lead**. This is what it produced.

**Verdict up front: DO NOT SHIP THE SENTENCE.** Its effect on what the Judge reports is **smaller
than the effect of asking the identical question twice.** The one place it did something the control
never did in two tries is a population of **three**, and F534 says only one of those three was
answerable at all.

**363 model calls, 121 trees, three arms, zero endings other than `answered`.**

| arm | brief | tag | wall clock | findings |
|---|---|---|---|---|
| control, sample a | shipped | `reviews-scope-off-a/` | 00:10:51 → 01:30:01, 79.1 min | 94 |
| treatment | shipped **+ one sentence** | `reviews-scope-on-a/` | 01:30:01 → 02:53:49, 83.8 min | 94 |
| **control, sample b** | **shipped — nothing changed** | `reviews-scope-off-b/` | 02:56:15 → 04:20:47, 84.5 min | **92** |

---

## 1. Why there is a third arm, and why it is the only one that matters

F536 found its lead inside a probe whose own conclusion was *"always run the same-view re-ask before
believing a switch."* Nothing in this stack samples at temperature zero — the engine sends no
`temperature`, no `top_p` and no `seed` — so **two arms cannot tell a treatment effect from a coin
flip.** The third arm asks the control a second time. It is the ruler.

🚨 **Without it this session would have shipped a false positive.** The two-arm result looked like a
signal: 17 trees changed between control and treatment. That is a real number and it means nothing.

## 2. The decisive table

| comparison | trees up | trees down | **CHANGED** |
|---|---|---|---|
| control a → **control b** — *nothing changed* | 13 | 14 | **27** |
| control a → **treatment** — *one sentence added* | 13 | 10 | **23** |

▶ **The treatment moved FEWER trees than re-asking the same question moved.** Per population the
same holds, and on the half that decides precision it is exact:

| population | trees | noise floor, changed | treatment, changed |
|---|---|---|---|
| `correct` | 59 | **6** | **6** |
| `wrong` | 59 | 20 | 14 |
| `sham` | 3 | 1 | 3 |

## 3. Precision: no cost, and the reason is that there was never a stable baseline

A finding on a `correct` tree is a candidate false positive, and ADR-0008's falsifier is a reviewer
whose findings cost an operator minutes for nothing. The three arms:

| arm | findings on `correct` | trees | which trees |
|---|---|---|---|
| control a | 5 | 4 | Q01, Q15, Q26, Q36 |
| **control b** | **2** | **2** | **Q43, Q45** |
| treatment | 5 | 4 | trace_dropped_samples, Q15, Q53, Q54 |

🚨 **The trees are almost entirely different every time.** Only `Q15` appears twice. Two runs of the
*identical* brief share **not one** flagged tree. So a correct-tree false positive is close to a
random draw, the control's own range is **2 to 5**, and the treatment's 5 sits inside it.

⚠ **This also retracts a number the two-arm read produced.** `round_at_the_line_not_the_total-sham`
went 3 findings → 0 under treatment and that looked like a loss. Control b scored it **0** as well:
the three findings were the outlier, not the zero.

## 4. 🚨 BOTH ARMS FABRICATE, AT THE SAME RATE — checked against the patches, not the prose

This is the result the control was run to get, and it is the one that would have been reported wrong.

* **control** — `q56-Q26-correct`: *"Typo in object comparison loop accesses out-of-scope variable
  `i`."* The object loop is `for (const key of aKeys)` and uses `a[key]`/`b[key]`. `i` occurs **only**
  in the array loop above it, correctly scoped. **Fabricated**, on a `green` tree, 3 rungs passing.
* **treatment** — `q56-Q54-correct`: *"`indegrade` is used instead of the defined `indegree`. This
  raises a `NameError` on any input with at least one dependency."* **`indegrade` does not occur in
  the patch.** `indegree` occurs five times. **Fabricated**, on a `green` tree, 3 rungs passing.

▶ **One invented identifier defect per 59 correct trees, each way.** F536 saw this class under
`Named` and read it as the cost of withholding evidence. It is not: **it is what this reviewer does
at this rate regardless.** Reporting the treatment's `NameError` as the scope sentence's cost would
have repeated F536's own error with the sign flipped.

## 5. What the sentence *did* change: prose, not findings

* **Coverage claims rose from 1 tree to 10** (a regex for claims about *extent* — deliberately not
  matching the word *scope*, which the treatment brief itself uses, so an echo proves compliance
  rather than insight).
* **Correct-tree assessments grew 444 → 555 characters, +25%.**
* 🚨 **All four coverage claims on correct trees are NEGATIVE and carry zero findings** — *"the scope
  aligns exactly with the task requirements"*, *"No other files or logic paths are affected."* The
  check ran and passed. That is the good version of this behaviour, and it is still **111 characters
  an operator reads to learn nothing they can act on.**

## 6. The one signal that is not noise — and it is three trees wide

| sham | control a | control b | treatment |
|---|---|---|---|
| `finish_the_cancelled_status` | 0 | 0 | **1**, naming the coverage gap |
| `trace_dropped_samples` | 0 | 0 | **1** |
| `round_at_the_line_not_the_total` | 3 | 0 | 0 |

▶ **The two shams whose defect lies outside the diff went 0 → 1 under treatment and stayed 0 across
both control samples.** `finish_the_cancelled_status` reproduced it twice — once in a smoke call and
again in the arm — with *"Only `jobs/sla.py` was modified. The task requires updating all consumers
of status decisions (six total)."* That is exactly the case F536 predicted.

⚠ **It is n = 2 of 3, and F534 says only 1 of the 3 shams was answerable from what the reviewer was
shown.** One is not a rate. **This is a lead for a bigger population, not a result.**

## 7. 🚨 F568 — the hedge detector is a NULL INSTRUMENT and nothing may be quoted from it

`hedge_candidate` fired **0 times in 363 reviews**, both briefs. It is a phrase list
(`cannot verify`, `no visibility`, …) shipped **without a positive control**, and the reviews plainly
carry the language it was built to catch — the treatment's own best answer says *"Other potential
consumers of job status were not updated"* and the column reads `false`.

▶ **The column is in all three TSVs and it is evidence of nothing.** Every number in this document
was read against the corpus by hand. **An instrument that returns zero without a positive control in
the same command has not measured zero** — [[verify-claims-against-code-not-docs]] has said this
since F494 and it was still shipped.

## 8. What this costs and what to do

* **Cost of the sentence:** +4.7 min per 121 trees (79.1 → 83.8), +5% completion tokens, +25%
  assessment prose. **Benefit at this resolution: none that is distinguishable from noise.**
* ▶ **Do not add the sentence to the shipped brief.** `ScopeNote::Absent` stays the default and no
  production caller passes one. The switch stays for the follow-up below.
* ▶ **The follow-up worth running is a bigger `correct-but-incomplete` population.** The corpus has
  **3** shams and that is the entire evidence base for the only real signal here. A tier of trees
  whose defect is *outside the diff* is what would settle it.
* 🚨 **The noise floor is now a measured property of this rig and every future probe owes it one:**
  **27 of 121 trees change when nothing changes.** Any switch that moves fewer than that has not been
  shown to do anything.

## 9. Provenance

* abcc `7cea4fd` — `judge::SCOPE_SENTENCE`, `ScopeNote`, three tests including one asserting the
  control brief is the shipped brief byte for byte.
* research `bfec91b` — both first arms and the hand-verified analysis.
* Runner `harness/scripts/scope-probe.sh`; `SAMPLE=b` names the second sample of an arm.
* Champion `qwen3.6-35b-a3b-mtp@iq3_s`, context 65536, `--parallel 1`, one resident instance with no
  TTL, asserted by the preflight before each arm (F567).
