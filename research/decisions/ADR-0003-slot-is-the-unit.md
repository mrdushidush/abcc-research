# ADR-0003 — The unit is a runtime slot, N=2, set by VRAM

- **Status:** ✅ Accepted
- **Date:** 2026-08-28
- **Deciders:** Claude Code (W11/W2 measurement), ratified by David with `research/SUMMARY.md`
- **Sources:** W11 F228, F229, F230, F238, F241, F275 · W1 F68, F75, F77, F79, F80 ·
  W2 F81, F83, F86
- **Depends on:** ADR-0002 (phases are the vocabulary a slot plays, not the thing being counted)

## Context

The brief's §10 gives every pipeline stage its own unit type. v1 built that, and the result is
enumerated in W11: **three unit types, one that ever receives work** (F228), and the unit type
degrading into **a scheduling token that carries resource exhaustion in a complexity field** (F229).
F230 measured the same inflation shape in every donor — declared-to-constructed runs about **3×** —
and §10 proposes a fourth.

The hardware answers the question independently of any of that. **Co-residency on this box is not
expensive, it is arithmetically impossible** (F275): with the champion resident at the held
constants, `nvidia-smi` reports **16,311 MiB total, 14,841 used, 1,210 free**, while the smallest
model `lms ls` reports on this host is **4.41 GB ≈ 4,205 MiB**. A second model needs **3.5× the free
VRAM before its own KV cache**, and shrinking the champion's window does not help: KV is allocated
in full at load (F77), so the entire window is worth about **905 MiB** — dropping it to zero frees
less than a quarter of what the smallest model on disk needs. **The card is the binding constraint,
not the context setting.**

And two slots is where the box stops paying. F83 loaded `--parallel 4 -c 65536` with a distinct
~5.5k-token prompt per worker:

| N | wall | ok | TTFT median | TTFT max | aggregate prefill | aggregate decode |
|---|---|---|---|---|---|---|
| 1 | 6.10 s | 1/1 | 4.92 s | 4.92 s | 910 tok/s | 16.4 tok/s |
| **2** | 7.28 s | 2/2 | 3.67 s | 5.16 s | **1,541 tok/s** | **27.5 tok/s** |
| 4 | 14.70 s | 4/4 | 7.23 s | 10.33 s | 1,511 tok/s | 27.2 tok/s |
| 6 | 21.82 s | 6/6 | 10.54 s | 19.25 s | 1,537 tok/s | 27.5 tok/s |

**Aggregate throughput saturates at N=2** — 1→2 buys +69% prefill and +68% decode; 2→4→6 buys
nothing (1,541 → 1,511 → 1,537, flat inside noise). Past 2 every additional worker is pure latency
tax, with the tail reaching 19.25 s. ⚠ **The honest correction to the brief's framing: it never
became unstable.** 13/13 requests succeeded, peak VRAM 15,339 of 16,311 MiB (94.0%), 69 °C, no
throttle. **The limit is economic, not a cliff.**

## Decision

**A unit is a runtime slot: a resident model plus a tool policy. It is not a stage and it is not a
role.**

- **The count is set by VRAM and measured concurrency — N=2 — never by the length of the phase
  list.** One slot plays every phase in turn.
- **A phase is the role a slot plays for one call**, which is why adding a phase costs nothing and
  adding a unit type costs a portrait on the console that can never be lit.
- **The architecture buys attempts, not tiers.** A tier change is a swap, and F238 prices it at
  three components, not one: the **23.77 s** round trip (F79), plus the arriving model's cold
  prefill, plus every head the champion had warm coming back cold — **~32–41 s per gate at 17k
  tokens and ~50–76 s at the daily driver's window**, against **zero** for same-model-no-history.
- ⚠ **The KV bound is a sum, not a division.** `--kv-unified` is on, so slots pool the window:
  the real constraint is **Σ(active sequence lengths) ≤ 65,536**. Four workers at the daily driver's
  61,440 is arithmetically impossible; four at ~16k each is the actual budget.

## Consequences

- **Two slots is the fleet, and it is the fleet for a reason that is measured** — this is the number
  the FLEET milestone must hold under a real workload with a worktree and a real build, not under an
  idle probe (`PLAN.md` § Fleet).
- **A cheaper tier costs more than it saves for any single call** (F238). A 4 B triage model saves
  ~10 s of decode on a 1,000-token brief against ~12–18 s of swap plus at least 8.5 s of destroyed
  cache, each way — and the retry loop forbids the long same-tier batch that would amortise it.
- **A model load is a cache wipe** (F241, F75): LM Studio spawns a fresh `llama-server` per load and
  the prefix cache lives in that process. A prompt head warm at **2.626 s** returned at **10.584 s**
  after unloading and loading the *same* model.
- **The console shows two slots.** That is the honest picture of the machine, and W5's fun argument
  is built on it: a supply line the player learns to respect, not a spinner.
- **Independence at the gate is bought by swapping or not at all** — which is what sends W6 to
  same-model-fresh-call as the Judge (ADR-0008, ADR-0009).
- **Hands onward:** N=2 is the admission bound ADR-0005's projection computes against, and the
  frozen tool-head set of ADR-0011 exists because a slot's prompt head is the cache.

## Alternatives rejected

- **A unit type per stage** (§10, v1) — F228/F229: two of three never received work, and the type
  became a scheduling token. On a box that saturates at N=2, four unit types means four portraits of
  which at most two can ever be lit.
- **Co-residency — a second model held alongside the champion for independence or triage** — F275:
  impossible by subtraction, before any run.
- **Raising N to 4 for more builders** — F83: buys no throughput, and the tail latency doubles then
  quadruples. It would also break the Σ-sequence-length bound at any realistic window.
- **A tier ladder** — priced out here and rejected outright in W4; see ADR-0010.

## What would falsify this

**Two slots plus a worktree plus a real build cannot hold inside 31.92 GiB** — SUMMARY.md's risk 2
and its first falsifier. Peak system RAM already runs 8.99 → **28.03 GiB** (87.8% of physical), and
two cold builds alone leave 2.3 GB free. If FLEET cannot hold it, **the unit count drops to one, or
the box changes** — the slot abstraction survives either way; only N moves. ⚠ Measure it against a
**same-session baseline** (F488): a `peak_committed_b` quoted across sessions is meaningless.
