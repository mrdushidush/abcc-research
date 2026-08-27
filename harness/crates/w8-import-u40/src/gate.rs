//! Stage 3 — run the gate (SPEC §9), for real, at import time.
//!
//! This suite can answer two of the three points rather than one, which is why the gate here is
//! stronger than `w8-import`'s and not weaker for being shorter:
//!
//! * **point 1 — does the verifier reject a non-answer?** Two pre-states are run, absence and a
//!   null-implementation stub, because absence alone only proves the import machinery raised
//!   (F19). Both must FAIL.
//! * **point 2 — does the verifier accept a correct answer?** The donor ships one: the `code`
//!   field. U100 had no reference solution and had to record `not_run` here.
//! * **point 3 — does it reject a *plausible wrong* answer?** No sham exists, so `not_run`, and
//!   `[selection]` is absent, which is how SPEC §9 says "this task is not in the sham set".
//!
//! A `broken` point is never dropped and never quietly fixed: the task is imported with
//! `quarantine = "with_baseline"`, which the loader enforces.

use crate::donor::DonorTask;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

/// A module that imports cleanly and implements nothing. Dunders must still raise, or the import
/// machinery reads a stub `__path__` and treats the module as a package. Lifted from
/// `w8-import/src/gate.rs`, deliberately byte-identical: the two suites' point 1 must mean the
/// same thing.
const STUB_PY: &str = "def __getattr__(name):\n\
                       \x20   if name.startswith(\"__\") and name.endswith(\"__\"):\n\
                       \x20       raise AttributeError(name)\n\
                       \x20   def _stub(*a, **k):\n\
                       \x20       return None\n\
                       \x20   return _stub\n";

/// The donor's `resetSystem` (`ollama-stress-test-40.js:362`) runs
/// `touch /app/workspace/tasks/__init__.py` before every campaign, so `tasks/` is a real package
/// in the pre-state of all 40 tasks. That file is this suite's fixture — the one donor artifact
/// the landing plan's "no fixtures" reading missed, because it lives in the harness rather than in
/// a `BUGGY_FILES` map.
pub const FIXTURE_INIT: &str = "tasks/__init__.py";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Tier {
    Absent,
    Stub,
    Refsol,
}

impl Tier {
    pub fn name(self) -> &'static str {
        match self {
            Tier::Absent => "absent",
            Tier::Stub => "stub",
            Tier::Refsol => "refsol",
        }
    }
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
}

#[derive(Debug, Clone)]
pub struct GateResult {
    pub point1: &'static str,
    pub point2: &'static str,
    pub point3: &'static str,
    pub evidence: Vec<Evidence>,
    pub run: String,
}

impl GateResult {
    pub fn not_run(run: String) -> Self {
        GateResult { point1: "not_run", point2: "not_run", point3: "not_run", evidence: Vec::new(), run }
    }
    /// The loader's rule: a `broken` point and a clean disposition cannot both be true.
    pub fn quarantine(&self) -> bool {
        [self.point1, self.point2, self.point3].contains(&"broken")
    }
}

pub struct Interpreters {
    pub bash: String,
    pub python: String,
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

impl Interpreters {
    /// Resolve both by **running** each candidate, never by looking it up — the same probe
    /// `w8-import/src/gate.rs:153` uses, and for the same two measured reasons: on this host
    /// `bash` on PATH is `C:\WINDOWS\system32\bash.exe`, the WSL launcher, which fails with a
    /// WSL configuration error before it ever reads the script; and `python3` is a Microsoft
    /// Store alias shim that prints an advert and exits 9009.
    pub fn resolve() -> Result<Interpreters, String> {
        let bash = std::env::var("W8_BASH")
            .ok()
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
                .map(|s| s.to_string()),
            )
            .find(|c| executes(c, &["-c", "exit 0"]))
            .ok_or(
                "no working bash found. Tried $W8_BASH, Git Bash, /bin/bash, /usr/bin/bash and \
                 `bash` on PATH, executing each. On Windows, `bash` on PATH is usually the WSL \
                 launcher; set W8_BASH to Git Bash.",
            )?;
        let python = std::env::var("PYTHON")
            .ok()
            .into_iter()
            .chain(["python3", "python"].iter().map(|s| s.to_string()))
            .find(|c| executes(c, &["-c", ""]))
            .ok_or("no working python found. Tried $PYTHON, python3 and python, executing each.")?;
        Ok(Interpreters { bash, python })
    }
}

fn scratch(id: &str, tier: Tier) -> std::io::Result<PathBuf> {
    let p = std::env::temp_dir().join(format!("w8-import-u40-{id}-{}", tier.name()));
    if p.exists() {
        fs::remove_dir_all(&p)?;
    }
    fs::create_dir_all(&p)?;
    Ok(p)
}

fn materialise(dir: &Path, task: &DonorTask, tier: Tier) -> std::io::Result<()> {
    let init = dir.join(FIXTURE_INIT);
    fs::create_dir_all(init.parent().expect("tasks/"))?;
    fs::write(&init, "")?;
    let artifact = dir.join(&task.artifact);
    match tier {
        Tier::Absent => Ok(()),
        Tier::Stub => fs::write(artifact, STUB_PY),
        Tier::Refsol => fs::write(artifact, format!("{}\n", task.code)),
    }
}

/// Run `verify.sh` the way SPEC §8 says the runner will.
fn run_verify(it: &Interpreters, script: &Path, work: &Path) -> (Verdict, String) {
    let transcript = work.join(".transcript");
    let _ = fs::write(&transcript, "");
    let out = Command::new(&it.bash)
        .arg(script)
        .arg(work)
        .arg(&transcript)
        .current_dir(work)
        .env("PYTHON", &it.python)
        .env("PYTHONIOENCODING", "utf-8")
        .env("PYTHONUTF8", "1")
        .stdin(std::process::Stdio::null())
        .output();
    let out = match out {
        Ok(o) => o,
        Err(e) => return (Verdict::Invalid, format!("could not run {}: {e}", it.bash)),
    };
    let stdout = String::from_utf8_lossy(&out.stdout);
    let Some(line) = stdout.lines().find(|l| l.trim_start().starts_with("RESULT:")) else {
        let err = String::from_utf8_lossy(&out.stderr);
        return (Verdict::Invalid, format!("no RESULT: line; stderr: {}", first_line(&err)));
    };
    let body = line.trim_start().trim_start_matches("RESULT:").trim();
    let (word, detail) = body.split_once(char::is_whitespace).unwrap_or((body, ""));
    let verdict = match word {
        "PASS" => Verdict::Pass,
        "FAIL" => Verdict::Fail,
        _ => Verdict::Invalid,
    };
    (verdict, detail.trim().to_string())
}

fn first_line(s: &str) -> String {
    s.lines().next().unwrap_or("").trim().to_string()
}

/// Run all three tiers for one task and score the two points this suite can answer.
pub fn run(it: &Interpreters, task: &DonorTask, script: &Path, run_label: &str) -> GateResult {
    let mut evidence = Vec::new();
    let mut verdicts = Vec::new();
    for tier in [Tier::Absent, Tier::Stub, Tier::Refsol] {
        let point = if tier.wants_pass() { 2 } else { 1 };
        let (verdict, detail) = match scratch(&task.id, tier).and_then(|d| {
            materialise(&d, task, tier)?;
            Ok(d)
        }) {
            Ok(d) => {
                let r = run_verify(it, script, &d);
                let _ = fs::remove_dir_all(&d);
                r
            }
            Err(e) => (Verdict::Invalid, format!("could not materialise the {} tier: {e}", tier.name())),
        };
        verdicts.push((tier, verdict));
        evidence.push(Evidence { point, tier, verdict, detail });
    }

    let verdict_of = |t: Tier| verdicts.iter().find(|(x, _)| *x == t).map(|(_, v)| *v).unwrap();
    let point1 = match (verdict_of(Tier::Absent), verdict_of(Tier::Stub)) {
        (Verdict::Fail, Verdict::Fail) => "sound",
        (Verdict::Invalid, _) | (_, Verdict::Invalid) => "inconclusive",
        _ => "broken",
    };
    let point2 = match verdict_of(Tier::Refsol) {
        Verdict::Pass => "sound",
        Verdict::Fail => "broken",
        Verdict::Invalid => "inconclusive",
    };
    GateResult { point1, point2, point3: "not_run", evidence, run: run_label.to_string() }
}
