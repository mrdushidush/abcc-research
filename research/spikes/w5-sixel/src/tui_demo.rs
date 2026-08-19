//! Question 4: does sixel compose with Ratatui? The 1995 C&C layout — viewport,
//! radar, sidebar, status strip — drawn as Ratatui widgets, with the viewport's
//! inner area painted by one sixel per tick: a battlefield JPEG backdrop with
//! sprites composited on top (a marching coder from the attacking GIF, a CTO
//! and a QA from the stills). Survives redraw because Ratatui's diff never
//! touches the untouched inner cells; survives resize because the backdrop is
//! re-scaled and re-emitted; runs in the alternate screen.
//!
//!   tui [--fps 10] [--sprite-px 150]
//!   keys: q quit · b cycle backdrop · r force full redraw

use crate::util::{battlefield_path, blit, flag_u32, load_gif_frames, load_rgba, sprite_path, FrameStats};
use crate::{sixel, Cell};
use anyhow::Result;
use crossterm::cursor::MoveTo;
use crossterm::event::{self, Event, KeyCode, KeyEventKind};
use crossterm::queue;
use image::imageops::FilterType;
use image::RgbaImage;
use ratatui::layout::{Constraint, Layout, Rect};
use ratatui::style::{Color, Style};
use ratatui::text::Line;
use ratatui::widgets::canvas::{Canvas, Line as CanvasLine, Points};
use ratatui::widgets::{Block, Paragraph};
use std::io::Write;
use std::time::{Duration, Instant};

pub fn run(cell: Cell, rest: &[String]) -> Result<()> {
    let fps = flag_u32(rest, "--fps", 10).max(1);
    let sprite_px = flag_u32(rest, "--sprite-px", 150);
    let tick = Duration::from_millis(1000 / u64::from(fps));

    eprintln!("loading assets...");
    let (coder_frames, _) = load_gif_frames(
        &sprite_path("coder-E-attacking.gif"),
        sprite_px,
        FilterType::Triangle,
        usize::MAX,
    )?;
    let cto = crate::util::resize_to_height(
        &load_rgba(&sprite_path("cto-E-idle.png"))?,
        sprite_px * 3 / 4,
        FilterType::Triangle,
    );
    let qa = crate::util::resize_to_height(
        &load_rgba(&sprite_path("qa-W-attacking.png"))?,
        sprite_px * 3 / 4,
        FilterType::Triangle,
    );
    let mut backdrop_n = 1u32;
    let mut backdrop_src = load_rgba(&battlefield_path(backdrop_n))?;

    let mut terminal = ratatui::init();
    let result = event_loop(
        &mut terminal, cell, tick, &coder_frames, &cto, &qa, &mut backdrop_n, &mut backdrop_src,
        sprite_px,
    );
    ratatui::restore();
    result
}

#[allow(clippy::too_many_arguments)]
fn event_loop(
    terminal: &mut ratatui::DefaultTerminal,
    cell: Cell,
    tick: Duration,
    coder_frames: &[RgbaImage],
    cto: &RgbaImage,
    qa: &RgbaImage,
    backdrop_n: &mut u32,
    backdrop_src: &mut RgbaImage,
    sprite_px: u32,
) -> Result<()> {
    let mut enc = sixel::Encoder::new();
    let mut scaled_backdrop: Option<RgbaImage> = None;
    let mut last_inner = Rect::default();
    let mut frame_i = 0usize;
    let mut coder_x = 0i64;
    let mut coder_dx = 3i64;
    let mut angle = 0f64;
    let mut fps_stats = FrameStats::new();
    let mut enc_ms = 0.0f64;
    let mut write_ms = 0.0f64;

    loop {
        let tick_start = Instant::now();
        let mut inner = Rect::default();
        let mut radar_blips: Vec<(f64, f64)> = Vec::new();
        let status = format!(
            " FPS {:.1} | encode {enc_ms:.1} ms | write {write_ms:.1} ms | viewport {}x{} px | q quit · b backdrop {} · r redraw ",
            fps_stats.achieved_fps(),
            u32::from(last_inner.width) * cell.w,
            u32::from(last_inner.height) * cell.h,
            backdrop_n,
        );

        terminal.draw(|f| {
            let cols = Layout::horizontal([Constraint::Min(30), Constraint::Length(26)])
                .split(f.area());
            let left = Layout::vertical([Constraint::Min(5), Constraint::Length(3)])
                .split(cols[0]);
            let side = Layout::vertical([Constraint::Length(13), Constraint::Min(0)])
                .split(cols[1]);

            let vp = Block::bordered()
                .title(Line::from(" BATTLEFIELD "))
                .border_style(Style::new().fg(Color::Yellow));
            inner = vp.inner(left[0]);
            f.render_widget(vp, left[0]);

            // Radar: circular sweep plus blips mirroring the sprite positions.
            radar_blips.push((-0.7, 0.3));
            radar_blips.push((0.5, -0.4));
            radar_blips.push((((coder_x % 200) as f64 / 100.0) - 1.0, 0.0));
            let radar = Canvas::default()
                .block(
                    Block::bordered()
                        .title(" RADAR ")
                        .border_style(Style::new().fg(Color::Yellow)),
                )
                .x_bounds([-1.2, 1.2])
                .y_bounds([-1.2, 1.2])
                .paint(|ctx| {
                    ctx.draw(&CanvasLine {
                        x1: 0.0,
                        y1: 0.0,
                        x2: angle.cos(),
                        y2: angle.sin(),
                        color: Color::Green,
                    });
                    ctx.draw(&Points { coords: &radar_blips, color: Color::LightGreen });
                });
            f.render_widget(radar, side[0]);

            let sidebar = Paragraph::new(vec![
                Line::from(" CREDITS: 2500"),
                Line::from(""),
                Line::styled(" > COMBAT CODER  $300", Style::new().fg(Color::White)),
                Line::from("   QA TURRET     $500"),
                Line::from("   CTO PALACE   $2000"),
                Line::from(""),
                Line::styled("  [ON HOLD]", Style::new().fg(Color::DarkGray)),
            ])
            .block(
                Block::bordered()
                    .title(" CONSTRUCTION ")
                    .border_style(Style::new().fg(Color::Yellow)),
            );
            f.render_widget(sidebar, side[1]);

            let strip = Paragraph::new(status.clone())
                .style(Style::new().fg(Color::Green))
                .block(Block::bordered().border_style(Style::new().fg(Color::Yellow)));
            f.render_widget(strip, left[1]);
        })?;

        // Sixel pass: composite backdrop + sprites at the viewport's pixel size.
        if inner.width > 0 && inner.height > 0 {
            let px_w = u32::from(inner.width) * cell.w;
            let px_h = u32::from(inner.height) * cell.h;
            if inner != last_inner || scaled_backdrop.is_none() {
                scaled_backdrop = Some(image::imageops::resize(
                    backdrop_src, px_w, px_h, FilterType::Triangle,
                ));
                last_inner = inner;
            }
            let base = scaled_backdrop.as_ref().unwrap();
            let mut composite = base.clone();
            let coder = &coder_frames[frame_i % coder_frames.len()];
            let ground = i64::from(px_h) * 55 / 100 - i64::from(sprite_px);
            blit(&mut composite, cto, i64::from(px_w) / 12, ground + 20);
            blit(&mut composite, qa, i64::from(px_w) * 7 / 10, ground + 40);
            blit(&mut composite, coder, coder_x, ground + 30);
            coder_x += coder_dx;
            if coder_x + i64::from(coder.width()) >= i64::from(px_w) || coder_x <= 0 {
                coder_dx = -coder_dx;
                coder_x = coder_x.clamp(0, i64::from(px_w.saturating_sub(coder.width())));
            }

            let t0 = Instant::now();
            let six = enc.encode_rgba(composite.as_raw(), px_w, px_h)?;
            enc_ms = t0.elapsed().as_secs_f64() * 1000.0;

            let t0 = Instant::now();
            let mut out = std::io::stdout().lock();
            queue!(out, MoveTo(inner.x, inner.y))?;
            out.write_all(&six)?;
            out.flush()?;
            write_ms = t0.elapsed().as_secs_f64() * 1000.0;
        }

        frame_i += 1;
        angle -= 0.35;

        // Pace to the tick, draining events as they come.
        loop {
            let left = tick.saturating_sub(tick_start.elapsed());
            if !event::poll(left)? {
                break;
            }
            match event::read()? {
                Event::Key(k) if k.kind == KeyEventKind::Press => match k.code {
                    KeyCode::Char('q') | KeyCode::Esc => return Ok(()),
                    KeyCode::Char('b') => {
                        *backdrop_n = *backdrop_n % 6 + 1;
                        *backdrop_src = load_rgba(&battlefield_path(*backdrop_n))?;
                        scaled_backdrop = None;
                    }
                    KeyCode::Char('r') => {
                        terminal.clear()?;
                        scaled_backdrop = None;
                    }
                    _ => {}
                },
                Event::Resize(_, _) => {
                    scaled_backdrop = None;
                }
                _ => {}
            }
        }
        fps_stats.record(tick_start.elapsed());
    }
}
