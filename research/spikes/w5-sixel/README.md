# W5 sixel spike — THROWAWAY

**Phase-1 spike under §15 ("spikes and benchmark harnesses only, clearly marked as
throwaway"). Not ABCC 2.0 product code.** The question it answers: can Ratatui render
ABCC's sprites in David's real Windows Terminal — the feasibility test for the
C&C-1995-style TUI console decided on 2026-08-19.

The sixel encoder is modeled on OpenAI Codex CLI's `codex-rs/tui/src/pets/sixel.rs`
(RGB332 → 256 colours, alpha threshold 128, transparent-background DCS) and passes
that encoder's test vectors byte-for-byte. The 256-colour ceiling is not a
compromise: the original C&C ran in VGA mode 13h, 320×200×256.

## Run it — in a real Windows Terminal tab

Not inside tmux or Zellij (they strip sixel), not over SSH.

```
cd research/spikes/w5-sixel
cargo build --release
target\release\w5-sixel-spike.exe probe
```

`probe` reports what the terminal claims: DA1 attributes (attr 4 = sixel) and the
cell size in pixels. **Pass its reported cell size as `--cell WxH` to everything
after it** (default is 10x20). This is the query `ratatui-image` panics on under
Windows (issue #69); here it just times out politely if unanswered.

Then the five questions, in order:

| # | command | what to look for |
|---|---------|------------------|
| 1 | `... hello` | a yellow-bordered gradient box; right half checkerboard with the terminal background showing through the holes |
| 2 | `... sprite` | the CTO sprite at 50/75/120/180 px — **which size reads as C&C at arm's length? This is David's judgement, not a measurement** |
| 3 | `... animate` | the coder attack GIF (97 frames, native 25 FPS) looping in place; flicker? tearing? stats on exit |
| 4 | `... tui` | the flagship look: battlefield JPEG + marching coder + CTO + QA inside a Ratatui C&C layout with radar, sidebar, status strip. Try resizing the window, `b` for other backdrops, `r` to force redraw |
| 5 | `... bench` | throughput table (also appended to `w5-sixel-bench-results.txt`) — the ceiling is the largest N whose FPS still clears ~12–15 |

Useful variations:

```
sprite D:\...\qa-W-attacking.png --sizes 60,100 --filter nearest
animate --height-px 200 --fps 12
animate --opaque              # composite on black — no transparency ghosting
tui --fps 15 --sprite-px 120
bench --height-px 100 --step-ms 4000
```

## What "it worked" means

All five: sixel renders, a sprite size David likes exists, animation holds its rate
without flicker, the sixel survives Ratatui redraw/resize/alternate-screen, and the
bench ceiling comfortably covers a battlefield's worth of units at ~12–15 FPS.

If it does not work: a text-and-colour Ratatui console with the radar, the C&C
sidebar and all 96 voice lines is still C&C in every sense except the sprites.

## Design notes

- Encoder hand-rolled (trap 1: `ratatui-image`'s stdio font query panics on
  Windows; Windows is absent from its compatibility matrix). Cell size is a flag.
- Windows Terminal has sixel (stable ≥1.22; this machine: 1.24), **not** kitty
  graphics — `arewesixelyet.com` is stale on this, trust the machine.
- The tui demo composites backdrop + sprites into **one sixel per tick** and
  paints it into the viewport widget's inner area after each Ratatui draw.
  Ratatui's diff never touches those untouched cells, so the image survives;
  bench phase A measures the alternative (N small per-sprite sixels).
