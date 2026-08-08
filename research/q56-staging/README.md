# q56 staging — the worked example, parked outside `corpus/` on purpose

`q56/` is the hand-authored Q08 worked example plus the suite descriptor, validated against the
frozen SPEC by **both** validators (`validate.py` and the compiled `w8-corpus` loader: ACCEPTED,
all four variants merging onto the task).

**It belongs at `corpus/suites/q56/`. It is here only because a second suite cannot appear under
`corpus/` while runs are in flight against u100** — `w8-run` makes `--suite` mandatory the moment a
corpus holds more than one, so any script that omits it starts failing mid-series. Both traps are
written up as F48 in `research/W8-q56-import.md`.

**To land it:** wait for the repeat runs to finish, `mv research/q56-staging/q56
corpus/suites/q56`, and re-run both validators. Then either add `--suite u100` to
`research/spikes/w8-repeats/repeat5.sh`-style loops, or accept that they must name a suite from then
on.

`expected_tasks` is deliberately absent from `suite.toml` until all 56 tasks are emitted — see the
comment in the file, and `harness/crates/w8-import-q56/README.md`.
