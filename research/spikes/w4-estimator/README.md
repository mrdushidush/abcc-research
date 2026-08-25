# w4-estimator — is a pre-dispatch estimate worth anything, and what does it cost?

Spike for **W4 item 3** (`research/W4-routing.md`, findings **F376–F385**). Run 2026-08-25/26 on the
champion `qwen3.6-35b-a3b-mtp@iq3_s`. **414 estimator calls over 69 tasks × 6 arms**, plus a
repeatability pass and two diagnostics.

This is the first W4 item that needed the GPU: items 1 and 2 were desk work over cells already on
disk.

## Held constants

| | |
|---|---|
| model | `qwen3.6-35b-a3b-mtp@iq3_s`, loaded `-c 65536 --gpu max --parallel 1` |
| `llama-server` | pid 20848, `--ctx-size 65536 --parallel 1 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --kv-unified --batch-size 2048 --spec-type draft-mtp --spec-draft-n-max 2` |
| sampler | `temperature: 0.0` — the value claudette sends in production (`api.rs:783`) and the value all 378 outcome cells ran under |
| `max_tokens` | 6000 (W2 F82: the reasoning trace is unconstrained and is spent first) |
| endpoints | LM Studio proxy `:1234` for the four trace arms; bare `llama-server` `:64703` for the two `nothink` arms — see trap 2 |

## What it proved

1. **The estimator is not free.** p50 wall clock **17.19–28.38 s** on the production path against
   Q56's **19.1 s** median attempt, and **8.71×–17.66×** the entire retry budget it would be
   allocating on Q56. On the no-think path it is **0.94–2.00 s**. **F376**
2. **`chat_template_kwargs: {"enable_thinking": false}` is honoured by bare `llama-server` and
   silently DROPPED by LM Studio's proxy** — same weights, same load, HTTP 200, full trace. That one
   field is 10× on every short structured call. `/no_think` does not work through the proxy either.
   **F377**
3. **An integer schema silently truncated `0.95` to `0` on every task.** The prompt said
   "probability", the model answered on 0–1, the grammar admitted only an integer, and the emitted
   stream stopped at the integer prefix. Valid JSON, right field, in range, wrong. **F378**
4. **No model arm beats counting the prompt's bytes, and at n = 56 nothing beats anything.** Best
   model arm ρ +0.288 / AUC 0.672 (19.41 s) against prompt bytes ρ +0.269 / **AUC 0.691** (free) —
   and **every paired bootstrap difference spans zero**, with six of nine AUC intervals including
   0.5. **OQ-W4-3 closes: no.** ⚠ This qualifies F362's ordering in place. **F379**
5. **Asked to score complexity the champion returns a near-constant**: all 10 U100 tasks score
   **2**, and 46 of 69 score 2 on Q56 — v1's own 149-of-149 floor, reproduced with a model instead
   of keywords, because the rubric measures engineering *scope* and every corpus task is a
   single-function edit. **F380**
6. **Asking the question routing actually needs is worse**: `pass_pct` ρ +0.172 / AUC 0.616, the
   most expensive arm, and **no answer at all on 9 of 69** (`finish_reason: length` at 6000 tokens,
   `content: ""`, HTTP 200). **F381**
7. **The estimator names the risk and does not price it.** 50 of 69 traces mention the hidden tests
   explicitly; mean estimate 92.9% against a measured 88.2% on Q56 and **88.3% against 66.7% on K** —
   most overconfident where the tasks are hardest. The deciding fact is not in the request: all 56
   Q56 `task.toml`s say so, and Q03 (0 of 5) turns on a `split_bill(7, 0)` no-panic test the prompt
   never mentions. **F382**
8. **The reasoning trace costs 10.25× and buys ΔAUC +0.025**, which the bootstrap cannot separate
   from zero; the schema's field order moves **17%** of the readings. **F383**
9. **Task kind and language carry no signal**: `kind` 7-fold CV ρ −0.239 / AUC 0.375, permutation
   **p = 0.908**. **OQ-W4-5 closes: no.** **F384**
10. **A *perfect* a-priori oracle spends more attempts than reacting** — 1.286 vs 1.118 per task on
    Q56 — because a task that fails is identified by failing. The ceiling is negative before the
    estimator's own cost. **F385**

## Files

| file | what it is |
|---|---|
| `tasks.py` | builds the population: the 69 tasks with both a prompt and a control-arm answer key, plus every free a-priori feature → `tasks.jsonl` |
| `estimate.py` | the six arms; `--out`, `--arms`, `--repeats`, `--rep-offset`, `--tasks`, `--limit` → `estimates.jsonl` |
| `analyze.py` | cost, discrimination, ρ/AUC vs the free baselines, arm-vs-arm, calibration, the oracle ceiling, the corpus bill, and the bootstrap → `analyze-out.txt` |
| `diag_schema.py` | why `pass_prob` returned 0 on every task — six schema variants, one change at a time (trap 1) |
| `diag_think.py` | the units fix, and whether the trace can be switched off through the proxy |
| `diag_hop.py` | the 2×2 that separates the hop from the trace → `diag_hop-out.txt` (trap 2) |
| `pilot.jsonl`, `smoke.jsonl` | the pilot and the six-arm smoke test, kept because trap 1 lives in them |
| `estimate-run0.log`, `estimate-run1.log` | the main run and the repeatability pass — **gitignored** (`*.log`); regenerate by re-running |
| `repeat-tasks.txt` | the 21-task subset the repeatability pass used |

Regenerate:

```sh
python tasks.py                                     # -> tasks.jsonl
python estimate.py --out estimates.jsonl --repeats 1            # ~2 h, 414 calls
python estimate.py --out estimates.jsonl --repeats 1 --rep-offset 1 \
       --tasks "$(cat repeat-tasks.txt)"                        # repeatability
python diag_hop.py > diag_hop-out.txt
python analyze.py > analyze-out.txt
```

⚠ `estimate.py` **appends** to `--out`. Delete the file to start clean, or the reps will double up.

## Traps

1. 🚨 **A constrained integer field can truncate rather than fail.** The first pass-estimate arm
   returned `{"p_pass": 0}` on every task and it was believed for as long as it took to run
   `diag_schema.py`. The model was answering 0.95. **Name the unit in the prompt AND in the field
   name**, and treat "the bottom of the range on every input" as an alarm. See F378.
2. 🚨 **The two endpoints are not interchangeable and the difference is silent.** LM Studio's proxy
   drops `chat_template_kwargs`. If the `nothink` arms had gone to `:1234` they would have been
   ordinary trace arms wearing a different label, and the cost table would have shown no difference
   at all. `diag_hop.py` is the 2×2 that keeps hop and trace apart; run it before trusting either.
3. 🚨 **Leave-one-out group encoding manufactures its own answer.** `(S_g − x_i) / (n_g − 1)` is a
   strictly decreasing function of the value it predicts, so within a group it is perfectly inversely
   ranked with the answer. On U100, where all 10 tasks share one `kind`, it returns **ρ = −1.000** on
   data with no signal. Use folds, and print nothing at all for a single-group column.
4. **ρ is a weak instrument on this population.** 40 of 56 Q56 tasks pass 5/5, so most of the outcome
   column is one value and the rank correlation is dominated by ties. AUC over "ever failed" is the
   metric that matches the question; report both.
5. 🚨 **Quote no ordering from the ρ/AUC table without the bootstrap.** Every paired difference spans
   zero at n = 56 and six of nine intervals include the coin. The point estimates are one draw from
   intervals ~0.3 AUC wide, and that applies to item 1's +0.219 bar as much as to item 3's arms.
6. **The reasoning trace shares the payload's token budget and is spent first.** 9 of 69 `pass_pct`
   calls returned `content: ""` at `max_tokens: 6000`. Empty content on a 200 is an error.
7. **Stratify K to the champion at `max_iterations = 40`** — `runs/k-champ-r*` + `runs/w11-b40-r*`.
   The six `k-27b-*` families are a different model and `w11-b12`/`w11-b20` are different loop
   budgets (item 2's trap 9). And K is **3 tasks**: corroboration, never a number.
8. **U100 is 10 tasks and all of them are `kind = bugfix`**, so no group statistic is available there
   at all.
9. **The estimator reads the prompt only.** Item 2 already measured the workspace (ρ(fixture bytes,
   pass) = −0.069), so this is not the gap it looks like — but it is stated rather than assumed. See
   OQ-W4-13.

## Donor source

v1's Haiku prompt is `packages/api/src/services/complexityAssessor.ts:47-67`, reproduced
byte-for-byte in `estimate.py` as `V1_PROMPT`, with the free-text JSON extraction from `:95`. The
dual-assessment weighting at `:117-161` is not exercised here — F366 already showed the rule half
contributes only a floor.
