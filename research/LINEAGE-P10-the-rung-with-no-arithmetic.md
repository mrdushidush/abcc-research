# LINEAGE P10 — the rung Self-Host is judged on, and the two clauses nobody writes

Session 12, 2026-09-14. `abcc` `c366440` → **`71f6aa8`**, `abcc-research` `bdcec67` → this commit,
both trees clean, neither pushed. Findings **F759–F762**. ▶ The queue's first item was *finish the
A4 arm*, which is hours of GPU and the machine was deliberately freed. **A3 is the item that needed
nothing but a desk**: `PLAN.md` puts Self-Host's exit at W13's M3, and `grep -rn consecutive
crates/` found the word in doc comments and **in no logic at all**.

🚨 **Two of these four findings are about the instruments rather than the subject, and both are
instruments I built in this session.** One is a console branch that can never be taken and that I had
already written; the other is a detector that under-reported a whole class, then over-reported on
ordinary text once widened. ▶ The rung reading itself ships, and the honest thing it prints about
this repository is **"There are none."**

---

## 1. 🚨 F759 — Theil–Sen's sign and Mann–Kendall's `S` **cannot disagree** over a positional window

M3's clause 2 is *human review minutes per merged change flat or falling*, which is a claim about
direction, and ten noisy points support one weakly. So the reading carries two estimators: a
**Theil–Sen** median pairwise slope for the direction and the size, and **Mann–Kendall**'s exact
two-sided p beside it for the strength.

▶ **I wrote an `estimators_disagree` predicate for the console to print, and it is a branch that can
never be taken.** The x values of a window are *positions*, so every pairwise denominator is a
positive index difference and the **sign** of each pairwise slope is just the sign of `y_j - y_i` —
which is exactly the term Mann–Kendall sums. For the median to be negative, more than half the pair
signs must be negative; for `S` to be positive, more must be positive than negative. Both cannot
hold. The even-length case lands on `S = 0` rather than on a disagreement.

**Brute-forced: every window of length 2–7 over four distinct values, exhaustively, plus 200,000
random windows of length 2–12 — 221,840 in all, ties included, because ties are where a
disagreement would hide. Zero.**

🚨 **The consequence is the part worth quoting.** The p is a statement about **strength only**. It can
say the direction is weakly supported; it can never say the direction is the other one. A console
that offered *the estimators disagree* would be offering a reading the arithmetic forbids — and the
reason it nearly shipped is that *two estimators can disagree* is true in general and false here, for
a reason that lives in the x values rather than in either estimator.

▶ It ships **inverted**, as `Trend::direction_is_undisputed`, with the proof in the doc comment and a
property test over 2,000 random windows, so that an estimator swap has to argue with a test rather
than with a comment.

## 2. F760 — M3 is **four** clauses and **two of them have no writer anywhere in the workspace**

Read at `research/W13-codev.md:345`, M3 is: **ten consecutive M2 tasks**, with **review minutes per
merged change flat or falling**, **no human edit to the agent's diff**, and **surviving defects from
those ten tracked at 30 and 90 days**.

| # | clause | on the log? |
|---|---|---|
| 1 | ten consecutive M2 tasks | ✅ `Reviewed::crossed_boundary` |
| 2 | minutes per merged change flat or falling | ✅ `Reviewed::seconds` |
| 3 | no human edit to the agent's diff | ❌ **nothing writes it** |
| 4 | surviving defects at 30 and 90 days | ❌ **OQ-W13-3, unspecified** |

Clauses 1 and 2 are arithmetic over rows that exist. Clause 4 is an open question W13 left open on
purpose. **Clause 3 has no mechanism and no open question either** — it is simply not recorded that a
person edited a diff before it landed, and `abcc land` applies a patch without asking whether the
worktree was touched by hand first.

🚨 **So the reading may compute two clauses of four and must never be spelled `reached_m3`.** The
shipped name is `Climb::countable_half`, and `Climb::cannot_say()` carries the other two **as data
rather than as a comment**, printed every time the half is. *Ten changes, falling* is exactly the
sentence a reader finishes as *so M3 is reached*, and the instrument built to judge a milestone is
the worst possible place for that sentence to be completable.

⚠ **And clause 1 is only as sharp as an operator's flag.** `--boundary` on `abcc review` still has no
written rule behind it — that is OQ-W13-1, and it is one decision, one doc line and one test. The
reading counts the flag; **it does not define it**, and it says so where it is defined.

## 3. The build — `Ladder::climb` and `abcc replay`, at `83a93fe`

`crates/abcc-core/src/climb.rs`, wired into `abcc replay`. **677 tests** (was 657), fmt and clippy
clean. Three choices, all stated in the module docs rather than buried:

1. 🚨 **The window is the most recent ten and never the best ten.** Searching a history for its
   flattest run is choosing the answer — F657's defect one level up. A test builds a ladder that
   *holds* a ten-change falling run and asserts the reading still refuses, because the run is no
   longer the recent one.
2. ⚠ **The order is the order reviews were recorded**, because it is the only order the ladder has.
   It is merge order exactly when changes are reviewed in the order they land, and nothing enforces
   that. `Landed::seq` gives landing order for changes that came through `abcc land`, so the day
   every row has one, this should be re-read against it.
3. ⚠ **A change that crossed no boundary does not break the run** — it is not an M2 task, so it is
   not a break in them — but `Climb::interleaved` hands the caller the count the stricter reading
   turns on, rather than the reading picking one silently.

🚨 **No floating point anywhere.** Every slope is an exact rational held as `(num, den)` and every p
is a count over a count, so the reading is identical on every platform and a test asserts the whole
of it to the last digit. The exact p is Mann–Kendall's null read through `S = N - 2D`, where `D` is
the inversion count, so the distribution is the Mahonian numbers by the sliding-window recurrence;
`u128` holds `30!`, and the window is ten.

▶ **The robustness claim is pointed at the thing it replaced, which is the only way it means
anything.** On a falling window with one four-hour review at the end, the test asserts the
least-squares numerator is **+441,300 — RISING** — while the Theil–Sen median is unmoved at **−10 s
per change**. A property that is never tested against the estimator it displaced is a preference.

**On this repository's own log the page now reads:**

```
W13's ladder — human review minutes per merged change
  nothing recorded: none of these 12118 event(s) is a review, so the ladder has no
  baseline — and a ladder whose baseline starts at Self-Host is unfalsifiable.
  `abcc review <change> <minutes>` writes one. The minutes it records are a person's.
  M3 wants 10 boundary-crossing changes, minutes flat or falling. There are none.
```

That is the honest answer, and it is **the first time in the project's history that the archive could
give it.** ⚠ It stays that way until David types `abcc review` — `by` defaults to `operator()`, so an
agent running it fabricates the exact measurement Self-Host is judged on.

## 4. 🚨 F761 — a detector that **under-reported a whole class, then over-reported on plain text**

Reading `replay.rs` for the ladder, its `StateEndings` doc block rendered as `ð¨` — the bytes of 🚨
re-encoded as UTF-8 a second time, so the file holds `C3 B0 C2 9F C2 9A C2 A8` where it means
`F0 9F 9A A8`. It arrived with the file at `4a3f9c2` on 2026-09-05 and had been read past for nine
days. **Nothing compiles differently, nothing warns, and a diff not looking for it shows a line that
reads fine.**

▶ **The first detector found 5 occurrences across both repositories and looked thorough doing it.**
It defined a candidate run as `[\u0080-\u00ff]+` — which is right for the **latin-1** round trip and
wrong for the **cp1252** one, because cp1252 maps `0x9F` to U+0178 and `0x9A` to U+0161, **outside
that range**. So the run breaks in the middle of every cp1252 case and the scan finds none of them.
`ðŸš¨` — the form that turned out to be in seventeen corpus task files — is exactly that shape.

**With both codecs tried: 55, in 20 files.** 🚨 **A detector that under-reports is indistinguishable
from a clean result**, which is F749's rule one layer down: the instrument's own coverage is a fact
that has to be measured, not assumed from a zero.

▶ **Then, widened, it over-reported.** In `research/spikes/w4-estimator/README.md` it flagged
`8.71×–17.66×`. With a real multiplication sign and an en dash that is `D7 96` in cp1252, and `D7 96`
is valid UTF-8 for a Hebrew zayin. **It is ordinary text.** No arithmetic separates that from a true
hit — only reading the line does.

🚨 **So the kept instrument prints and never repairs**, and exits 0 on a hit rather than failing a
build on one. The repair was a separate pass over a **named list of three substitutions**, asserting
that no demanglable run was left behind that it did not make — and that assertion **failed first, and
correctly**, on a hand-typed key that had cp1252's `0x9A` as U+009A instead of U+0161. It matched
nothing and would have silently repaired nothing. The keys are now **derived from the true character
rather than typed**.

## 5. 🚨 F762 — two `contains` assertions passed over the sentence between them

The rung page shipped one sentence broken. A `\`-continued string literal ended up as a single line
with **fourteen literal spaces** in the middle, so `abcc replay` printed:

```
  M3 wants 10 boundary-crossing changes, minutes flat or falling.              There are none.
```

The tests were green. They were:

```rust
assert!(page.contains("M3 wants 10 boundary-crossing changes"), ...);
assert!(page.contains("There are none."), ...);
```

▶ **Each half is present, so each assertion is true, and the defect is entirely in the join neither
of them spans.** This is the same shape as session 11's `--3way` test that had been *passing while
proving nothing* — a test that asserts the pieces it was easy to name rather than the thing a person
would see.

✅ **Repaired by asserting across the joins, and then mutation-tested**: the exact defect was
reproduced at all three sites in the printer and **all three tests fail**; removing it restores
green. ⚠ **The mutation test is the part that matters.** Widening the assertions and re-running is
not evidence — the assertions were green before and after. Only breaking the thing on purpose shows
they now have teeth.

## 6. The repairs, and one artifact deliberately left corrupt

| commit | repo | what |
|---|---|---|
| `2453d92` | abcc | five double-encoded characters in `StateEndings`' doc block |
| `d849131` | research | 26 in `caveats` prose across seventeen `od` task files |
| `71f6aa8` | abcc | the comment restating F656 counted **one tree too many** |
| `f128eb3` | research | `research/tools/mojibake.py`, kept, with a `--check` control |

⚠ **Nothing parses `caveats` or `[[gate.evidence]].detail`** — they are provenance a person reads —
so no measurement moved. One of them was damaging its own arithmetic: the password task's caveat
names `café-au-lait` as the example reducing to *eleven characters*, and `cafÃ©-au-lait` does not.

🚨 **`research/spikes/w6-judge/census-out.txt` keeps its 23 and is NOT repaired.** It is recorded
output from a spike, and editing a record of what a program printed to make it prettier is
falsifying an artifact. `--check` pins those 23, which is **one control doing two jobs**: if the
count ever drops, either somebody tidied the artifact or the detector stopped detecting, and both
need to be loud. The false positive in the w4 README is pinned at 1 for the same reason — named, so
nobody repairs it.

▶ **On `71f6aa8`:** DEBUG-P4 §6 has **two** trees at 544 passed, and the second is `a5738` — the one
tree the gate *was* asked about. Two passed; **one** of the five skipped ones did. F656 is right and
only the restatement was wrong, which is the failure a number acquires crossing from a table into
prose.

## 7. What is owed next

1. ▶ **The A4 arm, and it is the only thing here that needs the GPU.** Three of twelve attempts flew
   before session 11 was cut short. ~7 more Change-phase attempts take the cumulative post-fix to
   0 of ~34 against 9.5%, **p ≈ 0.03**. 🚨 **Run the `run_tests` mirror every time** — the story is
   only about `diagnostics` if `run_tests` recovers in the same cohort, and in the cohort measured so
   far **both checkers fell**, which is the task-size confound rather than a failed fix.
2. 🚨 **A2 and B1 are David's and they are one command and one sentence.** `c366440` is the first
   change `abcc review` could ever be typed against, and **the ladder still has no row**, so
   everything in §3 is an instrument with no data. B1 — *what is a module boundary in this
   workspace* — binds clause 1 and is one doc line and one test.
3. ⏸ **A5** (F744's repair, three priced options), **A6**, and F721 · F723 · F727 · F733 are still
   parked and still his.

⚠ **Nothing in this session moved the blocker.** The blocker is the repository's own declared
standard (F673/F672) and the arm that measures whether the model reaches for the tool that now runs
it. This session built the reading that will say whether the loop, once it closes, is *getting
cheaper* — which is the question M3 asks and the one nothing could previously answer.
