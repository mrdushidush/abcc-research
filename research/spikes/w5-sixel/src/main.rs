//! W5 sixel spike — THROWAWAY (Phase 1, §15). Can Ratatui render ABCC's
//! sprites in Windows Terminal? Six subcommands map onto the five questions
//! in the spike brief (`probe` is question 0: what does the terminal report).
//!
//! Run each of these in a real Windows Terminal tab — NOT inside tmux/Zellij,
//! which strip sixel:
//!
//!   w5-sixel-spike probe                # what the terminal claims: DA1, cell size
//!   w5-sixel-spike hello                # Q1: does any sixel render at all
//!   w5-sixel-spike sprite [path]        # Q2: an ABCC sprite at several scales
//!   w5-sixel-spike animate [path.gif]   # Q3: frame animation in place
//!   w5-sixel-spike tui                  # Q4: sixel inside a Ratatui C&C layout
//!   w5-sixel-spike bench                # Q5: throughput ceiling
//!
//! Global flag: --cell WxH  (terminal cell size in px; default 10x20 — run
//! `probe` first and pass what it reports).

mod animate;
mod bench;
mod hello;
mod probe;
mod sixel;
mod sprite;
mod tui_demo;
mod util;

use anyhow::Result;

#[derive(Clone, Copy)]
pub struct Cell {
    pub w: u32,
    pub h: u32,
}

fn main() -> Result<()> {
    let mut args: Vec<String> = std::env::args().skip(1).collect();
    let mut cell = Cell { w: 10, h: 20 };
    if let Some(i) = args.iter().position(|a| a == "--cell") {
        if let Some(v) = args.get(i + 1) {
            if let Some((w, h)) = v.split_once('x') {
                cell = Cell {
                    w: w.parse().unwrap_or(10),
                    h: h.parse().unwrap_or(20),
                };
            }
        }
        args.drain(i..(i + 2).min(args.len()));
    }
    let cmd = args.first().cloned().unwrap_or_else(|| "help".into());
    let rest: Vec<String> = args.iter().skip(1).cloned().collect();

    match cmd.as_str() {
        "probe" => probe::run(),
        "hello" => hello::run(cell),
        "sprite" => sprite::run(cell, &rest),
        "animate" => animate::run(cell, &rest),
        "tui" => tui_demo::run(cell, &rest),
        "bench" => bench::run(cell, &rest),
        "encbench" => bench::encbench(cell, &rest),
        _ => {
            eprintln!("usage: w5-sixel-spike [--cell WxH] <probe|hello|sprite|animate|tui|bench> [args]");
            eprintln!("run in Windows Terminal directly; tmux/Zellij strip sixel.");
            Ok(())
        }
    }
}
