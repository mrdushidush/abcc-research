//! Question 3: can it animate? Decodes a sprite GIF, pre-encodes every frame
//! to sixel once (Codex caches frames to disk; in-memory is enough for a
//! spike), then replays them in place at the GIF's own rate. The coder GIF
//! runs at 40 ms/frame — 25 FPS — which makes this a real pacing test.
//!
//!   animate [path.gif] [--height-px 150] [--fps N] [--max-frames N]
//!           [--opaque]   composite on black instead of transparent background
//!
//! Press q or Esc to stop; stats print on exit.

use crate::util::{cells, flag_u32, flag_val, load_gif_frames, parse_filter, positional, sprite_path, FrameStats};
use crate::{sixel, Cell};
use anyhow::Result;
use crossterm::event::{self, Event, KeyCode, KeyEventKind};
use crossterm::terminal;
use std::io::Write;
use std::time::{Duration, Instant};

pub fn run(cell: Cell, rest: &[String]) -> Result<()> {
    let path = positional(rest)
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|| sprite_path("coder-E-attacking.gif"));
    let height = flag_u32(rest, "--height-px", 150);
    let fps_override = flag_u32(rest, "--fps", 0);
    let max_frames = flag_u32(rest, "--max-frames", u32::MAX) as usize;
    let filter = parse_filter(&flag_val(rest, "--filter").unwrap_or_default());
    let opaque = rest.iter().any(|a| a == "--opaque");

    println!("decoding {} ...", path.display());
    let t0 = Instant::now();
    let (mut frames, delays) = load_gif_frames(&path, height, filter, max_frames)?;
    let decode_ms = t0.elapsed().as_secs_f64() * 1000.0;

    if opaque {
        for f in &mut frames {
            for px in f.pixels_mut() {
                if px.0[3] < 128 {
                    *px = image::Rgba([12, 24, 12, 255]);
                }
            }
        }
    }

    let t0 = Instant::now();
    let mut enc = sixel::Encoder::new();
    let mut encoded = Vec::with_capacity(frames.len());
    for f in &frames {
        encoded.push(enc.encode_rgba(f.as_raw(), f.width(), f.height())?);
    }
    let encode_ms = t0.elapsed().as_secs_f64() * 1000.0;
    let avg_bytes = encoded.iter().map(Vec::len).sum::<usize>() / encoded.len();
    let delay = if fps_override > 0 {
        Duration::from_millis(1000 / u64::from(fps_override))
    } else {
        Duration::from_millis(delays.first().copied().unwrap_or(40))
    };

    println!(
        "{} frames at {}x{} px; decode+resize {decode_ms:.0} ms, encode {encode_ms:.0} ms total \
         ({:.2} ms/frame), avg {avg_bytes} sixel bytes/frame, target {:.1} FPS",
        frames.len(),
        frames[0].width(),
        frames[0].height(),
        encode_ms / frames.len() as f64,
        1.0 / delay.as_secs_f64(),
    );
    println!("press q or Esc to stop");

    let rows = cells(height, cell.h);
    let mut out = std::io::BufWriter::new(std::io::stdout());
    for _ in 0..rows + 1 {
        writeln!(out)?;
    }
    write!(out, "\x1b[{}A\x1b[?25l", rows + 1)?;
    out.flush()?;
    terminal::enable_raw_mode()?;

    let mut stats = FrameStats::new();
    let mut write_stats = FrameStats::new();
    let mut i = 0usize;
    let run_result = (|| -> Result<()> {
        loop {
            let frame_start = Instant::now();
            write!(out, "\x1b7")?;
            out.write_all(&encoded[i])?;
            write!(out, "\x1b8")?;
            out.flush()?;
            write_stats.record(frame_start.elapsed());
            i = (i + 1) % encoded.len();

            loop {
                let left = delay.saturating_sub(frame_start.elapsed());
                if left.is_zero() {
                    break;
                }
                if event::poll(left)? {
                    if let Event::Key(k) = event::read()? {
                        if k.kind == KeyEventKind::Press
                            && matches!(k.code, KeyCode::Char('q') | KeyCode::Esc)
                        {
                            return Ok(());
                        }
                    }
                }
            }
            stats.record(frame_start.elapsed());
        }
    })();
    terminal::disable_raw_mode()?;
    write!(out, "\x1b[?25h\r\x1b[{}B", rows)?;
    writeln!(out)?;
    writeln!(
        out,
        "achieved {:.1} FPS over {} frames; write+flush avg {:.2} ms, p95 {:.2} ms",
        stats.achieved_fps(),
        stats.count(),
        write_stats.avg_ms(),
        write_stats.p95_ms()
    )?;
    out.flush()?;
    run_result
}
