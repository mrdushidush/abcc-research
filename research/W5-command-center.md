# W5 — The command center and the fun layer

**Status: OPEN, started 2026-08-18.** This file accretes one W5 item at a time. **Two of seven are
written:**

1. ✅ **Frontend architecture** (F93–F99) — §11's "big open question". Answered; David accepted the
   recommendation 2026-08-18.
2. ✅ **What the operator must be able to do** (F100–F106) — §11's "the genuinely new work", and
   where §14 item 3 says W5's extra room should go.

The remaining five (component-inventory decisions, what the console must *show*, observability
prior art, transport + storage, §7's fun research) are stubbed at the bottom with what is already
known, and are not answered here.

Scope reference: `RESEARCH_BRIEF.md` §11 lines 773–802 — **not** §14 item 3, which is about how to
spend W5's extra room, not what W5 covers.

---

## Question

**Which frontend architecture does ABCC 2.0 ship?** The brief names four and asks that all four be
argued: the existing React + React Three Fiber console over WebSocket, a Tauri desktop app, a
Ratatui TUI, or a TUI-plus-web hybrid.

The criterion is not aesthetics. §16 defines project-done as *"a working developer picks this up
for real work and enjoys it"*, and David's own success test is that in a few months he casually
opens ABCC 2.0 instead of Claude Code. So the question this section actually answers is:

> **What is the shape of the thing you reach for, and does the architecture make reaching for it
> easier or harder than the tool it has to displace?**

---

## Method

Desk work, no GPU. Sources in order of weight:

1. **Executed / measured inheritance** — `prestudy/verification.md` §3.5 (the ABCC UI was run
   2026-08-07 under headless Chrome), `prestudy/inheritance-map.md` §8, `prestudy/abcc-v1-dossier.md`
   §11.
2. **Re-read of the live source on disk, this session** — ABCC v1 at `d5528ea`
   (`D:\dev\agent-battle-command-center`) and Claudette at `af3f804`
   (`D:\dev\claudette`, ahead of the dossier pin `fc1ea22` / v0.17.0). Line counts and byte counts
   below are `wc -l` / `du` from this session, not quoted from the dossiers.
3. **An archived owner document the project had not cited** — found this session by grepping
   `D:\dev\_archive` for the Ratatui / Bubbletea / Textual research §11 says to start from. See F93.
4. **External prior art**, with URLs and retrieval date 2026-08-18.

---

## Inherited

| Asset | Where | Size, measured this session |
|---|---|---|
| The whole V1 console | `agent-battle-command-center/packages/ui/src` | **14,935 lines** of TS/TSX in 83 files |
| Isometric renderer + projection math | `components/isometric/` (8 files) | 1,298 lines |
| React Three Fiber battlefield | `components/battlefield/` (12 files) | 2,133 lines |
| Art and audio | `packages/ui/public/` | **44 MB** — sprites 35 MB, audio 6.7 MB, assets 2.3 MB, fonts 32 KB |
| 96 Bark voice lines | `public/audio/{field-command,mission-control,tactical}` | 96 `.wav`, confirmed by count |
| Claudette's Ratatui TUI | `crates/claudette/src/tui*.rs` + `tui/` | **3,011 lines** (1,202 + 967 + 554 + 150 + 87 + 51) |
| BCF's Ratatui TUI | `battle-command-forge` `tui.rs` | 1,803 lines (dossier) |

---

## Findings

### F93 — the frontend question has two opposite owner rulings five months apart, and neither document cites the other

§11 says *"the owner has already researched Ratatui, Bubbletea and Textual, so start from those
findings."* Those findings are not in this repo, and not in `prestudy/`. They are here:

`D:\dev\_archive\abcc_projects\abcc_projects\Archive\abcc-internal-docs-20260423\ABCC_V2_DESIGN_BRIEF.md`,
dated **Mar 3, 2026**, 143 lines. It is not referenced by `RESEARCH_BRIEF.md` or by any
`prestudy/` file — `prestudy/archive-repos.md` studied that same archive path for `independencev1`
and StealthForge and did not surface this document.

What it rules, in its own words:

- *"**Interface: Terminal CLI Only.** Reference implementation: opencode-ai/opencode (Go TUI,
  Bubble Tea, 11K stars, now charmbracelet/crush)."*
- Anti-pattern #6: *"**Web UI** — CLI only. No React, no browser-based interface."*

And what the current brief rules, §17 item 5: *"a full isometric web UI in the style of the
original Command and Conquer… **Not a TUI, not Tauri.**"*

**These are exact opposites, from the same owner, five months apart.** The resolution is not "the
older one is stale, ignore it" — it is that they were written against different premises, and the
premise change is documented:

| | Mar 2026 brief | Aug 2026 brief |
|---|---|---|
| Hardware | Mac Studio M4 Max **128 GB**, 70B CTO local | 32 GB RAM + **16 GB VRAM**, one card |
| Goal | *"enterprise-grade"* — auth + RBAC, multi-tenant, compliance, audit | single player, local-only, **fun is the differentiator** |
| Stack | Rust + Python, gRPC/HTTP, PostgreSQL **+ Redis** | Rust, HTTP to llama.cpp, storage undecided (W5) |

The August ruling is the live one and the March document does **not** overturn it: every premise
the CLI-only ruling rested on has since changed, and the enterprise framing is explicitly not what
2.0 is — ABCC's contribution to 2.0 is *fun*, Claudette's is correctness.

**But the reversal is itself the finding.** The owner has argued both poles of this question with
conviction, which is exactly why §11 still demands all four be argued rather than treating §17
item 5 as closed. Two things in the March document survive the premise change intact and are
carried into the argument below: the **typed pub/sub broker that decouples business logic from the
UI**, and the **permission system as a blocking channel** (F98, F99).

### F94 — the success test is terminal-shaped, and every tool it names is a terminal tool

The tool 2.0 has to displace is Claude Code: launched with `cd <repo> && claude`, driven by typing,
living in the same terminal as the build. When asked what workload 2.0 targets, David's answer
(§17 item 2) was *"like **aider** and **opencode** but way more fun and engaging."*

- `aider` — terminal.
- `opencode` — terminal. Go TUI on Bubble Tea; the lineage split in 2026 into **charmbracelet/crush**
  (Go, 25k+ stars, led by the original creator) and SST's TypeScript **opencode**, which kept the
  name. ([crush](https://github.com/charmbracelet/crush),
  [2026 coding-CLI comparison](https://www.tembo.io/blog/coding-cli-tools-comparison), retrieved 2026-08-18)
- **Claudette** — the correctness donor and David's actual shipped daily driver — is a CLI plus a
  3,011-line Ratatui TUI, installed as a single `.exe`.

**Every incumbent in the habit being displaced is a terminal program.** That is not an argument
that 2.0 must be a TUI, but it is a hard constraint on the *entry point*: if the first thing a user
does is leave the terminal, open a browser and find a tab, 2.0 is asking for a new habit before it
has earned one.

The counter-evidence is equally concrete and must not be waved away: **44 MB of art and 96 voice
lines have no terminal expression whatsoever.** §7's fun requirements — no dead air, legibility,
personality — were solved in V1 with sprites and sound. A TUI cannot show a painted battlefield.
The two halves of this finding are what force the hybrid question rather than settling it.

### F95 — install shape is a first-class difference, and the two donors sit at opposite ends of it

Measured this session:

**ABCC v1** — `package.json` requires `node >=18`, `pnpm >=10`; `pnpm dev` runs *two* dev servers
under `concurrently` (`@abcc/api` + `@abcc/ui`); `docker-compose.yml` brings up **postgres:16 +
redis:7 + ollama**. Getting a console on screen is a multi-service operation.

**Claudette** — `install.ps1` / `install.sh` one-liner: resolve the latest tag from the GitHub API,
download `claudette-<tag>-x86_64-pc-windows-msvc.zip` plus a `.sha256` sidecar, **verify the hash
and refuse to install on mismatch**, extract one `claudette.exe`. No toolchain, no daemon, no
database server.

§11.0 already flagged that SQLite plus a single binary is *"a dramatically lower barrier for a
public tool"*. This finding says the same thing from the other direction: **V1's console is
architecturally welded to a three-container stack**, and any option that inherits the console
without re-hosting it inherits the stack too. Whatever wins must not restore the docker-compose.

### F96 — "the existing React + R3F console" is a narrower asset than the brief's phrasing implies

The brief's option A is *"the existing React and React Three Fiber console over WebSocket"*. Read
in the source this session, that is two different things and only one of them is live:

- `components/battlefield/BattlefieldView.tsx:13` documents the 3D path in V1's own words as the
  *"legacy Three.js canvas (lazy-loaded)"*, behind `lazy(() => import('./BattlefieldCanvas'))` with
  the comment *"Lazy-load the heavy 3D canvas (Three.js ~600KB)"*.
- `store/uiState.ts:43` types the mode as `'isometric' | '3d'` and `:221` defaults it to
  `'isometric'`. (The "cards" view named in the dispatcher comment is not a third value of that
  union — it is the battlefield *disabled*, a separate `battlefieldEnabled` flag.)
- The running page had **zero `<canvas>` elements** (`verification.md` §3.5).

So option A is really **"keep the isometric DOM-sprite console"** — 1,298 lines of live renderer
inside a 14,935-line app — and the 2,133 lines of R3F are a REFERENCE asset that V1 deprecated on
its own. This matters because the strongest argument *for* option A is "the visual work already
exists", and the honest size of that work is smaller than the brief's sentence suggests. What is
irreplaceable is the **44 MB of art and audio**, which is renderer-agnostic and survives every
option except the pure TUI.

### F97 — Tauri is a packaging answer, not an interface answer, and that removes it from the axis that matters

What it buys: Tauri v2 renders through WRY against the **system** webview — WKWebView on
macOS/iOS, WebView2 on Windows, WebKitGTK on Linux — so the runtime is not bundled and installers
stay in the single-digit MB range, versus Electron shipping a whole Chromium.
([Tauri webview versions](https://v2.tauri.app/reference/webview-versions/),
[tauri-apps/tauri](https://github.com/tauri-apps/tauri), retrieved 2026-08-18) A Rust backend can be
linked in-process or shipped as a **sidecar** binary under a declared capability scope, and Tauri's
own docs warn that the `localhost` plugin *"brings considerable security risks"* and should be used
only if you know exactly why you need it. ([Tauri sidecar](https://v2.tauri.app/develop/sidecar/),
[Tauri localhost plugin](https://v2.tauri.app/plugin/localhost/), retrieved 2026-08-18)

What it costs: three webview engines' behavioural quirks instead of one browser, and a Linux floor
of webkit2gtk 4.1 (Ubuntu 22.04+).

**But the decisive point is what it does not change.** A Tauri window is still a GUI you alt-tab
to. Against F94's constraint — meet the developer where the habit already is — Tauri and the
browser console are the *same answer*, differing only in delivery. On the target hardware (one
user, one machine, `localhost`) a single Rust binary that serves the console already gets most of
Tauri's benefit with none of its three-engine surface.

**Consequence: Tauri is not a fourth position on the real axis.** It is a later packaging decision
over the same web assets, and deferring it costs nothing — which is a better outcome for it than
the brief's framing allows, because "not now" here does not mean "never".

### F98 — 🚨 the only working mid-run operator control in the entire family is in the terminal surfaces, not the console

This is the finding that most changes the shape of the answer.

§7 names agency as *"the single biggest gap in V1"*, and §11 calls operator control *"the genuinely
new work"*. Read across the three repos:

- **ABCC v1 has none.** `/execute/abort` checks a dict that `execute_task` never writes to, so the
  branch never fires and the endpoint returns `{"aborted": true}` **unconditionally, having aborted
  nothing** — and no cancellation token is threaded into `crew.kickoff()` either
  (`abcc-v1-dossier.md` §9.2). V1 does not merely lack agency; it ships an endpoint that claims it.
- **Claudette's TUI has exactly one, and it is real.** `crates/claudette/src/tui.rs:199-210`:

  ```rust
  struct PermissionPrompt {
      tool_name: String,
      input: String,          // full tool input — wrap + scroll, never truncated
      required_mode: String,  // e.g. "danger-full-access"
      scroll: u16,
      resp_tx: SyncSender<bool>,  // rendezvous answer channel: true → allow, false → deny
  }
  ```

  A **rendezvous channel**: the worker blocks, the operator decides, the worker unblocks. That is
  the human-in-the-loop primitive, already built, already shipped, already used daily — and it is
  precisely the *"permission system as a blocking channel"* pattern the March 2026 brief listed as
  the thing to adopt from opencode (F93).

And the CLI prompter's version of the same gate is **richer still** — it takes a free-text redirect,
not a yes/no (F106).

**The console is the surface with the art; the terminal is the surface with the agency.** W5's
operator-control section (pause, resume, retry, re-route, kill, edit a task prompt, take over,
replay) inherits its only working mechanism from the frontend the current ruling calls REFERENCE.
Any option that drops the terminal surface entirely starts the highest-value new work from zero,
next to a working example it chose not to keep.

### F99 — the hybrid's shared asset is the event stream, not the widget tree

The objection to a hybrid is that it means building two frontends in a solo project whose measured
cadence is 1–5 commits a day. That objection is real, and the mitigation is structural.

V1's `useSocket.ts` is 456 lines with **26 domain event handlers** — tasks, agents, execution logs
and steps, alerts, cost, budget, chat streaming, validation pipeline, auto-retry, code review, five
mission lifecycle events, clarification (`inheritance-map.md` §8). That taxonomy is the expensive
part and it is renderer-agnostic. What is *not* reusable is that V1 fused the feel into the
transport: sound on status transition, a 3 s anti-overlap window, a milestone sound every two
iterations, a failure sound when `currentIteration` decreases — all inside the socket handler.

If 2.0's backend publishes **one typed event stream over a broker** and every surface subscribes,
the TUI and the web console become two *renderers* over one contract, and the audio / no-dead-air
policy becomes a third subscriber rather than transport code. This is the March brief's own
top adopted pattern (*"generic typed pub/sub broker — decouples business logic from UI, pure
event-driven"*), it is what makes the hybrid affordable, and it is required anyway: §14 item 3
already puts "separate the audio and no-dead-air logic from the WebSocket transport" in W5's scope.

**Cost, stated honestly:** two view layers still have to be written and maintained, and the second
one will lag. The mitigation is not that it is free — it is that the broker has to exist under
option A too, so the *incremental* cost of a terminal surface is a view layer over a contract that
already exists, against 3,011 inherited lines that already do it.

---

## Options compared

Criteria weighted by §16's success test rather than by engineering taste. **Entry point** = does it
meet the developer where the habit already is. **Identity** = does the 44 MB of art and the 96 voice
lines survive. **Agency** = is there a working mid-run control mechanism to inherit. **Install** =
distance from one command to running. **Build cost** = solo, at the measured cadence.

| | Entry point | Identity | Agency | Install | Build cost | Verdict |
|---|---|---|---|---|---|---|
| **A. Browser console** — isometric DOM sprites over WebSocket | ✗ leaves the terminal for a tab | ✓✓ all of it | ✗ starts from zero (F98) | ~ a single binary can serve it, but must not restore the docker-compose (F95) | ~ 1,298 live renderer lines inherited, re-hosted onto Rust | **Primary view, not the whole answer** |
| **B. Tauri desktop app** | ✗ same as A — a window you alt-tab to | ✓✓ same assets | ✗ same as A | ✓ single-digit MB installer, system webview | ✗ three webview engines; webkit2gtk 4.1 floor | **Defer — packaging, not interface (F97)** |
| **C. Ratatui TUI only** | ✓✓ exactly where the habit is | ✗✗ 44 MB of art has no expression | ✓✓ 3,011 inherited lines incl. the blocking permission channel | ✓✓ one `.exe`, Claudette's exact shape | ✓ largest inheritance | **Rejected — deletes the differentiator** |
| **D. Hybrid, asymmetric** | ✓✓ CLI entry in the repo | ✓✓ console keeps all of it | ✓ inherits the primitive and ports it behind the broker | ✓ one binary serves both | ~ two view layers over one broker (F99) | **✅ Recommended** |

---

## Recommendation

**Option D, hybrid — but asymmetric and explicitly ordered, so it is not read as "build two
frontends".** In three parts:

**1. The entry point is a terminal command in the repo, and this is non-negotiable.**
`abcc "<prompt>"` run inside a working copy starts a run and streams to stdout; `abcc` with no
prompt opens the console. This is the cheapest item on the list and it is the one that decides
whether the habit transfers (F94). Nothing about it competes with Claude Code on features — it only
refuses to ask the user to leave the terminal first.

**2. The isometric web console is the primary view and the home of the identity.** This keeps §17
item 5 intact: the console is the isometric C&C-style web UI, served by the **same single Rust
binary** — not a second Node service, not a docker-compose (F95). This is where operator control,
the task DAG, the cost accounting and the voice lines live.

**3. The full Ratatui TUI is deferred, not rejected** — kept as the standing answer to the
headless / SSH question (`questions.md` §3.4 item 16), with Claudette's 3,011 lines as the
implementation if it is ever called for. What is *not* deferred is the **mechanism** underneath it:
the blocking permission channel (F98) and the typed event broker (F99) are core work regardless of
how many surfaces subscribe.

**And Tauri is deferred with a positive reason rather than dismissed** (F97): it is a packaging
choice over the same web assets, it costs nothing to add later, and on a single-user single-machine
target a binary serving `localhost` already delivers most of its benefit.

**What this changes about the standing ruling:** §17 item 5 said *"a full isometric web UI… Not a
TUI, not Tauri."* This recommendation **keeps the console ruling exactly** and **narrows the two
exclusions**: "not a TUI" becomes "not a TUI *as the primary view* — but a terminal entry point,
and the TUI's control mechanism, are load-bearing"; "not Tauri" becomes "not Tauri *first*". It
completes the ruling where it is silent — how you launch, and what happens on SSH — rather than
reopening it.

> ✅ **ACCEPTED by David, 2026-08-18.** OQ-W5-1 is closed: the narrowing stands. §17 item 5 now
> reads, in effect, *isometric C&C-style web console as the primary view, entered from a terminal
> command in the repo, with the TUI deferred to headless and Tauri deferred to packaging.* The rest
> of W5 is written against this.

---

## Rejected alternatives and why

- **C, TUI-only.** It has the best inheritance and the best entry point, and it is still wrong: it
  deletes the differentiator. 44 MB of art and 96 voice lines have no terminal expression, and a
  terminal ABCC 2.0 competes head-on with Claude Code, crush and aider on precisely the axis where
  it is weakest and they are strongest. Shipping a worse crush fails §16 even if every test passes.
- **A alone, browser-only.** Rejected not for what it builds but for what it assumes: that the user
  will change where they start work before the tool has earned it. It also starts the highest-value
  new work — operator control — from zero, beside a working implementation (F98).
- **B, Tauri now.** Rejected as premature, not as wrong. It answers a distribution question the
  project does not have yet (one user, one machine) at the cost of three webview engines.
- **The R3F 3D battlefield as the console.** Already deprecated by V1 itself (F96), and §11.0 closed
  the rendering-technology question in favour of the sprite technique — free to ~100 entities, no
  canvas and no WebGL needed at any plausible fleet size.
- **"Adopt an existing agent-ops UI"** (Langfuse and friends) at the interface layer. Pre-judged by
  the brief and out of scope for this section; taken up properly in the observability item below.

---

## Effect on fun

- **No dead air, at the moment it matters most.** The worst dead air is not mid-run, it is the first
  ten seconds: launch, find a tab, wait for a socket. A terminal entry point that streams
  immediately makes time-to-first-visible-thing a startup property rather than a rendering one,
  which is exactly what §7 asks be optimised.
- **Agency stops being aspirational.** F98 means pause / take-over has a shipped mechanism to port
  rather than a design to invent — the difference between V1's endpoint that *claimed* to abort and
  a channel the worker actually blocks on.
- **The personality survives whole.** The recommendation spends nothing from the 44 MB or the 96
  voice lines; the console remains the identity surface and the theme system remains the off-switch.
- **The risk it introduces, named:** two surfaces can drift, and the terminal one will look
  neglected if the console gets all the attention. The mitigation is the asymmetry — the terminal
  surface is deliberately thin (entry + stream + the permission prompt), not a second console.

---

## Open questions

- ~~**OQ-W5-1 — does David accept the narrowing of §17 item 5?**~~ ✅ **ANSWERED 2026-08-18:
  accepted.** Terminal entry point + isometric console as the primary view + TUI deferred to
  headless + Tauri deferred to packaging.
- **OQ-W5-2 — what is the terminal surface's exact floor?** "Entry + stream + permission prompt" is
  a boundary that will be under pressure the first time something is easier to show in the terminal
  than in the console. It needs a written line, or it becomes a second console by accretion.
- **OQ-W5-3 — where does the permission channel live** once there are two subscribers? Claudette's
  is a `SyncSender<bool>` owned by the render loop; with two surfaces it has to move behind the
  broker, and "who answered" becomes part of the event record.
- **OQ-W5-4 — is the console served, embedded, or both?** Serving from the binary means the static
  assets ship in it or beside it, and there are 44 MB of them. Interacts with W12's distribution
  story.
- **OQ-W5-5 — did a Ratatui / Bubbletea / Textual comparison ever exist beyond the March brief?**
  F93 found the ruling and its opencode reference but no side-by-side of the three frameworks. If
  those notes exist elsewhere they change nothing about the recommendation (the TUI is deferred),
  but they belong in the record.

---

## Confidence: medium-high on the recommendation, high on the findings under it

- **High** on F93–F99: every number and quotation is from a file read this session or from an
  executed verification pass, with paths and line numbers.
- **Medium-high** on the recommendation. It follows from the findings, but it rests on one judgement
  that evidence cannot settle: that the terminal habit is stickier than the appeal of a better
  console. That is a claim about David, and **the only thing that raises it is David answering
  OQ-W5-1** — or Phase 3 measuring which surface he actually opens, which is §7's honest metric and
  which W8 should carry as a first-class criterion.
- **What would lower it:** if the console turns out to be launchable *from* the terminal so cheaply
  that the distinction collapses, then option A absorbs the recommendation and the hybrid was never
  needed. That is a good outcome, and nothing in the design above prevents it.

---

# Item 2 — what the console must let the operator do

§11 calls this *"the genuinely new work"*, §7 calls agency *"the single biggest gap in V1"*, and
§14 item 3 says W5's extra room should be spent here and on replay. The brief's list is eight
verbs: **pause, resume, retry, re-route to another tier, kill, edit a task prompt, take over
manually, replay.**

## Question

What must the operator be able to do to a running fleet, what does each verb demand of the domain
model, and what is the *unit* the verbs act on? This section also closes `questions.md` §3.4 items
13–15 (unit of control, how take-over works concretely, live vs replay).

## Method

Source reading over the two donor implementations at the pins in Method above, plus one measurement
against the live `~/.claudette/` store on this machine, plus external prior art on agent
checkpointing. No GPU.

## Inherited

| Mechanism | Where | State |
|---|---|---|
| Blocking permission channel | Claudette `tui_events.rs:50-61`, `tui.rs:199-210` | ✅ works, used daily (F98) |
| Action transcript + trash + `/undo` | Claudette `transcript.rs`, 1,019 lines | ✅ works (F102) |
| Session persistence + `--resume` / `-r` | Claudette `main.rs`, `~/.claudette/sessions/` | ✅ works |
| Eleven task states incl. `needs_human`, `awaiting_approval`, `aborted` | ABCC `packages/api` | ⚠ untyped strings, no state machine |
| `/execute/abort` | ABCC `main.py:592-601` | ✗ no-op that reports success |
| Stuck-task watchdog | ABCC | ⚠ polls `in_progress` only, clock is time-since-*assignment* |

## Findings

### F100 — the operator's entire mid-run vocabulary in the family's best surface is three verbs, and none of them is "stop"

`crates/claudette/src/tui_events.rs:75-88` — everything the render loop can say to the worker:

```rust
pub enum UserInput {
    Message { text: String, images: Vec<ImageAttachment> },
    SlashCommand(String),
    Quit,
}
```

Against that, the worker → UI direction has **twelve** variants (`Token`, `TurnComplete`,
`ToolCallStart`, `ToolCallDone`, `Compacted`, `Saved`, `TurnError`, `Working`, `TokensUpdate`,
`SessionReset`, `Info`, `PermissionRequest`). **The observation channel is four times richer than
the control channel** — which is exactly §7's complaint about V1 restated in a type signature.

And the asymmetry is structural, not an oversight. From the `PermissionRequest` doc comment, on why
the answer travels on its own channel rather than as a `UserInput`:

> *"the worker owns that receiver and cannot read it while parked inside `run_turn`."*

**So the one working control verb works only because it bypasses the control channel.** A blocking
rendezvous does not generalise: eight verbs cannot each get their own parked channel.

**Consequence, and it is the central design requirement of this section:** 2.0's worker must
**select over a control channel at every step boundary** rather than block. Every verb below is a
message on that channel; the permission prompt becomes one message type among several rather than
the only one that works.

### F101 — two safety properties of that channel are worth porting verbatim

Same doc comment, and they are not incidental:

> *"Each request carries its own rendezvous channel, so a buffered or stale answer from an earlier
> prompt can never satisfy a later one, and any render-loop exit path that drops the prompt
> automatically denies it (the worker's `recv()` sees `Disconnected`)."*

Generalised, these are the two rules an operator-control channel needs:

1. **Every command carries the identity of what it was issued against** — a stale `pause` from a
   previous task must never pause the task that happens to be running now. With a console *and* a
   terminal surface (item 1) this stops being theoretical: two subscribers, two chances to answer
   late.
2. **Losing the operator is a defined state, not an undefined one.** Claudette's default on a
   dropped channel is *deny*, i.e. fail safe. 2.0 needs the same rule written down per verb — if
   the console disconnects mid-run, does the fleet continue, pause, or stop? (OQ-W5-7.)

### F102 — recoverability already exists, is bigger than the abort story implies, and is the wrong shape for replay

`crates/claudette/src/transcript.rs`, 1,019 lines, opens with the principle:

> *"For an autonomous agent acting on a user's files, **recoverability is itself a feature**."*

Three parts: **trash** (`move_to_trash` / `snapshot_to_trash` keep a pre-image, timestamp-prefixed
to avoid collisions), an **append-only** `~/.claudette/transcript/actions.jsonl` (one line per
*mutating* tool call — `{input, tool, ts, undo}`, input capped at 2,000 chars), and **`/undo`** with
`/undo one` for a single action versus a whole turn. Undo appends an `undo` entry rather than
rewriting the log, so the record stays truthful.

Measured on this machine, 2026-08-18: **16,150 recorded actions, 13,640 with `undo: null` → 2,510
(15.5%) carry a reversible pre-image.**

Two limits, both load-bearing:

- **"One step at a time, no stack."** Linear most-recent undo, not arbitrary rewind.
- **ReadOnly tools are never logged** — deliberately, as *"noise and a privacy footgun"*.

**Consequence, split two ways.** For **take over manually**: rewind-then-take-over is cheap in 2.0,
because the pre-image mechanism is already built and 15.5% of actions already carry one — the
operator can undo the agent's last edit and type their own without hand-reverting files. For
**replay a run**: this log cannot carry it. A record that omits every non-mutating action by design
can reconstruct a *filesystem*, not a *run*. Replay needs its own event log (F105), and the two
should not be conflated because they have opposite requirements — one wants completeness, the other
deliberately does not.

### F103 — the eight verbs are three mechanisms, and the shape is well-trodden

| Verb | Mechanism | What it demands that does not exist yet |
|---|---|---|
| pause / resume | control channel (F100) | a step boundary the worker checks; a `Paused` state that something reconciles |
| kill | control channel | cancellation threaded into the inference call — ABCC has none (`crew.kickoff()` is uninterruptible) |
| re-route to another tier | control channel + lifecycle | a checkpoint to restart the step from, and a **23.77 s** model-swap cost to show the operator (W1 F79) |
| retry | typed lifecycle + checkpoint | the checkpoint, and a retry budget that a circuit breaker can read |
| edit a task prompt | typed lifecycle + checkpoint | fork-from-checkpoint with an edited input |
| take over manually | lifecycle + F102's pre-images | a state that means *"the human has the keyboard"*, and slot/lock semantics while they do |
| replay | durable event log + paged read | the log itself (F102 is the wrong shape; V1's store is a 500-row ring buffer) |

So: **a control channel, a typed lifecycle with checkpoints, and a durable event log with a paged
read path.** Three mechanisms, eight verbs — which is a much smaller build than the brief's list
reads as, and it is the same decomposition the wider ecosystem converged on.

Prior art, for the shape rather than for adoption: LangGraph checkpoints graph state at every
super-step; `interrupt` parks the graph so it can be resumed hours later from the snapshot; and
"time travel" re-invokes from a specific `checkpoint_id`, which supports **replaying, forking, and
editing state at a checkpoint** to create an alternative branch. ([LangGraph time
travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel), retrieved 2026-08-18)
That is precisely "retry / edit a task prompt / replay" falling out of one mechanism. **It is not
adoptable here** — it is Python, and §15 keeps 2.0 on Rust — but it means the checkpoint-plus-fork
design is the trodden path, not an invention, and W3 should be told that the lifecycle enum it owns
has to carry a checkpoint identity.

### F104 — the unit of control is the task, and "pause" has to be defined against a boundary

`questions.md` §3.4 item 13 asks whether the unit is a task, a stage, a builder, or the run. The
answer follows from resources, not taste: **the unit of control must be the unit that holds
resources**, because every verb above ends in "…and then what happens to its model slot and its
workspace lock?" In ABCC that unit is the task — it is what holds the file locks and the pool slot.

Two facts bound the design:

- **The fleet is small.** W2 F83: aggregate throughput saturates at **N=2** on this card (1→2 buys
  +69% prefill / +68% decode; 2→4→6 buys nothing and TTFT degrades from 3.67 s to 10.54 s median).
  An RTS console over a fleet whose useful concurrency is two changes what "command" means — this is
  a squad, not an army, and it argues for per-task control being *legible* rather than for bulk
  fleet operations.
- **A state nothing reconciles is a hang.** ABCC has eleven task states including `needs_human` and
  `awaiting_approval`, held as untyped strings with no state machine, and its watchdog polls only
  `in_progress` on a time-since-*assignment* clock. A task parked in `assigned` or `needs_human`
  therefore holds its agent, slot and locks until a human presses reset (`verification.md` §3.4e,
  §3.4g). **`Paused` is a new member of exactly that family**, so it must arrive with its
  reconciliation, not after it.

So, precisely:

- **Kill** = cancel the in-flight inference now → `Aborted`; release slot and locks. Requires
  cancellation threaded into the model call, which nothing in the family has.
- **Pause** = stop at the next step boundary (end of tool call / end of turn) → `Paused`; **release
  the model slot, keep the workspace lock.** On one GPU a paused task holding a slot is dead weight,
  and with N=2 it is half the fleet.
- **Run-level** control is fan-out over tasks, not a separate mechanism.
- **Agent-level** control is *drain* — "give this agent no new work" — not suspend.
- **Take over** = `Operator` state: the human holds the workspace lock, the agent holds nothing.

### F105 — make replay primary, and live is replay with the cursor pinned to the tail

`questions.md` §3.4 item 15 asks whether the console renders live state or replay, and §11 already
suspects replay may be primary. Two inherited facts settle it:

- V1's console is a **live view, not a record**: a 500-row ring buffer in the store, 50 rows
  rendered, 200 recovered on reconnect, while Postgres holds everything (`inheritance-map.md` §8).
  Replay was never wired up, and §14 item 3 puts the paged read path in W5's scope.
- Claudette's action log is append-only JSONL and *deliberately incomplete* (F102).

Building "live" and "replay" as two read paths means two renderers, two sets of bugs, and the
familiar failure where replay quietly drifts from what the operator actually saw. Building **replay
as the only read path** — an ordered event log, a cursor, and a renderer that projects events into
console state — makes "live" the special case where the cursor is pinned to the tail and new events
push it along. One path, one renderer, and the ring-buffer problem disappears structurally rather
than being patched.

It also gives W8 something it currently cannot measure: a run that can be re-rendered is a run that
can be *scored after the fact* on the operator axis — how long the fleet was idle, how long the
operator watched dead air, when they intervened.

### F106 — 🚨 the family's richest control verb is a free-text redirect, and the port to the better display surface silently narrowed it to a boolean

`prestudy/inheritance-map.md` §12 item 3 already records that redirect and undo exist. Read in the
source this session, the mechanism is sharper than the row conveys, and it carries a warning.

`crates/claudette/src/run/cli_prompter.rs` prompts `Allow? [y/N · or type a redirect]` and
classifies the answer three ways (`gate_line_decision`, pure and unit-tested without a TTY):

- `y` / `yes` → **Allow**.
- empty / `n` / `no` → **Deny**, reason *"user denied permission"*.
- **anything else → Deny carrying the operator's instruction**:
  *"The user declined to run this tool and gave this instruction instead — follow it before
  continuing: {trimmed}"* — which reaches the model as an error `tool_result`.

On an interactive terminal a single keypress decides: `y`/`n` act without Enter, Esc / Enter /
Ctrl-C / Ctrl-D deny, and **any other printable key opens the free-text redirect** with that
character as its first.

**That third branch is steering, not gating.** It is the one place in the entire family where the
operator changes what the agent does next, mid-run, in their own words — the brief's *"edit a task
prompt"* and *"take over"* verbs in embryo.

**And the TUI does not have it.** The TUI's answer channel is `SyncSender<bool>` (F98) — allow or
deny, no third branch. **The port to the surface with better display narrowed the surface with
better control**, which is precisely the failure mode item 1's asymmetry is meant to avoid, already
having happened once inside the donor.

**Consequence:** 2.0's permission event must carry `Allow | Deny | Redirect(String)` from the start,
in the broker contract, not in one surface's channel type. Every subscriber then either renders the
third option or explicitly declines to — a decision, rather than an omission.

## Recommendation

**Build the three mechanisms; treat the eight verbs as the acceptance list for them.**

1. **A control channel the worker selects on at every step boundary** (F100), with per-command
   target identity and a written per-verb rule for operator loss (F101). Its permission message
   carries `Allow | Deny | Redirect(String)` from the start, so no surface can quietly drop the
   third branch the way the TUI already did (F106).
2. **A typed lifecycle enum carrying a checkpoint identity** (F103, F104) — and this is W3's first
   deliverable, not W5's; §14 item 4 already says the lifecycle enum and the Q8 vocabulary are the
   same piece of work. **W5's input to W3 is that the enum must include `Paused` and `Operator`,
   both with reconciliation, and every non-terminal state must be recoverable.**
3. **One ordered, durable event log with a paged read path** (F105), separate from Claudette's
   mutation transcript, which is kept as-is for `/undo` and take-over pre-images (F102).

**Verb-by-verb semantics** as specified in F104: kill cancels in-flight and releases everything;
pause stops at the next boundary, releases the model slot, keeps the workspace lock; re-route shows
the operator the 23.77 s swap cost before it commits; take-over is a state in which the human holds
the lock; replay is the primary read path.

**And one thing not to build:** a second control surface in the terminal. Item 1's asymmetry holds
here — the terminal surface carries entry, stream, and the permission prompt. Every other verb is
console-side until something proves otherwise.

## Rejected alternatives and why

- **Pause as "stop generating right now".** Rejected: mid-token suspension of a llama.cpp request
  has no resumable state, so it is a kill wearing a friendlier label. The honest pair is kill (now,
  destructive) and pause (next boundary, resumable).
- **Keeping the model slot across a pause.** Rejected on F83's arithmetic: with useful concurrency
  of 2, a paused task holding a slot costs half the fleet and is indistinguishable from a hang.
- **Extending `actions.jsonl` into the replay log.** Rejected on F102: it omits every non-mutating
  action by design and caps `input` at 2,000 chars. Widening it would destroy the property that
  makes it good at what it does, and the privacy posture that justifies it.
- **Adopting a checkpointing framework.** LangGraph's shape is right and its language is wrong;
  §15 keeps 2.0 on Rust, and the March 2026 brief's "let the spec decide the framework" question is
  answered by that constraint rather than re-opened.
- **Bulk fleet commands as a first-class feature** ("pause all", "retry all"). Deferred: with N=2
  they are a loop over two things. Revisit if W10's multiplayer mode ever makes the fleet large.

## Effect on fun

- **This is the section that turns the spectator into a commander**, which §7 names as the single
  biggest gap. The measurable form: V1's abort endpoint *claimed* to stop a run and stopped nothing;
  the bar here is that every verb either does what it says or reports honestly that it could not.
- **Honest failure gets a mechanism.** A control channel with defined loss behaviour (F101) is what
  makes "the console disconnected" a visible fleet state instead of a silent divergence.
- **Replay is the fun feature nobody asks for until they have it.** Re-watching a run that went
  wrong is how a failed run becomes as interesting to look at as a successful one — §7's exact ask —
  and F105 makes it the default read path rather than a feature to schedule.
- **The risk, named:** eight verbs that half-work are worse than three that work. The three
  mechanisms are the deliverable; the verb list is how you know when they are done.

## Open questions

- **OQ-W5-6 — does `Paused` release the workspace lock as well as the slot?** Keeping it blocks the
  operator from editing the files by hand, which is most of what take-over is for. Leaning: pause
  keeps the lock, take-over transfers it.
- **OQ-W5-7 — what happens to a running fleet when the operator disconnects?** Continue, pause at the
  next boundary, or kill. Claudette's precedent is fail-safe/deny; the analogue here is arguably
  "pause at the next boundary", but that turns a flaky socket into a stalled fleet.
- **OQ-W5-8 — is take-over per task, or does it stop the fleet?** With N=2, taking over one task
  while the other runs is coherent but hard to watch.
- **OQ-W5-9 — how much of a run does the event log keep, and for how long?** Replay-as-primary means
  the log is the store of record, so retention is now a product decision, not an ops detail. Feeds
  the SQLite-vs-Postgres item.

## Confidence: high on the mechanisms, medium on the verb semantics

- **High** on F100–F102: type definitions, doc comments and a line count read from source this
  session, plus one direct measurement of the live transcript.
- **High** on the three-mechanism decomposition (F103) — it is forced by what each verb needs, and
  the external prior art agrees on the shape.
- **Medium** on the specific semantics in F104 (what pause releases, what take-over holds). They
  follow from the N=2 arithmetic and from ABCC's hang bug, but no implementation in the family has
  ever run them. **What would raise it:** the first Phase-3 spike that pauses a real task, and W8
  measuring intervention on a real run.

---

# Not yet written — the rest of W5

Recorded so the next session starts in the right place, with what is already known attached.

1. **Component inventory, new vs inherited.** Largely already exists as `inheritance-map.md` §8
   (REUSE / PORT / REFERENCE / DROP per component, with the UI-run corrections). W5 owes the
   *decisions* on top of it — notably: pick **one** of the three minimaps (190 / 129 / 297 lines,
   three attempts at one problem), and decide what the theme off-switch means now that Q8 puts the
   RTS vocabulary in the Rust domain model, where a 28-line theme file cannot rename an enum
   variant.
2. **What the console must show.** Live task DAG, per-agent state, queue depth, escalation events,
   token + cost per task and per run, model-server health, throughput over time. ⚠ Most of this
   exists in V1 *as layout*; `TokenBurnLog`'s data path has never rendered a real number, so treat
   "V1 already has this surface" as a claim about design, not about behaviour under load.
3. **Observability prior art** — Langfuse, Arize Phoenix, OpenTelemetry GenAI semantic conventions,
   current agent-ops products. The brief pre-judges the UI layer ("a pure adopt-Langfuse answer is
   wrong"), so the live question is what comes free at the tracing and storage layer underneath.
4. **Transport and storage.** WebSocket vs SSE at 2.0's event volume; PostgreSQL vs SQLite. F95
   already loads the dice on storage, and `inheritance-map.md` §7 notes Claudette's `recall.sqlite`
   as the precedent. Also in scope: a **paged read path for replay** — V1's store is a 500-row ring
   buffer over a database that holds everything.
5. **§7's fun research, grounded.** Developer-tool ergonomics, flow, feedback latency: what the
   literature and the good tools actually do, rather than taste. Plus the written position on what
   "fun" means here, concrete enough to test.
