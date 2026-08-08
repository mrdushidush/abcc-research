# Agent Battle Command Center 2.0 - Pre-Research Brief

**Owner:** David (mrdushidush)
**Executing agent:** Claude Code
**Co-development partner (from Phase 3):** Claudette
**Phase:** 0 - Pre-research. Nothing is designed, chosen or built yet.
**Last updated:** 2026-08-07

---

## 0. Mission

ABCC v1 was the right idea at the wrong moment. It proved that a fun, legible, RTS-style
command center over AI coding agents is something people actually want to look at, and it
proved that most coding tasks do not need a frontier model. But it was built around a 7B
dense worker on Ollama, in a three-language stack, at a time when local inference could not
carry the load. The landscape has moved, and so has the owner's expertise.

2.0 combines three things that already exist and already work:

- **From ABCC v1:** the soul. The Command and Conquer command center, the unit metaphor, the
  voice lines, the battlefield view, the feeling that you are commanding something rather
  than watching a log scroll. Plus a real routing dataset and a real complexity model.
- **From Claudette:** the harness. Proven tool calling, the eval loop, the quality gates, and
  a local model that actually works on this hardware.
- **From BattleCommandForge:** the architecture. Rust, and a shipped pipeline design that has
  survived contact with real work.

Base agent: **Qwen 3.6 35B-A3B**, local.

**Success criterion, stated plainly:** a real coding and development tool that a working
developer reaches for by choice, and that is genuinely fun to use. Not a demo. Not a
benchmark harness with a skin on it. The tool humanity deserves, built properly.

**This will take time. That is the plan, not a problem.** Every phase below is gated. Nothing
starts before the previous thing is genuinely finished. There is no deadline and no reason to
ship something half-built.

---

## 1. Phases and gates

| Phase | What happens | Gate to exit |
| --- | --- | --- |
| **0 - Pre-research** (now) | Claude Code studies the three source repos in depth and produces a factual account of what each one actually is | Three repo dossiers exist, the inheritance map exists, and section 3 of this brief has been corrected against the code |
| **1 - Research** | The workstreams in section 11. Evidence, options, measurements, ADRs | SUMMARY.md states a recommended architecture with rejected alternatives and what would falsify it |
| **2 - Development plan** | Turn the research into a sequenced build plan with milestones | David signs off on the plan |
| **3 - Co-development** | Claude Code and Claudette build it together. See section 12 | The tool builds itself. See section 16 |

**You are in Phase 0.** Do not design the architecture. Do not open the model landscape
question. Do not write a line of ABCC 2.0. Read the code, write down what is there, and stop.

---

## 2. Hard rules

1. **Phase discipline.** If you find yourself proposing an architecture during Phase 0, stop
   and write the observation down as an input to Phase 1 instead.
2. **The repos beat this brief.** Section 3 describes the three projects partly from memory
   and secondary sources. Where the code contradicts this document, the code wins, and you
   update this document as the first Phase 0 deliverable.
3. **Verify everything external against live sources.** Model names, versions, context
   windows, licenses, quantization support, crate versions, prices, benchmark scores. Every
   such claim carries a source URL and the date you retrieved it. Do not trust training data
   on any of it.
4. **Flag staleness.** Sources older than 6 months get marked `[STALE]` with a note on
   whether the claim still holds. Rust crate ecosystems move fast; check the last commit date
   and open issue count on anything you propose depending on.
5. **Prefer primary sources.** Model cards, crate docs, repo READMEs, release notes. Vendor
   benchmarks of vendor products get marked `[VENDOR]`.
6. **Measure, do not assume.** Anything settleable by running it on the actual hardware gets
   run, with numbers reported.
7. **Do not re-derive what three working repos already answered.** Say per workstream what
   you inherited and what you measured fresh.
8. **No recommendation without a rejected alternative.** Name at least two options you did
   not pick and say why.
9. **Fun is a requirement, not a garnish.** See section 7. A recommendation that makes the
   system more correct and less enjoyable to operate has to justify itself.
10. Use plain hyphens in all prose. No em dashes, no en dashes.

---

## 3. The three source repos

**Corrected against the code, 2026-08-07.** Every repo is pinned: ABCC v1 `d5528ea`,
Claudette `fc1ea22` (v0.17.0), battle-command-forge `d6c1601` (v0.2.0). Full detail and file
references live in the three dossiers under `prestudy/`. Corrections are listed at the end of
this section.

### 3.1 ABCC v1 - the soul and the data

Public, MIT, `github.com/mrdushidush/agent-battle-command-center`. Still receiving commits
(last: 2026-08-06), 318 commits. Roughly 38k lines of source across three languages, plus a
24k-line `scripts/` tree of benchmark and ops tooling that outgrew the application.

Built as a learning project for local AI. Fun was the goal; architecture and correctness
deliberately were not. It succeeded at what it set out to do, and the defects below should be
read in that light.

Stack as shipped:

```
UI (React:5173) -> API (Express:3001) -> Agents (FastAPI:8000) -> Ollama / Claude / Grok
                          |                       |
                    PostgreSQL:5432    <----------+  (execution-log writeback over HTTP)
```

The back-edge matters: the agents service calls the API to persist logs while the API is
synchronously waiting on the agents service. The two are mutually dependent, not layered.

Behaviour as shipped:

- Local worker is `qwen2.5-coder:7b` with Modelfiles at 8K, 16K, 32K (and 64K, Mac-only).
  8K is deprecated. **Tuned throughout for an RTX 3060 Ti 8GB** - no model-sizing conclusion
  transfers to the 5060 Ti without re-measurement.
- **Dual complexity assessment on a 1 to 10 scale:** a rule-based pass over keywords and
  structure, plus a Haiku semantic pass, with asymmetric weighting - when Haiku scores 2 or
  more points *higher* it is taken outright; when 2 or more points lower the scores are
  blended 60/40 toward the rules. The asymmetry is the insight.
- Routing ladder: **C1-C6 local Ollama 16K, C7-C9 remote Ollama if configured otherwise local
  Ollama 32K, C10 Sonnet.** Haiku is *not* an execution tier: it does complexity assessment,
  periodic review, auto-retry phase 3, and fix attempt 1. Opus never writes code.
- The complexity model is grounded in Campbell's Task Complexity Theory, adapted to code.
  This is real intellectual property and it has already survived two ports into Rust
  (`battle-command-forge/src/router.rs` and Claudette's `Role::Planner`).
- **Measured results: 88 percent is a pass rate** (35/40, 2026-02-05), later 98 percent
  (39/40, 2026-02-20). It is *not* a routing rate. On a C1-C9 corpus the local routing rate is
  ~100 percent by construction. The cost-per-task figures are estimates, not measurements.
- **A 40-task evaluation set** scored C1 through C9. Superseded by Claudette's Q56; the C1-C4
  entries embed the reference implementation in the task description and are transcription
  exercises. The C8-C9 entries are worth salvaging.
- Three agent types: Coder, QA, CTO. In practice these are **model-tier bindings wearing role
  names** - routing to Sonnet selects the agent typed `qa`, and CTO is forced onto Claude.
- Auto-retry pipeline; its effect on pass rate is **unmeasured** and `CLAUDE.md` says so.
- Stuck-task detection at **5 minutes** (source comment: "was 10 - tightened").
- Loop detection: 50-call cap, per-path limits, similarity detection, reported back to the
  model as tool output. Good design, but its state is a **process-global singleton**, so it
  is mutually exclusive with the parallel execution listed below.
- Parallel execution, claimed 40 to 60 percent speedup on mixed batches, no cited measurement.
- Cost dashboard with daily budget limits and burn rate.
- Presentation layer: Red Alert styling, 96 Bark TTS voice lines (6.4 MB), a React Three Fiber
  3D battlefield, **a separate 2D isometric renderer with its own projection maths**, three
  minimaps, a terminal-style tool log, a token burn log, a theme system. No bounty board
  exists.
- Also present and undocumented in this brief: a Mission orchestrator, a Battle Claw external
  API, xAI/Grok support, a cross-task memory system, and a training-data export pipeline.
- Target languages: Python, JS, TS, Go, PHP, with per-language validation and test templates.
- One durable prompting finding: the "CodeX-7" elite operator persona plus **seven** worked
  examples pushed the model from write-read-rewrite into write-verify-report. The persona has
  since travelled into Claudette, where it is baked into the binary as `personas/codex7.md`.
  Note the ABCC copy is **textually corrupted** - a numbered list beginning at item 2 - so the
  measured results were achieved with a damaged prompt.

**Known defects worth carrying into design, not criticism:** a parse failure is reported as
success (`main.py:436-447`, `success=True  # Assume success unless proven otherwise`); the
`/execute/abort` endpoint aborts nothing because its state map is never populated; execution
logs are recovered by scraping CrewAI's stdout.

**What 2.0 inherits from ABCC:** the console concept and its entire visual and audio language,
the isometric renderer, the unit and stage metaphor, the complexity model, the `ExecutionLog`
shape, the C8-C9 corpus entries, and the CodeX-7 persona finding.

**What 2.0 does not inherit:** the codebase. V1 is a donor, not an ancestor.

### 3.2 Claudette - the harness

**Public**, MIT OR Apache-2.0, `github.com/mrdushidush/claudette`, published on crates.io.
Rust, v0.17.0, 470 commits, ~60k lines in a single crate. `cargo test --lib`: **1,145 passing
in 14.76 seconds.**

Built after significant local-AI expertise had accumulated, focused on precision, correctness
and usability, with the fun layer omitted entirely. The owner's most complete shipped product.

Daily driver is **LM Studio** (which runs llama.cpp underneath), reached over HTTP. `api.rs`
speaks two dialects: Ollama-native `/api/chat` and OpenAI-compatible under
`CLAUDETTE_OPENAI_COMPAT=1`. There are no in-process bindings and no FFI. The same surface has
driven LM Studio, `llama-server` and Ollama.

Three checkouts exist and all are working roles: `claudette` is canonical, `claudette-forge`
is the clone Claudette edits when working on her own code, `claudette-research-control` runs
the Q56 battery.

**What 2.0 inherits from Claudette:** far more than the brief originally assumed.

- **Native tool calling** (`tools` array out, `message.tool_calls` in) - the thing V1's 7B
  could never do.
- The **`ConversationRuntime<C,T>` seam**: two traits, `ApiClient` and `ToolExecutor`, which
  is why the loop is testable without a model.
- A **20-group on-demand tool registry** keeping the base schema at ~210 tokens, plus the
  hard-won fix for its failure mode (see below).
- **Nine differentiated loop breakers**, auto-compaction, context eviction, empty-turn retry.
- A **transcript with trash-backed undo**, secret redaction before write, and bounded restore
  targets - a working answer to the human-in-the-loop requirement.
- **Structural air-gapping**: `default = []` means no cloud code is compiled into the default
  binary, plus `egress.rs` guarding both the HTTP and subprocess paths.
- A **five-phase forge pipeline** (Planner, Coder, Verifier, Fix-loop, Submitter) that runs
  daily against real repos.
- **Q56**: 56 tasks across 11 surfaces and 12 task types, a shell verifier per task, no LLM
  judge anywhere, run across 131 model configurations with negative results retained. This is
  the project's evaluation baseline.
- The **champion campaign** and its measurements. See the correction to section 5 below.

**One transferable failure worth stating explicitly.** The tool-group indirection saves tokens
but the model dropped the required `group` argument 415 times in one baseline capture, then
spiralled to timeout. The fix kept the mechanism and removed the requirement to use it:
pre-enable a lean coding core when a workspace is set, and treat a bare `enable_tools()` as a
request for that core. Errors went to zero and tasks got faster. **A token-saving indirection
that a small model cannot reliably operate costs more than it saves.**

**Open:** whether Claudette and ABCC 2.0 share code as a library, share a running model
server, or stay fully separate. This is a Phase 1 decision, in W2 and W3. Note that Claudette
is deliberately synchronous - no async runtime at all - which collides with 2.0's need for
parallel builders, a live console and a fleet protocol.

### 3.3 battle-command-forge - the greenfield POC

**Public**, **Apache-2.0**, `github.com/mrdushidush/battle-command-forge`, on crates.io as
`battlecommand-forge` v0.2.0. Rust, ~16k lines in 33 flat modules in one crate, ~3.7 MB
binary, MSRV 1.95. Git history is a squashed snapshot: 7 commits, real work ending 2026-04-30.
`cargo test`: 96 passing, 2 failing (both Unix assumptions running on Windows).

A greenfield POC that generated production-shaped projects, including good-looking landing
pages. It never became a daily driver. Backend is Ollama, not LM Studio.

Section 3.3's original description was broadly correct. The **9-stage pipeline** is real:
Router, Architect, Tester, Coder, Verifier, Security, Critique, CTO, Gate. Stages 5 and 9 -
the two that actually decide anything - involve no model at all.

**What 2.0 inherits:**

- **The gate formula**, `final_score = critique_avg * 0.4 + verifier_score * 0.6`, with the
  source comment "Verifier (tests + linting) is the real quality signal - weight it higher".
  This is the most portable artifact in the three repos: it does not remove the LLM judge, it
  **outvotes** it, and unlike Q56's per-task verifiers it generalizes to arbitrary work.
- The **surgical fix loop**: trace imports to the broken files, fix each with its own call and
  its own error context, leave passing files untouched, restore the best round if the score
  declines twice, and never add features during a fix round.
- **`router.rs`** - a Rust port of ABCC's Campbell dual assessment that keeps `rule_score` and
  `ai_score` as separate typed fields, structurally fixing the data loss ABCC's 2026-02-01
  migration caused.
- **`sandbox.rs`** - a subprocess environment **allowlist** (adopted after a blocklist missed
  `OLLAMA_HOST`, `DATABASE_URL`, `AWS_ACCESS_KEY_ID`, `SSH_AUTH_SOCK`), path-traversal
  validation, and timeouts.
- `check_secrets` and `check_todos` folded into the quality score.

**What it does not offer:** project structure. There are no crate boundaries, no workspace and
no visibility discipline - take the pipeline, not the layout. The verifier is **not
Python-only**: project tests run for Python, Rust, Go and TS/JS, with Python the only
environment-constructing path. The complexity-scaled thresholds (9.2 / 8.5 / 8.0) are
**cloud-assisted calibration** and are empirically unreachable all-local, where the 10-mission
average was 7.5; the successor made the threshold config-driven with a default of 8.0.

**Two negative results worth more than the code:** decomposition was tried and reverted
("caused duplicate projects; single-task plus good prompts is better"), and the in-TUI
minigames are the wrong answer to the right question about operator dead air.

### 3.4 Corrections made to this section

Delivered as a git diff against the original brief. The substantive changes:

1. ABCC's 88 percent was a **pass rate**, presented here as a routing rate.
2. ABCC's routing ladder was wrong: **Haiku is not an execution tier.**
3. Stuck-task detection is 5 minutes, not 10. The persona has seven examples, not three.
4. There is no bounty board. There *is* an undocumented 2D isometric renderer.
5. ABCC was tuned on an **RTX 3060 Ti 8GB**, not the current hardware.
6. Claudette runs **LM Studio**, not bare llama.cpp, and is public rather than private.
7. Claudette's contribution was scoped to "tool calling and the eval loop"; it is most of an
   agent runtime, a safety layer and a 131-configuration measurement campaign.
8. BCF is **not Python-only**, is Apache-2.0 against ABCC's MIT, and has no reusable structure.
9. BCF's gate **thresholds** do not transfer to a local-first tool; its gate **formula** does.

Two corrections fall outside section 3 and are **left for David to accept or reject**, since
section 6 asks for loud disagreement rather than quiet redesign:

- **Section 5's hardware framing is out of date.** "MoE under llama.cpp with `--n-cpu-moe`,
  mmap off" describes the incumbent configuration. The crowned configuration of 2026-07-11
  runs **fully VRAM-resident with zero expert offload**; `--cpu-moe` measured 1.16x and is
  marked "don't use"; "residency is ~90% of the win". This reframes W1 and W2 from surviving
  offload into 32GB to staying resident in 16GB, and makes the 32GB ceiling much less binding.
- **Section 6's decision table** should read "LM Studio, which runs llama.cpp underneath". The
  value of the OpenAI-compatible surface is that it keeps that choice reversible.

---

## 4. Phase 0: the repo study

This is the current task and the only current task.

### 4.1 Per repo, produce a dossier

For each of ABCC v1, Claudette and BattleCommandForge, write
`prestudy/<repo>-dossier.md` covering:

- **Module map.** Directory structure, what each module owns, and the dependency graph
  between them. For the Rust repos, the crate layout and the workspace structure.
- **The agent loop.** Trace one task end to end through the code and write down the actual
  sequence of calls. Where the prompt gets assembled, how the model is called, how the
  response is parsed, how tools are dispatched, how failure is detected.
- **Tool calling.** How it is implemented, what schema, what parser, what happens on
  malformed output, what retry behaviour. This is the highest-value thing in Claudette and
  the biggest gap in ABCC v1, so be thorough.
- **State and persistence.** What is stored, where, in what schema, and what survives a
  crash.
- **Quality gates and verification.** What checks exist, when they run, how a pass or fail is
  decided, and what happens on fail.
- **Evaluation.** What test or eval sets exist, how they are run, what they measure.
- **Configuration surface.** Every knob, and which ones matter.
- **What works well.** Be specific and name files.
- **What is broken, half-finished or was clearly a workaround.** Equally specific.
- **Dependencies,** with versions, and a note on which look stale or unmaintained.
- **Size and test coverage,** roughly, so we know what we are actually carrying.

### 4.2 Extract the data assets

- ABCC's PostgreSQL holds months of real execution logs with per-tool-call timing, token
  usage and cost, plus collected training data. Dump the schema, characterize the contents,
  and report how many task runs are actually in there and how usable they are.
- Recover the 40-task evaluation set and its recorded results in a portable form.
- Recover Claudette's harness data and eval results in the same way.

Deliverable: `prestudy/data-assets.md` plus the extracted datasets committed somewhere sane.

### 4.3 The inheritance map

`prestudy/inheritance-map.md`. A table with one row per meaningful component across all three
repos and a column for the verdict: **port to Rust**, **reuse as-is**, **rewrite from
scratch**, **reference only**, or **drop**. Every verdict carries a one-line reason.

This document is the bridge between Phase 0 and Phase 1. It is the deliverable that matters
most.

### 4.4 Correct this brief

Rewrite section 3 against what you found. Flag every place where this document was wrong,
because it will be wrong somewhere. Deliver as a diff and a short note on what changed.

### 4.5 Open questions for Phase 1

`prestudy/questions.md`. Everything you noticed that the research phase needs to answer,
including things not currently in section 11. Do not answer them yet.

**Phase 0 gate:** all five deliverables exist, section 3 is accurate, and David has read the
inheritance map.

---

## 5. Hardware and constraints

| Resource | Spec | Role |
| --- | --- | --- |
| Desktop GPU | RTX 5060 Ti, 16GB VRAM (Blackwell) | Primary inference |
| Desktop CPU/RAM | 32GB DDR4, ASUS B460M-K, GPU link capped at PCIe 3.0 x8 | Hosts offloaded MoE experts. **Binding constraint.** |
| Desktop storage | C: Kingston SNV3S 2TB NVMe (OS, dev, GGUF models), D: Samsung 870 EVO 2TB SATA (games only) | Model load latency |
| Laptop | ASUS TUF F15, i5-12500H, RTX 3050 4GB | Secondary node over Tailscale. Too small to be a useful worker. |
| Network | Tailscale mesh, RDP and SSH between the two | Multiplayer test substrate |

There is no Apple silicon anywhere in this project. Do not research MLX or Metal. The fleet
is single-runtime CUDA.

Constraints that shape every recommendation:

- **32GB system RAM is the ceiling, not 16GB VRAM.** MoE under llama.cpp with
  `--n-cpu-moe`, mmap off. A past full-system freeze from RAM saturation, with model and dev
  environment running together, is the known failure mode. Any concurrency number is a
  measured number.
- **Rust helps here.** A Rust orchestrator has a far smaller resident footprint than Node plus
  Python plus CrewAI, and on a box where RAM is the binding constraint that is not an
  aesthetic preference, it is headroom for the model. Quantify it in Phase 1.
- **PCIe 3.0 x8 to the GPU.** Relevant to weight load times. Measure rather than assume.
- **No cloud GPU budget.** Frontier API spend is acceptable but metered and minimized.
- **Data sovereignty, honestly stated.** The requirement is not "code never leaves", it is
  "code leaves only through a deliberate, policy-governed, logged path".
- **Single operator, single machine, most of the time.** Design for that first.
- **It has to run on other people's machines.** ABCC is public with real users. A single Rust
  binary is a large improvement over a five-container Docker Compose stack here, but every
  hardware-specific recommendation still needs a stated degradation path for smaller rigs.

---

## 6. Decisions already made

These are settled. Do not reopen them in Phase 1 without new evidence strong enough to be
worth the disruption, and if you have that evidence, say so loudly rather than quietly
designing around it.

| Decision | Rationale |
| --- | --- |
| **Rust** | Proven twice already in Claudette and BattleCommandForge. Single binary, small resident footprint on a RAM-constrained box, and the owner's current working language. |
| **Qwen 3.6 35B-A3B as the base agent** | Already the daily driver in Claudette, already tuned for this hardware, roughly 3B active parameters, strong agentic and tool-calling behaviour. |
| **llama.cpp as the inference engine** | Already working, already tuned, handles MoE expert offload. Ollama's inability to load current GGUF releases on this hardware is a known blocker. |
| **Local-first** | Frontier models are support, not the default path. |
| **The RTS command center stays** | It is the project's identity and half its point. |
| **Fun is a success criterion** | See section 7. |

What is genuinely open: everything about how the orchestrator is structured internally, the
tier partners around the base model, the console's technical shape, the fleet protocol, the
verification stack, and the repo and naming strategy.

---

## 7. Fun as an engineering requirement

This is the part most technical briefs would leave out, and it is the actual differentiator.
V1 got this right by instinct. 2.0 has to get it right on purpose.

Research it properly in W5, and treat these as design constraints rather than decoration:

- **No dead air.** The worst thing an agent tool does is go quiet for ninety seconds. V1
  solved this with streaming tool logs, voice lines and visible agent state. Whatever 2.0
  does, the operator always knows something is happening and roughly what.
- **Legibility over completeness.** A dashboard that shows six things clearly beats one that
  shows forty. The operator should be able to glance and know the state of the front line.
- **Agency.** Fun comes from being in command. The single biggest gap in V1 is that you could
  watch but not intervene. Pause, redirect, re-route, take over: these are the features that
  turn a spectator into a commander.
- **Personality with an off switch.** The Red Alert voice lines are delightful and will be
  the first thing a subset of users disable. Both facts are true. Make it excellent by
  default and trivially mutable.
- **Honest failure.** Nothing kills trust faster than an agent reporting success on a test
  run that never executed. V1 hit exactly this. Failure should be loud, specific and
  actionable, and the console should make a failed run as interesting to look at as a
  successful one.
- **Speed where it is felt.** Total wall clock matters less than time-to-first-visible-thing.
  Optimize the second one.

**How to evaluate it:** the honest metric is whether David reaches for this instead of Claude
Code for a real task, and whether he keeps it open when he does not have to. Write that down
in W8 as a first-class evaluation criterion alongside pass rate and cost. Also research what
has actually been written on developer tool ergonomics and flow, so this is grounded in more
than taste.

---

## 8. What 2.0 is, in three pillars

- **The factory.** An orchestration core built for a 35B-A3B class model that is far more
  capable than the 7B V1 was designed around. Fewer, larger subtasks. Less babysitting.
  Local models doing decomposition, not just execution.
- **The command center.** An operator console with real controls, not just a view. Live task
  graph, agent states, queue depth, escalations, cost accounting, and the ability to pause,
  retry, re-route, kill, edit a prompt, take over manually and replay a run.
- **The tool.** Something a developer actually uses on real work every day. This is the pillar
  V1 never reached, and the one everything else is subordinate to.

---

## 9. Game modes

Each mode is a distinct compute topology with its own failure modes, and the architecture has
to support all three without three separate codepaths.

### Single player - local only

One machine, local models only, no cloud calls. Stricter than anything V1 ran, since V1
always assumed a Claude escalation path. With Qwen 3.6 35B-A3B as the base agent, this is now
plausibly the *primary* mode rather than a degraded fallback, which is a significant shift.

- Model residency: how many models fit at once on 16GB VRAM plus 32GB RAM with expert
  offload, if any? Measure load and unload latency with mmap off. That number decides whether
  swapping is viable or whether one resident model is the whole design.
- Can the base agent credibly play every unit role through prompting alone? For a 7B this was
  hopeless. For a 35B-A3B it is a serious possibility, and if it holds, an entire class of
  scheduling complexity disappears.
- Scheduling: stage-major versus task-major execution order, and what each does to
  end-to-end latency when only one model is resident.
- This is the evaluation baseline. Every other mode has to beat it on cost per completed task.

### Co-op - local fleet plus cloud models

Local does the volume, frontier models are support. Roughly what V1 did, so the question is
how to do it better rather than whether to do it.

- Routing across the boundary. V1's answer was decomposition plus periodic review, with a
  measured 88 percent local rate. Test whether a 35B-A3B base pushes that higher and where
  the remaining escalations genuinely earn their cost.
- **Egress policy.** Explicit per-repo rules for what may cross to a cloud provider, a
  redaction step before egress, and an audit log of every payload sent. First-class design
  problem, and a genuinely useful feature for a public project aimed at people with
  proprietary code.
- Budget metering: per-run and per-day ceilings, with the run degrading to single player
  rather than failing at the ceiling.
- Availability: async escalation so a pending cloud call does not stall the local pipeline,
  plus retry and fallback.
- Latency asymmetry: cloud is slow and strong, local is fast and adequate. Research
  schedulers that exploit this rather than treating providers as equivalent.
- Provider abstraction in Rust: a gateway crate versus per-provider adapters, and what each
  costs in traceability.

### Multiplayer - remote inference rigs join the fleet

There is a real second node on a real Tailscale mesh, so the protocol can be tested end to
end even though the 4GB laptop contributes no meaningful capacity. Build and prove the
protocol; do not over-engineer for a fleet that does not exist.

- Discovery and registration: how a rig advertises VRAM, system RAM, resident models,
  measured tokens/sec and queue depth.
- Transport and auth: Tailscale overlay versus mTLS versus API keys. Tailscale is already in
  place, which makes the trusted personal-mesh case nearly free and the untrusted case the
  only real design work.
- Distributed scheduling: work stealing versus central dispatch, capability matching,
  latency-aware placement, and behaviour when a rig is slower than advertised.
- Failure handling: heartbeats, draining a rig mid-run, reassigning in-flight tasks, partial
  results. The laptop is the test target.
- Trust: output from a rig you do not control is untrusted input. Verification of returned
  artifacts, and the poisoning risk of a malicious rig.
- Existing tech to evaluate rather than reinvent: llama.cpp RPC backend, distributed serving
  in vLLM or Ray, current peer-to-peer inference projects. Verify what is actually maintained.
- Key question: is a remote rig just another provider behind the same interface as a cloud
  model, or does it need its own plane? Argue it.

Deliverable: a mode capability matrix showing what is available in each mode and what happens
when a mode is downgraded mid-run.

---

## 10. Battle stages

Four stages, each with its own unit type, model tier, output artifact and exit gate. This is
also the organizing principle for the console: the operator should see where the front line is.

| Stage | Units | Job | Output artifact | Exit gate |
| --- | --- | --- | --- | --- |
| Research | Recon | Explore the codebase and the problem, gather context, locate files, find prior art | Context pack | Is the context sufficient and correct? |
| Architecture | Engineering | Decompose into atomic tasks, decide interfaces, sequence the work | Task DAG with per-task acceptance criteria | Is every task atomic, unambiguous and testable? |
| Coding | Builders | Produce the diffs, docs or reviews | Patch set | Compiles, tests pass, lints clean |
| Gate | Commandos | Adversarial verification: break it, review it, probe it | Verdict plus defect list | Pass or fail, with reasons |

**Reconciliation required.** V1 ships three unit types (Coder, QA, CTO). BattleCommandForge
reportedly runs nine pipeline stages. This table has four. Phase 0 must surface all three
taxonomies side by side, and W11 must produce one. Do not assume this table wins.

Research questions across the stages:

- **Tier mapping.** Which tier fits each stage, given a decided base agent? Recon wants cheap
  plus long context. Architecture wants the strongest reasoning available in the current mode.
  Building wants parallel throughput. Gate wants adversarial capability. Justify with
  measurements.
- **Gate independence.** Is a model grading its own output reliable? If not, commandos must be
  a different model from the builders, and that constraint collides directly with single
  player mode where one model is resident. V1 dodged this using Haiku and Opus for review,
  which is a co-op-only answer. Resolve the tension explicitly; it is one of the sharpest
  open problems in the design.
- **Handoff artifacts.** Schemas for what moves between stages. Context packs and task DAGs
  are the contract and the place context bloat accumulates. Research compaction between
  stages. Rust's type system should make these contracts enforceable rather than hopeful,
  which is a real advantage over V1's JSON-by-convention approach.
- **Fan out and fan in.** Maximum useful builder concurrency, bounded by W2 serving findings
  and by the 32GB ceiling. Report a number for this hardware and a formula for other hardware.
- **Failure routing.** On gate failure, back to build, back to architecture, or up a tier?
  Loop budgets and circuit breakers. V1's loop detection and 10 minute stuck timeout are the
  baseline to beat.
- **Fast path.** Trivial tasks should skip stages. Cheap triage for deciding a task needs no
  recon and no architecture.
- **Naming in the domain model.** Does the military framing live in the data model and code,
  or only in the console? Given that the framing is load-bearing for the project's identity
  and that Rust enums make domain naming very sticky, decide deliberately and write the ADR.

---

## 11. Phase 1 research workstreams

Each ends with a written finding. Do not merge them.

### 11.0 Premises this section was written on that Phase 0 changed

**Added 2026-08-07, after Phase 0 and the verification pass.** Six workstreams were scoped against
facts that are no longer true. This is the Phase 0 → Phase 1 handoff: read it before W-anything.
Sources are `prestudy/inheritance-map.md`, `prestudy/questions.md` and `prestudy/verification.md`.

| W | The premise below assumes | What is actually true | Consequence |
|---|---|---|---|
| **W1** | RAM headroom "is what actually determines concurrency"; the card runs an expert-offload setup | The crowned config is **fully VRAM-resident, zero offload**. `--cpu-moe` measured 1.16x, verdict "don't use"; "residency is ~90% of the win". This is now **code-sourced**: `hw.rs:103-109` ships the string *"fully VRAM-resident in 13.6 GB, zero RAM spill"* to every user | The binding constraint is **VRAM + KV cache**, not system RAM. Reframe from "survive offload into 32 GB" to "stay resident in 16 GB". Different question, different answer |
| **W1** | Model choice is settled and Q56 ranks candidates | Q56 crowned `gemma-4-26b-a4b-qat` (median 55/56) over `qwen3.6-35b-a3b-mtp` (48-52). **David's ruling: gemma wins single-shot and falls apart on agentic multi-file context; qwen stays the foundation brain.** The corpus agrees about its own limits — every fixture is small, ctx 32768 is never stressed, and the crown rule discards a measured **3.4x** wall-clock gap | **Never cite the Q56 score column as an agentic ranking.** W1 evaluates candidates on multi-file work *at context pressure*. The base choice stands; the instrument that would defend it cannot see the axis that decides it |
| **W1, W2** | `hw.rs` already reports peak RAM per configuration | It does not. 208 lines, `nvidia-smi` VRAM only — **no temperature probe, no system-RAM probe**, and it reads *installed* VRAM, never *peak* anything | "Report a hard limit, not a tuning suggestion" has **no existing implementation**. New work, now a REWRITE row |
| **W2** | The Rust↔llama.cpp boundary is the central open question | **Answered.** HTTP, two dialects (Ollama-native + OpenAI-compat), no FFI, proven across 131 configs. Re-verified live 2026-08-07: `--doctor` reaches LM Studio, `/v1/models` HTTP 200 | W2 shrinks to a confirmation run plus the parts that *are* open: concurrency under residency, prefix caching, constrained decoding, swap cost, shared-server-or-not |
| **W4** | ABCC's Postgres holds "months" of per-tool-call timing, token and cost data | **9 days**, and `token`/`cost`/`model_used` were never written (0% populated). One finding survives: a 10.5% tool-call malformation rate. `complexity_reasoning` is 18% populated; 137 of 182 scored tasks carry the default 5.0 | **Delete the data-mining half of W4.** It is done and it is empty. The "highest-evidence work available" is not there |
| **W4** | The escalation ladder runs through Haiku | Haiku was **never** an execution tier. The real ladder is C1-C6 local 16K, C7-C9 remote-or-local 32K, C10 Sonnet — confirmed at `taskRouter.ts:382` | W4's baseline is wrong in the text below. Start from the real ladder |
| **W6** | Gate independence in single player is an open question, and BCF's numbers are a calibration baseline | **Measured.** StealthForge ran an independent reviewer over 34 missions: median **+3.65** points of self-scoring inflation, **0 of 34** where the reviewer scored higher. Separately: BCF's verifier — the 60%-weighted deterministic half of the gate — does not parse any language, docks Python ~2.5 points on every platform, and on Windows scores a correct and a syntactically broken Python file identically at 5.80 | "Does it matter" is closed; **implementation** is open. And BCF's all-local 7.5 average was produced by a miscalibrated instrument — **the verifier must be fixed before the thresholds are recalibrated**, or W6 tunes a number against a broken measurement |
| **W8** | Q56 is the starting corpus and an eval harness question is open | Q56 exists, has 56 tasks, per-task shell verifiers, no LLM judge — but it is **not on Claudette's `main`**, only on unmerged `battery/q50-quality-corpus`. `main` carries a different, older A-K battery, and `hw.rs:108` cites *that* one. They are separate instruments. Also unknown to this brief: ABCC ships a **100-task suite with 7 recorded runs** across 10 categories, closer to 2.0's target workload than the 40-task set | W8 does not start from zero and does not start from Q56 alone. Start from the 100-task suite, and **the frozen core stays frozen** — C8-C9 and anything new land as a K-series-style extension |
| **W8** | Q56's shape is representative | Every Q56 task is one `claudette "<prompt>"` invocation against a small fixture, and ctx 32768 is never stressed — while David's **live daily driver runs `CLAUDETTE_NUM_CTX=61440`** | The evaluation gap is wider than "Q56 is one-shot". The eval never exceeds 32k; the tool runs at 60k. W8's first job is a corpus that can see agentic multi-file work under context pressure |

**One thing this table does not change:** the base model, Rust, and llama.cpp decisions stay
closed per §15. Nothing above is new evidence against them.

**Second verification pass, 2026-08-07 evening.** ABCC's orchestration and persistence rows were
traced and their test suites run (`verification.md` §3.4). **No premise in the table above is
overturned.** Three are sharpened, and one workstream gains a job it did not have:

- **W4's dead data-mining half now has a mechanism.** The token, cost and model columns were not
  merely unwritten — they are **unreachable**. The producer sends them, the API validates them, and
  `ExecutionLogService.createLog` drops them by writing an explicit field list that omits all three;
  TypeScript misses it because excess-property checking does not apply to spread properties. The
  same dead gate silently disables `budgetService.recordUsage`, `costAggregator`, and the
  `TokenBurnLog` console panel. **Consequence for W4:** running ABCC longer would never have
  produced this data, so there is nothing to recover and no reason to revisit the decision to delete
  that half. **Consequence for W8:** cost-per-task has never been measurable in this family, so it
  is new instrumentation, not a ported metric.
- **W5 inherits a console panel with zero observed behaviour.** `TokenBurnLog`'s real-data list is
  structurally always empty; its only non-empty state is an opt-in demo fed by `Math.random()`. The
  layout is proven, the data path never ran. Treat "ABCC already has this surface" as a claim about
  *design*, not about *behaviour under load*.

**Third pass, 2026-08-07 late evening: ABCC's UI was run for the first time.** Vite dev server plus
headless Chrome over the DevTools Protocol, no backend, per David's ruling. Full detail in
`verification.md` §3.5. **This changes a premise in W5's favour, and corrects one this brief
inherited from the map:**

- **The frame-budget question is answered and the answer is good.** `questions.md` §4 item 7 asked
  whether the console holds frame budget at 2.0's event volume. Measured on the real DOM shape:
  idle sprites are **free up to about 100 entities** (indistinguishable from an empty page), the
  cliff is between 100 and 400, and 1,000 costs 48.6 ms a frame. **At any plausible 2.0 fleet size
  the existing technique needs no canvas and no WebGL.** W5 does not have to solve a rendering
  problem; it has to make design choices. One specific fix carries over: `filter: blur()` on firing
  agents doubles frame cost, so pre-blur the glow and animate opacity instead.
- **The renderer is not what the map said, and the correction is mine.** It is
  absolutely-positioned raster sprites over a pre-rendered background image, not SVG polygons on a
  17x17 tile board, and `isoCubeFaces` is called by nothing. **ABCC's isometric identity is
  art-driven, not engine-driven** - six painted battlefield JPEGs and 35 MB of sprite art carry the
  look. That reframes what W5 is inheriting: the expensive, irreplaceable asset is the **art**, in
  the same way the 96 voice lines are.
- **The console is a live view, not a record.** A 500-row ring buffer in the store, 50 rows visible,
  200 recovered on reconnect, while Postgres holds everything. **2.0's replay requirement needs a
  paged read path that ABCC never built**, so put it in W5's scope explicitly rather than assuming
  the panel ports.
- **A tension Q8 creates that Phase 0 had not recorded.** ABCC's theme system is a 28-line
  **vocabulary** map - `taskQueue: 'Bounty Board'`, `agents: 'Strike Team'` - with a neutral
  `classic` theme as the off-switch. Q8 puts the RTS framing into the Rust domain model, where an
  enum variant cannot be renamed by a theme file. **W5 must decide what the off-switch means now**:
  labels-only translation over fixed enums, or a neutral theme that is only cosmetic. Q8 stands;
  this is a design consequence of it.
- **What is still open in §8:** `audioManager.ts`'s queueing, and **memory** under real event
  volume. 34.3 MB of animated GIF cost no measurable frame time, but decode memory was outside what
  this harness could see, and there are two OOM-fix comments in the UI source whose cause this pass
  did not establish. That one needs the stack up.
- **W3 gains the durability work as a first-class item, not a port.** ABCC's task lifecycle is
  eleven states held as **untyped strings** — no status union type anywhere in the package, ≥48
  bare literal sites for `Task` alone — with no state machine; file locks are
  durable in Postgres but resource-pool slots are a process-local `Map` with **no boot
  reconciliation**; and the stuck-task watchdog only looks at `in_progress`, so a task hung in
  `assigned` or `needs_human` holds its agent, slot and locks until a human presses reset. Its clock
  is time-since-assignment, not time-since-progress, and no liveness field exists to fix that with.
  **This is where Q8's "RTS framing into the Rust domain model" earns its cost:** the vocabulary
  decision and the durability fix are the same piece of work, and a typed enum with typed
  transitions makes that whole class of hang unrepresentable. See §14 item 4.

### W1 - Model tiering around the base agent

The base agent is decided. This workstream is not an open survey; it is about what surrounds
Qwen 3.6 35B-A3B.

- Validate the base choice against current alternatives, briefly, and record the date. If
  something has displaced it since, say so plainly rather than defending a settled decision.
- What partners it in each tier: a small fast model for triage and recon, something for
  adversarial gating that is not the builder, and which frontier models are worth calling.
- Measure prefill and decode throughput for each candidate on this hardware, plus quality
  degradation per quantization level, plus ~~**RAM headroom remaining**, which is what actually
  determines concurrency~~ → **VRAM headroom and KV-cache growth remaining**, which is what
  actually determines concurrency on a fully-resident config (see 11.0). Report peak VRAM *and*
  peak system RAM as a hard limit — **nothing in the family measures either today**, so budget
  building the probe as part of this workstream.
- **Quantizer lineage is a first-class variable**, not a footnote: byteshape ShapeLearn at
  3.06 bpw tied unsloth's 4-bit on quality using 4.1 GB less. On a residency-bound config that is
  a bigger lever than model choice, and this brief did not mention it.
- Evaluate on **agentic multi-file work under context pressure**, not on Q56's score column.
  Q56 is single-shot against small fixtures and never stresses 32k; the daily driver runs at 60k.
- Tool calling and structured output reliability per candidate. More important than raw
  coding benchmark scores for an agentic system, and the specific thing V1's 7B failed at.
  Compare against what Claudette already achieves.
- Effective versus advertised context window, using independent long-context evaluations.
- Licensing, for a public MIT project that may ship or auto-pull model weights.
- Do not re-litigate NVFP4, already assessed as prefill-only benefit and wrong for an
  expert-offload setup on this card, unless there is new evidence.

Deliverable: `research/W1-models.md` with a tier table, plus "if you only have 8GB" and "if
you have 24GB or more" variants, since users are not on this exact box.

### W2 - Serving and the Rust to llama.cpp boundary

- **The central question:** how does the Rust orchestrator talk to llama.cpp? An
  OpenAI-compatible HTTP server, in-process bindings such as `llama-cpp-2`, or something
  else. Compare on latency, control over sampling and grammars, crash isolation, and how each
  behaves when a model needs swapping. Start from what Claudette already does and say whether
  it should change.
- **Shared server or not.** Claudette and ABCC 2.0 on one 32GB box. One resident model server
  serving both, two separate processes, or a hard rule that only one runs at a time. This
  decision has larger consequences than it appears.
- Concurrency: N parallel builder requests with batching, and the effect on per-request
  latency and on ~~system RAM under expert offload~~ → **VRAM and KV cache on a fully-resident
  model** (see 11.0 — nothing spills, so the bound is a different formula entirely). Find the
  point where the machine becomes unstable and report it as a hard limit, not a tuning
  suggestion.
- **Note the direct conflict with prefix caching below.** Claudette's `ToolRegistry` is *mutable
  per turn* — a changed `tools` array invalidates the prefix. Four builders sharing a system
  prompt is the best case for prefix caching and the worst case for on-demand tool groups. The
  measured workload is **27.8:1 prefill:decode** (117.6M prompt vs 4.2M output tokens over 3,150
  runs), so this is not a tuning detail; quantify both sides before choosing.
- KV cache reuse and prefix caching. The system prompt is largely identical across tasks in a
  factory pattern. Quantify the savings.
- Grammar or schema constrained decoding for guaranteed-parseable output. Potentially a
  bigger quality lever than model choice, and much easier to exploit from Rust than from a
  loosely typed stack.
- Model swap cost with mmap off, from NVMe over PCIe 3.0 x8.
- Keeping an OpenAI-compatible surface available so users can point ABCC 2.0 at whatever they
  already run.

Deliverable: `research/W2-serving.md` plus a reproducible benchmark and raw results.

### W3 - Orchestration core in Rust

The language is decided, so this is about structure, not language selection.

- **Start from the inheritance map.** What does BattleCommandForge already provide, and what
  does Claudette already provide? The default answer to "what orchestration framework" should
  be "the one we already proved twice", and any deviation needs an argument.
- Rust ecosystem survey with live verification: async runtime, HTTP and WebSocket layer,
  persistence, serialization, job and queue crates, and whatever agent-specific crates are
  actually maintained today. Check last commit dates.
- Durability: a task must survive a crash, a reboot and a model server hang. Compare a
  custom state machine over a durable queue against anything the ecosystem offers. Note that
  a durable state machine in Rust with a typed domain model is a very different proposition
  from V1's CrewAI-plus-Postgres arrangement.
- Human-in-the-loop pause and resume. The single most important capability in the list,
  because it is the one that turns the console from a viewer into a command center.
- The escalation pattern specifically: worker fails, verification fails, task gets re-scoped
  by a stronger model, retried, and the whole lineage stays traceable.
- Process topology: one binary, or a supervisor plus workers? What does that mean for
  sandboxing in W7 and for the multiplayer protocol in W10?

Deliverable: `research/W3-orchestration.md` with a recommendation and rejected options.

### W4 - Routing, escalation and the complexity model

~~**Start with data you already own.** ABCC's PostgreSQL holds months of real per-tool-call
timing, token and cost data, plus a 40-task scored corpus and a documented complexity model.
Mine all of it before proposing anything.~~

**Superseded 2026-08-07. The mining is done and the well is dry.** ABCC's Postgres holds **9
days**, not months; `token`, `cost` and `model_used` were never written (0% populated);
`complexity_reasoning` is 18% populated and 137 of 182 scored tasks carry the default complexity
of 5.0. It yielded exactly one usable finding — **10.5% of tool calls fell outside the tool
vocabulary** — which belongs to W6 more than W4. Do not schedule this. See
`prestudy/data-assets.md` §5.

**What W4 actually starts from:** the complexity model as *code*. `taskRouter.ts:105-239` is the
Campbell rule-based scorer (port the structure, fix the unanchored `text.includes()` matching —
`'api'` fires inside "rapid", `'add'` inside "address"); `complexityAssessor.ts:117-161` is the
asymmetric dual-assessment weighting; BCF's `router.rs:60` already has the typed `RoutingResult`
that fixes ABCC's Feb 2026 field collapse. The real escalation ladder is **C1-C6 local 16K,
C7-C9 remote-or-local 32K, C10 Sonnet** — Haiku was never a tier.

- How well did V1's dual assessment actually work? Judge the rule-based plus Haiku weighting
  retrospectively against downstream retry and escalation rates. The 88 percent local routing
  figure is a claim; verify it from the logs.
- Does the Campbell-derived complexity model survive into 2.0, and does it need rescaling now
  that the base agent is far stronger? A task that was C7 for a 7B may be C3 for a 35B-A3B.
  The whole scale may need recalibrating, and that is a finding worth having.
- Separate the two things V1 conflated: task difficulty and required context length. They are
  independent routing dimensions and V1 mapped both onto one 8K/16K/32K axis.
- Whether the Haiku semantic assessment pass is still worth paying for, or whether the local
  base agent can now score complexity itself for free.
- Confidence scoring on worker output: logprobs, self-critique, test results, static
  analysis. Which correlate with real quality? The existing logs may allow retrospective
  correlation, which is much cheaper than generating new data.
- Cost model: per-task tokens and wall-clock across tiers, so routing optimizes against a
  real objective.
- Escalation ladder and retry budgets, plus circuit breakers for the failure mode where
  escalation loops burn more than doing it right the first time.
- Given V1's collected training data, assess whether a fine-tuned router or worker is worth
  it. Expect no for now, and say why.

Deliverable: `research/W4-routing.md` plus an analysis notebook over the V1 database.

### W5 - The command center and the fun layer

The highest-stakes workstream, because this is where the project's identity lives.

- **Frontend architecture is the big open question.** A Rust backend can serve: the existing
  React and React Three Fiber console over WebSocket, a Tauri desktop app, a Ratatui TUI, or
  a TUI plus web hybrid. Each has real consequences for how much of V1's visual work survives,
  how it feels, and how a user installs it. Argue all four. Note that the owner has already
  researched Ratatui, Bubbletea and Textual, so start from those findings.
- What survives from V1's console verbatim, what gets ported, what gets rebuilt. Inventory
  the existing assets, including the 96 Bark voice lines, before designing new screens.
- What the console must show: live task DAG, per-agent state, queue depth, escalation events,
  token and cost accounting per task and per run, model server health, throughput over time.
  Most of this exists in V1 in some form.
- What the console must let the operator do, which is the genuinely new work: pause, resume,
  retry, re-route to another tier, kill, edit a task prompt, take over manually, replay a run.
- Prior art on agent observability and control: Langfuse, Arize Phoenix, OpenTelemetry GenAI
  semantic conventions, current agent-ops products. What they give for free at the tracing and
  storage layer. Note that no generic observability tool will ever give the RTS console, so a
  pure "adopt Langfuse" answer is wrong at the UI layer even if it is right underneath.
- Transport for live updates at higher 2.0 event volume: WebSocket versus SSE from a Rust
  backend.
- Storage: PostgreSQL versus SQLite. SQLite plus a single binary is a dramatically lower
  barrier for a public tool, and worth serious consideration against V1's Postgres dependency.
- **The fun research from section 7.** Developer tool ergonomics, flow, feedback latency, and
  what the literature and the good tools actually do. Ground this rather than guessing.

Deliverable: `research/W5-command-center.md` plus a component inventory marked new versus
inherited, plus a written position on what "fun" means here concretely enough to test.

### W6 - Verification, gates and the TDD pipeline

- **Start from BattleCommandForge's 9-stage pipeline.** Document what it actually does, how
  the complexity-scaled quality gates score, and what carries over. This is the single most
  reusable asset across the three repos.
- Automated verification is the biggest lever on cheap-model output quality: type checks,
  linters, unit test generation, property-based testing, static analysis, sandboxed execution.
  Quantify the headroom over V1's syntax-error auto-retry plus periodic frontier review.
- BCF reportedly outputs Python only. 2.0 targets more languages. What in the pipeline is
  language-specific and what generalizes? This is a real scoping question.
- Git worktrees or per-task isolation for parallel work. Compare overhead, and check RAM cost
  against the 32GB ceiling.
- Verifying documentation and review output where there is no test to run. LLM-as-judge
  reliability and its known failure modes.
- **Honest failure reporting**, which V1 got badly wrong when an agent claimed two passing
  tests on a run that executed zero. Rust's error handling makes it possible to do this
  properly. Design for it explicitly.

Deliverable: `research/W6-verification.md`.

### W7 - Security and sandboxing

- Executing model-generated code locally: minimum viable isolation and its performance cost.
  V1 relied on Docker, which is a starting point but not a boundary against hostile code.
  What are the options for a single Rust binary that is not shipping a container runtime?
- Prompt injection through the codebase itself. A worker reading a file containing hostile
  instructions is a real threat once agents have tool access. Current mitigations.
- Secrets handling: credentials without embedding them in prompts and traces. Traces are
  stored and displayed by the console, so a leaked secret is persisted and rendered.
- Supply chain risk on dependencies and on model weights pulled at first run. `cargo audit`
  and friends as part of CI.
- Public-project angle: blast radius when a user points this at a repo they care about, and
  what the README has to warn them about.

Deliverable: `research/W7-security.md` with a threat model table.

### W8 - Evaluation harness

The workstream that makes everything else measurable. Do not defer it.

> **Approach decided by David, 2026-08-08, before W8 started.** Build a **new harness that treats
> ABCC's 100-task suite and Claudette's battery as importable corpora**, rather than extending
> ABCC's suite in place. See §14 item 1 for the reasoning and the accepted cost. The corpus
> inventory below still applies; what changed is that the harness is not any one corpus's
> successor.
>
> **Stand-in subject decided by David, 2026-08-08: Claudette.** The harness needs something to drive
> before 2.0 exists, and Claudette is the engine 2.0 copies, so its numbers are a baseline rather
> than a proxy - the same harness produces the before and the after, which is what makes "is 2.0
> better" answerable at all.

**What the stand-in can and cannot baseline — verified against the code at `fc1ea22`, 2026-08-08.**
This determines the metric set, so it was checked rather than assumed:

| Operator-control axis | In Claudette today | Harness mechanics |
|---|---|---|
| **Intervene / deny** | ✅ the `[y/N]` permission gate | Scriptable over a **pipe** |
| **Redirect** | ✅ **already implemented** — the gate prompt is literally `Allow? [y/N · or type a redirect]`; any non-y/n text denies the tool *and* forwards the instruction to the model as an error `tool_result` (`run/cli_prompter.rs:84`, `gate_line_decision` `:118-135`) | Scriptable over a pipe; `gate_line_decision` is pure and already unit-tested without a TTY |
| **Undo / rollback** | ✅ `/undo` plus `transcript::undo_last()` / `undo_last_turn()`, trash-backed | REPL slash command, one of **15** |
| **Resume** | ✅ `--resume` / `-r`, both single-shot and REPL (`main.rs:110`, `:696`) | Process-level flag |
| **Pause mid-run** | ❌ **does not exist.** The gate is the only synchronous interception point, so it pauses only when a tool happens to need permission. No SIGINT handler for a running turn; `ctrl_c` only cancels an input line (`run/line_editor.rs:663`) | Nothing to drive |
| **Take-over** | ~ partial — deny-plus-redirect is take-over at *tool* granularity; there is no "give me the wheel" mode | As redirect |

Three consequences for the harness design:

1. **No PTY needed, and the harness must drive the REPL rather than one-shot.** `cli_prompter.rs:89-96`
   documents the gate's fall-through: the single-keypress path is a TTY optimisation and it "falls
   through to the line reader below when stdin isn't a TTY (piped / scripted / spawned agent)".
   **Corrected and extended 2026-08-08 (see `research/W8-corpus-format.md` F1-F6, all measured).**
   That citation covers the gate but not the REPL's own input loop, which is the part that would have
   forced a PTY; `line_editor.rs:337,369-376` degrades to a plain `read_line` when stdin/stderr is not
   a terminal, so the conclusion stands on the right evidence. **But one-shot has no prompter at all**
   (`run.rs:186` passes `None`), which is why the Q56 battery *must* set `CLAUDETTE_AUTO_APPROVE=1` -
   without it a one-shot run cannot edit a file. Only the REPL constructs a `CliPrompter`
   (`repl.rs:56`). A spike drove it end to end over pipes: gate observed on stderr, redirect injected,
   file left unchanged, model obeyed the instruction.
2. **The permission configuration is part of the corpus definition, not the runner.** Interventions
   can only be measured if something actually prompts, and what prompts depends on the mode and the
   per-tool tier. So each task must pin its permission configuration explicitly. ⚠ **And the mode to
   avoid is `Prompt`:** `PermissionMode { ReadOnly, WorkspaceWrite, DangerFullAccess, Prompt, Allow }`
   still derives `Ord` at `fc1ea22`, so `Prompt` outranks `DangerFullAccess` and a `Prompt` session
   auto-approves everything (map §0 item 3). Pin the tier deliberately and assert that the gate fired.
3. **Pause is measured by its absence, and that is a result worth having.** Three of the four axes
   get a real baseline number; pause gets a documented "n/a - not implemented in the subject". Design
   the metric so `n/a` is a first-class value rather than a zero, because that column is precisely
   where 2.0's differentiator has to show up.
4. **Two metric findings that only appeared by running it**, both in `research/W8-corpus-format.md`.
   **Cost per task is reachable after all:** every REPL turn prints `turn iter=N in=X out=Y` to stderr
   from `summary.usage` (`repl.rs:205-214`), so the metric that is unreachable everywhere else in this
   family (ABCC's token columns are 0/5,977 populated) comes free on the stand-in, with no patch. And
   **"time to first visible output" cannot be defined on stdout alone:** model text goes to stdout
   (`api.rs:36-52`) while the gate preview goes to stderr (`cli_prompter.rs:52-84`), and in the spike
   the operator saw the gate at 25.9 s but the first stdout byte at 31.6 s. Define it over both
   streams or it overstates felt latency by the whole tool-call phase.

- ~~Start from what exists: ABCC's 40-task scored corpus and Claudette's eval loop. Characterize
  both, then decide what the 2.0 harness inherits.~~ → **Start from ABCC's 100-task suite, not the
  40** (§11.0), characterize both it and Claudette's battery, and **import** rather than inherit.
- The V1 corpus is calibrated for a 7B. Re-run it against the 35B-A3B base agent first, to see
  how much of it is now trivially passed. Expect significant ceiling effects, and expand the
  corpus upward accordingly.
- Build the task set from the workload 2.0 is actually for. See open question 2 in section 17.
  Target 30 to 50 tasks with checkable outcomes, on top of the inherited corpus.
- Metrics: pass rate, escalation rate, cost per completed task, wall-clock per task, human
  intervention rate, peak system RAM, and **time to first visible output**, which is the
  latency the operator actually feels.
- **Include the fun criterion.** Whether David reaches for this over Claude Code on real work,
  and whether he keeps it open. Track it as a log, not a vibe.
- Survey existing agentic coding benchmarks and say plainly which are relevant to this
  workload and which are not.

Deliverable: `research/W8-evaluation.md` plus a runnable harness skeleton in Rust.

### W9 - Prior art scan

- Open-source projects doing tiered local and frontier agent orchestration, especially any in
  Rust. Read their code. What they got right, where they stalled.
- Anything that makes part of this redundant. "This already exists, use it" is a valid and
  valuable finding. The console and the local-first stance are the differentiated parts; the
  orchestration core may well not be.

Runs continuously in the background of the other workstreams.

Deliverable: `research/W9-prior-art.md`.

### W10 - Fleet topology and game modes

Turns section 9 into an implementable design. Cross-reference W2 and W3 rather than
duplicating.

- One provider abstraction covering a local model server, a cloud API and a remote rig, or a
  reasoned argument that one of them does not fit. In Rust, this is a trait design question
  and worth getting right early because it is expensive to change later.
- Runtime mode transitions: can a run start in co-op and finish in single player when the
  budget runs out or the network drops?
- The egress policy engine for co-op, including redaction and audit trail.
- The rig registration, health and scheduling protocol, proven against the laptop over
  Tailscale.

Deliverable: `research/W10-fleet.md` plus the mode capability matrix.

### W11 - Stage pipeline and unit roles

Turns section 10 into a spec. Overlaps W3, W4 and W6.

- **Reconcile the three taxonomies:** V1's Coder/QA/CTO, BCF's nine stages, and the four-stage
  model in section 10. Produce one, and justify it.
- Stage-to-tier mapping backed by W1 and W2 measurements.
- Handoff artifact schemas as Rust types, not conventions.
- Gate independence findings and how they survive single player mode.
- Loop budgets and circuit breakers per stage, benchmarked against V1's existing behaviour.

Deliverable: `research/W11-stages.md` plus the artifact schemas.

### W12 - Repo strategy and succession

ABCC 2.0 is a Rust rewrite, not an upgrade. Existing users cannot `docker compose up` their
way into it. Decide how that is handled with some care, because the community is real and
small kindnesses matter.

- New repo, new major version of the existing repo, or a `2.x` branch? This gates everything
  else here.
- Naming. Is it still Agent Battle Command Center? The Battle family naming across ABCC and
  BattleCommandForge suggests a deliberate choice is available.
- What happens to V1: frozen with a clear notice, maintained for a period, or archived?
- Migration of task history and collected training data, if any of it is worth carrying.
- The 8 open good-first-issues and any in-flight community PRs. Do not leave contributors
  hanging without a word.
- Release communication: a "why we rewrote it in Rust" post is a genuinely good story and
  worth writing well rather than as an afterthought.
- Licensing: MIT throughout, and whether any inherited BCF code has different terms given it
  was heading toward a paid model.

Deliverable: `research/W12-repo-strategy.md` plus a draft announcement outline.

### W13 - Co-development ergonomics and self-hosting

The repo will be built by Claude Code and Claudette together, and eventually by ABCC 2.0
itself. Research what that actually requires.

- Repo conventions that make agents effective: CLAUDE.md structure, directory layout, test
  commands, hooks, subagents, and current Claude Code recommendations. Rust specifics:
  `cargo check` speed, workspace layout, and how long a full test run takes, because agent
  loop latency is bounded by it.
- CI an agent can read and act on. What signals should fail a run.
- Guardrails against silent architectural drift: ADR files, changelog discipline, review gates
  before merge.
- How agent-authored commits and human community PRs coexist without clobbering each other.
- Failure modes people report when agents maintain repos long term, and what they did.
- **The self-hosting milestone.** At what point can ABCC 2.0 take a task on its own codebase
  and complete it end to end through its own pipeline? Define that milestone concretely. It is
  the most honest possible proof that the tool works.

Deliverable: `research/W13-codev.md` plus a proposed CLAUDE.md skeleton.

---

## 12. Co-development model

From Phase 3, Claude Code and Claudette build this together. Define the split in the Phase 2
plan, but the shape is roughly:

- **Claude Code:** architecture, design decisions, the hard reasoning, review, and any work
  that needs frontier-level judgment or broad live research.
- **Claudette:** local execution, the high-volume mechanical work, and the running dogfood.
  Every time Claudette handles a task well or badly, that is harness data for W8.
- **David:** the gate. Decisions, direction, taste, and the final word on whether it is fun.
- **ABCC 2.0 itself:** progressively takes over its own construction as it becomes capable.
  Track this transition explicitly, because the point at which the tool builds itself is the
  point at which it is real.

Note that this is also a research input, not just a process choice. A tool built by the
workflow it is designed to support gets its ergonomics tested continuously, which is worth
more than any amount of upfront design.

---

## 13. Output format

```
prestudy/                 # Phase 0
  abcc-v1-dossier.md
  claudette-dossier.md
  battlecommandforge-dossier.md
  data-assets.md
  inheritance-map.md
  questions.md

research/                 # Phase 1
  W1-models.md ... W13-codev.md
  SUMMARY.md              # 2 pages max, decisions and open questions only
  decisions/              # one ADR per architectural decision
  benchmarks/             # scripts + raw results, reproducible
  spikes/                 # throwaway code, each with a README saying what it proved
```

Every Phase 1 workstream file uses this structure:

```markdown
# Wn - Title
## Question
## Method
## Inherited              (what came from ABCC, Claudette or BCF, with file references)
## Findings               (each claim carries a source URL + retrieval date)
## Options compared       (table, scored against stated criteria)
## Recommendation
## Rejected alternatives and why
## Effect on fun          (how this choice makes the tool better or worse to use)
## Open questions
## Confidence: high | medium | low, and what would raise it
```

---

## 14. Sequencing

**Phase 0.** Repo study, in the order ABCC v1, then Claudette, then BattleCommandForge. ABCC
first because it holds the data assets and the design language. Claudette second because the
harness is the thing being ported. BCF last because by then you will know what to look for.
Then the inheritance map, then the corrections to this brief.

~~**Phase 1**, after the Phase 0 gate:~~

~~1. W1 and W2 first. Everything depends on what the hardware can actually do and how Rust talks
to llama.cpp. 2. W4's data-mining half runs in parallel, since it needs only the existing
database. 3. W8 early, gated on open question 2. 4. W3, W6 and W11 as a block. 5. W5 next, and
give it room. 6. W7, W12, W13 after the core shape is settled. 7. W10 late. 8. W9 runs
continuously.~~

**Resequenced 2026-08-07, after Phase 0 and the verification pass.**

The original order put W1 and W2 first because "everything depends on what the hardware can
actually do and how Rust talks to llama.cpp". Phase 0 found most of that already measured: the
Rust↔llama.cpp boundary is settled (HTTP, two dialects, live-verified), the base model is ruled,
the crowned config is fully VRAM-resident, and NVFP4/MXFP4 is closed. W1 and W2 shrink to a
confirmation run plus a short list of genuinely open questions. Meanwhile W4's "highest-evidence
work available" turned out to be 9 days of empty columns. **Leading with hardware would spend the
best weeks of the schedule re-confirming settled facts.**

**Phase 1**, after the Phase 0 gate:

**0. ~~David's six open decisions~~ — ANSWERED 2026-08-07. Nothing here blocks any more.** All of
§17 and `questions.md` §2 are closed. What the answers do to the sequence below:

- **W12 is unblocked** — new repo, keeps the name, dual MIT/Apache-2.0.
- **W3 is unblocked** — 2.0 copies Claudette's engine and both stay live, so the tokio decision is
  genuinely 2.0's to make. But **W3 must settle the RTS vocabulary before it ports a single type**:
  the framing goes *into* the domain model, which deliberately reverses Claudette's functional
  naming principle, and Rust enums make it sticky. W3, W5 and W11 all inherit that choice.
- **W4 shrinks substantially** — spend is effectively zero. The escalation ladder is local, C10
  becomes a manual act rather than a routed tier, and W4 optimises latency and rework instead of
  allocating a budget. Combined with the dead data-mining half, W4 is now a small workstream.
- **W6 grows** — the independence check ships **always on**, so a second review pass per artifact
  is a design constraint, not an option. With zero spend on one GPU, "what plays the reviewer" is
  hard-constrained: same model with no history (cheapest, most correlated with what it is checking)
  or a second local model (less correlated, costs a swap or co-residency alongside 13.6 GB).
  **That interacts directly with W2's residency and concurrency work.**
- **W7 gets easier** — with cloud escalation manual and rare, §3.6 item 20's structural air-gap
  (`default = []`) can largely survive rather than degrading to a feature flag.

1. **W8 first, and give it the room W5 was promised.** This is the change with the most
   consequence. Phase 0 assumed W8 was mostly done because Q56 exists; it is not. Q56 is
   single-shot against small fixtures, never stresses 32k while the daily driver runs at 60k,
   lives only on an unmerged branch, and measures none of the operator-control axis that is 2.0's
   actual differentiator. Every later claim about whether 2.0 is *better* is measured by this
   harness. Building it late means grading the whole project with the wrong instrument. Start from
   ABCC's 100-task suite, keep the frozen core frozen, add the K-series extension.

   **Approach decided 2026-08-08: a new harness that imports both corpora, not an extension of
   either.** The alternative considered and rejected was extending ABCC's 100-task suite in place,
   which is faster and inherits its category structure and 7 baseline runs. It was rejected because
   **the axis 2.0 differentiates on is unmeasurable inside a corpus whose unit is one invocation
   against a fixture.** Both existing instruments share that shape: every Q56 task is a single
   `claudette "<prompt>"` call, and ABCC's suite is a one-shot scored corpus. Operator control -
   pause, redirect, take-over, replay - needs a harness whose unit of measurement is a **session
   with interventions in it**, and time-to-first-visible-output needs one that samples *during* a
   run rather than scoring after it. Neither is a metric you can bolt onto a pass/fail row.

   **Accepted costs, stated so they are not re-litigated as surprises:** it is slower to first
   number than extending in place; the 7 recorded ABCC runs and the 131 Claudette model runs become
   *imported baselines* whose comparability has to be argued rather than assumed; and W8 now owns a
   corpus format plus an importer, which is real engineering inside a research phase. **The frozen
   core stays frozen regardless** - importing is exactly what makes that possible, since neither
   donor corpus gets edited.

2. **W1 and W2 in parallel, scoped down.** Confirmation run plus the open parts only: concurrency
   and KV-cache growth under full residency, prefix caching against the 27.8:1 prefill:decode
   workload (and its conflict with a mutable tool registry), constrained decoding, model-swap cost,
   shared-server-or-not, quantizer lineage. Build the peak VRAM/RAM probe here — nothing in the
   family has one.

3. **W5 next, and it keeps its extra room.** The residency reframing freed the schedule; spend it
   here, as the brief itself argues. It carries the project's identity and the success test.
   Phase 0 narrowed the starting point usefully: `isoProjection.ts` is a good foundation (181
   lines of dependency-free 2:1 projection math), ~~but the renderer around it is SVG-per-sprite on
   a 17×17 board and the frame-budget question is still open~~. W5 also owns the four
   operator-control questions nothing in the family answers.

   **Updated after the UI was run, 2026-08-07 (see 11.0).** The renderer is raster sprites over
   painted backdrops, and **the frame-budget question is closed and favourable** - free to ~100
   entities, no canvas or WebGL needed at 2.0's scale. So W5's extra room is no longer insurance
   against a rendering risk; **spend it on the four operator-control questions and on replay**,
   which is where the real gap is. Three concrete items now in scope that were not before: a paged
   read path for replay (the console is a 500-row ring buffer over a database that has everything),
   deciding what the theme off-switch means once Q8 puts the vocabulary in the type system, and
   separating the audio and no-dead-air logic from the WebSocket transport, where ABCC left it.
   One item leaves scope: choosing a rendering technology.

4. **W3, W6 and W11 as a block**, unchanged — they interlock and the stage pipeline is the shape
   the orchestrator must express. Two entry conditions: W3 needs the Claudette code-sharing answer
   from item 0; and **W6 must fix BCF's verifier before recalibrating any threshold**, because the
   all-local 7.5 average it would calibrate against was produced by an instrument that scores a
   correct and a broken Python file identically. W6 also inherits a closed question — gate
   independence *matters*, measured at +3.65 median inflation over 34 missions — and an open one:
   who plays the reviewer, whether it always runs, and whether `critic_inflation` ships as a
   console metric.

   **Added after the second verification pass:** W3's first deliverable is the **typed lifecycle**,
   before any durability mechanism is chosen. ABCC's four services are the right set of concerns and
   none of them is the hard part — the hard part is that the lifecycle exists only as string
   literals, which is how a task hung in `assigned` came to be invisible to both the assigner and
   the watchdog. Three specific things to carry as requirements rather than as ports: every
   non-terminal state must be recoverable (not just the one the watchdog currently queries); the
   liveness clock must be **time since last progress**, not time since assignment, which means the
   domain model needs a heartbeat ABCC never had; and in-memory admission state must be
   **reconciled at startup** against the durable store, which ABCC never does. Sequencing note:
   settle the Q8 vocabulary in the same step — the enum is the fix, so naming it twice is waste.

5. **W4 after W8**, and without its data-mining half. It needs an eval to calibrate routing
   against and a spend ceiling to optimize toward; it has neither until items 0 and 1 land.

6. **W7, W12, W13** after the core shape is settled. ~~W12 stays blocked on item 0 until Q3 and Q12
   are answered — it cannot start at all without them.~~ **Both were answered 2026-08-07** (new
   repo keeping the ABCC name; dual MIT/Apache-2.0), so W12 is unblocked and this item carries no
   entry condition. Note that §17's body still marks items 3, 7 and 8 "STILL OPEN" — the banner at
   the top of §17 supersedes them.

7. **W10 late**, unchanged. Single player has to be solid before co-op means anything, and co-op
   has to be solid before multiplayer is more than a distributed way to fail.

8. **W9 runs continuously**, and Phase 0 raised its value: "this already exists, use it" is now
   the likely finding for several workstreams, which makes the prior-art scan the highest-value
   pure-research item left.

**Phase 2** starts only when SUMMARY.md exists and David has signed off.

---

## 15. Out of scope

- Any ABCC 2.0 implementation code during Phases 0 and 1. Spikes and benchmark harnesses
  only, clearly marked as throwaway.
- Migrating V1 workloads. Planning the succession is in scope, in W12. Doing it is not.
- Packaging, distribution or commercialization.
- UI polish. Component inventories, wireframes and a written design position only.
- Claudette's own feature roadmap. Only the shared-infrastructure and harness-donation
  questions are in scope.
- Reopening the Rust, base model or llama.cpp decisions without strong new evidence.

---

## 16. Acceptance criteria

**Phase 0 is done when:**

- Three repo dossiers exist and are detailed enough that someone could rebuild each project's
  architecture from them.
- The data assets are extracted and characterized, including how many usable task runs are
  actually in the V1 database.
- The inheritance map exists, with a verdict and a reason for every component.
- Section 3 of this brief has been corrected against the code, and the corrections are listed.
- No architecture has been proposed.

**Phase 1 is done when:**

- Every workstream file exists and follows the required structure.
- Every model, crate, tool, price and benchmark claim carries a source URL and retrieval date.
- Benchmarks were run on the desktop with raw results committed, and peak system RAM is
  reported for every configuration. Laptop benchmarks are required only for the multiplayer
  protocol work.
- SUMMARY.md states the recommended architecture in under two pages, with the three highest
  risks and what would falsify the recommendation.
- The evaluation harness runs end to end and produces a baseline, including a re-run of the
  V1 40-task corpus against the new base agent.
- The mode capability matrix and the stage artifact schemas exist and agree with W3.
- W5 contains a defensible written position on what makes this tool fun, specific enough that
  a later design choice can be judged against it.
- W12 states what happens to V1 and its users.

**The project is done when** a working developer picks this up for real work and enjoys it,
and when ABCC 2.0 can take a task on its own repository and complete it through its own
pipeline. Everything else is a milestone on the way.

---

## 17. Open questions for David

Answer during or shortly after Phase 0. These change the shape of Phase 1.
**Answers given 2026-08-07 are recorded inline.**

> **Second round, 2026-08-07 — section 17 is now fully answered, and so is `questions.md` §2.**
> Full consequences in `prestudy/questions.md` §2.
>
> - **Q3 repo and naming:** new repo, **keeps the name "Agent Battle Command Center"**. *W12 unblocked.*
> - **Q12 licensing:** **MIT OR Apache-2.0 dual**, matching Claudette. *W12 unblocked.*
> - **Claudette engine sharing:** **copy into 2.0; both stay live.** *W3 unblocked* — free to reopen the tokio decision without negotiating against a shipping product. Accepted cost: fixes stop propagating, the test suite splits.
> - **Q7 frontier spend:** **effectively zero, local only**; cloud escalation is manual and rare. **W4 shrinks substantially** — the ladder is local, C10-Sonnet is a manual act rather than a routed tier, and W4 optimises latency and rework instead of allocating a budget. Also rescues the structural air-gap in §3.6 item 20.
> - **Q8 RTS framing:** **into the Rust domain model.** This *deliberately overrides* Claudette's `forge/types.rs` principle ("role naming is about what the model is doing, not which weights are loaded"). **The vocabulary must be settled before W3 ports any type** — Rust enums make it sticky, and W3, W5 and W11 all inherit it.
> - **Q10 existing V1 users:** **clean break, documented.** No migration code; W12 writes the succession story.
> - **Q11 `BMORE.md`:** a **real business document — take it out** of the public BCF repo. Action on David's repo; already DROP in the map.
> - **Independence check:** **always on.** W6 budgets a second review pass per artifact — and with spend at zero on one GPU, "what plays the reviewer" is now a hard-constrained W6 question, not a menu.

1. ~~**BattleCommandForge:** confirm what it actually is...~~
   **ANSWERED.** `github.com/mrdushidush/battle-command-forge`. Public, Apache-2.0, sole-authored
   with no outside contributors, so relicensing is available. A greenfield POC, never a daily
   driver. See the rewritten 3.3.
2. **Target workload.** ~~V1 demonstrated self-contained algorithm tasks...~~
   **ANSWERED: repository work plus legacy review plus general-purpose coding.** In David's
   words, "like aider and opencode but way more fun and engaging." W8 builds its task set
   against this. Note this is a **different workload from every existing corpus**: ABCC's 40
   tasks are self-contained algorithms, BCF's missions are greenfield generation, and only
   Q56's I-series (bigrepo) and J-series (git) touch real repository work. That gap is W8's
   first job.
3. ~~**Repo and naming.** New repo or new major version of ABCC? Still called Agent Battle
   Command Center? This gates W12 entirely. **STILL OPEN.**~~
   **ANSWERED 2026-08-07 (see the banner above): new repo, keeps the name.** W12 unblocked.
4. ~~**Claudette's relationship.**~~ ~~**PARTIALLY ANSWERED.**~~ **FULLY ANSWERED 2026-08-07.**
   The three checkouts are working roles (canonical, self-edit sandbox, Q56 runner). And the part
   that was still open - whether 2.0 and Claudette share code as a crate - is now closed:
   **2.0 copies the engine and both stay live.** No shared crate. W3 is free to reopen the tokio
   decision on its own merits; accepted cost is that fixes stop propagating and the 1,145-test
   suite splits in two.
5. ~~**Console shape.**~~ **ANSWERED: a full isometric web UI in the style of the original
   Command and Conquer** - what ABCC v1 gestured at, done properly. Not a TUI, not Tauri.
   W5 starts from ABCC's existing `components/isometric/` rather than from a blank page or
   from the React Three Fiber battlefield. BCF's and Claudette's Ratatui work drops to
   reference-only, except as a possible headless fallback.
6. ~~**Single player as primary.**~~ **ANSWERED: yes.** Local-only on 32GB RAM plus 16GB VRAM
   is the mode to design for. Cloud is a future convenience (renting an H100 if ever needed),
   not a design assumption. This reframes the priority order: co-op and multiplayer are
   later, and the single-player evaluation baseline is the one that matters.
7. ~~**Monthly frontier API spend ceiling** to optimize routing against. **STILL OPEN**, and
   lower priority now that single player is primary.~~
   **ANSWERED 2026-08-07 (see the banner above): effectively zero, local only.** Cloud escalation
   is manual and rare. There is no ceiling to optimize against, so W4 optimizes latency and rework
   instead.
8. **RTS framing depth.** Presentation layer only, or into the Rust domain model?
   ~~**STILL OPEN.**~~ **ANSWERED 2026-08-07 (see the banner above): into the Rust domain
   model.** Sharper than when written: Claudette's `forge/types.rs` already states a
   *functional* naming principle - "role naming is about what the model is doing, not about
   which weights are loaded" - which military naming now deliberately replaces. This is the one
   answer that creates work rather than removing it, and §14 item 4 gives it a first job: the
   lifecycle enum and the RTS vocabulary are the same decision.
9. ~~**The 32GB ceiling.**~~ **ANSWERED: fixed.** 32GB RAM plus 16GB VRAM, no second machine,
   no AM4 upgrade. But see the correction in 3.4: on the crowned configuration the model is
   fully VRAM-resident and system RAM is barely involved, so this ceiling may not be the
   binding constraint the brief assumes.
10. **Existing users.** Willing to ship a clean break with a good migration story, or does
    something have to keep working for the people already running V1? ~~**STILL OPEN.**~~
    **ANSWERED 2026-08-07: clean break, documented.** No migration code; W12 writes the
    succession story.

**Added by Phase 0** - see `prestudy/questions.md` section 2 for the full list:

11. **`BMORE.md`** is a full commercial product specification sitting in the public
    battle-command-forge repo. Demo mission input, or a real business document that should
    come out? **ANSWERED 2026-08-07: a real business document - take it out.** Action on
    David's repo; already DROP in the map.
12. **Licensing for 2.0.** MIT like ABCC, MIT-OR-Apache like Claudette, or Apache-2.0 like
    BCF? Sole authorship makes all three available. Gates W12 with question 3.
    **ANSWERED 2026-08-07: MIT OR Apache-2.0 dual**, matching Claudette, the largest donor.

**Section 17 status: every item is answered.** Items 1-12 above are individually marked; the
banner at the top of this section is the authoritative summary. Nothing in Phase 1 waits on
David.
