//! The **checked** types: what the pipeline passes on, after the recorder has
//! confronted a wire value with the world.
//!
//! The split is the whole point. A schema guarantees *shape*; only a check
//! against the workspace guarantees *reference*. A model can emit a perfectly
//! schema-valid path that does not exist, and every donor that stored a brief
//! as a `String` had to go looking for paths with a tokeniser afterwards
//! (`claudette:forge_run.rs:1073` — `warn_if_brief_paths_missing`).
//!
//! Two rules hold everywhere below:
//!   * **no `Default`** on anything a gate reads (W11 F233 / item 1 §6);
//!   * **no `Ord`** on an outcome, so `Uncertain` cannot be sorted against a
//!     measurement — it is refused at the type level rather than losing by
//!     convention.

use serde::{Deserialize, Serialize};

// ── The tri-state every gate input wears ─────────────────────────────

/// A value a gate may read. Constructed at the site that knows why.
///
/// Deliberately **not** `Default`, **not** `Ord`, **not** `PartialOrd`: the
/// rule "Uncertain loses every comparison it enters" is enforced by there
/// being no comparison. Folding is `admits_pass`, which is a conjunction.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "state", rename_all = "snake_case")]
pub enum GateInput<T> {
    Measured { value: T },
    Uncertain { why: Why },
}

impl<T> GateInput<T> {
    /// The only fold. `Uncertain` and a failed measurement are both `false`,
    /// and they are `false` for different reasons that the value still carries.
    pub fn admits_pass(&self, pass: impl Fn(&T) -> bool) -> bool {
        match self {
            GateInput::Measured { value } => pass(value),
            GateInput::Uncertain { .. } => false,
        }
    }
}

/// Every reason a gate input can be `Uncertain`. Adding a variant is a
/// compile error at every `match`, which is the point.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "why", rename_all = "snake_case")]
pub enum Why {
    /// W11 F246: the reasoning trace overran the output budget and the payload
    /// was never emitted. HTTP 200, `finish_reason: length`, zero bytes.
    TraceOverran { reasoning_tokens: u32 },
    /// Budget hit with a partial payload.
    Truncated { reasoning_tokens: u32 },
    /// `finish_reason: stop` and nothing in the payload.
    EmptyPayload,
    /// Schema-valid JSON that failed the checked conversion.
    Ungrounded { detail: String },
    /// The wire payload did not parse at all.
    Unparseable { detail: String },
    /// W11 F251: the criterion exits 0 on the unchanged tree, so it measures
    /// nothing.
    CriterionDoesNotDiscriminate { exit: i32 },
    /// W11 F251: the criterion could not be run — binary absent, wrong shell.
    /// Never a fail.
    CriterionUnrunnable { detail: String },
    /// The instrument was not run. W11 F231's rule: absent is not pass.
    NotRun { detail: String },
    /// The instrument was killed by the idle-gap clock (W3 F172).
    Stalled { idle_ms: u32 },
}

// ── A1 → brief ───────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Brief {
    pub restatement: String,
    pub sites: Vec<Site>,
    pub approach: String,
    pub risks: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Site {
    pub path: RepoPath,
    pub span: Option<LineSpan>,
    pub why: String,
}

/// A workspace-relative path **that existed when the artifact was recorded**.
///
/// The only constructor takes the workspace root and hits the filesystem, so
/// an ungrounded path cannot be carried past the recorder. This is the type
/// that replaces `warn_if_brief_paths_missing`: per path, not per brief, and
/// a value rather than an `eprintln!`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RepoPath(String);

impl RepoPath {
    pub fn check(root: &std::path::Path, raw: &str) -> Result<Self, Why> {
        let candidate = std::path::Path::new(raw);
        if candidate.is_absolute() {
            return Err(Why::Ungrounded {
                detail: format!("absolute path outside the workspace: {raw}"),
            });
        }
        if raw.split(['/', '\\']).any(|c| c == "..") {
            return Err(Why::Ungrounded {
                detail: format!("path escapes the workspace: {raw}"),
            });
        }
        if root.join(candidate).exists() {
            Ok(RepoPath(raw.replace('\\', "/")))
        } else {
            Err(Why::Ungrounded {
                detail: format!("no such path under the workspace: {raw}"),
            })
        }
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct LineSpan {
    pub first: u32,
    pub last: u32,
}

// ── M1 → task set ────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskSet {
    pub tasks: Vec<Task>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    pub title: String,
    pub intent: String,
    pub touches: Vec<RepoPath>,
    pub depends_on: Vec<usize>,
    pub criterion: Criterion,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Criterion {
    pub command: String,
    pub shell: crate::wire::Shell,
    pub cwd: RepoPath,
    /// W11 F251's red-first check. Four states, not an `Option<ExitCode>`:
    /// an `Option` is one `unwrap_or` away from "absent means fine", which is
    /// the bug item 1 §6 forbids.
    pub baseline: Baseline,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "baseline", rename_all = "snake_case")]
pub enum Baseline {
    /// A3 has not run it against the unchanged tree yet. A task in this state
    /// may not be `Deployed`.
    Unmeasured,
    /// Non-zero on the unchanged tree for a reason that is not "cannot run".
    /// The criterion binds.
    Red { exit: i32 },
    /// Exit 0 on the unchanged tree. Not a criterion; back to M1 with the
    /// command and its exit code as the evidence.
    DoesNotDiscriminate { exit: i32 },
    /// Could not be run at all. Never a fail.
    Unrunnable { detail: String },
}

impl Baseline {
    /// The only state in which a criterion may be used as a gate.
    pub fn binds(&self) -> bool {
        matches!(self, Baseline::Red { .. })
    }
}

// ── A2 → diff ────────────────────────────────────────────────────────

/// The diff artifact is a **reference into git**, never diff text carried on
/// the log.
///
/// Three reasons, one per donor: the Judge must read the change from its
/// source of truth rather than from a transcript (W11 F232); a diff is
/// unbounded and the log is not; and a recorded SHA pair can be re-derived
/// forever while a copied hunk rots the moment anything rebases.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiffRef {
    pub base: Sha,
    pub head: Sha,
    /// Derived from `git diff --numstat`, not from the model.
    pub files: Vec<FileStat>,
    pub insertions: u32,
    pub deletions: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Sha(pub String);

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileStat {
    pub path: String,
    pub insertions: u32,
    pub deletions: u32,
    pub status: FileStatus,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum FileStatus {
    Added,
    Modified,
    Deleted,
    Renamed,
}

// ── A3 / M2 → measurement set ────────────────────────────────────────

/// What an instrument produced. No model, no score, no average.
///
/// BCF collapses its equivalent into one `f32` before anyone can read it —
/// `final_score = critique_avg * 0.4 + verifier_score * 0.6`, where the
/// second term already blends a real test pass rate with content heuristics
/// (`verifier.rs:741-763`). A weighted sum of a measurement and an opinion is
/// an opinion. This type keeps the checks apart and the gate is a conjunction.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeasurementSet {
    pub checks: Vec<Check>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Check {
    pub name: CheckName,
    pub outcome: GateInput<Run>,
    /// Whether this check can fail the attempt on its own.
    pub required: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "check", rename_all = "snake_case")]
pub enum CheckName {
    Build,
    Typecheck,
    ProjectSuite,
    /// The task's own acceptance criterion.
    Criterion,
    DiffScan,
}

/// One command that actually ran. Exit code and streams, no interpretation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Run {
    pub command: String,
    pub exit: i32,
    pub wall_ms: u32,
    pub stdout_bytes: u32,
    pub stderr_bytes: u32,
    /// Head of the output, for the console and the Judge's prompt. The full
    /// streams live beside the log, addressed by `seq`.
    pub excerpt: String,
}

impl MeasurementSet {
    /// The gate: a conjunction of vetoes over the required checks (W6 item 2).
    /// `Uncertain` is a veto because it is not a pass, and it says so.
    pub fn admits_pass(&self) -> bool {
        self.checks
            .iter()
            .filter(|c| c.required)
            .all(|c| c.outcome.admits_pass(|r| r.exit == 0))
    }
}

// ── A4 → verdict ─────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Verdict {
    pub call: crate::wire::Call,
    pub rationale: String,
    pub defects: Vec<Defect>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Defect {
    /// `None` when the defect is about the change as a whole. A path the model
    /// named that does not exist is not silently dropped — it fails the
    /// conversion and the verdict becomes `Uncertain(Ungrounded)`.
    pub path: Option<RepoPath>,
    pub severity: crate::wire::Severity,
    pub description: String,
}

// ── Provenance: what the recorder adds, and the model never sees ─────

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum FinishReason {
    Stop,
    Length,
    ToolCalls,
    /// The transport ended without a reason. Not `Stop`.
    Dropped,
}

/// Everything a model call is known to have cost. Filled from the response,
/// never from the payload.
///
/// BCF's per-round report has five of these and writes `0.0` into all five
/// (`mission.rs:880-919`), because the call path that returns the numbers —
/// `run_*_with_stats` — is used by two of its nine stages and not by the
/// round report. Provenance the producer does not have is provenance the
/// artifact should not be shaped to hold.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ModelCall {
    pub model: String,
    pub head: String,
    pub prompt_tokens: u32,
    pub completion_tokens: u32,
    /// W11 F246: the quantity that overran. Already on the wire as
    /// `usage.completion_tokens_details.reasoning_tokens`; invisible in the
    /// record unless it is written down.
    pub reasoning_tokens: u32,
    pub finish_reason: FinishReason,
    pub wall_ms: u32,
}
