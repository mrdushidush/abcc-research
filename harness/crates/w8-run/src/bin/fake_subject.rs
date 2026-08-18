//! A subject that speaks Claudette's pipe protocol and has no model behind it.
//!
//! This is the driver's **positive control**, and the reason it exists is the same lesson the all-90
//! gate sweep produced (F18-F21): when every case is expected to fail, "they all failed" is not a
//! result. A driver test suite that asserts "no gate was observed" or "the turn did not complete"
//! would pass just as calmly against a driver that never spawned anything. A subject that *does*
//! fire a gate, *does* print a turn boundary, and *does* record what it was answered turns those
//! assertions into evidence.
//!
//! Everything it emits is copied from the real thing:
//!
//! - the three banner lines, the third carrying `session: ` (`repl.rs:71-85`), which is how the
//!   driver knows the first `read_line` has been reached;
//! - the gate preview shape — blank line, `  ⚠ <tool> wants to run (<n> chars):`, four-space
//!   indented input, then `  Allow? [y/N · or type a redirect] ` **with no trailing newline**
//!   (`cli_prompter.rs:52-85`);
//! - the turn-end line on stderr, with **session-cumulative** `in=`/`out=` (F9), because a harness
//!   that accumulated them would look correct against a per-turn fake;
//! - `exit` / EOF ending the loop (`repl.rs:115-131`);
//! - the **sentinel-delimited block** that makes a multi-line prompt one turn
//!   (`line_editor.rs`, added 2026-08-08). Without it here, a driver test for block delivery would
//!   be asserting against a fake that treats each line as its own turn — i.e. it would pass for a
//!   driver that had not implemented blocks at all.
//!
//! Knobs, all via the environment so a test can compose them:
//!   `FAKE_GATES`      gates to fire per turn (default 0)
//!   `FAKE_TOOL`       tool name in the preview (default `apply_diff`)
//!   `FAKE_PREVIEW`    preview body; `|` separates lines (default a two-line diff)
//!   `FAKE_IN`         per-turn input tokens added to the running total (default 4900)
//!   `FAKE_OUT`        per-turn output tokens added (default 60)
//!   `FAKE_ITER`       `iter=` to report (default 1)
//!   `FAKE_LOG`        append every line read from stdin here, prefixed by kind
//!   `FAKE_NO_BANNER`  print no banner at all — the driver must refuse to measure
//!   `FAKE_HANG`       accept the turn and never print a turn boundary
//!   `FAKE_MUTE`       print no reply at all — a subject working with its mouth shut (F91)
//!   `FAKE_TAIL`       write this to stdout with NO trailing newline, then carry on
//!   `FAKE_STALL_MS`   sleep this long before the turn boundary
//!   `FAKE_DIE`        exit immediately after reading the turn

use std::io::{BufRead, Write};

/// The pair the real subject declares, and the corpus descriptor carries.
const BLOCK_OPEN: &str = "<<<CLAUDETTE-PROMPT";
const BLOCK_CLOSE: &str = "CLAUDETTE-PROMPT>>>";

fn env(k: &str) -> Option<String> {
    std::env::var(k).ok().filter(|v| !v.is_empty())
}

fn num(k: &str, default: u64) -> u64 {
    env(k).and_then(|v| v.parse().ok()).unwrap_or(default)
}

fn log(kind: &str, text: &str) {
    if let Some(p) = env("FAKE_LOG") {
        if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(p) {
            let _ = writeln!(f, "{kind}\t{text}");
        }
    }
}

fn main() {
    let mut err = std::io::stderr();
    let mut out = std::io::stdout();

    if env("FAKE_NO_BANNER").is_none() {
        let _ = writeln!(err, "🤖 claudette — your local coding agent");
        let _ = writeln!(err, "✨ type /help for commands, /exit (or Ctrl-D) to leave");
        let _ = writeln!(err, "💾 session: C:\\Users\\fake\\.claudette\\sessions\\default.json");
        let _ = writeln!(err);
        let _ = err.flush();
    }

    let gates = num("FAKE_GATES", 0);
    let tool = env("FAKE_TOOL").unwrap_or_else(|| "apply_diff".to_string());
    let preview = env("FAKE_PREVIEW").unwrap_or_else(|| "-     return a + b|+     return a - b".into());
    let per_in = num("FAKE_IN", 4900);
    let per_out = num("FAKE_OUT", 60);
    let iter = num("FAKE_ITER", 1);

    // Session-cumulative, exactly like `UsageTracker::record` (`usage.rs:44-50`), which only ever
    // `+=` and is seeded from the restored session.
    let mut total_in = 0u64;
    let mut total_out = 0u64;

    let stdin = std::io::stdin();
    let mut lines = stdin.lock().lines();

    while let Some(Ok(line)) = lines.next() {
        // A block is consumed whole, inside what the real subject does in a single `read_line`, so
        // no gate can interleave with it and `exit` inside it is content rather than a command.
        let turn = if line.trim_end_matches(['\r', '\n']) == BLOCK_OPEN {
            let mut body: Vec<String> = Vec::new();
            loop {
                match lines.next() {
                    Some(Ok(l)) if l.trim_end_matches(['\r', '\n']) == BLOCK_CLOSE => break,
                    Some(Ok(l)) => body.push(l.trim_end_matches(['\r', '\n']).to_string()),
                    _ => {
                        log("BLOCK_UNTERMINATED", "");
                        return;
                    }
                }
            }
            body.join("\n").trim().to_string()
        } else {
            line.trim().to_string()
        };
        // Escaped so one turn stays one log line — the tests count `TURN\t` entries, and a raw
        // multi-line turn would inflate that count into a passing-looking number.
        log("TURN", &turn.replace('\n', "\\n"));
        if turn.is_empty() {
            continue; // repl.rs:125-127
        }
        if matches!(turn.as_str(), "exit" | "quit" | ":q") {
            break; // repl.rs:129-131
        }
        if env("FAKE_DIE").is_some() {
            return;
        }

        for _ in 0..gates {
            let _ = writeln!(err);
            let _ = writeln!(err, "  ⚠ {tool} wants to run ({} chars):", turn.len());
            for l in preview.split('|') {
                let _ = writeln!(err, "    {l}");
            }
            // NO trailing newline, and flushed: this is the shape that hangs a line-buffered
            // reader forever.
            let _ = write!(err, "  Allow? [y/N · or type a redirect] ");
            let _ = err.flush();

            match lines.next() {
                Some(Ok(answer)) => {
                    log("GATE_ANSWER", answer.trim());
                    let _ = writeln!(err);
                    let _ = err.flush();
                }
                _ => return,
            }
        }

        // Muted is not broken. The real subject echoes a line for file *mutations* only
        // (`tools.rs:962`), so one that spends a whole turn reading emits nothing between the
        // prompt and the turn boundary — and a harness that cannot reproduce that cannot test
        // what it does about it (F91).
        if env("FAKE_MUTE").is_none() {
            let _ = writeln!(out, "fake reply to: {turn}");
            let _ = out.flush();
        }
        // Bytes on the pipe that will never finish a line. The real subject does this on purpose
        // with its gate prompt, and by accident whenever it is killed mid-sentence.
        if let Some(tail) = env("FAKE_TAIL") {
            let _ = write!(out, "{tail}");
            let _ = out.flush();
        }

        if env("FAKE_HANG").is_some() {
            // Park forever. The driver's per-cell deadline is what has to end this.
            loop {
                std::thread::sleep(std::time::Duration::from_secs(3600));
            }
        }
        if let Some(ms) = env("FAKE_STALL_MS").and_then(|v| v.parse::<u64>().ok()) {
            std::thread::sleep(std::time::Duration::from_millis(ms));
        }

        total_in += per_in;
        total_out += per_out;
        let _ = writeln!(
            err,
            "⚡ turn iter={iter} in={total_in} out={total_out} ctx ~485/32k (1%)"
        );
        let _ = err.flush();
    }
}
