//! Question 5: the throughput ceiling — the sixel analogue of Phase 0's DOM
//! measurement ("free to ~100 entities"), which does not transfer and must be
//! re-established. Two phases, both uncapped (they measure the ceiling, not a
//! target):
//!
//!   A  "sprites":   N independent pre-encoded sprites per frame, N stepping
//!                   up until the grid is full. Measures Windows Terminal's
//!                   escape-stream ingest ceiling; encode cost is prepaid.
//!   B  "composite": one full-viewport sixel per frame (battlefield + N
//!                   sprites), encode and write measured separately. This is
//!                   the architecture the tui demo uses.
//!
//! The number that answers Q5: where achieved FPS crosses the C&C tick rate
//! (~12-15 FPS). Results print at the end and append to
//! w5-sixel-bench-results.txt in the working directory.
//!
//!   bench [--height-px 75] [--step-ms 2500]   (q aborts, partial results kept)

use crate::util::{battlefield_path, blit, cells, flag_u32, load_gif_frames, load_rgba, sprite_path, FrameStats};
use crate::{sixel, Cell};
use anyhow::Result;
use crossterm::event::{self, Event, KeyCode, KeyEventKind};
use crossterm::terminal::{self, EnterAlternateScreen, LeaveAlternateScreen};
use crossterm::{cursor, execute};
use image::imageops::FilterType;
use std::io::Write;
use std::time::{Duration, Instant};

struct Row {
    phase: &'static str,
    n: usize,
    frames: usize,
    fps: f64,
    avg_ms: f64,
    p95_ms: f64,
    enc_ms: f64,
    mb_s: f64,
}

pub fn run(cell: Cell, rest: &[String]) -> Result<()> {
    let height = flag_u32(rest, "--height-px", 75);
    let step = Duration::from_millis(u64::from(flag_u32(rest, "--step-ms", 2500)));

    println!("preparing: decoding sprite frames at {height}px and the battlefield ...");
    let (frames_rgba, _) = load_gif_frames(
        &sprite_path("coder-E-attacking.gif"),
        height,
        FilterType::Triangle,
        usize::MAX,
    )?;
    let mut enc = sixel::Encoder::new();
    let mut frames_six = Vec::with_capacity(frames_rgba.len());
    for f in &frames_rgba {
        frames_six.push(enc.encode_rgba(f.as_raw(), f.width(), f.height())?);
    }
    let sprite_w = frames_rgba[0].width();
    let backdrop_src = load_rgba(&battlefield_path(1))?;

    let mut out = std::io::stdout();
    execute!(out, EnterAlternateScreen, cursor::Hide)?;
    terminal::enable_raw_mode()?;
    let bench = bench_inner(
        cell, step, &frames_rgba, &frames_six, sprite_w, height, &backdrop_src, &mut enc,
    );
    terminal::disable_raw_mode()?;
    execute!(out, cursor::Show, LeaveAlternateScreen)?;
    let rows = bench?;

    let mut report = String::new();
    report.push_str(&format!(
        "w5-sixel bench — cell {}x{} px, sprite {}x{} px ({} frames, avg {} sixel bytes)\n",
        cell.w,
        cell.h,
        sprite_w,
        height,
        frames_six.len(),
        frames_six.iter().map(Vec::len).sum::<usize>() / frames_six.len(),
    ));
    report.push_str("| phase     |   N | frames |    FPS | avg ms | p95 ms | enc ms |  MB/s |\n");
    report.push_str("|-----------|-----|--------|--------|--------|--------|--------|-------|\n");
    for r in &rows {
        report.push_str(&format!(
            "| {:<9} | {:>3} | {:>6} | {:>6.1} | {:>6.2} | {:>6.2} | {:>6.2} | {:>5.1} |\n",
            r.phase, r.n, r.frames, r.fps, r.avg_ms, r.p95_ms, r.enc_ms, r.mb_s
        ));
    }
    println!("\n{report}");
    println!("Q5 readout: the ceiling is the largest N whose FPS still clears ~12-15.");
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open("w5-sixel-bench-results.txt")
    {
        let _ = writeln!(f, "{report}");
        println!("(appended to w5-sixel-bench-results.txt)");
    }
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn bench_inner(
    cell: Cell,
    step: Duration,
    frames_rgba: &[image::RgbaImage],
    frames_six: &[Vec<u8>],
    sprite_w: u32,
    sprite_h: u32,
    backdrop_src: &image::RgbaImage,
    enc: &mut sixel::Encoder,
) -> Result<Vec<Row>> {
    let (cols, rows) = terminal::size()?;
    let mut results = Vec::new();
    let mut out = std::io::stdout();

    // ---- phase A: N independent sprites, pre-encoded ----
    let cols_per = cells(sprite_w, cell.w) + 1;
    let rows_per = cells(sprite_h, cell.h) + 1;
    let per_row = (cols / cols_per).max(1);
    let grid_rows = (rows.saturating_sub(2) / rows_per).max(1);
    let capacity = usize::from(per_row) * usize::from(grid_rows);

    'outer: for &n in &[1usize, 2, 4, 8, 16, 32, 48, 64] {
        if n > capacity {
            break;
        }
        execute!(out, terminal::Clear(terminal::ClearType::All), cursor::MoveTo(0, 0))?;
        write!(out, "phase A: {n} sprites (capacity {capacity}) — q aborts")?;
        out.flush()?;
        let mut stats = FrameStats::new();
        let mut buf: Vec<u8> = Vec::with_capacity(n * 64 * 1024);
        let mut bytes_total = 0usize;
        let mut tick = 0usize;
        let t_end = Instant::now() + step;
        while Instant::now() < t_end {
            let t0 = Instant::now();
            buf.clear();
            for i in 0..n {
                let col = (i % usize::from(per_row)) as u16 * cols_per;
                let row = 1 + (i / usize::from(per_row)) as u16 * rows_per;
                buf.extend_from_slice(format!("\x1b[{};{}H", row + 1, col + 1).as_bytes());
                buf.extend_from_slice(&frames_six[(tick + i * 7) % frames_six.len()]);
            }
            out.write_all(&buf)?;
            out.flush()?;
            bytes_total += buf.len();
            stats.record(t0.elapsed());
            tick += 1;
            if tick % 8 == 0 && aborted()? {
                break 'outer;
            }
        }
        results.push(Row {
            phase: "sprites",
            n,
            frames: stats.count(),
            fps: stats.achieved_fps(),
            avg_ms: stats.avg_ms(),
            p95_ms: stats.p95_ms(),
            enc_ms: 0.0,
            mb_s: bytes_total as f64 / 1e6 / step.as_secs_f64(),
        });
    }

    // ---- phase B: one full-viewport composite per frame ----
    let px_w = u32::from(cols) * cell.w;
    let px_h = u32::from(rows.saturating_sub(2)) * cell.h;
    let base = image::imageops::resize(backdrop_src, px_w, px_h, FilterType::Triangle);
    for &n in &[0usize, 4, 8, 16] {
        execute!(out, terminal::Clear(terminal::ClearType::All), cursor::MoveTo(0, 0))?;
        write!(out, "phase B: composite {px_w}x{px_h} px + {n} sprites — q aborts")?;
        out.flush()?;
        let mut stats = FrameStats::new();
        let mut enc_stats = FrameStats::new();
        let mut bytes_total = 0usize;
        let mut tick = 0usize;
        let t_end = Instant::now() + step;
        while Instant::now() < t_end {
            let t0 = Instant::now();
            let mut composite = base.clone();
            for i in 0..n {
                let f = &frames_rgba[(tick + i * 7) % frames_rgba.len()];
                let x = (i % 6) as i64 * i64::from(px_w) / 6 + (tick as i64 * 2 % 40);
                let y = (i / 6) as i64 * i64::from(sprite_h + 10) + 10;
                blit(&mut composite, f, x, y);
            }
            let te = Instant::now();
            let six = enc.encode_rgba(composite.as_raw(), px_w, px_h)?;
            enc_stats.record(te.elapsed());
            write!(out, "\x1b[2;1H")?;
            out.write_all(&six)?;
            out.flush()?;
            bytes_total += six.len();
            stats.record(t0.elapsed());
            tick += 1;
            if tick % 4 == 0 && aborted()? {
                break;
            }
        }
        results.push(Row {
            phase: "composite",
            n,
            frames: stats.count(),
            fps: stats.achieved_fps(),
            avg_ms: stats.avg_ms(),
            p95_ms: stats.p95_ms(),
            enc_ms: enc_stats.avg_ms(),
            mb_s: bytes_total as f64 / 1e6 / step.as_secs_f64(),
        });
    }
    Ok(results)
}

/// Headless encode-cost measurement + a PNG preview of the composite frame.
/// Needs no terminal at all — this is the part of Q5 that can run in CI.
///
///   encbench [--px 1200x600] [--sprites 8] [--height-px 150] [--iters 50]
pub fn encbench(cell: Cell, rest: &[String]) -> Result<()> {
    let px = crate::util::flag_val(rest, "--px").unwrap_or_else(|| "1200x600".into());
    let (px_w, px_h) = px
        .split_once('x')
        .map(|(w, h)| (w.parse().unwrap_or(1200), h.parse().unwrap_or(600)))
        .unwrap_or((1200, 600));
    let n = flag_u32(rest, "--sprites", 8) as usize;
    let height = flag_u32(rest, "--height-px", 150);
    let iters = flag_u32(rest, "--iters", 50) as usize;

    let (frames_rgba, _) = load_gif_frames(
        &sprite_path("coder-E-attacking.gif"),
        height,
        FilterType::Triangle,
        usize::MAX,
    )?;
    let cto = crate::util::resize_to_height(
        &load_rgba(&sprite_path("cto-E-idle.png"))?,
        height,
        FilterType::Triangle,
    );
    let base = image::imageops::resize(
        &load_rgba(&battlefield_path(1))?,
        px_w,
        px_h,
        FilterType::Triangle,
    );

    let mut enc = sixel::Encoder::new();
    let mut compose_stats = FrameStats::new();
    let mut enc_stats = FrameStats::new();
    let mut bytes = 0usize;
    let mut preview_saved = false;
    for tick in 0..iters {
        let t0 = Instant::now();
        let mut composite = base.clone();
        blit(&mut composite, &cto, i64::from(px_w) / 10, i64::from(px_h) / 3);
        for i in 0..n {
            let f = &frames_rgba[(tick + i * 7) % frames_rgba.len()];
            let x = (i % 6) as i64 * i64::from(px_w) / 6 + (tick as i64 * 3 % 60);
            let y = i64::from(px_h) / 4 + (i / 6) as i64 * i64::from(height + 16);
            blit(&mut composite, f, x, y);
        }
        compose_stats.record(t0.elapsed());
        let t0 = Instant::now();
        let six = enc.encode_rgba(composite.as_raw(), px_w, px_h)?;
        enc_stats.record(t0.elapsed());
        bytes += six.len();
        if !preview_saved {
            composite.save("composite_preview.png")?;
            preview_saved = true;
        }
    }
    println!(
        "encbench {px_w}x{px_h} px + {n} sprites, {iters} iters (cell {}x{} -> {}x{} cells):",
        cell.w,
        cell.h,
        px_w.div_ceil(cell.w),
        px_h.div_ceil(cell.h)
    );
    println!(
        "  compose (clone+blit): avg {:.2} ms, p95 {:.2} ms",
        compose_stats.avg_ms(),
        compose_stats.p95_ms()
    );
    println!(
        "  encode:               avg {:.2} ms, p95 {:.2} ms",
        enc_stats.avg_ms(),
        enc_stats.p95_ms()
    );
    println!(
        "  avg sixel bytes/frame: {} ({:.2} MB/s at 15 FPS)",
        bytes / iters,
        (bytes / iters) as f64 * 15.0 / 1e6
    );
    println!("  first frame saved to composite_preview.png");
    Ok(())
}

fn aborted() -> Result<bool> {
    while event::poll(Duration::ZERO)? {
        if let Event::Key(k) = event::read()? {
            if k.kind == KeyEventKind::Press && matches!(k.code, KeyCode::Char('q') | KeyCode::Esc) {
                return Ok(true);
            }
        }
    }
    Ok(false)
}
