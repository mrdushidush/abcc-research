//! The typed corpus model — `corpus/SPEC.md` v1 §3–§7, §10.
//!
//! Every enum here is closed on purpose. The spec's vocabularies are finite and adding a value
//! is a `schema` bump (SPEC §0), so a parse that cannot map a string onto one of these is a
//! rejection and never a shrug.

use std::collections::BTreeMap;
use std::fmt;
use std::path::PathBuf;

// ---------------------------------------------------------------------------
// Closed vocabularies
// ---------------------------------------------------------------------------

macro_rules! vocab {
    ($name:ident { $($variant:ident => $text:literal),+ $(,)? }) => {
        #[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
        pub enum $name { $($variant),+ }

        impl $name {
            pub fn parse(s: &str) -> Option<Self> {
                match s { $($text => Some(Self::$variant),)+ _ => None }
            }
            pub fn as_str(self) -> &'static str {
                match self { $(Self::$variant => $text),+ }
            }
            /// For the "not in {...}" half of a rejection message.
            pub fn allowed() -> &'static [&'static str] { &[$($text),+] }
        }

        impl fmt::Display for $name {
            fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result { f.write_str(self.as_str()) }
        }
    };
}

vocab!(Lang {
    Python => "python", Node => "node", Rust => "rust",
    Go => "go", TypeScript => "typescript", Html => "html", Mixed => "mixed",
});

vocab!(Verifiable {
    Full => "full", PresenceOnly => "presence_only", None => "none",
});

vocab!(Quarantine {
    None => "none", WithBaseline => "with_baseline",
});

vocab!(GateVerdict {
    Sound => "sound", Broken => "broken", Inconclusive => "inconclusive", NotRun => "not_run",
});

vocab!(GateTier {
    Stub => "stub", Absent => "absent", DonorFixture => "donor_fixture",
    Refsol => "refsol", Sham => "sham",
});

vocab!(RunVerdict { Pass => "PASS", Fail => "FAIL", Invalid => "INVALID" });

vocab!(VerifierUnderTest { Rewritten => "rewritten", Donor => "donor" });

// SPEC §6. `prompt` is deliberately **not** here — it is rejected at load with the reason
// attached (rule 3), because `PermissionMode` derives `Ord` at `fc1ea22` with `Prompt` ranked
// above `DangerFullAccess`, so a `Prompt` session auto-approves everything. The trap is that
// the variant reads as "prompt me" and does the opposite.
vocab!(PermissionMode {
    ReadOnly => "read_only", WorkspaceWrite => "workspace_write",
    DangerFullAccess => "danger_full_access", Allow => "allow",
});

// ---------------------------------------------------------------------------
// Task
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct Task {
    pub id: String,
    pub title: String,
    pub lang: Lang,
    pub kind: String,
    pub timeout_s: u32,
    pub turns: Vec<Turn>,
    pub verify: Verify,
    pub disposition: Disposition,
    pub selection: Selection,
    pub gate: Gate,
    pub provenance: Provenance,
    pub donor_tags: BTreeMap<String, String>,
    /// Merged per SPEC §5: suite defaults, overridden or extended by `variants.toml`.
    pub variants: Vec<Variant>,
    /// What gets copied into the subject's work dir, and the only path list that ever should.
    pub workdir: crate::workdir::WorkdirPlan,
    pub dir: PathBuf,
    /// Private, and the privacy is the feature — see the accessors below.
    pub(crate) gate_dirs: GateDirs,
}

/// Which gate-time directories a task ships. Presence, never a path.
#[derive(Debug, Clone, Copy, Default)]
pub(crate) struct GateDirs {
    pub refsol: bool,
    pub sham: bool,
    pub stub: bool,
}

impl GateDirs {
    pub(crate) fn probe(dir: &std::path::Path) -> GateDirs {
        GateDirs {
            refsol: dir.join("refsol").is_dir(),
            sham: dir.join("sham").is_dir(),
            stub: dir.join("stub").is_dir(),
        }
    }
}

impl Task {
    // SPEC §2: "`refsol/`, `sham/` and `stub/` are gate-time only. The runner must never copy
    // them into a workdir the subject can see; a loader that cannot guarantee that must refuse
    // to run." These three report presence and **do not hand out a path**. A runner that cannot
    // name the directory cannot copy it by accident, which is a stronger guarantee than a
    // comment asking it not to. Gate execution belongs to the importer (step 2) and the sham
    // authoring (step 4), neither of which goes through this loader.
    pub fn has_refsol(&self) -> bool { self.gate_dirs.refsol }
    pub fn has_sham(&self) -> bool { self.gate_dirs.sham }
    pub fn has_stub(&self) -> bool { self.gate_dirs.stub }

    /// The absolute path of the verifier, or `None` for `[verify].kind = "none"` (F13: ten U100
    /// tasks carry `validation: null` and were scored on the agent-execution success flag).
    pub fn verify_script(&self) -> Option<PathBuf> {
        match &self.verify {
            Verify::Script(rel) => Some(self.dir.join(rel)),
            Verify::None => None,
        }
    }

    pub fn variant(&self, id: &str) -> Option<&Variant> {
        self.variants.iter().find(|v| v.id == id)
    }
}

#[derive(Debug, Clone)]
pub enum Turn {
    /// Resolved to an absolute path at load; rule 4 rejects one that does not.
    SendFile(PathBuf),
    SendText(String),
}

#[derive(Debug, Clone)]
pub enum Verify {
    Script(String),
    None,
}

#[derive(Debug, Clone, Copy)]
pub struct Disposition {
    pub verifiable: Verifiable,
    pub quarantine: Quarantine,
}

#[derive(Debug, Clone, Copy, Default)]
pub struct Selection {
    /// R9's rename of `hardest`: "hardest" reads as *where a sham is most likely to pass*.
    pub gate3: bool,
    pub gate3_rank: Option<u32>,
}

#[derive(Debug, Clone)]
pub struct Gate {
    pub point1: GateVerdict,
    pub point2: GateVerdict,
    pub point3: GateVerdict,
    pub evidence: Vec<Evidence>,
}

#[derive(Debug, Clone)]
pub struct Evidence {
    pub point: u8,
    pub tier: GateTier,
    pub verdict: RunVerdict,
    pub detail: String,
    /// SPEC §9: `rewritten` is the authoritative column. A gate result measured against the
    /// donor's verifier does not describe the verifier this corpus runs.
    pub verifier: VerifierUnderTest,
    pub run: String,
}

#[derive(Debug, Clone)]
pub struct Provenance {
    pub donor: String,
    pub donor_id: Option<String>,
    pub donor_commit: Option<String>,
    pub donor_path: Option<String>,
    pub imported_at: Option<String>,
    pub verbatim: Vec<String>,
    pub rewritten: Vec<String>,
    pub synthesized: Vec<String>,
    pub caveats: Vec<String>,
}

/// SPEC §3. Closed by design, and it is only *because* it is closed that "the three lists
/// partition it" is a checkable claim at all (rule 10). Adding a name is a `schema` bump.
pub const PARTITION: &[&str] = &[
    "id", "title", "lang", "kind", "timeout_s", "turn", "prompt", "fixture", "verify",
    "refsol", "sham", "variants", "disposition", "selection", "gate", "donor_tags",
];

// ---------------------------------------------------------------------------
// Variants — SPEC §5
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VariantOrigin {
    /// Declared in `suite.toml` and inherited unchanged.
    Suite,
    /// A `variants.toml` entry whose id already existed: replaces the suite one *entirely*.
    /// No field-level merge — a partial merge of an ordered rule list is not readable in a diff.
    TaskOverride,
    /// A `variants.toml` entry with a new id: appended after the inherited ones.
    TaskNew,
}

impl VariantOrigin {
    pub fn as_str(self) -> &'static str {
        match self {
            VariantOrigin::Suite => "suite",
            VariantOrigin::TaskOverride => "task-override",
            VariantOrigin::TaskNew => "task-new",
        }
    }
}

#[derive(Debug, Clone)]
pub struct Variant {
    pub id: String,
    pub mode: PermissionMode,
    pub requires: Vec<String>,
    pub expect: Expect,
    /// Declaration order is match order: first matching rule wins.
    pub operator: Vec<OperatorRule>,
    /// Answers any gate no rule matched, and every use increments `unscripted_gates`. It exists
    /// so a stray gate cannot deadlock the session on stdin until the timeout burns.
    pub default: Option<Action>,
    pub origin: VariantOrigin,
}

#[derive(Debug, Clone)]
pub struct OperatorRule {
    pub on: Matcher,
    pub action: Action,
    /// How often the rule may fire. `None` is unlimited; an exhausted rule stops matching and
    /// the next one is tried.
    pub times: Option<u32>,
}

/// v1 has exactly one event class. Rules are event-triggered, never turn- or clock-triggered:
/// the subject decides when it calls a tool, and nothing else is reliably schedulable.
#[derive(Debug, Clone, Default)]
pub struct Matcher {
    pub gate: GateMatcher,
}

#[derive(Debug, Clone, Default)]
pub struct GateMatcher {
    pub tool: Option<String>,
    /// A substring of the tool input as previewed on stderr.
    pub input_contains: Option<String>,
}

impl GateMatcher {
    /// `{ gate = {} }` matches any permission gate.
    pub fn matches(&self, tool: &str, input_preview: &str) -> bool {
        self.tool.as_deref().is_none_or(|t| t == tool)
            && self.input_contains.as_deref().is_none_or(|s| input_preview.contains(s))
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Action {
    Approve,
    Deny,
    Redirect(String),
}

impl Action {
    pub fn label(&self) -> &str {
        match self {
            Action::Approve => "approve",
            Action::Deny => "deny",
            Action::Redirect(_) => "redirect",
        }
    }
}

/// SPEC §5: an `expect` violation is `INVALID`, not `FAIL`. A run where the gate never fired did
/// not measure the thing; scoring it as a failure would be a lie in the direction that flatters
/// 2.0.
#[derive(Debug, Clone, Default)]
pub struct Expect {
    pub gate_fires: Option<Bound>,
    /// Gates that fired **strictly after** the first `deny` the operator track delivered. F36:
    /// `gate_fires = { min = 2 }` cannot say "re-proposed after being refused" — a run that fired
    /// five gates, four of them exploratory `bash`, satisfied it while the denial was the session's
    /// last gate. See SPEC §5.
    pub gate_fires_after_deny: Option<Bound>,
    pub interventions_delivered: Option<u32>,
    pub unscripted_gates: Option<Bound>,
}

/// What a run actually did, for checking against [`Expect`].
///
/// A struct rather than four positional `u32`s: the counters are interchangeable at the type level
/// and three of them are already easy to transpose. A silently swapped pair would move a cell
/// between `invalid` and `pass` with nothing to show for it.
#[derive(Debug, Clone, Copy, Default)]
pub struct Observed {
    pub gate_fires: u32,
    pub gate_fires_after_deny: u32,
    pub interventions_delivered: u32,
    pub unscripted_gates: u32,
}

#[derive(Debug, Clone, Copy, Default)]
pub struct Bound {
    pub min: Option<u32>,
    pub max: Option<u32>,
}

impl Bound {
    pub fn holds(&self, n: u32) -> bool {
        self.min.is_none_or(|m| n >= m) && self.max.is_none_or(|m| n <= m)
    }
}

impl Expect {
    /// Returns the first violated expectation, if any, as a sentence fit for an `INVALID` reason.
    pub fn violation(&self, obs: Observed) -> Option<String> {
        if let Some(b) = self.gate_fires
            && !b.holds(obs.gate_fires)
        {
            return Some(format!("gate_fires = {}, expected {}", obs.gate_fires, describe(&b)));
        }
        if let Some(b) = self.gate_fires_after_deny
            && !b.holds(obs.gate_fires_after_deny)
        {
            return Some(format!(
                "gate_fires_after_deny = {}, expected {} (of {} gates in total)",
                obs.gate_fires_after_deny,
                describe(&b),
                obs.gate_fires
            ));
        }
        if let Some(n) = self.interventions_delivered
            && n != obs.interventions_delivered
        {
            return Some(format!(
                "interventions_delivered = {}, expected {n}",
                obs.interventions_delivered
            ));
        }
        if let Some(b) = self.unscripted_gates
            && !b.holds(obs.unscripted_gates)
        {
            return Some(format!(
                "unscripted_gates = {}, expected {}",
                obs.unscripted_gates,
                describe(&b)
            ));
        }
        None
    }
}

fn describe(b: &Bound) -> String {
    match (b.min, b.max) {
        (Some(lo), Some(hi)) => format!("{lo}..={hi}"),
        (Some(lo), None) => format!(">= {lo}"),
        (None, Some(hi)) => format!("<= {hi}"),
        (None, None) => "anything".into(),
    }
}

// ---------------------------------------------------------------------------
// Suite and subject — SPEC §4, §7
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct Suite {
    pub id: String,
    pub title: String,
    pub caveats: Vec<String>,
    pub aggregate: AggregateRule,
    /// Retry-once-on-timeout is deliberately absent from the donor's behaviour here: the warmup
    /// turn required by RUNMETA removes the cause it existed for (F10), and a retry would hide a
    /// real timeout as difficulty signal (F12).
    pub retry_on_timeout: bool,
    pub expected_tasks: Option<usize>,
    pub tasks: Vec<Task>,
    pub dir: PathBuf,
}

/// SPEC §10. Which dispositions enter a headline number. Flipping this re-scores without
/// re-importing — that is what carrying disposition as a field rather than a fork buys.
#[derive(Debug, Clone)]
pub struct AggregateRule {
    pub include_verifiable: Vec<Verifiable>,
    pub exclude_quarantined: bool,
}

impl AggregateRule {
    pub fn counts(&self, d: &Disposition) -> bool {
        self.include_verifiable.contains(&d.verifiable)
            && !(self.exclude_quarantined && d.quarantine != Quarantine::None)
    }

    /// The sentence every published number has to carry with it. SPEC §10: "any published number
    /// must state the rule it was computed under."
    pub fn describe(&self) -> String {
        let inc: Vec<&str> = self.include_verifiable.iter().map(|v| v.as_str()).collect();
        format!(
            "include_verifiable = [{}], exclude_quarantined = {}",
            inc.join(", "),
            self.exclude_quarantined
        )
    }
}

#[derive(Debug, Clone)]
pub struct Subject {
    pub id: String,
    pub version: String,
    /// The subject's own commit. SPEC §11 lists it among the RUNMETA row's required fields, and it
    /// is what makes "measured against Claudette" mean a specific tree. The first version of this
    /// loader dropped the key — `subjects/claudette-fc1ea22.toml` carries `commit = "fc1ea22"` and
    /// nothing read it, so the runner's RUNMETA wrote an empty string for a required field. Optional
    /// because SPEC §7's example does not show it and a descriptor without one is still valid.
    pub commit: Option<String>,
    pub bin: String,
    /// `repl-pipe`, never one-shot: one-shot passes `None` for its prompter (`run.rs:186`), so it
    /// cannot edit a file without `CLAUDETTE_AUTO_APPROVE` and can never show a gate (F1).
    pub drive: String,
    pub capabilities: Vec<String>,
    pub env: BTreeMap<String, String>,
    pub markers: Markers,
    /// How this subject receives a prompt whose text contains newlines, or `None` if it cannot.
    /// A runner must read the pair from here rather than knowing any subject's strings: the whole
    /// point of a descriptor is that a second subject can differ.
    pub delivery: Option<BlockDelivery>,
    pub path: PathBuf,
}

/// A subject's sentinel pair for delivering a multi-line prompt as one turn.
///
/// Claudette gained this on 2026-08-08 (David's call: fix the subject rather than rewrite 69 of
/// the 90 U100 prompts). Before it, no path existed — the piped REPL read one line per turn, paste
/// stripped newlines, and one-shot had no permission prompter — so 69 tasks were undeliverable.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BlockDelivery {
    /// The line that opens a block. Must be alone on its line and match exactly.
    pub open: String,
    /// The line that closes it.
    pub close: String,
}

#[derive(Debug, Clone, Default)]
pub struct Markers {
    /// The gate prompt has no trailing newline (`write!`, not `writeln!`,
    /// `cli_prompter.rs:84`), so a line-buffered reader blocks on it forever. Match the suffix.
    pub gate: String,
    /// The only turn boundary, because piped mode never echoes `❯` (`line_editor.rs:370-376`).
    pub turn_end: String,
}
