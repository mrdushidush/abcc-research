# w11-budgets — what a loop budget should count, and what a breaker should do when it fires

Probes and analyses run 2026-08-22 for **W11 item 5 (loop budgets and circuit breakers per stage)**.
Findings **F285–F296** in `research/W11-stages.md`.

The brief asks for this item to be *"benchmarked against V1's existing behaviour"*
(`RESEARCH_BRIEF.md:958`), and it names the baseline: v1's loop detection and its 10-minute stuck
timeout (`:550-551`). Two of the four analyses here are that benchmark, run against data that was
already on disk.

## The data

`runs/` holds **1,342 measured cells across 29 runs** — every W8/Q56 cell, every U100 cell, and the
27 K-suite cells from W1's model comparison. Each carries `iterations`, `wall_clock_s` and a graded
verdict, and each has a millisecond-stamped transcript. That is a distribution of real agent
attempts on this box, which is what a loop budget has to be set against.

⚠ `runs/` is **gitignored** — the raw cells are not in the repository, so the `*-out.txt` files here
are the committed record of what the scripts printed. Re-running any script needs the runs present.

⚠ Composition matters and the analyses stratify for it: **1,315 of the 1,342 cells are Q56/U100** —
single-invocation cells against small fixtures — and only 27 are K-suite repository work. Q56 also
runs three *interference* variants (`deny-first-edit`, `redirect-first-edit`, `gated`) whose whole
purpose is to interrupt the agent. Pooling those with the controls manufactures a low-iteration
failure shoulder that does not exist (F290, and `breakers.py` section 3b is the check).

## Layout

| script | question | raw output |
|---|---|---|
| `census.py` | the distribution of attempt cost, with v1's constants placed on it as percentiles | `census-out.txt` |
| `breakers.py` | do the two budget units cut the same cells; how much does s/iteration vary; does a long attempt fail more — pooled *and* stratified by variant | `breakers-out.txt` |
| `v1_limits_replay.py` | v1's per-path tool caps (`file_write: 3`, `file_edit: 5`) replayed over all 1,342 transcripts | `v1-limits-out.txt` |
| `silence.py` | how long a *working* agent goes without producing a byte — the number an idle-gap timeout needs (OQ-W3-13) | `silence-out.txt` |
| `fastapi_blocking_probe.py` | does a blocking call in an `async def` handler make v1's abort endpoint unreachable | `fastapi-probe-out.txt` |
| `run_budget_sweep.sh` | the GPU probe: K suite on the champion at `CLAUDETTE_MAX_ITERATIONS` ∈ {12, 20, 40}, 3 reps | `runs/w11-b{12,20,40}-r{1,2,3}` |
| `sweep_report.py` | read out the sweep: pass rate per budget, per task, and how often the cap was reached | `sweep-out.txt` |

The four analysis scripts are pure Python over `runs/`, need no GPU, and finish in seconds.

## Two traps that cost time here

**`--bin` is mandatory on `w8-run`.** `~/.cargo/bin/claudette` is an older install that shadows
`D:/dev/claudette/target/release/claudette.exe` on `PATH` and reports the same `--version`. The
first attempt at the sweep lost all nine runs to it; the delivery pre-flight is what caught it, and
its error message names the cause exactly.

**`fastapi_blocking_probe.py` needs `fastapi` and `uvicorn`,** which are not installed on this host.
It was run from a throwaway venv rather than by adding packages globally. Nothing else here has a
dependency outside the standard library.

## Replay mapping for `v1_limits_replay.py`

v1's per-path caps are keyed on path and counted **cumulatively for the whole task**
(`action_history.py:15-19`), so unnarrated tool calls in between cannot change the count — which is
what makes them replayable against a Claudette transcript that narrates mutations only (F91).

| claudette | v1 tool | v1 cap |
|---|---|---|
| `write_file` | `file_write` | 3 per path |
| `apply_diff`, `edit_file`, `apply_patch` | `file_edit` | 5 per path |

The script also reports a `5 same verb in a row` column for v1's window rule
(`action_history.py:124`). That column is an **upper bound** and is labelled as such: an unnarrated
read between two edits would break a run the count treats as consecutive. The two per-path columns
carry no such caveat.
