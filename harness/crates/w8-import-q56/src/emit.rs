//! Stage 4 — emit. Writes the task directory SPEC v1 describes.
//!
//! The TOML is written by hand rather than serialized, for the same reason `w8-import` writes its
//! own: a serializer strips comments, and the comments carry the findings. SPEC §2 makes that the
//! format's job, not a nicety.

use crate::donor::DonorTask;
use crate::gate::{GateResult, Verdict};
use std::collections::BTreeMap;
use std::path::Path;

/// SPEC §3's closed vocabulary. The three provenance lists must partition it exactly, and the
/// loader checks that (§13 rule 10) — which is checkable only because the vocabulary is closed.
const FIELDS: [&str; 16] = [
    "id", "title", "lang", "kind", "timeout_s", "turn", "prompt", "fixture", "verify", "refsol",
    "sham", "variants", "disposition", "selection", "gate", "donor_tags",
];

fn escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\t' => out.push_str("\\t"),
            '\r' => out.push_str("\\r"),
            _ => out.push(c),
        }
    }
    out
}

fn basic(s: &str) -> String {
    format!("\"{}\"", escape(s))
}

/// A word-wrapped multi-line basic string with TOML line continuations — the shape the worked
/// examples use. A trailing `\` eats the newline and the next line's indent, so the value reads as
/// one paragraph while the file stays inside 100 columns.
fn wrapped(s: &str, indent: usize) -> String {
    let pad = " ".repeat(indent);
    let width = 96usize.saturating_sub(indent);
    let mut lines: Vec<String> = Vec::new();
    let mut cur = String::new();
    for word in s.split_whitespace() {
        if !cur.is_empty() && cur.chars().count() + 1 + word.chars().count() > width {
            lines.push(std::mem::take(&mut cur));
        }
        if !cur.is_empty() {
            cur.push(' ');
        }
        cur.push_str(word);
    }
    if !cur.is_empty() {
        lines.push(cur);
    }
    let body = lines
        .iter()
        .map(|l| format!("{pad}{}", escape(l)))
        .collect::<Vec<_>>()
        .join(" \\\n");
    format!("\"\"\"\n{body}\\\n{pad}\"\"\"")
}

fn str_array(items: &[&str], indent: usize) -> String {
    let pad = " ".repeat(indent);
    let mut out = String::from("[");
    let mut width = indent + 1;
    for (i, it) in items.iter().enumerate() {
        let piece = format!("{}{}", basic(it), if i + 1 < items.len() { ", " } else { "" });
        if width + piece.len() > 96 {
            out.push('\n');
            out.push_str(&pad);
            width = indent;
        }
        width += piece.len();
        out.push_str(&piece);
    }
    out.push(']');
    out
}

pub struct Provenance {
    pub verbatim: Vec<&'static str>,
    pub rewritten: Vec<&'static str>,
    pub synthesized: Vec<&'static str>,
}

/// Which of the three lists each corpus field lands in, for Q56.
///
/// The headline is that **`prompt` is verbatim**. U100 had to rewrite all 90 of its prompts because
/// they name ABCC's `file_write` tool, and that rewrite is the largest single threat to
/// comparability in that import. These prompts name no tool and no absolute path.
///
/// `refsol` is verbatim, which no U100 task can say: the donor authored one per task and W8 copies
/// it. `verify` is the only rewritten field.
pub fn provenance(task: &DonorTask) -> Provenance {
    let mut verbatim =
        vec!["id", "lang", "kind", "timeout_s", "prompt", "fixture", "donor_tags"];
    let mut synthesized = vec!["title", "turn", "sham", "variants", "disposition", "selection", "gate"];
    if task.refsol.is_empty() {
        synthesized.push("refsol");
    } else {
        verbatim.push("refsol");
    }
    let p = Provenance { verbatim, rewritten: vec!["verify"], synthesized };
    assert_partition(&p);
    p
}

/// The check the loader will make (§13 rule 10), made here so a bad import cannot be written in the
/// first place rather than only refused when it is read back.
fn assert_partition(p: &Provenance) {
    let mut seen: Vec<&str> =
        p.verbatim.iter().chain(&p.rewritten).chain(&p.synthesized).copied().collect();
    seen.sort_unstable();
    let mut want: Vec<&str> = FIELDS.to_vec();
    want.sort_unstable();
    assert_eq!(seen, want, "the provenance lists must partition SPEC §3's vocabulary exactly");
}

/// The one-line title. The donor has no title field, so it is synthesized from the prompt's first
/// sentence — clipped, lowercased at the front, and never invented.
pub fn title(prompt: &str) -> String {
    let first = prompt.split_terminator(['.', '\n']).next().unwrap_or(prompt).trim();
    let mut t: String = first.chars().take(80).collect();
    if t.len() < first.len() {
        while !t.is_empty() && !t.ends_with(' ') {
            t.pop();
        }
        t = t.trim_end().to_string();
    }
    t
}

pub fn task_toml(task: &DonorTask, lang: &str, gate: &GateResult, imported_at: &str, commit: &str) -> String {
    let r = &task.row;
    let p = provenance(task);
    let mut s = String::new();

    s.push_str("# GENERATED by w8-import-q56. Edits here are overwritten on the next import.\n");
    s.push_str("schema    = 1\n");
    s.push_str(&format!("id        = {}\n", basic(&r.id)));
    s.push_str(&format!("title     = {}\n", basic(&title(&task.prompt))));
    s.push_str(&format!("lang      = {}\n", basic(lang)));
    s.push_str(&format!("kind      = {}\n", basic(&r.kind)));
    s.push_str(&format!(
        "\n# Straight off the manifest row. The donor gave its harder tasks longer on purpose, so \
         that\n# a 15 tok/s candidate is never wall-punished — one of the few donor decisions that \
         transfers\n# to W8 unchanged.\ntimeout_s = {}\n",
        r.timeout_s
    ));

    s.push_str("\n[[turn]]\nsend_file = \"prompt.txt\"\n");
    s.push_str("\n[verify]\nkind   = \"script\"\nscript = \"verify.sh\"\n");

    s.push_str("\n# ---------------------------------------------------------------------------\n");
    s.push_str("# Disposition — SPEC.md §10\n");
    s.push_str("# ---------------------------------------------------------------------------\n");
    s.push_str("[disposition]\n");
    s.push_str("verifiable = \"full\"\n");
    let quarantined = gate.point1 != Verdict::Sound || gate.point2 == Verdict::Broken;
    s.push_str(&format!(
        "quarantine = {}\n",
        if quarantined { "\"with_baseline\"" } else { "\"none\"" }
    ));
    s.push_str(&format!(
        "reason = {}\n",
        wrapped(
            if quarantined {
                "the import gate did not hold against the rewritten verifier. Per David's standing \
                 rule the donor baseline is carried, the task still runs, and it is excluded from \
                 every aggregate — failing the gate changes the disposition, never whether the task \
                 is on disk."
            } else {
                "the verifier injects hidden reviewer tests at grade time and runs them against \
                 whatever the subject left on disk. It grades the code and not the transcript — no \
                 Q56 verifier reads the transcript at all (F41), so nothing here is presence-only."
            },
            0
        )
    ));

    s.push_str("\n[selection]\ngate3 = false\n");
    s.push_str(
        "# R9/R10's gate3 set is a U100 selection with no meaning in this suite, and Q56 needs no\n\
         # equivalent: points 1 and 2 are available for all 56 without authoring anything, because\n\
         # every task ships a fixture that is already a wrong answer and a refsol that is a right\n\
         # one. The question gate3 exists to answer — which 30 do we author for — does not arise.\n",
    );

    s.push_str("\n# ---------------------------------------------------------------------------\n");
    s.push_str("# Gate — SPEC.md §9. Measured at import against the REWRITTEN verifier, which is\n");
    s.push_str("# the authoritative column. The donor's own gate_q50.sh already requires both\n");
    s.push_str("# points before a task may enter manifest-q50.tsv (F45), so this normally confirms\n");
    s.push_str("# rather than discovers — but U100 was 79 of 80 sound at point 1 and F8 still found\n");
    s.push_str("# a verifier passing an intact SQL injection. A donor's gate is a reason to expect a\n");
    s.push_str("# result, never a substitute for measuring it.\n");
    s.push_str("#\n");
    s.push_str("# Point 1's pre-state is the donor's untouched fixture (tier `donor_fixture`), not\n");
    s.push_str("# §9's generated null-implementation stub: the fixture already compiles and passes\n");
    s.push_str("# the visible tests while failing the hidden ones, which is the state the stub was\n");
    s.push_str("# invented to simulate.\n");
    s.push_str("# ---------------------------------------------------------------------------\n");
    s.push_str("[gate]\n");
    s.push_str(&format!("point1 = \"{}\"\n", gate.point1.as_str()));
    s.push_str(&format!("point2 = \"{}\"\n", gate.point2.as_str()));
    s.push_str("point3 = \"not_run\"   # no sham/ — never silently treated as passed\n");

    for e in &gate.evidence {
        s.push_str("\n[[gate.evidence]]\n");
        s.push_str(&format!("point    = {}\n", e.point));
        s.push_str(&format!("tier     = {}\n", basic(&e.tier)));
        s.push_str(&format!("verdict  = {}\n", basic(&e.verdict)));
        s.push_str(&format!("detail   = {}\n", basic(&e.detail)));
        s.push_str("verifier = \"rewritten\"\n");
        s.push_str(&format!("run      = {}\n", basic(&e.run)));
    }

    s.push_str("\n# ---------------------------------------------------------------------------\n");
    s.push_str("# Provenance — every corpus field appears in exactly one of the three lists\n");
    s.push_str("# ---------------------------------------------------------------------------\n");
    s.push_str("[provenance]\n");
    s.push_str("donor        = \"claudette-q56\"\n");
    s.push_str(&format!("donor_id     = {}\n", basic(&r.id)));
    s.push_str(&format!("donor_commit = {}\n", basic(commit)));
    s.push_str("donor_path   = \"runs/eval-2026-05-29/battery\"\n");
    s.push_str(&format!("imported_at  = {}\n\n", basic(imported_at)));
    s.push_str(&format!("verbatim    = {}\n", str_array(&p.verbatim, 15)));
    s.push_str(&format!("rewritten   = {}\n", str_array(&p.rewritten, 15)));
    s.push_str(&format!("synthesized = {}\n", str_array(&p.synthesized, 15)));

    s.push_str("\ncaveats = [\n");
    for c in caveats(task) {
        s.push_str(&format!("  {},\n\n", wrapped(&c, 2)));
    }
    s.push_str("]\n");

    s.push_str("\n[donor_tags]                       # donor-scoped, no cross-suite meaning\n");
    s.push_str(&format!("manifest_row = {}\n", basic(&r.raw)));
    s.push_str(&format!("lang         = {}   # the donor's own column, before SPEC's vocabulary\n", basic(&r.lang)));
    s.push_str(&format!("fixture_dir  = {}\n", basic(&r.fixture_dir)));
    s
}

fn caveats(task: &DonorTask) -> Vec<String> {
    let mut v = vec![
        "THE PROMPT IS VERBATIM AND THAT IS THE HEADLINE. U100's import rewrites all 90 of its \
         prompts because they name ABCC's file_write tool, and that is the largest single threat to \
         comparability in the whole import. This donor's prompts name no tool and no absolute path: \
         they are written in a user's voice, state the goal, show one example, and deliberately do \
         not enumerate the edge cases. Nothing needed changing."
            .to_string(),
        "VERIFIER REWRITE, three ways and no assertion touched. _lib.sh is inlined because a W8 \
         task dir is self-contained (SPEC §2), carrying only the four lines Q56 uses — the \
         tc/tcre/tcount transcript helpers are dropped as dead code, since no Q56 verifier reads \
         the transcript (F41). Interpreters resolve through the environment as shell FUNCTIONS \
         rather than by rewriting call sites, so the donor body stays byte-identical and the hidden \
         reviewer tests in its heredocs are never touched. And a missing toolchain prints INVALID \
         rather than FAIL — a deliberate strictening over the donor, whose README says a missing \
         toolchain does not skip its tasks but fails them, silently costing up to 19 points."
            .to_string(),
        "the hidden reviewer tests live in the verifier and are written into the work dir at grade \
         time, so the subject never sees them. The fixture ships only happy-path visible tests on \
         purpose: a PASS is possible only if the subject handled an edge the prompt implies but \
         does not state. This is the donor's central design and it survives the import untouched."
            .to_string(),
        "the donor ran this task as one invocation with no permission gate anywhere in the path, so \
         its recorded number is comparable to the `control` variant and to nothing else — the same \
         limitation U100's baselines carry (F1)."
            .to_string(),
    ];
    if task.fixture.contains_key("Cargo.toml") {
        v.push(
            "fixture/Cargo.toml carries an empty [workspace] table. It is load-bearing, not \
             clutter: without it the parent repo's cargo workspace captures the fixture and the \
             build refuses. Copied verbatim and never tidied."
                .to_string(),
        );
    }
    if task.refsol.is_empty() {
        v.push(
            "NO refsol/ IN THE DONOR for this task, so gate point 2 records not_run rather than \
             being silently treated as passed (SPEC §9)."
                .to_string(),
        );
    }
    v
}

pub fn write_files(dir: &Path, files: &BTreeMap<String, String>) -> Result<(), String> {
    for (rel, body) in files {
        let path = dir.join(rel);
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).map_err(|e| format!("{}: {e}", parent.display()))?;
        }
        std::fs::write(&path, body).map_err(|e| format!("{}: {e}", path.display()))?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_provenance_lists_partition_the_vocabulary() {
        // assert_partition panics on any gap or duplicate, so constructing both shapes is the test.
        let mut t = crate::gate::tests::sample_task();
        provenance(&t);
        t.refsol.clear();
        provenance(&t);
    }

    #[test]
    fn a_wrapped_caveat_stays_inside_a_hundred_columns() {
        let long = "word ".repeat(120);
        for line in wrapped(&long, 2).lines() {
            assert!(line.chars().count() <= 100, "{} chars: {line}", line.chars().count());
        }
    }

    #[test]
    fn a_title_is_clipped_at_a_word_and_never_invented() {
        let p = "This crate evaluates simple integer arithmetic expressions (see src/lib.rs). \
                 There's a bug.";
        let t = title(p);
        assert!(p.starts_with(&t), "the title must be a prefix of the prompt, not a paraphrase");
        assert!(t.chars().count() <= 80);
        assert!(!t.ends_with(' '));
    }
}
