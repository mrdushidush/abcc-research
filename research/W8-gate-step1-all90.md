# W8 — Gate step 1 across all 90 ABCC tasks

Answers **open question 2** of `W8-hardest-30.md`: *should gate step 1 be run across all 90 now?*
David said yes on 2026-08-08. It was the one piece of import work needing no approval and no authored
content, and its purpose was to turn "56 executing verifiers, strength unknown" into a number.

Status: **result, not a proposal.** Nothing here needs approving. One consequence does — see
"What this changes" at the end.

Findings are numbered from F18 to continue `W8-hardest-30.md`, which ends at F17.

Retrieval and run date for every claim: **2026-08-08**. Donor: `agent-battle-command-center` at
`d5528ea`.

---

## What was run

One new throwaway program, `research/spikes/w8-hardest-30/gate_step1_all90.py`, reproducible.

Section 4B was cheap to gate because the donor ships a real buggy fixture for it (`BUGGY_FILES`,
`ultimate-100-task-test.js:1706-1717`). The other 80 tasks generate from nothing, so there is no
fixture to be wrong — the wrong answer has to be **synthesised**, and the only synthesis needing no
per-task authoring is a *null implementation*. Four tiers, each of them a wrong answer, so each
of them must FAIL:

| tier | n | the artifact is |
|---|---|---|
| `absent` | 80 | never produced — nothing exists |
| `stub` | 80 | present and imports cleanly, and does nothing: every symbol is a no-op returning `None` |
| `sham` | 24 | a file whose entire content is a comment holding every substring the verifier searches for |
| `fixture` | 10 | the donor's own buggy file — F16's tier, re-run so all four appear in one table |

**Fidelity.** Both donor validation paths run the same string (`task.validation`) as `python3 -c` /
`node -e` with cwd `/app/workspace`, scoring `exit 0 AND "PASS" in stdout`:

- local — `ultimate-100-task-test.js:2788-2814` (`runValidationLocal`, via `docker exec`)
- server — `packages/agents/src/main.py:524-589` (`/run-validation`), reached from
  `packages/api/src/services/asyncValidationService.ts:432`; the script sends the same string with a
  `LANG=` prefix (`ultimate-100-task-test.js:2695-2709`)

Traced both because the recorded runs used the server path, and a second copy of the verifier would
have made this whole exercise measure the wrong thing. There is no second copy.

**Where it ran.** On the host (Windows, Python 3.14.5, Node 24.15.0), not in the `abcc-agents`
container — the Docker daemon is not running and there is no general-purpose WSL distro. That matters
in one direction only: a spurious FAIL would read as *"this verifier is sound"*, which is exactly how
a defect hides. Three controls close it, and all three are in the script:

1. **Every failure is attributed.** 80/80 `absent` and 79/80 `stub` failures resolve to a named
   exception at line start or to the verifier's own `process.exit(1)` reject path. **Zero
   inconclusive.** Only stdlib is imported across all 80 verifiers (`sys`, `json`), so a
   `ModuleNotFoundError` can only ever be about `tasks.*`.
2. **The error class changes between tiers** — `absent` gives `ModuleNotFoundError` / `Cannot find
   module`, `stub` gives `AssertionError` / `TypeError` / `AttributeError`. That transition only
   happens if the stub really was imported, which is what proves the tier is testing what it claims.
3. **A positive control**, run before the sweep and aborting it on failure: a hand-written correct
   artifact must PASS. `py_json_response` and `node_json_response` both PASS. This is gate step 2 for
   two tasks, and it rules out a harness that silently never loads anything and calls all 80 sound.

---

## Findings

### F18. Gate step 1, all 90: 79 of 80 sound, and no new defect of the F15 class

```
  GATE STEP 1 - n=80: SOUND=79  BROKEN=1  INCONCLUSIVE=0
      fix_path_traversal       passes: stub, fixture

  by tier:
    absent   n=80  FAIL=80
    stub     n=80  FAIL=79  PASS=1
    fixture  n=10  FAIL=9  PASS=1

  step 1 by shape:
    py-import     n=39  BROKEN=1  SOUND=38
    node-require  n=17  SOUND=17
    py-open       n=24  SOUND=24
    none          n=10  NO VERIFIER=10
```

`fix_path_traversal` is the **only** verifier in the suite that passes its own wrong answer at step 1,
and the `fixture` column reproduces F16 exactly, including `fix_sql_inject` failing for the wrong
reason (`AttributeError: 'NoneType' object has no attribute 'execute'` — a crash on a `None` db, not
detection). So the classifying pass that turned F8 into F13/F15 has now been run to exhaustion at this
gate point: **there is no third `fix_path_traversal`.**

This is the reassuring half of the result, and it is worth stating plainly because the previous two
documents only ever found defects. 55 of the 56 executing verifiers reject both an absent artifact and
an inert one.

### F19. `absent` is too weak to be the gate, and `stub` is what does the work

Gate step 1 phrased as "the untouched fixture must FAIL" has an obvious generalisation to generative
tasks — run the verifier against an empty workspace — and that generalisation would have found
**nothing**:

| | `absent` | `stub` |
|---|---|---|
| `fix_path_traversal` | **FAIL** | **PASS** |

Its import statement sits outside the `try`, so an empty workspace raises `ModuleNotFoundError` before
control ever reaches the swallowed `assert`. The defect is invisible to the weaker tier and obvious to
the stronger one. Both tiers cost the same to run.

**For the importer this is the transferable part:** the cheap mechanical gate is not "does the
verifier notice absence" but "does the verifier notice a *no-op*". A null-implementation stub needs no
authoring — a module whose `__getattr__` returns a function returning `None`, or a node `Proxy` whose
every export is a no-op — and it is strictly stronger for free.

### F20. All 24 string-match verifiers accept a file whose entire content is a comment

F14 asserted this analytically — "a sham with the tokens in a comment passes". It is now measured, and
the sham did not have to be authored:

```
  GATE STEP 3, mechanical sham - n=24: SOUND=0  BROKEN=24
    sham     n=24  PASS=24
```

Every one of the 24 `strmatch` assertions is a **positive** presence or count check — there is no
`not in` anywhere in the 24 — so a document containing each searched substring five times satisfies
all of them, including the two count thresholds (`saas_features` `c>=2`, `portfolio_projects` `c>=3`).
Wrapped in `<!-- -->` or `/* */`, the artifact renders as an **empty page** and every verifier says
PASS.

Two consequences, one for each side of the ledger:

- The sham for these 24 is **generated, not authored**. That is the one place the 30/60 split gets
  cheaper than `W8-hardest-30.md` estimated.
- These verifiers cannot distinguish a landing page from nothing at all. They pass gate step 1 (an
  empty file FAILs, a missing file FAILs) and fail gate step 3 by construction.

### F21. The extraction was double-escaping template literals; one verifier affected, F16 and F17 are not

Found while checking that the string reaching `python3 -c` is the string the donor sends.
`extract_tasks.py`'s walkers capture `\x` escape pairs verbatim so the closing backtick is not
misread, but the value was never unescaped afterwards — so `tasks.json` carried `\\n` where the donor
passes `\n`.

The one-directional consequence is the point: `py_csv_transform`'s verifier builds its input as
`parse_csv('name,age\nAlice,30\n...')`. With the extra backslash Python sees a literal backslash-n,
the CSV parses as one row, `assert len(rows)==3` fails, and the verifier **FAILs for a reason that has
nothing to do with the artifact** — scored as "this verifier is sound".

Blast radius, measured rather than assumed:

- **1 of 80** verifiers contains a backslash at all: `py_csv_transform`.
- **No section-4B verifier contains one**, so the **F16 table is unaffected**.
- Fixed at source (`js_unescape` in `extract_tasks.py`), `tasks.json` regenerated. `rank.py`'s output
  is **byte-identical** before and after, so **F17 and R10 are unaffected**. The regeneration also
  corrected 10 task *descriptions* — the ts/go prompts that embed whole file bodies (F13).

Worth keeping for the importer: the donor's verifier source has to survive one JS-string decode before
it is executable, and getting it wrong fails silently in the direction that looks like good news.

---

## Where the suite now stands

Every task whose verifier is **demonstrated** not to reject at least one wrong answer:

| | n | how it fails | evidence |
|---|---|---|---|
| no verifier at all | 10 | `validation: null`; `passed = execSuccess` | F13 |
| passes its own unfixed fixture | 1 | `fix_path_traversal` | F15, F18 |
| passes an intact vulnerability | 1 | `fix_sql_inject` | F8 (inspection) |
| passes an empty page | 24 | all `strmatch` | **F20** |
| **total** | **36 of 90** | | |

The remaining **54** are executing verifiers that are step-1 sound with no step-3 evidence either way.
That is exactly the population `R10`'s authored shams probe, and it matches R10's "54 importable".

**Step-1 SOUND is necessary, not sufficient, and the suite contains its own proof.**
`fix_sql_inject` is step-1 SOUND here — it rejects absence, inertness, and its own unfixed fixture —
and F8 still showed it passing a solution with the SQL injection fully intact. Step 1 bounds the
defect rate **from below**. Only an authored sham closes it.

## What this changes

**Nothing about R9 or R10.** The ranking is unaffected: `rank.py`'s output is byte-identical, and the
one step-1 defect found was already in tier 1 with its disposition already set.

**One thing needs David, and it is a consequence rather than a new question.** His standing rule is
*anything that fails the gate is quarantined-with-baseline*. F20 measures 24 tasks failing gate point
3. Applied literally, the rule quarantines them, and the usable suite goes from 90 to 54 — a third of
the corpus, and all 15 of section 2.

`R9` already anticipated this and recommended the other route: **record at suite level that section 2
is unverifiable by construction** rather than quarantining task by task, because a `landing` task has
no ground truth to be wrong about in the first place. F20 turns that recommendation from a judgement
into a measurement. The two readings differ in what the headline number means, not in what gets
imported, so this is worth deciding before the importer writes its first aggregate — not before it
starts.

## Confidence: high

The population, the tier definitions and the per-task verdicts are all measured, with every failure
attributed and a positive control that would have caught the harness lying. The one soft spot is
platform: this ran on Windows against the host toolchain rather than in `abcc-agents`. The controls
above make an unattributed FAIL detectable, and none occurred — but the honest statement is that a
Linux-container re-run is a cheap confirmation nobody has done, and the `absent`/`stub` tier
transition is the thing to check if it ever disagrees.

## Open questions

1. **Do the 24 (F20) get quarantined, or recorded as unverifiable at suite level?** See above. R9
   recommends the latter.
2. **Does the null-implementation stub belong in the real importer's gate?** It is strictly stronger
   than the absent-artifact check at the same cost (F19), and it is mechanical. Recommend yes, as
   gate step 1b, applied to all 90 rather than just the 30.
3. Unchanged from `W8-hardest-30.md`: the sham for the 54 executing verifiers still has to be authored
   against the *rewritten* verifier, which orders the import pass.
