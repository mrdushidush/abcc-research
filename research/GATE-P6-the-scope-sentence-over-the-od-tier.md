# GATE P6 — the scope sentence over the outside-the-diff tier

**Session of 2026-09-04.** `GATE-P5` built the population and refused to rule on it: *"It is a
build record, not a result. Nothing here was measured with a model."* This is the result.

**Three arms, 216 live reviews, 72 trees each: `off` (control), `on` (treatment), and `off` again
(the noise floor, measured on this tier rather than inherited).** The verdict of `GATE-P4` —
*do not ship the scope sentence* — **stands on detection.** But the tier did what David built it
to do: it found the one thing the switch reliably changes, and the totals could not have shown it.

---

## 1. What ran

    SUITE=od ./harness/scripts/scope-probe.sh both            # off-a, then on-a
    SUITE=od SAMPLE=b ./harness/scripts/scope-probe.sh off    # off-b, the floor

Preflight passed on all three arms and is worth stating because F566/F567 were written after it
did not: `lms unload --all`, one explicit `lms load` at `-c 65536 --parallel 1`, an assertion of
**exactly one resident instance with an empty TTL column**, then a warm one-token pulse read as a
token count — **661 ms**, against F566's 9,106 ms signature for a JIT load wearing a preflight's
clothes. **Zero trees came back `unmeasured` or `stopped` in 216 calls.**

Wall clock 73.4 / 79.3 / 77.2 min. Logs in `research/corpus-run/logs/scope-od-*`.

---

## 2. The three arms

| population | off-a (control) | off-b (floor) | on-a (treatment) |
|---|---|---|---|
| | find / silent / hedge | find / silent / hedge | find / silent / hedge |
| correct | 4 / 20 / 0 | 6 / 19 / 0 | 7 / 18 / **2** |
| wrong | 26 / 4 / 1 | 27 / 2 / 0 | 29 / 4 / **2** |
| sham | 11 / 15 / 0 | **17** / 15 / 0 | 15 / 14 / **5** |
| **TOTAL** | **41** / 39 / **1** | **50** / 36 / **0** | **51** / 36 / **9** |

Every row is `/ GREEN` and only `/ GREEN`, on all three arms — **F570 confirmed live**: the
deterministic ladder partitions nothing on this tier, so the judge is the sole instrument and
there is no rung for it to restate. One restatement candidate per arm, out of 72.

---

## 3. 🚨 F575 — the floor on this tier is as large as the effect, so the totals say nothing

**Asking the identical question twice moved total findings 41 to 50. Turning the switch on moved
it 41 to 51.** The treatment is one finding outside a floor of nine.

This is the reason the `SUITE=od` rule exists: q56+k's *27 of 121 trees change when nothing
changes* is a number about q56+k's trees, and a probe over a new population owes a floor measured
on **that** population. Had the floor arm been skipped, or inherited, this run would have reported
a 24% lift in findings that does not exist.

## 🚨 F576 — the sham "improvement" reverses sign once the floor is measured

Pointwise, `off-a` to `on-a` on shams reads 11 findings to 15 and looks like the switch working
on exactly the population it was written for. **`off-b` scored 17 on the same trees with the
switch off.** The treatment is not merely inside the floor, it is **below the second control**.

⚠ The general shape: a two-arm design over a sampling instrument can report the sign of the
noise. Nothing here samples at temperature zero — the engine sends no temperature, no top_p and
no seed — so one sample a side measures the day.

## ⚠ F581 — where the switch does move detection, it moves it the wrong way

`outside_file` shams, silent trees of 8: **5 (off-a), 3 (off-b), 6 (on-a).** The treatment left
**more** trees silent than either control. `outside_cover` went 7, 5, 3 — an improvement half of
which the floor already spent. Netted over the tier the two cancel, which is F575 restated at
the level where it can be seen.

---

## 4. 🚨 F577 — hedging is the only statistic that clears the floor, and it clears it by 9x

| | off-a | off-b | on-a |
|---|---:|---:|---:|
| trees carrying a scope hedge | 1 | **0** | **9** |

**A floor of one tree in 144 control reviews, against nine in 72.** No other column in section 2
survives its own floor; this one is not close.

## 🚨 F578 — the hedge is shape-selective, and lands nowhere on the control shape

F574 required the cell rather than the margin. It is the whole result. **Sham population, hedged
trees per 8:**

| shape | gap exists? | off-a | off-b | **on-a** |
|---|---|---:|---:|---:|
| `inside` | **no — same file, scope complete, logic wrong** | 0 | 0 | **0** |
| `outside_cover` | yes — sham patches a strict subset of refsol | 0 | 0 | **2** |
| `outside_file` | yes — the defect is in a file the patch never opens | 0 | 0 | **3** |

**Zero in all six control cells. All five sham hedges landed on the two shapes where a coverage
gap exists by construction, and none on the shape where it does not.** `inside` is the control
arm of the tier precisely because a switch that reports a coverage gap there is reporting one
that does not exist — and it did not.

⚠ **Five events across cells of eight.** The selectivity is 0-of-8 against 5-of-16 with a zero
floor, which is suggestive and is not a rate. It is the strongest thing in this run and it is
thin, and those two are not in tension.

## ⚠ F579 — but it also fires on complete patches, so it is not a gap detector

Two of the nine hedges are on **`correct`** trees, both `outside_cover`:
`honour_the_do_not_contact_flag` and `retire_the_legacy_sku_prefix`. On a `correct` tree the patch
**is** the full refsol — there is no gap, and the hedge is a false alarm. Both sit in the shape
whose tickets state their extent most broadly, which suggests the hedge is keyed partly to **how
wide the ticket sounds** rather than to what the diff omits. Shape and `scope_statement` are not
orthogonal here (F574), so this run cannot separate the two.

## ⚠ F580 — F568's dead instrument now has its positive control

`GATE-P5` quoted nothing from `hedge_candidate` and was right not to: **0 hits in 363 reviews, no
positive control**, and an unvalidated zero is not a measurement. It has now fired **10 times in
216 reviews**, once with the switch off. The detector works.

🚨 **What it detects is an utterance.** `hedges_on_scope` is a case-folded substring scan for 15
phrases — `cannot verify`, `no visibility`, `outside the diff`, `beyond the diff` — over the
assessment plus each finding's defect line. It cannot distinguish a judge that located the gap
from one that recited a caveat. **F577 and F578 are results about what the judge said, not about
what it understood**, and every sentence quoting them must carry that.

---

## 5. The cost, which is also mostly floor

| | off-a | off-b | on-a |
|---|---:|---:|---:|
| prompt tokens | 99,883 | **99,883** | 103,987 |
| completion tokens | 294,232 | 300,460 | 305,017 |
| wall clock (min) | 73.4 | 77.2 | 79.3 |
| median s (correct / wrong / sham) | 48 / 49 / 57 | 60 / 56 / 65 | 63 / 68 / 61 |

The two `off` arms agree to the token on prompt, which is the prompt being deterministic and a
free check that the arms differ only where intended. **The sentence costs 4,104 prompt tokens
over 72 calls — 57 a call.** Completion rose 6,228 on the floor and 10,785 on the treatment, and
the medians put the floor above the treatment in two cells of three. ADR-0008's falsifier is a
reviewer whose findings cost minutes for nothing; **the minutes are real but small, and are not
cleanly attributable to the switch.**

---

## 6. What this does to the ruling

**`GATE-P4` said do not ship the scope sentence because it moved fewer trees than asking the
same question twice. On the population built to give it its best possible case, that holds:
detection did not improve, and on `outside_file` it degraded.**

What the tier added is that the sentence is **not inert**. It reliably changes one thing —
whether the judge voices a scope caveat — and it aims that caveat at the right shapes. Whether
that is worth 57 tokens a call depends on a question this run cannot answer: **is a hedge that
lands on the right shape, without the finding, useful to a human reviewer?** A caveat that says
*look outside this diff* on the two shapes where something is outside it is a routing signal
even when it names nothing. A caveat on a complete patch is noise, and 2 of 9 were.

**Recommended: still do not ship it as a finding-producing change.** The live option it opens is
narrower and was not on the table before — **surface `hedge_candidate` as a flag rather than the
sentence as an instruction** — and testing it needs the thing this run does not have: a second
sample of the `on` arm, so the 9 has a floor of its own.

---

## 7. Owed

* **A floor for the treatment.** `on` has been asked once. F575 is the argument for why a single
  `on` arm cannot settle the 9, and it applies to the 9 exactly as it applied to the 51.
* **F563–F565** remain owed in `research/` from prior sessions.
* Artefacts: `research/corpus-run/reviews-scope-od-{off-a,off-b,on-a}.tsv`, 72 rows each, and
  `reviews-scope-od-*/` alongside them.
