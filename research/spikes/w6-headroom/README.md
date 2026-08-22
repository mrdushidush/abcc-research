# w6-headroom — what verification actually buys over v1's syntax check

Probes run 2026-08-22 for **W6 item 4 (verification headroom)**. Findings **F297–F310** in
`research/W6-verification.md`.

§11's scope for the item: *"Automated verification is the biggest lever on cheap-model output
quality: type checks, linters, unit test generation, property-based testing, static analysis,
sandboxed execution. Quantify the headroom over V1's syntax-error auto-retry plus periodic frontier
review."*

So each of those is a **rung**, each rung is scored the same way — does its verdict move between a
tree the suite's own verifier accepts and one it rejects, and what does it cost — and the baseline
it is scored against is read out of v1's code rather than out of v1's README.

No scratchpad paths: every script resolves everything from its own location. Ground truth is a
program in this repository — `verify.sh` for the K suite (gate-sound at all three SPEC.md §9 points,
2026-08-17) and for Q56.

⚠ **Only half of this is re-runnable from a clean checkout.** The constructed population, the v1
channel replay and the property ceiling read `corpus/`, which is tracked. The two *real* populations
read `runs/`, which is **git-ignored local data** — 431 preserved agent workdirs from earlier
sessions. On a machine without them, `census.py` reports zero cells and the `results-*.json` files
committed here are the only record of those measurements. That is also why the result files are kept
in full rather than summarised.

## The two populations

| population | what it is | n | ground truth |
|---|---|---|---|
| **constructed** | for each K task: the unfixed fixture, the reference solution, the shipped sham | 9 | `verify.sh`, re-measured here |
| **real, K** | every preserved agent workdir from the K comparison and the W11 budget sweeps — repository bugfixes, 16–20 files | 54 | the verdict its run recorded, **re-measured here** |
| **real, Q56** | every preserved agent workdir for the Rust and Python Q56 tasks — small single-function tasks, v1's own workload shape | see `results-q56.json` | `verify.sh` (hidden tests) |

The Q56 corpus is five languages (rust 14, python 15, node 10, typescript 9, shell 8). Only the
Rust and Python halves are run here; the other three are W6 item 5's (language generality).

## Layout

| script | question | raw output |
|---|---|---|
| `common.py` | repo paths, the Git Bash + `python3` shim, workdir copies, the verifier call | — |
| `census.py` | which recorded cells still have a workdir, and what the run said about them | — |
| `instruments.py` | the rungs, one function each, all returning `verdict / ms / n` | — |
| `ladder.py` | run every rung over a population | `results-constructed.json`, `results-k.json`, `results-q56.json` |
| `add_entrypoint.py` | merge the `entrypoint` rung into an existing K result file without re-timing the rest | (in place) |
| `residue.py` | what a diff scanner sees: files added, deleted, modified, and the breadth of the change | `residue-results.json` |
| `v1_channel.py` | v1's `/run-validation` rule, reimplemented, against real trees | `v1-channel-results.json` |
| `gentests.py` | generated tests: written before the change, after it, and after a *wrong* change | `gentests-results.json` |
| `properties.py` | the property-test rung at its ceiling — invariants quoted from the fixture's own docs | `properties-results.json` |
| `analyse.py` | one table per question, over whatever result files exist | — |

```
python -m pip install ruff mypy hypothesis     # the rungs that are not in the stdlib
python census.py
python ladder.py constructed && python ladder.py k && python add_entrypoint.py
python residue.py && python v1_channel.py && python properties.py
python ladder.py q56                    # ~20 min, CPU only
python gentests.py 3                    # GPU, ~25 min, arms tdd + posthoc
python gentests.py 3 posthoc_sham       # GPU, ~10 min
python analyse.py
```

Held constants for the GPU probe, identical to W11 items 2–5: champion
`qwen3.6-35b-a3b-mtp@iq3_s`, loaded `-c 65536 --gpu max --parallel 1 -y`, nothing else resident,
LM Studio on `:1234`, temperature 0, `max_tokens` 8192.

## The rungs

Python (K, and the Python half of Q56):

| rung | what it is | v1's analogue |
|---|---|---|
| `syntax` | `python -m py_compile` over every file | **this is v1's baseline** (`code_validation.py:28`) |
| `ruff` / `ruff_all` | the linter, default rules and `--select ALL` | none |
| `mypy` / `mypy_strict` | the type checker, default and strict | none |
| `pytest` | the tests the repository already has | none |
| `entrypoint` | run the command the ticket itself names, and believe the exit code | v1's `validationCommand`, roughly |
| *(delta forms)* | the same, minus the findings the unfixed tree already had | none |

Rust (the Rust half of Q56): `cargo check`, `cargo clippy -D warnings`, `cargo test --lib`. There is
no syntax-only rung in Rust — the cheapest check is already the type check, which is itself a
finding about language generality.

## Runner hygiene

Five traps, most of which produce a *better-looking* number if you miss them:

1. 🚨 **The Q56 verifier leaves its hidden tests in the workdir.** Every preserved Q56 workdir
   contains `tests/hidden_gate.rs` or `hidden_gate_test.py` — the answer key, written by the
   verifier during the original run. An instrument that runs "the project's tests" post hoc reads
   it and reports a perfect gate. `instruments.verifier_residue()` measures the residue rather than
   guessing it: it runs the verifier against a pristine fixture and diffs the tree.
2. **The K overlays are CRLF and the fixtures are LF**, so a byte diff calls every line of every
   touched file changed. `gentests.diff_of` normalises newlines first.
3. **`results-q56.json`'s Rust rows carry a one-character `detail`.** `_rust_result` indexed a
   string where it meant to index a list, so the recorded diagnostic for `cargo check` / `clippy` /
   `cargo test` reads `"e"`. Fixed here after the run; the **verdicts and counts are unaffected**
   (they come from the exit code), and the clippy diagnostics quoted in F307 were re-derived by
   re-running the rung on the same cells.
4. 🚨 **A timeout that kills only the direct child hangs the whole run.** One Q56 attempt
   (`Q13/deny-first-edit`) loops forever on an input its own fixture test never supplies. The
   verifier's `pytest` running it was orphaned by `subprocess.run(timeout=...)`, kept the stdout
   pipe open, and stalled the harness for 22 minutes with no output — F220, live, in this probe's
   own plumbing. `common.kill_tree` kills the tree and `common.run` returns
   `code=None` with whatever partial output was captured.
5. **`_run` is not a unique cell id.** Every Q56 campaign run lives under `runs/q56/`, so six run
   directories share the name and a resume keyed on `run/task__variant` silently skips 377 cells as
   "already done". `common.cells` now yields `_uid` as well, which includes the inner directory.
6. Same host traps as the W11 spikes: Git Bash named explicitly (`bash` on PATH here is WSL's) and a
   `python3` shim, because `python3` on PATH is the Microsoft Store shortcut. The Q56 verifiers also
   take the transcript as a **required** second argument and refuse to run without it — passing `""`
   yields no `RESULT:` line at all, which reads exactly like a verifier that could not decide.

## What came out

See `research/W6-verification.md` item 4. In one line: **on this workload the deterministic ladder
above the syntax check is silent, the free structural check is the one that fires, and the only
instrument that reads behaviour is the acceptance test — which also costs less than the ladder that
reads nothing.**
