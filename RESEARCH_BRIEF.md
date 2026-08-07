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

### W1 - Model tiering around the base agent

The base agent is decided. This workstream is not an open survey; it is about what surrounds
Qwen 3.6 35B-A3B.

- Validate the base choice against current alternatives, briefly, and record the date. If
  something has displaced it since, say so plainly rather than defending a settled decision.
- What partners it in each tier: a small fast model for triage and recon, something for
  adversarial gating that is not the builder, and which frontier models are worth calling.
- Measure prefill and decode throughput for each candidate on this hardware, plus quality
  degradation per quantization level, plus **RAM headroom remaining**, which is what actually
  determines concurrency.
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
  latency and on system RAM under expert offload. Find the point where the machine becomes
  unstable and report it as a hard limit, not a tuning suggestion.
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

**Start with data you already own.** ABCC's PostgreSQL holds months of real per-tool-call
timing, token and cost data, plus a 40-task scored corpus and a documented complexity model.
Mine all of it before proposing anything.

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

- Start from what exists: ABCC's 40-task scored corpus and Claudette's eval loop. Characterize
  both, then decide what the 2.0 harness inherits.
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

**Phase 1**, after the Phase 0 gate:

1. W1 and W2 first. Everything depends on what the hardware can actually do and how Rust
   talks to llama.cpp.
2. W4's data-mining half runs in parallel, since it needs only the existing database. It is
   cheap and it is the highest-evidence work available.
3. W8 early, gated on open question 2. Without the harness the rest is opinion.
4. W3, W6 and W11 as a block. They interlock, and the stage pipeline is the shape the
   orchestrator must be able to express.
5. W5 next, and give it room. It is the identity of the project and it deserves more than a
   week.
6. W7, W12, W13 after the core shape is settled.
7. W10 late. Single player has to be solid before co-op means anything, and co-op has to be
   solid before multiplayer is more than a distributed way to fail.
8. W9 runs continuously throughout.

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

1. **BattleCommandForge:** confirm what it actually is, whether the description in 3.3 is
   close, whether it is public or private, and whether any of it is under terms that
   complicate an MIT release. Section 3.3 is the least reliable part of this document.
2. **Target workload.** V1 demonstrated self-contained algorithm tasks. Is 2.0 for real
   repository work such as refactors and bug fixes, for greenfield feature building, for
   legacy documentation and review, or general purpose? W8 cannot start without this and
   every tier mapping depends on it.
3. **Repo and naming.** New repo or new major version of ABCC? Still called Agent Battle
   Command Center? This gates W12 entirely.
4. **Claudette's relationship.** Shared crate, shared model server, or fully separate
   processes that never run simultaneously?
5. **Console shape.** Do you have an instinct on web console versus Tauri desktop app versus
   Ratatui TUI? Your taste here is worth more than any amount of research, and W5 should start
   from it rather than pretend to be neutral.
6. **Single player as primary.** With a 35B-A3B base agent, is local-only now the mode you
   actually intend to live in, with co-op as an occasional assist? That reframes the whole
   priority order.
7. **Monthly frontier API spend ceiling** to optimize routing against.
8. **RTS framing depth.** Presentation layer only, or into the Rust domain model? Rust enums
   make this stickier than it was in a loosely typed stack, so it is worth deciding before any
   code exists.
9. **The 32GB ceiling.** Fixed for the duration, or is the AM4 upgrade (Ryzen 7 5700X plus
   B550M, more RAM headroom, PCIe 4.0) on the table? A move to 64GB would materially change
   the concurrency findings, so it is worth knowing before benchmarking starts.
10. **Existing users.** Willing to ship a clean break with a good migration story, or does
    something have to keep working for the people already running V1?
