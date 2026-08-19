//! Question 2: does an ABCC sprite look good at terminal scale? Renders one
//! sprite at several heights side by side. This one is David's judgement call —
//! the spike only puts the pixels in front of him.
//!
//!   sprite [path] [--sizes 50,75,120,180] [--filter triangle|nearest|catmullrom|lanczos]
//!
//! V1 drew agents at 280 px; Codex draws pets at 75 px. The default sizes
//! bracket that range.

use crate::util::{cells, flag_val, load_rgba, parse_filter, positional, resize_to_height, sprite_path};
use crate::{sixel, Cell};
use anyhow::Result;
use std::io::Write;
use std::time::Instant;

pub fn run(cell: Cell, rest: &[String]) -> Result<()> {
    let path = positional(rest)
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|| sprite_path("cto-E-idle.png"));
    let sizes: Vec<u32> = flag_val(rest, "--sizes")
        .unwrap_or_else(|| "50,75,120,180".into())
        .split(',')
        .filter_map(|s| s.trim().parse().ok())
        .collect();
    let filter = parse_filter(&flag_val(rest, "--filter").unwrap_or_default());
    // The encoder drops alpha < 128, and these sprites carry feathered alpha
    // over much of the body — a lower cutoff promotes those pixels to opaque
    // instead of punching holes. Try --alpha-cutoff 32 against the default.
    let cutoff = crate::util::flag_u32(rest, "--alpha-cutoff", 128).min(255) as u8;

    let mut img = load_rgba(&path)?;
    if cutoff < 128 {
        for px in img.pixels_mut() {
            if px.0[3] >= cutoff {
                px.0[3] = 255;
            }
        }
    }
    println!(
        "{} — {}x{} px source, filter {:?}, cell {}x{}",
        path.display(),
        img.width(),
        img.height(),
        filter,
        cell.w,
        cell.h
    );

    let mut renders = Vec::new();
    for &h in &sizes {
        let t0 = Instant::now();
        let scaled = resize_to_height(&img, h, filter);
        let six = sixel::encode_image(&scaled)?;
        renders.push((h, scaled.width(), six, t0.elapsed()));
    }

    let max_h = sizes.iter().copied().max().unwrap_or(75);
    let rows = cells(max_h, cell.h);

    let mut out = std::io::stdout();
    // Label line at each sprite's column offset.
    let mut col: u16 = 1; // CHA is 1-based
    let mut offsets = Vec::new();
    for (h, w, _, _) in &renders {
        offsets.push(col);
        write!(out, "\x1b[{col}G{h}px")?;
        col += cells(*w, cell.w) + 2;
    }
    writeln!(out)?;
    // Reserve the vertical space, climb back, draw each at its column.
    for _ in 0..rows + 1 {
        writeln!(out)?;
    }
    write!(out, "\x1b[{}A", rows + 1)?;
    for ((_, _, six, _), col) in renders.iter().zip(&offsets) {
        write!(out, "\x1b7\x1b[{col}G")?;
        out.write_all(six)?;
        write!(out, "\x1b8")?;
    }
    write!(out, "\r\x1b[{}B", rows)?;
    writeln!(out)?;
    for (h, w, six, took) in &renders {
        writeln!(
            out,
            "  {h:>3}px: {w}x{h}, {} sixel bytes, resize+encode {:.1} ms",
            six.len(),
            took.as_secs_f64() * 1000.0
        )?;
    }
    out.flush()?;
    Ok(())
}
