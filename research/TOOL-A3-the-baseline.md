# TOOL-A3 — the baseline: abcc and claudette on the same bench, one night

**2026-09-23 16:18 → 2026-09-24 04:27.** PLAN-TOOL.md Phase A3, approved by David as one overnight
run. `qwen3.6-35b-a3b-mtp@iq3_s`, `-c 40960 --parallel 1`, `w8-run --num-ctx 40960
--verify-timeout-s 1200`, corpus `6b8f96d`. Driver `harness/a3-overnight.sh`; 14 invocations, all
exit 0, 12 h 09 min. Per-invocation index `research/a3/INDEX.tsv`, every graded cell (214) in
`research/a3/cells.tsv`, abcc's per-cell tool metrics in `research/a3/abcc-cells.tsv`
(`research/tools/w8_abcc_metrics.py`).

| subject | pin | notes |
|---|---|---|
| `abcc-e5eef90` | abcc `e5eef90` (B1: `edit_file` + windowed `read_file`) | `control` is its only runnable variant |
| `claudette-af3f804` | `--bin D:/dev/claudette/target/release/claudette.exe` | the binary every earlier claudette baseline used (built 2026-08-27: `af3f804` + dependency and lint bumps). `~/.cargo/bin/claudette` predates `af3f804` and has no prompt sentinels — never use it. Run `--variant control` only, so every cell has an abcc pair |

Order: for pass 1..3 {R abcc, R claudette, K abcc, K claudette}, then Q56 abcc, Q56 claudette.
Pre-flight (not part of A3): claudette on R `runtime_11`, run `w8-1790169321010` — graded end to
end, FAIL on `fmt` only.

## F836 — the A3 baseline: abcc wins R on the grade, ties it on the hidden test, loses K and Q56

| | abcc | claudette |
|---|---|---|
| **R, full verdict** (3 × 14) | **23 / 42** (8, 8, 7) | **8 / 42** (1, 1, 6) |
| R, hidden test alone | 24 / 42 (9, 8, 7) | 25 / 42 (8, 8, 9) |
| R, subject timeout (1800 s) | 0 | 8 |
| R batch 1 (the six pilot cards), full | 12 / 18 | 4 / 18 |
| R batch 2 (the eight new cards), full | 11 / 24 | 4 / 24 |
| **K** (3 × 3) | **0 / 9** | **7 / 9** |
| **Q56** `control` (× 1) | **50 / 56** | **53 / 56** |
| wall, summed over cells: R · K · Q56 | 177 · 25 · 68 min | 381 · 21 · 24 min |

**The R gap is `fmt` and `clippy`, not behaviour.** 17 of claudette's R cells pass the hidden
test and fail the verdict — 16 on `fmt`, 5 on `clippy` (they overlap); abcc has 1 such cell.
This is F673's criterion the model cannot see: abcc's own gate runs both, claudette is never told.
claudette's pass-3 jump from 1 to 6 is the same effect — its hidden-test count moved 8 → 9 while
its `fmt` failures fell. All three claudette R invocations carry the same bin, corpus commit,
`num_ctx` and verify timeout in `runmeta.json`; nothing changed but the draw.

Per card, three passes (`P` pass · `b` hidden test passes, the verdict fails · `.` hidden test
fails · `T` subject timeout):

| suite | card | abcc | claudette |
|---|---|---|---|
| R b1 | `runtime_10` | PPP | PbP |
| R b1 | `runtime_11` | PPP | bPP |
| R b1 | `sec_06` | PPP | ..b |
| R b1 | `shell_10` | PPP | bbb |
| R b1 | `shell_04` | ... | TTT |
| R b1 | `shell_06` | ... | b.b |
| R b2 | `sched_02` | PPP | .bP |
| R b2 | `shell_07` | PPP | bb. |
| R b2 | `ux_06` | PPP | bbP |
| R b2 | `edit_10` | P.. | .bP |
| R b2 | `cargo_failures` | bP. | bb. |
| R b2 | `edit_06` | ... | bTP |
| R b2 | `edit_09` | ... | .TT |
| R b2 | `sec_04` | ... | TT. |
| K | `finish_the_cancelled_status` | ... | .P. |
| K | `round_at_the_line_not_the_total` | ... | PPP |
| K | `trace_dropped_samples` | ... | PPP |

Q56: both fail `Q03` `Q46`; abcc alone fails `Q04` `Q05` `Q25` `Q29`; claudette alone fails `Q51`.

⚠ n = 3 on R and K, n = 1 on Q56, one model, one window. claudette's repeats vary a lot per card
(`edit_06` went `b`, `T`, `P`); abcc's barely vary (next section). Quote the pooled numbers
with the per-card table beside them.

## F837 — abcc's failures happen in Recon, before any edit, and the same way every pass

Of abcc's **28** R + K failures, **24 ended in the Recon (localize) phase with no editing call**,
and each of those tasks ended the same way on all three passes:

| ending (abcc's own) | cells | tasks |
|---|---:|---|
| `reasoning_runaway` — the 50,000-character reasoning ceiling (F829, `turn.rs:349`) cut the call | 12 | `edit_06` `edit_09` `sec_04` `shell_04`, 3 / 3 each |
| `said_nothing` — Recon finished and produced no answer | 9 | `shell_06` (R); `finish_the_cancelled_status`, `round_at_the_line_not_the_total` (K) |
| `truncated_at_cap` — 16,384-token cap, empty payload | 3 | `trace_dropped_samples` (K) |
| reached Builders, then `budget_exhausted` | 2 | `cargo_failures` |
| reached Commandos, then `refused` | 2 | `edit_10` |

The K endings are near-identical across passes: `said_nothing` after exactly 1,163 and 27
output tokens in all three passes, `truncated_at_cap` every time. With an attempt budget of 1,
none of the 24 ever reached a phase that edits.

**The editor is no longer where abcc loses.** R made 111 `edit_file` calls and 101 applied; Q56
made 74 and 73 applied; there was not one `write_file` or `apply_patch` call in either suite.
The runaway cells die early — `edit_06`'s pass-1 attempt read two files (24,938 bytes) in
3 min 38 s and was cut on its third call — so this is not the re-read spiral of PLAN-TOOL's H1
either (R failures median 2 `read_file` calls; R passes median 8).

⚠ **Observed, not explained.** Whether the 12 runaway cells would finish without the ceiling was
untested when this was written — F838 below ran the control.

⚠ abcc's `completion_tokens` undercount failed cells — a call cut by the ceiling is never billed.
Do not read R failures' median of 491 completion tokens as "the model barely spoke".

## F838 — with the ceiling off, the same four tasks hit the token cap instead: 12 of 12, byte-identical

**2026-09-24 12:24 → 13:25.** F837's control. Subject `abcc-e5eef90-ceil0` = the same build plus
`--reasoning-ceiling 0` (research `d8cbdfc`: a subject's `args` now reach `abcc run`; the flag was
seen on the live process's command line). `edit_06 edit_09 sec_04 shell_04`, n = 3, same model,
window and corpus as A3. Runs `w8-1790241837779`, `w8-1790243040950`, `w8-1790244261798`; per-cell
metrics `research/a3/ceil0-cells.tsv`.

| task | A3 (ceiling 50,000) | ceiling off, × 3 | model calls | read_file | read bytes | completion tokens | wall |
|---|---|---|---:|---:|---:|---:|---:|
| `edit_06` | runaway ×3 | `truncated_at_cap` ×3 | 3 | 2 | 24,938 | 16,748 | 257–264 s |
| `edit_09` | runaway ×3 | `truncated_at_cap` ×3 | 3 | 2 | 24,938 | 16,708 | 262–275 s |
| `sec_04` | runaway ×3 | `truncated_at_cap` ×3 | 2 | 1 | 11,063 | 16,483 | 255–259 s |
| `shell_04` | runaway ×3 | `truncated_at_cap` ×3 | 4 | 2 | 13,727 | 16,875 | 264–277 s |

All 12 fail the hidden test in Recon with **no editing call**, and every count except wall clock is
identical across the three passes. So **the ceiling costs these cells nothing**: without it the
model reasons on until the 16,384-token cap and still returns an empty payload; the ceiling only
ends the same dead attempt ~40 s sooner (A3's `edit_06` was cut at 3 min 38 s, here 4 min 15 s).
This agrees with F829's "costs 0" on a sample F829 never saw.

It moves F837's question. All 24 of abcc's Recon failures in A3 share one observable outcome —
**Recon never returns an answer** — reached three ways: cut at the ceiling (12), capped at 16,384
tokens (3; and these 12 once the ceiling is off), or finishing with nothing (9). Whether those are
one mechanism is NOT shown. claudette, on the same model and window, has no Recon phase: of these
four R tasks it passes the hidden test only on `edit_06`, in 2 of 3 passes (`bTP`; the others are
`.TT`, `TT.`, `TTT` — mostly timeouts), but it passes every K task in at least one pass (7 / 9).

⚠ The runs are deterministic per task (abcc seeds every call, F715), so n = 3 here is one
observation three times, not three samples. A different seed or prompt is what would vary it.

## F839 — what Recon is doing when it never answers: working the fix, and calling tools from inside its reasoning

**2026-09-24 13:55 → 14:25.** abcc stores reasoning LENGTHS, never text, so the eight tasks behind
F837's 24 Recon failures were replayed once each (`abcc-e5eef90-ceil0`) through a logging
pass-through in front of LM Studio (`research/tools/llm_tap.py`, read with `llm_tapread.py`;
abcc pointed at it by `ABCC_MODEL_BASE_URL`). The replay is exact: per-call seeds match the
original log, and every cell's completion tokens equal F838's and A3's (`edit_06` 292 + 72 +
16,384 = 16,748; the K `said_nothing` endings again 1,163 and 27). Runs `w8-1790247318166` (R),
`w8-1790248615651` (K); the 64 captured chat calls are in `harness/runs/tap/calls/` (gitignored — they
hold `sec_04` secret-pattern text).

**Two different things, both inside the reasoning channel.** No failing call ever closed its
reasoning block: every character of the 24 cells' final calls is `reasoning_content`, `content`
is empty.

1. **The capped calls work the fix instead of locating it** (`edit_06` `edit_09` `sec_04`
   `shell_04` R, `trace_dropped_samples` K). After two reads the model writes "Now I have the full
   picture" (`edit_06`, `edit_09`) and then designs and drafts the implementation — 9 to 41 fenced code blocks per R
   trace, 34–54 "Actually", edge cases of `split_inclusive` tested by hand, "I'll replace lines
   290-354 with my new implementation" — in a phase whose tools are `read_file list_files search`
   and whose brief says *"Find the place … When you know where the work goes, say so and stop
   asking for tools."* The brief also carries the card's full THE FIX recipe. It is not a loop:
   61–90% of the lines are distinct. On the K task, with no way to run code, it executes the
   pipeline by hand, sample by sample, until the cap.
2. **The `said_nothing` endings are tool calls written inside the reasoning.** 11 calls in the
   replay finished `stop` with an empty reply; **10 of them end in a `<tool_call><function=read_file>`
   block (Qwen's XML form) that never left the reasoning**, so the server returned no call and no
   text. The 11th (K `finish_the_cancelled_status`, the 1,163-token one) holds a complete Recon
   answer — files, lines, the change, what proves it — also as reasoning. abcc then nudges
   (ADR-0016): *"Your last turn produced no reply text at all … Say the answer now"* — to a model
   that was asking to read a file. Three such turns end the attempt (`nudges: 2`): `shell_06`,
   `finish_the_cancelled_status` and `round_at_the_line_not_the_total` each had exactly three.

⚠ **What this does NOT show.** Whether either fix would turn these cells green is untested: (a)
recovering a `<tool_call>` block from reasoning (and a reasoning-only answer), and (b) a Recon
that can end without the model having to stop designing. claudette does NOT parse reasoning
either (`api.rs:1165`, size only); in this harness it sends `temperature: 0.0` and no seed where
abcc sends a seed and the server's default temperature — a real difference between the two
subjects, NOT tested as the reason claudette gets through K.

## F840 — at temperature 0, K goes 0 / 9 → 3 / 3 and R 9 / 14; the fix-drafting Recon does not move

**2026-09-24 15:02 → 17:02.** F839's option (c), David's pick. Subject `abcc-e5eef90-t0`
(research `97982a4`): the same build, `abcc run --url` pointed at `llm_tap.py … temperature=0`,
which sets `temperature: 0` on every chat body (abcc keeps its seed; the engine is unchanged — the
2026-09-12 ruling that abcc sends no temperature stands). Every forwarded body carries it. n = 1.
Runs `w8-1790251346941` (K), `w8-1790254482991` (R); an earlier R attempt was stopped by Claude
Code's low-memory reaper after three cells and is not counted. Per-cell metrics
`research/a3/t0-cells.tsv`.

| | A3, server-default temperature (3 passes) | temperature 0 (1 pass) |
|---|---|---|
| K | 0, 0, 0 of 3 | **3 of 3** — all three leave Recon; `finish` and `round` run all three phases |
| R | 8, 8, 7 of 14 | **9 of 14** |

Per R card, the only changes: **`shell_06` `...` → pass** (A3: `said_nothing` in Recon ×3),
**`cargo_failures` `bP.` → pass**, **`edit_10` `P..` → fail** (hidden test passes; abcc's own
gate refused on `cargo fmt`). All seven A3 `PPP` cards pass again. **`edit_06` `edit_09` `sec_04`
`shell_04` are unchanged: Recon cut at the 50,000-character ceiling, no edit** — F839's
fix-drafting failure does not respond to temperature.

⚠ **Temperature 0 does NOT stop the tool calls from landing in the reasoning.** The tap shows 22
empty `stop` turns across the two graded runs (K 8, R 14), **every one of them with a
`<tool_call>` block inside the reasoning** — on passing cards too (`runtime_10`, `sec_06`,
`shell_10`, `ux_06` …). At temperature 0 the attempts survive it; at the default they did not.
Why is NOT shown (fewer per phase, so the two nudges suffice? a cleaner call after the nudge?).

⚠ n = 1, and temperature 0 is not deterministic on this stack (claudette sends it and varied
pass to pass in A3). Repeat before quoting 3 / 3 or 9 / 14 as rates. What this run does support:
the two F839 failures are different — one moved with sampling, one did not.

### F840 at n = 3 — passes 2 and 3 (2026-09-24 18:28 → 20:59)

David's order at the end of session 4: repeat the temperature-0 run twice more. Same subject, same
tap (`temperature=0` on every forwarded body — checked on a captured request), one tap directory per
suite and pass (`harness/runs/t0/calls-p{2,3}-{k,r}`, gitignored). Runs: pass 2 `w8-1790263700527`
(K) `w8-1790264322583` (R); pass 3 `w8-1790268472391` (K) `w8-1790268949595` (R). All six runs'
cells are in `research/a3/t0-cells.tsv`.

| | A3, server default (3 passes) | temperature 0, passes 1 · 2 · 3 |
|---|---|---|
| K | 0, 0, 0 of 3 | **3, 2, 2 of 3** (7 / 9) |
| R | 8, 8, 7 of 14 (23 / 42) | **9, 10, 8 of 14** (27 / 42) |

Per card, temperature 0, passes 1 · 2 · 3 (`P` pass, `.` fail):

* **Every pass, 3 of 3:** K `finish_the_cancelled_status`, `round_at_the_line_not_the_total`; R
  `runtime_10 runtime_11 sched_02 sec_06 shell_06 shell_07 shell_10 ux_06`. **`shell_06` is the
  one card of these eight that A3 failed (`...`, `said_nothing` in Recon).**
* **Every pass, 0 of 3, identically:** `edit_06 edit_09 sec_04 shell_04` — Recon cut at the
  50,000-character ceiling, no edit, `reasoning_runaway`, all twelve cells. **The fix-drafting
  failure does not move with temperature.** A3 was the same 0 of 12.
* **Varies pass to pass:** K `trace_dropped_samples` `P..` — passes 2 and 3 LEAVE Recon, make one
  applied edit (`pipeline/stats.py` skips empty windows) and fail the verifier on the same line
  (`expected 'windows: 12', got: windows: 10`): a wrong fix, not a Recon death. R `cargo_failures`
  `PP.` (pass 3: behaviour and others pass, fmt and clippy fail — `write!()` ending in `\n` —
  and the round budget ran out); R `edit_10` `.P.` (pass 1: fmt refused by abcc's own gate;
  pass 3: the hidden test and two existing permission tests red — a wrong change).

⚠ **The tool calls written inside the reasoning are still there at every pass.** Empty `stop`
turns (no text, no wire call) in the tap, graded runs only: pass 1 K 8 · R 14, pass 2 K 4 · R 14,
pass 3 K 3 · R 13 — **56, and all 56 end with a `<tool_call>` block inside the reasoning.**
Temperature 0 lets the attempts survive them (abcc's two nudges); it does not stop them happening.

What n = 3 supports: the K lift (0 / 9 → 7 / 9) and `shell_06` (0 / 3 → 3 / 3) are repeatable, and
both are the `said_nothing` population; the R total moves by exactly those cells plus noise on
`cargo_failures` / `edit_10`. The drafting four are 0 / 12 at both temperatures. Temperature 0 is
still NOT deterministic here (three cards changed between passes) — say *repeatable*, not
*reproducible*.

## F841 — tool calls recovered from the reasoning: K 0 / 9 → 2 / 3 and `shell_06` passes, at the server's default temperature

**2026-09-24 21:17 → 21:41.** F839 option (a), built as a PROBE while David was away ("keep pushing
- and use the GPU as needed"): abcc branch `probe/reasoning-calls` `412d2d8` = `e5eef90` + one
commit, NOT merged. On a `stop` turn with no text and no wire call, the OpenAI adapter reads the
trailing run of `<tool_call>` blocks (Qwen XML or JSON form) off the end of the reasoning and runs
them as calls (`from_reasoning_N`); each such turn writes a `Note` ("F841 probe: …") on the log.
Subject `abcc-412d2d8-probe-a` — straight to LM Studio, **no tap, no temperature**: the one
difference from A3 is the commit. Runs `w8-1790273844694` (K), `w8-1790274855539` (R `shell_06`); every probe cell of F841–F843 is in `research/a3/probe-cells.tsv`.

| cell | A3 (3 passes) | probe (a) | turns recovered (calls) | nudges |
|---|---|---|---|---|
| K `finish_the_cancelled_status` | `...` Recon, said_nothing | **fail — after Builders edited** (`RETRY candidates 3`, want 7) | 6 (11) | 1 |
| K `round_at_the_line_not_the_total` | `...` Recon, said_nothing | **pass** | 4 (7) | 1 |
| K `trace_dropped_samples` | `...` Recon, cap | **pass** | 3 (5) | 0 |
| R `shell_06` | `...` Recon, said_nothing | **pass** (all four parts) | 4 | 0 |

Every cell now leaves Recon, and the one failure is a wrong change (`should_retry` rewritten to
`status != FAILED`), not an absence. Recovery happened in Builders too (3 of the 6 turns on
`finish_the_cancelled_status`). This matches temperature 0 (F840: K 7 / 9, `shell_06` 3 / 3) without
changing the sampler — the ruling that abcc sends no temperature is untouched.

⚠ n = 1 per cell. A second K pass and a full R run (the regression check on the 13 other cards)
were queued behind it; see the addendum below when they land.

## F842 — Recon briefed WITHOUT the card's THE FIX recipe still drafts the fix: 0 / 4, unchanged

**2026-09-24 20:59 → 21:17.** F839 option (b) as a PROBE: abcc branch `probe/recon-no-recipe`
`0d54e08`, NOT merged. `brief::localize` drops the card's `THE FIX` section (to the next
all-capitals heading — a dry run over all 14 R prompts cut only that section; `runtime_11` has
none); Builders still gets the whole prompt. Subject `abcc-0d54e08-probe-b`, server default, no
tap. Run `w8-1790272786560`, the four drafting cards only.

**All four end exactly as in A3: Recon, `reasoning_runaway` at the 50,000-character ceiling, no
edit** (`edit_06` 266 s, `edit_09` 228 s, `sec_04` 227 s, `shell_04` 194 s). The brief really was
cut: `BriefRecorded` on `edit_06` has no `THE FIX` and still has `A TEST`, and `sec_04`'s Recon prompt
is 2,061 tokens against A3's 2,377. **The recipe in the brief is not what makes Recon design the
fix.** The prompts still name the file, the lines and the defect, which may be enough to start it.

## F843 — letting Builders run after a Recon that never answered: K 2 / 3, but the drafting cards run away in Builders too

**2026-09-24 21:42 → 22:59.** A third PROBE, (d), after F842 came back null: abcc branch
`probe/recon-fallthrough` `132edd3`, NOT merged. A Recon that ends `Unmeasured` (ceiling, cap,
said_nothing) no longer ends the attempt: Builders runs with the report *"Recon did not report:
{why}. … find the place yourself from the task above"*. Recon's own ending stays on the log. Four
abcc-drive tests pin the old rule and fail on the branch (named in its commit). Subject
`abcc-132edd3-probe-d`, server default, no tap. Runs `w8-1790275322427` (R, 5 cards),
`w8-1790278485510` (K).

| cell | Recon | Builders | result |
|---|---|---|---|
| R `edit_06` | ceiling | **ceiling, no edit** (6 m 30 s) | fail |
| R `edit_09` | ceiling | **ceiling, no edit** | fail |
| R `shell_04` | ceiling | **ceiling, no edit** (1 read) | fail |
| R `sec_04` | ceiling | 5 `edit_file`, 24-round budget exhausted | fail — **hidden test PASSES**; one existing test red (`session::tests::save_redacts_secrets_and_writes_owner_only`) |
| R `shell_06` | said_nothing | said_nothing again (4 nudges in all) | fail |
| K `finish_the_cancelled_status` | said_nothing | said_nothing | fail |
| K `round_at_the_line_not_the_total` | said_nothing | edits | **pass** |
| K `trace_dropped_samples` | never answered | edits, round budget exhausted | **pass** (the verifier grades the tree) |

**The drafting failure follows the model, not the phase.** Three of the four cards hit the ceiling
again in Builders — a phase that can write — without making an edit. What it reasons about there
is not on the log (lengths only); a tapped replay of `edit_06` and `shell_04` was queued to read it.
`sec_04` is the one drafting card that reached an edit, and its behaviour test passed.

For the said_nothing population the fall-through helps on K (2 / 3, both passes after a silent
Recon) and not on `shell_06`, where Builders went silent too — the same tool call inside the
reasoning, which (d) does nothing about and (a) recovers.

## F844 — a model's `2>nul` kills abcc's checkpoint: the work is lost and the attempt has no ending

**2026-09-24 23:05, probe (a)'s second K pass** (run `w8-1790280002291`, `trace_dropped_samples`).
Builders ran, through abcc's `bash` tool, `… dir C:\…\python* 2>nul`. Under Git Bash `2>nul` is not
the Windows null device: it created a **file named `nul`** in the worktree. At the next checkpoint
abcc's `Repo::checkpoint` (`abcc-vcs/src/lib.rs:249`) runs `git add -A` into a scratch index, and
git cannot index a Windows reserved name — `error: short read while indexing nul … fatal: adding
files failed` (exit 128). **abcc exited 1**: no checkpoint, no `AttemptEnded`, replay says *"it has
no ending on the log — in flight, or a crash took it"*, and the harness graded the untouched tree
(`run.py exited 1`).

**The work was right.** The abcc worktree still holds it (`pipeline/ingest.py`, `pipeline/stats.py`
modified, plus `nul`); the K verifier run over a copy of it without `nul` says `RESULT: PASS all four
channels report both firmware revisions (54 samples, 12 windows)`. So this K pass is 2 / 3 as graded
and 3 / 3 in substance.

First occurrence: it is the only `abcc_exit: 1` and the only `unable to index file 'nul'` in every
harness run on disk. It is not caused by the probe — any attempt whose `bash` redirects to `nul`
reaches it. ▶ Not fixed (an engine change is David's). The smallest repair is an exclude pathspec
on that one `git add` for Windows device names (`nul con prn aux com1-9 lpt1-9`, any depth), or
deleting such a file before the snapshot; either way the checkpoint must not be able to crash the
attempt it is recording.
