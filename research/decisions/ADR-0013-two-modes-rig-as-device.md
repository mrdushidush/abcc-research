# ADR-0013 — Two modes; a remote rig is a device; `Provider` takes `&self` and returns a stream

- **Status:** ✅ Accepted — with one part **unrunnable today** and stated as such (§5 below)
- **Date:** 2026-08-28
- **Deciders:** Claude Code (W10, measured on this machine 2026-08-28), ratified with `SUMMARY.md`
- **Sources:** W10 F464–F474 · `research/W10-mode-matrix.md` (the §16 deliverable) · W11 F275 ·
  W1 F79 · W7 (redaction, 6 of 13 shapes) · W9 F462/F463
- **Depends on:** ADR-0005 (mode transitions are events), ADR-0004 (no new Task state)

## Context

**All four brief items turned out to be blocked on something already on this disk and already the
wrong shape** — and in three cases the donor's own comments say so.

1. 🚨 **Multiplayer's mechanism is not installed.** `--rpc` parses on the shipped `llama-server` and
   then fails: the flag lives in `llama-common.dll` and the backend implementing it ships in **none
   of the eight** llama.cpp runtimes on this machine (F464).
2. 🚨 **The transport that *does* work has no auth at all.** LM Studio's OpenAI-compat port answers
   **HTTP 200 to a request with no key and to a request with a wrong key**, and its exposure control
   has exactly two documented positions: loopback, or **every** interface (F474). **Tailscale is an
   interface, not a filter.**
3. **The provider abstraction has never been proven** — **one production implementation out of
   eighteen**, pinned to a concrete type at every production call site, with a signature
   (`&mut self`, returns a `Vec`, blocking) that makes co-op's headline requirement — an async
   escalation that does not stall the local pipeline — **unrepresentable** (F466–F468).
4. **Egress is guarded on the tools and never on the model call**, which is the one path a co-op
   payload actually leaves by; and redaction — which W7 measured as leaking **6 of 13 shapes** — is
   wired to six log and transcript sites and to **nothing on the wire** (F469–F471).

And the mesh the brief calls the proof rig is real but mostly *absent*: three nodes, two offline,
the test target a family laptop last seen a day ago (F465).

## Decision

### 1. `Provider` takes `&self` and returns a stream — two cases, not three

```rust
pub trait Provider: Send + Sync {
    fn id(&self) -> ProviderId;        // on every event; the log, not the caller's memory
    fn class(&self) -> ProviderClass;  // Local | Cloud — the egress-relevant fact
    fn start(&self, req: &ApiRequest<'_>) -> Result<Box<dyn TurnStream>, ProviderError>;
}
```

**`&self` rather than `&mut self` is the whole point**: it permits a pending cloud turn and a running
local turn to coexist, which the inherited trait forbids. `TurnStream` yields events one at a time
and is cancellable, which ADR-0006 and ADR-0012 already require. **`ProviderClass` is two-valued on
purpose** — it is the predicate the egress guard binds to, and **a value only ever read by a `match`
asking "does this leave the machine" must not have a third arm that answers "sort of".**

### 2. 🚨 A remote rig is a **device on the local provider**, never a peer

The brief asks whether a rig is another provider behind the same interface, or needs its own plane.
**It is neither.** llama.cpp's own RPC documentation says the runtime *"distributes model weights and
the KV cache across all available devices — both local and remote — in proportion to each device's
available memory"* (retrieved 2026-08-28). **A rig therefore spreads one model thinner; it does not
add a second worker.** It buys parameters or context at LAN latency and **buys no parallelism at
all** — which compounds F275 (co-residency is impossible on this card) and F79 (23.77 s to swap).

So a rig is configured *on the local provider* as a device list, and it changes that provider's
**capability** — a bigger model, or a longer context, becomes resident — rather than adding a routing
target. **Nothing above the provider ever names a rig.**

### 3. Mode is a per-run one-way ratchet, and a downgrade is an event

- **Two values matter at runtime: `SinglePlayer` and `CoOp`**, differing only in whether a `Cloud`
  provider is admitted. Mode is **a property of a run**, fixed at admission and **recorded as the
  run's first event**.
- **Transitions are downward only and sticky.** `CoOp → SinglePlayer` is permitted on a budget
  ceiling, an egress denial or a network failure, and **latches for the rest of the run**. The
  reverse is **denied**: an upgrade mid-run would make the run's own egress record retroactively
  wrong.
- **The transition is an event on the durable log**, carrying reason, `Seq` and the provider that
  failed — so the console can show it, replay reproduces it, and **the effective mode at any point is
  a projection** (ADR-0005).
- **In flight at the moment of downgrade:** an attempt with an outstanding cloud call is cancelled
  and tombstoned `HardFailure(egress_revoked)`; its task returns to `Queued` and is re-attempted
  locally. Attempts with no outstanding cloud call are untouched. ✅ **No new Task state is
  introduced by any of it** — it reuses ADR-0004's per-state contract table unchanged.

### 4. The egress engine binds the **provider**, not the tool

Three things get built: **(a)** a per-repo policy **resolved at run admission and frozen into the
run**, because a policy that can change mid-run cannot be audited; **(b)** a redaction pass **at the
`Provider::start` boundary** for every `ProviderClass::Cloud` call — **new code, not `redact.rs`
extended outward**; **(c)** an audit record per outbound payload — hash, byte count, policy decision,
redaction hits — **as event rows**, not a private JSONL.

It inherits `egress.rs`'s three *shapes* verbatim (as specification, per ADR-0001): **one registry
with a maintenance contract, a CI test that drives every entry through the real dispatcher and
asserts the refusal, and a startup preflight.**

▶ **`SinglePlayer` is then a policy, not a code path** — zero `Cloud` providers admitted — which is
the whole reason it can be the *primary* mode rather than a degraded fallback.

### 5. Rig registration: a claim that carries its provenance, absent by default

Every advertised field — VRAM, system RAM, resident models, measured tokens/sec, queue depth —
carries **how it was learned: probed, self-reported, configured or stale**, so *"a rig is slower than
advertised"* has somewhere to live and a self-reported number can be distrusted without a special
case. 🚨 **The default health state is `Absent`, not `Unknown`** — two of three nodes are offline and
the test target is a household laptop, so **absence is the common case.**

⚠ **None of this is built until F464 is resolved**, and the honest order is: **(i)** W2 re-opens the
serving-runtime question with *"does it ship `ggml-rpc`?"* as a new criterion; **(ii)** the
registration record is designed and proved against a **second local instance on loopback**;
**(iii)** the laptop is a confirmation, not a dependency. **When the Tailscale proof runs, it runs
behind the overlay from the first attempt, never on the LAN "just to see"** (OQ-W9-5).

## Consequences

- **Losing air support mid-mission becomes an event on the field**, with a reason and a timestamp,
  instead of a silent config change nobody sees.
- **Multiplayer keeps its best moment even after being demoted from parallelism to capacity**:
  reinforcements arriving means the *big brain* becomes available, which is a better story than
  "throughput went up 4%".
- **The single-player game must be good with the network unplugged** — with zero standing cloud spend
  and no installed RPC backend, the machine on the desk is the whole army.
- **One open question is genuinely David's**: does a downgrade abandon the run's *completed* cloud
  work, or keep it and mark the run mixed-provenance (OQ-W10-4)? And a second: leave
  `logSensitiveData: true` on the local server as a useful audit, or turn it off as a second
  unredacted sink (OQ-W10-5)?
- **Boxing cost on a per-token path is unmeasured** (OQ-W10-2). ▶ The confidence-raiser is one day's
  work and it is Phase 3's first provider commit: implement `Provider` with the existing client
  behind it and a second loopback instance standing in as the "rig".

## Alternatives rejected

- **A third trait case for remote rigs** — a rig has no wire protocol distinct from the local
  server's. A third arm would be a case that never differs from the first, and every `match` would
  carry a redundant branch a later reader would try to fill.
- **Extending `redact.rs` to cover the wire** — it is too weak *and* on the wrong side; **reusing it
  would make a measured leak look guarded.**
- **Reversible mode transitions** — upgrading mid-run rewrites the meaning of every earlier event in
  the run's egress record. **The cost of the ratchet is one abandoned run; the cost of reversibility
  is an unauditable one.**
- **Binding the server to `0.0.0.0` behind Tailscale** — the switch exposes *every* interface, the
  endpoint has no auth, and a tailnet's default ACL is permissive between own nodes. **Bind the
  tailnet address specifically, or do not expose it.**
- **A gateway process** — it would route co-op payloads through an opaque hop at exactly the place
  the project has no visibility today.

## What would falsify this

**A runtime that ships `ggml-rpc` arrives, and a rig turns out to add a worker rather than spread one
model.** That would overturn the *device* ruling and reopen the third trait case. Everything else
here — `&self`, the two classes, the sticky ratchet — is independent of it, because it is forced by
the co-op requirement and the egress predicate rather than by the transport.
