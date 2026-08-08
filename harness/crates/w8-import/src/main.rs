//! `w8-import` — imports ABCC's 100-task suite into a `corpus/SPEC.md` v1 corpus.
//!
//! Step 2 of the W8 plan: extract -> rewrite -> emit, with gate point 1 measured at import time
//! on all 90 tasks against the **rewritten** verifier.
//!
//! ```text
//! cargo run -p w8-import -- --donor D:/dev/agent-battle-command-center --out ../corpus
//! ```
//!
//! The importer **never drops a task** (SPEC §9). A task that fails a gate point is imported with
//! `quarantine = "with_baseline"`: the donor baseline is carried, the task still runs, and it is
//! excluded from every aggregate. Failing the gate changes the disposition, never whether the
//! task is on disk.
//!
//! It also never overwrites an existing task directory unless `--force` is given, because
//! `refsol/`, `sham/` and the prose in a hand-authored `task.toml` are authored artifacts that a
//! mechanical re-run has no business clobbering.

mod donor;
mod emit;
mod gate;
mod rewrite;
mod verify_sh;

use rewrite::{Task, VClass};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

const DEFAULT_DONOR: &str = r"D:\dev\agent-battle-command-center";
/// Held constant so re-running the importer does not churn every `imported_at` in the corpus.
const DEFAULT_IMPORTED_AT: &str = "2026-08-08";

struct Args {
    donor: PathBuf,
    out: PathBuf,
    only: Option<String>,
    force: bool,
    skip_gate: bool,
    imported_at: String,
}

fn parse_args() -> Result<Args, String> {
    let mut a = Args {
        donor: PathBuf::from(DEFAULT_DONOR),
        out: PathBuf::from("corpus"),
        only: None,
        force: false,
        skip_gate: false,
        imported_at: DEFAULT_IMPORTED_AT.to_string(),
    };
    let mut it = std::env::args().skip(1);
    while let Some(arg) = it.next() {
        let mut need = |name: &str| it.next().ok_or_else(|| format!("{name} needs a value"));
        match arg.as_str() {
            "--donor" => a.donor = PathBuf::from(need("--donor")?),
            "--out" => a.out = PathBuf::from(need("--out")?),
            "--only" => a.only = Some(need("--only")?),
            "--imported-at" => a.imported_at = need("--imported-at")?,
            "--force" => a.force = true,
            "--skip-gate" => a.skip_gate = true,
            "-h" | "--help" => {
                println!(
                    "w8-import — ABCC 100-task suite -> corpus/SPEC.md v1\n\n\
                     \x20 --donor <dir>        donor repo (default {DEFAULT_DONOR})\n\
                     \x20 --out <dir>          corpus root to emit into (default ./corpus)\n\
                     \x20 --only <task id>     emit a single task\n\
                     \x20 --force              overwrite task directories that already exist\n\
                     \x20 --skip-gate          do not run gate point 1 (development only)\n\
                     \x20 --imported-at <date> value for provenance.imported_at\n"
                );
                std::process::exit(0);
            }
            other => return Err(format!("unknown argument {other:?} (try --help)")),
        }
    }
    Ok(a)
}

fn main() -> ExitCode {
    match run() {
        Ok(true) => ExitCode::SUCCESS,
        Ok(false) => ExitCode::from(1),
        Err(e) => {
            eprintln!("w8-import: {e}");
            ExitCode::from(2)
        }
    }
}

fn run() -> Result<bool, String> {
    let args = parse_args()?;

    // ---- stage 1: extract -----------------------------------------------------------------
    let js_path = args.donor.join("scripts").join("ultimate-100-task-test.js");
    let js = donor::read(&js_path)
        .map_err(|e| format!("cannot read {}: {e}", js_path.display()))?;
    let all = donor::extract(&js);
    let stable = donor::stable(all.clone());
    let buggy = donor::buggy_files(&js);

    println!("w8-import — ABCC's 100-task suite -> corpus/SPEC.md v1");
    println!("  donor        {} @ {}", args.donor.display(), emit::DONOR_COMMIT);
    println!("  out          {}", args.out.display());
    println!(
        "  extracted    {} task objects, {} stable after dropping {:?} (F11)",
        all.len(),
        stable.len(),
        donor::UNSTABLE_CATEGORIES
    );
    println!("  BUGGY_FILES  {} donor fixtures", buggy.len());
    if stable.len() != 90 {
        return Err(format!(
            "expected 90 stable tasks, got {}. The pool is 90, not 100 (F11); a different count \
             means the donor moved and every recorded count in the corpus needs re-checking.",
            stable.len()
        ));
    }

    // ---- stage 2: rewrite -----------------------------------------------------------------
    let mut tasks: Vec<Task> = stable
        .iter()
        .map(|d| rewrite::build(d, &buggy, &stable))
        .collect();

    // Postconditions on the rewrite, checked rather than trusted. Each of these was a real
    // defect risk: a leftover `file_write` instructs the subject to call a tool Claudette does
    // not have, and a leftover container path points outside the work dir.
    for t in &tasks {
        if t.prompt.contains("file_write") {
            return Err(format!("task {}: emitted prompt still names file_write", t.id));
        }
        if t.prompt.contains("/app/workspace") || t.prompt.contains("tasks/") {
            return Err(format!("task {}: emitted prompt still holds a container path", t.id));
        }
        if let Some(v) = &t.verify {
            if v.body.contains("/app/workspace") || v.body.contains("tasks/") || v.body.contains("tasks.") {
                return Err(format!("task {}: rewritten verifier still holds a donor path", t.id));
            }
            if v.script.contains('\r') {
                return Err(format!(
                    "task {}: verify.sh contains a CR. The donor source is entirely CRLF and a \
                     stray \\r inside a bash heredoc or a raw python string is the kind of defect \
                     that changes behaviour without changing how the file reads.",
                    t.id
                ));
            }
        }
        if t.prompt.contains('\r') {
            return Err(format!("task {}: emitted prompt contains a CR", t.id));
        }
    }
    println!(
        "  rewrote      {} prompts (tool rename + path flatten), {} verifiers",
        tasks.len(),
        tasks.iter().filter(|t| t.verify.is_some()).count()
    );

    let deps: Vec<&Task> = tasks.iter().filter(|t| !t.deps.is_empty()).collect();
    if !deps.is_empty() {
        println!("\n  cross-task dependencies reconstructed into fixture/ (F7):");
        for t in &deps {
            println!(
                "    {:<22} needs {:?}{}",
                t.id,
                t.deps,
                if t.deps.iter().all(|d| t.fixture.contains_key(d)) {
                    ""
                } else {
                    "   <-- UNRESOLVED"
                }
            );
        }
    }

    // ---- stage 3: gate --------------------------------------------------------------------
    let mut gates: BTreeMap<String, gate::GateResult> = BTreeMap::new();
    if args.skip_gate {
        println!("\n  gate         SKIPPED (--skip-gate): every point records not_run");
        for t in &tasks {
            gates.insert(t.id.clone(), gate::GateResult::not_run());
        }
    } else {
        let it = gate::probe().map_err(|e| e)?;
        println!("\n  interpreters probed by EXECUTING, not by looking (SPEC §8):");
        println!("    bash    {}", it.bash.display());
        println!("    python  {}", it.python);
        println!(
            "    node    {}",
            it.node.as_deref().unwrap_or("NOT FOUND — node verifiers will be inconclusive")
        );
        if !selftest(&it, &mut tasks)? {
            return Err(
                "the positive control failed outright: not one verifier produced a PASS, so a \
                 FAIL cannot be attributed to the verifier rather than to this importer. The \
                 gate results below would be meaningless and were not written."
                    .into(),
            );
        }
        println!("\n  gate point 1 on all 90, against the REWRITTEN verifier (F19):");
        for t in &tasks {
            let existing = task_dir(&args.out, &t.id);
            let g = gate::run(
                &it,
                t,
                existing.exists().then_some(existing.as_path()),
                &args.imported_at,
            )
            .map_err(|e| format!("task {}: gate failed: {e}", t.id))?;
            gates.insert(t.id.clone(), g);
        }
        report_gate(&tasks, &gates);
    }

    // ---- stage 4: emit --------------------------------------------------------------------
    let mut written = 0usize;
    let mut skipped: Vec<&str> = Vec::new();
    let mut hand_authored: Vec<&str> = Vec::new();
    for t in &tasks {
        if let Some(only) = &args.only {
            if &t.id != only {
                continue;
            }
        }
        let dir = task_dir(&args.out, &t.id);
        // `--force` overwrites generated output. It must never overwrite an authored task:
        // `refsol/`, `sham/` and a hand-written task.toml carry reasoning a mechanical re-run
        // cannot reproduce, and losing them is silent until someone reads the diff. Generated
        // files say so on their first line, which makes "was this authored" a fact rather than
        // a judgement.
        let existing_toml = dir.join("task.toml");
        if existing_toml.exists() {
            let head = std::fs::read_to_string(&existing_toml).unwrap_or_default();
            if !head.starts_with("# GENERATED by") {
                hand_authored.push(&t.id);
                continue;
            }
        }
        if dir.exists() && !args.force {
            skipped.push(&t.id);
            continue;
        }
        emit::write_task(&dir, t, &gates[&t.id], &args.imported_at)
            .map_err(|e| format!("task {}: cannot write {}: {e}", t.id, dir.display()))?;
        written += 1;
    }

    println!("\n  emitted      {written} task directories");
    if !skipped.is_empty() {
        println!(
            "  preserved    {} that already exist (use --force to overwrite): {}",
            skipped.len(),
            skipped.join(", ")
        );
    }
    if !hand_authored.is_empty() {
        println!(
            "  authored     {} left untouched — their task.toml is hand-written, and --force \
             does not apply to those: {}",
            hand_authored.len(),
            hand_authored.join(", ")
        );
    }

    report_dispositions(&tasks, &gates);
    Ok(true)
}

/// The positive control: a **right** answer must PASS.
///
/// Every gate tier expects FAIL, so an importer that emitted a `verify.sh` incapable of ever
/// printing PASS would report 80 sound verifiers and look like a clean run. The donor's own
/// prompts dictate the finished file body for 60 of the 90 tasks, which is a reference solution
/// by construction — so this control costs no authoring and covers far more than a hand-written
/// pair would.
///
/// A task that FAILs here is worth looking at rather than worth panicking about: it means the
/// donor's dictated answer does not satisfy the donor's own verifier, which is a fact about the
/// donor, not about the import. It is reported per task for exactly that reason.
fn selftest(it: &gate::Interpreters, tasks: &mut [Task]) -> Result<bool, String> {
    let candidates: Vec<(usize, String, String)> = tasks
        .iter()
        .enumerate()
        .filter(|(_, t)| t.verify.is_some() && t.dictated.is_some())
        .map(|(i, t)| (i, t.artifact.clone(), t.dictated.clone().unwrap()))
        .collect();
    println!(
        "\n  positive control — the donor's own dictated solution must PASS ({} of {} tasks\n\
         \x20 dictate their artifact body verbatim in the prompt):",
        candidates.len(),
        tasks.len()
    );

    let mut pass = 0usize;
    let mut bad: Vec<(String, &'static str, String)> = Vec::new();
    for (i, artifact, body) in &candidates {
        let mut overlay = BTreeMap::new();
        overlay.insert(artifact.clone(), body.clone());
        let (verdict, detail) = gate::run_overlay(it, &tasks[*i], &overlay)
            .map_err(|e| format!("task {}: positive control failed to run: {e}", tasks[*i].id))?;
        match verdict {
            gate::Verdict::Pass => pass += 1,
            v => {
                // Record it on the task, not just in this report. Someone reading that task's
                // task.toml a year from now should not have to already know the finding.
                tasks[*i].caveats.push(format!(
                    "THE DONOR'S OWN DICTATED SOLUTION DOES NOT PASS THIS VERIFIER: the prompt \
                     spells out the whole artifact body, and writing exactly that body yields \
                     `{}: {detail}`. So this task is not passable by following its own \
                     instructions literally. Left unrepaired: the 7 recorded donor runs used \
                     this prompt, and repairing it would change the task's difficulty while \
                     claiming to be an import. Measured by the importer's positive control",
                    v.name()
                ));
                bad.push((tasks[*i].id.clone(), v.name(), detail));
            }
        }
    }
    println!(
        "    n={}: PASS={pass}  not-PASS={}",
        candidates.len(),
        bad.len()
    );
    for (id, v, detail) in &bad {
        println!("      {id:<24} {v:<8} {detail}");
    }
    if bad.is_empty() {
        println!(
            "    Every dictated solution passes its own verifier, so a FAIL at a gate tier is\n\
             \x20   attributable to the tier and not to the import."
        );
    }
    Ok(pass > 0)
}

fn task_dir(out: &Path, id: &str) -> PathBuf {
    out.join("suites").join("u100").join("tasks").join(id)
}

fn report_gate(tasks: &[Task], gates: &BTreeMap<String, gate::GateResult>) {
    let mut sound = 0;
    let mut broken: Vec<(&str, String)> = Vec::new();
    let mut inconclusive: Vec<&str> = Vec::new();
    let mut not_run = 0;
    for t in tasks {
        match gates[&t.id].point1.as_str() {
            "sound" => sound += 1,
            "broken" => {
                let tiers: Vec<&str> = gates[&t.id]
                    .evidence
                    .iter()
                    .filter(|e| e.point == 1 && e.verdict == gate::Verdict::Pass)
                    .map(|e| e.tier.name())
                    .collect();
                broken.push((&t.id, tiers.join(", ")));
            }
            "inconclusive" => inconclusive.push(&t.id),
            _ => not_run += 1,
        }
    }
    let live = tasks.len() - not_run;
    println!(
        "    n={live} exercised ({not_run} have no verifier): SOUND={sound}  BROKEN={}  \
         INCONCLUSIVE={}",
        broken.len(),
        inconclusive.len()
    );
    for (id, tiers) in &broken {
        println!("      {id:<24} accepted a wrong answer at: {tiers}");
    }
    for id in &inconclusive {
        println!("      {id:<24} INCONCLUSIVE — the verifier did not run");
    }
    println!(
        "    Step-1 sound is necessary, not sufficient: fix_sql_inject is sound here and F8\n\
         \x20   still showed it passing an intact SQL injection. Point 1 bounds the defect rate\n\
         \x20   from below; only an authored sham closes it."
    );
}

fn report_dispositions(tasks: &[Task], gates: &BTreeMap<String, gate::GateResult>) {
    let mut clean = 0;
    let mut presence = 0;
    let mut quarantined: Vec<(&str, &'static str)> = Vec::new();
    for t in tasks {
        let d = emit::disposition(t, &gates[&t.id]);
        match (d.verifiable, d.quarantine) {
            (_, "with_baseline") => quarantined.push((&t.id, d.verifiable)),
            ("presence_only", _) => presence += 1,
            _ => clean += 1,
        }
    }
    println!("\n  disposition (SPEC §10)");
    println!("    clean                    {clean:>3}   full verifier, in every aggregate");
    println!("    presence-only            {presence:>3}   string-match verifier, in aggregates per R9");
    println!("    quarantined-with-baseline {:>2}   baseline carried, excluded from aggregates", quarantined.len());
    println!("                             ---");
    println!("    total                    {:>3}", clean + presence + quarantined.len());
    println!(
        "\n    aggregate denominator {} under include_verifiable = [full, presence_only],\n\
         \x20   exclude_quarantined = true. Any published number must state the rule it was\n\
         \x20   computed under.",
        clean + presence
    );
    println!("\n    quarantined:");
    for (id, v) in &quarantined {
        println!("      {id:<24} verifiable={v}");
    }

    let vc = |c: VClass| tasks.iter().filter(|t| t.vclass == c).count();
    println!(
        "\n  verifier class: exec={} strmatch={} none={}",
        vc(VClass::Exec),
        vc(VClass::StrMatch),
        vc(VClass::None)
    );
    let g3 = tasks.iter().filter(|t| t.gate3_rank.is_some()).count();
    println!("  gate3 selection: {g3} tasks carry [selection].gate3 = true");
}
