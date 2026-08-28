# W9 — Prior art scan

**Status: COMPLETE — sessions 8 and 9 of the 14-session landing budget, 2026-08-27/28.** **Line
budget: ≤ 500, landed at 500.** §13's ten sections once for the whole workstream. **Findings
F450–F463**; next free number is **F464**. Session 8 wrote the evidence; session 9 wrote the
per-workstream verdict table and the closing sections.

The two bullets from `RESEARCH_BRIEF.md:921-931`:

1. ▶ **Open-source projects doing tiered local and frontier agent orchestration, especially any in
   Rust. "Read their code." What they got right, where they stalled.** — F450–F454, F460–F463.
2. ▶ **Anything that makes part of this redundant.** *"'This already exists, use it' is a valid and
   valuable finding."* — F455–F459, F462, and the verdict table below.

**What this workstream changes for anyone reading only one thing.** The brief's own sentence —
*"the console and the local-first stance are the differentiated parts; the orchestration core may
well not be"* — is wrong in **all three** of its claims, and the correction is measured, not
argued. The orchestration core is not differentiated (correct, but far more so than the brief
implies: **217 harness/orchestration projects in one curated list**). The console is not
differentiated (**68 session managers**, the top four at 53.7k–32.3k stars). And **local-first is
not differentiated either — 26 of the list's entries claim it by name.** Both of the brief's
nominated differentiators are crowded. The one thing that is genuinely unoccupied is the thing the
brief treats as decoration: **across all 340 entries, the words *game*, *battle*, *RTS*,
*isometric*, *sprite*, *XP*, *leaderboard* and *arcade* appear zero times.** The differentiator is
the game framing, and nothing else is.

Second: the routing core has a real "use it" candidate that turns out to be a **"read it"** —
`NVIDIA-NeMo/Switchyard`, Rust, Apache-2.0, 2,517 stars, and **self-declared pre-alpha**. Its
escalation judge is the single most valuable artefact this scan found, and its objective function
is the one axis ABCC 2.0 has already zeroed.

---

## Question

**(a)** Does something already exist that makes part of ABCC 2.0 redundant, and if so which part —
asked per workstream, because "use it" is only actionable at that granularity. **(b)** For the
routing and orchestration core specifically, which the brief singles out as probably *not*
differentiated: what has been built, does it work, and can 2.0 adopt it under MIT OR Apache-2.0?
**(c)** Is the console genuinely the differentiated half, as the brief asserts — and if not, what
is? **(d)** What did the projects that stalled stall *on*, since that is the cheapest available
warning about ABCC 2.0's own next twelve months.

## Method

Repo-first, per the standing rule and the brief's own *"read their code"*. Every candidate was
resolved to a GitHub repository and its metadata read from `api.github.com` — `stargazers_count`,
`license.spdx_id`, `pushed_at`, `archived` — never from a blog. Source code was pulled with `curl`
to `raw.githubusercontent.com` and read locally: **2,892 lines of Switchyard's routing algorithms**
(`escalation.rs`, `util/escalation.rs`, `util/llm_judge.rs`, `stage.rs`, `advisor_gate.rs`) plus
its judge prompt and JSON schema. Retrieval date for every claim below: **2026-08-27**.

▶ **Citation rule (§16), added by acceptance sweep A 2026-08-28.** Every project here is named
as `org/repo` at least once, and **that string is the citation**: the page is
`https://github.com/<org>/<repo>`, and every ⭐, licence, `pushed_at` and `archived` value quoted
below came from `https://api.github.com/repos/<org>/<repo>`. Retrieved **2026-08-27**; F462–F463
**2026-08-28**. Sources that are not `org/repo` are linked in place.

Category saturation was measured, not estimated: `bradAGI/awesome-cli-coding-agents` (1,094 stars,
pushed 2026-08-26) was downloaded whole — 768 lines, 101,448 bytes — and entries counted per
section with `awk` on its `- **[` entry marker. All vocabulary claims below are local `grep` over
that file.

⚠ **One method finding, recorded because it nearly produced a false claim.** Asking a model to
search a large fetched document is unreliable **in both directions**. A summarizer first reported
category counts of "56 / 62 / 101+ / 120+"; the local `awk` count is **47 / 68 / 102 / 340** —
every one wrong. It then reported the string `pets` as *"Not found"* in a file where `parallel-
harness-pets` sits on line 714. The absence was false and the counts were invented. **Nothing in
this document is quoted from a model's reading of a page; every count and every string match is a
local command over a downloaded file.** This is [[verify-claims-against-code-not-docs]] item 36's
trap arriving from a new direction — not a backgrounded grep, but a delegated one.

## Inherited

Nothing. W9 is the one workstream with no donor component to audit: it looks outward by definition.
What it inherits is a **constraint set** to test candidates against, and three of those constraints
do the deciding here:

- **Zero cloud spend is standing** (David, 2026-08-07, [[abcc-2-decisions]]), so there is no
  frontier tier and no dollar cost to optimise.
- **Co-residency is arithmetically impossible on this card** — W11 F275 — and a per-gate model
  swap costs **23.77 s** (W1 F79). A second tier is a swap, not a second endpoint.
- **2.0 ships MIT OR Apache-2.0 with no inherited-code caveat** (David, 2026-08-27, W12). A
  candidate whose licence is GPL, AGPL or unresolved is not adoptable, only readable.

---

## Findings

### F450 — Switchyard is real, is exactly the right shape, and is pre-alpha

`NVIDIA-NeMo/Switchyard` verified at the API: **Rust, Apache-2.0, 2,517 stars, 216 forks, 54 open
issues, created 2026-05-19, pushed 2026-08-27** (the day of retrieval), not archived. It is a proxy
*and* an embeddable library: `switchyard-libsy` *"embeds the routing algorithms in your own Rust
application and never calls a model itself — an algorithm decides which target to use and hands
every model call back to you."* That is precisely the integration shape 2.0 would need, and the
licence is compatible.

🚨 **And its own README says: *"Switchyard is pre-alpha software that is evolving rapidly. The API
and algorithms are expected to change significantly before we reach v1.0."*** Per-crate maturity is
stated separately and is worse than the star count implies: `libsy` *"Beta. Ready for trial
integration"*, `llm-client` *"Alpha. May change significantly"*, `runner` *"Alpha. Evolving
rapidly"*, and the server *"Demo server, not for production use."*

**The gap between 2,517 stars under an NVIDIA org and "demo server, not for production" is the
finding.** A blog-level scan reads this as a solved problem to adopt; the repo says otherwise.

### F451 — its escalation trigger judges the *trajectory*, not the task — which inverts W4

W4 spent a workstream asking an *ex ante* question: predict from the task which tier it needs. It
found nothing predicts — the donor complexity score does not order tasks by anything 2.0 cares
about, the estimator costs an attempt and predicts nothing, and a logprob loses to a free token
count. Switchyard does not attempt the question at all. Its judge prompt says so in one line:

> *"Judge the *trajectory* — is the agent making real progress toward the stated task — not the
> difficulty of the task itself."*

🚨 **The shipped answer to "which tier does this task need" is: you do not ask.** You start cheap,
watch the run, and react to a named pattern of failure. That is *ex post* detection, and it
sidesteps every negative result W4 recorded rather than contradicting them. W4's recommendation 2
already landed next to this — *"what is genuinely open is how much budget this attempt gets and
when to stop"* — and Switchyard is the same instinct, built.

**The artefact is the prompt, not the crate.** `crates/libsy/src/prompts/escalation/prompt.md` is
9,574 bytes of failure taxonomy: repetition and loops (*"the same command or edit failing 2+ times
with materially the same error"*), false progress (*"declaring success while the latest visible
evidence shows failure"*), drift, desperation (*"rm -rf, wholesale reinstalls … as a reaction to
being stuck"*), each with worked examples, and a matching list of **expected friction that must not
escalate** (a TDD test written to fail, sequential alternatives, `0 failed` read as clean). It also
draws the boundary W6 would care about: *"no model can fix these, so escalation is pure waste"* for
missing files and broken services.

### F452 — the judge verdict is not a gate on one call; it is a confirmed streak that latches

Read directly in `escalation.rs`. The classifier holds a per-session counter, `STREAK_KEY =
"escalation_streak"`, and escalates only when consecutive escalate verdicts reach `confirmations`:

> `/// Consecutive escalate verdicts required to latch.`
> `confirmations: u32,`

The shipped default is **`confirmations: 2`**, and the config's own doc comment calls it *"the
router's main cost dial"*. Three further properties, all read in the source:

- **It latches.** Once confirmed, `if streak(state) >= self.confirmations` returns the capable tier
  *"without a judge call"* — a one-way ratchet per session, so the judge cost is bounded.
- **It fails up, not open.** A context-window overflow or a transport error on the cheap tier both
  `return Ok((decisive(&self.capable), None))`. Contrast W7's destructive-git guard, which **fails
  open** when it cannot read the tree.
- **Only a decline is evidence.** The policy distinguishes a judge that said "no" from a judge that
  was unavailable: *"both a decline and an outage stay efficient, but only a decline is evidence,
  so only a decline clears the streak."* That is W6's honest-outcome type, in someone else's code.

🚨 **This is a shippable middle position on W6's ruling that "a model verdict is a report and never
a gate."** The ruling holds for a *single* verdict; NVIDIA's answer is that N agreeing verdicts,
with unavailability excluded from the count, is a different instrument. W6 is closed and this does
not reopen it — but the ruling should be read as *one* verdict, which is how it was tested.

### F453 — the advisor-gate is a model verdict used as a gate, and its guardrails are the design

`advisor_gate.rs` gates on a stronger model's `APPROVE`/`REDO` verdict over the executor's output.
Its module doc states the scope precisely: turns with tool calls *"pass through unreviewed"*; only
*"the first **terminal** turn — no tool calls"* is buffered and reviewed, i.e. **the gate fires
only on the agent's claim to be done.** `REDO` appends the discarded turn plus the advisor's plan
as feedback and re-invokes the executor.

The guardrails are what make it defensible, and each is a design decision worth copying:

- **Bounded**: `max_reviews` per budget scope; *"afterwards every call is a pure passthrough."*
- **Fail-open on the advisor**: advisor errors *"pass through as an implicit APPROVE"*, refund the
  consumed review, and count toward `MAX_FAILED_CONSULTS: u32 = 3`, which *"stops consulting a down
  advisor entirely."* Executor errors, by contrast, always propagate.
- **Framed as a superset**: *"identical until the executor first claims to be done, plus one
  quality gate that catches premature convergence."*

🚨 **And one measured negative result, stated in the source as the reason for a design choice:**
*"Front-loading advice was measured to suppress the executor's own test-and-iterate loop, so no
advice is injected up front."* Telling the worker how to do it up front made it worse. That is a
direct warning to any 2.0 stage pipeline that plans to brief the Coder from a Planner.

### F454 — the numbers are real, and they optimise the one axis 2.0 has already zeroed

The repo publishes **no** benchmark results — `benchmark/README.md` is an operational guide only,
despite the source citing *"benchmarked defaults"* and *"measured"* outcomes. The numbers live in
NVIDIA's developer blog
(<https://developer.nvidia.com/blog/route-ai-agent-workloads-across-models-with-nvidia-nemo-switchyard/>,
2026-08-11, retrieved 2026-08-27; the escalation-router row re-verified 2026-08-28):

| strategy | benchmark | result |
|---|---|---|
| escalation router | LangChain deep-agents suite, 145 multi-turn tasks | **74% cost reduction**, **~6-point accuracy tradeoff**, **7% of calls to frontier** |
| staged routing | Cognition FrontierCode | **50.6%** at **$3.11** mean cost — within **2.8 pp** of Opus 5 at **~28% lower** mean cost |

🚨 **Every one of those results is denominated in dollars, and ABCC 2.0 has no dollars in the
loop.** Zero cloud spend is standing, so there is no frontier tier to route away from and no cost
curve to ride down. Worse, the accuracy column runs the wrong way for a local project: the
escalation router **loses ~6 points of accuracy** to buy savings 2.0 cannot bank.

The local analogue is not free either. With co-residency arithmetically impossible (F275), "escalate
to the strong tier" on this hardware means a **23.77 s model swap** (F79) on every escalation, paid
in wall clock — the currency 2.0 actually spends. **A router whose entire measured value is cost
reduction, ported to a project with one resident model and no cost axis, is buying nothing.** What
survives the port is the judge's *reading* of the trajectory (F451), which is a stop/continue and
budget signal — exactly W4 recommendation 2's open question — not a tier selector.

### F455 — the category is not crowded, it is saturated: 340 projects in one list

`bradAGI/awesome-cli-coding-agents`, counted locally, 2026-08-27:

| section | entries |
|---|---|
| Terminal-native coding agents (open source) | 95 |
| OpenClaw ecosystem | 12 |
| Terminal-native (closed source) | 16 |
| **Session managers & parallel runners** | **68** |
| **Orchestrators & autonomous loops** | **47** |
| **Agent infrastructure** | **102** |
| **total** | **340** |

**Harnesses and orchestration alone: 217 projects.** The top of the session-manager section is not
a hobby tier — Orca (Stably) 53.7k, Multica 47.7k, herdr 32.4k, AionUi 32.3k, vibe-kanban 27.9k,
cmux 26.5k. Five further competing curated lists of the same category were encountered while
verifying this one. **"Build a thing that supervises several coding agents from a terminal" is not
an available position in August 2026**, and any part of 2.0's pitch that rests on it is dead.

### F456 — zero of 340 entries use game vocabulary

A local `grep -oin` over all 768 lines for `isometric`, `RTS`, `battle`, `voice pack`, `sprite`,
`game`, `gamif`, `XP`, `leaderboard`, `arcade`, `villager` and `units` returns **no matches at
all**. Not one entry in the largest curated directory of this category is framed as a game.

🚨 **This is the differentiator, and it is the only one the evidence supports.** It is also the
half of ABCC that is hardest to justify on a feature list and easiest to cut under schedule
pressure — and F455 says the parts that would survive such a cut are the parts 217 projects already
ship.

### F457 — "local-first" is not differentiated either, which kills the brief's other half

`grep -oin "local-first\|local model\|llama\.cpp\|ollama\|lm studio\|local llm"` over the same file:
**26 `local-first` claims, 10 Ollama, 5 llama.cpp, 2 LM Studio.** Local-first is a common stance in
this category, not a distinguishing one.

The brief nominated *"the console and the local-first stance"* as the differentiated parts. Measured:
the console is one of 68, and local-first is one of 26. **Both nominations fail.** The brief's
throwaway clause — *"the orchestration core may well not be"* — is the only part that holds, and it
understates the problem by two orders of magnitude.

### F458 — the fun layer is not empty; it is three accessories, none of them a game

Correcting the implication of F456: playfulness exists in this category, just never as an
organising metaphor. Three entries, verified in the list and by repo lookup:

- **`TevvvB/parallel-harness-pets`** ⭐ 10, Go, MIT — *"each worktree gets its own creature so
  near-identical terminals are tellable apart … `pets party` shows every live session at once,
  worst first."* Note the justification is **functional** (telling terminals apart), not fun.
- **`launsion-boop/EchoCoding`** ⭐ 28 — *"Audio layer for CLI coding agents with hook-triggered
  SFX, ambient soundscape, and optional cloud TTS/ASR voice interaction."* This is v1's voice-pack
  idea, shipped by someone else, at 28 stars.
- **`tristan666666/agent-island`** ⭐ 87, MIT — *"Local status companion … shows working,
  your-turn, stalled, and attention states."*

**10, 28 and 87 stars.** The fun layer is being attempted, by small projects, in pieces, and
nobody has assembled the pieces. That is a better position for 2.0 than an empty field — it is
evidence of demand without a competitor — but it also means the idea is not unthinkable, and the
window is not indefinite.

### F459 — the closest competitor by name scores 3,144 stars on the pun alone

**`agent-of-empires/agent-of-empires`**: **Rust, MIT, 3,144 stars, created 2026-01-09, pushed
2026-08-27.** Same language, same category, compatible licence, actively developed, and named after
a real-time strategy game.

🚨 **It has no game in it.** Read against its README: no units, no villagers, no sprites, no
isometric view, no XP, no sound packs with RTS flavour. The only game-adjacent sentence is a
metaphor about tracking *"which agent is stuck, which is waiting on input, and which just made a
mess of your working tree."* The TUI shows a status dashboard, keybindings, and tmux panes. Its
stack is Rust + tmux + `axum` + React. **And it lists no local-model support at all** — every
integration named is a cloud CLI.

Two things follow. **The name space is taken and the design space is not:** an RTS pun with a
status table earns 3.1k stars, which prices the appetite for the framing while proving nobody has
built the thing. And it is the sharpest available evidence for F457's converse — the one project
that most resembles 2.0 superficially is **cloud-only**, so local-first plus the game framing
together is a narrower and more defensible position than either alone.

### F460 — the Rust cluster is real, and licence is the first filter, not capability

Verified at the API on 2026-08-27:

| project | ⭐ | licence | pushed | note |
|---|---|---|---|---|
| `0xPlaygrounds/rig` | 8,429 | MIT | 2026-08-27 | the largest general Rust LLM framework |
| `RightNow-AI/openfang` | 18,137 | Apache-2.0 | **2026-07-02** | *"Agent Operating System"*; **~8 weeks stale** |
| `ThousandBirdsInc/chidori` | 1,363 | Apache-2.0 | 2026-08-27 | see F461 |
| `liquidos-ai/AutoAgents` | 744 | Apache-2.0 | 2026-08-26 | actor-model multi-agent |
| `zavora-ai/adk-rust` | 623 | **NOASSERTION** | 2026-08-27 | ⚠ licence unresolved — **not adoptable** |
| `a-agmon/rs-graph-llm` | 363 | MIT | 2026-07-19 | workflow graphs |
| `librefang/librefang` | 363 | MIT | 2026-08-27 | second *"agent operating system"* in Rust |

Two corrections to the scout. **`kalosm/ADK-Rust` does not exist** — the real repo is
`zavora-ai/adk-rust`, and its licence is `NOASSERTION`, so W12's MIT-OR-Apache-2.0 ruling removes
it from consideration before any code is read. And **openfang's 18,137 stars are the largest number
in this scan attached to the longest silence** — no push in eight weeks in a category where five of
its six peers pushed within 36 hours of retrieval. `rs-graph-llm` is the other quiet one at five
weeks. **Star count is the least informative column in this table**, and it is the column the
scout's blog sources led with.

### F461 — chidori ships W3's central ruling as its one-line pitch

**`ThousandBirdsInc/chidori`**, 1,363 stars, Apache-2.0, pushed 2026-08-27: *"The agent framework
where every run is durable, replayable, and resumable by default."*

W3's ruling, arrived at independently over 3,403 lines, was the **durable event log** with seven
Task states. Chidori's entire positioning is that sentence. This does not make W3 wrong — it makes
W3 *confirmed by an outside party who reached it first*, and it is the strongest "read their code"
candidate for the orchestration core specifically, because it is the one project whose stated
architecture matches a conclusion 2.0 already reached on its own evidence.

### F462 — W10's "fleet" is one box: multi-machine is unoccupied, and the one shipped path warns against itself

W10 was the last workstream with no scan at all. It has one now, run 2026-08-28 over the same
340-entry directory plus API lookups. **The word *fleet* appears 8 times and every one is a fleet of
sessions on a single machine** — Orca (53.7k) in terminal splits, `repomon` (⭐16) in tmux panes,
`construct` (⭐16) in one Rust binary, DevPilot (⭐0) as `claude -p` subprocesses. ***Remote* appears
15 times and means remote *control* of one machine** — `tlbx` (⭐105) and `ADHDev` (⭐80) from a
phone, `Untether` (⭐66) from Telegram, `Clave` (⭐47) over SSH. **`multiplayer`, `co-op`,
`multi-machine`, `peer-to-peer` and `tailscale`: zero hits in 340 entries.** Two projects genuinely
spread work across machines, and the licence filter takes the closer one:

| project | ⭐ | licence | pushed | what it is |
|---|---|---|---|---|
| `AgentsMesh/AgentsMesh` | 2,330 | **NOASSERTION** | 2026-08-03 | *"a hundred AI coding agents across your own machines"* — ⚠ not adoptable |
| `google/ax` | 1,972 | Apache-2.0 | 2026-08-20 | *"An open source distributed agent runtime"*; remote gRPC controller, durable |
| `exo-explore/exo` | 47,105 | Apache-2.0 | 2026-08-25 | *"Run frontier AI locally"* — the home-cluster incumbent by two orders of magnitude |

🚨 **The remote-rig capability already ships inside the server 2.0 already uses.** llama.cpp's
`tools/rpc/README.md` (<https://github.com/ggml-org/llama.cpp/blob/master/tools/rpc/README.md>,
retrieved 2026-08-28) documents `ggml-rpc-server` and `--rpc host:port,host:port`, over TCP or
RDMA. Its own first paragraph: *"the RPC backend [is] currently in a proof-of-concept
development stage. As such, the functionality is fragile and insecure. **Never run the RPC server on
an open network or in a sensitive environment!**"* No auth, no TLS, no `--api-key` in its usage —
`-p 50052` exposes every accelerator on the host. **The private overlay is not a convenience in
W10's brief, it is the documented precondition**, so *"proven against the laptop over Tailscale"* is
the right test and cannot be dropped for a LAN shortcut.

⚠ **And read what it distributes:** *"llama.cpp distributes model weights and the KV cache across
all available devices — both local and remote — in proportion to each device's available memory."*
A remote rig makes **one bigger model spread thinner**, not a second independent worker — the
opposite of what a fleet of agents needs, and it compounds F275 (co-residency impossible). Adding
the laptop buys parameters or context at LAN latency, never parallelism. **So W10's provider
abstraction has three cases and the third is not a peer of the first two.**

### F463 — what the stalled projects stalled on: stars do not keep an inference project alive

The brief asks *"where they stalled"*. Across every candidate verified at the API, the answer is not
funding or architecture — **the star count and the pulse are unrelated columns**, and the biggest
numbers in this scan sit on the longest silences (all retrieved 2026-08-28):

| project | ⭐ | state | last push |
|---|---|---|---|
| `bigscience-workshop/petals` | 10,525 | not archived, simply silent | **2024-09-07 — ~24 months** |
| `rustformers/llm` | 6,153 | **archived**, *"[Unmaintained, see README]"* | 2024-06-24 |
| `RightNow-AI/openfang` | 18,139 | alive but quiet | 2026-07-02 — ~8 weeks |
| `b4rtaz/distributed-llama` | 3,046 | MIT, C++, home cluster | 2026-07-05 — ~8 weeks |
| `lemon07r/SanityHarness` | 241 | **top of the whole eval-harness field** | 2026-04-17 — ~19 weeks |

🚨 **A 6,153-star Rust LLM ecosystem died, and a 10,525-star distributed-inference project has been
silent for two years.** Both are the shape of thing 2.0 is about to depend on. The rule that follows
is cheap and applies to every "use it" below: **read `pushed_at`, never `stargazers_count`**, and
prefer a dependency whose upstream is compiler-grade (llama.cpp: 126,028 ⭐, pushed the hour of
retrieval) over one whose upstream is a category-leading wrapper.

---

## The verdict table — one row per workstream

The point of W9 is not a survey; it is a verdict per workstream, because *"use it"* is only
actionable at that granularity. **`build`** = nothing found that shortens the work. **`use it`** =
adopt the dependency. **`read it`** = do not adopt, but read it before writing 2.0's version.
**The `seen` column is the coverage statement**: `code` = source pulled and read, `docs` = README or
reference docs read, `meta` = API metadata plus the project's own one-line description, `none` = not
scanned. **Only one project in this entire scan was read as code.**

| W | subject | verdict | forced by | seen |
|---|---|---|---|---|
| **W1** | model tiering | **build** | nothing — settled by measurement on this box, not by prior art | `none` |
| **W2** | serving, Rust↔llama.cpp | **use it** | `utilityai/llama-cpp-rs` — 639 ⭐, **MIT OR Apache-2.0** (F479), pushed 2026-08-28 | `meta` |
| **W3** | orchestration core | **build, read first** | `chidori` 1,363 ⭐ Apache-2.0; `google/ax` 1,972 ⭐ Apache-2.0 | `meta` |
| **W4** | routing and escalation | **read it** | Switchyard's 9,574-byte judge prompt — the prompt, not the crate | `code` |
| **W5** | command center, fun | **build** | 68 session managers already exist; **zero of 340 are games** | `docs` |
| **W6** | verification and gates | **read it** | Switchyard `advisor_gate.rs` + the latching streak in `escalation.rs` | `code` |
| **W7** | security and sandboxing | **build** | `stacklok/brood-box` — 63 ⭐, Apache-2.0, microVM + egress control | `meta` |
| **W8** | evaluation harness | **build** | no incumbent: field tops out at 241 ⭐, no licence, quiet 19 weeks | `meta` |
| **W9** | prior art | **use it** | `awesome-cli-coding-agents` is the instrument — re-count it at freeze | `docs` |
| **W10** | fleet topology | **use it, warily** | llama.cpp's own `ggml-rpc-server`, under a private overlay only | `docs` |
| **W11** | stages and unit roles | **build** | `rs-graph-llm` 363 ⭐ MIT, `AutoAgents` 744 ⭐ Apache-2.0 | `meta` |
| **W12** | repo strategy | **build** | already ruled; the scan's contribution is the licence filter itself | `meta` |
| **W13** | co-dev ergonomics | **build** | nothing found; W13 ran its own live scan and needs no second one | `none` |

Six rows need a sentence the table cannot hold:

- **W2 is the only unqualified `use it`.** `llama-cpp-rs` is the binding 2.0 would otherwise write
  by hand, its licence clears W12's filter, and it was pushed the day of retrieval. The alternative
  — `EricLBuehler/mistral.rs`, 7,632 ⭐, MIT — replaces `llama-server` outright and is a much larger
  bet; it belongs in W2's own options table, not here. ⚠ Neither was read as code.
- **W4's `read it` is the scan's single most valuable artefact** and it is a text file (F451). Take
  the failure taxonomy and the expected-friction list; leave the crate, which is pre-alpha (F450)
  and optimises a cost axis 2.0 has zeroed (F454).
- **W6's `read it` is a correction to a closed ruling, not a dependency** (F452): N confirming
  verdicts with unavailability excluded is a different instrument from the single verdict W6 tested.
- **W7's row is `build` on 2.0's own audit, not on this scan.** W7 closed at 945 lines against the
  donors' source; `brood-box` is one microVM implementation to read if the Windows boundary question
  is reopened, nothing more.
- **W9's own row is real:** the directory is the instrument behind every count here, and F455–F457
  therefore have a shelf life — re-run them before the freeze.
- **W12's row is the licence filter earning its place twice**: `adk-rust` (623 ⭐) and `AgentsMesh`
  (2,330 ⭐) were both removed by `NOASSERTION` **before a line of either was read**. That is ~3k
  stars of candidate disqualified by a policy decision that cost one API field.

## Options compared

The evidence forces one strategic choice, so this is the option set: **which position does 2.0
claim**, scored against occupancy (how many of the 340 already hold it), defensibility, and what it
costs to build.

| position | occupied by | defensible? | cost | verdict |
|---|---|---|---|---|
| A. Supervise many agents from a terminal | **68 session managers**, top four 53.7k–32.3k ⭐ | no | high | **dead on arrival** |
| B. Local-first agent harness | **26 entries** claim it by name | weak alone | high | necessary, not sufficient |
| C. **Local-first *and* a game** | **zero of 340** | yes — two filters at once | high | ▶ **chosen** |
| D. Skin an existing harness | any of 217 | no — inherits their roadmap | low | rejected, see below |

**C is chosen because it is the only cell with a zero in it.** F456 measures the game half as
unoccupied and F459 shows the nearest name-alike (`agent-of-empires`, 3,144 ⭐, Rust, MIT) is
cloud-only with no game in it — so each half of C is crowded alone and the intersection is empty.

## Recommendation

1. 🚨 **Stop describing the console as the differentiator and start describing the game as one.**
   The brief's sentence is measurably wrong in all three claims (F455–F457). Every public-facing
   text — README, announcement outline, SUMMARY.md — should lead with the framing that has zero
   competitors, not the terminal dashboard that has 68. **The console is table stakes; it must be
   excellent and it will never be the reason anyone chooses this.**
2. **Protect the fun layer from the schedule.** It is the differentiator, it is the cheapest thing
   to cut when Phase 2 runs late, and F458 prices the appetite: three accessories at 10, 28 and 87
   stars, one of which (`EchoCoding`) is v1's voice-pack idea shipped by somebody else.
3. **W2: adopt `utilityai/llama-cpp-rs`** (639 ⭐, MIT OR Apache-2.0, pushed 2026-08-28) as the
   boundary, subject to W2's own read of its API. The one unqualified `use it` this scan produced.
4. **W4 and W6: port Switchyard's *prompt*, not its crate.** The failure taxonomy (loops, false
   progress, drift, desperation) plus the expected-friction list is a 9.5 KB text file that answers
   a question W4 could not answer *ex ante*, and the latching-streak semantics (confirm twice, fail
   up, count only declines) are ~20 lines of policy, not a dependency.
5. **W3: read `chidori` before writing the event log.** It reached W3's conclusion first and states
   it in one sentence; an afternoon in its source is cheaper than discovering the divergence later.
6. **W10: the remote rig is `ggml-rpc-server` behind a private overlay, or it is nothing** (F462).
   Never on an open network — its own README — and the provider trait must model it as a *device
   extension*, not a peer worker, because it spreads one model rather than adding a second.
7. **Adopt one operational rule from the corpses: read `pushed_at`, never `stargazers_count`**
   (F463), and re-run every count in this document before it is quoted publicly.

## Rejected alternatives and why

- **Adopt Switchyard as the router.** Pre-alpha by its own README, server *"not for production
  use"*, and its entire measured value is a 74% dollar saving for ~6 accuracy points — on a project
  with zero cloud spend, that is a pure accuracy loss (F454).
- **Build on `AgentsMesh` or `adk-rust`.** Both `NOASSERTION`. W12's ruling removes them before any
  capability question is asked; ~3k stars of candidate, disqualified by one API field.
- **Skin an existing harness (option D).** Cheapest by far and it forfeits the position: the thing
  that would be differentiated is the layer on top, built on a roadmap 2.0 does not control, in a
  category where an 18,139-star project can go eight weeks silent (F463).
- **Treat `exo` (47,105 ⭐) as the fleet answer.** It is a home *cluster* for running one large
  model, not a fleet of agents; same category error as the RPC backend, at a much larger scale.

## Effect on fun

**This is the workstream that turns the fun layer from a preference into a strategy.** Every other
document treats the game as something ABCC wants; W9 measures it as the only thing ABCC has. A
console is one of 68, local-first is one of 26, an orchestrator is one of 217 — and units, sprites,
XP and voice packs are zero of 340. The consequence is directional: **when Phase 2 is late, the fun
layer is the last thing to cut, not the first**, because cutting it lands 2.0 in the crowded cell.

Two cautions from the same evidence. `EchoCoding` (⭐28) already ships hook-triggered SFX — v1's
voice-pack idea, in someone else's repo — and `agent-island` (⭐87) ships the status companion, so
**the window is open, not indefinite**. And `agent-of-empires` earns 3,144 ⭐ on an RTS *name* with
no game inside it (F459): the appetite is priced, and it is priced for the metaphor.

## Open questions

- **OQ-W9-1 — `chidori`'s source is unread.** It is the one project whose stated architecture
  matches W3's independent conclusion (F461). Resolve before W3 implementation, not before Phase 2.
- **OQ-W9-2 — `llama-cpp-rs` is a `use it` verdict on metadata alone.** Does its API expose the
  slot, `--rpc` and KV-reuse control W2's measurements depend on? W2 must read it before adopting.
- **OQ-W9-3 — the judge prompt was written for a frontier judge.** Switchyard's taxonomy is 9.5 KB
  of nuance; whether the local champion can apply it reliably is a W6-shaped measurement nobody has
  run. **Do not assume the prompt ports with the design.**
- **OQ-W9-4 — the 340-entry directory is one curator's view.** Five competing lists exist. The
  counts are reproducible, not canonical; re-run them before any public claim (F455).
- **OQ-W9-5 — `ggml-rpc-server` has never been run on this hardware.** W10's brief calls for a
  laptop-over-Tailscale proof; F462 says do it behind the overlay from the first attempt.

## Confidence: high on the counts and the metadata, low on any capability claim

Every count is a local `grep`/`awk` over a downloaded file, every star, licence and `pushed_at` is
an `api.github.com` field read on 2026-08-27 or 2026-08-28, and the one project read as source was
read at 2,892 lines. **What is deliberately weak: capability.** Twelve of the thirteen table rows
rest on metadata and one-line descriptions, so a `build` verdict means *nothing found that shortens
the work*, never *nothing exists that could*. The "nobody does X" claims are safe only for the
strings actually grepped — entries were counted, not read. **What would raise it:** reading
`chidori` and `llama-cpp-rs` as code (OQ-W9-1, OQ-W9-2). **What would lower it:** time. Three of
the five stall-table rows went quiet inside eight weeks; these numbers decay.
