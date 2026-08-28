# The mode capability matrix

**The §16 deliverable, defined at `RESEARCH_BRIEF.md:513`:** *"a mode capability matrix showing what
is available in each mode and what happens when a mode is downgraded mid-run."* Companion to
`research/W10-fleet.md`; findings cited here are F464–F474 there. **It must agree with W3** (§16),
and §3 below is the line-by-line check that it does. Written 2026-08-28.

## What a mode is, and what it is not

**A mode is a property of a run, not of the installation** — fixed at admission, written as the
run's first event, and thereafter a *projection* of the event log rather than a stored column (W3's
"status is a projection" ruling, applied one level up).

**There are two runtime modes, not three.** `SinglePlayer` and `CoOp` differ in exactly one thing:
whether any provider of `ProviderClass::Cloud` is admitted. **Multiplayer is not a third column** —
F462 and F464 show a remote rig distributes one model's weights and KV across devices, so it makes
the *local* provider more capable rather than adding a peer. It is therefore a **modifier on the
local column**, and it is shown that way below. Anything that reads a mode reads two values.

## 1. Capability matrix

Legend: ✅ available · ⚠ available with a stated condition · ❌ not available ·
**⟨rig⟩** = the multiplayer modifier, i.e. what changes when one or more remote rigs are attached to
the local provider. Every ⟨rig⟩ cell is **blocked today by F464** — the RPC backend is not installed
in any of the eight llama.cpp runtimes on this machine — so the column states the design, and
OQ-W10-1 states the precondition.

| Capability | Single player | Co-op | ⟨rig⟩ modifier |
|---|---|---|---|
| Local provider (`ProviderClass::Local`) | ✅ the only one | ✅ carries the volume | ✅ same provider, more devices |
| Cloud provider (`ProviderClass::Cloud`) | ❌ none admitted | ⚠ admitted, and per Q7 usually **not configured** — zero standing spend | – no effect |
| Largest resident model | ⚠ bounded by one card; co-residency impossible (F275) | same as single player | ✅ **the point of a rig** — parameters or context bought at LAN latency |
| Concurrent in-flight turns | ⚠ saturates at **N=2** (W1/W2) | ⚠ N=2 local **+** 1 pending cloud | ❌ **no parallelism** — a rig splits one model, F462 |
| Async escalation (cloud call does not stall local) | – not applicable | ✅ requires the `&self` + stream trait (F468) | – no effect |
| Model swap between tiers mid-run | ⚠ **23.77 s** each way (F79) | ⚠ same, plus the cloud arm needs no swap | ⚠ swap re-plans the device split; cost unmeasured |
| Egress beyond loopback + local backend | ❌ **denied by policy, not by code path** | ⚠ only to admitted cloud providers, only after §2 | ⚠ tailnet only — never `0.0.0.0` (F474) |
| Redaction before egress | – nothing leaves | ✅ mandatory at `Provider::start`, new code (F471) | ✅ same guard, LAN is still egress |
| Per-repo egress policy | – vacuous (nothing may cross) | ✅ resolved at admission, frozen for the run | ✅ inherits the run's policy |
| Per-payload audit record | – nothing to record | ✅ W3 event rows: hash, bytes, decision, redaction hits | ✅ same rows, rig destination |
| Budget metering / ceilings | – no spend | ✅ per-run and per-day; hitting one **downgrades**, never fails (§2) | – no spend |
| W3 durable event log + replay | ✅ | ✅ | ✅ |
| Cancellation of an in-flight attempt | ✅ 4–14 ms (W3 F200) | ✅ local same; cloud call abandoned, tombstoned | ⚠ rig-side cancel is an open protocol question |
| `AwaitingOrders` / `Commandeered` (human) | ✅ | ✅ | ✅ — unaffected, these hold no provider |
| `Holding` (pause / Esc) | ✅ | ✅ | ✅ |
| M1 Plan, A1 Localize, A2 Change | ✅ local model | ✅ either class, per routing | ✅ |
| A3 Measure | ✅ **no model at all** — build, typecheck, suite, acceptance criterion | identical | identical |
| A4 Judge | ✅ one local call | ⚠ the one place a cloud call most earns its cost (W4) | ✅ |
| Console live view of the field | ✅ | ✅ | ⚠ rig health is a new tile; `Absent` is the default (F473) |
| Rig registration / health | ❌ | ❌ | ✅ the whole feature — claims carry provenance (F473) |
| Distributed dispatch across workers | ❌ nothing in the donor does this (`scheduler.rs` is cron) | ❌ | ❌ **still no** — F462; a rig is a device, not a worker |
| Deterministic replay from the log | ✅ | ⚠ cloud responses are recorded, not reproducible | ✅ |

**The row that matters most is "distributed dispatch": it is ❌ in all three columns.** The brief's
mental model of multiplayer is more workers; the measured mechanism is one bigger worker. Any design
that reads the matrix left-to-right expecting parallelism to appear in the third column is designing
for a machine that does not exist.

## 2. Downgrade: what happens when a mode changes mid-run

**Downgrade is one-way and sticky.** `CoOp → SinglePlayer` is permitted; the reverse is **denied**,
because an upgrade mid-run makes the run's own egress record retroactively wrong (W7's ruling: the
control that works is denying the class). A run that needs cloud after downgrading is a **new run**.

**The transition is an event, not a config change** — `ModeDowngraded { from, to, reason, seq,
provider }` on the durable log. The effective mode at any `Seq` is therefore a projection, the
console can render the moment it happened, and replay reproduces it. No new Task state is
introduced, and W3's per-state contract table is used unchanged.

| Trigger | Detected by | In-flight attempt **with** an outstanding cloud call | In-flight attempt without one | Run |
|---|---|---|---|---|
| Per-run or per-day budget ceiling reached | budget meter, before dispatch | none can exist — the ceiling is checked *before* `start` | untouched | continues in `SinglePlayer` |
| Network failure / provider unreachable | `ProviderError` from `start` or mid-stream | cancel; attempt tombstoned `HardFailure(egress_revoked)`; task → `Queued`, re-attempted locally | untouched | continues in `SinglePlayer` |
| Egress policy denies the payload | redaction/policy pass at `Provider::start` | never dispatched; attempt → `Queued` for a local attempt | untouched | continues; **the denial is logged with the reason** |
| Operator downgrades by hand | console action | cancel, as for network failure | untouched | continues in `SinglePlayer` |
| Cloud provider returns repeated errors | retry policy exhausted | tombstoned, task → `Queued` | untouched | continues in `SinglePlayer` |
| ⟨rig⟩ disappears mid-run | heartbeat, default `Absent` (F473) | – rigs serve no separate call | the *local* provider must reload without the rig's devices — **a 23.77 s-class event** (F79), not a free failover | continues; capability row drops |

**Three rules the table encodes.**

1. **A downgrade never fails a run.** §9's budget bullet asks for exactly this — *"the run degrading
   to single player rather than failing at the ceiling"* — and it generalises to every trigger. The
   only thing a downgrade may cost is one attempt.
2. **Only attempts holding a cloud call are touched.** Everything else keeps its slot, its workspace
   lock and its liveness clock, per W3's per-state contract table.
3. **The rig row is the odd one out**, because losing a rig is not a failover — it is a resident-model
   change, and the local provider has to rebuild its device split. That is why rig health defaults to
   `Absent` rather than `Unknown`: an optimistic default turns a laptop being asleep into a stall.

## 3. Agreement with W3 — the §16 check, row by row

| This matrix says | W3 mechanism it relies on | Agrees? |
|---|---|---|
| Mode is a projection of the log, not a column | "status is a projection"; one write path | ✅ same rule, one level up |
| Downgrade is `ModeDowngraded` on the durable log | the durable event log is the only thing that crosses | ✅ |
| Cancelled cloud attempt becomes `HardFailure(egress_revoked)` | attempts are immutable; failure is a tombstone (F151) | ✅ reuses the existing tombstone shape |
| Task returns to `Queued` after a revoked attempt | `Queued` holds no slot, no lock, no clock; boot reconciliation re-admits | ✅ no new state |
| `AwaitingOrders`, `Holding`, `Commandeered` unaffected by mode | operator states are watched but never reaped | ✅ |
| Rig health defaults to `Absent` | watchdogs distinguish "no human yet" from "no progress" | ✅ same distinction, applied to a device |
| No new Task state anywhere in this document | seven-row per-state contract table; a new variant must add a row | ✅ **none added** |
| A downgrade is a report, never a gate | "a model verdict is a report and never a gate" | ✅ only A3 Measure gates |

## 4. What is not decided here

- **Whether ⟨rig⟩ is ever runnable** — F464, OQ-W10-1. Everything in the modifier column is design
  against a backend that is not installed.
- **Mixed-provenance runs** — OQ-W10-4: after a downgrade, is completed cloud work kept and the run
  marked, or discarded? The matrix is written so either answer fits.
- **Rig-side cancellation** — the one ⚠ in the cancellation row; the protocol has no prior art in the
  category (F462: zero hits for `multiplayer`, `co-op`, `multi-machine`, `peer-to-peer`, `tailscale`
  across 340 catalogued projects).
