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
