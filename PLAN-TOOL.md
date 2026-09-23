# ABCC — the plan to make it a good coding tool

**Written 2026-09-23**, after reading the research record (SUMMARY, PLAN, the 25 ADRs, every Phase 3
P-doc's verdict, the memory work order), the `abcc` tree at `486d095` and the `claudette` tree at
`a450e00`. Every number below was either re-read from the four abcc logs today or is quoted from a
named finding. `PLAN.md` governs how abcc was *built*; this document governs how it becomes *good*.

---

## 0. The verdict, in one screen

**The architecture is right and the agent loop is wrong.** The event log, worktrees, deterministic
gate, report-only judge, `board`/`diff`/`land` and the lifecycle are sound and worth keeping. What
decides whether a coding tool works is the loop: the turn engine, the tools, and how context is
managed. ADR-0001 rewrote that loop from scratch, and **it has never been run against the donor on
the same tasks.**

**Same model, same window, very different results.** Claudette drives `qwen3.6-35b-a3b-mtp@iq3_s` at
`-c 40960`. On the K-series (multi-file work under context pressure) it passed 8/9, 6/9 and 8/8 over
three batches, and it scores 50/56 on Q56. abcc on the same model and window has landed **0 of 6
multi-part attempts**. It went **0 for 4 on `SEC-06`**, a one-line deletion, **without ever calling an
editor**. Across all four logs, **20 of 169 attempts succeeded (11.8%) and 7 changes landed.**
⚠ The tasks differ (fixtures vs a 1,164-test real repo), so this is a strong signal, not a controlled
result. §3 Phase A turns it into a controlled one.

**Six weeks studied the model *inside* abcc's loop and never varied the loop.** Every Phase 3
finding — the re-read spiral (F800, F819, F827), reasoning runaways (F829, F831), cut tool calls
(F798, F515), the size-gates-shape interaction — is about the model's behaviour in one fixed
environment. `PLAN.md` §1 wrote the falsifier for exactly this:

> *"the rewrite does not re-earn the engine's working behaviour inside the Skeleton and Gate
> milestones, [then] the engine's turn loop goes back on the table as a port."*

**That falsifier has fired.** Gate closed 2026-08-29. The loop still lacks claudette's editor, its
windowed read, its compaction and its fix-loop, and it re-derived claudette's read-loop breaker
(`b28159a`, three months after claudette shipped one).

**The plan, in five moves:**

1. **Build the bench first** — abcc and claudette on identical, hidden-graded tasks (Q56, K, and a
   new suite of real claudette cards). This replaces the hand-picked ladder as evidence.
2. **Close the engine gap** — give abcc claudette's loop behaviours, `edit_file` first, and measure
   each bundle on the bench.
3. **Build the co-dev mode** — an interactive conversation in the operator's repo. That is how
   claudette is actually used day to day; the batch queue is not a daily driver.
4. **Drive 100 real tasks** (David's ruling of 2026-09-20), with claudette as the control arm on a
   slice.
5. **Stop the research tax** — the bench decides; a findings doc is written only when a bench number
   moves or David has a decision to make.

---

## 1. Where it stands — re-read from the logs today

| log | attempts | success | landed | biggest ending |
|---|---:|---:|---:|---|
| `abcc-1ae35b…` (self-host) | 125 | 10 | 5 | `budget_exhausted` 39, `truncated_at_cap` 26, `refused` 22, `said_nothing` 17 |
| `claudette-92490a…` (pilot) | 26 | 9 | 2 | `truncated_at_cap` 7, `budget_exhausted` 4 |
| `arm-redact-7fe980f` | 18 | 1 | 0 | `budget_exhausted` 8 |
| **all** | **169** | **20** | **7** | **uncertain: the model never produced a gradeable tree** |

What those numbers mean, from the record:

* **70.4% of self-host attempts end `uncertain`.** The gate is not what kills attempts; the
  loop is. The review-ladder roast found the same thing on 2026-09-20.
* **The five self-host landings are accessors with zero production callers** — tasks chosen to
  fit the tool (the review-ladder roast).
* **Pilot successes are almost all one card.** `RUNTIME-11` succeeded 7 of 8 times on a
  112-line file. `SHELL-10` succeeded once, but its test passes on the unfixed tree. `RUNTIME-10b`
  went green on a test that also passes unfixed (F832). Real, distinct, proven fixes landed: **one**
  (`RUNTIME-11`).
* **The quality tier does not rescue it.** 27B at 4.9× cost reached Change, made 13 tool calls
  and **zero edits** (F833).
* **The review-minutes ladder is not usable.** Every recorded row claims more seconds than elapsed
  (the review-ladder roast). The metric is typed, not observed.

What works and is worth keeping — not up for redesign:

* **The gate.** It grades trees, not claims. It put 0 of 59 correct corpus trees at `Red`
  (ACCEPTANCE-C), and three manufactured-red bugs in it were found and fixed (F803, F804, the
  `ENV_ALLOWLIST` pair).
* **The report-only Judge.** It produced the first finding the rungs could not (F832).
* **The event log, worktree isolation, lifecycle, `board`, `diff`, `land`, `CHEATSHEET.md`, and the
  posture work.**
* **The two stops shipped this week** — the re-read guard and the reasoning ceiling. The falsifier
  passed (`prompt_cut` 8 → 0, bytes −78%). Keep both.

---

## 2. Diagnosis — the engine differences, ranked

Claudette is the reference implementation. It is David's code, it works on this model at this
window, and `harness/` already drives it (`corpus/subjects/claudette-af3f804.toml`). These are the
places the two loops differ, verified in both trees today:

| # | | claudette | abcc | evidence it matters |
|---|---|---|---|---|
| **D1** | **editor** | `edit_file` (old→new text, must be unique, `replace_all`, near-miss hint on 0 matches) **and** `apply_diff` (fuzzy before/after); `write_file` is for new files | `write_file` (whole file) and strict unified-diff `apply_patch` only | `apply_patch` applies ~36% (F771); 23 of 300 cut at 0 chars (P14); *"a card costs its file size twice"*; `api.rs`/`conversation.rs` cards ruled unqueueable; `SEC-06`: 0 editing calls in 4 attempts |
| **D2** | **read window** | `read_file` returns 400 lines by default, with `offset`/`limit`/`tail` and *"do not re-read the same range"* | whole file by default up to 64 KiB (`workspace.rs:74`) | whole-file reads are **54% of calls and 92.5% of bytes** (F826) |
| **D3** | **context** | compaction at `num_ctx/2` (`compaction_policy.rs`); stale tool-result eviction (`context_evict.rs`) | append-only `Body`; overflow is left to LM Studio's `truncateMiddle`, which cuts in the *middle* | a cut middle orphans tool results and **multiplies the reasoning trace ~8×** (lmstudio memory); 9 of 36 round-exhausted attempts were cut (F775) |
| **D4** | **conversation shape** | one conversation per task (forge: a tool-less plan prefix, then one Coder conversation) | Localize and Change are **two fresh bodies**; Change gets Recon's prose and is told to re-check it (`brief.rs::change`) | **47% of Change reads are files Recon already read** (F774) |
| **D5** | **fix loop** | forge feeds build/test failures back to the Coder, up to 3 rounds; opt-in post-edit check | the gate runs **after** the attempt; a refusal goes to INTERVENTION REQUIRED and waits for a human | **all 10 one-rung-from-landing refusals were at `standard`; 4 were pure `cargo fmt`** (the self-host memory) |
| **D6** | **sampling** | `temperature: 0.0` | no `temperature` sent, so the server's unrecorded default applies, plus a seed | claudette's Q56/K numbers were all greedy (F728); no abcc attempt has ever been flown at T=0 on purpose |
| **D7** | **budgets** | 40 iterations, a budget warning near the cap, and a *graceful landing* (one text-only turn summarising the work) | 24 rounds, then a hard stop | `budget_exhausted` is the #1 ending (39/125) |
| **D8** | **window** | documented daily-driver load is `-c 65536` (README) | `-c 40960` everywhere; inherited from the K-series need to match the 27B | the champion fits at 65,536 (14,745 MiB, K README), with a spill risk that has a known witness |

### The hypothesis worth testing first — H1: the editor causes the spiral

The biggest open behavioural question in the work order (Action ③) is *why does the model never reach
an editor on `SEC-06`?* It re-read the same 427-line file six to thirteen times and never edited. The
context-exhaustion explanation died when the guard cut the pressure by 78% and nothing changed.

**H1:** with only a whole-file rewrite or an exact unified diff on offer, the model cannot act until it
holds verbatim bytes and exact line numbers. So it keeps fetching the file to get them. A
search/replace editor needs only a unique snippet. For `SEC-06` that snippet is three lines, and the
deletion is `new_text: ""`.

H1 would also explain four other records at once:

* **Size gates shape** (180 vs 427 lines): whole-file cost grows with the file, a snippet's does not.
* The **"unqueueable" 3,500-line files.**
* The **36% `apply_patch` rate.**
* The **cut-at-zero diff calls.**

⚠ **It is a hypothesis, not a finding.** The test is cheap: `SEC-06`, v1 prompt unchanged, with
`edit_file` on the menu, n = 3. Outside this repo, the dominant editing interface in current agent
scaffolds is exactly this shape: Claude Code's Edit, SWE-agent/OpenHands `str_replace_editor`, Aider's
search/replace blocks. **abcc is the outlier.**

---

## 3. The phases

Work rules for every phase:

* **The bench decides.** A change ships if it moves the bench or fixes a defect. The bench replaces
  n = 2 GPU anecdotes.
* **Bundle for the product, ablate only when needed.** Attribution is not the goal; landing is. Ship
  the parity bundle and measure it once. Ablate only if the bundle fails to move the number, or if a
  change is a candidate for revert.
* **One commit per change, and one bench row per commit that touches the loop.**
* **Heavy GPU runs are asked for** (PLAN.md ground rule 6). A single card or a probe is not.

### ▶ Phase A — the bench (instrument first)

**Why first:** without it, every Phase B change is another n = 2 story, and F7xx findings are
already retracted at 29.6% (the review-ladder roast).

* **A1 — abcc as a harness subject.** Add an `abcc` subject to `w8-run` (or an `abcc bench <suite>`
  verb that reads `corpus/suites/*`). Each task becomes `abcc task` + `abcc run` in the fixture
  repo, and the result is graded by the suite's own hidden `verify.sh`, **not by the abcc gate**.
  The harness is the instrument and does not change (PLAN.md §9.4).
* **A2 — the R suite: real cards from a real repo.** Package the claudette cards that already have
  a reference patch and a verified-red test: `RUNTIME-11`, `SHELL-10`, `SEC-06`, `RUNTIME-10`,
  `SHELL-04`, `SHELL-06`. Add ~10 more from `FINDINGS.md`, each grep-verified still open, across a
  spread of file sizes (180 → 900 lines).
  * **Grading injects the card author's red test at grade time**, the Q56 hidden-test method. That
    also closes F832 for the bench: a model's sham test cannot pass it.
  * ⚠ `FINDINGS.md` must never be copied into this repo (exploit strings). The suite stores card
    ids, base shas, prompts and reference tests only. Keep `SEC-*` cards local, as today.
* **A3 — the baseline.** Both arms, same model, **same window (40,960), same prompt bytes**: R at
  n = 3, K at n = 3, and Q56 at n = 1 for abcc (claudette's Q56 numbers exist at 32k; re-run one at
  40,960 so the pair is legal).
  * Record per cell: outcome, editing calls, bytes read, peak prompt, wall clock.
  * **GPU: roughly 6–8 hours in total. Ask David before running.**
* **Exit:** a two-column table, abcc vs claudette, on three suites. **Decision D1** (§5) reads it.

### ▶ Phase B — close the engine gap (the core of the plan)

Order is by expected effect. Each bundle is one bench run against the Phase A baseline.

* **B1 — the parity bundle: D1 + D2.**
  * `edit_file`: `path`, `old_text`, `new_text`, `replace_all`. Refuse on 0 or more than 1 match,
    with claudette's near-miss hint. It is atomic and reported per call.
  * A `before`/`after` fuzzy variant, **only** if the bench shows exact matching failing on
    whitespace drift.
  * `read_file` windowed by default: 400 lines, with a `lines A–B of N` header already in the
    output, which F826 relies on.
  * `write_file`'s summary says "new files; use `edit_file` to modify".
  * `apply_patch` stays but is listed last. Fix its write loop so it is all-or-nothing on the write
    side too (the review-ladder roast).
  * **Run H1's `SEC-06` n = 3 before the full bench**: it is the cheapest decisive test in the plan.
* **B2 — one conversation per attempt (D4).** Keep Localize as a *phase of the log*, not a separate
  body. The same `Body` continues into Change with a plan-then-act instruction. Nothing Recon read
  needs re-reading, and F834's cross-phase repeats disappear by construction.
  * This amends ADR-0002's *attempt* level, not the mission level. The frozen prefix per posting
    (ADR-0011) can stay: the Change instruction arrives as a body message.
  * ⚠ **Measure it; do not assume it.** F781 says carrying Recon's bytes costs a p50 of 9,939 tokens,
    so it has to come with B3.
* **B3 — abcc owns its context (D3).**
  * **Compact before the server cuts:** at ~60% of the known window (`loaded_context_length`, F818),
    stub stale tool results claudette's way. The stub says *do not re-run to restore this*. Keep the
    last K results whole.
  * **Never let `truncateMiddle` decide.** The guard's escape valve (Action ④) becomes moot here:
    the stub replaces the back-reference.
* **B4 — the fix loop inside the attempt (D5).**
  * When Builders says done, the host runs the declared rungs. On a refusal it appends the rung's
    own output to the **same** conversation and grants up to N more rounds (N = 2–3), still inside
    the attempt. This is claudette's forge loop, with abcc's deterministic rungs as the verifier —
    better than forge's model verifier.
  * **Auto-format:** apply the repository's declared formatter (`cargo fmt`) to the worktree before
    the standard rung and record it as an event. It is what any human does before committing, and it
    converts the 4-of-10 pure-fmt near-misses for free.
  * Both change what the gate accepts, so both need David's ruling (ADR-0024 amendment).
* **B5 — the knobs (D6, D7, D8), each one bench arm:**
  * temperature 0 vs server default;
  * rounds 40 with a graceful landing vs 24 hard;
  * `-c 65536` vs 40,960, with the spill witness (`main.log`) checked on every load.
  * These are cheap flags. Keep whichever wins, and write it into `abcc check`'s output.
* **Exit:** abcc ≥ claudette on R and K at matched settings, **or Decision D2**.

### ▶ Phase C — co-dev mode, the daily driver

David's success test is *"casually opens ABCC 2.0 for his daily work instead of Claude Code."*
Claudette earns that as an **interactive REPL**. abcc today is a batch queue: `task`, then `run`,
then read the result later.

* **C1 — `abcc chat` (or `abcc do "<ask>"`).**
  * **Conversation:** one conversation in a worktree of the operator's repo, streaming, with the
    operator able to type mid-task: correct, redirect, *"stop reading, edit line 180"*.
  * **Machinery:** same engine, same tools, same event log.
  * **Ending:** `/done` runs the gate, shows `abcc diff`, and `land`s on a keypress.
  * This is where the human steering that made claudette's co-dev work lives. Nothing in the batch
    path can supply it.
* **C2 — review minutes, observed rather than typed.** The clock starts when the diff is shown and
  stops at land or reject, and it is recorded by the tool. The review-ladder roast showed typed
  minutes are fiction. This makes W13's metric real without an agent ever "typing a review".
  `abcc review <minutes>` stays as a manual override.
* **C3 — the batch queue stays** for overnight and for the bench. `board` already answers *what is
  waiting on me*.
* **Exit:** David uses `abcc chat` for real work on two separate days, by choice.

### ▶ Phase D — the 100-task drive (David, 2026-09-20)

*"Drive the tool for at least 100 tasks before we decide if it's a good coding tool."* Started only
after Phase B's exit, so the 100 measure the tool we mean to keep.

* **Sources:** grep-verified claudette `FINDINGS.md` cards, a second real repo (David's ruling), and
  abcc's own backlog (items with production callers only, never accessors chosen to fit).
* **Control arm:** 20 of the 100 also go through claudette on the same prompt.
* **Recorded per task:** landed?, attempts, observed review minutes, rework (a later commit touching
  the same lines within 14 days), and whether the model's own test goes red on the pre-image (see
  E1).
* **Verdict:** David's, on the numbers.

### ▶ Phase E — trust and finish (in parallel, desk work)

* **E1 — `abcc verify <task>`: F832's missing check, report-only (Action ①).**
  * **Hunk split, scoped to Rust and Python deliberately:** a Rust hunk inside the post-image's
    `#[cfg(test)]` span or under `tests/` is a test hunk; a `test_*.py` or `tests/` file is a test
    file.
  * **The check:** apply only the test hunks to `checkpoint_from` and run the toolchain test command
    via `Gate::run_rung`. **Red = the test proves the fix. Green = regression guard only.**
  * **It never refuses** (SHELL-10's ruling). Print it beside the Judge's report in `land`.
* **E2 — `t2018` (Action ②):** land the correct production fix and replace its test in a
  follow-up. Cheaper than a re-run.
* **E3 — the typed Judge question** (GATE-P7), **only after** the 72-tree `off-b` control run
  (F825).
* **E4 — the console and battlefield:** after Phase C. It is the differentiator (W9) and it only
  matters once the tool is used.
* **E5 — code hygiene for self-hosting.** **36.5% of abcc's source lines are comments**
  (11,222 of 30,704 across the nine crates' `src/`), much of it finding narrative. A local model
  pays for every one of those lines when abcc works on abcc. Going forward, findings go in
  `research/` and ADRs, and code comments say *what and why* in a few lines. Trim opportunistically,
  never as a campaign.

---

## 4. The current work order, reconciled

| work-order item | where it goes |
|---|---|
| ① build the F832 check | **E1**, report-only, Rust/Python scoped |
| ② `t2018` | **E2**: land and replace the test |
| ③ why no editor on `SEC-06` | **B1's H1 test**, the first GPU run of Phase B |
| ④ does the escape valve earn 13% | **superseded by B3**: stale-result stubs replace back-references |

---

## 5. Decisions for David

1. **D1 — approve bench-first, and ~6–8 GPU hours for the Phase A baseline.**
   *Recommended.* Everything after depends on it.
2. **The ADR-0001 falsifier has fired: how should claudette's loop behaviours come over?**
   * **(a)** *Recommended:* reimplement them in `abcc-engine`, using claudette's own tests for those
     behaviours as the acceptance spec. This keeps the letter of *rewrite, don't port*.
   * **(b)** Port the specific functions directly (`edit_file` + `near_miss.rs`, `fuzzy_apply.rs`,
     `context_evict.rs`). They are David's own code; W12's licensing concern was v1's outside
     contributors, not claudette's core.
   * **(c)** Drive claudette as abcc's engine through the harness adapter.
3. **D2 — if Phase B does not reach parity:** fall back to 2(c) for the loop and keep abcc's log, gate,
   board and land around it. *Recommended as the pre-agreed fallback, so it is not re-argued later.*
4. **One conversation per attempt** (B2, amends ADR-0002 at the attempt level). *Recommended,
   subject to the bench.*
5. **The in-attempt fix loop and auto-`cargo fmt`** (B4). Both move what the gate accepts, which
   ADR-0017 makes David's call. *Recommended.*
6. **Co-dev mode is the daily driver; the queue is for overnight** (Phase C). *Recommended.*
7. **Retire the hand-picked ladder as evidence.** The three inconsistent accountings (p = 0.0186 /
   0.0609 / 0.0808) stay on the record, and the bench replaces them. *Recommended.*
8. **Research discipline:** a findings doc only when a bench number moves or a decision is needed,
   and no new prompt-paragraph experiments (F827 and P14 settled that a paragraph moves tool choice,
   never outcome). *Recommended.*
9. **Board debt** (the nine INTERVENTION REQUIRED rows, the six never-land P14 rows, and the four
   junk review rows) stays David's hand, as before.

---

## 6. What not to do

* **No more prompt paragraphs** as levers (F827, P14). The standing exception is naming the defect
  site and ruling out sibling files, which is subtractive (F820).
* **Do not wire `OpenAt200`** (F811–F814).
* **Do not change the Judge** before the `off-b` control (F825).
* **Do not reopen the slot count** (ADR-0020). Throughput is not the problem.
* **Do not add console or battlefield work** before Phase C exits.
* **Do not choose tasks to fit the tool.** An accessor with no caller is not a data point.
* **Do not quote any pooled rate** from the pilot ladder; quote the bench.

---

## 7. Scoreboard — what "good" means, checkably

| milestone | criterion |
|---|---|
| **Instrumented** | Phase A table exists: abcc vs claudette, three suites, matched settings |
| **Parity** | abcc ≥ claudette on R and K, n = 3, same model and window |
| **Useful** | R-suite land rate ≥ 50% on one-change cards and > 0 on multi-part; `SEC-06` lands |
| **Daily driver** | David uses `abcc chat` on two separate days by choice; review minutes observed, not typed |
| **Good coding tool** | Phase D's 100 tasks: David's verdict, on landed rate, observed review minutes and rework |

**Rough size:**

* **Phase A:** 2 desk sessions plus one GPU night.
* **Phase B:** 3–5 sessions with overnight bench runs.
* **Phase C:** 3–4 sessions.
* **Phase D:** 2–3 weeks of normal use.
* **Phase E:** in parallel.

The first GPU spend worth making is the **H1 test: `SEC-06` with `edit_file`, n = 3, about 30
minutes.** If it lands, most of this plan's ranking is confirmed in one evening.
