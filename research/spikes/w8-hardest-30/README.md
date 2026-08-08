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
python gate_step1_all90.py                                      # F18-F20: all 90, four tiers
```

`gate_step1_all90.py` supersedes `gate_step1_section4b.py` — it runs that script's tier as its
`fixture` column and reproduces its result — but both are kept, because F16 was published from the
narrower one. It self-tests before sweeping and aborts if the positive control fails.

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

**F18** gate step 1 across all 90 (`gate_step1_all90.py`) — 79 of 80 verifiers sound, 0 inconclusive,
and `fix_path_traversal` is the only one that passes its own wrong answer. No third defect of its kind.

**F19** the obvious generalisation of step 1 to generative tasks — run the verifier against an empty
workspace — finds nothing. `fix_path_traversal` FAILs that tier (its import raises before the
swallowed `assert`) and PASSes a null-implementation stub. Same cost, strictly stronger.

**F20** all 24 `strmatch` verifiers PASS a file whose entire content is a comment holding the searched
substrings, i.e. an empty page. F14's analytic claim, measured — and the sham is generated, not authored.

**F21** `extract_tasks.py` was double-escaping template literals, so `tasks.json` carried `\\n` where
the donor passes `\n`. Affects `py_csv_transform` only, in the direction that reads as "verifier
sound". Fixed at source; `rank.py` output byte-identical, so F16/F17/R10 are unaffected.

## Caveats

- `gate_fix_path_traversal.py` rewrites the donor's `/app/workspace` and `/tmp` paths to a temp
  workdir. Nothing else about the verifier is changed; the `try/except` is verbatim.
- `chk/cx` in `rank.py` is a crude exposure proxy (assertions and compound conditions, over the
  donor's own complexity score). It only orders tier 2 and never includes or excludes a task.
- The extraction bounds each task object by the next `name:` key rather than by parsing JS. It
  round-trips to the right counts (90 stable + 11 CTO, categories matching the results TSV exactly),
  which is the only check it gets.
- `gate_step1_all90.py` runs on the **host** toolchain (Windows, Python 3.14.5, Node 24.15.0), not in
  the `abcc-agents` container — no Docker daemon, no general-purpose WSL distro. A spurious FAIL would
  read as "verifier sound", so it attributes every failure to a named exception or a `process.exit`
  reject path, reports anything else as INCONCLUSIVE (none occurred), and runs a positive control
  first. A Linux-container re-run is an unspent cheap confirmation.
