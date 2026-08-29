# Acceptance run C — the Q56 and K corpora, and the Gate's exit criterion

**Status: COMPLETE — 2026-08-29.** Both halves: the deterministic ladder over 121 trees and the
Judge over all 121 of them. This is the run `PLAN.md` §3's GATE
milestone names as its exit: *"run against the Q56 and K corpora, whose answer keys already exist.
**Zero false fails on the correct-tree population**, any one of them fixed as a rung defect before
the milestone closes; and the report volume on wrong trees measured, so the new falsifier above has
a number."* **Findings F523–F536**; next free number is **F537**.

🚨 **Read F531 first, then F536, which answers it, then F534, which re-prices it.** The criterion is met, the volume is low
and the precision is excellent; F531 is the one result that is not good news, and it qualifies every other
number here. **F532 is the one that is immediately actionable** — it discharges a condition
ADR-0010 §7 wrote down as waiting for exactly this population.

The instrument is four `#[ignore]`d tests in `D:\dev\abcc`, all committed:
`crates/abcc-gate/tests/corpus.rs` walks the ladder over three populations with no model call, and
`crates/abcc-gate/tests/corpus_review.rs` asks the Judge about each tree it wrote a dossier for.
Artifacts are under `research/corpus-run/`: `correct.tsv`, `wrong.tsv`, `sham.tsv`, `reviews.tsv`,
and one dossier and one review per tree.

| the three populations | trees | pair |
|---|---|---|
| **correct** | 59 | `fixture` → `fixture`+`refsol` |
| **wrong** | 59 | `fixture` minus the solution → `fixture` |
| **sham** | 3 | `fixture` → `fixture`+`sham` |

⚠ **The finding numbers below are not in the order they were found.** F529 (line endings) was found
by reading a dossier produced for F528 (the shams), and F528 was found while writing up F523. They
are numbered in the order they are worth reading.

---

## ▶ THE HEADLINE — the criterion is met, and it is not met vacuously

> **0 false fails on 59 correct trees. 48 of them `Green`, 11 `Unverified`, and not one `Red`.**

That is the clause ADR-0017 left standing after David's ruling of 2026-08-30. Under *a correct tree
is one that could land*, the 25-attempt population on this project's own log contains **no correct
trees at all**, so F518's 25-of-25 satisfied the clause by having nothing to satisfy it with. This
population has 59 of them, produced by somebody else, with an answer key that shipped with them.

| | correct trees (`fixture` → `fixture`+`refsol`) | wrong trees (`fixture` minus the solution → `fixture`) |
|---|---|---|
| **`Green`** | **48** | **35** |
| **`Red`** | **0** ← the criterion | **13** |
| **`Unverified`** | 11 | 11 |
| total | **59** | **59** |

🚨 **The two halves cross-tabulate perfectly and that is the result, not a coincidence:**

| | wrong=`Green` | wrong=`Red` | wrong=`Unverified` |
|---|---|---|---|
| **correct=`Green`** | **35** | **13** | 0 |
| **correct=`Unverified`** | 0 | 0 | **11** |

Every tree the ladder could measure at all, it passed on the right answer. Of those 48, it
**refused 13 of the wrong answers and accepted 35 of them.** So:

▶ **The deterministic ladder separates right from wrong on 13 of 48 measurable trees — 27%.**
That is the number the new falsifier wants, and it is the whole argument for the Judge stated as a
fraction: **35 wrong trees reach an operator with a green headline unless something reads the
diff.**

⚠ It is not a defect in a rung and there is nothing to fix. The donor's central design is that the
visible tests are happy-path and a wrong answer passes them on purpose; the hidden reviewer tests
live in `verify.sh` and are written into the work dir at grade time, so the subject — and the
acceptance rung — never see them. A gate measuring the tests a repository actually has will accept
these. **The 27% is a property of the corpus's design, and it is exactly the situation ADR-0008
built the Judge for.**

---

## The population, and what it actually is

59 tasks, **121 measured trees**. Every task ships `prompt.txt`, `task.toml`, `verify.sh`,
`fixture/` (already a wrong answer) and `refsol/` (the solution file(s) of a right one); the K tasks
add `sham/`.

| suite | tasks | languages |
|---|---|---|
| `q56` | 56 | rust 14 · python 15 · node 10 · typescript 9 · shell 8 |
| `k` | 3 | python, and they are real multi-file projects (19–32 files) |

### The three pairs, and why the wrong one has the `before` it has

```text
CORRECT   fixture                      ->  fixture + refsol
WRONG     fixture minus the solution   ->  fixture
SHAM      fixture                      ->  fixture + sham        (K only, 3)
```

The correct pair is the ruled one. The wrong pair's `before` is the fixture with exactly the files
`refsol/` overlays **removed**, so its patch reads *the model wrote the solution file* — what the
prompt asked for — and touches the same file set as the correct pair's patch. The only difference
between the two halves is what is in the solution file, which makes them a controlled pair.

🚨 **The reverse pair (`refsol` → `fixture`) was considered and rejected.** It needs no deletion and
is tempting, but it shows a reviewer a prompt saying *implement `slugify`* beside a diff that
*removes* working slug handling. That asks the model about a mismatch rather than about a defect,
and a finding rate measured that way would be about prompt/patch coherence. Nothing in the chosen
design is authored — a deletion is not content.

⚠ `refsol/` is a **partial overlay, not a tree**, on all 59: it carries no `Cargo.toml` and never
the test file. *After* is `fixture` copied and then overwritten by `refsol`'s files. `cp refsol
after` would produce a tree with no manifest and no tests, which the gate would report faithfully as
broken — reading exactly like a real result.

---

## 🎉 THE JUDGE OVER ALL THREE POPULATIONS — 121 calls, 85.7 minutes

| population / ladder | trees | answered | findings | silent | restatement? | median |
|---|---|---|---|---|---|---|
| **correct** (all) | 59 | **58** | **1** | **57** | 0 | 36 s |
| ‣ correct / `Green` | 48 | 47 | 1 | 46 | 0 | 37 s |
| ‣ correct / `Unverified` | 11 | 11 | **0** | 11 | 0 | 28 s |
| **wrong** (all) | 59 | 59 | 86 | 1 | 7 | 38 s |
| ‣ wrong / `Green` | 35 | 35 | 56 | 0 | **0** | 41 s |
| ‣ wrong / `Red` | 13 | 13 | 14 | 0 | 6 | 22 s |
| ‣ wrong / `Unverified` | 11 | 11 | 16 | 1 | 1 | 36 s |
| **sham** (all) | 3 | 3 | **0** | **3** | 0 | 61 s |
| **TOTAL** | **121** | **120** | **87** | 61 | 7 | — |

160,641 prompt tokens, 354,708 completion, **333,296 reasoning — 94.0%**.

### 🎉🎉 Precision: ONE candidate false positive in 59 correct trees, and it was refuted by running it

**57 of the 58 correct trees the reviewer answered about came back silent.** The single finding was
`q56/Q10 (correct)`:

> *at:* `src/lib.rs:12-30` · *defect:* trailing dot allows an invalid address to pass ·
> *run:* `is_valid_ipv4("1.2.3.4.")` · *expected:* `false` · *actual:* **`true`**

It is wrong, and **checking that took one command**, because ADR-0008 rule 2 requires a finding to
carry something runnable:

```text
assert_eq!(is_valid_ipv4("1.2.3.4."), false);   →   test result: ok. 1 passed
```

🚨 **And the reviewer's own assessment names the reason it was wrong:** *"relies on Rust's
`str::split`, which discards trailing empty strings by default."* **Rust's `split` does no such
thing** — that is Python's `str.split()`, applied to Rust code. ▶ **So the confirmed false-positive
count on 59 correct trees is 0, and the one candidate cost ten seconds to dismiss.** ADR-0008's
*10 of 23 against 1 of 34* was borrowed from Phase 1; this is the project's own, and rule 2 is the
reason the number is cheap to establish rather than a matter of opinion.

⚠ **The other side of the same coin is F531.** The reviewer is silent on 57 of 58 correct trees
*and* on 3 of 3 shams. **Silence is its normal output for "this looks fine", so silence carries no
information about which of the two a tree is.** Precision is excellent; the failure is recall on the
one tier built to be hard.

### 🚨🚨 F532 — `OpenAt200` fired once in 121 calls, on the one call that failed

ADR-0010 §7 asks *at token 200, has the reasoning trace closed?*, says the answer should be a stop
rather than a score, and then says why it is not acted on yet: *"at Skeleton it is recorded and not
acted on. Stopping a generation on this signal is a behavioural change that needs a population to
justify it, **and the population is what recording it produces**."*

> **The population is 121 calls. `TraceSignal::OpenAt200` fired on exactly one of them, and that one
> is the only call of the 121 that did not answer.** `Closed` on all 120 that did.

`q56/Q35 (correct)` — reviewing a **correct** tree, so a change with nothing wrong in it — ran
**209 seconds**, spent the **entire 16,384-token budget**, **100% of it on reasoning**, and returned
an **empty payload**: `Unmeasured { TruncatedAtCap }`. It is also by a wide margin the most
expensive call in the run; the next largest completion is 8,890 tokens.

▶ **This is the evidence ADR-0010 said it was waiting for, and it is a clean 1-for-1.** At this
sample the signal has **0 false positives in 120 good calls** and caught **1 of 1** failures. Acting
on it would have saved 209 s and 16,384 tokens and cost nothing, because the call it would have
stopped produced nothing.

⚠ **One event is one event.** A perfect correspondence over a single failure bounds the
false-positive rate at under 1-in-120 at this sample size; it does not establish a rate for the
failure side. 🚨 **The decision is David's** — it is a behavioural change to a generation, which is
exactly the class ADR-0010 §7 reserved. What has changed is that the *justification* clause is now
discharged: there is a population, and it says what the ADR guessed it would.

---

## 🚨🚨🚨 F531 — THE JUDGE MISSES THE SHAMS, AND ON ONE IT MANUFACTURED ITS OWN CORROBORATION

**This is the finding that qualifies every other number in this file, and the sham tier exists
because somebody suspected it.** F530's recall is 43 of 46 on the ordinary wrong trees
(**44 of 46** once F535 is applied). On the three
trees the corpus built to be *hard* — the tempting local fix that resolves the reported symptom —
the reviewer reports **nothing at all on 3 of 3**, and it does not report nothing quietly.

`k/round_at_the_line_not_the_total (sham)`, verbatim, all of it:

> *"This change replaces `money.quantize(running)` with a ceiling-based rounding formula that forces
> the accumulated float sum to round up (or stay exact) to the nearest cent, preventing IEEE-754
> representation drift from silently truncating the total below the printed line amounts. It
> guarantees internal invoice consistency without touching output formatting or test data, and **the
> host's acceptance suite confirms all eighteen discrepancies are resolved**.*
> *Defects: None found."*

🚨 **The bolded clause is false, and it is manufactured out of a rung's own count.** What the Judge
was shown, from the dossier it was built from:

```json
{"rung":"acceptance","exit":0,"counts":{"run":18,"passed":18,"failed":0},
 "detail":"..................  [100%]\n18 passed in 0.26s"}
```

What the answer key says about the very same tree:

```text
RESULT: FAIL — expected 'MISMATCHES 0 of 18', got: MISMATCHES 7 of 18
```

The fixture has **18 visible tests** and the order set has **18 invoices**, and the two numbers are
not the same quantity. The reviewer read *18 passed* and wrote *all eighteen discrepancies are
resolved*, then filed it as a reason to find no defects. **Seven of the eighteen invoices are still
wrong.**

🚨 **It is 0 findings on 3 of 3, and all three cite the rungs as positive evidence.** That is the
part that makes it a pattern rather than one bad call:

| sham | what it actually leaves broken | what the reviewer said |
|---|---|---|
| `round_at_the_line` | `MISMATCHES 7 of 18` | *"the host's acceptance suite confirms all eighteen discrepancies are resolved"* |
| `finish_the_cancelled_status` | still bills 4 cancelled jobs, still requeues them | *"the acceptance suite confirms correct behavior across the updated logic"* |
| `trace_dropped_samples` | `samples: 30`, should be 54 — rev-B still dropped | *"The structural checks and acceptance tests pass without errors, confirming no regressions were introduced"* |

The third is the tidiest illustration of the tier: the sham guards the `ZeroDivisionError` the
ticket reported and never touches the ingest filter that is dropping the samples. **It fixed the
crash and left the bug**, and the reviewer described that as *no regressions*.

### Why this is the most important paragraph in the file

1. 🚨 **"No findings" does not distinguish a correct tree from the hardest wrong one.** The correct
   trees also come back with no findings — which is the right answer *there*. So on this population
   an empty findings list carries no information about which of the two it is.
2. 🚨 **It is the exact failure ADR-0008's rule-3 caution is about, arriving by a route the rule
   does not cover.** The brief deliberately withholds the **headline** — *"a reviewer shown the
   decision is a reviewer asked to agree with it"* — and then shows every **rung**, including its
   `counts` and its captured output. The rung detail did the headline's job anyway. ▶ **That was left as a design
   question for David, and he ruled *probe it first*. It is now answered by measurement rather than
   by argument — see F536: the answer is no, the rung output stays.**
3. **It is this project's own recurring defect class, in the model's voice.** A count from one
   measurement quoted as evidence about a different quantity is F517 (`0 passed` on a run that
   measured nothing), and it is the standing rule *a token total says the size of a completion,
   never where it went*. Here the gate did not make the mistake — the reviewer did, out of the
   gate's honest output.

⚠ **What this does NOT say.** It is **3 trees**, all python, all from one suite, and a rate cannot
be built on 3. What can be said is that it is **3 of 3 rather than 1 of 3**, and that the mechanism
is the same one each time. It also **changes no verdict**: the Judge cannot refuse and cannot fail, the ladder
had already called all three `Green`, and nothing about the attempt's ending moved. The cost is
precisely what ADR-0008 said the cost would be — *these reach the operator as reports* — and on
these three the report was **actively reassuring and wrong**, which is worse than silence and is the
thing to watch.

▶ **The falsifier is not triggered by volume; it is nudged by this.** *"The wrong trees reaching
David as reports"* is fine at 86 findings and a median of 1. But a report that says **"Defects: None
found"** about a change that leaves seven bad invoices spends the reviewer's trust rather than their
minutes, and trust is the thing `PLAN.md` says a false block costs.

---

## 🚨🚨🚨 F536 — F531's PROBE, RUN: withholding the rung output does not survive its own measurement

**David ruled on 2026-08-29: probe the three shams before changing the brief.** Done — **15 calls**,
3 shams × 2 views × 2 fresh samples, plus the original run's 3. `RungView::Named` renders each rung
as `- acceptance — measured` and nothing else: **no exit status, no `counts`, no captured output.**
Only the rung block moves; the task, the diff and every sentence of instruction are byte-identical,
asserted by `the_view_moves_the_rungs_and_nothing_else_in_the_brief`.

⚠ **The control was run first and it held.** Nothing here is sampled at temperature zero — the
engine sends no `temperature`, no `top_p`, no `seed` — so the shams were re-asked twice under the
*shipped* view before the switch was touched. **9 of 9 `Full` calls: 0 findings.** F531's 0-for-3 is
the model's behaviour, not a sample.

| view | calls | findings | **cites the rungs as proof** | **says it cannot verify** | median s | median completion |
|---|---|---|---|---|---|---|
| `Full` | 9 | **0** | **7 of 9** | 1 of 9 | 60.5 | 4,036 |
| `Named` | 6 | **5** | **1 of 6** | 2 of 6 | 96.6 | 5,502 |

Read only that table and the change looks right. **It is not, and three things say so.**

### 1. 🚨 Four of the five findings are wrong, and one of them is wrong *because* of the change

`round_at_the_line (named-b)` produced **three findings, none of them the defect**:

1. *"`import math` inside the function body causes repeated module loading."* **False** — Python
   caches in `sys.modules`. A style note asserted as an overhead defect.
2. *"Float accumulation drift ... off by multiple pennies for long invoices."* Speculative, and not
   the defect: the sham is wrong because it rounds the **sum** instead of the **lines**.
3. 🚨 *"`money.EPSILON` ... is not guaranteed to exist ... `NameError: name 'EPSILON' is not
   defined`."* **False, and it is the probe's own doing.** The tree runs and its suite passes;
   under `Full` the reviewer could see that and did. **Withholding the measurement did not make it
   humble — it made it invent a runtime crash on a tree that runs.**

`finish_the_cancelled_status (named-a)` is the fourth: it flags `st.is_terminal` as possibly
excluding `CANCELLED`. It does not exclude it — and per F534 **that hunk is byte-identical to the
answer key's.** The one part of the change that is provably right is the part it reported.

✅ **One of five is correct**: `trace_dropped_samples (named-a)` — *"leaves upstream data loss
unaddressed ... the fix **suppresses symptoms rather than resolving why sample volumes are lower**
than expected."* That is the sham's real defect, named, on the tree F534 shows the defect is not in
the diff for. **It is the only correct sham finding in all 15 calls, under either view.**

### 2. 🚨🚨 The failure mode came back through the new wording: it read `measured` as *passed*

`trace_dropped_samples (named-b)`, under `Named`, with no counts and no output anywhere in its
brief:

> *"**The host measurements already confirm structural, acceptance, and veto checks pass.**"*

**Nothing in that brief says any rung passed.** It listed the three rung names it was given and
supplied the verdict itself. 🚨 **That is the exact hazard `RungView::Named`'s own doc claims to
avoid** — *"under `Named` the word `measured` no longer claims *fine*"* — and it is the hazard
`abcc_core::outcome` exists to remove, arriving from the model's side of the prompt rather than the
gate's. Withholding the evidence removed the citation, not the conclusion.

### 3. It costs about 1.6× the wall clock, and up to 3×

Median 96.6 s against 60.5 s, and `round_at_the_line (named-a)` took **191.9 s and 11,990 completion
tokens** — 3× the wall clock and 3× the completion of the same tree under `Full`, to return **zero
findings**. F522 already says the completion is 93–96% reasoning trace, so this is the trace getting
longer with less to work from.

### ▶ THE RULING THIS SUPPORTS, and it is not the one the question offered

🚨 **`RungView::Full` stays. `Named` is kept in the tree as the instrument that measured it, reached
only by `ABCC_JUDGE_RUNGS=named` from `tests/corpus_review.rs`, and no production caller passes a
view.** It buys **1 correct finding and 4 wrong ones** on 6 calls, re-introduces the false-confidence
conclusion in different words, and costs 1.6–3× the wall clock. **Report volume with nothing in it
is ADR-0008's own falsifier**, and 4 fabricated defects on trees whose code runs is that falsifier
being fed, not starved. See ADR-0019.

⚠ **This does not retract F531.** Under `Full` the reviewer cited the rungs as proof in **7 of 9**
calls and manufactured `18 passed → all eighteen discrepancies are resolved`. That is real. What the
probe establishes is that **hiding the rungs is not the fix for it** — the conclusion survives the
evidence being removed.

### 🎉 What the probe found by accident, and it is the better lead

**The best answer in all 15 calls came from `Full`.** `finish_the_cancelled_status (full-b)`, with
the counts and the stdout in front of it:

> *"the task explicitly requires treating cancelled jobs correctly **everywhere** it makes a
> decision based on status, not just in the complained-about report. Since this diff only modifies
> one file and **I do not have visibility into the other five consumers** of `job.status` ... I
> cannot verify full spec compliance or provide reproduction commands for unmodified areas."*

That is the correct reading of the sham — F534's *correct-but-incomplete* — reached with the rung
output visible and **not** used as a warrant. So the discriminating variable is not what the
reviewer was shown. It is **whether it checked the change against the scope the ticket stated**, and
two of the three shams state their scope in the ticket in so many words (*"everywhere ... not only
in the report"*; *"must account for every usable sample ... not merely avoid crashing"*).

🚨 **And the counter scored that call `0 findings, silent` — F535 again**, on the single best output
of the probe. The prose flag added in this session fires on a defect written into the assessment; it
does **not** fire on a correct refusal to endorse, which is a third thing the `findings[]`/`silent`
pair cannot express.

▶ **The candidate that follows is a brief change, not a rung change** — one sentence asking whether
the change covers the scope the task states, and whether anything it depends on is outside the diff.
**It is not written and not decided**, because it has a population of one call and this file's own
rule is that a name standing in for a specification is worse than an open question. Its falsifier is
cheap and it is the same one used here: three shams, two samples, one switch.

---

## 🚨🚨 F530 — THE JUDGE OVER 59 WRONG TREES, and the falsifier's number is good news

`PLAN.md` §3's second clause: *"the report volume on wrong trees measured, so the new falsifier
above has a number."* The falsifier is **"the wrong trees reaching David as reports are frequent
enough that unattended `Accept` is not worth having."** One model call per tree, champion at 32k,
`--parallel 1`, sequential, **39.8 minutes**.

| ladder | trees | answered | findings | restatement candidates | median |
|---|---|---|---|---|---|
| `Green` | 35 | **35** | 56 | **0** | 41 s |
| `Red` | 13 | **13** | 14 | **6** | 22 s |
| `Unverified` | 11 | **11** | 16 | 1 | 36 s |
| **total** | **59** | **59** | **86** | 7 | — |

**59 of 59 answered. 59 of 59 parsed as the shape they were asked for. One turn each, every trace
`Closed`, no truncation, no `ContextOverflow`, no `SaidNothing`.** 77,588 prompt tokens and 163,262
completion, of which **148,115 reasoning — 90.7%**.

### The volume is low, and that is the answer

> **42 of 59 trees got exactly one finding. One got none. Exactly one hit the cap of five.**
> Median **1**, mean **1.46**, and no language is an outlier (1.1 rust → 1.8 shell).

The reviewer is not padding. A report an operator has to read is one to three lines with a command
in it, not a wall. ▶ **On this population the falsifier is not triggered**: 86 findings across 59
wrong trees is a cost worth paying for what it buys below.

### 🚨 F521's sentence works exactly where it can, and cannot where it can't

The brief tells the reviewer that the measurements *"already ran and the operator has already been
shown them, so a finding that repeats one is a line they read twice"*, and that a refusal it
understands *"belongs in the assessment"*.

* **`Green` trees: 0 restatement candidates out of 56 findings.** Nothing to restate — the rungs
  found nothing — and the reviewer said something of its own every time.
* **`Red` trees: 6 of 14.** When the acceptance rung has already refused a stub, **the only defect
  in the tree is the one the rung found**, and the reviewer reaches for the test command as its
  runnable evidence.

▶ So the sentence **eliminates restatement on the population where restatement would be waste, and
cannot on the population where the rung's finding is the whole truth about the tree.** ⚠ And none of
the six is F521's actual failure mode: F521 was a bare echo (`run: cargo clippy` / `expected: exit
0` / `actual: exit 101`). These name the *cause* the rung could not — *"`slugify` is a stub and
returns `String::new()` for all inputs"* — with the concrete values expected. The assessment carried
the refusal correctly on all 13.

### 🚨🚨 Recall: 43 of 46, read by hand against the answer key

⚠ **Corrected to 44 of 46 by F535** — `Q05` wrote its finding into the `assessment` prose
with `findings: []` beside it, so the counter read it as silence. The number below is the one
the hand-reading produced before that was found; F535 carries the scan that bounds it at one
tree.

Recall is **not** scored automatically and this is not an automated number: `verify.sh` grades a
tree and a reviewer's prose is not a tree, so every review was read against the `# Hidden reviewer
tests:` note the importer left in each verifier. Over the **46 trees where recall is a meaningful
question** — 35 `Green` and 11 `Unverified`; the 13 `Red` are stubs with nothing subtle in them —
**the finding names the defect the answer key probes on 43.**

Some of them name every probe the key lists:

| task | what the key probes | what came back |
|---|---|---|
| **Q35** | repeated keys → array, percent/plus decoding, leading `?`, bare key → `""`, empty → `{}` | **all five, one finding each** |
| **Q44** | count-desc order, alphabetical tie-break, case folding, tabs/newlines as separators | **all four**, plus a `uniq -c` leading-space leak the key does not mention |
| Q07 | punctuation split, case folding, ordering | all three |
| Q13 | quoted commas, escaped quotes, quoted-empty fields | all three |
| Q23 | inclusive ranges, sort, dedupe, whitespace | all four |
| Q08 | left-associative chained subtraction | `evaluate("10 - 3 - 2")` → 5 / 9 |
| Q21 | tax on the subtotal, not per item | `invoice_total([33,33,33],10)` → 109 / 108 |
| Q25 | the classic float trap | `total_cents(['4.35'])` → 435 / 434 |

**The three misses, named:**

* **Q20** — the key probes *"present means not None: falsy-but-real values like `0`, `""` and
  `False` must be KEPT"*. The reviewer reported **unidiomatic iteration** (`range(len(values))`)
  instead. 🚨 The instructive part is that its one finding is exactly the low-value kind — a style
  note where a correctness defect was sitting in the same six lines.
* **Q05** — **nothing reported at all.** The one tree of 59 that produced no finding.
* **`k/trace_dropped_samples`** — reported *"the file is a standalone module with no diffs touching
  callers"*. ⚠ **That is my pair construction's fault rather than the model's**, and it is written
  up under *What the run does not say*: deleting the solution file and re-adding it makes an
  existing module look newly added and unwired. The reading was correct about the diff it was shown.

⚠ **Do not read 43/46 as a general recall rate.** These are single-function exercises where the
defect is concentrated in the file the diff shows; ADR-0008's Phase 1 number (10 of 23) came from a
different and harder population. What this establishes is a **floor on tasks of this shape**, and
the shape is the one the donor built to be gradeable.

### 🚨 The 11 trees where the Judge is the only reader there has ever been

The 8 shell tasks ship no test and 3 rust fixtures ship no test function, so **every deterministic
rung is silent on them** — `Unmeasured { NothingToRun }`, `Unverified`, no verdict available at any
price. The Judge produced **16 findings on those 11 trees and 10 of the 11 were on target**:

* **Q43** — `printf 'a\nb\nc' | bash solution.sh` → 3, got 2. The key probes exactly *"trailing
  newline, NO trailing newline, single unterminated line"*.
* **Q48** — unquoted `"$@"` word-splitting. The key: *"spaces inside an argument must be preserved"*.
* **Q50** — `cut -d' '` where the data is comma-separated.
* Q44, Q45, Q46, Q47, Q49, Q52, Q11 on target; **Q05** the miss.

▶ **This is the clearest statement of what the phase buys.** On a tree the gate cannot measure, a
`Green` is impossible and an operator gets `Unverified` and nothing else. With the Judge they get
`Unverified` **and a runnable reproduction of the actual bug**, ten times in eleven.

⚠ Two payload defects worth naming: **Q49's finding has `expected` and `actual` both equal to
`hi`**, so it demonstrates nothing even though the defect it names is real; and the shell findings
all offer `bash solution.sh …` as the command to run, which on this host is **F525's WSL relay**. An
operator following one literally would not reproduce anything.

---

## 🚨🚨 F529 — nine CRLF files turned a six-line change into a 190-line diff, and only the Judge could see it

Found by reading one sham dossier and asking why a change the corpus describes as *"ceil instead of
half-up"* had a **5,587-character** patch. Measured across both corpora:

| | files | endings |
|---|---|---|
| every `fixture/` file | **164** | **LF** |
| every Q56 `refsol/` file | **57** | **LF** |
| **K-suite `refsol/` and `sham/` files** | **9** | **CRLF** |

An overlay whose line endings differ from the file it replaces makes `git diff` report **every line
as changed**. `billing/pricing.py`'s sham is a six-line edit and the diff was **94 deletions and 96
insertions**.

🚨 **It is invisible to the deterministic rungs and it is not invisible to the Judge.** The
structural rung counts files and the acceptance rung runs the real file, so **nothing in
`correct.tsv` or `wrong.tsv` moved** — re-running the correct half after the fix gives the same
48 / 0 / 11. But ADR-0008's rule 1 is that the reviewer is shown *the other artifact*: the `-` lines
are the pre-image and the `+` lines the post-image, measured at **14 of 14 pairwise against 0 of 8
pointwise**. A whole-file rewrite hands the model both images with the six lines that matter hidden
in 190. **That is the pointwise case wearing a diff's clothes**, and it would have degraded every
K-suite review silently — no error, no warning, just a worse answer.

The fix is in `copy_tree`: every text file written into a scratch tree is normalised to LF (a file
containing a NUL byte is copied verbatim, which is git's own test for text).

> **`round_at_the_line`'s sham patch: 5,587 → 717 characters**, an 87% cut, and what is left is the
> six-line change. After the fix the three sham patches are **577 / 717 / 568** characters.

⚠ 5,587 is the only pre-fix number that was measured; the other two sham dossiers were regenerated
before anyone read their size, so this quotes one measured pair and three measured after-values
rather than three pairs.

⚠ **Normalising is the honest fix and hiding it would not be.** Both sides get the same treatment,
so no difference is manufactured *and none is concealed*. A real attempt edits a file in place and
keeps its endings, so the mixed endings are an artifact of how the corpus was assembled, not a
property of any change; leaving them in measures the importer's text editor.

▶ **The general shape, for [[verify-claims-against-code-not-docs]]: a diff is a rendering, and a
rendering can be wrong about a change that is right.** Every rung agreed the tree was fine and every
rung was correct; the thing that was wrong was the *picture of the change*, and the only consumer
that reads the picture is the one whose measured design depends on it.

---

## 🚨🚨 F528 — the SHAMS, and they are the tier the whole argument turns on

The K suite ships a third thing the first pass missed: **`sham/` — "the local wrong answer".**
`point3 = "sound"` on all three (Q56 has none, `not_run`). A sham is neither of the other tiers. It
is not a stub and it is not a naive first attempt; it is **a change that fixes the symptom the
ticket reported and leaves the defect**. The corpus says so in its own words:

* `finish_the_cancelled_status` — *"fixing `sla.py` alone … fixes exactly what the ticket described
  — SLA breaches drop from 6 to 2 — and leaves the service billing customers for four cancelled jobs
  and requeueing work an operator told it to stop."*
* `round_at_the_line_not_the_total` — *"changing the rounding direction at the end — ceil instead of
  half-up — FIXES the reported invoice, which is what makes it tempting. It fails because the eight
  wrong totals differ in BOTH directions: five need the total higher and three need it LOWER."*

The pair is deliberately the same shape as the correct one — same `before`, an overlay on top — and
for `round_at_the_line` it is **literally the same file** (`billing/pricing.py`) in both, so the
sham row and the correct row differ in exactly one thing: what the solution file says.

> 🚨 **All three shams are `Green`. Structural, acceptance and veto, every rung measured, nothing
> refused.**

**Point 3 was re-measured here rather than quoted** — `verify.sh` over three trees per task:

| task | fixture | +sham | +refsol |
|---|---|---|---|
| `finish_the_cancelled_status` | FAIL | **FAIL** | PASS |
| `round_at_the_line_not_the_total` | FAIL | **FAIL** | PASS |
| `trace_dropped_samples` | FAIL | **FAIL** | PASS |

▶ **This is the falsifier stated without any hedging.** A deterministic gate cannot distinguish
*fixed the bug* from *fixed the symptom the ticket named*, because both pass the tests the
repository has. The rungs are not wrong; the information is not in them. **On this tier the Judge is
not a second opinion, it is the only opinion there is.**

So the population is three wrong tiers and one absence:

| tier | trees | ladder | what it is |
|---|---|---|---|
| **stub** | 13 | **`Red` 13 of 13** | null implementation; fails its own visible tests |
| **naive** | 35 | **`Green` 35 of 35** | plausible wrong first attempt; passes the visible tests |
| **sham** | 3 | **`Green` 3 of 3** | the tempting local fix; fixes the reported symptom |
| no checker | 11 | `Unverified` | no test to run at all |

---

## 🚨 F523 — the fixtures are TWO tiers, and the corpus's own note says one

`task.toml`'s gate block says point 1's pre-state is *"the donor's untouched fixture (tier
`donor_fixture`), not §9's generated null-implementation stub: the fixture already compiles and
**passes the visible tests** while failing the hidden ones, which is the state the stub was invented
to simulate."*

Measured on this host over all 59, by running each fixture's own visible tests:

| | fixtures | what they are |
|---|---|---|
| **naive** | **38 of 51 runnable** | a plausible wrong implementation that passes the visible tests — what the note describes |
| **stub** | **13 of 51 runnable** | `// TODO: implement`, `raise NotImplementedError`, empty method bodies — they **fail** the visible tests |
| unrunnable | 8 | the shell tasks, which ship no test file at all |

The 13 stubs are `Q01 Q02 Q06 Q09 Q10 Q56` (rust), `Q24 Q51 Q54` (python), `Q31 Q53` (node),
`Q40 Q55` (typescript). The note is right about point 1 — both tiers fail the *hidden* tests, which
is what the donor gate recorded — and wrong about the tier. **A null-implementation stub is not what
the fixture tier claims to be, and 13 of them are exactly that.**

▶ **This is not cosmetic: the two tiers behave differently at the gate, and the split is the
27%.** The 13 `Red` rows on the wrong half are the 13 stubs, one for one, with no exceptions. The
acceptance rung refuses a stub because a stub fails the tests that ship with it; it accepts a naive
wrong answer because a naive wrong answer passes them. **The ladder's discrimination on this
population is entirely the stub/naive split and none of it is edge-case reasoning.**

---

## 🚨🚨 F524 — the gate is STRICTER than the raw command, and it caught three trees nobody would have

Running the acceptance command directly says **38 fixtures pass**. The gate says **35 `Green`** and
three `Unverified`. The three are `Q05`, `Q11` and `Q52` — rust tasks whose fixture **and** refsol
carry **zero `#[test]` functions anywhere**. `cargo test` on them exits **0** and prints
`test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured`.

Any gate that reads the exit status alone records those as verified-green. `Reading::Cargo` does not:
*no exit code means "nothing to run"*, so the rung is `Unmeasured { NothingToRun }` and the headline
is `Unverified`.

▶ **F517 was found while building the gate, on this repository's own suite. This is the same defect
class arriving from an unrelated corpus, and the mechanism built for F517 caught it without being
touched.** Three of 59 trees — 5% of the population — would otherwise have been counted as passing a
test suite that does not exist. It is also the cleanest available demonstration of why `Green`
promises *every declared rung was measured* rather than *nothing failed*.

⚠ It cuts the other way too, and honestly: those three tasks are in the corpus and are **not
gradeable by an acceptance rung at all**. They are gradeable by `verify.sh`, which writes its own
hidden tests in.

---

## The `Unverified` eleven, named

`Unverified` is neither a pass nor a fail — `Headline::is_pass` is `Green` and nothing else — so it
is counted separately rather than folded into either column. All 11 are the same `Why`,
`NothingToRun`, and all 11 are `Unverified` in **both** directions:

| trees | which | why |
|---|---|---|
| **8** | `Q43`–`Q50`, shell | the fixture is `solution.sh` and nothing else. No test, no test runner, no manifest. |
| **3** | `Q05`, `Q11`, `Q52`, rust | F524 — the crate ships no test function. |

🚨 **No `bash`-based rung was invented for the eight shell tasks, and that is a decision.** A rung
running `bash solution.sh` is not a test, and — measured live this session, F525 — `bash` from a
Windows process is the WSL relay, which fails before running anything. Declaring it would have
manufactured **eight false fails on eight correct trees**, which is the exact quantity this run
exists to count. The honest answer is `NothingToRun`, and the report says so per rung.

▶ So the criterion is met at **48 measured green, 11 named absences, 0 refusals** — and the
sentence is *every tree that carries a test passed, and every tree that does not is named*, which is
a different and much stronger sentence than "48 of 59".

---

## 🚨 F525 — `CreateProcess` searches `System32` before `PATH`, so `bash` is the WSL relay whatever `PATH` says

F492 recorded that `bash` on PATH here is the WSL relay and fails at exit 1. This run reproduced it
and found the mechanism, which is worth more than the symptom.

Verifying the answer key means running each task's `verify.sh`. From a Windows process,
`subprocess.run(["bash", ...])` produced, 8 times of 8:

```text
<3>WSL (13 - Relay) ERROR: CreateProcessCommon:818: execvpe(/bin/bash)
```

— while `shutil.which("bash")` in the same process returned `C:\Program Files\Git\usr\bin\bash.EXE`,
the right one. The two disagree because they search differently: `which` reads `PATH`, and
**`CreateProcess` searches the application directory, the current directory, `System32`, `Windows`,
and only then `PATH`.** `C:\Windows\System32\bash.exe` is the WSL launcher, so it wins before `PATH`
is consulted at all.

▶ **The rule: for `bash` on this host, an absolute path is not a nicety.** And the wider one is
[[verify-claims-against-code-not-docs]]'s — *a non-zero exit from the wrong program looks exactly
like the right one failing*. The check that caught it was writing the verdict parser to return
`NO-RESULT-LINE` rather than `FAIL` when `verify.sh` printed no `RESULT:` line; a parser that
defaulted to `FAIL` would have reported the answer key broken on 8 of 8.

---

## ✅ F526 — the answer key holds on all 59, verified here rather than inherited

`task.toml` records point 1 `donor_fixture` → **FAIL** and point 2 `refsol` → **PASS**, both
`sound`, measured at import in 2026-08. Those two rows are what the whole run leans on, so they were
re-measured on this host by running the corpus's own `verify.sh` — the hidden reviewer tests — over
both trees of every task.

> **59 of 59: `fixture` FAIL, `fixture`+`refsol` PASS. No exceptions, no `INVALID`.**

That is a positive and a negative control in the same command, and it is what makes *correct-tree
population* a measured phrase rather than an inherited one. Full table in `scratch/answer-key.log`.

🚨 **It also settles the eight shell tasks, and the answer is not comfortable.** `verify.sh` grades
them fine — 8 of 8 FAIL on the fixture and PASS on the refsol — so they are genuinely right and
wrong trees. The gate cannot see it, because grading them means *writing tests in*, which is the
answer key's privilege and not a rung's. ▶ **`Unverified` on those eight is the gate being honest
about a tree that is decidable by something else.** That is the correct outcome and it is also a
real limit: a repository with no tests gets no acceptance measurement, whatever is true of it.

---

## F527 — the cold-build price is a property of THIS workspace, not of cold builds

`abcc-gate`'s own docs quote **55 s and 2.3 GB** for one cold `cargo test --workspace`, measured at
F512's run 10, and `tests/live.rs` warns that every changed tree costs one. This run built **28 rust
trees cold** — no shared `CARGO_TARGET_DIR`, because it is not on `ENV_ALLOWLIST` (F356) — and:

> **118 trees, both halves, walked in 44 seconds total. The slowest single tree was 0.97 s.**
> (The three shams add 3 s, for 121 trees in 47 s.)

The 55 s is the price of building *this workspace*, which is eight crates and 44 test targets. A
one-file library crate is under a second. ▶ **Do not plan Fleet's disk or wall-clock budget off the
55 s figure as though it were the cost of a gate walk** — it is the cost of a gate walk *on a
repository this size*, and the corpus says the rung mechanism itself is free.

---

## The blocker that opened the session, and how it was closed

`Toolchain::detect` finds a profile on **14 of 59 trees**. There is no `pyproject.toml`,
`pytest.ini`, `setup.py`, `tox.ini`, `package.json` or `clippy.toml` anywhere in either corpus; the
only witness that exists is `Cargo.toml`, in the 14 rust fixtures. The other 45 would land
`Unmeasured { NoCheckerForArtifact }` → `Unverified`, which is the type being honest and is **not** a
false fail — but 45 shrugs is not a measurement either.

**The fix needed no new mechanism.** `Gate::with_toolchain` already takes an operator-configured
profile; the instrument builds one per `task.toml`'s `lang`:

| lang | test command | reading | trees |
|---|---|---|---|
| rust | `cargo test` | `Cargo` | 14 |
| python | `python -m pytest -q` | `Python` | 18 |
| node | `node test_basic.mjs` | `ExitOnly` | 10 |
| typescript | `node test_basic.ts` | `ExitOnly` | 9 |
| shell | *(empty — `NothingToRun`)* | — | 8 |

🚨 **They are NOT added to `abcc_engine::workspace::TOOLCHAINS`, and that is the decision rather
than the shortcut.** That table is a claim about *every repository* — a witness file, then a
command. `node test_basic.mjs` is true of this corpus and of nothing else, and a witness-less entry
would be an entry `detect` can never reach. **The instrument is the honest home for a command that
is true of one population.**

Three sub-decisions worth keeping:

* **`node --test` was rejected.** Its default glob does not match `test_basic.mjs`, so it would
  discover nothing and exit 0 — a green rung that measured nothing, which is F517's shape exactly.
  The fixture's own test file is named directly.
* **Node 24 strips TypeScript natively**, measured rather than assumed, so the 9 `.ts` fixtures need
  no second runtime.
* **`python`, never `python3`** (F312), and `pytest` lives in this interpreter's own
  `site-packages` rather than the user one, so it survives `env_clear()` plus `ENV_ALLOWLIST`.
  Verified under the scrubbed environment a rung child actually gets, not under the shell's.

⚠ The cargo profile **keeps its standard rung** even though no tree in either corpus carries a
`clippy.toml`. `Standard::declared_at` answers `false` and the rung is *absent*, so every tree here
has **three** rungs. An absence a mechanism computed is worth more than an absence the instrument
assumed — and it confirms the corollary: **the standard rung gets no false-fail number from these
corpora at all.** Its evidence stays this repository (F512), and its falsifier is the operator who
routinely `abcc accept`s past a `Refused { rung: "standard" }`.

---

## Why `u40` and `u100` are not in it, measured rather than assumed

`PLAN.md` names Q56 and K, but two other suites sit beside them and a bigger correct-tree population
would strengthen the headline, so both were checked rather than skipped on the strength of the
sentence.

* **`u100` has no answer key.** 90 fixtures, **1** `refsol`. There is nothing to compare against.
* **`u40` has a complete answer key — 40 fixtures, 40 refsols — and would still add nothing.** Its
  fixture is not a wrong answer, it is an **empty scaffold**: all 40 are a single
  `tasks/__init__.py`, and across all 80 of its trees there is **not one test file**. Every tree
  would land `Unmeasured { NothingToRun }` → `Unverified`, exactly like the eight shell tasks.
  40 more shrugs is not 40 more correct trees.

▶ So the population is not 99 and cannot be made 99 by including a suite that ships one. `u40` is
gradeable — by `verify.sh`, which writes its tests in — and not by a rung, which is the same limit
F526 states for shell.

## 🚨 F533 — EVERY wrong tree's diff has NO PRE-IMAGE, so 43 of 46 is a *pointwise* number

Measured over all 121 dossiers, counting diff lines that start with `-` and are not the `---` header:

| population | trees | median chars | median `+` lines | median `-` lines | **trees with any `-` line** |
|---|---|---|---|---|---|
| correct | 59 | 625 | 7 | 3 | **58 of 59** |
| wrong | 59 | 389 | 9 | **0** | **0 of 59** |
| sham | 3 | 577 | 5 | 1 | **3 of 3** |

🚨 **Not one of the 59 wrong trees showed the reviewer a pre-image.** That is not a defect — it
follows from the pair `fixture minus the solution -> fixture`, which is ruled and whose alternative
was rejected for good reasons — but it is a **confound the run's own numbers were read without.**

**ADR-0008 rule 1 is the rule the whole phase is built on:** *show it the other artifact, never a
threshold* — pointwise **0 of 8**, pairwise against the pre-image **14 of 14**. On the wrong half
there was no other artifact to show. So:

* ▶ **The recall figure was earned with rule 1's mechanism unavailable.** A reviewer reading a new
  file and naming its defect is doing the thing ADR-0008 measured at 0 of 8 — with the caveat that
  ADR-0008's 0 of 8 was pointwise **scoring** and this is pointwise **defect-finding**, which are
  not the same task. Still: the number is good, and it is not evidence for rule 1.
* 🚨 **The three shams are the only wrong-tier trees measured pairwise at all.** So *0 of 3 on shams
  against 43 of 46 on wrong trees* varies two things at once — the tier **and** the shape of the
  input. F531's question has to be read knowing that.

▶ **Q20 is the counterexample to this file's own caveat**, which says the pair "costs nothing on the
56 single-file Q56 tasks". Q20 asks for `keep_present` to be made Pythonic; the defect is that
`if v:` drops `0` and `""` as well as `None`. On the **correct** tree, where the diff shows
`-if v:` beside `+if v is not None:`, the reviewer named the defect class precisely and unprompted:
*"corrects the filtering logic from truthiness to strict None identity checking ... including falsy
ones like 0 or False."* On the **wrong** tree, with the same function arriving as a new file, it
reported a **style** note and proposed `[v for v in values if v]` — **reproducing the bug in its own
suggested fix.** Same model, same defect, same session; the pre-image is the only difference.

---

## 🚨🚨 F534 — two of the three shams' defects ARE NOT IN THE DOSSIER, and one hunk is byte-identical to the answer key

F531 reads *0 for 3 and it endorsed them*. Read against `refsol/` rather than against the review,
the three are not one failure — they are **one reading miss and two questions the dossier cannot
answer**:

| sham | the answer key touches | the sham touches | is the defect in what the reviewer saw? |
|---|---|---|---|
| `round_at_the_line_not_the_total` | `pricing.py` | `pricing.py`, **same function** | ✅ **yes** |
| `finish_the_cancelled_status` | `charges.py`, `retry.py`, `sla.py`, `summary.py` | `sla.py` — **1 of 4** | ❌ no — 3 files absent |
| `trace_dropped_samples` | `ingest.py` | `stats.py` | ❌ no — **different file** |

🚨 **`finish_the_cancelled_status` is the sharpest of the three, and it inverts the story.** Its
`sla.py` hunk is **byte-for-byte the answer key's own `sla.py` hunk**. The change the reviewer was
shown is not wrong; it is *correct and incomplete*, and the missing three files are nowhere in the
dossier. Its report — *"this directly fixes the operations complaint about cancelled jobs"* — is
**true about the change it was given**. The defect is an **omission**, and a diff cannot exhibit an
omission: the evidence for it is the absence of code that was never written.

🚨 **`trace_dropped_samples` is the same shape, further away.** The real fix is a case-fold four
modules upstream — `flag = normalize.canonical_flag(rec.get(...))` in `ingest.py`, because rev B
firmware emits `OK`/`WARN` upper-case and comparing them raw silently drops half the fleet. The
reviewer was shown `stats.py`. **The file containing the defect is not in the diff, the dossier, or
the prompt.**

✅ **`round_at_the_line_not_the_total` is the real one, and it is enough on its own.** Everything
needed is in front of the reviewer: the ticket says the printed line amounts *must add up to* the
total, and the sham's own replacement docstring says the total is *"never below the sum of the
printed lines"*. **Never-below is not equal-to** — the contradiction is between two sentences in the
same dossier. It missed that, and then wrote *"the host's acceptance suite confirms all eighteen
discrepancies are resolved"*, which is the manufactured corroboration F531 is named for.

▶ **What this does to F531.** It does not retract it — the manufactured count is real and it is the
worst thing in the run. It **re-prices it**: the reviewer's honest score on the shams is **1 miss
out of 1 answerable question**, not 0 out of 3, and on the other two the best available answer was
*I cannot tell from this*. 🚨 **That is what makes the probe worth running rather than arguing:** on
exactly the trees where the diff cannot answer, the rungs' `counts` and captured stdout are the only
thing in the dossier that looks like evidence — and they are the thing that is misleading.

---

## 🚨 F535 — the finding counter reads `findings.len()`, and one review put its finding in the prose

`q56-Q05` is recorded in F530 as a recall miss — *"nothing"*. It is not. The payload parsed, and the
`assessment` string says:

> *"populates it with the exact same panicking implementation described in the task prompt rather
> than the requested fix ... **Defects: 1. Missing Result conversion and error handling** — call:
> `parse_kv("malformed_line")`; expected: returns `Err(String)` describing the missing delimiter;
> actual: panics at runtime."*

**The defect, carrying the runnable triple ADR-0008 rule 2 asks for, written into the prose field
with `findings: []` beside it.** Every `silent` column in this file counts empty arrays, not silence.

▶ **The blast radius is measured, not assumed.** All 61 silent reviews were scanned for a prose
defect — the `call`/`expected`/`actual` triple, or a `Defects:` list that is not *none*:

| population | silent (`findings == []`) | prose carries a defect |
|---|---|---|
| correct | 57 | **0** |
| wrong | 1 | **1** — `q56-Q05` |
| sham | 3 | **0** |

* ✅ **Precision is untouched.** 0 of 57 silent correct trees hid a finding, so *0 confirmed false
  positives* stands as a checked statement rather than an assumed one.
* ✅ **F531 is untouched.** 0 of 3 — the shams' assessments say *"Defects: None found"* in those
  words. They are silent in the sense that finding claims.
* 🚨 **Recall corrects to 44 of 46, and both remaining misses are explained by F533 and F534:**
  `Q20` (no pre-image — it named the same defect on the correct tree) and `k/trace_dropped_samples`
  (the defective file is not in the dossier).

⚠ **The instrument is what to fix, not the model.** The schema cannot stop a model writing prose
into a string field, and the brief already asks for the triple in the findings array. What is cheap
is that `corpus_review.rs` **flags a silent review whose assessment carries the triple**, the same
way it already flags restatement candidates — a pointer to reading, printed verbatim, never a
number. It is this project's own standing rule arriving from the other side: *a keyword count is not
a capability count*, and here a **zero from an unvalidated counter was read as a silence.**

---

## What the run does not say

* **It is not a measurement of the model.** Every tree is the answer key's; no model wrote one.
* ⚠ **The wrong pair's `before` slightly misrepresents K's multi-file tasks.** Deleting the solution
  file and re-adding it makes an *existing* module look newly added and unwired, and the reviewer
  read it that way on `trace_dropped_samples`: *"the file is a standalone module with no diffs
  touching callers."* That is a correct reading of the diff it was shown and a wrong reading of the
  task. It costs nothing on the 56 single-file Q56 tasks, where the solution file genuinely is the
  whole of the work, and it is a real limit on the 3 K tasks. **The sham pair does not have it** —
  its `before` is the untouched fixture — which is a second reason that tier is the better one.
* **It says nothing about the standard rung**, per above.
* **It says nothing about a repository with a manifest.** Every profile here was handed over. A real
  repository declares its own witness and `detect` finds it; that path is exercised by
  `tests/live.rs` on this project, not by this file.
* **`Unverified` is not a pass.** 11 of 59 trees produced no acceptance measurement. The criterion
  is about `Red`, and there are none — but a reader who wants "the gate verified 59 correct trees"
  should read "48".
