# w4-router — what the inherited complexity model scores, and whether it predicts anything

Spike for **W4 item 1** (`research/W4-routing.md`, findings **F360–F367**). Run 2026-08-25. No GPU.

## What it proved

1. **v1's own compiled scorer puts 149 of 149 real coding tasks in the bottom tier** (C1–C6 → local
   16K). Range 1.5–6.0, median 3.5. Its C7–C9 and C10 rungs are unreachable from prompt text, so the
   rule half is a floor and not a router — every routing decision v1 ever made above the bottom rung
   was the model half's. **F360**
2. **The score predicts nothing**: |ρ| ≤ 0.21 against pass rate, cumulative tokens, peak occupancy,
   iterations and wall clock, **in all four Q56 arms**. On the control arm ρ(score, pass) = −0.101 —
   the wrong sign. The only task that never passes carries the corpus's lowest score; the
   highest-scoring task passes 5/5. **F361**
3. **What predicts failure is measured effort**, and none of it is available before dispatch: peak
   occupancy +0.405, cumulative tokens +0.326, iterations +0.320 — against BCF's `rule_score` +0.219,
   prompt word count +0.187 and v1's complexity score +0.101. **Every a-priori signal sits below
   every in-flight one, and counting the prompt's words beats v1's scorer 1.9×.** **F362**
4. **Context is very nearly a constant**: over 945 cells the recovered peak-occupancy *floor* is
   5,201–13,066 (p50 5,898). **0 of 945 exceed 16K**; 74 exceed the deprecated 8K. The median
   preamble is 4,874 — **83% of the median peak**. Cumulative cost, by contrast, spans 29× and
   reaches 34× the largest occupancy. **F363**
5. **The unanchored `text.includes()` is real and nearly harmless**: 21 embedded false fires in 16 of
   149 tasks, moving **2** tasks' tier score. The brief's own example `'add'` sits in the `low`
   keyword tier, which is **defined and never read**, so it cannot move a score at all. `'api'` fires
   inside "capitalized" and is Q07's *entire* semantic score — anchoring takes one of the eight
   hardest tasks from 4.0 to 2.0. **F364**
6. **BCF reaches its second tier on 20 of 149 — and 18 of the 20 come from one line**,
   `if text.contains("html") … { score = score.max(7.0) }` (`router.rs:303-306`), which fires on the
   *easiest* class in the corpus (14/15 pass vs 126/140). **F365**
7. **The dual assessment is the model's score with a floor under it**: the model half is called on
   149 of 149 tasks (the `rules <= 8` gate never blocks), taken **outright on 53.8%** of the
   (task × answer) grid, and the median task loses the decision at a model answer of 6. **F366**

## Files

| file | what it is |
|---|---|
| `score_corpus.mjs` | imports the **donor's compiled** `taskRouter.js` and calls `calculateComplexity` over all 149 corpus tasks → `scores.jsonl` |
| `build_bcf_scorer.py` | slices `rule_score` + `detect_language_hint` **verbatim by byte range** out of `battle-command-forge/src/router.rs` (sha256 `5263aeaf87…`, lines 147–309 and 312–322) into `bcf_score/`, asserting the slice is a substring of the donor file |
| `bcf_score/` | throwaway crate wrapping that slice with a stdin driver. `cargo build --release` |
| `bcf_run.py` | feeds the 149 prompts to it the way `mission.rs:268` does → `bcf_scores.jsonl`, `bcf_run-out.txt` |
| `bcf_followup.py` | which C7s survive without the html floor; do either scorer's numbers predict Q56/U100 failure → `bcf_followup-out.txt` |
| `ctx_recover.py` | recovers peak prompt occupancy from all 952 Q56 transcripts → `ctx.jsonl`, `ctx_recover-out.txt` |
| `join.py` | first pass: tier assignment, pass rate by score per arm → `join-out.txt` |
| `analyze.py` | the item's numbers: occupancy, cost-vs-occupancy, correlations per arm, what predicts failure → `analyze-out.txt` |
| `anchor_probe.mjs` | classifies every substring keyword hit INFLECTION / COMPOUND / EMBEDDED and rescores → `anchor_probe-out.txt` |
| `ratchet.py` | F221's blend arithmetic over the 149 real rule scores × 10 model answers → `ratchet-out.txt` |

Regenerate everything:

```sh
node score_corpus.mjs 2>/dev/null | grep "^{" > scores.jsonl   # see trap 1
python ctx_recover.py > ctx_recover-out.txt
python build_bcf_scorer.py && (cd bcf_score && cargo build --release)
python bcf_run.py > bcf_run-out.txt
python join.py > join-out.txt ; python analyze.py > analyze-out.txt
node anchor_probe.mjs > anchor_probe-out.txt
python bcf_followup.py > bcf_followup-out.txt ; python ratchet.py > ratchet-out.txt
```

## Traps, all of which bit

1. **Importing v1's router starts a Prisma client.** `taskRouter.js` pulls in `budgetService`, which
   reaches for `localhost:5432` on import and prints its failure **to stdout**. Three lines of it
   landed in the first `scores.jsonl` and broke the reader. Filter to lines beginning `{`.
2. **`tokens_in` is not context.** It is session-cumulative prompt tokens summed over iterations
   (`harness/crates/w8-run/src/result.rs:1-12`). Reading it as occupancy produces *"56 of 56 tasks
   exceed v1's 16K tier"* — the exact opposite of the true **0 of 945**, and it was one join away
   from being written down. `peak_prompt_tokens` is absent from every Q56 cell; the number has to be
   recovered from the transcript gauge.
3. **The recovered occupancy is a FLOOR, four ways** (`main.rs:966-977`): the gauge omits the system
   prompt and tool schemas (so the run's measured preamble is added back), the preamble is itself a
   lower bound, granularity is 1,024 tokens above 1k, and it is a chars/4 estimate against a corpus
   measuring ~3.39 chars/token. All four understate, which makes it safe for *"nothing crossed 16K"*
   and unsafe as a peak.
4. **A crude anchored matcher manufactures a defect.** The first `anchor_probe.mjs` counted every
   non-word-boundary hit and reported **75** spurious hits and **13** tier changes. Classifying
   inflections and compounds out first gives **21** and **2**. Memory item 30's failure mode, caught
   by reading the examples rather than the count.
5. **Stratify by arm.** 672 of the 952 Q56 cells are non-control and 560 come from arms built to stop
   the agent editing. The pooled pass-rate-by-score table looks like a U; per arm it is four flat
   lines.
6. **`git diff` the corpus before scoring it.** The 8 runs span three corpus commits. No `prompt.txt`
   changed across them (`git diff --name-only de26d3d HEAD -- corpus/suites/*/tasks/*/prompt.txt` is
   empty), so scoring the working tree scores the bytes the agent saw — but that had to be checked,
   not assumed.

## Donor commits

v1 `d5528ea`, BCF `d6c1601`, corpus commits `de26d3d` / `665038b` / `0766e6d`.
