//! `w8-corpus` — load a corpus and say whether it is acceptable.
//!
//! ```text
//! w8-corpus [corpus-root]           human report; exit 1 if the corpus is rejected
//! w8-corpus [corpus-root] --facts   a sorted fact stream, for diffing against validate.py --facts
//! ```
//!
//! The `--facts` mode exists because a port whose reference is a Python script is only as good as
//! the comparison nobody ran. Both implementations emit the same sorted lines, so `diff` is the
//! check — not a reading of two files that look like they agree.

use std::path::PathBuf;
use std::process::ExitCode;

use w8_corpus::{Corpus, Support, Verifiable};

fn main() -> ExitCode {
    let mut root = PathBuf::from("corpus");
    let mut facts = false;
    let mut subject_id: Option<String> = None;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--facts" => facts = true,
            "--subject" => subject_id = args.next(),
            "-h" | "--help" => {
                println!("usage: w8-corpus [corpus-root] [--facts] [--subject <id>]");
                return ExitCode::SUCCESS;
            }
            other => root = PathBuf::from(other),
        }
    }

    if !root.is_dir() {
        eprintln!("no corpus at {}", root.display());
        return ExitCode::FAILURE;
    }

    let (corpus, rejections) = Corpus::load_reporting(&root);
    if facts {
        emit_facts(&corpus, rejections.len());
    } else {
        report(&corpus, &rejections, subject_id.as_deref());
    }
    if rejections.is_empty() { ExitCode::SUCCESS } else { ExitCode::FAILURE }
}

fn emit_facts(corpus: &Corpus, rejections: usize) {
    let mut lines: Vec<String> = Vec::new();
    for s in &corpus.subjects {
        let delivery = s
            .delivery
            .as_ref()
            .map_or_else(|| "none".to_string(), |d| format!("{}..{}", d.open, d.close));
        lines.push(format!(
            "subject {} drive={} caps={} delivery={delivery}",
            s.id,
            s.drive,
            s.capabilities.join("|")
        ));
    }
    for suite in &corpus.suites {
        let inc: Vec<&str> = suite.aggregate.include_verifiable.iter().map(|v| v.as_str()).collect();
        lines.push(format!(
            "suite {} include={} exclude_quarantined={} expected={}",
            suite.id,
            inc.join("|"),
            suite.aggregate.exclude_quarantined,
            suite.expected_tasks.map(|n| n.to_string()).unwrap_or_else(|| "-".into()),
        ));
        for t in &suite.tasks {
            lines.push(format!(
                "task {}/{} verifiable={} quarantine={} gate={}|{}|{} counted={}",
                suite.id,
                t.id,
                t.disposition.verifiable,
                t.disposition.quarantine,
                t.gate.point1,
                t.gate.point2,
                t.gate.point3,
                if suite.aggregate.counts(&t.disposition) { "yes" } else { "no" },
            ));
            for v in &t.variants {
                lines.push(format!(
                    "variant {}/{} {} origin={} mode={} requires={} operator={} default={}",
                    suite.id,
                    t.id,
                    v.id,
                    v.origin.as_str(),
                    v.mode,
                    v.requires.join("|"),
                    v.operator.len(),
                    v.default.as_ref().map(|a| a.label()).unwrap_or("none"),
                ));
            }
        }
    }
    lines.sort();
    for l in &lines {
        println!("{l}");
    }
    let tasks: usize = corpus.suites.iter().map(|s| s.tasks.len()).sum();
    println!(
        "verdict {} rejections={rejections} tasks={tasks}",
        if rejections == 0 { "ACCEPTED" } else { "REJECTED" }
    );
}

fn report(corpus: &Corpus, rejections: &[w8_corpus::Rejection], subject_id: Option<&str>) {
    println!("corpus/SPEC.md v1 — loader check ({})\n", corpus.root.display());

    for s in &corpus.subjects {
        println!("  subj {}  v{}  drive={}  caps=[{}]", s.id, s.version, s.drive, s.capabilities.join(", "));
    }

    for suite in &corpus.suites {
        println!("\n  suite {} — {}", suite.id, suite.title);
        println!("    {} task(s) loaded, {} suite caveat(s)", suite.tasks.len(), suite.caveats.len());

        let c = suite.disposition_counts();
        println!(
            "    disposition: {} full · {} presence_only · {} no-verifier · {} quarantined-with-baseline",
            c.full, c.presence_only, c.no_verifier, c.quarantined
        );

        let agg = suite.aggregate();
        println!("    aggregate:   denominator {} under {}", agg.denominator, agg.rule);
        if agg.excluded_quarantined + agg.excluded_verifiable > 0 {
            println!(
                "                 excluded: {} quarantined, {} by verifiable",
                agg.excluded_quarantined, agg.excluded_verifiable
            );
        }

        let gate3: Vec<&str> = suite.tasks.iter().filter(|t| t.selection.gate3).map(|t| t.id.as_str()).collect();
        println!("    gate3 set:   {} task(s)", gate3.len());

        let unverifiable = suite.tasks.iter().filter(|t| t.disposition.verifiable == Verifiable::None).count();
        let empty_fixtures = suite.tasks.iter().filter(|t| t.workdir.is_empty()).count();
        println!("    fixtures:    {empty_fixtures} empty, {} with files", suite.tasks.len() - empty_fixtures);
        println!("    verifiers:   {} script, {unverifiable} none", suite.tasks.len() - unverifiable);

        // Rule 8 is a property of the (variant, subject) pair, so it can only be answered once a
        // subject is named. Without one, the cell count is all that can honestly be reported.
        if let Some(sid) = subject_id {
            match corpus.subject(sid) {
                Some(subject) => {
                    let cells = suite.plan(subject);
                    let na = cells.iter().filter(|c| c.support != Support::Runnable).count();
                    println!("\n    against {}: {} cell(s), {} runnable, {na} n/a", subject.id, cells.len(), cells.len() - na);
                    let mut missing: Vec<&str> = cells
                        .iter()
                        .filter_map(|c| match &c.support {
                            Support::NotSupported { capability } => Some(capability.as_str()),
                            Support::Runnable => None,
                        })
                        .collect();
                    missing.sort_unstable();
                    missing.dedup();
                    if !missing.is_empty() {
                        println!("    n/a because the subject does not declare: {}", missing.join(", "));
                    }
                }
                None => println!("\n    no subject {sid:?} in this corpus"),
            }
        }
    }

    if rejections.is_empty() {
        println!("\n  ACCEPTED — every §13 rule holds");
    } else {
        println!("\n  REJECTED — {} violation(s):", rejections.len());
        for r in rejections {
            println!("    {r}");
        }
    }
}
