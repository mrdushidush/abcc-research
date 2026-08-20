# W3 item 6 — the runtime probe

**Question this spike exists to settle:** the standing argument for adopting `tokio` in ABCC 2.0's
core is that a blocking stack cannot cancel a request in flight and cannot tell a hung model server
from a slow one. Both halves are testable in an afternoon, against the *exact* dependency line the
engine being copied already ships — `reqwest = { version = "0.12", features = ["blocking", …] }`,
`crates/claudette/Cargo.toml:57` — with no async anywhere in the caller.

Run 2026-08-20. Two repeats, agreeing within milliseconds. Raw output:
`w3-runtime-probe-results.txt`.

## What is here

| File | What it is |
|---|---|
| `server.py` | stdlib-only chunked HTTP server with four shapes: `/gap` (N lines M ms apart), `/hang` (one line then silence, socket held), `/firehose` (cancellation target), `/slowhead` (headers delayed — the prefill analogue). Logs to stderr **when the client's socket died and how long after the request started**: the server-side witness. |
| `src/main.rs` | five tests, A/A2/B/C/D/E, each printing its own verdict |
| `w3-runtime-probe-results.txt` | both runs plus the server witness lines |

## How to run

```
python server.py 8731          # one shell
cargo run --release            # the other
```

The server holds `/hang` sockets for up to 120 s; kill it when done.

## Results

**A — the blocking `timeout` is a per-read budget, not a total-duration one.** Six lines 1000 ms
apart (≈5 s of body) complete under a **2 s** client timeout: 7 lines in 5.003 s / 5.002 s. The
budget restarts on every chunk.

**A2 — and it is exact.** The same server with one 3000 ms gap under the same 2 s budget fails at
**2.004 s / 2.015 s**, on the first over-budget gap — not at the end of the body.

**B — a hung server is detected on schedule.** Headers, one line, then silence: the client gives up
at **3.005 s / 3.013 s** under a 3 s budget. The server's own log shows it saw the peer close at
**3.024 s**, 19 ms later.

**C — cancellation needs no runtime.** A watchdog thread flips an `AtomicBool` at 1.000 s; the
reading thread checks it between lines and drops the `Response`: stopped at **1.014 s / 1.004 s**.
The server observed the dead socket at 1.205–1.215 s — one write cadence later (it writes every
100 ms), because a first write into a just-closed socket succeeds locally and the second one fails.
A server that *polls* its socket instead of writing sees it in ~20 ms (test B).

**E — one knob covers time-to-first-byte too, and it is not cumulative.** Headers delayed 3 s under
a 2 s budget: `send()` fails at **2.006 s / 2.012 s**. Delayed 1.5 s: succeeds, and the body then
gets its own fresh budget (total 1.516 s / 1.502 s). So the single `timeout` value bounds *the wait
for the first byte* and *each subsequent read* separately — but with the same number. The blocking
`ClientBuilder` has no second knob: `read_timeout` was added in reqwest 0.12.4 to the **async**
builder only and is still absent from the blocking one on master (checked 2026-08-20).

**D — what the blocking stack costs in threads.** Exactly **+1 OS thread per `blocking::Client`**,
released on drop: 5 → 6 → 7 → 8 → 9 for four clients, back to 5 after dropping them. That thread is
reqwest's own: `blocking/client.rs:1365-1370` spawns `reqwest-internal-sync-runtime` running a
**current-thread tokio runtime** and forwards every request to it over an mpsc channel.

## The mechanism behind A/A2/E, for the record

`impl Read for Response` (`blocking/response.rs:435-441`) calls
`wait::timeout(self.body_mut().read(buf), self.timeout)` — and `wait::timeout` computes
`deadline = Instant::now() + d` **inside the call** (`blocking/wait.rs`), parking the thread until
the waker fires. A fresh deadline per `read()` is exactly idle-gap semantics. Verified unchanged on
reqwest master, so the behaviour is not a 0.12-only accident: the changelog puts
"`blocking` request-scoped timeout applying to bodies" at v0.11.7.

## Caveat

The server here is Python's `ThreadingHTTPServer`, so the *server-side* detection latencies
characterise a naive server, not llama.cpp. The real numbers against `llama-server` are F162's
(≤0.25 s mid-decode) and were measured separately in the OQ-W3-8 probe. What this spike measures is
the **client** side, which is the side 2.0 writes.
