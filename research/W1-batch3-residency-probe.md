# W1 batch 3 — the three new arrivals, and a residency cliff that `nvidia-smi` cannot see

**Status: PROBE COMPLETE, no K-series run yet. Three models were put on the bench at David's
request. One of them is not a model. The other two are real, and both top out at exactly the same
context — 40960 — which is the window at which, for the first time, EVERY 27B build on disk is
simultaneously fully resident and within 6% of the same decode rate.** Findings **F613–F621**; next
free number is **F622**. Measured 2026-09-05 on the RTX 5060 Ti, 16,311 MiB, desktop baseline
**1,148 MiB** measured with nothing loaded in this same session.

▶ **The headline for the roster: the matched-bpw quality experiment the roster has wanted since
2026-08-28 is now runnable, and its bpw spread is 0.065 rather than the 0.16 that was planned.**

---

## 1. What was measured, and with what

Two instruments, both written this session and both validated before use.

* **`ggufinfo.py`** — a from-scratch GGUF header parser (no `gguf` lib on this box, no `llama-gguf`
  binary in the LM Studio backend). Walks the tensor table, sums `(n / block_size) * type_size` per
  tensor, reports effective bpw and the per-type share.
  **Positive control: it reproduced all three bpw figures already on record — 3.064, 3.674, 3.933 —
  exactly, and reproduced unsloth's recorded per-type shares (IQ3_S 42.4 / IQ4_XS 47.9 / no IQ2) as
  42.41 / 47.95 / none.** Only then was it pointed at anything new.
* **`gpumem.ps1`** — the `\GPU Process Memory(pid_*)\Dedicated Usage` / `Shared Usage` counters for
  the live `llama-server`, which is the only thing on this box that distinguishes VRAM from
  driver-paged system memory. It prints its matched instance count so a zero can never be read as a
  measurement.

## 2. F613 — the Flash-Next download is not a model, and the catalogue cannot tell

`unsloth/Qwen3.8-Flash-Next-GGUF/mtp-Qwen3.8-Flash-Next-BF16.gguf`, 7.24 GiB, arrived 2026-09-05.

**It contains 34 tensors. Every one of them is in `blk.48`, plus `token_embd` and `output`.** The
metadata says `qwen4exp.block_count 49` and `qwen4exp.nextn_predict_layers 1` — so blk.48 IS the MTP
layer, and **blocks 0–47, the entire model, are absent.** 2.37 GiB of the file is nothing but the
two 248320x2560 BF16 embedding matrices; 4.69 GiB is the single MTP layer's 512 experts.

▶ **This is the speculative-decoding sidecar, as its `mtp-` filename prefix says.** It cannot be
loaded and run. The main model file still needs downloading.

🚨 **`lms ls` lists it as `qwen3.8-flash-next / 512x1.4B / qwen4exp / 7.77 GB`, which is
indistinguishable from a real model** — because `general.size_label` in the sidecar is the PARENT
model's label. **A catalogue row is not evidence that a model is present.** The witness is the
tensor table: a 65-block 27B carries 866 tensors, and this carries 34.

## 3. F614–F615 — what the two real files actually are

Both are structurally identical to Qwen3.8-27B: 866 tensors, 65 blocks, `blk.64` = MTP,
`full_attention_interval` 4. So quantization is the only difference, exactly as in batch 2.

| build | filename claims | **measured bpw** | weights | dominant types |
|---|---|---|---|---|
| byteshape `IQ4_XS-3.67bpw` | 3.67 | **3.674** | 11,965 MiB | IQ3_XXS 57.1%, IQ4_XS 35.6% |
| unsloth `UD-Q3_K_XL` | — | **3.933** | 12,808 MiB | IQ4_XS 47.9%, IQ3_S 42.4% |
| **Qwopus `Flash-MTP-Q3_K_M`** | — | **3.950** | 12,865 MiB | **Q3_K 62.6%, Q4_K 31.0%** |
| **byteshape `IQ4_XS-4.00bpw`** | 4.00 | **3.998** | 13,020 MiB | IQ4_XS 54.3%, IQ3_XXS 35.2% |

* **F614 — the filename is honest this time, and it is the same publisher that oversold last time.**
  byteshape's `4.00bpw` measures 3.998. Batch 2's lesson was that byteshape's `IQ4_XS-3.67bpw` was
  majority IQ3_XXS and 0.26 bpw BELOW the unsloth build; **this new file genuinely clears unsloth,
  and is the highest-bpw 27B on disk.** ▶ A publisher's past mislabelling does not transfer to its
  next file. Measure each one.
* **F615 — Qwopus is the only K-quant 27B here.** `general.name` is *"Qwopus3.8 27B Flash Merged
  16bit"*, and it is a plain `Q3_K_M` ladder (Q3_K 62.6% / Q4_K 31.0%) where every other 27B on disk
  is an I-quant build. Same architecture, so it is a merge/fine-tune of Qwen3.8-27B, not a new model.

## 4. F616 — `nvidia-smi` reports free VRAM on a model that has already spilled

byteshape 4.00bpw loaded at `-c 65536`. `lms load` said *"Model loaded successfully in 16.21s"*.

```
nvidia-smi          15800 MiB used,  251 MiB free      <- looks like it fits
GPU Process Memory  dedicated 15,107 MiB   SHARED 1,732 MiB   committed 16,839 MiB
```

**`nvidia-smi` does not count driver-paged shared system memory, so a model that overcommits by
1.7 GB reads as a model with 251 MiB to spare.** `main.log` says why this is possible at all:
`Limit weight offload to dedicated GPU Memory: OFF`. ▶ **Never certify residency from `nvidia-smi`.**

## 5. F617 — but shared usage is not a clean witness either; DECODE RATE is

The obvious next move is to treat `Shared Usage` as the spill detector. **It is not.** Held at one
model and walked up the context ladder, it barely moves while dedicated grows 2,400 MiB:

| byteshape 3.67 at ctx | 8192 | 32768 | 49152 | 65536 |
|---|---|---|---|---|
| dedicated MiB | 12,483 | 13,505 | 14,209 | 14,883 |
| **shared MiB** | **788** | **836** | **868** | **900** |

**~800–970 MiB of shared is the floor every arm pays, resident or not** — CUDA staging, not spill.
And at the cliff itself the counter is nearly blind: byteshape 4.00bpw at 49152 showed shared 932
MiB, a mere +80 over baseline, while its **decode rate had already halved.**

▶ **The sharp instrument is the functional one: tokens per second.** A memory counter says how
much was committed; only the clock says whether the machine is still working.

## 6. F618 — the ceiling is a cliff, not a slope

byteshape 4.00bpw, one model, four windows, same 6,334-token prompt:

| ctx | dedicated | shared | prefill tok/s | **decode tok/s** | verdict |
|---|---|---|---|---|---|
| 32768 | 14,559 | 836 | 811.9 | **35.10** | resident |
| 40960 | 14,911 | 852 | 829.1 | **35.22** | resident |
| 49152 | 15,199 | 932 | 491.1 | **15.73** | **2.24x collapse** |
| 65536 | 15,107 | **1,732** | — | **ZERO tokens in 208 s** | **hung** |

**Between 40960 and 49152 the model goes from full speed to half speed; by 65536 it emits nothing at
all in three and a half minutes.** David hit this independently and unloaded it: *"i unloaded the
4bpw - its stuck"*. ▶ **A hang and a slowdown are the same defect at two context settings**, and the
zero-token reading is a real measurement of an unusable configuration, not a broken instrument —
the same bench returned 461.7 / 35.34 tok/s against a working model minutes later.

⚠ Note dedicated at 65536 (15,107) is LOWER than at 49152 (15,199): once thrashing begins the driver
evicts weights to system memory, so **the memory figure improves as the machine gets worse.**

Qwopus fails the same way, less dramatically: at 65536 it returns 101.0 tok/s prefill and **5.87
tok/s decode** — an 8.2x / 5.9x collapse — where at 40960 it is healthy.

## 7. The correction: byteshape 3.67 IS fully resident at 64k

On first reading the 900 MiB of shared at ctx 65536, this probe called it a spill. **That was
wrong, and David said so at the time** — *"try the byteshape 3.67 instead. at iq4xs - its
resident"*. §5's ladder is what settles it: 900 MiB is the baseline every arm pays. The 3.67 build
holds 65536 with **dedicated 14,883 MiB and no excess shared at all**, and performs like it:

| byteshape 3.67 @ ctx 65536 | prompt 6,334 | prompt 23,834 |
|---|---|---|
| TTFT | 7.94 s | 23.66 s |
| prefill | 797.6 tok/s | 1,007.4 tok/s |
| decode | 36.6 tok/s | 35.06 tok/s |

▶ **Its context title stands, and it is the only 27B on disk that holds 64k.**

## 8. F619 — the matched-bpw experiment is now available, and it is TIGHTER than planned

At **ctx 40960 every 27B build on disk is fully resident**, on one card, in one session:

| build | bpw | dedicated | shared | prefill tok/s | decode tok/s |
|---|---|---|---|---|---|
| byteshape 3.67 | 3.674 | 13,857 | 852 | 839.9 | **37.50** |
| unsloth | 3.933 | 14,823 | 728 | 841.0 | 35.49 |
| Qwopus | 3.950 | 14,879 | 728 | **715.8** | 34.66 |
| byteshape 4.00 | 3.998 | 14,911 | 852 | 829.1 | 35.22 |

🚨 **The top three span 3.933 to 3.998 — a 0.065 bpw spread — and their decode rates span 34.66 to
35.49, under 2.4%.** The roster's planned matched-bpw arm was 3.933 vs 4.090 at 0.16 apart and
required deliberate expert offload because the MoE half overcommitted by ~1.8 GB.

▶ **This one needs none of that.** Same architecture, same 866 tensors, same context, same card,
all resident, all within noise on the clock. **Any K-series difference between these three is
attributable to the quantization and the merge, and to nothing else.** That is a cleaner controlled
comparison than batch 2 achieved, and it is the arm to run next.

⚠ **The 3.67 build's decode advantage (37.50, fastest of the four) is a bandwidth effect of being
the smallest file, and batch 2 already ruled that lower bpw bought MORE flailing, not less.** Speed
here is not evidence of quality.

⚠ These prefill/decode figures are `prompt_tokens / TTFT` and `completion_tokens / (total - TTFT)`
over the OpenAI-compatible endpoint, not llama.cpp's internal timings. They are internally
comparable — one session, one prompt, one method — and **must not be compared against the W1
figures recorded on 2026-08-17**, which used a different instrument.

## 9. F620–F621 — two smaller findings

* **F620 — the K-quant build pays ~15% of prefill.** At an identical 40960 window Qwopus returns
  715.8 tok/s where the three I-quant builds return 829–841. Its decode gap is much smaller (34.66
  vs 35.2–37.5). ▶ Q3_K/Q4_K kernels are the difference; it is the only structural axis separating
  these files apart from the merge itself.
* **F621 — `$pid` is a reserved automatic variable in PowerShell, and assigning to it fails into a
  plausible number.** The first version of `gpumem.ps1` did `$pid = (Get-CimInstance ...)`, which
  errored with `VariableNotWritable` and left `$pid` holding **the PowerShell host's own process
  id** — so the counter query matched a process with no GPU allocations and reported
  `dedicated=0 MiB SHARED=0 MiB`. **A wrong pid produces a clean, well-formed zero.** The fix that
  caught it was printing the matched instance count (5 of 140) alongside the reading.

## 10. What this leaves for the K-series

**Survivors, both at `-c 40960`, `--parallel 1`:**

1. **byteshape 4.00bpw (3.998)** — the highest-bpw 27B on disk and the direct successor to the build
   that LOST batch 2. The open question batch 2 raised: byteshape's file lost at 3.674 against
   unsloth's 3.933, so **does byteshape win when it is the one with more bits?**
2. **Qwopus (3.950)** — a merge, and the only K-quant. Costs 15% of prefill; the question is whether
   the merge buys anything back.
3. **unsloth (3.933)** — the incumbent quality champion and the control. Its 9/9 in batch 2 is the
   bar.

**Not runnable: Qwen3.8-Flash-Next** — the main model file is not on disk (§2).

⚠ **Budget from batch 2: unsloth ran 9 cells in 6,615 s.** Three arms at that rate is roughly 5.5
hours, and the byteshape arm in batch 2 took 11,202 s, so **pilot `trace_dropped_samples` first and
set `timeout_s` from the measurement** before committing 27 cells — a K-series timeout records no
verdict and no metrics at all.
