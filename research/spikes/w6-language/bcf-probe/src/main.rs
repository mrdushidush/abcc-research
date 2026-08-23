//! W6 item 5 probe — BCF's per-language quality score, run through BCF's own
//! `verifier` module (path dependency on the pinned donor checkout `d6c1601`).
//!
//! Two questions:
//!   1. What score can a *perfect* file of each language reach? BCF's gate is a
//!      constant threshold over an average of these, so a per-language ceiling
//!      is a per-language handicap.
//!   2. Which extensions does `verify_project` even look at, and what does the
//!      average become when none of a project's files are in the list?
//!
//! Output: JSON on stdout.

use battlecommand_forge::verifier;
use std::path::{Path, PathBuf};

/// (fixture file, the `language` string BCF would pass to `verify_file`)
const CASES: &[(&str, &str)] = &[
    ("best.py", "python"),
    ("best.ts", "typescript"),
    ("best.js", "javascript"),
    ("best.rs", "rust"),
    ("best.go", "go"),
    ("best.cpp", "c++"),
    ("best.c", "c++"),
    ("best.java", "java"),
    ("best.rb", "ruby"),
];

/// BCF's own gate: `mission.rs:1139` and `quality_gate()` at `mission.rs:61`.
fn gate(complexity: u32) -> f32 {
    match complexity {
        0..=6 => 9.2,
        7..=8 => 8.5,
        _ => 8.0,
    }
}
fn final_score(critique: f32, verifier_score: f32) -> f32 {
    critique * 0.4 + verifier_score * 0.6
}

fn main() {
    let fixtures: PathBuf = Path::new(env!("CARGO_MANIFEST_DIR")).join("../fixtures");
    let mut out = Vec::new();

    for (file, lang) in CASES {
        let p = fixtures.join(file);
        let r = verifier::verify_file(&p, lang).expect("verify_file");
        // Best case the project average can reach for a project made only of
        // files like this one: the per-file score plus the maximum test bonus
        // (`verify_project`: pass_rate 1.0 → +2.0), clamped at 10.
        let with_tests = (r.score + 2.0f32).clamp(0.0, 10.0);
        out.push(serde_json::json!({
            "file": file,
            "language": lang,
            "score": r.score,
            "syntax_valid": r.syntax_valid,
            "lint_passed": r.lint_passed,
            "lint_issues": r.lint_issues,
            "has_tests": r.has_tests,
            "has_docstring": r.has_docstring,
            "has_error_handling": r.has_error_handling,
            "has_hardcoded_secrets": r.has_hardcoded_secrets,
            "avg_no_tests": r.score,
            "avg_tests_all_green": with_tests,
            "final_no_tests_perfect_critique": final_score(10.0, r.score),
            "final_tests_green_perfect_critique": final_score(10.0, with_tests),
            "gate_c1_c6": gate(1),
            "gate_c9_c10": gate(9),
            "passes_c1_c6_best_case": final_score(10.0, with_tests) >= gate(1),
            "passes_c9_c10_best_case": final_score(10.0, with_tests) >= gate(9),
        }));
    }

    // What does `verify_project` see? Run it over a directory holding one file
    // per language. `language` is the *mission* language; pass "rust" so the
    // Python test path (venv + pip install of 20 packages) is not triggered —
    // the question here is the per-file mapping and the average, not pytest.
    let pr = verifier::verify_project(&fixtures, "rust").expect("verify_project");
    let seen: Vec<&str> = pr.file_reports.iter().map(|(f, _)| f.as_str()).collect();

    // And the same call over a directory whose files are ALL outside the
    // extension list — the "language BCF has never heard of" case.
    let only_unknown = Path::new(env!("CARGO_MANIFEST_DIR")).join("../fixtures-unknown");
    std::fs::create_dir_all(&only_unknown).expect("mkdir");
    std::fs::copy(fixtures.join("best.rb"), only_unknown.join("best.rb")).expect("copy rb");
    std::fs::copy(fixtures.join("best.java"), only_unknown.join("best.java")).expect("copy java");
    let pr_unknown = verifier::verify_project(&only_unknown, "ruby").expect("verify_project");

    println!(
        "{}",
        serde_json::json!({
            "per_file": out,
            "project_mixed": {
                "files_scored": seen,
                "n_files_in_dir": std::fs::read_dir(&fixtures).unwrap().count(),
                "avg_score": pr.avg_score,
                "tests_run": pr.tests_run,
                "tests_passed": pr.tests_passed,
                "tests_failed": pr.tests_failed,
            },
            "project_unknown_language_only": {
                "files_scored": pr_unknown.file_reports.iter().map(|(f, _)| f.clone()).collect::<Vec<_>>(),
                "avg_score": pr_unknown.avg_score,
                "tests_run": pr_unknown.tests_run,
                "final_perfect_critique": final_score(10.0, pr_unknown.avg_score),
                "gate_lowest": gate(9),
            }
        })
    );
}
