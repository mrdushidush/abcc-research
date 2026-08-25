# W6 item 7 — drafted prose, not yet in `research/W6-verification.md`

Written 2026-08-25 while the `edge`, `check` and `docgate` runs were still going. F336-F338 are
already in the workstream document and committed; **everything below is a draft awaiting the
numbers from those runs**, and F339-F343 (the edge arm, `check.py`, docgate's three model arms)
are not written at all yet. Re-derive every number with `python analyse.py` before pasting any of
this into the document — the drafts below are exact for the probes that had finished
(`citations.py`, `taxonomy.py`, `v1_review.mjs`, `bcf-doc/`, docgate's `free` arm) and were written
against partial data for anything from `judge.py` or `docgate.py`'s model arms.


### 🚨 F344 — the free rung for prose checks addresses and nothing else: 1,861 of them across four documentation corpora, and exactly one points past the end of the file it names

`citations.py` is the documentation analogue of item 4's structural check — the thing a machine can
own without reading. Three kinds of claim in a research document are addresses rather than
assertions: a finding number must be defined somewhere, an open-question id must be defined
somewhere, and a `file:line` citation must name a file that exists and is at least that long. A
fenced block introduced by a citation is a fourth and stronger kind: a *quotation*, which can be
compared with the file line for line.

Run over this repository's **44 authored documents, 1,695,867 bytes** — the workstream documents,
the harness crates' READMEs, the prestudy dossiers, the corpus SPEC and the brief — resolving
against this repository and the three donor checkouts:

| | count |
|---|---:|
| findings defined | 328, by 332 headings |
| finding references | **2,453**, over 339 distinct numbers |
| dangling finding references | **11 numbers, 27 references** — 8 numbers and 23 references are one story (F345), and 3 are this section citing findings written below it |
| open questions defined / referenced | 92 / 92, over 263 references |
| dangling open questions | **0** |
| `file:line` citations, unique | **740** |
| — resolve, and in range | 388 (52%) |
| — ambiguous under any mechanical rule | 341 (46%) |
| — name no file in the resolution set | 10 (1%) |
| — **point past the end of the file** | **1** |
| citations that quote the code they cite | 30 |
| — quotation matches the file line for line | 7 |
| — differs | 7, and all 7 are paraphrase or an introducing citation that is not the block's source |

And the same address check on each donor's own documentation, resolved against its own tree:

| corpus | head | docs | citations | ok | no such file | ambiguous | past EOF |
|---|---|---:|---:|---:|---:|---:|---:|
| v1 | `d5528ea` | 65 | 752 | 636 | 24 | 92 | **0** |
| BCF | `d6c1601` | 12 | **0** | — | — | — | — |
| Claudette | `af3f804` | 163 | 369 | 51 | 39 | 279 | **0** |
| this repo | `05dfd91` | 44 | 740 | 388 | 10 | 341 | **1** |

**1,861 unique addresses across four corpora and one provable stale citation** — W5's F100 cites
`crates/claudette/src/tui_events.rs:75-88` and the file ends at line 87. (The quoted enum is really
at 73–87, so even that one is an address off by one around content that is right.) BCF's twelve
documents cite their own code by line **zero** times, which is its own kind of answer.

Three things this measurement is worth more for than its yield.

**The checker's number is a measurement of the checker.** It reported **40** dangling finding
references, then 21, then 12, then 9, as it learned that this corpus defines a finding in **five**
different ways — `### F158 —`, `### 🚨 F158 —`, `### F35.`, `## 4. F54 —`, and a bold paragraph
`**F41.**`. Open questions have two conventions and a status marker. Every one of the first 31
"errors" was the rule, not the corpus. The same happened twice more: attributing a fenced block to
"the citation within three lines above" produced 12 documentation errors of which all 12 were the
rule, and resolving a bare `Cargo.toml:57` to a workspace's 23-line root manifest produced five
"past EOF" citations in the successor's documentation that were the rule again. **Every loosening
of the attribution manufactured defects, and no tightening ever cost a real one.**

**What is checkable is 52% of what is written, at best.** A bare basename — `orchestrator.py:43`,
which is how most of this corpus cites — is not an address until a resolution rule is fixed, and
46% of the citations here have no unambiguous target across four trees. The convention that would
make the rung meaningful is one line long (*cite a repository-relative path*), and its value is
prospective: it does not find today's errors, it makes tomorrow's findable.

**And the rung is silent about every claim.** The documentation errors this project has actually
found, it found by hand, and the two that were cross-reference errors — F193 and F88, each cited as
saying something it does not say — pointed at findings that **exist**. Existence-checking would have
passed both. That is the honest bound on this instrument: it verifies
that an address resolves, never that the sentence around it is true.

### 🚨 F345 — eight finding numbers are cited 23 times across six documents in this repository and defined in none of them

The one residue the corrected checker leaves is a real defect and it is a single story. **F22
through F29** are referenced 23 times, across six documents — `harness/crates/w8-run/README.md`,
`harness/crates/w8-corpus/README.md`, `harness/crates/w8-import-q56/README.md`,
`harness/crates/hw-probe/README.md`, `research/W8-q56-import.md` and, as of item 5,
`research/W6-verification.md` itself — in load-bearing sentences —
*"third time CRLF has produced a difference that looks like a finding and is not (cf. F21, F22)"*,
*"76 of the 90 tasks ship an empty fixture (F29)"*, *"it prints an advert instead of running code
(F27)"*. **None of the eight is defined anywhere in the repository**, under any of the five
conventions, and `git log --diff-filter=D -- '*.md'` shows no document was ever deleted.

They exist in the private memory directory. `memory/abcc-2-w8-state.md` says of
`harness/crates/w8-import/`: *"Its README is the design record; findings F22-F27 below"* — and
`harness/crates/w8-import/README.md` contains **six headings and no finding numbers at all**. The
memory file then defines F28 and F29 itself, under a heading that names two findings at once
(`### F28-F29, both found by building the loader`), which is a sixth convention and outside the
repository.

This is worth a finding of its own because of what it is evidence for. **The repository's
cross-reference integrity had never been checked**, in 91 commits and 1.7 MB of prose, by anyone;
the check costs milliseconds; and it found a defect that only a mechanical pass would ever find,
because a human reading any one of those six documents sees a citation that looks exactly like the
2,426 that resolve. It is the documentation-shaped version of item 4's cheapest rung — free,
narrow, and worth running because it is free.

### 🚨 F346 — the family has no word for a documentation deliverable, and the one artifact type that is pure prose is the one type its reviewer is told to skip

Executed, not read. `bcf-doc/` takes a path dependency on the pinned BCF checkout and calls
`verifier::verify_project` on a three-file documentation project — the K suite's real status
lifecycle spec, a README and a CHANGELOG.

BCF's per-file mapping (`verifier.rs:73-81`) is `py | ts | js | rs | go | cpp` and `_ => continue`,
so no file is scored, `file_reports` is empty, and `avg_score` falls to the `5.0` literal at
`verifier.rs:96` — which W11 item 3 identified as the family's `Uncertain` spelled as a passing-ish
number (F258). Measured:

| | files scored | avg | final with a **perfect** critique | lowest gate |
|---|---:|---:|---:|---:|
| `language = "markdown"` | 0 | 5.00 | **7.00** | 8.00 |
| `language = "python"` (BCF's default, F315) | 0 | 5.00 | **7.00** | 8.00 |

**A documentation deliverable cannot pass BCF's gate at any complexity, however good it is**, and
it cannot fail it for any reason to do with its content. This is F313's mechanism arriving at the
artifact the brief names. One incidental measurement is worth recording: under the default
`python` language the run printed `Creating venv... Installing dependencies in venv... pytest: no
tests found` — **BCF builds a Python virtualenv and runs pytest against a directory of markdown.**

v1 is more explicit about it. Its task vocabulary is
`TaskType = 'code' | 'test' | 'review' | 'debug' | 'refactor'`
(`packages/shared/src/index.ts:53`), and the route accepts a sixth, `'decomposition'`, that the
type does not contain (`packages/api/src/routes/tasks.ts:13`). **There is no documentation task
type**, so a documentation deliverable is a `code` task and goes to the same validation command
item 5 measured running 1 of 13 real commands (F312).

And the one type in the vocabulary that is unambiguously prose with no test — `review` — is on
`SKIP_REVIEW_TYPES` (`codeReviewService.ts:54`), alongside `decomposition` and `debug`. **The
family's only reviewer is explicitly told not to look at review output.**

Two more facts fell out of running the donor's own decision function over the donor's own test
inputs (`v1_review.mjs`, ported byte-for-byte from `d5528ea`):

- **Both unit tests for the skip list pass for the wrong reason.**
  `codeReviewService.test.ts:34-48` builds `{ type: 'decomposition', status: 'completed' }` and
  asserts `shouldReview === false`. `getReviewDecision` reads `task.taskType`, which is
  `undefined`, so the skip never fires; the returned reason is
  `"No review needed (Ollama: 1/5, All: 1/10)"` — the *scheduler* declining, not the skip list. Run
  with the field the code actually reads, the reason becomes `"Skipping decomposition task type"`.
  **The skip list has never been exercised by its own tests.**
- **`refactor` and `debug` score 0 in the router's complexity switch** (`taskRouter.ts:200-213`,
  which has cases for `code`, `test`, `review` and `decomposition` only), so the two task types
  most likely to be a rewrite with no new behaviour are the two the router treats as the simplest.

### 🚨 F347 — v1's frontier review tier fires zero times in thirty tasks in exactly the regime the project was built for, because the cheaper tier's schedule divides the expensive one's

v1's graduated review is two schedules over two counters (`codeReviewService.ts:139-155`): Haiku
when `isOllamaTask && ollamaTaskCounter % 5 == 0`, Opus when
`complexity > 5 && allTaskCounter % 10 == 0`. The Haiku branch returns first. When every task is
executed locally the two counters are equal — and **every multiple of 10 is a multiple of 5**, so
the Opus branch is unreachable.

Run over four task streams, complexity 9 throughout, one service instance each:

| stream | haiku | opus | unreviewed |
|---|---:|---:|---:|
| 30 tasks, all `ollama` | 6 | **0** | 24 |
| 30 tasks, alternating sonnet / ollama | 3 | **0** | 27 |
| 30 tasks, alternating ollama / sonnet — *the same stream, other phase* | 3 | 3 | 24 |
| 30 tasks, all sonnet | 0 | 3 | 27 |

**All-local is the premise of the entire project**, and it is the row where the expensive reviewer
never runs. Whether it runs at all is decided by the *phase* of the model stream, which is not a
property anyone chose. This is F270 and F271 with a mechanism attached: the tier table is not a
policy, it is an interference pattern between two counters.

`isOllamaTask` is `executedByModel === 'ollama' || !executedByModel`, so a task with no recorded
model counts as local — the provenance F271 called invented. And the complexity default is a falsy
coalesce, `task.complexity || 5`, against a strict `complexity > 5`: measured on the Opus tick with
a non-local model, complexity `undefined`, `0` and `5` all decline, and `5.5` and `9` review. **A
task whose complexity was never recorded, or was honestly recorded as zero, can never receive the
frontier review** — the same `||` defect W11 item 2 found destroying a reviewer's zero, in the
other direction.

### 🚨 F348 — the successor refuses to fold a timeout into "clean" and folds "there is no checker for this artifact" into it three lines later

Claudette's post-edit check is the most careful gate in the family, and its enum says so:

```rust
/// A timeout is deliberately NOT folded into "clean". A check that never
/// finished has verified nothing, and reporting silence there is exactly how a
/// corrupt file slips through unnoticed (roast CHECK-01).
pub(crate) enum CheckOutcome { Skipped, Passed, Failed(String), TimedOut(u64) }
```

`Skipped` covers three different situations (`post_edit_check.rs:289-299`): the feature is off, the
process is offline, and **no check command matched this file type**. `builtin_cmd` maps `.rs`,
`.py`, `.go`, `.js`, `.mjs` and `.cjs`; everything else returns `None`, and the donor's own test
asserts it for `["ts", "tsx", "md", "toml"]` and for an extensionless path
(`post_edit_check.rs:483-491`).

The single call site (`runtime/conversation.rs:753-754`) then writes
`CheckOutcome::Skipped | CheckOutcome::Passed => None`.

So **editing a document produces exactly the observable result of editing a Rust file that
compiles**: nothing is appended, and the model that just wrote the document is told the same thing
either way. The type carries the distinction the design argued for and the consumer discards it —
which is item 1's diagnosis restated for the unrunnable artifact, and the reason item 5's
`Option<bool>` ruling (F317) is necessary and not sufficient. What 2.0 needs is not a third Boolean
but a *reason*: `Uncertain(NoCheckerFor(".md"))` is a different fact from `Uncertain(FeatureOff)`,
and only one of them should ever reach an operator.


## Options compared

| For an artifact with no test | What it costs | What it buys | Evidence |
|---|---|---|---|
| **Nothing** — accept the artifact | free | v1's answer for documentation (no task type) and for review output (`SKIP_REVIEW_TYPES`); Claudette's answer for every file its table does not map | F346, F348 |
| **An address-level rung** — do the citations resolve, do the symbols exist | milliseconds, no toolchain, no model | catches what is an *address*: 1 of 7 planted document defects, 1 stale citation in 1,861, 8 dangling finding numbers. **Zero false positives once the attribution rule is tight** | F344, F345, F341 |
| **A model verdict** — the shipped `pass`/`fail` field | one call, ~35 s | 3 of 22 wrong answers, 1 false fail in 33, 2 empty payloads in 56. Every catch is a case the ticket's own words decide | F338 |
| **A model report, verdict discarded** — read the defect list, not the call | the same call | the model *names* the defect on artifacts it then passes; the report and the binary disagree in both directions | F338, F339, F341 |
| **A model report shaped as concrete cases** — `call → expected → actual` | the same call, a different schema | (edge arm) | F339 |
| **Running the reviewer's cases** — execute each named case on the pre-image and the post-image | one process per case, seconds | (check arm) — and it needs no oracle, because item 6's snapshot **is** the pre-image | F340 |
| **A second model** | a 26.3 s swap plus 4.6× decode | measured in W11 item 4 and rejected: a better reader, an unusable component | F284 |

## Recommendation

**1 — A model verdict is a report, never a gate.** Measured on the population where nothing else
fires, the shipped binary catches 3 of 22 wrong answers and false-fails 1 of 33 right ones. That is
not a weak gate, it is not a gate: a wrong answer walks past it 86% of the time, and the one time it
fires on a correct answer it does so with an empty defect list and a rationale that says the code is
fine. 2.0's `Verdict::call` stays advisory and never binds a merge.

**2 — A verdict that contradicts its own report is `Uncertain`, in both directions.** On
documentation the same call *finds the defect and then approves the artifact* — the wrong constant,
the non-existent function and the reversed billing rule are all named at `high` severity under
`call: "pass"`. On code the two agree, so simply deriving the gate from the defect list buys nothing
there (3 of 22, exactly the binary). The rule that is right on both populations is a consistency
check the type system can carry: **a `fail` with an empty defect list is not a verdict, and a `pass`
carrying a `high` defect is not a verdict either.** Both are `Uncertain`, both stop the gate rather
than deciding it, and both are free. The single false-fail in the whole code arm and five of the
seven planted document defects are caught by that one rule and by nothing else.

**3 — Demand a concrete case, because the schema is the cheapest intervention there is.** W11 item 4
found the deciding axis is what the reviewer is *shown* (F280). This item adds the other half: what
it is *asked to emit*. Same model, same context, same temperature — a schema whose leaf is
`{why, call, expected, actual}` rather than a paragraph changes what comes back.

**4 — A review finding is verified by running it, and item 6 already built the machine.** A finding
that names an input is falsifiable: run it on the snapshot commit (item 6's `read-tree` /
`write-tree` / `commit-tree` pre-image, 0.16 s) and on the tree as it stands. Differ → the finding is
real and the reviewer earned its keep. Same → the reviewer is wrong, and the operator should never
see it. Will not run → it was never a finding. **This is the answer to "verifying review output":
you do not verify the prose, you require the prose to carry something you can execute.** It closes
F277's gap — a generated criterion with no positive control — for free, because the pre-image is a
control.

**5 — Run the address rung on documentation because it is free, and never call it verification.**
It found 1 stale citation in 1,861 addresses and 8 dangling finding numbers in 2,453 references. It
is silent on every claim: 6 of 7 planted document defects, including a reversed billing rule and a
wrong return type, cite symbols that resolve perfectly.

**6 — Ship one citation convention, and its value is prospective.** 46% of this corpus's citations
are a bare basename with no unambiguous target. `path/relative/to/repo.rs:12-18` is one line of
convention and it turns 341 unresolvable addresses into checkable ones. Do the same for finding
ids: one definition form, checked in CI.

**7 — Quote what you cite.** 30 of 740 citations here are followed by the code they name, and a
quotation can be checked against the file line for line while an address cannot. A document that
quotes is a document a machine can partly verify.

**8 — `Uncertain` needs a reason, not a Boolean.** Claudette's `CheckOutcome::Skipped` folds "the
feature is off", "we are offline" and "there is no checker for a `.md` file" into one variant, and
its single call site then folds that into `Passed`. 2.0's `Uncertain(why)` carries the why, and the
console shows *no checker for this artifact* as a different line from *check disabled*.

**9 — Review output is reviewed.** v1 puts `review` on `SKIP_REVIEW_TYPES`. In 2.0 the artifact with
no test is exactly the artifact that most needs a second reading, and the second reading is cheap
because it is the same model in a fresh call reading the diff (W11 F280).
