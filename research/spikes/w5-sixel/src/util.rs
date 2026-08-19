//! Shared helpers: asset paths, loading, resizing, GIF decode, args, timing.

use anyhow::{Context, Result};
use image::imageops::FilterType;
use image::{AnimationDecoder, RgbaImage};
use std::io::BufReader;
use std::path::PathBuf;
use std::time::Instant;

/// The real V1 assets, measured 2026-08-18 (44 MB total).
pub const ASSET_BASE: &str = r"D:\dev\agent-battle-command-center\packages\ui\public";

pub fn sprite_path(name: &str) -> PathBuf {
    PathBuf::from(ASSET_BASE).join("sprites").join(name)
}

pub fn battlefield_path(n: u32) -> PathBuf {
    let file = if n <= 1 {
        "battlefield.jpg".to_string()
    } else {
        format!("battlefield{n}.jpg")
    };
    PathBuf::from(ASSET_BASE).join("assets").join("background").join(file)
}

pub fn load_rgba(path: &std::path::Path) -> Result<RgbaImage> {
    Ok(image::open(path)
        .with_context(|| format!("loading {}", path.display()))?
        .to_rgba8())
}

pub fn parse_filter(name: &str) -> FilterType {
    match name {
        "nearest" => FilterType::Nearest,
        "catmullrom" => FilterType::CatmullRom,
        "lanczos" => FilterType::Lanczos3,
        _ => FilterType::Triangle,
    }
}

/// Resize preserving aspect ratio to a target pixel height.
pub fn resize_to_height(img: &RgbaImage, target_h: u32, filter: FilterType) -> RgbaImage {
    let w = (u64::from(img.width()) * u64::from(target_h) / u64::from(img.height())).max(1) as u32;
    image::imageops::resize(img, w, target_h, filter)
}

/// Decode a GIF, resize every frame to `target_h`, return frames + delays (ms).
pub fn load_gif_frames(
    path: &std::path::Path,
    target_h: u32,
    filter: FilterType,
    max_frames: usize,
) -> Result<(Vec<RgbaImage>, Vec<u64>)> {
    let file = std::fs::File::open(path).with_context(|| format!("opening {}", path.display()))?;
    let decoder = image::codecs::gif::GifDecoder::new(BufReader::new(file))?;
    let mut frames = Vec::new();
    let mut delays = Vec::new();
    for frame in decoder.into_frames() {
        let frame = frame?;
        let (num, den) = frame.delay().numer_denom_ms();
        let ms = if den == 0 { 40 } else { u64::from(num / den.max(1)) };
        delays.push(if ms == 0 { 40 } else { ms });
        frames.push(resize_to_height(&frame.into_buffer(), target_h, filter));
        if frames.len() >= max_frames {
            break;
        }
    }
    anyhow::ensure!(!frames.is_empty(), "GIF had no frames: {}", path.display());
    Ok((frames, delays))
}

/// Blit `src` onto `dst` at (x, y) with true source-over alpha blending,
/// clipping at the edges. The ABCC sprites carry feathered alpha over a third
/// of their body (measured on cto-E-idle: 5062 of ~15k pixels semi-transparent),
/// so hard thresholding punches holes; blending onto the opaque battlefield is
/// what the real console does and costs nothing extra here.
pub fn blit(dst: &mut RgbaImage, src: &RgbaImage, x: i64, y: i64) {
    let (dw, dh) = (dst.width() as i64, dst.height() as i64);
    for (sx, sy, px) in src.enumerate_pixels() {
        let a = u32::from(px.0[3]);
        if a == 0 {
            continue;
        }
        let (tx, ty) = (x + i64::from(sx), y + i64::from(sy));
        if tx < 0 || ty < 0 || tx >= dw || ty >= dh {
            continue;
        }
        if a == 255 {
            dst.put_pixel(tx as u32, ty as u32, *px);
        } else {
            let under = dst.get_pixel(tx as u32, ty as u32).0;
            let blend = |s: u8, d: u8| ((u32::from(s) * a + u32::from(d) * (255 - a)) / 255) as u8;
            dst.put_pixel(
                tx as u32,
                ty as u32,
                image::Rgba([
                    blend(px.0[0], under[0]),
                    blend(px.0[1], under[1]),
                    blend(px.0[2], under[2]),
                    255,
                ]),
            );
        }
    }
}

/// How many terminal rows / columns a pixel extent occupies at a cell size.
pub fn cells(px: u32, cell_px: u32) -> u16 {
    px.div_ceil(cell_px.max(1)) as u16
}

// ---- tiny arg helpers (spike-grade, no clap) ----

pub fn flag_val(rest: &[String], flag: &str) -> Option<String> {
    rest.iter()
        .position(|a| a == flag)
        .and_then(|i| rest.get(i + 1).cloned())
}

pub fn flag_u32(rest: &[String], flag: &str, default: u32) -> u32 {
    flag_val(rest, flag).and_then(|v| v.parse().ok()).unwrap_or(default)
}

pub fn positional(rest: &[String]) -> Option<String> {
    let mut skip = false;
    for a in rest {
        if skip {
            skip = false;
            continue;
        }
        if a.starts_with("--") {
            skip = true;
            continue;
        }
        return Some(a.clone());
    }
    None
}

// ---- frame timing ----

pub struct FrameStats {
    times_ms: Vec<f64>,
    started: Instant,
}

impl FrameStats {
    pub fn new() -> Self {
        Self { times_ms: Vec::new(), started: Instant::now() }
    }

    pub fn record(&mut self, dur: std::time::Duration) {
        self.times_ms.push(dur.as_secs_f64() * 1000.0);
    }

    pub fn count(&self) -> usize {
        self.times_ms.len()
    }

    pub fn achieved_fps(&self) -> f64 {
        let secs = self.started.elapsed().as_secs_f64();
        if secs > 0.0 { self.times_ms.len() as f64 / secs } else { 0.0 }
    }

    pub fn avg_ms(&self) -> f64 {
        if self.times_ms.is_empty() {
            return 0.0;
        }
        self.times_ms.iter().sum::<f64>() / self.times_ms.len() as f64
    }

    pub fn p95_ms(&self) -> f64 {
        if self.times_ms.is_empty() {
            return 0.0;
        }
        let mut sorted = self.times_ms.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
        sorted[(sorted.len() * 95 / 100).min(sorted.len() - 1)]
    }
}
