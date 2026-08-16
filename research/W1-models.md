# W1 — Model tiering around the base agent (desk half; measurements still open)

**Retrieval date for every external claim in this file: 2026-08-16.** Written after the peak
VRAM/RAM probe landed (`d7a0f67`, `harness/crates/hw-probe`, F60–F64) and before any new
measurement on the champion. §14 item 2 splits naturally in two, and this is the half that needed
no GPU: base-choice re-validation, tier partners, quantizer lineage, effective-vs-advertised
context, licensing. **The measurement half is untouched and listed in §Open questions.**

⚠ **Nothing in this file is a new number off this box.** Every VRAM figure quoted is either
*imported* from the donor's Q56 run metadata (`prestudy/data/q56-runmeta.tsv`, measured 2026-07)
or produced by `lms load --estimate-only`, which §Findings F69 shows is weights-only. New numbers
need the champion loaded.

## Question

The base agent is decided (§6, and §15 keeps it closed). This workstream asks what stands *around*
Qwen 3.6 35B-A3B on a 16 GB card whose binding constraint is VRAM residency, not system RAM
(§11.0): which model answers triage, which plays the adversarial gate that W6 needs, which frontier
models are worth a manual C10 call — and whether anything released since April has displaced the
base choice.

## Method

- **Base re-validation and tier survey**: web search + vendor model cards, every claim dated
  2026-08-16. Cross-checked release dates and licences against the primary source (Hugging Face
  model card or the vendor's own licence page), never an aggregator summary — which mattered twice
  (F71).
- **Residency**: `lms load … --estimate-only` for weight footprints on the models actually on this
  disk (26 of them, 341.64 GB), plus the donor's measured `vram_mib` column for real load figures.
  `--estimate-only` does not load the model, so this involved no GPU work and no heat.
- **Quantizer lineage**: byteshape's model card for the ladder, and the *donor's own* crowning
  document for the quality comparison — which turned out to be the load-bearing source (F70).
- **Not done**: any measurement requiring the champion resident. No throughput, no prefill/decode
  split, no quality-per-quant run, no agentic-under-context-pressure evaluation. Those are §14
  item 2's other half.

## Inherited

| From | What | Where |
|---|---|---|
| Claudette | The crowning that chose the champion, its speed decomposition, and the ShapeLearn-vs-unsloth quality tie | `prestudy/claudette-dossier.md:432-441`, `:644-654` |
| Claudette | Measured `vram_mib` for 14 model configs on this exact card at ctx 32768 / KV q8_0 | `prestudy/data/q56-runmeta.tsv` (col 8 `vram_mib`, col 11 `provenance`) |
| Q56 | The score column that must **not** be used as an agentic ranking (§11.0) | `prestudy/data-assets.md:97-98` |
| Phase 0 | "Residency is ~90% of the win"; the reframing from *survive offload into 32 GB* to *stay resident in 16 GB* | `prestudy/claudette-dossier.md:645-658` |
| W1/W2 | The probe that makes the open half measurable, and the F61 rule that residency claims need `--pid` | `harness/crates/hw-probe/README.md` |

## Findings

### F65 — the base choice is not displaced, and the one real challenger is already on this disk

Qwen3.6-35B-A3B: released **2026-04-15**, Apache 2.0, 35B total / 3B active, 40 layers, 256 experts
(8 routed + 1 shared), hybrid Gated DeltaNet + Gated Attention, 262,144 native context (1,010,000
with YaRN). Vendor-reported: SWE-bench Verified **73.4**, SWE-bench Pro **49.5**, Terminal-Bench 2.0
**51.5**, MCPMark **37.0**. Ships a `qwen3_coder` tool parser, structured outputs, and MTP.
([model card](https://huggingface.co/Qwen/Qwen3.6-35B-A3B))

What has landed since is mostly **irrelevant to this box because it does not fit**. The
June–August open-weights wave is large-MoE: GLM-5.2 (753B, MIT), Kimi K3 (2.8T), DeepSeek V4 Flash
(~284B/13B active, MIT, SWE-bench Verified 79.0). None is a 16 GB candidate; they are C10-class
models you would call, not host.

Three that *do* fit the class:

- **Qwen3.8-27B** — released **2026-08-14, two days ago**. Apache 2.0, **dense** 27.78B, natively
  multimodal, 262,144 native context. Vendor-reported SWE-bench Pro **61.7** against the
  champion's 49.5 — the one directly comparable pair, same vendor, same benchmark, **+12.2
  points**. Also Terminal-Bench 2.1 73.0, DeepSWE 1.1 42.2, OSWorld-Verified 84.3.
  ([model card](https://huggingface.co/Qwen/Qwen3.8-27B)) **Already downloaded here at 13.44 GB**,
  and a quality test against the champion is already on the books
  (`qwen38-27b-daily-driver-question`) — that memory records it fully resident at 32k and ~30 tok/s,
  1.9× slower than the champion, which is the price of dense-27B-active versus 3B-active.
- **Poolside Laguna XS 2.1** — released 2026-07-02, **OpenMDW-1.1**, 33B total / 3B active, 40
  layers, 256 experts + 1 shared, 262,144 context, built for agentic long-horizon coding.
  SWE-bench Verified **70.9**, SWE-bench Multilingual 63.1, SWE-Bench Pro 47.6, Terminal-Bench 2.0
  37.5. ([model card](https://huggingface.co/poolside/Laguna-XS-2.1)) Architecturally it is the
  champion's twin. **But the official GGUFs are BF16 and Q4_K_M only** — Q4_K_M on 33B lands near
  20 GB, well past this card. Not a candidate until a sub-3.5 bpw quant exists.
- **Cohere North-Mini-Code-1.0** — 2026-06-09, Apache 2.0, 30B/3B, 256K in / 64K out. Already on
  disk and already *measured* by the donor (F66).

**Verdict, stated plainly as the brief asks:** nothing has displaced Qwen 3.6 35B-A3B on the axis
that decides it. But **Qwen3.8-27B is a genuine open question, not a formality** — it is two days
old, it fits, it is downloaded, and its one comparable benchmark is 12 points ahead. The brief
forbids settling this on a score column (§11.0), and 12 vendor-reported points on SWE-bench Pro is
exactly the kind of number that has to survive agentic multi-file work under context pressure
before it means anything. The comparison is the first item of the measurement half.

### F66 — the residency ladder for this card is already measured, and it is in the repo

`prestudy/data/q56-runmeta.tsv` carries a `vram_mib` column nobody has read as a W1 artifact.
At **ctx 32768, KV q8_0, parallel 1, full offload**, on the RTX 5060 Ti (16,311 MiB):

| Model / quant | `vram_mib` observed | of 16,311 |
|---|---|---|
| gemma-4-e2b | 3,759 – 3,823 | 23% |
| gemma-4-e4b | 4,042 – 4,441 | 27% |
| gemma-4-12b-qat | 7,968 – 8,095 | 50% |
| qwen3.5-4b UD-Q8_K_XL | 8,878 – 8,934 | 55% |
| granite-4.1-8b Q8_0 | 12,042 – 12,173 | 75% |
| gpt-oss-20b | 12,395 – 12,527 | 77% |
| gemma-4-12b | 13,418 – 13,888 | 85% |
| **champion IQ3_S 3.06 bpw** | **14,362 – 14,820** | **88–91%** |
| gemma-4-26B-A4B-it UD-Q4_K_M | 14,245 – 15,512 | 87–95% |
| MTP-GPU-3 3.53 bpw *(inferred)* | 14,891 | 91% |
| North-Mini-Code UD-Q3_K_M | 15,095 – 15,219 | 93% |
| MTP-GPU-4 3.97 bpw | 15,330 – 15,669 | 94–96% |
| Qwen3-Coder-30B UD-Q4_K_XL | 15,482 – 15,494 | 95% |
| gemma-4-26b-a4b-qat *(the Q56 crown)* | 15,530 – 15,622 | 95–96% |
| Devstral Small 2 24B IQ4_XS | 15,497 – **15,848** | 95–**97%** |

Three rows are the champion at other settings, and they are the only KV evidence here:
**32768 / q8_0 → 14,820**, **32768 / f16 → 15,080**, **65536 / f16 → 15,772** (all `measured`).

The shape of this table is the finding: **above the champion's rung, every candidate is at 93–97%
of the card at half the daily driver's context.** The crowned config is recorded at 15.4 GiB of
16.3 at ctx 65536, and W8 ran at 15.0–15.2 GiB. There is no headroom tier here — there is a cliff.

⚠ **Do not compute KV cost from the deltas above.** The f16 32k→64k step is 692 MiB and the
q8_0→f16 step at 32k is 260 MiB, but F67 shows both sit inside the instrument's own noise, and
`always-test-on-the-champion-model` already records that this arithmetic does not close from the
GGUF side either.

### F67 — the donor's VRAM readings have a ~460 MiB noise floor, which is wider than the deltas people want from them

Repeats of *nominally identical* configs in the same table disagree:

- champion, 32768 / q8_0: 14,362 / 14,778 / 14,820 → **spread 458 MiB**
- Devstral IQ4_XS, same settings: 15,497 / 15,515 / 15,826 / 15,848 → **spread 351 MiB**
- gemma-4-e4b: 4,042 / 4,175 / 4,441 / 4,441 → **spread 399 MiB**
- gemma-4-26b-a4b-qat: 15,530 / 15,537 / 15,592 / 15,622 → spread 92 MiB

So a single reading is worth about ±0.25 GiB, and **any residency claim finer than ~0.5 GiB taken
from this table is noise, not signal.** This is the strongest existing argument for hw-probe: the
donor's numbers are one-shot `nvidia-smi`-class readings with no stated sampling window, and F61
already established that a system-wide figure is not a residency verdict at all. The probe's
`--pid` + `max_gap_ms` discipline is what turns this column into evidence.

### F68 — no second model can be co-resident with the champion, and that closes one of W6's two options by arithmetic

The card is 16,311 MiB. The champion occupies **14,820 MiB at ctx 32768** and **15,772 MiB at
65536 with f16 KV** (F66), and the desktop holds a 461–585 MiB floor before anything loads (the
idle baseline, F60). Free space beside a loaded champion is therefore **roughly 0.5–1.5 GiB
depending on window**, and at the daily driver's 61440 it is at the bottom of that range.

The smallest model on this disk is `gemma-4-e2b` at **3,759 MiB measured**. It does not fit. Nor
does anything else — the next rung, `gemma-4-e4b`, is 4,042 MiB.

**Consequence for W6:** §14 item 0 framed the reviewer choice as "same model with no history
(cheapest, most correlated) **or** a second local model (less correlated, costs a swap or
co-residency alongside 13.6 GB)". **Co-residency is not on the menu.** The second-model option is
a *swap* option, and its cost is model-swap latency (W2 item 4, mmap off, NVMe over PCIe 3.0 x8) paid
on every gate. W6 should cost it that way, and the swap number is now a blocking input to W6 rather
than a nice-to-have.

### F69 — `lms load --estimate-only` is weights-only, and is therefore not an instrument for this question

Run today against the champion, three ways:

| Invocation | Estimated GPU memory |
|---|---|
| `-c 65536` | 12.67 GiB |
| `-c 65536 --speculative-draft-mtp` | 12.67 GiB |
| `-c 4096` | 12.67 GiB |

**Identical across a 16× context change and identical with MTP requested**, at `Confidence: LOW`.
The estimator excludes KV, compute buffers, and MTP heads. It reproduces exactly the 12.67 GiB
figure the memory has been carrying, which settles one small thing: **12.67 GiB and the 13.61 GB in
`lms ls` are the same quantity in different units** (13.61 × 10⁹ B = 12.67 GiB), and both are
*weights*. The measured ~14,800 MiB is that plus everything the estimator ignores.

Useful as a cheap, zero-heat ladder of weight footprints (12.52 GiB qwen3.8-27b, 12.67 champion,
14.56 gemma-4-26b-a4b-qat, 14.59 champion at 3.53 bpw) — useless as a residency verdict. Recorded
as a **negative control for the estimator**, in the same spirit as F61.

### F70 — the "4.1 GB less" claim is real, and it is David's own measurement, not a vendor claim

The brief states quantizer lineage as a first-class variable on the strength of "byteshape
ShapeLearn at 3.06 bpw tied unsloth's 4-bit on quality using 4.1 GB less" (§W1, and
`prestudy/questions.md:60-61`). Checked today:

- **byteshape publishes no such comparison.** The MTP model card compares only against byteshape's
  own NTP release, and reports its six-benchmark evaluation (BFCL-V3, LiveCodeBench V6, HumanEval,
  GSM8K, IFEVAL) **as charts with no numeric table**. The blog index has no unsloth or bartowski
  comparison either. ([model card](https://huggingface.co/byteshape/Qwen3.6-35B-A3B-MTP-GGUF))
- **The claim's actual source is Claudette's crowning document**, quoted in
  `prestudy/claudette-dossier.md:650-654`: ShapeLearn "fit 35B-A3B into 13.6 GB at 3.06 bpw and
  **tied the best quality score on the battery** (50/50 + K 8/8), with 4.1 GB less than the unsloth
  4-bit that also scored 50/50", and it explicitly overturned the project's own prior — *"The
  '3-bit damage' precedent does NOT apply to ShapeLearn's learned per-tensor datatypes."*

That is **better** provenance than a vendor benchmark, and it should be cited that way. But it
carries the donor battery's limits with it: it is the older A–K battery at 50 tasks, not Q56, and
not agentic-under-pressure. The published ShapeLearn ladder for this model is
2.25 bpw / 10 GB → 3.06 / 13.6 → 3.53 / 15.7 → 3.97 / 17.6 → 4.19 / 18.6, Apache 2.0.

Cross-referencing that ladder against F66: **3.06 bpw is not a preference on this card, it is the
only rung with room for a 65k window.** The 3.53 rung measured 14,891 MiB at *half* that context.

### F71 — licensing is uniformly permissive, and Gemma 4 quietly moved to Apache 2.0

For a public repo, dual MIT/Apache-2.0 (Q3/Q12, answered 2026-08-07), that may ship or auto-pull
weights:

| Model | Licence | Auto-pull OK? |
|---|---|---|
| Qwen3.6-35B-A3B, Qwen3.8-27B | Apache 2.0 | Yes |
| byteshape GGUF re-quants | Apache 2.0 | Yes |
| **Gemma 4 (all sizes, incl. QAT)** | **Apache 2.0** | Yes — see below |
| Cohere North-Mini-Code-1.0 | Apache 2.0 | Yes |
| Mistral Devstral Small 2 24B | Apache 2.0 | Yes |
| OpenAI gpt-oss-20b | Apache 2.0 | Yes |
| IBM Granite 4.1 | Apache 2.0 | Yes |
| Poolside Laguna XS 2.1 | OpenMDW-1.1 | Yes, with conditions |

Two things worth recording because an aggregator would get them wrong:

- **Gemma 4 ships under Apache 2.0**, confirmed on Google's own licence page, which redirects
  "Gemma 4 license" to plain Apache 2.0 — a change from the Gemma-specific Terms of Use that Gemma
  1–3 carried. ([licence page](https://ai.google.dev/gemma/docs/gemma_4_license)) A separate
  [prohibited use policy](https://ai.google.dev/gemma/prohibited_use_policy) exists and says "You
  may not use nor allow others to use Gemma…", but it states no mechanism by which it attaches and
  imposes no downstream pass-through obligation. **Treat the weights as Apache 2.0 and do not build
  a licence-acceptance flow for Gemma.**
- **North-Mini-Code is Apache 2.0 on the model card itself**, despite a secondary source claiming
  the card adds a non-commercial note. It does not.
  ([model card](https://huggingface.co/CohereLabs/North-Mini-Code-1.0)) Cohere's historical CC-BY-NC
  default does not apply here.

**OpenMDW-1.1** (Linux Foundation, adopted by NVIDIA for Cosmos/Nemotron) is permissive with two
conditions that matter to an auto-puller: redistribution must include a copy of the agreement and
all original copyright/origin information, and there is a patent-litigation termination clause.
Nothing that blocks use; something to encode if 2.0 ever *redistributes* rather than fetches.

**Net: there is no licensing constraint on the tier table.** Every candidate can be auto-pulled by
a public MIT/Apache-2.0 tool. This item is closed.

### F72 — effective-vs-advertised context is not a live risk at this operating point

No independent long-context evaluation of Qwen3.6-35B-A3B (RULER, LongBench, fiction.live) was
found today; the searches return RULER figures for *Qwen3-32B* and generic methodology papers. The
honest statement is that the independent evidence does not exist yet for this specific model.

It matters less than it looks, and the reason is F66. The advertised window is 262,144. The daily
driver runs `CLAUDETTE_NUM_CTX=61440` under a 65,536 load, and **the card cannot hold the KV for
much more than that** — the champion is already at 15,772 MiB of 16,311 at 65k with f16 KV. The gap
between advertised and effective context is a real research topic for a model served on a bigger
card; on this box the *hardware* clips the window at ~23% of native long before attention quality
does. Effective-vs-advertised becomes a live W1 question only for the "24 GB or more" variant.

One dated data point on the same axis, on foreign hardware: an April 2026 benchmark on 2× RTX
4070 Ti (24 GB total, Q4_K_M, Ollama) measured Gemma 4 26B at 96.4 / 86.7 / 65.2 tok/s at
32k / 64k / 128k against Qwen 3.6 35B-A3B at 26.3 / 19.3 / 9.1 — a 3.7× gap widening to 7.2×.
([source](https://modtechgroup.com/the-model-that-barely-slows-down-gemma-4-26b-vs-qwen-3-6-35b-at-long-context/))
⚠ **Do not port that number here.** Q4_K_M of a 35B-A3B does not fit 24 GB with a 128k window, so
those Qwen figures almost certainly include offload — the exact regime §11.0 says this project left
behind. It is directionally consistent with Q56's measured 3.4× wall-clock gap, and that is all it
is good for.

### F73 — MTP is in the crowned config but absent from this box's sticky config

`lms load` exposes `--speculative-draft-mtp` (plus `--speculative-draft-max-tokens`,
`--speculative-draft-min-tokens`, `--speculative-draft-min-continue-probability`). The champion is
an MTP build, and the crowning specifies **"MTP draft-max 2"**
(`prestudy/claudette-dossier.md:439-441`).

But the sticky config on this box today —
`~/.lmstudio/.internal/user-concrete-model-default-config/byteshape/Qwen3.6-35B-A3B-MTP-GGUF/Qwen3.6-35B-A3B-IQ3_S-3.06bpw.gguf.json`
— carries **no speculative key of any kind**. Its nine keys are `offloadRatio 1`,
`numCpuExpertLayersRatio 0`, `kCacheQuantizationType q8_0`, `vCacheQuantizationType q8_0`,
`contextLength 65536`, `tryMmap false`, `cpuThreadPoolSize 2`, `numParallelSessions 1`,
`keepModelInMemory false`. And the canonical load command in
`always-test-on-the-champion-model` passes no speculative flag either.

**Before treating this as a free win, note the donor already measured MTP's contribution and it is
small**: at 24k, NTP 67.34 vs MTP-d2 76.31 tok/s; at 64k, 68.71 vs 69.77
(`prestudy/claudette-dossier.md:646-647`). That is **+13% at 24k and +1.5% at 64k** — nothing like
the 1.5–2.2× the vendor advertises for MTP generally, and the donor's own conclusion was
*"Residency is ~90% of the win; MTP in LMS is a small bonus."*

So this is a **held-constant discrepancy, not a missed opportunity**: the crowned config had MTP on
at draft-max 2, and it is not visible in the config file that every W8 champion cell inherited.
Whether LM Studio defaults it on when the key is absent is unresolved and is not answerable from
the config file. It costs one flag to settle during the first measured load.

## Options compared

Scored against the criteria this box actually imposes: fits resident at 61440 with room for the
gate; agentic and tool-calling behaviour, not one-shot score; licence clean for auto-pull. **Every
quality column is vendor-reported or donor-measured on a corpus §11.0 says cannot see the deciding
axis — none of it is a 2.0 measurement.**

| Tier | Candidate | Resident at 61440? | Licence | Why / why not |
|---|---|---|---|---|
| **Base (builder)** | **qwen3.6-35b-a3b-mtp@iq3_s** | Yes, 15.4 GiB of 16.3 — the whole card | Apache 2.0 | Incumbent. 3 B active, MTP, `qwen3_coder` parser, 262k native. Ruled in §6, not displaced (F65) |
| Base challenger | qwen3.8-27b | Yes, ~12.5 GiB weights; resident at 32k per prior session | Apache 2.0 | Two days old; +12.2 on SWE-bench Pro; **dense**, so ~1.9× slower measured. Test planned, not run |
| Base — blocked | Laguna XS 2.1 | **No** — official GGUFs stop at Q4_K_M (~20 GB) | OpenMDW-1.1 | Architecturally the champion's twin (33B/3B, 256 experts). Revisit if a ≤3.5 bpw quant appears |
| Triage / recon | gemma-4-e4b | 4,042–4,441 MiB measured | Apache 2.0 | Cheapest thing on disk that is not a toy; ~27% of the card |
| Triage / recon | qwen3.5-4b | 8,878–8,934 MiB measured | Apache 2.0 | Same family as the base — shared tokenizer and prompt idiom is worth more than 4 GB here |
| Adversarial gate | **same model, no history** | Free — it is already loaded | — | **The only co-resident option (F68).** Cheapest, most correlated with what it checks |
| Adversarial gate | gemma-4-26b-a4b-qat | Not alongside the champion; 15,530–15,622 MiB *alone* | Apache 2.0 | Least-correlated local reviewer, and the Q56 crown. **Costs a full model swap per gate** |
| Adversarial gate | gpt-oss-20b | Not alongside; 12,395–12,527 MiB alone | Apache 2.0 | Cheapest swap-in reviewer; different lineage from both Qwen and Gemma |
| C10 (manual) | Claude Opus 5 | n/a — API | commercial | $5 / $25 per MTok, 1M context. Default frontier call |
| C10 (manual) | Claude Sonnet 5 | n/a — API | commercial | $3 / $15 ($2 / $10 intro through 2026-08-31), 1M context. The volume option if C10 ever stops being rare |
| C10 (manual) | Claude Haiku 4.5 | n/a — API | commercial | $1 / $5, 200K context. Only if a cheap remote tier earns its place |

**"If you only have 8 GB":** the ladder is real and it is short. `gemma-4-12b-qat` at 7,968–8,095
MiB measured is the largest thing that fits, and it fits *exactly* — with no gate, no second model,
and a window well under 32k. Below it, `gemma-4-e4b` (4.0–4.4 GiB) and `gemma-4-e2b` (3.8 GiB)
leave room to work. The honest framing for that user is that they get a builder or a gate, not
both, and the operator-control story has to survive a single-model fleet.

**"If you have 24 GB or more":** the champion's whole reason for being at 3.06 bpw disappears —
`Qwen3.6-35B-A3B` at 3.97 bpw (17.6 GB) or 4.19 (18.6) becomes resident, and F68 inverts:
a 4 GB reviewer co-resident with a 4-bit builder is comfortable. This is also the tier where F72
stops being moot and effective-vs-advertised context becomes a question worth researching. **Both
variants are written from arithmetic against this box's measured ladder, not from measurement on
other hardware** — they carry the degradation-path requirement of §5, and nothing more.

## Recommendation

1. **Keep Qwen 3.6 35B-A3B at byteshape IQ3_S 3.06 bpw as the base agent**, and record the date:
   re-validated 2026-08-16, nothing displaced it. Quantizer choice is *not* free preference — F66
   shows 3.06 bpw is the only rung on its ladder that leaves room for a 65k window on this card.
2. **Run the Qwen3.8-27B comparison before W1 closes**, and run it on agentic multi-file work under
   context pressure, not on a score column. It is the one live threat to a settled decision, and it
   is two days old, downloaded, and 12 vendor-points ahead on the one comparable benchmark. If it
   wins, that is new evidence "strong enough to be worth the disruption" (§6) and should be said
   loudly.
3. **Tell W6 that a co-resident second-opinion reviewer is impossible on this box** (F68). The
   choice is same-model-no-history or a per-gate model swap, and W6 cannot cost the second option
   until W2 item 4 measures swap latency. That makes swap cost a blocking input, not a curiosity.
4. **Take triage from the same family as the base** — `qwen3.5-4b` over `gemma-4-e4b` unless the
   4 GB matters — so the fleet shares one prompt idiom and one tool-call dialect. The brief's own
   warning about V1's 7B failing at tool calling is about exactly this.
5. **Keep C10 as `claude-opus-5`**, manual and rare per §14 item 0. No routing tier, no budget
   allocation, no escalation ladder through it.
6. **Close the licensing item** (F71). Nothing here constrains a public dual-licensed tool, and no
   licence-acceptance flow is needed — including for Gemma, which is now plain Apache 2.0.

## Rejected alternatives and why

- **GLM-5.2, Kimi K3, DeepSeek V4 Flash as local models** — 753B, 2.8T, and ~284B. Not candidates
  on a 16 GB card at any quantization. Worth knowing about only as C10-class remote calls, which
  §14 item 0 already made manual and rare.
- **Poolside Laguna XS 2.1 today** — right architecture, right size class, wrong quants. Q4_K_M is
  the smallest official GGUF. Revisit if byteshape or another lineage publishes ≤3.5 bpw.
- **Promoting gemma-4-26b-a4b-qat on its Q56 crown** — explicitly barred by §11.0, and F66 adds a
  hardware reason: it lands at 15,530–15,622 MiB at ctx 32768, so it is not a co-residency
  candidate and probably not a 61440 candidate either. It stays a swap-in reviewer.
- **Using `lms --estimate-only` as the residency instrument** — F69. Weights-only, `Confidence:
  LOW`, blind to KV and to the MTP heads. Kept as a cheap ladder, rejected as evidence.
- **Deriving KV cost from the donor's VRAM deltas** — F67. The instrument's repeat spread (up to
  458 MiB) is wider than the deltas, and the GGUF-side arithmetic already refused to close.
- **Re-opening NVFP4** — no new evidence, and §W1 forbids it absent some. Not revisited.

## Effect on fun

The residency cliff is the fun problem hiding in this workstream. A fleet where the builder eats
91% of the card means the RTS console can never show a *fleet* on one machine — one unit is
resident and every other "unit" is a swap. That is either a fiction the console tells badly, or an
honest mechanic: **units cost VRAM, the card is the map, and swapping in the reviewer is a visible,
costed action the operator watches happen.** The second reading is better, and it is only available
because the constraint got measured instead of designed around. F68 turns a disappointing hardware
fact into the single-player game's central resource.

The tier table also protects the thing §7 cares about: triage on a 4 B model in the same family
keeps the *feel* fast — recon units that answer instantly — while the slow, expensive builder is
the one you deploy deliberately. That asymmetry is a game mechanic, not a compromise.

## Open questions

**The measurement half of §14 item 2, unchanged and untouched.** Every item needs the champion
loaded, and per `always-test-on-the-champion-model` and two killed W8 campaigns, it needs David's
say-so on heat first:

1. **Peak VRAM through a model load**, `-c 65536` vs `-c 32768`, `hw-probe run --pid <LM Studio
   server>`. Settles F66's ladder with a stated blind window instead of a one-shot reading, and
   retires F67's noise floor.
2. **Qwen3.8-27B vs the champion on agentic multi-file work under context pressure** — the F65
   decision. Also the moment to check whether its 500 MiB of headroom at 65k survives a real
   prefill (`qwen38-27b-daily-driver-question`).
3. **KV growth under residency**, re-measured with the probe. Session 9 saw +2 MiB across
   18,915→60,915 prompt tokens; F66's f16 rows suggest ~692 MiB per 32k. Both cannot be right.
4. **Whether MTP is on** (F73) — one flag on the first measured load, plus a tok/s pair. Cheap, and
   it retro-validates or invalidates a held constant for every W8 champion cell.
5. **Model-swap cost**, mmap off, NVMe over PCIe 3.0 x8 — promoted from W2 item 4 to a **blocking
   input for W6** by F68.
6. **The concurrency ceiling**, N parallel builders, reported as a hard limit. `Non Local Usage` is
   the instability detector (F60).
7. **Prefill/decode throughput and quality-per-quant** for the tier table's empty columns — the
   3.06 vs 3.53 vs 3.97 bpw rungs are all on disk and all measurable in one session.

**Desk-side, still open:** no independent long-context evaluation of Qwen3.6-35B-A3B exists yet
(F72) — worth one more sweep before W1 closes, and required for the "24 GB or more" variant.

## Confidence: medium

**High** on the parts that are arithmetic or primary-source: the licensing table (F71, every row
checked against the vendor's own page), the co-residency impossibility (F68 — it follows from two
measured numbers and a subtraction), the estimator's weights-only behaviour (F69 — three runs,
identical output), and the provenance correction on the 4.1 GB claim (F70).

**Medium** on the base re-validation (F65): the survey is one day's search, and the deciding
comparison is vendor-reported benchmarks on a model 48 hours old. **Low** on anything that would
rank models by quality — Q56's score column cannot see the axis, and the 2.0 harness that can does
not have these models in it yet.

**What would raise it:** running item 2 above. A single agentic-under-pressure comparison between
the champion and Qwen3.8-27B, on the W8 corpus that was built precisely to see that axis, would
convert the weakest claim in this file into the strongest. After that, item 1 — because every
residency number here is imported from an instrument with a 460 MiB noise floor, and the
replacement is already built, tested, and committed.
