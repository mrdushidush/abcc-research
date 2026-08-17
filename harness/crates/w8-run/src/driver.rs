//! Driving the subject over three pipes, and the four traps that shape it.
//!
//! 1. **The gate prompt has no trailing newline** (`write!`, not `writeln!`,
//!    `cli_prompter.rs:84`). A line-buffered reader blocks on it forever, so this reads bytes and
//!    matches the marker against the *unterminated* tail of the stderr buffer (F3).
//! 2. **stdout and stderr carry different event classes.** Model text is stdout; the gate preview
//!    and the turn-end line are stderr. Merged, a harness cannot tell a gate from model output —
//!    and "first visible output" has to span both, or it overstates felt latency by the whole
//!    tool-call phase (F6: 25.9 s on stderr against 31.6 s on stdout for the same turn).
//! 3. **The turn-end line is the only turn boundary**, because piped mode never echoes the prompt
//!    arrow (`line_editor.rs:370-376` ignores its `prompt` argument entirely).
//! 4. **One line at a time, never pre-queued.** The line editor and the gate share one stdin and
//!    take turns owning it (`repl.rs:106-108`). A next turn sitting in the pipe when a gate fires
//!    is consumed as *the gate's answer*, and since any non-`y`/`n` text is a redirect
//!    (`cli_prompter.rs:118-135`), it is silently absorbed as an instruction instead of running as
//!    a turn. Nothing is written until the previous turn's end marker has been seen.

use std::io::{BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::mpsc::{self, Receiver, RecvTimeoutError};
use std::time::{Duration, Instant};

use regex::Regex;
use w8_corpus::{Action, OperatorRule};

use crate::env::ChildEnv;

/// The REPL's third banner line (`repl.rs:81-85`). Readiness matters because TTFVO is measured from
/// the moment the turn is written: send before the REPL reaches its first `read_line` and the
/// number silently absorbs process startup. The bytes would not be *lost* — a pipe buffers them —
/// which is exactly why this cannot be left to a sleep and hoped for.
const READY_MARKER: &str = "session: ";
/// After the marker, the recall pre-flight and the mission rehydrate may each still print
/// (`repl.rs:91`, `:97`). Quiet means startup is done.
const READY_QUIET: Duration = Duration::from_millis(250);
/// Default ceiling on waiting for the banner before refusing to measure. Overridable per spawn: a
/// real subject on a cold host can be slow, and the driver's own tests need it short.
pub const READY_CAP: Duration = Duration::from_secs(30);

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Stream {
    Out,
    Err,
}

impl Stream {
    fn tag(self) -> &'static str {
        match self {
            Stream::Out => "OUT",
            Stream::Err => "ERR",
        }
    }
}

struct Chunk {
    at: Duration,
    stream: Stream,
    bytes: Vec<u8>,
}

/// What ended a turn.
#[derive(Debug, Clone)]
pub enum TurnEnd {
    /// The `turn iter=` marker matched. **Session-cumulative** counts, not per-turn (F9).
    ///
    /// `ctx_est` is the subject's OWN estimate of its session size when the turn ended, already
    /// converted to tokens, and it is `None` unless the descriptor's `turn_end` declares a fourth
    /// capture group for it. It exists because the three cumulative counts cannot answer *"did this
    /// cell ever hold a large context"* — 317,865 tokens over 22 iterations is the same number
    /// whether the session sat at 14k throughout or climbed to 30k. The K-series needs that
    /// distinction: a task that measures behaviour under context pressure cannot report a result
    /// from a cell that never entered the regime. See `peak_prompt_tokens` in `main.rs`.
    Marker { iterations: u32, tokens_in: u64, tokens_out: u64, ctx_est: Option<u64> },
    Timeout,
    /// The subject exited without printing a turn boundary.
    Eof,
    /// The harness could not answer something and refused to guess. `INVALID`, never `FAIL`.
    Blocked(String),
}

#[derive(Debug, Clone)]
pub struct GateAction {
    pub at_ms: u64,
    pub tool: String,
    pub action: String,
    /// Index of the operator rule that fired, or `None` when the variant's `default` answered.
    pub rule: Option<usize>,
}

#[derive(Debug, Clone)]
pub struct TurnRun {
    pub ttfvo_ms: Option<u64>,
    pub ttft_stdout_ms: Option<u64>,
    pub wall_ms: u64,
    pub end: TurnEnd,
}

/// The operator track for one session. `times` counters live here because SPEC §5 scopes them to
/// the session: "an exhausted rule stops matching and the next one is tried."
pub struct OperatorTrack<'a> {
    rules: &'a [OperatorRule],
    default: Option<&'a Action>,
    fired: Vec<u32>,
    pub gate_fires: u32,
    /// Gates that fired strictly after the first `deny` this track delivered (SPEC §5, F36). The
    /// denied gate itself is not counted, and neither is anything before it.
    pub gate_fires_after_deny: u32,
    /// Set the moment a `deny` is delivered. Not set by the unanswerable-gate path: that writes
    /// `n` to avoid a deadlock and fails the cell, so it is the harness refusing to guess rather
    /// than the operator refusing the subject.
    deny_delivered: bool,
    pub interventions_delivered: u32,
    pub unscripted_gates: u32,
    pub actions: Vec<GateAction>,
}

/// What the track decided for one gate.
enum Decision<'a> {
    Rule(usize, &'a Action),
    Default(&'a Action),
    /// No rule matched and there is no `default`.
    Unanswerable,
}

impl<'a> OperatorTrack<'a> {
    pub fn new(rules: &'a [OperatorRule], default: Option<&'a Action>) -> Self {
        OperatorTrack {
            rules,
            default,
            fired: vec![0; rules.len()],
            gate_fires: 0,
            gate_fires_after_deny: 0,
            deny_delivered: false,
            interventions_delivered: 0,
            unscripted_gates: 0,
            actions: Vec::new(),
        }
    }

    /// What this track observed, in the shape `Expect::violation` checks.
    pub fn observed(&self) -> w8_corpus::Observed {
        w8_corpus::Observed {
            gate_fires: self.gate_fires,
            gate_fires_after_deny: self.gate_fires_after_deny,
            interventions_delivered: self.interventions_delivered,
            unscripted_gates: self.unscripted_gates,
        }
    }

    fn decide(&mut self, tool: &str, preview: &str) -> Decision<'a> {
        for (i, rule) in self.rules.iter().enumerate() {
            if let Some(cap) = rule.times
                && self.fired[i] >= cap
            {
                continue;
            }
            if rule.on.gate.matches(tool, preview) {
                self.fired[i] += 1;
                return Decision::Rule(i, &rule.action);
            }
        }
        match self.default {
            Some(a) => Decision::Default(a),
            None => Decision::Unanswerable,
        }
    }
}

/// A live subject process with byte-level pumps and a transcript.
pub struct Session {
    child: Child,
    stdin: Option<ChildStdin>,
    rx: Receiver<Chunk>,
    t0: Instant,
    pending: [Vec<u8>; 2],
    gate_ctx: Vec<String>,
    transcript: BufWriter<std::fs::File>,
    pub transcript_path: PathBuf,
    gate_marker: String,
    turn_end: Regex,
    ready_cap: Duration,
    pub startup_ms: u64,
}

/// Everything one spawn needs. A struct rather than nine positional arguments, because two of them
/// are `&str` and mixing up `gate_marker` and `label` would silently stop every gate being noticed.
pub struct SpawnSpec<'a> {
    pub bin: &'a str,
    pub args: &'a [String],
    pub workdir: &'a Path,
    pub env: &'a ChildEnv,
    /// A substring of the gate prompt, not a regex — the prompt's full text is
    /// `  Allow? [y/N · or type a redirect] ` and the descriptor declares only its stable head.
    pub gate_marker: &'a str,
    pub turn_end: Regex,
    pub transcript_path: PathBuf,
    pub label: &'a str,
    pub ready_cap: Duration,
}

#[derive(Debug)]
pub enum SpawnError {
    Io(std::io::Error),
    /// The subject descriptor's `turn_end` is not a usable regex, or has no capture groups. It is
    /// the only source of `iterations`, `tokens_in` and `tokens_out`, so this is fatal at startup
    /// rather than a metric that quietly comes back empty.
    Marker(String),
    NotReady(String),
}

impl std::fmt::Display for SpawnError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SpawnError::Io(e) => write!(f, "{e}"),
            SpawnError::Marker(m) => write!(f, "{m}"),
            SpawnError::NotReady(m) => write!(f, "{m}"),
        }
    }
}

/// Parse a humanized token count of the shape Claudette's gauge prints — `840` or `14k`.
///
/// 🚨 **`k` is 1024, not 1000.** `humanize_tokens` is
/// `if n < 1024 { n } else { round(n / 1024.0) }k` (`run/cli_prompter.rs:18-24`), so `14k` means
/// 14,336. Reading it as 14,000 would understate every context figure by 2.4%, in the direction
/// that makes a cell look like it entered a regime it did not.
fn parse_humanized(s: &str) -> Option<u64> {
    match s.strip_suffix('k') {
        Some(head) => head.parse::<u64>().ok().map(|k| k * 1024),
        None => s.parse::<u64>().ok(),
    }
}

/// Compile the descriptor's `turn_end` and check it can actually yield the three numbers.
pub fn compile_turn_end(pattern: &str) -> Result<Regex, SpawnError> {
    let re = Regex::new(pattern)
        .map_err(|e| SpawnError::Marker(format!("markers.turn_end is not a regex: {e}")))?;
    if re.captures_len() < 4 {
        return Err(SpawnError::Marker(format!(
            "markers.turn_end {pattern:?} has {} capture group(s); SPEC §7 needs three \
             (iterations, in, out) and they are the only source of the token metrics",
            re.captures_len() - 1
        )));
    }
    // A FOURTH group is optional and means the subject's context estimate, humanized.
    // Optional rather than required so both existing subject descriptors stay valid without
    // edits — a descriptor is pinned to a subject commit, and a baseline whose subject id no
    // longer resolves is not a baseline. A descriptor that declares it gets
    // `peak_prompt_tokens`; one that does not gets an explicit `not_applicable`, never a zero.
    Ok(re)
}

impl Session {
    /// Spawn the subject, wait until the REPL is ready for its first line, and record how long that
    /// took. `startup_ms` is kept separate from `wall_clock_s` because process start is a property
    /// of the harness, not of the task.
    pub fn spawn(spec: SpawnSpec<'_>) -> Result<Session, SpawnError> {
        let SpawnSpec {
            bin,
            args,
            workdir,
            env,
            gate_marker,
            turn_end,
            transcript_path,
            label,
            ready_cap,
        } = spec;
        let mut cmd = Command::new(bin);
        cmd.args(args)
            .current_dir(workdir)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());
        env.apply(&mut cmd);

        let t0 = Instant::now();
        let mut child = cmd.spawn().map_err(SpawnError::Io)?;
        let stdin = child.stdin.take();
        let out = child.stdout.take().expect("piped");
        let err = child.stderr.take().expect("piped");

        let (tx, rx) = mpsc::channel::<Chunk>();
        for (mut rdr, stream) in
            [(Box::new(out) as Box<dyn Read + Send>, Stream::Out), (Box::new(err), Stream::Err)]
        {
            let tx = tx.clone();
            std::thread::spawn(move || {
                let mut buf = [0u8; 4096];
                loop {
                    match rdr.read(&mut buf) {
                        Ok(0) | Err(_) => return,
                        Ok(n) => {
                            if tx
                                .send(Chunk { at: t0.elapsed(), stream, bytes: buf[..n].to_vec() })
                                .is_err()
                            {
                                return;
                            }
                        }
                    }
                }
            });
        }
        drop(tx);

        let file = std::fs::File::create(&transcript_path).map_err(SpawnError::Io)?;
        let mut transcript = BufWriter::new(file);
        let _ = writeln!(transcript, "# w8-run transcript v1 — {label}");
        let _ = writeln!(transcript, "# {bin} in {}", workdir.display());
        let _ = writeln!(transcript, "# [ms] STREAM text; IN = written to the subject's stdin");

        let mut s = Session {
            child,
            stdin,
            rx,
            t0,
            pending: [Vec::new(), Vec::new()],
            gate_ctx: Vec::new(),
            transcript,
            transcript_path,
            gate_marker: gate_marker.to_string(),
            turn_end,
            ready_cap,
            startup_ms: 0,
        };
        s.await_ready()?;
        Ok(s)
    }

    fn ms(&self) -> u64 {
        self.t0.elapsed().as_millis() as u64
    }

    fn note(&mut self, tag: &str, text: &str) {
        let ms = self.ms();
        let _ = writeln!(self.transcript, "[{ms:>8}ms] {tag}  {text}");
    }

    /// Block until the banner's session line has appeared and the stream has gone quiet.
    fn await_ready(&mut self) -> Result<(), SpawnError> {
        let deadline = Instant::now() + self.ready_cap;
        let mut saw_marker = false;
        loop {
            let wait = if saw_marker { READY_QUIET } else { Duration::from_millis(500) };
            match self.rx.recv_timeout(wait) {
                Ok(chunk) => {
                    let lines = self.absorb(&chunk);
                    if lines.iter().any(|(st, l)| *st == Stream::Err && l.contains(READY_MARKER)) {
                        saw_marker = true;
                    }
                }
                Err(RecvTimeoutError::Timeout) => {
                    if saw_marker {
                        self.startup_ms = self.ms();
                        return Ok(());
                    }
                    if Instant::now() >= deadline {
                        return Err(SpawnError::NotReady(format!(
                            "the subject printed no line containing {READY_MARKER:?} within \
                             {} ms. That line is the REPL banner (repl.rs:81-85) and it is how the \
                             harness knows the first `read_line` has been reached; writing a turn \
                             before then folds process startup into ttfvo_ms",
                            self.ready_cap.as_millis()
                        )));
                    }
                }
                Err(RecvTimeoutError::Disconnected) => {
                    return Err(SpawnError::NotReady(
                        "the subject closed both streams before printing its banner".into(),
                    ));
                }
            }
        }
    }

    /// Fold one chunk into the per-stream buffers, returning every **complete** line it finished.
    /// The unterminated tail stays pending, which is what makes the newline-less gate prompt
    /// observable.
    fn absorb(&mut self, chunk: &Chunk) -> Vec<(Stream, String)> {
        let idx = match chunk.stream {
            Stream::Out => 0,
            Stream::Err => 1,
        };
        self.pending[idx].extend_from_slice(&chunk.bytes);
        let mut lines = Vec::new();
        while let Some(pos) = self.pending[idx].iter().position(|b| *b == b'\n') {
            let line: Vec<u8> = self.pending[idx].drain(..=pos).collect();
            let text = String::from_utf8_lossy(&line).trim_end_matches(['\n', '\r']).to_string();
            let at = chunk.at.as_millis() as u64;
            let _ = writeln!(self.transcript, "[{at:>8}ms] {}  {text}", chunk.stream.tag());
            lines.push((chunk.stream, text));
        }
        lines
    }

    /// Is a gate prompt sitting in the stderr tail? The marker is a substring, not a regex: the
    /// prompt's full text is `  Allow? [y/N · or type a redirect] ` and the descriptor declares
    /// only its stable head.
    fn pending_gate(&self) -> bool {
        String::from_utf8_lossy(&self.pending[1]).contains(&self.gate_marker)
    }

    fn write_line(&mut self, text: &str, why: &str) -> std::io::Result<()> {
        self.note("IN  ", &format!("{why}: {text}"));
        let stdin = self.stdin.as_mut().ok_or_else(|| {
            std::io::Error::new(std::io::ErrorKind::BrokenPipe, "subject stdin already closed")
        })?;
        stdin.write_all(text.as_bytes())?;
        stdin.write_all(b"\n")?;
        stdin.flush()
    }

    /// Send one turn and drive it to its end marker, answering gates from the operator track.
    ///
    /// `deadline` is the whole cell's, not this turn's: `timeout_s` comes from the donor's global
    /// per-task `TASK_TIMEOUT_MS`, so for a multi-turn task the budget is shared.
    pub fn run_turn(
        &mut self,
        lines: &[String],
        track: &mut OperatorTrack<'_>,
        deadline: Instant,
    ) -> TurnRun {
        let mut run = TurnRun {
            ttfvo_ms: None,
            ttft_stdout_ms: None,
            wall_ms: 0,
            end: TurnEnd::Eof,
        };
        // More than one line only for a sentinel-wrapped block, and writing it up front is safe
        // precisely because the subject consumes the whole block inside a single read: no gate can
        // fire part-way through, so none of these lines can be swallowed as a gate answer. That is
        // the one exception to "never pre-queue" (SPEC §5) and it holds only because the block is
        // read, not run.
        for line in lines {
            if let Err(e) = self.write_line(line, "turn") {
                run.end = TurnEnd::Blocked(format!("could not write the turn: {e}"));
                return run;
            }
        }
        let sent = Instant::now();
        // The send, expressed on the pumps' clock. Latency is computed from the *arrival* timestamp
        // a pump stamped, not from when this loop got round to the chunk.
        let sent_at = self.t0.elapsed();
        self.gate_ctx.clear();

        loop {
            let now = Instant::now();
            if now >= deadline {
                run.end = TurnEnd::Timeout;
                break;
            }
            let budget = (deadline - now).min(Duration::from_millis(500));
            match self.rx.recv_timeout(budget) {
                Ok(chunk) => {
                    // First visible output spans BOTH streams (F6). A chunk that arrived *before*
                    // the send is left-over startup output and is not this turn's first visible
                    // output — counting it would report 0 ms, which is an error in the flattering
                    // direction. The readiness quiet period should have drained it; this is the
                    // guard for when it did not.
                    let at = chunk.at.as_millis() as u64;
                    if chunk.at >= sent_at {
                        let since_send = (chunk.at - sent_at).as_millis() as u64;
                        if run.ttfvo_ms.is_none() {
                            run.ttfvo_ms = Some(since_send);
                        }
                        if run.ttft_stdout_ms.is_none() && chunk.stream == Stream::Out {
                            run.ttft_stdout_ms = Some(since_send);
                        }
                    }
                    let lines = self.absorb(&chunk);
                    let mut ended: Option<TurnEnd> = None;
                    for (stream, line) in lines {
                        if stream != Stream::Err {
                            continue;
                        }
                        if let Some(caps) = self.turn_end.captures(&line) {
                            ended = Some(TurnEnd::Marker {
                                iterations: caps[1].parse().unwrap_or(0),
                                tokens_in: caps[2].parse().unwrap_or(0),
                                tokens_out: caps[3].parse().unwrap_or(0),
                                // Absent group, or a group that does not parse, both mean "the
                                // subject did not tell us" — which is not the same as zero.
                                ctx_est: caps.get(4).and_then(|m| parse_humanized(m.as_str())),
                            });
                            break;
                        }
                        self.gate_ctx.push(line);
                    }
                    if let Some(end) = ended {
                        run.end = end;
                        break;
                    }
                    if self.pending_gate() {
                        // The prompt has no newline, so `absorb` never emitted it as a line and it
                        // would be missing from the transcript the verifier is handed. Record it
                        // before clearing, or the transcript shows a preview and an answer with no
                        // question between them.
                        let prompt =
                            String::from_utf8_lossy(&self.pending[1]).trim_end().to_string();
                        self.note("GATE", &prompt);
                        self.pending[1].clear();
                        if let Some(blocked) = self.answer_gate(track, at) {
                            run.end = TurnEnd::Blocked(blocked);
                            break;
                        }
                        self.gate_ctx.clear();
                    }
                }
                Err(RecvTimeoutError::Timeout) => {
                    if let Ok(Some(_)) = self.child.try_wait() {
                        run.end = TurnEnd::Eof;
                        break;
                    }
                }
                Err(RecvTimeoutError::Disconnected) => {
                    run.end = TurnEnd::Eof;
                    break;
                }
            }
        }
        run.wall_ms = sent.elapsed().as_millis() as u64;
        run
    }

    /// Has the subject process exited? Cheap, non-blocking.
    pub fn exited(&mut self) -> bool {
        matches!(self.child.try_wait(), Ok(Some(_)))
    }

    /// Answer one gate. `Some(reason)` means the harness refused to guess.
    fn answer_gate(&mut self, track: &mut OperatorTrack<'_>, at_ms: u64) -> Option<String> {
        let (tool, preview) = gate_context(&self.gate_ctx);
        track.gate_fires += 1;
        // Counted BEFORE this gate's own decision, so the denied gate is not counted as coming
        // after itself. F36: this is the only counter that answers "did being refused stop it".
        if track.deny_delivered {
            track.gate_fires_after_deny += 1;
        }

        let (action, rule, unscripted) = match track.decide(&tool, &preview) {
            Decision::Rule(i, a) => (a.clone(), Some(i), false),
            Decision::Default(a) => (a.clone(), None, true),
            Decision::Unanswerable => {
                // Deny first so the subject is never left blocked on stdin burning the task's
                // timeout, then fail the cell. Scoring this as anything but INVALID would be a
                // lie: a `control` cell reaching a gate means CLAUDETTE_AUTO_APPROVE did not take,
                // and the run measured a subject that could not edit a file rather than a hard
                // task.
                let _ = self.write_line("n", "unanswerable gate — denying to avoid a deadlock");
                track.unscripted_gates += 1;
                return Some(format!(
                    "a permission gate fired for tool {tool:?} and the variant declares no \
                     matching operator rule and no `default`. Denied to avoid deadlocking on \
                     stdin. For a mode = \"allow\" variant this means the auto-approve pin did \
                     not take effect"
                ));
            }
        };

        let line = match &action {
            Action::Approve => "y".to_string(),
            Action::Deny => "n".to_string(),
            Action::Redirect(text) => {
                // The gate reads ONE line (`cli_prompter.rs:96-101`). A redirect carrying a newline
                // would answer the gate with its first line and leave the rest in the pipe, where
                // the REPL's next `read_line` would run it as an unscripted turn.
                if text.contains('\n') || text.contains('\r') {
                    let _ = self.write_line("n", "malformed redirect — denying");
                    return Some(format!(
                        "operator redirect spans more than one line, which the gate cannot \
                         receive: {text:?}"
                    ));
                }
                let trimmed = text.trim();
                if trimmed.is_empty()
                    || matches!(trimmed.to_lowercase().as_str(), "y" | "yes" | "n" | "no")
                {
                    let _ = self.write_line("n", "degenerate redirect — denying");
                    return Some(format!(
                        "operator redirect {text:?} classifies as a plain allow/deny at the gate \
                         (cli_prompter.rs:118-135), so it would not be delivered as an instruction"
                    ));
                }
                text.clone()
            }
        };

        if matches!(action, Action::Deny) {
            track.deny_delivered = true;
        }
        if matches!(action, Action::Redirect(_)) {
            // An intervention is operator-authored content handed back to the subject. An approve
            // or a deny is an answer, not an intervention — `deny-first-edit` sets no
            // `interventions_delivered` expectation, and `redirect-first-edit` sets exactly one
            // against exactly one redirect rule.
            track.interventions_delivered += 1;
        }
        if unscripted {
            track.unscripted_gates += 1;
        }
        track.actions.push(GateAction {
            at_ms,
            tool: tool.clone(),
            action: action.label().to_string(),
            rule,
        });
        let why = format!("gate answer for {tool} ({})", action.label());
        if let Err(e) = self.write_line(&line, &why) {
            return Some(format!("could not answer the gate: {e}"));
        }
        None
    }

    /// Close stdin (EOF ends the REPL loop, `repl.rs:115-117`), then reap. Kills on any hang so a
    /// stuck subject cannot outlive the run.
    pub fn finish(mut self) -> Option<i32> {
        drop(self.stdin.take());
        let deadline = Instant::now() + Duration::from_secs(15);
        loop {
            match self.child.try_wait() {
                Ok(Some(status)) => {
                    let _ = self.transcript.flush();
                    return status.code();
                }
                Ok(None) if Instant::now() < deadline => {
                    // Keep draining, or a full pipe buffer keeps the child from exiting.
                    while let Ok(chunk) = self.rx.recv_timeout(Duration::from_millis(100)) {
                        self.absorb(&chunk);
                    }
                }
                _ => {
                    let _ = self.child.kill();
                    let _ = self.child.wait();
                    let _ = self.transcript.flush();
                    return None;
                }
            }
        }
    }

    pub fn kill(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
        let _ = self.transcript.flush();
    }
}

/// Pull the tool name and the input preview out of the stderr lines that precede a gate.
///
/// The prompter writes (`cli_prompter.rs:49-84`): a blank line, then
/// `  ⚠ <tool> wants to run (<n> chars):`, then each preview line indented four spaces, then the
/// newline-less prompt. So the tool name and the text an `input_contains` matcher looks at are
/// **already gone** by the time the marker appears — they have to be kept as they stream past.
pub fn gate_context(lines: &[String]) -> (String, String) {
    let anchor = lines.iter().rposition(|l| l.contains(" wants to run ("));
    let Some(a) = anchor else {
        return (String::new(), lines.join("\n"));
    };
    let tool = parse_tool_name(&lines[a]).unwrap_or_default();
    let preview = lines[a + 1..]
        .iter()
        .map(|l| l.strip_prefix("    ").unwrap_or(l))
        .collect::<Vec<_>>()
        .join("\n");
    (tool, preview)
}

/// `  ⚠ apply_diff wants to run (415 chars):` -> `apply_diff`. Tolerates the glyph being absent,
/// because `NO_COLOR` strips ANSI and not glyphs and a future theme could drop it.
pub fn parse_tool_name(line: &str) -> Option<String> {
    let head = &line[..line.find(" wants to run (")?];
    head.split_whitespace().last().map(str::to_string)
}

#[cfg(test)]
mod tests {
    use super::*;
    use w8_corpus::{GateMatcher, Matcher};

    fn rule(tool: Option<&str>, contains: Option<&str>, action: Action, times: Option<u32>) -> OperatorRule {
        OperatorRule {
            on: Matcher {
                gate: GateMatcher {
                    tool: tool.map(str::to_string),
                    input_contains: contains.map(str::to_string),
                },
            },
            action,
            times,
        }
    }

    #[test]
    fn tool_name_comes_off_the_real_prompter_line() {
        assert_eq!(
            parse_tool_name("  ⚠ apply_diff wants to run (415 chars):").unwrap(),
            "apply_diff"
        );
        assert_eq!(parse_tool_name("  bash wants to run (12 chars):").unwrap(), "bash");
        assert_eq!(parse_tool_name("  Allow? [y/N · or type a redirect] "), None);
    }

    #[test]
    fn gate_context_keeps_the_preview_an_input_contains_matcher_needs() {
        let lines = vec![
            String::new(),
            "  ⚠ bash wants to run (10 chars):".to_string(),
            "    cargo test --all".to_string(),
        ];
        let (tool, preview) = gate_context(&lines);
        assert_eq!(tool, "bash");
        // The four-space indent is the prompter's, not the tool input's, so `input_contains =
        // "cargo test"` has to match without the caller knowing about it.
        assert_eq!(preview, "cargo test --all");
    }

    #[test]
    fn a_second_gate_in_one_turn_uses_the_later_anchor() {
        let lines = vec![
            "  ⚠ read_file wants to run (4 chars):".to_string(),
            "    a.py".to_string(),
            "  ⚠ apply_diff wants to run (9 chars):".to_string(),
            "    -x +y".to_string(),
        ];
        assert_eq!(gate_context(&lines).0, "apply_diff");
    }

    #[test]
    fn first_matching_rule_wins_in_declaration_order() {
        let rules = vec![
            rule(Some("apply_diff"), None, Action::Deny, None),
            rule(None, None, Action::Approve, None),
        ];
        let mut t = OperatorTrack::new(&rules, None);
        assert!(matches!(t.decide("apply_diff", ""), Decision::Rule(0, Action::Deny)));
        assert!(matches!(t.decide("bash", ""), Decision::Rule(1, Action::Approve)));
    }

    #[test]
    fn an_exhausted_rule_stops_matching_and_the_next_one_is_tried() {
        let rules = vec![
            rule(None, None, Action::Redirect("say which file".into()), Some(1)),
            rule(None, None, Action::Approve, None),
        ];
        let mut t = OperatorTrack::new(&rules, None);
        assert!(matches!(t.decide("apply_diff", ""), Decision::Rule(0, _)));
        assert!(matches!(t.decide("apply_diff", ""), Decision::Rule(1, Action::Approve)));
        assert!(matches!(t.decide("apply_diff", ""), Decision::Rule(1, Action::Approve)));
    }

    #[test]
    fn input_contains_narrows_within_the_same_tool() {
        let rules = vec![
            rule(Some("bash"), Some("cargo test"), Action::Deny, None),
            rule(None, None, Action::Approve, None),
        ];
        let mut t = OperatorTrack::new(&rules, None);
        assert!(matches!(t.decide("bash", "cargo test --all"), Decision::Rule(0, Action::Deny)));
        assert!(matches!(t.decide("bash", "ls"), Decision::Rule(1, Action::Approve)));
    }

    #[test]
    fn no_rule_and_no_default_is_unanswerable_rather_than_a_guess() {
        let rules: Vec<OperatorRule> = vec![];
        let mut t = OperatorTrack::new(&rules, None);
        assert!(matches!(t.decide("apply_diff", ""), Decision::Unanswerable));
    }

    #[test]
    fn the_default_answers_a_gate_no_rule_matched() {
        let rules = vec![rule(Some("bash"), None, Action::Approve, None)];
        let deny = Action::Deny;
        let mut t = OperatorTrack::new(&rules, Some(&deny));
        assert!(matches!(t.decide("apply_diff", ""), Decision::Default(Action::Deny)));
    }

    #[test]
    fn the_declared_turn_end_marker_yields_all_three_numbers() {
        let re = compile_turn_end(r"^⚡ turn iter=(\d+) in=(\d+) out=(\d+)").unwrap();
        let line = "⚡ turn iter=5 in=21106 out=505 ctx ~485/32k (1%)";
        let caps = re.captures(line).expect("the real REPL line must match");
        assert_eq!((&caps[1], &caps[2], &caps[3]), ("5", "21106", "505"));
    }

    #[test]
    fn the_one_shot_usage_line_is_not_a_turn_boundary() {
        // Measured: one-shot prints `⚡ iter=1 in=1816 out=142` with no `turn`. If that ever
        // matched, a one-shot subject would look like a REPL one while carrying a different system
        // prompt (1,816 input tokens against the REPL's ~4,885) — comparable to nothing.
        let re = compile_turn_end(r"^⚡ turn iter=(\d+) in=(\d+) out=(\d+)").unwrap();
        assert!(re.captures("⚡ iter=1 in=1816 out=142").is_none());
    }

    #[test]
    fn a_marker_without_three_captures_is_refused_at_startup() {
        let e = compile_turn_end(r"^⚡ turn iter=(\d+)").expect_err("must refuse");
        assert!(format!("{e}").contains("capture"), "{e}");
    }

    #[test]
    fn a_fourth_capture_group_is_optional_not_required() {
        // Both shipped descriptors declare only three groups and must keep compiling: a
        // descriptor is pinned to a subject commit, and a baseline whose subject no longer
        // resolves is not a baseline.
        compile_turn_end(r"^⚡ turn iter=(\d+) in=(\d+) out=(\d+)").expect("three is still valid");
        compile_turn_end(r"^⚡ turn iter=(\d+) in=(\d+) out=(\d+).*?ctx ~(\d+k?)/")
            .expect("four is also valid");
    }

    #[test]
    fn humanized_k_is_1024_not_1000() {
        // The bug this pins. `humanize_tokens` is round(n / 1024.0) with a `k` suffix
        // (claudette run/cli_prompter.rs:18-24), so reading `k` as 1000 understates every
        // context figure by 2.4% — in the direction that makes a cell look like it entered a
        // regime it did not. A conservative gate must never be optimistic by accident.
        assert_eq!(parse_humanized("14k"), Some(14 * 1024));
        assert_eq!(parse_humanized("39k"), Some(39_936));
        // Below 1024 the gauge prints the raw count with no suffix.
        assert_eq!(parse_humanized("840"), Some(840));
        // Anything unparseable is absent, never zero: "the subject did not say" and "the subject
        // said nothing was in context" are different facts.
        assert_eq!(parse_humanized(""), None);
        assert_eq!(parse_humanized("k"), None);
        assert_eq!(parse_humanized("~14k"), None);
    }

    #[test]
    fn the_context_estimate_is_read_from_the_fourth_group() {
        // The real line Claudette printed on the first K-series cell, verbatim.
        let re = compile_turn_end(r"^⚡ turn iter=(\d+) in=(\d+) out=(\d+).*?ctx ~(\d+k?)/").unwrap();
        let line = "⚡ turn iter=22 in=317865 out=27734 ctx ~14k/39k (36%)";
        let caps = re.captures(line).expect("must match the shipped format");
        assert_eq!(&caps[1], "22");
        assert_eq!(&caps[2], "317865");
        assert_eq!(&caps[3], "27734");
        assert_eq!(parse_humanized(&caps[4]), Some(14 * 1024));
    }
}
