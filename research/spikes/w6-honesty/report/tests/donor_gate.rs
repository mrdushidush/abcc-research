//! Claudette's build/test gate, ported verbatim and run over real captures.
//!
//! Of the three donors this is the one that gets the shape right: `classify_tests`
//! (`crates/claudette/src/tools/quality.rs:458-502` at `af3f804`) returns
//! `Option<bool>`, separates "timed out" from "could not run" from "failed", and
//! even reads pytest's exit 5 for *no tests collected*. It is the successor of
//! the thing §11 complains about, and the closest any donor comes to what item 8
//! asks for.
//!
//! So the question worth executing is the narrow one: what does it return for a
//! run that ended green having measured nothing?
//!
//! `classify_tests`, `parse_cargo_counts` and `parse_pytest_counts` below are
//! copied byte-for-byte from the donor. The two helpers they call for message
//! text only -- `summarize_test_failures` and `tail` -- are stubbed, because the
//! `Option<bool>` is what is under test and neither helper can change it.
//!
//! Inputs are `../captured/`, written by `cargo_endings.py` and `v1_parser.py`
//! from real runs, with the exit status the OS returned.

use std::fs;
use std::path::{Path, PathBuf};

// ─── donor types, verbatim (test_runner.rs:11-20) ───────────────────────────

#[derive(Debug, Clone)]
pub struct CommandResult {
    pub success: bool,
    pub stdout: String,
    pub stderr: String,
    pub timed_out: bool,
    pub exit_code: Option<i32>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[allow(dead_code)] // Npm and Go are in the donor enum; neither is captured here.
enum Framework {
    Cargo,
    Npm,
    Pytest,
    Go,
}

// ─── donor logic, verbatim (quality.rs:458-502, 887-912, 957-979) ───────────

fn summarize_test_failures(_f: Framework, _s: &str) -> String {
    "<message text, stubbed>".to_string()
}

fn tail(s: &str, n: usize) -> String {
    s.chars().rev().take(n).collect::<String>().chars().rev().collect()
}

fn parse_cargo_counts(s: &str) -> (u32, u32) {
    let mut passed = 0u32;
    let mut failed = 0u32;
    for line in s.lines() {
        let Some(rest) = line.strip_prefix("test result: ") else {
            continue;
        };
        let tokens: Vec<&str> = rest.split([' ', ';']).filter(|t| !t.is_empty()).collect();
        for window in tokens.windows(2) {
            let Ok(n) = window[0].parse::<u32>() else {
                continue;
            };
            let next = window[1].trim_end_matches(';');
            if next.starts_with("passed") {
                passed += n;
            } else if next.starts_with("failed") {
                failed += n;
            }
        }
    }
    (passed, failed)
}

fn parse_pytest_counts(s: &str) -> (u32, u32) {
    let mut passed = 0u32;
    let mut failed = 0u32;
    for line in s.lines().rev() {
        if line.contains(" passed") || line.contains(" failed") {
            let mut tokens = line.split_whitespace().peekable();
            while let Some(t) = tokens.next() {
                if let Ok(n) = t.parse::<u32>() {
                    match tokens.peek() {
                        Some(&w) if w.starts_with("passed") => passed += n,
                        Some(&w) if w.starts_with("failed") => failed += n,
                        _ => {}
                    }
                }
            }
            if passed > 0 || failed > 0 {
                break;
            }
        }
    }
    (passed, failed)
}

fn classify_tests(
    framework: Framework,
    result: &CommandResult,
    combined: &str,
    passed: u32,
    failed: u32,
    lines: &mut Vec<String>,
) -> Option<bool> {
    if result.timed_out {
        lines.push("tests: timed out (not counted as a failure)".to_string());
        return None;
    }
    if result.exit_code.is_none() {
        lines.push(
            "tests: could not run the test command (is the test tool installed?) — tests skipped"
                .to_string(),
        );
        return None;
    }
    if failed > 0 {
        lines.push(format!(
            "tests: {failed} failed, {passed} passed:\n{}",
            summarize_test_failures(framework, combined)
        ));
        return Some(false);
    }
    if result.success {
        lines.push(format!("tests: {passed} passed"));
        return Some(true);
    }
    // pytest exit 5 = "no tests collected" — advisory, not a failure.
    if framework == Framework::Pytest && result.exit_code == Some(5) {
        lines.push("tests: no tests collected (nothing to verify)".to_string());
        return None;
    }
    lines.push(format!(
        "tests: command exited {:?} with no parseable test results (build error in the \
         test target or a harness failure):\n{}",
        result.exit_code,
        tail(combined, 1200)
    ));
    Some(false)
}

// ─── the harness ────────────────────────────────────────────────────────────

fn captured_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("spike dir")
        .join("captured")
}

fn load(slug: &str) -> (i32, String) {
    let dir = captured_dir();
    let out = fs::read_to_string(dir.join(format!("{slug}.txt")))
        .unwrap_or_else(|e| panic!("{slug}.txt — run cargo_endings.py / v1_parser.py first: {e}"));
    let exit: i32 = fs::read_to_string(dir.join(format!("{slug}.exit")))
        .expect("exit file")
        .trim()
        .parse()
        .expect("exit code");
    (exit, out)
}

fn run(framework: Framework, slug: &str) -> (Option<bool>, Vec<String>) {
    let (exit, out) = load(slug);
    let result = CommandResult {
        success: exit == 0,
        stdout: out.clone(),
        stderr: String::new(),
        timed_out: false,
        exit_code: Some(exit),
    };
    let (passed, failed) = match framework {
        Framework::Cargo => parse_cargo_counts(&out),
        Framework::Pytest => parse_pytest_counts(&out),
        _ => (0, 0),
    };
    let mut lines = Vec::new();
    let verdict = classify_tests(framework, &result, &out, passed, failed, &mut lines);
    (verdict, lines)
}

#[test]
fn the_successors_gate_passes_a_crate_with_no_tests() {
    let (verdict, lines) = run(Framework::Cargo, "cargo__no-tests-at-all");
    println!("cargo, no tests at all -> {verdict:?}  {lines:?}");
    // The line is honest and the verdict is a pass: `cargo test` on a crate with
    // no tests exits 0, so `result.success` is true and the zero never reaches a
    // decision. This is §11's defect surviving into the best of the three donors.
    assert_eq!(verdict, Some(true));
    assert!(lines.iter().any(|l| l == "tests: 0 passed"), "{lines:?}");
}

#[test]
fn the_successors_gate_gets_the_pytest_no_collect_case_right() {
    let (verdict, lines) = run(Framework::Pytest, "pytest__nothing-to-collect");
    println!("pytest, nothing to collect -> {verdict:?}  {lines:?}");
    // exit 5 is read, and the answer is neither pass nor fail. This is the rung
    // 2.0 keeps, generalised: ask the process, not the prose.
    assert_eq!(verdict, None);
    assert!(lines.iter().any(|l| l.contains("no tests collected")), "{lines:?}");
}

#[test]
fn the_successors_gate_separates_a_broken_build_from_a_red_suite_only_by_text() {
    let (red, _) = run(Framework::Cargo, "cargo__3-of-3-fail");
    let (broken, lines) = run(Framework::Cargo, "cargo__does-not-compile");
    println!("cargo, does not compile -> {broken:?}  {lines:?}");
    // Both are `Some(false)`, and cargo exits 101 for both, so the only thing
    // that distinguishes "three tests failed" from "the test target does not
    // exist" is whether a `test result:` line was printed at all.
    assert_eq!(red, Some(false));
    assert_eq!(broken, Some(false));
    assert!(
        lines.iter().any(|l| l.contains("no parseable test results")),
        "{lines:?}"
    );
}

#[test]
fn the_successors_count_parsers_are_order_free_where_v1s_is_not() {
    // Real pytest prints `2 failed, 1 passed in 0.30s`. v1's regex requires
    // `passed` first and reports 2 run / 0 passed; Claudette pairs each integer
    // with the word after it and gets 1 and 2.
    let (_, out) = load("pytest__1-passes_2-fail");
    assert_eq!(parse_pytest_counts(&out), (1, 2));
    let (_, out) = load("cargo__1-passes_2-fail");
    assert_eq!(parse_cargo_counts(&out), (1, 2));
}
