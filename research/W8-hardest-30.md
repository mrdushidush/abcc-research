# W8 - "The 30 hardest" ABCC tasks

Sub-deliverable 2 of W8, and the first open question of the import pass. Answers open question 3
of `W8-corpus-format.md`, which David scoped on 2026-08-08: **author the three-point gate across the
30 hardest ABCC tasks only**; the other 70 import on the two-point gate.

Status: **approved 2026-08-08.** David accepted R9 (read "hardest" as *where a sham is most likely to
pass*), so R10's 30 is the set that gets a `sham/` authored. He also set the disposition for R11 item 1
— the 10 no-verifier tasks are **quarantined-with-baseline** — and answered open question 2 with yes,
which produced `W8-gate-step1-all90.md` (findings F18-F21). Per R9 the selection field should be named
`gate3` rather than `hardest` when the corpus format encodes it.

Findings are numbered from F11 to continue `W8-corpus-format.md`, which ends at F10.

---

## Question

Which 30 of ABCC's 100 tasks get a `sham/` authored for them?

The corpus-format doc predicted the shape of the answer: rank by observed failure rate, expect the
suite to saturate, expect to need a tie-break on complexity band then category. Two of those three
predictions held. The third was wrong in a way that matters, and it is most of this document.

## Method

Everything below is derived from two sources and nothing else:

- `prestudy/data/abcc-100task-results.tsv` - 481 rows, the 7 recorded runs.
- `agent-battle-command-center` at `d5528ea`, `scripts/ultimate-100-task-test.js` - the suite
  definition and the execution engine, read at source.

Three throwaway programs, all in `research/spikes/w8-hardest-30/`, all reproducible:

- `extract_tasks.py` - pulls all 101 task objects with their verifiers out of the donor JS. Needed a
  string walker rather than a regex, because `validation` is a template literal spanning lines for
  the go and typescript tasks.
- `rank.py` - joins the extraction to the results and applies the selection rule below.
- `gate_fix_path_traversal.py`, `gate_step1_section4b.py` - **ran** the donor's own verifiers against
  the donor's own fixtures, the same way F8 was established.

Retrieval date for every claim: **2026-08-08**.

---

## Findings

### F11. The candidate pool is 90 tasks, not 100

The suite's last 10 slots are a CTO-decomposition experiment (`react_cto`, `cto_decomposed`) whose
task content changed between runs - a weather app in `2026-02-24T18-14-53`, a recipe app in
`2026-02-24T21-10-56`. Five of the ten appear exactly once ever.

Extracting from the donor source agrees exactly: 101 task objects, of which 90 are stable and 11 are
CTO. The category counts match the results TSV row for row (landing 15, py_api 13, node_api 12,
react 10, security 10, bugfix 10, typescript 5, go 5, py_data 5, mini 5).

So the population the 30 is drawn from is 90, and the split is 30/60 rather than 30/70. The CTO
section is already out of scope for v1 of the format, which is consistent - it just needs saying
before someone tries to import it.

Observation counts: 80 tasks have 4 clean runs, 10 (the react section) have 5.

### F12. `fetch failed` means two opposite things, and the difference is difficulty signal

The data README says to exclude the `2026-02-26T11-04-01` run as an infrastructure collapse. Correct,
but the reason matters for the ranking:

| | count | median duration | meaning |
|---|---|---|---|
| errors in the collapse run | 72 | **2 s** | endpoint down |
| errors in the 5 clean runs | 12 | **307 s** | the 300 s `TASK_TIMEOUT_MS` |

Identical error text, opposite cause. **Exclude the collapse run by run id, never by error string** -
a filter on `error == 'fetch failed'` would throw away the clean runs' timeouts too.

And those 12 are not noise to be dropped. A task the subject could not finish in five minutes is a
hard task. They are counted as difficulty here, alongside genuine failures.

### F13. Ten of the ninety tasks have no verifier at all

All 5 `typescript` and all 5 `go` tasks carry `validation: null`. The runner's fallback
(`ultimate-100-task-test.js:3166-3169`):

```js
} else {
  // No validation defined — consider passed if execution succeeded
  passed = execSuccess;
}
```

and `execSuccess` is `Boolean(execJson.success)` (`:3140`) - the agent-execution endpoint's own
success flag. It reports that the agent ran, not that the artifact works. **These ten tasks are
scored PASS whenever the agent does not crash**, and they count toward the 95/100 headline.

There is a second problem underneath. Their prompts hand the agent the complete file body and say to
write it out - `ts_pipe`'s description (`:1840-1859`) contains the entire finished `pipe.ts`,
self-test included, followed by "DO NOT just output the code - you MUST call file_write." Even with a
working verifier these tasks would measure tool-calling compliance, not capability.

This is larger than F8. F8 found one verifier that does not verify; this is ten tasks with nothing to
verify with, found by classification rather than by luck.

### F14. Verifier strength splits the 90 three ways

| Class | n | Categories | What a `sham/` would prove |
|---|---|---|---|
| `exec` - imports the artifact and asserts on behaviour | **56** | py_api 13, node_api 12, security 10, bugfix 10, py_data 5, mini 5, react 1 | genuinely unknown |
| `strmatch` - reads the file, asserts substrings present | **24** | landing 15, react 9 | nothing - a sham with the tokens in a comment passes, and the task has no ground truth to be wrong about |
| `none` - `validation: null` | **10** | typescript 5, go 5 | nothing - every sham passes by construction (F13) |

This is the finding that replaces the predicted complexity/category tie-break. See the
recommendation.

### F15. `fix_path_traversal`'s verifier cannot fail. Ran it.

Found by looking for the F8 pattern systematically rather than waiting to trip over it. Exactly one
verifier in the 90 wraps its assertions in a broad `except` (`:1738-1744`):

```python
try:
    r=read_file('/tmp','../etc/passwd')
    assert r is None
except (ValueError, Exception):
    pass
print('PASS')
```

`AssertionError` is a subclass of `Exception`, so the `assert` that is supposed to be the check is
caught by the handler and discarded. `print('PASS')` is unconditional for any implementation that
imports.

Ran the full three-point gate (`gate_fix_path_traversal.py`):

```
--- gate step 1: untouched fixture must FAIL ---
  fixture (vulnerable)      donor verdict: PASS
                            ground truth:  LEAKED:'root:x:0:0:root:/root:/bin/sh\n'
--- gate step 2: fixture + refsol must PASS ---
  refsol (correct fix)      donor verdict: PASS
                            ground truth:  contained
--- gate step 3: sham must FAIL ---
  sham (traversal intact)   donor verdict: PASS
                            ground truth:  LEAKED:'root:x:0:0:root:/root:/bin/sh\n'
```

This is **worse than `fix_sql_inject`**, which at least fails its own fixture. `fix_path_traversal`
fails gate step 1, the cheapest point, and so has never measured anything across all 7 recorded runs.

The recorded data confirms the prediction the code makes: across 4 clean runs `fix_path_traversal`
has **0 failures and 2 timeouts**. It can only ever be `passed` or `error`. Its two `passed` results
mean the agent finished, nothing more.

### F16. Gate step 1 across all ten of section 4B: nine pass

Since step 1 needs no authored content - seed the donor's own buggy file, run the donor's own
verifier - it can be run across a whole section for free (`gate_step1_section4b.py`):

```
  fix_sql_inject            FAIL  AttributeError: 'NoneType' object has no attribute 'execute'
  fix_xss_reflect           FAIL  AssertionError
  fix_path_traversal        PASS      <-- verifier passes its own bug
  fix_weak_hash             FAIL  AssertionError
  fix_hardcoded_secret      FAIL  AssertionError
  fix_insecure_random       FAIL  AssertionError
  fix_missing_validation    FAIL  AssertionError
  fix_info_leak             FAIL  AssertionError
  fix_open_redirect         FAIL  AssertionError
  fix_type_confusion        FAIL  AssertionError
```

Nine of ten detect their own bug, which is a genuinely reassuring result for the section carrying
most of the suite's difficulty. `fix_sql_inject` fails for the wrong reason - the `AttributeError` is
a crash on a `None` db, not detection, as F8 already recorded.

Worth noting what this buys: two of the three gate points are mechanical and can be run across all 90
tasks in an afternoon. Only the sham needs authoring, which is exactly why the 30/60 split exists.

### F17. The suite saturates at 12 tasks, and duration cannot break the tie

Across the 5 clean runs, **12 of 90 tasks show any negative signal at all** - failure or timeout:

| # | task | cat | cx | runs | F | TO | rate | verifier |
|---|---|---|---|---|---|---|---|---|
| 1 | `fix_xss_reflect` | bugfix | 7 | 4 | 3 | 1 | 1.00 | exec |
| 2 | `fix_weak_hash` | bugfix | 6 | 4 | 2 | 2 | 1.00 | exec |
| 3 | `fix_insecure_random` | bugfix | 6 | 4 | 4 | 0 | 1.00 | exec |
| 4 | `fix_missing_validation` | bugfix | 7 | 4 | 4 | 0 | 1.00 | exec |
| 5 | `sec_xss_filter` | security | 7 | 4 | 3 | 0 | 0.75 | exec |
| 6 | `fix_path_traversal` | bugfix | 7 | 4 | 0 | 2 | 0.50 | exec (broken, F15) |
| 7 | `py_rate_limiter` | py_api | 8 | 4 | 0 | 2 | 0.50 | exec |
| 8 | `fix_open_redirect` | bugfix | 7 | 4 | 0 | 1 | 0.25 | exec |
| 9 | `fix_hardcoded_secret` | bugfix | 5 | 4 | 0 | 1 | 0.25 | exec |
| 10 | `fix_sql_inject` | bugfix | 7 | 4 | 0 | 1 | 0.25 | exec (broken, F8) |
| 11 | `ts_pipe` | typescript | 7 | 4 | 0 | 1 | 0.25 | **none** (F13) |
| 12 | `fix_type_confusion` | bugfix | 7 | 4 | 0 | 1 | 0.25 | exec |

**Nine of the ten `bugfix` tasks are here** - every one except `fix_info_leak`. The other 78 passed
every clean run.

The predicted tie-break was complexity band then category. Complexity is not usable: it is the
donor's own authored guess, it takes four values across the whole suite (5/6/7/8), and 233 of 481
rows are complexity 7. Duration is not usable either - among the 78 clean-sweep tasks the median
duration spread is 10 s to 244 s with a p50 of 23 s, and below the timeout that number tracks how
much output the task asks for, not how hard it is. Ranking by it would put three
`portfolio_*` landing-page tasks in the top 20.

---

## Recommendation

### R9. Read "hardest" as *where a sham is most likely to pass*

The third gate point adds exactly one thing: a deliberately wrong solution that must be rejected. So
the 30 should be the 30 where authoring one is real work with an unknown answer. On that reading, two
whole blocks drop out - **not because they are easy, but because their gate outcome is already
known**:

- the 10 `none` tasks (F13): every sham passes by construction, so writing one is a formality;
- the 24 `strmatch` tasks (F14): a sham with the right tokens in a comment passes, and a
  "make a landing page with a hero section" task has no ground truth to be wrong about anyway.

That leaves the 56 executing verifiers as the only population where the answer is not knowable in
advance.

**This is a departure from the brief and it is David's to overrule.** He asked for the 30 hardest;
this proposes the 30 most-shammable, which is not the same set. Concretely it drops `ts_pipe` -
observed-hard, rank 11 - because it has no verifier to sham against, and it adds 19 tasks with no
observed difficulty at all. The argument for it is that a sham authored against the other definition
would spend most of its 30 slots proving things already proven. The cost is that "hardest" no longer
means what it says, and the doc should call the field `gate3` rather than `hardest` if this is
accepted.

### R10. The 30

Two tiers. Tier 1 is all 20 of section 4; tier 2 is 10 more from the remaining 36 executing
verifiers, ranked by how little the verifier checks relative to what the task asks, capped at 3 per
category so the tier does not collapse onto `node_api`.

Section 4 goes in whole for three reasons, not one:

1. it holds 10 of the 12 observed-hard tasks (F17) - the other two are `py_rate_limiter` and
   `ts_pipe`;
2. it is the only block asserting a **negative** property - "the vulnerability is gone" - which is
   the class assertion-chains demonstrably fail at; both known non-verifying verifiers are here
   (F8, F15);
3. it is the only section where the agent reads an existing file instead of generating from nothing,
   which is the closest ABCC gets to the repo work W8 exists to measure.

| # | task | category | sec | cx | F/TO | chk/cx | basis |
|---|---|---|---|---|---|---|---|
| 1 | `fix_insecure_random` | bugfix | 4 | 6 | 4/0 | 0.67 | observed |
| 2 | `fix_missing_validation` | bugfix | 4 | 7 | 4/0 | 0.43 | observed |
| 3 | `fix_weak_hash` | bugfix | 4 | 6 | 2/2 | 0.83 | observed |
| 4 | `fix_xss_reflect` | bugfix | 4 | 7 | 3/1 | 0.29 | observed |
| 5 | `sec_xss_filter` | security | 4 | 7 | 3/0 | 0.43 | observed |
| 6 | `fix_path_traversal` | bugfix | 4 | 7 | 0/2 | 0.14 | observed; **already failed the gate (F15)** |
| 7 | `fix_hardcoded_secret` | bugfix | 4 | 5 | 0/1 | 0.40 | observed |
| 8 | `fix_open_redirect` | bugfix | 4 | 7 | 0/1 | 0.29 | observed |
| 9 | `fix_sql_inject` | bugfix | 4 | 7 | 0/1 | 0.29 | observed; **already failed the gate (F8)** |
| 10 | `fix_type_confusion` | bugfix | 4 | 7 | 0/1 | 0.71 | observed |
| 11 | `fix_info_leak` | bugfix | 4 | 6 | 0/0 | 0.67 | section 4 |
| 12 | `sec_brute_force` | security | 4 | 7 | 0/0 | 0.43 | section 4 |
| 13 | `sec_csp_builder` | security | 4 | 7 | 0/0 | 0.43 | section 4 |
| 14 | `sec_csrf_token` | security | 4 | 7 | 0/0 | 0.71 | section 4 |
| 15 | `sec_input_validator` | security | 4 | 7 | 0/0 | 0.71 | section 4 |
| 16 | `sec_jwt_simple` | security | 4 | 8 | 0/0 | 0.62 | section 4 |
| 17 | `sec_password_hash` | security | 4 | 8 | 0/0 | 0.50 | section 4 |
| 18 | `sec_rate_limit` | security | 4 | 8 | 0/0 | 0.50 | section 4 |
| 19 | `sec_sanitize_html` | security | 4 | 7 | 0/0 | 0.43 | section 4 |
| 20 | `sec_sanitize_sql` | security | 4 | 7 | 0/0 | 0.57 | section 4 |
| 21 | `py_rate_limiter` | py_api | 3 | 8 | 0/2 | 0.75 | observed |
| 22 | `py_text_pipeline` | py_data | 5 | 8 | 0/0 | 0.25 | under-checked |
| 23 | `node_router` | node_api | 3 | 7 | 0/0 | 0.29 | under-checked |
| 24 | `py_router` | py_api | 3 | 7 | 0/0 | 0.29 | under-checked |
| 25 | `node_query_parser` | node_api | 3 | 6 | 0/0 | 0.33 | under-checked |
| 26 | `node_server_main` | node_api | 3 | 8 | 0/0 | 0.38 | under-checked |
| 27 | `py_server_main` | py_api | 3 | 8 | 0/0 | 0.38 | under-checked |
| 28 | `mini_markdown` | mini | 5 | 8 | 0/0 | 0.50 | under-checked |
| 29 | `tm_utils` | react | 1 | 6 | 0/0 | 0.50 | under-checked |
| 30 | `mini_todo_cli` | mini | 5 | 8 | 0/0 | 0.50 | under-checked |

`chk/cx` is the exposure proxy: distinct behavioural claims the verifier makes, divided by the
donor's own complexity score. Low means the verifier checks little relative to what the task asks.
It is a crude number and it is only used to order tier 2, never to include or exclude.

Spread: `bugfix` 10, `security` 10, `py_api` 3, `node_api` 3, `mini` 2, `py_data` 1, `react` 1.
Sections 4/3/5/1 = 20/6/3/1.

**Section 2 (`landing`, 15 tasks) gets zero slots**, and that is the rule working rather than
failing: all 15 are `strmatch` against generated marketing pages. If David wants section 2
represented, the honest way is not a sham - it is to say that section 2 is unverifiable by
construction and record it as such at suite level.

### R11. Three things that need a disposition, not a sham

These came out of the analysis and are decisions, not work:

1. **The 10 `none` tasks (typescript, go).** They have no verifier and their prompts contain the
   answer. Options: import quarantined-with-baseline like `fix_sql_inject`; import with a synthesized
   verifier (recorded as `rewritten`, breaking comparability); or drop. Recommend
   **quarantine-with-baseline**, consistent with the disposition David already set.
   **Decided 2026-08-08: quarantine-with-baseline.** The corpus loses its only `typescript` and `go`
   coverage, which is the accepted cost.
2. **`fix_path_traversal`.** Fails gate step 1. Same disposition as `fix_sql_inject` by David's
   standing rule - quarantine-with-baseline - so it needs no new decision, only recording.
3. **The 24 `strmatch` tasks.** They pass the two-point gate and will import cleanly. The caveat that
   their verifier establishes presence rather than correctness belongs at suite level, in the same
   block as the F7 isolation caveat.

Running count of the 90: **2 quarantined outright** (`fix_sql_inject`, `fix_path_traversal`),
**10 recommended for quarantine** (F13), **24 importable with a suite-level caveat**,
**54 importable**, of which 28 will get a sham authored.

---

## Effect on fun

Neutral-to-positive, in a way worth noting.

None of this is the operator-control work that makes 2.0 interesting, and it is more verifier
archaeology than the corpus-format doc budgeted for. But three short scripts found that 11 of ABCC's
90 tasks are scored by something that cannot report a wrong answer, and the alternative was
discovering it later from a number that looked fine. The 95/100 headline is now known to include 10
tasks scored on "the agent didn't crash" and one verifier that prints PASS unconditionally - plus a
twelfth, `fix_sql_inject`, that fails its fixture but passes an unfixed vulnerability.

The 30/60 split is also cheaper than it looked. Two of the three gate points need no authored content
at all and can be run across all 90 tasks mechanically (F16) - so the 60 are not ungated, they are
two-point gated by a script, and only the sham is hand work.

## Open questions

1. **Does R9's redefinition stand?** The one real decision in this document. If "hardest" is to keep
   its literal meaning, `ts_pipe` returns to the list and something drops - but see F13 for why that
   slot buys nothing.
2. ~~**Should gate step 1 be run across all 90 now?**~~ **Done — `W8-gate-step1-all90.md` (F18-F21).**
   79 of 80 sound, 0 inconclusive, `fix_path_traversal` the only step-1 defect, so there is no third
   one. Two things this document got wrong: the "other 34" were *not* a foregone conclusion — the 24
   `strmatch` verifiers turned out to be mechanically shammable, which is F20 — and the obvious
   empty-workspace generalisation of step 1 would have found nothing at all (F19).
3. **Does the sham get authored against the donor verifier or the rewritten one?** For the U100
   import every verifier is `rewritten` (paths, contract, execution model - corpus-format doc §B), so
   the sham tests the rewrite. That is the right target, but it means a sham cannot be authored until
   the verifier rewrite for that task is done, which orders the import pass.
4. **`chk/cx` is a proxy and only orders tier 2.** A better exposure measure would compare the
   verifier's assertions against the behaviours the prompt actually specifies. Not worth building
   unless tier 2's composition turns out to matter.

## Confidence: high on the pool and the defects, medium on the selection

**High** on F11-F17. The pool size, the two error meanings, the ten missing verifiers and the
`fix_path_traversal` break are all read from the donor source and, for the last two, confirmed by
running the donor's own code against the donor's own fixtures. F15 in particular makes a prediction
about the recorded data (this task can never show a failure) that the recorded data confirms.

**Medium** on the selection itself. Tier 1 is well-founded - section 4 is where both known defects
are and where 11 of 12 observed-hard tasks are. Tier 2 rests on `chk/cx`, which is a crude proxy
ordering tasks that are otherwise indistinguishable in the data. If tier 2 turns out to matter, the
fix is open question 4.

**Low, and flagged:** nothing here says whether a *sham* will actually catch anything in the 28 not
already known broken. F8 and F15 were both found by inspection, not by the sham step, which is mild
evidence that inspection is the cheaper instrument and the sham is the confirmation.
