//! W6 item 7 probe — what BCF's gate does with a DOCUMENTATION deliverable.
//!
//! `verifier::verify_project` maps extensions to languages at `verifier.rs:73-81`
//! and `_ => continue`s everything else, so a project whose deliverable is prose
//! contributes no file reports at all. Item 5 measured the consequence for a
//! language BCF has never heard of (F313); this runs the same code path with the
//! artifact the brief actually names, and with a real, good document.
//!
//! Output: JSON on stdout.

use battlecommand_forge::verifier;
use std::path::{Path, PathBuf};

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
    let repo: PathBuf = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../../..")
        .canonicalize()
        .expect("repo root");
    let tmp = std::env::temp_dir().join("w6-judge-bcf-doc");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).expect("mkdir");

    // A real, good document: the K suite's status lifecycle spec, plus a README
    // and a CHANGELOG, which is what a documentation mission actually delivers.
    let doc = repo.join("corpus/suites/k/tasks/finish_the_cancelled_status/fixture/docs/status_lifecycle.md");
    std::fs::copy(&doc, tmp.join("status_lifecycle.md")).expect("copy doc");
    std::fs::copy(repo.join("RESEARCH_BRIEF.md"), tmp.join("README.md")).expect("copy brief");
    std::fs::write(tmp.join("CHANGELOG.md"), "# Changelog\n\n## 4.2\n- `cancelled` status\n")
        .expect("write changelog");

    let pr = verifier::verify_project(&tmp, "markdown").expect("verify_project");
    let files: Vec<String> = std::fs::read_dir(&tmp)
        .unwrap()
        .map(|e| e.unwrap().file_name().to_string_lossy().to_string())
        .collect();

    // And the same call with `language = "python"`, since BCF takes the mission
    // language from a keyword scan of the prompt (F315) and defaults to python.
    let pr_py = verifier::verify_project(&tmp, "python").expect("verify_project");

    println!(
        "{}",
        serde_json::json!({
            "donor": "d6c1601",
            "files_in_dir": files,
            "as_markdown": {
                "files_scored": pr.file_reports.iter().map(|(f, _)| f.clone()).collect::<Vec<_>>(),
                "avg_score": pr.avg_score,
                "tests_run": pr.tests_run,
                "final_with_perfect_critique": final_score(10.0, pr.avg_score),
            },
            "as_python_the_default": {
                "files_scored": pr_py.file_reports.iter().map(|(f, _)| f.clone()).collect::<Vec<_>>(),
                "avg_score": pr_py.avg_score,
                "tests_run": pr_py.tests_run,
                "final_with_perfect_critique": final_score(10.0, pr_py.avg_score),
            },
            "gate_c1_c6": gate(1),
            "gate_c7_c8": gate(7),
            "gate_c9_plus": gate(9),
            "passes_lowest_gate_with_perfect_critique":
                final_score(10.0, pr.avg_score) >= gate(9),
        })
    );
    let _ = std::fs::remove_dir_all(&tmp);
}
