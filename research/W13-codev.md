# W13 — Co-development ergonomics and self-hosting

**Status: COMPLETE — 2026-08-27.** Session 6 of the 14-session landing budget. **Line budget:
≤ 500**, unchanged by W7's amendment. §13's ten sections once for the whole workstream rather than
per item — the six brief bullets share one ruling, so splitting them would spend the budget on
headers. **Findings F423–F437**; next free number is **F438**. The second half of the deliverable,
the proposed CLAUDE.md skeleton, is `research/W13-claude-md-skeleton.md` and is not counted against
this budget (precedent: W7's `spikes/w7-injection/`).

The six bullets from `RESEARCH_BRIEF.md:983-1001`:

1. ✅ **Repo conventions that make agents effective** (F423–F428) — CLAUDE.md structure, layout,
   test commands, hooks, subagents, current Claude Code recommendations, and the Rust loop latency
   the brief singles out *"because agent loop latency is bounded by it."*
2. ✅ **CI an agent can read and act on** (F429, F430) — what signals should fail a run.
3. ✅ **Guardrails against silent architectural drift** (F431, F432) — ADRs, changelog, review gates.
4. ✅ **How agent commits and human PRs coexist** (F433).
5. ✅ **Long-term failure modes people report** (F434–F436) — the one bullet with no donor evidence;
   answered by live research, and it is the bullet that ends up defining the milestone.
6. ✅ **The self-hosting milestone, defined concretely** (F437) — §16's *"the project is done when"*,
   so this is an acceptance-criteria item and not just a section.

**What this workstream changes for anyone reading only one thing.** The donor evidence inverts:
**the repo that actually co-develops with an agent has no agent-facing conventions at all, and the
two that do not have three files between them, one six months stale.** So there is no convention
set to inherit — only a set of shapes to avoid. And the milestone cannot be defined in commits.
Every long-term failure mode in the literature is a *review-burden* failure, so a milestone counted
in agent-authored commits measures the thing that got cheap. **The milestone is defined in human
review minutes per merged change, and the donor's own self-hosting week is the floor to beat.**

---

## Question

Three questions, in dependency order. **(a)** What does this repository have to contain, on day one,
for an agent to work in it effectively — and what does the family's existing practice tell us to
copy or avoid? **(b)** What is the fastest honest feedback loop a Rust agent can run here, measured,
since the brief states loop latency bounds everything. **(c)** What exactly is the self-hosting
milestone, stated so that reaching it is *evidence*, not an announcement?

§12's split — Claude Code on architecture and hard reasoning, Claudette on local execution and
mechanical volume, David as the gate, ABCC 2.0 progressively taking over — is already written and
answered. It is confirmed here, not re-derived.

## Method

Three donor checkouts read directly, at `af3f804` (Claudette), `d5528ea` (ABCC v1), `d6c1601`
(BCF). Every agent-facing and contributor-facing file located by `find` over each tree, then read.
Loop timings measured on this desktop, warm, **with exit status asserted on every run** — the
`cargo fmt` row came back a *failure*, and a failure is not a timing (see the standing rule on
verifying claims against code). Self-hosting numbers come from `git log` over all 471 commits, not
from the README's claim about them. Bullet 5 and the current Claude Code recommendations are live
research: primary sources fetched and cited with retrieval dates, because no donor has anything on
either. `ls` counts were checked recursively — `plans/` shows 7 entries and holds 119 files.

**One limit, stated rather than hidden.** The loop ladder is **Claudette only**. That is the right
subject — 2.0 is Rust and Claudette is the Rust donor — but no equivalent numbers were taken for
v1 (TypeScript/Python) or BCF, so nothing here generalises to them.

## Inherited

Everything agent-facing in the family, with the file references:

| repo | file | lines | state |
|---|---|---|---|
| Claudette | `CLAUDE.md` / `AGENTS.md` | — | 🚨 **absent.** Neither exists anywhere in the tree |
| Claudette | `.claude/settings.local.json` | — | **41 `permissions.allow` entries and nothing else.** No hooks, subagents or skills |
| Claudette | `.github/` human stack | — | `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `PULL_REQUEST_TEMPLATE.md`, `ISSUE_TEMPLATE/`, `SECURITY.md`, `dependabot.yml` |
| v1 | `CLAUDE.md` | 582 | the live one — architecture, model routing, Ollama config; touched 2026-08-05 |
| v1 | `.claude.md` | 500 | 🚨 a **six-month-stale orphan** (2026-02-07), never read |
| v1 | `CLAUDETTE.md` | 113 | 🚨 the best-designed of the three, and see F426 |
| v1 | `.claude/settings.local.json` | — | permissions only, same shape as Claudette's |
| BCF | `CLAUDE.md` | 388 | developer guide; no `.claude/` directory at all |
| BCF | `CONTRIBUTING.md` | 163 | names the three CI commands explicitly — and see F430 |

What other workstreams already decided, which this one applies rather than reopens:

- **W7 — the ruling.** A denial in prose binds only as far as the model complies (shipped
  configuration complied with an injected instruction 39/50); the real control is denying the
  class. **Every "never do X" line in a CLAUDE.md is a candidate capability removal.**
- **W7 F422** — the destructive-git guard exists twice with neither copy covering the other.
- **W6 item 6** — worktree isolation, measured at 0.25 s. That is the mechanism for bullet 4;
  it is cited here, not re-derived.
- **W3** — the seven Task states, the durable event log, the three-phase gate, and *"a model
  verdict is a report and never a gate."* Bullet 3's "review gates before merge" is W3's gate
  applied to this repository.
- **`prestudy/inheritance-map.md:431`** already marks v1's `plans/` discipline **REUSE** as the
  direct precedent for W13's conventions.

## Findings

### Bullet 1 — repo conventions

**F423 — The repo that co-develops with an agent has no agent-facing conventions; the two that do
not, do.** Claudette's README says *"She helps build herself"* and the agent is a listed GitHub
contributor — and `find` over the whole tree returns **no `CLAUDE.md` and no `AGENTS.md`**. Its
entire agent configuration is `.claude/settings.local.json`, which has exactly one top-level key,
`permissions`, holding **41 allow entries**. Meanwhile v1 and BCF, neither of which has an agent
in its contributor list, ship **three agent-facing files between them**. The practice and the
documentation of the practice are in different repositories. **There is no convention set here to
inherit; there is a set of shapes to avoid.**

**F424 — One of the three is a six-month-stale orphan that Claude Code never reads.** v1 has both
`CLAUDE.md` (582 lines, last touched 2026-08-05) and `.claude.md` (500 lines, 2026-02-07). They
share no structure — the diff between them is 1,084 lines — so this is not a stale copy, it is a
second document. **The leading dot makes it a different filename**, so the loader never opens it,
and nothing in the repo says so. This is the failure mode the whole workstream is about, in its
cheapest form: an agent-facing document that has been wrong for six months with no signal.

**F425 — Both donor CLAUDE.md files are status documents, and a third of each sits under headings
the current guidance names on its exclude list.** Measured by heading span: **v1, 183 of 583 lines
(31%)** under `Package Structure` (63), `Database Models` (11), `Archive Structure` (6) and a
`Current Priorities` block of six numbered phases (103) still marked *"COMPLETED Feb 2026"*;
**BCF, 150 of 389 (39%)** under `10-Mission Stress Test Results (March 2026)` (26), `Model
Benchmark Results (8+ models tested)` (15), `Best Run Results` (14), `Claude vs Local Comparison`
(11), `Key Learnings` (32), `Module Map (30 modules)` (36) and `TUI Polish — DONE` (16). The
official guidance's exclude column names, verbatim, *"Information that changes frequently"*,
*"File-by-file descriptions of the codebase"* and *"Long explanations or tutorials"*, and warns
*"Bloated CLAUDE.md files cause Claude to ignore your actual instructions!"*
(<https://code.claude.com/docs/en/best-practices>, retrieved 2026-08-27). **Both donors put their
roadmap and their benchmark results in the file that is loaded on every single turn.**

**F426 — v1's `CLAUDETTE.md` is W7's ruling written as prose, and its denial list is wider than the
guard that shipped.** It opens with denials: *"Never run `git commit`, `git push`, or any
destructive git command (`reset --hard`, `checkout -- .`, `restore .`, `clean -fdx`, `stash drop`,
`branch -D`). Leave your work uncommitted in the working tree. A human reviews and commits it."*
Then: never `pnpm install` or edit the lockfile, do not reformat code you were not asked to change,
splice `old_text`/`new_text` exactly. **This is `max_tier` expressed as a sentence, because v1 had
no mechanism to express it any other way** — and W7 measured what a sentence buys. Note the
direction of the gap: **this prose denies `git clean` and `git stash drop`, and W7 F422 found that
Claudette's shipped guard catches neither of them through either path.** The best-designed
agent-facing document in the family is a list of the capabilities that should have been removed.

**F427 — The agent loop ladder, measured** (Claudette `af3f804`, this desktop, warm, exit status
asserted on every row):

| step | time | note |
|---|---|---|
| `cargo check --workspace --all-targets`, no-op | **415–529 ms** | the inner loop; two runs, two sessions |
| same, one file touched | **585 ms** | the realistic inner loop |
| `cargo fmt --all --check` | 916 ms | **rc=1** — see F430; a failure, not a timing |
| `cargo clippy --all-targets -- -D warnings` | **6,753 ms** | the CI gate; **11× the check** |
| `cargo test --lib` | **4,957 ms** | 1,155 pass, 6 ignored, 4.45 s in-process |
| `cargo test --lib --bins --tests` (the CI form) | **4,988 ms** | |
| `cargo test --workspace`, test binaries relinking | **40,373 ms** | the cliff |

Single crate (`crates/claudette`), **1,293 `#[test]`/`#[tokio::test]` functions**, 23 GB `target/`.
**In-process execution is 4.91 s across 6 binaries; everything else on those rows is compile and
link.** ⚠ The dossier's headline *"14.76 s full-suite"* is `cargo test --lib` at a different
version and warmth — not wrong, but **not the number that bounds the loop.** An agent pays ~12 s
warm for check+clippy+test and **~47 s whenever the test binaries relink**, which is ~113× the
inner loop. That ratio, not any absolute number, is the design input.

**F428 — Hooks and subagents have zero precedent in this family, and the one real piece of co-dev
tooling was deliberately kept out of the public repo.** Both `.claude/settings.local.json` files
are permissions-only (F423); BCF has no `.claude/` at all. The closest artifact in the family is
v1's `claudette-check.mjs`, a post-edit check router held **outside** the public repo on the stated
grounds that *"ABCC is public and this is co-dev tooling"* — and its own header documents two traps
in Claudette's `override_cmd`: the command string is `split_whitespace()`'d so **no token may
contain a space**, and if no token contains `{file}` the path is **appended blindly**. So the
family has built the thing a hook does, learned two real lessons doing it, and published neither.
Current guidance is explicit about the division this repo will need: *"Unlike CLAUDE.md
instructions which are advisory, hooks are deterministic and guarantee the action happens"*, and
the fix for an over-specified CLAUDE.md is *"delete it or convert it to a hook"*; a Stop hook
*"runs your check as a script and blocks the turn from ending until it passes"*, overridden after
8 consecutive blocks; subagents *"run in their own context with their own set of allowed tools"*
(<https://code.claude.com/docs/en/best-practices>, retrieved 2026-08-27).

### Bullet 2 — CI an agent can read and act on

**F429 — Eight jobs, and exactly one of them cannot fail a run.** Claudette's `ci.yml` defines
`fmt`, `clippy` (matrix OS, run twice — plain and `--all-features`, both `-D warnings`), `audit`,
`deny`, `test` (matrix OS, plain and `--all-features`), `build` (`--release --locked`), `msrv`
(Rust 1.88, `--locked`) and `coverage`. **`coverage` carries `continue-on-error: true`
(`ci.yml:169`)** — it is the one advisory signal, and the other seven are gates. That is bullet 2's
question already answered by the donor, and answered well: the signal an agent must not act on is
marked in the file the agent can read. Release adds the publish gate W7 F419 recorded
(`needs: [verify, tag-version-match, audit, deny]`).

**F430 — Every third-party action is SHA-pinned except the one that chooses the compiler, and that
one is unpinned twice.** `ci.yml` pins `actions/checkout`, `Swatinem/rust-cache` and
`actions/upload-artifact` to full SHAs with version comments — and references
**`dtolnay/rust-toolchain@stable` by floating tag in all 8 jobs, then asks it for the floating
`stable` toolchain.** None of the three repos has a `rust-toolchain.toml`. The author demonstrably
knows how: the `msrv` job passes `toolchain: "1.88"` explicitly. **The floor is pinned and the
ceiling floats.** Measured consequence: at `af3f804` with a clean tree, local `cargo fmt --all
--check` **exits 1** with 3 diff hunks, all in one file (`crates/claudette/src/run/line_editor.rs`
at :817, :862, :910), on rustfmt 1.9.0-stable (59807616e1, 2026-04-14) — all three are line-wrapping
disagreements in test assertions. ⚠ **This is not "HEAD fails its own gate"**: the direction depends
on which rustfmt each side resolved, and CI's is unknowable from the file. The finding is the
unpinning. And it already has a victim: **BCF's `CONTRIBUTING.md:41` promises *"They're the same
ones CI runs, so if they're green locally, CI will be green too"*** — true of the *commands* (they
match `ci.yml` exactly) and not of the *toolchain*, in a repo with no pin either. An agent that
runs the gate locally and believes the green can be red in CI for reasons unrelated to its change.

### Bullet 3 — guardrails against silent architectural drift

**F431 — The drift failure mode is captured in the wild here, with the correction written by the
same author.** Claudette's `docs/decisions.md` opens with a 12-line `> [!WARNING]` banner declaring
itself *"HISTORICAL — planning-era design doc, NOT the shipped architecture"* and then **enumerates
which of its own ADs are fiction**: AD-1/AD-2 (it is a single crate, not six), AD-3 (*"claudette
has no cloud provider"*), AD-4/AD-7 (the real loop is Coder → Verifier), AD-5 (three-tier
permissions and no platform sandboxing — **that module was removed**), AD-6 (MSRV 1.88). This is
the honest retrofit, and it is the right one for a document that already drifted. It is also proof
that a design doc which can be edited will be believed until someone notices: **AD-5 independently
corroborates W7 item 1, which had to re-derive it from source.**

**F432 — The written-before-the-work discipline exists and is large.** `plans/` is **119 files
across 6 dated campaigns** (61 of them under `roast-2026-08-02`) — per-sprint task specs written
before the work, which the inheritance map already marks REUSE. `CHANGELOG.md` is 2,404 lines.
⚠ `ls plans/` shows 7 entries; they are directories, and the 119 is the recursive count.

### Bullet 4 — agent commits and human PRs coexisting

**F433 — The merge record is erased, both contributor stacks are silent on agent-authored work, and
the family's only working precedent for bot commits is dependabot.** In 471 commits there are
**zero merge commits** — everything lands squashed or rebased, so nothing in the history says which
changes arrived as a PR. Both contributor docs are silent on the question: Claudette's
`CONTRIBUTING.md` discusses Claudette-the-product, its `PULL_REQUEST_TEMPLATE.md` has zero hits for
agent/AI/generated/bot, and BCF's `CONTRIBUTING.md` mentions "agent" only when describing its own
CTO module. Yet the repo already runs a working bot-and-human coexistence: **`dependabot[bot]` has
40 of the 471 commits**, and it works for reasons that transfer exactly — its changes are narrow,
its `dependabot.yml` caps it at 5 open PRs on a weekly schedule, its commits are prefixed and
labelled, and it passes the same eight jobs as everyone else. **Rate limit, narrow scope,
identifiable authorship, same gate.** That is the pattern, and it is already in the repo.

### Bullet 5 — long-term failure modes (no donor evidence; live research)

**F434 — AI-introduced defects survive, and they are overwhelmingly maintainability debt.** The
largest empirical study available tracked 484,366 distinct issues across 3,946 repositories from
302.6K verified AI-authored commits (≥100 stars; Python/JS/TS; attribution from git metadata —
actor logins, author emails, `Co-authored-by` trailers): **22.7% of tracked AI-introduced issues
still survive at HEAD**, and issues introduced more than nine months earlier survive at 22.8%.
The mix is **89.3% code smells, 6.0% correctness, 4.7% security**. The authors state their own
limit plainly — this captures AI work *"when the use of an AI coding tool leaves explicit traces in
Git metadata"*, a *"visible and attributable subset rather than the entire population."*
(Liu, Widyasari, Zhao, Irsan, Chen, Lo, *Debt Behind the AI Boom*, arXiv:2603.28592v2, 2026-04-26,
<https://arxiv.org/html/2603.28592v2>, retrieved 2026-08-27.) **The debt is not where an agent's
gate looks.** Seven of Claudette's eight CI jobs check correctness, safety and lint; none of them
measures whether the shape of the code is getting worse.

**F435 — What gets expensive is review, and it is what maintainers say in their own words.** A
practitioner study of 3,100 opinions finds verification burden *increasing* rather than decreasing,
with review shifting from stylistic to correctness-focused and reviewers scrutinising AI-generated
code more carefully rather than less (Agarwal, Miller, Kästner, Vasilescu, arXiv:2607.07980, 2026,
<https://arxiv.org/pdf/2607.07980>, retrieved 2026-08-27; ⚠ the PDF's compressed streams blocked
verbatim extraction of the quantitative tables, so only the structural findings are cited here).
The lived version is sharper: Godot maintainer Rémi Verschelde describes AI PRs as *"increasingly
draining and demoralizing for Godot maintainers"* and says *"I don't know how long we can keep it
up"* (devclass, 2026-02-19,
<https://www.devclass.com/ai-ml/2026/02/19/github-itself-to-blame-for-ai-slop-prs-say-devs/4091420>,
retrieved 2026-08-27). **The cost of producing a change fell to near zero; the cost of triaging one
did not move.** This is the finding that decides bullet 6.

**F436 — The responses projects actually reached for are rate limits and identity, not quality
filters.** From the same reporting: Blender proposed an AI-contributions policy, with similar
policies at the Linux Foundation, Fedora, Firefox, Ghostty, Servo and LLVM; Coolify shipped an
"Anti Slop GitHub Action" it claims *"could have closed 98 percent of slop PRs"*; tldraw
auto-closes all external PRs; Gentoo is migrating off GitHub over Copilot promotion (devclass,
2026-02-19, as above). ⚠ The 98% is a vendor's claim about its own tool, quoted here as a claim.
**None of these is a code-quality mechanism** — they are caps on volume, requirements to declare
authorship, and in the limit closing the door. Which is exactly the dependabot pattern in F433,
arrived at independently by projects under load.

### Bullet 6 — the self-hosting milestone

**F437 — The donor's self-hosting claim is true, one week wide, and none of it is architectural.**
Claudette's README says she *"runs her own Forge pipeline against this repo, clears the real
build-and-test gate before anything is pushed, and opens genuine pull requests under her own git
identity."* Against `git log`: **15 of 471 commits (3.2%)** are authored by `Claudette
<293093788+claudette-ai-01@users.noreply.github.com>`. 🚨 **All 15 land between 2026-06-13 and
2026-06-19 — one week, and nothing since** (HEAD is 2026-08). Every one is a small additive tool
feature: `grep_search` context lines / `count_only` / `case_sensitive`, `repo_map` definitions for
C#, Java, C/C++ and PHP, `git_status` filter, `edit_file replace_all`, two runtime compaction
fixes, one docs commit, one single-keypress approval. **None touches architecture, and none crosses
a module boundary.** Other authors: david/David/mrdushidush **416**, `dependabot[bot]` **40**.
**The claim is honest and the milestone it represents is a floor, not a finish line.**

## Options compared

How to define the milestone — the only genuinely open choice here, scored against what §16 needs
from it (*"the most honest possible proof that the tool works"*):

| option | countable? | resists F435? | evidence of what | verdict |
|---|---|---|---|---|
| **A. Commit share** — "N% of commits are agent-authored" | yes, trivially | ❌ no | that generating changes is cheap, which is not in doubt | rejected |
| **B. Task completed end to end** — pipeline runs plan→edit→gate unattended | yes | partly | that the loop closes; says nothing about what it closed on | **a rung** |
| **C. Gate-accepted, boundary-crossing** — crosses a module boundary or alters a public interface, and the gate is what accepts it | yes | partly | that the work is non-trivial and the human is not the verifier | **a rung** |
| **D. Review minutes per merged change, flat or falling over N consecutive tasks** | yes, with a log | ✅ **yes** | that the burden the literature says moves has *not* moved here | **the milestone** |

## Recommendation

**1. Ship a CLAUDE.md on day one, and keep it under ~120 lines.** The family's practice inverts the
right answer (F423), and both existing files fail the current guidance in the same measurable way —
31% and 39% roadmap, benchmark results and file-by-file maps in a file loaded every turn (F425).
Apply the guidance's own test to every line: *"Would removing this cause Claude to make mistakes?"*
Roadmap goes to `plans/`, benchmarks to `research/`, module maps nowhere — an agent reads the code.
The skeleton is `research/W13-claude-md-skeleton.md`.

**2. Every denial in that file becomes a capability the role does not have.** This is W7's ruling
and it is not re-argued here; F426 is the evidence that the family already knows the *content* of
the right denial list and only lacked the mechanism. Concretely: v1's `CLAUDETTE.md` prose is the
specification for 2.0's `max_tier` for the agent role, and **it names two commands (`git clean`,
`git stash drop`) that W7 F422 found unguarded through both shipped paths.** Where a rule cannot be
a capability, make it a hook — deterministic, not advisory (F428).

**3. Pin the toolchain, and mark the advisory job.** Add `rust-toolchain.toml` and pin
`dtolnay/rust-toolchain` by SHA like every other action in the file (F430). Keep Claudette's eight
jobs and its single `continue-on-error` job — that is the inherited control worth copying (F429),
and it should stay at exactly one, labelled, so "which signals fail a run" is answerable from the
file by an agent. Do **not** repeat BCF's local-equals-CI promise until the pin exists.

**4. The loop contract, in CLAUDE.md, with the measured numbers and the machine named.**
`cargo check` in the edit loop (~0.5 s), `clippy` + `--lib` tests before proposing a change
(~12 s), the full workspace gate once before commit (~47 s when binaries relink). The ratio is
~113× between the ends of that ladder (F427), which is why this is a rule and not a preference.

**5. Drift: ADRs are append-only, in `research/decisions/`.** §13 already requires the directory.
The rule that follows from F431 is that **an ADR is never edited to match reality — it is
superseded by a new one that says so**, because the donor's `docs/decisions.md` had to grow a
12-line banner enumerating its own fictions, and until it did, W7 had to re-derive AD-5 from
source. Keep `plans/`-style specs written before the work (F432, already REUSE in the inheritance
map). W3's three-phase gate is the review gate; nothing new is needed.

**6. Coexistence: copy the dependabot pattern, and write the policy before the first outside PR.**
Rate limit, narrow scope, identifiable authorship, same gate (F433). Concretely: agent work happens
in a worktree (W6 item 6, 0.25 s), every agent commit carries a `Co-authored-by:` trailer so the
share is countable at any time, agent PRs are capped in flight, and `CONTRIBUTING.md` states the
AI-contribution policy from the first public commit. Both donors have nothing, and F436 shows what
the projects that waited ended up doing under load. **Keep squash-merge, but the trailer is then
the only surviving record of authorship** — that is the cost of zero merge commits (F433), and it
is acceptable only because the trailer is machine-readable.

**7. The self-hosting milestone, defined concretely — this closes §16's clause.** Four rungs, each
strictly harder, each countable from the event log W3 already specifies:

- **M0 — the floor, already reached by a donor.** Additive single-tool features, human reviews
  each diff, sustained for one week. **v1's Claudette did exactly this: 15 commits, 2026-06-13 to
  06-19** (F437). 2.0 does not get to claim this rung as an achievement.
- **M1 — the loop closes.** ABCC 2.0 takes a task from its own tracker and runs its own pipeline
  end to end unattended — plan, worktree, edit, gate — with the human's only act being merge.
- **M2 — the work is non-trivial and the gate is the acceptor.** The change **crosses a module
  boundary or alters a public interface**, and it is accepted because the gate passed, not because
  a human read it closely. This is the rung v1's week explicitly did not reach.
- **M3 — the milestone.** **Ten consecutive M2 tasks with human review minutes per merged change
  flat or falling**, no human edit to the agent's diff, and the surviving-defect count from those
  ten tracked at 30 and 90 days. M3 is the only rung that is evidence *against* F434 and F435
  rather than a restatement of what got cheap.

**Measure review minutes from the start**, at M0, or M3 has no baseline. That instrument is one
column in the W8 harness format and one event type in W3's log; it needs no new machinery.

## Rejected alternatives and why

- **Counting agent-authored commits as the milestone.** Rejected: F437 shows the donor's honest
  15 commits, and F435 shows the burden moved to review, so a commit count measures the half that
  got cheap. Kept as a *reported* number, never as the criterion.
- **Copying a donor CLAUDE.md as the starting skeleton.** Rejected on F425 — a third of each is
  content the current guidance names on its exclude list, and the shape would be inherited along
  with it. v1's `CLAUDETTE.md` is the exception worth reading, and its content becomes capabilities
  (recommendation 2), not prose.
- **A `.claude.md`-style second agent document** (v1's shape). Rejected on F424: two documents with
  no loader relationship is a six-month-stale orphan waiting to happen. One file, plus on-demand
  skills for the things that are only sometimes relevant.
- **Requiring a human review of every agent change indefinitely.** Rejected: that *is* M0, it is
  the donor's floor, and F435 says it is the thing that stops scaling. The gate has to become the
  acceptor, or the project has built a faster way to generate a review queue.
- **An AI-contribution policy written after the first outside PR arrives.** Rejected on F436 — the
  projects in that finding all wrote theirs under load, and one of them shut the door entirely.

## Effect on fun

Two effects, both real. **The ladder is a scoreboard.** M0→M3 is four ranks with countable
promotion criteria, which is exactly the shape W5's command center already renders, and "the tool
took a boundary-crossing task and the gate accepted it" is a better campaign milestone than any
synthetic mission. **And the loop ladder is the difference between a game and a wait.** 0.5 s is
interactive; 47 s is a loading screen. Putting `cargo check` in the inner loop is an ergonomics
decision and a fun decision at once — the operator watching the console sees the agent move. The
risk in the other direction is F435's: if the human becomes a full-time reviewer of an agent that
never stops, the tool has made the least fun part of the job bigger. M3 is defined the way it is
specifically so that outcome fails the milestone.

## Open questions

- **OQ-W13-1 — what is a "module boundary" in a single-crate layout?** Claudette is one crate;
  M2's criterion needs a concrete test for 2.0's layout, and W3's workspace decision settles it.
  Not blocking: M0 and M1 are unambiguous.
- **OQ-W13-2 — who reviews at M2?** "Accepted on the gate" needs a named policy for what David
  still reads. W6's independence check is always on, so the gate is not bare, but the human's
  remaining role is a decision, not a derivation.
- **OQ-W13-3 — surviving-defect tracking at 30/90 days needs a mechanism.** F434 is the reason to
  want it; nothing in the current harness measures defect survival. Possibly W8's, possibly nothing
  until M2 is close.
- **OQ-W13-4 — does the agent get commit rights, ever?** v1's `CLAUDETTE.md` says never, W7 says
  make that a capability, and M3's "human's only act is merge" preserves it. Revisit only if M3
  lands.

## Confidence: high on the donor evidence, high on the ladder, medium on the milestone thresholds

The donor findings are direct file and `git log` reads at named commits, re-verified this session
after being scouted, and two got sharper under re-verification (F430's SHA-pinning contrast, and
F425's exact spans). The loop ladder is measured with exit status asserted, and the inner-loop
number reproduced across two sessions (415 ms / 529 ms). The live-research findings are primary
sources with retrieval dates, and their two soft spots are flagged in place — the 98% is a vendor
claim, and the 3,100-opinion paper's tables could not be extracted verbatim.

**Medium on the thresholds, and specifically on "ten consecutive."** Ten is a judgement call, not a
derived number; it is large enough that a lucky run does not clear it and small enough to reach in
a campaign. What would raise confidence: running M1 once for real and measuring how long a single
end-to-end task takes, which converts "ten" from a guess into a schedule. What would falsify the
whole recommendation: if review minutes per change turn out to be dominated by something other than
the agent's diff — reading the gate output, say — then M3 measures the wrong thing and the
criterion moves to the gate's legibility instead.
