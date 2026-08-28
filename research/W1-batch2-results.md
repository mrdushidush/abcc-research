# W1 batch 2 — champion vs TWO Qwen3.8-27B builds, one session, matched constants

Run 2026-08-27 23:54 → 2026-08-28 05:17 unattended. Driver `scratch/overnight-k-b2.sh`,
console log `runs/overnight-k-b2.log`. **Findings below need F-numbers assigning** — W9 closed at
**F463** on 2026-08-28, so the next free number is **F464**; they are left unnumbered here.

## Why a third arm

Batch 1 (F87–F92) measured the champion against `unsloth/Qwen3.8-27B-UD-Q3_K_XL` on 2026-08-18.
David downloaded `byteshape/Qwen3.8-27B-IQ4_XS-3.67bpw` on 2026-08-27 expecting a **quality**
upgrade. It is not one, and the filename is why.

**Measured from the tensor table, not the filename.** Both 27B GGUFs are structurally identical
— 866 tensors, 65 blocks, `blk.64` = the MTP layer, 17 full-attention blocks at `[3,7,…,63,64]`
— so quantization is the only difference:

| build | effective bpw | FFN tensors |
|---|---|---|
| champion `IQ3_S-3.06bpw` | **3.064** | IQ3_XXS 83.4%, IQ2_XXS 11.3% |
| byteshape 27B `IQ4_XS-3.67bpw` | **3.674** | IQ3_XXS 57.1%, IQ4_XS 35.6%, IQ2_XXS 1.3% |
| unsloth 27B `UD-Q3_K_XL` | **3.933** | IQ3_S 42.4%, IQ4_XS 47.9%, **no IQ2** |

▶ **"IQ4_XS" is the headline type, not the rate.** Only 35.6% of byteshape's params are IQ4_XS;
the majority is IQ3_XXS (3.0625 bpw), plus IQ2_XXS in three `ffn_gate` tensors. It lands
**0.26 bpw BELOW the build batch 1 already tested.** Arm C re-runs unsloth **in the same session**
because F59 says the token baseline steps ~10% between sessions, so batch 1's numbers are not
safely comparable to tonight's.

## Held constants

`--suite k --variant control`, n=3 per arm, subject `claudette-af3f804` (**force-rebuilt this
session** — cargo printed `Compiling`, not a cache hit), `--num-ctx 40000` under
`lms load … -c 40960 --gpu max --parallel 1`. Backend `llama.cpp-…-cuda12-avx2-2.27.1`.
Every arm captured its own fresh `llama-server` command line (F75); all three carried
`--cache-type-k/v q8_0`, `--flash-attn on`, `--kv-unified`, `--spec-type draft-mtp
--spec-draft-n-max 2`, `--batch-size 2048 --ubatch-size 512`. ⚠ `--threads` is **2** for the
champion and **4** for both 27Bs — the same uncontrolled asymmetry batch 1 carried.
VRAM at load: A 14,417 MiB, B 14,454 MiB, C 15,420 MiB. No arm spilled.

✅ **The driver's load-guard is worth reusing.** After each `lms load` it greps the live
command line for that arm's expected `.gguf` and aborts the arm if absent. Without it a failed
load silently measures the *previous* arm at full plausibility. All three guards passed.

## Result

| arm | pass | fail | timeout | wall clock, 9 cells | vs champion |
|---|---|---|---|---|---|
| A champion 3.064 bpw | 6 | 3 | 0 | 1,352 s | — |
| B byteshape 27B 3.674 bpw | 8 | 0 | 1 | 11,202 s | **8.3×** |
| C unsloth 27B 3.933 bpw | **9** | 0 | 0 | 6,615 s | **4.9×** |

C's 4.9× reproduces batch 1's 5.2× closely — a good cross-session reproducibility signal.

### The champion's three failures are all one task, and only ONE is real

All three land on `finish_the_cancelled_status`, and the workdir diffs show it hit **all four
sites** (`charges.py`, `retry.py`, `sla.py`, `summary.py`) in every repeat. Nobody took the sham.

- **r1 — a genuinely broken artifact.** It rewrote `summary.py`'s leading `if job.status ==
  st.QUEUED:` as `elif`, leaving an `elif` with no `if`. `python run.py` dies with
  `SyntaxError: invalid syntax` at line 17. **This failure mode is new — batch 1 never produced it.**
- **r2, r3 — the F308 format failure**, reproduced verbatim: it replaced `other` with `cancelled`
  in `summary.BUCKETS`, so `COUNTS` prints no `other=0` and the verifier rejects it. The behaviour
  is right; the ticket never asks for the format to be preserved.

▶ **F308-adjusted the champion scores 8/9, which reproduces batch 1 exactly.** But note batch 1
saw this BUCKETS substitution in 1 of 3 repeats and batch 2 saw it in **3 of 3** — the champion
makes that choice reliably, and W1's recorded "verdict instability" was the verifier catching a
consistent behaviour inconsistently.

### The champion patched the call site again — and the verifier let it through

🚨 On `round_at_the_line_not_the_total` **r2 the champion never touched `billing/pricing.py`.**
It left `total_of` summing raw floats and quantizing once at the end — the original defect — and
fixed the symptom in `billing/invoice.py` instead. Its own inline comment correctly diagnoses the
bug in `total_of` and then leaves it in place. **The cell PASSED.** This is exactly the shape F87
recorded for the champion in batch 1, now reproduced on a different task, and it means the `round`
verifier does not discriminate a root fix from a call-site fix. Any other caller of
`pricing.total_of` is still wrong.

Both 27B arms fixed `total_of` at the root in every completed repeat. Arm B r1 wrote
`sum_amounts([line.total …])` without the explicit per-line `quantize` — **still correct**, because
`sum_amounts` calls `to_cents` on every element itself.

### Both 27Bs write tests; the champion never does

On `finish_the_cancelled_status` both 27B arms edited `tests/test_jobs.py` in all three repeats
(B also touched `README.md`). The champion edited it **zero times in three**. That reproduces F87.

### `trace_dropped_samples` — the redundant guard is universal, third confirmation

All 27 cells across all three arms edited **both** `pipeline/ingest.py` (the root, per refsol)
**and** `pipeline/stats.py` (the sham site). Every arm passes. Not a differentiator.

### 🚨 The new finding: byteshape blows through the context window

| arm | peak_prompt_tokens (min / med / max) | max occupancy of the 40,000 pin |
|---|---|---|
| A champion | 12,031 / 17,151 / 19,199 | 48% |
| C unsloth 27B | 18,216 / 21,288 / 26,408 | 66% |
| B byteshape 27B | 19,240 / 25,384 / **40,744** | **102%** |

*(`peak_prompt_tokens` is quantized to 1024 and is a floor — read these as "at least".)*

Byteshape needs **43% more iterations** than unsloth (25.5 vs 17.8 mean) and emits **23% more
output tokens** (212,072 vs 173,059) to reach a worse result. Its one timeout — `round` r3 —
**made no code edit at all**: the workdir contains only `out_before.txt` / `out_before_utf8.txt`,
the subject went silent at 279 s (`subject_last_output_ms`), emitted 1,049 bytes total, and burned
the remaining ~35 minutes of the 2400 s ceiling producing nothing. Legible only because of F91's
`seal()`.

Per-task mean wall clock shows byteshape slower on **every** task, worst on `round` at 3.5×:

| task | A champion | B byteshape | C unsloth |
|---|---|---|---|
| `finish_the_cancelled_status` | 104 s | 1,003 s | 775 s |
| `round_at_the_line_not_the_total` | 132 s | 1,160 s | 331 s |
| `trace_dropped_samples` | 215 s | 1,570 s | 1,099 s |

## What this settles

1. **The byteshape build is not a quality champion — it is dominated by the unsloth build on every
   axis measured**: verdicts (8+1 timeout vs 9/9), wall clock (11,202 vs 6,615 s), peak context
   (102% vs 66% of the pin), iterations, output tokens. Its one real advantage is the ~880 MB that
   lets it hold **64k fully resident**, which unsloth cannot. It is a **context** build, not a
   quality one. Lower bpw bought more flailing, not less.
2. **The unsloth 27B is the strongest brain measured on this box**: 9/9, right-reason on all three
   discriminators, root-fixes where the champion patches call sites, and it writes tests.
3. **The champion's quality case is weaker than batch 1 suggested.** It shipped code that does not
   parse (1 of 9), and it passed a cell by fixing a call site while leaving the defect in place.
4. **The price is unchanged and it is the whole argument**: 4.9× the wall clock, reproducing
   batch 1's 5.2×. Nothing here moves that number.

## Open

- The `round` verifier passes a call-site fix (champion r2). Deciding whether that should FAIL is a
  W8 call, like OQ-W6-10 — and it would change the recorded batch 1 cells too.
- F90 still open: the champion never exceeded 48% occupancy, so the arms remain in different
  context regimes. Byteshape's 102% is pressure from *inefficiency*, not from fixture size.
- `--threads` 2 vs 4 remains uncontrolled across arms.
