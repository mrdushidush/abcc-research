//! `w8-corpus` — the loader for a `corpus/SPEC.md` v1 corpus.
//!
//! Step 3 of the W8 plan needs a runner, and the first thing a runner needs is something that can
//! read the corpus and refuse it when it is wrong. `w8-import` (step 2) only *writes* the corpus;
//! `research/spikes/w8-corpus-v1/validate.py` is the throwaway stand-in that read it. This crate
//! is the port, and `validate.py` — numbered to match the spec — is the reference, not a guess.
//!
//! Three things it does that a `serde` derive would not:
//!
//! 1. **Every rejection names the SPEC §13 rule it violates.** "missing field `quarantine`" sends
//!    an author back to the spec; "[rule 6] no [disposition]" does not.
//! 2. **It accumulates.** All ninety tasks are checked before anything is returned.
//! 3. **It enforces SPEC §2's isolation guarantee structurally** — see [`workdir`]. `Task` will
//!    not hand out the path of `refsol/`, `sham/` or `stub/` at all, so a runner cannot copy one
//!    into the subject's work dir by accident.

pub mod model;
mod parse;
pub mod workdir;

pub use model::*;

use std::fmt;
use std::path::{Path, PathBuf};

// ---------------------------------------------------------------------------
// Rejections
// ---------------------------------------------------------------------------

/// SPEC §13's rules, by their spec number. The enum is the reason a rule that changes in the spec
/// and not here shows up as a numbering gap rather than as silence.
///
/// **Rule 8 is deliberately absent.** "A variant whose `requires` names a capability no subject
/// declares — caught at run planning, not load, since it is a property of the pair." It surfaces
/// as [`Support::NotSupported`] from [`Suite::plan`], which prints as `n/a` and is arithmetically
/// distinct from zero.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RuleId {
    /// Not a numbered rule: the file did not read or did not parse.
    Parse,
    /// SPEC §3's field reference — a required field missing or of the wrong type.
    Field,
    R1Schema,
    R2IdMismatch,
    R3PermissionMode,
    R4Turn,
    R5Verify,
    R6Disposition,
    R7Gate,
    R9DuplicateVariant,
    R10Partition,
    /// SPEC §5's operator-rule grammar.
    OperatorGrammar,
    /// SPEC §5: operator rules with no `default`.
    NoDefault,
    /// SPEC §2's isolation guarantee.
    Isolation,
}

impl RuleId {
    pub fn code(self) -> &'static str {
        match self {
            RuleId::Parse => "0",
            RuleId::Field => "§3",
            RuleId::R1Schema => "1",
            RuleId::R2IdMismatch => "2",
            RuleId::R3PermissionMode => "3",
            RuleId::R4Turn => "4",
            RuleId::R5Verify => "5",
            RuleId::R6Disposition => "6",
            RuleId::R7Gate => "7",
            RuleId::R9DuplicateVariant => "9",
            RuleId::R10Partition => "10",
            RuleId::OperatorGrammar => "§5.1",
            RuleId::NoDefault => "§5.2",
            RuleId::Isolation => "§2",
        }
    }
}

#[derive(Debug, Clone)]
pub struct Rejection {
    pub rule: RuleId,
    pub at: String,
    pub message: String,
}

impl fmt::Display for Rejection {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "[rule {}] {}: {}", self.rule.code(), self.at, self.message)
    }
}

#[derive(Debug, Default)]
pub(crate) struct Rejections(Vec<Rejection>);

impl Rejections {
    pub(crate) fn add(&mut self, rule: RuleId, at: impl AsRef<str>, message: impl Into<String>) {
        self.0.push(Rejection { rule, at: at.as_ref().to_owned(), message: message.into() });
    }
    pub(crate) fn len(&self) -> usize {
        self.0.len()
    }
    pub(crate) fn into_vec(self) -> Vec<Rejection> {
        self.0
    }
}

// ---------------------------------------------------------------------------
// Corpus
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct Corpus {
    pub root: PathBuf,
    pub subjects: Vec<Subject>,
    pub suites: Vec<Suite>,
}

impl Corpus {
    /// Load and validate. `Err` carries **every** rejection, not the first.
    pub fn load(root: &Path) -> Result<Corpus, Vec<Rejection>> {
        let (corpus, rejections) = Corpus::load_reporting(root);
        if rejections.is_empty() { Ok(corpus) } else { Err(rejections) }
    }

    /// The same load, with whatever was valid handed back alongside the rejections. For the
    /// report binary: an operator fixing a corpus wants to see the tasks that *did* load.
    ///
    /// Note that a task with any rejection is **not** in the returned corpus. `validate.py`
    /// counts it as loaded; this does not, because a half-valid task has no business reaching a
    /// runner. The two therefore agree exactly on an accepted corpus and differ in the task count
    /// on a rejected one.
    pub fn load_reporting(root: &Path) -> (Corpus, Vec<Rejection>) {
        let mut rej = Rejections::default();
        let mut subjects = Vec::new();
        let mut suites = Vec::new();

        for path in sorted_dir(&root.join("subjects")) {
            if path.extension().is_some_and(|e| e == "toml")
                && let Some(s) = parse::parse_subject(&path, &mut rej)
            {
                subjects.push(s);
            }
        }

        for dir in sorted_dir(&root.join("suites")) {
            if !dir.join("suite.toml").is_file() {
                continue;
            }
            let Some((mut suite, suite_variants)) = parse::parse_suite(&dir, &mut rej) else {
                continue;
            };
            let tasks_dir = dir.join("tasks");
            let mut seen = 0usize;
            for tdir in sorted_dir(&tasks_dir) {
                if !tdir.is_dir() {
                    continue;
                }
                seen += 1;
                if let Some(t) = parse::parse_task(&tdir, &suite.id, &suite_variants, &mut rej) {
                    suite.tasks.push(t);
                }
            }
            // The suite asserting its own size. A silently missing task directory is exactly the
            // failure that flatters a run — fewer tasks, same pass rate — so it is checked rather
            // than trusted. Not one of §13's ten; recorded in the README as a strictening.
            if let Some(expected) = suite.expected_tasks
                && expected != seen
            {
                rej.add(
                    RuleId::Field,
                    format!("suites/{}", suite.id),
                    format!("expected_tasks = {expected} but the tree holds {seen} task directories"),
                );
            }
            suites.push(suite);
        }

        (Corpus { root: root.to_path_buf(), subjects, suites }, rej.into_vec())
    }

    pub fn subject(&self, id: &str) -> Option<&Subject> {
        self.subjects.iter().find(|s| s.id == id)
    }

    pub fn suite(&self, id: &str) -> Option<&Suite> {
        self.suites.iter().find(|s| s.id == id)
    }
}

fn sorted_dir(dir: &Path) -> Vec<PathBuf> {
    let Ok(rd) = std::fs::read_dir(dir) else {
        return Vec::new();
    };
    let mut v: Vec<PathBuf> = rd.filter_map(Result::ok).map(|e| e.path()).collect();
    v.sort();
    v
}

// ---------------------------------------------------------------------------
// Run planning — SPEC §13 rule 8, §7
// ---------------------------------------------------------------------------

/// Whether a `(task, variant, subject)` cell can run at all.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Support {
    Runnable,
    /// Prints as `n/a` and is arithmetically distinct from zero. SPEC §7: that column is exactly
    /// where 2.0's differentiator has to appear, so it must never round to nothing.
    NotSupported { capability: String },
}

#[derive(Debug, Clone)]
pub struct Cell<'a> {
    pub task: &'a Task,
    pub variant: &'a Variant,
    pub support: Support,
}

impl Suite {
    /// Every cell this suite would produce against one subject, in task × variant order.
    pub fn plan<'a>(&'a self, subject: &Subject) -> Vec<Cell<'a>> {
        let mut cells = Vec::new();
        for task in &self.tasks {
            for variant in &task.variants {
                let missing = variant.requires.iter().find(|c| !subject.capabilities.contains(c));
                cells.push(Cell {
                    task,
                    variant,
                    support: match missing {
                        Some(c) => Support::NotSupported { capability: c.clone() },
                        None => Support::Runnable,
                    },
                });
            }
        }
        cells
    }

    /// SPEC §10's arithmetic, with the rule it was computed under attached — because a headline
    /// that does not say whether presence-only tasks are in it is not interpretable.
    pub fn aggregate(&self) -> AggregateSummary {
        let mut counted = Vec::new();
        let mut excluded_quarantined = 0usize;
        let mut excluded_verifiable = 0usize;
        for t in &self.tasks {
            if self.aggregate.counts(&t.disposition) {
                counted.push(t.id.clone());
            } else if self.aggregate.exclude_quarantined && t.disposition.quarantine != Quarantine::None {
                excluded_quarantined += 1;
            } else {
                excluded_verifiable += 1;
            }
        }
        AggregateSummary {
            denominator: counted.len(),
            counted,
            excluded_quarantined,
            excluded_verifiable,
            rule: self.aggregate.describe(),
        }
    }

    /// The disposition breakdown — the 54 / 24 / 12 the import is checked against.
    pub fn disposition_counts(&self) -> DispositionCounts {
        let mut c = DispositionCounts::default();
        for t in &self.tasks {
            if t.disposition.quarantine == Quarantine::WithBaseline {
                c.quarantined += 1;
            } else {
                match t.disposition.verifiable {
                    Verifiable::Full => c.full += 1,
                    Verifiable::PresenceOnly => c.presence_only += 1,
                    Verifiable::None => c.no_verifier += 1,
                }
            }
        }
        c
    }
}

#[derive(Debug, Clone)]
pub struct AggregateSummary {
    pub denominator: usize,
    pub counted: Vec<String>,
    pub excluded_quarantined: usize,
    pub excluded_verifiable: usize,
    pub rule: String,
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct DispositionCounts {
    pub full: usize,
    pub presence_only: usize,
    pub no_verifier: usize,
    pub quarantined: usize,
}
