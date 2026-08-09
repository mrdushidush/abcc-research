# W8 — the first full Q56 campaign (n=2, 448 measured cells)

Two complete repetitions of all 224 Q56 cells, run back to back on 2026-08-09 against subject
`claudette-af3f804`. This is the measurement the workstream exists for: **the first operator-control
numbers taken on a corpus where every task can fire a permission gate.**

Evidence: `research/spikes/w8-repeats/RESULTS-q56-n2.txt` (committed), run artifacts under
`runs/q56/w8-1786245496371/` and `runs/q56/w8-1786256305205/` (gitignored — runs are evidence, not
deliverables).

## Held constants

| | |
|---|---|
| subject | `claudette-af3f804`, driven over the REPL pipe, one fresh process per cell |
| model | `qwen3.6-35b-a3b-mtp@iq3_s`, **confirmed by the endpoint**, not just requested (F33) |
| window | LM Studio **65536** loaded, `CLAUDETTE_NUM_CTX=61440` — the F50 inequality, ~4K cushion |
| parallel | 1, full GPU offload, RTX 5060 Ti, 15.0–15.2 GiB of 16.3 |
| corpus | `de26d3d`, suite `q56`, 56 tasks × 4 variants |
| caps | `max_iterations = 40`, `num_predict = 8192` |
| preamble | **4855** then **4859** `tokens_in` — 4 tokens apart across two runs |

**⚠ `kv_cache_type` was not pinned.** Every donor row records `kv=q8_0`; this campaign inherited LM
Studio's sticky setting, which neither `lms ps` nor `/api/v0/models` reports. Recorded as a known
uncontrolled variable, and the first thing to fix before the next campaign.

## 1. The control variant reproduces the donor's own score, twice

**`control` = 50/56 in run 1 and 50/56 in run 2.** The donor's eight recorded champion runs scored
**49, 50, 50, 50, 48, 52, 50, 50** — so W8's control sits exactly on the donor's median, and did so
twice.

This is the strongest available evidence that the import is faithful, and it disposes of the
apparent discrepancy the campaign raised mid-flight ("this model scored 50/56 two weeks ago, why is
the rate lower?"). It was never lower. The low-looking aggregate — 173 and 178 of 224 — pools three
variants that inject gates, redirects and a denial **the donor never had**. Only `control` is
donor-comparable, which the suite caveat states as an import-time fact.

The failures agree too. Control fails **Q03, Q05, Q46** in *both* runs; the donor's failure
frequency across its eight runs is Q03 **8/8**, Q05 6/8, Q46 4/8. Every stable W8 control failure is
a task the donor also failed.

## 2. Pass counts

| variant | run 1 | run 2 | mean | vs `control` |
|---|---|---|---|---|
| `control` | 50/56 | 50/56 | **50.0** | — |
| `gated` | 48/56 | 52/56 | **50.0** | **0** |
| `redirect-first-edit` | 46/56 | 43/56 | **44.5** | **−5.5** |
| `deny-first-edit` | 29/56 | 33/56 | **31.0** | **−19.0** |

## 3. Cost, as medians over 112 pooled cells per variant

Medians, never means — the spread is wide and one outlier cell would move a mean.

| variant | wall | iterations | `tokens_in` | `gate_fires` |
|---|---|---|---|---|
| `control` | 19.3 s | 7.0 | 35,043 | 0 |
| `gated` | 16.7 s | 6.5 | 35,229 | 2.5 |
| `redirect-first-edit` | 32.6 s | 9.0 | 57,430 | 3.0 |
| `deny-first-edit` | 20.5 s | 6.0 | 28,834 | 2.0 |

**The gate itself is free.** `gated` costs **+186 input tokens** against `control` — 0.5% — with
half an iteration *fewer* and no pass-rate cost at all. On u100 the same comparison gave +2,702
tokens and +0.5 iterations. Both readings say the same thing, and Q56 says it on a corpus where the
gate actually fires on every task rather than on ~14 of 90.

**One redirect costs +22,387 input tokens, +2 iterations, +13.3 s, and 5.5 passes.** u100 measured
+14,979 tokens and +3 iterations. **The iteration cost is the same size on both corpora; the token
cost is larger on the harder one**, which is what one would expect if the redirect makes the subject
re-read more context.

## 4. F54 — every cell gates. The reason the second donor was sourced, confirmed by execution

`gate_fires ≥ 1` on **56 of 56 cells in all three gated variants**, and **0 of 56** in `control`.
Minimum 1, median 2–3, maximum 35.

U100 could not do this. Creating a new file never fires a gate and touching an existing one always
does (F39), and 76 of u100's 90 tasks start from an empty fixture — so at most ~14 could gate, and
*which* ones did depended on the model's tool choice (F30's lottery). Q56 ships a non-empty fixture
on all 56 (F40), so gating is **structural**. The lottery is retired as a threat to the measurement.

Two supporting facts, both clean across all 448 cells: `unscripted_gates = 0` everywhere, so the
operator script met every gate that fired; and `interventions_delivered = 1` on every one of the 112
redirect cells, exactly as authored. Delivery was faithful on all 224 cells per run (220 `line`,
4 `sentinel`).

## 5. F55 — deny and redirect have opposite cost shapes, and that is the operator's real trade

- **A redirect is expensive in resources and cheap in outcomes**: +22,387 tokens, +2 iterations,
  +13.3 s — and it still finishes **44.5 of 56**.
- **A denial is cheap in resources and expensive in outcomes**: **−6,209 tokens, −1 iteration** —
  and it finishes only **31 of 56**.

A denial costs *less* than doing nothing because the subject frequently **stops rather than working
around it**. So the two interventions an operator might reach for trade in opposite directions, and
**a harness that measured only tokens or wall-clock would have ranked denial the cheaper control** —
it is cheaper, and it destroys 38% of the work.

This is the axis §14 item 1 of the brief says is unmeasurable in a corpus whose unit is one
invocation against a fixture. It is the first W8 number no donor baseline can express at all.

## 6. F56 — reproducibility degrades as the operator intervenes more

Cells whose verdict is not identical across the two runs:

| variant | flips | rate |
|---|---|---|
| `control` | 6/56 | 11% |
| `gated` | 6/56 | 11% |
| `redirect-first-edit` | 14/56 | 25% |
| `deny-first-edit` | 22/56 | 39% |

**48 of 224 cells (21%) flipped**, and the ordering is monotone in how much the operator interferes.
The gate alone adds no instability — `gated` matches `control` exactly at 6 flips. Intervening does.

This sharpens u100's F52, where `redirect-first-edit` carried 4 of 7 flipping cells but the sample
was too small to say more. **The practical consequence is a sampling rule: `control` and `gated`
claims are defensible at n=2, and `redirect`/`deny` claims are not.** The pass-rate spreads say the
same thing — `control` was 50 and 50, while `deny` was 29 then 33.

Only **Q03, Q05, Q46** fail control in both runs. Everything else in the control column that failed,
failed once.

## What this does and does not license

**Licensed:** the gate is free; a redirect costs about +22k tokens and +2 iterations on this corpus;
denial destroys roughly a third of completions; every Q56 task is gate-capable; the import is
faithful to the donor's own scoring.

**Not licensed:** any single cell (n=2, and 21% of cells flip); any comparison of *absolute* pass
rate against the donor's beyond `control`, since the harness, the scaffold and the context window
all differ; and anything about `deny`/`redirect` magnitudes to better than ±4 passes.

**Next:** pin `kv_cache_type = q8_0` to match the donor's rows, and take `redirect` and `deny` to
n=5 — they are the two variants whose numbers are still soft, and they are the two the workstream
cares most about.
