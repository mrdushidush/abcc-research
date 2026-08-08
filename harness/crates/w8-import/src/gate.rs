//! Stage 3 — the import gate (SPEC §9), run against the **rewritten** verifier.
//!
//! ```text
//! gate(task) := verify(pre_state)        == FAIL
//!            && verify(fixture + refsol) == PASS
//!            && verify(fixture + sham)   == FAIL
//! ```
//!
//! Every input is a wrong answer, so every one must be rejected.
//!
//! Point 1's pre-state is a **null-implementation stub**, not the absent artifact (F19). Running
//! a verifier against an empty workspace misses `fix_path_traversal` entirely, because its
//! import raises before reaching the swallowed `assert`; the stub makes the import succeed and
//! exposes the defect. Same cost, strictly stronger. The cheap gate asks *"does the verifier
//! notice a no-op"*, not *"does it notice absence"* — and it runs on all 90 because it is
//! mechanical.
//!
//! Points 2 and 3 need authored artifacts, so they run only for tasks that already ship a
//! `refsol/` or `sham/` on disk. Absent, the point records `not_run` — never a silent pass.

use crate::rewrite::{Task, VClass, VerifyLang};
use std::collections::BTreeMap;
use std::ffi::OsString;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicU32, Ordering};

// ---------------------------------------------------------------------------------------------
// Generated pre-state artifacts (SPEC §9)
// ---------------------------------------------------------------------------------------------

/// A module that imports cleanly and implements nothing. Dunders must still raise, or the import
/// machinery reads a stub `__path__` and treats the module as a package.
const STUB_PY: &str = "def __getattr__(name):\n\
                       \x20   if name.startswith(\"__\") and name.endswith(\"__\"):\n\
                       \x20       raise AttributeError(name)\n\
                       \x20   def _stub(*a, **k):\n\
                       \x20       return None\n\
                       \x20   return _stub\n";

/// Same idea for node: every export resolves to a no-op. Symbol keys stay undefined so the
/// module does not accidentally look thenable or iterable to the runtime.
const STUB_NODE: &str = "module.exports = new Proxy({}, { get: (t, k) => \
                         (typeof k === 'symbol' ? undefined : function () { return undefined; }) \
                         });\n";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Tier {
    Absent,
    Stub,
    DonorFixture,
    Refsol,
    Sham,
}

impl Tier {
    pub fn name(self) -> &'static str {
        match self {
            Tier::Absent => "absent",
            Tier::Stub => "stub",
            Tier::DonorFixture => "donor_fixture",
            Tier::Refsol => "refsol",
            Tier::Sham => "sham",
        }
    }
    /// What SPEC §9 requires of this tier.
    fn wants_pass(self) -> bool {
        self == Tier::Refsol
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Verdict {
    Pass,
    Fail,
    Invalid,
}

impl Verdict {
    pub fn name(self) -> &'static str {
        match self {
            Verdict::Pass => "PASS",
            Verdict::Fail => "FAIL",
            Verdict::Invalid => "INVALID",
        }
    }
}

#[derive(Debug, Clone)]
pub struct Evidence {
    pub point: u8,
    pub tier: Tier,
    pub verdict: Verdict,
    pub detail: String,
    pub run: String,
}

#[derive(Debug, Clone)]
pub struct GateResult {
    pub point1: String,
    pub point2: String,
    pub point3: String,
    pub evidence: Vec<Evidence>,
}

impl GateResult {
    pub fn not_run() -> Self {
        GateResult {
            point1: "not_run".into(),
            point2: "not_run".into(),
            point3: "not_run".into(),
            evidence: Vec::new(),
        }
    }
    pub fn any_broken(&self) -> bool {
        [&self.point1, &self.point2, &self.point3]
            .iter()
            .any(|p| *p == "broken")
    }
}

// ---------------------------------------------------------------------------------------------
// Interpreters — probed by executing (SPEC §8)
// ---------------------------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct Interpreters {
    pub bash: PathBuf,
    pub python: String,
    pub node: Option<String>,
}

fn executes(prog: &str, args: &[&str]) -> bool {
    Command::new(prog)
        .args(args)
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .stdin(std::process::Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

/// Resolve `bash`, `python` and `node` by **running** each candidate, never by looking it up.
///
/// Two things on this host make the looking-up version wrong, and both were measured:
///
///   * `python3` is a Microsoft Store alias shim. It is on PATH, `command -v` finds it, and it
///     prints an advert and exits 9009 (F19's cousin, SPEC §8).
///   * `bash` on PATH resolves to `C:\WINDOWS\system32\bash.exe`, the WSL launcher, which on
///     this machine fails with a WSL configuration error before ever running the script.
pub fn probe() -> Result<Interpreters, String> {
    let bash_candidates: Vec<OsString> = std::env::var_os("W8_BASH")
        .into_iter()
        .chain(
            [
                "C:/Program Files/Git/bin/bash.exe",
                "C:/Program Files/Git/usr/bin/bash.exe",
                "/bin/bash",
                "/usr/bin/bash",
                "bash",
            ]
            .iter()
            .map(OsString::from),
        )
        .collect();
    let bash = bash_candidates
        .iter()
        .find(|c| executes(&c.to_string_lossy(), &["-c", "exit 0"]))
        .map(PathBuf::from)
        .ok_or_else(|| {
            "no working bash found. Tried $W8_BASH, Git Bash, /bin/bash, /usr/bin/bash and \
             `bash` on PATH, executing each. On Windows, `bash` on PATH is usually the WSL \
             launcher; set W8_BASH to Git Bash."
                .to_string()
        })?;

    let python = std::env::var("PYTHON")
        .ok()
        .into_iter()
        .chain(["python3", "python", "py"].iter().map(|s| s.to_string()))
        .find(|c| executes(c, &["-c", ""]))
        .ok_or_else(|| {
            "no working python found. Tried $PYTHON, python3, python, py, executing each. \
             Note `python3` may be the Microsoft Store alias shim, which resolves but does not \
             run (exit 9009)."
                .to_string()
        })?;

    let node = std::env::var("NODE")
        .ok()
        .into_iter()
        .chain(["node"].iter().map(|s| s.to_string()))
        .find(|c| executes(c, &["-e", ""]));

    Ok(Interpreters { bash, python, node })
}

// ---------------------------------------------------------------------------------------------
// Running one tier
// ---------------------------------------------------------------------------------------------

static SEQ: AtomicU32 = AtomicU32::new(0);

fn scratch_dir() -> std::io::Result<PathBuf> {
    let n = SEQ.fetch_add(1, Ordering::Relaxed);
    let p = std::env::temp_dir().join(format!("w8-import-{}-{n}", std::process::id()));
    if p.exists() {
        fs::remove_dir_all(&p)?;
    }
    fs::create_dir_all(&p)?;
    Ok(p)
}

/// The generated pre-state for the artifact. SPEC §9: a null implementation for code the
/// verifier imports, and an empty file for one it only opens.
fn stub_for(task: &Task) -> String {
    if task.vclass == VClass::StrMatch {
        // The verifier only reads this file as text, so "inert" means empty. An empty page is
        // also what F20 showed all 24 of these verifiers accept when it holds their substrings
        // in a comment — that is gate point 3's business, not point 1's.
        return String::new();
    }
    match task.artifact.rsplit('.').next().unwrap_or("") {
        "js" | "jsx" => STUB_NODE.to_string(),
        _ => STUB_PY.to_string(),
    }
}

/// Materialise the work dir for one tier. Dependencies are always real: stubbing a dependency
/// would make the tier's FAIL a fact about the missing dependency rather than about detection.
fn materialise(dir: &Path, task: &Task, tier: Tier, overlay: &BTreeMap<String, String>) -> std::io::Result<()> {
    for (name, body) in &task.fixture {
        if *name == task.artifact && tier != Tier::DonorFixture {
            continue; // the artifact is supplied by the tier, not by the fixture
        }
        fs::write(dir.join(name), body)?;
    }
    match tier {
        Tier::Absent => {}
        Tier::Stub => fs::write(dir.join(&task.artifact), stub_for(task))?,
        Tier::DonorFixture => {}
        Tier::Refsol | Tier::Sham => {
            for (name, body) in overlay {
                fs::write(dir.join(name), body)?;
            }
        }
    }
    Ok(())
}

/// Run `verify.sh` the way SPEC §8 says the runner will: `bash verify.sh <workdir> <transcript>`,
/// absolute paths, one RESULT: line on stdout, exit status ignored.
fn run_verify(it: &Interpreters, script: &Path, work: &Path) -> (Verdict, String) {
    let transcript = work.join(".transcript");
    let _ = fs::write(&transcript, "");
    let mut cmd = Command::new(&it.bash);
    cmd.arg(script)
        .arg(work)
        .arg(&transcript)
        .current_dir(work)
        .env("PYTHON", &it.python)
        .env("PYTHONIOENCODING", "utf-8")
        .env("PYTHONUTF8", "1")
        .stdin(std::process::Stdio::null());
    if let Some(n) = &it.node {
        cmd.env("NODE", n);
    }
    let out = match cmd.output() {
        Ok(o) => o,
        Err(e) => return (Verdict::Invalid, format!("could not run bash: {e}")),
    };
    let stdout = String::from_utf8_lossy(&out.stdout);

    // SPEC §8: the line is the verdict, and output with no RESULT: line is INVALID rather than
    // FAIL. That distinction is the reason this function ignores the exit status.
    let Some(line) = stdout.lines().find(|l| l.trim_start().starts_with("RESULT:")) else {
        let stderr = String::from_utf8_lossy(&out.stderr);
        let hint = stderr
            .lines()
            .chain(stdout.lines())
            .map(str::trim)
            .find(|l| !l.is_empty())
            .unwrap_or("no output at all");
        return (
            Verdict::Invalid,
            format!("no RESULT: line on stdout; first output was: {}", trunc(hint)),
        );
    };
    let rest = line.trim_start().trim_start_matches("RESULT:").trim();
    let (word, detail) = rest.split_once(' ').unwrap_or((rest, ""));
    let verdict = match word {
        "PASS" => Verdict::Pass,
        "FAIL" => Verdict::Fail,
        "INVALID" => Verdict::Invalid,
        other => {
            return (
                Verdict::Invalid,
                format!("unknown verdict word {other:?} on the RESULT: line"),
            );
        }
    };
    // The worked example records `detail = "AssertionError"`, not `"AssertionError: "`, so an
    // empty exception message is normalised away rather than recorded as punctuation.
    (verdict, trunc(detail.trim().trim_end_matches(':').trim()))
}

fn trunc(s: &str) -> String {
    let s = s.replace(['\n', '\r'], " ");
    if s.chars().count() <= 110 {
        s
    } else {
        let cut: String = s.chars().take(107).collect();
        format!("{cut}...")
    }
}

fn read_flat_dir(dir: &Path) -> BTreeMap<String, String> {
    let mut out = BTreeMap::new();
    if let Ok(rd) = fs::read_dir(dir) {
        for e in rd.flatten() {
            if e.path().is_file() {
                if let (Some(n), Ok(b)) = (
                    e.file_name().to_str().map(str::to_string),
                    fs::read(e.path()),
                ) {
                    out.insert(n, String::from_utf8_lossy(&b).into_owned());
                }
            }
        }
    }
    out
}

// ---------------------------------------------------------------------------------------------
// The gate
// ---------------------------------------------------------------------------------------------

/// Run the gate for one task. `existing` is the task's directory in the target corpus, if it
/// already exists — that is where authored `refsol/` and `sham/` come from, so points 2 and 3
/// are measured rather than assumed for any task that has them.
pub fn run(
    it: &Interpreters,
    task: &Task,
    existing: Option<&Path>,
    imported_at: &str,
) -> std::io::Result<GateResult> {
    let Some(verify) = &task.verify else {
        // Nothing to exercise: the donor wrote `validation: null` (F13). `not_run` is how the
        // spec says "not yet"; silence is not an option (SPEC §13 rule 7).
        return Ok(GateResult::not_run());
    };
    if verify.lang == VerifyLang::Node && it.node.is_none() {
        let mut g = GateResult::not_run();
        g.point1 = "inconclusive".into();
        g.evidence.push(Evidence {
            point: 1,
            tier: Tier::Stub,
            verdict: Verdict::Invalid,
            detail: "node not found on this host, so the verifier could not be run".into(),
            run: format!("w8-import, host, {imported_at}"),
        });
        return Ok(g);
    }

    // verify.sh has to exist on disk to be run, and it must be the emitted one.
    let staging = scratch_dir()?;
    let script = staging.join("verify.sh");
    fs::write(&script, &verify.script)?;

    let run_label = format!(
        "corpus/suites/u100/tasks/{}/verify.sh, host, {imported_at}",
        task.id
    );

    let mut tiers = vec![Tier::Absent, Tier::Stub];
    if task.fixture_is_donor {
        // Where the donor also supplies a real buggy fixture, that fixture is an *additional*
        // point-1 input and must also FAIL (SPEC §9).
        tiers.push(Tier::DonorFixture);
    }

    let mut evidence = Vec::new();
    let empty = BTreeMap::new();
    for tier in tiers {
        let work = scratch_dir()?;
        materialise(&work, task, tier, &empty)?;
        let (verdict, detail) = run_verify(it, &script, &work);
        let _ = fs::remove_dir_all(&work);
        evidence.push(Evidence {
            point: 1,
            tier,
            verdict,
            detail,
            run: run_label.clone(),
        });
    }
    let point1 = judge(&evidence, 1);

    // Points 2 and 3, from authored artifacts if the task already has them on disk.
    for (tier, sub, point) in [(Tier::Refsol, "refsol", 2u8), (Tier::Sham, "sham", 3u8)] {
        let Some(dir) = existing.map(|p| p.join(sub)).filter(|p| p.is_dir()) else {
            continue;
        };
        let overlay = read_flat_dir(&dir);
        if overlay.is_empty() {
            continue;
        }
        let work = scratch_dir()?;
        materialise(&work, task, tier, &overlay)?;
        let (verdict, detail) = run_verify(it, &script, &work);
        let _ = fs::remove_dir_all(&work);
        evidence.push(Evidence {
            point,
            tier,
            verdict,
            detail,
            run: run_label.clone(),
        });
    }

    let _ = fs::remove_dir_all(&staging);
    Ok(GateResult {
        point1,
        point2: judge(&evidence, 2),
        point3: judge(&evidence, 3),
        evidence,
    })
}

/// Run one verifier against an arbitrary overlay of work-dir files, on top of the fixture.
///
/// This exists for the positive control. Every gate tier expects FAIL, so a `verify.sh` that
/// could never emit PASS — a bad heredoc, a mis-quoted body, an interpreter that silently does
/// nothing — would score as 80 sound verifiers. Only a **right** answer that PASSes rules that
/// out, and the error class changing between the absent and stub tiers is corroboration, not
/// proof.
pub fn run_overlay(
    it: &Interpreters,
    task: &Task,
    overlay: &BTreeMap<String, String>,
) -> std::io::Result<(Verdict, String)> {
    let Some(verify) = &task.verify else {
        return Ok((Verdict::Invalid, "task has no verifier".into()));
    };
    if verify.lang == VerifyLang::Node && it.node.is_none() {
        return Ok((Verdict::Invalid, "node not found on this host".into()));
    }
    let staging = scratch_dir()?;
    let script = staging.join("verify.sh");
    fs::write(&script, &verify.script)?;
    let work = scratch_dir()?;
    materialise(&work, task, Tier::Refsol, overlay)?;
    let got = run_verify(it, &script, &work);
    let _ = fs::remove_dir_all(&work);
    let _ = fs::remove_dir_all(&staging);
    Ok(got)
}

/// SPEC §9's vocabulary: `sound` (the requirement held) · `broken` (a wrong answer was accepted)
/// · `inconclusive` (the failure could be platform noise rather than detection) · `not_run`.
fn judge(evidence: &[Evidence], point: u8) -> String {
    let mine: Vec<&Evidence> = evidence.iter().filter(|e| e.point == point).collect();
    if mine.is_empty() {
        return "not_run".into();
    }
    // INVALID is checked before PASS/FAIL: it means the verifier did not run, so nothing about
    // detection can be concluded either way.
    if mine.iter().any(|e| e.verdict == Verdict::Invalid) {
        return "inconclusive".into();
    }
    let held = mine.iter().all(|e| {
        if e.tier.wants_pass() {
            e.verdict == Verdict::Pass
        } else {
            e.verdict == Verdict::Fail
        }
    });
    if held { "sound".into() } else { "broken".into() }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ev(point: u8, tier: Tier, verdict: Verdict) -> Evidence {
        Evidence {
            point,
            tier,
            verdict,
            detail: String::new(),
            run: String::new(),
        }
    }

    #[test]
    fn point1_is_sound_only_when_every_wrong_answer_is_rejected() {
        let e = vec![
            ev(1, Tier::Absent, Verdict::Fail),
            ev(1, Tier::Stub, Verdict::Fail),
        ];
        assert_eq!(judge(&e, 1), "sound");
    }

    #[test]
    fn a_verifier_that_accepts_a_no_op_is_broken() {
        // This is fix_path_traversal: it rejects absence and accepts inertness, and the weaker
        // absent-only check would have called it sound (F19).
        let e = vec![
            ev(1, Tier::Absent, Verdict::Fail),
            ev(1, Tier::Stub, Verdict::Pass),
        ];
        assert_eq!(judge(&e, 1), "broken");
    }

    #[test]
    fn invalid_outranks_everything_because_nothing_ran() {
        let e = vec![
            ev(1, Tier::Absent, Verdict::Fail),
            ev(1, Tier::Stub, Verdict::Invalid),
        ];
        assert_eq!(judge(&e, 1), "inconclusive");
    }

    #[test]
    fn refsol_is_the_one_tier_that_must_pass() {
        assert_eq!(judge(&[ev(2, Tier::Refsol, Verdict::Pass)], 2), "sound");
        assert_eq!(judge(&[ev(2, Tier::Refsol, Verdict::Fail)], 2), "broken");
        // ...and a sham that passes is the F8 case.
        assert_eq!(judge(&[ev(3, Tier::Sham, Verdict::Pass)], 3), "broken");
        assert_eq!(judge(&[ev(3, Tier::Sham, Verdict::Fail)], 3), "sound");
    }

    #[test]
    fn a_missing_point_is_not_run_never_a_silent_pass() {
        assert_eq!(judge(&[], 3), "not_run");
    }

    #[test]
    fn stub_shape_follows_what_the_verifier_does_with_the_file() {
        // A python stub must keep dunders raising, or the import machinery treats the module as
        // a package.
        assert!(STUB_PY.contains("raise AttributeError"));
        // A node stub must leave symbol keys undefined so it does not look thenable.
        assert!(STUB_NODE.contains("typeof k === 'symbol'"));
    }
}
