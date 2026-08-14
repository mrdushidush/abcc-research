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
//! **The verifier is bounded** (F57, [`DEFAULT_TIMEOUT`]), and it is bounded separately from the
//! subject: `timeout_s` in the corpus is the subject's budget, and for the whole first Q56 campaign
//! nothing at all bounded this half. The verifier runs code the *subject* wrote, so "the artifact
//! never terminates" is a routine outcome, not an edge case — and an unbounded verifier turns it
//! into an unbounded harness.
//!
//! **This is the second copy of that probe** — `w8-import/src/gate.rs:145-197` has the first, and it
//! is a binary crate, so sharing one function would mean giving the importer a library surface the
//! runner would then depend on wholesale. The two must agree: they read the same `W8_BASH` override
//! and try the same candidates in the same order, so a host fix applies to both. If they ever
//! diverge, the gate evidence recorded in the corpus and the verdicts produced here stop describing
//! the same verifier.

use std::ffi::OsString;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use w8_corpus::RunVerdict;

/// Ceiling on **one verifier**, and the reason it exists is F57.
///
/// The corpus's `timeout_s` bounds the *subject interaction only*. Nothing bounded the verify phase,
/// and `Command::output()` blocks forever — so on `Q13 / deny-first-edit` the subject wrote a
/// `parse_csv_line` whose scanner could fail to advance, the verifier executed that code, and one
/// `python.exe` burned 2h17m pinned at 100% of a core while the whole campaign waited behind it. A
/// subject that writes a non-terminating solution is not an exotic failure — it is a normal failure
/// mode of a code-writing subject, so this recurs.
///
/// 300 s is chosen against what real verifiers cost, not against the hang: the slowest Q56 verifiers
/// are the 14 `cargo` ones and they finish in seconds to low tens of seconds, so this is an order of
/// magnitude of headroom and still bounds a hang at 5 minutes instead of forever. It is recorded in
/// RUNMETA and overridable with `--verify-timeout-s`, because a bound nobody records is a held
/// constant nobody measures (SPEC §11), and every number banked before this existed was measured
/// with no bound at all.
pub const DEFAULT_TIMEOUT: Duration = Duration::from_secs(300);

/// How long to keep reading after the process exits, waiting for the pipes to reach EOF.
///
/// Not paranoia: the snapshot is taken from a buffer another thread is still appending to, so
/// returning the instant `try_wait` succeeds can truncate the last chunk — which is the chunk with
/// the `RESULT:` line in it. Bounded rather than joined, because a *grandchild* can hold the write
/// end open after bash is gone and a join would reintroduce the unbounded wait this module exists to
/// remove.
const DRAIN_GRACE: Duration = Duration::from_secs(5);
const POLL: Duration = Duration::from_millis(25);

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

/// Run one verifier, bounded by `timeout` (F57).
///
/// The bound produces `INVALID`, never `FAIL`, and that is SPEC §8 rather than a choice made here: a
/// verifier that was killed graded nothing, so "the artifact is wrong" is a fact this run does not
/// have. It holds even when partial stdout already carried a `RESULT:` line — a verdict from a
/// verifier that then failed to terminate is not a verdict, and taking it would be believing the
/// half of a broken instrument that flatters the subject. The partial line is put in the message so
/// nothing is thrown away.
pub fn run(
    it: &Interpreters,
    script: &Path,
    workdir: &Path,
    transcript: &Path,
    timeout: Duration,
) -> Verdict {
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
    detach_group(&mut cmd);
    match bounded_output(&mut cmd, timeout) {
        Err(e) => Verdict {
            verdict: RunVerdict::Invalid,
            message: format!("could not run bash {}: {e}", script.display()),
        },
        Ok(Ran::Exited { stdout, stderr }) => classify(&stdout, &stderr),
        Ok(Ran::TimedOut { after, reaped, stdout, stderr }) => Verdict {
            verdict: RunVerdict::Invalid,
            message: format!(
                "the verifier did not finish within {} s and was killed{} (F57). It graded nothing, \
                 so this is INVALID and not FAIL. partial stdout={:?} stderr={:?}",
                after.as_secs(),
                if reaped { "" } else { ", AND THE KILL DID NOT CONFIRM — check for a leaked \
                 interpreter still burning a core" },
                tail(&stdout, 400),
                tail(&stderr, 400)
            ),
        },
    }
}

enum Ran {
    Exited { stdout: String, stderr: String },
    /// Killed on expiry. `reaped` is whether the tree kill reported success — recorded rather than
    /// assumed, because a failed kill leaves a spinner pinning a core for the rest of the campaign
    /// and that has to be visible in the cell rather than inferred later from a fan.
    TimedOut { after: Duration, reaped: bool, stdout: String, stderr: String },
}

/// `Command::output()` with a deadline and a tree kill.
///
/// Three things this cannot do the obvious way, each of which would put the unbounded wait back:
///
/// 1. **It cannot use `output()`**, which reads both pipes to EOF before returning — the wait it is
///    replacing.
/// 2. **It cannot read the pipes on this thread**, or a verifier producing more output than the pipe
///    buffer deadlocks against a runner that is not reading. Hence a draining thread per stream.
/// 3. **It cannot `join` those threads.** EOF arrives when the *last* holder of the write end closes
///    it, and after a tree kill a survivor still holds it. So the buffers are shared and snapshotted
///    under a bounded wait, and a reader that never finishes is left to leak — one detached thread
///    blocked on a dead pipe costs nothing, and a harness that hangs costs a campaign.
fn bounded_output(cmd: &mut Command, timeout: Duration) -> std::io::Result<Ran> {
    let mut child = cmd.stdout(Stdio::piped()).stderr(Stdio::piped()).spawn()?;
    let out = drain(child.stdout.take());
    let err = drain(child.stderr.take());
    let start = Instant::now();
    loop {
        if child.try_wait()?.is_some() {
            wait_for_eof(&[&out, &err], DRAIN_GRACE);
            return Ok(Ran::Exited { stdout: out.text(), stderr: err.text() });
        }
        let waited = start.elapsed();
        if waited >= timeout {
            let reaped = kill_tree(&mut child);
            wait_for_eof(&[&out, &err], DRAIN_GRACE);
            return Ok(Ran::TimedOut {
                after: waited,
                reaped,
                stdout: out.text(),
                stderr: err.text(),
            });
        }
        std::thread::sleep(POLL.min(timeout - waited));
    }
}

/// A pipe being read by a thread this module will not wait on.
struct Pipe {
    buf: Arc<Mutex<Vec<u8>>>,
    eof: Arc<AtomicBool>,
}

impl Pipe {
    /// Read what has arrived so far. `into_inner` on a poisoned lock on purpose: a panicking reader
    /// must cost the tail of a message, never the verdict.
    fn text(&self) -> String {
        let b = self.buf.lock().unwrap_or_else(|e| e.into_inner());
        String::from_utf8_lossy(&b).into_owned()
    }
}

fn drain<R: Read + Send + 'static>(r: Option<R>) -> Pipe {
    let buf = Arc::new(Mutex::new(Vec::new()));
    let eof = Arc::new(AtomicBool::new(r.is_none()));
    if let Some(mut r) = r {
        let (buf, eof) = (Arc::clone(&buf), Arc::clone(&eof));
        std::thread::spawn(move || {
            let mut chunk = [0u8; 8192];
            while let Ok(n) = r.read(&mut chunk) {
                if n == 0 {
                    break;
                }
                buf.lock().unwrap_or_else(|e| e.into_inner()).extend_from_slice(&chunk[..n]);
            }
            eof.store(true, Ordering::Release);
        });
    }
    Pipe { buf, eof }
}

fn wait_for_eof(pipes: &[&Pipe], grace: Duration) {
    let start = Instant::now();
    while start.elapsed() < grace {
        if pipes.iter().all(|p| p.eof.load(Ordering::Acquire)) {
            return;
        }
        std::thread::sleep(POLL);
    }
}

/// Kill the child **and everything it spawned**.
///
/// `Child::kill()` alone is not the fix: F57's spinner was a *grandchild* — `python` under `bash` —
/// so killing bash would leave it running, still pinned at 100% of a core and still holding the
/// stdout pipe the runner is reading. The verifier is exactly the place where grandchildren are the
/// norm rather than the exception, since a verify script's whole job is to invoke an interpreter.
#[cfg(windows)]
fn kill_tree(child: &mut Child) -> bool {
    // `/T` is the tree, `/F` is unconditional. Spawned directly rather than through a shell, so the
    // MSYS path rewriting that turns `/F` into `F:/` from Git Bash cannot apply.
    let ok = Command::new("taskkill")
        .args(["/F", "/T", "/PID", &child.id().to_string()])
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false);
    let _ = child.kill();
    let _ = child.wait();
    ok
}

#[cfg(unix)]
fn kill_tree(child: &mut Child) -> bool {
    // The child leads its own process group (`detach_group`), so the negative pid reaches every
    // descendant. `kill` the binary rather than a `libc` dependency: this crate has two third-party
    // deps and both are load-bearing (see Cargo.toml), and the Windows half already shells out.
    let ok = Command::new("kill")
        .args(["-9", &format!("-{}", child.id())])
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false);
    let _ = child.kill();
    let _ = child.wait();
    ok
}

/// Give the verifier its own process group so one signal reaches the whole tree. No-op on Windows,
/// where `taskkill /T` walks the parent chain instead.
#[cfg(unix)]
fn detach_group(cmd: &mut Command) {
    use std::os::unix::process::CommandExt;
    cmd.process_group(0);
}

#[cfg(not(unix))]
fn detach_group(_cmd: &mut Command) {}

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

    /// A scratch work dir holding one `verify.sh`. Written with LF endings whatever the host does:
    /// bash reads the shebang line byte for byte and a CR lands inside the interpreter path.
    fn scratch(name: &str, script: &str) -> (PathBuf, PathBuf) {
        let dir = std::env::temp_dir().join(format!("w8-verify-{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(&dir).unwrap();
        let sh = dir.join("verify.sh");
        std::fs::write(&sh, script.replace("\r\n", "\n")).unwrap();
        (dir, sh)
    }

    /// **F57's regression, and the shape it is written in is the point.** The hang was not bash — it
    /// was `python` *under* bash, executing a `parse_csv_line` the subject wrote whose scanner could
    /// fail to advance. So this test spins a grandchild, exactly as the campaign did, and asserts
    /// three separate things: the call returns, it returns INVALID rather than FAIL, and **the
    /// grandchild is actually dead**. The third is what a `Child::kill()`-only fix would fail — it
    /// would pass the first two while leaving a python pinned at 100% of a core for the rest of the
    /// run, which is the failure mode that cost 2h17m.
    ///
    /// **Confirmed by mutation, not by assertion alone**: dropping `/T` from the tree kill fails
    /// this test on the heartbeat (`384 != 456`) while the verdict assertions still pass — and the
    /// leaked tree then held an inherited stdout handle open, hanging the parent pipeline too. That
    /// second effect is the one to remember: a leaked grandchild does not merely waste a core, it
    /// can keep the process that spawned it from ever being seen to finish.
    #[test]
    fn a_verifier_that_never_terminates_is_killed_and_scored_invalid() {
        let (dir, sh) = scratch(
            "spin",
            "#!/usr/bin/env bash\n\
             \"${PYTHON:-python3}\" -c '\n\
             import sys, time\n\
             p = sys.argv[1]\n\
             while True:\n\
             \x20   open(p, \"a\").write(\"x\")\n\
             \x20   time.sleep(0.02)\n\
             ' \"$1/heartbeat\"\n\
             echo \"RESULT: PASS never reached\"\n",
        );
        let it = probe().expect("a working bash and python are required");
        let hb = dir.join("heartbeat");

        let t0 = Instant::now();
        let v = run(&it, &sh, &dir, &dir.join("transcript.log"), Duration::from_secs(3));
        let took = t0.elapsed();

        // Pre-F57 this call never returned at all.
        assert!(took < Duration::from_secs(60), "the bound did not bite: {took:?}");
        // SPEC §8: a verifier that graded nothing did not find the artifact wrong.
        assert_eq!(v.verdict, RunVerdict::Invalid, "{}", v.message);
        assert!(v.message.contains("did not finish"), "{}", v.message);

        // Not vacuous: the grandchild has to have run before its death means anything.
        let first = std::fs::metadata(&hb).map(|m| m.len()).unwrap_or(0);
        assert!(first > 0, "the spinning python never started, so this test proved nothing");
        std::thread::sleep(Duration::from_millis(1500));
        let second = std::fs::metadata(&hb).map(|m| m.len()).unwrap_or(0);
        assert_eq!(first, second, "the python grandchild outlived the kill and is still spinning");
        let _ = std::fs::remove_dir_all(&dir);
    }

    /// The other half of the same claim: the bound must not change what a working verifier reports.
    /// A timeout that scored everything INVALID would satisfy the test above on its own.
    #[test]
    fn a_verifier_that_terminates_is_untouched_by_the_bound() {
        let (dir, sh) =
            scratch("fast", "#!/usr/bin/env bash\necho \"RESULT: PASS donor assertions held\"\n");
        let it = probe().expect("a working bash and python are required");
        let v = run(&it, &sh, &dir, &dir.join("transcript.log"), Duration::from_secs(60));
        assert_eq!(v.verdict, RunVerdict::Pass, "{}", v.message);
        assert_eq!(v.message, "donor assertions held");
        let _ = std::fs::remove_dir_all(&dir);
    }

    /// The deadlock the draining threads exist to prevent. A verifier that prints more than the pipe
    /// buffer holds blocks on the write until someone reads, so a runner that waits for exit *before*
    /// reading waits forever — a second unbounded wait, arriving through the fix for the first. The
    /// verdict is the last line, so if this regresses the test hangs rather than failing quietly.
    #[test]
    fn a_verifier_that_outruns_the_pipe_buffer_still_delivers_its_verdict() {
        let (dir, sh) = scratch(
            "flood",
            "#!/usr/bin/env bash\n\
             \"${PYTHON:-python3}\" -c 'print(\"noise \" * 12 * 20000)'\n\
             echo \"RESULT: FAIL after the flood\"\n",
        );
        let it = probe().expect("a working bash and python are required");
        let v = run(&it, &sh, &dir, &dir.join("transcript.log"), Duration::from_secs(60));
        assert_eq!(v.verdict, RunVerdict::Fail, "{}", v.message);
        assert_eq!(v.message, "after the flood");
        let _ = std::fs::remove_dir_all(&dir);
    }
}
