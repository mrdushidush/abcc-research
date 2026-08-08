//! Metrics, RUNMETA and the JSONL these are written as — SPEC §11.
//!
//! Three things the shape here is defending against, all of them silent (F9):
//!
//! 1. `in=`/`out=` are **session-cumulative and summed per iteration**, not per turn. Cost per task
//!    is the *final* line of a fresh session; cost per turn is the delta. Summing the lines over a
//!    3-turn session gave 29,371 against a true 14,701. So [`Cell::tokens_in`] is set from the last
//!    turn's marker and never accumulated.
//! 2. Sessions must start fresh, or the restored seed has to be subtracted
//!    (`conversation.rs:287`). Every cell gets its own process, and `--resume` is never passed.
//! 3. The `ctx ~N/32k` gauge is not cost — it omits the system prompt and tool schemas by design
//!    (the gauge read `~7` while real input was 4,885). It is not read at all.
//!
//! `Metric::NotApplicable` and `Metric::NotSupported` are distinct on purpose: `n/a` from an
//! unsupported capability is where 2.0's differentiator has to appear, and it must never round to
//! zero (SPEC §7).

use std::collections::BTreeMap;
use std::fmt::Write as _;

use crate::endpoint::json_quote;

#[derive(Debug, Clone)]
pub enum Metric {
    Measured(f64),
    NotApplicable { reason: String },
    NotSupported { capability: String },
}

impl Metric {
    fn to_json(&self) -> String {
        match self {
            Metric::Measured(v) => {
                if v.fract() == 0.0 && v.abs() < 9.0e15 {
                    format!("{{\"measured\":{}}}", *v as i64)
                } else {
                    format!("{{\"measured\":{v}}}")
                }
            }
            Metric::NotApplicable { reason } => {
                format!("{{\"not_applicable\":{}}}", json_quote(reason))
            }
            Metric::NotSupported { capability } => {
                format!("{{\"not_supported\":{}}}", json_quote(capability))
            }
        }
    }
}

/// SPEC §11's status vocabulary. `Invalid` is load-bearing: an `expect` violation, an unanswerable
/// gate or a verifier that never ran are all "this run did not measure the thing", and scoring any
/// of them as `Fail` would be a lie in the direction that flatters the subject.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Status {
    Pass,
    Fail,
    Invalid,
    NotSupported,
    Timeout,
    Error,
}

impl Status {
    pub fn as_str(self) -> &'static str {
        match self {
            Status::Pass => "pass",
            Status::Fail => "fail",
            Status::Invalid => "invalid",
            Status::NotSupported => "not_supported",
            Status::Timeout => "timeout",
            Status::Error => "error",
        }
    }
}

#[derive(Debug, Clone)]
pub struct Cell {
    pub suite: String,
    pub task: String,
    pub variant: String,
    pub subject: String,
    pub status: Status,
    pub reason: Option<String>,
    pub verifier_verdict: Option<String>,
    pub verifier_message: Option<String>,
    pub metrics: BTreeMap<String, Metric>,
    pub gate_fires: u32,
    pub interventions_delivered: u32,
    pub unscripted_gates: u32,
    pub gate_actions: Vec<(u64, String, String, Option<usize>)>,
    pub delivery_mode: String,
    pub prompt_lines: usize,
    pub delivery_faithful: bool,
    /// The variant's `permissions.mode`, and whether `CLAUDETTE_AUTO_APPROVE` was set for **this
    /// cell**. Both live here rather than in RUNMETA because they are variant-scoped: see
    /// [`crate::env::PER_CELL_KEYS`] for the run this got wrong.
    pub permission_mode: String,
    pub auto_approve: bool,
    pub disposition: String,
    pub in_aggregate: bool,
    pub workdir: String,
    pub transcript: String,
    pub startup_ms: u64,
}

impl Cell {
    pub fn to_json(&self) -> String {
        let mut s = String::new();
        s.push('{');
        let _ = write!(s, "\"suite\":{}", json_quote(&self.suite));
        let _ = write!(s, ",\"task\":{}", json_quote(&self.task));
        let _ = write!(s, ",\"variant\":{}", json_quote(&self.variant));
        let _ = write!(s, ",\"subject\":{}", json_quote(&self.subject));
        let _ = write!(s, ",\"status\":{}", json_quote(self.status.as_str()));
        if let Some(r) = &self.reason {
            let _ = write!(s, ",\"reason\":{}", json_quote(r));
        }
        match (&self.verifier_verdict, &self.verifier_message) {
            (Some(v), m) => {
                let _ = write!(
                    s,
                    ",\"verifier\":{{\"verdict\":{},\"message\":{}}}",
                    json_quote(v),
                    json_quote(m.as_deref().unwrap_or(""))
                );
            }
            _ => s.push_str(",\"verifier\":null"),
        }
        s.push_str(",\"metrics\":{");
        for (i, (k, v)) in self.metrics.iter().enumerate() {
            if i > 0 {
                s.push(',');
            }
            let _ = write!(s, "{}:{}", json_quote(k), v.to_json());
        }
        s.push('}');
        let _ = write!(
            s,
            ",\"operator\":{{\"gate_fires\":{},\"interventions_delivered\":{},\
             \"unscripted_gates\":{},\"actions\":[",
            self.gate_fires, self.interventions_delivered, self.unscripted_gates
        );
        for (i, (at, tool, action, rule)) in self.gate_actions.iter().enumerate() {
            if i > 0 {
                s.push(',');
            }
            let _ = write!(
                s,
                "{{\"at_ms\":{at},\"tool\":{},\"action\":{},\"rule\":{}}}",
                json_quote(tool),
                json_quote(action),
                rule.map_or("null".to_string(), |r| r.to_string())
            );
        }
        s.push_str("]}");
        let _ = write!(
            s,
            ",\"delivery\":{{\"mode\":{},\"prompt_lines\":{},\"faithful\":{}}}",
            json_quote(&self.delivery_mode),
            self.prompt_lines,
            self.delivery_faithful
        );
        let _ = write!(
            s,
            ",\"permissions\":{{\"mode\":{},\"auto_approve\":{}}}",
            json_quote(&self.permission_mode),
            self.auto_approve
        );
        let _ = write!(
            s,
            ",\"disposition\":{},\"in_aggregate\":{}",
            json_quote(&self.disposition),
            self.in_aggregate
        );
        let _ = write!(s, ",\"startup_ms\":{}", self.startup_ms);
        let _ = write!(s, ",\"workdir\":{}", json_quote(&self.workdir));
        let _ = write!(s, ",\"transcript\":{}", json_quote(&self.transcript));
        s.push('}');
        s
    }
}

/// RUNMETA. **Required, not best-effort** — a held constant nobody measures is not held, and the
/// Q56 campaign lost two nights to exactly that.
#[derive(Debug, Clone)]
pub struct RunMeta {
    pub run_id: String,
    pub started_unix_ms: u128,
    pub subject_id: String,
    pub subject_version: String,
    pub subject_commit: String,
    pub subject_bin: String,
    pub subject_drive: String,
    pub corpus_root: String,
    pub corpus_commit: String,
    /// A cell measured against an edited corpus is not reproducible from a commit, so the state of
    /// the tree is part of the row rather than a footnote.
    pub corpus_dirty: bool,
    pub model_requested: String,
    /// **What the endpoint said it actually used.** LM Studio answers a request naming a model it
    /// does not have with whichever model is loaded, so the requested id alone is not evidence.
    pub model_confirmed: String,
    pub num_ctx: u32,
    pub num_predict: u32,
    pub max_iterations: u32,
    pub max_tools: Option<u32>,
    pub endpoint: String,
    pub platform: String,
    /// The interpreters as **probed by execution**, not as named in the environment. A verifier's
    /// verdict is only transferable to another host alongside the interpreter that produced it.
    pub bash: String,
    pub python: String,
    pub node: Option<String>,
    /// It must have run: on the champion, turn 1 took 169.7 s against 4.1 s and 3.7 s for turns
    /// 2-3, and since corpora run in a fixed order the same unlucky task eats that JIT load every
    /// time (F10).
    pub warmup: bool,
    pub warmup_prompt: String,
    pub warmup_wall_ms: u64,
    /// The warmup turn's `in=`: Claudette's fixed per-turn overhead plus the warmup prompt, so an
    /// upper bound on the preamble. Worth its own number because it is the part 2.0 attacks
    /// directly, and because reporting `tokens_in` without separating it credits or blames the
    /// model for the harness's preamble.
    pub preamble_tokens_in: u64,
    pub delivery_mode: String,
    pub aggregate_rule: String,
    /// **Run-scoped pins only.** The variant-scoped ones are on the cell — see
    /// [`crate::env::PER_CELL_KEYS`].
    pub env_pinned: BTreeMap<String, String>,
    pub env_removed: Vec<String>,
}

impl RunMeta {
    pub fn to_json(&self) -> String {
        let mut s = String::new();
        s.push('{');
        let _ = write!(s, "\"run_id\":{}", json_quote(&self.run_id));
        let _ = write!(s, ",\"started_unix_ms\":{}", self.started_unix_ms);
        let _ = write!(
            s,
            ",\"subject\":{{\"id\":{},\"version\":{},\"commit\":{},\"bin\":{},\"drive\":{}}}",
            json_quote(&self.subject_id),
            json_quote(&self.subject_version),
            json_quote(&self.subject_commit),
            json_quote(&self.subject_bin),
            json_quote(&self.subject_drive)
        );
        let _ = write!(
            s,
            ",\"corpus\":{{\"root\":{},\"commit\":{},\"dirty\":{}}}",
            json_quote(&self.corpus_root),
            json_quote(&self.corpus_commit),
            self.corpus_dirty
        );
        let _ = write!(
            s,
            ",\"held\":{{\"model_requested\":{},\"model_confirmed\":{},\"num_ctx\":{},\
             \"num_predict\":{},\"max_iterations\":{},\"max_tools\":{},\"endpoint\":{}}}",
            json_quote(&self.model_requested),
            json_quote(&self.model_confirmed),
            self.num_ctx,
            self.num_predict,
            self.max_iterations,
            self.max_tools.map_or("null".to_string(), |n| n.to_string()),
            json_quote(&self.endpoint)
        );
        let _ = write!(
            s,
            ",\"warmup\":{{\"ran\":{},\"prompt\":{},\"wall_ms\":{},\"preamble_tokens_in\":{}}}",
            self.warmup,
            json_quote(&self.warmup_prompt),
            self.warmup_wall_ms,
            self.preamble_tokens_in
        );
        let _ = write!(
            s,
            ",\"platform\":{},\"interpreters\":{{\"bash\":{},\"python\":{},\"node\":{}}}",
            json_quote(&self.platform),
            json_quote(&self.bash),
            json_quote(&self.python),
            self.node.as_ref().map_or("null".to_string(), |n| json_quote(n))
        );
        let _ = write!(s, ",\"delivery_mode\":{}", json_quote(&self.delivery_mode));
        let _ = write!(s, ",\"aggregate_rule\":{}", json_quote(&self.aggregate_rule));
        // `scope` is not decoration: a reader has to know this block does not describe
        // CLAUDETTE_AUTO_APPROVE, which changes per variant.
        s.push_str(",\"env\":{\"scope\":\"run\",\"pinned\":{");
        for (i, (k, v)) in self.env_pinned.iter().enumerate() {
            if i > 0 {
                s.push(',');
            }
            let _ = write!(s, "{}:{}", json_quote(k), json_quote(v));
        }
        s.push_str("},\"removed\":[");
        for (i, k) in self.env_removed.iter().enumerate() {
            if i > 0 {
                s.push(',');
            }
            s.push_str(&json_quote(k));
        }
        s.push_str("]}}");
        s
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::endpoint::json_string_field;

    fn cell() -> Cell {
        let mut metrics = BTreeMap::new();
        metrics.insert("ttfvo_ms".to_string(), Metric::Measured(25902.0));
        metrics.insert(
            "peak_rss_mb".to_string(),
            Metric::NotApplicable { reason: "no probe exists yet (W1/W2 owns building it)".into() },
        );
        metrics.insert(
            "interventions_delivered".to_string(),
            Metric::NotSupported { capability: "redirect".into() },
        );
        Cell {
            suite: "u100".into(),
            task: "fix_sql_inject".into(),
            variant: "control".into(),
            subject: "claudette-fc1ea22".into(),
            status: Status::Pass,
            reason: None,
            verifier_verdict: Some("PASS".into()),
            verifier_message: Some("donor assertions \"held\"".into()),
            metrics,
            gate_fires: 0,
            interventions_delivered: 0,
            unscripted_gates: 0,
            gate_actions: vec![(1234, "apply_diff".into(), "redirect".into(), Some(0))],
            delivery_mode: "verbatim".into(),
            prompt_lines: 1,
            delivery_faithful: true,
            permission_mode: "allow".into(),
            auto_approve: true,
            disposition: "full/with_baseline".into(),
            in_aggregate: false,
            workdir: "C:\\tmp\\w8\\wd".into(),
            transcript: "C:\\tmp\\w8\\t.log".into(),
            startup_ms: 512,
        }
    }

    #[test]
    fn the_three_metric_arms_serialise_distinguishably() {
        // `not_supported` collapsing into `0` or into `not_applicable` is the failure SPEC §7 calls
        // out: that column is where 2.0's differentiator has to appear.
        let j = cell().to_json();
        assert!(j.contains("\"ttfvo_ms\":{\"measured\":25902}"), "{j}");
        assert!(j.contains("\"not_applicable\":"), "{j}");
        assert!(j.contains("\"not_supported\":\"redirect\""), "{j}");
    }

    #[test]
    fn quotes_and_backslashes_in_a_verifier_message_survive() {
        // Windows paths and quoted assertion text both appear in real verifier output; a naive
        // writer produces a line no reader can parse and the cell silently disappears from a report.
        let j = cell().to_json();
        assert!(j.contains("C:\\\\tmp\\\\w8\\\\wd"), "{j}");
        assert_eq!(json_string_field(&j, "message").unwrap(), "donor assertions \"held\"");
    }

    #[test]
    fn the_cell_carries_the_permission_mode_that_actually_applied_to_it() {
        let j = cell().to_json();
        assert!(j.contains("\"permissions\":{\"mode\":\"allow\",\"auto_approve\":true}"), "{j}");
    }

    #[test]
    fn a_cell_is_exactly_one_jsonl_line() {
        let j = cell().to_json();
        assert!(!j.contains('\n'), "a JSONL record must not contain a raw newline");
    }

    #[test]
    fn a_null_verifier_is_written_as_null_not_omitted() {
        // `[verify].kind = "none"` — ten U100 tasks (F13). An omitted key reads as "not measured
        // yet"; null reads as "there was nothing to run".
        let mut c = cell();
        c.verifier_verdict = None;
        c.verifier_message = None;
        assert!(c.to_json().contains("\"verifier\":null"));
    }

    #[test]
    fn runmeta_carries_both_the_requested_and_the_confirmed_model() {
        let m = RunMeta {
            run_id: "r1".into(),
            started_unix_ms: 1,
            subject_id: "claudette-fc1ea22".into(),
            subject_version: "0.17.0".into(),
            subject_commit: "fc1ea22".into(),
            subject_bin: "claudette".into(),
            subject_drive: "repl-pipe".into(),
            corpus_root: "corpus".into(),
            corpus_commit: "b9967f4".into(),
            corpus_dirty: false,
            model_requested: "qwen3.6-35b-a3b-mtp@iq3_s".into(),
            model_confirmed: "qwen3.6-35b-a3b-mtp@iq3_s".into(),
            num_ctx: 61440,
            num_predict: 8192,
            max_iterations: 40,
            max_tools: None,
            endpoint: "http://localhost:1234".into(),
            platform: "windows/x86_64".into(),
            bash: "C:/Program Files/Git/bin/bash.exe".into(),
            python: "python".into(),
            node: Some("node".into()),
            warmup: true,
            warmup_prompt: crate::env::WARMUP_PROMPT.into(),
            warmup_wall_ms: 169_700,
            preamble_tokens_in: 4885,
            delivery_mode: "verbatim".into(),
            aggregate_rule: "include_verifiable = [full, presence_only], exclude_quarantined = true"
                .into(),
            env_pinned: [("CLAUDETTE_FALLBACK_BRAIN_MODEL".to_string(), String::new())]
                .into_iter()
                .collect(),
            env_removed: vec!["CLAUDETTE_AUTO_APPROVE".into()],
        };
        let j = m.to_json();
        assert!(j.contains("\"model_confirmed\":\"qwen3.6-35b-a3b-mtp@iq3_s\""), "{j}");
        assert!(j.contains("\"preamble_tokens_in\":4885"), "{j}");
        // The pin that stops a stuck signal escalating a second model into a measured turn has to
        // be visible in the record, or nobody can tell whether a run held it.
        assert!(j.contains("\"CLAUDETTE_FALLBACK_BRAIN_MODEL\":\"\""), "{j}");
        // The env block must say what it covers: it is built from the warmup and does NOT describe
        // the variant-scoped CLAUDETTE_AUTO_APPROVE.
        assert!(j.contains("\"scope\":\"run\""), "{j}");
        assert!(!j.contains('\n'));
    }
}
