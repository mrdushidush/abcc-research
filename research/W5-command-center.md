# W5 — The command center and the fun layer

**Status: WRITTEN — all seven items, 2026-08-18.** The file was built one item at a time and reads
in that order; each item carries its own Question / Method / Findings / Recommendation / Rejected /
Effect on fun / Open questions / Confidence, per §13.

1. ✅ **Frontend architecture** (F93–F99) — §11's "big open question". Answered; David accepted the
   recommendation 2026-08-18.
2. ✅ **What the operator must be able to do** (F100–F106) — §11's "the genuinely new work", and
   where §14 item 3 says W5's extra room should go.
3. ✅ **The component inventory, new versus inherited** (F107–F113) — the brief's second named
   deliverable. Corrects `inheritance-map.md` in three places.
4. ✅ **What the console must show** (F114–F118) — §11's seven-item list against §7's "six things
   clearly".
5. ✅ **Observability prior art** (F119–F122) — Langfuse, Phoenix, the OTel GenAI conventions.
   Adopt the vocabulary, own the store, export optionally.
6. ✅ **Transport and storage** (F123–F126) — SSE + SQLite, and one integer that is the transport
   cursor, the SQL cursor and the scrub position.
7. ✅ **Fun, grounded and made testable** (F127–F130) — the written position, as six queries over the
   event log.

Plus an **addendum** (F131–F139), added the same day: the Ratatui / Bubble Tea / Textual comparison
§11 wrongly said already existed, run from scratch by four parallel researchers — and the shipped-
agent evidence around it, which corrects F94 and adds three verbs to item 2.

🚨 **And a DECISION (F140–F141), taken by David 2026-08-19: the TUI is primary and the web console is
dropped for now — a C&C-1995-style Ratatui console is the flagship component.** This **reverses item
1's primacy**; see the re-scope section immediately before the handoff table for what it does to
items 2–7. Next session runs the sixel spike.

**All three of §11's named deliverables exist:** this file, the component inventory (item 3), and
the written position on what "fun" means (item 7, F129).

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
findings."* Those findings are not in this repo, and not in `prestudy/`.

> ✅ **Resolved 2026-08-18 — the premise was false.** Asked directly, David: *"i did not research
> Ratatui, Bubbletea and Textual."* There were never any findings to start from. `RESEARCH_BRIEF.md`
> §11 has been corrected in place, and the three frameworks were researched from scratch the same
> day — see the addendum at the end of this file. **OQ-W5-5 is closed.**

What the search did turn up is a different document, and it is worth keeping:

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

> ⚠ **Corrected 2026-08-18 by F136 (addendum).** "A TUI cannot show a painted battlefield" is too
> strong: Windows Terminal supports sixel, and OpenAI's Codex CLI ships animated sprites in the
> terminal. But the capability is palette-reduced to 256 colours and **dies under tmux and over
> SSH** — i.e. it exists exactly where the web console is already available, and not in the case the
> TUI is deferred for. The conclusion holds; the absolute phrasing does not.

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
- ~~**OQ-W5-5 — did a Ratatui / Bubbletea / Textual comparison ever exist beyond the March brief?**~~
  ✅ **ANSWERED 2026-08-18 — no.** David: *"i did not research Ratatui, Bubbletea and Textual."* The
  brief's premise was false; it has been corrected in place, and the comparison was run from scratch
  (see the addendum).

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

> ➕ **Extended 2026-08-18 by F138 (addendum).** Four shipped agents have now specified the verbs
> this section called least-specified, and two of their answers were missing above. **Add
> stop-but-keep-the-work** — Claude Code's `Esc` stops generating and retains the artefacts, which is
> neither kill nor pause and is what an operator wants most often. **Add queue-while-streaming** —
> type during a turn, land at the next boundary — which is take-over's cheap first step and needs no
> checkpoint machinery. F133 also supplies a scoped persistent grant key worth copying.

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

# Item 3 — the component inventory, new versus inherited

§11: *"What survives from V1's console verbatim, what gets ported, what gets rebuilt. Inventory the
existing assets, including the 96 Bark voice lines, **before designing new screens**."* This is the
brief's second named deliverable.

## Question

Of V1's 14,935 lines and 44 MB of assets, what is 2.0 actually inheriting — and what does the brief
ask for that has no V1 equivalent at all?

## Method

Every component enumerated with `wc -l` from `D:\dev\agent-battle-command-center` at `d5528ea`,
this session, then read where the verdict depended on behaviour rather than size.
`prestudy/inheritance-map.md` §8 already carries per-component REUSE/PORT/REFERENCE/DROP verdicts
from Phase 0; this section is the layer on top that the map defers to W5 — **the decisions** — and
it corrects the map in three places (F108, F110, F112).

## The inventory

Verdicts: **PORT** = the design and code carry over onto a Rust backend · **REUSE** = copied
essentially as-is · **REBUILD** = the surface stays, the implementation does not · **REFERENCE** =
read it, do not carry it · **DROP** · **NEW** = the brief asks for it and V1 has nothing.

### Inherited — identity (the part that makes it ABCC)

| Surface | Lines / size | Verdict | Decision |
|---|---|---|---|
| `isometric/` renderer + `isoProjection.ts` | 1,298 / 8 files | **PORT** | The live renderer. Fix on port: pre-blur the firing glow (`filter: blur()` doubles frame cost at N=100) |
| Art — sprites, backdrops, fonts | 35 MB + 2.3 MB | **REUSE** | Irreplaceable. ⚠ 34.3 MB of the sprites is four attacking GIFs; see OQ-W5-10 |
| 96 Bark voice lines | 6.7 MB, 3 packs × 32 | **REUSE** | Copy the files. `bark-generate-all.py` REUSE for extending the set |
| `audioManager.ts` + `voicePacks.ts` | 229 + 271 | **REBUILD** | Queue *policy* is the problem, not the playback (F112) |
| `themes/` vocabulary map | 105 / 3 files | **PORT** | ~28 lines each, `classic.ts` is the off-switch. Collides with Q8 — see OQ-W5-11 |

### Inherited — surfaces that work and carry over

| Surface | Lines | Verdict | Decision |
|---|---|---|---|
| `ToolLog` terminal feed | 205 | **PORT** | The no-dead-air surface that actually ran |
| `minimap/` — three styles | 616 / 3 | **PORT one, keep two** | Not three abandoned attempts — a user setting (F108) |
| `SuccessRateChart`, `ComplexityDistribution`, `AgentComparison` | 644 | **PORT** | Hand-rolled `<svg>`, no charting library — keep that instinct |
| `TaskQueue`, `TaskDetail`, `ActiveMissions`, `TaskCard`, `AgentCard` | 1,543 | **REBUILD** | The shapes are right; the code is welded to V1's REST + socket API |
| `CodeWindow`, `CodeReviewPanel` | 375 | **PORT** | Feeds W6's gate output |
| `MemoryApproval` | 205 | **PORT as a pattern** | An async approval *queue* — gates knowledge, not execution (F110) |
| `AlertPanel`, `ResourceBar` | 190 | **PORT** | Partial answer to "model-server health" |
| `TopBar`, `Sidebar`, `CommandCenter`, `ThemeSelector` | 744 | **REBUILD** | Layout survives, wiring does not |
| `useKeyboardShortcuts` + `ShortcutsHelp` | 201 | **PORT** | Cheap, and operator control needs a key map |
| `useSocket.ts` event taxonomy | 456 | **PORT the taxonomy, break the coupling** | 26 domain events; the feel is fused into the transport |
| `SettingsModal` | 368 | **REBUILD** | Personality off-switch lives here |

### Inherited — not carried

| Surface | Lines | Verdict | Why |
|---|---|---|---|
| `battlefield/` React Three Fiber | 2,133 / 12 | **REFERENCE** | V1 calls it *"legacy"* itself (F96); source of motifs |
| `chat/` panel, `CTOWelcome`, `MissionProgressTracker` | 904 / 5 | **REFERENCE** | Overlaps the conversational surface Claudette already owns |
| `TokenBurnLog` | 322 | **REBUILD** | Layout proven, data path never ran — no human has seen it render a real number |
| `CostDashboard` | 280 | **REBUILD** | Starved by the same dead column; degrades to zeros |
| `api/client.ts`, `store/uiState.ts`, remaining hooks | 2,646 | **REBUILD** | The V1 backend contract does not survive |
| BCF `snake.rs` / `space.rs` minigames | — | **REFERENCE** | Right instinct about dead air, wrong answer |
| BCF macOS `say` voice | — | **DROP** | macOS-only, dead on this hardware |

### NEW — the brief asks for it and V1 has nothing

| Surface | Why it is new |
|---|---|
| **Operator control bar** — the eight verbs | Nothing in the family has them; only the terminal has any (F98) |
| **Permission + redirect modal** | Must carry `Allow \| Deny \| Redirect(String)` (F106) |
| **Replay transport** — cursor, scrub, fork | Replay is the primary read path (F105); V1 never built a paged read |
| **Live task DAG** | 🚨 V1 has no dependency edges at all (F109) |
| **Escalation events** | No routing tier exists to escalate between yet (W4) |
| **Model-server health / swap cost** | The 23.77 s swap (W1 F79) has to be visible before a re-route commits |
| **Per-task and per-run cost accounting** | New instrumentation, not a ported metric — the columns were never writable |

## Findings

### F107 — only about an eighth of the console is the thing that makes it ABCC

Of 14,935 lines: `isometric/` 1,298 + `audio/` 500 + `themes/` 105 = **1,903 lines, 12.7%**. The
other 87% is task CRUD, dashboards, chat, layout, hooks, an API client, and a deprecated 3D
renderer — most of it coupled to a Node + Postgres + Redis backend that does not survive (F95).

**The irreplaceable asset is not the code, it is the 44 MB.** The art and the voice lines took work
that cannot be redone cheaply; the CRUD took work that a Rust backend invalidates anyway.

**Consequence for planning:** "port the console" reads like 15k lines of work and is not. It is
~1.9k lines of identity to port carefully, ~44 MB to copy, and a CRUD layer that should be
**rebuilt against the new contract rather than ported** — because porting it means preserving V1's
API shape, which is the one thing 2.0 is deliberately replacing.

### F108 — the three minimaps are a user setting, not three abandoned attempts

`inheritance-map.md` §8 records them as *"Three attempts at one problem. Pick one deliberately in
W5."* Read in the store this session, that is not what they are:

```ts
interface Settings {
  toolLogOpenByDefault: boolean;
  minimapStyle: 'timeline' | 'grid' | 'flow';
}
```

Three deliberate styles over the same data, switchable at runtime, all three reading `tasks` from
the same store with the same status→colour map. And "flow" does not mean a graph: `FlowMinimap` is
a **status kanban** — QUEUE / ASSIGNED / ACTIVE / BLOCKED / COMPLETE / FAILED — over tasks from the
last 24 hours, with `failed` and `aborted` collapsed into one column.

**Decision, and it is settled by F105 rather than by taste:** keep **timeline** as the default,
because under replay-as-primary the timeline *is* the cursor — the scrub bar and the minimap are
the same widget. Keep **grid** (the circular radar sweep) as the idle/identity view. **Drop flow**:
a status kanban is what the task queue already shows, and once there is a real DAG (F109) a kanban
is the weaker picture of the same thing.

### F109 — 🚨 V1 has no task DAG, and the brief's first "must show" item is therefore new work

The brief's list of what the console must show opens with *"live task DAG"*. The V1 store carries
`subtaskCount?: number` and **no dependency edges of any kind**; a grep for `depend` / `dependsOn`
/ `parentTask` across the minimaps and the store returns nothing but that one count. What V1 models
is a mission fanning out into subtasks — a one-level tree, and only its width is retained.

None of the three minimaps draws edges (F108). So the DAG is **NEW**, it depends on W3's domain
model carrying real dependency edges, and W5 should say so rather than budgeting it as a port.

### F110 — the console does have a human-approval surface, and it gates knowledge rather than execution

Refines F98 rather than contradicting it. `dashboard/MemoryApproval.tsx` (205 lines) polls
`/api/memories/pending` and `/api/memories/stats` and lets the operator approve agent-proposed
memories — `{pattern, solution, errorPattern, keywords, successCount, failureCount, approved,
proposedByAgent, proposedByTask}`.

That is a real human-in-the-loop surface, but it is **asynchronous and post-hoc**: nothing blocks
on it, no agent waits, and approving late costs nothing. It is a review queue, not a gate. F98's
claim stands as stated — no *mid-run* control in the console — and this adds the shape that W6's
independent-review output should land in, since W6's gate produces exactly this kind of
"proposed, awaiting a human" record.

### F111 — the edit surface exists and is deliberately partial, in exactly the place F103 predicted

`main-view/EditTaskModal.tsx` (155 lines) edits a task's title and description. Type and required
agent are rendered `disabled` under the comment *"Type and Agent (read-only for existing tasks)"*.

So of F103's verb table, **"edit a task prompt" is half-inherited** — the surface exists, and it
edits a queued task's text — while **"re-route to another tier" is absent by construction**: the
one field that would express it is the one V1 froze after creation. Neither is a mid-run operation.

### F112 — the no-dead-air mechanism has three independent drop policies, and it degrades exactly when there is most to say

This closes the `audioManager.ts` queueing item `verification.md` §3.5i left open, and establishes
the cause of **both** OOM-fix comments that pass could not explain.

Three bounded queues sit between an event and a voice line:

1. **`useSocket.ts`** — a 3 s anti-overlap window, plus `MAX_PENDING_TIMEOUTS = 5`: *"Track pending
   audio timeouts to prevent accumulation (OOM fix)"*. Past five, the sound is **dropped**.
2. **`audioManager.ts`** (229 lines) — a priority queue **capped at 10**: *"Cap queue size to
   prevent unbounded growth (OOM fix)"*, discarding the lowest-priority entry, then sorting by
   priority descending.
3. **Playback is strictly serial** — one `currentAudio`, one sound at a time.

And the second OOM comment's cause, from `store/uiState.ts:7-10`: `MAX_EXECUTION_LOG_BUFFER = 500`
is *"WebSocket-driven; replaces the 10s HTTP polling pattern that previously caused OOM on the
frontend."* Both scars are now explained: one from polling, one from audio timers.

**The finding is not that the caps are wrong — they are right.** It is that all three degrade in
the same direction under the same condition: **the busier the fleet, the more the console goes
quiet.** §7 asks for no dead air; V1's mechanism produces its worst silence at peak activity, and
does it in three places with three different policies. 2.0's audio subscriber needs **one** policy,
stated deliberately — most likely "collapse to a summary line rather than drop", since the operator
needs to know a burst happened more than they need to hear each event in it.

### F113 — four of the eleven task states have no colour, in three places

`STATUS_COLORS` is defined independently in all three minimaps, covering seven states: `pending`,
`assigned`, `in_progress`, `needs_human`, `completed`, `failed`, `aborted`. The lifecycle actually
in use has **eleven** (`verification.md` §3.4g adds `decomposing`, `awaiting_approval`, `reviewing`,
`approved`).

So four states render with no defined colour, and the mapping from domain state to visual state is
duplicated three times and owned by no one — the same untyped-lifecycle problem as `verification.md`
§3.4g, showing up in the view layer. Under Q8's typed enum this becomes one exhaustive `match`, and
a new state cannot be added without the compiler asking what colour it is. **This is the cheapest
concrete argument for the Q8 ruling that W5 can offer, so it is worth handing to W3.**

## Recommendation

1. **Copy the 44 MB, port the 1,903 lines of identity, rebuild the CRUD** (F107). Do not treat the
   line count as the work.
2. **Minimaps: default timeline, keep grid, drop flow** (F108) — the timeline is the replay cursor,
   so this decision is downstream of F105 and not a matter of preference.
3. **Budget the DAG as new work with a W3 dependency** (F109). It is the brief's headline "must
   show" item and the family has nothing to port.
4. **One audio policy, stated deliberately, replacing three drop policies** (F112). Collapse-to-
   summary rather than drop, so a busy fleet gets louder rather than quieter.
5. **Hand W3 two W5-sourced requirements:** the lifecycle enum must be exhaustively renderable
   (F113), and it must carry dependency edges (F109).
6. **Keep `MemoryApproval`'s shape** as the landing surface for W6's independent-review output
   (F110).

## Rejected alternatives and why

- **Porting `store/uiState.ts` and `api/client.ts`.** Rejected: 1,113 lines whose entire job is
  speaking V1's backend contract, which 2.0 replaces. Rebuilding is cheaper than adapting.
- **Keeping all three minimaps because they are already written.** Rejected: three renderings of one
  data set is three places to update every time the lifecycle changes — F113 shows that cost is
  already being paid.
- **Carrying `audioManager`'s queue as-is.** Rejected on F112: the playback singleton is fine, the
  three-layer drop policy is the bug, and porting it would import the silence-at-peak behaviour.
- **Rebuilding the isometric renderer "properly" on canvas.** Rejected: §11.0 closed this — DOM
  sprites are free to ~100 entities, and W2 F83 caps the useful fleet at 2.

## Effect on fun

- **The 44 MB is the fun, and it is the cheapest thing to keep.** Naming that explicitly protects it
  from being traded away during a rewrite that is mostly about backends.
- **F112 is a direct fun regression in the inherited design** — the console's personality fades out
  precisely when the battle is busiest. Fixing the policy is a small change with a large felt effect.
- **A DAG the operator can see is the difference between a queue and a battle plan** — and it is the
  one "must show" item that has to be built rather than inherited.

## Open questions

- **OQ-W5-10 — do the four attacking GIFs survive?** 34.3 MB of 35 MB, 242 frames for the building
  alone. Frame cost measured at zero; **decode memory never measured** (`verification.md` §3.5i). If
  they stay, 2.0 ships a 44 MB binary or a 44 MB sidecar directory (OQ-W5-4).
- **OQ-W5-11 — what does the theme off-switch mean after Q8?** `classic.ts` renames vocabulary in a
  28-line file; an enum variant cannot be renamed by a theme. Labels-only translation over fixed
  enums, or a cosmetic-only neutral theme.
- **OQ-W5-12 — does the chat panel come back?** Marked REFERENCE because Claudette owns the
  conversational surface, but item 1 puts the terminal in that role. If the console has no chat, the
  operator's "type at it" path is terminal-only by design rather than by omission.

## Confidence: high

Every verdict traces to a file read this session or to an executed Phase 0 pass. The three
corrections to `inheritance-map.md` (F108, F110, F112) are each backed by the source line that
contradicts the earlier note. **What would lower it:** OQ-W5-10 — if GIF decode memory turns out to
be prohibitive, the art inventory changes shape, and that is the one row in this section resting on
an unmeasured quantity.

---

# Item 4 — what the console must show

§11's list: *"live task DAG, per-agent state, queue depth, escalation events, token and cost
accounting per task and per run, model server health, throughput over time. Most of this exists in
V1 in some form."* Against §7's constraint: *"Legibility over completeness. A dashboard that shows
six things clearly beats one that shows forty."*

## Question

Those two sentences are in tension — the list has seven items before anything is added for operator
control or replay. What does the operator see at a glance, what gets demoted, and which of the
seven turn out to mean something different than they did when the brief was written?

## Method

Each item on §11's list checked against what actually exists: V1's components (item 3), the
measured hardware numbers from W1 and W2, and this repo's own `harness/crates/hw-probe`. Where the
brief's phrasing predates a decision that changed its meaning, the decision is named.

## Findings

### F114 — "cost accounting" cannot mean money, because the spend ceiling is zero by decision

§11 asks for *"token and cost accounting per task and per run"*. Q4 (2026-08-07) set the frontier
spend ceiling at **effectively zero — local only, cloud escalation manual and rare**. So the dollar
column on a single-player run is **0.00, correctly, forever**, and a cost panel that leads with it
is a panel that leads with a zero.

This is a different failure from V1's, and worth separating: V1's `CostDashboard` and `TokenBurnLog`
render zeros because the token, cost and model columns were never writable (`verification.md`
§3.4h). 2.0 would render an honest zero for a real reason. **Both produce a dead panel.**

What is actually scarce on this hardware, and therefore what "cost" has to mean:

| Resource | Why it is the real cost | Number to show against |
|---|---|---|
| **Wall clock** | The only budget the operator personally spends | per task and per run |
| **Tokens** | Prefill dominates: the workload is ~**27.8:1** prefill:decode (§14 item 2) | in / out, per task |
| **GPU occupancy** | Useful concurrency is **2** (W2 F83) — a slot is the scarce unit | slot-seconds per task |
| **Model swaps** | **23.77 s** round trip (W1 F79), and a re-route buys one | count, and seconds lost |

**Consequence:** replace "cost" with **time, tokens, slots and swaps**, and keep a currency column
only for the rare manual cloud escalation, where it is genuinely non-zero. This also rescues the
inherited panels — `TokenBurnLog`'s layout is fine, it was starved; feeding it wall-clock and tokens
gives it something true to render for the first time (item 3 marks it REBUILD for this reason).

And it hands W8 the same reframing: cost-per-task in this family has never been measurable, so it
is new instrumentation either way — and the version worth instrumenting is the one denominated in
seconds.

### F115 — 🚨 liveness is not a status field, and this project has already been fooled by silence once

V1 shows agent state as `busy` / `idle` / offline. That is a *state*, and it cannot distinguish
working from hung — which is the exact mistake this repo already made and recorded.

W1 F91: a cell timed out with an almost-empty transcript and was first read as "the model produced
nothing". It was not. The fix (`25afec2`) added two fields, and the comment on them is the whole
lesson:

> *"Claudette echoes a `▸` line for file mutations only, so a subject that spends its whole budget
> reading the repository prints nothing at all — and a timeout with an almost-empty transcript then
> looks identical to a hang. It is not: the first cell this hit had 20 chat completions behind it in
> the server log."*

`subject_last_output_ms` is the decisive field and `subject_output_bytes` the corroborating one —
and even then the comment warns that the banner alone puts ~180 bytes on stderr, so a small total
is not by itself a silent cell.

**Two things follow for the console.**

1. **Time-since-last-event is a first-class, always-visible element** — not a tooltip, not a
   derived value in a chart. §7's "no dead air" is not satisfied by an animation; it is satisfied by
   a number the operator can trust to distinguish *thinking* from *stuck*.
2. **2.0 must not repeat the harness's inference.** The harness had to guess liveness from stray
   bytes on a pipe *because it was outside the process*. The console is inside it: the broker (F99)
   already carries `ToolCallStart` / `ToolCallDone` / `Token`, so 2.0 can emit an event for reads as
   well as writes and know liveness rather than infer it. **The inherited limit — narrating
   mutations only — is a property of watching someone else's binary, not a property of the design.**

### F116 — legibility resolved: two screens, and replay makes the second one nearly free

§11's seven items plus operator control plus replay is far past §7's "six things clearly". The
resolution is not to cut the list; it is to notice that it contains **two different jobs**.

**The battle screen** answers six questions, and nothing else earns space:

| # | Question | Surface | Source |
|---|---|---|---|
| 1 | Is anything happening *right now*? | liveness — time since last event | **NEW** (F115) |
| 2 | What is it doing, in words? | `ToolLog` feed | PORT |
| 3 | How much is left? | DAG + queue depth | **NEW** (F109) |
| 4 | What has it cost me so far? | elapsed, tokens, slots, swaps | **NEW** (F114) |
| 5 | Is anything wrong or waiting for me? | failures, permission prompts, `needs_human` | PORT + **NEW** |
| 6 | What can I do about it? | the control bar | **NEW** (item 2) |

**The after-action screen** takes everything else: success rate over time, complexity distribution,
agent comparison, throughput history, per-run cost. All four inherited charts (item 3) live here,
and none of them belongs on the battle screen — a chart of historical success rate tells the
operator nothing about the run in front of them.

**And it is nearly free.** Under F105 replay is the primary read path, so the after-action screen is
the same renderer with the cursor parked at the end of a finished run. The design does not pay twice.

Note the shape of the table: **four of the six are NEW.** The console 2.0 needs is not mostly a port
even though the console V1 has is mostly built — which is the same conclusion item 3 reached from
the other direction (F107).

### F117 — the fleet is two, and the inherited visual grammar already survives that

W2 F83 caps useful concurrency at **N=2**. An RTS console commanding two workers sounds like a
problem for the identity — an army of two.

It is not, because V1's battlefield does not draw the fleet as the army. Read this session,
`IsometricBattlefield.tsx` maps **tasks → buildings** and **agents → squads** that target them:
`buildings.find(b => b.taskId === squad.targetTaskId)`, building size from
`complexity ?? priority ?? 5`, an explosion spawned per finished task keyed on `task.status ===
'completed'`, and the backdrop rotating every 10 tasks.

So the battlefield already reads as *a small strike team working a large objective list* — few
tanks, many buildings — which is exactly the shape of the real workload. **"Per-agent state" is a
two-row table; the screen space belongs to tasks.** That is a legibility win, not a compromise: the
thing the operator cares about is the queue, and the inherited art already points the camera there.

### F118 — model-server health is already built, in this repo, and its two documented limits bite a long-running console

§11.0 recorded that nothing in the family measures peak VRAM, peak RAM or temperature — `hw.rs` is
`nvidia-smi --query-gpu=memory.total`, read once. That gap is **closed**: `harness/crates/hw-probe`
exists and describes itself as *"peak VRAM, peak system RAM, temperature and throttle, around any
workload"*, built for §14 item 2. GPU sampling is one long-lived `nvidia-smi -lms N` including
`temperature.gpu`; host sampling is one long-lived `typeperf` over PDH counters.

So the health panel is **inherited from 2.0's own harness**, not new. Two limits its source
documents are the ones that matter for a console rather than for a benchmark:

1. **The host series floors at one second** — `-si` takes whole seconds and `-si 0.25` is rejected,
   so RAM is an order of magnitude coarser than the GPU series. The panel must show two cadences or
   it lies about one of them.
2. 🚨 **`typeperf` resolves wildcards once, at start** — `\GPU Process Memory(*)\…` expands to the
   processes alive when it starts, *"and a process that appears later never gets a column"*. LM
   Studio spawns a **fresh `llama-server` per load** (W1 F75), so **every model swap invalidates the
   per-process column** of a probe that started earlier.

Item 2 makes re-route a first-class operator verb, which means swaps happen *on purpose*, mid-run,
at the operator's command. A health panel that silently loses its per-process column after the
first re-route is `TokenBurnLog`'s failure mode again — a panel that renders confidently and means
nothing. **The probe must be restarted around a swap, and the console must show which process the
numbers belong to.**

## Recommendation

1. **Two screens.** The battle screen answers the six questions in F116 and shows nothing else; the
   after-action screen is the same renderer with the replay cursor at the end, and it takes all four
   inherited charts.
2. **Liveness first.** Time-since-last-event is always on screen, sourced from the broker rather than
   inferred (F115). If one element survives a redesign, it is this one.
3. **Cost is time.** Elapsed, tokens (in/out), slot-seconds and swap count — with a currency column
   only when a manual cloud escalation actually happened (F114).
4. **Screen space follows tasks, not agents** (F117). Per-agent state is two rows; the queue and the
   DAG own the canvas.
5. **Feed health from `hw-probe`, restart it around every swap, and label the process** (F118).
6. **Escalation events are deferred to W4's shape.** With spend at zero the ladder is local and C10
   is a manual act, so the console shows *swaps and re-routes*, which are real today, rather than a
   tier ladder that does not exist yet.

## Rejected alternatives and why

- **One dashboard with everything.** Rejected on §7 and on F116's split: the two jobs have different
  time horizons, and merging them is how the live screen fills with history.
- **A dollar-denominated cost panel.** Rejected on F114 — it is a zero by decision, and a panel whose
  headline number is always zero trains the operator to stop reading it.
- **Prominent per-agent telemetry.** Rejected on F117: two rows do not deserve the canvas, and V1's
  own art already points elsewhere.
- **Reusing `hw.rs` for health.** Rejected: it reads *installed* VRAM once and has no peak, no
  temperature and no RAM. `hw-probe` supersedes it and is already written.
- **A "thinking…" spinner as the no-dead-air answer.** Rejected on F115 — a spinner is exactly the
  animation that cannot tell working from hung, and this project has already paid for that mistake.

## Effect on fun

- **The six-question screen is the "glance and know the front line" test from §7**, made concrete
  enough to check: if the operator cannot answer all six in one look, the screen has failed.
- **The liveness number is the anti-dead-air feature**, and it is more honest than the voice lines:
  it says *something is happening* even when nothing is worth narrating.
- **Cost in seconds is the number a hobbyist actually feels.** Dollars are someone else's metric on
  a local rig; "this run has eaten eleven minutes and two model swaps" is the one that changes
  behaviour.
- **The after-action screen is where a failed run becomes interesting to look at** — §7 asks for
  exactly that, and replay-as-primary is what makes it possible.

## Open questions

- **OQ-W5-13 — what is the liveness threshold before the console escalates from quiet to concerned?**
  W1 F91 saw a genuinely silent 40 minutes of real work. A warning at 60 s would have cried wolf; no
  warning at all is how a hang hides. Needs a number, ideally learned from W8 runs.
- **OQ-W5-14 — does the battle screen show one run or the whole fleet?** With N=2 they nearly
  coincide, but "replay a run" implies a run-scoped view, and a queue implies a global one.
- **OQ-W5-15 — where does the DAG live on screen?** It is question 3 of six and the most
  space-hungry element; the isometric battlefield may already *be* the DAG view if buildings gain
  edges, which would be cheaper and more in character than a second graph widget.

## Confidence: high on the demotions, medium on the six

- **High** on F114, F115, F117, F118 — each rests on a decision already made, a source file read
  this session, or a measured number from W1/W2.
- **Medium** on the exact membership of the six (F116). The split into two screens is forced; which
  six questions make the cut is a design judgement that only Phase 3 use can confirm. **What would
  raise it:** W8 measuring which surfaces the operator actually looks at, and OQ-W5-13's threshold
  coming from real runs rather than from taste.

---

# Item 5 — observability prior art

§11: *"Prior art on agent observability and control: Langfuse, Arize Phoenix, OpenTelemetry GenAI
semantic conventions, current agent-ops products. What they give for free at the tracing and storage
layer. Note that no generic observability tool will ever give the RTS console, so a pure 'adopt
Langfuse' answer is wrong at the UI layer even if it is right underneath."*

## Question

The brief has already ruled the UI layer. So: **is any of this right underneath?** 2.0 needs an
event log, a paged read path and per-call token accounting (items 2 and 4). Those are exactly what
an LLM-observability stack gives away. Does adopting one save real work?

## Method

Vendor documentation and the OpenTelemetry registry, retrieved 2026-08-18, read against two
constraints this project has already fixed: the hardware (32 GB RAM, 13.6 GB of VRAM already spent
on a resident model) and the install story (F95 — one verified `.exe`, no docker-compose).

## Findings

### F119 — 🚨 self-hosting Langfuse costs more RAM than the model it would be watching

Langfuse v3 self-hosted is **six services**: `langfuse-web`, `langfuse-worker`, ClickHouse, MinIO
(S3-compatible blob storage), Redis 7, and PostgreSQL 17, with the worker declaring
`service_healthy` dependencies on four of them. Recommended resources, per the vendor's own
infrastructure guide: worker 2 CPU / **4 GiB**, PostgreSQL 2 CPU / **4 GiB**, Redis 1 CPU /
**1.5 GiB**, ClickHouse 2 CPU / **8 GiB**, MinIO 2 CPU / **4 GiB**.
([Langfuse self-hosting](https://langfuse.com/self-hosting),
[docker-compose.yml](https://github.com/langfuse/langfuse/blob/main/docker-compose.yml),
[ClickHouse guide](https://langfuse.com/self-hosting/deployment/infrastructure/clickhouse),
retrieved 2026-08-18)

That is **≈21.5 GiB of recommended memory, on a 32 GB box**, to observe an agent whose own budget is
13.6 GB of VRAM and whose useful concurrency is two (W2 F83). And it is precisely the multi-service
docker-compose that F95 rules out — the same shape as V1's postgres + redis + ollama stack, which is
the thing 2.0 is escaping.

**This is not a quality judgement.** Langfuse is built for teams shipping cloud LLM products, and its
architecture is proportionate to that. It is disproportionate here by roughly the size of the model.

### F120 — Phoenix is right-sized, and still redundant for the same reason

Arize Phoenix is the honest counter-example: `docker run -p 6006:6006 arizephoenix/phoenix:latest`,
**SQLite by default**, no additional infrastructure, data under `~/.phoenix/` or
`PHOENIX_WORKING_DIR`. Documented caveats: without a mounted volume a container restart loses the
data, and concurrent writes are limited.
([Phoenix hosting + persistence](https://phoenix.arize.com/how-to-host-phoenix-persistence/),
retrieved 2026-08-18)

One container and a SQLite file is a footprint this project could actually carry — and it still
should not, for a reason that has nothing to do with weight.

Under F105, **2.0's own event log is the store of record**: replay is the primary read path, and the
console renders by projecting that log. Adopting Phoenix underneath would create a *second* record
of the same run, in a different schema, owned by a different process. The console would then either
read the copy (and diverge from the authority) or read the authority (and make Phoenix decorative).
**A trace store you do not read from is not infrastructure you adopted; it is a mirror you now
maintain.**

Where Phoenix does earn a place: as an **optional export target** for someone who wants eval
tooling, dataset management and a familiar trace UI. That is a feature flag, not a foundation.

### F121 — adopt the vocabulary, not the stack — and the half 2.0 needs most is the least settled

The OpenTelemetry GenAI semantic conventions are the one item on the brief's list that costs nothing
to adopt, because they are **naming, not software**. Status as of this session:

- As of **v1.42.0 (12 June 2026)** all `gen_ai.*` attributes and spans moved out of the main
  semantic-conventions repository into a dedicated GenAI conventions repository, giving them their
  own release cadence.
- As of **mid-July 2026, every `gen_ai.*` attribute, span, metric and event carries the
  "Development" stability badge — not one is marked Stable.**
- Core chat and embedding attributes are considered settled enough to build on; **agent and
  tool-orchestration conventions are still moving** and should be treated as provisional.
  ([state of the GenAI conventions, July 2026](https://john-hodge.com/blog/opentelemetry-genai-semantic-conventions/),
  [OTel GenAI observability](https://opentelemetry.io/blog/2026/genai-observability/), retrieved 2026-08-18)

The attributes worth taking verbatim map one-to-one onto what item 4 already decided to show:
`gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`,
`gen_ai.response.finish_reasons`.

**The catch is the ordering.** The settled half is single-call chat telemetry; the unsettled half is
agents and tool orchestration — which is the half 2.0 is *made of*. So the rule is: **name the
fields that already have names, pin the convention version in the docs, and do not wait on the
agent-level conventions to settle before designing the event log.** They will change; 2.0's log
should not be hostage to that.

### F122 — the Rust side inverts the usual maturity order, and it inverts against this project

Two facts, and together they close the "adopt it underneath" question.

**First, the SDK.** On the 0.32 release line, `opentelemetry-rust` shipped **logs and metrics stable
before traces** — the reverse of Go, Java and most other languages, where traces stabilised first.
The ecosystem's bridge is the `tracing` crate: existing `tracing` spans become OTel spans through
subscriber layers.
([opentelemetry-rust](https://github.com/open-telemetry/opentelemetry-rust),
[OTel Rust exporters](https://opentelemetry.io/docs/languages/rust/exporters/), retrieved 2026-08-18)
**Traces are what a run console is,** so the least-mature component of the Rust implementation is
the one 2.0 would depend on hardest.

**Second, the donors' posture.** Neither donor carries `tracing` or `opentelemetry` at all.
Claudette's dependency list is deliberately short (`reqwest`, `serde`, `serde_json`, `chrono`,
`toml`, `anyhow`, `colored`, …), it ships `default = []` so no cloud code is compiled in, and it
describes itself as *"privacy-first, air-gapped… single-binary Rust CLI + TUI"*. This repo's own
harness is stricter still: `w8-import` has **zero** third-party dependencies, `w8-corpus` took `toml`
as the workspace's *first*, and `w8-run` **hand-rolled an HTTP/1.1 client in ~90 lines** rather than
take an HTTP dependency.

Adopting the OTel Rust stack would import the immature half of a large dependency tree into a
project whose two ancestors both treat dependencies as a cost to be argued for. **That is a real
mismatch, and it is the reason to take the convention and leave the crates.**

## Recommendation

**Adopt the vocabulary. Own the store. Export optionally.**

1. **Name the event log's fields after `gen_ai.*` where a name already exists** (F121), and pin the
   convention version in the docs so a future rename is a decision rather than a surprise.
2. **2.0's own event log is the store of record** (F105, F120) — SQLite-shaped, single-binary,
   readable by the console's paged read path. No second store.
3. **OTLP export is an optional, non-default feature**, mirroring Claudette's `default = []` air
   gap: someone who wants Phoenix or a collector gets one, and the default build has no telemetry
   path compiled in at all. This also keeps W7's structural guarantee intact rather than degrading
   it to a runtime toggle.
4. **Do not adopt Langfuse** (F119). Record the reason as arithmetic, not taste, so it is not
   revisited as a preference: ~21.5 GiB recommended against 32 GB total, on a box where the model
   already holds 13.6 GB of VRAM.
5. **Keep Phoenix on the reading list** as the design reference for what an eval + dataset + trace
   UI looks like when it is right-sized — it is the closest thing on the market to the after-action
   screen (F116), and worth stealing layout ideas from.

**Sharpened restatement of the brief's own ruling:** the brief said a pure adopt-Langfuse answer is
wrong at the UI layer even if right underneath. On this hardware it is **also wrong underneath**,
and the thing that is right underneath is a specification rather than a service.

## Rejected alternatives and why

- **Langfuse self-hosted as the trace store.** F119 — the arithmetic.
- **Phoenix as the trace store.** F120 — right-sized, but it duplicates the store of record and the
  console would have to choose which copy to trust.
- **OTLP as the console's live transport.** Rejected: OTLP is an export protocol shaped for
  collectors, batching and sampling; a console needs low-latency ordered delivery of *domain* events
  (F99's broker), not spans. Exporting spans in parallel is fine; reading the console from them is
  not.
- **Waiting for the GenAI agent conventions to stabilise.** Rejected on F121 — they are the
  fastest-moving half and 2.0 cannot be blocked on someone else's release cadence.
- **A cloud-hosted observability tier.** Rejected on Q4 (spend ≈ zero) and on W7's air-gap posture.
  Prompts and completions leaving the box by default contradicts what Claudette's users were
  promised.

## Effect on fun

- **Nothing here is felt directly, and that is the point** — this is the layer that must not cost
  the operator anything. The felt consequence of getting it wrong is the install: five extra
  containers is a tool nobody opens on a Sunday.
- **Owning the log is what makes replay fun** (F105). A borrowed trace store makes the scrub bar
  someone else's feature with someone else's latency.
- **`default = []` for telemetry keeps the promise the donor made.** Part of ABCC 2.0's appeal is
  that it is *yours* and it does not phone home; an observability dependency that quietly changes
  that would cost more trust than the dashboard is worth.

## Open questions

- **OQ-W5-16 — which `gen_ai.*` version gets pinned, and where is it recorded?** The conventions
  moved repositories in June 2026 and are pre-stable; the pin belongs somewhere a future reader will
  actually look.
- **OQ-W5-17 — does the optional OTLP feature ship at all in the first release?** It costs nothing to
  design for and something real to test, and nobody has asked for it yet.
- **OQ-W5-18 — what is 2.0's own event schema versioning story?** Owning the store of record means
  owning migrations, which V1 outsourced to Prisma and Claudette avoids by keeping files.

## Confidence: high

Every number is from vendor documentation or the OTel registry, retrieved this session with URLs,
and the two constraints they are judged against (32 GB / 13.6 GB resident; single-binary install)
are already-settled facts of this project rather than preferences introduced here. **What would
lower it:** if the console's storage answer (item 6) turns out to need OLAP-shaped queries over
long histories, ClickHouse's presence in Langfuse's stack stops looking disproportionate and starts
looking like a warning.

---

# Item 6 — transport and storage

§11: *"Transport for live updates at higher 2.0 event volume: WebSocket versus SSE from a Rust
backend. Storage: PostgreSQL versus SQLite. SQLite plus a single binary is a dramatically lower
barrier for a public tool, and worth serious consideration against V1's Postgres dependency."*
Plus §14 item 3's addition: **a paged read path for replay.**

## Question

Three questions that turn out to be one: what carries live updates, what stores the record, and how
does the console read a run that already happened?

## Method

Volume arithmetic from measured numbers (W1 F80's throughput ladder, W2 F83's concurrency ceiling),
file sizes taken from the live `~/.claudette/` store on this machine 2026-08-18, V1's transport read
in source, and protocol documentation retrieved 2026-08-18.

## Findings

### F123 — the event volume is small, and it is large in exactly one place

"Higher 2.0 event volume" needs a number before it can drive a choice. Two granularities, and they
differ by orders of magnitude:

**Token granularity.** Decode runs 70.12–75.84 tok/s single-stream (W1 F80) and useful concurrency
is 2 (W2 F83), so the ceiling is roughly **150 tokens/second**. A 40-minute run — not hypothetical,
W1 F91 recorded one — is **~360,000 token events**. At even 50 bytes each that is ~18 MB of log for
one run.

**Action granularity.** Measured on this machine: `~/.claudette/transcript/actions.jsonl` is
**8,245,526 bytes across 16,150 lines** — ~511 bytes per line, with `input` already capped at 2,000
chars. That is **months of daily driving**.

**So persisting at token granularity costs more for a single run than the entire action log costs
over months of real use.** Which settles the design rather than the transport:

- **The broker streams tokens** — they are what makes the feed feel alive and what F115's liveness
  clock reads. Ephemeral.
- **The log persists turns, tool calls, state transitions and periodic liveness marks.** Durable.
- **Replay re-streams stored text; it does not store the stream.** The turn's text is written once;
  playback re-emits it with synthetic timing. The operator sees the same thing; the disk does not.

One more measurement, because it bounds what replay can promise. In this repo's own W8 runs, a
completed agentic cell's `transcript.log` is **1.9–4.1 KB** — while `runs/` on this disk totals
**3.1 GB**, almost all of it working directories and fixtures. **The narration of a task is
kilobytes; the artifacts of running it are gigabytes.** (Claudette narrates mutations only, so 4 KB
is a floor for what 2.0 would emit — the order of magnitude is the point.)

So replay reconstructs **what the operator saw, not what the agent touched**. Re-rendering a run is
cheap and belongs in the log; restoring the workspace it produced is a different feature with three
orders of magnitude more data behind it, and F102's trash pre-images are the only part of that which
2.0 inherits.

Neither transport is stressed by 150 events/second. **Throughput is not the axis this decision
turns on** — which frees it to turn on the axis that matters.

### F124 — SSE's `Last-Event-ID` *is* the replay cursor, and V1 hand-rolled it over WebSocket, badly

The EventSource API reconnects automatically after a drop and sends a **`Last-Event-ID` header so
the server resumes from where it left off**; events carry IDs for exactly this purpose. It is plain
HTTP, so it traverses proxies and load balancers with no special handling, and it is the protocol
behind streaming AI responses generally. WebSocket has no equivalent: reconnection and replay are
the application's problem.
([SSE vs WebSockets, Ably](https://ably.com/blog/websockets-vs-sse),
[SSE vs WebSockets 2026](https://oneuptime.com/blog/post/2026-01-27-sse-vs-websockets/view),
retrieved 2026-08-18)

Now compare what V1 built. `useSocket.ts` is a WebSocket with 26 domain handlers, and its recovery
story is hand-rolled: rehydrate the log buffer from REST via `listRecent(200)` on reconnect, into a
**500-row ring buffer**, while Postgres holds every row (`inheritance-map.md` §8). **That is a
worse version of `Last-Event-ID`** — bounded, lossy, and a second code path — written because
WebSocket does not come with the better one.

The usual reason to pay that price is bidirectionality. Here it is nearly worthless: item 2's eight
verbs are **operator clicks**, a handful per run, and a plain `POST /control` carries them with less
machinery than a socket. The asymmetry of the two directions — a firehose down, a trickle up — is
precisely the shape SSE is for.

**One caveat to record rather than discover later:** SSE over HTTP/1.1 inherits the browser's
~6-connections-per-origin limit, so a console that opens a stream per panel will stall. One stream
per console, demultiplexed by event type — which is what a single broker subscription is anyway.

### F125 — SQLite, and the numbers are not close

V1 runs PostgreSQL 16 in a container beside Redis and Ollama (F95). The measured alternative, from
the same machine:

| Store | Size | Shape |
|---|---|---|
| `~/.claudette/recall.sqlite` | **708 KB** | cross-session semantic recall, 50k-row FIFO |
| `~/.claudette/transcript/actions.jsonl` | **7.9 MB** | 16,150 mutating actions, months of use |

At F123's action granularity an event log grows at roughly the second row's rate. A year of heavy
daily driving is single-digit megabytes. **There is no volume argument for a database server here**,
and there is a decisive install argument against one (F95): Postgres means a container, and a
container means the docker-compose 2.0 exists to escape.

The two objections worth stating and answering:

- **Concurrent writers.** SQLite in WAL mode is one writer, many readers. 2.0's backend is a single
  process and the *only* writer; the console is a reader. This is the configuration SQLite is best
  at, not the one it struggles with.
- **Analytical queries for the after-action screen.** F119 noted Langfuse reaches for ClickHouse
  precisely for OLAP over traces. At single-digit megabytes per year that reach is not justified —
  but it is the one number to watch, and it is why OQ-W5-9's retention answer matters.

Claudette is the precedent and the proof: a serious agent with cross-session memory, sessions, todos,
notes and an action journal, and **no database server anywhere** — everything under `~/.claudette/`.

### F126 — one monotonic integer is the transport cursor, the SQL cursor and the scrub position

This is why the three questions are one question.

Give every event a monotonically increasing `seq`. Then:

- **SSE** sends it as the event `id:`, and a reconnecting console returns it as `Last-Event-ID`
  (F124).
- **The paged read** is `SELECT … WHERE seq > ? ORDER BY seq LIMIT n` — the paged read path §14
  item 3 asks for, and the thing V1 never built.
- **Replay** (F105) positions the cursor at a `seq`; "live" is the cursor pinned to the maximum.
- **The timeline minimap** (F108) draws that integer as a scrub bar.

Four requirements, one field. Choosing WebSocket means the first bullet needs its own mechanism;
choosing Postgres changes nothing about the integer but adds a service to hold it. **The
combination that makes them the same integer is SSE plus SQLite**, and that is the substantive
reason to choose it — the install story is the bonus, not the argument.

## Recommendation

1. **SSE for the live stream, plain HTTP POST for control.** One stream per console, event `id:` =
   `seq`, resume via `Last-Event-ID` (F124, F126).
2. **SQLite as the store of record**, under the 2.0 equivalent of `~/.claudette/` — no server, no
   container (F125). WAL mode, single writer, console as reader.
3. **Log at action granularity, stream at token granularity** (F123). Replay re-streams stored text
   rather than storing the stream.
4. **`seq` is the project's cursor**, used by the transport, the paged read, replay and the scrub
   bar. Design it once and do not let a second cursor concept appear.
5. **Keep WebSocket as a documented fallback**, not a plan: if the terminal surface or a future
   remote-fleet mode (W10) ever needs genuine bidirectional streaming, the broker contract is
   transport-agnostic (F99) and only the edge changes.

## Rejected alternatives and why

- **WebSocket as the primary transport.** Rejected on F124: it costs a hand-rolled recovery path to
  buy a bidirectionality that eight occasional operator clicks do not need — and V1 already paid
  that price and got a 500-row ring buffer for it.
- **PostgreSQL.** Rejected on F125 and F95: a service to hold single-digit megabytes, and the exact
  dependency that makes the install a multi-step operation.
- **Persisting the token stream.** Rejected on F123's arithmetic — one 40-minute run would out-weigh
  months of Claudette's action log.
- **A second cursor for replay** (e.g. wall-clock timestamps for the scrub bar, `seq` for paging).
  Rejected on F126: two cursors that must agree are two cursors that will not. Timestamps stay as
  *data* on the event, not as the addressing scheme.
- **Polling REST for updates**, V1's pre-WebSocket shape. Rejected by V1's own scar tissue: the
  10-second poll is what caused the frontend OOM the ring buffer was introduced to fix (F112).

## Effect on fun

- **Reconnect stops being a visible event.** The console you left open overnight picks up exactly
  where it stopped rather than showing the last 200 rows and a gap — which is the difference between
  a tool you trust and a tool you refresh.
- **The scrub bar is free.** Because `seq` already exists for three other reasons, dragging back
  through a run is a query, not a feature that needs building.
- **The install stays one file.** §7's fun is felt before the first token: a tool that runs from one
  binary with no services is a tool people actually try.
- **The risk, named:** SSE plus SQLite is unglamorous, and the temptation later — when a remote rig
  joins the fleet in W10 — will be to rebuild both. Keeping the broker contract transport-agnostic
  (F99) is what makes that a swap rather than a rewrite.

## Open questions

- **OQ-W5-19 — where does `seq` live: per run, or global?** Global makes the cursor trivially
  orderable across runs; per run makes replay addressing shorter and retention simpler. Leaning
  global with a run column, but it interacts with OQ-W5-9's retention answer.
- **OQ-W5-20 — how long does the server hold replayable history for a live reconnect?** SSE's resume
  is only as good as the server's ability to answer from an arbitrary `seq`; if the log is the store
  of record this is free, which is another argument for not bounding the log in memory the way V1
  bounded its store.
- **OQ-W5-21 — does the terminal surface use the same SSE stream?** It should, by F99, but a CLI
  consuming SSE is slightly unusual and worth a spike before it is assumed.

## Confidence: high

The volume arithmetic uses this project's own measured numbers, the file sizes were taken from disk
this session, and the protocol behaviours are documented rather than inferred. **What would lower
it:** OQ-W5-9 landing on very long retention plus a heavily analytical after-action screen, which is
the one combination where F125's "no volume argument for a server" stops holding — and F119's note
about ClickHouse becomes the warning rather than the counter-example.

---

# Item 7 — fun, grounded and made testable

§11: *"**The fun research from section 7.** Developer tool ergonomics, flow, feedback latency, and
what the literature and the good tools actually do. Ground this rather than guessing."* The
deliverable is *"a written position on what 'fun' means here, concrete enough to test."*

## Question

§7 lists six design constraints and one metric. The metric is *"whether David reaches for this
instead of Claude Code for a real task, and whether he keeps it open when he does not have to."*
Is that metric sound, what does the literature actually say about the six, and what would a test
look like that does not consist of asking someone whether they had fun?

## Method

Two bodies of evidence: the interaction-design literature on response time and attention, and the
strongest available empirical work on how developers perceive AI coding tools. Both read against
this project's own measured numbers. Retrieved 2026-08-18.

## Findings

### F127 — the literature gives hard numbers, this hardware already violates the biggest one, and the prescribed fix is the feature the brief already wants

Nielsen's three response-time limits are the durable result here, and they are specific:

- **0.1 s** — the limit for feeling that you are directly manipulating the thing on screen.
- **1 s** — the limit for the user's *flow of thought* to stay uninterrupted; past it they notice.
- **10 s** — the limit for keeping attention on the dialogue at all. Past it, users switch to
  another task, and the interface owes them *"a percent-done indicator as well as a clearly
  signposted way to interrupt the operation."*
  ([NN/g, Response Time Limits](https://www.nngroup.com/articles/response-times-3-important-limits/),
  retrieved 2026-08-18)

Now this project's own numbers. W1 F80, champion resident, single stream:

| prompt tokens | time to first token |
|---|---|
| 2,361 | **2.215 s** |
| 7,440 | **5.920 s** |
| 18,470 | **11.549 s** |

**At realistic agentic context sizes the model crosses the 10-second attention limit before it
emits its first token** — and that is the *good* case. W1 F91 recorded a run that was genuinely
silent for **40 minutes**: 240× the attention limit, on a workload where the operator has nothing
to look at.

Two things follow, and neither is a matter of taste:

1. **The console owes a percent-done indicator and an interrupt, by the literature's own
   prescription** — which is item 2's kill/pause verb and item 4's liveness clock, arriving from a
   1993 usability rule rather than from RTS nostalgia. §7 guessed right; the grounding confirms it.
2. **The 0–11.5 s window is the console's to fill, not the model's.** The console can acknowledge in
   well under 1 s — accepting the command, showing the task, showing which model is loading — and
   that is entirely within 2.0's control because it happens before inference starts. **"Speed where
   it is felt" is a startup-path property, not an inference property**, which is exactly why item
   1's terminal entry point matters: it is the shortest possible path to the first visible thing.

### F128 — 🚨 §7's own metric cannot stand alone, because developer perception of these tools is measurably wrong

This is the uncomfortable finding, and it goes to the heart of how the project judges itself.

METR ran a randomized controlled trial with 16 experienced open-source developers across **246 real
issues** in mature repositories (22,000+ stars, 1M+ lines). When allowed AI tools, they completed
tasks **19% slower**. They had forecast a **24% speedup**. And *after finishing*, having lived
through the slowdown, they still estimated AI had made them **20% faster**.
([METR, July 2025](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/),
[arXiv:2507.09089](https://arxiv.org/abs/2507.09089), retrieved 2026-08-18)

A roughly **39-point gap between felt and actual**, which survived direct experience of the
opposite.

**Limits, stated so this is not over-cited:** n=16 developers in one setting with early-2025 models
and tooling, and METR has since revised its experiment design
([METR, Feb 2026](https://metr.org/blog/2026-02-24-uplift-update/)). It is one strong study, not a
law.

But it is directly aimed at this project's metric. §7 proposes to measure success by whether David
*reaches for* 2.0 — a perception signal, from exactly the population whose perception this study
found to be off by 39 points in exactly this domain. **That does not invalidate the goal.** ABCC
2.0's stated purpose is enjoyment, not throughput
(`abcc-2-lineage-and-intent`: ABCC's contribution is fun, Claudette's is correctness), and choosing
a tool you enjoy is a legitimate preference even at a time cost.

**What it does mean is that the two must be measured separately and never allowed to proxy for each
other:**

- **Fun is measured as logged behaviour** — what the operator does, not what they say (F129).
- **Speed is measured against a baseline** — wall clock per task versus Claude Code on the same
  work, which is W8's job.
- **If 2.0 is more fun and slower, that is a legitimate outcome to ship** — but it has to be a
  *known* one. The failure mode this study describes is shipping it as a speedup and believing it.

### F129 — the written position: what "fun" means here, as six queries over the event log

§7's six constraints become six observables, and item 6's `seq` log is where every one of them
already lives. This is the deliverable, and it is deliberately written as things a machine can
compute without asking anyone anything.

| §7 constraint | The observable | Computed from the log as | Bar |
|---|---|---|---|
| **No dead air** | longest silence inside a run | max gap between consecutive events | **no gap > 10 s without a liveness mark** (F127); report p50 / p95 / max per run |
| **Speed where it is felt** | time to first visible thing | first console event − command accepted | **< 1 s**, independent of TTFT (F127) |
| **Legibility** | surfaces consulted before acting | screen/panel switches between run start and first operator command | fewer is better; no absolute bar, tracked as a trend |
| **Agency** | intervention rate | control events per run; share of runs with ≥ 1 | **> 0 in a meaningful share of runs** — a control bar nobody touches is decoration |
| **Personality with an off switch** | whether the switch is used *both ways* | audio/theme setting-change events | turning it off **and later back on** proves it is a preference, not an irritant |
| **Honest failure** | whether failures are worth re-watching | replay-cursor movement on failed runs ÷ failed runs | a failed run that gets replayed is an interesting one |

And the §16 test itself, made loggable rather than remembered:

- **Unprompted opens per week** — sessions started with no run pending.
- **Idle-open time** — console open with nothing executing, which is §7's *"keeps it open when he
  does not have to"* stated as a number.
- **Abandonment** — runs killed by the operator versus run to completion, split by whether the
  operator intervened first (an abandoned run after three interventions means something very
  different from one abandoned in silence).

Paired with it, per F128, the outcome measure that must never be dropped: **wall clock per task
against the Claude Code baseline**, owned by W8.

**In one sentence, the position:** *fun here means the operator is never uninformed for more than
ten seconds, can always intervene, and chooses to keep the thing open — and every clause of that is
a query over the event log, not a feeling anyone is asked to report.*

### F130 — the off-switch after Q8: labels are cosmetic, the enum is not, and that is the honest answer

Closing OQ-W5-11, because it is a personality question rather than a data-model one.

V1's themes are ~28-line **vocabulary maps** — `taskQueue: 'Bounty Board'`, `agents: 'Strike Team'`
— with `classic.ts` as the neutral off-switch. Q8 (2026-08-07) put the RTS framing **into the Rust
domain model**, where an enum variant cannot be renamed by a theme file.

The two candidate readings and the one that survives:

- ~~"Off means the domain model goes neutral."~~ Impossible without reversing Q8, and Q8 was chosen
  deliberately, with §14 item 4 giving it a first job.
- **"Off means the presentation layer stops translating."** The enum stays military; the theme is a
  **label map from enum variant to displayed string**, and `classic` is the identity map onto
  functional names. Exhaustive over the enum (F113), so a new state cannot ship without a label in
  every theme.

**What this costs, said plainly:** the off-switch is now cosmetic — logs, API field names and any
error message that quotes a variant stay military. A user who dislikes the framing gets a neutral
*screen*, not a neutral *system*. That is the real consequence of Q8 and it should be documented in
the settings UI rather than discovered.

**What it buys:** personality is on by default and one toggle away from off, which is exactly §7's
*"make it excellent by default and trivially mutable"* — and the 96 voice lines get the same
treatment, since audio is the loudest half of the personality and the first thing a subset of users
will disable.

## Recommendation

1. **Adopt the six-row table in F129 as W5's definition of fun**, and hand it to W8 as a first-class
   evaluation criterion alongside pass rate — which is what §7 asked for in as many words.
2. **Budget the 0–11.5 s window as a design surface, not a wait** (F127). Sub-second acknowledgement
   from the console, a percent-done for anything past ten seconds, and an interrupt always visible.
3. **Never report fun as speed** (F128). Ship wall-clock-versus-baseline next to any claim about how
   the tool feels, and be willing to say "more fun, slower" out loud if that is the result.
4. **The theme off-switch is a label map over a fixed enum** (F130), exhaustive by construction, with
   its cosmetic-only scope documented where the user toggles it.
5. **Instrument from day one.** Every row in F129 is a query over the `seq` log, so the cost is
   emitting a handful of extra event types — a decision that is nearly free now and expensive to
   retrofit.

## Rejected alternatives and why

- **Asking the operator to rate the experience.** Rejected on F128 — the population's self-report in
  this exact domain was off by 39 points and did not correct after direct experience.
- **Total wall clock as the speed metric that matters to feel.** Rejected on F127: the felt quantity
  is time-to-first-visible-thing, and §7 says so independently. Total wall clock stays as the
  *honesty* metric, not the *feel* metric.
- **Minigames while you wait** (BCF's `snake.rs` / `space.rs`). Rejected, and the reason is worth
  keeping: they treat dead air as unavoidable and decorate it. F127's prescription is a percent-done
  and an interrupt — make the work watchable rather than the wait entertaining.
- **A neutral "professional mode" that strips the RTS framing everywhere.** Rejected on F130 — it
  would require reversing Q8, and the honest partial version is better than a promise the type
  system cannot keep.
- **Deferring instrumentation until there is something to measure.** Rejected on cost asymmetry: the
  event types are nearly free to add now and require a schema migration plus a lost history later.

## Effect on fun

This item *is* the fun section, so the honest framing is what it costs rather than what it gives:

- **It makes fun falsifiable**, which is uncomfortable by design. A console that scores badly on the
  F129 table is not saved by looking good in a screenshot.
- **It protects the identity from the metric.** Because F128 separates enjoyment from speed, a slower
  ABCC 2.0 does not have to be argued away — it can be chosen on purpose, with the number stated.
- **The 10-second rule is the single most actionable thing in this document.** It converts "no dead
  air" from a value into a threshold with a prescribed remedy, and this hardware crosses it on
  ordinary work.

## Open questions

- **OQ-W5-22 — what counts as a "liveness mark" for the 10-second bar?** A token is obviously one; a
  heartbeat with no content is obviously not enough on its own. The line between *informative* and
  *noise* is the one thing F129's first row leaves to judgement.
- **OQ-W5-23 — who runs the F129 queries, and where do they surface?** They are the after-action
  screen's real content (F116), but they are also W8's evaluation criteria, and the two want
  different presentations of the same numbers.
- **OQ-W5-24 — is there a baseline run of Claude Code on the same tasks?** F128's paired measure
  needs one, and W8's corpus does not currently include the incumbent as a subject.

## Confidence: high on the grounding, medium on the bars

- **High** on F127 and F128 — both are published, cited and read against this project's own measured
  latency numbers.
- **Medium** on the specific thresholds in F129. The 10-second bar is inherited from the literature
  and is defensible; the "< 1 s to first visible thing" bar is Nielsen's flow limit applied to a
  path nobody has built yet; and the agency and abandonment rows have no prior art to calibrate
  against, in this family or outside it. **What would raise it:** running the queries against real
  Phase-3 sessions and seeing which rows discriminate between a good day and a bad one.
- **What would lower it:** if a larger replication of METR's result reverses the sign, F128's
  separation of fun from speed loses its strongest support — though not its logic.

---

# Addendum — the TUI framework comparison, run from scratch 2026-08-18

**Why this exists.** §11 instructed W5 to *"start from"* the owner's prior research on Ratatui,
Bubbletea and Textual. Asked directly, David: *"i did not research Ratatui, Bubbletea and
Textual."* The premise was false, `RESEARCH_BRIEF.md` §11 is corrected in place, and the comparison
below was run the same day by four parallel researchers.

**What it does and does not decide.** Item 1 defers the TUI to the headless/SSH question, and David
accepted that. **This addendum does not reopen it.** It exists so that when the deferred decision is
taken it is taken from evidence — and because two of its findings bear on work that is *not*
deferred (F101's stale-answer hazard, and the streaming-render budget).

All claims retrieved 2026-08-18.

## Ratatui (Rust)

**Status.** 0.30.2 published 2026-06-19; 0.30.0 2025-12-26 after a ~14-month gap for the workspace
restructure into `ratatui-core` / `-widgets` / `-macros` / per-backend crates. 22.3k stars, MSRV
1.86. Applications keep depending on the umbrella `ratatui` crate. **Expect a breaking change every
minor** — `BREAKING-CHANGES.md` is a maintained file, which is honest and also the point.
([crates.io](https://crates.io/api/v1/crates/ratatui), [repo](https://github.com/ratatui/ratatui),
[v0.30 highlights](https://ratatui.rs/highlights/v030/))

**Streaming.** Immediate mode: every `draw()` rebuilds the whole buffer, and the double-buffer diff
bounds *terminal I/O*, not *your* construction cost. So the documented pattern decouples the rates —
`tick_rate(1.0).frame_rate(30.0)` — coalescing ~5 tokens per frame at F123's 150 events/sec.
([rendering](https://ratatui.rs/concepts/rendering/under-the-hood/),
[async tutorial](https://ratatui.rs/tutorials/counter-async-app/full-async-events/))

**Two open issues that land on this project's exact paths.**
[#1004](https://github.com/ratatui/ratatui/issues/1004) — a `Table` of 15k rows costs 1–2 s per
scroll, because rows are collected into a `Vec` at construction. And
[#584](https://github.com/ratatui/ratatui/issues/584) — `Viewport::Inline` plus high-frequency
`insert_before()` **flickers, reproduced on Windows Terminal**, which is the chat-scrollback path
exactly. The `scrolling-regions` feature (0.29) partially mitigates and is **not on by default**.

**Windows.** crossterm is the default and the documented recommendation when Windows matters.
Documented gotcha: Windows emits **duplicate key events**, so `KeyEventKind::Press` must be filtered.

**Modals.** Nothing built in — `Clear` for overdraw plus an app-state enum is the convention, and the
idiomatic way to block a worker is a request channel carrying a `oneshot` reply.

**Images.** `ratatui-image` covers sixel / kitty / iTerm2 with a half-block fallback, but **Windows
is absent from its compatibility matrix** and [issue #69](https://github.com/benjajaja/ratatui-image/issues/69)
(open since 2025-01-05) reports `Picker::from_query_stdio` panicking there. Windows Terminal itself
gained sixel in 1.22 — the gap is the crate's autodetection. **Plan on half-blocks on Windows.**

**Async.** Tokio is **not** required; a `std::thread` + `mpsc` worker feeding one event enum is
equally idiomatic — which matters, because §14 item 0 leaves 2.0 free to reopen the tokio question.

**Who ships on it.** 🚨 **OpenAI's Codex CLI** — `codex-tui` is ratatui + crossterm with streaming
responses, inline diffs and **approval overlays**. That is the closest shipped analogue to what item
2 specifies, in the same language as the backend. Also gitui, bottom, yazi, xplr.

### F131 — the inherited TUI already neutralises three of Ratatui's four named hazards

Checked in Claudette's source this session, against the hazards above:

| Hazard | Claudette at `af3f804` |
|---|---|
| Breaking change every minor | On **ratatui 0.30 + crossterm 0.29** — current majors, not trailing |
| Windows duplicate key events | **`KeyEventKind::Press` filtered** at `tui.rs:820` and `:915` |
| #584 inline-viewport flicker | Uses **`EnterAlternateScreen`** (`tui.rs:712`), so the flicker path is structurally unreachable |
| Redraw per token | Event loop polls on a **50 ms** budget (`:817`, `:872`) — a bounded ~20 Hz redraw, which is the decoupling the docs require |

So the 3,011 inherited lines are not merely "a TUI exists" — they are **a TUI that already met this
framework's sharp edges and is on the right side of them**. That raises the value of the deferred
option without changing the deferral.

### 🚨 F132 — Codex CLI shipped F101's stale-answer hazard, then fixed it, and the fix adds a rule W5 missed

[`openai/codex#19513`](https://github.com/openai/codex/pull/19513), merged 2026-04-27: an approval
modal appearing **while the user was typing** let a plain `y` or `a` be consumed as an approval
shortcut. The fix was a one-second delay while the composer is active, plus queuing.

F101 derived from Claudette's source that an operator-control channel needs per-request identity and
a defined loss behaviour. **This is that hazard, in shipped code, on the exact mechanism item 2
recommends porting** — and it adds a third rule the derivation missed: **a control surface must not
accept an answer the operator had no chance to read.** Arrival time is part of the contract, not just
target identity.

This one does **not** wait for the deferred TUI decision. It applies to the console's permission
modal the moment there is one.

## Textual (Python)

**Status — healthy code, fragile institution.** v8.2.8 published 2026-06-30 on a 2–4 week cadence;
36,968 stars; MIT; actively released. But Textualize *the company* wound down: on 2025-05-07 Will
McGugan wrote that it *"will be wrapping up in the next few weeks"* and that Textual *"has always
been a solution in search of a problem"*, while committing to maintain it personally. He has — 8.x is
post-wind-down work — but **14 of the last 15 commits are his**, and a recent release note reads
*"This release sponsored by Mistral AI."* Per-release patronage, **bus factor 1**.
([the future of Textualize](https://textual.textualize.io/blog/2025/05/07/the-future-of-textualize/),
[releases](https://api.github.com/repos/Textualize/textual/releases))

**Streaming — structurally the best of the three.** Retained mode with a widget tree, TCSS
stylesheets, reactive attributes and a spatial map for visible-widget lookup. `MAX_FPS` defaults to
**60**, and `Widget.refresh()` sets a flag serviced on the next idle — *"only one refresh will be
done even if this method is called multiple times."* F123's 150 events/sec collapses to ≤60 repaints
**by construction**, where Ratatui requires the developer to arrange it.
([constants.py](https://raw.githubusercontent.com/Textualize/textual/main/src/textual/constants.py),
[Widget.refresh](https://textual.textualize.io/api/widget/#textual.widget.Widget.refresh))

**Modals — also the best of the three.** `ModalScreen` blocks app-level bindings, and
`push_screen_wait()` gives `if await self.push_screen_wait(QuestionScreen(...))` — a genuine
block-on-human-decision primitive, with the documented constraint that it *"can only be done from a
worker, so that waiting for the screen doesn't prevent your app from updating."*
([screens guide](https://textual.textualize.io/guide/screens/))

**Windows.** *"The new Windows Terminal runs Textual apps beautifully"* — with no legacy-conhost
guarantee, and eight open Windows-titled issues including **CJK IME breakage on both Windows
Terminal (#5457) and conhost (#5456)**.

**⚠ `textual-web` / `textual-serve` are not a two-surface shortcut.** Worth stating plainly, because
the name invites exactly that hope: both render **a terminal emulator in a browser tab**, not a web
UI. And both are near-dormant — `textual-serve` has ~2 commits in two years, both version bumps;
`textual-web` last saw a commit 2024-08-30 and depends on relay infrastructure from a wound-down
company. It would not have given 2.0 its console.

**Packaging — the disqualifier.** Official guidance is `pip` / `pipx`; there is **no
standalone-binary story** in the docs, and PyInstaller on Windows has an open regression
([#5162](https://github.com/Textualize/textual/issues/5162), open since 2024-10). Against F95's
one-verified-`.exe` install that is decisive on its own.

**Who ships on it.** Posting (12,277 stars, active), Harlequin, Toolong, Bloomberg's Memray. **The AI
gap is the notable part:** Elia, the flagship LLM chat TUI, was last pushed 2024-10-10 — ~22 months
stale. The maintained agent TUIs are Go or Rust.

**The Rust tension, stated exactly.** A TUI sidecar is worse than the usual sidecar case: it must own
the parent TTY — raw mode, stdin, resize — so the Rust binary degrades to a launcher that hands over
the terminal, having paid a bundled interpreter and tens of megabytes for the *deferred* surface.

## Bubble Tea (Go)

**Status — the healthiest of the three, and the most recently churned.** v2.0.8 published 2026-07-03;
**v2.0.0 landed 2026-02-24** after a long beta. 44,437★, 153 contributors, pushed the day this was
retrieved. The ecosystem shipped v2 together — Lip Gloss v2.0.6, Bubbles v2.1.1, Glamour v2.0.1 —
with one exception worth knowing: **Harmonica (animation) is dormant, last released 2022-04-15.**
v2 brought the "Cursed Renderer" (an ncurses-derived diffing engine) and a new lower-level
primitives library, `ultraviolet`, which crush still pins by pseudo-version. **The foundation is
good and still moving.**
([releases](https://github.com/charmbracelet/bubbletea/releases),
[v2: what's new](https://github.com/charmbracelet/bubbletea/discussions/1374))

**Streaming — the sharpest difference between the three, and it was found in source, not docs.**
The renderer flushes on a ticker at `fps` (default 60, hard cap 120), so *writes* are coalesced. But
`View()` is called **once per message, not once per frame**: `eventLoop` runs `model.Update(msg)`
and then unconditionally renders (`tea.go:872`, `:880`). At F123's 150 msg/sec that is **150 full
re-renders of the entire UI string per second**, of which ~60 reach the terminal. The ceiling is
your `View()` cost — and for a view containing Glamour-rendered markdown, that is the expensive
path. **Mitigation is producer-side batching**, before `p.Send`.

### F133 — 🚨 crush has already built F101's permission channel *and* item 6's transport, and it solved a case W5 missed

Read in `charmbracelet/crush` source (`internal/permission/permission.go`), the mechanism is:

1. A tool calls `Request(...)`, which takes a mutex that **globally serialises to one prompt at a
   time**, creates `respCh := make(chan bool, 1)`, registers it under a request ID, publishes the
   request over a **pubsub broker**, and blocks on `select` over `ctx.Done()` and `respCh`.
2. The UI subscribes to the broker, renders the dialog, and calls `Grant` / `GrantPersistent` /
   `Deny`. All three route through `resolve()`, which does an atomic take-under-lock so **"the first
   caller wins, the rest become no-ops"** — a comment that says it is deliberately written *"so
   multi-subscriber UIs can race safely."*
3. In client/server mode the same flow is bridged over **SSE plus `POST /v1/workspaces/{id}/permissions/grant`.**

**Three things this does to W5's design, and they all point the same way.**

- **F101 is confirmed and extended.** W5 derived per-request identity and fail-safe loss from
  Claudette's single-subscriber rendezvous. crush shows the *multi*-subscriber case — which is
  exactly what item 1's console-plus-terminal creates — and its answer is the same shape: a
  per-request channel, resolved atomically, first answer wins.
- **F124 and F126 are independently arrived at by someone else.** crush's chosen wire format for
  this is **SSE down, POST up** — the exact split item 6 recommends, reached from the same asymmetry.
- **W5 missed a scoping idea worth stealing:** crush's persistent grants are keyed on
  `PermissionKey{SessionID, ToolName, Action, Path}`. That is "don't ask me again *for this*", scoped
  narrowly enough to stay safe — a middle ground between prompting every time and a global
  danger-mode toggle, and neither donor has it.

### 🚨 F134 — the polyglot TUI sidecar was tried at scale, by a better-resourced team, and deleted

This is the decisive finding for the Bubble Tea option, and it is empirical rather than theoretical.

**It works.** crush runs its own HTTP server over a **Unix socket, or a Windows named pipe** (via
`go-winio`, message mode), ships a **Swagger/OpenAPI spec** with ~50 `/v1` endpoints including
`/workspaces/{id}/events` (SSE), `/permissions/grant` and `/agent/sessions/{sid}/cancel`, and lets
multiple TUI clients attach to one `crush serve`. So a Rust backend would not "embed Go" — it would
serve a documented local protocol that a stock TUI binary consumes.

**And then it was abandoned.** `opencode` ran precisely that architecture: a Go/Bubble Tea TUI as a
**separate platform-specific binary spawned by a TypeScript backend**, talking HTTP + SSE against an
OpenAPI 3.1 spec explicitly intended for generating clients in other languages. Today the repo
reports **zero Go** — the TUI was replaced by **OpenTUI** (TypeScript with a Zig core), with issue
#2956 documenting the deliberation.
([opencode server docs](https://opencode.ai/docs/server/),
[issue #2956](https://github.com/anomalyco/opencode/issues/2956))

**What it costs, quantified honestly:** not a Go rewrite, but (a) a versioned local RPC surface —
which item 6 wants anyway for the console, (b) a second binary shipped and updated per platform,
(c) named-pipe versus Unix-socket branching, (d) owning a Go build. **And the real cost is drift:
every backend feature needs a second client implementation.** That is what opencode paid and then
stopped paying.

**Conclusion for W5:** this is the strongest available evidence that the *deferred* TUI, when it is
built, should be **Rust/Ratatui in-process** rather than a polyglot sidecar — and it strengthens the
deferral itself, since the sidecar is the only route by which Bubble Tea's superior agent ecosystem
was ever reachable from a Rust backend.

**Windows.** Materially better than its reputation, and recently so: the deprecated Windows caveat
was removed from the README in **2026-05-10**, and v2's resize/`WindowSizeMsg` regressions
(#1595, #1601) are closed. **Windows Terminal is fine; legacy `cmd.exe`/conhost is where the
remaining bugs live** — clipboard paste garbling (#1712), `Ctrl+Space` undetectable (#1495), cursor
visibility under `WithAltScreen` (#1454).

**Images.** None built in — [issue #163](https://github.com/charmbracelet/bubbletea/issues/163) has
been open since **2021-11-29**. Bubble Tea offers only *detection* (query primary device attributes
for Sixel) and a raw escape hatch. Third-party support is small (`go-termimg` 66★, `rasterm` 112★).
Note that "kitty" throughout the codebase means the **keyboard** protocol, not graphics — the same
trap Textual's release notes set.

**Who ships on it.** crush 27,483★ (pushed the day of retrieval, and 643 open issues — young and
fast-moving, not settled), glow 26,938★, gum 24,250★, gh-dash 12,319★, soft-serve, huh. The README
additionally names Microsoft, NVIDIA, AWS, MinIO and Ubuntu as users.

**Honest weaknesses.** `View()`-per-message (above); no first-class nested-component routing, so
message plumbing is manual past ~3 levels; a documented input-loss defect during shutdown from the
async input reader ([dr-knz.net, 2022](https://dr-knz.net/bubbletea-control-inversion.html)) whose
status on v2 is **unverified**, with a related issue (#1692) still open — which matters for headless
*testing* of the TUI; v2 is only ~6 months old and broke its API meaningfully.

## The surrounding reality — what shipped agents actually do

The three framework write-ups above answer "which library". This section answers the question that
turned out to matter more: **what do the agents people actually use build their terminal UIs with,
and what can a terminal really do?**

### F135 — the choice tracks the backend language in every current case, and the one exception reversed itself

| Tool | Language | Terminal UI |
|---|---|---|
| **Claude Code** | TS/JS in a per-platform native binary | **React + Ink** (a fork), Yoga flexbox |
| **Gemini CLI** | TypeScript | **Ink** (a different fork) + React 19 |
| **opencode** | TypeScript / Bun | **OpenTUI** — SolidJS in the terminal over a **Zig** render core |
| **crush** | Go | **Bubble Tea v2** |
| **OpenAI Codex CLI** | **Rust** | **ratatui + crossterm** |
| **aider** | Python | `prompt_toolkit` + `rich` — **a line REPL, not a full-screen TUI** |
| **Cursor CLI** | closed binary, unverified | unverified — and its installer serves **linux/darwin only, no Windows** |

Two things fall out. First, **there is no dominant framework, but there is a dominant rule: the TUI
is written in the backend's language.** Every current example follows it. Second, **the single
exception was opencode**, whose Go/Bubble Tea TUI drove a TypeScript server over HTTP+SSE — and they
reversed it (F134), building OpenTUI so that `packages/tui`, an Electron desktop app and their web
console all consume **one shared SolidJS component layer**.

For a Rust backend the rule points at **Ratatui**, and Codex CLI is the proof that it carries an
agent of this exact shape. Note also that both React-in-terminal shops run a **fork** of Ink rather
than upstream — a reminder that the terminal is not a solved rendering target for anyone.

### 🚨 F136 — correction to F94: a terminal *can* show animated sprites, and it fails in exactly the case the TUI is deferred *for*

**F94 asserted that "a TUI cannot show a painted battlefield." That was too strong, and this
corrects it.**

- **Windows Terminal supports sixel**, since Preview 1.22; the stable build on this machine
  (`v1.24.11911.0`, 2026-07-16) has it. It does **not** support the kitty graphics protocol
  ([microsoft/terminal#8389](https://github.com/microsoft/terminal/issues/8389), open) — kitty's
  *keyboard* protocol is a different thing that it does ship.
  ([WT Preview 1.22](https://devblogs.microsoft.com/commandline/windows-terminal-preview-1-22-release/))
  ⚠ [arewesixelyet.com](https://www.arewesixelyet.com/) still lists Windows Terminal as unsupported;
  that contradicts Microsoft's own release blog and OpenAI's shipped detection code, and should be
  treated as stale.
- **OpenAI's Codex CLI ships animated sprites in the terminal** — `codex-rs/tui/src/pets/`, with
  `image_protocol.rs` selecting kitty / kitty-local-file / sixel, and a purpose-built sixel encoder
  using RGB332 colour reduction to a 256-colour palette, alpha threshold 128, a transparent-background
  DCS introducer and a disk frame cache. Sprites target 75 px against a 15 px terminal row.

So the capability is real. **But read the failure modes against W5's actual use case:**

- The sprites are **palette-reduced to 256 colours** — against 35 MB of full-colour art and four
  animated GIFs, that is a different medium, not the same one.
- **tmux and Zellij are hard-unsupported**, in Codex's own shipped error text: *"Pets aren't
  available in this terminal… Try a terminal with Kitty graphics or Sixel support, or run Codex
  outside tmux."*
- Over SSH, kitty's file and shared-memory transports are local-only, leaving base64 over the wire —
  and a multiplexer kills images outright.

**The corrected claim, and it is sharper than the original:** a terminal can carry the identity
*locally on Windows Terminal*, which is precisely where the web console is already available — and
cannot carry it *over SSH inside tmux*, which is the only scenario the TUI is deferred for. **The
sprite capability exists in the case that does not need it.** F94's conclusion survives; its
absolute phrasing does not.

### F137 — Codex ships a tuned answer to F123's streaming problem, with numbers, in Rust

F123 established that the console must not redraw per token at ~150 events/sec. Codex's source
gives a shipped policy rather than a guess:

- `tui/frame_rate_limiter.rs` — a hard **120 FPS** cap, `MIN_FRAME_INTERVAL = 8_333_334 ns`, with the
  comment that it *"clamps draw notifications to a maximum of 120 FPS to avoid wasted work."*
- `tui/streaming/chunking.rs` — an adaptive two-mode policy. **Smooth** emits one line per tick;
  **CatchUp** drains the queue. Enter CatchUp at **queue depth ≥ 8 lines** *or* **oldest line
  ≥ 120 ms**; leave it only when depth ≤ 2 **and** age ≤ 40 ms, sustained for **250 ms**, with a
  **250 ms** re-entry cooldown — which a **severe** backlog (≥ 64 lines or ≥ 300 ms) bypasses.

For comparison: Bubble Tea defaults to 60 FPS (cap 120); Ink defaults to **30** FPS (a 34 ms
throttle) with incremental rendering **off** by default.

**Why this matters beyond the TUI:** the same problem exists in the web console, and the same shape
solves it. A smooth mode that paces output for readability, a catch-up mode that sacrifices smoothness
to stay current, and hysteresis so it does not oscillate — that is a better specification than
"throttle to 30 fps", and it is free to copy.

### 🚨 F138 — three different shipped answers to "redirect mid-run", and the console should copy Claude Code's

Item 2 named *take over manually* and *edit a task prompt* as the least-specified verbs
(`questions.md` §3.4 item 14 calls take-over *"the single most-cited 2.0 feature and the least
specified"*). Four shipped agents have now specified it, differently:

| Agent | Interrupt | Redirect mid-run | Permission gate |
|---|---|---|---|
| **Claude Code** | `Esc` stops the response or tool call mid-turn and **keeps the work done so far**; `Ctrl+C` interrupts, then clears, then exits | **Queue-while-streaming**: type + Enter queues a message, shown above the input; `Esc` flushes the queue immediately; `Up` recalls it. **No key injects into a live turn** | `Shift+Tab` cycles modes (default → acceptEdits → plan → bypass → auto). ⚠ **Windows: `Alt+M` instead**, when the runtime does not enable VT input mode |
| **Codex CLI** | `Esc` interrupts | **Genuine steering** — state carries `queued_user_messages`, `pending_steers`, `rejected_steers_queue`, `submit_pending_steers_after_interrupt`; a steer rejected against a non-regular turn is **retried first on the next turn** | policies `untrusted` / `on-request` / `never`, plus sandbox profiles |
| **crush** | `esc` cancels the chat; **`ctrl+c` quits, not interrupts** | none documented — no queue while streaming | modal keys: `a` allow, **`s` allow-for-session**, `d` deny, `t` diff, `f` fullscreen; global `ctrl+y` yolo; desktop notification when a call needs permission |
| **aider** | `Ctrl-C`, and *"the partial response remains in the conversation, so you can refer to it when you reply"* | implicit — you just reply | none (line REPL) |

**Three design lessons W5 should take:**

1. **"Keeps the work done so far" is the important half of interrupt.** F104 defined kill as
   destructive and pause as resumable; Claude Code's Esc is a third thing — *stop generating, keep
   the artefacts, hand control back*. That is what an operator actually wants most of the time, and
   W5's verb list did not name it. Add it.
2. **Queue-while-streaming is the cheap version of take-over**, and it is what the most-used agent
   ships. The operator types while the model works; the input lands at the next boundary. It needs
   no checkpoint machinery, and it is a far smaller first step than fork-from-checkpoint.
3. **Esc must be unambiguous.** Claude Code documents that when a dialog is open, `Esc` closes the
   dialog *instead of* interrupting — a disambiguation rule, written down. With a console and a
   terminal surface both bound to the same verbs (item 1), that rule has to exist here too.

### F139 — the unification trick that saved opencode is not available in Rust, which prices the deferral honestly

opencode's escape from the polyglot sidecar was to build **one component layer that renders to the
terminal, to Electron and to the browser**. There is no Rust equivalent — no framework renders the
same components to both a browser and a terminal.

**So the deferral has an honest price:** whenever ABCC 2.0's TUI arrives, it will be a **second,
separate UI codebase**, not a re-skin of the console. Nothing in the ecosystem removes that cost for
a Rust backend.

**And the mitigation is already W5's answer.** The lever available now is keeping the agent core
behind a **surface-agnostic event/SSE API** — which is exactly what opencode, Codex's app-server and
Claude Code's multi-surface story all do. That is F99's broker and item 6's transport, arrived at
independently by three shipped agents. **Build the contract now; build the second renderer only when
something demands it.**

Two further structural notes on the deferral, in both directions. **For it:** every serious vendor
now ships multiple surfaces, and Anthropic explicitly sells its desktop app on *"review diffs
visually"* — the visual affordances are deliberately not in the terminal; Cursor's CLI does not even
install on Windows, which is this project's primary platform. **Against it:** crush and aider are
terminal-only and viable, and opencode's response to a limiting TUI was to build a whole framework
rather than drop the terminal.

## Where this leaves the deferred decision

| | Ratatui | Bubble Tea | Textual |
|---|---|---|---|
| Language vs backend | **Rust — same process** | Go — second binary | Python — bundled interpreter |
| Streaming at 150 ev/s | manual decoupling required | `View()` per **message**; producer must batch | **coalesced to ≤60 FPS by construction** |
| Blocking modal | hand-rolled + `oneshot` | crush's broker, **production-proven** (F133) | `push_screen_wait`, cleanest API |
| Windows | crossterm, current majors; key-repeat gotcha | good since 2026-05; legacy `cmd.exe` still rough | Windows Terminal fine; **CJK IME broken** |
| Images | sixel/kitty crate, **broken on Windows** | none built in since 2021 | none built in |
| Install | **same `.exe`** | second binary per platform | no standalone-binary story |
| Agent precedent | **Codex CLI** | **crush** | none maintained (Elia stale ~22 months) |
| Project health | active, breaks every minor | very active, v2 six months old | active but **bus factor 1** |
| Inherited here | **3,011 lines already written** (F131) | none | none |

**Ratatui, when the time comes.** It is the only option that stays inside the single binary F95
requires, it is what the one shipped Rust agent chose, this project already owns 3,011 lines of it
that are on the right side of the framework's known hazards (F131), and the alternatives' advantages
— Textual's coalescing refresh, crush's permission broker — are **patterns that can be copied
without adopting the runtime** (F133, F137).

**None of that changes the deferral.** Item 1's ordering stands: terminal entry point now, console
next, TUI when the headless case is real.

---

# 🚨 RE-SCOPE — "TUI first, skip the web console" — RAISED AND ACCEPTED 2026-08-19

**Status: DECIDED.** This **reverses the primacy half of item 1**, which David accepted on
2026-08-18 and re-scoped a day later. Kept as its own section rather than edited into item 1, so the
original argument and the decision that changed it both stay readable — item 1's *reasoning* is
what justified the reversal, so overwriting it would destroy the evidence.

**What he asked:** *"so Ratatui is an option? 256 colors is fine for basic animations. and if we can
skip the web ui for now it will be great. i imagine a TUI like the old C&C (1995 style)."*

## F140 — the 256-colour ceiling is not a compromise against a 1995 C&C look; it is that look's native constraint

The original Command & Conquer (1995) ran in VGA mode 13h — **320×200 at 256 colours**. Sixel's
palette ceiling and Codex's RGB332→256-colour reduction (F136) land on **the same constraint the
source material was authored under.**

This inverts the weakest-looking part of the terminal option. Under item 1's console-primary plan,
F136 read "palette-reduced sprites are a different medium from the 35 MB of full-colour art." Under
a TUI-primary plan aimed explicitly at 1995, palette reduction is **period fidelity**, not loss.

The 1995 C&C screen layout also maps onto a terminal unusually well: a right-hand sidebar, a radar
minimap, a status strip and a main viewport are four rectangles — which is what a TUI is made of.
V1 already ships the radar (`Minimap`, 190 lines, the circular sweep that occupies the whole left
column) as one of its three minimap styles (F108).

## F141 — under a TUI-primary plan, F136's own conclusion flips

F136 concluded: the terminal's sprite capability *"exists exactly where the web console is already
available, and not in the case the TUI is deferred for."* **That reasoning assumed the console
exists.** If there is no console, sixel on Windows Terminal is not redundant — it is the entire
visual identity, on the primary machine, where David actually works.

The SSH/tmux limitation then stops being a hole and becomes a **degradation ladder**: sprites
locally, text over SSH. That is what a headless session wants anyway.

## What the proposal actually buys — and it is more than it looks

| | Console-primary (item 1 as accepted) | TUI-primary (this proposal) |
|---|---|---|
| UI codebases | **Two** — F139 says the TUI is a second one whenever it lands | **One** |
| Inherited code used | 1,298 lines of live renderer, re-hosted; 14,935-line app mostly rebuilt (F107) | **3,011 lines already written**, already past 3 of 4 known hazards (F131) |
| Transport | SSE + POST + a paged read (item 6) | **None** — an in-process broker is channels; SSE returns only when a second surface does |
| Install | one binary **+ 44 MB of assets** (OQ-W5-4) | one binary, sprites downscaled and cached |
| Time-to-first-visible-thing | sub-second console acknowledgement (F127) | **the terminal is already open** |
| Precedent | V1 | **Codex CLI** — Rust + ratatui + sixel sprites, shipped (F135, F136) |

For a solo project measured at 1–5 commits a day, **halving the UI surface area is the single
largest schedule lever available in this workstream.**

## What it costs, stated plainly

1. **The 44 MB becomes source material rather than shipped assets.** 280 px sprites → ~75 px sixel
   is a mechanical downscale, not a redraw — but the four attacking GIFs (34.3 MB, 242 frames for
   the building alone) need frame extraction, palette reduction and a disk frame cache. Codex built
   exactly that (F136), so it is known work rather than research, but it is work.
2. **The isometric renderer does not port, and the projection math only half-ports.**
   `isoProjection.ts` is pure screen-space arithmetic (`sx=(x−z)·64`, `sy=(x+z)·32`), so the shape of
   it survives — but it emits *pixels*, and a terminal cell is roughly 8×15 px with its own aspect
   ratio. Depth sorting and `Z_LAYER` survive; the renderer around them is new.
3. **Phase 0's frame-budget result is spent.** "Free to ~100 entities, no canvas needed" was measured
   on the DOM. It says nothing about sixel throughput.
4. **Sixel on David's actual terminal is unverified.** The research could not test it — no TTY in
   that environment — and `arewesixelyet.com` still contradicts Microsoft's own release blog (F136).
   **The entire visual half of this proposal rests on one untested capability on one machine.**
5. **The DAG is harder in a terminal** than in a browser, and it is the console's headline element
   (F109, item 4). Charts, tables, sparklines and scrollback are all fine in Ratatui; a graph layout
   is the one thing that is not.

## Position

**Split the proposal in two, because it is two decisions wearing one coat.**

**A — the shape: TUI primary, web console deferred or dropped. Recommended, and it strengthens the
project.** It uses the inherited code instead of the rebuilt code, removes a transport, removes a
second codebase, gives the best possible entry point (F94) and the best install (F95), and it has a
shipped Rust precedent. Item 1's *reasoning* survives this reversal intact — that argument was
about the entry point and the daily-use shape, and a TUI-primary plan satisfies it more directly
than the hybrid did. What changes is which surface carries the identity.

**B — the identity: a C&C-1995 isometric battlefield rendered in sixel. Do not commit to this yet.**
It is delightful, it is period-coherent (F140), and it rests on an untested capability plus an
unported renderer. **It should be bought with a spike, not with a plan.**

**The spike, and it is small.** Render one existing ABCC sprite — and then one downscaled frame
sequence — as sixel in David's Windows Terminal, on the real machine, and look at it. That answers
questions 4 and 1 together, in an afternoon. §15 permits it explicitly: *"Spikes and benchmark
harnesses only, clearly marked as throwaway."*

**If the spike looks good**, the C&C TUI is the plan and the web console can be dropped rather than
merely deferred — and W5's items 2–7 mostly survive, because they were written about a broker, a
lifecycle, a log and a set of verbs, not about a browser. **If it looks bad**, the fallback is not a
loss: a text-and-colour Ratatui TUI with the radar minimap, the sidebar and the 96 voice lines is
still a C&C console in every sense except the sprites — audio is untouched by any of this, and it is
half the identity.

**One risk to name out loud, because it is the one that kills projects like this:** the agent does
not exist yet. Phase 3 has not started. A 1995-isometric terminal renderer is a project in its own
right, and it must not become the critical path in front of the thing it is meant to display. The
spike is also the guard against that — it is an afternoon, and it is reversible.

## ✅ DECIDED 2026-08-19 — David ruled on both

His words: *"next session we run the sixel spike. and test it — i dont care if we are building this
from scratch. it will be awesome and our flagship component of this app… we will be the first to
ever mix those together."*

- **(A) ACCEPTED.** **The TUI is the primary surface; the web console is dropped for now.** Item 1's
  primacy is reversed and this section supersedes it. Building the renderer from scratch is
  explicitly accepted as a cost, not a risk to be mitigated away.
- **(B) COMMITTED IN INTENT, still gated on the spike** — not as a go/no-go David is neutral about,
  but as a **feasibility and calibration** test. The C&C-1995 isometric battlefield in sixel is now
  named as the **flagship component**.

**What this does to the rest of W5, so the next session does not re-derive it.** Items 2–7 largely
survive, because they were written about a broker, a lifecycle, a log, a set of verbs and a
definition of fun — not about a browser:

| Item | Under TUI-primary |
|---|---|
| 2 — operator control | **Unchanged.** Three mechanisms, and F133's multi-subscriber safety becomes *simpler*, not harder, with one surface |
| 3 — inventory | **Re-scored.** The 44 MB is now source material to transform, not assets to ship; the 1,298-line isometric renderer drops to REFERENCE; `isoProjection.ts` half-ports |
| 4 — what to show | **Unchanged in substance**, harder in execution. The six questions still hold; the **DAG is the one genuinely harder element** in a terminal |
| 5 — observability | **Unchanged.** Adopt the vocabulary, own the store |
| 6 — transport | **Deferred, not wrong.** With one in-process surface the broker is channels; SSE + `seq` return the moment a second surface does, so keep the contract shape |
| 7 — fun | **Unchanged, and strengthened** — F129's six queries are surface-agnostic, and F140 makes the palette part of the identity rather than a compromise |

⚠ **`RESEARCH_BRIEF.md` §17 item 5 is now materially out of date** — it rules "a full isometric web
UI… Not a TUI, not Tauri", and the live decision is close to its inverse. It should be corrected in
place, dated and quoting David, the same way §11 was. **Left for the next session rather than done
here, because it deserves the owner's exact words at the moment of the change.**

**The fallback, so it is not read as failure.** If sixel does not work on the real machine, a
text-and-colour Ratatui console with the radar minimap, the C&C sidebar layout and all 96 voice
lines is still C&C in every sense except the sprites. Audio is untouched by every version of this,
and it is half the identity.

---

# What W5 hands to other workstreams

W5 is a design workstream, so several of its conclusions are other people's requirements. Collected
here so they are not lost in the body.

| To | Requirement | From |
|---|---|---|
| **W3** | The lifecycle enum must include `Paused` and `Operator`, **each with its reconciliation**, and every non-terminal state must be recoverable | F104 |
| **W3** | The enum must carry a **checkpoint identity** — retry, edit-prompt and replay are all fork-from-checkpoint | F103 |
| **W3** | The domain model needs real **dependency edges**; V1 has none, and the DAG is the console's headline element | F109 |
| **W3** | Enum rendering must be **exhaustive** — four of V1's eleven states have no colour, in three duplicated maps | F113 |
| **W3 / core** | The worker must **select on a control channel at every step boundary**, not block on a rendezvous | F100 |
| **W3 / core** | The permission event carries `Allow \| Deny \| Redirect(String)` — the TUI already lost the third branch once | F106 |
| **W3 / core** | A control answer must not be accepted if the operator had no chance to read the prompt — **arrival time is part of the contract**, not just target identity | F132 |
| **W3 / core** | Persistent grants scoped as `{session, tool, action, path}` — "don't ask again *for this*", between prompt-every-time and a global yolo toggle | F133 |
| **W3 / core** | Add two verbs item 2 missed: **stop-but-keep-the-work** (distinct from kill and from pause) and **queue-while-streaming** as the cheap take-over | F138 |
| **Console** | Streaming render policy: a smooth mode, a catch-up mode, and hysteresis between them — not a flat FPS throttle | F137 |
| **Console** | One written disambiguation rule for `Esc` across both surfaces, before either binds it | F138 |
| **W6** | `MemoryApproval`'s async review-queue shape is where independent-review output should land | F110 |
| **W7** | OTLP export ships as a **non-default feature**, preserving the structural air gap rather than degrading it to a toggle | F121, F122 |
| **W8** | The six-row fun table is a **first-class evaluation criterion**, alongside pass rate | F129 |
| **W8** | Cost per task is denominated in **seconds, tokens, slot-seconds and swaps** — not currency | F114 |
| **W8** | A **Claude Code baseline** on the same tasks, so "more fun" can never be reported as "faster" | F128 |
| **W12** | Distribution must carry **44 MB of art and audio** in or beside a single binary | F107, OQ-W5-4 |
| **W4** | The console shows **swaps and re-routes**, which exist, rather than a tier ladder that does not yet | item 4 |

---

# Open questions, consolidated

Answered here: **OQ-W5-1** (David, 2026-08-18 — the narrowing accepted), **OQ-W5-5** (David,
2026-08-18 — the prior research never existed; the brief's premise was false and is corrected in
place, and the comparison was run from scratch — see the addendum) and **OQ-W5-11** (F130 — the
off-switch is a label map over a fixed enum).

Still open, in the order they would be cheapest to close:

| # | Question | Waiting on |
|---|---|---|
| 2 | The terminal surface's exact floor | a written line, before accretion starts |
| 3 | Where the permission channel lives with two subscribers | W3's broker design |
| 4 | Console served, embedded, or both — with 44 MB of assets | W12 |
| 6 | Does `Paused` release the workspace lock as well as the slot | design call, leaning "keeps it" |
| 7 | What a disconnected operator does to a running fleet | design call, per verb |
| 8 | Take-over per task or fleet-wide | design call |
| 9 | Event-log retention | interacts with 19 and with F125's one caveat |
| 10 | Do the four 34.3 MB attacking GIFs survive | an unmeasured decode-memory number |
| 12 | Does the chat panel come back | follows from item 1's terminal role |
| 13 | The liveness threshold before the console escalates | W8 runs |
| 14 | Battle screen: one run or the whole fleet | design call |
| 15 | Where the DAG lives on screen | possibly the battlefield itself, if buildings gain edges |
| 16 | Which `gen_ai.*` version gets pinned, and where | a line in the docs |
| 17 | Does optional OTLP ship in the first release | not blocking |
| 18 | Event-schema versioning and migrations | follows from owning the store |
| 19 | `seq` per run or global | leaning global with a run column |
| 20 | How much history the server can resume from | free if the log is the store of record |
| 21 | Does the terminal surface consume the same SSE stream | worth a spike |
| 22 | What counts as a liveness mark for the 10-second bar | judgement, then W8 |
| 23 | Who runs the fun queries and where they surface | overlaps W8 |
| 24 | Is there a Claude Code baseline run | W8's corpus does not include the incumbent |

**None of them blocks Phase 2.** §16's bar for W5 is a written position, not a running UI; the
questions above are the shape of the design conversation Phase 2 sequences, not gaps in the answer.

---

# W5 status

**Written and complete as a Phase 1 research deliverable.** Seven items, findings F93–F130, three
named deliverables produced, one owner ruling narrowed and accepted, three corrections filed against
`prestudy/inheritance-map.md`, and one previously uncited owner document brought into the record
(F93).

What W5 deliberately does **not** contain, per §16 and §15: any ABCC 2.0 implementation code. The
first line of it belongs to Phase 3.

---

# Addendum 2026-08-19 — the sixel spike ran, and all five questions closed YES

The feasibility spike the RE-SCOPE gated on (`research/spikes/w5-sixel/`, commit `cb5aa3a`,
throwaway per §15) was built and machine-verified in one session, then run by David in his real
Windows Terminal the same day. Encoder byte-matches Codex's reference implementation (its test
vectors pass verbatim); results below are from the real terminal, not an emulator or a spec sheet.

## F142 — Windows Terminal answers the cell-size query; the ratatui-image panic is their bug, not a WT gap

Probe results on the stable WT of this machine (1.24, `WT_SESSION` set): DA1 returns
`?61;4;6;7;14;21;22;23;24;28;32;42;52c` — attribute 4, sixel, advertised outright — and CSI 16t
answers `10x20 px`, confirmed independently by CSI 14t (1200x600 text area / 120x30 cells). The
significance: `ratatui-image` issue #69 (the Windows panic in `Picker::from_query_stdio`, the
spike brief's trap 1) is a defect in that crate's query plumbing, **not** a missing terminal
capability. The real console does not need a hardcoded font size; it needs the same query with a
deadline and a fallback — ~60 lines in the spike's `probe.rs`.

## F143 — David's verdicts, in his own terminal: renders, reads as C&C at 75–120 px, animates at native rate, survives Ratatui

The four judgement questions, answered by eye 2026-08-19: **hello** renders (Q1 pass, binary).
**sprite**: "75px or 120px looks best" — squarely inside the predicted ~3.7× downscale from V1's
280 px raster, bracketing Codex's 75 px pet size (Q2). **animate**: the 97-frame coder GIF at its
native 25 FPS — 40 ms/frame, the demanding case — "looks great"; encode side was 0.53 ms/frame,
18.4 KB/frame at 100x150 px (Q3). **tui**: the composite battlefield inside the Ratatui C&C
layout "behaves o.k on resize" — redraw, resize and alternate screen all survived (Q4).

## F144 — the throughput ceiling: the screen fills before the pipe does

Q5's number, measured (`w5-sixel-bench-results.txt`, cell 10x20, 120x30 terminal):

| phase     |   N | FPS    | avg ms | p95 ms | enc ms |  MB/s |
|-----------|-----|--------|--------|--------|--------|-------|
| sprites   |   1 | 3090.5 |   0.32 |   0.38 |      — |  20.6 |
| sprites   |  16 |  218.5 |   4.57 |   4.94 |      — |  23.3 |
| sprites   |  64 |   55.1 |  18.15 |  19.75 |      — |  23.5 |
| composite |   0 |   28.6 |  34.69 |  36.23 |  10.86 |  13.2 |
| composite |  16 |   25.6 |  38.79 |  39.94 |  12.53 |  13.3 |

Two regimes, both comfortable. **Per-sprite**: WT ingests a steady ~23.5 MB/s of sixel stream;
64 pre-encoded 50x75 sprites — the grid capacity of the whole terminal — still run at 55 FPS,
and the extrapolated 15 FPS ceiling is ~235 sprites, more than three screens' worth. This is the
sixel analogue of Phase 0's "free to ~100 DOM entities", and it is roomier: **the binding
constraint is screen area, not throughput.** **Composite** (the flagship architecture, one
full-viewport sixel per tick, 1200x560 px): 25.6–28.6 FPS end-to-end *including* the 11–12.5 ms
encode, and near-flat in sprite count (28.6 → 25.6 from 0 to 16 sprites — compositing is ~1 ms;
the cost is the fixed viewport encode+write). The full-screen battlefield sustains the coder
GIF's native 25 FPS; at a C&C-style 12–15 FPS tick it uses under half the measured budget, on
one core, before any dirty-region or caching work.

## F145 — the sprites' alpha is feathered, and it decides where transparency is allowed

Found during the build, confirmed against ground truth: cto-E-idle carries **5,062
semi-transparent pixels (alpha 1–127) against ~10,000 opaque** — AI-rendered soft alpha across a
third of the body, not just an anti-aliased rim. Sixel has no alpha channel, so Codex's
threshold-128 rule punches visible holes in a *floating* sprite on the terminal background. The
resolution is architectural and already the plan: sprites are alpha-blended onto the opaque
battlefield composite (the spike's `blit()` does true source-over), where the feathering renders
correctly and costs nothing. Rule for the real console: **transparent-background sixels are for
incidental glyphs only; anything from the sprite corpus goes through the composite.**

## Verdict

**The spike passes on all five questions, and the flagship is feasible on the measured machine
with margin.** The RE-SCOPE's bet is now backed by numbers from the real terminal: a
C&C-1995-style Ratatui console with a live sixel battlefield runs at native sprite frame rate on
stable Windows Terminal, and the fallback ladder (text over SSH, F136/F141) remains intact for
every terminal that answers probe with less. RGB332's look on the battlefield JPEGs is not a
tax — banding shows only in the sky, and the quantisation reads as period-correct (F140 held).
Remaining spike-scale unknowns worth one line each: sixel over the *inline* viewport (the spike
used the alternate screen throughout), and behaviour under WT's canvas renderer versus Direct3D
on other machines. Neither blocks Phase 2 design.
