# TOOL-B1 — the editor: `SEC-06` with `edit_file` on the menu

**2026-09-23.** PLAN-TOOL.md §2's H1 test, run first in Phase B as the plan asked. abcc at
`e5eef90` (B1: `edit_file` + a 400-line `read_file` window), `qwen3.6-35b-a3b-mtp@iq3_s`,
`-c 40960 --parallel 1`, claudette at `a450e00`. n = 3.

## F835 — with a snippet editor on the menu, `SEC-06` went from 0 of 4 to 3 of 3

| attempt | task | prompt | ending | editing calls | read_file calls | read bytes | prompt tokens | wall |
|---|---|---|---|---|---:|---:|---:|---:|
| a1711 | t1703 | v1 | uncertain/truncated_at_cap | 0 | 19 | 187,230 | 368,523 | 532 s |
| a1866 | t1858 | v2 | uncertain/budget_exhausted | 0 | 21 | 175,361 | 444,736 | 306 s |
| a2009 | t1703 | v1 | uncertain/said_nothing | 0 | 3 | 15,496 | 42,415 | 92 s |
| a2065 | t1703 | v1 | uncertain/budget_exhausted | 0 | 22 | 41,341 | 258,023 | 533 s |
| **a2929** | t2919 | h1 | **MISSION ACCOMPLISHED** | edit_file 3 (3 ok) | 7 | 31,706 | 144,414 | 286 s |
| **a3032** | t2920 | h1 | **MISSION ACCOMPLISHED** | edit_file 2 (2 ok) | 7 | 30,161 | 100,243 | 191 s |
| **a3115** | t2921 | h1 | **MISSION ACCOMPLISHED** | edit_file 2 (2 ok) | 7 | 30,673 | 163,794 | 259 s |

All three: 4 of 4 rungs green, the Judge reported no findings, and the production change is
exactly the card's one-line deletion at `semantic.rs:179-184`. Every editing call applied, and
none of them was `write_file` or `apply_patch`.

✅ **None of the three tests is a sham (F832's check, by hand).** Each attempt's test hunk was
applied **alone** to its opening checkpoint and run: `walk_skips_dotfiles`,
`walk_skips_dotfiles_no_exceptions` and `walk_skips_dotenv` all **FAIL at run time** on the
unfixed code. So all three tests prove the fix.

⚠ **What changed between the arms, and it is two things, not one.**

1. **The tool menu** — `edit_file` is offered and `read_file` is windowed (the B1 bundle).
2. **One deleted paragraph.** The `h1` prompt is v1 with only its `USE write_file, NOT
   apply_patch … ONE write_file call whose content is the COMPLETE new file` paragraph removed.
   That was David's ruling: v1 ordered a whole-file rewrite, so running it unchanged would have
   tested obedience, not the editor. No word was added (`research/patches/SEC-06-task-prompt-h1.txt`).

So this does not separate *the editor* from *the prompt stopped forbidding it*. It does show that
the bundle PLAN-TOOL called D1 + D2 turns a card that died four times into one that lands
every time, at about two thirds of the wall clock (mean 245 s against 366 s) and half the prompt
tokens (mean 136k against 278k) of attempts that changed nothing.

⚠ **n = 3 on one card.** It says the ranking in PLAN-TOOL §2 is right about `SEC-06`, not that
abcc is at parity. The bench (Phase A) is what decides that.

## Also shipped this session, for the bench

The `abcc` drive for `w8-run` (`harness/crates/w8-run/src/abcc.rs`, subject
`corpus/subjects/abcc-e5eef90.toml`). Each cell runs one `abcc task` and one `abcc run` in a git
repository made from the fixture. The attempt's closing checkpoint is then checked out and the
suite's own `verify.sh` grades it: **abcc's gate is recorded, never used as the grade.**
Smoke-tested on Q56 `Q01` (`control`): PASS, a checkpoint diff of 66 changed lines, and the
untouched fixture FAILs the same verifier on all four hidden tests (the negative control).
