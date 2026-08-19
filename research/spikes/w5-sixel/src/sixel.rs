//! Sixel encoder, modeled on OpenAI Codex CLI's `codex-rs/tui/src/pets/sixel.rs`
//! (the reference implementation named in the W5 spike brief): RGB332 reduction
//! to a 256-colour palette, alpha threshold 128, transparent-background DCS,
//! sixel run-length encoding. Reimplemented with a precomputed index map and a
//! reusable per-band mask buffer so full-viewport composites encode in
//! milliseconds. Output is byte-identical to Codex's encoder (its test vectors
//! are ported below and pass verbatim).

use anyhow::{bail, Result};

const ST: &[u8] = b"\x1b\\";
const BAND_H: u32 = 6;
const TRANSPARENT_ALPHA_THRESHOLD: u8 = 128;
/// P2=1: pixels not written keep the terminal background (transparency).
const TRANSPARENT_BACKGROUND_DCS: &[u8] = b"\x1bP9;1;0q";
/// Sentinel in the index map for a transparent pixel.
const TRANSP: u16 = 256;

/// Reusable scratch buffers; keep one alive across frames when animating.
pub struct Encoder {
    idx: Vec<u16>,
    masks: Vec<u8>, // 256 rows of `width` column masks, reused per band
}

impl Encoder {
    pub fn new() -> Self {
        Self { idx: Vec::new(), masks: Vec::new() }
    }

    pub fn encode_rgba(&mut self, rgba: &[u8], width: u32, height: u32) -> Result<Vec<u8>> {
        if width == 0 || height == 0 {
            bail!("sixel image dimensions must be non-zero");
        }
        let n = (width as usize) * (height as usize);
        let expected = n * 4;
        if rgba.len() != expected {
            bail!("sixel RGBA buffer has {} bytes, expected {expected}", rgba.len());
        }
        let w = width as usize;

        self.idx.clear();
        self.idx.resize(n, TRANSP);
        let mut used = [false; 256];
        for (i, px) in rgba.chunks_exact(4).enumerate() {
            if px[3] < TRANSPARENT_ALPHA_THRESHOLD {
                continue;
            }
            let c = rgb332_index(px[0], px[1], px[2]);
            self.idx[i] = u16::from(c);
            used[usize::from(c)] = true;
        }

        let mut out = Vec::with_capacity(n / 2 + 256);
        out.extend_from_slice(TRANSPARENT_BACKGROUND_DCS);
        out.extend_from_slice(format!("\"1;1;{width};{height}").as_bytes());
        for c in 0..256usize {
            if used[c] {
                let (r, g, b) = rgb332_color(c as u8);
                out.extend_from_slice(
                    format!("#{c};2;{};{};{}", pct(r), pct(g), pct(b)).as_bytes(),
                );
            }
        }

        self.masks.clear();
        self.masks.resize(256 * w, 0);
        let mut active: Vec<u8> = Vec::with_capacity(64);
        let band_count = height.div_ceil(BAND_H);
        for band in 0..band_count {
            for &c in &active {
                let row = usize::from(c) * w;
                self.masks[row..row + w].fill(0);
            }
            active.clear();
            let mut seen = [false; 256];
            let top = band * BAND_H;
            for bit in 0..BAND_H {
                let y = top + bit;
                if y >= height {
                    break;
                }
                let base = (y as usize) * w;
                for x in 0..w {
                    let c = self.idx[base + x];
                    if c == TRANSP {
                        continue;
                    }
                    let c = c as u8;
                    if !seen[usize::from(c)] {
                        seen[usize::from(c)] = true;
                        active.push(c);
                    }
                    self.masks[usize::from(c) * w + x] |= 1 << bit;
                }
            }
            active.sort_unstable();
            for (pos, &c) in active.iter().enumerate() {
                out.extend_from_slice(format!("#{c}").as_bytes());
                let row = usize::from(c) * w;
                emit_rle(&mut out, &self.masks[row..row + w]);
                if pos + 1 < active.len() {
                    out.push(b'$');
                }
            }
            if band + 1 < band_count {
                if active.is_empty() {
                    out.push(b'-');
                } else {
                    out.extend_from_slice(b"$-");
                }
            }
        }
        out.extend_from_slice(ST);
        Ok(out)
    }
}

fn emit_rle(out: &mut Vec<u8>, masks: &[u8]) {
    let mut i = 0;
    while i < masks.len() {
        let byte = b'?' + masks[i];
        let mut run = 1;
        while i + run < masks.len() && masks[i + run] == masks[i] {
            run += 1;
        }
        if run > 3 {
            out.extend_from_slice(format!("!{run}").as_bytes());
            out.push(byte);
        } else {
            out.extend(std::iter::repeat(byte).take(run));
        }
        i += run;
    }
}

pub fn encode_rgba(rgba: &[u8], width: u32, height: u32) -> Result<Vec<u8>> {
    Encoder::new().encode_rgba(rgba, width, height)
}

pub fn encode_image(img: &image::RgbaImage) -> Result<Vec<u8>> {
    encode_rgba(img.as_raw(), img.width(), img.height())
}

fn rgb332_index(r: u8, g: u8, b: u8) -> u8 {
    ((r >> 5) << 5) | (((g >> 5) & 0b111) << 2) | (b >> 6)
}

fn rgb332_color(index: u8) -> (u8, u8, u8) {
    let r = index >> 5;
    let g = (index >> 2) & 0b111;
    let b = index & 0b11;
    (bucket(r, 7), bucket(g, 7), bucket(b, 3))
}

fn bucket(v: u8, max: u8) -> u8 {
    ((u16::from(v) * 255) / u16::from(max)) as u8
}

fn pct(v: u8) -> u8 {
    ((u16::from(v) * 100) / 255) as u8
}

// Test vectors ported from Codex's sixel.rs — output must match byte-for-byte.
#[cfg(test)]
mod tests {
    use super::*;

    const DCS: &str = "\x1bP9;1;0q";

    #[test]
    fn encodes_red_pixel_with_palette_and_pixel_data() {
        let sixel = encode_rgba(&[255, 0, 0, 255], 1, 1).unwrap();
        let sixel = String::from_utf8(sixel).unwrap();
        assert_eq!(sixel, format!("{DCS}\"1;1;1;1#224;2;100;0;0#224@\x1b\\"));
    }

    #[test]
    fn transparent_pixels_do_not_emit_palette_or_pixel_data() {
        let sixel = encode_rgba(&[255, 0, 0, 0], 1, 1).unwrap();
        let sixel = String::from_utf8(sixel).unwrap();
        assert_eq!(sixel, format!("{DCS}\"1;1;1;1\x1b\\"));
    }

    #[test]
    fn multi_band_images_advance_to_next_sixel_band() {
        let mut rgba = Vec::new();
        for _ in 0..7 {
            rgba.extend_from_slice(&[255, 0, 0, 255]);
        }
        let sixel = encode_rgba(&rgba, 1, 7).unwrap();
        let sixel = String::from_utf8(sixel).unwrap();
        assert_eq!(
            sixel,
            format!("{DCS}\"1;1;1;7#224;2;100;0;0#224~$-#224@\x1b\\")
        );
    }

    #[test]
    fn repeated_cells_use_sixel_run_length_encoding() {
        let mut rgba = Vec::new();
        for _ in 0..4 {
            rgba.extend_from_slice(&[255, 0, 0, 255]);
        }
        let sixel = encode_rgba(&rgba, 4, 1).unwrap();
        let sixel = String::from_utf8(sixel).unwrap();
        assert!(sixel.contains("#224!4@"), "got: {sixel}");
    }

    #[test]
    fn rejects_mismatched_rgba_buffer_length() {
        let err = encode_rgba(&[255, 0, 0], 1, 1).unwrap_err();
        assert_eq!(err.to_string(), "sixel RGBA buffer has 3 bytes, expected 4");
    }

    #[test]
    fn encoder_reuse_across_frames_is_clean() {
        let mut enc = Encoder::new();
        let red = enc.encode_rgba(&[255, 0, 0, 255], 1, 1).unwrap();
        // A second, different frame must not inherit state from the first.
        let blue = enc.encode_rgba(&[0, 0, 255, 255, 0, 0, 255, 255], 2, 1).unwrap();
        let again = enc.encode_rgba(&[255, 0, 0, 255], 1, 1).unwrap();
        assert_eq!(red, again);
        assert!(String::from_utf8(blue).unwrap().contains("#3"));
    }
}
