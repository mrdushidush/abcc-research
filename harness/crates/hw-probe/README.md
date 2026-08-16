# `hw-probe` — the instrument W1 and W2 owe every measured claim to

Brief §14 item 2 scopes W1+W2 down to "the open parts only", and one of them is not a question but
a build: *"Report peak VRAM **and** peak system RAM as a hard limit — **nothing in the family
measures either today**, so budget building the probe as part of this workstream."*

That was checked before writing a line, and it is accurate:

| where | what it measures |
|---|---|
| Claudette `crates/claudette/src/hw.rs` | `nvidia-smi --query-gpu=memory.total`, once. **Installed** VRAM. No peak, no system RAM, no temperature. |
| `harness/crates/w8-*` | nothing touches VRAM at all. `w8-run` captures `lms ps` verbatim into RUNMETA, which reports weights and `PARALLEL`, not usage. |

So this crate is new work, and it is the dependency root for the rest: the concurrency ceiling
("find the point where the machine becomes unstable and report it as a **hard limit**, not a tuning
suggestion"), KV-cache growth under full residency, model-swap cost, and W6's question of whether a
second model can sit beside the champion's 13.6 GB — none of them are answerable without it.

```bash
cargo run -q -p hw-probe --bin hw-probe -- doctor
cargo run -q -p hw-probe --bin hw-probe -- baseline --for 30s --out runs/hw-probe/idle.json
cargo run -q -p hw-probe --bin hw-probe -- run --pid <lm-studio-pid> --label load-65k \
    --out runs/hw-probe/load.json -- lms load qwen3.6-35b-a3b-mtp@iq3_s -c 65536 --gpu max --parallel 1 -y
```

`run` exits with the wrapped command's own status, so it drops in front of an existing step without
changing what that step means to whatever called it.

---

## 🚨 What this instrument cannot see. Read this before quoting a number from it

**A peak over samples is a lower bound on the true peak.** Nothing here except one number (below)
is a high-water mark kept by the kernel; the rest is a maximum over what was observed. An
allocation that rises and falls between two samples is invisible. **The width of that blind window
is printed beside every peak** — `max_gap_ms`, the widest gap the run actually experienced, not the
interval that was requested. A peak quoted without it invites being read as exact.

**The one exception, and it is worth knowing:** `\Process(<name>)\Working Set Peak` is a true
high-water mark maintained by the kernel, so **peak RAM for a named process is exact while peak
VRAM is a lower bound.** Nothing on this stack offers the VRAM equivalent — NVML keeps no
per-process high-water mark and WDDM does not either. That asymmetry should travel with any table
that puts the two side by side.

**Two cadences, an order of magnitude apart.** The GPU stream runs at ~107 ms actual against 100 ms
requested; the host stream cannot go below **1 second**, which is `typeperf`'s own floor. They are
reported separately and deliberately never averaged into one "sample interval" field, because such
a field would be wrong about one of them.

**`memory.used` is the whole card.** See F60 — per-process VRAM is unavailable from `nvidia-smi` on
this box. Either name a pid (`--pid`, which uses Windows' counters instead) or measure a
`hw-probe baseline` with the model unloaded and subtract.

---

## Design

Two long-lived child processes, each streaming CSV, each parsed on its own thread. Nothing is
spawned per sample.

| source | tool | cadence | gives |
|---|---|---|---|
| `gpu` | `nvidia-smi --query-gpu=… -lms N` | ~107 ms | used / reserved / total VRAM, temperature, GPU and memory utilisation, power, SM clock, throttle bitmask |
| `host` | `typeperf … -si S` | 1 s floor | available and committed system memory, the commit limit; with `--per-process`, per-pid GPU **Local** and **Non Local** usage and per-adapter dedicated/shared; with `--pid`, that process's working set and its exact peak |

**Why streaming children rather than a shell-out per sample.** One `nvidia-smi` invocation costs
**73–87 ms** here (measured, five runs). At a 100 ms cadence, per-sample spawning would burn most of
a core *and* put the spawn cost inside the interval being measured. `-lms` costs one process for the
whole run.

**Why no FFI.** The obvious way to read system memory on Windows is `GlobalMemoryStatusEx`, and this
crate deliberately does not: `typeperf` is a platform built-in that streams the same numbers in the
shape the GPU source already uses. The workspace has no `unsafe` anywhere and no dependency that is
not load-bearing; this crate keeps both properties and adds neither.

**Why `Reading` has three states.** `Measured` / `NotSupported` / `NotAvailable`, mirroring
`w8-run`'s `Metric` and for the SPEC §7 reason: a card that does not report power draw must not be
summarised as drawing **0 W**. `unwrap_or(0.0)` is how an instrument comes to state a limitation as
a measurement.

**Why a bitmask is OR-ed, never averaged.** `clocks_throttle_reasons.active` is flags. The mean of
`0x1, 0x20, 0x1` is 11.33 — a number that looks like a reading and is not one. OR-ing answers the
question that is actually being asked: *did this ever throttle, and why*, including when the card
had recovered by the final sample. Two W8 campaigns were killed for heat; `is_thermal()` is the
narrow question, and it deliberately ignores `GpuIdle`, which is set on essentially every sample of
an idle card.

---

## Findings

### 🚨 F60. `nvidia-smi` cannot attribute VRAM to a process on this box, and Windows can

`nvidia-smi --query-compute-apps=pid,process_name,used_memory` returns **`[N/A]` for every
process's memory** and `[Insufficient Permissions]` for most names — the consumer WDDM driver does
not expose it. So NVIDIA's own tool cannot answer "how much VRAM is LM Studio holding".

Windows' performance counters can, per pid, and they additionally split it in the way that matters:

- `\GPU Process Memory(pid_N_luid_…)\Local Usage` — dedicated VRAM;
- `\GPU Process Memory(pid_N_luid_…)\Non Local Usage` — **the shared system memory a WDDM driver
  spills into**.

That second counter is the direct measurement of the question W1 exists to answer. §11.0 reframed
W1 from "survive offload into 32 GB" to "stay resident in 16 GB", and *stay resident* has, until
now, been argued from `memory.used` not exceeding the card. **Non Local usage measures it
directly**: a config that spills is not resident, however good its `memory.used` looks.

Consequence for the runs already banked: none are invalidated, but none of them measured this
either. It is new information, available from the first W1/W2 run onward.

### 🚨 F61. A system-wide "spill" number is not a residency verdict, and this crate claimed it was

The first live baseline — 12 seconds, **nothing loaded**, an idle desktop — reported **15.9 MiB of
Non Local usage** and printed `🚨 NOT fully resident`. It was reading Explorer and a browser.
**Ordinary desktop processes hold shared GPU memory all the time**, so a system-wide maximum can
never distinguish that from a model spilling.

Residency is a claim about *one process*. The crate now refuses to make it without `--pid`, and
prints the system-wide figure marked `NOT a residency verdict` instead. Pinned by
`an_idle_desktops_shared_memory_is_not_a_residency_verdict`.

This is the flattering-silence shape again (F28, F49, F51): a plausible number, produced by working
code, that would have been quoted into a document. It survived a clean build, clean clippy and a
green test suite, and only the *live idle baseline* exposed it — **the negative control was the
thing that caught it.**

### 🚨 F62. A streaming child does not die when its pipe closes

`nvidia-smi --query-gpu=… -lms 200 | head -3` left `nvidia-smi` running after `head` exited; it had
to be killed by hand, and it survived long enough to be noticed only because the tool call timed
out. Windows has no SIGPIPE for a child to inherit.

A probe that merely drops its end of the pipe therefore **leaks one process per measurement**. Both
sources are killed as a **tree**, which is the same conclusion F57 reached from the other direction
and for the same reason: a leaked descendant both wastes a core and holds an inherited stdout
handle, which can hang the parent waiting to see the pipe close.

### 🚨 F63. `-lms100` is rejected, exits 0, and produced a measurement that silently did not happen

`-lms` and its value must be **separate arguments**. `-lms100` prints
`ERROR: Option -lms100 is not recognized` — **to stdout** — and then **exits 0**. The probe spawned
it successfully, read EOF, and reported `peak VRAM n/a` at the end of a 12-second run.

It survived a clean build, clean clippy and 37 passing tests. The fix is not the argument: it is
`GpuSource::warm_up`, which **blocks until the stream produces one real sample** and otherwise
fails loudly, quoting whatever the tool said. Fourth member of the family whose symptom is silence
(F49 writes refused, the session-12 shutdown, F57 the hang) — and the rule this project keeps
relearning holds again: **alarm on the absence of progress, never on the presence of a success
marker.**

### F64. The two instruments agree to ~2%, and are not interchangeable

At idle, `nvidia-smi memory.used` read **461 MiB** while Windows' `\GPU Adapter Memory(…)\Dedicated
Usage` read **470.5 MiB** for the same adapter over the same window — **9.5 MiB apart, 2%**. Close
enough to confirm both are measuring the quantity intended (a units error would show as a factor,
not 2%), far enough apart that the two must not be mixed inside one number. `--per-process` captures
both, so any run can be checked against itself.

### The idle baseline on this box, 2026-08-16

Held for reference, since every VRAM delta here is measured against it (F60):

```
VRAM         461–585 MiB of 16,311   (varies with what the desktop is drawing)
reserved     261 MiB                 (driver's own, part of the 16,311)
temperature  43–52 °C, no throttle bits beyond GpuIdle
commit       9.2–9.9 GiB of a 63.92 GiB limit
available    ~24.4 GiB
GPU shared   8.5–15.9 MiB across all desktop processes  ← the F61 floor
```

---

## Reading the output

`--out report.json` writes the summary, and `report.jsonl` beside it holds every sample. Both, not
either: **a peak with no trace cannot be checked, and a trace with no summary is not a result.**
Files are written LF, because everything tracked in this repo is LF in the index and a probe's
output is meant to be committable as evidence.

The trace is pruned to what was asked for. `\Process(*)` expands to **375 columns** on this box
(~187 processes × 2 counters + pids); with `--pid` it is resolved to that one process's three
columns via `ID Process` — **never by executable name**, because instances are keyed by name with
`#1`/`#2` suffixes whose assignment order is undocumented and can change between runs.

⚠ **Wildcards are resolved when `typeperf` starts.** A process that appears *later* gets no column
at all. For a model load that is fine — the pid holding the weights is LM Studio's server process,
which already exists before `lms load` runs — but the probe must be started **after** its target
exists, and a pid with no columns is reported as such rather than as zero.
