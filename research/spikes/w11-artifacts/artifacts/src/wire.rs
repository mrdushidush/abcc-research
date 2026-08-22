//! The **wire** types: exactly what a model is asked to emit, and nothing else.
//!
//! Rule this file exists to enforce: the model fills in what it can honestly
//! know. Identity (`seq`, ids), provenance (model, tokens, finish_reason,
//! wall clock) and anything measured by an instrument are added by the
//! recorder, never by the model. A schema that asks a model for its own
//! token count is asking it to lie.
//!
//! Every type here is `Deserialize` + `JsonSchema` and **none** is `Default`:
//! a missing field is a parse failure, not a zero (W11 F233's rule).

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

// ── A1 Localize → brief ──────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct BriefWire {
    /// The task, restated in the model's own words. Grading input, not prose.
    pub restatement: String,
    /// Where the change goes. At least one; an empty brief is not a brief.
    pub sites: Vec<SiteWire>,
    /// How the change should be made, in prose. The Change phase reads this.
    pub approach: String,
    /// What could go wrong. May be empty; may not be absent.
    pub risks: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct SiteWire {
    /// Workspace-relative path. A string here; a `RepoPath` only after the
    /// recorder has checked it against the tree (see `checked::Site`).
    pub path: String,
    /// Optional line span. `null` means "the whole file", not "line 0".
    pub first_line: Option<u32>,
    pub last_line: Option<u32>,
    /// Why this site is in the brief.
    pub why: String,
}

// ── M1 Plan → task set ───────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct TaskSetWire {
    pub tasks: Vec<TaskWire>,
}

#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct TaskWire {
    pub title: String,
    /// What this task must achieve. The Change phase's prose contract.
    pub intent: String,
    /// Files this task is expected to touch. Checked against the tree.
    pub touches: Vec<String>,
    /// Indices into `TaskSetWire::tasks` this task depends on (W3 F109 edges,
    /// emitted rather than inferred from list order).
    pub depends_on: Vec<u32>,
    /// One executable acceptance criterion. Prose criteria do not exist
    /// (W11 F236).
    pub criterion: CriterionWire,
}

#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct CriterionWire {
    /// The command, verbatim. Its shell is part of it (W11 F251).
    pub command: String,
    pub shell: Shell,
    /// Workspace-relative working directory. `"."` for the root.
    pub cwd: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum Shell {
    Sh,
    Powershell,
    Cmd,
}

// ── A2 Change → note (NOT the diff) ──────────────────────────────────

/// What the Change phase says about what it did.
///
/// This is deliberately **not** the diff. The diff is read from git by the
/// recorder (`checked::DiffRef`); a model-authored account of its own edits
/// is narration, and grading narration is W11 F232. The note exists so the
/// model can flag what it could not finish — which git cannot tell you.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ChangeNoteWire {
    pub summary: String,
    /// Anything the model knows it did not do. Empty is a claim; absent is a
    /// parse failure.
    pub unresolved: Vec<String>,
}

// ── A4 Judge → verdict ───────────────────────────────────────────────

/// No score. W11 F247 measured the binary as reproducible at temperature 0
/// and the number as not (0, 2, 0, 2 on identical input), so a numeric score
/// is not a field this type is entitled to have.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct VerdictWire {
    pub call: Call,
    /// Why, in one or two sentences. Read by the operator and by the next
    /// attempt's Change phase.
    pub rationale: String,
    pub defects: Vec<DefectWire>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum Call {
    Pass,
    Fail,
}

#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct DefectWire {
    /// Workspace-relative path the defect is in, or `null` when the defect is
    /// about the change as a whole.
    pub path: Option<String>,
    pub severity: Severity,
    pub description: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum Severity {
    Low,
    Medium,
    High,
}
