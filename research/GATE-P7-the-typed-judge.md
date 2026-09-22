# GATE P7 — the typed judge, and the control that has to run before it

**Session of 2026-09-22.** David asked what `Jev` is and whether something like it can be built for
abcc's judge phase. This is the answer.

**Verdict up front: the thing worth copying from Jev is NOT the probability. It is the TYPED
QUESTION.** The probability is the half this stack cannot serve and has already ruled out twice;
the typed question is the half that fixes the weakest joint in three consecutive judge probes.

🚨 **This is a DESIGN, and it is a build record rather than a result.** Nothing below was measured
with a model. `GATE-P5` set the precedent and the rule it set applies here: *a probe over a new
population owes a floor measured on that population*, and this one owes a floor that does not yet
exist, for the reason given in section 3.

---

## 1. What Jev actually is

TypeSafe AI's `Jev` is a **System One** model: one endpoint that takes a `state` blob plus a map of
typed questions and returns a map of typed answers in a single parallel forward pass. It generates
no tokens.

    POST https://tokenra.io/v1/decisions
    { "state": "...",
      "questions": {
        "is_urgent":   { "type": "noul",   "instructions": "...",
                         "criteria": { "true": "...", "false": "..." } },
        "department":  { "type": "choice", "instructions": "...",
                         "criteria": { "billing": "...", "technical": "..." } },
        "frustration": { "type": "score",  "instructions": "...",
                         "criteria": [ "Calm", "Frustrated", "Very angry" ] } } }

    -> { "answers": { "is_urgent":   { "noul": 0.92 },
                      "department":  { "choice": "billing" },
                      "frustration": { "score": 1.6 } } }

Three primitives: **one-of-N** (up to 255), a **2-to-10 level scale**, and a **yes/no probability**.
Each answer carries a calibrated probability. Roughly 100 ms a call; input $0.042/M, output free.
The eval pitch is variance: quality-score variance 92-913x below generative judges.

⚠ **Every number in this section is the vendor's**, read from its own docs and a LangChain writeup.
None of it was reproduced here, and the one independent benchmark found (`crman/jev-ai-output-judge`)
states outright that it has **no results yet**. Quote it as a claim, never as a measurement.

## 2. What ports to abcc, and what does not

### 2.1 The probability does not port, and this is settled rather than uncertain

| finding | what it says |
|---|---|
| **F386** | LM Studio's proxy **DROPS `logprobs`** at HTTP 200 — no key, no warning. |
| **F387** | Under MTP the array is complete, well-formed, in range and **91.6% FABRICATED**. Array length equals `completion_tokens` on 29 of 29 fabricated calls. |
| **F388** | The bare server refuses `logprobs` + `tools` + `stream` with **HTTP 400**. |
| **F389** | A real logprob costs **1.18x decode** and forbids streaming. |

**W4 ruling 7 already says it: 2.0 reads no logprobs.** A local `noul` returning `0.92` would be a
number with no calibration behind it, which is worse than no number — it is F531's failure mode
wearing a decimal point.

⚠ **And the hosted API does not port either**: zero cloud spend is standing (David, 2026-08-07).

### 2.2 The typed question ports, and the machinery is already in the tree

`abcc-engine` sends `response_format: json_schema` with `strict: true` (ADR-0011 §3), and
`judge::REVIEW` is already a constrained schema. What the judge is not is **decomposed**: it asks
one open question — *assess this, give up to five findings* — where Jev asks N independent typed
ones, each with its own per-answer criteria.

## 3. 🚨 THE CONTROL THAT HAS TO RUN FIRST — every judge floor predates the seed

`turn.rs:988`:

    fn seed_for(attempt: AttemptId, posting: Posting, round: u32) -> u32

The three inputs are the attempt id, the **head's charter digest**, and the round.
`Posting::digest()` is the SHA-256 of `Posting::prefix` — a `&'static str` computed once per
process. **The brief is not an input.**

`GATE-P4` and `GATE-P6` each say, in their own text: *"Nothing here samples at temperature zero —
the engine sends no temperature, no top_p and no seed."* That was true when they ran. **`223ae3a`
changed it**: `openai.rs:928` now sends `seed` on every call.

Two consequences, and both are large:

1. 🚨 **Every noise floor this project owns was measured before the seed existed.** `GATE-P4`'s
   *27 of 121 trees change when nothing changes*; **F575**'s 41 → 50; **F576**'s sign reversal on
   shams; **F577**'s 1 / 0 / 9 on hedging. All four are pre-`223ae3a` numbers, and all four are
   load-bearing — F576 is the finding that killed the scope sentence.
2. ▶ **Arms of a brief-level probe now draw the SAME seed per tree.** What differs between `off-a`,
   `off-b` and `on-a` is the brief, and the seed ignores the brief. So the floor arm becomes a test
   of server determinism at a fixed seed, and the treatment arm becomes **paired at matched seed** —
   which is the variance reduction Jev is selling, available here for free.

⚠ **This does not mean the floor collapses to zero.** F716: *a seed does not pin this stack — say
attributable, never reproducible.* The floor is **unmeasured**, not **absent**. One 72-tree `off-b`
arm on the OD tier answers it in about 77 minutes at the wall clocks `GATE-P6` recorded.

⚠ One assumption to check before quoting consequence 2: `corpus_review.rs` builds its id as
`AttemptId::at(Seq::new(n))` over the dossier index, so the arms collide on seed only if they
iterate the dossier directory in the same order. That is a five-minute check and it has not been run.

🚨 **Nothing in section 4 should be measured until this floor is re-measured**, for the reason
`GATE-P6` §3 gives: without it, this project would have reported a 24% lift that did not exist.

## 4. The design — what a typed judge looks like here

### 4.1 The joint it fixes is F580, and F580 is the project's own caveat

`hedges_on_scope` (`corpus_review.rs:342`) is a **case-folded substring scan for 15 phrases** —
`cannot verify`, `no visibility`, `outside the diff`, `beyond the diff` — over the assessment plus
each finding's `defect` line. `GATE-P6` §4 says what that costs:

> 🚨 **What it detects is an utterance.** It cannot distinguish a judge that located the gap from
> one that recited a caveat. **F577 and F578 are results about what the judge said, not about what
> it understood**, and every sentence quoting them must carry that.

**F577 is the only statistic in three judge probes that cleared its own floor** — by 9x — and it is
measured by grepping prose. That is the joint.

### 4.2 The change: typed fields beside the prose, not instead of it

Add to `judge::REVIEW`, leaving `assessment` and `findings` exactly as they are:

    "coverage": { "type": "string",
                  "enum": ["complete", "incomplete", "cannot_tell_from_what_i_was_shown"] },
    "not_reached": { "type": "array", "maxItems": 5, "items": { "type": "string" } }

`not_reached` is *what the change does not reach*, named — a path, a symbol, a consumer. It is
`maxItems`-bounded for ADR-0008's reason: **an unbounded array is the shape that ran into the token
cap**, 17 of 57 calls.

Three things this buys that prose cannot:

1. **The hedge stops being an utterance.** `coverage == "cannot_tell_from_what_i_was_shown"` is a
   value. F578's shape-selectivity becomes a 3×3 confusion matrix over `inside` / `outside_cover` /
   `outside_file` instead of a keyword count.
2. **F579 becomes checkable.** Two of nine hedges landed on `correct` trees, where the patch *is*
   the full refsol and there is no gap. A hedge that **names files** can be scored against the
   answer key mechanically; a hedge that names none is a caveat. Today both read identically.
3. **The criteria get a home.** Jev's per-answer `criteria` map is the one part of its request
   shape with no analogue in `brief`. Writing out what `complete` means, and what
   `cannot_tell_from_what_i_was_shown` means, is the scope sentence **expressed as a rubric on a
   value** rather than as one more sentence of prose competing with the rest of the brief.

### 4.3 🚨 What this does NOT change, and must not

**The Judge still does not vote.** A typed field attaches through `Report::note` exactly as a
`Claim` does, touches no `Outcome` and therefore no `Headline`, and there is still no function in
the workspace that converts either into one. `AttemptPhase::may_refuse` stays `!uses_model()`.
ADR-0008's line is unchanged:

    Accept  <=>  structural AND acceptance AND NOT Veto     (every one of them Measured)
    Judge   ->   a report attached to the attempt, never a term in the conjunction

⚠ **A typed verdict is more tempting to wire than a prose one, and that is the risk this section
exists to name.** `coverage: "incomplete"` reads like a gate input in a way that a paragraph does
not. It is not one. The enforcement is the same as today's and it is structural rather than a
convention: **making the model's opinion count would be a new function somebody has to write,
rather than a flag somebody can flip.**

## 5. What it costs

ADR-0008 measured constrained output at **2.8× the decode, 2.7× the wall clock, and 17 of 57 calls
lost to the token cap**. Two enum fields and one bounded array of five short strings is a small
addition to a schema that already carries a five-element array of five-field objects — but *small
addition* is a prediction, and the falsifier is the same one as before: a call that ends
`Why::TruncatedAtCap`. ⚠ **The `ending` column already reports it**; `GATE-P6` ran 216 calls with
**zero** endings other than `answered`, so there is a clean baseline to compare against.

⚠ **No `description` strings in the schema** — ADR-0008's rule, because a schema on this stack
becomes a decoding grammar and it is not established that the model ever reads one. The criteria go
in `brief`, where they are certainly read.

## 6. The arms, if it is measured

The rig exists. `corpus_review.rs` is restartable, skips a dossier whose review file exists, and
already takes `ABCC_JUDGE_RUNGS` and `ABCC_JUDGE_SCOPE`. A third switch is the whole of the harness
work.

| arm | brief | schema | what it answers |
|---|---|---|---|
| `off-b` (**first, alone**) | shipped | shipped | §3 — is there still a floor once the seed is wired? |
| control | shipped | shipped | the comparison baseline |
| treatment | + criteria | + `coverage`, `not_reached` | does the typed field beat the grep? |

⚠ **The treatment changes two things at once** — a schema field and a paragraph of criteria — and
`ScopeNote`'s doc comment already states the rule it breaks: *a probe that changes two things at
once measures neither.* If the floor in §3 comes back small enough to afford four arms, split them.
If it does not, the honest report is that the two were varied together.

🚨 **The arm that can refuse this is `correct`, not the shams.** An instruction to name what a change
does not reach is an instruction that can manufacture incompleteness on a tree that is fine. F579
already caught the shipped brief doing it twice in nine. **Precision is the cost this has to be
measured for**, and the 83 `correct` trees are where it is visible.

## 7. What would falsify the design

* `coverage` and the prose hedge agree on every tree. Then the typed field is a re-encoding of the
  grep and buys nothing but tidiness.
* `not_reached` comes back empty whenever `coverage` is not `complete`. Then the judge is still
  reciting a caveat, and the type made the recitation easier to count rather than rarer.
* The `correct` arm's precision drops outside its own floor. Then it costs operator minutes, which
  is the number W13 grades this project on, and ADR-0008's falsifier has fired.

## 8. Findings this session wants to file

* **F825** — the seed is derived from `(attempt, charter digest, round)` and **not** from the brief,
  so every judge noise floor in `GATE-P4` and `GATE-P6` predates `223ae3a`, and brief-level arms now
  collide on seed. Read from `turn.rs:988`, `head.rs:334` and `openai.rs:928`.
* **F826** — `read_file` whole-file reads are **54.1% of calls and 92.5% of bytes** (235 calls /
  3,195,864 B against 199 / 259,456 B), so a ranged read averages 1,304 B against a whole-file
  read's 13,599 B — **10.4×**. On claudette alone whole-file is 70.1% of calls and 92.1% of bytes.
  ▶ This reframes P16's change 2: the 64 KiB cap bit twice in 422 calls because a 1,623-line file
  **fits under it** and still eats the window. The lever is making the whole-file read the
  exception, not raising the cap.
  ⚠ Recovered from the `output` header (`{path} lines {from}-{to} of {total}`), **not** from
  `arguments`, which F505 logs only on failure — 4 of 1,959 read_file calls.
