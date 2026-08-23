//! W6 item 5 probe — Claudette's four-language build+test gate, on trees that
//! differ only in which language they are written in.
//!
//! `run_build_and_tests` (claudette `af3f804`,
//! `crates/claudette/src/tools/quality.rs:344-404`) is the successor's
//! deterministic gate: detect the framework from a marker file, run the build
//! step, run the suite, and return `Option<bool>` for each so that "could not
//! run" is advisory rather than a failure. It is `pub(crate)`, so the parts
//! under test are **vendored verbatim below** with their line numbers, and the
//! subprocesses are spawned from Rust — which is itself part of the question,
//! because a language binding on Windows is a binding to whatever `where`
//! finds.
//!
//! One tree per (framework × state), where state is: a project with no tests, a
//! project whose suite passes, and a project whose suite fails. Plus the
//! polyglot case — two languages in one repo — for the detector.
//!
//! Output: JSON on stdout.

use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

// ────────────────────────── vendored from quality.rs ──────────────────────────

/// `quality.rs:75-102`
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Framework {
    Cargo,
    Npm,
    Pytest,
    Go,
}

impl Framework {
    fn label(self) -> &'static str {
        match self {
            Self::Cargo => "cargo",
            Self::Npm => "npm",
            Self::Pytest => "pytest",
            Self::Go => "go",
        }
    }
}

/// `quality.rs:136-152`, minus the `CLAUDETTE_WORKSPACE` boundary walk (issue
/// #176), which does not change the answer for a tree probed at its own root.
fn detect_framework(start: &Path) -> Option<Framework> {
    let mut current = Some(start);
    while let Some(dir) = current {
        if dir.join("Cargo.toml").exists() {
            return Some(Framework::Cargo);
        }
        if dir.join("package.json").exists() {
            return Some(Framework::Npm);
        }
        if dir.join("pytest.ini").exists() || dir.join("pyproject.toml").exists() {
            return Some(Framework::Pytest);
        }
        if dir.join("go.mod").exists() {
            return Some(Framework::Go);
        }
        current = dir.parent();
    }
    None
}

/// The shape `run_command_with_timeout` returns (`test_runner.rs`): a failed
/// **spawn** is `exit_code: None`, which is what the classifier reads as
/// "toolchain not installed".
struct CommandResult {
    exit_code: Option<i32>,
    success: bool,
    stdout: String,
    stderr: String,
    timed_out: bool,
    spawn_error: Option<String>,
    ms: u128,
}

fn run(program: &str, args: &[&str], cwd: &Path) -> CommandResult {
    let t0 = std::time::Instant::now();
    match Command::new(program).args(args).current_dir(cwd).output() {
        Ok(o) => CommandResult {
            exit_code: o.status.code(),
            success: o.status.success(),
            stdout: String::from_utf8_lossy(&o.stdout).to_string(),
            stderr: String::from_utf8_lossy(&o.stderr).to_string(),
            timed_out: false,
            spawn_error: None,
            ms: t0.elapsed().as_millis(),
        },
        Err(e) => CommandResult {
            exit_code: None,
            success: false,
            stdout: String::new(),
            stderr: String::new(),
            timed_out: false,
            spawn_error: Some(e.to_string()),
            ms: t0.elapsed().as_millis(),
        },
    }
}

/// `quality.rs:410-453`
fn run_build_step(framework: Framework, dir: &Path, lines: &mut Vec<String>) -> Option<bool> {
    let (program, args): (&str, Vec<&str>) = match framework {
        Framework::Cargo => ("cargo", vec!["check", "--all-targets"]),
        Framework::Go => ("go", vec!["build", "./..."]),
        Framework::Pytest | Framework::Npm => return None,
    };
    let joined = args.join(" ");
    let r = run(program, &args, dir);
    if r.timed_out {
        lines.push(format!("build: `{program} {joined}` timed out (not counted as a failure)"));
        return None;
    }
    if r.exit_code.is_none() {
        lines.push(format!(
            "build: could not run `{program}` (is it installed?) — build check skipped"
        ));
        return None;
    }
    if r.success {
        lines.push(format!("build: `{program} {joined}` OK"));
        Some(true)
    } else {
        lines.push(format!("build: `{program} {joined}` FAILED"));
        Some(false)
    }
}

/// `quality.rs:222-263`
fn invoke(framework: Framework, cwd: &Path) -> CommandResult {
    match framework {
        Framework::Cargo => run("cargo", &["test"], cwd),
        Framework::Npm => run("npm", &["test"], cwd),
        Framework::Pytest => run("pytest", &[], cwd),
        Framework::Go => run("go", &["test", "./..."], cwd),
    }
}

/// `quality.rs:887-912`
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

/// `quality.rs:957-980`
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

/// `quality.rs:999-1010`
fn parse_go_counts(s: &str) -> (u32, u32) {
    let mut passed = 0u32;
    let mut failed = 0u32;
    for line in s.lines() {
        if line.starts_with("--- PASS") {
            passed += 1;
        } else if line.starts_with("--- FAIL") {
            failed += 1;
        }
    }
    (passed, failed)
}

/// `quality.rs:1028-1049`
fn parse_jest_counts(s: &str) -> (u32, u32) {
    // Lines look like `Tests:       2 failed, 10 passed, 12 total`.
    let mut passed = 0u32;
    let mut failed = 0u32;
    for line in s.lines() {
        if !line.trim_start().starts_with("Tests:") {
            continue;
        }
        let mut tokens = line.split([',', ' ', ':']).peekable();
        while let Some(t) = tokens.next() {
            if let Ok(n) = t.parse::<u32>() {
                match tokens.peek() {
                    Some(&"passed") => passed += n,
                    Some(&"failed") => failed += n,
                    _ => {}
                }
            }
        }
    }
    (passed, failed)
}

/// `quality.rs:458-497`
fn classify_tests(
    framework: Framework,
    result: &CommandResult,
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
        lines.push(format!("tests: {failed} failed, {passed} passed"));
        return Some(false);
    }
    if result.success {
        lines.push(format!("tests: {passed} passed"));
        return Some(true);
    }
    if framework == Framework::Pytest && result.exit_code == Some(5) {
        lines.push("tests: no tests collected (nothing to verify)".to_string());
        return None;
    }
    lines.push(format!(
        "tests: command exited {:?} with no parseable test results",
        result.exit_code
    ));
    Some(false)
}

/// `quality.rs:333-339`
fn is_hard_fail(build_ok: Option<bool>, tests_ok: Option<bool>) -> bool {
    build_ok == Some(false) || tests_ok == Some(false)
}

// ────────────────────────────── the trees ────────────────────────────────────

fn w(root: &Path, rel: &str, content: &str) {
    let p = root.join(rel);
    fs::create_dir_all(p.parent().unwrap()).expect("mkdir");
    fs::write(p, content).expect("write");
}

/// state: "no_tests" | "green" | "failing"
fn build_tree(root: &Path, framework: &str, state: &str) {
    let _ = fs::remove_dir_all(root);
    fs::create_dir_all(root).expect("mkdir");
    match framework {
        "cargo" => {
            w(root, "Cargo.toml", "[package]\nname = \"probe\"\nversion = \"0.1.0\"\nedition = \"2021\"\n\n[dependencies]\n");
            let tests = match state {
                "green" => "\n#[cfg(test)]\nmod t {\n    #[test]\n    fn ok() { assert_eq!(super::add(1, 2), 3); }\n}\n",
                "failing" => "\n#[cfg(test)]\nmod t {\n    #[test]\n    fn ok() { assert_eq!(super::add(1, 2), 4); }\n}\n",
                _ => "",
            };
            w(root, "src/lib.rs", &format!("pub fn add(a: i64, b: i64) -> i64 {{ a + b }}\n{tests}"));
        }
        "pytest" => {
            w(root, "pyproject.toml", "[project]\nname = \"probe\"\nversion = \"0.1.0\"\n");
            w(root, "mod_probe.py", "def add(a, b):\n    return a + b\n");
            match state {
                "green" => w(root, "test_probe.py", "from mod_probe import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n"),
                "failing" => w(root, "test_probe.py", "from mod_probe import add\n\n\ndef test_add():\n    assert add(1, 2) == 4\n"),
                _ => {}
            }
        }
        "npm" => {
            let pkg = match state {
                "no_tests" => "{\n \"name\": \"probe\",\n \"private\": true,\n \"version\": \"0.1.0\"\n}\n",
                _ => "{\n \"name\": \"probe\",\n \"private\": true,\n \"version\": \"0.1.0\",\n \"scripts\": { \"test\": \"node --test\" }\n}\n",
            };
            w(root, "package.json", pkg);
            w(root, "mod.js", "export function add(a, b) { return a + b; }\n");
            match state {
                "green" => w(root, "mod.test.js", "import { test } from 'node:test';\nimport assert from 'node:assert';\nimport { add } from './mod.js';\ntest('add', () => { assert.strictEqual(add(1, 2), 3); });\n"),
                "failing" => w(root, "mod.test.js", "import { test } from 'node:test';\nimport assert from 'node:assert';\nimport { add } from './mod.js';\ntest('add', () => { assert.strictEqual(add(1, 2), 4); });\n"),
                _ => {}
            }
        }
        "go" => {
            w(root, "go.mod", "module probe\n\ngo 1.22\n");
            w(root, "probe.go", "package probe\n\nfunc Add(a int, b int) int { return a + b }\n");
            match state {
                "green" => w(root, "probe_test.go", "package probe\n\nimport \"testing\"\n\nfunc TestAdd(t *testing.T) {\n\tif Add(1, 2) != 3 {\n\t\tt.Fatal(\"bad\")\n\t}\n}\n"),
                "failing" => w(root, "probe_test.go", "package probe\n\nimport \"testing\"\n\nfunc TestAdd(t *testing.T) {\n\tif Add(1, 2) != 4 {\n\t\tt.Fatal(\"bad\")\n\t}\n}\n"),
                _ => {}
            }
        }
        _ => panic!("framework"),
    }
}

fn main() {
    let trees = Path::new(env!("CARGO_MANIFEST_DIR")).join("../trees-frameworks");
    let mut rows: Vec<Value> = Vec::new();

    for framework in ["cargo", "pytest", "npm", "go"] {
        for state in ["no_tests", "green", "failing"] {
            let root: PathBuf = trees.join(format!("{framework}-{state}"));
            build_tree(&root, framework, state);
            let detected = detect_framework(&root);
            let mut lines: Vec<String> = Vec::new();
            let (build_ok, tests_ok, counts, test_run) = match detected {
                None => (None, None, (0, 0), None),
                Some(fw) => {
                    let b = run_build_step(fw, &root, &mut lines);
                    let r = invoke(fw, &root);
                    let combined = format!("{}\n{}", r.stdout, r.stderr);
                    let c = match fw {
                        Framework::Cargo => parse_cargo_counts(&combined),
                        Framework::Pytest => parse_pytest_counts(&combined),
                        Framework::Go => parse_go_counts(&combined),
                        Framework::Npm => parse_jest_counts(&combined),
                    };
                    let t = classify_tests(fw, &r, c.0, c.1, &mut lines);
                    (b, t, c, Some(r))
                }
            };
            let r = test_run.as_ref();
            rows.push(json!({
                "framework_dir": framework,
                "state": state,
                "detected": detected.map(|f| f.label()),
                "build_ok": build_ok,
                "tests_ok": tests_ok,
                "parsed_passed": counts.0,
                "parsed_failed": counts.1,
                "test_exit_code": r.and_then(|x| x.exit_code),
                "test_spawn_error": r.and_then(|x| x.spawn_error.clone()),
                "test_ms": r.map(|x| x.ms),
                "hard_fail": is_hard_fail(build_ok, tests_ok),
                "summary": lines.join(" | "),
                "test_stdout_tail": r.map(|x| x.stdout.chars().rev().take(300).collect::<String>().chars().rev().collect::<String>()),
            }));
            let last = rows.last().unwrap();
            eprintln!(
                "{:7} {:9} detected={:?} build={:?} tests={:?} hard_fail={} | {}",
                framework, state, last["detected"], build_ok, tests_ok,
                last["hard_fail"], lines.join(" | ")
            );
        }
    }

    // Polyglot: a Rust crate at the root with a Python package beside it. The
    // change under review is in the Python half; the detector never looks at it.
    let poly = trees.join("polyglot");
    build_tree(&poly, "cargo", "green");
    let pysub = poly.join("pysrc");
    fs::create_dir_all(&pysub).expect("mkdir");
    w(&poly, "pysrc/pyproject.toml", "[project]\nname = \"sub\"\nversion = \"0.1.0\"\n");
    w(&poly, "pysrc/mod_probe.py", "def add(a, b):\n    return a + b\n");
    w(&poly, "pysrc/test_probe.py", "from mod_probe import add\n\n\ndef test_add():\n    assert add(1, 2) == 4\n");
    let mut lines: Vec<String> = Vec::new();
    let fw = detect_framework(&poly).expect("detect");
    let b = run_build_step(fw, &poly, &mut lines);
    let r = invoke(fw, &poly);
    let combined = format!("{}\n{}", r.stdout, r.stderr);
    let c = parse_cargo_counts(&combined);
    let t = classify_tests(fw, &r, c.0, c.1, &mut lines);
    let polyglot = json!({
        "detected_at_root": fw.label(),
        "detected_in_python_subdir": detect_framework(&pysub).map(|f| f.label()),
        "build_ok": b,
        "tests_ok": t,
        "hard_fail": is_hard_fail(b, t),
        "note": "the failing python test is in pysrc/ and is never run",
        "summary": lines.join(" | "),
    });
    eprintln!("polyglot: {}", polyglot);

    // Can the four toolchain binaries be spawned at all from a Rust process on
    // this host? `npm` is `npm.ps1`/`npm.cmd`, `pytest` is a Scripts shim.
    let mut spawnable = serde_json::Map::new();
    for bin in ["cargo", "pytest", "npm", "go", "node", "python", "python3"] {
        let r = run(bin, &["--version"], Path::new("."));
        spawnable.insert(
            bin.to_string(),
            json!({
                "spawned": r.spawn_error.is_none(),
                "exit_code": r.exit_code,
                "error": r.spawn_error,
                "first_line": r.stdout.lines().next().unwrap_or("").to_string(),
            }),
        );
    }

    println!(
        "{}",
        json!({ "cases": rows, "polyglot": polyglot, "spawnable": spawnable })
    );
}
