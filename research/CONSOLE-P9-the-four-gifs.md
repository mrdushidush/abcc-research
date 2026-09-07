# CONSOLE P9 — the four GIFs, decoded, and a filter that only ever asked frame 0

**Status: the loader takes every frame now, and `abcc paint --play <seconds>` runs the field and
says what rate it reached. All four pictures the corpus can draw are animations — 676 frames
between them, every single one a different picture — and the still loader had been dropping 672 of
them.** Findings **F642–F644**; next free number is **F645**. Built 2026-09-07 against `D:\dev\abcc`
at `92c55d8`. **526 tests passing (up from 513), 19 ignored, clippy clean under `-D warnings`,
`cargo fmt --all --check` clean.** Sixteen of those tests are new — thirteen that run everywhere and
three corpus instruments — and **eight mutations were run against eight of them, one at a time**.

▶ This closes item 6 of CONSOLE's non-eyeballing queue: *decode the four GIFs*. What is left there
is `rust-embed`, and §8 argues its stated precondition is not met.

**The session's shape: the queue item read like a decoder change and turned out to be two other
things. The first is that the animation was worth having — every frame differs, so nothing here was
dropped harmlessly. The second is that F565's admission filter, the one that found twelve broken
images, passes the four survivors only because it looks at frame 0: asked of every frame it refuses
310 of 676, including both buildings. A well-meant loop over the frames would have emptied the
corpus and looked principled doing it.**

---

## 1. What shipped

* **`abcc_tui::assets::Film`** — every frame of one file, scaled on the way in, with the time each
  is held. The play head takes a `Duration`, not an index. A still is a film of one frame, so
  nothing downstream has to know which it opened.
* **`abcc_tui::assets::Motion`** and **`Poses::open_playing`** — a corpus opened with the frames or
  without them. `Poses::sprite` still answers the first frame, so every existing caller is
  unchanged; `Poses::film` is the new one.
* **`abcc paint --play <seconds>`** — plays the field and reports the rate, with `--cell <px>` for
  the one thing a Windows terminal will not tell us (F644).
* **`cli::Paint`** — the six `paint` arguments as a struct, for the reason `Run` is one.
* Tests: **7** in `abcc-tui/tests/assets.rs`, **3** in the new `abcc-tui/tests/films.rs` (corpus
  instruments, `#[ignore]`d), **2** in the new `abcc/tests/paint.rs` (real git, real log, a real
  GIF the test writes), **3** in `paint.rs`'s own unit module, **1** in `abcc/tests/cli.rs`.
  Two new test targets: `paint` drives real git so it joins the process bucket, `films` does not.

1,649 lines added across 11 files.

⚠ **And adding a test file is what re-derived `CLAUDE.md`'s two test lists, which had drifted
again.** The cheap middle rung named **24 targets of 47** and ran **291 tests** under a heading that
said 251; the process bucket said nine and is thirteen (`corpus`, `replay` and `sortie` had been
added since, plus `paint`). Re-derived: **34 names, 383 tests, 2.5 s**, against a full suite that is
now **28.9 s** rather than the 16.8 s written down. The file's own warning — *a list of names does
not fail when the workspace grows, it just stops covering things* — was right, including about
itself.

---

## 2. F642 — all four pictures are animations, and every frame is a different picture

`assets::load` calls `image::load_from_memory`, which for a GIF returns **the first frame**. That is
the right answer for a still and it is the whole of what the battlefield has ever drawn. Measured at
source, 2026-09-07:

| file | frames | distinct | hold | loop | source | at 150 px | decode |
|---|---|---|---|---|---|---|---|
| `coder-E-attacking.gif` | 97 | **97** | 40 ms | 3.88 s | 300×450 | 5.6 MB | 0.27 s |
| `coder-W-attacking.gif` | 97 | **97** | 40 ms | 3.88 s | 300×450 | 5.6 MB | 0.24 s |
| `building-E-attacking.gif` | 241 | **241** | 40 ms | 9.64 s | 380×568 | 13.8 MB | 0.77 s |
| `building-W-attacking.gif` | 241 | **241** | 40 ms | 9.64 s | 380×568 | 13.8 MB | 0.76 s |

**Every frame differs from every other frame** — hashed, not eyeballed — so there is nothing in
these files a still loader was right to drop. Every hold is 40 ms, which is **25 FPS**, and the
field repeats on the longest loop it holds: **9.64 s**.

⚠ **The GIFs are not the shape the module's docs describe.** `assets.rs` said the corpus is
"292×221 for the idle poses and 292×181 for everything else" — that is the *PNG* poses, the twelve
F565 found unusable. The four that ship are 300×450 and 380×568, which is a different aspect ratio
and a taller figure. The doc comment now says so.

### What the frames cost, and why `Motion` is a choice rather than always the frames

| | frames held | RGBA | to open |
|---|---|---|---|
| `Poses::open` (still) | 4 | 0.2 MB | **0.06 s** |
| `Poses::open_playing` | 676 | **38.7 MB** | **2.05 s** |

34× the time and 190× the memory. `abcc paint` draws one picture and would have been paying two
seconds for 38 MB it never looks at, so the still path stays still and `--play` asks for the rest.

🚨 **The source is never held.** A building at source is 241 × 380 × 568 × 4 = **208 MB** of frames;
scaling each frame as it comes out of the decoder is the difference between a type you can put four
of on a battlefield and one you cannot. `Film::bytes` answers what an instance costs rather than
leaving it to arithmetic.

---

## 3. 🚨 F643 — the admission filter is a statement about frame 0, and per frame it empties the corpus

F565 gave the corpus two questions: is the art one connected thing (`Sprite::coherence` ≥ `INTACT`,
90) and does it stay inside its own frame (`Sprite::top_edge_ink` == 0, which is how the four
captioned poses were caught). The four GIFs pass both. **They pass them on frame 0.**

Asked of *every* frame at source resolution:

| file | coherence | frames under `INTACT` | frames touching the ceiling |
|---|---|---|---|
| `coder-{E,W}-attacking.gif` | 94–99 | **0** of 97 | **8** of 97 |
| `building-{E,W}-attacking.gif` | **71**–100 | **63** of 241 | **95** of 241 |

**310 of 676 frames — 46% — would be refused by the filter that admitted the files they are in.**

▶ **And the shape of it is the point: these are runs, not scatter.** The buildings' ceiling contact
is frames 70, 90–94, 104–105, 124–129, **152–192** and **196–235**; the coherence dips are 60–85,
95–114 and a handful of singletons. Two runs of about forty frames each is **1.6 s of a 9.6 s loop**
with something leaving the top of the frame, and a long stretch with a piece of the body detached.
That is what *attacking* looks like — a muzzle effect and thrown debris. Neither measurement is
wrong; both are answering a question about a still, put to a film.

**So the rule is written down where the constant is** (`assets.rs`, on `INTACT`): the admission
question is asked of frame 0 and stays there, and anything that later filters frames has to be a
different question with a different name. The instrument that would catch a change of mind is
`films.rs::the_admission_questions_are_about_the_first_frame_only`, which asserts both that frame 0
passes for every file and that **some** frame does not — so if better art arrives that is clean all
the way through, the test fails and says the frame-0 rule can be re-argued.

⚠ **And F565's first trap was waiting here too.** Measured on the
*scaled* frames instead of the source, the buildings read a minimum coherence of **90** — exactly at
the line, one point from a completely different conclusion — because downscaling spreads soft edges
until fragments touch. The instrument decodes twice on purpose, and says why.

---

## 4. F644 — the terminal will not say how tall a cell is, and we are not going to ask

Redrawing in place needs to know how many rows the picture occupies, which is
`field height ÷ cell height`. `crossterm::terminal::window_size()` returns pixel dimensions —
and on Windows its entire implementation is:

```rust
Err(io::Error::new(ErrorKind::Unsupported,
    "Window pixel size not implemented for the Windows API."))
```

The alternative is an XTWINOPS `CSI 16 t` query, and `paint.rs` already refuses that class: *a
probe that hangs waiting for an answer is worse than a picture that does not appear.* So the cell
height is **told**, `--cell <px>`, defaulting to 20 — Windows Terminal at 100% scale with its
default font. It is a guess, and the only thing it decides is how many rows the picture is given:
too small and the picture overwrites the report under it, too large and there is a gap. Both are
visible to the operator, which is what makes a guess allowable where a hang is not.

---

## 5. The player, and what its number is

`--play` reserves the rows, walks back up into them, and then per frame saves the cursor, writes
the sixel and restores it — the W5 spike's method, which is the one that works. **The cursor is not
hidden**: a run stopped with Ctrl-C would leave the operator with an invisible caret, and a caret
parked over the corner of the picture is the cheaper of those two.

Measured on this box, the real log's 7 units on a 640×360 field, `--px 150`, into a file:

```
playing 676 frame(s) across 4 pose(s) — 38.7 MB at 150 px, decoded in 2.03 s,
  longest loop 9.64 s, one frame every 40 ms
played 200 frame(s) in 8.00 s — 25.0 FPS achieved against 25.0 asked, 0 dropped
  frame cost mean 4.98 ms, p95 11.46 ms — 201 FPS sustainable unpaced,
  2.53 MB/s of sixel at this rate
```

**Two rates, because they answer two questions.** *Achieved* is what the operator saw and cannot
beat the rate the art asks for. *Sustainable* is one over the mean frame cost — what the path could
do unpaced — and it is the one that says whether there is room for a bigger field or a slower
terminal. A report that gave only the first would call a 201 FPS path and a 25 FPS path the same
result.

🚨 **What this does NOT settle is the end-to-end question**, and the report says so itself: stdout
was a file, so nothing drew any of it. Run in a sixel terminal, a display that cannot keep up
eventually stops accepting bytes and the write blocks, so *some* of the display cost is in the
number — but this still does not measure what the terminal did with the bytes after taking them.
**The 25.6–28.6 FPS the W5 spike reported for a full-viewport composite remains a number from
another encoder.** ▶ The instrument to close it now exists and takes eight seconds; it needs
somebody in Windows Terminal, and it belongs in the eyeballing review.

For the record beside F562's generation table (1.91 ms/frame for 16 sprites at 640×360, encode
only): **4.98 ms** here is that plus a fresh canvas, the tile rules, the deploy, and a 100 KB write
per frame. At the corpus's own 25 FPS that is **2.53 MB/s**, against the ~23.5 MB/s Windows
Terminal was measured ingesting — about 9× headroom, which is the same conclusion F562 reached from
the other side.

**Pacing is against the wall clock, not a frame counter.** A frame that overruns its slot must not
push the next one later, so `next_slot` answers the next boundary rather than the one already
missed and the player drops a frame instead of slowing the animation down. That only works because
`Film::at` takes a time rather than an index — both halves have to make the same decision, and
`the_next_frame_is_due_on_the_beat_however_long_the_last_one_took` is the guard on it. ⚠ Windows'
15.6 ms default timer granularity was the expected problem here and did not appear: **0 dropped
frames over 200**, twice.

---

## 6. Two near-misses, both in the tests rather than the code

🚨 **The frame extractor found itself.** `abcc/tests/paint.rs` asserts that consecutive frames
differ, which is the whole point of a player. Its first extractor split the output stream on `ESC`
and kept the parts beginning with `7` — but **a sixel payload is `ESC P … ESC \` and carries its own
escapes**, so every "frame" it returned was the empty string between the cursor save and the
payload's own introducer. Every frame identical, test failing, code fine. *The failure a test is
written to catch is also the failure its instrument can produce.*

⚠ **And the fixture was incomplete in a way that produced the same red.** The first corpus the test
wrote held only `coder-E-attacking.gif` — but a single unit on an empty field faces **west**
(`roster::face`: a thing exactly on the midline looks west), the corpus had no picture for it, and
the field was bare ground in every frame. Both causes were real: with the extractor fixed and the
single-pose corpus restored, the test still fails, which is how the comment in it can say so. The
test now asserts that the footnotes carry no *"have no picture"* line, so the fixture cannot
regress to measuring an empty field.

---

## 7. The mutations

Eight, one at a time, each against the test named for it:

| mutation | caught by |
|---|---|
| the play head always answers frame 0 | `the_play_head_holds_each_frame_for_its_own_time_and_wraps` |
| the play head does not wrap | the same |
| a declared zero delay is taken literally | `a_declared_zero_delay_becomes_a_hold_rather_than_a_division_by_zero` |
| `Playing` quietly loads a still | `a_still_corpus_and_a_playing_one_admit_the_same_pictures` |
| the player sleeps a whole tick after every frame | `the_next_frame_is_due_on_the_beat_however_long_the_last_one_took` |
| every frame draws the still | `the_player_redraws_in_place_and_the_frames_differ` |
| the cursor is never restored | the same |
| the report counts drops it did not have | `the_report_separates_what_was_drawn_from_what_could_be` |

All eight caught. The two worth having are the fifth and sixth: *sleep a tick per frame* is the
naive player and it looks like it works — it just runs the animation slower than the art says, by
an amount that changes with the size of the field.

---

## 8. ⏸ What is left, and why `rust-embed` should wait

The queue's last non-eyeballing item is *`rust-embed` the 16 distinct images, not 28*. **Its own
precondition — "when the asset set is settled" — is not met**, and two things have moved under it
since it was written:

* **F565 reduced 16 usable images to 4.** Embedding sixteen would ship twelve pictures the field
  refuses to draw.
* **The four that survive are the whole weight.** 34.3 MB of the corpus's 35 MB is those GIFs. The
  release binary is **8.4 MB**; embedding them makes it about **43 MB**, and puts 34 MB of binary
  assets permanently into the repository's history. De-duplication saves nothing that matters — the
  twelve distinct PNGs are about 1 MB between them.
* **David has said better art is coming** ("i will add much better art later on", 2026-08-31), so
  the bytes that would go into git are the ones expected to be replaced.

▶ **The friction it would remove is also small**: `abcc paint` with no `ABCC_SPRITES` already
refuses with a sentence naming the flag, the variable and where the corpus lives. **This is
David's call, not a defect to fix quietly** — the three answers are *embed the four anyway*,
*embed nothing until the art settles*, and *embed a pre-scaled corpus*, which is a third thing
again because it would fix `--px` at the size it was encoded for.

Everything else on CONSOLE's list is unchanged: the eyeballing review, the three console
instruments (F587), `redirect`/`resume` (F585), `--px`, sixel on the inline viewport, the 96 voice
lines. **And the end-to-end display rate is now one command away from being a measurement rather
than an inherited number.**
