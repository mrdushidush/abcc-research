# TOOL-S6 — the ship bench: abcc dc57bde at temperature 0, batch vs chat

**2026-09-27 23:05 → 2026-09-29 05:17, two nights.** Session 6 of the three-session ship plan.
`qwen3.6-35b-a3b-mtp@iq3_s`, `-c 40960 --parallel 1`, `w8-run --num-ctx 40960
--verify-timeout-s 1200`. Corpus `24b6a90` (night 1) and `85d0928` (night 2); `corpus/suites` is
unchanged since A3's `6b8f96d`, so every card is the card A3 ran. Driver `harness/s6-night.sh`, then
`harness/s6-resume.sh`, which David started from his own terminal on night 2 (outside Claude Code, so
the low-memory reaper that cut night 1 could not reach it). Driver log `harness/runs/s6/driver.log`.
Index `research/s6/INDEX.tsv` (14 invocations), every graded cell (147) with abcc's own metrics and
its PromptCut and eviction counts in `research/s6/cells.tsv` (built with `w8_abcc_metrics.cell_row`).

| subject | what it is |
|---|---|
| `abcc-dc57bde` (**main**) | `abcc run`, the shipped pin: F844 fix, temperature 0 by default, (a') merged (a `<tool_call>` left in the reasoning of a turn that said nothing is recovered), compaction, the emergency eviction tier built but eviction off |
| `abcc-dc57bde-chat` (**chat**) | `abcc chat`: one conversation, Builders only (no Recon, no hand-off), `/done` after the first answer |
| `abcc-dc57bde-evict` (**evict**) | main plus `--evict`. It ran K pass 1 only: the arm was dropped from the resume (David, 2026-09-28) |

`main-r-p1` (`w8-1790541257686`) is **junk** and is not counted: 13 `error` cells, `git read-tree`
exited `0xC0000142` (a process that failed to start under a memory crunch). It was re-run as
`main-r-p1r`.

## F847 — main at dc57bde: R 10,10,10 and K 2,2,2 — both above A3 — with the same four drafting cards failing; Q56 48

| | A3 abcc `e5eef90` (server temperature) | **S6 main** `dc57bde` (T = 0) | S6 chat | S6 evict |
|---|---|---|---|---|
| **R, full verdict** (× 14) | 23 / 42 (8, 8, 7) | **30 / 42 (10, 10, 10)** | 20 / 28 (10, 10) | — |
| R, hidden test alone | 24 / 42 (9, 8, 7) | 30 / 42 | 20 / 28 | — |
| **K** (× 3) | 0 / 9 | **6 / 9 (2, 2, 2)** | 3 / 9 (1, 1, 1) | 2 / 3 |
| **Q56** `control` (× 1) | 50 / 56 | **48 / 56** | — | — |
| wall per cell: R · K · Q56 | — | 248 · 152 · 68 s | 217 · 279 s | 155 s |

Per card (`P` pass · `b` hidden test passes, the verdict fails · `.` hidden test fails):

| suite | card | A3 abcc | main | chat | evict |
|---|---|---|---|---|---|
| R | `runtime_10` `runtime_11` `sched_02` `sec_06` `shell_07` `shell_10` `ux_06` | PPP each | PPP each | PP each | |
| R | `cargo_failures` | bP. | PPP | PP | |
| R | `edit_10` | P.. | PPP | PP | |
| R | `shell_06` | ... | PPP | PP | |
| R | `edit_06` `edit_09` `sec_04` `shell_04` | ... each | ... each | .. each | |
| K | `finish_the_cancelled_status` | ... | PPP | ... | P |
| K | `round_at_the_line_not_the_total` | ... | PPP | PPP | P |
| K | `trace_dropped_samples` | ... | ... | ... | . |

* **The (a') regression rule holds.** K is at least 2 of 3 in every main pass, and no card fails
  outside the four drafting cards (`edit_06 edit_09 sec_04 shell_04`, F837–F845). All 12 of main's
  R failures end in `reasoning_runaway`, as in A3.
* **Q56 moved in both directions.** Fixed since A3: `Q04` `Q29`. Still failing: `Q03` `Q05` `Q25`
  `Q46`. **New failures: `Q20` `Q26` `Q39` `Q51`.** `Q20` `Q26` `Q51` made an edit and fail the
  hidden test on substance (`Q20` drops a present `0`; `Q51` no longer rejects stray characters).
  `Q39` made no edit at all (F849). ⚠ **The −2 is UNATTRIBUTED.** A3 sampled at the server's
  temperature and ran `e5eef90`; S6 runs temperature 0 and `dc57bde`, which also carries (a'),
  compaction and the F844 fix. The control that separates the two is proposed, not run: the ten
  moved or failing Q56 tasks at `--temperature server` × 3, plus T = 0 × 1.
* **Eviction and compaction were barely exercised.** Across the 147 cells: **0** `prompt_cut` events,
  **2** eviction notes (chat R `shell_07`, both passes, the stale tier), **0** uses of the emergency
  (recent) tier. The one evict pass scored K exactly as main did. K, R and Q56 do not fill the
  40,960 window, so this bench says nothing about eviction either way. Large-file work is where
  the tier would fire.
* **At T = 0 the passes give the same verdicts, not the same bytes.** Every pass of every arm gives
  the same per-card result (main R × 3, main K × 3, chat K × 3, chat R × 2), so × 3 at T = 0 carries
  about n = 1 of information about the verdict. The work itself is not reproducible:
  - The bash tool's result names its own wall time (`exit 0 in 64 ms`, `workspace.rs:1102`), and
    that line goes into the model's context. Main K pass 1 vs pass 2 saw different timings on all
    four bash calls and differed in 5 model calls' token counts. Its three source diffs are
    still byte-identical, because Recon's hand-off dictates the code (F848).
  - Chat `finish_the_cancelled_status` passes 1, 2 and 3 are three different diffs, differing in
    docstrings and hunk shape, with the same verdict. Passes 2 and 3 first diverge at a bash
    timing line. Passes 1 and 2 (different nights, different model loads) diverge at the
    **first** call, whose prompt is identical: 122 vs 169 completion tokens.
  - So "a seed does not pin this stack" (F715, F728) holds at T = 0 too: say *attributable*,
    never *reproducible*.

⚠ n = 1 of information per card at T = 0, one model, one window. S6's R and K sit where F840 put
`e5eef90` at T = 0 through the tap (R 9, 10, 8; K 3, 2, 2). That fits T = 0 being the lever, and
nothing here shows that the code since `e5eef90` moved R or K.

## F848 — main passes `finish_the_cancelled_status` by applying Recon's written fix; chat's Builders, with no Recon, renames the bucket

The one K card that splits the arms, deterministic in both: **main PPP, chat `...`.** The verifier
fails chat on `COUNTS must show other=0 … got: … cancelled=4`.

**What each arm wrote in `jobs/summary.py`, all three passes:**

| | main | chat |
|---|---|---|
| `BUCKETS` | `(…, "failed", "cancelled", "other")` | `(…, "failed", "cancelled")` |
| `counts()` | a new `elif job.status == st.CANCELLED` before the `else` | the `else` branch now adds to `"cancelled"` |
| rates | `cancelled` added to both denominators | unchanged |

Chat's version is a real defect, not a verifier quibble. The default branch now counts every
status it does not name as `cancelled`: exactly the "default branch will swallow the fifth" failure
that `docs/status_lifecycle.md` warns about. The other three sites (`sla`, `charges`, `retry`) are
correct in both arms.

**Why main gets it right: Recon writes the fix and Builders applies it.** Main's Recon brief
(`brief_recorded`, attempt 10 of `w8-1790539560433`) spells out all three `summary.py` changes as
code: keep `other`, add the `elif`, and add `cancelled` to both rate denominators. Nobody asked for
that last change, and it appears in main's diff every pass. This is F839's drafting Recon, and on
this card the draft is right. Chat's Builders read the same material (the spec, `summary.py` whole,
the other status consumers, and the tests) and decides alone, and at T = 0 it renames the bucket every time.

⚠ **Two things differ between the arms, and they are not separated:** the Recon section of the
brief, and chat's framing paragraph ("This is a conversation with the operator…", `brief.rs:134`)
in place of main's "Make the change". The cheapest control is a tapped replay (`llm_tap.py`,
F839) of chat's Builders prompt with main's Recon section pasted in: a handful of GPU calls. Not run.

**The chat judge saw it once in three.** Commandos flagged the `else` branch in pass 1, but with a
wrong reproduction: it claims a `running` job is counted as cancelled, and `counts()` names
`RUNNING`. In passes 2 and 3 it reported no findings. Its three briefs carry the same source diff
and differ only in the `.pyc` blob hashes (below), so at T = 0 the judge's verdict turned on
hash noise.

**`trace_dropped_samples` fails in both arms, differently.** Its fix is one line upstream
(`pipeline/ingest.py`: fold the flag through `normalize.canonical_flag`, because rev B firmware
sends upper-case flags). Main's Recon localises the crash site instead and prescribes a guard that
skips empty windows. Builders applies it and the report prints `windows: 10` (12 expected), which
is the card's local wrong answer. Chat's Builders reads 14 files and hits the 50,000-character
reasoning ceiling without an edit, 3 of 3.

⚠ **Harness hygiene, not abcc.** Every K diff carries `__pycache__/*.pyc` hunks because
`corpus/suites/k/tasks/*/fixture/**/__pycache__` exists on disk (untracked, gitignored by
`corpus/.gitignore`, dated 2026-08-22). `w8-run` copies it into each cell, and the cell's
repository has no `.gitignore`. It pads the structural rung's file list and the judge's brief, and
adds per-run noise to both.

## F849 — Q39: Builders wrote its tool call as answer text, and (a') only reads the reasoning

`Q39` (`makeGrid` shares one row array) passed in A3 and fails in S6 with **no edit**. Recon found
the line and the fix in 9 s. Builders then made one call, which ended `stop` with 98 characters of
**text**: `<tool_call><function=read_file>\n<parameter=path>\nsolution.ts\n</parameter>\n</function>\n</tool_call>`.
The server's parser did not return it as a tool call, and it is not recovered in abcc either:
(a')'s `calls_in_reasoning` (`openai.rs:817`) runs only when a `stop` turn said nothing and called
nothing (`openai.rs:788`), and this turn said something. The phase ended on that text, the
structural rung refused an unchanged tree, and the judge was not asked.

It is **1 cell of 147**: no other phase in S6 ends on tool-call markup, and none of the 107 A3
abcc cell logs still on disk does. The mechanism is shown, the frequency is low, and whether
T = 0 made it more likely is not. Extending the recovery to a turn whose whole text is trailing `<tool_call>` blocks would
catch it; that is a code change, and it waits for David.
