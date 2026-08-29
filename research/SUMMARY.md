# ABCC 2.0 — Phase 1 summary

**Phase 1 is complete: 13 workstream docs and 2 acceptance sweeps, 23,643 lines over 24 files,
findings F1–F488.** This file is the gate — *"Phase 2 starts only when SUMMARY.md exists and David
has signed off"* (`RESEARCH_BRIEF.md:1192`). The brief specifies it three ways (§1:46 *rejected
alternatives* · §16:1228 *three risks + what would falsify* · §12:1038 *decisions and open
questions*); this is the union. Every line is a ruling from a closed workstream, stated not
re-argued — **the evidence is in the named file, deliberately not repeated here.** ✅ **Approved by
David 2026-08-28**, which is the gate; his five decisions are recorded below. Next free at the time of writing: **F489**. ⚠ **The series continued into Phase 3 — F1–F509 are
now closed and the live pointer is `research/decisions/README.md`.** This paragraph is a Phase 1
record and is left as written.

## The recommendation

**One Rust binary that runs repository work as a fleet of two local slots, drives Claudette's turn
engine per attempt, records everything as one SQLite event log, and gates on a conjunction of
deterministic refusals in which a model verdict is a report and never a vote.** The console is a
Ratatui TUI with a sixel C&C battlefield. It inherits BCF's *vocabulary* and Claudette's *shape*,
~~copies the engine rather than sharing a crate (David, 2026-08-07)~~ — 🚨 **SUPERSEDED 2026-08-28:
David ruled REWRITE, do not port; the donors become a specification and a test corpus, never a
source tree. See `PLAN.md` §1** — and reimplements from scratch what outside contributors added to
v1, shipping MIT OR Apache-2.0 (W12).

## The architecture

**1 · Two levels, four phases each — W11.** *Mission:* **Plan** (model, read-only) → the task set
runs → **Integrate** (no model — build and test the assembled workspace) → **Accept** (human by
default, a W3 ladder rung when unattended). *Attempt:* **Localize → Change → Measure** (no model,
tri-state) **→ Judge** (one model call, no tools, **sees the measurements**), plus **Veto**
(deterministic, non-scoring). Router, Tester and CTO are deliberately *not* phases. BCF's nine
stages collapse to three; six of them existed only to compensate for having no repository.

**2 · The unit is a runtime slot, not a stage or a role — W11.** A slot holds a resident model and a
tool policy; the count is set by VRAM (**N=2**), never by the length of the phase list.
Co-residency is impossible, so a tier change costs a **23.77 s swap plus a cold prefill**, which is
why the architecture buys attempts rather than tiers.

**3 · State, store and runtime — W3.** **Seven** Task states, one vocabulary per entity, with
data-carrying variants so v1's NULL-clock bugs are unrepresentable. **One write path:** a single
transition writer appends the event and updates status in one transaction — no generic set-status.
**Attempts are immutable**; retry, edit, re-route and replay are all fork-from-checkpoint with a
`cause`, so lineage exists by construction. **Status is a projection and boot is the same code as
replay** — measured free, with no snapshot mechanism needed until ~1M events. The store is a
**SQLite event log, `journal_mode=WAL` + `synchronous=FULL`**, FULL because it was measured
affordable against an action-granularity log. **Threads own the work, one tokio runtime owns the
console edge, and the event log is the only thing that crosses**: tokio's one honest argument was
cancellation, and it is discharged on the blocking stack. Timeouts are per-rung and are a *per-read
gap*, not a total — pin that semantic with a test before someone "fixes" it.

**4 · Isolation and the gate — W6.** Per-task **git worktree at a temp-index snapshot sha** — the
whole cycle costs well under a second, and **the sha must be written to a ref** or `git gc` collects
it. **Isolate the workspaces, serialize the gate.** The gate is a **conjunction of refusals, never a
weighted average**: a free structural rung ∧ an acceptance test ∧ a Judge for the residue. Outcomes
are a compiled type — `Measured | Unmeasured(Why)`, a `Green` that requires every declared rung to
have been measured, and a `Claim` that **no function converts into an Outcome**. **A model verdict
is a report and never a gate**: it does not measure a property of the tree, since changing only the
output schema catches a different three. **Show a judge the other artifact, not a threshold**, and
**a review finding must carry something runnable** — executing the reviewer's own named case is the
only instrument measured to beat the model's own verdict.

**5 · Routing — W4, where every item inverted its brief.** Ship **no pre-dispatch estimate**
(`complexity` is an `Option`; 2.0 emits `None`). **One tier; the only purchase is another attempt;
retry budget 2.** The breaker fires on the first failure and **reports, never gates**. Do not route
on context length. `NextAction { Attempt | Stop | HandToOperator }`, one counter, `HandToOperator` a
durable state. **2.0 reads no logprobs and fine-tunes nothing.**

**6 · Serving and models — W1/W2, settled by measurement, not by prior art.** One shared LM Studio
server; three champions by axis — **speed** `qwen3.6-35b-a3b-mtp@iq3_s`, **quality**
`unsloth/Qwen3.8-27B-UD-Q3_K_XL` at **4.9×**, **context** the byteshape 3.67 bpw build. **Enumerate
a finite tool-head set and freeze it per attempt**: prefix caching saves **79.7%** of TTFT and one
token changed at the *front* costs a full cold prompt. Constrain decoding with `json_schema`, budget
**8192**, and treat an empty payload at `finish_reason == length` as `Uncertain`, never a score.
Short structured calls go **direct to the bare server** — the proxy silently drops fields at 200.

**7 · Console — W5.** **Ratatui TUI primary; the web console is dropped for now** (David,
2026-08-19), with the C&C-1995 isometric **sixel** battlefield as the flagship, its spike passed on
all five criteria. **SSE + SQLite**, one `seq` serving as event id, `Last-Event-ID`, paged-read
cursor and scrub position. Eight operator verbs reduce to three mechanisms, **the agency is in the
terminal rather than the console**, and fun is **six queries over the event log**.

**8 · Modes and posture — W10/W7.** **Two runtime modes, not three** — `SinglePlayer` and `CoOp`
differ only in whether a `Cloud` provider is admitted, and a remote rig is a **device on the local
provider**, never a peer. Mode is a **one-way sticky ratchet** whose downgrade is an event on the
log, adding no Task state. `Provider` takes `&self` and returns a stream — two cases, not three.
Security is **denying the class**, i.e. `max_tier` per role. Copy the dependency gate verbatim, and
**add the digest pin on model weights that no donor in the family has**.

## Rejected alternatives

**tokio owning the work** — its one honest argument was discharged by measurement. · **Postgres or a
durable-execution product** (Restate, Temporal, DBOS) — every one needs a server. · **Adopting
Langfuse** — six services, ~21.5 GiB on a 32 GB box; take the vocabulary, own the store. · **A web
console or Tauri as primary** — reversed 2026-08-19. · **BCF's nine-stage pipeline** — 7 → 3. · **A
complexity router, a tier ladder, an escalation estimator, logprobs, a fine-tune** — all of W4. ·
**Generated tests as a gate** — they ratify a wrong change 6 times in 9. · **Type and syntax checking
as the verification workhorse** — 1 of 160 across 728 real attempts. · **A pointwise judge score
against a threshold** — 0 of 8. · **Switchyard the crate** — self-declared pre-alpha; take its judge
prompt instead. · **Per-argument permission checks as the security control** — the shipped
untrusted-content wrapper was *measured* not to work, 39 of 50. · **Sharing a crate with Claudette**
— both stay live (David, 2026-08-07) · **and porting the donor code at all** — David 2026-08-28:
rewrite, because a port inherits the donors' *design* defects as shape (`PLAN.md` §1).

## The three highest risks

**1 · Containment does not exist on this platform, so the unattended story is a policy, not a
control.** Measured: a `runas /trustlevel:0x20000` child stays at Medium integrity, writes `$HOME`
and opens TCP; WSL2's `binfmt_misc` hands any PE file back to the host; `write_file` on a new path
plus `run_tests` is arbitrary code execution at the tier that never prompts. **On Windows there is
no containment without Win32 token code**, and a prompt binds only as far as the model complies — a
~7% residual at best against 78% as shipped. Every mode above `SinglePlayer` inherits this, and the
stated posture must be blast radius, not a sandbox. — W7

**2 · The architecture may not fit the machine it is designed for.** Peak system RAM already runs
8.99 → **28.03 GiB**, and 28.03 is **87.8% of 31.92 GiB physical** though only 43.9% of the commit
limit — the reassuring number is the wrong one. On top of that the design wants two slots, a
worktree per task and real builds, and **two cold builds alone leave 2.3 GB free**. The quality
champion costs **4.9×** on the same box. — sweep B, W6, W1

**3 · The gate is the product, and its best instrument catches under half.** Six deterministic rungs
over 63 trees give a *constant*; across the 280 cells where the agent was left alone nothing fired
on any of the 29 real failures; and the strongest instrument found catches **10 of 23** wrong trees.
The 40-task floor check says it from the other side: the artifact reaches the graded directory in
**half** the attempts, and where it does, 38 of 40 pass. If the gate cannot separate right from
wrong, the self-hosting milestone is unreachable however well everything else works. — W6, W3, W8

*Demoted:* the provider trait's blocking `&mut self` (W10) is a known engineering cost with a
written fix, not an open risk; and the game framing being the only differentiator (W9 — zero
game/RTS/sprite vocabulary across 340 projects) argues *for* the plan, not against it.

## What would falsify the recommendation

- **Two slots plus a worktree plus a real build cannot hold inside 31.92 GiB on the target
  workload** → the N=2 fleet is wrong; the unit count drops to one, or the box changes.
- ~~**The conjunction gate false-fails more than a few percent of correct trees over a real week**~~
  → 🚨 **REPLACED 2026-08-28: David ruled only deterministic rungs may refuse, so false-fails are
  ~0 by construction and a false fail is a rung bug, not a rate. The exposure moved — *the wrong
  trees reaching David as reports are frequent enough that unattended `Accept` is not worth
  having.* `PLAN.md` § Gate.**
- **Review minutes per merged change rise from M0 to M1** → the co-dev thesis is wrong regardless of
  how many agent-authored commits land. W13: **M0 is already taken by v1**, 15 of 471 commits.
- ~~**`Provider` cannot be made `&self` + stream without forking the engine past a maintainable
  delta**~~ → 🚨 **RETIRED 2026-08-28 by the rewrite ruling — there is no fork, so it cannot fire.
  REPLACED by a schedule falsifier: *the rewrite does not re-earn the engine's working behaviour
  inside the Skeleton and Gate milestones*, in which case the turn loop goes back on the table as a
  port. `PLAN.md` §1.**
- **The sixel battlefield does not survive a real workday** — tmux, SSH, or the operator turning it
  off → the only measured differentiator is gone and TUI-primary reopens.

## Decisions — David, 2026-08-28, on reading this document

All five open questions this file was written to raise are now answered. **Phase 2 inherits them
as settled.**

1. ✅ **§16 item 3 is CLOSED in both clauses.** `.gitignore` now tracks `runs/hw-probe/` (32 files)
   **and** `runs/**/runmeta.json` (62 files) — 94 files, ~2.0 MB, **0.05% of the 3.8 GB tree** — so
   the peak-RAM answer *and* the join that produced it are both reproducible from the repo. (F480)
2. ✅ **§12's layout stands; the ADRs get written in Phase 2**, one per architectural decision, as
   the build plan consumes each ruling — genuine decision records rather than backfill dated after
   the fact. `research/decisions/` is Phase 2's to create.
3. ✅ **The lifecycle names are RATIFIED as sketched (OQ-W3-6 closed):** `Queued, Deployed, Engaged,
   AwaitingOrders, Holding, Commandeered, Accomplished, Failed, Aborted`, nine data-carrying
   variants over `since: Seq`. The RTS vocabulary is now load-bearing, which is the one
   differentiator W9 found evidence for.
4. ✅ **The byteshape 27B is measured — the RAM clause closes at 6 of 6** (F488). ⚠ Its raw
   **26.71 GiB** would invert the finding: today's baseline is 1.37 GiB busier, and corrected it is
   *lighter* than unsloth, as its VRAM and file size independently confirm. **28.03 GiB remains the
   ceiling of record**, so risk 2 above is unchanged.
5. ✅ **The three risks are ratified** by approval of this document.

## §16 scorecard — verified on disk 2026-08-28

| # | Criterion | Status |
|---|---|---|
| 1 | Workstream files exist and follow the required structure | ✅ 13 of 13 |
| 2 | Every model/crate/tool/price/benchmark claim carries a URL + date | ✅ sweep A, F475–F479 |
| 3 | Desktop benchmarks, **raw results committed**, peak RAM per config | ✅ — RAM 6 of 6 (8.99 → 28.03 GiB, byteshape closed by F488); committed via 94 tracked files, ~2.0 MB |
| 4 | SUMMARY.md — architecture, three risks, what would falsify | ✅ this file |
| 5 | Harness end to end + baseline, incl. the V1 40-task re-run | ✅ — a **floor check, never a comparison**: v1's 39/40 is after-retry, 36/40 single |
| 6 | Mode matrix and stage schemas exist **and agree with W3** | ✅ `W10-mode-matrix.md` §3 is a row-by-row check, not an assertion |
| 7 | W5 holds a defensible written position on what makes this fun | ✅ six queries over the event log |
| 8 | W12 states what happens to V1 and its users | ✅ clean break; the users are three Docker `:latest` tags, not npm |

✅ **All eight criteria are met. Phase 1 is CLOSED — David signed off 2026-08-28.** Phase 2 is the
sequenced build plan, and its own gate is his sign-off on that plan (§1). **Next free finding: F489.**
