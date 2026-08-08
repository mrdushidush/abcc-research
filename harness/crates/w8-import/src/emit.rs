//! Stage 4 — emit. Writes the corpus tree SPEC §2 describes.
//!
//! The TOML is written as text rather than serialized. A serializer would drop the comments, and
//! the comments are half of why the format is TOML at all (SPEC §2: "the donor TSV manifest
//! cannot say *why* a timeout is what it is"). It also lets the field order match the worked
//! example, so an emitted task and the hand-authored one are diffable side by side.

use crate::gate::GateResult;
use crate::rewrite::{Task, VClass};
use std::fs;
use std::path::Path;

pub const DONOR: &str = "abcc-u100";
pub const DONOR_REPO: &str = "agent-battle-command-center";
pub const DONOR_COMMIT: &str = "d5528ea";
pub const DONOR_PATH: &str = "scripts/ultimate-100-task-test.js";

/// SPEC §3's closed vocabulary. The three provenance lists must partition it exactly; the loader
/// checks that (§13 rule 10) and it is checkable only because the vocabulary is closed.
pub const PARTITION: [&str; 16] = [
    "id",
    "title",
    "lang",
    "kind",
    "timeout_s",
    "turn",
    "prompt",
    "fixture",
    "verify",
    "refsol",
    "sham",
    "variants",
    "disposition",
    "selection",
    "gate",
    "donor_tags",
];

// ---------------------------------------------------------------------------------------------
// TOML text helpers
// ---------------------------------------------------------------------------------------------

fn escape_basic(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 8);
    for c in s.chars() {
        match c {
            '\\' => out.push_str("\\\\"),
            '"' => out.push_str("\\\""),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04X}", c as u32)),
            c => out.push(c),
        }
    }
    out
}

fn basic(s: &str) -> String {
    format!("\"{}\"", escape_basic(s))
}

/// A multi-line basic string, word-wrapped with TOML line continuations — the shape the worked
/// example uses for its caveats. A trailing `\` trims the newline and the next line's leading
/// whitespace, so the value reads as one paragraph while the file stays under 100 columns.
fn wrapped(s: &str, indent: usize) -> String {
    let pad = " ".repeat(indent);
    let body = s
        .replace('\\', "\\\\")
        .replace("\"\"\"", "\\\"\\\"\\\"")
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ");
    let width = 96usize.saturating_sub(indent + 2);
    let mut lines: Vec<String> = Vec::new();
    let mut cur = String::new();
    for w in body.split(' ') {
        if !cur.is_empty() && cur.chars().count() + 1 + w.chars().count() > width {
            lines.push(std::mem::take(&mut cur));
        }
        if !cur.is_empty() {
            cur.push(' ');
        }
        cur.push_str(w);
    }
    if !cur.is_empty() {
        lines.push(cur);
    }
    let mut out = "\"\"\"\n".to_string();
    for (i, l) in lines.iter().enumerate() {
        let last = i + 1 == lines.len();
        out.push_str(&pad);
        out.push_str(l);
        out.push_str(if last { "\\\n" } else { " \\\n" });
    }
    out.push_str(&pad);
    out.push_str("\"\"\"");
    out
}

fn str_array(items: &[&str]) -> String {
    let mut out = String::from("[");
    let mut line = String::new();
    for (i, it) in items.iter().enumerate() {
        let piece = format!("{}{}", basic(it), if i + 1 == items.len() { "" } else { ", " });
        if line.chars().count() + piece.chars().count() > 78 {
            out.push_str(&line);
            out.push_str("\n               ");
            line.clear();
        }
        line.push_str(&piece);
    }
    out.push_str(&line);
    out.push(']');
    out
}

// ---------------------------------------------------------------------------------------------
// Provenance
// ---------------------------------------------------------------------------------------------

/// Which of the three lists each corpus field lands in, for this task.
///
/// `lang` is verbatim even though the donor has no such field: it is read off the artifact path
/// the donor dictates, without editing it. `fixture` is verbatim only for the ten section-4B
/// tasks that ship a real buggy file in `BUGGY_FILES`; for everything else it is synthesized,
/// because the donor ran a shared cumulative workspace rather than a per-task fixture (F7).
/// `verify` is verbatim for the ten tasks the donor left as `validation: null` — nothing was
/// rewritten because there was nothing to rewrite.
pub fn provenance_lists(task: &Task) -> (Vec<&'static str>, Vec<&'static str>, Vec<&'static str>) {
    let mut verbatim = vec!["id", "lang", "kind", "donor_tags"];
    let mut rewritten = vec!["prompt"];
    let mut synthesized = vec![
        "title",
        "timeout_s",
        "turn",
        "refsol",
        "sham",
        "variants",
        "disposition",
        "selection",
        "gate",
    ];
    if task.fixture_is_donor {
        verbatim.push("fixture");
    } else {
        synthesized.push("fixture");
    }
    if task.verify.is_some() {
        rewritten.push("verify");
    } else {
        verbatim.push("verify");
    }
    (verbatim, rewritten, synthesized)
}

/// The check the loader will make (§13 rule 10), made here so a bad import cannot be written in
/// the first place.
fn assert_partition(task: &Task) {
    let (v, r, s) = provenance_lists(task);
    let mut all: Vec<&str> = v.iter().chain(&r).chain(&s).copied().collect();
    all.sort_unstable();
    let n = all.len();
    all.dedup();
    assert_eq!(n, all.len(), "task {}: a field is in two provenance lists", task.id);
    let mut want: Vec<&str> = PARTITION.to_vec();
    want.sort_unstable();
    assert_eq!(
        all, want,
        "task {}: the provenance lists do not partition SPEC §3's closed vocabulary",
        task.id
    );
}

// ---------------------------------------------------------------------------------------------
// Disposition
// ---------------------------------------------------------------------------------------------

pub struct Disposition {
    pub verifiable: &'static str,
    pub quarantine: &'static str,
    pub reason: Option<String>,
}

/// SPEC §10. Two orthogonal fields, both always written.
///
/// The standing rule David set on 2026-08-08: anything that fails the gate is imported with
/// `quarantine = "with_baseline"` — the donor baseline is carried, the task runs, and it is
/// excluded from every aggregate. Failing the gate changes the disposition; it never changes
/// whether the task is on disk.
pub fn disposition(task: &Task, gate: &GateResult) -> Disposition {
    let verifiable = task.vclass.verifiable();
    if task.vclass == VClass::None {
        return Disposition {
            verifiable,
            quarantine: "with_baseline",
            reason: Some(
                "the donor supplied no verifier at all (`validation: null`) and the runner \
                 scored `passed = execSuccess`, the agent-execution endpoint's own success \
                 flag. There is nothing here that can reject a wrong answer, so the donor \
                 baseline is carried and the task is excluded from every aggregate. F13"
                    .into(),
            ),
        };
    }
    if gate.any_broken() {
        let which: Vec<String> = [("point1", &gate.point1), ("point2", &gate.point2), ("point3", &gate.point3)]
            .iter()
            .filter(|(_, v)| **v == "broken")
            .map(|(k, _)| (*k).to_string())
            .collect();
        let tiers: Vec<String> = gate
            .evidence
            .iter()
            .filter(|e| {
                (e.tier == crate::gate::Tier::Refsol && e.verdict != crate::gate::Verdict::Pass)
                    || (e.tier != crate::gate::Tier::Refsol
                        && e.verdict == crate::gate::Verdict::Pass)
            })
            .map(|e| e.tier.name().to_string())
            .collect();
        return Disposition {
            verifiable,
            quarantine: "with_baseline",
            reason: Some(format!(
                "gate {} did not hold: the verifier accepted a wrong answer at tier(s) {}. A \
                 verifier that accepts an answer cannot report that answer as wrong, so the \
                 donor baseline is carried and the task is excluded from every aggregate. This \
                 is the standing rule David set on 2026-08-08",
                which.join(" and "),
                if tiers.is_empty() { "-".to_string() } else { tiers.join(", ") }
            )),
        };
    }
    Disposition {
        verifiable,
        quarantine: "none",
        reason: if task.vclass == VClass::StrMatch {
            Some(
                "the verifier string-matches generated source, so a PASS establishes presence \
                 and not correctness. Included in aggregates per David 2026-08-08 (R9's route, \
                 not the literal standing rule): a `landing` task has no ground truth to be \
                 wrong about, so quarantining it would describe a property of the task genre as \
                 if it were a defect. The suite-level caveat records this. F20"
                    .into(),
            )
        } else {
            None
        },
    }
}

// ---------------------------------------------------------------------------------------------
// task.toml
// ---------------------------------------------------------------------------------------------

pub fn task_toml(task: &Task, gate: &GateResult, imported_at: &str) -> String {
    assert_partition(task);
    let d = disposition(task, gate);
    let mut s = String::new();

    s.push_str(&format!(
        "# GENERATED by harness/crates/w8-import from {DONOR_REPO} @ {DONOR_COMMIT}.\n\
         # Hand edits are fine, but re-running the importer over this directory will not\n\
         # overwrite it: emit into a fresh tree and diff if you want to see what changed.\n\n"
    ));
    s.push_str("schema    = 1\n");
    s.push_str(&format!("id        = {}\n", basic(&task.id)));
    s.push_str(&format!(
        "title     = {}   # mechanical; see [provenance].caveats\n",
        basic(&task.title)
    ));
    s.push_str(&format!("lang      = {}\n", basic(task.lang)));
    s.push_str(&format!("kind      = {}\n", basic(&task.kind)));
    s.push_str(
        "\n# No per-task timeout in the donor; the global TASK_TIMEOUT_MS is 5 minutes. The clean\n\
         # runs' 307 s `fetch failed` entries are this timeout firing, not infra noise. F12.\n",
    );
    s.push_str(&format!("timeout_s = {}\n", task.timeout_s));

    s.push_str("\n[[turn]]\nsend_file = \"prompt.txt\"\n");

    s.push_str("\n[verify]\n");
    match &task.verify {
        Some(_) => s.push_str("kind   = \"script\"\nscript = \"verify.sh\"\n"),
        None => s.push_str(
            "# The donor wrote `validation: null` for this task and the runner fell back to the\n\
             # agent-execution success flag (ultimate-100-task-test.js:3168). SPEC §8 allows\n\
             # kind = \"none\", and requires disposition.verifiable = \"none\" with it. F13.\n\
             kind = \"none\"\n",
        ),
    }

    s.push_str("\n# ---------------------------------------------------------------------------\n");
    s.push_str("# Disposition — SPEC.md §10\n");
    s.push_str("# ---------------------------------------------------------------------------\n");
    s.push_str("[disposition]\n");
    s.push_str(&format!("verifiable = {}\n", basic(d.verifiable)));
    s.push_str(&format!("quarantine = {}\n", basic(d.quarantine)));
    if let Some(r) = &d.reason {
        s.push_str(&format!("reason = {}\n", wrapped(r, 0)));
    }

    if let Some(rank) = task.gate3_rank {
        s.push_str("\n[selection]\n");
        s.push_str("gate3      = true\n");
        s.push_str(&format!("gate3_rank = {rank}\n"));
        s.push_str(
            "# In R10's approved 30: \"hardest\" read as *where a sham is most likely to pass*,\n\
             # tie-broken by verifier exposure (R9). Points 2 and 3 need authored artifacts, so\n\
             # they stay `not_run` until step 4 of the W8 plan writes a sham against THIS\n\
             # verifier — not the donor's.\n",
        );
    } else {
        s.push_str(
            "\n# [selection] absent ⇒ gate3 = false. Not in R10's 30: a sham here would either\n\
             # pass by construction or test a task with no ground truth to be wrong about.\n",
        );
    }

    s.push_str("\n# ---------------------------------------------------------------------------\n");
    s.push_str("# Gate — SPEC.md §9. Recorded at import, not asserted at run time.\n");
    s.push_str("#\n");
    s.push_str(
        "# `verifier = \"rewritten\"` is the authoritative column: a gate result measured against\n\
         # the donor's verifier does not describe the verifier this corpus runs. Point 1's\n\
         # pre-state is a null-implementation stub, not the absent artifact — running a verifier\n\
         # against an empty workspace misses fix_path_traversal entirely, because its import\n\
         # raises before reaching the swallowed assert. Same cost, strictly stronger. F19.\n",
    );
    s.push_str("# ---------------------------------------------------------------------------\n");
    s.push_str("[gate]\n");
    for (k, v) in [
        ("point1", &gate.point1),
        ("point2", &gate.point2),
        ("point3", &gate.point3),
    ] {
        s.push_str(&format!("{k} = {}\n", basic(v)));
    }
    if task.verify.is_none() {
        s.push_str(
            "# All three are not_run because there is no verifier to exercise. `not_run` is how\n\
             # SPEC §13 rule 7 says \"not yet\"; silence is not an option.\n",
        );
    }

    for e in &gate.evidence {
        s.push_str("\n[[gate.evidence]]\n");
        s.push_str(&format!("point    = {}\n", e.point));
        s.push_str(&format!("tier     = {}\n", basic(e.tier.name())));
        s.push_str(&format!("verdict  = {}\n", basic(e.verdict.name())));
        s.push_str(&format!("detail   = {}\n", basic(&e.detail)));
        s.push_str("verifier = \"rewritten\"\n");
        s.push_str(&format!("run      = {}\n", basic(&e.run)));
    }

    // -- provenance -------------------------------------------------------------------------
    let (verbatim, rewritten, synthesized) = provenance_lists(task);
    s.push_str("\n# ---------------------------------------------------------------------------\n");
    s.push_str("# Provenance — every corpus field appears in exactly one of the three lists\n");
    s.push_str("# ---------------------------------------------------------------------------\n");
    s.push_str("[provenance]\n");
    s.push_str(&format!("donor        = {}\n", basic(DONOR)));
    s.push_str(&format!("donor_id     = {}\n", basic(&task.donor.name)));
    s.push_str(&format!("donor_commit = {}\n", basic(DONOR_COMMIT)));
    s.push_str(&format!("donor_path   = {}\n", basic(DONOR_PATH)));
    s.push_str(&format!("imported_at  = {}\n", basic(imported_at)));
    s.push('\n');
    s.push_str(&format!("verbatim    = {}\n", str_array(&verbatim)));
    s.push_str(&format!("rewritten   = {}\n", str_array(&rewritten)));
    s.push_str(&format!("synthesized = {}\n", str_array(&synthesized)));

    let mut caveats = task.caveats.clone();
    caveats.push(format!(
        "TITLE is mechanical: `{}`, derived from the artifact name. The donor has no title \
         field, so this is synthesized rather than rewritten, and it is meant to be replaced by \
         hand where a better one exists",
        task.title
    ));
    if !task.fixture_is_donor {
        caveats.push(
            "EMPTY FIXTURE: the donor generated this artifact from nothing, inside one \
             cumulative workspace shared by all 100 tasks (F7). Per-task isolation here is \
             better science and breaks byte-comparability with the 7 recorded runs. The \
             fixture directory holds only a .gitkeep, which the runner must not copy into the \
             work dir"
                .into(),
        );
    }
    s.push_str("\ncaveats = [\n");
    for c in &caveats {
        s.push_str("  ");
        s.push_str(&wrapped(c, 2));
        s.push_str(",\n\n");
    }
    s.push_str("]\n");

    // -- donor tags -------------------------------------------------------------------------
    s.push_str("\n[donor_tags]\n");
    s.push_str(&format!(
        "complexity = {}        # donor-scoped; takes four values across the whole suite, so it\n\
         \x20                     # is not a difficulty ranking and is never read by the\n\
         \x20                     # aggregate. F17.\n",
        if task.donor.complexity.is_empty() { "0" } else { &task.donor.complexity }
    ));
    s.push_str(&format!("section    = {}\n", basic(&task.donor.section)));
    s.push_str(&format!("category   = {}\n", basic(&task.donor.category)));
    s.push_str(&format!("dir        = {}\n", basic(&task.donor.dir)));
    s.push_str(&format!(
        "files      = {}\n",
        if task.donor.files.is_empty() { "1" } else { &task.donor.files }
    ));
    s.push_str(&format!(
        "artifact   = {}   # the donor path this flattens from\n",
        basic(&task.artifact_donor)
    ));
    s
}

// ---------------------------------------------------------------------------------------------
// Writing a task directory
// ---------------------------------------------------------------------------------------------

pub fn write_task(
    dir: &Path,
    task: &Task,
    gate: &GateResult,
    imported_at: &str,
) -> std::io::Result<()> {
    fs::create_dir_all(dir)?;
    fs::write(dir.join("task.toml"), task_toml(task, gate, imported_at))?;
    fs::write(dir.join("prompt.txt"), format!("{}\n", task.prompt.trim_end()))?;

    let fixture = dir.join("fixture");
    fs::create_dir_all(&fixture)?;
    if task.fixture.is_empty() {
        // SPEC §2 requires `fixture/`, and git cannot carry an empty directory.
        fs::write(
            fixture.join(".gitkeep"),
            "# This task generates its artifact from nothing: the donor had no fixture for it.\n\
             # SPEC §2 requires fixture/ to exist, and git cannot carry an empty directory.\n\
             # The runner must not copy dotfiles into the work dir.\n",
        )?;
    } else {
        for (name, body) in &task.fixture {
            fs::write(fixture.join(name), body)?;
        }
    }

    if let Some(v) = &task.verify {
        fs::write(dir.join("verify.sh"), &v.script)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn wrapped_produces_parseable_continuations() {
        let s = wrapped("one two three four five six seven eight nine ten", 2);
        assert!(s.starts_with("\"\"\"\n"));
        assert!(s.trim_end().ends_with("\"\"\""));
        // every content line but the last closes with a continuation
        for l in s.lines().skip(1) {
            if l.trim() == "\"\"\"" {
                continue;
            }
            assert!(l.ends_with('\\'), "line without a continuation: {l:?}");
        }
    }

    #[test]
    fn wrapped_escapes_backslashes_and_triple_quotes() {
        let s = wrapped(r#"a \ b """ c"#, 0);
        assert!(s.contains(r"\\"));
        assert!(!s.contains(r#"a \ b"#));
        assert!(s.matches("\\\"\\\"\\\"").count() == 1);
    }

    #[test]
    fn basic_escapes_what_toml_requires() {
        assert_eq!(basic("a\"b"), "\"a\\\"b\"");
        assert_eq!(basic("a\\b"), "\"a\\\\b\"");
        assert_eq!(basic("a\nb"), "\"a\\nb\"");
    }

    #[test]
    fn partition_is_exactly_specs_closed_vocabulary() {
        assert_eq!(PARTITION.len(), 16);
        let mut v = PARTITION.to_vec();
        v.sort_unstable();
        v.dedup();
        assert_eq!(v.len(), 16, "the vocabulary itself must have no duplicates");
    }
}
