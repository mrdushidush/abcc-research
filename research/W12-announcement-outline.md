# W12 — Draft announcement outline

Second half of W12's deliverable (`RESEARCH_BRIEF.md:979`), not counted against
`research/W12-repo-strategy.md`'s ≤400-line budget. An **outline**: the beats, what backs each
one, and the rules — not a finished post. Findings cited as `F4xx` live in the W12 doc.

## Audience, measured — write for strangers, not for a following

**2 stargazers on v1, 18 on Claudette, 1 on BCF** (2026-08-27). The announcement is not serving an
existing audience; **its whole job is the first impression on people who have never heard of any of
this.** Two consequences: (a) it must stand alone with zero prior context, and (b) the four past
contributors are a *courtesy* audience of four named people, not a broadcast segment — reach them
in the v1 notice and the credits file, not in the launch post.

## Three artefacts, three audiences, three lengths

| # | artefact | audience | length | when |
|---|---|---|---|---|
| 1 | **v1 freeze notice** — replaces `README.md:3` | someone landing on v1 | ~6 lines | **first**, before 2.0 is public |
| 2 | **2.0 README opening** | someone landing on the new repo | ~10 lines | with the first public commit |
| 3 | **"Why we rewrote it in Rust" post** | strangers, HN/Reddit/Lobsters | 1,200–1,800 words | at 2.0's first tagged release |

Order matters. Artefact 1 is the only one with an existing audience, and it is the one currently
wrong in three ways (F446). Ship it first, alone, with the credits commit (F440).

## Artefact 1 — the v1 freeze notice

Six lines, replacing the current banner. It must: state the real version (**0.13.0**, last commit
2026-08-06 — not the banner's v0.11.0/March); name **ABCC 2.0 as the successor**, not Claudette;
say v1 stays online read-only as a reference implementation; **name the four contributors**; and
point at the pinned `0.13.0` Docker tag so an existing `docker compose up` keeps working (F447).
🚨 **Delete the "single-pass" benchmark sentence at `:5` and the badge at `:14` in the same
commit** — do not restate the number in corrected form here; the post is where the correction gets
its paragraph.

## Artefact 2 — the 2.0 README opening

Ten lines. What it is, what it runs on, what it costs (local, zero cloud spend by default), and one
sentence of lineage pointing back at v1. **No benchmark claim in the opening at all** until the
harness has a number that survives §16's source-plus-date rule.

## Artefact 3 — "Why we rewrote it in Rust"

The brief calls this *"a genuinely good story and worth writing well rather than as an
afterthought."* It is. The story is **not** "Rust is faster." Eight beats:

1. **The toy.** v1 was built to learn local AI, with fun as the only goal and architecture
   deliberately not cared about. Say that in David's own words — it is disarming, it is true, and
   it makes the rest credible. *Source: lineage.*
2. **The serious one.** Claudette: precision, correctness, usability — and **the fun removed
   completely.** Shipped, on crates.io, 471 commits.
3. **The observation that starts the project.** The two halves never existed in one tool. One was
   watchable and wrong; the other was right and silent.
4. **The honest benchmark section — the beat that earns the post.** v1's README advertised
   *98% (39/40) single-pass*. Re-measured: **39/40 is after-retry; 36/40 on a single attempt**, and
   one task failed in all five recorded runs. Then the sharper one: re-run against the new base
   agent, **the artifact reached the graded directory in about half of 80 attempts (40 of 80,
   ±11 points at 95%), and where it did, 38 of 40 passed** — because `write_file` is path-sandboxed
   and `bash` is not. **Publish the defect, not the pass rate.** ⚠ The doc's own precision rule:
   say "about half", never "exactly half". *Source: `research/W8-u40-floor-check.md:10,252`.*
5. **What the rewrite is actually buying**, one paragraph each, each with a measured number from
   Phase 1 — not adjectives. Candidates: the prefix-cache result, schema-constrained decoding,
   worktree isolation at 0.25 s, the sixel console holding 25–29 FPS.
6. **What we are *not* claiming.** The security work found the family's own guards do not bound
   what they look like they bound (W7). Say so. A rewrite announcement that lists only wins reads
   as marketing; this project's whole voice is that it measures and publishes either way.
7. **What happens to v1 and to you** — frozen, read-only, pinned Docker tag, no migration tooling
   and **why**: 218 task rows over nine days with token, cost and label columns empty (F449).
8. **Credits and the invitation.** The four contributors by name. Then the one thing a stranger can
   do next.

## Honesty rules for every artefact

- **Every model, price, benchmark or tool claim carries a source and a retrieval date** (§16). No
  exceptions in a public post; that is where the claims escape review.
- **Banned strings**, all falsified in this study: *"98% single-pass"*, *"39/40 single-pass"*,
  *"prompts \[y/N\] every time"* (W7, `README.md:104`), and any pass rate stated without the
  placement caveat from beat 4.
- **No franchise names.** v1's packs are `tactical` / `mission-control` / `field-command` (F444);
  the commit titles that mention StarCraft and Age of Empires are history, not copy.
- **Do not write the small community as a failure** (F438). Four people sent thirteen commits and
  twenty-one good-first-issues were closed. The finding is that the work is *done*.
- **No dates for 2.0 features that do not exist.** The self-hosting milestone (W13) is the only
  forward-looking claim worth making, and it is stated as a *test*, not a date.

## What to cut when it runs long

Beat 5 shrinks to two numbers. Beat 3 shrinks to two sentences. **Beats 1, 4, 6 and 7 do not
shrink** — they are the post. A version of this story without the benchmark correction is a
different, worse post that anyone could have written.

## Open

- **Where it is published.** No blog exists. GitHub Release notes plus the README is the zero-cost
  default; a post needs somewhere to live. **David's call** — this is OQ-W12-2's sibling.
- **Whether beat 4 names the champion model and its quantisation.** It is the honest thing and it
  invites "you tested the wrong model" replies. Recommend naming it, with the load command.
