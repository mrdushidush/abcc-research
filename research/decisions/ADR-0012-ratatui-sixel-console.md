# ADR-0012 — Ratatui + sixel is the primary console; SSE + SQLite; one `seq` with four roles

- **Status:** ✅ Accepted — the primacy reversal is **David's decision of 2026-08-19** (F140–F141)
- **Date:** 2026-08-28
- **Deciders:** David (TUI primary, web dropped), Claude Code (transport, verbs, fun)
- **Sources:** W5 F93–F145, esp. **F103** (eight verbs → three mechanisms), **F123–F126**
  (transport), **F127–F130** (fun), **F140–F145** (the decision and the sixel spike) · W1 F79
- **Depends on:** ADR-0005 (`seq` is the log's primary key), ADR-0004 (the states it renders)

## Context

Item 1 recommended a web console and David accepted it on 2026-08-18. **He reversed it a day
later**: the TUI is primary, the web console is dropped for now, and **a C&C-1995-style Ratatui
console with a live sixel battlefield is the flagship component** (F140–F141). Everything downstream
was re-scoped rather than rewritten — item 7's fun position is surface-agnostic, and the reversal
makes the palette part of the identity rather than a compromise.

**The spike then passed on all five questions** (2026-08-19, David's own Windows Terminal):

- **It renders**, and the encoder is hand-rolled because `ratatui-image`'s stdio font query panics
  on Windows — Windows is absent from its compatibility matrix. ⚠ Windows Terminal has **sixel**
  (stable ≥1.22; this machine 1.24), **not** kitty graphics; `arewesixelyet.com` is stale on this,
  **trust the machine**.
- **75–120 px reads as C&C at arm's length** — David's judgement, bracketing the predicted ~3.7×
  downscale from v1's 280 px raster (F143).
- **The 97-frame coder GIF animates at its native 25 FPS**, 40 ms/frame, encode 0.53 ms/frame.
- **The composite battlefield sustains 25.6–28.6 FPS end to end**, including the 11–12.5 ms encode,
  and is near-flat in sprite count (28.6 → 25.6 from 0 to 16 sprites). At a C&C-style 12–15 FPS tick
  it uses **under half** the measured budget, on one core, before any dirty-region work.
- 🚨 **The binding constraint is screen area, not throughput** (F144): Windows Terminal ingests a
  steady ~23.5 MB/s, 64 pre-encoded sprites — the grid capacity of the whole terminal — still run at
  55 FPS, and the extrapolated 15 FPS ceiling is **~235 sprites**, more than three screens' worth.

## Decision

### 1. Ratatui primary, sixel battlefield, with a fallback ladder

The console is a Ratatui TUI in the terminal where the operator already lives. The sixel
battlefield is the flagship, and **the text fallback ladder stays intact for every terminal that
answers the probe with less** (F136/F141) — which is also what `PLAN.md` puts in **Skeleton**: a
plain-text Ratatui reader over the event log, so the event-shape contract is enforced by code from
the first milestone, and Console *extends* that reader rather than replacing it.

### 2. 🚨 Sprites go through the composite, always

**Transparent-background sixels are for incidental glyphs only; anything from the sprite corpus is
alpha-blended onto the opaque battlefield composite** (F145). The reason is measured: `cto-E-idle`
carries **5,062 semi-transparent pixels (alpha 1–127) against ~10,000 opaque** — AI-rendered soft
alpha across a third of the body, not an anti-aliased rim. Sixel has no alpha channel, so a
threshold-128 rule punches visible holes in a *floating* sprite. Blended onto the composite the
feathering renders correctly and costs ~1 ms.

### 3. SSE + SQLite, and one integer with four roles

**`seq` is the event id, the SSE `Last-Event-ID`, the paged-read cursor and the scrub position**
(F126) — and, per ADR-0004, the `since:` in every lifecycle variant. **Two cursors that must agree
are two cursors that will not.** Timestamps stay as data; they are never the cursor.

**No WebSocket** until something needs bidirectional streaming: the console reads over SSE and
writes through a control endpoint that appends a row (ADR-0006).

### 4. Eight verbs, three mechanisms

| Mechanism | Verbs it delivers |
|---|---|
| **A control channel** with a step boundary the worker checks | pause / resume, kill, re-route |
| **A typed lifecycle with checkpoints** | retry, edit a task prompt, take over manually |
| **A durable event log with a paged read path** | replay, and every after-action view |

▶ **Build the three mechanisms; treat the eight verbs as the acceptance list for them.** **The risk,
named: eight verbs that half-work are worse than three that work.** ⚠ **The unit of control is the
task**, because the unit of control must be the unit that holds resources — every verb ends in
*"…and then what happens to its model slot and its workspace lock?"*

**Re-route shows the operator its price**: a 23.77 s model swap is a visible cost, not a hidden
pause (ADR-0003).

### 5. Fun is six queries over the event log

**The written position, computable without asking anyone anything** (F129):

| §7 constraint | The observable | Bar |
|---|---|---|
| No dead air | longest silence inside a run | **no gap > 10 s without a liveness mark**; report p50/p95/max |
| Speed where it is felt | first console event − command accepted | **< 1 s**, independent of TTFT |
| Legibility | screen switches before the first operator command | fewer is better, tracked as a trend |
| Agency | control events per run | **> 0 in a meaningful share of runs** — a control bar nobody touches is decoration |
| Personality with an off switch | theme/audio setting-change events | off **and later back on** proves it is a preference, not an irritant |
| Honest failure | replay-cursor movement on failed runs ÷ failed runs | a failed run that gets replayed is an interesting one |

Plus the §16 test made loggable: **unprompted opens per week**, **idle-open time**, and
**abandonment split by whether the operator intervened first**. And the outcome measure that must
never be dropped: **wall clock per task against the Claude Code baseline**, owned by W8.

🚨 **The 10-second bar is the single most actionable line in W5.** At realistic agentic context sizes
the model crosses it before it emits anything, and the harness once sat silent for **40 minutes —
240× the attention limit**. *Fun here means the operator is never uninformed for more than ten
seconds, can always intervene, and chooses to keep the thing open — and every clause is a query over
the event log, not a feeling anyone is asked to report.*

### 6. The off-switch is cosmetic, and that is the honest answer

The RTS enum stays military (ADR-0004); **a theme is a label map from enum variant to displayed
string**, exhaustive over the enum, with `classic` as the identity map onto functional names — so a
new state cannot ship without a label in every theme. **What this costs, said plainly: logs and
field names stay military even with the theme off.**

## Consequences

- **The agency is in the terminal, not in a dashboard.** That is what makes the control bar
  meaningful and what W5's whole fun layer is built on.
- **Replay-as-primary makes the after-action screen nearly free** — it is the same paged read as the
  live view, positioned at a different `seq`.
- **The 44 MB of art and the 96 voice lines finally have an expression.** They are copied assets
  (ADR-0001), and two lifecycle states have no line yet (`Holding`, `Commandeered`) — an asset-list
  item that blocks nothing.
- **Two spike-scale unknowns remain and neither blocks the design**: sixel over the *inline*
  viewport (the spike used the alternate screen throughout), and WT's canvas renderer versus
  Direct3D on other machines.

## Alternatives rejected

- **A web console or Tauri as primary** — reversed 2026-08-19 by David. It stays possible later: the
  transport is SSE over an event log, which a browser reads as easily as a terminal.
- **Per-sprite transparent sixels** — F145: the corpus's feathered alpha punches holes.
- **A separate cursor for the transport and the store** — F126.
- **A 10-second poll for updates** — it is what caused the frontend OOM the donor's ring buffer was
  introduced to fix (F112).
- **Adopting Langfuse for observability** — six services, ~21.5 GiB on a 32 GB box. **Adopt the
  vocabulary, own the store, export optionally.**
- **Turning the domain model neutral when the theme is off** — impossible without reversing the
  RTS-in-the-model decision, which was taken deliberately.

## What would falsify this

**The sixel battlefield does not survive a real workday** — tmux, SSH, or the operator turning it
off. That is SUMMARY.md's fifth falsifier, and it is measurable by F129's own instruments: the
theme-switch events say whether the personality is a preference or an irritant. If it fires, the
only measured differentiator is gone and TUI-primary reopens — the text ladder already exists, which
is precisely why it ships in Skeleton.
