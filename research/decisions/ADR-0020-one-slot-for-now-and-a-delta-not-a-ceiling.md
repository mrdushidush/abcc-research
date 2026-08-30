# ADR-0020 — One slot for now; and the memory clause is a delta, never an absolute

- **Status:** ✅ Accepted · **supersedes [ADR-0003](ADR-0003-slot-is-the-unit.md)'s *count* only**
  (N=2 → N=1). The unit *is* still a runtime slot, and every other consequence in ADR-0003 stands.
  ⚠ It also revises **ADR-0006**'s thread inventory row *attempt workers = 2* to **1**.
- **Date:** 2026-08-30
- **Deciders:** **David**, on the FLEET probe — *"dont need two slots for the time being — we will
  revise it in the future — right now parallel=1 is best"* and *"replace it with delta over a
  same-session baseline + min_avail_mib + the blind window"*
- **Sources:** `research/FLEET-P1-two-slots.md` F539, F540, F541, F542, F545, F546, F547 ·
  W2 F83 · sweep B F488
- **Depends on:** ADR-0003 (the unit), ADR-0005 (admission is a projection), ADR-0010 (retry
  budget 2)

## Context

ADR-0003 set N=2 from two independent measurements that landed on the same number: VRAM, and F83's
aggregate throughput saturating at two concurrent sequences. Neither was ever run against **this
project's own workload** — an attempt is a model conversation *interleaved with tool calls and a
cold `cargo` build*, not the pure ~5.5k-token completions F83 measured. `PLAN.md`'s FLEET milestone
existed to close that gap and its exit criterion measured only memory.

The probe ran both scenarios: two real attempts on `D:\dev\abcc`, sequentially and concurrently,
against one `llama-server` at `--parallel 2 -c 65536`. Three results decide this ADR.

**1. Nothing blocks concurrency.** The reason `--parallel 1` had always been used was written into
`corpus_review.rs` — *two turns in flight push each other past the 90 s idle gap* — and it had never
been measured. **It is false** (F545): across 171 model calls in four post-fix arms, max time to
first byte under two concurrent attempts was **25.5 s**, and the worst wait of the whole session,
**30.3 s, happened sequentially** on a 30,000-token prompt. The variable is prompt size, not slot
count.

**2. Nothing pays for concurrency either.** Completion tokens per second of arm wall clock:

| pair | sequential | concurrent | concurrent is |
|---|---|---|---|
| `SEQ-F1` / `PAR-F2` | 66.6 tok/s | 82.6 tok/s | **+24%** |
| `SEQ-F2` / `PAR-F3` | 34.9 tok/s | 28.9 tok/s | **−17%** |

🚨 **The two matched pairs disagree in sign, and the reason is in the same table.** The *same arm*
on the *same two tasks* ran **393 s and 1,113 s** (2.8× apart) and **378 s and 1,006 s** (2.7×
apart). **Within-arm variance is 2.7–2.8×; the between-arm difference is 1.1×.** Nothing here
samples at temperature zero, so an attempt takes 5 rounds or 24 depending on the sample. **A
difference eight times smaller than the noise is not a measurement** (F546).

**3. Memory is a wash, and ADR-0003's own falsifier did not fire.** `SEQ-F2` peaked at **50.60 GiB
commit / 3,155 MiB available**; `PAR-F3` at **50.02 GiB / 2,976 MiB** — 0.58 GiB apart with the
*sequential* arm higher (F547). Two slots plus two worktrees plus real builds **held inside
31.92 GiB**. ▶ **So N drops to 1 for the opposite reason to the one ADR-0003 anticipated**: not
because two slots did not fit, but because the second slot bought nothing measurable. The second
slot itself costs **187 MiB** on-card — `--kv-unified` pools the window rather than dividing it
(F541) — so the slot count was never a memory decision at all.

## Decision

🚨 **N = 1. One slot, `--parallel 1`, until something wants the throughput.** Two slots are
**deferred, not cancelled**: *"we will revise it in the future."*

**FLEET is descoped, not dropped.** Everything the milestone owes that is not the second slot is
still owed, and one item got sharper:

- Admission as a projection of the store; worktree isolation; **the gate serialised** (F542 prices
  that at 34.4 s against 4.1 GiB of commit and a 5× better responsiveness figure); the tool-head set
  frozen per attempt.
- 🚨 **`NextAction { Attempt | Stop | HandToOperator }` with retry budget 2, which is enforced
  nowhere.** With one slot its receiver is **a loop, not a scheduler** — *less* work than the
  two-slot version and the same design. This is now the milestone's centre of gravity.
- 🚨 **The breaker's input is a real one-token completion, not a liveness endpoint** (F539). A
  wedged `llama-server` answered `GET /v1/models` normally and completely while **every**
  `POST /v1/chat/completions` returned nothing for 60 s, and it took *both* slots down until a
  reload. Retry budget 2 would otherwise spend both retries against a server that cannot answer.

### The memory clause, restated — three numbers, never one

**Replacing** *"peak must stay under the 28.03 GiB ceiling of record"*, which could not be met and
could not have meant anything if it were:

1. 🚨 **The delta over a same-session baseline. Never an absolute.** This session's *unloaded idle*
   baseline was **17.58 GiB** against session 19's 8.99 — **because Chrome was open** — so loading
   the model alone reached **32.83 GiB**, past a "ceiling" the run had not begun to approach. The
   **delta reproduced to within 0.8 GiB** (15.24 against 16.01) for the identical serving
   configuration. F488 already said quote a peak against its own baseline; the old clause then
   quoted an absolute from a different session and contradicted it (F540).
2. **`min_avail_mib`** — the free-physical-RAM floor, which is what the box actually feels.
   **2,976–3,155 MiB** under two attempts, and the same in both modes.
3. **The blind window** (`max_gap_ms` on the host stream) — which is also the only instrument
   *"box still responsive"* has ever had (F543): **1.0 s idle · 3.7 s one cold build · 19.6 s two
   concurrent builds.** A sampler asking for one sample per second that cannot get scheduled for
   nineteen is the box saying it is not responsive, with no person needed in front of it.

## Consequences

- **The console shows one slot.** ADR-0003's *"the console shows two slots — the honest picture of
  the machine"* becomes one, and the honesty argument is unchanged: it draws what is there.
- **ADR-0006's thread inventory drops from ~8–11 to ~6–8** (attempt workers 2 → 1, and one
  `reqwest-internal-sync-runtime` rather than two). Nothing else in it moves; threads still own the
  work and the runtime still lives only at the console edge.
- **F83 is not retracted and is not the authority here.** It measured pure completions and remains
  correct about them. What it could not see is a workload whose wall clock is dominated by tool
  calls and cold builds — where the two slots' builds contend for the CPU that `--threads 2` leaves
  the server.
- ⚠ **`Σ(active sequence lengths) ≤ ctx` still binds** and is now trivially satisfied. What *can*
  approach the idle gap is a **single cold prefill of a very large prompt** — 30.3 s observed at
  ~30k tokens, and the window is 65,536. Watch the window, not the slot count.

## Alternatives rejected

- **Keeping N=2 because it is already designed for.** The design cost is real but small, and F546
  says the benefit is unmeasured rather than measured-small. Shipping a scheduler for an effect
  nobody has demonstrated is how ADR-0003's own rejected alternative — *a unit type per stage* —
  produced two portraits that could never be lit.
- **Running more repetitions now to settle F546.** The noise is 2.7×; narrowing a 1.1× effect under
  it costs many arms at ~15 minutes each, and **nothing is waiting on the answer.**
- **Dropping the slot abstraction to a single hard-coded worker.** ADR-0003's unit survives intact;
  only N moves, which is exactly what its own falsifier said would happen. A hard-coded worker would
  have to be undone to revisit this.

## What would falsify this

**Something wanting the throughput** — a queue that is genuinely backed up, or a self-host loop
whose wall clock an operator is waiting on. Then the reopening evidence has to beat F546's noise,
and *one more pair proves nothing*: it is **either** many repetitions per arm, enough that the
interval is narrower than the effect, **or**, far cheaper, a **deterministic subject** — replay two
fixed transcripts rather than two live agents, which removes the sampling variance that swamped this
probe.

⏸ **Two open ends survive either way.** `--parallel 1` versus `--parallel 2` was never compared
**under load** — everything after the load rung ran on one `--parallel 2` server, on the reasoning
that a sequential arm uses one slot, which F541's 187 MiB supports but does not prove. And the wedge
of F539 has **one occurrence and no cause**; what it justifies today is the health check, not a
theory.
