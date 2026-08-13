# W8 — the full Q56 campaign (784 measured cells; `redirect`/`deny` at n=5)

Two complete repetitions of all 224 Q56 cells, run back to back on 2026-08-09 against subject
`claudette-af3f804`, plus **three further repetitions of the 112 `redirect`/`deny` cells on
2026-08-13** (§7). This is the measurement the workstream exists for: **the first operator-control
numbers taken on a corpus where every task can fire a permission gate.**

Evidence: `research/spikes/w8-repeats/RESULTS-q56-n2.txt` and
`research/spikes/w8-repeats/RESULTS-q56-rd-n5.txt` (both committed), run artifacts under `runs/q56/`
(gitignored — runs are evidence, not deliverables).

⚠ **Sections 1–6 report the n=2 campaign as it stood. §7 supersedes two of its numbers** — read it
before quoting any `deny` magnitude.

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

**⚠ `kv_cache_type` was not pinned *by the harness* — but it was not floating either. Resolved
2026-08-09 (session 12), and the answer is `q8_0`, matching every donor row.**

The setting lives in LM Studio's per-model sticky config, not in anything the runner controls:

```
~/.lmstudio/.internal/user-concrete-model-default-config/
  byteshape/Qwen3.6-35B-A3B-MTP-GGUF/Qwen3.6-35B-A3B-IQ3_S-3.06bpw.gguf.json
```

It carries `llm.load.llama.kCacheQuantizationType` and `...vCacheQuantizationType`, both
`{checked: true, value: "q8_0"}`. Four things make it the operative value for this campaign:

- the file's mtime is **2026-08-08 14:59**, before both runs (06:18 and 09:18 on 08-09);
- **loading a model does not rewrite it** — the 08-09 06:16 load left the mtime untouched, so it is
  a stable preference and not a load journal;
- **`lms load` has no KV flag at all**, so the command line could not have overridden it;
- the three values the CLI *does* set — `contextLength 65536`, `numParallelSessions 1`,
  `offloadRatio 1` — match the file exactly, while its other keys (`tryMmap`, `cpuThreadPoolSize`,
  `keepModelInMemory`) have no CLI expression and must come from somewhere.

**The reporting gap is real and stands: `lms ps`, `lms ps --json` and `GET /api/v0/models` all omit
the KV cache type**, so `server_uncaptured: ["kv_cache_type"]` in RUNMETA remains correct. The one
mechanism that *would* record it is LM Studio's own engine log — `llama_kv_cache: CUDA0 KV buffer
size = N MiB` appears in the May 2026 server logs and is absent from August's, gated by
`fileLoggingMode` in `~/.lmstudio/.internal/http-server-config.json`. That key is a validated enum
whose accepted values are not discoverable from outside the app: setting it to `"verbose"` was
silently rejected and reset to `"succinct"` on restart. **Reading it off the GUI load panel, or
finding the valid enum value, is the way to close the capture gap for good.**

⚠ **VRAM does not identify the KV type here, and two plausible-looking readings of it are wrong.**
The `13.61 GB` in `lms ps` and the `12.67 GiB` from `lms load` are the *weights*, invariant across
KV settings — the donor's own `gib` column is 12.67 on every champion row regardless of `kv`. And
the arithmetic does not close from the other end either: the GGUF gives 41 layers × 2 KV heads ×
(k 256 + v 256) = 41,984 bytes/token per byte of element width, so 65536 tokens needs ~2,788 MiB at
q8_0 and ~5,248 MiB at f16, while the measured load delta leaves only ~1,279 MiB unaccounted for
after weights. Filling the window confirms the puzzle rather than solving it: between prompts of
18,915 and 60,915 tokens, GPU VRAM moved **+2 MiB**. Whatever the allocator is doing, **VRAM is not
a measurement of KV element width on this stack — do not treat it as one.**

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

## 7. The top-up: `redirect` and `deny` at n=5 (session 14, 2026-08-13)

Three further repetitions of just the 112 `redirect`/`deny` cells, pooled with the two runs above.
`control` and `gated` are deliberately **not** re-run — F56 puts them at 11% cell flipping. Evidence:
**`research/spikes/w8-repeats/RESULTS-q56-rd-n5.txt`**. All three banked clean, `error: 0`.

```
redirect-first-edit  [46, 43, 46, 41, 44]  median 44  range 41-46
deny-first-edit      [29, 33, 33, 38, 37]  median 33  range 29-38
control [50, 50]   gated [48, 52]          (n=2)
```

| variant | pass | wall | iter | `tokens_in` | vs `control` |
|---|---|---|---|---|---|
| `control` (n=2) | 50 | 19.3 s | 7.0 | 35,043 | — |
| `redirect-first-edit` (n=5) | **44** | 32.0 s | 10.0 | 59,284 | **+24,241 tok, +3 iter, −6 passes** |
| `deny-first-edit` (n=5) | **33** | 20.7 s | 6.0 | 33,192 | **−1,851 tok, −1 iter, −17 passes** |

**The redirect number got stronger.** n=2 said +22,387 tokens, +2 iterations, −5.5 passes; n=5 says
**+24,241, +3, −6**.

⚠ **F55's "a denial *saves* 6,209 tokens" does not survive: at n=5 the saving is ~1,851, a 70%
shrink.** The qualitative finding — deny is the cheaper intervention that destroys far more work —
holds and is the point. The *magnitude* was an n=2 artefact. It is also measured against a `control`
still at n=2, so that delta's error is dominated by the un-topped-up baseline. **Quote the saving as
"small", not as a number, until `control` is itself at n=5.**

### F56 survives — but only when the statistic is computed correctly

`aggregate.py` reports *"cells whose verdict is not identical across all N runs"*: 65/112 at n=4 and
71/112 at n=5, against F56's 25%/39% at n=2. **That is a category error, not a regression** — the
statistic rises mechanically with N, because each added run is another chance to disagree.

The comparable statistic is the **mean pairwise flip rate**, and it reproduces F56 almost exactly:

| variant | pairs | mean pairwise flip rate | F56 at n=2 |
|---|---|---|---|
| `control` | 1 | 10.7% | 11% |
| `gated` | 1 | 10.7% | 11% |
| `redirect-first-edit` | 10 | **24.3%** | 25% |
| `deny-first-edit` | 10 | **35.2%** | 39% |

**The monotone ordering in operator interference is real and reproduces at n=5.**

### Two caveats specific to this top-up

- ⚠ **One cell of the 280 is `fail` by intervention, not by grading**: Q13/`deny-first-edit` in
  repetition 3, the F57 hang, killed by hand after 2h17m of verifier CPU. No other cell was touched.
- Repetitions 3–5 carried a **5-minute cooling pause between runs** (operator request). The gap is
  between repetitions, never inside a cell.

## What this does and does not license

**Licensed:** the gate is free; a redirect costs about **+24k tokens and +3 iterations** and −6
passes; **denial destroys about a third of completions (−17 of 50) while costing slightly fewer
resources**; every Q56 task is gate-capable; reproducibility degrades monotonically with operator
interference; the import is faithful to the donor's own scoring.

**Not licensed:** any single cell; any comparison of *absolute* pass rate against the donor's beyond
`control`, since the harness, the scaffold and the context window all differ; **the size of denial's
token saving**, which moved by 70% between n=2 and n=5 and is measured against an n=2 baseline; and
any `control`/`gated` magnitude to better than what n=2 supports.

**Next:** bound the verify phase (F57 — `verify.rs:142` calls `Command::output()` with no timeout).
Deliberately **not** done mid-campaign, because changing the harness between repetitions would break
comparability with runs 1–2. After that, brief §14 item 2 (W1+W2). Taking `control` to n=5 is the
cheapest way to firm up the remaining soft number.

Pooling a 112-cell top-up with the 224-cell runs requires the aggregator's variant filter, added for
exactly this reason:

```
python research/spikes/w8-repeats/aggregate.py runs/q56 \
    --variant redirect-first-edit --variant deny-first-edit
```

⚠ **Without `--variant` the aggregator keeps the majority cell set, and three 112-cell runs outvote
two 224-cell runs — the two full runs above would be silently dropped.** The runner script and its
reasoning are `research/spikes/w8-repeats/repeat-rd3.sh`.
