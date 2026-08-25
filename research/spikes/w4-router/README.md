# w4-router — what the inherited complexity model scores, and whether it predicts anything

Spike for **W4 items 1 and 2** (`research/W4-routing.md`, findings **F360–F375**). Run 2026-08-25.
No GPU: every number here is re-read from cells already on disk.

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
4. **Context is very nearly a constant** *on Q56*: over 945 cells the recovered peak occupancy is
   5,201–13,066 (p50 5,898). **0 of 945 exceed 16K**; 74 exceed the deprecated 8K. The median
   preamble is 4,874 — **83% of the median peak**. Cumulative cost, by contrast, spans 29× and
   reaches 34× the largest occupancy. **F363** — ⚠ qualified twice by item 2: the number is an
   estimate and not a floor (**F368**), and the constant belongs to the *fixture* (**F369**).
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

### And what item 2 added

8. **The recovered gauge is not a floor.** Against `tokens_in / iterations` — the server's own
   tokenizer, an exact lower bound on the peak — it sits below that bound on **61 of 945** Q56 cells;
   ratio p50 1.093 (Q56), 1.223 (U100), 1.205 (K). And **all 12 cells with no occupancy sample are
   timeouts**, so the population drops the longest-running cells. F363's headline survives; its
   "floor" wording does not. **F368**
9. **The constant is the fixture's.** Q56 (415 B median fixture) p50 5,898 and U100 (97 B) p50 5,867
   against **K (42.6 KB) p50 16,125**, where 8 of 18 champion cells cross 16,384. **OQ-W4-1 closes
   no.** **F369**
10. **Occupancy is set by the loop, not the request.** ρ(occupancy, rounds) = **+0.74…+0.94** in every
    suite × arm; every a-priori workspace measure is ≤ +0.30 (fixture bytes +0.048 on Q56 control).
    The two axes §11 asks to separate really are independent — ρ(fixture bytes, pass) = −0.069 — and
    neither is routable. **F370, F371**
11. **One tier, and the only purchase is another attempt.** Head to head on K at the same budget, the
    27B costs **7.75×** the champion's median attempt with 5 timeouts in 18 and one task each way.
    `pass@2` buys +6.4 pp (Q56) to +20.0 pp (K); `pass@4` buys noise. **F372, F373**
12. **The first failure is worth 44 points.** P(next passes) falls 88.2% → **43.6%** on Q56 control
    after one failure, but only 88.8% → 81.9% on U100 — the update's size is a property of the
    population's bimodality, so the breaker's threshold must be learned. **F374**

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
| **item 2** | | 
| `ctx_calibrate.py` | calibrates the recovered gauge against (a) the 49 cells carrying `peak_prompt_tokens` natively and (b) the server's own tokenizer → `ctx_calib.jsonl`, `ctx_calibrate-out.txt` |
| `axes.py` | fixture profile per task joined to per-cell occupancy: what sets occupancy, variance decomposition, occupancy vs difficulty → `axes.jsonl`, `axes-out.txt` |
| `cost.py` | per-attempt cost per suite/arm, `pass@k`, the posterior after k failures, and the price list → `cost.jsonl`, `cost-out.txt` |

Regenerate everything:

```sh
node score_corpus.mjs 2>/dev/null | grep "^{" > scores.jsonl   # see trap 1
python ctx_recover.py > ctx_recover-out.txt
python build_bcf_scorer.py && (cd bcf_score && cargo build --release)
python bcf_run.py > bcf_run-out.txt
python join.py > join-out.txt ; python analyze.py > analyze-out.txt
node anchor_probe.mjs > anchor_probe-out.txt
python bcf_followup.py > bcf_followup-out.txt ; python ratchet.py > ratchet-out.txt
# item 2 — ctx_calibrate must run before axes.py, which reads ctx_calib.jsonl
python ctx_calibrate.py > ctx_calibrate-out.txt
python axes.py > axes-out.txt
python cost.py > cost-out.txt
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
3. ⚠ **"The recovered occupancy is a FLOOR, four ways" — this was believed during item 1 and item 2
   disproved it.** `main.rs:966-977` lists four mechanisms that each understate: the gauge omits the
   system prompt and tool schemas (so the run's measured preamble is added back), the preamble is
   itself a lower bound, granularity is 1,024 tokens above 1k, and it is a chars/4 estimate against
   prose measuring ~3.39 chars/token. Their **sum is not a floor**: `bytes/4` runs *high* on code and
   JSON, and against an exact real-token lower bound the composite sits **below** it on 61 of 945 Q56
   cells (trap 7). Treat it as ±10–20%, and see trap 8 for the fifth mechanism, which nobody listed.
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

## Traps item 2 added

7. **The "native" metric is not an independent instrument.** `peak_prompt_tokens`
   (`w8-run/src/main.rs:985`) is `peak_ctx + preamble_tokens_in` — the same arithmetic over the same
   `ctx ~N/…` gauge the transcript recovery parses. They agree on 49 of 49 cells and that proves only
   that the parser is faithful. The independent instrument is on the **same line**: `in=` is
   `usage.prompt_tokens` from the server's tokenizer (claudette `api.rs:896-899`), so
   `tokens_in / iterations` is an exact real-token lower bound on the peak. Use that to calibrate.
8. **Every cell with no occupancy sample is a timeout.** 12 of 1,254. The gauge prints at turn end
   and a killed cell never reaches one — so the occupancy population drops exactly the longest-running
   cells. Any "nothing exceeded X" claim has to say so.
9. **K is not one population.** Six of its eighteen run families ran `qwen3.8-27b`, and `w11-b12` /
   `w11-b20` capped the loop at 12 and 20 rounds. Pooling them mixes two models and three budgets.
   The apples-to-apples local rung is `k-champ-r*` + `w11-b40-r*` (champion, `max_iterations = 40`).
10. **The 27B K runs used two different timeouts** — `k-27b-r*` at 900 s and `k-27b-t2400-r*` at
    2,400 s — and 4 of 18 cells were truncated by one. Any wall-clock ratio built on them is a lower
    bound on the 27B's real cost.
11. **`mean_prompt_tokens` post-dates the Q56 and U100 runs** (added in `29703ef`, 2026-08-17, the
    same commit as `peak_prompt_tokens` and the descriptor's 4th capture group). Derive it as
    `tokens_in / iterations` rather than dropping those 1,180 cells.
12. **U100 is 10 tasks, not 31.** A U100 run has 31 *cells* spread across four arms.

## Donor commits

v1 `d5528ea`, BCF `d6c1601`, corpus commits `de26d3d` / `665038b` / `0766e6d`.
