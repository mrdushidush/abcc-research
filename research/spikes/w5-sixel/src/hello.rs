//! Question 1: does a sixel render at all? Emits a programmatic test pattern —
//! no image files involved, so a failure here is the terminal, not the assets.

use crate::sixel;
use crate::util::cells;
use crate::Cell;
use anyhow::Result;
use std::io::Write;

const W: u32 = 240;
const H: u32 = 96;

pub fn run(cell: Cell) -> Result<()> {
    let mut rgba = vec![0u8; (W * H * 4) as usize];
    for y in 0..H {
        for x in 0..W {
            let i = ((y * W + x) * 4) as usize;
            let (r, g, b, a) = if x < W / 2 {
                // Left half: hue sweep left-to-right, darkening top-to-bottom.
                let hue = x as f32 / (W / 2) as f32 * 360.0;
                let v = 1.0 - 0.6 * (y as f32 / H as f32);
                let (r, g, b) = hsv(hue, 1.0, v);
                (r, g, b, 255)
            } else {
                // Right half: checkerboard, odd squares fully transparent.
                let sq = (x / 12 + y / 12) % 2 == 0;
                if sq {
                    (57, 255, 20, 255) // C&C green
                } else {
                    (0, 0, 0, 0)
                }
            };
            rgba[i] = r;
            rgba[i + 1] = g;
            rgba[i + 2] = b;
            rgba[i + 3] = a;
        }
    }
    // Border so partial rendering is obvious.
    for x in 0..W {
        for y in [0, 1, H - 2, H - 1] {
            set(&mut rgba, x, y, (255, 255, 0, 255));
        }
    }
    for y in 0..H {
        for x in [0, 1, W - 2, W - 1] {
            set(&mut rgba, x, y, (255, 255, 0, 255));
        }
    }

    let six = sixel::encode_rgba(&rgba, W, H)?;
    let rows = cells(H, cell.h);

    let mut out = std::io::stdout();
    writeln!(out, "SIXEL TEST — {W}x{H} px ({} bytes encoded). Expected below:", six.len())?;
    writeln!(out, "a yellow-bordered box; left half a colour gradient, right half a green")?;
    writeln!(out, "checkerboard whose alternate squares show the terminal background through.")?;
    writeln!(out)?;
    // Reserve rows so emission never scrolls mid-image, then climb back up.
    for _ in 0..rows + 1 {
        writeln!(out)?;
    }
    write!(out, "\x1b[{}A", rows + 1)?;
    out.write_all(&six)?;
    // Reposition explicitly below the image; don't trust post-sixel cursor.
    write!(out, "\r\x1b[{}B", rows)?;
    writeln!(out)?;
    writeln!(out, "If you see raw '?@~' garbage or nothing: sixel did not render.")?;
    out.flush()?;
    Ok(())
}

fn set(rgba: &mut [u8], x: u32, y: u32, (r, g, b, a): (u8, u8, u8, u8)) {
    let i = ((y * W + x) * 4) as usize;
    rgba[i] = r;
    rgba[i + 1] = g;
    rgba[i + 2] = b;
    rgba[i + 3] = a;
}

fn hsv(h: f32, s: f32, v: f32) -> (u8, u8, u8) {
    let c = v * s;
    let hp = h / 60.0;
    let x = c * (1.0 - (hp % 2.0 - 1.0).abs());
    let (r, g, b) = match hp as u32 {
        0 => (c, x, 0.0),
        1 => (x, c, 0.0),
        2 => (0.0, c, x),
        3 => (0.0, x, c),
        4 => (x, 0.0, c),
        _ => (c, 0.0, x),
    };
    let m = v - c;
    (
        ((r + m) * 255.0) as u8,
        ((g + m) * 255.0) as u8,
        ((b + m) * 255.0) as u8,
    )
}
