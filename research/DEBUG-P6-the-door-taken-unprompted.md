# DEBUG P6 — the door taken unprompted, and the lint that is the same edit as the error

**Status: four arms flown, six attempts, and the change DEBUG P5 could only demonstrate by hand
fired on its own.** 🎉 **`a7484` ended `budget_exhausted` with a two-file change in the tree**, so
F655's gate measured it — structural green, acceptance `Unmeasured`, veto refusing a tree that
does not build — instead of telling the operator the attempt produced no artifact. That is the
rescue case, prospective and unassisted, **1 of 6 since F655 shipped**. 🚨 The session's larger
finding is why no tree ever clears the standard rung: **the model is graded by `cargo fmt --check`
and `cargo clippy -D warnings`, is never told so, and the tool it is handed to check its own work
runs `cargo check`, which sees neither** (F673). Three of tonight's trees pass **550 of 550
tests** and are refused by house style. At the desk beforehand the findings archive was shown to
**parse** — 656 of 668 defined individually and **0 issued-then-lost** — while **supersession was
shown to be underivable** (38 real edges, the obvious rule writes 67). Findings **F668–F678**;
next free number is **F679**. Built 2026-09-07/08 against `D:\dev\abcc` at `38763a6`, model
`qwen3.6-35b-a3b-mtp@iq3_s` at `-c 40960 --parallel 1`, prompt sha `6917f0ccaf0f83c3` (329 chars)
asserted before every flight.

---

## 1. The ledger probe: the archive parses, and nothing was lost

David asked whether the memory files should become a database. The honest way to answer it was to
try to build the index and see what the prose gives up, so `research/tools/fread.py` reads all 116
research docs plus the 37 memory files and separates **definitions** from **references**.

It is derived-only. It writes a TSV and never touches a source, which is the property that makes
the whole idea safe: a regenerable index cannot be the thing that loses data.

| | |
|---|---|
| docs scanned | 136 |
| definition-shaped rows | 999 |
| **distinct findings defined** | **656 of 668 (98.2%)** |
| range-covered only | 11 — appears only inside `F206–F212` |
| cited, never defined | 1 |
| **never mentioned** | **0** |
| accounted for | **668 of 668** |
| rows per finding | **1.52** — findings are restated, not stated once |

▶ **The first pass got 105 of 668, and every miss was a convention rather than a fog.** The
archive defines findings **six ways**, and each one cost a separate rule:

1. `**F664** — claim` — bolded number at the head of a paragraph
2. `- **F620** — claim` / `| **F123** | claim |` — list item and table row
3. `### 🚨🚨 F600 — the method` — a **heading**, emoji before the number
4. `## 3. 🚨 F633 — the announcement is on the wire` — a heading with a **section number** first
5. `⚠ **F574 — the two axes are NOT orthogonal**` — bold spanning the whole claim, number not
   individually bolded
6. `| F218 — every gate input is Measured | W6 |` — an unbolded summary-table row

Shape 4 alone was worth 58 findings; shape 5 was worth 65. **The rate went 15% → 88.5% → 98.2% on
three widenings of the same reader over the same unchanged corpus** — which is the honest headline:
the number a probe reports about a corpus is a claim about the probe first.

## 2. 🚨 The one thing that cannot be back-extracted, and it is the one thing worth storing

The reason to want a database here was never storage. It was that the memory files are palimpsests
— *"no longer the bottleneck"*, *"overtaken by seven sorties"*, *"do NOT credit F649"* — and a
reader has to reconstruct which claim is live. **Supersession is the payload.** It is also the one
field that does not survive being derived.

Deriving it looks easy: a block that carries retraction vocabulary and names another finding is a
retraction of that finding. Measured against the corpus, that rule **manufactures edges**:

| | |
|---|---|
| correction edges actually present in the prose | **38** |
| edges the derived rule would write | **67** |
| over-assertion | **+76%** |
| worst single row | **F290, claiming to supersede 10 findings** |

The mechanism is a cartesian product, not a near miss. `supersedes` becomes *(a retraction word
appears somewhere in this block)* × *(every finding number mentioned in the block)*, and findings
cite each other constantly — 289 of 999 rows name another finding. So `F657`'s row asserts it
supersedes `F641`, `F648`, `F649` and `F651`, when what it actually says is **do not credit F649**
and the other three are the context that makes the sentence readable.

⚠ **And the vocabulary has a shape no keyword rule can resolve even in principle**, because the
archive argues with itself in place:

* `**F531 is not retracted and it is not fixed.**`
* `**F83 is not retracted and is not the authority here.**`
* `(F74, with the method corrected by F75)`

The first two assert that a retraction did **not** happen, in a sentence built from the word
*retracted*. A ledger that flips one of those produces confident green over a claim its author
explicitly refused to withdraw — the same shape as F667, where a harness that could not tell
*nothing ran* from *nothing failed* was worth less than no harness.

▶ **So the ruling the probe supports: derive everything except supersession, and author that.** A
`Supersedes: F649 (reason)` line costs one line at writing time and is exact. Back-filling the 38
existing edges is a human read done once, not a script.

⚠ **And the index is not the thing to move.** `MEMORY.md` is 36 lines and 14.8 KB because retraction
notes get bolted onto entries with nowhere else to put *this is now false*. That is this section's
problem, not a schema problem. A file read for free at session start beats a query that has to be
remembered; the failure mode of a queried memory is acting on stale context without ever asking.

### The probe measured itself, which is not a joke

Writing this document changed the corpus it reports on. Section 2's bullet list above quotes
`**F83 is not retracted…**` as an example, and the reader parsed that quotation as a **definition of
F83**, then swallowed the following bullets and recorded F83 as superseding F74, F75 and F550. Every
one of those is wrong, and all of it came from a document *about* the ledger.

▶ **A corpus that contains documents about the corpus cannot be read by position alone.** This is
the concrete argument for an explicit marker — a definition should say it is one, rather than being
inferred from where it sits on a line.

## 3. `a6689`, to the line: one blank line and one `match` arm

DEBUG P5 left `a6689` as *the best tree this subject has produced* and two mechanical edits from
Green, without saying which two. They are now named, read out of the log rather than re-derived.

The tree is a real commit — the checkpoint sha `e19e3d32` is reachable in `D:\dev\abcc`, four files,
**+13 lines, 0 deletions**, and it passes structural (exit 0), acceptance (**550 run, 550 passed, 0
failed**) and veto (nothing vetoed).

**Edit 1 — `crates/abcc/src/cli.rs:284`.** The `standard` rung's own refusal carries the diff:

```
Diff in ...\worktrees\t6530-6687\crates\abcc\src\cli.rs:284:
     return Err(CliError::Version(env!("CARGO_PKG_VERSION").to_owned()));
 }
-
 // The two global flags are pulled out first so they can appear anywhere,
```

One stray blank line — the model left **two** where rustfmt wants one. That is the entire content of
the refusal that stopped a 550-test-green tree from landing.

**Edit 2 — `crates/abcc/tests/cli.rs`.** This one was never reported, because F666 already said why:
the standard rung is a **conjunction**, cheapest first, and the first refusal ends it. `cargo fmt
--check` refused, so `cargo clippy --all-targets -- -D warnings` never ran.

## 4. 🚨 The trap: the arm the compiler demands is the arm the lint refuses

This subject is named after `error[E0004]` — a non-exhaustive match. Adding a `CliError::Version`
variant forces the model to extend a match in the test file, or the tree does not compile. Here is
what it wrote:

```rust
let complaint = match parse(verb) {
    Ok(_) | Err(CliError::Help) => String::new(),
    Err(CliError::Version(_)) => String::new(),   // <- identical body
    Err(CliError::Usage(said)) => said,
};
```

🚨 **The obvious way to satisfy the compiler is precisely what `clippy::match_same_arms` refuses.**
The new arm's body is `String::new()`, and so is the body of the arm above it. The compiler demands
an edit; the repository's declared standard refuses the shape that edit naturally takes. The way
through is to extend the existing or-pattern rather than add an arm — a different edit, not a
tidier one.

The lint chain was verified without running it, because an arm was in flight and wall clock is part
of what these arms measure:

* `Cargo.toml` workspace: `pedantic = { level = "warn", priority = -1 }`
* all **nine** crates carry `[lints] workspace = true`, so `crates/abcc` inherits it
* the rung runs `cargo clippy --all-targets -- -D warnings`, and `--all-targets` is what makes it
  lint `tests/`, which is where the arm is
* `match_same_arms` is pedantic, so `-D warnings` promotes it to a refusal

▶ **This reframes F658.** *Five of five compiling trees trip `match_same_arms`* reads like a
quality problem — the model writes careless code. It is better read as a **property of the
subject**: on this task the compiler error and the lint refusal are the same edit, so tripping it
is the default path and clearing it takes knowledge the error message does not carry.

⚠ **And the repository does not obey this lint either.** `crates/abcc-core/src/task.rs:469` carries
`#[allow(clippy::match_same_arms)]`, with a comment giving the reason: *"this match is the
transition table and a reader has to be able to see which commands a state accepts. Collapsing
`Deployed | Engaged` into one arm would save a line and hide the fact that both are reapable."* The
project reserves the right to judge the lint wrong and say so in a line of prose. The agent has the
same `#[allow]` available and has never once reached for it — in five arms it has neither merged the
arm nor suppressed the lint.

## 5. The arm: four sorties, and what it was allowed to be

DEBUG P5 ruled that the next arm for F655 **is a re-fly and nothing else** — the change needs an
attempt that exhausts its budget *with a changed tree*, which the log says happens about half the
time and did not happen in four. So nothing was changed to chase it. Same subject at `38763a6`,
same model, same `-c 40960 --parallel 1`, and the prompt read back from `abcc replay t4886` rather
than retyped: **329 characters, sha `6917f0ccaf0f83c3`, asserted before every task was created.**

Four tasks queued at once so the running fleet took them back to back on one slot — the same shape
as arms 1–7, and no idle GPU between them.

⚠ **One contamination, mine, recorded rather than hidden.** The prompt was written to
`D:\dev\abcc\.arm_prompt.txt` to keep it byte-identical, and that is inside the subject. It is not
in `.gitignore`, and `list_files` is built with `.hidden(false)`, so **it appeared in the root
listing the model reads** — in arms 8 and 9. It carries the task prompt and nothing else, so it
cannot have told the model anything it was not already given, but it is a difference from arms 1–7.
It was moved out to the scratchpad before arms 10 and 11, and the subject verified clean at
`38763a6`. ▶ Next time the anchor file lives outside the repository under test; the checkpoint
stages the whole tree, and *the whole tree* includes what the operator left in it.

## 6. 🚨🚨 Why no tree ever clears the standard rung: it is judged on a criterion it cannot observe

Four attempts on this subject have reached the standard rung. **None passed.** Read together with
what the change phase can actually see, the reason stops being about model quality.

| attempt | arm | fmt | clippy | acceptance |
|---|---|---|---|---|
| `a5738` | 4 | passed | **refused** — `write!` newline **+ `match_same_arms`** | — |
| `a6689` | 7 | **refused** — stray blank line, `cli.rs:284` | not reached | 550/550 |
| `a6865` | 8 | **refused** — import order, `main.rs:8` | not reached | 550/550 |
| `a7085` | 9 | passed | **refused** — `match_same_arms`, `lib.rs:89` | 550/550 |

**The standard rung is:**

```
cargo fmt --check -- --color=never
cargo clippy --all-targets -- -D warnings
```

**What the Change phase is given to check itself with:**

```
diagnostics  ->  cargo check --all-targets      # no rustfmt, no clippy
run_tests    ->  cargo test
```

🚨 **`cargo check` cannot see either half of the standard.** The model's entire in-loop feedback
signal is blind to the criterion that refuses it, so it iterates to green on `cargo check` and
`cargo test` — which it reaches, 550 of 550 — and stops, because by its own instruments it is done.

⚠ **It is not a capability problem.** Builders reaches `Tier::Exec` — it calls `run_tests` and `git`
— so `bash` is admitted and `cargo fmt` was always one call away. It is a **knowledge** problem: the
brief that opens the Change phase says *"Make the change… say what you changed and where, and stop
asking for tools"* and **never mentions the standard, rustfmt, or clippy at all.** The rung's
refusal is composed after the phase has ended, so the model never reads it either.

▶ **So the honest form of F658 is not *the model writes code that trips `match_same_arms`*.** It is:
*the model is graded on two commands it is never told about and cannot run through the tool it was
handed for checking its work.* Both remedies clippy itself prints — `#[allow(clippy::match_same_arms)]`
or *merge the patterns into a single arm* — arrive in text no model in this project has ever seen.

⚠ **And the rung is passable**, so this is not a gate that refuses everything: `a2995` and `a3176`
passed `cargo fmt --check` and `cargo clippy -D warnings` together, on a different subject
(`Seq::is_origin`). The standard is reachable. This subject has never reached it.

⚠ **What this does not license.** W7's ruling stands — *a prompt binds only as far as the model
complies*, measured at 39 of 50 for the shipped wrapper and **0 of 50** for the best re-aimed
candidate. Naming the standard in the brief is a **string flown as an arm**, not a fix, and it must
be flown as one before it is credited. The cheaper and more binding change is to make `diagnostics`
report what the gate will measure, because that is a tool result rather than a request.

## 7. The other door, taken without being offered

DEBUG P3 asked whether the model takes the `write_file` door **when it is actually offered**, and
F650 answered *we still do not know*, because the offer needs the server to fold twice running. Four
flights and ten attempts later the trigger had still never fired.

In `a6865` the model used `write_file` anyway. The write-tier sequence is unambiguous:

| seq | call | outcome |
|---|---|---|
| 6918 / 6922 / 6926 | `apply_patch` | ok, ok, ok |
| 6942 | `apply_patch` | **refused** — `NoMatch`: *hunk 2 does not match… 3 of its 6 context lines* |
| 6949 | `write_file` | **ok** |
| 6970 | `apply_patch` | ok |

🚨 **The refusal it responded to was `NoMatch`, and `NoMatch` does not name `write_file`.** F649's
sentence lives on the **`NotADiff`** variant — the transcript-shaped diff, the server's fold — and
that variant did not fire once in this attempt. The model was refused on an ordinary
one-context-line-out miss, read a file, and switched tools on its own.

**Scoped honestly, this is a first and a small one.** Across the eleven E0004 arm tasks there are
**18 attempts and exactly one `write_file` call** — `a6865`, the fifteenth. The preceding fourteen
have none, which reproduces the *0 of 10* the F650 re-flies recorded.

⚠ **But the behaviour is not new, and this matters for what may be credited to F649.** Over the
whole `--version` subject the model has called `write_file` in **9 of 48 attempts**, and eight of
those nine — `a479`, `a645`, `a1440`, `a1711`, `a1857`, `a1968`, `a3714`, `a8` — **predate F649
entirely**, most of them following a run of `apply_patch` refusals in exactly this shape.

▶ **So F650's question stays open and F657's ruling gets firmer.** *Does the model take the door
when the refusal names it?* is still unanswered, because the refusal that preceded the one firing
did not name it. What is now measured is the weaker and more useful fact: **the fallback exists in
the model without the prompt, and it is rare** — one attempt in eighteen inside the arms, nine in
forty-eight over the subject's whole history.

⚠ **And the per-run `apply_patch` rate must still not be quoted.** Over the eleven arm tasks it is
**29 of 62 = 47%**; `a6865` alone is 4 of 5 (80%) and `a7085` is 1 of 5 (20%), on a byte-identical
prompt an hour apart. That is F657's sequence — 5/5, 1/2, 1/1, 1/6, 0/13 — continuing, and it is the
reason the aggregate is the only figure worth carrying.

## 8. 🚨 The pincer, shown on both horns in one night

Section 4 argued from the desk that the compiler and the lint want opposite edits. Tonight's four
sorties demonstrated both horns on the same 329-character prompt, hours apart:

| attempt | what it did with the test file's `match` | what refused it |
|---|---|---|
| `a7247` (arm 10) | **no arm added** — changed only `cli.rs`, `main.rs` | **veto**: `error[E0004]: non-exhaustive patterns` — the tree does not build |
| `a7085` (arm 9) | arm added, **own body** `=> String::new()` | **standard**: `clippy::match_same_arms` |
| `a6689` (arm 7) | arm added, own body | standard: fmt refused first; the same duplicate arm sits underneath |
| `a6865` (arm 8) | merged, but at the **outer** level — see §11, still not the accepted form | standard: fmt, on **import order** elsewhere |

▶ **Do nothing and the tree does not compile; do the obvious thing and the standard refuses it.**
⚠ And the obvious *fix* is refused too: §11 shows the merge has to be **nested** —
`Err(CliError::Help | CliError::Version)`, not `Err(CliError::Help) | Err(CliError::Version)` —
because `clippy::unnested_or_patterns` is pedantic as well. `a6865` wrote the outer form, so it
would have been refused at clippy too had it ever cleared `cargo fmt`.

🚨 **Every one of the four failed on a different rung for a different reason, and none of the four
reasons is the task.** The task — *add a `--version` flag that prints the crate version and exits
successfully* — is solved in all four trees. `a6689`, `a6865` and `a7085` each pass **550 of 550
tests**. What refuses them is `error[E0004]` once and the repository's declared house style three
times.

## 9. Findings

**F668** — ✅ **The findings archive parses, and nothing in it was lost.** 656 of 668 numbers are
defined individually (98.2%), 11 appear only inside a range, 1 is cited without a definition, and
**0 were issued and then lost**. The archive defines findings **six ways**, and the parse rate went
**15% → 88.5% → 98.2%** across three widenings of the same reader over an unchanged corpus. ▶ The
transferable part: *a coverage number about a corpus is a claim about the reader first.*

**F669** — 🚨 **Supersession is the one field worth storing and the one that cannot be derived.**
The prose holds **38** correction edges; the obvious derivation rule writes **67** (+76%), one row
claiming ten. The rule degenerates into *(a retraction word appears in this block)* × *(every
finding the block cites)*, and findings cite each other in 289 of 999 rows. The archive also argues
in the negative — `**F531 is not retracted and it is not fixed**` — which no keyword rule resolves.
▶ Derive everything else; **author supersession** as an explicit line.

**F670** — ⚠ **The probe measured itself.** Writing this document added rows to the corpus it
reports on: section 2's quotation of `**F83 is not retracted…**` parsed as a *definition of F83*
superseding F74, F75 and F550, all of it wrong. ▶ A corpus containing documents about the corpus
cannot be read by position alone, which is the argument for an explicit marker over an inferred one.

**F671** — ✅ **`a6689`'s two blockers, named.** One stray blank line at `crates/abcc/src/cli.rs:284`
and one duplicate `match` arm in `crates/abcc/tests/cli.rs`. The second was never reported because
F666's conjunction ends at the first refusal, and `cargo fmt` is cheapest and runs first.

**F672** — 🚨 **The compiler and the lint demand opposite edits, and both horns were flown tonight.**
Adding the `Version` variant forces a new `match` arm or the tree does not build (`a7247`:
`error[E0004]`, refused by veto). Adding it the obvious way duplicates a body and
`clippy::match_same_arms` refuses (`a7085`, confirmed in the field). The only path between is
merging the or-pattern, which `a6865` found. ▶ **F658 is better read as a property of the subject
than of the model.**

**F673** — 🚨🚨 **The model is graded on a criterion it cannot observe.** The standard rung is
`cargo fmt --check` then `cargo clippy --all-targets -- -D warnings`. The Change phase's own
instruments are `diagnostics` → **`cargo check --all-targets`** and `run_tests` → `cargo test`,
**neither of which runs rustfmt or clippy**, and the brief that opens the phase never names the
standard. It is not a ceiling problem — Builders reaches `Tier::Exec`, so `bash` and therefore
`cargo fmt` were always one call away. The model iterates to green on its own instruments, reaches
550 of 550, and stops. Four attempts have reached the standard rung on this subject and **none
passed**; the rung itself is passable — `a2995` and `a3176` cleared it on another subject.

**F674** — 🎉 **The `write_file` door was taken, and nobody offered it.** In `a6865` an
`apply_patch` was refused as **`NoMatch`** — the variant that does **not** name `write_file` — and
the next write-tier call was `write_file`, which succeeded. F649's sentence lives on `NotADiff`,
which did not fire once in the attempt. ⚠ Scoped: **1 `write_file` call in 18 arm-block attempts**,
the first after fourteen without one. ⚠ And not new — the model has used the fallback in **9 of 48**
attempts on this subject, eight of them predating F649. ▶ F650's question stays open; F657's *do not
credit F649* gets firmer.

**F675** — 🚨 **The rescue base rate depends on which unmeasured ending, and the blended number
hides two opposite populations.** Over 37 unmeasured attempts on this subject, 17 (46%) left a
changed tree — the *"about half"* DEBUG P5 carried. Split by reason it is **`budget_exhausted`: 11
of 13 (85%)** against **`truncated_at_cap`: 1 of 12 (8%)**. ▶ F655's rescue case is far commoner
than credited *when the budget is rounds*, and nearly absent when the cap is completion tokens.

**F676** — ⚠ **F655's path fired on a third kind of ending, and the tree was still empty.** `a7016`
ended `truncated_at_cap`, the gate was asked, structural exited 1. The wiring generalises beyond
rounds-exhaustion as designed; **the rescue is still scored 0**, now over more attempts.

**F677** — ⚠ **Two instruments were wrong before their subjects were, both failing into plausible
output.** The landing monitor read task state as `list(state)[0]`, which returns the **key**
`"state"` and never the value, so it reported *all four arms done* on its first poll with three
still queued. And *"the first tree ever to clear `cargo fmt`"* was wrong — `a5738` reached clippy in
arm 4, and four older attempts passed the whole rung. ▶ F667's family, twice in one session: **the
check that cannot fail is the one to distrust.**

**F679** — 🎉 **`a7085` is two edits from Green, both edits must be *nested*, and it took three
tries to find that.** In a scratch worktree the model's tree is already `cargo fmt`-clean; merging
the duplicate arms **at the outer level** (`A(Help) | A(Version)`) is refused again by
**`clippy::unnested_or_patterns`** and by rustfmt; only the nested form
`A(Help | Version)` passes. With that in `lib.rs` and `tests/cli.rs` — **two lines** — the tree
returns `cargo fmt` **0**, `cargo clippy --all-targets -- -D warnings` **0**, and **550 passed / 0
failed across 68 binaries**, matching the gate's own count exactly. **The first `--version` tree in
this project's history to clear the whole standard rung.** ⚠ This also corrects §8's first reading:
`a6865` used the *outer* form, so it would have been refused at clippy too. ▶ **The three tries are
the finding.** Each fix revealed the next lint only when the tool was run — and the model is given
no pass at that information at all, which is F673 stated as a loop rather than a list.

## 10. 🎉 The rescue fired, prospectively, on the sixth attempt

DEBUG P5 closed with F655 *proven wired and proven cheap, and its value case still only
retrospective* — 0 of 4 attempts had ended with an exhausted budget **and** work in the tree. Arm
11's retry, `a7484`, is that attempt.

```
ended       uncertain — budget_exhausted, "24 rounds"
structural  measured   exit 0   2 file(s) changed: crates/abcc/src/cli.rs, crates/abcc/src/main.rs
acceptance  UNMEASURED          error[E0308]: mismatched types
veto        measured   exit 1   the tree does not build — error[E0308]
```

**Before F655 this attempt would have been told it produced no artifact.** Instead the operator is
handed the three things that are actually true: the model ran out of rounds, it left a two-file
change behind, and **that change does not compile** —

```
281 |  return Err(CliError::Version(env!("CARGO_PKG_VERSION").to_string()));
    |  error[E0308]: mismatched types … help: try using a conversion method
```

▶ **This is the whole of the change's value case, in the field, unassisted.** The measurement is
`Unmeasured` for acceptance and `Measured` for structural and veto in the same ladder — ADR-0009's
honest-outcome type doing exactly what it exists for: *the suite is red* and *there was no suite*
kept apart, on a tree nobody declared finished.

⚠ **It is one attempt.** F655's rescue is now **1 of 6** since it shipped, against a base rate of
**11 of 13 for budget-exhausted endings** (F675). Two of tonight's six drew `truncated_at_cap`,
where the tree is empty 11 times in 12, so the arm's spread is what F675 predicts rather than
evidence about F655.

**F678** — 🎉 **F655's rescue fired in the field, unassisted, and it is the change's whole value
case.** `a7484` ran out of its 24 rounds having left `cli.rs` and `main.rs` changed. The gate was
asked, structural measured **exit 0 / 2 files**, acceptance came back **`Unmeasured`** because the
tree does not build, and veto refused it on `error[E0308]: mismatched types` at `cli.rs:281`. Before
F655 the operator would have been told the attempt produced no artifact. ⚠ **1 of 6 since F655
shipped**, against F675's base rate of 11 of 13 for budget-exhausted endings; two of tonight's six
drew `truncated_at_cap`, where the tree is empty 11 times in 12. ▶ ADR-0009's honest-outcome type
earning its keep: *the suite is red* and *there was no suite* kept apart in one ladder.

## 11. 🎉 Two edits from Green — verified, and it took me three tries to make them

`a7085`'s tree was taken into a scratch worktree and asked the repository's own standard, directly.

**The starting point checks out.** `cargo fmt --check` printed **nothing** — the model's tree is
already correctly formatted — and `cargo clippy --all-targets -- -D warnings` refused it with
`these match arms have identical bodies`, reproducing the rung exactly.

**Then the fix, which is where the interesting part is.** Three iterations, each one guided by
clippy's own output, and *only* discoverable by running it:

| try | the edit | what refused it |
|---|---|---|
| 1 | `A(Help) => 0,` / `A(Version) => 0,` — the model's own | `clippy::match_same_arms` |
| 2 | `A(Help)`<br>`| A(Version) => 0,` — merged at the **outer** level | **`clippy::unnested_or_patterns`**, plus `cargo fmt` wanting one line |
| 3 | `A(Help | Version) => 0,` — **nested inside** `Cli(...)` | nothing |

Applying try 3 in both places — `crates/abcc/src/lib.rs` and `crates/abcc/tests/cli.rs`, **two lines
changed, four removed and two added** — gives:

```
cargo fmt --check -- --color=never          exit 0
cargo clippy --all-targets -- -D warnings   exit 0
cargo test                                  550 passed, 0 failed, across 68 binaries
```

▶ **That is the first `--version` tree in this project's history to clear the whole standard rung**,
and the acceptance count matches the gate's own 550 to the digit.

🚨 **The three tries are the finding, not the two edits.** I knew the trap, had read F658, had
clippy's exact suggestion text in front of me, and still needed three passes — because each fix
reveals the next lint *only when the tool is run*. The model is given zero passes at that
information: `cargo check` reports none of it, the rung runs after the phase has ended, and nothing
in the brief says the standard exists. ▶ **F673 is not a story about a careless model. It is a
closed loop the model is not in.**

## 12. What this leaves

▶ **The database question, answered with a measurement rather than a preference.** Build a findings
ledger; make it **derived** from the markdown, so it can never be the thing that loses data; and
**author supersession** rather than parsing it (F669). Do **not** move the memory index into it —
`MEMORY.md` is read for free at session start, and a query that has to be remembered is a worse
failure mode than a file that is simply there. An MCP server buys a round-trip and a process that
can fail, and fixes nothing the parser did not already fix. ⏸ **David's call; nothing was built.**

▶ **The one-line convention that makes the rest cheap.** A finding should say it is one. Six
implicit shapes cost six rules and still leave the reader guessing at a document that *quotes*
findings (F670). `Supersedes: F649 (reason)` and a stable definition marker cost one line each at
writing time and remove the whole class.

🚨 **The blocker on this subject has a name and it is not `apply_patch`.** Four trees have reached
the standard rung and none passed it, while three of them pass **550 of 550 tests**. The reason is
F673: **the model is graded by `cargo fmt --check` and `cargo clippy -D warnings`, is never told so,
and the tool it is given to check its own work runs `cargo check`, which sees neither.** Two changes
are available and they are not equal — teaching `diagnostics` to report what the gate will measure
is a **tool result**; naming the standard in the brief is a **string**, and W7 already measured what
strings are worth (39 of 50 shipped, 0 of 50 for the best re-aimed candidate). ⏸ Both are David's.

✅ **F655 no longer needs an arm.** `a7484` gave it the prospective demonstration it was missing
(F678), so the open item DEBUG P5 left is closed by observation rather than argument. ⚠ **Still do
not raise `rounds`**, and read any future arm by *which ending it drew*: the rescue case is **11 of
13 when the budget is rounds** and **1 of 12 at the completion cap** (F675).

⏸ **Seven tasks were in `AwaitingOrders` before tonight and four more joined them.** Nothing was
accepted or rejected; that is David's. 🎉 **`a7085` is the one to read first** — F679 shows it is
**two nested-or-pattern edits from a fully green tree**: `cargo fmt` 0, `cargo clippy -D warnings` 0,
550 passed / 0 failed. `a6865` and `a6689` are the next two.

🚨 **And the decision DEBUG P5 left is untouched and now has more evidence under it:** may a
gate-green tree the model never declared finished be `Accomplished`? Tonight produced three trees
that are *not* gate-green, for reasons that have nothing to do with whether the work is right.
