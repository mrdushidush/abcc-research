# W4 — Routing, escalation and the complexity model

**Status: OPEN — started 2026-08-25, items 1 and 2 of 6 closed.** §14 orders W4 after the
W3 + W6 + W11 block, and that block closed on 2026-08-25 (`d3a17a5`). Findings continue the family
numbering from **F360**; the workstream now runs to **F375**. Built one item at a time in §13
format.

Planned items:

1. ✅ **The complexity model, run** (F360–F367) — §11's first two bullets: *"How well did V1's dual
   assessment actually work?"* and *"Does the Campbell-derived complexity model survive into 2.0, and
   does it need rescaling now that the base agent is far stronger?"* Answered by executing both
   donors' scorers over **149 real coding tasks** and joining the result to **952 measured agent
   attempts**. The answer is not a rescaling.
2. ✅ **Difficulty, context and cost as three axes** (F368–F375) — §11's *"Separate the two things
   V1 conflated: task difficulty and required context length"*, plus the cost-model bullet. The two
   axes are genuinely independent and neither is routable: required context is not a property of the
   request at all (ρ = +0.048 against the workspace's bytes, +0.836 against the rounds the agent
   actually ran), the constant F363 found was a fact about donor fixtures, and the only rung the
   budget can buy is another attempt — priced, with its yield curve and its stopping rule.
3. ⬜ **The estimator: rules, a recorded model reading, or neither** — **OQ-W6-7**, twice deferred.
   §11's *"Whether the Haiku semantic assessment pass is still worth paying for, or whether the local
   base agent can now score complexity itself for free."* Item 1 changes this question's shape: see
   F366.
4. ⬜ **Confidence signals on worker output** — §11's *"logprobs, self-critique, test results, static
   analysis. Which correlate with real quality?"* W6 items 4, 5 and 7 have already answered three of
   the four on 728 real attempts; logprobs are untouched, and item 1's F362 says the strongest
   available signal is neither.
5. ⬜ **The escalation ladder, retry budgets and circuit breakers** — §11's *"circuit breakers for the
   failure mode where escalation loops burn more than doing it right the first time."* Inherits W11
   item 5 (count rounds, one budget with per-stage breakers, exhaustion classified and never
   `Ok(())`) and item 1's F367, which found that the ladder the brief points W4 at has no callers.
6. ⬜ **A fine-tuned router or worker** — §11 says *"Expect no for now, and say why."* The why has to
   be priced, not asserted.

Scope reference: `RESEARCH_BRIEF.md` §11 lines 731–771. 🚨 The workstream's opening instruction —
*"Start with data you already own… mine all of it"* — **is struck through in the brief itself**
(superseded 2026-08-07): v1's Postgres holds 9 days, `token`/`cost`/`model_used` were never written,
and 137 of 182 scored tasks carry the default complexity of 5.0. `prestudy/data-assets.md` §5. The
mining is not scheduled and this document does not do it. What replaces it is this project's own
substrate: **1,383 measured cells with an answer key**, which is the retrospective correlation §11
asked for, on a corpus where the outcome is known rather than absent.

The numbering is one sequence across all workstreams — check the maximum before adding, not the last
number in this file (`grep -rho "F[0-9]\{2,3\}" research/*.md | sort -u | sed 's/F//' | sort -n | tail -3`).

---

# Item 1 — the complexity model, run

## Question

§11 hands W4 a scale and asks whether it survives:

> *How well did V1's dual assessment actually work? Judge the rule-based plus Haiku weighting
> retrospectively against downstream retry and escalation rates. The 88 percent local routing figure
> is a claim; verify it from the logs.*
>
> *Does the Campbell-derived complexity model survive into 2.0, and does it need rescaling now that
> the base agent is far stronger? A task that was C7 for a 7B may be C3 for a 35B-A3B. The whole
> scale may need recalibrating, and that is a finding worth having.*

Both sentences assume the scale **works and is mis-calibrated**. That assumption is the thing to test
first, because it decides what item 3 is even for. If the scorer separates hard tasks from easy ones
and merely puts the boundaries in the wrong place, then W4's job is arithmetic: move the thresholds
and keep the model. If it does not separate them at all, then no threshold exists to move, and
rescaling is a way of spending a workstream on an instrument that reads a constant.

The logs §11 wants verified are gone. What this project has instead is better: **952 Q56 cells and
251 U100 cells**, every one an unimpeded or deliberately-interfered-with agent attempt at a real
coding task, with a hidden-test verdict attached. That is a retrospective correlation with an answer
key, which is what the brief wanted and could not have.

Three parts.

1. **What score does the donor's own code give a real task?** Not a reading of the algorithm — the
   compiled function, called.
2. **Does that score predict anything that matters?** Outcome, cost, context, iterations — stratified
   by arm: 672 of the 952 Q56 cells are non-control, and 560 of those come from arms built to stop
   the agent editing, so a pooled rate over them is a claim about the arm (memory items 26, 28, 31).
3. **What does the arithmetic of the dual assessment do**, given the scores the rules actually
   produce? F221 established the ratchet on paper. This puts real numbers in it.

## Method

Nine scripts in `research/spikes/w4-router/` (see its README for the file map, the regeneration
commands and the six traps that bit). Both donor scorers are **executed** rather than paraphrased —
one imported compiled, one sliced out of its source by byte range; everything else is arithmetic over
what they and the harness produced. No GPU: nothing in this item asks a model anything.

- **v1's scorer, imported and called.** `score_corpus.mjs` imports
  `packages/api/dist/services/taskRouter.js` from the v1 donor and calls
  `TaskRouter.prototype.calculateComplexity` — the same function `routeTask()` calls at
  `taskRouter.ts:290`. The compiled body was read against `taskRouter.ts:105-239` statement by
  statement before it was trusted; they agree. Every task in `corpus/suites/{q56,u100,k}` is scored
  with `taskType: 'code'` and `currentIteration: 0`, which are its routing-time values, and also
  without the title and without the task-type constant, so the text's contribution is separable from
  the constants'. **Note the loader prints Prisma errors to stdout** — it reaches for `localhost:5432`
  on import through `budgetService` — so the reader filters to lines beginning `{`.
- **BCF's scorer, extracted verbatim and compiled.** `build_bcf_scorer.py` slices `fn rule_score` and
  `fn detect_language_hint` out of `battle-command-forge/src/router.rs` **by byte range**, asserts the
  slice is a substring of the donor file, and writes them into a throwaway crate with a stdin driver.
  Donor sha256 `5263aeaf87…`, `rule_score` = lines 147–309, `detect_language_hint` = lines 312–322.
  What runs is the donor's code, not a transcription of it. `bcf_run.py` feeds it the same 149
  prompts the way BCF's own call site does — one prompt, no title (`mission.rs:268`).
- **The outcomes.** `join.py` and `analyze.py` read `runs/q56/w8-*/cells.jsonl` — **8 runs, 952
  cells**, one subject (`claudette-af3f804`), one held config (champion `qwen3.6-35b-a3b-mtp@iq3_s`,
  `num_ctx` 61440, `num_predict` 8192, `max_iterations` 40). `runs/q56-degraded` is **excluded**: it
  is a different configuration. Everything is computed per arm as well as pooled, and both are
  printed.
- **The context axis, recovered.** ⚠ `tokens_in` in `cells.jsonl` is **session-cumulative prompt
  tokens summed over iterations** (`harness/crates/w8-run/src/result.rs:1-12`) — a cost number, not
  an occupancy number — and `peak_prompt_tokens` is **absent from every Q56 cell**, because those
  runs' subject descriptor declared no context-estimate capture group. The datum is still in the
  transcripts: the turn-end marker carries the subject's own gauge, `ctx ~N/60k`.
  `ctx_recover.py` parses it from all 952 transcripts and adds back the run's measured
  `preamble_tokens_in`. **The result is a floor and never the peak**, for the four reasons the
  harness documents at `main.rs:966-977` — the gauge omits the system prompt and tool schemas, the
  preamble is itself a lower bound, granularity is 1,024 tokens above 1k, and it is a chars/4
  estimate against a corpus that measures ~3.39 chars/token. All four understate, so a threshold it
  says was crossed **was** crossed. Q56 tasks are one turn and context grows monotonically within a
  turn, so the turn-end gauge is that cell's peak.
- **The unanchored matcher.** `anchor_probe.mjs` finds every keyword hit that is not a standalone
  word and classifies it three ways before counting anything as a defect — `INFLECTION` (keyword at
  word start plus a known English suffix: "returns" for `return`), `COMPOUND` (keyword at word start,
  other letters after: "checkbox" for `check`), `EMBEDDED` (keyword does not start the word:
  "capitalized" for `api`). **Only EMBEDDED is counted.** A cruder anchored rule manufactures a
  defect out of morphology, which is memory item 30's failure mode exactly, and it did: the first
  version of this probe reported 75 spurious hits and 13 tier changes. The classified version reports
  21 and 2.
- **The ratchet.** `ratchet.py` evaluates `complexityAssessor.ts:137-154`'s three branches over the
  149 real rule scores × the 10 answers the model half can give, and asks what final score is
  reachable.

Donor commits: v1 `d5528ea`, BCF `d6c1601`. The 8 Q56 runs span three corpus commits
(`de26d3d`, `665038b`, `0766e6d`); **no `prompt.txt` in either suite changed across them or since**
(`git diff --name-only de26d3d HEAD -- corpus/suites/*/tasks/*/prompt.txt` is empty), so scoring the
working tree scores the bytes the agent was actually given.

## Inherited

| What | Source | Verdict here |
|---|---|---|
| The dual estimator is a **one-way ratchet**: model taken outright at ≥2 above, floored at the rule score when close, damped to 40% at ≥2 below | W6 item 2, F221 | **CONFIRMED and it is worse than "one-way"** — with the rules pinned ≤6 on every real task the outright branch is the **normal** case, 53.8% of the grid, and the median task loses it at a model answer of 6 (F366) |
| Complexity **lowers** the review bar (9.2 / 8.5 / 8.0 by tier), and every one of those numbers is void | W6 items 1–2 | **STANDS** — and F361 removes the input as well as the output: there is no complexity signal left to scale a bar with |
| Grep the **readers** of any tier you inherit; v1's frontier review tier fires 0 times in 30 | W6 item 7, F347 | **BIT AGAIN, one layer up** — `getFixDecision`, the whole documented escalation cycle, has **no production caller at all** (F367) |
| A pooled rate can invent a finding that stratification denies; 448 of 728 Q56 cells come from arms built to stop the agent editing | memory items 26, 28, 31 | **HELD** — every correlation in F361 is reported per arm; none of the four arms rescues the score |
| A checker's yield is a measurement of the checker | memory item 30 | **BIT, and was caught** — the crude anchored matcher reported 3.6× the false fires and 6.5× the tier changes of the classified one (F364) |
| The 88% local-routing figure is a claim | §11 | **VOID as evidence** — the rules route 100% local on 149 of 149 real tasks by construction (F360), so the figure measures the corpus, not the router |
| Prompt-cache: one token changed at the front annihilates 79.7% of TTFT; a head rewrite costs 4.60× | W2 F81, W11 item 2 | **CARRIED to item 2** — it prices the context-tier decision F363 makes available |

## Findings

### 🚨 F360 — v1's scorer, run over 149 real coding tasks, puts 149 of them in the bottom tier: the rule half is not a router, it is a floor

`score_corpus.mjs` calls the donor's own compiled `calculateComplexity` on every task in the three
corpora — 56 Q56, 90 U100, 3 K — at the inputs `routeTask()` would supply.

| | n | min | median | max |
|---|---|---|---|---|
| Q56 | 56 | 1.5 | 2.5 | **4.5** |
| U100 | 90 | 1.5 | 3.5 | **6.0** |
| K | 3 | 4.0 | 4.0 | 6.0 |
| **all** | **149** | **1.5** | **3.5** | **6.0** |

Against v1's own ladder (`taskRouter.ts:18-24, 356-401`):

| tier | what it buys | tasks reaching it |
|---|---|---|
| C1–C6 → local Ollama, 16K context | the default | **149 / 149** |
| C7–C8 → 32K context, remote if configured | context headroom | **0** |
| C9 → 32K | more headroom | **0** |
| C10 → Sonnet | the only paid rung | **0** |

**Not one real task in this project's entire corpus reaches the second rung.** The escalation ladder
above the default is not merely rarely used; on 149 tasks it is unreachable from text. Nothing in the
scorer's four sections can produce a 7 from a prompt a person would actually write: the semantic
tiers cap at +4, the structural section needs seven numbered steps and three distinct file
extensions, and the base is 1.

Two consequences, and the second is the one that matters.

- **§11's "88 percent local routing" is not evidence about a router.** A scorer that emits ≤6 on
  every real task routes 100% local before any model is consulted. The figure is a property of the
  task mix, and 12% of v1's traffic went non-local for some other reason — which F366 identifies.
- **The rule half contributes a floor and nothing else.** Every routing decision above the bottom
  rung in v1's production history was the *model's* opinion, arriving through a blend that F221
  showed can almost only push up. This inverts the brief's framing: the question is not whether the
  Haiku pass is *worth paying for* alongside the rules. It is that the Haiku pass **was** the router.

### 🚨 F361 — and the score predicts nothing: |ρ| ≤ 0.21 against outcome, cost, context and iterations, in all four arms

952 cells, joined to the score of the task each ran. Spearman's ρ, per arm, per outcome:

| arm | cells | pass rate | tokens_in | peak occupancy | iterations | wall clock |
|---|---|---|---|---|---|---|
| control | 280 | **−0.101** | −0.091 | −0.072 | −0.100 | +0.002 |
| gated | 112 | +0.016 | +0.047 | +0.129 | −0.014 | +0.098 |
| redirect-first-edit | 280 | +0.117 | +0.083 | +0.206 | +0.063 | +0.119 |
| deny-first-edit | 280 | +0.023 | +0.017 | +0.109 | +0.007 | +0.133 |

Nothing reaches 0.21. On the control arm — the only one that measures the agent rather than the
interference — the pass-rate correlation is **negative**: a higher complexity score goes with a
marginally *better* outcome. Stratification does not rescue it, which is the point of doing it: this
is not a pooled rate hiding a real effect in a subgroup.

The task-level view is starker than the coefficient.

| task | control pass | v1 score | BCF score | lang | kind |
|---|---|---|---|---|---|
| **Q03** | **0 / 5** | **1.5** (corpus minimum) | 3 | rust | bugfix |
| Q46 | 1 / 5 | 1.5 | 2 | shell | boundary |
| Q05 | 2 / 5 | 3.5 | 4 | rust | error-handling |
| Q25 | 2 / 5 | 1.5 | 2 | python | api-misuse |
| Q51 | 2 / 5 | 3.5 | 4 | python | implement-spec |
| Q52 | 2 / 5 | 3.5 | 5 | rust | implement-spec |
| Q07 | 3 / 5 | 4.0 | 4 | rust | api-misuse |
| **Q22** | **5 / 5** | **4.5** (corpus maximum) | 4 | python | concurrency |

**The only task in the battery that never passes carries the lowest score in the corpus; the task
with the highest score passes every time.**

By the donor's own task `kind`, the ordering is inverted against the score:

| kind | control pass | mean v1 score |
|---|---|---|
| bugfix | 80.0% (24/30) | 2.58 |
| api-misuse | 83.3% (25/30) | 2.17 |
| implement-spec | 85.6% (77/90) | 2.64 |
| error-handling | 88.0% (22/25) | 3.00 |
| boundary | 88.6% (31/35) | 1.79 |
| multi-file | 90.0% (18/20) | 2.50 |
| refactor | **100%** (20/20) | 2.62 |
| **concurrency** | **100%** (10/10) | **4.00** |
| perf | **100%** (20/20) | 2.75 |

`concurrency` scores highest and never fails. `bugfix` scores mid and fails most. The scorer's
keyword list contains `'concurrent'`, `'parallel'` and `'async'` in its **high** tier and nothing
whatever for *"this code is already wrong and you have to find out why"*, which is the shape that
actually breaks the agent — and which W6 item 7 independently identified as the boundary class
(F336: the axis is whether the ticket's own words decide the failing input).

On U100 the sign is worse and the sample is small: over the 10 distinct U100 tasks with cells,
ρ(v1 score, failure) = **−0.465**. **n = 10 tasks**, so this is a direction and not a magnitude — but
it is the wrong direction, and it is the stronger of the two.

**Answering the brief directly: the Campbell-derived model does not need rescaling. Rescaling relocates
boundaries on an axis that carries no signal.** A task that was C7 for a 7B is not C3 for a 35B-A3B;
it was never C7, because the scorer cannot emit a 7.

### 🚨 F362 — what does predict failure is measured effort, and every one of those signals arrives after the routing decision

Same 280 control cells, per task, against the control failure rate:

| candidate | ρ with failure | available before the attempt? |
|---|---|---|
| **peak prompt occupancy** (recovered floor) | **+0.405** | no |
| cumulative prompt tokens | +0.326 | no |
| iterations | +0.320 | no |
| BCF's `rule_score` | +0.219 | **yes** |
| prompt word count | +0.187 | **yes** |
| **v1 complexity score** | **+0.101** | **yes** |

Every signal a router can see before dispatch sits below every signal it can only see afterwards, and
the gap is roughly 2×. Among the three a-priori ones, **v1's scorer is last** — beaten 1.9× by
counting the words in the prompt, which costs nothing and needed no keyword list, and 2.2× by the
successor's variant of itself. The three strongest are all observations of the attempt in flight, and
they are ordered the way effort is: how big the context got, how many tokens it cost, how many turns
it took.

This is the item's design consequence and it is larger than the calibration question §11 asked.
**Routing is not a prediction problem.** The prediction is available and it is worth ρ ≈ 0.1; the
observation is worth ρ ≈ 0.4 and it costs nothing but reading a counter the harness already keeps.
2.0 should dispatch every task at the bottom rung and spend its budget on **deciding when the attempt
in front of it has gone wrong**, which is a measurement, not an estimate. That is the same shape W6
item 4 arrived at from the other side — the gate is a conjunction of cheap vetoes over a real
attempt, not a ladder of static analysis run before one.

⚠ The honest caveat, stated because it bounds the claim: +0.405 is a correlation between *effort* and
*failure* on tasks the agent mostly passes (247 of 280 control cells pass, 88.2%). It says a struggling attempt
looks different from a smooth one. It does **not** say a threshold on occupancy is a usable circuit
breaker — item 5 has to establish that separately, and W11 item 5 already found that above the
binding point the model stops on its own judgement with 25 rounds unspent (F296).

### 🚨 F363 — difficulty is not context, and context is very nearly a constant: 0 of 945 cells exceed 16K, and 83% of the peak is the preamble

`ctx_recover.py` over all 952 Q56 transcripts; 945 carry a turn-end marker.

| | tokens |
|---|---|
| minimum peak occupancy (floor) | **5,201** |
| p50 | **5,898** |
| p90 | 7,948 |
| maximum | **13,066** |
| median preamble (system prompt + tool schemas) | **4,874** |

| v1 context tier | cells whose floor exceeds it |
|---|---|
| 8K — *deprecated by v1 as "insufficient for complex multi-component projects"* | **74 / 945** |
| 16K — v1's C1–C6 default | **0 / 945** |
| 32K — v1's C7+ tier, the thing complexity buys | **0 / 945** |
| 61,440 — this run's actual `num_ctx` | 0 / 945 |

Three things follow.

1. **The 32K tier buys nothing measurable.** The rung the complexity score exists to unlock is not
   reached by any of 945 real attempts, by a floor that understates four ways. v1's own deprecation
   of 8K is the one boundary with any bite, and it bites 7.8% of cells.
2. **83% of the peak prompt is fixed overhead.** The median cell's occupancy is 5,898 tokens of which
   4,874 is the preamble — the system prompt and the tool schemas, identical in every cell. The
   *task's* share of context is a median of ~1,024 tokens and a maximum of ~8,200. Routing on "how
   much context does this task need" is routing on 17% of the number, and W2's F81 already
   established that the other 83% is the part you must never touch, because one token changed at the
   front annihilates 79.7% of TTFT.
3. **The axis with real dynamic range is cost, and it is a different axis.** Cumulative prompt tokens
   over the same cells run **15,399 → 445,661**, a 29× spread against occupancy's 2.5×. The maximum
   cost is **34× the maximum occupancy**. The two are rank-correlated (ρ = +0.892 — both grow with
   iteration count) but they are not one quantity, and v1 mapped both onto a single 8K/16K/32K knob.
   Complexity predicts neither (ρ = −0.091 against cost, −0.072 against occupancy).

**§11's instruction to separate difficulty from required context length is right, and the separation
has a surprising shape:** required context is not a routing dimension at all on this workload. It is a
constant plus noise. The dimension that varies is *how much work the attempt turned out to be*, which
is F362's finding and is not knowable in advance.

🚨 **QUALIFIED IN PLACE BY F368 AND F369 (item 2, 2026-08-25). Read those before quoting this.**
Two corrections, neither of which moves the headline. (1) **The word "floor" is wrong.** Calibrated
against the server's own tokenizer — `tokens_in / iterations`, an exact real-token lower bound on the
peak — the recovered number sits **below** that bound on **61 of these 945 cells**. It is an estimate
good to about ±10–20%, not a bound; and all 12 cells in this project with no occupancy sample at all
are **timeouts**, so the population excludes the longest-running cells. On the exact bound, 0 of 945
still exceed 16K; under a linear growth model, 2 of 945 do and the count above 8K rises from 74 to
158. (2) **The constant is the fixture's.** On the K suite — 42 KB fixtures instead of 415 bytes —
the same agent runs at p50 **16,125** and 8 of 18 champion cells cross 16,384. "Context is a
constant" is a statement about donor fixtures, not about agent work.

⚠ Scope, because this number is a floor and its population is one suite: 945 cells of **one subject**
on **one battery of single-turn tasks**. Q56 tasks hand the agent a small fixture and one prompt. A
multi-turn session on a large repository is a different measurement and this says nothing about it —
the K suite exists to probe that regime and its three tasks are the only cells in this project that
carry `peak_prompt_tokens` natively. Item 2 owns extending this.

### F364 — the unanchored matcher is real, nearly harmless, and one of the brief's two examples cannot fire at all

§11 tells W4 to *"fix the unanchored `text.includes()` matching — `'api'` fires inside "rapid",
`'add'` inside "address""*. Measured over the 149 prompts, classifying each substring occurrence
before counting it:

| class | occurrences | counted as a defect? |
|---|---|---|
| INFLECTION — `return` in "returns", `handle` in "handled" | 67 | no: a keyword scorer means to catch these |
| COMPOUND — `check` in "checkbox", `handle` in "handler" | 56 | no: arguable either way |
| **EMBEDDED — the keyword does not start the word** | **21** | **yes** |

21 false fires, in **16 of 149 tasks**. Once they are dropped, **2 tasks** change their semantic tier
score: Q56/Q07 and U100/coffee\_about, both 2 → 0.

The false fires, all of them:

| keyword | tier | inside |
|---|---|---|
| `add` | low | padded, padding, onadd (×6) |
| `handle` | moderate | errorhandler, notehandlers (×3) |
| `api` | high | **capitalized, escaping** (×2) |
| `graph` | high | **paragraph** (×2) |
| `component` | high | decodeuricomponent |
| `parse` | moderate | queryparser |
| `write` | low | overwrites |
| `print` | low | sprintf |

**The brief's first example cannot move a score.** `'add'` is in the `low` keyword tier — and
`complexityIndicators.low` is **defined at `taskRouter.ts:143` and never read**. The scoring block
reads `.extreme`, `.high`, `.moderate` and `.trivial` (lines 175–190) and never `.low`. One of the
five documented tiers, seven keywords wide, contributes nothing. That is why `add`/`write`/`print` —
the three loudest sources of substring noise — are also the three that cost nothing.

**The brief's second example is real and it points the wrong way.** Q07's entire semantic tier score
is `'api'` matching inside *"…fussy about how words are separated and capitalized"*. Anchoring the
matcher takes Q07 from **4.0 to 2.0** — and Q07 is one of the eight hardest tasks in the battery
(3/5). Fixing the defect the brief names makes the score *less* correlated with difficulty on that
task, which is what F361 predicts should happen when you polish an instrument that reads noise.

The defect is real and should not be ported. It is not, on this evidence, worth calling a cause of
anything.

### 🚨 F365 — BCF's port reaches its second tier on 20 of 149 tasks, and 18 of the 20 come from one line that is not the complexity model at all

The vendored `rule_score`, run on the same 149 prompts the way `mission.rs:268` calls it:

| BCF tier | tasks |
|---|---|
| C1–C3 Trivial | 56 |
| C4–C6 Moderate | 73 |
| **C7–C8 Complex** | **20** |
| C9–C10 Expert | **0** |

BCF's port therefore does what v1's cannot — it reaches a second tier — and it does so almost
entirely through a rule that has nothing to do with Campbell:

```rust
// Web project boost (HTML/CSS usually need more files/context)
if text.contains("html") || text.contains("landing page") || text.contains("website") {
    score = score.max(7.0);
}
```
`battle-command-forge/src/router.rs:303-306`

**18 of the 20 tasks that reach C7 are floored there by that line.** The remaining two —
`k/finish_the_cancelled_status` and `u100/py_todo_handlers` — reach it by accumulation. Strip the
floor and the successor's ladder collapses to v1's: two tasks above the bottom two tiers, out of 149.

And the floor fires on the **easiest** class of work in the corpus. Of the U100 tasks with measured
cells, the html-floored ones pass **14/15 (93.3%)** against **126/140 (90.0%)** for everything else.
The single rule in the entire inherited family that ever routes a task upward selects for tasks the
agent almost never fails.

BCF's scorer is nonetheless the better of the two at the thing both are for: ρ(BCF score, Q56 control
failure) = **+0.219** against v1's **+0.101**, and it is the best a-priori signal measured in this
item — narrowly ahead of counting the prompt's words (+0.187), which is most likely *why*: BCF adds
a **length rule with thresholds this corpus actually crosses**. Both donors have one; the thresholds
differ and the corpus decides. Prompt lengths here are min 28 words, median 77, max 228:

| rule | fires on |
|---|---|
| BCF `word_count > 50 → +1`, `> 100 → +2` (`router.rs:286-292`) | **127 / 149** |
| v1 `wordCount > 100 → +0.5`, `> 200 → +1` (`taskRouter.ts:221-223`) | **36 / 149** |

BCF's length term is live on 85% of the corpus and v1's on 24%, which is the mechanical reason the
successor's variant is the better of the two — it is measuring the prompt's size, which F362 says is
the strongest a-priori signal there is. It is still less than half the weakest in-flight one.

Two further donor facts, since they are what a port would inherit: BCF's `extreme` list contains the
bare word **`'project'`** (+3 on a single hit), and `detect_language_hint` adds +0.5 for Rust, Go or
TypeScript — so the same task described in two languages routes differently, which is a claim about
the *model's* competence that no one measured. This item's own control arm says the champion passes
**78.6% of Rust tasks against 95.6% of TypeScript ones**, so the sign of BCF's modifier is right and
its magnitude is invented.

### 🚨 F366 — v1's "dual assessment" is the model's score with a floor under it: the model half is called on 149 of 149 tasks and taken outright on 53.8% of the grid

F221 established the ratchet's shape. With F360's real rule scores in it, the arithmetic
(`complexityAssessor.ts:137-154`) is no longer a bias — it is the whole mechanism.

- `routeTask()` calls the model half whenever the rule score is **≤ 8** (`taskRouter.ts:297`). The
  rule score never exceeds 6. **The gate never blocks: 149 of 149 tasks pay for the model call.** It
  is not an occasional refinement for ambiguous cases; it runs on everything.
- Over the 149 × 10 grid of (task, model answer): the model's score is **taken outright 53.8%**,
  averaged 35.6%, damped toward the rules 10.6%.
- The model answer at which it wins outright: **min 4, median 6, max 8**. For 116 of 149 tasks, a
  model answering "6" — the middle of its own prompt's scale, where `complexityAssessor.ts:53` says
  *"6-7: Moderate (multiple files, external APIs, error handling)"* — **takes the decision entirely**.
- What the rules alone guarantee, i.e. the final score when the model answers 1: median **2.5**.
- Every tier above C6 is reachable for **149 of 149** tasks — but only through the model. Rules-only,
  it is 0 of 149 (F360).

**So the answer to *"is the Haiku semantic assessment pass still worth paying for"* is that the
question is mis-posed.** There is no rules-plus-model system to trade off. There is a model estimate
with a floor of median 2.5 under it, called on every task, whose output is a number nobody ever
checked against an outcome — and F361 says that when you do check the rules half against an outcome,
it is worth ρ = 0.1.

This is what OQ-W6-7 has to answer, and item 1 narrows it to a real choice: **not "rules or rules plus
a model", but "a recorded model reading, or no estimate at all"** — with F362 saying that whatever is
recorded should be a *report* rather than a *gate*, which is exactly W6 item 7's ruling one layer up.

### F367 — the escalation ladder §11 points W4 at has no production caller

`taskRouter.ts:35-38` documents the cycle in the file's own header:

> `FIX/ESCALATION CYCLE:` · `Ollama fails/bad review → Haiku retries with context` · `Haiku fails/bad
> review → Human escalation` · `Sonnet fails/bad review → Human escalation`

It is implemented at `taskRouter.ts:478` as `getFixDecision(failureCount)`, with four unit tests that
all pass. Grepping the readers across the whole of `packages/`:

| method | production callers | test callers |
|---|---|---|
| `getFixDecision` | **0** | 4 |
| `getDecompositionDecision` | **0** | 4 |
| `getReviewDecision` (TaskRouter's) | **0** | 2 |
| `calculateComplexity` | 2 (`queue.ts:279`, `trainingDataService.ts:67`) | — |
| `routeTask` | 3 | — |

The escalation that actually runs in v1 is somewhere else entirely, in **four separate services**:
`asyncValidationService.ts:204` ("Phase 2: Haiku escalation"), `autoRetryService.ts:208` ("Phase 3:
Haiku escalation with full context"), `codeReviewService.ts:388` calling `getEscalationTier`
(`:461`, an `ollama → haiku → human` switch) and `humanEscalation.ts` (a background checker). Item 5
has to read those four and not the one the brief and the header point at — memory item 19's rule
(*grep the readers, not the writers*), landing again on the same donor.

## Options compared

The question this item decides is narrow: **what does 2.0 do with a text-derived complexity score?**

| option | evidence | cost | verdict |
|---|---|---|---|
| **A. Port the Campbell scorer, fix the substring bug, recalibrate the thresholds** — the brief's implied plan | F361 (ρ ≤ 0.21 in four arms), F364 (the fix moves 2 of 149 tasks, one of them the wrong way) | ~250 lines, permanent | **rejected** — recalibration relocates boundaries on an axis with no signal |
| **B. Port the scorer with the thresholds removed, as a recorded number** | F360, F365 | ~250 lines | **rejected** — a number nothing reads is F347 with extra steps; if it is not a gate it must at least be a *better* report than the free alternatives, and prompt word count beats it |
| **C. No a-priori complexity estimate. Dispatch everything at the one rung that exists, and spend the budget on in-flight measurement** | F360 (one rung is all there is), F362 (observation beats prediction 4:1), F363 (context is a constant), W6 item 4 (the gate is a conjunction of cheap vetoes over a real attempt) | 0 lines, and it deletes a model call per task | **recommended** |
| **D. Ask the local model to score complexity, and route on that** | F366 (this is what v1 actually did), W11 F284 (a stronger model is a better reader and an unusable component), memory item 25 (more context is not monotonically better) | one call/task, plus a head rewrite at 4.60× if the score changes the prompt | **defer to item 3** — but it must be argued as a *report*, and against the ρ = 0.187 baseline of counting words |

## Recommendation

**1. 2.0 ships no a-priori complexity score in v1 of the router.** Not rescaled, not anchored, not
ported behind a flag. The evidence against it is not that it is mis-calibrated; it is that on 952
measured attempts across four arms it does not order tasks by any quantity 2.0 cares about, and its
one documented consumer tier is unreachable.

**2. The routing question 2.0 actually faces is a different one, and item 2 owns it.** There is one
local model, one GPU, zero cloud spend and no co-residency (W11 F275). "Which tier" has one answer.
What is genuinely open is **how much budget this attempt gets** and **when to stop**, and F362 says
both are answerable from counters the harness already keeps.

**3. Whatever estimate item 3 lands on must beat ρ = +0.219, and it should be measured against
`prompt.split_whitespace().count()` at +0.187.** Those are the two baselines this item establishes:
the best a-priori number either donor produces, and the free one-liner that gets 85% of the way there
with no keyword list and no model call. An estimator that does not clear the first is not worth
porting; one that does not clear the second by a wide margin is not worth its prompt-cache cost, let
alone a swap. Both are still worth less than half of any in-flight counter.

**4. Record the in-flight counters as first-class routing inputs from the start.** Peak occupancy,
cumulative tokens and round count are the three strongest predictors measured here, they cost
nothing, and W3's event log already has to carry them. They are also exactly what a circuit breaker
needs (item 5) and what W5's console already shows.

**5. Do not port the `low` keyword tier, and do not port BCF's html floor.** Both are dead or
actively wrong: one is never read (F364), the other is the only rule in the family that routes
upward and it selects the easiest tasks in the corpus (F365).

**6. Carry v1's typed `RoutingResult` and nothing else from the router file.** BCF's `router.rs:59-67`
is the shape §11 recommends and the recommendation survives: a typed result with the source of the
decision recorded (`Rules | Ai | Dual`) is right, even when — especially when — the decision is
"there is one rung". What must change is that `complexity: u32` becomes an `Option`, because "no
estimate was made" is a state this design has and v1's type cannot express. That is W6 item 8's rule
(`Measured | Unmeasured(Why)`) applied to routing.

## Rejected alternatives and why

- **Recalibrating the scale for the stronger base agent**, which is what §11 explicitly asks for. It
  presumes the scale orders tasks. It does not (F361), and the specific hypothesis — *"a task that was
  C7 for a 7B may be C3 for a 35B-A3B"* — cannot be tested on this scorer at all, because it cannot
  emit a 7 for a real task (F360).
- **Mining v1's Postgres for the retrospective correlation.** Struck through in the brief, and this
  item is the reason it is not a loss: the correlation §11 wanted exists here with an answer key,
  which the database never had (`complexity` is the default 5.0 for 137 of 182 rows).
- **Treating the substring bug as the finding.** It is 21 false fires in 149 tasks and it moves 2
  tasks (F364). Reporting it as the problem would have been the third time in this project that a
  real-but-tiny mechanical defect was mistaken for a cause.
- **Quoting the pooled pass-rate-by-score curve.** The first version of `join.py` printed one and it
  looked like a U. Stratified by arm it is four flat lines. Memory items 26/28/31, held.
- **Using `tokens_in` as the context measurement.** It is session-cumulative cost
  (`result.rs:1-12`), 34× the real occupancy at the maximum. Reading it as occupancy would have
  produced "56 of 56 tasks exceed v1's 16K tier" — the exact opposite of F363's true "0 of 945" — and
  it was one join away from being written down.

## Effect on fun

Deleting the complexity score removes the most legible thing v1's console showed: a number, per task,
with a tier label and a reasoning string. That is a real loss and it should be replaced rather than
mourned. What replaces it is better television: **the in-flight counters are a live quantity**, and
F362 says they are the ones that mean something. A task whose occupancy is climbing and whose round
count is past the median *is* in trouble, visibly, while it happens — which is a far better thing to
put on an RTS console than a static "C4" assigned before anything began. W5's escalation-event panel
(`W5-command-center.md` item 4) was deliberately deferred to W4's shape; this is the shape, and it is
a gauge rather than a badge.

The honest cost: 2.0 will not be able to say *"this is a hard one"* before it starts. It will only be
able to say *"this one is going badly"* while it runs. On this evidence the first sentence was never
true anyway.

## Open questions

| id | question | why it is not answered here |
|---|---|---|
| **OQ-W4-1** | Does F363's "context is a constant" survive a **multi-turn session on a real repository**? Q56 is single-turn on a small fixture; the K suite's three tasks are the only cells carrying `peak_prompt_tokens` natively. | needs cells this project does not have; item 2 owns it |
| **OQ-W4-2** | Is there a **threshold** on peak occupancy or round count that works as a circuit breaker, or only a correlation? F362 measures ordering, not a cut point. | item 5, and W11 F296 already complicates it |
| **OQ-W4-3** | Does the champion score complexity better than ρ = 0.187 when asked directly? F366 makes this the only version of the estimator question left. | item 3; needs GPU |
| **OQ-W4-4** | v1 wrote `complexity`, `complexitySource` and `complexityReasoning` back to the task row for *"future fine-tuning"* (`taskRouter.ts:309-317`), and `trainingDataService.ts:67` recomputes it. If 2.0 emits no score, what is the label in the by-product training data W3 promised? | item 6 |
| **OQ-W4-5** | `bugfix` and `api-misuse` are the two hardest kinds and the scorer has no vocabulary for either. Is *task kind* — which the corpus carries and a router could read — a better a-priori signal than any text score? | item 3; the corpus has the labels already |

## Confidence: high on both donor scorers and on the tier arithmetic, high on the Q56 correlations, medium on how far they travel

**High** on F360, F364, F365, F366 and F367: every one is donor code executed or grepped rather than
read, over a corpus of 149 real prompts, and the two scorers are the donors' own compiled and
byte-sliced bodies rather than ports.

**High** on F361 and F362 within Q56: 952 cells, one subject, one held config, four arms reported
separately, and the conclusion is a *null* result on the score — which is the direction that a small
sample makes harder to claim, not easier.

**Medium** on how far they travel. Three bounds, stated plainly:

1. **One subject.** Everything is the champion at IQ3\_S. A different model could fail differently.
2. **One task shape.** Q56 is single-turn, small-fixture, hidden-test work with an 88.2% control pass
   rate. W6 item 5 already showed that the free structural check's yield is a property of task shape
   (9/12 on repository work, 0/29 on clean single-function work), and the same warning applies here:
   a corpus of large multi-file repository tasks could restore some dynamic range to both the score
   and the occupancy.
3. **The occupancy number is a floor**, four ways (method above). It is safe in the direction F363
   uses it — "0 of 945 crossed 16K" would only get *more* true with a better instrument for the
   preamble, and less true only if the gauge understates by 2.8× — but it is not a peak.

What would raise it: cells from a multi-turn repository suite with `peak_prompt_tokens` captured
natively (OQ-W4-1), and item 3's direct measurement of the model as an estimator against the
word-count baseline (OQ-W4-3).

---

# Item 2 — difficulty, context and cost as three axes

## Question

§11 gives this item two bullets:

> *"Separate the two things V1 conflated: task difficulty and required context length. They are
> independent routing dimensions and V1 mapped both onto one 8K/16K/32K axis."*
>
> *"Cost model: per-task tokens and wall-clock across tiers, so routing optimizes against a real
> objective."*

Item 1 measured all three quantities on Q56 and found the complexity score predicts none of them.
This item asks the sharper questions that follow. **What actually sets occupancy?** **Is required
context knowable before dispatch at all?** And **what is the router buying**, in seconds, when it
chooses anything other than "run it".

It opens with a debt. F363 — *context is a constant, 0 of 945 cells exceed 16K* — rests entirely on
`ctx_recover.py` parsing the subject's own `ctx ~N/60k` gauge out of transcripts, because
`peak_prompt_tokens` is absent from every Q56 cell. Before anything is built on that number it has to
be checked against an instrument that is not itself. That check is F368 and it came back mixed.

## Method

Four passes, all desk work over cells already on disk. Spike `research/spikes/w4-router/`.

1. **`ctx_calibrate.py`** — recovers occupancy from every transcript in three populations and
   compares it to (a) the natively captured `peak_prompt_tokens` on the 49 K/W11 cells that have it,
   and (b) `tokens_in / iterations`, which is the **server's own tokenizer count** averaged over the
   turn's requests and therefore an exact real-token lower bound on the peak.
2. **`axes.py`** — profiles every task's fixture (bytes, files, lines) and prompt, joins it to the
   per-cell occupancy, and asks what occupancy correlates with, per suite **and per arm**.
3. **`cost.py`** — the per-attempt cost distribution, `pass@k` over the repeated cells, the
   conditional value of the next retry given the failures already burnt, and the price list of every
   alternative rung.
4. Source reading in the subject and the harness to establish what each instrument *is*.

**Populations, and they are three different regimes rather than one corpus:**

| | tasks | cells scanned | fixture bytes (min / med / max) | model |
|---|---|---|---|---|
| Q56 | 56 | 952 | 77 / 415 / 3,928 | champion |
| U100 | 10 | 248 | 63 / 97 / 160 | champion |
| K, champion @ `max_iterations = 40` | 3 | 18 | 41,739 / 42,636 / 74,508 | champion |
| K, 27B @ `max_iterations = 40` | 3 | 18 | same fixtures | `qwen3.8-27b` |
| K, champion @ budget 12 / 20 (W11) | 3 | 18 | same fixtures | champion |

🚨 **The K family is stratified by model *and* by iteration budget and never pooled.** Six of its
eighteen families ran the 27B; `w11-b12` and `w11-b20` capped the loop at 12 and 20 rounds, which
caps occupancy and cost by construction. A pooled "K" row would be memory item 26's error twice over.
Q56 and U100 are stratified by arm throughout, for the same reason.

## Inherited

- **F362/F363 (item 1)** — the numbers this item calibrates and extends.
- **W2 F79 / W11 F284** — the swap costs 23.77 s / 26.3 s round trip plus 4.6× the decode.
- **W1 F87–F88** — the 27B tied on verdicts at 5.2× the wall clock on the earlier battery.
- **W2 F81** — the prefix cache saves 79.7% of TTFT and one token at the front annihilates it.
- **W11 F275** — co-residency is arithmetically impossible: 1,210 MiB free against a 4.41 GB model.
- **W11 item 5** — a loop budget must count *rounds*, not seconds.
- **W6 item 8** — `Measured | Unmeasured(Why)`; a record that cannot say "not measured" lies by
  omission.
- **F59** — the token baseline stepped 10% between sessions, so cross-session token deltas are
  untrustworthy; every comparison below is within one instrument.

## Findings

### 🚨 F368 — the recovered gauge is faithful to the field and neither of them is a floor: measured against the server's own tokenizer it falls *below* an exact lower bound on 61 of 945 cells

Two checks, and they answer different questions.

**Check A, parser fidelity: 49 of 49 exact.** Every K and W11 cell that carries
`peak_prompt_tokens` natively agrees with the transcript recovery to the token. **This proves less
than it looks.** `w8-run/src/main.rs:985` computes the native field as `peak_ctx + preamble_tokens_in`
— the same arithmetic over the same gauge, captured live instead of re-read. Agreement establishes
that the parser is faithful. It establishes nothing about the gauge.

**Check B, the gauge against a real tokenizer.** The same marker line carries a second instrument
that item 1 read only as cost:

| field | what it is | units |
|---|---|---|
| `ctx ~N/60k` | `estimate_session_tokens` — `bytes/4 + 1` per content block, omitting the system prompt and tool schemas (claudette `compact.rs:27`, `:433-446`) | an estimate |
| `in=` | `summary.usage.input_tokens` ← OpenAI `usage.prompt_tokens` (`api.rs:896-899`, `:1172-1176`) — **the server's tokenizer**, cumulative over the turn's requests | exact |

`iterations` is incremented once per loop pass and each pass issues exactly one request
(`conversation.rs:437`; the graceful iteration-cap landing adds one request *and* one increment, so
the identity holds there too). So `tokens_in / iterations` is the **mean real prompt tokens per
request**, and a mean never exceeds a max: it is an **exact real-token lower bound on the peak**.

| population | recovered peak ÷ real mean, p50 | min | cells where the recovered peak is **below** the exact floor |
|---|---|---|---|
| Q56, 945 cells | 1.093 | 0.944 | **61 / 945 = 6.5%** |
| U100, 235 cells | 1.223 | 1.013 | 0 / 235 |
| K + W11, 49 cells | 1.205 | 0.900 | 1 / 49 |

**So the recovered number is not a floor on the peak. It is an estimate good to roughly ±10–20%, and
on 6.5% of Q56 cells it is provably low.** F363's docstring claim that it *"understates four ways, so
if it says a cell crossed a threshold the cell crossed it"* is right about each of the four
mechanisms and wrong about their sum: the gauge is compared against a real-token quantity, and
`bytes/4` runs *high* on code and JSON, which are denser than the ~3.39 chars/token the prose
correction assumed.

**And there is a fifth mechanism nobody listed, which is the one that matters.** Of 1,254 scanned
cells, **12 carry no occupancy sample at all — and all 12 are `status = timeout`** (7 of 952 Q56, 5 of
54 K/W11). The gauge prints at turn end; a cell killed by the clock never reaches turn end. So the
occupancy population systematically **excludes the cells that ran longest**, which are exactly the
cells with the most context. The selection is not random and it points one way.

**Effect on F363, stated so it can be quoted without a footnote:** the *headline survives, the word
"floor" does not.* Re-tested on the exact real-token lower bound, **0 of 945** Q56 cells exceed 16K;
under a linear within-turn growth model (`peak ≈ 2 × mean − preamble`) **2 of 945** do, and the count
above the deprecated 8K rises from 74 to 158. Quote F363 as *"p50 ≈ 5.9K, essentially nothing near
16K, ±20%"*, not as a bound.

### 🚨 F369 — the constant is a property of the fixture, not of agent work: on a 42 KB repository the same agent runs at 2.7× the occupancy and crosses v1's 16K line. OQ-W4-1 closes **no**

The three populations differ in fixture size by two orders of magnitude, and occupancy tracks that
and nothing else about the task.

| | fixture bytes, median | occupancy p50 (recovered) | max | real-token floor p50 | cells provably > 16K |
|---|---|---|---|---|---|
| U100, 235 cells | 97 | 5,867 | 18,167 | 5,136 | **0 / 235** |
| Q56, 945 cells | 415 | 5,898 | 13,066 | 5,706 | **0 / 945** |
| K champion @ 40, 18 cells | 42,636 | **16,125** | 21,245 | 14,089 | **2 / 18** |
| K 27B @ 40, 13 cells | 42,636 | **22,375** | 30,567 | 18,531 | **8 / 13** |

On the gauge itself, **8 of 18** champion K cells and **12 of 13** 27B K cells exceed 16,384; under
the linear peak model, **14 of 18** champion cells do and one exceeds 32,768.

**OQ-W4-1 asked whether "context is a constant" survives multi-turn repository work. It does not.**
Q56 and U100 hand the agent a few hundred bytes; the K suite hands it 20–32 files and ~1,200 lines,
and the same model on the same box runs at 2.7× the occupancy and pushes past the boundary the
complexity score exists to unlock. F363's constant was a fact about donor fixtures.

⚠ **Two limits on this, both real.** K is **three tasks**, so this is a regime demonstration and not a
distribution. And the 27B's larger occupancy is partly its own tokenizer and partly its longer
sessions — it is not evidence that the harder model *needs* more context.

**The one place in the donor corpora where the line is crossed says the same thing.** The only two
U100 cells above 16K are the same task, `fix_missing_validation`, at **41 iterations — the iteration
cap plus the landing call** — and both **failed**. They crossed the boundary by looping, not by being
big.

### 🚨 F370 — "required context length" is not a property of the task: occupancy is set by the loop, at ρ ≈ +0.8 to +0.9, against ρ ≤ +0.30 for every a-priori measure of the workspace

ρ over cells, within one suite and one arm, so neither the suite mix nor the arm mix can carry it.

| suite / arm | n | fixture bytes | fixture lines | prompt words | **iterations** | cumulative tokens |
|---|---|---|---|---|---|---|
| q56 / control | 278 | +0.048 | +0.119 | +0.299 | **+0.836** | +0.879 |
| q56 / deny-first-edit | 279 | +0.266 | +0.197 | +0.251 | **+0.815** | +0.865 |
| q56 / gated | 110 | +0.116 | +0.126 | +0.266 | **+0.835** | +0.879 |
| q56 / redirect-first-edit | 278 | +0.233 | +0.188 | +0.212 | **+0.739** | +0.810 |
| u100 / control | 76 | +0.185 | +0.122 | +0.141 | **+0.940** | +0.971 |
| u100 / gated | 76 | +0.116 | +0.077 | +0.150 | **+0.930** | +0.967 |
| u100 / redirect-first-edit | 76 | +0.178 | +0.171 | +0.205 | **+0.853** | +0.906 |

**Every a-priori measure of the workspace sits at or below +0.30. The number of rounds the agent
actually ran sits at +0.74 to +0.94, in every suite and every arm.**

The variance decomposition says the same thing from the other side. Occupancy does differ
systematically between Q56 tasks — 65.6% of the control arm's variance is between-task — but **that
component is not a size effect**: ρ(fixture bytes, per-task mean occupancy) = **+0.041**, and the
whole between-task range is 5,477 → 10,192, a factor of **1.86** against a within-task spread whose
median is 1,020 tokens and whose maximum is 7,187. On U100 and K the between-task share collapses to
13.8% and 8.1%. What separates one task's occupancy from another's is how much work it induced, not
how much text it shipped.

**This is the item's central result and it is stronger than "the two axes are independent".** §11
asks the router to route on *required context length*. That quantity is not knowable before dispatch,
because it is not a property of the request — it is a property of the attempt, and it is the same
quantity as effort, which F362 already showed arrives too late to route on. The part of context that
*is* knowable before dispatch — the preamble, and the bytes on disk — the router can **measure
exactly and for free**, and it does not vary.

### F371 — the two axes really are independent, and that is precisely why neither one routes

Per-task, per-arm, difficulty being the task's pass rate in that arm.

| suite / arm | tasks | ρ(fixture bytes, pass) | ρ(occupancy, pass) | ρ(iterations, pass) | ρ(fixture bytes, occupancy) |
|---|---|---|---|---|---|
| q56 / control | 56 | **−0.069** | −0.405 | −0.320 | +0.041 |
| q56 / gated | 56 | −0.047 | −0.197 | −0.240 | +0.141 |
| q56 / deny-first-edit | 56 | −0.077 | **+0.082** | +0.219 | +0.176 |
| q56 / redirect-first-edit | 56 | +0.091 | **+0.099** | +0.114 | +0.266 |
| u100 / control | 10 | **+0.026** | −0.368 | −0.515 | +0.564 |
| u100 / gated | 10 | +0.089 | −0.013 | +0.019 | +0.079 |
| u100 / redirect-first-edit | 10 | +0.447 | +0.195 | +0.259 | +0.418 |

**§11 is right that v1 conflated two independent things**: the a-priori size of the workspace and the
difficulty of the task are uncorrelated (−0.069 and +0.026 on the two clean arms). Separating them is
the correct move. It just does not produce two routable axes — it produces one axis with no a-priori
estimator that beats ρ = +0.219 (item 1), and one axis with no a-priori variation to estimate.

**The apparent coupling between occupancy and difficulty is effort, and the interference arms prove
it by reversing its sign.** On control, more occupancy means more failure (−0.405). On
`deny-first-edit` and `redirect-first-edit` — arms where extra rounds are the *operator's* doing —
the sign flips positive (+0.082, +0.099). A signal that inverts when the cause of the rounds changes
is a measure of the rounds, not of the task.

### 🚨 F372 — the cost model has one rung, and the escalation rung is 7.75× the wall clock for nothing measurable

**(a) What one attempt costs.** Median over cells, per suite and per arm:

| suite / arm | n | wall p50 | wall p90 | tokens_in p50 | tokens_out p50 | rounds p50 |
|---|---|---|---|---|---|---|
| q56 / control | 280 | 19.1 s | 107.0 s | 39,486 | 1,101 | 7 |
| q56 / gated | 112 | 16.7 s | 57.9 s | 35,211 | 1,006 | 6 |
| q56 / deny-first-edit | 280 | 20.7 s | 54.6 s | 33,192 | 1,403 | 6 |
| q56 / redirect-first-edit | 280 | 32.0 s | 75.4 s | 59,269 | 2,253 | 10 |
| u100 / control | 77 | 13.9 s | 38.3 s | 21,387 | 795 | 5 |
| **K champion @ 40** | 18 | **110.8 s** | 285.6 s | 239,329 | 6,094 | 18 |
| **K 27B @ 40** | 18 | **858.8 s** | 1,086.4 s | 315,284 | 21,226 | 19 |
| K champion @ budget 12/20 | 18 | 120.4 s | 171.1 s | 180,018 | 5,067 | 13 |

**(b) The price of every alternative, in the same units.**

| alternative | price | source |
|---|---|---|
| **another attempt on the same rung** | **1.00 attempt** | this item |
| model swap, round trip | 23.77 s = **1.24** median Q56 attempts | W2 F79 |
| model swap, re-measured | 26.30 s = **1.37** median Q56 attempts | W11 F284 |
| …and then every token | **4.6×** the decode | W11 F284 |
| a router that rewrites the head of the prompt | **4.60×** a warm turn (full cold prefill) | W11 item 2 |
| leaving the prefix alone | saves **79.7%** of TTFT; one token at the front annihilates it | W2 F81 |
| a second model, co-resident | **impossible**: 1,210 MiB free vs a 4.41 GB model | W11 F275 |
| a cloud rung | not a tier — zero cloud spend is standing | David, 2026-08-07 |

**(c) The swap, re-measured head to head on the hard suite.** W1 F87–F88 priced the 27B at 5.2× on
the earlier battery. K runs both models over the same three fixtures, the same verifier and the same
`max_iterations = 40`:

| | median attempt | timeouts | pass@1 | per-task pass rate |
|---|---|---|---|---|
| champion | **110.8 s** (max 629.1) | **0 / 18** | 66.7% | 0.33 / 0.83 / 0.83 |
| `qwen3.8-27b` | **858.8 s** | **5 / 18** | 72.2% | 0.83 / 0.83 / 0.50 |

**7.75× the wall clock, and the 5.5-point pass@1 difference is one task each way over 18 cells.** The
27B wins the task the champion is worst at and loses the one the champion is best at. And the
multiplier is a **lower bound**: four of the 27B's cells were truncated by their timeout (three at
900 s, one at 2,400 s), which only shortens the measurement. Its dominant failure mode on this box is
the clock, not the reasoning — the champion's slowest cell, 629.1 s, is below the 27B's median.

### 🚨 F373 — the retry curve flattens after two, and 40 of 56 tasks never needed one

`pass@k` by the unbiased estimator over repeated cells, control arm only.

| | pass@1 | @2 | @3 | @4 | @5 |
|---|---|---|---|---|---|
| Q56, 56 tasks × 5 | 88.2% | **94.6%** (+6.4) | 96.8% (+2.1) | 97.9% (+1.1) | 98.2% (+0.4) |
| U100, 10 tasks × 8 | 88.8% | **99.3%** (+10.5) | 100.0% (+0.7) | 100.0% | 100.0% |
| K champion @ 40, 3 tasks × 6 | 66.7% | **86.7%** (+20.0) | 93.3% (+6.7) | 97.8% (+4.4) | 100.0% (+2.2) |
| K 27B @ 40, 3 tasks × 6 | 72.2% | 93.3% (+21.1) | 98.3% (+5.0) | 100.0% | 100.0% |

**The second attempt buys 6.4 to 21.1 points. The third buys 0.7 to 6.7. The fourth and fifth buy
noise.** In pass-rate points per minute at the median Q56 attempt: retry #2 is **20.1 pp/min**; the
swap-and-attempt is 125.9 s for a difference W1 measured as level, so **≤ 0 pp/min** — and on K the
same comparison is 110.8 s for +20.0 pp against 858.8 s for a tie.

**And the budget is mostly irrelevant.** On Q56, **40 of 56 tasks pass all five times and 1 (Q03)
passes none**; the retry budget can only change the outcome on the remaining 15. On U100 it is 7 of
10; on K, 3 of 3.

⚠ The repeats are **separate runs**, so `pass@k` mixes sampling variance with run-to-run variance;
F59 saw the token baseline move 10% between sessions. This overstates the value of a retry, in the
direction of making retries look better than resampling within one session would.

### 🚨 F374 — the first failure is worth 44 points of information, and no a-priori score in this project is worth 5

`pass@k` prices a budget chosen *before* the first attempt. A circuit breaker needs the value of the
*next* attempt given the ones already burnt — and those failures are evidence about which task this
is. With `p_t` the task's measured pass rate and the corpus as the prior:

    P(pass at k+1 | first k all failed) = Σ p_t (1−p_t)^k ⁄ Σ (1−p_t)^k

| failures so far | Q56 control | U100 control | K champion @ 40 |
|---|---|---|---|
| 0 (the unconditional rate) | 88.2% | 88.8% | 66.7% |
| 1 | **43.6%** | 81.9% | 50.0% |
| 2 | 31.0% | 79.8% | 38.9% |
| 3 | 22.4% | 78.0% | 34.8% |
| 4 | 16.6% | 76.7% | 33.7% |

**On Q56 one observed failure moves the estimate by 44.6 points.** The best a-priori signal item 1
could find was BCF's `rule_score` at ρ = +0.219, and the best free one was counting the prompt's
words at +0.187. The failure is free, it is exact, and it is available at the moment the decision has
to be made.

**And the size of that update is a property of the population, not a constant.** Q56 is bimodal — 40
tasks at p = 1.0 and one at p = 0 — so a single failure is strong evidence you are on one of the 15
hard ones. U100's tasks sit at middling probabilities, so the same failure moves the estimate by
under 7 points. **A fixed "retry twice then escalate" rule is therefore right on one corpus and wrong
on the other, and the breaker has to be calibrated from the outcome history rather than written
down.** W3's event log already holds exactly that history.

### F375 — the instrument samples once per *turn* and the router needs it once per *round*; the harness action item the handoff carried is already closed

**The descriptor is not the bug, and the handoff's diagnosis needs correcting.** Commit `29703ef`
(2026-08-17) added the optional 4th capture group to `corpus/subjects/claudette-af3f804.toml:49`
**and** `peak_prompt_tokens` to `w8-run` — one commit, both halves. Q56 ran 2026-08-09 → 08-15 and
U100 on 2026-08-08; all 43 runs on disk name the same subject, `claudette-af3f804`, and the ones
missing the metric are simply the ones that ran before the metric and the capture group existed. There is nothing to fix: every run
since 2026-08-17 captures occupancy natively, and so will every future one.

**The real gap is the sampling rate, and it is in the subject.** The gauge is printed once, at turn
end (`repl.rs:203-214`). A K cell that ran 41 rounds emits **one** occupancy number. A cell killed by
the clock emits **zero** — which is why all 12 zero-sample cells are timeouts. Rounds *are* observable
live, because each tool call prints to stderr; occupancy is not observable at all until the turn is
over.

**So in-flight routing on occupancy is not merely unimplemented — the signal does not exist at the
rate a breaker would need.** A breaker that must decide at round 12 whether round 13 is worth paying
for cannot read a number that is published at round 41. This is a requirement on 2.0's own agent
loop, not on its router: **emit occupancy and round count as an event per iteration**, onto W3's
durable event log, where W5's console already wants them.

## Options compared

| | what it routes on | available when? | measured worth |
|---|---|---|---|
| **A. v1 as written** — one 8K/16K/32K axis from a complexity score | a prediction of difficulty *and* of context, conflated | before dispatch | ρ ≤ 0.21 for difficulty (F361); the context half is a constant on the donor corpora and unreachable in the K regime for the wrong reason (F369) |
| **B. two a-priori axes** — score difficulty, size the context separately | a prediction, plus `du` on the workspace | before dispatch | the axes are genuinely independent (F371) but the context one has ρ = +0.048 against real occupancy (F370) |
| **C. no a-priori axis; route the retry** | rounds, cumulative tokens, occupancy and the outcome of attempts already made | during and after each attempt | +0.74…+0.94 against occupancy (F370); one failure = 44.6 points (F374) |
| **D. escalate to the bigger local model** | any of the above | after a failure | 7.75× wall clock, 5 timeouts in 18, one task each way (F372) |

## Recommendation

**1. There is one tier, and the only purchase a router can make is another attempt.** Everything else
on the price list costs more than an attempt and buys nothing this project has measured: the swap is
1.24 Q56 attempts *before* 4.6× the decode, 7.75× measured end to end on K; the head rewrite is
4.60×; co-residency does not fit; the cloud rung does not exist. **Retry is not the fallback option,
it is the option.**

**2. The retry budget is 2, and the third attempt is a per-population decision, not a constant.**
Two attempts capture 6.4 of Q56's 10 available points, 10.5 of U100's 11, and 20.0 of K's 33. A
third is worth paying for only where the outcome history says the population is not bimodal — which
the event log can answer and a config file cannot.

**3. The breaker fires on the first failure, and its threshold is learned.** One failure takes Q56
from 88.2% to 43.6% and U100 from 88.8% to 81.9%. Ship the update rule, not the number.

**4. Do not route on "required context length".** It is not a property of the request. The part that
is knowable — preamble plus bytes on disk — is measurable exactly, for free, and does not vary within
a corpus; the part that varies is the loop, and it is the same quantity as effort. Where the fixture
*does* change by two orders of magnitude (F369), the right response is a **window check**, not a
tier: does the workspace plus the preamble plus a working margin fit in `num_ctx`? That is arithmetic
on measured numbers, and it has one honest answer per workspace.

**5. The typed routing input 2.0 carries.** Aligned with W3's event log and W6 item 8's
`Measured | Unmeasured(Why)`. Nothing in it is a prediction: every field is either a fact about the
request or a count of work already done.

```rust
/// Everything the router is allowed to know, and when it learns it.
pub struct RoutingInput {
    /// Known before dispatch. Facts, not estimates.
    pub request: RequestFacts,
    /// Empty on the first attempt. After that it is the whole of the evidence.
    pub history: Vec<AttemptRecord>,
}

pub struct RequestFacts {
    pub prompt_tokens: u32,              // counted, not estimated
    pub workspace_bytes: u64,            // what the agent could read
    pub workspace_files: u32,
    pub preamble_tokens: u32,            // system prompt + tool schemas, measured at warmup
    pub window_tokens: u32,              // num_ctx, so the fit check is arithmetic
    pub toolchain: ToolchainProfile,     // W6 item 5
    // NO complexity score. F360-F366: v1's puts 149 of 149 tasks in one tier and
    // predicts nothing. BCF's typed `RoutingResult` survives (router.rs:59-67) with
    // `complexity: Option<f32>`, and 2.0 emits `None`.
}

pub struct AttemptRecord {
    pub rounds: u32,                             // the strongest in-flight signal, F370
    pub cumulative_prompt_tokens: u64,           // cost, NOT occupancy
    pub peak_occupancy: Measured<u32>,           // Unmeasured(Why) when the turn never ended
    pub wall_clock: Duration,
    pub outcome: HonestOutcome,                  // W6 item 8
    pub stopped_by: StopReason,                  // budget | model's own judgement | clock | gate
}

/// The decision is a STOPPING rule. There is no tier to choose.
pub enum NextAction {
    Attempt { round_budget: u32 },
    Stop(StopReason),
    HandToOperator(Evidence),
}
```

**6. Harness / subject action item, restated correctly.** The descriptor is already fixed and every
run since 2026-08-17 captures `peak_prompt_tokens` natively (F375). What is *not* fixed is that the
subject publishes occupancy once per turn, so a 41-round attempt yields one sample and a timed-out
attempt yields none. **2.0's agent loop must emit a per-iteration event carrying round index,
cumulative prompt tokens and current occupancy.** Until it does, every breaker is a post-mortem.

**7. When quoting F363, quote it as an estimate.** p50 ≈ 5.9K on Q56, ±10–20% against the server's
tokenizer, and bounded to fixtures of a few hundred bytes. The phrase "a floor four ways" should not
be repeated: 61 of 945 cells sit below an exact real-token lower bound (F368).

## Rejected alternatives and why

- **Rescaling the 8K/16K/32K axis for the K regime.** K crosses 16K (F369) so a boundary there is
  reachable at last — but occupancy at ρ = +0.048 against fixture bytes is not predictable before
  dispatch, so the boundary would be crossed *during* the attempt, when the window is already
  allocated. W1 F84: KV is allocated in full at load. A window is a **load-time** decision, not a
  per-task one.
- **Using cumulative `tokens_in` as the context axis.** It is session-cumulative cost
  (`w8-run/src/result.rs:1-12`) and reading it as occupancy inverts the answer — item 1's trap 2.
- **A "context tier" derived from `du` on the workspace.** ρ = +0.048 (Q56 control) and +0.185 (U100
  control) against actual occupancy. It measures what the agent *could* read, and what it actually
  reads is set by the loop.
- **Escalating to `qwen3.8-27b` on failure.** F372. 7.75× the wall clock, 5 timeouts in 18, and it
  wins one task while losing another.
- **A fixed "retry N times" constant.** F374: the correct N differs between two corpora measured on
  the same box with the same model, because the update a failure carries depends on the population's
  bimodality.

## Effect on fun

The console gets a number it can actually animate. W5's six queries over the event log now have a
seventh worth showing: **the live posterior** — *"this task has failed once; the next attempt is
44 points less likely to work than the first was"* — computed from the operator's own history rather
than asserted. That is a genuinely legible thing to put beside the retry button, and it is the same
number the breaker uses, so the operator and the machine are looking at one quantity. The tier ladder
2.0 will not have would have shown a badge; this shows a decision.

## Open questions

- **OQ-W4-6** — the linear within-turn growth model (`peak ≈ 2 × mean − preamble`) is an assumption.
  A single run with a per-iteration occupancy event (recommendation 6) would replace it with a
  measurement, and would settle whether the K regime crosses 32K.
- **OQ-W4-7** — F374's posterior is computed from the *task's* measured pass rate, which a live
  router does not have. Does the update survive when the prior is over a task *population* the router
  has seen before rather than over the task itself?
- **OQ-W4-8** — is the second attempt's +6.4 points sampling variance or is it *recovery*? The
  repeats here are independent cold starts; a real retry could carry the failed attempt's evidence
  forward, which is a different and probably better experiment. W3's lineage chain makes it cheap.
- **OQ-W4-9** — occupancy correlates with rounds at +0.8 to +0.9 and rounds are observable live.
  Is there a **round threshold** that beats "retry twice"? W11 F296 complicates it (above the binding
  point the model stops on its own judgement with rounds unspent); OQ-W4-2 owns the threshold
  question and item 5 inherits both.
- **OQ-W4-10** — U100's only two cells over 16K are the same task at the iteration cap, both failed.
  Is "occupancy above 16K" simply a synonym for "this attempt is looping"? On these populations the
  two are indistinguishable.

## Confidence: high on the instrument calibration and the cost model, high on the Q56/U100 correlations, medium on the K regime, low on any threshold

The calibration is arithmetic over two instruments whose source was read (F368), and the correlation
tables are over 945 + 235 cells stratified by arm. The cost model's local-rung numbers are medians
over the same cells, and its price list is entirely re-quoted from measurements that already exist.
**The K regime is three tasks**, so F369 is a demonstration that the constant breaks, not a
distribution for the regime beyond it. F374's posterior is exact arithmetic on measured pass rates
but rests on the repeats being independent draws, which F59 says is only approximately true. No
threshold on rounds or occupancy is proposed here, because none was measured.
