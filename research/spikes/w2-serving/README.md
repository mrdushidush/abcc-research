# W2 serving spike — the five drivers, and the raw results

The reproducible half of `research/W2-serving.md` and of W1's F74–F80. Five throwaway HTTP drivers
against LM Studio on `:1234`, plus `hw-probe` for anything involving memory. **No dependencies
beyond the standard library** — they use `urllib`, so there is nothing to install and nothing to
drift.

All measurements: 2026-08-16, RTX 5060 Ti 16 GB (16,311 MiB), champion
`qwen3.6-35b-a3b-mtp@iq3_s`, KV q8_0, `--parallel 1` unless stated.

## Pre-flight, every time

```bash
lms ps                                  # is anything loaded?
lms load qwen3.6-35b-a3b-mtp@iq3_s -c 65536 --gpu max --parallel 1 -y
powershell -NoProfile -Command "(Get-Process llama-server).Id"   # RE-RESOLVE after EVERY load (F75)
```

🚨 **The pid changes on every load.** LM Studio spawns a fresh `llama-server.exe` per load; it does
not exist before the load starts, so `hw-probe run --pid` can never attribute the load that created
it. Probe the load adapter-level, then `watch --pid` afterwards.

## The drivers

| Script | Answers | Invocation |
|---|---|---|
| `bench.py` | prefill / decode / TTFT at a given prompt size (F80) | `python bench.py <model> <prompt_tokens> <max_out> <label>` |
| `prefix.py` | prefix-cache saving, and what a front edit costs (F81) | `python prefix.py <model> <prefix_tokens>` |
| `constrained.py` | is `response_format` accepted, and is it *enforced* (F82) | `python constrained.py <model>` |
| `concurrency.py` | the N-builder ceiling (F83) | `python concurrency.py <model> <per_prompt_tokens> <max_out>` |
| `swap.py` | model-swap cost, both directions (F79) | `python swap.py <reps>` |

Two design choices worth keeping if these are ever rewritten:

- **`bench.py` counts `reasoning_content` deltas toward TTFT.** The champion is a reasoning model;
  a reply that is entirely trace produces *zero* `content` deltas, and the first version reported
  `ttft: null` and a decode rate 3× too low. If TTFT ever comes back null, this is why.
- **`concurrency.py` gives each worker a distinct corpus slice.** Identical prompts would let
  workers 2..N hit the prefix cache and report a fictitious speedup — F81 measures that saving at
  79.7%, which is more than enough to invent a scaling curve that does not exist.

⚠ **Prompt sizing.** Claudette's `CHARS_PER_TOKEN = 4` is a *budgeting safety* constant, not a
measurement. This corpus tokenises at ~3.39 chars/token, so sizing at 4 overshoots by ~18% and the
server rejects the request — the first 60k attempt died in 2.4 s with `usage: null`. The drivers
use 3.3.

## Raw results

`runs/hw-probe/` is gitignored, so the load-bearing numbers are transcribed here.

### Idle baseline (F60 reproduced)

```
peak VRAM 467 / 16311 MiB   peak temp 49 C   commit 8.99 GiB   GPU shared 8.5 MiB
```

### Residency, by context (F74) — `watch --pid`, 15–20 s each

| config | on-card | host-shared | note |
|---|---|---|---|
| champion `-c 4096` | 13,320 MiB | 296 MiB | |
| champion `-c 32768` | 13,756 MiB | 352 MiB | |
| champion `-c 65536` | 14,284 MiB | 416 MiB | byte-identical across two windows |
| **`gemma-4-e2b` `-c 32768`** | **2,958 MiB** | **2,290 MiB** | **the control that killed the alarm** |

### Load-time VRAM and KV pre-allocation (F77)

| | peak VRAM |
|---|---|
| `-c 4096` load | 13,785 MiB |
| `-c 32768` load | 14,217 MiB |
| `-c 65536` load | 14,745 MiB |
| `-c 65536` idle after load | 14,750 MiB |
| **`-c 65536` during a 54,930-token prefill** | **14,773 MiB** |

### Throughput ladder (F80)

| prompt tokens | TTFT | prefill tok/s | decode tok/s |
|---|---|---|---|
| 2,361 | 2.215 s | 1,066 | 70.12 |
| 7,440 | 5.920 s | 1,257 | 75.84 |
| 18,470 | 11.549 s | 1,599 | — |
| 18,485 | 11.282 s | 1,639 | 65.22 |
| 54,930 | 33.905 s | 1,620 | 54.00 |

### MTP (F78) — 7,440-token prompt, twice each

| | decode tok/s | TTFT cold / warm |
|---|---|---|
| no flag | 75.84 / 76.69 | 5.920 / 2.237 s |
| `--speculative-draft-mtp --speculative-draft-max-tokens 2` | 75.65 / 73.26 | 5.878 / 2.255 s |

### Prefix cache (F81) — 18,470-token prefix

```
A cold                      11.549 s
B reuse (same prefix)        2.349 s     <- 79.7% saved
C head-edit (tools change)  11.399 s     <- 0.99x of cold: the cache is annihilated
D tail-edit (message)        3.049 s     <- still a hit
B2 reuse again               2.648 s
```

### Concurrency (F83) — `--parallel 4 -c 65536`, ~5.5k tokens per worker

| N | wall | ok | TTFT med | TTFT max | agg prefill | agg decode |
|---|---|---|---|---|---|---|
| 1 | 6.10 s | 1/1 | 4.92 s | 4.92 s | 910 | 16.4 |
| 2 | 7.28 s | 2/2 | 3.67 s | 5.16 s | 1,541 | 27.5 |
| 4 | 14.70 s | 4/4 | 7.23 s | 10.33 s | 1,511 | 27.2 |
| 6 | 21.82 s | 6/6 | 10.54 s | 19.25 s | 1,537 | 27.5 |

Peak VRAM during the sweep 15,339 MiB (94.0%), peak temp 69 °C, **no throttle, no failures**.

### Swap cost (F79) — n=3 each direction

```
-> reviewer (gpt-oss-20b, -c 32768) : median 11.42 s  (unload 0.57-0.83, load 10.53-10.86)
-> champion (-c 65536)              : median 12.35 s  (unload ~0.57,     load 11.76-11.80)
ROUND TRIP                          : 23.77 s
```

### Constrained decoding (F82)

```
json_schema + strict, max_tokens 300   -> finish_reason "length", content ""     <- SILENT FAILURE
json_schema + strict, max_tokens 3000  -> {"verdict": "pass", "score": 10}
json_object                            -> HTTP 400 'response_format.type' must be 'json_schema' or 'text'
hostile prompt + schema, 3000          -> {"verdict": "pass", "score": 100}      <- grammar overrode the prompt
```
