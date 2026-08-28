# Acceptance sweep A — source URL and retrieval date on every external claim

**Status: COMPLETE — 2026-08-28**, session 11 of the 14-session landing budget. Closes §16's
second Phase 1 criterion. **Findings F475–F479**; next free number is **F480**. Seven files
changed, **+46 lines across 23,252**; five were already complete and ten have no external claim
to cite. This file is the record, not a workstream doc.

## What §16 asks, and the ruling that made it finite

§16: *"Every model, crate, tool, price and benchmark claim carries a source URL and retrieval
date."* Read literally against 22 files that is a line-by-line re-reading of the whole corpus.
The pre-scout ([[abcc-2-w10-state]]) already said it was narrower than that, and it was right —
but a URL count is not a claim count, so the scope had to be settled by a rule, not by a grep:

▶ **A claim needs a URL when its truth lives on someone else's server. A claim needs a date
always.**

| claim class | what carries it |
|---|---|
| **External** — model card, crate registry, repo metadata, upstream docs, published benchmark, price | **URL + retrieval date** |
| **Local measurement** — any number produced on this box | **artifact path** (`runs/…`, `research/spikes/…`) **+ measurement date** |
| **Donor code** | **`file:line`** at a stated commit |

The corollary did most of the work: **a tool that is *invoked* is not *cited*.** W6 names `pytest`
69 times, `ruff` 25 and `mypy` 20, and it runs all three on this host — those are measurements of
what is installed here, and a vendor URL would be the wrong citation, not a missing one. The same
distinction is why W3's crate table needs `crates.io` (it quotes download counts and release
dates that live there) while W6's toolchain line needs only a date and a path.

## The audit — 22 files, by what kind of evidence each is built on

| file | lines | external claims | before | after |
|---|---|---|---|---|
| `W9-prior-art.md` | 509 | **the whole doc** — 24 repos, 1 blog, 1 upstream README | dates ✅, **0 URLs** | ✅ URL rule + 3 links |
| `W1-models.md` | 745 | model cards, vendor benchmarks, **3 API prices** | blanket date ✅, 8 URLs | ✅ +5 URLs, price re-checked |
| `W3-orchestration.md` | 3,407 | 3 crate tables, SQLite docs, Restate SDK | dates ✅, **0 URLs** | ✅ 9 URLs / rules |
| `W2-serving.md` | 331 | 3 — llama.cpp server, `llama-cpp-2`, OpenAI dialect | blanket date ✅, **0 URLs** | ✅ 3 URLs, all re-verified |
| `W12-repo-strategy.md` | 352 | 2 GitHub Docs pages, cited by **title only** | dates ✅, **0 URLs** | ✅ 2 URLs, quotes re-verified |
| `W12-announcement-outline.md` | 98 | 1 — Claudette on crates.io | none | ✅ 1 URL + version |
| `W6-verification.md` | 4,400 | **none** — every number local or donor | **no dates at all** | ✅ 2 dates + status note |
| `W5-command-center.md` | 2,448 | ~45, the most in the corpus | ✅ complete | ✅ unchanged |
| `W7-security.md` | 945 | crate table + 3 upstream docs | ✅ complete | ✅ unchanged |
| `W13-codev.md` | 413 | 2 papers, 1 vendor doc, 1 trade article | ✅ complete | ✅ unchanged |
| `W10-fleet.md` | 395 | 2 — Tailscale ACLs, llama.cpp RPC README | ✅ complete | ✅ unchanged |
| `W11-stages.md` | 4,316 | **none** | n/a | ✅ nothing to do |
| `W4-routing.md` | 2,416 | **none** | n/a | ✅ nothing to do |
| `W8-*.md` (6 files) | 2,119 | **none** | n/a | ✅ nothing to do |
| `W1-batch2-results.md` | 140 | **none** | n/a | ✅ nothing to do |
| `W10-mode-matrix.md` | 110 | **none** | n/a | ✅ nothing to do |
| `W13-claude-md-skeleton.md` | 108 | 1, already linked | ✅ complete | ✅ unchanged |

---

## Findings

### F475 — 🚨 a price rotted inside twelve days, and the retrieval date is the only reason anyone saw it

`W1-models.md:463-465` quotes three Claude API prices at retrieval date **2026-08-16**. Re-checked
2026-08-28 at <https://platform.claude.com/docs/en/about-claude/pricing> and
<https://platform.claude.com/docs/en/about-claude/models/overview>:

| model | W1, 2026-08-16 | standing, 2026-08-28 |
|---|---|---|
| Claude Opus 5 | $5 / $25, 1M | ✅ unchanged |
| **Claude Sonnet 5** | **$3 / $15, with a $2/$10 intro "through 2026-08-31"** | 🚨 **$2 / $10 flat** |
| Claude Haiku 4.5 | $1 / $5, 200K | ✅ unchanged |

The intro rate did not expire, it became the rate — so the row was wrong in its *framing*, not
just its number, and the framing was the part a reader would have acted on. **Twelve days.** Every
other claim class in this corpus survived its retrieval date intact; the price did not. ▶ **Prices
are the only claim class that needs a re-check at the freeze, and W12's announcement outline
already carries the rule for itself (`W12-announcement-outline.md:74`).**

### F476 — citation debt does not track line count, it tracks where the evidence came from

The four files with **zero** URLs before the sweep were W6 (4,393 lines), W11 (4,316), W4 (2,416)
and W2 (319) — **11,444 lines pre-sweep, and three of them make no external claim at all.** The
file with the *worst* URL count for its content was W9, **0 URLs in 500 lines**, and W9 is the one
file that is almost entirely external claim. **The two rankings are unrelated.** The pre-scout's
per-doc URL counts were accurate as counts and misleading as a work estimate: they nominated W6 (a
doc needing no URLs) alongside W9 (a doc needing 26), and ranked W11 and W4 — which needed nothing
— above W12, which needed two. ▶ **The instrument for "is this doc cited" is *what kind of
evidence is it built on*, never a URL count.** That is
[[verify-claims-against-code-not-docs]] item 44 again: the grep was local, the number correct, the
inference false.

### F477 — the compliant docs use two mechanisms, and the cheap one scales

Five files passed untouched — W5, W7, `W13-codev`, `W13-claude-md-skeleton` and W10 — and they
split by citation *density*, not by care. The two dense ones use a **section-level blanket**: W5's
*"All claims retrieved 2026-08-18"* (`:1789`) and *"Retrieved 2026-08-18"* (`:1577`), W7's *"All
retrieved 2026-08-27:"* sitting immediately above its crate table (`:330`). The three sparse ones
date each citation in its own parentheses. **W5 carries 45 URLs against 20 date statements and is
complete** — a naive ratio reads that as 25 uncited claims. ▶ **Blanket where a section shares one
date; parentheses where citations are sparse.** Sweep A adopted the blanket for W9's 24
repositories, which is why that fix cost five lines instead of twenty-eight.

### F478 — nothing in the corpus turned out to be uncitable

Going in, the expected failure mode was a claim whose source was lost — a number quoted from a page
nobody recorded. **There were none.** Three reasons, and they are worth keeping:

- **W9's 24 projects are `org/repo` strings**, so the citation is a *construction rule*
  (`https://github.com/<org>/<repo>`, metadata from `https://api.github.com/repos/<org>/<repo>`),
  not 24 lookups. Same for W3's crate rows against `https://crates.io/crates/<name>`.
- **W12 named its two sources by title** — *"Renaming a repository"*, *"Archiving repositories"* —
  which was enough to find both pages and confirm that the quoted sentences are verbatim.
- **The one genuinely loose source was recovered.** `W9:181-186` attributed F454's price and
  benchmark row to *"NVIDIA's developer blog (2026-08-11)"* with no link; it is
  <https://developer.nvidia.com/blog/route-ai-agent-workloads-across-models-with-nvidia-nemo-switchyard/>,
  and the escalation-router row's three figures — **74% cost reduction, ~6-point accuracy
  tradeoff, 7% of calls to frontier** — re-verify exactly. ⚠ The second row (Cognition
  FrontierCode, 50.6% at $3.11) was **not** re-verified and is still on the 2026-08-27 read.

### F479 — 🚨 GitHub's `license.spdx_id` reports ONE licence for a dual-licensed repository

W9's licence filter is the first gate on every candidate and it runs on a single API field. Checked
against the one candidate that filter actually admitted, `utilityai/llama-cpp-rs`:

```
api.github.com/repos/utilityai/llama-cpp-rs  →  "spdx_id": "Apache-2.0"    (stars 639, pushed 2026-08-28)
api.github.com/repos/utilityai/llama-cpp-rs/contents/  →  LICENSE-APACHE  and  LICENSE-MIT
```

The repo is **MIT OR Apache-2.0** — exactly 2.0's own licence (W12) — and the API reported half of
it. W9's stars and push date re-verify to the digit, so this is not a stale read; it is the field
answering a narrower question than the one asked. **The error direction is conservative** — it
understates permissiveness, so no candidate was wrongly *admitted*, and the two `NOASSERTION`
exclusions (`zavora-ai/adk-rust`, `AgentsMesh/AgentsMesh`) stand. `W9-prior-art.md:386` and `:446`
are corrected. ⚠ **Only this one repository's LICENSE files were read**; the other 23 rows are
still single-field reads, and any of them may also be dual-licensed in 2.0's favour. ▶ **When a
licence gates a decision, read the repo's LICENSE files, not `license.spdx_id`.**

---

## What sweep A did not do

- **It did not re-verify the corpus.** Re-checks were run only where adding the URL required
  opening the page anyway: W1's three prices, W2's three sources, W9's llama.cpp README and NVIDIA
  blog, W12's two GitHub Docs pages, `utilityai/llama-cpp-rs`, and the three model cards added to
  W1. Everything else keeps its original retrieval date, which is the honest state.
- **It did not touch W9's `seen` column.** *"Only one project in this entire scan was read as
  code"* is still true; a URL is not a reading.
- **It found no second price claim** anywhere in the corpus. `W1-batch2-results.md:131`'s *"the
  price is unchanged"* is wall-clock (4.9×), not dollars.

## Effect on the line budgets

Six of the seven changed files have no line budget. **W9 does: ≤ 500, and it now stands at 509
(+9, 1.8% over).** The overrun is nine lines of citation apparatus — a five-line construction rule
plus three link insertions plus one rewrap — added *after* the doc closed at 500 exactly, and none
of it is depth. W7's budget was amended once for the same reason (a §16 acceptance item), at +5%.
▶ **Flagged for David, not decided here.** The alternative was a companion `W9-sources.md`, which
keeps the number and costs a reader one hop for every one of 24 repositories.

**Remaining for Phase 1: acceptance sweep B, then `SUMMARY.md`.** Both are pre-scouted in
[[abcc-2-w10-state]] — sweep B is a JOIN over `runs/hw-probe/`'s 12 labelled configurations, not a
probe build, and nothing is to be re-run before asking David.
