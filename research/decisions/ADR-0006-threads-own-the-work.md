# ADR-0006 — Threads own the work; one tokio runtime at the console edge; the log is the only crossing

- **Status:** ✅ Accepted
- **Date:** 2026-08-28
- **Deciders:** Claude Code (W3 probe, `research/spikes/w3-runtime/`), ratified with `SUMMARY.md`
- **Sources:** W3 F154, F172, F197, F198, F199, F200, F201, F202, F203, F204, F205 · W2 F83 ·
  W3 F162, F184
- **Depends on:** ADR-0005 (the log is the seam), ADR-0003 (N=2 sets the thread count)

## Context

The inherited claim was that async had been *"proved twice"* in the family. **F154 found that
threads proved once and tokio was never exercised**, and the probe then took the argument apart on
this machine.

**F197 — the engine contains no async at all, and is already running a tokio runtime.** Across 93
modules and 65,519 lines: `async fn` **0**, `.await` **0**, `tokio::` **0**; the string "tokio"
appears once, as an example crate name in a JSON schema. Concurrency is `std::thread` — 11 spawn
sites plus 58 uses of `mpsc`/`Arc<Mutex>`/`AtomicBool`. **And tokio 1.52.1 is in its `Cargo.lock`
already**, under `reqwest`'s `blocking` feature, which spawns a `reqwest-internal-sync-runtime`
thread per client — measured at exactly one extra OS thread per `blocking::Client`, released on
drop. So **"adopt tokio" is not a dependency decision — the dependency is already paid.** It is a
code-shape decision about 93 modules that currently have no colour at all.

**F200 — the one honest argument for tokio was cancellation, and it is discharged by measurement.**
A watchdog thread flips an `AtomicBool`; the reader checks it between SSE lines and drops the
response: **stopped at 14 ms and 4 ms**, with the server observing the dead socket one write cadence
later (~200 ms), or in **19 ms** where it polls. Combined with the ≤0.25 s slot release measured
against `llama-server` itself (F162), the cancellation argument is gone. It was never a runtime
capability; **it was a socket close, and a socket closes when its owner drops it.**

**F198 — the blocking timeout is a *per-read* budget, not a total-duration one.** Six body lines
1000 ms apart under a 2 s client timeout **complete in 5.003 s**; a 3000 ms gap **fails at 2.004 s**.
The deadline is recomputed inside each `read()`. **A fresh deadline per read is the definition of an
idle-gap timeout** — the mechanism F172 says the whole family lacks, sitting under the code already.

**F201 — the donor that "proved" tokio uses async as a calling convention**: 69 `async fn`, zero
`select!`, zero `Arc<`, and a runtime worker parked in a 200 ms sleep-poll for up to two minutes.

## Decision

🚨 **Threads own the work; a runtime owns the edge; the event log is the only thing that crosses.**

The fleet is OS threads — one per attempt, each owning its state, taking commands from a channel and
writing events through ADR-0004's single `apply()`. **`tokio` exists in exactly one place: the
thread running the console's HTTP server** (features `rt-multi-thread`, `net`, `sync` — *not*
`full`).

### The thread inventory, counted rather than hand-waved

| Thread | Count | Why |
|---|---|---|
| main / supervisor | 1 | admission, watchdog sweep, `apply()` ownership |
| attempt workers | 2 | one per concurrent attempt (F83's ceiling) |
| `reqwest-internal-sync-runtime` | 2 | one per `blocking::Client`, measured (F197) |
| tool child pipe drainers | ≤4 | 2 per running tool, only while one runs (F202) |
| console runtime workers | 2–4 | axum's runtime |
| **total, steady state** | **~8–11** | on a box whose GPU is the scarce resource |

**Nothing here is near the scale at which async's advantage exists** — cheap tasks in the tens of
thousands. The workload is two GPU-bound conversations and one operator.

### The seam

- **Downstream:** the SSE handler is a **reader** of the event log, positioned by `Last-Event-ID` →
  `seq`, tailing new rows. Two readers or ten make no difference to a worker.
- **Upstream:** `POST /control` **writes a `ControlRequest` row** and pokes an in-memory `Sender`.
  **The poke is a latency optimisation and never the truth**; boot replay is the backstop.
- **The runtime boundary and the data boundary are therefore the same line**, which is what makes
  this cost nothing.

### Timeouts, with the numbers on them

**Per-request, not per-client** — `RequestBuilder::timeout`, set from the rung: champion **90 s**,
R3 **180 s** (F199), roughly 2.4× each one's measured worst-case TTFB and 1.7–3.3× tighter than the
300 s inherited. Because the budget is per-read on a streamed body, **that same number is the
idle-gap timeout**: a stream silent for 90 s is a hang, and the worker records
`Stuck { signal: IdleGap }` — a class, never a generic failure.

⚠ **The inherited constant means two different things and a response header decides which.**
Claudette's `REQUEST_TIMEOUT_SECS = 300` is an inter-chunk budget on the streaming paths and a
*total* budget on the non-streaming fallback taken when a `stream: true` request comes back without
an SSE content type. 2.0 keeps both semantics and **comments the fallback**, because the constant
looks identical at both call sites.

## Consequences

- 🚨 **Two tests this design owes itself, and they are not optional.**
  1. **Pin the per-read semantic.** `RequestBuilder::timeout`'s *doc comment describes the opposite
     behaviour* — total duration, for a per-read implementation (F198). A future release could align
     the code to the doc and silently turn 2.0's hang detector into a wall clock.
  2. **Pin the cancel latency.** F200's 3–14 ms is the number the operator's abort button inherits.
- **The residue is honest and small.** `select!` would let a worker wait on the stream and the
  control channel *simultaneously*; the thread design samples the channel between lines. **The
  sampling interval is one SSE line — 13–18 ms** at measured decode rates. Against an operator's
  reaction time and a 23.77 s model swap, that difference does not exist.
- **Child pipes are drained on background threads from the moment the child starts** (F202) — the
  donor defect this avoids is a child that writes past the 64 KiB pipe buffer, blocks on `write`,
  and is recorded as a *timeout* for a tool that had finished its work.
- ⚠ **The dependency list survives ADR-0001 as a specification, not as an inheritance.** W3 wrote it
  as *"arrives with the copy"*; under the rewrite ruling the crates are still the right crates and
  the list is still ~16 direct dependencies, but every line of the code between them is written
  fresh. The new ones each have one reason: **`axum` + `tower-http`** (console and static assets),
  **`tokio`** (edge only), **`rust-embed`** (44 MB of identity in one binary), **`shared_child`**
  (kill a tool child from the control thread), **`thiserror`** (typed domain errors).

## Alternatives rejected

- **An all-tokio core** — F197 + F200 + F201: it recolours every function between `main` and the
  socket to buy `select!` over a 13–18 ms sampling interval, and the family's own async repo
  demonstrates the failure mode. ⚠ W3's fourth reason — *it ends the option of tracking Claudette
  upstream* — **is void under ADR-0001**; the first three are measurements and stand alone.
- **A blocking HTTP server, keeping tokio out entirely** — F203's dates: `tiny_http` last commit
  2023-05-16, `rouille`'s release from 2023, `astra` at 989 downloads/90d, `iron`/`nickel` 2019. **A
  long-lived SSE stream is exactly where an unmaintained server layer becomes the project's
  problem.**
- **`ureq` instead of `reqwest`**, which would remove tokio from the process entirely — a real
  option, alive, with **nine named timeout knobs** against reqwest's one. Rejected on the *shape* of
  those knobs: they are phase deadlines (`timeout_recv_response`, `timeout_recv_body`,
  `timeout_global`) and **none of them is an inter-chunk gap**. Where the body legitimately takes
  minutes and silence is the failure signal, the per-read budget is the better instrument.
- **`smol` / `async-std`** — F204; and **an agent framework** — F205: the agent loop is the thing
  being written, not a thing to import.
- **WebSocket** — until something needs bidirectional streaming (W5, unchanged).

## What would falsify this

**A worker legitimately needs to wait on more than the stream plus a sampled channel** — for example
if a phase ever fans out to several concurrent model calls *within one attempt*. Then `select!` buys
something real, and the runtime line moves inward one worker at a time rather than all at once.
