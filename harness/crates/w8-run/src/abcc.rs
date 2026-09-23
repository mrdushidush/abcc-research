//! The `abcc` drive (PLAN-TOOL Phase A1): one `abcc task` and one `abcc run` per cell, in a git
//! repository made from the fixture, graded by the suite's own verifier on the tree the attempt
//! left behind.
//!
//! 🚨 **abcc's gate is not the grader.** Its verdict, its rungs and its landing rules are all
//! ignored here: the attempt's closing checkpoint is checked out into the work dir whatever the gate
//! said, and `verify.sh` decides — the same verifier, run the same way, as for every other subject.
//! That is what makes an abcc cell and a claudette cell comparable.
//!
//! Each cell's work dir is its own repository, so each cell gets its own abcc home (abcc keys the
//! home on the repository root): a fresh log, no board carried over, nothing shared between cells.
//! The per-cell log is left where abcc put it and named in `abcc.json`, which is what the
//! tool-level metrics (editing calls, bytes read, prompt sizes) are computed from afterwards.

use std::fs::{self, File};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

use crate::endpoint::json_quote;
use crate::result::{Cell, Metric, Status};
use crate::verify::{self, Interpreters};
use w8_corpus::RunVerdict;

/// How often a running `abcc run` is polled for exit.
const POLL: Duration = Duration::from_millis(500);

/// What a cell needs that the corpus does not supply.
pub struct Spec<'a> {
    /// The `abcc` binary.
    pub bin: &'a str,
    /// The model id, handed to abcc as `ABCC_MODEL`.
    pub model: &'a str,
    /// The subject's budget for the whole `abcc run`, from the task's `timeout_s`.
    pub timeout: Duration,
    pub verify_timeout: Duration,
}

/// Run one cell. `cell` arrives from `base_cell`; `wd` is already materialized from `fixture/`.
#[allow(clippy::too_many_arguments)]
pub fn run_cell(
    mut cell: Cell,
    spec: &Spec<'_>,
    prompt: &str,
    title: &str,
    dir: &Path,
    wd: &Path,
    interp: &Interpreters,
    script: Option<PathBuf>,
) -> Cell {
    // Absolute, because every child below runs with the work dir as its cwd and is also told
    // `--repo <wd>`: a relative path would resolve twice.
    let (dir, wd) = match (std::path::absolute(dir), std::path::absolute(wd)) {
        (Ok(d), Ok(w)) => (d, w),
        (Err(e), _) | (_, Err(e)) => {
            cell.status = Status::Error;
            cell.reason = Some(format!("cannot make the work dir absolute: {e}"));
            return cell;
        }
    };
    let (dir, wd) = (dir.as_path(), wd.as_path());
    let transcript = dir.join("transcript.log");
    cell.workdir = wd.display().to_string();
    cell.transcript = transcript.display().to_string();
    // `abcc.json`: field name and already-encoded JSON value, in the order they were learned.
    let mut side: Vec<(&str, String)> = Vec::new();

    // ── The fixture becomes a repository, because abcc works in worktrees of one ─────────────
    if let Err(e) = init_repo(wd) {
        cell.status = Status::Error;
        cell.reason = Some(format!("cannot make the fixture a git repository: {e}"));
        return cell;
    }

    // ── Queue ────────────────────────────────────────────────────────────────────────────────
    let repo = wd.display().to_string();
    let queued = abcc(spec, wd, &["task", prompt, "--title", title, "--repo", &repo]);
    let task = match queued.as_ref().ok().and_then(|out| task_id(out)) {
        Some(t) => t,
        None => {
            cell.status = Status::Error;
            cell.reason = Some(format!("abcc task did not queue anything: {queued:?}"));
            return cell;
        }
    };
    side.push(("task", json_quote(&task)));

    // ── One attempt, bounded ─────────────────────────────────────────────────────────────────
    let t0 = Instant::now();
    let ran = run_bounded(spec, wd, &task, &repo, &transcript);
    let wall = t0.elapsed();
    let (exit, timed_out) = match ran {
        Ok(r) => r,
        Err(e) => {
            cell.status = Status::Error;
            cell.reason = Some(format!("abcc run could not be started: {e}"));
            return cell;
        }
    };
    side.push(("abcc_exit", exit.map_or("null".into(), |c| c.to_string())));
    side.push(("timed_out", timed_out.to_string()));

    // ── What it left: the closing checkpoint, whatever the gate said ─────────────────────────
    for (file, args) in [
        ("abcc-diff.txt", vec!["diff", task.as_str(), "--repo", repo.as_str()]),
        ("abcc-replay.txt", vec!["replay", task.as_str(), "--repo", repo.as_str()]),
        ("abcc-where.txt", vec!["where", "--repo", repo.as_str()]),
    ] {
        let text = abcc(spec, wd, &args).unwrap_or_else(|e| format!("(failed) {e}"));
        let _ = fs::write(dir.join(file), &text);
        if file == "abcc-where.txt" {
            if let Some(log) = text.lines().find_map(|l| l.strip_prefix("log")) {
                let log = log.trim().trim_end_matches("(exists)").trim();
                side.push(("log", json_quote(log)));
            }
        }
        if file == "abcc-diff.txt" {
            match closing_checkpoint(&text).and_then(|short| rev_parse(wd, &short).ok()) {
                Some(sha) => {
                    side.push(("checkpoint", json_quote(&sha)));
                    if let Err(e) = git(wd, &["checkout", "-q", "-f", "--detach", &sha]) {
                        cell.status = Status::Error;
                        cell.reason = Some(format!("cannot check out the attempt's tree {sha}: {e}"));
                        write_side(dir, &side);
                        return cell;
                    }
                }
                // No pair: the attempt recorded no tree, so the fixture as it was is what it left.
                None => {
                    side.push(("checkpoint", "null".into()));
                }
            }
        }
    }
    write_side(dir, &side);

    let not_here = || Metric::NotApplicable {
        reason: "abcc drive: tool and token counts come from the cell's abcc log, named in \
                 abcc.json"
            .into(),
    };
    for name in super_metrics() {
        cell.metrics.insert((*name).to_string(), not_here());
    }
    cell.metrics.insert("wall_clock_s".into(), Metric::Measured(wall.as_secs_f64()));
    cell.metrics.insert(
        "verify_ms".into(),
        Metric::NotApplicable { reason: "no verifier ran for this cell".into() },
    );

    if timed_out {
        cell.status = Status::Timeout;
        cell.reason = Some(format!(
            "abcc run did not finish within timeout_s = {} and was killed",
            spec.timeout.as_secs()
        ));
        return cell;
    }

    let Some(script) = script else {
        cell.status = Status::Invalid;
        cell.reason = Some("[verify].kind = \"none\": a completed run is not a verdict (F13)".into());
        return cell;
    };
    let t1 = Instant::now();
    let v = verify::run(interp, &script, wd, &transcript, spec.verify_timeout);
    cell.metrics.insert("verify_ms".into(), Metric::Measured(t1.elapsed().as_millis() as f64));
    cell.verifier_verdict = Some(v.verdict.as_str().to_string());
    cell.verifier_message = Some(v.message.clone());
    cell.status = match v.verdict {
        RunVerdict::Pass => Status::Pass,
        RunVerdict::Fail => Status::Fail,
        RunVerdict::Invalid => Status::Invalid,
    };
    if v.verdict == RunVerdict::Invalid {
        cell.reason = Some(format!("verifier: {}", v.message));
    }
    cell
}

/// The metric names the REPL drive measures and this drive does not.
fn super_metrics() -> &'static [&'static str] {
    &[
        "ttfvo_ms",
        "ttft_stdout_ms",
        "turns",
        "iterations",
        "tokens_in",
        "tokens_out",
        "tokens_in_preamble",
        "tokens_in_net",
        "mean_prompt_tokens",
        "peak_prompt_tokens",
    ]
}

fn write_side(dir: &Path, side: &[(&str, String)]) {
    let body: Vec<String> = side
        .iter()
        .map(|(k, v)| format!("{}:{v}", json_quote(k)))
        .collect();
    let _ = fs::write(dir.join("abcc.json"), format!("{{{}}}\n", body.join(",")));
}

/// `git init`, then one commit of everything the fixture holds.
fn init_repo(wd: &Path) -> Result<(), String> {
    git(wd, &["init", "-q", "-b", "main"])?;
    git(wd, &["add", "-A"])?;
    git(
        wd,
        &[
            "-c",
            "user.name=w8-run",
            "-c",
            "user.email=w8-run@localhost",
            "commit",
            "-q",
            "--no-gpg-sign",
            "--allow-empty",
            "-m",
            "fixture",
        ],
    )?;
    Ok(())
}

fn git(wd: &Path, args: &[&str]) -> Result<String, String> {
    let out = Command::new("git")
        .args(args)
        .current_dir(wd)
        .stdin(Stdio::null())
        .output()
        .map_err(|e| format!("git {}: {e}", args.join(" ")))?;
    if out.status.success() {
        Ok(String::from_utf8_lossy(&out.stdout).into_owned())
    } else {
        Err(format!(
            "git {} exited {:?}: {}",
            args.join(" "),
            out.status.code(),
            String::from_utf8_lossy(&out.stderr).trim()
        ))
    }
}

fn rev_parse(wd: &Path, short: &str) -> Result<String, String> {
    git(wd, &["rev-parse", "--verify", &format!("{short}^{{commit}}")]).map(|s| s.trim().to_owned())
}

/// One short-lived abcc command; stdout on success, both streams on failure.
fn abcc(spec: &Spec<'_>, wd: &Path, args: &[&str]) -> Result<String, String> {
    let out = Command::new(spec.bin)
        .args(args)
        .current_dir(wd)
        .env("ABCC_MODEL", spec.model)
        .stdin(Stdio::null())
        .output()
        .map_err(|e| format!("{} {}: {e}", spec.bin, args.first().unwrap_or(&"")))?;
    let stdout = String::from_utf8_lossy(&out.stdout).into_owned();
    if out.status.success() {
        Ok(stdout)
    } else {
        Err(format!(
            "exit {:?}\n{stdout}\n{}",
            out.status.code(),
            String::from_utf8_lossy(&out.stderr)
        ))
    }
}

/// `abcc run`, with both streams going to the transcript, killed at the task's budget.
fn run_bounded(
    spec: &Spec<'_>,
    wd: &Path,
    task: &str,
    repo: &str,
    transcript: &Path,
) -> std::io::Result<(Option<i32>, bool)> {
    let log = File::create(transcript)?;
    let mut child = Command::new(spec.bin)
        .args(["run", "--task", task, "--repo", repo])
        .current_dir(wd)
        .env("ABCC_MODEL", spec.model)
        .stdin(Stdio::null())
        .stdout(log.try_clone()?)
        .stderr(log)
        .spawn()?;
    let deadline = Instant::now() + spec.timeout;
    loop {
        if let Some(status) = child.try_wait()? {
            return Ok((status.code(), false));
        }
        if Instant::now() >= deadline {
            // ⚠ A kill ends abcc, not a toolchain child it started; the next cell is a different
            // repository and a different abcc home, so nothing it leaves is read again.
            let _ = child.kill();
            let _ = child.wait();
            return Ok((None, true));
        }
        std::thread::sleep(POLL);
    }
}

/// `t123` from `abcc task`'s first line (`t123  queued  <title>`).
fn task_id(out: &str) -> Option<String> {
    let first = out.split_whitespace().next()?;
    (first.len() > 1 && first.starts_with('t') && first[1..].bytes().all(|b| b.is_ascii_digit()))
        .then(|| first.to_owned())
}

/// The closing half of `abcc diff`'s `checkpoints <from>..<to>` line.
fn closing_checkpoint(diff: &str) -> Option<String> {
    diff.lines()
        .find_map(|l| l.strip_prefix("checkpoints "))
        .and_then(|pair| pair.split_once(".."))
        .map(|(_, to)| to.trim().to_owned())
        .filter(|to| !to.is_empty())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_task_id_comes_off_the_queue_line() {
        assert_eq!(task_id("t2919  queued  SEC-06h1a\n\nrun it with"), Some("t2919".into()));
        assert_eq!(task_id("error: nope"), None);
        assert_eq!(task_id("t"), None);
    }

    #[test]
    fn the_closing_checkpoint_is_the_right_half_of_the_pair() {
        let diff = "t5  title\nt5a9 — will not land: red. This is what it wrote anyway.\n\
                    checkpoints 1a2b3c4..5d6e7f8\n\ndiff --git a/x b/x\n";
        assert_eq!(closing_checkpoint(diff), Some("5d6e7f8".into()));
        assert_eq!(closing_checkpoint("t5  title\nno pair here\n"), None);
    }
}
