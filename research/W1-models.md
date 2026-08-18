# W1 — Model tiering around the base agent

**Retrieval date for every external claim in this file: 2026-08-16.** Desk half written first
(F65–F73, `d09011d`); **the measurement half ran the same day and is F74–F80 below.**

⚠ **The two halves have different provenance and must not be quoted as one.** F65–F73 are desk
work — vendor model cards, licences, and VRAM figures either *imported* from the donor's Q56 run
metadata (`prestudy/data/q56-runmeta.tsv`, measured 2026-07) or produced by `lms load
--estimate-only`, which F69 shows is weights-only. **F74–F80 are new measurements on this box**,
champion resident, via `harness/crates/hw-probe`.

🚨 **The measured half overturned one thing in the desk half and one thing in the instrument, and
left §11.0's central premise standing.** Read F74 before quoting any residency number from
anywhere in this repo.

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
- **Measurement half (added 2026-08-16)**: champion loaded via the canonical command, probed with
  `hw-probe` (`baseline` / `watch --pid` / `run --pid`) and driven over
  `/v1/chat/completions` — the same dialect Claudette uses, `stream: true` with
  `stream_options.include_usage`, so token counts come from the server rather than an estimate.
  Twelve loads across the session; the `llama-server` pid re-resolved after each (F75).
- **Every residency claim here has a named negative control**, after F74 showed that a plausible
  number from working code survived a week of review without one.
- **Still not done**: quality-per-quant, and any agentic-under-context-pressure evaluation. Those
  need the W8 corpus rather than a probe, and they are §Open questions items 1–2.

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

---

## Findings — the measured half (2026-08-16, champion resident)

### 🚨 F74 — "host-shared GPU memory" is not eviction, the probe's residency alarm was wrong, and §11.0 survives

The first `--pid` reading on a real model looked like the biggest finding of the project: the
champion at `-c 65536` reported **14,284 MiB on-card + 416 MiB host-shared**, and `hw-probe`
printed `🚨 NOT fully resident` — apparently falsifying the string Claudette ships to every user,
*"fully VRAM-resident in 13.6 GB, zero RAM spill"* (`hw.rs:103-109`, quoted in §11.0). It
reproduced byte-identically across two windows.

**It was the instrument, not the model.** The control:

| Loaded | on-card | host-shared | free VRAM at the time |
|---|---|---|---|
| champion `-c 4096` | 13,320 MiB | 296 MiB | ~2.5 GiB |
| champion `-c 32768` | 13,756 MiB | 352 MiB | ~2.1 GiB |
| champion `-c 65536` | 14,284 MiB | 416 MiB | ~1.5 GiB |
| **`gemma-4-e2b` `-c 32768`** | **2,958 MiB** | **2,290 MiB** | **~12.9 GiB** |

A 4.1 GiB model with **13 GiB of the card free** reports 5.5× more "spill" than the champion at
65k. Nothing is evicting it; there is no pressure to evict it. `Non Local Usage` counts host memory
a process commits to the GPU address space, which llama.cpp allocates by design — both configs run
`--no-mmap`, so this is not a mapped-file artefact.

**What actually settles residency is throughput.** 416 MiB fetched per token across PCIe 3.0 x8
(~7.9 GB/s) caps decode near 19 tok/s; the champion measures **54–76 tok/s** (F80). It is resident.
**§11.0's premise stands and no document needs correcting** — but `hw-probe` did: the alarm is
deleted, the fields are renamed `focus_on_card_b` / `focus_host_shared_b`, and the control is
pinned by `host_shared_memory_never_becomes_an_eviction_verdict`.

**This is F61 repeating one level deeper.** F61 fixed a bad system-wide verdict by demanding
`--pid` — a *narrower* verdict — instead of asking whether the counter supports a verdict at all.
Both times a cheap negative control caught it, and both times the control ran late. **F67's 458 MiB
"noise floor" is not retired by this session**, because the quantity it was measuring was never the
one that mattered.

### F75 — LM Studio spawns a fresh `llama-server` per load, so the weight-holder never predates the probe

`hw-probe run --per-process` around a load showed **not one pre-existing pid rising** — the
README's guidance (*"the pid holding the weights is LM Studio's server process, which already
exists before `lms load` runs"*) was false. LM Studio holds no weights itself; it spawns
`llama-server.exe`, which appears *during* the load and therefore can never have a `typeperf`
column for it. The pid changes every time (23412 → 21304 → 20760 → … over session 19).

Consequences: **peak VRAM through a load is adapter-level only**, per-process attribution must come
from a second `watch --pid` after the load, and the pid must be re-resolved after every load. Full
correction in the probe README (F75); the serving detail it exposed is W2 F86.

### F77 — the KV cache is allocated in full at load time, which reconciles "+2 MiB" with "692 MiB"

Session 9 saw VRAM move **+2 MiB** across an 18,915 → 60,915-token prompt; F66's f16 rows implied
**~692 MiB per 32k**. `always-test-on-the-champion-model` records both and says they cannot both be
right. **They can.** Measured across a real 54,930-token prefill:

| | peak VRAM |
|---|---|
| champion at `-c 65536`, idle | 14,750 MiB |
| same, during a 54,930-token prefill | **14,773 MiB** |

**+23 MiB to fill 55k tokens of context.** Meanwhile the *load-time* figures scale strongly with
the requested window: 13,785 → 14,221 → 14,750 MiB at `-c` 4096 → 32768 → 65536.

So llama.cpp reserves the whole KV for the configured window **when the model loads**, and filling
it costs nothing. F66's 692 MiB is a difference between two *loads*; Session 9's +2 MiB is growth
*within* one. Both observations were correct and neither was a measurement of the other.

▶ **This is a design lever, not trivia:** `-c` is not a ceiling you might use, it is memory you
have already spent. Loading at 65,536 to run a 20k session costs ~965 MiB of card for nothing.

### F78 — MTP is genuinely engaged by the flag, and buys nothing measurable here

F73 could not tell whether MTP was on. It is now settled from both ends. Passing
`--speculative-draft-mtp --speculative-draft-max-tokens 2` puts **`--spec-type draft-mtp
--spec-draft-n-max 2 --spec-draft-n-min 0 --spec-draft-p-min 0.75`** on the real `llama-server`
command line (W2 F86) — so the flag is not silently ignored. And at a 7,440-token prompt, twice
each:

| | decode tok/s | TTFT (cold / warm) |
|---|---|---|
| without the flag | 75.84 / 76.69 | 5.920 s / 2.237 s |
| **with MTP draft-max 2** | **75.65 / 73.26** | 5.878 s / 2.255 s |

**No difference — the MTP arm is if anything marginally slower**, and TTFT matches to ~40 ms. This
is consistent with the donor's own measurement (+13% at 24k, **+1.5% at 64k**) and with its
conclusion that *"residency is ~90% of the win; MTP in LMS is a small bonus"*.

**Consequence for W8:** the held-constant discrepancy is closed and it is harmless. Every champion
cell ran without the flag, the flag changes nothing at this context, so **no W8 number needs
re-running or re-labelling.** Do not add it to the canonical load command; it costs a config
divergence and buys noise.

### F79 — a per-gate model swap costs 23.77 s, and W6 can now be costed

F68 made W6's second-opinion reviewer a swap rather than a co-resident model, which made this a
blocking input. Measured, n=3 each direction, unload and load timed separately:

| Direction | unload | load | total |
|---|---|---|---|
| champion → `gpt-oss-20b` (reviewer, `-c 32768`) | 0.57–0.83 s | 10.53–10.86 s | **11.42 s** median |
| `gpt-oss-20b` → champion (`-c 65536`) | ~0.57 s | 11.76–11.80 s | **12.35 s** median |
| **round trip — one gate firing** | | | **23.77 s** median |

Spreads are tight (the champion's load varies by <50 ms across three runs), so this is a solid
number. Unload is nearly free; **load dominates and is not bandwidth-bound** — 12.67 GiB in 11.78 s
is ~1.10 GiB/s, far under PCIe 3.0 x8, so it is dequantisation and upload, not the NVMe read.
A warm OS file cache is worth only ~0.5 s (first load of the session 12.29 s vs 11.80 s warm).

**For W6:** every gate that uses a second local model costs **~24 s of wall clock before the
reviewer has read a single token**. Against same-model-no-history at zero swap cost, that is the
price of decorrelation, and it should be quoted per gate, per task, in whatever budget W6 writes.
W2's open question 3 (slot save/restore) is the one thing that might reduce it.

### F80 — the champion's throughput ladder, and the number that proves residency

Measured on the loaded champion, `-c 65536`, single stream:

| prompt tokens | TTFT | prefill tok/s | decode tok/s |
|---|---|---|---|
| 2,361 | 2.215 s | 1,066 | 70.12 |
| 7,440 | 5.920 s | 1,257 | 75.84 |
| 18,470 | 11.549 s | 1,599 | — |
| 18,485 | 11.282 s | 1,639 | 65.22 |
| **54,930** | **33.905 s** | **1,620** | **54.00** |

**Prefill throughput rises with prompt size and plateaus near 1,600 tok/s** (batching amortises
fixed cost). **Decode degrades gracefully with context** — 70 → 76 → 65 → 54 tok/s — losing ~29%
between 2.4k and 55k. The donor's NTP figures (67.34 at 24k, 68.71 at 64k) sit inside this range.

Two things follow. First, **TTFT at the daily driver's context is ~34 s**, which is the number every
latency claim in this project should be anchored to. Second, this table is F74's proof: sustained
54–76 tok/s decode is not achievable by a model streaming its weights over PCIe.

⚠ **Temperature: peak 73 °C under a 55k prefill, 69 °C under 6-way concurrency, no throttle at any
point.** Thermals were never the constraint in this session.

---

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

## K-series cross-model comparison — Qwen3.8-27B vs the champion (2026-08-18)

Item 1 below, run. `corpus/suites/k`, `--variant control`, n=3 per arm, subject
`claudette-af3f804` (force-rebuilt), `--num-ctx 40000` under `lms load … -c 40960 --parallel 1`
for **both** arms. Held constants read off each fresh `llama-server` command line (F75) and
matched: `cache-type-k/v q8_0`, `flash-attn on`, `kv-unified`, `batch 2048/ubatch 512`,
`parallel 1`, `spec-type draft-mtp`, `n-gpu-layers 999999`, `n-cpu-moe 0` — fully GPU-resident on
both. **Two constants did NOT match and both are recorded rather than hidden:** the quantizations
differ (champion **IQ3_S 3.06 bpw**, challenger **Q3_K_XL**), and `threads` was 2 vs 4 by LM
Studio's own choice. So this compares *these two local builds*, not the two architectures.

### F87 — on cells that complete, the two models are level on verdicts and differ in how they fix

Champion **8 pass / 1 fail / 0 timeout**; 27B **8 pass / 0 fail / 1 no-evidence timeout**. The
score column does not separate them, which is exactly why §11.0 bars deciding on one. Every cell
was workdir-diffed against `refsol` and `sham`; the separation is in the diffs:

| behaviour | champion (9 cells) | 27B (8 completed) |
|---|---|---|
| took the sham | 0 | 0 |
| destroyed the `other` catch-all (renamed it rather than adding a bucket) | 1 | 0 |
| fixed at the call site, leaving the defective root function and its wrong docstring | 1 | 0 |
| **added tests covering the gap the fixture documents as untested** | **0** | **2** |
| redundant guard at the crash site on `trace_dropped_samples` | 3 of 3 | 3 of 3 |

The champion's one FAIL is **not** the sham: it changed all four correct sites, then *replaced*
`BUCKETS`' `other` entry with `cancelled`, so an unknown future status would be silently counted as
cancelled. Its transcript states the choice deliberately ("Replaced `other` with `cancelled`
everywhere") and then claims `cancelled` is "visible in its own bucket", which is what it did not
do. A confident, articulate, wrong answer — the failure mode the K-series was built to expose.

The redundant-guard row is the one to *not* read as a differentiator: **both** models bolt
`if not window.values: continue` onto the sham's site in `stats.py` on top of the correct upstream
`ingest.py` fix, in every single run. It is dead code once the real fix lands, and in champion r1
it also deleted the comment documenting the `strict_empty_windows` invariant. Universal behaviour,
not a model property.

### F88 — the task-level cost of the 27B is far worse than its token-rate ratio, 1.3× to 9.5×

The matched-throughput figures (2.25× prefill, 2.54× decode) understate the agentic cost badly,
because the 27B also runs longer and does more per cell. Median wall clock per task:

| task | champion | 27B | ratio |
|---|---|---|---|
| `finish_the_cancelled_status` | 100.0 s | 947.2 s | **9.5×** |
| `round_at_the_line_not_the_total` | 181.9 s | 228.5 s | 1.26× |
| `trace_dropped_samples` | 189.6 s | ~1349 s (n=2) | ~7.1× |
| whole campaign, 9 cells | **1662 s** | **8681 s** | **5.2×** |

⚠ Champion wall clock is itself wildly variable — `trace_dropped_samples` ran 70 s, 190 s and 629 s
on identical inputs. Quote the ratio as a range, never a point estimate, and prefer F80's matched
ladder for anything that needs precision.

### F89 — `timeout_s = 900` was miscalibrated, and a timeout records NO metrics at all

At the suite's original ceiling the 27B scored **5 pass / 4 timeout**. Four of those were an
artefact: raised to 2400, **four cells that exceed 900 s complete and pass** (907.2, 947.2, 1086.4,
1957.8 s). One missed the old ceiling by **7.6 seconds**. The champion is unaffected — its slowest
cell was 629 s, so the ceiling never bound for it, which is why Arm A was not re-run.

The cost of getting this wrong is asymmetric and silent: a timed-out cell emits **no verdict, no
`iterations`, and no `peak_prompt_tokens`**, so the ceiling converted the slower model's
thoroughness into missing data rather than a result. `timeout_s` is now 2400 in all three
`task.toml` files with this rationale inline. Both files already carried the note *"A subject that
reads the codebase properly must not lose to the clock for doing so"* — the calibration contradicted
the suite's own stated intent.

### 🚨 F90 — the two models were never in the same context regime, and only the 27B reaches the one the suite exists to test

`peak_prompt_tokens` floors, against the 40,000 pin:

| arm | range | occupancy | auto-compaction events |
|---|---|---|---|
| champion | 13,053 – 21,245 | 33–53% | **0 in 9 cells** |
| 27B | 15,207 – **30,567** | 38–**76%** | 3 across 6 runs |

Claudette's auto-compaction (`hard tier crossed at 20000 tokens`) fires for the 27B and **never**
for the champion on this corpus. So the K-series' known "fixtures are too small" weakness is only
half the story: **the champion does not reach the pressure regime because it is terser**, not only
because the fixtures are small. Growing the fixtures will not by itself put the champion under
pressure. This is also the first time anything in W1 has exercised the compaction path under
measurement, and it means the quality comparison above is across two different regimes — a
confound to close, not a result to celebrate.

### F91 — a cell can time out having done substantial work and leave no evidence

`trace_dropped_samples` timed out in the first repeat of *both* Arm B configurations with a
1,887-byte transcript: banner at 99 ms, prompt at 358 ms, then nothing for 40 minutes, and an
untouched workdir. **This is not a hang** — the LM Studio server log records **20 chat completions**
in that window (one per ~2 min, message counts climbing to 31), so the subject was working
throughout. `driver.rs:388` writes only **newline-terminated** lines to the transcript, deliberately,
so the newline-less gate prompt stays observable; nothing newline-terminated arrived. Net effect: a
`timeout` verdict with zero evidence of 40 minutes of work. Reproduced twice on the largest fixture;
never once in the champion's 9 cells. **Needs its own investigation before the K-series is used
again** — any cell it hits is unfalsifiable.

### F92 — what the 27B spends its extra time on

Partly the work itself: in 2 of 3 `finish_the_cancelled_status` cells it wrote a
`TestCancelledSemantics` class covering precisely the consumer gap the fixture README documents as
untested, including an assertion that `other == 0` — the exact invariant the champion's r1 broke.
It also fixed `round_at_the_line_not_the_total` at the root (`pricing.total_of`) in all three runs,
with a docstring citing `docs/money.md` and explaining why rounding at the total is not equivalent;
the champion patched the *call site* in one run and left the defective function behind. That is a
real quality difference, and it is bought at 5.2× the wall clock.

## Open questions

**Six of the seven measurement items are now closed.** What the 2026-08-16 session settled: peak
VRAM through a load and at rest (F74, with the method corrected by F75), KV growth (F77), MTP
(F78), swap cost (F79), prefill/decode throughput (F80), and the concurrency ceiling
(`research/W2-serving.md` F83). Per `gpu-is-available-by-default` these no longer wait on anything.

**What is genuinely left:**

1. ✅ **Qwen3.8-27B vs the champion on agentic multi-file work — RUN 2026-08-18, F87–F92.** No
   longer vendor-benchmark-only: 18 diffed cells, n=3 per arm. **The verdict columns tie (8/9 each)
   and the diffs favour the 27B on how it fixes, at 5.2× the wall clock.** What it did *not* settle,
   and these are now the live questions:
   - **"Under context pressure" was not actually held** (F90). Only the 27B reached the regime;
     the champion never crossed compaction on this corpus. A comparison across two regimes cannot
     close the base choice on its own.
   - **F91 must be fixed first.** A cell that times out with no transcript is unfalsifiable, and it
     hit the largest fixture twice.
   - The 65k-headroom-under-real-prefill check is still unrun; at `-c 40960` the 27B sits at
     **15,398 / 16,311 MiB (94.4%, 913 MiB spare)**, fully resident, no CPU offload.
2. **Quality-per-quant across the 3.06 / 3.53 / 3.97 bpw rungs** — all three are on disk, and F80's
   method now makes the throughput half a single session's work. The *quality* half needs the same
   harness as item 1, so run them together.
3. **Tool-calling and structured-output reliability per candidate**, which the brief asks for and
   nothing here measured. W2's F82 changes the shape of this question: with schema-constrained
   decoding available and enforced, "reliability" splits into *can it be forced* (yes, for anything
   expressible as a schema) and *does it choose the right tool* (unmeasured, and the part that
   matters).
4. **Desk-side:** still no independent long-context evaluation of Qwen3.6-35B-A3B (F72). Required
   for the "24 GB or more" variant, moot for this box.

**Closed and explicitly not worth re-running:** F67's 458 MiB noise floor is superseded rather than
retired — F74 shows the counter it came from was never measuring residency. Do not spend a session
reconciling the donor's `vram_mib` column with the probe's; they are different quantities.

## Confidence: medium overall — high on the hardware, unchanged on the choice

**High**, and now measured rather than argued: KV pre-allocation (F77, +23 MiB across a 55k
prefill), MTP's irrelevance here (F78, both arms twice, plus the server command line), swap cost
(F79, n=3 per direction with <50 ms spread), and the throughput ladder (F80, five prompt sizes).
Also high on the desk items that are arithmetic or primary-source: licensing (F71), co-residency
impossibility (F68), the estimator's weights-only behaviour (F69), and the 4.1 GB provenance
correction (F70).

**Medium, and now measured rather than argued, on the base re-validation (F65).** The 2026-08-18
K-series campaign (F87–F92) replaced the vendor benchmark with 18 diffed cells. It **does not**
promote the base choice to high, for two stated reasons rather than caution: the arms sat in
different context regimes (F90), and one task is unfalsifiable until F91 is fixed. What it does
establish is that **the 12.2-point SWE-bench Pro gap did not show up as a verdict gap here** — the
arms tie at 8/9 — while the 27B costs 5.2× the wall clock. On this evidence the champion stays the
champion, and that is now a measured position instead of an inherited one.

**Low→medium** on ranking models by quality. The K-series can now *see* a quality difference and
did (F87's diff table, F92), but it reads it from three tasks in one regime, and n=3 was enough to
show the champion's own verdicts are unstable (`finish_the_cancelled_status` failed once and passed
twice on identical inputs). Not a ranking instrument yet.

**What would raise it, in order:** (1) fix F91 — no conclusion from this suite is safe while a cell
can time out silently having worked 40 minutes; (2) close F90 by getting both arms into the same
regime, which means growing the fixtures rather than lowering the pin, since the champion's terseness
and not the fixture size is what keeps it at 33–53%; (3) then re-run for the quality-per-quant ladder
(item 2), which shares the harness.

⚠ **One methodological warning this session earned.** F74 deleted a residency verdict that had
survived a clean build, clean clippy, 44 green tests and a written README for a week; it died to a
four-second negative control. **Before quoting any number in this file, ask what its control was.**
Where a finding has one, it is named.
