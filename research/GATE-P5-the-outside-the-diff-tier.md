# GATE P5 — the outside-the-diff tier, built

**Session of 2026-09-04.** `GATE-P4` ended with a verdict and a request. The verdict was *do not
ship the scope sentence*: over 363 calls it moved fewer trees than asking the identical question
twice. The request was David's — **"don't rule yet; build the population that could actually answer
it: trees whose defect lies outside the diff."**

This is that population. **It is a build record, not a result.** Nothing here was measured with a
model; every number below comes from the deterministic gate or from parsing the corpus.

**`corpus/suites/od` — 24 tasks, 387 files, 4,783 lines of authored python and 1,660 of `verify.sh`,
all 24 gate-sound on `SPEC.md` §9's three points, measured rather than asserted.**

---

## 1. Why it had to be authored

Measured on disk, all four suites: **only two tasks in the entire corpus have a multi-file
`refsol/`** — `k/finish_the_cancelled_status` and `q56/Q34`. A single-file task cannot host a defect
outside its own diff, so the tier could not be assembled from what was there.

Authoring it is precedented rather than a breach of *rewrite, do not port*: the K suite and all
three of its shams are this project's own `feat(K)` commits, and `SPEC.md` §2 reserved
`suites/<new>` for exactly this. The donor corpora are untouched.

## 2. The design rule, and the third of the suite that can refuse it

> **The sham's defect must be UNREACHABLE FROM THE PATCH ALONE and REACHABLE FROM THE PATCH PLUS
> THE TICKET.**

A reviewer is shown a title, a prompt, a patch and the rung measurements — never the tree
(`crates/abcc-gate/tests/corpus_review.rs`). So a task here is built around those four and nothing
else. If the ticket does not state or imply the extent, no instruction can recover it. If the diff
already shows the defect, the scope question is not what answered.

| `shape` | the sham patches | n | what it asks |
|---|---|---|---|
| `outside_cover` | a **strict subset** of `refsol`'s files | 8 | does the reviewer see what the change does not reach? |
| `outside_file` | a **different file** from `refsol` | 8 | does it see that the change is at the symptom? |
| **`inside`** | **the same file**, scope complete, logic wrong | 8 | 🚨 **the control** |

🚨 **The `inside` third is the falsifier, not filler.** Its shams have no coverage gap at all: same
file, same function, every consumer reached. A switch that reports a scope problem there is
reporting one that does not exist, and a switch that fires there as often as on the other two thirds
is producing volume rather than scope. GATE-P4 already has one reading to check it against —
`round_at_the_line_not_the_total`, the one K sham of this shape, went 0 under treatment and 0 across
both control samples.

## 3. The second axis, and the confound in it

`scope_statement` says how the ticket carries the extent: **`explicit`** (states it in words),
**`implied`** (points at a rule that does), **`single_instance`** (names one case of a general
defect). Without it, a ceiling — a ticket so explicit that the control finds the gap unaided — reads
as an effect size, and a floor reads as its absence.

| | explicit | implied | single_instance |
|---|---|---|---|
| `outside_cover` | 3 | 3 | 2 |
| `outside_file` | 2 | 4 | 2 |
| `inside` | 1 | 1 | **6** |

⚠ **F574 — the two axes are NOT orthogonal in this population, and the write-up of any probe over it
has to say so.** `inside` is 6 of 8 `single_instance`, because a wrong local fix is what a ticket
naming one case produces; that is the honest shape of the defect class and it is also a confound.
A rate quoted per shape is partly a rate per scope statement. **Report the cell, not the row.**

## 4. 🚨 F569 — a sham must be GREEN, so the behaviour it changes cannot be under test

The tier's whole point is to put the Judge where it is the only opinion there is. If a sham tree
fails the visible tests the ladder refuses it, the reviewer is shown a red rung, and the tree stops
measuring what it was built for. `harness/scripts/gate-task.sh` therefore **refuses** a task whose
sham fails `python -m pytest -q`.

That has a consequence which looks like a trick the fourth time you meet it and is structural: **a
sham that relaxes an integrity check breaks any visible test of that check raising.** So each
fixture's suite covers its checks on inputs they accept and not on inputs they refuse — which is how
most real suites are written, and is why these defects survive in real repositories. Every task's
`caveats` names the absence it leans on. It was found by hitting it three times, in
`the_import_creates_a_second_customer`, `the_retry_budget_never_resets` and
`the_export_drops_the_last_page`, and re-shaping the sham each time rather than deleting the test.

## 5. What the deterministic gate says — and F570, why that is the point

Full run, all three suites, no model call:

| population | trees | green | red | unverified |
|---|---|---|---|---|
| `correct` | 83 | 72 | **0** | 11 |
| `wrong` | 83 | 59 | 13 | 11 |
| `sham` | 27 | **27** | 0 | 0 |

`PLAN.md` §3's clause holds: **zero false fails on a correct-tree population**, now 83 tasks wide.

🚨 **F570 — every OD tree is green: 24 correct, 24 wrong, 24 sham.** On this tier the deterministic
ladder answers *nothing*, on 72 of 72, against 13 refusals in the other suites' wrong population.
The OD third therefore contributes nothing to the false-fail count and everything to the Judge's —
which is the tier working as designed and is also a warning: **a probe over OD alone is a probe with
no deterministic signal in it at all.**

Per-task shape of the overlays: 16 tasks have a one-file `refsol` (every `outside_file` and every
`inside`), 8 have 3–5 files (`outside_cover`), and **every sham is one file** — which is what makes
the file-count difference visible in a diff without being the whole of the tell.

## 6. Three defects found in the instruments, not in the corpus

* 🚨 **F571 — eight of the 24 generated `task.toml` files carried a raw carriage return and would
  not parse.** The sanitiser stripped backslashes and double quotes from a `detail` string and not
  `\r`; `tr '\n' ' '` in a `verify.sh` does not touch a CR; nothing prints one. Exactly the eight
  tasks whose fixture *crashes* were affected, because only those details quote a traceback. Found
  by parsing all 24 with `tomllib`, which is a thing nobody had done — a generated record that
  nothing parses is not a record. [[verify-claims-against-code-not-docs]]
* 🚨 **F572 — `ABCC_CORPUS_ONLY` could only ever select the `wrong` tree of a task.** It matched
  `slug.ends_with(name)` and the slugs are `q56-Q01`, `q56-Q01-correct`, `q56-Q01-sham`. The two
  populations a probe most needs were unreachable through the only switch that reaches them, and it
  failed by returning a **smaller set**, which is indistinguishable from a small corpus. Fixed, with
  a test that asserts 3 dossiers where the old rule reached 1. `ABCC_REVIEW_SUITE` is new beside it.
* 🚨 **F573 — `NothingToRun` is 11, not 8, and the doc comment said "51 greens and 8 shrugs" where
  the stored `correct.tsv` in the same directory said 48 and 11.** The extra three are `q56/Q05`,
  `Q11` and `Q52`: rust trees with a `Cargo.toml` on which `cargo test` runs and reports *0 passed;
  0 failed*, because the fixture has no test function. The number was never 8 — only the prose was.

## 7. What a probe over this tier owes

1. **A noise floor arm measured ON THIS TIER.** `27 of 121` is q56+k's number on q56+k's trees.
   Nothing in this stack samples at temperature zero, so the control asked twice is the ruler and
   `SUITE=od` has to be set on all three arms or on none.
2. **The `inside` third read separately.** A treatment that moves it as much as the other two has
   not been shown to be about scope.
3. **The 3 × 3 cell, not the row** — see §3's confound.
4. **The `correct` arm.** An instruction to look for what a change does *not* reach can manufacture
   incompleteness on a tree that is fine, and 24 correct trees is what would show it.
5. **Nothing quoted from `hedge_candidate`** — F568: 0 hits in 363 reviews, no positive control.
6. **Findings read against the answer key by hand.** `verify.sh` grades a tree; a reviewer's prose
   is not a tree, and a keyword count is not a finding count.

**Budget, from the 121-tree run's 60.5 s median:** `SUITE=od` is 72 trees, ~72 min an arm, **~3.6 h
for control + treatment + control-again.** Unfiltered it is 193 trees and most of a day.

## 8. Provenance

* Research repo `908f6e9`…`ac1edb2` — the suite, its README, and three instruments:
  `gate-task.sh` (SPEC §9's three points, `WRITE=1` puts the measured block into `task.toml`),
  `od_new_task.py` (the boilerplate half, and it writes `point1 = "not_run"` so an ungated task says
  so), `od_show.py` (the three trees' real output, because the loop is predict-then-look).
* abcc `4a7403a` — `tasks()` builds `["q56", "k", "od"]`; three corrected numbers in the doc
  comments. abcc `90c1273` — the dossier selectors and their test.
* `gate-task.sh` was run against the **K suite** before it was trusted and reproduces all three of
  K's recorded gate records. That is the positive control for the instrument itself.
