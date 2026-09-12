# LINEAGE P5 — the first sortie carrying both new fields, and neither reader said a word

**Status: queue item 3 is CLOSED, and it closed in the wrong direction.** `abcc` `223ae3a` →
**`f3ce25c`**, one commit, **621 tests** (was 615), 19 ignored, fmt and `clippy --workspace
--all-targets -D warnings` clean. Flown on `qwen3.6-35b-a3b-mtp@iq3_s` at `-c 40960 --parallel 1`,
one attempt, 10 model calls, 9 tool calls, 3 m 28 s. Findings **F718–F723, next free F724** — ask
`fledger.py next`, never this line.

🎉 **F713's `output` and F715's `seed` are on a live log, and the seeds recompute from the log's
own fields, 10 of 10.** Both had been proved against the scripted provider and a raw HTTP probe and
neither had been through `abcc run`. They are there, they are correct, and the derivation is
checkable from the record alone.

🚨 **And no reader showed either of them.** `abcc watch` rendered a model call as *model, head,
budget* — all three constant across a phase, so two consecutive calls printed the same line — and
`abcc replay` listed a tool's calls, tier and elapsed time with no mention of what it handed back.
**A field written with nobody reading it is exactly what F708 was**, one layer up: F708 was a
prompt surface the log could not see, this is a log surface the screen could not see.

🎉 **F717's quadrupling is confirmed by a second instrument, and F717 was if anything low.** It
estimated ~4× from the model's own prompt-token deltas across 1,136 windows. Measured on the bytes
actually written, the first attempt to carry the field went **18,634 → 74,043 body bytes: 3.97×**,
with output at **75% of the attempt's record**. The per-result mean this sortie is **1.56× F717's
estimated mean**.

⚠ **Three traps in the reading, each of which produces a clean, plausible, wrong number**: a
`serde(default)` zero that is also a legal seed, an unrecorded output that is not an empty one, and
a length in bytes reported as characters. All three are now negative-controlled.

🚨 **The task flown was the change this session then made by hand, and the fleet did not make it.**
`t11312` asked for the seed on the model-call line. The attempt read seven files, wrote nothing, and
ended `Uncertain/TruncatedAtCap`. It is attempt **96 of 96**, and the funnel moved from 5 of 95 to
**5 of 96**.

---

## 1. F718 — two fields shipped onto the log, and neither reader showed them

**F718 — the sortie answered *are the new fields live* with yes and raised a better question.**
`output` appeared on 9 of 9 tool calls and `seed` on 10 of 10 model calls, both carrying real
content. Then reading the attempt back:

```
  model    10 call(s), 76006 in / 21367 out, cap 16384, worst ttfb 4.5 s  [6 tool_calls, 3 stop, …]
  tool     read_file        7 call(s) at read   12 ms
```

Neither line mentions a seed or a byte. The feed was the same: `calling <model> · head <model> ·
16384 tokens back`, identical for every call of a phase, because the head is frozen per attempt
(ADR-0011) and the budget is a compile-time constant. **The one value on that line that changes
between two calls was the one not on it.**

▶ **Fixed at `f3ce25c`.** The feed names the seed and sizes a tool's output; `abcc replay` gains a
`sampler` line and a per-tool byte tally. On the sortie:

```
  sampler  10 of 10 call(s) seeded, 10 distinct
  tool     read_file        7 call(s) at read   12 ms  [53667 bytes back]
  tool     search           1 call(s) at read   1.1 s  [1634 bytes back]
```

and on an attempt from before F715, which is the reading that had to be got right:

```
  sampler  no seed recorded — this attempt was flown at the server's own sampling
  tool     read_file       18 call(s) at read   26 ms  [18 without recorded output]
  tool     bash            12 call(s) at exec   568 ms  [1 non-zero, 12 without recorded output]
```

⚠ **One trade, and it is recorded as a test rather than as a comment.** The size is omitted when a
call had no measurable ending. That arm was already spending **103 of F501's 112-character bar** —
the tool, the sentence `no measurable ending:`, a `CLIP`-clipped `Why`, the elapsed time — and
appending a size pushed the real log's worst row to **120**, where the overflow comes off the *end*,
which is where the size would have been. So the operator would have paid the tail of the error
sentence for a number that then fell off the frame. **156 of 2,156 tool calls are unmeasured, so
7.2% of rows carry no size on the feed**; `abcc replay` tallies their bytes, where there is room.

▶ The F501 line-discipline test caught this on its own, before the new test existed. That is the
second time `assert_one_line` has earned its keep on a change nobody expected it to touch.

## 2. F719 — the seeds recompute from the log's own fields, and the rounds solve

**F719 — a sortie's sampling is attributable from the record alone.** `seed_for` is
`sha256(attempt ‖ 0 ‖ head_digest ‖ 0 ‖ round_le)[..4]` as a little-endian `u32`. The log carries
`attempt`, `head_digest` and `seed` but **not** `round` — so the round was solved for, and a row
counts as confirmed only if some round in `0..64` reproduces its seed exactly:

```
10 seeded model calls on the log
reproduced from the log's own fields: 10/10

a11320 recon      rounds [0, 1, 2, 3, 4, 5, 6] · 7 distinct seeds of 7 calls
a11320 builders   rounds [0, 1, 2] · 3 distinct seeds of 3 calls
```

▶ **The solved rounds are monotone within a phase and restart at the phase boundary**, which is the
derivation's stated behaviour recovered from the outside. Nothing was taken on the code's word: the
oracle is the log, and the digest re-seeds per head (`2d7ac53218f2e381` for recon,
`9d491d116cf78300` for builders), so two heads do not share a draw.

⚠ **This is *attributable*, not *reproducible*.** F716 stands unchanged — MTP flips draft-acceptance
state on every call, 7 of 8 seeds pinned the output and one alternated. What F719 adds is that the
*input* is now recoverable from the record, which is the half a re-flight needs.

## 3. F720 — F717 measured rather than estimated, and it was low

**F720 — the quadrupling is real and the estimate understated the per-result size.** F717 derived
its number from the model's prompt-token deltas across 1,136 inter-call windows: 244 tokens at the
median, 984 at the mean, projecting *the log roughly quadruples*. This is the same question asked of
the bytes actually written to disk.

| | F717 (prompt deltas) | this sortie (bytes on disk) |
|---|---|---|
| per result, median | 244 tok ≈ 976 B | **2,165 B ≈ 541 tok** — 2.22× |
| per result, mean | 984 tok ≈ 3,936 B | **6,157 B ≈ 1,539 tok** — 1.56× |
| one attempt's record | — | 18,634 → **74,043 B = 3.97×** |
| output's share of that attempt | — | **75%** |

▶ **Attempt `a11320` alone lands on 3.97× against F717's ~4×**, from two methods that share no
instrument. ⚠ And the honest caveat is the sample: **n = 9 tool calls, one attempt, every one of
them read-class** — 7 `read_file`, 1 `search`, 1 `list_files`, and **zero `bash`**. A gate-running
attempt carrying `cargo` output would shift the mix, and the historical log says which way — the 96
attempts before this one ran 12 `bash` calls in a single attempt.

Projected over the whole log's 2,156 tool calls, the spread between the two instruments is the
whole answer:

| at | output alone | whole log | multiplier |
|---|---|---|---|
| F717's median | 2.0 MiB | 4.6 MiB | 1.8× |
| F717's mean | 8.1 MiB | 10.7 MiB | **4.1×** |
| this sortie's median | 4.5 MiB | 7.1 MiB | 2.7× |
| this sortie's mean | 12.7 MiB | 15.3 MiB | 5.8× |

▶ **Quote the multiplier with its method.** *Roughly quadruples* survives both instruments; a
single figure does not, and the mean/median spread is 2.3× within one sortie because the tail is
whole-file reads.

## 4. F721 — zero is both *no seed recorded* and a legal seed

**F721 — the field that distinguishes seeded from unseeded is `#[serde(default)]` over a type with
no vacant value.** `seed: u32`, so each of the **1,910** model calls logged before F715 replays as
`seed: 0`. A tally that counted rows rather than reading them would report the entire archive as
pinned to one seed — **the exact inverse of what F715 found**, which is that those calls were flown
at the server's own sampling where five identical requests gave five distinct answers.

⚠ **And the read is a convention, not a proof.** `seed_for` maps `u32::MAX` — llama.cpp's *choose
your own* sentinel — to `0`, so a genuinely derived seed can be zero, once in 2^32 calls. At this
log's 1,910 it has never happened and would take a century of sorties to. ▶ **So the reader says
*recorded no seed*, and never *unseeded*.** The two are different claims and only one of them is
provable from the record.

⏸ **An open call for the operator, not taken here.** `Option<u32>` would make the absence a type
rather than a sentinel and remove the ambiguity outright. It is a wire-format change to a field that
shipped the previous day, and the probability it ever bites is 2^-32 per call — so it is recorded
and left.

## 5. F722 — the seed's triple can repeat, and only the charter stops it

**F722 — a derivation property that is really a roster property.** `seed_for` takes
`(attempt, head digest, round)` and `round` restarts at zero with each phase. Two phases of one
attempt posting the **same** head would therefore repeat the whole triple and hand two different
prompts one sampler draw. Nothing in the derivation forbids it.

Measured over the whole log — 96 attempts, 1,910 model calls:

```
heads per attempt: min 1 max 3
heads posted in MORE THAN ONE phase of the same attempt: 0
a11320: 10 seeded calls, 10 distinct, 0 collision(s)
```

▶ **It has never happened, because the roster gives each phase its own head.** That is a fact about
the charter, and a charter edit is the thing that would break it — which is the same surface F711
made visible by putting the head's *digest* on the record.

🚨 **So `seeds.len()` is kept apart from `seeded_calls` rather than inferred from it.** The gap
between the two numbers is the only reading that would say so on the day it happens, and a fold that
stored a count could not. `abcc replay` prints `10 of 10 call(s) seeded, 10 distinct`, and would
print `🚨 1 call(s) shared a seed with another`.

## 6. F723 — a shipped line says *chars* and means bytes

**F723 — `Scrubbed::len()` and `String::len()` are byte lengths, and two readings of one attempt's
output differ by 291.** The first cut of this change reported `53376 chars` from a character count
and `53667` from the field itself, over the same seven `read_file` calls. ▶ Bytes is the right unit
for a field whose entire question is what it costs on disk and in a context window — so the tally is
`output_bytes` and the line says **bytes**, and the fixture carries a `·` so that 48 would mean
somebody counted characters. The test asserts the unit, not just the number.

⏸ **The same inaccuracy is on a line that already shipped**, and it is left for the operator:
`BriefRecorded` renders `{} chars` from `text.len()`, which is bytes, and its test asserts the byte
figure. One word on one line, in an arm whose reasoning is otherwise exactly right. It is flagged
rather than changed because the feed would then carry two units under one word, and which way to
resolve that is a call about vocabulary rather than about correctness.

## 7. The sortie itself, and what it says about the funnel

`t11312` asked for precisely the change section 1 describes: render the seed on the model-call line,
and add a named unit test for it. The attempt read `line.rs` whole (twice), `lines.rs`, `view.rs`
and three others, wrote nothing, and ended at the completion cap.

```
a11320 ended Uncertain { why: TruncatedAtCap { budget: 16384 } }
localize  7 turn(s), 6 tool call(s), 0 denial(s), 54516+4662 tokens (3789 reasoning), 71084 ms
change    3 turn(s), 3 tool call(s), 0 denial(s), 21490+16705 tokens (272 reasoning), 137407 ms
  REFUSED structural  exit 1  the attempt changed no file the repository tracks
  🚨 discarded apply_patch of 0 argument char(s), never run: empty
```

▶ **The `apply_patch` with zero argument characters is F622's shape exactly** — LM Studio buffers a
tool call's arguments whole and delivers them in one delta at the end, so a turn cut at the cap
never sends them at all. `argument_chars: 0` is a true reading, not a broken counter.

⚠ **The one number that moved**, from the repo's own fold rather than a hand-rolled query:

| | before | after |
|---|---|---|
| events | 11,311 | **11,391** |
| tasks | 67 | **68** |
| ended attempts | 95 | **96** |
| Success | 5 | **5** — 5.3% → **5.2%** |

🚨 **And a method note worth more than the number.** The first attempt at this table was a hand
parser over the event JSON, and it printed **`success 0 of 96 = 0.0%`** — clean, plausible, and
wrong, because it guessed the nesting of the outcome field. `abcc replay` bare is the fold that
already exists and it gave the right answer in one command. **Item 121 again: the instrument that
already works beats the one written at the point of use.**

---

## What is now open

⏸ **The two items this sortie did not touch.** K-series arms B and C are still unrun and are worth
more than before — arm A was taken unseeded on an MTP-on server, so a per-cell difference between
two quantizations sits inside F716's noise. If they are ever run, **n ≥ 3 at a recorded seed**, and
F719 means the seed can now be read back off the log rather than trusted.

⏸ **`review_recorded` is still 0 of 11,391**, and this session adds a fifth unreviewed commit
(`f3ce25c`) to session 5's four. It is not a forgotten command: `abcc review <change> <minutes>`
records how many minutes a **human** spent, `by` defaulting to `operator()`. An agent running it on
its own commits fabricates the measurement W13 says SELF-HOST is judged on.

⏸ **`Option<u32>` for the seed** (F721) and **`BriefRecorded`'s *chars*** (F723) are both recorded
and both left to the operator.
