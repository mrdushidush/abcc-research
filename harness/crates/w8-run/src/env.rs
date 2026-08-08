//! The child environment, and the reason this module is bigger than it looks.
//!
//! Claudette loads `~/.claudette/.env` at startup (`main.rs:264-279`) through
//! `dotenvy::from_path`, whose `load()` is
//!
//! ```text
//! if env::var(&key).is_err() { env::set_var(&key, value); }   // dotenvy-0.15.7/src/iter.rs:34
//! ```
//!
//! — **non-overriding**. So a variable this runner sets explicitly wins, and a variable it leaves
//! unset is supplied by David's personal daily-driver config. Confirmed by execution as well as by
//! reading: an `OLLAMA_HOST` passed from the parent beat the `.env` value and the turn failed
//! against the dead port.
//!
//! That makes the .env a live contamination channel for *exactly* the constants a baseline has to
//! hold, and the host file really does carry them — `CLAUDETTE_MODEL`, `CLAUDETTE_NUM_CTX`,
//! `CLAUDETTE_NUM_PREDICT`, `CLAUDETTE_FALLBACK_BRAIN_MODEL`, `CLAUDETTE_MAX_TOOLS`,
//! `OLLAMA_HOST`. SPEC §11's "a held constant nobody measures is not held" therefore has a
//! sharper form here: **a held constant nobody *sets* is not held, it is inherited**, and it would
//! be inherited silently and differently on another machine.
//!
//! Everything below is pinned for that reason, and every pinned value is written into RUNMETA.

use std::collections::BTreeMap;
use std::path::Path;

use w8_corpus::{PermissionMode, Subject, Variant};

/// The run-scoped constants. None of these belong in the subject descriptor: the subject is
/// Claudette, and the model, the context window and the endpoint are properties of the *run*.
#[derive(Debug, Clone)]
pub struct Held {
    pub model: String,
    pub num_ctx: u32,
    pub num_predict: u32,
    pub max_iterations: u32,
    /// `None` means "no cap", which is Claudette's own default (`api.rs:309-320`). Pinned either
    /// way, because the tools array is part of every request and therefore part of the preamble.
    pub max_tools: Option<u32>,
    /// `OLLAMA_HOST`. Plain HTTP, localhost by default.
    pub endpoint: String,
}

impl Default for Held {
    fn default() -> Self {
        Held {
            // No default model on purpose — see main.rs. Naming one here is how a convenience 4b
            // ends up in a baseline.
            model: String::new(),
            // David's daily driver, not the donor's 32768. Recorded, never assumed.
            num_ctx: 61440,
            num_predict: 8192,
            max_iterations: 40,
            max_tools: None,
            endpoint: "http://localhost:1234".to_string(),
        }
    }
}

/// A resolved child environment: what is set, and what is deliberately taken away.
#[derive(Debug, Clone, Default)]
pub struct ChildEnv {
    pub pinned: BTreeMap<String, String>,
    pub removed: Vec<String>,
}

/// Keys whose value is a property of **one cell**, not of the run.
///
/// They are excluded from the RUNMETA snapshot, and the reason is a defect this crate shipped for
/// about an hour. RUNMETA's env block was taken from the warmup session — and the warmup always runs
/// in `allow` mode, so it always pins `CLAUDETTE_AUTO_APPROVE=1`. The row therefore stated that every
/// cell in the run had auto-approve on, while the gated cells had it *removed*. Silent, and in the
/// flattering direction for anything reading the run as a gate measurement. The per-cell truth now
/// lives on the cell as `permission_mode` and `auto_approve`.
pub const PER_CELL_KEYS: &[&str] = &["CLAUDETTE_AUTO_APPROVE", "CLAUDETTE_WORKSPACE"];

#[derive(Debug)]
pub enum EnvError {
    /// SPEC §6 admits four permission modes. Only two of them are reachable on this subject.
    ModeUnreachable { mode: PermissionMode, why: String },
    /// The subject descriptor's `[env]` sets a key the runner pins. Rather than let one silently
    /// win, say so: the corpus and the runner disagreeing about a held constant is the whole
    /// failure this module exists to prevent.
    Conflict { key: String, subject: String, pinned: String },
}

impl std::fmt::Display for EnvError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            EnvError::ModeUnreachable { mode, why } => {
                write!(f, "permissions.mode = \"{mode}\" is not reachable on this subject: {why}")
            }
            EnvError::Conflict { key, subject, pinned } => write!(
                f,
                "subject [env] sets {key} = {subject:?} but the runner pins it to {pinned:?}; \
                 one of the two is wrong and the runner will not pick silently"
            ),
        }
    }
}

/// The warmup prompt. Held constant, and it has to be: `preamble_tokens_in` is the warmup turn's
/// `in=`, which is Claudette's fixed per-turn overhead **plus this string**, so it is comparable
/// across subjects only while the string does not move (SPEC §11).
pub const WARMUP_PROMPT: &str = "Reply with the single word: ready.";

/// Build the child environment for one cell.
///
/// `memory_stub` is an empty file the caller has created. It is pinned as `CLAUDETTE_MEMORY`
/// because `try_load_memory` (`memory.rs:59`, via `default_memory_path` at `:26`) folds
/// `~/.claudette/CLAUDETTE.MD` into the system prompt when it exists — so a file appearing in
/// David's home directory would move `preamble_tokens_in` for every future run and nothing would
/// say so. An empty file reads back as `None` (`memory.rs:68-71`). Note that `CLAUDETTE_MEMORY=""`
/// would NOT work: the empty case falls through to the host path (`memory.rs:27-31`).
pub fn build(
    subject: &Subject,
    variant: &Variant,
    held: &Held,
    workdir: &Path,
    memory_stub: &Path,
) -> Result<ChildEnv, EnvError> {
    let mut pinned: BTreeMap<String, String> = BTreeMap::new();
    let mut removed: Vec<String> = Vec::new();

    // ── The model and the endpoint ──────────────────────────────────────────
    pinned.insert("CLAUDETTE_MODEL".into(), held.model.clone());
    pinned.insert("CLAUDETTE_NUM_CTX".into(), held.num_ctx.to_string());
    pinned.insert("CLAUDETTE_NUM_PREDICT".into(), held.num_predict.to_string());
    pinned.insert("OLLAMA_HOST".into(), held.endpoint.clone());

    // The default preset is `Auto`, which is qwen3.5:4b with **qwen3.5:9b wired as a fallback**
    // (`model_config.rs`, `Preset::Auto`), and `CLAUDETTE_MODEL` replaces only the brain
    // (`merge_env`, `:186-188`) — the fallback survives. Every REPL turn then goes through
    // `brain_selector::run_turn_with_fallback` (`repl.rs:169-170`), which can escalate mid-turn.
    // An escalation would swap the model underneath a measured task, JIT-load a second one, and
    // report a number attributed to the model named in RUNMETA. The explicit empty string is
    // Claudette's own documented off switch (`model_config.rs:196-200`).
    pinned.insert("CLAUDETTE_FALLBACK_BRAIN_MODEL".into(), String::new());

    // `iter=` is a reported metric and the cap changes it. `CLAUDETTE_MAX_TOOLS` changes the size
    // of the tools array in every request, so it changes `preamble_tokens_in` — and the host .env
    // sets it.
    pinned.insert("CLAUDETTE_MAX_ITERATIONS".into(), held.max_iterations.to_string());
    match held.max_tools {
        Some(n) => {
            pinned.insert("CLAUDETTE_MAX_TOOLS".into(), n.to_string());
        }
        // `api.rs:320` parses the var and falls back to no cap, so removing it is the way to pin
        // "uncapped" — leaving it alone would inherit the host's value.
        None => removed.push("CLAUDETTE_MAX_TOOLS".into()),
    }

    // Recall indexing embeds every turn against the same endpoint on a background thread
    // (`repl.rs:246-247`), and the startup pre-flight (`:91`) JIT-loads the embedding model.
    // Both contend with the measured turn for the same GPU. Disabling it also skips the probe —
    // `probe_recall_at_startup` honours the same flag (`repl.rs:88-90`).
    pinned.insert("CLAUDETTE_RECALL_DISABLE".into(), "1".into());

    pinned.insert("CLAUDETTE_MEMORY".into(), memory_stub.display().to_string());
    pinned.insert("CLAUDETTE_WORKSPACE".into(), workdir.display().to_string());

    // TTY-only, so a no-op on a pipe today (`repl.rs:63-66`). Pinned anyway: it costs nothing and
    // it means a future spinner that forgets the TTY check cannot start writing into the stream
    // the gate marker is matched on.
    pinned.insert("CLAUDETTE_NO_SPINNER".into(), "1".into());

    // ── Permissions: SPEC §6's four modes against a subject that has two ────
    //
    // The REPL's policy is a single chokepoint (`runtime_build.rs:145-149`): the ambient policy is
    // `PermissionPolicy::new(WorkspaceWrite)` (`:442`), and the *only* thing that changes the
    // active mode is `CLAUDETTE_AUTO_APPROVE` (`run.rs:223`), which sets it to `Allow`. There is
    // no CLI flag and no other env var. `ReadOnly` as an active mode exists only as a `max_tier`
    // cap on forge Planner/Verifier (`:288-293`) and the research runtime (`:361`), neither
    // reachable from the REPL; `DangerFullAccess` is a tool *requirement* tier, not something the
    // REPL ever makes active.
    //
    // So two of SPEC §6's four modes are unreachable on `claudette-fc1ea22`, and the honest thing
    // is to refuse the cell by name rather than to map it onto the nearest thing that runs. The
    // corpus uses only the two reachable ones today.
    match variant.mode {
        PermissionMode::Allow => {
            // Required, not optional, and this is the one place SPEC §7's "CLAUDETTE_AUTO_APPROVE
            // is never set" must be read narrowly. That sentence is about the *subject
            // descriptor's* suite-wide [env]; the flag is variant-scoped. The `control` variant is
            // `mode = "allow"` precisely because the donor had no gate in the path at all (F1), so
            // without the flag `control` would gate on its first edit, find no operator rule and
            // no `default` (it declares neither), and score as a harness failure on the one
            // variant whose whole job is to reproduce the imported baseline.
            pinned.insert("CLAUDETTE_AUTO_APPROVE".into(), "1".into());
        }
        PermissionMode::WorkspaceWrite => {
            // The gated variants. Removing rather than ignoring: the host .env does not set this
            // one today, but "the gate is observable" is the premise of every operator-track
            // measurement, and an inherited `1` would silently delete every gate in the run.
            removed.push("CLAUDETTE_AUTO_APPROVE".into());
        }
        PermissionMode::ReadOnly => {
            return Err(EnvError::ModeUnreachable {
                mode: variant.mode,
                why: "the REPL's ambient policy is PermissionPolicy::new(WorkspaceWrite) \
                      (runtime_build.rs:442) and nothing lowers the active mode; ReadOnly appears \
                      only as with_max_tier on forge roles (:288-293) and the research runtime \
                      (:361), neither of which the REPL builds"
                    .into(),
            });
        }
        PermissionMode::DangerFullAccess => {
            return Err(EnvError::ModeUnreachable {
                mode: variant.mode,
                why: "DangerFullAccess is a per-tool requirement tier in build_permission_policy \
                      (runtime_build.rs:439-540), never an active mode the REPL sets; the only \
                      active-mode override is CLAUDETTE_AUTO_APPROVE -> Allow (run.rs:223)"
                    .into(),
            });
        }
    }

    // Forge has its own auto-approve knob. It cannot fire on the REPL path, but it is one
    // `CLAUDETTE_*` name away from the one that can, so it is taken away rather than trusted.
    removed.push("CLAUDETTE_FORGE_AUTO_APPROVE".into());

    // ── The subject descriptor's own [env], last, and checked ───────────────
    for (k, v) in &subject.env {
        if let Some(mine) = pinned.get(k) {
            if mine != v {
                return Err(EnvError::Conflict {
                    key: k.clone(),
                    subject: v.clone(),
                    pinned: mine.clone(),
                });
            }
        }
        if removed.contains(k) {
            return Err(EnvError::Conflict {
                key: k.clone(),
                subject: v.clone(),
                pinned: "<removed>".into(),
            });
        }
        pinned.insert(k.clone(), v.clone());
    }

    Ok(ChildEnv { pinned, removed })
}

impl ChildEnv {
    /// The pins that are the same for every cell in the run — what RUNMETA is entitled to claim.
    pub fn run_scoped(&self) -> BTreeMap<String, String> {
        self.pinned
            .iter()
            .filter(|(k, _)| !PER_CELL_KEYS.contains(&k.as_str()))
            .map(|(k, v)| (k.clone(), v.clone()))
            .collect()
    }

    /// The same filter over the removals.
    pub fn run_scoped_removed(&self) -> Vec<String> {
        self.removed
            .iter()
            .filter(|k| !PER_CELL_KEYS.contains(&k.as_str()))
            .cloned()
            .collect()
    }

    /// Apply to a command. The parent environment is inherited rather than cleared — on Windows a
    /// cleared environment loses `SystemRoot` and `PATH` and the child does not start — so the
    /// pins above are what make the run reproducible, not isolation.
    pub fn apply(&self, cmd: &mut std::process::Command) {
        for (k, v) in &self.pinned {
            cmd.env(k, v);
        }
        for k in &self.removed {
            cmd.env_remove(k);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn subject(env: &[(&str, &str)]) -> Subject {
        Subject {
            id: "claudette-fc1ea22".into(),
            version: "0.17.0".into(),
            commit: Some("fc1ea22".into()),
            bin: "claudette".into(),
            drive: "repl-pipe".into(),
            capabilities: vec!["tool_gate".into(), "redirect".into()],
            env: env.iter().map(|(k, v)| ((*k).to_string(), (*v).to_string())).collect(),
            markers: Default::default(),
            delivery: None,
            path: PathBuf::from("subjects/claudette-fc1ea22.toml"),
        }
    }

    fn variant(mode: PermissionMode) -> Variant {
        Variant {
            id: "v".into(),
            mode,
            requires: vec![],
            expect: Default::default(),
            operator: vec![],
            default: None,
            origin: w8_corpus::VariantOrigin::Suite,
        }
    }

    fn build_ok(mode: PermissionMode, env: &[(&str, &str)]) -> ChildEnv {
        build(
            &subject(env),
            &variant(mode),
            &Held { model: "m".into(), ..Held::default() },
            Path::new("/w"),
            Path::new("/w/.memory"),
        )
        .expect("should build")
    }

    #[test]
    fn allow_sets_auto_approve_and_workspace_write_removes_it() {
        let a = build_ok(PermissionMode::Allow, &[]);
        assert_eq!(a.pinned.get("CLAUDETTE_AUTO_APPROVE").map(String::as_str), Some("1"));
        assert!(!a.removed.contains(&"CLAUDETTE_AUTO_APPROVE".to_string()));

        let w = build_ok(PermissionMode::WorkspaceWrite, &[]);
        assert!(!w.pinned.contains_key("CLAUDETTE_AUTO_APPROVE"));
        assert!(w.removed.contains(&"CLAUDETTE_AUTO_APPROVE".to_string()));
    }

    #[test]
    fn the_two_unreachable_modes_are_refused_by_name() {
        for mode in [PermissionMode::ReadOnly, PermissionMode::DangerFullAccess] {
            let e = build(
                &subject(&[]),
                &variant(mode),
                &Held { model: "m".into(), ..Held::default() },
                Path::new("/w"),
                Path::new("/w/.memory"),
            )
            .expect_err("must refuse");
            match e {
                EnvError::ModeUnreachable { mode: m, why } => {
                    assert_eq!(m, mode);
                    // The refusal has to carry the citation, or the next reader re-derives it.
                    assert!(why.contains("runtime_build.rs") || why.contains("run.rs"), "{why}");
                }
                other => panic!("expected ModeUnreachable, got {other:?}"),
            }
        }
    }

    #[test]
    fn the_fallback_brain_is_switched_off() {
        // The measurement-critical pin: without it a stuck signal can escalate qwen3.5:9b into the
        // middle of a task measured as the champion.
        let e = build_ok(PermissionMode::Allow, &[]);
        assert_eq!(e.pinned.get("CLAUDETTE_FALLBACK_BRAIN_MODEL").map(String::as_str), Some(""));
    }

    #[test]
    fn every_constant_the_host_dotenv_carries_is_pinned_or_removed() {
        // The keys measured in ~/.claudette/.env on 2026-08-08. If Claudette grows another one
        // that matters, this test is where the omission should show up.
        let e = build_ok(PermissionMode::WorkspaceWrite, &[]);
        for key in [
            "CLAUDETTE_MODEL",
            "CLAUDETTE_NUM_CTX",
            "CLAUDETTE_NUM_PREDICT",
            "CLAUDETTE_FALLBACK_BRAIN_MODEL",
            "OLLAMA_HOST",
        ] {
            assert!(e.pinned.contains_key(key), "{key} is not pinned");
        }
        assert!(
            e.pinned.contains_key("CLAUDETTE_MAX_TOOLS")
                || e.removed.contains(&"CLAUDETTE_MAX_TOOLS".to_string()),
            "CLAUDETTE_MAX_TOOLS is neither pinned nor removed"
        );
    }

    #[test]
    fn max_tools_none_removes_rather_than_unsets_to_empty() {
        let e = build_ok(PermissionMode::Allow, &[]);
        assert!(e.removed.contains(&"CLAUDETTE_MAX_TOOLS".to_string()));
        let capped = build(
            &subject(&[]),
            &variant(PermissionMode::Allow),
            &Held { model: "m".into(), max_tools: Some(24), ..Held::default() },
            Path::new("/w"),
            Path::new("/w/.memory"),
        )
        .unwrap();
        assert_eq!(capped.pinned.get("CLAUDETTE_MAX_TOOLS").map(String::as_str), Some("24"));
    }

    #[test]
    fn subject_env_is_carried_and_a_disagreement_is_an_error_not_a_winner() {
        let ok = build_ok(PermissionMode::Allow, &[("NO_COLOR", "1")]);
        assert_eq!(ok.pinned.get("NO_COLOR").map(String::as_str), Some("1"));

        let e = build(
            &subject(&[("CLAUDETTE_NUM_CTX", "32768")]),
            &variant(PermissionMode::Allow),
            &Held { model: "m".into(), num_ctx: 61440, ..Held::default() },
            Path::new("/w"),
            Path::new("/w/.memory"),
        )
        .expect_err("a held constant declared twice, differently, must not resolve silently");
        assert!(matches!(e, EnvError::Conflict { .. }), "{e}");
    }

    #[test]
    fn a_subject_setting_auto_approve_conflicts_with_a_gated_variant() {
        // SPEC §7 says the descriptor never sets it. If one ever does, a `workspace_write` cell
        // would silently measure a run with no gate in it.
        let e = build(
            &subject(&[("CLAUDETTE_AUTO_APPROVE", "1")]),
            &variant(PermissionMode::WorkspaceWrite),
            &Held { model: "m".into(), ..Held::default() },
            Path::new("/w"),
            Path::new("/w/.memory"),
        )
        .expect_err("must refuse");
        assert!(matches!(e, EnvError::Conflict { .. }), "{e}");
    }

    #[test]
    fn the_run_scoped_snapshot_excludes_the_variant_scoped_auto_approve() {
        // The defect this guards: RUNMETA's env block is built from the warmup, which is always
        // `allow`, so an unfiltered snapshot asserted auto-approve for every cell in the run
        // including the gated ones.
        let allow = build_ok(PermissionMode::Allow, &[]);
        assert_eq!(allow.pinned.get("CLAUDETTE_AUTO_APPROVE").map(String::as_str), Some("1"));
        assert!(!allow.run_scoped().contains_key("CLAUDETTE_AUTO_APPROVE"));
        // The work dir is per-cell too, so a snapshot naming one cell's dir describes no other.
        assert!(!allow.run_scoped().contains_key("CLAUDETTE_WORKSPACE"));
        // ...while everything genuinely held for the whole run survives the filter.
        assert!(allow.run_scoped().contains_key("CLAUDETTE_FALLBACK_BRAIN_MODEL"));
        assert!(allow.run_scoped().contains_key("CLAUDETTE_MODEL"));

        let gated = build_ok(PermissionMode::WorkspaceWrite, &[]);
        assert!(!gated.run_scoped_removed().contains(&"CLAUDETTE_AUTO_APPROVE".to_string()));
        assert!(gated.run_scoped_removed().contains(&"CLAUDETTE_FORGE_AUTO_APPROVE".to_string()));
    }

    #[test]
    fn memory_is_pinned_to_a_path_and_never_to_the_empty_string() {
        // `CLAUDETTE_MEMORY=""` falls through to ~/.claudette/CLAUDETTE.MD (memory.rs:27-31), so
        // the empty string is the one value that looks like "off" and is not.
        let e = build_ok(PermissionMode::Allow, &[]);
        let m = e.pinned.get("CLAUDETTE_MEMORY").expect("pinned");
        assert!(!m.is_empty());
    }
}
