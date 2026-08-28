# Acceptance sweep B — peak system RAM per configuration

**Status: COMPLETE — 2026-08-28**, session 12 of the 14-session landing budget. Closes §16's
third and last Phase 1 criterion. **Findings F480–F487**; next free number is **F488**. No probe
was built and nothing was re-run — the standing rule held. This file is the record, not a
workstream doc.

## What §16 asks — two clauses, and only one of them was ever in doubt

§16: *"Benchmarks were run on the desktop with **raw results committed**, and **peak system RAM is
reported for every configuration**. Laptop benchmarks are required only for the multiplayer
protocol work."*

The laptop clause is already closed by W10: **F465** (the multiplayer test target has been offline
one day and the protocol must be provable on loopback) and **F464** (the RPC backend is not
installed at all). So sweep B is the desktop half — and the desktop half is **two** claims, not
one. The pre-scout only ever looked at the RAM clause. The committed clause is where the sweep
found its worst result.

## 🚨 The first clause is false, and it is false for every benchmark in the repo

`.gitignore:6` is a bare `runs/`. **Zero of the 55,577 files under `runs/` are tracked by git** —
`git ls-files runs` returns nothing, and `git check-ignore -v` names line 6 for both a hw-probe
headline and a `q56` cell stream. Every raw benchmark result in this project lives on one disk,
in one working tree, with no history and no second copy.

The reason is defensible: **`runs/` is 3.8 GB.** Committing it is not on the table, and no one
should propose it.

▶ **But the sweep-B evidence is not 3.8 GB. `runs/hw-probe/` is 1,923,675 bytes across 32 files
— 1.9 MB, 0.05% of the tree.** The entire measured answer to §16's RAM clause is small enough to
commit today, and there is precedent for exactly that: `research/spikes/` is also mostly
untracked (384 of 9,146 files) yet its curated artifacts — `w11-artifacts/*.json` and the schema
payloads — are in git. The pattern already exists; hw-probe was simply never given it.

## Half (a) — the measurement, re-derived from disk

`runs/hw-probe/` holds **16** `*.json` headline files (plus a `.jsonl` sample stream each),
measured **2026-08-16 10:52 → 2026-08-17 08:26**. Every one carries `peak_committed_b`. The
handoff's table reproduces digit for digit; the pre-scout in [[abcc-2-w10-state]] that said *12*
was a sample, not a count — [[verify-claims-against-code-not-docs]] item 41 again.

| label | file | peak committed | min avail MiB | peak VRAM MiB | focus resident | wall s |
|---|---|---|---|---|---|---|
| `idle-session19` | `s19-idle` | **8.99 GiB** ← floor | 24,445 | 467 | — | 30.1 |
| `baseline` | `baseline-idle` | 9.17 GiB | 24,418 | 461 | — | 15.0 |
| `pid-smoke` | `pid-smoke` | 9.22 GiB | 24,394 | 461 | 0.03 GiB | 8.0 |
| `control-e2b-32k` | `s19-control-e2b` | 15.15 GiB | 21,640 | 3,419 | 2.89 GiB | 15.0 |
| `resident-4k-idle` | `s19-resident4k-idle` | 24.04 GiB | 23,433 | 13,785 | 13.01 GiB | 15.0 |
| `resident-32k-idle` | `s19-resident32k-idle` | 24.44 GiB | 23,463 | 14,221 | 13.43 GiB | 15.0 |
| `load-32k` | `s19-load32k` | 24.56 GiB | 23,434 | 14,217 | — | 7.2 |
| `champ-40k-idle` | `s19-champ-40k-idle` | 24.63 GiB | 23,430 | 14,318 | on-card 13.56 | 12.0 |
| `resident-65k-idle` | `s19-resident65k-idle` | **25.00 GiB** | 23,420 | 14,750 | 13.95 GiB | 20.1 |
| `resident-65k-idle-rep2` | `…-rep2` | **25.03 GiB** ← reproduces | 23,392 | 14,750 | 13.95 GiB | 20.0 |
| `load-65k-ident` | `s19-load65k-ident` | 25.27 GiB | 23,215 | 14,745 | — | 12.8 |
| `prefill-60k` | `s19-prefill60k` | 25.71 GiB | 22,769 | 14,773 | 13.97 GiB | 2.6 |
| `27b-40k-idle` | `s19-27b-40k-idle` | 25.98 GiB | 23,199 | 15,269 | on-card 14.48 | 12.0 |
| `prefill-58k` | `s19-prefill58k` | 26.12 GiB | 22,323 | 14,773 | 13.97 GiB | 37.9 |
| `load-27b-65k` | `s19-load27b-65k` | 27.48 GiB | 22,310 | 15,847 | — | 13.4 |
| `concurrency-sweep` | `s19-concurrency` | **28.03 GiB** ← ceiling | 20,986 | 15,339 | 14.56 GiB | 50.2 |

**Range 8.99 → 28.03 GiB.** The floor is `idle-session19`, not `baseline` at 9.17; both are idle
rows and the gap is noise, but quote the measured one.

### The denominator decides what this number means

The host is **31.92 GiB physical** (34,271,211,520 B) with a **63.92 GiB commit limit** — roughly
32 GiB of pagefile behind it. `peak_committed_b` is *commit charge*, not resident physical, so the
same ceiling reads two ways:

| row | peak committed | % of 31.92 GiB physical | % of 63.92 GiB commit limit |
|---|---|---|---|
| `idle-session19` | 8.99 GiB | 28.2% | 14.1% |
| `champ-40k-idle` | 24.63 GiB | 77.2% | 38.5% |
| `resident-65k-idle` | 25.00 GiB | 78.3% | 39.1% |
| `27b-40k-idle` | 25.98 GiB | 81.4% | 40.6% |
| `concurrency-sweep` | **28.03 GiB** | **87.8%** | 43.9% |

▶ **Report both or the headline misleads in whichever direction the reader guesses.** "44% of
commit" sounds like headroom; "88% of physical" sounds like a wall. `min_avail_mib` is the
tiebreaker and it sides with the second reading: the ceiling row left **20,986 MiB available**,
3.4 GiB below the idle rows' 24.4 GiB.

## The join — 62 run manifests collapse to FIVE serving configurations

This is what made sweep B finite. Every run writes a `runmeta.json` carrying `server.id`,
`server.quantization` and `server.loaded_context_length`. Across **62 manifests** those fields
take only **five** distinct values, plus seven early runs that captured no server at all:

| serving configuration | runs | cells | families | hw-probe row | peak system RAM |
|---|---|---|---|---|---|
| `qwen3.6-35b-a3b-mtp@iq3_s` IQ3_S @ 65,536 | 37 | 1,511 | 27 | `resident-65k-idle` (+rep2) | **25.00 / 25.03 GiB** idle |
| ” — the same server under prefill | | | | `prefill-60k` / `prefill-58k` | 25.71 / **26.12 GiB** |
| ” — the same server under concurrency | | | | `concurrency-sweep` | **28.03 GiB** |
| `qwen3.6-35b-a3b-mtp@iq3_s` IQ3_S @ 40,960 | 6 | 18 | 6 | `champ-40k-idle` | **24.63 GiB** |
| `qwen3.8-27b` Q3_K_XL @ 40,960 | 6 | 18 | 6 | `27b-40k-idle` | **25.98 GiB** |
| `unsloth/qwen3.8-27b` Q3_K_XL @ 40,960 | 3 | 9 | 3 | `27b-40k-idle` (same file) | **25.98 GiB** |
| `byteshape/qwen3.8-27b` IQ4_XS @ 40,960 | 3 | 9 | 3 | **none** | ⚠ **no row** |
| *(server uncaptured)* | 7 | 95 | 2 | n/a | n/a |

▶ **So §16's "every configuration" is a five-row table, not a fifty-six-row one** — and five of
six configurations have a measured peak, by reference to the probe of the identical serving state.

### 🚨 The join key is `loaded_context_length`, and the obvious key is wrong

`runmeta.json` carries two window numbers and they disagree. **W11's nine budget-sweep runs pin
`held.num_ctx` to 40,000 against a server whose `loaded_context_length` is 65,536.** KV is
allocated in full at load ([[abcc-2-w1-w2-state]]), so the client-side pin costs nothing and
changes no RAM: those nine runs belong on the 65k row, not the 40k one. Keying on `held.num_ctx`
would move 9 of 37 runs onto a configuration **0.37 GiB cheaper than the one they actually ran
on**, and would misdescribe what was loaded.

### The 27B identity, settled by file size rather than by name

The probes' `load-27b-65k` note reads `lms load qwen3.8-27b -c 65536 --gpu max --parallel 1 -y` —
a bare id with no publisher, from a time before the batch-2 arms were disambiguated. `lms-ps.txt`
settles it: bare `qwen3.8-27b` is **13.44 GB** and `unsloth/qwen3.8-27b` is **13.44 GB**, while
`byteshape/qwen3.8-27b` is **12.56 GB**. Same size, same `Q3_K_XL` quantization, same 40,960
window — **the probed 27B is the unsloth build**, which is [[abcc-2-model-roster]]'s QUALITY
champion. That is evidence, not an inference from naming.

And it explains the one gap: **byteshape has no RAM row because it did not exist when the probes
ran.** The probes are 2026-08-16/17; `k-27bBS-b2-r1` started **2026-08-28 00:17**, eleven days
later. The batch-1 K arms, by contrast, started 2026-08-17 20:16 — the same day as the
`champ-40k-idle` and `27b-40k-idle` probes taken that morning at 08:26 and 08:25.

### Two caveats that belong on the join, not hidden under it

- **`kv_cache_type` is listed in `server_uncaptured` in all 55 runs that captured a server at
  all** (the other 7 captured none). It is the one server-side field that scales KV bytes, so the
  join matches on model, quantization and window while the cache dtype is assumed constant, never
  shown.
- **10 of 16 probe rows carry an empty `notes[]`.** Only the six that spawned a child command
  name their model in the artifact; for the other ten — including `champ-40k-idle`,
  `27b-40k-idle` and every `resident-*` row — **model identity lives in the label alone.**

## Half (b) — the per-cell metric is uniformly empty, and now exactly counted

- **1,619 of 1,660 cells across 56 `cells.jsonl` files carry `peak_rss_mb`, and `sort -u` over all
  of them returns exactly ONE distinct value:** `{"not_applicable":"no probe exists yet; W1/W2
  owns building it"}`. The remaining **41 cells do not carry the key at all** — 29 in
  `q56-degraded`, 12 in `prefix-invalid`.
- The name is reserved at `corpus/SPEC.md:488` (*"no probe exists yet (W1/W2 owns building it);
  the name is reserved"*) and emitted as `Metric::NotApplicable` at
  `harness/crates/w8-run/src/main.rs:1000-1001`.
- **No benchmark run directory contains a hw-probe artifact.** `grep -rl peak_committed_b runs
  --include=*.json` matches 16 files, all of them inside `runs/hw-probe/` itself.

▶ **The honest framing, and it is stronger than the pre-scout expected.** The hw-probe rows
characterise the **serving configuration** — which model, which window, resident versus spilling,
idle versus prefill versus concurrent — and on this box *that is* what determines peak system RAM,
because the model is the allocation. The join above therefore answers §16's RAM clause for five of
six configurations from measurement already on disk. What remains genuinely unmeasured is
**per-cell process RSS**, a different question nobody has yet asked, plus the one serving
configuration that post-dates the probes.

## Findings

### F480 — 🚨 §16's "raw results committed" clause is false for every benchmark in the repo
`.gitignore:6` is `runs/`. **0 of 55,577 files tracked**; the tree is 3.8 GB, which is why. But
`runs/hw-probe/` is **1.9 MB across 32 files** — the whole of sweep B's evidence — and
`research/spikes/` already demonstrates the selective-commit pattern (384 of 9,146 files tracked).
The criterion is unmet by a wide margin and reachable at 0.05% of the cost.

### F481 — 62 run manifests are only five serving configurations
62 `runmeta.json` manifests take five distinct `(server.id, quantization, loaded_context_length)`
values, plus 7 that captured no server. "Peak RAM for every configuration" is a five-row
obligation, and it was never the fifty-six-row job it looked like.

### F482 — 🚨 the intuitive join key is wrong and moves nine runs to the wrong configuration
`held.num_ctx` is a client pin; `server.loaded_context_length` is the allocation. W11's nine runs
pin 40,000 against a server loaded at 65,536. KV is allocated in full at load, so keying on the
pin would credit those runs with `champ-40k-idle`'s 24.63 GiB instead of the 25.00 GiB actually
committed, and would name the wrong window in the record.

### F483 — the probed 27B is the unsloth build, proved by size, and byteshape has no row
Bare `qwen3.8-27b` and `unsloth/qwen3.8-27b` are both **13.44 GB** at Q3_K_XL/40,960;
`byteshape/qwen3.8-27b` is **12.56 GB** at IQ4_XS. The probes therefore measured the QUALITY
champion. Byteshape is the single configuration with no RAM measurement, because its arms ran
**2026-08-28**, eleven days after the last probe.

### F484 — 10 of 16 probe rows do not name the model they measured
Only the six rows that spawned a child command carry it in `notes[]`. The other ten have
`notes: []`, and their model identity is carried by the filename label alone — including all four
`resident-*` rows and both 40k comparison rows. The labels are right; they are just not evidence.

### F485 — the same ceiling reads as 88% or 44% depending on the denominator
28.03 GiB is **87.8% of 31.92 GiB physical** but **43.9% of the 63.92 GiB commit limit**, because
`peak_committed_b` is commit charge over physical-plus-pagefile. `min_avail_mib` breaks the tie
toward the alarming reading: 20,986 MiB at the ceiling versus 24,445 at idle.

### F486 — the one server field that scales KV bytes is the one never captured
`kv_cache_type` appears in `server_uncaptured` in all 55 runs that recorded a server. The join
holds model, quantization and window constant and *assumes* the cache dtype was constant too.

### F487 — the cell-level metric is exactly, uniformly empty
1,619 cells carry `peak_rss_mb` with one distinct value across all 56 files; 41 more do not carry
the key at all (`q56-degraded` 29, `prefix-invalid` 12). Nothing was ever measured here, and the
placeholder says so honestly in every one.

## What this sweep did not do

- **It built no probe and re-ran nothing.** The standing rule from session 10 held. Every number
  above was already on disk before the session opened.
- **It did not measure the byteshape 27B.** That would be a re-run, and the model is not the one
  [[abcc-2-model-roster]] recommends. It is one `hwprobe` invocation whenever David wants it —
  the gap is stated, not closed by construction.
- **It did not commit `runs/hw-probe/`.** F480 names a 1.9 MB fix and a precedent for it, but
  changing `.gitignore` is David's call, not a sweep's.
- **It did not touch the harness.** `peak_rss_mb` stays `NotApplicable`; W1/W2 still owns it.

## Effect on the line budgets

**No line budget was ever assigned to either sweep.** David's ruling of 2026-08-28 stands and is
general: *exceeding a budget by up to 10% is a non-issue*, and no document is to be split or
stripped to protect a count — see [[abcc-2-phase-1-landing-plan]].

**Remaining for Phase 1: `SUMMARY.md` alone** — under two pages, the three highest risks, and what
would falsify them. All thirteen workstream docs and both acceptance sweeps are now closed. Sweep
A's record is `research/ACCEPTANCE-A-citations.md` (F475–F479).
