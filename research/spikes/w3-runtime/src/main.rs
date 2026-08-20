//! W3 item 6 — the runtime probe.
//!
//! Four questions, all asked against the EXACT stack the engine being copied
//! already ships (`reqwest` 0.12, `blocking` feature, no async in the caller):
//!
//!   A. Is the blocking client's `timeout` a total-duration budget or a
//!      per-read (idle-gap) budget when the body is streamed through `Read`?
//!   B. Does a hung server — headers sent, one line, then silence — actually
//!      trip that timeout, and after how long?
//!   C. Can a *second thread* stop a stream mid-flight with nothing but an
//!      `AtomicBool` checked between lines, and how fast does the server see
//!      the disconnect?
//!   D. What does the blocking stack cost in threads? (one runtime thread per
//!      `blocking::Client`, per reqwest's own construction.)
//!
//! Run: `python server.py 8731` in one shell, `cargo run --release` here.

use std::io::{BufRead, BufReader};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

const BASE: &str = "http://127.0.0.1:8731";

fn client(timeout_secs: u64) -> reqwest::blocking::Client {
    reqwest::blocking::Client::builder()
        .no_proxy()
        .timeout(Duration::from_secs(timeout_secs))
        .build()
        .expect("client")
}

/// Read a streamed body line by line, optionally aborting when `cancel` flips.
/// Returns (lines read, elapsed, outcome string).
fn drain(
    resp: reqwest::blocking::Response,
    cancel: Option<Arc<AtomicBool>>,
) -> (usize, Duration, String) {
    let t0 = Instant::now();
    let mut n = 0usize;
    let reader = BufReader::new(resp);
    for line in reader.lines() {
        if let Some(c) = &cancel {
            if c.load(Ordering::Relaxed) {
                // Dropping the reader (and with it the Response) here is the
                // whole cancellation mechanism. No runtime involved.
                return (n, t0.elapsed(), "CANCELLED between lines".to_string());
            }
        }
        match line {
            Ok(l) => {
                if !l.trim().is_empty() {
                    n += 1;
                }
            }
            Err(e) => return (n, t0.elapsed(), format!("READ ERROR: {e}")),
        }
    }
    (n, t0.elapsed(), "EOF".to_string())
}

fn test_a() {
    println!("\n=== A. total-duration or per-read? ===");
    // 6 lines, 1000 ms apart => ~5 s of wall clock, with no single gap over
    // 1 s. Client timeout 2 s. A total-duration budget fails at ~2 s; a
    // per-read budget completes.
    let c = client(2);
    let t0 = Instant::now();
    match c.get(format!("{BASE}/gap?gap_ms=1000&n=6")).send() {
        Ok(r) => {
            let (n, d, why) = drain(r, None);
            println!(
                "  gap=1000ms n=6, client timeout=2s -> {n} lines in {:.3}s ({why}); total {:.3}s",
                d.as_secs_f64(),
                t0.elapsed().as_secs_f64()
            );
            println!(
                "  VERDICT: {}",
                if n >= 6 {
                    "PER-READ — the 2 s budget restarts on every chunk"
                } else {
                    "TOTAL-DURATION — the whole body shares one budget"
                }
            );
        }
        Err(e) => println!("  send failed: {e}"),
    }
}

fn test_a2() {
    println!("\n=== A2. the same body, one gap longer than the budget ===");
    // 3 lines, 3000 ms apart, client timeout 2 s. Under per-read semantics
    // this must FAIL — and fail on the first gap, ~2 s in, not at the end.
    let c = client(2);
    match c.get(format!("{BASE}/gap?gap_ms=3000&n=3")).send() {
        Ok(r) => {
            let (n, d, why) = drain(r, None);
            println!(
                "  gap=3000ms n=3, client timeout=2s -> {n} lines, stopped after {:.3}s ({why})",
                d.as_secs_f64()
            );
        }
        Err(e) => println!("  send failed: {e}"),
    }
}

fn test_b() {
    println!("\n=== B. the hung server: headers, one line, then silence ===");
    let c = client(3);
    match c.get(format!("{BASE}/hang")).send() {
        Ok(r) => {
            let (n, d, why) = drain(r, None);
            println!(
                "  client timeout=3s -> {n} lines, gave up after {:.3}s ({why})",
                d.as_secs_f64()
            );
        }
        Err(e) => println!("  send failed: {e}"),
    }
}

fn test_c() {
    println!("\n=== C. cancel from another thread, no runtime ===");
    // Firehose with a 100 ms gap; a watchdog thread flips the flag at 1 s.
    let c = client(30);
    let cancel = Arc::new(AtomicBool::new(false));
    let flag = cancel.clone();
    let watchdog = std::thread::spawn(move || {
        std::thread::sleep(Duration::from_millis(1000));
        flag.store(true, Ordering::Relaxed);
    });
    match c.get(format!("{BASE}/firehose?n=1000&gap_ms=100")).send() {
        Ok(r) => {
            let (n, d, why) = drain(r, Some(cancel));
            println!(
                "  {n} lines then {why} at {:.3}s (watchdog fired at 1.000s)",
                d.as_secs_f64()
            );
            println!("  server-side FIN observation is in the server log above/below.");
        }
        Err(e) => println!("  send failed: {e}"),
    }
    watchdog.join().ok();
    // Give the server a moment to notice and log the closed socket.
    std::thread::sleep(Duration::from_millis(1500));
}

fn test_e() {
    println!("
=== E. does the same number govern time-to-first-byte? ===");
    // Headers delayed 3 s, client timeout 2 s. If `send()` shares the budget
    // the request dies before a single byte arrives — meaning one knob covers
    // both the prefill wait and the inter-chunk gap, and they cannot be set
    // apart on the blocking API.
    let c = client(2);
    let t0 = Instant::now();
    match c.get(format!("{BASE}/slowhead?head_ms=3000")).send() {
        Ok(r) => {
            let (n, d, why) = drain(r, None);
            println!(
                "  head=3000ms, client timeout=2s -> headers arrived, {n} lines ({why}) at {:.3}s",
                d.as_secs_f64()
            );
            println!("  VERDICT: send() has its OWN budget, separate from the body");
        }
        Err(e) => {
            println!(
                "  head=3000ms, client timeout=2s -> send() failed after {:.3}s: {e}",
                t0.elapsed().as_secs_f64()
            );
            println!("  VERDICT: ONE knob — the same duration bounds TTFB and each read");
        }
    }
    // And the converse: headers delayed 1 s, under the 2 s budget, then a
    // normal body. Must succeed, proving the budget is not cumulative.
    let c = client(2);
    let t0 = Instant::now();
    match c.get(format!("{BASE}/slowhead?head_ms=1500")).send() {
        Ok(r) => {
            let (n, _d, why) = drain(r, None);
            println!(
                "  head=1500ms under a 2s budget -> {n} lines ({why}), total {:.3}s",
                t0.elapsed().as_secs_f64()
            );
        }
        Err(e) => println!("  head=1500ms unexpectedly failed: {e}"),
    }
}

fn thread_count() -> usize {
    // Windows: count threads of this process via the toolhelp-free route —
    // read it from the OS through `tasklist`, which needs no extra crate.
    let pid = std::process::id();
    let out = std::process::Command::new("powershell")
        .args([
            "-NoProfile",
            "-Command",
            &format!("(Get-Process -Id {pid}).Threads.Count"),
        ])
        .output();
    match out {
        Ok(o) => String::from_utf8_lossy(&o.stdout)
            .trim()
            .parse()
            .unwrap_or(0),
        Err(_) => 0,
    }
}

fn test_d() {
    println!("\n=== D. what the blocking stack costs in threads ===");
    let before = thread_count();
    println!("  process threads before any client: {before}");
    let mut clients = Vec::new();
    for i in 1..=4 {
        let c = client(5);
        // A client only spawns its runtime thread lazily? No — reqwest builds
        // the ClientHandle (and its thread) in `Client::builder().build()`.
        // Issue one request anyway so the connection pool is live too.
        let _ = c.get(format!("{BASE}/gap?gap_ms=1&n=1")).send().map(|r| {
            let _ = drain(r, None);
        });
        clients.push(c);
        println!("  after {i} blocking::Client(s): {} threads", thread_count());
    }
    drop(clients);
    std::thread::sleep(Duration::from_millis(500));
    println!("  after dropping all clients: {} threads", thread_count());
}

fn main() {
    println!("W3 item 6 runtime probe — reqwest blocking, no async in the caller");
    println!("reqwest version compiled in: see Cargo.lock");
    test_a();
    test_a2();
    test_b();
    test_c();
    test_e();
    test_d();
    println!("\ndone");
}
