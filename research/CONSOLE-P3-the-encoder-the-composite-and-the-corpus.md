# CONSOLE opens — an encoder written from the format, the composite as a type, and a corpus that is smaller than it looks

**Status: FLEET's two residual rulings are landed, and CONSOLE has its first three pieces.**
Findings **F557–F562**; next free number is **F563**. Built 2026-08-30 against `D:\dev\abcc` at
`6fbaf4f`, landed as `1a460c3` (the two rulings), `57de658` (the sixel encoder), `f372c4d` (the battlefield,
the assets and `abcc paint`) and `576432a` (the frame-cost instrument). **399 tests passing, 13
ignored, 61 targets, clippy clean under `-D warnings`, `cargo fmt --check` clean.**

▶ **There is something to look at.** `abcc paint --sprites <dir>` composites the real corpus onto an
opaque isometric field and writes one sixel frame to stdout. It is a still and not a screen, on
purpose: what it answers is *does this terminal draw **our** composite*, and the W5 spike could only
answer that for the spike's own encoder.

The session's shape was: two rulings David made before going to sleep, then the flagship — and
**three of the six findings came from measuring things the brief had already written down.**

---

## 1. ✅ David's two rulings, landed

### F555 — the standard rung is a conjunction, and formatting runs first

The gate said MISSION ACCOMPLISHED about a tree `cargo fmt --check` refuses: four green rungs, the
Judge with no findings, and one function whose single-line body rustfmt reformats. rustfmt was in
**none of the four rungs**, so ADR-0017's criterion — *a correct tree is one that could land* — was
being checked with part of the repository's own declared standard missing.

**Ruled: add it unconditionally.** `Standard.command` becomes `Standard.commands`, a conjunction in
the order it runs, and the first refusal ends the rung. Cheapest first — formatting is a parse and a
print, clippy is a compile, and an operator waiting on a red wants the fast one to say so.

Two things the rung owes a reader, and both are why it does not simply return the last outcome:

* **A red says which command.** `standard: exit 1` with clippy's name nowhere near it sends a reader
  to the compiler for a formatting refusal — F555 read backwards, and the same class as F492's
  *non-zero exit from the wrong program*.
* **A green says what it checked.** The green is the sentence F555 caught lying, so it now names
  every command it stands on.

🎉 **The new rung caught the F555 shape in the commit that added it** — a call I had wrapped over
seven lines that rustfmt collapses to one. The check works, demonstrated on its author.

### 🚨 F557 — rustfmt colours a diff it is writing to a *file*

`cargo fmt --check` prints the diff it wanted. That output is the evidence ADR-0019 keeps, so it
goes into a durable SQLite log and is re-rendered in the TUI. **It carries ANSI escapes even when
stdout is a plain file rather than a terminal** — 5 lines' worth on the one-line-body fixture,
measured by redirecting to a file and grepping for `ESC`, not by assuming isatty behaviour.

▶ The command is `cargo fmt --check -- --color=never`. Clippy is left alone: changing what it prints
is not what was ruled.

### The pulse refuses a preflight

ADR-0010 §4's *reports and never gates* is aimed at the **rate**, which is a statistical verdict over
a population, and the reason it may not refuse is that it **cannot tell a hard task from a dead
server**. A pulse is the other thing — the host asked for one token and watched what happened, which
is the shape of a gate rung — so it may. **F539 is the price of the old reading**: both attempts
spent against a server whose listing answered normally throughout.

🚨 **`Pulse::refuses()` is deliberately not `!answered()`, and the gap between them is `NotTaken`.**
That variant is an *absence*: nobody asked, so nothing was measured. Letting it refuse would read
*nothing was measured* as *something failed*, which is the single confusion the whole `Outcome` type
exists to prevent — the same rule the gate's ladder already applies to an `Unmeasured` rung.

Three limits, each deliberate:

| Where | Refuses? | Why |
|---|---|---|
| `run` / `fleet` preflight | **yes** | it is about to spend the budget; F539 |
| `abcc check` | **yes** | it already refused on the *weaker* fault of an unconfirmed model, and a health command that exits 0 about a wedged server lies to whatever script asked it |
| `abcc breaker` | **no** | the rate is beside the pulse there, and the rate may never gate |

⚠ The instrument had to be right first. **F550 is a live demonstration that a health check can be
confidently wrong about a healthy box, and it was this one** — refusing on `message.content` would
have stopped every run on this machine.

### 🚨 F558 — nine `\uXXXX` escapes living in comments, where Rust never reads them

Found while matching text to edit, not by looking. Three source files carried sequences like
`\u26a0` and `\u00a7` inside `//` comments — **literal seven-character strings**, because Rust
interprets `\u{...}` in a *string literal* and not in a comment. A reader of `run.rs` saw

```
// \u26a0 It **reports and never gates** (ADR-0010 \u00a74): the sentence goes on the
```

three lines above a `writeln!` where the identical escape was correct and rendered `⚠`. That is why
it survived: the working spelling and the dead one sat next to each other. All nine repaired; a
scan over every comment line in `crates/` now returns zero.

---

## 2. 🚨 The encoder is rewritten, not ported — and that was not a close call

The W5 spike's encoder works and renders on David's own Windows Terminal. It could not be lifted,
and its own first line says why:

> *"modeled on OpenAI Codex CLI's `codex-rs/tui/src/pets/sixel.rs` … Output is byte-identical to
> Codex's encoder (its test vectors are ported below and pass verbatim)."*

That is a derived work with ported tests. Three standing positions land on it at once — **ADR-0001**
(*donors are a specification and a test corpus, never a source tree*; assets are the stated
exception and the sprites are still copied), **W12's** *reimplement from scratch*, and `CREDITS.md`,
which states in its own words that this repository is a clean-room rewrite in which *"no copyright
question arises"*. **Porting it would have made that sentence false for the flagship component.**

So `abcc-tui/src/sixel.rs` is written from the sixel format, which is public. The spike contributes
what a spike is for: its measurements.

### How the bit order was settled, which is the part an author cannot check alone

🚨 **An encoder and a decoder written by the same person share their mistakes and round-trip
perfectly while a terminal draws scrambled bands.** Whether bit 0 of a data byte is the top row of a
six-row band or the bottom is exactly that kind of fact.

It was settled against a **different implementation that is proven on screen**. The spike's `hello`
output was redirected to a file — its sixel goes to stdout, so no terminal is needed — and decoded
under this convention:

```
raster 240x96, 100 palette entries defined, 96 rows written
  row 0: 240 px, 1 colours  UNIFORM (255, 255, 0)
  row 1: 240 px, 1 colours  UNIFORM (255, 255, 0)
  row 2: 240 px, 34 colours
```

240×96 is what the spike prints for itself, and rows 0–1 uniform yellow over a 34-colour gradient is
the *yellow-bordered gradient box* its README documents. **Under the opposite convention the border
would have decoded at rows 4–5.** That is the donor used the way ADR-0001 allows — as a test corpus,
by its output, never by its source.

Then every pixel of a composited canvas round-trips: **1,280 of 1,280 land on the right palette
entry**, with zero unset.

### 🚨 F559 — a sixel cannot reproduce its source byte for byte, and the reason is the format

Sixel defines a colour register in **percentages** — `#n;2;r;g;b` with `r,g,b` in 0–100, about 101
levels a channel. **Only 32 of the 256 RGB332 entries survive that exactly**; the rest land within
1/255, worst channel error 1, measured over the whole palette rather than over one image.

Invisible in practice and worth writing down anyway: nothing in this project should ever assert that
a rendered sixel matches its source pixels, and the round-trip test compares **palette index**
rather than colour for exactly this reason.

### ADR-0012 §2 as a type, not a comment

* **`Canvas`** is opaque — three bytes a pixel, no alpha to lose — and is the only thing with an
  `encode`.
* **`Sprite`** is RGBA and has **no path to a sixel at all**. The single exit is `Canvas::blend`.

A floating sprite — the thing F145's feathering makes wrong — is not expressible with this module.
Same technique as `line::describe` for event coverage and `theme` for labels: a compile failure
rather than a sentence.

---

## 3. 🚨🚨 The corpus is smaller than the brief says, twice over

Both of these are the shape the standing instruction names: **a file count is not a capability
count**, and **a count travels without its units**.

### F560 — 28 files, 16 distinct images

Every `qa-*.png` is a **byte-identical copy** of its `cto-*` twin. Twelve duplicate pairs, verified
by hashing all 28 files:

| what | count |
|---|---|
| files in `sprites/` | **28** |
| distinct images | **16** |
| duplicate pairs (`cto-*` = `qa-*`) | **12** |

▶ **The battlefield therefore has one humanoid design and not two.** The QA unit and the CTO unit
cannot be told apart by their art; colour, position and label are what separate them, and any roster
design that assumed a sprite per role has to be revised now rather than after it is drawn.

The rest of the corpus is thinner than it reads too: `coder-{E,W}-attacking.gif` (97 frames) and
`building-{E,W}-attacking.gif` (241 frames) are **attacking only, east and west only** — no idle
animation and no north or south facing for either.

`Corpus::distinct()` answers this by hashing rather than by counting filenames, and `abcc paint`
picks distinct images rather than the first nine files, or it would paint the same figure twice and
call it two units.

### F561 — F145's 5,062 reproduces exactly, and its companion number is mislabelled

Measured again through a decode path this repository wrote, on `cto-E-idle.png` at 292×221:

| band | pixels |
|---|---|
| clear (alpha 0) | 49,466 |
| **alpha 1–127** | **5,062** |
| alpha 128–254 | 3,983 |
| opaque (alpha 255) | 6,021 |

🎉 **The 5,062 lands exactly**, which is what makes the rest of the row trustworthy.

⚠ ADR-0012 §2 renders the comparison as *"5,062 semi-transparent pixels (alpha 1–127) against
~10,000 opaque"*. The 5,062 is exact. **The ~10,000 is the set a threshold-128 rule *keeps*
(6,021 + 3,983 = 10,004), not the set that is opaque, which is 6,021.** The argument is unchanged
and slightly starker than its label: of the **15,066** pixels visible at all, **9,045 carry partial
alpha** — the majority — and a threshold erases a third of them.

**The first version of `Sprite::feathered` returned 9,045 under a doc comment claiming 5,062.** I
transcribed the ADR's number onto a method that answers a different question. It is now two methods:
`feathered` (any partial alpha) and `dropped_by_threshold` (F145's question — what a threshold
erases).

### Scaling premultiplies, and it is not a nicety

A straight RGBA resize mixes the *colour* of fully transparent pixels into their visible neighbours.
That colour is usually black, so the result is a dark rim around everything — and **this corpus is
the worst case for it**, since 9,045 pixels on one sprite carry partial alpha.

Tested with the failure in miniature: one opaque white pixel beside one fully transparent **black**
one, 2×2 down to 1×1. Straight resize hands back grey; premultiplied hands back white. ⚠ The
assertion is on the *colour* and not the alpha — both methods produce the same alpha, which is why
this bug is easy to ship.

---

## 4. The battlefield, and a test that was measuring nothing

Two placement rules, both of which look like decoration until they are wrong:

1. **A unit is anchored bottom-centre.** A sprite is mostly empty air above a small pair of feet, so
   top-left placement floats a tall unit a body-length behind where it stands — and the corpus is
   *not one height* (idle poses 292×221, everything else 292×181), so the error would differ per
   pose of the same unit.
2. **Depth order is `cx + cy`, drawn ascending.** Roster order puts whichever unit was queued last
   on top, so a unit at the back of the field occludes one at the front about half the time. No
   z-buffer is needed: on a grid, distance from the camera *is* the sum of the coordinates.

### ⚠ The depth test as first written could not fail

It placed two 20 px sprites at cells `(0,0)` and `(2,2)` on a tile-40 grid. Those ground points are
**88 px apart vertically**, so the sprites never touch — the assertion checked a colour in a region
only one sprite could occupy, and **would have passed with the sort deleted**.

Rewritten at tile 8 to force a 16-row overlap, and then *checked the way a control should be
checked*: the sort was removed and the suite run again.

```
test a_nearer_unit_covers_a_further_one_whatever_order_it_arrives_in ... FAILED
```

It fails without the sort and passes with it. The other five tests in the file passed under the
mutant, which is the useful part of the result — it says precisely which test carries the claim.

### The frame, end to end

`abcc paint` against the shipped corpus, decoded back:

```
raster 640x360   holes 0   colours 106   non-ground 19,987 (8.7%)
ink spans rows 4..356 of 0..359
```

🚨 **Zero unset pixels** — the composite's whole promise, checked rather than asserted. And nothing
at either edge: the grid origin is vertically centred because at `height/4` the back rank lost **54
rows off the top**, which the first render showed and the ink profile now guards.

---

## 5. What CONSOLE still owes

None of this is blocked, and the order below is the order the exit criterion cares about.

* **The battlefield is not wired to the log.** `paint` reads a directory; the roster has to come
  from the event log's task projection, one sprite per live task, positioned by slot.
* **A frame is not an animation.** ✅ **Generation is now measured (F562, below) and it is not the
  problem.** What is still unmeasured is **display** — the terminal receiving and drawing the bytes,
  which is what the spike's end-to-end 25.6–28.6 FPS includes and this does not.
* **The GIFs are undecoded.** Four animated assets, and the loader takes the first frame.
* **The eight verbs and the six fun queries** (ADR-0012 §4, §5) — the control channel, the typed
  lifecycle and the paged read. ⚠ *Eight verbs that half-work are worse than three that work.*
* **The 96 voice lines**, and the two lifecycle states that have none: `Holding`, `Commandeered`.
* **`rust-embed`** for the 44 MB, when the asset set is settled. F560 says 12 of the 24 PNGs are
  redundant, so the embedded set should be the 16 distinct images.
* ⏸ **Two spike-scale unknowns remain and neither blocks anything**: sixel over the *inline*
  viewport (the spike used the alternate screen throughout), and WT's canvas renderer versus
  Direct3D on other machines.

**The exit is unchanged: David runs a real task through it, on purpose, twice, without turning the
sprites off.**

---

## 6. ✅ F562 — what one frame costs to generate

Taken because §5 above listed it as owed, and because it is the number ADR-0012's animation case
rests on. Release build, sprites decoded and scaled once the way an animation would hold them, 30
frames after 3 warm-up frames, kept as `crates/abcc-tui/tests/frame_cost.rs` (`#[ignore]`d, pointed
by `ABCC_SPRITES`).

| field | sprites | ms/frame | frames/s | bytes | MB/s at 15 FPS |
|---|---|---|---|---|---|
| 640×360 | 1 | 0.99 | 1012 | 12,006 | 0.2 |
| 640×360 | 4 | 1.24 | 805 | 27,037 | 0.4 |
| 640×360 | 16 | **1.91** | **523** | 73,101 | 1.1 |
| 1280×720 | 1 | 3.84 | 260 | 12,653 | 0.2 |
| 1280×720 | 4 | 4.26 | 235 | 27,673 | 0.4 |
| 1280×720 | 16 | **5.13** | **195** | 73,736 | 1.1 |

▶ **Cost tracks screen area, not sprite count.** Sixteen sprites cost **1.9×** one sprite, while
four times the area costs **3.9×**. That is F144's *screen area binds before throughput does*
arriving again from the generation side, and it was not assumed — the table is what says it.

▶ **The transport has room too.** At a C&C 15 FPS tick the worst row is **~1.1 MB/s** against the
**~23.5 MB/s** Windows Terminal was measured ingesting (F144).

⚠ **This is GENERATION ONLY.** Composite plus encode, with nothing drawn. A fast result here settles
one thing and no more: **the encoder is not what is in the way.** The end-to-end number — which is
what the spike's 25.6–28.6 FPS is — has not been taken for this encoder and is still owed.

⚠ **`--release` is not optional.** Debug is roughly **6×** slower on this path; a number taken from
it would say the opposite of the truth. The test's assertion is deliberately loose (four times the
tick) because it exists to catch an order-of-magnitude regression on a shared desktop, not to police
a few per cent.

---

## 7. ▶ The next session is a review, at David's request

*"next session is human in the loop. I want to eyeball the console and terminal rendered so I can
approve your work."* — David, 2026-08-31.

The review script is the head block of the session brief. What it puts in front of him: `abcc paint`
at **75, 100 and 120 px** (F143's band — 🚨 **which size reads as C&C is his taste, not a
measurement**), `abcc watch` in both themes over a log that already holds **29 real tasks**, the
table above, and the three corpus facts in §3 — of which **F560 is a question for him**, since one
humanoid design instead of two is either something to live with or a reason to want new art.

🚨 **If what he dislikes is the sixels themselves rather than a colour or a size, that is
`SUMMARY.md`'s fifth falsifier firing.** The honest response is the text ladder, which already
exists — that is precisely why it shipped at Skeleton.
