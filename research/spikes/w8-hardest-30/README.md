# Spike: ranking ABCC's 90 tasks, and testing its verifiers (THROWAWAY)

Run 2026-08-08. Supports `research/W8-hardest-30.md`. **This is throwaway code**, kept only as
evidence for the findings it produced. None of it is a proposal for the real importer, which is Rust.

Reads two things and writes nothing outside this directory:

- `prestudy/data/abcc-100task-results.tsv` (in this repo)
- `D:\dev\agent-battle-command-center` at `d5528ea`, `scripts/ultimate-100-task-test.js`

## Order to run

```
python extract_tasks.py "D:\dev\agent-battle-command-center"   # -> tasks.json (101 task objects)
python rank.py                                                  # the pool, the wall, the 30
python gate_step1_section4b.py                                  # F16: 9 of 10 detect their own bug
python gate_fix_path_traversal.py                               # F15: this verifier cannot fail
```

`tasks.json` is generated; it is the extraction, not a source of truth.

## What it found

**F11** the stable pool is 90, not 100 — the last 10 slots are a CTO experiment whose task content
changed between the only two runs it appeared in.

**F12** `fetch failed` at 2 s (collapse run, endpoint down) and `fetch failed` at 307 s (clean runs,
the 300 s task timeout) are the same string with opposite meaning. Exclude the collapse run by run
id, never by error text — and count the timeouts as difficulty.

**F13** all 5 `typescript` and all 5 `go` tasks have `validation: null`, and the runner's fallback is
`passed = execSuccess` (`:3168`), the agent-execution endpoint's own success flag. Ten tasks scored
on "the agent didn't crash", counting toward the 95/100 headline.

**F14** the 90 split 56 `exec` / 24 `strmatch` / 10 `none` by what the verifier actually establishes.

**F15** `fix_path_traversal`'s verifier wraps `assert r is None` in `except (ValueError, Exception):
pass`, which catches the `AssertionError` the assert exists to raise. Ran the three-point gate:

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

Worse than `fix_sql_inject` (F8), which at least fails its own fixture. This one fails gate step 1.
The recorded data agrees with what the code predicts: 0 failures and 2 timeouts across 4 clean runs,
because `failed` is not a verdict it can produce.

**F16** gate step 1 across all ten of section 4B — 9 of 10 verifiers do detect their own bug. This
point of the gate needs no authored content, so it can be run across the whole suite cheaply.

**F17** 12 of 90 tasks show any failure or timeout at all; the other 78 swept every clean run.
Duration cannot break the tie — below the timeout it tracks output length, not difficulty.

## Caveats

- `gate_fix_path_traversal.py` rewrites the donor's `/app/workspace` and `/tmp` paths to a temp
  workdir. Nothing else about the verifier is changed; the `try/except` is verbatim.
- `chk/cx` in `rank.py` is a crude exposure proxy (assertions and compound conditions, over the
  donor's own complexity score). It only orders tier 2 and never includes or excludes a task.
- The extraction bounds each task object by the next `name:` key rather than by parsing JS. It
  round-trips to the right counts (90 stable + 11 CTO, categories matching the results TSV exactly),
  which is the only check it gets.
