//! Running `verify.sh`, and refusing to call a broken harness a hard task.
//!
//! SPEC §8: `bash verify.sh <workdir> <transcript>`, one `RESULT:` line on stdout, **exit status
//! ignored**. Output with no `RESULT:` line is `INVALID`, never `FAIL` — "the verifier did not run"
//! and "the artifact is wrong" are different facts, and the donor conflated them.
//!
//! Interpreters are probed **by executing**, never by looking, and the reason is a live host trap
//! rather than caution: Windows ships a Microsoft Store alias shim named `python3.exe` that sits on
//! `PATH`, satisfies `command -v`, prints an advert and exits 9009. `bash` on `PATH` is the WSL
//! launcher, which fails before running anything at all.
//!
//! **This is the second copy of that probe** — `w8-import/src/gate.rs:145-197` has the first, and it
//! is a binary crate, so sharing one function would mean giving the importer a library surface the
//! runner would then depend on wholesale. The two must agree: they read the same `W8_BASH` override
//! and try the same candidates in the same order, so a host fix applies to both. If they ever
//! diverge, the gate evidence recorded in the corpus and the verdicts produced here stop describing
//! the same verifier.

use std::ffi::OsString;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

use w8_corpus::RunVerdict;

#[derive(Debug, Clone)]
pub struct Verdict {
    pub verdict: RunVerdict,
    pub message: String,
}

/// Resolved by execution, never by lookup. `node` is optional: 24 U100 verifiers are python-only.
#[derive(Debug, Clone)]
pub struct Interpreters {
    pub bash: PathBuf,
    pub python: String,
    pub node: Option<String>,
}

fn executes(prog: &str, args: &[&str]) -> bool {
    Command::new(prog)
        .args(args)
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .stdin(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

/// Probe `bash`, `python` and `node` by running each candidate.
///
/// The candidate lists, the env-var overrides and the order are **deliberately identical** to
/// `w8-import/src/gate.rs:153-198`. That is the promise this module's header makes: the corpus's
/// recorded gate evidence and the verdicts produced here have to describe the same verifier
/// executed the same way, and the interpreter is part of "the same way". Found by running the first
/// version of this file, which left `${PYTHON:-python3}` to the environment and got the Microsoft
/// Store alias shim.
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
            "no working bash found. Tried $W8_BASH, Git Bash, /bin/bash, /usr/bin/bash and `bash` \
             on PATH, executing each. On Windows, `bash` on PATH is usually the WSL launcher; set \
             W8_BASH to Git Bash"
                .to_string()
        })?;

    let python = std::env::var("PYTHON")
        .ok()
        .into_iter()
        .chain(["python3", "python", "py"].iter().map(|s| (*s).to_string()))
        .find(|c| executes(c, &["-c", ""]))
        .ok_or_else(|| {
            "no working python found. Tried $PYTHON, python3, python, py, executing each. Note \
             `python3` may be the Microsoft Store alias shim, which resolves but does not run \
             (exit 9009)"
                .to_string()
        })?;

    let node = std::env::var("NODE")
        .ok()
        .into_iter()
        .chain(["node"].iter().map(|s| (*s).to_string()))
        .find(|c| executes(c, &["-e", ""]));

    Ok(Interpreters { bash, python, node })
}

/// SPEC §8: "Both arguments are absolute paths."
///
/// It says so for a reason this run demonstrated. The verifier's cwd is the work dir — so a donor
/// snippet's relative path resolves as it did in the container — and a *relative* script path is
/// then resolved against the work dir too, where it does not exist. The first version passed
/// `../corpus/suites/…/verify.sh` straight through and got
/// `No such file or directory` on stderr with nothing on stdout, which the SPEC §8 rule correctly
/// reported as INVALID rather than FAIL. `std::path::absolute` rather than `canonicalize`, because
/// canonicalize returns a `\\?\` UNC path on Windows and bash cannot open one.
fn absolute(p: &Path) -> PathBuf {
    std::path::absolute(p).unwrap_or_else(|_| p.to_path_buf())
}

/// Run one verifier.
pub fn run(it: &Interpreters, script: &Path, workdir: &Path, transcript: &Path) -> Verdict {
    let script = absolute(script);
    let workdir = absolute(workdir);
    let transcript = absolute(transcript);

    let mut cmd = Command::new(&it.bash);
    cmd.arg(&script)
        .arg(&workdir)
        .arg(&transcript)
        .current_dir(&workdir)
        // SPEC §8: interpreters resolve through the environment (`${PYTHON:-python3}`) so the same
        // task runs on the host and in a container. Passing the *probed* ones is what makes the
        // host half of that work.
        .env("PYTHON", &it.python)
        // The transcript is UTF-8 and the subject emits non-ASCII glyphs even under NO_COLOR, so a
        // transcript-reading verifier on a cp1252 console would raise on the read rather than on
        // the artifact.
        .env("PYTHONIOENCODING", "utf-8")
        .env("PYTHONUTF8", "1")
        .stdin(Stdio::null());
    if let Some(n) = &it.node {
        cmd.env("NODE", n);
    }
    let out = match cmd.output() {
        Ok(o) => o,
        Err(e) => {
            return Verdict {
                verdict: RunVerdict::Invalid,
                message: format!("could not run bash {}: {e}", script.display()),
            };
        }
    };
    classify(
        &String::from_utf8_lossy(&out.stdout),
        &String::from_utf8_lossy(&out.stderr),
    )
}

/// SPEC §8's parse. The **last** `RESULT:` line wins: a verifier that echoes its own source, or
/// prints a progress line before the verdict, must not be read off its first mention.
pub fn classify(stdout: &str, stderr: &str) -> Verdict {
    let line = stdout.lines().rev().find(|l| l.trim_start().starts_with("RESULT:"));
    match line {
        Some(l) => {
            let rest = l.trim_start().trim_start_matches("RESULT:").trim_start();
            let (word, msg) = match rest.split_once(char::is_whitespace) {
                Some((w, m)) => (w, m.trim()),
                None => (rest, ""),
            };
            match RunVerdict::parse(word) {
                Some(v) => Verdict { verdict: v, message: msg.to_string() },
                None => Verdict {
                    verdict: RunVerdict::Invalid,
                    message: format!(
                        "RESULT: line carries {word:?}, which is not one of {:?}",
                        RunVerdict::allowed()
                    ),
                },
            }
        }
        None => Verdict {
            verdict: RunVerdict::Invalid,
            message: format!(
                "no RESULT: line on stdout. stdout={:?} stderr={:?}",
                tail(stdout, 400),
                tail(stderr, 400)
            ),
        },
    }
}

fn tail(s: &str, n: usize) -> String {
    let t = s.trim();
    if t.chars().count() <= n {
        return t.to_string();
    }
    let skip = t.chars().count() - n;
    format!("…{}", t.chars().skip(skip).collect::<String>())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_three_verdicts_parse_with_their_messages() {
        let p = classify("RESULT: PASS donor assertions held\n", "");
        assert_eq!(p.verdict, RunVerdict::Pass);
        assert_eq!(p.message, "donor assertions held");

        assert_eq!(classify("RESULT: FAIL AssertionError\n", "").verdict, RunVerdict::Fail);
        assert_eq!(classify("RESULT: INVALID no python\n", "").verdict, RunVerdict::Invalid);
    }

    #[test]
    fn no_result_line_is_invalid_and_not_fail() {
        // The Store-shim case: an advert on stdout and exit 9009. Scoring it FAIL would report a
        // broken harness as a hard task.
        let v = classify("Python was not found; run without arguments to install\n", "");
        assert_eq!(v.verdict, RunVerdict::Invalid);
        assert!(v.message.contains("no RESULT: line"));
    }

    #[test]
    fn empty_output_is_invalid() {
        assert_eq!(classify("", "").verdict, RunVerdict::Invalid);
    }

    #[test]
    fn the_last_result_line_wins() {
        // A verifier that echoes its own source would otherwise be read off the copy in the echo.
        let v = classify("echo \"RESULT: PASS\"\nRESULT: FAIL real verdict\n", "");
        assert_eq!(v.verdict, RunVerdict::Fail);
        assert_eq!(v.message, "real verdict");
    }

    #[test]
    fn an_unknown_verdict_word_is_invalid_and_says_what_was_allowed() {
        let v = classify("RESULT: MAYBE hmm\n", "");
        assert_eq!(v.verdict, RunVerdict::Invalid);
        assert!(v.message.contains("PASS"), "{}", v.message);
    }

    #[test]
    fn a_verdict_with_no_message_is_still_a_verdict() {
        let v = classify("RESULT: PASS\n", "");
        assert_eq!(v.verdict, RunVerdict::Pass);
        assert_eq!(v.message, "");
    }

    #[test]
    fn indented_result_lines_are_accepted() {
        assert_eq!(classify("  RESULT: PASS ok\n", "").verdict, RunVerdict::Pass);
    }

    #[test]
    fn the_interpreters_are_found_by_executing_them() {
        // Not a tautology: on this host `bash` on PATH is the WSL launcher and `python3` is the
        // Store alias shim, and both fail this probe. A pass means a *working* pair was named.
        let it = probe().expect("a working bash and python are required to run any verifier");
        let out = Command::new(&it.bash).arg("-c").arg("printf w8ok").output().unwrap();
        assert!(String::from_utf8_lossy(&out.stdout).contains("w8ok"));
        let out = Command::new(&it.python).args(["-c", "print('w8ok')"]).output().unwrap();
        assert!(String::from_utf8_lossy(&out.stdout).contains("w8ok"), "{:?}", it.python);
    }

    #[test]
    fn a_relative_script_path_is_made_absolute_before_the_cwd_changes() {
        // The bug this run found: cwd is the work dir, so `../corpus/…/verify.sh` resolved against
        // the work dir and did not exist. Every verifier in the suite would have been INVALID.
        let abs = absolute(Path::new("../corpus/suites/u100/tasks/x/verify.sh"));
        assert!(abs.is_absolute(), "{}", abs.display());
        // Not a UNC path: bash cannot open `\\?\C:\…`.
        assert!(!abs.to_string_lossy().starts_with("\\\\?\\"), "{}", abs.display());
    }

    #[test]
    fn an_already_absolute_path_is_unchanged() {
        let p = std::env::temp_dir().join("w8-abs-check");
        assert_eq!(absolute(&p), p);
    }
}
