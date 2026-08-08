//! The driver against `fake-subject` — a subject with no model behind it.
//!
//! Every assertion here would also pass against a driver that never spawned anything, if the fake
//! did not actively produce the events being looked for. That is why the fake prints a real gate
//! preview, a real newline-less prompt and a real session-cumulative turn line, and why it logs
//! **what it was answered**: the log is the positive control, and without it "the gate was
//! approved" is a claim about the harness's own bookkeeping rather than about bytes that reached the
//! subject (F18-F21's lesson, applied to the instrument instead of the corpus).

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use w8_corpus::{Action, GateMatcher, Matcher, OperatorRule};
use w8_run::driver::{compile_turn_end, OperatorTrack, Session, SpawnSpec, TurnEnd};
use w8_run::env::ChildEnv;

const TURN_END: &str = r"^⚡ turn iter=(\d+) in=(\d+) out=(\d+)";
const GATE: &str = "Allow? [y/N";

fn scratch(name: &str) -> PathBuf {
    let d = std::env::temp_dir().join(format!("w8-run-test-{name}"));
    let _ = std::fs::remove_dir_all(&d);
    std::fs::create_dir_all(&d).unwrap();
    d
}

fn env_with(vars: &[(&str, &str)]) -> ChildEnv {
    let mut pinned: BTreeMap<String, String> = BTreeMap::new();
    for (k, v) in vars {
        pinned.insert((*k).to_string(), (*v).to_string());
    }
    ChildEnv { pinned, removed: Vec::new() }
}

fn spec<'a>(dir: &'a Path, env: &'a ChildEnv, label: &'a str) -> SpawnSpec<'a> {
    SpawnSpec {
        bin: env!("CARGO_BIN_EXE_fake-subject"),
        args: &[],
        workdir: dir,
        env,
        gate_marker: GATE,
        turn_end: compile_turn_end(TURN_END).unwrap(),
        transcript_path: dir.join("transcript.log"),
        label,
        ready_cap: Duration::from_secs(10),
    }
}

fn spawn(dir: &Path, vars: &[(&str, &str)], label: &str) -> Session {
    let env = env_with(vars);
    Session::spawn(spec(dir, &env, label))
        .expect("the fake subject must start and print its banner")
}

fn log_lines(dir: &Path) -> Vec<String> {
    std::fs::read_to_string(dir.join("fake.log"))
        .unwrap_or_default()
        .lines()
        .map(str::to_string)
        .collect()
}

fn answers(dir: &Path) -> Vec<String> {
    log_lines(dir)
        .iter()
        .filter_map(|l| l.strip_prefix("GATE_ANSWER\t").map(str::to_string))
        .collect()
}

fn log_path(dir: &Path) -> String {
    dir.join("fake.log").display().to_string()
}

fn deadline(secs: u64) -> Instant {
    Instant::now() + Duration::from_secs(secs)
}

/// A one-line turn. `run_turn` takes a slice because a sentinel-wrapped block is several lines
/// that the subject reassembles into one turn.
fn one(text: &str) -> Vec<String> {
    vec![text.to_string()]
}

#[test]
fn a_turn_completes_and_the_marker_carries_all_three_numbers() {
    let d = scratch("plain-turn");
    let log = log_path(&d);
    let mut s = spawn(&d, &[("FAKE_LOG", &log), ("FAKE_IN", "4885"), ("FAKE_OUT", "63")], "plain");
    let mut t = OperatorTrack::new(&[], None);
    let run = s.run_turn(&one("do the thing"), &mut t, deadline(30));
    match run.end {
        TurnEnd::Marker { iterations, tokens_in, tokens_out } => {
            assert_eq!((iterations, tokens_in, tokens_out), (1, 4885, 63));
        }
        other => panic!("expected a marker, got {other:?}"),
    }
    // The turn text reached the subject as one line.
    assert_eq!(
        log_lines(&d).iter().filter(|l| l.starts_with("TURN\t")).count(),
        1,
        "one line in must be one turn"
    );
    assert_eq!(t.gate_fires, 0);
    s.finish();
}

#[test]
fn a_sentinel_block_is_delivered_as_exactly_one_turn() {
    // The whole point of the delivery fix: several lines in, ONE turn out, with the newlines and
    // the blank line intact and a bare `exit` treated as content instead of ending the session.
    let d = scratch("block-turn");
    let log = log_path(&d);
    let mut s = spawn(&d, &[("FAKE_LOG", &log)], "block");
    let mut t = OperatorTrack::new(&[], None);
    let block: Vec<String> = [
        "<<<CLAUDETTE-PROMPT",
        "first line",
        "",
        "exit",
        "last line",
        "CLAUDETTE-PROMPT>>>",
    ]
    .iter()
    .map(|s| (*s).to_string())
    .collect();

    let run = s.run_turn(&block, &mut t, deadline(30));
    assert!(matches!(run.end, TurnEnd::Marker { .. }), "expected a marker, got {:?}", run.end);

    let turns: Vec<String> = log_lines(&d)
        .iter()
        .filter_map(|l| l.strip_prefix("TURN\t").map(str::to_string))
        .collect();
    assert_eq!(turns.len(), 1, "six lines in must still be one turn: {turns:?}");
    assert_eq!(
        turns[0], "first line\\n\\nexit\\nlast line",
        "the block's interior newlines and blank line survive, and `exit` is content"
    );
    s.finish();
}

#[test]
fn an_unterminated_block_is_visible_rather_than_silently_swallowed() {
    // The negative control for the test above. If the fake accepted an unterminated block as a
    // turn, the delivery test would pass against a driver that never wrote the closing sentinel.
    let d = scratch("block-unterminated");
    let log = log_path(&d);
    let mut s = spawn(&d, &[("FAKE_LOG", &log)], "block-bad");
    let mut t = OperatorTrack::new(&[], None);
    let open = vec!["<<<CLAUDETTE-PROMPT".to_string(), "orphan".to_string()];

    let run = s.run_turn(&open, &mut t, Instant::now() + Duration::from_millis(1500));
    assert!(
        !matches!(run.end, TurnEnd::Marker { .. }),
        "an unterminated block must not complete a turn, got {:?}",
        run.end
    );
    // The load-bearing half: the subject is still *waiting* for the terminator, so it has not
    // logged a turn. Without this, the test above would pass against a fake that ran the opening
    // sentinel as a turn of its own and got a marker back by luck.
    assert!(
        !log_lines(&d).iter().any(|l| l.starts_with("TURN\t")),
        "no turn may be logged while the block is still open: {:?}",
        log_lines(&d)
    );
    s.finish();
}

#[test]
fn ttfvo_spans_both_streams_and_stdout_alone_would_overstate_it() {
    // F6: the gate preview lands on stderr well before any model text lands on stdout. With a
    // stall between them the two numbers must differ, and ttfvo must be the earlier one.
    let d = scratch("ttfvo");
    let log = log_path(&d);
    let rules = vec![rule(None, None, Action::Approve, None)];
    let mut s = spawn(
        &d,
        &[("FAKE_LOG", &log), ("FAKE_GATES", "1"), ("FAKE_STALL_MS", "400")],
        "ttfvo",
    );
    let mut t = OperatorTrack::new(&rules, None);
    let run = s.run_turn(&one("edit it"), &mut t, deadline(30));
    assert!(matches!(run.end, TurnEnd::Marker { .. }), "{:?}", run.end);
    let ttfvo = run.ttfvo_ms.expect("something was written");
    let ttft = run.ttft_stdout_ms.expect("the fake replies on stdout");
    assert!(ttfvo <= ttft, "ttfvo {ttfvo} must not be later than ttft_stdout {ttft}");
    s.finish();
}

fn rule(
    tool: Option<&str>,
    contains: Option<&str>,
    action: Action,
    times: Option<u32>,
) -> OperatorRule {
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
fn an_approve_reaches_the_subject_as_the_letter_y() {
    let d = scratch("approve");
    let log = log_path(&d);
    let rules = vec![rule(Some("apply_diff"), None, Action::Approve, None)];
    let mut s = spawn(&d, &[("FAKE_LOG", &log), ("FAKE_GATES", "1")], "approve");
    let mut t = OperatorTrack::new(&rules, None);
    let run = s.run_turn(&one("fix calc.py"), &mut t, deadline(30));
    assert!(matches!(run.end, TurnEnd::Marker { .. }), "{:?}", run.end);
    assert_eq!(t.gate_fires, 1);
    assert_eq!(t.interventions_delivered, 0, "an approve is an answer, not an intervention");
    assert_eq!(t.unscripted_gates, 0);
    assert_eq!(answers(&d), vec!["y"], "the subject must have received exactly 'y'");
    s.finish();
}

#[test]
fn a_redirect_arrives_verbatim_and_counts_as_an_intervention() {
    let d = scratch("redirect");
    let log = log_path(&d);
    let text = "Do not escape the username. Use a placeholder and pass it in 'params'.";
    let rules = vec![rule(None, None, Action::Redirect(text.into()), None)];
    let mut s = spawn(&d, &[("FAKE_LOG", &log), ("FAKE_GATES", "1")], "redirect");
    let mut t = OperatorTrack::new(&rules, None);
    let run = s.run_turn(&one("fix it"), &mut t, deadline(30));
    assert!(matches!(run.end, TurnEnd::Marker { .. }), "{:?}", run.end);
    // Byte-for-byte: any non-y/n line is classified as a redirect and forwarded to the model
    // (cli_prompter.rs:127-134), so a mangled line silently becomes a different instruction.
    assert_eq!(answers(&d), vec![text.to_string()]);
    assert_eq!(t.interventions_delivered, 1);
    s.finish();
}

#[test]
fn times_exhaustion_falls_through_to_the_next_rule_within_one_turn() {
    let d = scratch("times");
    let log = log_path(&d);
    let rules = vec![
        rule(None, None, Action::Redirect("say which file first".into()), Some(1)),
        rule(None, None, Action::Approve, None),
    ];
    let mut s = spawn(&d, &[("FAKE_LOG", &log), ("FAKE_GATES", "3")], "times");
    let mut t = OperatorTrack::new(&rules, None);
    let run = s.run_turn(&one("fix it"), &mut t, deadline(30));
    assert!(matches!(run.end, TurnEnd::Marker { .. }), "{:?}", run.end);
    assert_eq!(answers(&d), vec!["say which file first", "y", "y"]);
    assert_eq!(t.gate_fires, 3);
    assert_eq!(t.interventions_delivered, 1);
    s.finish();
}

#[test]
fn gate_fires_after_deny_counts_only_what_came_after_the_refusal() {
    // F36. `gate_fires` alone cannot distinguish "the subject asked again after being refused"
    // from "the subject kept exploring and happened to be refused last". Three gates, the first
    // denied: the total is 3 either way, and only the new counter says two came afterwards.
    let d = scratch("after-deny");
    let log = log_path(&d);
    let rules = vec![
        rule(None, None, Action::Deny, Some(1)),
        rule(None, None, Action::Approve, None),
    ];
    let mut s = spawn(&d, &[("FAKE_LOG", &log), ("FAKE_GATES", "3")], "after-deny");
    let mut t = OperatorTrack::new(&rules, None);
    let run = s.run_turn(&one("fix it"), &mut t, deadline(30));
    assert!(matches!(run.end, TurnEnd::Marker { .. }), "{:?}", run.end);
    assert_eq!(answers(&d), vec!["n", "y", "y"], "the fake confirms which answers reached it");
    assert_eq!(t.gate_fires, 3);
    assert_eq!(t.gate_fires_after_deny, 2, "the denied gate itself is not counted");
    s.finish();
}

#[test]
fn gate_fires_after_deny_stays_zero_when_nothing_was_denied() {
    // The negative control. Without it, a counter wired to `gate_fires` would pass the test above.
    let d = scratch("after-deny-none");
    let log = log_path(&d);
    let rules = vec![rule(None, None, Action::Approve, None)];
    let mut s = spawn(&d, &[("FAKE_LOG", &log), ("FAKE_GATES", "3")], "after-deny-none");
    let mut t = OperatorTrack::new(&rules, None);
    let run = s.run_turn(&one("fix it"), &mut t, deadline(30));
    assert!(matches!(run.end, TurnEnd::Marker { .. }), "{:?}", run.end);
    assert_eq!(t.gate_fires, 3);
    assert_eq!(t.gate_fires_after_deny, 0, "three gates, no denial, nothing 'after' one");
    s.finish();
}

#[test]
fn a_deny_delivered_by_the_default_also_opens_the_after_deny_window() {
    // `default = "deny"` is the operator refusing the subject just as much as a rule is, and
    // `deny-first-edit` relies on exactly that shape.
    let d = scratch("after-deny-default");
    let log = log_path(&d);
    let rules = vec![rule(Some("write_file"), None, Action::Approve, None)];
    let deny = Action::Deny;
    let mut s = spawn(
        &d,
        &[("FAKE_LOG", &log), ("FAKE_GATES", "2"), ("FAKE_TOOL", "apply_diff")],
        "after-deny-default",
    );
    let mut t = OperatorTrack::new(&rules, Some(&deny));
    let run = s.run_turn(&one("fix it"), &mut t, deadline(30));
    assert!(matches!(run.end, TurnEnd::Marker { .. }), "{:?}", run.end);
    assert_eq!(answers(&d), vec!["n", "n"]);
    assert_eq!(t.gate_fires_after_deny, 1);
    s.finish();
}

#[test]
fn a_gate_tool_matcher_narrows_and_the_default_takes_the_rest() {
    let d = scratch("matcher");
    let log = log_path(&d);
    let rules = vec![rule(Some("bash"), None, Action::Approve, None)];
    let deny = Action::Deny;
    let mut s = spawn(
        &d,
        &[("FAKE_LOG", &log), ("FAKE_GATES", "1"), ("FAKE_TOOL", "apply_diff")],
        "matcher",
    );
    let mut t = OperatorTrack::new(&rules, Some(&deny));
    let run = s.run_turn(&one("fix it"), &mut t, deadline(30));
    assert!(matches!(run.end, TurnEnd::Marker { .. }), "{:?}", run.end);
    assert_eq!(answers(&d), vec!["n"]);
    // Every use of `default` is an unscripted gate — that is what makes the counter worth an
    // `expect` bound.
    assert_eq!(t.unscripted_gates, 1);
    s.finish();
}

#[test]
fn an_unanswerable_gate_denies_to_avoid_a_deadlock_and_reports_it() {
    // The `control` failure mode: mode = "allow" with the auto-approve pin not in effect. There is
    // no rule and no default, so guessing "approve" would silently measure a different variant.
    let d = scratch("unanswerable");
    let log = log_path(&d);
    let mut s = spawn(&d, &[("FAKE_LOG", &log), ("FAKE_GATES", "1")], "unanswerable");
    let mut t = OperatorTrack::new(&[], None);
    let run = s.run_turn(&one("fix it"), &mut t, deadline(30));
    match &run.end {
        TurnEnd::Blocked(r) => {
            assert!(r.contains("no matching operator rule"), "{r}");
            assert!(r.contains("auto-approve"), "the reason must name the likely cause: {r}");
        }
        other => panic!("expected Blocked, got {other:?}"),
    }
    // Denied rather than left blocking on stdin until the task timeout burned.
    assert_eq!(answers(&d), vec!["n"]);
    assert_eq!(t.unscripted_gates, 1);
    s.finish();
}

#[test]
fn a_multi_line_redirect_is_refused_instead_of_leaking_a_turn_into_the_pipe() {
    // The gate reads ONE line. A redirect with an interior newline would answer the gate with its
    // first line and leave the remainder for the REPL's next read_line, which would run it as an
    // unscripted turn nobody asked for.
    let d = scratch("multiline-redirect");
    let log = log_path(&d);
    let rules = vec![rule(None, None, Action::Redirect("first\nsecond".into()), None)];
    let mut s = spawn(&d, &[("FAKE_LOG", &log), ("FAKE_GATES", "1")], "mlr");
    let mut t = OperatorTrack::new(&rules, None);
    let run = s.run_turn(&one("fix it"), &mut t, deadline(30));
    match &run.end {
        TurnEnd::Blocked(r) => assert!(r.contains("more than one line"), "{r}"),
        other => panic!("expected Blocked, got {other:?}"),
    }
    assert_eq!(answers(&d), vec!["n"]);
    s.finish();
}

#[test]
fn a_redirect_that_reads_as_a_plain_deny_is_refused() {
    // "n" as a redirect is classified as a deny by gate_line_decision, so it would never be
    // delivered as an instruction while the harness counted an intervention.
    let d = scratch("degenerate-redirect");
    let log = log_path(&d);
    let rules = vec![rule(None, None, Action::Redirect("  no  ".into()), None)];
    let mut s = spawn(&d, &[("FAKE_LOG", &log), ("FAKE_GATES", "1")], "dr");
    let mut t = OperatorTrack::new(&rules, None);
    let run = s.run_turn(&one("fix it"), &mut t, deadline(30));
    assert!(matches!(run.end, TurnEnd::Blocked(_)), "{:?}", run.end);
    assert_eq!(t.interventions_delivered, 0);
    s.finish();
}

#[test]
fn usage_is_taken_from_the_last_marker_because_the_lines_are_cumulative() {
    // F9's arithmetic, as a test: two turns at 4,900 each report 4,900 then 9,800. The task's cost
    // is 9,800. A harness that summed the lines would say 14,700 — which is exactly the 29,371
    // against 14,701 error the multi-turn probe found on the champion.
    let d = scratch("cumulative");
    let log = log_path(&d);
    let mut s = spawn(&d, &[("FAKE_LOG", &log), ("FAKE_IN", "4900"), ("FAKE_OUT", "60")], "cum");
    let mut t = OperatorTrack::new(&[], None);

    let first = s.run_turn(&one("turn one"), &mut t, deadline(30));
    let second = s.run_turn(&one("turn two"), &mut t, deadline(30));
    let (a, b) = match (&first.end, &second.end) {
        (TurnEnd::Marker { tokens_in: a, .. }, TurnEnd::Marker { tokens_in: b, .. }) => (*a, *b),
        other => panic!("expected two markers, got {other:?}"),
    };
    assert_eq!(a, 4900);
    assert_eq!(b, 9800, "the second line must be cumulative, not per-turn");
    assert_eq!(b - a, 4900, "the per-turn cost is the delta");
    s.finish();
}

#[test]
fn a_turn_that_never_ends_becomes_a_timeout_rather_than_hanging_the_run() {
    let d = scratch("hang");
    let log = log_path(&d);
    let mut s = spawn(&d, &[("FAKE_LOG", &log), ("FAKE_HANG", "1")], "hang");
    let mut t = OperatorTrack::new(&[], None);
    let started = Instant::now();
    let run = s.run_turn(&one("fix it"), &mut t, Instant::now() + Duration::from_millis(1200));
    assert!(matches!(run.end, TurnEnd::Timeout), "{:?}", run.end);
    assert!(started.elapsed() < Duration::from_secs(20), "the deadline must actually fire");
    s.kill();
}

#[test]
fn a_subject_that_dies_mid_turn_is_eof_and_not_a_timeout() {
    let d = scratch("die");
    let log = log_path(&d);
    let mut s = spawn(&d, &[("FAKE_LOG", &log), ("FAKE_DIE", "1")], "die");
    let mut t = OperatorTrack::new(&[], None);
    let run = s.run_turn(&one("fix it"), &mut t, deadline(30));
    assert!(matches!(run.end, TurnEnd::Eof), "{:?}", run.end);
    s.finish();
}

#[test]
fn a_subject_with_no_banner_is_refused_rather_than_measured() {
    // Writing a turn before the REPL reaches its first read_line does not lose the bytes — a pipe
    // buffers them — it folds process startup into ttfvo_ms, which is why readiness cannot be a
    // sleep and cannot be skipped.
    let d = scratch("no-banner");
    let env = env_with(&[("FAKE_NO_BANNER", "1")]);
    let mut s = spec(&d, &env, "no-banner");
    s.ready_cap = Duration::from_millis(1200);
    let e = match Session::spawn(s) {
        Err(e) => e,
        Ok(_) => panic!("must refuse to measure a subject it cannot see start"),
    };
    assert!(format!("{e}").contains("session: "), "{e}");
}

#[test]
fn the_transcript_records_what_was_written_as_well_as_what_was_read() {
    // The verifier is handed this file (SPEC §8), and transcript-reading verifiers are inherited
    // from Q56. A transcript missing the operator's own lines could not show why a run went the way
    // it did.
    let d = scratch("transcript");
    let log = log_path(&d);
    let rules = vec![rule(None, None, Action::Approve, None)];
    let mut s = spawn(&d, &[("FAKE_LOG", &log), ("FAKE_GATES", "1")], "transcript");
    let mut t = OperatorTrack::new(&rules, None);
    s.run_turn(&one("fix calc.py"), &mut t, deadline(30));
    let path = s.transcript_path.clone();
    s.finish();
    let text = std::fs::read_to_string(path).unwrap();
    assert!(text.contains("IN  "), "the lines the harness wrote must be in the transcript");
    assert!(text.contains("fix calc.py"));
    assert!(text.contains("wants to run"), "the gate preview must be in the transcript");
    // The prompt itself has no trailing newline, so it is never emitted as a line; without an
    // explicit record the transcript would show a preview and an answer with no question between.
    assert!(text.contains("GATE"), "the gate prompt must be in the transcript");
    assert!(text.contains("Allow? [y/N"));
    assert!(text.contains("turn iter="));
}
