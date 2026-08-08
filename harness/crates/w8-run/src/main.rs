//! ```text
//! w8-run <corpus-root> --subject <id> --model <id> [--suite <id>]
//!        [--task <id>]... [--variant <id>]... [--out <dir>]
//!        [--num-ctx N] [--num-predict N] [--max-iterations N] [--max-tools N]
//!        [--endpoint URL] [--delivery verbatim|escape-newlines] [--bin <path>]
//!        [--list] [--dry-run]
//! ```
//!
//! Order of operations, and none of it is arbitrary:
//!
//! 1. **Load the corpus and refuse to run a rejected one** (SPEC §13). A runner that measures a
//!    corpus the loader would not accept is measuring something nobody can describe.
//! 2. **Probe `bash`, `python` and `node` by executing them** (SPEC §8). On this host `bash` on
//!    `PATH` is the WSL launcher and `python3` is a Microsoft Store alias shim; both resolve and
//!    neither runs.
//! 3. **Confirm the model with the endpoint**, and abort on a mismatch — LM Studio answers a
//!    request naming a model it does not have, so the requested id is not evidence.
//! 4. **Warm up in its own session.** Required, not best-effort (SPEC §11). Its `in=` is
//!    `preamble_tokens_in`, and it must be a *separate* session: usage is session-cumulative
//!    (F9), so a warmup turn inside the measured session would be added to the task's cost.
//! 5. One fresh process per cell, in a work dir built only from `fixture/`.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use w8_corpus::{
    Corpus, PermissionMode, Quarantine, RunVerdict, Subject, Suite, Support, Task, Turn, Variant,
    VariantOrigin, Verifiable,
};
use w8_run::delivery;
use w8_run::driver::{self, compile_turn_end, OperatorTrack, Session, SpawnSpec, TurnEnd};
use w8_run::endpoint;
use w8_run::env::{self as held_env, Held, WARMUP_PROMPT};
use w8_run::result::{Cell, Metric, RunMeta, Status};
use w8_run::verify;

struct Args {
    root: PathBuf,
    subject: Option<String>,
    suite: Option<String>,
    tasks: Vec<String>,
    variants: Vec<String>,
    held: Held,
    delivery: delivery::Mode,
    out: PathBuf,
    bin: Option<String>,
    list: bool,
    dry_run: bool,
}

fn main() -> ExitCode {
    let args = match parse_args() {
        Ok(a) => a,
        Err(m) => {
            eprintln!("{m}");
            return ExitCode::FAILURE;
        }
    };
    match run(args) {
        Ok(code) => code,
        Err(m) => {
            eprintln!("✗ {m}");
            ExitCode::FAILURE
        }
    }
}

fn parse_args() -> Result<Args, String> {
    let mut a = Args {
        root: PathBuf::from("corpus"),
        subject: None,
        suite: None,
        tasks: Vec::new(),
        variants: Vec::new(),
        held: Held::default(),
        delivery: delivery::Mode::Verbatim,
        out: PathBuf::from("runs"),
        bin: None,
        list: false,
        dry_run: false,
    };
    let mut it = std::env::args().skip(1);
    let mut positional = false;
    while let Some(arg) = it.next() {
        let mut next = |name: &str| -> Result<String, String> {
            it.next().ok_or_else(|| format!("{name} needs a value"))
        };
        match arg.as_str() {
            "--subject" => a.subject = Some(next("--subject")?),
            "--suite" => a.suite = Some(next("--suite")?),
            "--task" => a.tasks.push(next("--task")?),
            "--variant" => a.variants.push(next("--variant")?),
            "--model" => a.held.model = next("--model")?,
            "--endpoint" => a.held.endpoint = next("--endpoint")?,
            "--num-ctx" => a.held.num_ctx = parse_num(&next("--num-ctx")?)?,
            "--num-predict" => a.held.num_predict = parse_num(&next("--num-predict")?)?,
            "--max-iterations" => a.held.max_iterations = parse_num(&next("--max-iterations")?)?,
            "--max-tools" => a.held.max_tools = Some(parse_num(&next("--max-tools")?)?),
            "--out" => a.out = PathBuf::from(next("--out")?),
            "--bin" => a.bin = Some(next("--bin")?),
            "--delivery" => {
                let v = next("--delivery")?;
                a.delivery = delivery::Mode::parse(&v)
                    .ok_or_else(|| format!("unknown --delivery {v:?}: verbatim|escape-newlines"))?;
            }
            "--list" => a.list = true,
            "--dry-run" => a.dry_run = true,
            "-h" | "--help" => {
                println!("{}", usage());
                std::process::exit(0);
            }
            other if other.starts_with('-') => return Err(format!("unknown flag {other}")),
            other if !positional => {
                a.root = PathBuf::from(other);
                positional = true;
            }
            other => return Err(format!("unexpected argument {other}")),
        }
    }
    Ok(a)
}

fn parse_num<T: std::str::FromStr>(s: &str) -> Result<T, String> {
    s.parse().map_err(|_| format!("{s:?} is not a number"))
}

fn usage() -> &'static str {
    "usage: w8-run <corpus-root> --subject <id> --model <id> [--suite <id>] [--task <id>]...\n\
     \x20      [--variant <id>]... [--out <dir>] [--num-ctx N] [--num-predict N]\n\
     \x20      [--max-iterations N] [--max-tools N] [--endpoint URL]\n\
     \x20      [--delivery verbatim|escape-newlines] [--bin <path>] [--list] [--dry-run]\n\
     \n\
     --model is required and has no default: naming one here is how a convenience 4b ends up in\n\
     a baseline. The champion is qwen3.6-35b-a3b-mtp@iq3_s.\n\
     --delivery verbatim (the default) delivers the prompt byte-for-byte, wrapping a multi-line\n\
     one in the sentinels the subject declares in [delivery], and refuses the cell if the subject\n\
     declares none. escape-newlines is a labelled, unapproved fallback; see src/delivery.rs."
}

fn run(args: Args) -> Result<ExitCode, String> {
    // ── 1. The corpus, and refusing a rejected one ──────────────────────────
    if !args.root.is_dir() {
        return Err(format!("no corpus at {}", args.root.display()));
    }
    let corpus = Corpus::load(&args.root).map_err(|rejections| {
        let mut m = format!("the corpus was REJECTED — {} rejection(s):\n", rejections.len());
        for r in &rejections {
            m.push_str(&format!("  {r}\n"));
        }
        m.push_str("a runner that measures a corpus the loader will not accept is measuring \
                    something nobody can describe (SPEC §13)");
        m
    })?;

    let subject_id = args.subject.as_deref().ok_or_else(|| {
        format!(
            "--subject is required. Available: {}",
            corpus.subjects.iter().map(|s| s.id.as_str()).collect::<Vec<_>>().join(", ")
        )
    })?;
    let subject = corpus
        .subject(subject_id)
        .ok_or_else(|| format!("no subject {subject_id:?} in {}", args.root.display()))?;
    if subject.drive != "repl-pipe" {
        return Err(format!(
            "subject {subject_id} declares drive = {:?}; this runner only implements repl-pipe, \
             because one-shot passes None for its prompter (run.rs:186) and can never show a gate",
            subject.drive
        ));
    }

    let suite = match &args.suite {
        Some(id) => corpus.suite(id).ok_or_else(|| format!("no suite {id:?}"))?,
        None if corpus.suites.len() == 1 => &corpus.suites[0],
        None => {
            return Err(format!(
                "--suite is required when the corpus holds more than one: {}",
                corpus.suites.iter().map(|s| s.id.as_str()).collect::<Vec<_>>().join(", ")
            ));
        }
    };

    // ── The plan, with n/a already decided by the loader ────────────────────
    let plan: Vec<_> = suite
        .plan(subject)
        .into_iter()
        .filter(|c| args.tasks.is_empty() || args.tasks.contains(&c.task.id))
        .filter(|c| args.variants.is_empty() || args.variants.contains(&c.variant.id))
        .collect();
    if plan.is_empty() {
        return Err("the filters selected no cells".to_string());
    }

    if args.list {
        println!("{} cell(s) for subject {}", plan.len(), subject.id);
        for c in &plan {
            let support = match &c.support {
                Support::Runnable => "runnable".to_string(),
                Support::NotSupported { capability } => format!("n/a ({capability})"),
            };
            let deliverable = match turn_texts(c.task) {
                Err(e) => format!("unreadable: {e}"),
                Ok(ts) => match plan_turns(&ts, args.delivery, sentinel_of(subject)) {
                    Ok(p) => match p.first().map(|p| p.transport) {
                        Some(delivery::Transport::Sentinel) => "ok (block)".to_string(),
                        _ => "ok".to_string(),
                    },
                    Err(u) => format!("UNDELIVERABLE ({} lines)", u.prompt_lines),
                },
            };
            println!(
                "  {:<24} {:<20} {support:<18} {} / {}   delivery: {deliverable}",
                c.task.id,
                c.variant.id,
                c.task.disposition.verifiable,
                c.task.disposition.quarantine
            );
        }
        return Ok(ExitCode::SUCCESS);
    }

    if args.held.model.is_empty() {
        return Err("--model is required and has no default. The champion is \
                    qwen3.6-35b-a3b-mtp@iq3_s; never a convenience 4b for anything that produces \
                    a number"
            .to_string());
    }

    // ── 2. bash, python and node, by executing them ─────────────────────────
    let interp = verify::probe()?;
    println!(
        "bash: {}   python: {}   node: {}",
        interp.bash.display(),
        interp.python,
        interp.node.as_deref().unwrap_or("(none found)")
    );

    let turn_end = compile_turn_end(&subject.markers.turn_end).map_err(|e| e.to_string())?;
    if subject.markers.gate.is_empty() {
        return Err("subject markers.gate is empty; every gate would go unnoticed".to_string());
    }

    let run_id = format!(
        "w8-{}",
        SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_millis()).unwrap_or(0)
    );
    let out_run = args.out.join(&run_id);
    std::fs::create_dir_all(&out_run).map_err(|e| format!("cannot create {out_run:?}: {e}"))?;

    // Pinned as CLAUDETTE_MEMORY. Empty, so `try_load_memory_at` returns None and a CLAUDETTE.MD
    // appearing in David's home directory cannot move `preamble_tokens_in` without anyone noticing.
    let memory_stub = out_run.join("memory-stub.md");
    std::fs::write(&memory_stub, "").map_err(|e| format!("cannot write the memory stub: {e}"))?;

    let bin = args.bin.clone().unwrap_or_else(|| subject.bin.clone());
    let (corpus_commit, corpus_dirty) = git_state(&args.root);

    // ── 3. Which model is actually going to answer ──────────────────────────
    let mut model_confirmed = String::new();
    if !args.dry_run {
        let served = endpoint::confirm_model(&args.held.endpoint, &args.held.model)
            .map_err(|e| format!("the endpoint at {} did not answer: {e}", args.held.endpoint))?;
        if served != args.held.model {
            let available = endpoint::list_models(&args.held.endpoint).unwrap_or_default();
            return Err(format!(
                "asked {} for {:?} and it answered as {:?}.\n  \
                 LM Studio serves a request naming a model it does not have using whichever model \
                 is loaded, so this is silent by default and every number would be attributed to \
                 the wrong model.\n  loaded/available: {}",
                args.held.endpoint,
                args.held.model,
                served,
                available.join(", ")
            ));
        }
        model_confirmed = served;
        println!("model confirmed by the endpoint: {model_confirmed}");
    }

    // ── 4. The warmup, in its own session ───────────────────────────────────
    let mut meta = RunMeta {
        run_id: run_id.clone(),
        started_unix_ms: SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_millis())
            .unwrap_or(0),
        subject_id: subject.id.clone(),
        subject_version: subject.version.clone(),
        subject_commit: subject.commit.clone().unwrap_or_default(),
        subject_bin: bin.clone(),
        subject_drive: subject.drive.clone(),
        corpus_root: args.root.display().to_string(),
        corpus_commit,
        corpus_dirty,
        model_requested: args.held.model.clone(),
        model_confirmed,
        num_ctx: args.held.num_ctx,
        num_predict: args.held.num_predict,
        max_iterations: args.held.max_iterations,
        max_tools: args.held.max_tools,
        endpoint: args.held.endpoint.clone(),
        platform: format!("{}/{}", std::env::consts::OS, std::env::consts::ARCH),
        bash: interp.bash.display().to_string(),
        python: interp.python.clone(),
        node: interp.node.clone(),
        warmup: false,
        warmup_prompt: WARMUP_PROMPT.to_string(),
        warmup_wall_ms: 0,
        preamble_tokens_in: 0,
        delivery_mode: args.delivery.to_string(),
        aggregate_rule: suite.aggregate.describe(),
        env_pinned: BTreeMap::new(),
        env_removed: Vec::new(),
    };

    if !args.dry_run {
        let (preamble, wall, env_snapshot) = warmup(
            subject,
            &bin,
            &args.held,
            &out_run,
            &memory_stub,
            &subject.markers.gate,
            turn_end.clone(),
        )?;
        meta.warmup = true;
        meta.preamble_tokens_in = preamble;
        meta.warmup_wall_ms = wall;
        // Run-scoped only. The warmup always runs in `allow` mode, so its raw snapshot would
        // claim CLAUDETTE_AUTO_APPROVE=1 for every cell in the run — including the gated ones,
        // whose whole point is that it is unset. The per-cell truth is on the cell.
        meta.env_pinned = env_snapshot.run_scoped();
        meta.env_removed = env_snapshot.run_scoped_removed();
        println!(
            "warmup: {} ms, preamble_tokens_in = {preamble}",
            wall
        );
    }

    std::fs::write(out_run.join("runmeta.json"), format!("{}\n", meta.to_json()))
        .map_err(|e| format!("cannot write runmeta.json: {e}"))?;

    if !args.delivery.is_faithful() {
        println!(
            "⚠ delivery mode is {} — every prompt with an interior newline is rewritten before the \
             subject sees it. Numbers from this run are labelled on each cell and are NOT \
             comparable to the donor baselines.",
            args.delivery
        );
    }

    // ── 5. One fresh process per cell ───────────────────────────────────────
    let cells_dir = out_run.join("cells");
    std::fs::create_dir_all(&cells_dir).map_err(|e| e.to_string())?;
    let mut jsonl = String::new();
    let mut tally: BTreeMap<&'static str, usize> = BTreeMap::new();

    for c in &plan {
        let cell = match &c.support {
            Support::NotSupported { capability } => {
                not_supported_cell(suite, c.task, c.variant, subject, capability, args.delivery)
            }
            Support::Runnable if args.dry_run => {
                let mut cell = base_cell(suite, c.task, c.variant, subject, args.delivery, 0);
                cell.status = Status::Invalid;
                cell.reason = Some("--dry-run: nothing was executed".into());
                cell
            }
            Support::Runnable => run_cell(
                suite,
                c.task,
                c.variant,
                subject,
                &bin,
                &args.held,
                &args.delivery,
                &cells_dir,
                &memory_stub,
                &interp,
                turn_end.clone(),
                meta.preamble_tokens_in,
            ),
        };
        *tally.entry(cell.status.as_str()).or_default() += 1;
        println!(
            "  {:<24} {:<20} {:<14} {}",
            cell.task,
            cell.variant,
            cell.status.as_str(),
            cell.reason.as_deref().map(first_clause).unwrap_or_default()
        );
        jsonl.push_str(&cell.to_json());
        jsonl.push('\n');
    }

    let cells_path = out_run.join("cells.jsonl");
    std::fs::write(&cells_path, &jsonl).map_err(|e| format!("cannot write cells.jsonl: {e}"))?;

    println!("\n{}", meta.aggregate_rule);
    for (k, v) in &tally {
        println!("  {k}: {v}");
    }
    println!("→ {}", out_run.display());

    let bad = tally.get("error").copied().unwrap_or(0);
    Ok(if bad == 0 { ExitCode::SUCCESS } else { ExitCode::FAILURE })
}

fn first_clause(s: &str) -> &str {
    let cut = s.find(". ").unwrap_or(s.len().min(160));
    &s[..cut]
}

/// The warmup session. Runs in `allow` mode so a stray tool call cannot produce a gate this session
/// has no operator track for — auto-approve changes the permission policy only
/// (`runtime_build.rs:145-149`), not the system prompt or the tools array, so the `in=` it reports is
/// the same preamble a gated cell pays.
fn warmup(
    subject: &Subject,
    bin: &str,
    held: &Held,
    out_run: &Path,
    memory_stub: &Path,
    gate_marker: &str,
    turn_end: regex::Regex,
) -> Result<(u64, u64, held_env::ChildEnv), String> {
    let wd = out_run.join("warmup/wd");
    std::fs::create_dir_all(&wd).map_err(|e| e.to_string())?;
    let variant = synthetic_allow_variant();
    let env = held_env::build(subject, &variant, held, &wd, memory_stub)
        .map_err(|e| format!("warmup environment: {e}"))?;

    let mut session = Session::spawn(SpawnSpec {
        bin,
        args: &[],
        workdir: &wd,
        env: &env,
        gate_marker,
        turn_end,
        transcript_path: out_run.join("warmup/transcript.log"),
        label: "warmup",
        ready_cap: driver::READY_CAP,
    })
    .map_err(|e| format!("warmup spawn: {e}"))?;

    let deny = w8_corpus::Action::Deny;
    let mut track = OperatorTrack::new(&[], Some(&deny));
    // Generous: this turn is where the 35B JIT load lands — 169.7 s on the champion against 4.1 s
    // for the turns after it (F10). That is the whole reason it exists.
    let warmup = [WARMUP_PROMPT.to_string()];
    let run = session.run_turn(&warmup, &mut track, Instant::now() + Duration::from_secs(900));
    let end = run.end.clone();

    // Prove the subject actually understands the block it declares, before any cell is measured.
    //
    // The failure this exists for is silent and total: a subject that does not understand the
    // sentinels runs the OPENING LINE as a turn of its own, returns a marker that looks exactly
    // like the answer, and then runs each body line as a further turn while the harness has moved
    // on to the verifier. Every one of the 207 block-delivered cells would carry a plausible number
    // for a prompt the subject never received whole. A stale binary earlier on PATH is all it takes
    // — `~/.cargo/bin/claudette` and a fresh `target/release/claudette` report the same `--version`.
    //
    // The probe is decisive because a split is fatal *immediately* rather than after a model turn:
    // on a subject that understands blocks the turn text is two harmless lines, and on one that
    // does not, the second line it reads is a bare `exit`, which ends the session with no model
    // call at all. So a short wait separates them.
    let block_probe = if let Some(d) = &subject.delivery {
        let probe = [
            d.open.clone(),
            "exit".to_string(),
            "Reply with the single word: ready".to_string(),
            d.close.clone(),
        ];
        let p = session.run_turn(&probe, &mut track, Instant::now() + Duration::from_secs(300));
        std::thread::sleep(Duration::from_millis(750));
        match (&p.end, session.exited()) {
            (TurnEnd::Marker { .. }, false) => Ok(()),
            (end, exited) => Err(format!(
                "subject {} declares [delivery] open = {:?} / close = {:?}, but the binary at {bin} \
                 did not reassemble a block into one turn (probe ended {end:?}{}). Every \
                 multi-line cell would otherwise be measured against a prompt the subject never \
                 received whole. Check that this binary is the commit the descriptor pins — an \
                 older `claudette` earlier on PATH reports the same --version",
                subject.id,
                d.open,
                d.close,
                if exited { ", and the session then ended — the `exit` line inside the block was \
                              read as a command, which is exactly what a split looks like" } else { "" }
            )),
        }
    } else {
        Ok(())
    };

    session.finish();
    block_probe?;

    match end {
        TurnEnd::Marker { tokens_in, .. } => Ok((tokens_in, run.wall_ms, env)),
        other => Err(format!(
            "the warmup turn did not complete ({other:?}). RUNMETA requires a warmup — without it \
             the first task of the run is a model-load measurement wearing a task's name (F10) — \
             so the run stops here rather than producing a row that claims one ran"
        )),
    }
}

fn synthetic_allow_variant() -> Variant {
    Variant {
        id: "warmup".into(),
        mode: PermissionMode::Allow,
        requires: Vec::new(),
        expect: Default::default(),
        operator: Vec::new(),
        default: None,
        origin: VariantOrigin::Suite,
    }
}

fn turn_texts(task: &Task) -> Result<Vec<String>, String> {
    task.turns
        .iter()
        .map(|t| match t {
            Turn::SendFile(p) => std::fs::read_to_string(p)
                .map_err(|e| format!("cannot read the turn file {}: {e}", p.display())),
            Turn::SendText(s) => Ok(s.clone()),
        })
        .collect()
}

/// The subject's declared block sentinels, or `None` if it declares none. Read from the descriptor
/// on every call rather than cached: which strings a subject accepts is the subject's fact, and a
/// runner that hard-codes one subject's pair silently mis-delivers against the next one.
fn sentinel_of(subject: &Subject) -> Option<delivery::Sentinel<'_>> {
    subject
        .delivery
        .as_ref()
        .map(|d| delivery::Sentinel { open: &d.open, close: &d.close })
}

fn plan_turns(
    texts: &[String],
    mode: delivery::Mode,
    sentinel: Option<delivery::Sentinel<'_>>,
) -> Result<Vec<delivery::Plan>, delivery::Undeliverable> {
    texts.iter().map(|t| delivery::plan(t, mode, sentinel)).collect()
}

fn base_cell(
    suite: &Suite,
    task: &Task,
    variant: &Variant,
    subject: &Subject,
    mode: delivery::Mode,
    prompt_lines: usize,
) -> Cell {
    Cell {
        suite: suite.id.clone(),
        task: task.id.clone(),
        variant: variant.id.clone(),
        subject: subject.id.clone(),
        status: Status::Error,
        reason: None,
        verifier_verdict: None,
        verifier_message: None,
        metrics: BTreeMap::new(),
        gate_fires: 0,
        gate_fires_after_deny: 0,
        interventions_delivered: 0,
        unscripted_gates: 0,
        gate_actions: Vec::new(),
        delivery_mode: mode.to_string(),
        prompt_lines,
        delivery_faithful: mode.is_faithful(),
        // Overwritten once the prompt is planned. `line` is the honest default for the cells that
        // never get that far (n/a, unreadable turn file, undeliverable): nothing was wrapped.
        delivery_transport: delivery::Transport::Line.to_string(),
        permission_mode: variant.mode.as_str().to_string(),
        // Derived from the mode rather than read back from the environment, and the two are checked
        // against each other in `env::build`: a subject descriptor that sets the flag is refused.
        auto_approve: variant.mode == PermissionMode::Allow,
        disposition: format!(
            "{}/{}",
            task.disposition.verifiable, task.disposition.quarantine
        ),
        in_aggregate: suite.aggregate.counts(&task.disposition),
        workdir: String::new(),
        transcript: String::new(),
        startup_ms: 0,
    }
}

/// SPEC §7: `n/a` is arithmetically distinct from zero, so every metric says `not_supported` and
/// carries the capability that was missing. Nobody types "n/a" into a results table.
fn not_supported_cell(
    suite: &Suite,
    task: &Task,
    variant: &Variant,
    subject: &Subject,
    capability: &str,
    mode: delivery::Mode,
) -> Cell {
    let mut cell = base_cell(suite, task, variant, subject, mode, 0);
    cell.status = Status::NotSupported;
    cell.reason = Some(format!(
        "variant {:?} requires capability {capability:?}, which subject {} does not declare",
        variant.id, subject.id
    ));
    for name in METRIC_NAMES {
        cell.metrics.insert(
            (*name).to_string(),
            Metric::NotSupported { capability: capability.to_string() },
        );
    }
    cell
}

const METRIC_NAMES: &[&str] = &[
    "ttfvo_ms",
    "ttft_stdout_ms",
    "wall_clock_s",
    "tokens_in",
    "tokens_out",
    "tokens_in_preamble",
    "tokens_in_net",
    "iterations",
    "turns",
    "gate_fires",
    "interventions_delivered",
    "unscripted_gates",
];

#[allow(clippy::too_many_arguments)]
fn run_cell(
    suite: &Suite,
    task: &Task,
    variant: &Variant,
    subject: &Subject,
    bin: &str,
    held: &Held,
    mode: &delivery::Mode,
    cells_dir: &Path,
    memory_stub: &Path,
    interp: &verify::Interpreters,
    turn_end: regex::Regex,
    preamble_tokens_in: u64,
) -> Cell {
    let mut cell = base_cell(suite, task, variant, subject, *mode, 0);

    // Delivery first, before anything is created on disk: an undeliverable prompt is not a fact
    // about the subject's work, and running the process to find out would waste a model load.
    let texts = match turn_texts(task) {
        Ok(t) => t,
        Err(e) => {
            cell.status = Status::Error;
            cell.reason = Some(e);
            return cell;
        }
    };
    let plans = match plan_turns(&texts, *mode, sentinel_of(subject)) {
        Ok(p) => p,
        Err(u) => {
            cell.prompt_lines = u.prompt_lines;
            // INVALID, not FAIL: nothing about the subject's work was measured. SPEC §5's rule
            // ("a run where the gate never fired did not measure the thing") is the same shape.
            cell.status = Status::Invalid;
            cell.reason = Some(u.reason);
            return cell;
        }
    };
    cell.prompt_lines = plans.first().map_or(0, |p| p.prompt_lines);
    cell.delivery_transport = plans
        .first()
        .map_or(delivery::Transport::Line, |p| p.transport)
        .to_string();

    let dir = cells_dir.join(format!("{}__{}", task.id, variant.id));
    let wd = dir.join("wd");
    if let Err(e) = std::fs::create_dir_all(&wd) {
        cell.status = Status::Error;
        cell.reason = Some(format!("cannot create the work dir: {e}"));
        return cell;
    }
    // The ONLY path list that ever reaches the subject. `Task` will not hand out `refsol/`,
    // `sham/` or `stub/` at all, so this cannot copy one by accident (SPEC §2).
    if let Err(e) = task.workdir.materialize(&wd) {
        cell.status = Status::Error;
        cell.reason = Some(format!("cannot materialize the fixture: {e}"));
        return cell;
    }
    let transcript = dir.join("transcript.log");
    cell.workdir = wd.display().to_string();
    cell.transcript = transcript.display().to_string();

    let env = match held_env::build(subject, variant, held, &wd, memory_stub) {
        Ok(e) => e,
        Err(e) => {
            // A mode this subject cannot reach is not a failed run — it is a cell that has no
            // meaning against this subject, which is what `not_supported` is for.
            cell.status = match e {
                held_env::EnvError::ModeUnreachable { .. } => Status::NotSupported,
                held_env::EnvError::Conflict { .. } => Status::Error,
            };
            cell.reason = Some(e.to_string());
            return cell;
        }
    };

    let label = format!("{}/{} · {}", task.id, variant.id, subject.id);
    let mut session = match Session::spawn(SpawnSpec {
        bin,
        args: &[],
        workdir: &wd,
        env: &env,
        gate_marker: &subject.markers.gate,
        turn_end,
        transcript_path: transcript,
        label: &label,
        ready_cap: driver::READY_CAP,
    }) {
        Ok(s) => s,
        Err(e) => {
            cell.status = Status::Error;
            cell.reason = Some(format!("spawn: {e}"));
            return cell;
        }
    };
    cell.startup_ms = session.startup_ms;

    let mut track = OperatorTrack::new(&variant.operator, variant.default.as_ref());
    let deadline = Instant::now() + Duration::from_secs(u64::from(task.timeout_s));
    let mut last_marker: Option<(u32, u64, u64)> = None;
    let mut ttfvo: Option<u64> = None;
    let mut ttft: Option<u64> = None;
    let mut wall_ms = 0u64;
    let mut ended: Option<TurnEnd> = None;
    let mut turns_run = 0usize;

    for p in &plans {
        let run = session.run_turn(&p.lines, &mut track, deadline);
        turns_run += 1;
        wall_ms += run.wall_ms;
        // The FIRST turn's first byte is the headline: it is when the operator saw the subject
        // react. Later turns get their own row in the transcript, not their own metric.
        if ttfvo.is_none() {
            ttfvo = run.ttfvo_ms;
        }
        if ttft.is_none() {
            ttft = run.ttft_stdout_ms;
        }
        match &run.end {
            // Session-cumulative: the LAST marker is the cost of the task, and summing the lines
            // multiply-counts (F9). Overwriting rather than adding is the whole point.
            TurnEnd::Marker { iterations, tokens_in, tokens_out } => {
                last_marker = Some((*iterations, *tokens_in, *tokens_out));
            }
            other => {
                ended = Some(other.clone());
                break;
            }
        }
    }

    if matches!(ended, Some(TurnEnd::Timeout)) {
        session.kill();
    } else {
        session.finish();
    }

    cell.gate_fires = track.gate_fires;
    cell.gate_fires_after_deny = track.gate_fires_after_deny;
    cell.interventions_delivered = track.interventions_delivered;
    cell.unscripted_gates = track.unscripted_gates;
    cell.gate_actions =
        track.actions.iter().map(|a| (a.at_ms, a.tool.clone(), a.action.clone(), a.rule)).collect();

    let mut m = BTreeMap::new();
    let measured = |v: u64| Metric::Measured(v as f64);
    m.insert(
        "ttfvo_ms".to_string(),
        ttfvo.map_or(
            Metric::NotApplicable { reason: "the subject produced no output for this turn".into() },
            measured,
        ),
    );
    m.insert(
        "ttft_stdout_ms".to_string(),
        ttft.map_or(
            Metric::NotApplicable { reason: "the subject wrote nothing to stdout".into() },
            measured,
        ),
    );
    m.insert("wall_clock_s".to_string(), Metric::Measured(wall_ms as f64 / 1000.0));
    m.insert("turns".to_string(), measured(turns_run as u64));
    match last_marker {
        Some((iter, tin, tout)) => {
            m.insert("iterations".to_string(), measured(u64::from(iter)));
            m.insert("tokens_in".to_string(), measured(tin));
            m.insert("tokens_out".to_string(), measured(tout));
            let pre = preamble_tokens_in * turns_run as u64;
            m.insert("tokens_in_preamble".to_string(), measured(pre));
            // Deliberately signed: a negative means the warmup's preamble estimate exceeded this
            // task's whole input, which is information about the estimate, not something to clamp.
            m.insert("tokens_in_net".to_string(), Metric::Measured(tin as f64 - pre as f64));
        }
        None => {
            let reason = "no turn-end marker, so the session-cumulative counts were never printed";
            for k in ["iterations", "tokens_in", "tokens_out", "tokens_in_preamble", "tokens_in_net"]
            {
                m.insert(k.to_string(), Metric::NotApplicable { reason: reason.into() });
            }
        }
    }
    m.insert("gate_fires".to_string(), measured(u64::from(track.gate_fires)));
    m.insert(
        "interventions_delivered".to_string(),
        measured(u64::from(track.interventions_delivered)),
    );
    m.insert("unscripted_gates".to_string(), measured(u64::from(track.unscripted_gates)));
    m.insert(
        "peak_rss_mb".to_string(),
        Metric::NotApplicable { reason: "no probe exists yet; W1/W2 owns building it".into() },
    );
    cell.metrics = m;

    // ── Status, in precedence order ─────────────────────────────────────────
    if let Some(end) = ended {
        cell.status = match &end {
            TurnEnd::Timeout => Status::Timeout,
            // The harness refused to guess. INVALID, because a run it could not steer did not
            // measure the subject.
            TurnEnd::Blocked(_) => Status::Invalid,
            TurnEnd::Eof => Status::Error,
            TurnEnd::Marker { .. } => unreachable!("a marker does not end the loop"),
        };
        cell.reason = Some(match end {
            TurnEnd::Timeout => format!(
                "no turn boundary within timeout_s = {}. The suite sets retry_on_timeout = false: \
                 a retry would hide a real timeout as difficulty signal (F12)",
                task.timeout_s
            ),
            TurnEnd::Blocked(r) => r,
            TurnEnd::Eof => {
                "the subject exited without printing a turn boundary; see the transcript".into()
            }
            TurnEnd::Marker { .. } => unreachable!(),
        });
        return cell;
    }

    // SPEC §5: an `expect` violation is INVALID and it is checked BEFORE the verifier. A cell whose
    // gate never fired did not measure operator control, and letting the verifier's PASS stand
    // would report the run as a success at the thing it failed to observe.
    if let Some(v) = variant.expect.violation(track.observed()) {
        cell.status = Status::Invalid;
        cell.reason = Some(format!("expect violation: {v}"));
        return cell;
    }

    match task.verify_script() {
        None => {
            // F13: ten U100 tasks carry `validation: null` and the donor scored them on the
            // agent-execution success flag — "the agent didn't crash". Reproducing that would
            // import the defect; a completed turn is not a verdict.
            cell.status = Status::Invalid;
            cell.reason = Some(
                "[verify].kind = \"none\": the donor supplied no verifier and scored the task on \
                 its own execSuccess flag (F13). A completed turn is not a verdict"
                    .into(),
            );
        }
        Some(script) => {
            let v = verify::run(interp, &script, &wd, Path::new(&cell.transcript));
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
        }
    }

    // Not a status, but it belongs on the row: a quarantined task carries a verdict nobody should
    // aggregate, and the field that says so is the one the reader will forget to check.
    if task.disposition.quarantine == Quarantine::WithBaseline && cell.reason.is_none() {
        cell.reason = Some(format!(
            "quarantined with baseline ({}); this verdict is excluded from every aggregate",
            match task.disposition.verifiable {
                Verifiable::None => "no verifier",
                _ => "the verifier accepts at least one wrong answer",
            }
        ));
    }
    cell
}

/// The corpus commit, and whether the tree is dirty. A cell measured against edited files is not
/// reproducible from a commit id, so the dirt is part of the row.
fn git_state(root: &Path) -> (String, bool) {
    let head = Command::new("git")
        .args(["rev-parse", "HEAD"])
        .current_dir(root)
        .output()
        .ok()
        .filter(|o| o.status.success())
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
        .unwrap_or_else(|| "unknown".to_string());
    let dirty = Command::new("git")
        .args(["status", "--porcelain", "."])
        .current_dir(root)
        .output()
        .ok()
        .filter(|o| o.status.success())
        .map(|o| !String::from_utf8_lossy(&o.stdout).trim().is_empty())
        .unwrap_or(true);
    (head, dirty)
}
