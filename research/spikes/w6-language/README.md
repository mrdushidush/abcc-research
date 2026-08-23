# w6-language — what in the pipeline is language-specific, and what generalises

Probes run 2026-08-23 for **W6 item 5 (language generality)**. Findings **F311–F320** in
`research/W6-verification.md`.

§11's scope for the item: *"BCF reportedly outputs Python only. 2.0 targets more languages. What in
the pipeline is language-specific and what generalizes? This is a real scoping question."* Plus
**OQ-W6-9** from item 4: *does the picture change in a language whose type checker is the build?*

Seven probes. Three run the donors' own code, one is a controlled experiment where the language is
the only variable, and three measure real agent output in five languages.

| probe | what it runs | output |
|---|---|---|
| `bcf-probe/` | BCF's `verifier::verify_file` / `verify_project` via a **path dependency** on the pinned donor checkout | `bcf-scores.json` |
| `v1_channel.py` | v1's `ValidateSyntaxTool._run` and the `/run-validation` dispatch, **ported verbatim** and executed | `v1-channel-results.json` |
| `claudette-probe/` | Claudette's detector, build step, count parsers and `classify_tests`, **vendored verbatim** with line citations, driven by real subprocess results | stdout JSON, quoted in the finding |
| `mutants.py` | one ticket, seven candidate answers, **three languages × two coding styles**, five instruments | `mutants-results.json` |
| `../w6-headroom/ladder.py q56` | item 4's ladder, with the node / typescript / shell rungs this item added to `instruments.py`, over the **351 real cells item 4 skipped** | `../w6-headroom/results-q56.json` (now 728 cells) |
| `q56_langs.py` | F307's table, re-cut over all five languages | prints; reads the file above |
| `structural.py` | item 4's free structural rung over all 728 Q56 cells (`--k` for the K population, stratified by arm) | `structural-results.json`, `structural-k-results.json` |
| `baseline.py` | every rung over the pristine fixture **and** the reference solution — the control that catches a rung which is red before the change (F323) | `baseline-results.json` |

## Running them

```
cd research/spikes/w6-language
npm install                                   # typescript 5.9.3 + @types/node, pinned in package.json
python mutants.py                             # 42 trees, ~4 min
python v1_channel.py                          # ~30 s
(cd claudette-probe && cargo run --release)   # ~15 s after the first build
(cd bcf-probe && cargo run --release)         # first build ~70 s: it compiles the donor crate
                                              # BCF prints its own progress lines before the JSON;
                                              # keep the last stdout line
python baseline.py                            # ~3 min, mostly cargo
(cd ../w6-headroom && python ladder.py q56)   # resumable: only measures cells not already in
                                              # results-q56.json. ~20 min for the 351 new ones
python q56_langs.py                           # prints the five-language table
python structural.py ; python structural.py --k
```

`bcf-probe` depends on `../../../../../battle-command-forge` at `d6c1601` being checked out beside
this repository; the others are self-contained. `trees/`, `trees-frameworks/`, `node_modules/` and
`target/` are generated and git-ignored — the committed `*.json` files are the record.

## The controlled experiment (`mutants.py`)

The ticket is the K corpus's shape, reduced to something that can be written three times: *a fourth
order status exists in the type; make the four consumers agree about what it means.* Ground truth is
by construction.

| mutant | what the agent did |
|---|---|
| `m0_empty` | nothing |
| `m1_one_site` | 1 of the 4 consumers |
| `m2_three_sites` | 3 of the 4 |
| `m3_wrong_semantics` | all 4, one of them backwards |
| `m4_wrong_type` | all 4, one returning a `bool` where a string is declared |
| `m5_reference` | all 4, correct — the control |
| `m6_regression` | all 4 correct **and** breaks a behaviour the old suite covers |

The second axis is the **subject code's style**, not the language:

- `wildcard` — every consumer ends in `case _:` / `default:` / `_ =>`. Adding a variant compiles.
- `exhaustive` — none does; Python closes the match with `typing.assert_never`, TypeScript with
  `const unhandled: never =`, Rust with nothing at all, which is how Rust spells it.

Five instruments per tree: the syntax check, the type check, the linter, the repository's own test
suite (which covers the three original statuses and nothing about the fourth), and the acceptance
test (which covers the fourth and nothing else).

Two notes on fidelity. In Rust the syntax check and the type check are the same command
(`cargo check --lib`), which is the point of the arm rather than a defect in the harness. TypeScript
has no linter here — `eslint` was not installed, and item 4 already measured linters in two
languages.

## What the numbers were

- The type check catches **1 of 6** wrong answers under `wildcard` and **4 of 6** under
  `exhaustive` — the same split in all three languages (F318).
- The acceptance test catches **5 of 6** in every cell of the grid; the sixth is the regression,
  which only the pre-existing suite sees (F318).
- `clippy -D warnings` is **green on the do-nothing answer and red on the correct one** under
  `wildcard`, because completing the work makes the pre-existing `_` arm unreachable (F320).
- BCF scores a perfect Python file **5.80** and a language it has never heard of **8.00** (F313).
- v1's five-language syntax table separates valid from invalid code in **0 of 6** languages on this
  host (F311), and its validation channel scores **1 of 13** realistic commands a pass (F312).
- Claudette's `npm` arm cannot spawn `npm` from a Rust process on Windows at all — `program not
  found`, in all three tree states (F317).
- On **728 real agent attempts in five languages**, a type or syntax check caught **1 of 160**
  failures, and on the 280 cells from the arms that leave the agent alone **nothing caught anything**
  (F321).
- The free structural check has **0 false positives on 609 correct trees**, and a yield that is a
  property of the task's shape rather than of the language (F322).

⚠ **Every rate here is reported per stratum.** 448 of the 728 Q56 cells come from arms that deny or
redirect the agent's first edit; pooling them gives the structural check a 90/160 that stratification
cuts to 0/29 on the clean arms.
