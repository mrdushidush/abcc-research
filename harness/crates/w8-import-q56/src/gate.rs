//! Stage 3 — the import gate, measured by executing (SPEC §9).
//!
//! Point 1: the pre-state must FAIL. **Here the pre-state is the donor's untouched fixture**, tier
//! `donor_fixture`, not §9's generated null-implementation stub. Every Q56 fixture compiles and
//! passes its visible happy-path tests while failing the hidden reviewer tests, which is exactly
//! the state the stub was invented to simulate for U100 — so the stronger input is the free one.
//!
//! Point 2: fixture + `refsol/` overlaid must PASS. Without it every tier expects FAIL and a
//! `verify.sh` incapable of ever printing PASS would score as a suite of sound verifiers. This is
//! F25's positive control, and here it needs no trick: the donor authored a reference solution for
//! all 56.
//!
//! Point 3 needs an authored sham and records `not_run` until step 4 writes one.

use crate::donor::DonorTask;
use std::collections::BTreeMap;
use std::path::Path;
use std::process::Command;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Verdict {
    Sound,
    Broken,
    Inconclusive,
    NotRun,
}

impl Verdict {
    pub fn as_str(self) -> &'static str {
        match self {
            Verdict::Sound => "sound",
            Verdict::Broken => "broken",
            Verdict::Inconclusive => "inconclusive",
            Verdict::NotRun => "not_run",
        }
    }
}

#[derive(Debug, Clone)]
pub struct Evidence {
    pub point: u8,
    pub tier: String,
    pub verdict: String,
    pub detail: String,
    pub run: String,
}

#[derive(Debug, Clone)]
pub struct GateResult {
    pub point1: Verdict,
    pub point2: Verdict,
    pub evidence: Vec<Evidence>,
}

impl GateResult {
    pub fn not_run() -> Self {
        GateResult { point1: Verdict::NotRun, point2: Verdict::NotRun, evidence: Vec::new() }
    }
    pub fn holds(&self) -> bool {
        self.point1 == Verdict::Sound && self.point2 == Verdict::Sound
    }
}

/// SPEC §8's parse, and the half of it that matters most: **output with no `RESULT:` line is
/// INVALID, never FAIL**. A misresolved interpreter makes a verifier print something unrelated and
/// exit 0, and scoring that as FAIL reports a broken harness as a hard task (F35).
fn classify(stdout: &str) -> (String, String) {
    match stdout.lines().rev().find(|l| l.trim_start().starts_with("RESULT:")) {
        None => ("INVALID".to_string(), format!("no RESULT: line. stdout={:?}", clip(stdout))),
        Some(l) => {
            let rest = l.trim_start().trim_start_matches("RESULT:").trim_start();
            let word = rest.split_whitespace().next().unwrap_or("");
            let msg = rest[word.len()..].trim().trim_start_matches('—').trim();
            match word {
                "PASS" | "FAIL" | "INVALID" => (word.to_string(), clip(msg)),
                other => ("INVALID".to_string(), format!("RESULT: carries {other:?}")),
            }
        }
    }
}

fn clip(s: &str) -> String {
    let one = s.replace(['\n', '\r'], " ");
    if one.chars().count() > 160 {
        one.chars().take(157).collect::<String>() + "..."
    } else {
        one
    }
}

/// Run `verify.sh` against a freshly materialised work dir. `overlay` is applied on top of the
/// fixture, which is how `refsol/` is layered in without ever being visible to a subject.
fn run_verify(
    bash: &str,
    scratch: &Path,
    tier: &str,
    verify_sh: &str,
    fixture: &BTreeMap<String, String>,
    overlay: &BTreeMap<String, String>,
) -> Result<(String, String), String> {
    let wd = scratch.join(tier);
    let _ = std::fs::remove_dir_all(&wd);
    std::fs::create_dir_all(&wd).map_err(|e| format!("{}: {e}", wd.display()))?;
    crate::emit::write_files(&wd, fixture)?;
    crate::emit::write_files(&wd, overlay)?;

    let script = scratch.join(format!("verify-{tier}.sh"));
    std::fs::write(&script, verify_sh).map_err(|e| format!("{}: {e}", script.display()))?;

    // `std::path::absolute`, never `canonicalize`: the latter yields a \\?\ UNC path on Windows
    // which bash cannot open, and that cost a whole run once (F35).
    let abs = |p: &Path| std::path::absolute(p).unwrap_or_else(|_| p.to_path_buf());
    let out = Command::new(bash)
        .arg(abs(&script))
        .arg(abs(&wd))
        .arg(abs(&scratch.join("transcript.log")))
        .output()
        .map_err(|e| format!("cannot run {bash}: {e}"))?;
    Ok(classify(&String::from_utf8_lossy(&out.stdout)))
}

/// Probe bash by executing it. On this host the `bash` on PATH is the WSL launcher, which fails
/// before running anything; Git Bash is what works. Looking at a name never establishes this.
pub fn find_bash() -> Result<String, String> {
    for cand in ["C:/Program Files/Git/bin/bash.exe", "bash"] {
        if let Ok(o) = Command::new(cand).arg("-c").arg("echo w8").output()
            && String::from_utf8_lossy(&o.stdout).trim() == "w8"
        {
            return Ok(cand.to_string());
        }
    }
    Err("no working bash: Git Bash at C:/Program Files/Git/bin/bash.exe is what works here; \
         the `bash` on PATH is the WSL launcher"
        .to_string())
}

pub fn run(
    bash: &str,
    scratch: &Path,
    task: &DonorTask,
    verify_sh: &str,
    today: &str,
) -> Result<GateResult, String> {
    let empty = BTreeMap::new();
    let mut ev = Vec::new();
    let run_note = format!("w8-import-q56, host, {today}");

    // ── Point 1: the untouched donor fixture must be rejected ────────────────
    let (v1, d1) = run_verify(bash, scratch, "donor_fixture", verify_sh, &task.fixture, &empty)?;
    ev.push(Evidence {
        point: 1,
        tier: "donor_fixture".into(),
        verdict: v1.clone(),
        detail: d1,
        run: run_note.clone(),
    });
    let point1 = match v1.as_str() {
        "FAIL" => Verdict::Sound,
        "PASS" => Verdict::Broken,
        _ => Verdict::Inconclusive,
    };

    // ── Point 2: fixture + refsol must be accepted ───────────────────────────
    let point2 = if task.refsol.is_empty() {
        Verdict::NotRun
    } else {
        let (v2, d2) = run_verify(bash, scratch, "refsol", verify_sh, &task.fixture, &task.refsol)?;
        ev.push(Evidence {
            point: 2,
            tier: "refsol".into(),
            verdict: v2.clone(),
            detail: d2,
            run: run_note,
        });
        match v2.as_str() {
            "PASS" => Verdict::Sound,
            "FAIL" => Verdict::Broken,
            _ => Verdict::Inconclusive,
        }
    };

    Ok(GateResult { point1, point2, evidence: ev })
}

#[cfg(test)]
pub mod tests {
    use super::*;
    use crate::donor::Row;

    pub fn sample_task() -> DonorTask {
        let mut fixture = BTreeMap::new();
        fixture.insert("Cargo.toml".to_string(), "[package]\n".to_string());
        let mut refsol = BTreeMap::new();
        refsol.insert("src/eval.rs".to_string(), "fn main() {}\n".to_string());
        DonorTask {
            row: Row {
                id: "Q08".into(),
                lang: "rust".into(),
                kind: "multi-file".into(),
                fixture_dir: "Q08".into(),
                timeout_s: 700,
                raw: "Q08\trust\tmulti-file\tQ08\t700".into(),
            },
            prompt: "This crate evaluates expressions. There's a bug.".into(),
            fixture,
            refsol,
            verify: "#!/usr/bin/env bash\n".into(),
        }
    }

    #[test]
    fn no_result_line_is_invalid_and_never_fail() {
        let (v, d) = classify("Python was not found; run without arguments to install\n");
        assert_eq!(v, "INVALID", "a broken harness must not read as a hard task (F35)");
        assert!(d.contains("no RESULT: line"));
    }

    #[test]
    fn the_last_result_line_wins_and_the_em_dash_is_not_part_of_the_message() {
        let (v, d) = classify("echo \"RESULT: PASS\"\nRESULT: FAIL — hidden tests failed: x\n");
        assert_eq!(v, "FAIL");
        assert_eq!(d, "hidden tests failed: x");
    }

    #[test]
    fn a_verifier_that_passes_its_own_untouched_fixture_is_broken_not_sound() {
        // The F8 shape: point 1 exists precisely to catch this, so the mapping must not be lenient.
        assert_eq!(
            match "PASS" {
                "FAIL" => Verdict::Sound,
                "PASS" => Verdict::Broken,
                _ => Verdict::Inconclusive,
            },
            Verdict::Broken
        );
    }
}
