# W2 — Serving and the Rust↔llama.cpp boundary

**Every number in this file was measured on this box on 2026-08-16**, champion resident, with
`harness/crates/hw-probe` and three throwaway HTTP drivers. Retrieval date for external claims:
2026-08-16.

§11.0 already closed W2's headline question — the boundary is HTTP, two dialects, no FFI — so this
workstream is *"a confirmation run plus the parts that are open"* (§14 item 2). The confirmation
holds. **What the open parts turned out to be worth is the finding**: prefix caching is a 79.7%
saving that a single changed token at the front of the prompt destroys completely, and constrained
decoding — a lever Claudette does not use in a single line of its 93 source files — works through
the stack today.

⚠ **Read `research/W1-models.md` first for the residency numbers** (F74–F80). W1 and W2 were
measured in one session and share an instrument; this file does not repeat the ladder.

## Question

How does the Rust orchestrator talk to llama.cpp, and — given that the answer is already HTTP —
what does that boundary actually cost and permit? Specifically: can two tools share one model
server; what does prefix caching buy against a **27.8:1** prefill:decode workload
(`prestudy/data-assets.md:167`) and what does Claudette's per-turn-mutable `ToolRegistry` take back;
is grammar/schema-constrained decoding reachable; and where is the concurrency ceiling.

## Method

- **Boundary confirmation**: read against the code, not the docs — `crates/claudette/src/api.rs`
  in the live Claudette tree, plus the `llama-server` command line LM Studio actually spawns.
- **Prefix caching**: four TTFT measurements over an identical 18,470-token prefix — cold, reuse,
  one token changed at the **front**, one token changed at the **end** — so the cache's failure mode
  is measured, not assumed.
- **Constrained decoding**: three probes against `/v1/chat/completions`, the third deliberately
  hostile (a prompt demanding prose, "no JSON, no braces, no quotes") to separate *accepted* from
  *enforced*.
- **Concurrency**: 1/2/4/6 concurrent builders, each on a **distinct** corpus slice so the sweep
  cannot be flattered by cross-worker cache hits, wrapped in `hw-probe run --pid`.
- **Not done**: no in-process `llama-cpp-2` FFI spike, and no multi-hour soak. Both are argued
  below rather than measured, and marked as such.

## Inherited

| From | What | Where |
|---|---|---|
| Phase 0 | The boundary is answered: HTTP, two dialects, no FFI, 131 configs, live-verified | §11.0 W2 row |
| Claudette | Both dialects, and the retry that makes a model reload survivable | `api.rs:603-640`, `:655-733` |
| Claudette | `ToolsProvider::Dynamic` — the tools array re-read on **every** request | `api.rs:163-187`, `:740` |
| Claudette | 20 on-demand tool groups: 827 chars core, 33,251 chars fully loaded | `prestudy/inheritance-map.md:287` |
| ABCC v1 | The 10.5% tool-call malformation rate constrained decoding would attack | `prestudy/data-assets.md:350` |
| W1 | Swap cost, residency, KV pre-allocation, MTP | `research/W1-models.md` F74–F80 |

## Findings

### F81 — prefix caching saves 79.7% of time-to-first-token, and one token at the front destroys all of it

The brief predicted this conflict and asked for both sides quantified before choosing. Measured at
an 18,470-token prefix, champion at `-c 65536`:

| Request | TTFT | vs reuse | What it models |
|---|---|---|---|
| **A** cold | 11.549 s | — | first sight of the prefix |
| **B** reuse, identical prefix, new question | **2.349 s** | 1.00× | four builders sharing a system prompt |
| **C** one token changed at the **front** | **11.399 s** | **4.85×** | **a changed `tools` array** |
| **D** one token changed at the **end** | 3.049 s | 1.30× | a new user message — the benign case |
| **B2** reuse again | 2.648 s | 1.13× | stability check |

Two numbers carry the whole finding. **Reuse saves 79.7% of TTFT.** And **C is statistically
indistinguishable from a cold prompt — 11.399 s against 11.549 s, 0.99×.** The cache is not
degraded by a front edit; it is *annihilated*. D shows the mechanism is a genuine longest-common-
prefix match: edit the tail and everything before it still hits.

**Why this lands on `ToolRegistry` specifically.** Claudette's main runtime uses
`ToolsProvider::Dynamic` (`api.rs:169`), and `build_chat_body` resolves it **fresh on every
request** (`api.rs:740`). The rendered prompt puts tools in the system position — LM Studio spawns
`llama-server` with `--jinja --chat-template-file`, so the tools array is templated *ahead of* the
conversation. An `enable_tools` call between turns is therefore exactly case **C**, and the
registry grows from 827 chars to as much as 33,251 (`inheritance-map.md:287`).

**Priced at the daily driver's context this is brutal.** The same cold prefill at ~55k tokens took
**33.9 s** (F80). Against a 27.8:1 prefill:decode workload, a design that mutates the tool array
mid-session pays that repeatedly, and the *only* turn that benefits from on-demand tool groups is
the one that enables them — every subsequent turn in the session would have hit the cache anyway.

⚠ **The saving is real but it is not free of a subtlety:** B2 (2.648 s) is 13% slower than B
(2.349 s), so reuse is not perfectly reproducible. Treat 79.7% as "roughly four-fifths", not a
constant.

### F82 — constrained decoding works through the whole stack today, and Claudette uses it nowhere

**`response_format: {"type": "json_schema", …, "strict": true}` is honoured end-to-end** through
LM Studio's proxy on `:1234`. The proof is the hostile probe, not the happy path:

> Prompt: *"Write a two-paragraph prose essay about the sea. Use no JSON, no braces, no quotes.
> Begin with the word 'The'. Do not mention verdicts or scores."*
> Reply: `{"verdict": "pass", "score": 100}`

Every instruction in that prompt pushed away from the schema and the grammar won. That is
enforcement, not compliance. Three operational facts come with it:

1. **`json_object` is rejected**, HTTP 400: `'response_format.type' must be 'json_schema' or
   'text'`. The older, looser OpenAI dialect is **not** available here — which matters directly for
   the "keep an OpenAI-compatible surface" item, since code written against `json_object` fails
   closed against LM Studio.
2. 🚨 **The reasoning trace is not constrained, and it is spent first.** At `max_tokens: 300` both
   schema probes returned `finish_reason: "length"` with **`content: ""`** — the model burned the
   entire budget on reasoning tokens and never reached the constrained payload. At 3,000 it
   answered instantly and correctly. **This is a silent failure**: an empty string that parses as
   nothing, from an endpoint that returned HTTP 200. Any 2.0 code path using schemas on a reasoning
   model must budget for trace + payload and treat empty content as an error, not as "the model
   declined".
3. **Claudette does not use any of it.** `response_format`, `json_schema`, `grammar`, `gbnf`:
   **zero occurrences across all 93 source files.** Structured output is prompt-and-pray today.

The brief calls constrained decoding *"potentially a bigger quality lever than model choice"*. On
this evidence that is not hyperbole: it is available, it is enforced, it costs one request field,
and the family's one surviving hard number about output reliability is ABCC's **10.5% tool-call
malformation rate** (`data-assets.md:350`) — a failure class a grammar makes unrepresentable.

### F83 — the concurrency ceiling is 2, and the machine does not become unstable

The brief asks for *"the point where the machine becomes unstable, reported as a hard limit, not a
tuning suggestion"*. Loaded `--parallel 4 -c 65536`, distinct ~5.5k-token prompt per worker:

| N | wall | ok | TTFT median | TTFT max | aggregate prefill | aggregate decode |
|---|---|---|---|---|---|---|
| 1 | 6.10 s | 1/1 | 4.92 s | 4.92 s | 910 tok/s | 16.4 tok/s |
| **2** | 7.28 s | 2/2 | 3.67 s | 5.16 s | **1,541 tok/s** | **27.5 tok/s** |
| 4 | 14.70 s | 4/4 | 7.23 s | 10.33 s | 1,511 tok/s | 27.2 tok/s |
| 6 | 21.82 s | 6/6 | 10.54 s | 19.25 s | 1,537 tok/s | 27.5 tok/s |

**Aggregate throughput saturates at N=2** — 1→2 buys +69% prefill and +68% decode, and 2→4→6 buys
**nothing** (1,541 → 1,511 → 1,537 tok/s, flat inside noise). Past 2, every additional builder is
pure latency tax: median TTFT rises 3.67 → 7.23 → 10.54 s and the tail reaches 19.25 s.

**The honest correction to the brief's framing: it never became unstable.** 13/13 requests
succeeded, including at N=6 with only 4 slots (the extra two queued). Peak VRAM reached 15,339 MiB
of 16,311 (94.0%) — the highest of the session, because concurrent sequences hold more KV — and the
card stayed at 69 °C with no throttle. The limit is economic, not a cliff, and reporting it as a
crash point would have been wrong.

⚠ **The KV bound is a sum, not a division.** `--kv-unified` is on, so slots *pool* the window
rather than each getting `ctx/N`: an 18,485-token prompt succeeded on a 4-slot server whose
`--ctx-size` was 65,536 (16,384 per slot if it divided). The real constraint is
**Σ(active sequence lengths) ≤ 65,536**. Four builders at the daily driver's 61,440 is arithmetically
impossible; four builders at ~16k each is the actual budget.

### F84 — the boundary is confirmed, and the compat dialect silently drops the context knob

Confirmed against code. Claudette speaks two dialects from one client: `/api/chat` (Ollama-native,
NDJSON) and `/v1/chat/completions` (OpenAI-compat, SSE), selected by `CLAUDETTE_OPENAI_COMPAT=1`
(`api.rs:603-608`, `:368`). Both stream. Both send `tools`. The compat path asks for
`stream_options.include_usage` to recover real token counts (`api.rs:782`).

Two things the confirmation surfaced that the §11.0 row does not say:

- 🚨 **`num_ctx` has no analogue in the compat dialect and is simply not sent** (`api.rs:759-761`).
  The window is fixed at load time. This is the mechanism behind the F50 trap, now confirmed from
  the serving side: the client cannot request a window, so `LM Studio window ≥ CLAUDETTE_NUM_CTX`
  is an inequality *nothing on the wire enforces*. A window smaller than the pin means the server
  drops the front of the context and every downstream number still looks plausible.
- **The reload retry is load-bearing and should be inherited.** `api.rs:655-733` matches six
  surface forms of LM Studio's transient 400 (`model reloaded`, `model is loading`, `model not
  loaded`, `model unloaded`, `failed to load`, `operation canceled`) and retries once after 750 ms.
  F79's measured swap cost (23.77 s round trip) is exactly when that window opens, so a 2.0 that
  swaps models per gate will hit this constantly. **Do not reimplement it from scratch; port it.**

### F85 — one shared server is the only affordable answer, and the swap cost decides it

The brief flags this as having *"larger consequences than it appears"*. On this box the arithmetic
removes most of the choice:

- **Two resident model servers is impossible.** F68 closed co-residency: the champion occupies
  ~14.3–14.8 GiB of a 16,311 MiB card and the smallest model on disk is 3,759 MiB.
- **Two servers time-sharing one GPU** means every context switch is a 12 s load (F79), and neither
  process can know the other is mid-swap.
- **One server, two clients** is free at the model layer — LM Studio already multiplexes, and F83
  shows the second concurrent sequence is the *only* one that buys aggregate throughput. Claudette
  and ABCC 2.0 running one builder each is precisely the N=2 sweet spot.

**Recommendation: one shared LM Studio server, and 2.0 must not assume it owns the model.** Two
concrete consequences fall out of the measurements. First, F81 means a second client sharing the
server **shares the prefix cache** — and evicts it. Claudette and 2.0 alternating turns with
different system prompts will thrash a cache worth 79.7% of TTFT; the "one resident model serving
both" option is cheap in VRAM and *not* free in latency. Second, F75 means either client can pull
the weights out from under the other: `lms unload` is unilateral and the pid changes.

### F86 — `llama-server`'s command line is the only complete witness to the serving config

LM Studio spawns, per load:

```
llama-server.exe --model …IQ3_S-3.06bpw.gguf --host 127.0.0.1 --port 52842 --api-key …
  --no-webui --jinja --chat-template-file …chat-template.jinja
  --ctx-size 65536 --n-gpu-layers 999999 --n-cpu-moe 0 --main-gpu 0 --tensor-split 0
  --split-mode layer --batch-size 2048 --ubatch-size 512 --threads 2 --parallel 1
  --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --kv-offload --kv-unified
  --no-direct-io --no-mmap --spec-type draft-mtp --spec-draft-n-max 2 --spec-draft-n-min 0
  --spec-draft-p-min 0.75
```

**`--cache-type-k/v`, `--flash-attn`, `--kv-unified`, `--batch-size`, `--spec-type` are reported by
no LM Studio API** — `GET /api/v0/models` returns only id, arch, quantization, state,
`loaded_context_length` and capabilities. Q56's rule is that a held constant nobody measures is not
held; this command line is the only place several of them are visible. **Record it per campaign**
via `Get-CimInstance Win32_Process -Filter "Name='llama-server.exe'"`.

It also settles the boundary question in 2.0's favour in a way the dossier could not: underneath
LM Studio is **stock llama-server on a random localhost port behind an API key**. Everything
llama.cpp's server can do — GBNF `grammar`, `/infill`, `/props`, slot save/restore — exists one
layer down, and LM Studio is a supervisor, not a reimplementation.

## Options compared

Scored on what this box measured: latency, control over sampling and grammars, crash isolation,
and behaviour when a model must swap.

| Option | Latency | Grammar control | Crash isolation | Model swap | Verdict |
|---|---|---|---|---|---|
| **HTTP to LM Studio (incumbent)** | 2.35 s TTFT warm at 18k; 79.7% cache saving | **Full** — `json_schema` enforced (F82) | **Process boundary**; client survives a server crash, and `api.rs:655` already retries the reload window | `lms load`, 12 s, unilateral | **Keep** |
| HTTP to bare `llama-server` | Same wire, one less hop | Full, **plus GBNF `grammar` and slot save/restore** | Same | Own the process; no LM Studio UI | Fallback / power option |
| In-process `llama-cpp-2` (FFI) | Saves an HTTP hop — irrelevant at 27.8:1, where TTFT is dominated by prefill | Full, in-process | 🚨 **None** — a llama.cpp abort takes the orchestrator with it | Direct, but 2.0 owns the memory | **Reject** |
| Ollama-native `/api/chat` | Equivalent | Weaker — no schema field in the shape Claudette sends | Same | `keep_alive` semantics | Keep as the second dialect, not the primary |

**Crash isolation is the argument that ends the FFI question**, and it is not theoretical here: a
process boundary is what let session 19 kill and reload the model twelve times without restarting
anything else. The brief's own framing — latency, control, crash isolation, swap behaviour — scores
HTTP first on three of four, and the fourth (latency) is worth ~1 ms against a 33.9 s prefill.

## Recommendation

1. **Keep the HTTP boundary and both dialects. Do not build FFI bindings.** Confirmed, and the
   crash-isolation argument is stronger than the latency argument against it.
2. **Adopt constrained decoding as a first-class mechanism** (F82). It is enforced, it costs one
   request field, and it attacks the family's only measured output-reliability number. Two rules
   ship with it: never `json_object`, and always budget tokens for the unconstrained reasoning
   trace ahead of the payload — treat empty content on `finish_reason: length` as a hard error.
3. 🚨 **Make the system prefix immutable within a session, and put the tool schema in it once.**
   This is the biggest single lever in W2. On-demand tool groups save ~33 KB of prompt but cost a
   **full cold prefill on the turn they change** — 11.4 s at 18k, 33.9 s at 55k — against a 27.8:1
   prefill-dominated workload. Decide the tool set at session start; if a group must be added, treat
   it as starting a new session, and say so in the console rather than paying it invisibly.
4. **One shared LM Studio server for Claudette and 2.0** (F85), with 2.0 written to assume it does
   not own the model: re-resolve the `llama-server` pid, tolerate the reload 400, and expect the
   prefix cache to be shared and evictable.
5. **Cap concurrent builders at 2** (F83). Report it as the hard limit the brief asked for, with the
   correction that the failure mode is latency, not instability, and the KV bound is
   Σ(sequence lengths) ≤ window, not window/N.
6. **Port `post_with_model_reload_retry` rather than rewriting it** (F84). Six matched surface forms
   is accumulated field knowledge, and a swap-per-gate design will exercise it far harder than
   Claudette ever did.

## Rejected alternatives and why

- **In-process `llama-cpp-2` FFI** — no crash isolation, and the latency it saves is invisible
  against a workload that is 96% prefill. Reconsider only if 2.0 ever needs logit-level access that
  HTTP cannot express.
- **Two model servers, one per tool** — F68 makes co-residency impossible and F79 prices
  time-sharing at 23.77 s per switch.
- **`response_format: json_object`** — rejected by the server, HTTP 400. Not a style preference.
- **On-demand tool groups as a prompt-size optimisation** — F81 shows the trade is inverted on this
  workload. Keep the *mechanism* for capability scoping and permissions; stop treating it as a token
  saving.
- **Reporting a concurrency "instability point"** — measured, and it does not exist up to N=6.
  Reporting one would have been a fabricated cliff.

## Effect on fun

The prefix-cache result is a game mechanic waiting to be surfaced. A 79.7% saving that a single
front-of-prompt edit annihilates means **"what the fleet knows" has a visible, costed state** — and
2.0 already wants to show the operator what their machine is doing. Changing a unit's loadout
mid-mission genuinely costs 11–34 seconds of the console going quiet; that is not a wart to hide
behind a spinner, it is a supply line the player can learn to respect. The honest reading of F83 is
the same shape as F68's: **two builders is the fleet size the hardware supports**, and a console
that shows six units pretending to work in parallel is lying about a 19-second tail.

Constrained decoding is the quieter win. Guaranteed-parseable output is what lets the console
render structured verdicts, scores and diffs as *interface* rather than as text a parser hopes to
survive — and it removes the failure mode where a unit reports garbage and the operator cannot tell
whether the model or the harness broke.

## Open questions

1. **Does the prefix cache survive a second client?** F85 argues Claudette and 2.0 will thrash it;
   that is reasoning from F81, not a measurement. Two clients alternating turns against one server,
   measuring TTFT on each, would settle it and is a one-session experiment.
2. **GBNF `grammar` against bare `llama-server`** — richer than JSON schema and reachable on the
   random port, but not exercised. Worth it only if schema proves insufficient.
3. **Slot save/restore** (`--slot-save-path`) as an alternative to prefix caching: it would let a
   session's KV be parked and restored across a model swap, which is exactly what a swap-per-gate
   W6 design needs. Unmeasured, and potentially the answer to F79's 23.77 s.
4. **Does constrained decoding cost throughput?** Not measured — the grammar probes were single
   short replies. Grammar evaluation is per-token work and should be checked before it ships on a
   hot path.
5. **Soak behaviour.** Everything here is minutes-long. Nothing establishes what a shared server
   does over an 8-hour session with hundreds of swaps.

## Confidence: high, on a narrow base

**High** on everything measured, because the measurements are direct, repeated, and several carry
their own negative control: prefix caching (F81, five requests including the front/tail
discriminator), constrained decoding (F82, proven by a hostile prompt rather than a cooperative
one), the concurrency ladder (F83, 13 requests, no failures), and the serving configuration (F86,
read off the process rather than from a doc).

**Medium** on F85's shared-server recommendation — the VRAM arithmetic is certain, but the
cache-thrashing consequence is inference from F81 rather than a two-client measurement (open
question 1).

**Low** on anything about duration. No soak test ran, and the one thing this session proved
repeatedly is that instruments look correct until a control is run against them — F74 deleted a
verdict this crate had been printing for a week.

**What would raise it:** open question 1, then 3. Slot save/restore is the item most likely to
change a recommendation elsewhere in the project, because it could turn W6's per-gate model swap
from a 23.77 s stall into something affordable.
