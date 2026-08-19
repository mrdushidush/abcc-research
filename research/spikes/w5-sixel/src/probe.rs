//! Question 0: what does the terminal itself report? Sends DA1 (`ESC [ c`) and
//! XTWINOPS 14t/16t, reads the responses with a timeout, and prints both the
//! raw bytes and the parsed conclusion. This is the query `ratatui-image`
//! panics on under Windows (issue #69) — done here with a reader thread and a
//! deadline instead, so the worst case is "no response", never a panic.

use anyhow::Result;
use crossterm::terminal;
use std::io::{Read, Write};
use std::sync::mpsc;
use std::time::{Duration, Instant};

pub fn run() -> Result<()> {
    println!("-- environment --");
    for var in ["WT_SESSION", "TERM", "TERM_PROGRAM", "TMUX", "ZELLIJ"] {
        println!("  {var} = {:?}", std::env::var(var).ok());
    }
    if std::env::var("TMUX").is_ok() || std::env::var("ZELLIJ").is_ok() {
        println!("  !! multiplexer detected — sixel will NOT pass through. Run outside it.");
    }
    let (cols, rows) = terminal::size()?;
    println!("  terminal size: {cols} cols x {rows} rows");

    // Reader thread: raw mode makes query responses arrive on stdin.
    let (tx, rx) = mpsc::channel::<u8>();
    std::thread::spawn(move || {
        let mut stdin = std::io::stdin();
        let mut buf = [0u8; 256];
        loop {
            match stdin.read(&mut buf) {
                Ok(0) | Err(_) => break,
                Ok(n) => {
                    for &b in &buf[..n] {
                        if tx.send(b).is_err() {
                            return;
                        }
                    }
                }
            }
        }
    });

    terminal::enable_raw_mode()?;
    let mut out = std::io::stdout();
    // DA1 (device attributes), XTWINOPS 16t (cell size px), 14t (text area px).
    out.write_all(b"\x1b[c\x1b[16t\x1b[14t")?;
    out.flush()?;

    let mut bytes = Vec::new();
    let deadline = Instant::now() + Duration::from_millis(1200);
    let mut last_byte = Instant::now();
    loop {
        let now = Instant::now();
        if now >= deadline || (!bytes.is_empty() && now - last_byte > Duration::from_millis(300)) {
            break;
        }
        match rx.recv_timeout(Duration::from_millis(50)) {
            Ok(b) => {
                bytes.push(b);
                last_byte = Instant::now();
            }
            Err(mpsc::RecvTimeoutError::Timeout) => continue,
            Err(_) => break,
        }
    }
    terminal::disable_raw_mode()?;

    println!("\n-- raw response ({} bytes) --", bytes.len());
    println!("  {}", printable(&bytes));

    println!("\n-- parsed --");
    let text = String::from_utf8_lossy(&bytes).to_string();
    match parse_da1(&text) {
        Some(attrs) => {
            let sixel = attrs.iter().any(|a| *a == 4);
            println!("  DA1 attributes: {attrs:?}");
            println!(
                "  sixel (attr 4): {}",
                if sixel { "YES — the terminal advertises sixel" } else { "NO — attr 4 absent" }
            );
        }
        None => println!("  DA1: no response (terminal may not answer, or output was swallowed)"),
    }
    match parse_winops(&text, 6) {
        Some((h, w)) => println!("  cell size (CSI 16t): {w}x{h} px  -> pass `--cell {w}x{h}`"),
        None => println!("  cell size (CSI 16t): no response — use the default --cell 10x20 and eyeball it"),
    }
    match parse_winops(&text, 4) {
        Some((h, w)) => {
            println!("  text area (CSI 14t): {w}x{h} px");
            if cols > 0 && rows > 0 {
                println!("  derived cell: {}x{} px", w / u32::from(cols), h / u32::from(rows));
            }
        }
        None => println!("  text area (CSI 14t): no response"),
    }
    Ok(())
}

fn printable(bytes: &[u8]) -> String {
    let mut s = String::new();
    for &b in bytes {
        match b {
            0x1b => s.push_str("\\e"),
            0x20..=0x7e => s.push(b as char),
            _ => s.push_str(&format!("\\x{b:02x}")),
        }
    }
    s
}

/// DA1 response: ESC [ ? a;b;c... c
fn parse_da1(text: &str) -> Option<Vec<u32>> {
    let start = text.find("\x1b[?")?;
    let body = &text[start + 3..];
    let end = body.find('c')?;
    Some(body[..end].split(';').filter_map(|p| p.parse().ok()).collect())
}

/// XTWINOPS response: ESC [ kind;height;width t  -> (height, width)
fn parse_winops(text: &str, kind: u32) -> Option<(u32, u32)> {
    let needle = format!("\x1b[{kind};");
    let start = text.find(&needle)?;
    let body = &text[start + needle.len()..];
    let end = body.find('t')?;
    let mut parts = body[..end].split(';').filter_map(|p| p.parse::<u32>().ok());
    Some((parts.next()?, parts.next()?))
}
