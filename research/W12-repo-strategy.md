# W12 — Repo strategy and succession

**Status: COMPLETE — 2026-08-27.** Session 7 of the 14-session landing budget. **Line budget:
≤ 400.** §13's ten sections once for the whole workstream: three of the brief's seven bullets were
answered by David on 2026-08-07 and are applied here, not re-derived, so per-bullet sections would
spend the budget on headers. **Findings F438–F449**; next free number is **F450**. The second half
of the deliverable, the draft announcement outline, is `research/W12-announcement-outline.md` and
is not counted against this budget (precedent: W13's CLAUDE.md skeleton).

The seven bullets from `RESEARCH_BRIEF.md:966-979`:

1. ✅ **New repo, new major version, or a `2.x` branch** — **answered** (new repo). Applied, not
   re-derived. But it does not answer the *slug*, which is a separate question and is F445.
2. ✅ **Naming** — **answered** (keeps "Agent Battle Command Center"). Same caveat.
3. ▶ **What happens to V1** (F447, F448, the options table, recommendations 1–4) — §16's named
   acceptance item, so this is the load-bearing bullet.
4. ▶ **Migration of task history and training data** (F449).
5. ▶ **The open good-first-issues and in-flight community PRs** (F438–F440).
6. ▶ **Release communication** — the announcement outline, plus F446 on what must not be repeated.
7. ✅/▶ **Licensing** — dual MIT OR Apache-2.0 is **answered**; whether it can be *offered* is not,
   and that is F441–F444.

**What this workstream changes for anyone reading only one thing.** Both halves of the brief's
worry invert. The community it asks you to protect **is not in flight** — zero outside PRs are
open, the eight good-first-issues are one, and the four contributors finished in February — so the
obligation is *attribution to past contributors*, not PR triage, and the repo currently pays it to
nobody. And the licensing risk is the **mirror image** of the brief's guess: BCF, the repo it
worried about, is sole-authored and freely relicensable; **v1** is the one with four outside
copyright holders. Measured across the whole tree, **944 outside-authored lines survive at HEAD in
20 files** — not the 162 a three-file spot check finds. **David's ruling of 2026-08-27 settles it:
reimplement from scratch.** The measurement is why that costs nothing (F443).

---

## Question

Four questions, in dependency order. **(a)** What does 2.0 actually owe the people who contributed
to v1, given that "the community is real and small kindnesses matter" — and is the debt the one the
brief assumes? **(b)** Can David offer 2.0 under MIT OR Apache-2.0 at all, given v1's inherited
code? **(c)** What happens to v1 and its users, mechanically — which is §16's acceptance item and
therefore the deliverable's spine. **(d)** What does the announcement have to say, and what must it
not repeat?

## Method

Three sources, all re-derived rather than quoted. **Live GitHub state** via `gh` against
`mrdushidush/agent-battle-command-center`, retrieved **2026-08-27** — every count below carries
that date because these numbers drift. **The repository itself** at `d5528ea` (2026-08-06): licence
files, `package.json`, README, the `.github/` stack, and `docker-compose.hub.yml`. **`git blame
HEAD`** over *every* tracked text file — 395 files, not a sample — counting surviving lines per
outside author, then cross-referenced against `prestudy/inheritance-map.md`. One GitHub behaviour
claim (rename redirects) is cited to primary documentation with a retrieval date.

⚠ **Two traps this method exists to avoid.** Blame must be taken as `git blame HEAD`; blaming the
working tree returns *"Not Committed Yet"* for whole files and hides the question entirely. And a
spot check of three files is a *sample*, not a coverage claim — the scout's 162 lines were right
about the three files it read and silent about sixteen others. Per the standing rule on verifying
claims against code, the sweep here is exhaustive over tracked text files and says so.

**One limit, stated rather than hidden.** Nothing here is legal advice, and the one genuinely legal
question — whether a Rust reimplementation of a TypeScript file is a derivative work — is *not
answered* in this document. It is measured, routed to David, and now ruled on by him.

## Inherited

| source | artefact | state at `d5528ea` / 2026-08-27 |
|---|---|---|
| v1 | `LICENSE` | **MIT**, "Copyright (c) 2026 Agent Battle Command Center" — no `NOTICE`, no `AUTHORS` |
| v1 | `README.md:3` | a succession banner that already exists — and see F446 |
| v1 | `package.json` | `"version": "0.13.0"`, 🚨 **`"private": true`** — never published to npm |
| v1 | `docker-compose.hub.yml` | `dushidush/api\|agents\|ui:latest` — the actual distribution channel |
| v1 | `.github/` + community files | `CONTRIBUTING.md` 575, `SECURITY.md` 316, `CODE_OF_CONDUCT.md` 44, `ISSUE_TEMPLATE/`, `pull_request_template.md`, `dependabot.yml` |
| BCF | `LICENSE`, `Cargo.toml:7` | **Apache-2.0 only**, sole-authored |
| Claudette | `crates/claudette/Cargo.toml:6` | **MIT OR Apache-2.0** — already the target, and on crates.io |

What other workstreams already decided, applied here rather than reopened:

- **David, 2026-08-07** (`abcc-2-decisions`) — new repo; keeps the name; dual MIT OR Apache-2.0;
  **Q10: clean break, documented, no migration code.**
- **W13 recommendation 6** — the AI-contribution policy and `Co-authored-by:` trailers go into
  `CONTRIBUTING.md` from the first public commit. 2.0's repo inherits that on day one.
- **W13 F433** — Claudette's `.github/` is the template for 2.0's *engineering* stack; v1's is
  where the *community-facing* half comes from (F440's fix lands there).
- **W8 `research/W8-u40-floor-check.md`** — v1's 39/40 is an after-retry number; 36/40 single
  attempt. This is the one measurement the announcement must respect (F446).
- **W5** — the console is a terminal, not a React web app. That decision is what puts most of the
  outside-authored code outside the carry path (F442).

## Findings

### The community, and what is actually owed

**F438 — The community is real, was real in February, and is not in flight.** Live, 2026-08-27:
**2 stargazers, 1 fork, not archived, public, created 2026-02-10**, last push 2026-08-24
(dependabot). **11 open pull requests — 10 are dependabot** and the eleventh is **David's own
#190**, open since 2026-05-18. 🚨 **There are zero in-flight community PRs.** The four outside
humans sent **13 commits, all between 2026-02-12 and 2026-02-23**, and none since: Gonçalo Alves 6,
Ayush 4, Karel Švancar 2, Mohit Hingorani 1 — every one merged. So the brief's *"do not leave
contributors hanging without a word"* has **nobody currently hanging**, and the obligation is
retrospective: attribution and a courteous notice, not PR triage. **This is not a failure and must
not be written as one** — four people showed up, thirteen commits landed, and the work is *done*.

**F439 — The brief's eight open good-first-issues are one, and it is David's own.** `gh` over all
labelled issues: **21 closed, 1 open** — #57, "Add export task results as CSV/JSON", opened
2026-02-13 **by David**. Of the four open issues in the whole repo, **all four are David's**, three
of them roadmap issues (#189, #120, #119). The onboarding surface the brief asks 2.0 to protect
was consumed as intended. **Nothing here needs a migration plan; it needs a closing note.**

**F440 — The repository thanks five upstream projects and zero humans.** `README.md:759`
*"🙏 Acknowledgments"* lists Anthropic, Ollama, CrewAI, Bark TTS and *"Classic RTS games"*. Four
humans with thirteen merged commits appear **nowhere in the repository outside git history** —
there is no `AUTHORS`, no `NOTICE`, no contributors section — while the README's last line reads
*"Built with ❤️ by the ABCC community"*. 🚨 **This is the small kindness the brief is actually
asking about, it costs one commit, and it is unpaid today.** It also has to be paid *before* the
succession notice goes up, not with it: a freeze notice that names no contributors is the version
that reads badly.

### Licensing, and the carry path

**F441 — The licensing risk is the mirror image of the brief's guess.** The brief asks about
*"whether any inherited BCF code has different terms given it was heading toward a paid model."*
Measured:

| repo | licence | copyright holders | can David offer it as MIT OR Apache-2.0? |
|---|---|---|---|
| **BCF** | Apache-2.0 only | David alone (Phase 0: no outside contributors) | ✅ **yes** — sole author, relicensable at will |
| **v1 ABCC** | MIT | David **+ 4 outside humans** | 🚨 **not unilaterally** |
| Claudette | MIT OR Apache-2.0 | David | ✅ already the target |

**The repo the brief worried about is the safe one.** BCF's Apache-2.0-only licence is a choice
David can change; v1's MIT contributions from four people are not his to re-offer under different
terms. The paid-model concern behind the question is a non-issue: nothing in BCF is licensed to
anyone else, so there is no third party whose terms could conflict.

**F442 — 944 outside-authored lines survive at HEAD across 20 files, not the 162 a three-file spot
check finds.** `git blame HEAD` over all 395 tracked text files:

| file | surviving outside lines | author | inheritance-map verdict |
|---|---|---|---|
| `ui/src/hooks/useKeyboardShortcuts.ts` | 124 | Gonçalo | not named — React UI |
| `ui/src/audio/voicePacks.ts` | 112 | Gonçalo | **PORT** (map `:370`) |
| `ui/src/components/layout/TopBar.tsx` | 104 + 8 | Gonçalo, Karel | not named — React UI |
| `ui/src/components/shared/Skeleton.tsx` | 93 | Gonçalo | not named — React UI |
| `ui/src/components/main-view/TaskQueue.tsx` | 92 + 25 | Ayush, Gonçalo | not named — React UI |
| `ui/src/components/shared/ShortcutsHelp.tsx` | 72 | Gonçalo | not named — React UI |
| `ui/src/components/shared/TaskCard.tsx` | 52 + 38 | Gonçalo, Karel | not named — React UI |
| `api/src/services/stuckTaskRecovery.ts` | 29 | Mohit | **PORT** (map `:256`) |
| `ui/src/store/uiState.ts` | 24 | Gonçalo | PORT row's ring buffer (map `:372`) |
| `ui/src/audio/audioManager.ts` | 21 | Gonçalo | **PORT** (map `:370`) |
| 10 more (`ActiveMissions.tsx`, 2 hooks, `App.tsx`, `routes/agents.ts`, 5 test files) | 150 | Gonçalo, Mohit | not named |

🚨 **Only 162 of the 944 sit in the three files the map marks PORT** — a fourth, `uiState.ts`, is
cited inside a PORT row for its ring buffer. The other 782 are React components,
hooks and tests that no map row names individually, and **W5's terminal decision drops the React
console wholesale** — so they are not on the carry path at all. Both halves of this matter: the
scout's *"it is all React UI a rewrite would not carry"* was right about 83% of the lines and wrong
about the three that count, and its corrected 162 was right about those three and silent about the
other sixteen files. **The honest statement is the sweep, not either spot check.**

**F443 — In the PORT files, the surviving outside lines are the container, not the content — and
David's ruling of 2026-08-27 is to reimplement from scratch.** Measured line by line:

- `voicePacks.ts` — of Gonçalo's 112 lines, **60 are pure punctuation** (`],`, `}`, `*/`) and the
  rest are the `interface` declaration, four function signatures, and the ten event keys repeated
  across three packs. **All 95 voice-line literals — every `text: '…'` — are David's** (`aad6612b`,
  `1e209d0b`). The creative content of the sound pack is David's without exception.
- `audioManager.ts` — the map calls the **queueing behaviour "the non-obvious part."** The priority
  queue, the sort, the `shift`, and the OOM cap are **100% David's** (`cc29c0ec`, `6f893943`).
  Gonçalo's 21 lines are two pack-selection accessors and two wrappers that delegate to
  `getVoiceLineFromPack`.
- `stuckTaskRecovery.ts` — Mohit's 29 lines are **one method**, `forceRecoverAll()`, a Prisma
  `findMany` over `status in (assigned, in_progress)`, of which ~9 lines are braces and blanks.

🚨 **So the clean-room instruction costs nothing, and the behaviour spec already exists.** PORT
means *reimplemented in Rust* regardless; the map at `:256` already specifies 2.0's stuck-task
watchdog **differently and better** than the code being replaced (watch `max(execution_log
.timestamp)`, cover every non-terminal state — the inherited found-set is a defect the map records
at length). Reimplementing `forceRecoverAll` from that spec is what W6 would have done anyway.
**Ruling, David, 2026-08-27: reimplement from scratch what the outside contributors added, so no
copyright question arises.** Recorded here as a project decision, not a legal conclusion.

**F444 — Nothing trademarked survives, and the audio assets are clean.** Gonçalo's commit is titled
*"feat: add StarCraft and Age of Empires voice packs"*, but at HEAD the three packs are `tactical`
/ `mission-control` / `field-command` (`voicePacks.ts:20`) — matching the map's REUSE row exactly.
**No franchise naming survives to carry.** The 96 Bark `.wav` files (map `:369`, REUSE, 32 per
pack) are David's own generation from `scripts/bark-generate-all.py` and are unaffected by any of
the above.

### The name, the slug and the notice

**F445 — Keeping the name does not mean keeping the slug, and reusing it would break every link to
v1.** `agent-battle-command-center` is occupied by v1. The tempting move — rename v1 to
`agent-battle-command-center-v1` and give 2.0 the freed slug — is the one GitHub explicitly warns
against: *"If you create a new repository under your account in the future, do not reuse the
original name of the renamed repository. If you do, redirects to the renamed repository will no
longer work"* (GitHub Docs, "Renaming a repository", retrieved 2026-08-27). 🚨 **Every existing
link, star reference, README badge, Docker Hub description and search result for v1 would silently
land on a brand-new empty repository.** Same page: renaming otherwise redirects issues, wikis,
stars, followers and all git operations, so **renaming v1 alone is safe — it is the reuse that is
not.** 2.0 needs a *new slug* under the same product name. No repo named `abcc` exists on the
account (checked 2026-08-27; 9 repos, 5 public).

**F446 — The succession notice already exists, names the wrong successor, is version-stale, and
carries a benchmark claim its own next paragraph half-retracts.** `README.md:3` reads *"Status:
stable at v0.11.0 (March 2026)… Active development has since moved to newer projects — most notably
**claudette**… This repo remains online as a reference implementation… Issues and PRs still
welcome."* Three defects, all cheap to fix and all actively misleading the day 2.0 exists:

1. 🚨 **It names Claudette as the successor.** 2.0 keeps the ABCC *name*, so a reader arriving at
   v1 will be pointed at the wrong repository by v1's own banner.
2. 🚨 **It is stale in two directions**: banner says v0.11.0 / March 2026, `package.json` says
   **0.13.0**, HEAD is **2026-08-06**. The `Stable v0.11.0` badge at `:9` repeats it. Same class as
   W13's F424.
3. 🚨 **`README.md:5` claims *"Both figures are single-pass runs of the 40-task C1-C9 benchmark:
   88% (35/40)… 98% (39/40)…"* and then adds *"The auto-retry pipeline's contribution is
   unmeasured."*** Session 2 measured it: **39/40 is an after-retry number; single attempt is
   36/40**, and one task failed in all five recorded runs. The badge at `:14` reads *"Ollama C1-C9
   88-98% single-pass."* **The announcement must not carry this number forward**, and the freeze is
   the natural moment to correct the README rather than leave it standing.

### What "V1 and its users" mechanically means

**F447 — Its users are three Docker `:latest` tags and a git clone; v1 was never on npm.**
`package.json:4` is **`"private": true`**, so there is no registry deprecation to perform and no
`npm deprecate` message anyone will ever see. Distribution is `docker-compose.hub.yml` pulling
**`dushidush/api:latest`, `dushidush/agents:latest`, `dushidush/ui:latest`** (badged at
`README.md:10`) plus the GitHub repo. 🚨 **`:latest` is the failure mode**: an existing user's
`docker compose pull` silently takes whatever is pushed there next, so the freeze has to include a
decision about those three tags, not just about the git repo. **The cheap, kind answer is to push a
final immutable version tag (`0.13.0`) and stop moving `:latest`** — which costs one release and
means every existing `docker compose up` keeps working. 2.0's own distribution channel is an open
question this document names but does not settle (OQ-W12-2).

**F448 — Ten open dependabot PRs on a repo about to be frozen — "frozen" and "29 bot commits and
counting" are not the same state.** dependabot has authored 29 commits and holds 10 of the 11 open
PRs; the last push to the repo, 2026-08-24, was one of them. A frozen-but-live repo keeps
generating PRs nobody will merge, which is a worse signal to a visitor than either a maintained
repo or an archived one. Archiving resolves it mechanically: GitHub Docs, "Archiving repositories"
(retrieved 2026-08-27) — *"its issues, pull requests, code, labels, milestones, projects, wiki,
releases, commits, tags, branches, reactions, code scanning alerts, comments and permissions"*
become read-only, and *"to make changes in an archived repository, you must unarchive the
repository first."* ⚠ That page does not state dependabot's behaviour explicitly; what is certain
is that the repository can no longer accept changes, which is what freezing means. **The decision
is required either way** — see the options table.

**F449 — The data worth carrying has already been carried, as files, and the "collected training
data" is dead on arrival.** `prestudy/data-assets.md` extracted everything to `prestudy/data/`
(1.9 MB, 13 files) in Phase 0, and the 40-task corpus was imported to `corpus/suites/u40/` in
session 2 (`corpus/suites/` now holds `k`, `q56`, `u100`, `u40`). What the brief means by task
history is v1's PostgreSQL, and it is **"mostly not" real**: 218 tasks over **9 days, not months**,
token and cost columns **0% populated**. The `training_datasets` table is 154 rows with
`claude_output` populated **5 times (3%)** and `claude_tokens`, `local_tokens` and `quality_score`
**0 of 154**. 🚨 **There is no labelled training set to migrate; there is a table with a name.**
So **Q10's "clean break, no migration code" costs nothing** — the migration already happened, by
hand, into files, and the live database is not worth a schema translation.

## Options compared — what happens to V1

Scored against: **honesty to a visitor**, **cost to David**, **kindness to the four contributors**,
and **does it stop the bot noise** (F448).

| option | honest? | cost | kind? | stops noise | verdict |
|---|---|---|---|---|---|
| **Archive immediately** | ✅ unambiguous | one click | ⚠ closes #57 and the fork's issue path with no warning | ✅ yes | too abrupt *today* |
| **Freeze with a corrected notice, archive later** | ✅ if the notice is fixed first | ~1 commit + 1 release | ✅ credits and a closing note land first | ⚠ not until archived | ✅ **recommended** |
| **Maintain for a period** | ⚠ implies feature work that will not happen | recurring, unbounded | neutral | ❌ no | rejected |
| **Rename v1, give 2.0 the slug** | ❌ silently breaks every existing link (F445) | low | ❌ | n/a | **rejected on evidence** |

## Recommendation

1. **New repo at a new slug — `abcc` — keeping the product name "Agent Battle Command Center."**
   Never reuse v1's slug (F445). State the relationship in both READMEs so the name collision is
   explained rather than confusing.
2. **Pay the attribution debt before anything else ships** (F440). Add the four contributors to
   v1's `README.md` Acknowledgments by name, and carry a `CREDITS.md` into 2.0 naming them and what
   they contributed. This is one commit and it is the brief's "small kindness" in full.
3. **Reimplement from scratch what the outside contributors added** — David's ruling, F443. It is
   what PORT already meant, the behaviour spec is already in the inheritance map, and the measured
   content of those lines is scaffolding. Record the ruling in 2.0's `CREDITS.md` as an
   *acknowledgement*, not a licence claim: credit is given because it is deserved, not because it
   is owed. **2.0 ships MIT OR Apache-2.0 with no inherited-code caveat.**
4. **Freeze v1 in three steps, then archive at 2.0's first tagged release.** (a) Correct the README
   banner — right successor, right version, and drop the falsified single-pass claim (F446).
   (b) Push a final `0.13.0` Docker tag and stop moving `:latest` (F447). (c) Close #57 and the
   three roadmap issues with a one-line pointer to 2.0, and close the 10 dependabot PRs with the
   same. Then archive, which makes the freeze real and ends the bot noise (F448).
5. **No migration code, and say why in the announcement** (F449) — not "we couldn't", but "the 218
   task rows carry no tokens, no cost and no labels; the corpora that *were* worth keeping are
   already extracted and are running in 2.0's harness today." Q10's clean break, defended with a
   number.
6. **Inherit v1's community stack for the human-facing half** — `CONTRIBUTING.md`,
   `CODE_OF_CONDUCT.md`, `SECURITY.md`, issue and PR templates (W13 F433 governs the engineering
   half). 🚨 v1's `CONTRIBUTING.md` has **zero** AI-authorship content — no match for
   `co-authored|ai-generated|llm|copilot|disclose` in 575 lines — so W13 recommendation 6's policy
   is an *addition* on day one, not something to copy across.
7. **Do not open 2.0's repo publicly until the notice, the credits and the final Docker tag are
   done.** The announcement is the moment every existing link gets clicked; the three defects in
   F446 are the ones a visitor hits first.

## Rejected alternatives and why

- **A `2.x` branch or a major version of v1** — rejected by David 2026-08-07 and confirmed here on
  mechanics: a Rust rewrite sharing a repo with a TypeScript/Python monorepo inherits its CI, its
  dependabot configuration and its 575-line CONTRIBUTING, none of which apply.
- **Renaming v1 to free the slug** — rejected on documented GitHub behaviour, F445. The gain is
  cosmetic; the cost is every existing inbound link.
- **Asking the four contributors for a licence grant** — considered and unnecessary after F443. It
  is a courteous act, not a required one, and David's ruling removes the dependency. If 2.0 ever
  does copy an outside-authored line verbatim, this becomes required again.
- **Keeping v1 maintained "for a period"** — rejected: the repo has had no outside PR since
  February and no feature work since. A maintenance promise that is not kept is worse than a freeze
  that is stated.
- **A trademark or name change for 2.0** — the brief offers it (*"the Battle family naming suggests
  a deliberate choice is available"*); David answered it. Not reopened.

## Effect on fun

Mostly indirect, with one direct line. **Indirect:** every hour spent on migration tooling for a
database with 0% populated cost columns is an hour not spent on the console, and the clean break is
what buys it. **Direct:** the announcement is the first thing anyone will ever read about 2.0, and
the thing that makes this project fun to *read about* is that it measures its own claims and
publishes the ones that came out badly — the 39/40 correction is a better story than the 39/40 was.
**The freeze notice is also the last impression v1 leaves.** A repo that ends by naming the four
people who showed up reads as a project that was worth showing up for; one that ends with ten
unmerged bot PRs and a stale badge reads as abandonware. Same effort, different memory.

## Open questions

- **OQ-W12-1 — when to archive.** Recommendation 4 says "at 2.0's first tagged release", which is
  months out. If 2.0 slips, v1 sits frozen-but-open longer than intended. **David's call**, and the
  cheap hedge is to archive on a date rather than on an event.
- **OQ-W12-2 — 2.0's own distribution channel.** v1 was Docker Hub; Claudette is crates.io. A Rust
  binary with a terminal console argues for crates.io plus GitHub Releases, but Postgres and the
  isometric surface argue for keeping a compose file. **Not settled here** — it belongs with W10's
  deployment shape.
- **OQ-W12-3 — the fork.** One fork exists. It is not checked here whether it carries commits that
  do not exist upstream; if it does, the freeze notice is the moment to say so.
- **OQ-W12-4 — whether to email the four contributors** rather than relying on a GitHub notice.
  Their addresses are in the commits. A one-line thank-you is defensible; a mass mail is not.

## Confidence: high

Every count is measured rather than quoted, the blame sweep is exhaustive over tracked text files
rather than sampled, and the two GitHub behaviour claims are cited to primary documentation with
retrieval dates. **What would lower it:** the live GitHub numbers drift — re-run before quoting
them anywhere public. **What is deliberately outside this confidence:** the derivative-work
question in F443 is a legal question, answered by David's ruling as a *project decision*; this
document measures the input and does not opine on the law. **What would raise it further:** a
check of the single fork's divergence (OQ-W12-3), which was not run.
